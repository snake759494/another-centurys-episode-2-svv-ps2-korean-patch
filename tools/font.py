import struct,numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=r"D:\ps2\ACE_어나더센츄리즈에피소드2_스페셜보컬버전"
H=12
def load_orig(metric,tex):
    d=metric; nr,ng=struct.unpack_from('<2H',d,0x10); ro,go=struct.unpack_from('<2I',d,0x14)
    ranges=[struct.unpack_from('<3I',d,ro+12*k) for k in range(nr)]
    a=np.zeros((512,1024),np.uint8); t=tex[0x20:0x40020]
    a[:,0::2]=np.frombuffer(t,np.uint8).reshape(512,512)&15
    a[:,1::2]=np.frombuffer(t,np.uint8).reshape(512,512)>>4
    glyphs=[]
    for k in range(ng):
        o=go+24*k; u0,v0,u1,v1=struct.unpack_from('<4f',d,o); x0,w,adv,p=struct.unpack_from('<4H',d,o+16)
        X0,Y0,X1,Y1=[int(round(v)) for v in (u0*1024,v0*512,u1*1024,v1*512)]
        glyphs.append(dict(bmp=a[Y0:Y1,X0:X1].copy(),x0=x0,w=w,adv=adv,p=p))
    return ranges,glyphs
def code_index(ranges,code):
    for s,e,b in ranges:
        if s<=code<=e: return b+code-s
    return None
def render(ch,ttf,size,thr=110,yoff=0,bold=0):
    f=ImageFont.truetype(ttf,size)
    im=Image.new('L',(32,32),0); dr=ImageDraw.Draw(im)
    asc,desc=f.getmetrics()
    dr.text((4,4+yoff),ch,font=f,fill=255,stroke_width=bold,stroke_fill=255)
    a=np.array(im)
    # 세로 기준: 폰트 em 박스를 12px 셀에 맞춤
    return a
