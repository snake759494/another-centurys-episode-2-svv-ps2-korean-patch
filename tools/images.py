"""이미지 속 일본어 → 한국어로 다시 그림. 반환 {(top,sub): bytes}"""
import sys,os;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import bnd,tex,numpy as np
from PIL import Image,ImageDraw,ImageFont
R=r"D:\ps2\ACE_어나더센츄리즈에피소드2_스페셜보컬버전"
def F(n,s): return ImageFont.truetype(os.path.join(R,n+'.ttf'),s)
def img_of(x):
    rgba,idx,pal=tex.decode(x); return Image.fromarray(rgba.copy(),'RGBA')
def disclaimer(x):
    im=img_of(x); d=ImageDraw.Draw(im)
    bg=tuple(int(v) for v in np.asarray(im)[250,250]); d.rectangle((0,128,255,255),fill=bg)
    lines=["「Another Century's Episode2」의","스토리는 게임을 위해 독자적으로","제작된 것입니다.","원작인 각 애니메이션 작품을","참고하여 구성했지만, 각 작품의","설정이나 스토리와는 다릅니다."]
    f=F('SeoulHangangM',14)
    for k,l in enumerate(lines): d.text((6,134+k*19),l,font=f,fill=(235,235,235,255))
    return tex.encode_linear(x,im)
def stamp(im,xy,text,font,color,thr=40):
    m=Image.new('L',im.size,0); ImageDraw.Draw(m).text(xy,text,font=font,fill=255)
    a=np.array(im); cov=np.array(m)/255.0; mk=cov*255>thr
    c=np.array(color,float)
    a[mk,:3]=c[:3]; a[mk,3]=np.maximum(a[mk,3],(c[3]*cov[mk])).astype(np.uint8)
    return Image.fromarray(a,'RGBA')
def unit_titles(x):
    rgba,idx,pal=tex.decode(x)
    im=Image.fromarray(rgba.copy(),'RGBA'); d=ImageDraw.Draw(im); a=np.asarray(im)
    bgc=tuple(int(v) for v in a[2,2])
    op=[tuple(int(v) for v in c) for c in pal if c[3]>0]
    fg=max(op,key=lambda c:sum(c[:3])+c[3]); fg=(fg[0],fg[1],fg[2],min(255,fg[3]*2))
    d.rectangle((0,0,255,29),fill=bgc); d.rectangle((0,58,200,88),fill=bgc)
    f=F('SeoulHangangB',24)
    for y,t,w0 in ((1,'플레이어 유닛',256),(59,'어나더 유닛',200)):
        w=ImageDraw.Draw(im).textlength(t,font=f); im=stamp(im,((w0-w)//2,y),t,f,fg)
    return tex.encode_linear(x,im)
JOBS=[((38002,50019),disclaimer),((38003,50019),disclaimer),((62050,50641),unit_titles)]
def build(f,E):
    out={}
    for (top,sid),fn in JOBS:
        if top not in E: continue
        d=bnd.read(f,*E[top]); S={i:(o,s) for i,o,s in bnd.sub_entries(d)}
        if sid not in S: continue
        out.setdefault(top,{})[sid]=fn(d[S[sid][0]:S[sid][0]+S[sid][1]])
    # 같은 이미지가 다른 묶음에도 있으면 함께 교체
    return out

# ---------- 로딩/목표 카드(64500~64713) 제목 ----------
import json,cv2
def _title_layer(text,size,maxw):
    f=F('NanumSquareNeo-eHv',size*4)
    tw=int(f.getlength(text))+40; im=Image.new('L',(tw,size*4+40),0)
    ImageDraw.Draw(im).text((20,20),text,font=f,fill=255)
    sh=0.18; im=im.transform((tw+int(sh*im.height),im.height),Image.AFFINE,(1,sh,-sh*im.height,0,1,0),Image.BICUBIC)
    bb=im.getbbox(); im=im.crop(bb)
    w=max(1,im.width//4); h=max(1,im.height//4)
    if w>maxw: h=int(h*maxw/w); w=maxw
    return np.asarray(im.resize((w,h),Image.LANCZOS),np.float32)/255
def card(x,text,cid=0):
    rgba,idx,pal=tex.decode(x); a=rgba.astype(np.float32); H_,W_=a.shape[:2]
    BH=27 if cid%100==0 else 19
    band=slice(0,BH)
    lum=a[band,:,:3].mean(-1); sat=a[band,:,:3].max(-1)-a[band,:,:3].min(-1)
    white=(lum>170)&(sat<60)
    cols=np.nonzero(white.sum(0)>=2)[0]
    if len(cols)==0: return None
    x0,x1=int(cols[0]),int(cols[-1])
    right=cid>=64600
    # 지우기: 글자+외곽선 영역 인페인팅
    m=np.zeros((H_,W_),np.uint8); m[band][:, :]=0
    mm=np.zeros((H_,W_),np.uint8); mm[0:BH,max(0,x0-2):min(W_,x1+3)]=1
    dark=(a[...,:3].mean(-1)<70)
    txt=np.zeros((H_,W_),bool); txt[0:BH]=white
    txt=cv2.dilate(txt.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
    m=(txt&mm.astype(bool)).astype(np.uint8)
    rgb=cv2.inpaint(np.ascontiguousarray(rgba[...,:3]),m,3,cv2.INPAINT_TELEA)
    out=rgba.copy(); out[...,:3]=rgb
    # 한글 제목
    cov=_title_layer(text,14,W_-6)
    h,w=cov.shape; ty=max(0,(18-h)//2+1)
    tx=(W_-3-w) if right else 5
    pad=np.pad(cov,2); ol=cv2.dilate((pad>0.25).astype(np.uint8),np.ones((3,3),np.uint8)).astype(np.float32)
    region=out[ty-2 if ty>=2 else 0:ty+h+2, max(0,tx-2):tx+w+2].astype(np.float32)
    oy=0 if ty>=2 else 2-ty; ox=0 if tx>=2 else 2-tx
    olr=ol[oy:oy+region.shape[0],ox:ox+region.shape[1]]; cvr=pad[oy:oy+region.shape[0],ox:ox+region.shape[1]]
    region[...,:3]=region[...,:3]*(1-olr[...,None]*0.85)+np.array([15,15,25])*olr[...,None]*0.85
    region[...,:3]=region[...,:3]*(1-cvr[...,None])+255*cvr[...,None]
    region[...,3]=np.maximum(region[...,3],olr*255)
    out[ty-2 if ty>=2 else 0:ty+h+2, max(0,tx-2):tx+w+2]=region.astype(np.uint8)
    return tex.encode_linear(x,Image.fromarray(out,'RGBA'))
def build_cards(f,E):
    t=json.load(open(os.path.join(R,'work','translation','card_titles.json'),encoding='utf-8'))
    out={}
    for k,v in t.items():
        i=int(k)
        if i not in E: continue
        x=bnd.read(f,*E[i]); r=card(x,v,i)
        if r: out[i]=r
    return out
