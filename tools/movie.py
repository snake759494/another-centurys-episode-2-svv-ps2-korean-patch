"""동영상 자막 한글화: 박힌 일본어 자막을 지우고(인페인팅) 같은 자리·같은 페이드로 한글을 그린다.
python tools/movie.py <원본 PSS> <출력 PSS> <자막 json>
- 바뀐 프레임이 든 GOP 구간만 닫힌 GOP로 재인코딩, 구간 바이트가 원본 이하가 되는 가장 고운 q 선택, 남는 바이트는 0 채움
"""
import os,sys,json,subprocess
import numpy as np,av,cv2
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import pss
FF=imageio_ffmpeg.get_ffmpeg_exe()
ROOT=r"D:\ps2\ACE_어나더센츄리즈에피소드2_스페셜보컬버전"
W,H=640,448
Q_STEPS=[2,3,4,5,6,7,8,10,12,14,17,20,24,28,31]
def stroke_mask(fr):
    fr=np.ascontiguousarray(fr)
    g=cv2.cvtColor(fr,cv2.COLOR_RGB2GRAY).astype(np.int16)
    bg=cv2.medianBlur(g.astype(np.uint8),15).astype(np.int16)
    sat=fr.max(-1).astype(np.int16)-fr.min(-1)
    return ((g-bg)>7)&(sat<90)&(g>50)
def persist(frames,f0,f1,y0,y1):
    P=np.zeros((H,W),np.float32); n=0
    for k in range(f0,f1,2): P+=stroke_mask(frames[k]); n+=1
    P/=max(n,1); P[:y0]=0; P[y1:]=0
    return P
def bands(P,want,thr=0.30):
    st=P>thr
    prof=st.sum(1); on=prof>=3; runs=[];s=None
    for i,v in enumerate(list(on)+[False]):
        if v and s is None: s=i
        if not v and s is not None: runs.append([s,i]); s=None
    m=[]
    for r in runs:
        if m and r[0]-m[-1][1]<=2: m[-1][1]=r[1]
        else: m.append(r)
    m=[r for r in m if r[1]-r[0]>=6]
    if len(m)!=want: print('  경고: 줄 감지',len(m),'예상',want,m,flush=True)
    return m,st
def xext(st,b):
    xs=np.nonzero(st[b[0]:b[1]].sum(0)>0)[0]
    return int(xs[0]),int(xs[-1])
def alpha_series(frames,f0,f1,b,x0,x1,st):
    sm=st[b[0]:b[1],x0:x1+1]; tot=max(1,sm.sum())
    e=np.array([(stroke_mask(frames[k])[b[0]:b[1],x0:x1+1]&sm).sum()/tot for k in range(f0,f1)],float)
    ref=np.percentile(e,90) if e.max()>0 else 1
    return np.clip(e/max(ref,1e-3)*1.1,0,1)
FONT=os.path.join(ROOT,'SeoulHangangM.ttf')
CWD=18.6; CWN=21.6
def make_jobs(cfg):
    jobs=[]
    for f0,f1,name,lines,lens in cfg.get('dialogue',[]):
        rects=[(366,388,114,int(120+lens[0]*CWD+10))]
        for k,L in enumerate(lens[1:]): rects.append((388+19*k,409+19*k,130,int(138+L*CWD+10)))
        jobs.append((f0,f1,rects,[name]+lines,'dlg',None))
    for f0,f1,lines,geo,*jp in cfg.get('narration',[]):
        rects=[(cy-13,cy+13,int(320-L*CWN/2-34),int(320+L*CWN/2+34)) for cy,L in geo]
        jobs.append((f0,f1,rects,lines,'nar',jp[0] if jp else None))
    return jobs
