"""부분집합 글꼴(메트릭 0x10000 + PSMT4 텍스처) 읽기/재생성"""
import sys,os,struct,numpy as np;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import gsmem
from PIL import Image,ImageDraw,ImageFont
ROOT=r"D:\ps2\ACE_어나더센츄리즈에피소드2_스페셜보컬버전"
def tex_info(t):
    tex0=struct.unpack_from('<Q',t,0x10)[0]
    tw=1<<((tex0>>26)&15); th=1<<((tex0>>30)&15); psm=(tex0>>20)&63
    swz=struct.unpack_from('<I',t,0xc)[0]
    n=struct.unpack_from('<I',t,4)[0]
    return tw,th,psm,swz,n
def ct32_dims(tw,th):
    # PSMT4 tw x th 를 CT32로: 페이지 128x128(4bpp) ↔ 64x32(32bpp)
    pw=max(1,tw//128); ph=max(1,th//128)
    return pw*64, ph*32
def read_tex(t):
    tw,th,psm,swz,n=tex_info(t); assert psm in (0x14,0x24,0x2c) and (psm==0x14 or not swz)
    data=t[0x20:0x20+n]
    if swz:
        w32,h32=ct32_dims(tw,th)
        mem=gsmem.mem_from_ct32(data,w32,h32)
        a=gsmem.read4(mem,tw,th,max(1,tw//64))
    else:
        b=np.frombuffer(data,np.uint8).reshape(th,tw//2)
        a=np.zeros((th,tw),np.uint8); a[:,0::2]=b&15; a[:,1::2]=b>>4
    clut=t[0x20+n:0x20+n+64]
    return a,clut
def write_tex(t,a):
    tw,th,psm,swz,n=tex_info(t); out=bytearray(t)
    if swz:
        w32,h32=ct32_dims(tw,th)
        data=gsmem.t4_to_ct32(a,tw,th,max(1,tw//64),w32,h32)
    else:
        data=((a[:,0::2]&15)|((a[:,1::2]&15)<<4)).astype(np.uint8).tobytes()
    assert len(data)==n
    out[0x20:0x20+n]=data
    return bytes(out)
def read_metric(m):
    nr,ng=struct.unpack_from('<2H',m,0x10); ro,go=struct.unpack_from('<2I',m,0x14)
    H=struct.unpack_from('<I',m,8)[0]
    R=[struct.unpack_from('<3I',m,ro+12*k) for k in range(nr)]
    G=[]
    for k in range(ng):
        o=go+24*k; G.append(struct.unpack_from('<4f',m,o)+struct.unpack_from('<4H',m,o+16))
    codes={}
    for s,e,b in R:
        for c in range(s,e+1): codes[c]=b+c-s
    return H,R,G,codes
def load(m,t):
    H,R,G,codes=read_metric(m); a,clut=read_tex(t); th,tw=a.shape
    glyphs={}
    for c,k in codes.items():
        u0,v0,u1,v1,x0,w,adv,p=G[k]
        X0,Y0,X1,Y1=[int(round(v)) for v in (u0*tw,v0*th,u1*tw,v1*th)]
        glyphs[c]=dict(bmp=a[Y0:Y1,X0:X1].copy(),x0=x0,w=w,adv=adv,p=p)
    return H,glyphs,clut,(tw,th)
def palette_levels(clut):
    ent=[tuple(clut[4*i:4*i+4]) for i in range(16)]
    opaque=[i for i in range(1,16) if ent[i][3]>0]
    opaque.sort(key=lambda i:-ent[i][0])
    outline=opaque[-1]; fills=opaque[:-1]
    return outline,fills
def is_kanji(c):
    return 0x889F<=c<=0x9FFC or 0xE040<=c<=0xEAA4
def is_kana(c):
    return 0x829F<=c<=0x82F1 or 0x8340<=c<=0x8396
_fonts={}
def _font(path,size):
    k=(path,size)
    if k not in _fonts: _fonts[k]=ImageFont.truetype(path,size)
    return _fonts[k]
def coverage(ch,path,size,ss=4):
    if not has_glyph(path,ch): path=FALLBACK
    f=_font(path,size*ss); W=size*ss*2
    im=Image.new('L',(W,W),0); ImageDraw.Draw(im).text((size*ss//2,size*ss//2),ch,font=f,fill=255)
    im=im.resize((W//ss,W//ss),Image.BOX)
    return np.array(im).astype(np.float32)/255,size//2
def stylize(cov,outline,fills,thr=(0.82,0.62,0.45,0.30,0.16)):
    idx=np.zeros(cov.shape,np.uint8)
    lv=fills[:len(thr)]
    for t_,ix in reversed(list(zip(thr,lv))): idx[cov>=t_]=ix
    core=cov>=thr[-1]
    pad=np.pad(core,1); dil=np.zeros_like(core)
    for dy in (-1,0,1):
        for dx in (-1,0,1): dil|=pad[1+dy:1+dy+core.shape[0],1+dx:1+dx+core.shape[1]]
    idx[(dil)&(~core)]=outline
    return idx
def build(m,t,add,H_ink_ref=None,ttf=None,size=None,yoff=0,force=()):
    """add: {code: char} 새로 넣을 글리프. force: 원본 글리프라도 다시 그릴 code 집합"""
    H,glyphs,clut,(tw,th)=load(m,t)
    outline,fills=palette_levels(clut)
    keep={c:g for c,g in glyphs.items() if not is_kanji(c) and not is_kana(c) and c not in add}
    new={}
    for c,ch in add.items():
        cov,org=coverage(ch,ttf,size)
        idx=stylize(cov,outline,fills)
        ys=np.nonzero(idx.any(1))[0]; xs=np.nonzero(idx.any(0))[0]
        # 세로: 기준선 고정(글꼴 원점 기준), 가로: 잉크 영역
        top=org+yoff
        bm=idx[top:top+H, xs[0]:xs[-1]+1] if len(xs) else np.zeros((H,1),np.uint8)
        if bm.shape[0]<H: bm=np.pad(bm,((0,H-bm.shape[0]),(0,0)))
        w=bm.shape[1]
        if ch==' ': bm=np.zeros((H,1),np.uint8); w=1
        new[c]=dict(bmp=bm,x0=0,w=w,adv=w if ch!=' ' else size//3,p=0)
    allg=dict(keep); allg.update(new)
    codes=sorted(allg)
    # 범위표
    R=[];b=0
    for c in codes:
        if R and R[-1][1]==c-1: R[-1][1]=c
        else: R.append([c,c,b])
        b+=1
    # 패킹
    tex=np.zeros((th,tw),np.uint8); x=0;y=0; out_g=[]
    for c in codes:
        g=allg[c]; bm=g['bmp']; h,w=bm.shape
        if x+w>tw: x=0;y+=H
        if y+H>th: raise RuntimeError(f'텍스처 부족: {len(codes)}자, {codes.index(c)}번째에서 초과')
        tex[y:y+h,x:x+w]=bm
        out_g.append((x/tw,y/th,(x+w)/tw,(y+h)/th,g['x0'],w,g['adv'],g['p'])); x+=w+1
    nr=len(R); ng=len(codes); ro=0x20; go=ro+12*nr
    md=bytearray(m[:0x20])
    struct.pack_into('<2H',md,0x10,nr,ng); struct.pack_into('<2I',md,0x14,ro,go)
    for s,e,bb in R: md+=struct.pack('<3I',s,e,bb)
    for gg in out_g: md+=struct.pack('<4f',*gg[:4])+struct.pack('<4H',*gg[4:])
    tail=(-len(md))%16; md+=b'\0'*tail
    struct.pack_into('<I',md,4,len(md))
    return bytes(md),write_tex(t,tex),dict(glyphs=ng,rows=y//H+1,maxrows=th//H)

FALLBACK=r'C:\Windows\Fonts\msgothic.ttc'
def has_glyph(path,ch):
    from fontTools.ttLib import TTFont
    k=('cmap',path)
    if k not in _fonts:
        t=TTFont(path,fontNumber=0); _fonts[k]=set(t.getBestCmap().keys())
    return ord(ch) in _fonts[k]
def build_fit(m,t,cmap,prio,extra_chars,ttf):
    """prio: 우선순위 한글 목록. extra_chars: 반드시 넣을 비한글 문자. 들어가는 만큼 넣는다."""
    H,glyphs,clut,dims=load(m,t)
    size=H-3
    add_extra={}
    for ch in extra_chars:
        try: b=ch.encode('cp932')
        except UnicodeEncodeError: continue
        c=b[0] if len(b)==1 else (b[0]<<8)|b[1]
        if c in glyphs and not is_kana(c) and not is_kanji(c): continue
        add_extra[c]=ch
    lo,hi=0,len(prio); best=None
    while lo<=hi:
        mid=(lo+hi)//2
        add=dict(add_extra); add.update({cmap[ch]:ch for ch in prio[:mid]})
        try:
            r=_build_mixed(m,t,add,ttf,size); best=(mid,r); lo=mid+1
        except RuntimeError: hi=mid-1
    return best
def _build_mixed(m,t,add,ttf,size):
    a1={c:ch for c,ch in add.items()}
    return build(m,t,a1,ttf=ttf,size=size)
