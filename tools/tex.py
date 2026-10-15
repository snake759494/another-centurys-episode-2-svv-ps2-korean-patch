"""텍스처 파일(헤더 0x20 + 픽셀 + CLUT) 디코드/인코드. 헤더: [총크기][픽셀크기][1][스위즐][TEX0 u64]..."""
import sys,os,struct,numpy as np;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import gsmem
def is_tex(x):
    if len(x)<0x20: return False
    tot,n,one,swz=struct.unpack_from('<4I',x,0)
    if not(tot==len(x) and one==1 and swz in (0,1) and 0<n<tot): return False
    tex0=struct.unpack_from('<Q',x,0x10)[0]; psm=(tex0>>20)&63
    return psm in (0x00,0x01,0x02,0x13,0x14,0x1b,0x24,0x2c)
def info(x):
    tot,n,one,swz=struct.unpack_from('<4I',x,0); tex0=struct.unpack_from('<Q',x,0x10)[0]
    return dict(n=n,swz=swz,psm=(tex0>>20)&63,tw=1<<((tex0>>26)&15),th=1<<((tex0>>30)&15),cpsm=(tex0>>51)&15,tcc=(tex0>>34)&1)
def unswz_clut8(c):
    c=np.frombuffer(c,np.uint32).copy().reshape(-1)
    out=c.copy()
    for i in range(256):
        j=(i&0xe7)|((i&0x08)<<1)|((i&0x10)>>1); out[i]=c[j]
    return out
def decode(x):
    """→ RGBA 배열, 인덱스 배열(또는 None), 팔레트"""
    I=info(x); n=I['n']; tw,th=I['tw'],I['th']; data=x[0x20:0x20+n]; psm=I['psm']
    if psm==0x14:
        if I['swz']:
            from subfont import ct32_dims
            w32,h32=ct32_dims(tw,th); mem=gsmem.mem_from_ct32(data,w32,h32); idx=gsmem.read4(mem,tw,th,max(1,tw//64))
        else:
            b=np.frombuffer(data,np.uint8)[:tw*th//2].reshape(th,tw//2); idx=np.zeros((th,tw),np.uint8); idx[:,0::2]=b&15; idx[:,1::2]=b>>4
        pal=np.frombuffer(x[0x20+n:0x20+n+64],np.uint8).reshape(16,4)
    elif psm==0x13:
        if I['swz']:
            w32,h32=tw//2,th//2
            if w32<1 or h32<1: return None
            idx=gsmem.ct32_to_t8(data,w32,h32,tw,th) if (tw>=128 and th>=64) else np.frombuffer(data,np.uint8)[:tw*th].reshape(th,tw)
        else: idx=np.frombuffer(data,np.uint8)[:tw*th].reshape(th,tw)
        c=x[0x20+n:0x20+n+1024]
        if len(c)<1024: return None
        pal=unswz_clut8(c).view(np.uint8).reshape(256,4)
    elif psm==0x00:
        a=np.frombuffer(data,np.uint8)[:tw*th*4].reshape(th,tw,4); return a,None,None
    else: return None
    rgba=pal[idx].copy()
    rgba[...,3]=np.minimum(255,rgba[...,3].astype(int)*2)
    return rgba,idx,pal
def encode_linear(x,rgb_img):
    """선형(비스위즐) PSMT4/PSMT8 텍스처에 RGB(A) 이미지를 기존 팔레트로 양자화해 다시 기록"""
    I=info(x); assert not I['swz'] and I['psm'] in (0x13,0x14)
    rg,idx,pal=decode(x)
    p=pal.astype(int).copy(); p[:,3]=np.minimum(255,p[:,3]*2)
    a=np.asarray(rgb_img.convert('RGBA')).astype(int)
    d=((a[:,:,None,:]-p[None,None,:,:])**2).sum(-1); ni=d.argmin(-1).astype(np.uint8)
    out=bytearray(x); n=I['n']
    if I['psm']==0x13:
        # 8bpp: CLUT는 스위즐 순서 → decode에서 펼친 인덱스 그대로 원래 인덱스
        out[0x20:0x20+n]=ni.tobytes()
    else:
        out[0x20:0x20+n]=((ni[:,0::2]&15)|((ni[:,1::2]&15)<<4)).astype(np.uint8).tobytes()
    return bytes(out)