def event_mask(frames,f0,f1,rects,alpha=None):
    """자막이 다 보이는 프레임들에서 밝기가 거의 변하지 않고 주변보다 밝은 화소 = 박힌 글자"""
    ks=list(range(f0,f1)) if alpha is None else [f0+i for i,v in enumerate(alpha) if v>0.85]
    if len(ks)<6: ks=list(range(f0,f1))
    ks=ks[::max(1,len(ks)//60)]
    G=np.stack([cv2.cvtColor(np.ascontiguousarray(frames[k]),cv2.COLOR_RGB2GRAY) for k in ks]).astype(np.float32)
    mean=G.mean(0); std=G.std(0); bg=cv2.medianBlur(mean.astype(np.uint8),15).astype(np.float32)
    R=np.zeros((H,W),bool)
    for (y0,y1,x0,x1) in rects: R[y0:y1,x0:x1]=True
    m=((mean-bg)>5)&(std<42)&R
    return cv2.dilate(m.astype(np.uint8),np.ones((5,5),np.uint8))
def render_frame(fr,rects,texts,kind,alphas,emask=None,plate=None,strict=False):
    mask=np.zeros((H,W),np.uint8) if emask is None else emask.copy()
    near=cv2.dilate(mask,np.ones((7,7),np.uint8)) if emask is not None else None
    for (y0,y1,x0,x1) in rects:
        sm=stroke_mask(fr[y0:y1,x0:x1]).astype(np.uint8)
        if near is not None: sm&=near[y0:y1,x0:x1]
        if strict: sm[:]=0
        mask[y0:y1,x0:x1]|=sm
    if plate is not None and mask.any():
        m=cv2.GaussianBlur(cv2.dilate(mask,np.ones((9,9),np.uint8)).astype(np.float32),(7,7),0)[...,None]
        fr=(np.asarray(fr,np.float32)*(1-m)+plate.astype(np.float32)*m).astype(np.uint8); mask=mask*0
    if mask.any():
        mask=cv2.dilate(mask,np.ones((3,3),np.uint8))
        fr=cv2.inpaint(np.ascontiguousarray(fr),mask,3,cv2.INPAINT_TELEA)
    if kind=='nar' and max(alphas)>0.03:
        ys=[r[0] for r in rects]+[r[1] for r in rects]; xs=[r[2] for r in rects]+[r[3] for r in rects]
        sh=np.zeros((H,W),np.float32); sh[min(ys)-4:max(ys)+4,min(xs)-6:max(xs)+6]=1
        sh=cv2.GaussianBlur(sh,(0,0),9)*0.5*max(alphas)
        fr=(np.asarray(fr,np.float32)*(1-sh[...,None])).astype(np.uint8)
    base=Image.fromarray(fr).convert('RGBA')
    for k,(y0,y1,x0,x1) in enumerate(rects[:len(texts)]):
        a=alphas[k]
        if a<=0.03: continue
        L=Image.new('RGBA',(W,H),(0,0,0,0)); cy=(y0+y1)/2
        if kind=='nar': draw_line(L,texts[k],320,cy,19,'mm')
        else: draw_line(L,texts[k],x0+6,cy,17 if k else 16,'lm')
        A=np.array(L); A[...,3]=(A[...,3]*a).astype(np.uint8); base.alpha_composite(Image.fromarray(A))
    return np.asarray(base.convert('RGB'))
def draw_line(layer,text,x,y,size,anchor):
    f=ImageFont.truetype(FONT,size); d=ImageDraw.Draw(layer)
    d.text((x,y),text,font=f,fill=(255,255,255,255),anchor=anchor,stroke_width=1,stroke_fill=(10,10,20,170))
def process(src_path,dst_path,cfg):
    src=open(src_path,'rb').read(); es=pss.video_es(src)
    st=[];i=0
    while True:
        i=es.find(b'\x00\x00\x01\xb8',i)
        if i<0: break
        st.append(i); i+=4
    st[0]=0; end=len(es)-4 if es.endswith(b'\x00\x00\x01\xb7') else len(es)
    gops=[(s,st[k+1] if k+1<len(st) else end) for k,s in enumerate(st)]
    nf=[es.count(b'\x00\x00\x01\x00',a,b) for a,b in gops]; first=np.cumsum([0]+nf); total=int(first[-1])
    cache=src_path+'.frames.npy'
    if os.path.exists(cache):
        mm=np.load(cache,mmap_mode='r'); assert mm.shape[0]==total
    else:
        tmp=dst_path+'.m2v'; open(tmp,'wb').write(es)
        mm=np.lib.format.open_memmap(cache,mode='w+',dtype=np.uint8,shape=(total,H,W,3))
        c=av.open(tmp); n=0
        for fr in c.decode(video=0): mm[n]=fr.to_ndarray(format='rgb24'); n+=1
        c.close(); os.remove(tmp); assert n==total,(n,total); mm.flush()
    changed=np.zeros(total,bool)
    class _Store:
        """수정 프레임을 디스크(memmap)에 보관해 메모리 사용을 줄인다"""
        def __init__(s): s.mm=np.lib.format.open_memmap(dst_path+'.out.npy',mode='w+',dtype=np.uint8,shape=(total,H,W,3)); s.has=np.zeros(total,bool)
        def get(s,k,d=None): return np.array(s.mm[k]) if s.has[k] else d
        def __getitem__(s,k): return np.array(s.mm[k])
        def __setitem__(s,k,v): s.mm[k]=v; s.has[k]=True
    out_frames=_Store()
    jobs=make_jobs(cfg)
    if DRY: return
    for f0,f1,rects,texts,kind,jp in jobs:
        al=[]
        for (y0,y1,x0,x1) in rects:
            e=np.array([stroke_mask(mm[k][y0:y1,x0:x1]).sum() for k in range(f0,f1)],float)
            lo=np.percentile(e,5); hi=np.percentile(e,90)
            al.append(np.clip((e-lo)/max(hi-lo,1)*1.1,0,1))
        em=event_mask(mm,f0,f1,rects,np.min(al,0)); pl={}
        al=line_alpha(mm,f0,f1,rects,em)
        print('  구간',f0,f1,'시간축 복원',len(pl),'/',f1-f0,flush=True)
        for fi in range(f0,f1):
            fr=out_frames.get(fi)
            if fr is None: fr=np.array(mm[fi])
            out_frames[fi]=render_frame(fr,rects,texts,kind,[float(x[fi-f0]) for x in al],em,pl.get(fi),strict=True); changed[fi]=True
    # GOP마다 따로 인코딩: GOP 개수·프레임 수·바이트 위치를 원본과 같게 유지(스트리밍 일정 보존)
    out=bytearray(); prev=0; qs=[]; nrun=0
    for g in range(len(gops)):
        if not changed[first[g]:first[g+1]].any(): continue
        out+=es[prev:gops[g][0]]
        seg=[out_frames.get(k,mm[k]) for k in range(first[g],first[g+1])]
        budget=gops[g][1]-gops[g][0]
        for q in Q_STEPS:
            enc=encode(seg,q)
            if len(enc)<=budget: break
        assert len(enc)<=budget,(g,len(enc),budget)
        assert enc.count(b'\x00\x00\x01\x00')==len(seg)
        assert enc.count(b'\x00\x00\x01\xb8')==1,(g,enc.count(b'\x00\x00\x01\xb8'))
        out+=enc+b'\0'*(budget-len(enc)); prev=gops[g][1]; qs.append(q); nrun+=1
    out+=es[prev:]; assert len(out)==len(es)
    dst=pss.put_video_es(src,bytes(out)); assert len(dst)==len(src)
    open(dst_path,'wb').write(dst)
    pv=dst_path+'_preview'; os.makedirs(pv,exist_ok=True)
    for f0,f1,bs,texts,kind,_ in jobs:
        k=(f0+f1)//2; Image.fromarray(out_frames[k]).save(os.path.join(pv,f'{k:05d}.png'))
    print('바뀐 프레임',int(changed.sum()),'GOP',nrun,'q 최대',max(qs),flush=True)
def encode(frames,q):
    cmd=[FF,'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','%dx%d'%(W,H),'-r','30000/1001','-i','-',
         '-c:v','mpeg2video','-pix_fmt','yuv420p','-qscale:v',str(q),'-qmin','1','-qmax','31','-g',str(len(frames)),'-bf','2','-flags','+cgop',
         '-sc_threshold','1000000000','-intra_vlc','1','-dc','10','-maxrate','4500000','-bufsize','1441792',
         '-aspect','10:7','-seq_disp_ext','never','-f','mpeg2video','-']
    r=subprocess.run(cmd,input=b''.join(np.ascontiguousarray(f).tobytes() for f in frames),capture_output=True)
    if r.returncode: raise RuntimeError(r.stderr.decode())
    es=r.stdout
    return es[:-4] if es.endswith(b'\x00\x00\x01\xb7') else es
def line_alpha(frames,f0,f1,rects,em):
    """줄마다 원래 글자 화소(em)가 주변보다 얼마나 밝은지로 페이드 값(0~1)을 잰다"""
    out=[]
    for (y0,y1,x0,x1) in rects:
        m=em[y0:y1,x0:x1]>0
        if m.sum()<8: out.append(np.zeros(f1-f0)); continue
        c=[]
        for k in range(f0,f1):
            g=cv2.cvtColor(np.ascontiguousarray(frames[k][max(0,y0-8):y1+8,max(0,x0-8):x1+8]),cv2.COLOR_RGB2GRAY).astype(np.float32)
            bg=cv2.medianBlur(g.astype(np.uint8),15).astype(np.float32)
            d=(g-bg)[y0-max(0,y0-8):y0-max(0,y0-8)+(y1-y0),x0-max(0,x0-8):x0-max(0,x0-8)+(x1-x0)]
            c.append(float(np.maximum(d[m],0).mean()))
        c=np.array(c); lo=np.percentile(c,3); hi=np.percentile(c,85)
        a=np.clip((c-lo)/max(hi-lo,1e-3),0,1)
        a=np.convolve(np.pad(a,2,mode='edge'),np.ones(5)/5,mode='valid')   # 깜빡임 완화
        out.append(a)
    return out
DRY=False
if __name__=='__main__':
    DRY='--dry' in sys.argv
    a=[x for x in sys.argv[1:] if x!='--dry']
    process(a[0],a[1],json.load(open(a[2],encoding='utf-8')))

# ---------- 시간축 배경 복원(광류 추적) ----------
def _gray(fr): return cv2.cvtColor(np.ascontiguousarray(fr),cv2.COLOR_RGB2GRAY)
def _flow(a,b,mask):
    """a(k)의 각 화소가 b(k±1)의 어디에 있는지. 자막 영역은 주변 흐름으로 메움"""
    F=cv2.calcOpticalFlowFarneback(a,b,None,0.5,4,21,3,5,1.1,0)
    if mask is not None and mask.any():
        for c in range(2): F[...,c]=cv2.inpaint(np.ascontiguousarray(F[...,c]),mask,9,cv2.INPAINT_TELEA)
    return F
def _cut(a,b): return np.abs(a.astype(np.int16)-b.astype(np.int16)).mean()>22
def clean_plates(frames,f0,f1,emask,alpha=None):
    """f0..f1-1 각 프레임의 자막 없는 배경(광류 추적). 자막이 가장 옅은 프레임을 기준으로 삼고,
    자막 둘레 띠에서 실제 프레임과 맞지 않으면 버린다(호출 측이 인페인팅으로 대체)."""
    T=len(frames); m=cv2.dilate(emask,np.ones((9,9),np.uint8))
    ring=(cv2.dilate(m,np.ones((17,17),np.uint8))>0)&(m==0)
    g={k:_gray(frames[k]) for k in range(f0,f1)}
    yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
    n=f1-f0; a=np.zeros(n) if alpha is None else alpha
    w=max(3,min(25,n//6))
    anchors=[(f0+int(np.argmin(a[:w])),1),(f0+n-w+int(np.argmin(a[n-w:])),-1)]
    plates={}; dist={}
    for anchor,step in anchors:
        if a[anchor-f0]>0.15: continue
        C=np.asarray(frames[anchor]); M=np.dstack([xx,yy]); k=anchor
        for direction in (step,-step):
            M=np.dstack([xx,yy]); k=anchor
            while True:
                nk=k+direction
                if not(f0<=nk<f1) or _cut(g[k],g[nk]): break
                F=_flow(g[nk],g[k],m)
                M=cv2.remap(M,xx+F[...,0],yy+F[...,1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
                P=cv2.remap(C,M[...,0],M[...,1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
                err=np.abs(P[ring].astype(np.int16)-np.asarray(frames[nk])[ring].astype(np.int16)).mean()
                if err>14: break
                d=abs(nk-anchor)
                if nk not in dist or d<dist[nk]: plates[nk]=P; dist[nk]=d
                k=nk
    return plates

def shift_fill(fr,mask,cands=(-16,16,-32,32,-48,48,-64,64,-80,80)):
    """가려진 화소를 같은 프레임의 위/아래 실제 배경으로 채움(흐림 없음). 남는 화소만 인페인팅."""
    fr=np.asarray(fr).copy(); m=mask>0; left=m.copy()
    for dy in cands:
        if not left.any(): break
        src=np.roll(fr,-dy,axis=0); sm=np.roll(m,-dy,axis=0)
        ok=left&~sm
        if dy>0: ok[H-dy:]=False
        else: ok[:-dy]=False
        fr[ok]=src[ok]; left&=~ok
    if left.any(): fr=cv2.inpaint(fr,left.astype(np.uint8),3,cv2.INPAINT_TELEA)
    return fr

JPFONT=r'C:\Windows\Fonts\msmincho.ttc'
def _render_jp(text,size,pitch):
    f=ImageFont.truetype(JPFONT,size); w=int(len(text)*pitch+size*2)
    im=Image.new('L',(w,size*2),0); d=ImageDraw.Draw(im); x=size//2
    for ch in text:
        d.text((x,size//2),ch,font=f,fill=255)
        x+=pitch if ord(ch)>0x2000 else pitch*0.55
    a=np.asarray(im,np.float32)/255; ys,xs=np.nonzero(a>0.2)
    return a[ys.min():ys.max()+1,xs.min():xs.max()+1]
def glyph_mask(frames,f0,f1,rects,jp,alpha):
    """일본어 원문을 명조체로 그려 화면의 자막 위치에 맞추고, 그 획만 마스크로 쓴다"""
    ks=[f0+i for i,v in enumerate(alpha) if v>0.85] or list(range(f0,f1))
    ks=ks[::max(1,len(ks)//60)]
    P=np.zeros((H,W),np.float32)
    for k in ks:
        fr=np.asarray(frames[k])
        for (y0,y1,x0,x1) in rects: P[y0:y1,x0:x1]+=stroke_mask(fr[y0:y1,x0:x1])
    P/=len(ks)
    out=np.zeros((H,W),np.uint8)
    for (y0,y1,x0,x1),t in zip(rects,jp):
        ya,yb=max(0,y0-8),min(H,y1+8); xa,xb=max(0,x0-20),min(W,x1+20)
        reg=P[ya:yb,xa:xb]; best=(-1,)
        for size in (17,18,19,20):
            for pitch in np.arange(size*1.0,size*1.25,0.4):
                T=_render_jp(t,size,pitch)
                if T.shape[0]>reg.shape[0] or T.shape[1]>reg.shape[1]: continue
                r=cv2.matchTemplate(reg,T,cv2.TM_CCORR_NORMED); _,v,_,loc=cv2.minMaxLoc(r)
                if v>best[0]: best=(v,loc,T)
        v,(lx,ly),T=best
        m=np.zeros_like(reg,np.uint8); m[ly:ly+T.shape[0],lx:lx+T.shape[1]]=(T>0.15)
        out[ya:yb,xa:xb]|=m
    return cv2.dilate(out,np.ones((5,5),np.uint8))
