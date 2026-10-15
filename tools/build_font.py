"""한글 글꼴 생성: 원본 메트릭(35)·텍스처(36)에서 한자 칸(0x889F~)을 KS X 1001 한글 2350자로 교체"""
import sys,struct,json,numpy as np
from PIL import Image,ImageDraw,ImageFont
import os;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import font
TTF=font.ROOT+r'\NanumSquareNeo-bRg.ttf'
SIZE=12; YOFF=0; THR=100
def hangul2350():
    out=[]
    for b1 in range(0xB0,0xC9):
        for b2 in range(0xA1,0xFF):
            out.append(bytes([b1,b2]).decode('cp949'))
    return out
def kanji_codes(ranges):
    codes=[]
    for s,e,b in ranges:
        for c in range(s,e+1):
            if c>=0x889F: codes.append(c)
    return codes
_F=None
def glyph(ch,size=SIZE,thr=THR):
    global _F
    if _F is None: _F=ImageFont.truetype(TTF,size)
    im=Image.new('L',(40,40),0); ImageDraw.Draw(im).text((8,8+YOFF),ch,font=_F,fill=255)
    a=np.array(im)>thr
    return a
def make_bitmap(ch):
    a=glyph(ch)
    # 기준선: '가' 글자의 잉크 영역으로 세로 위치 결정
    y0=REF_TOP
    rows=a[y0:y0+12]
    cols=np.nonzero(rows.any(0))[0]
    if len(cols)==0: return np.zeros((12,1),np.uint8),0
    bm=rows[:,cols[0]:cols[-1]+1].astype(np.uint8)
    return bm,0
def ref_top():
    a=np.zeros((40,40),bool)
    for ch in '가나다라마바사아자차카타파하밝뷁깊훑':
        a|=glyph(ch)
    ys=np.nonzero(a.any(1))[0]; h=ys[-1]-ys[0]+1
    return ys[0]-(12-h)//2, h
REF_TOP,REF_H=ref_top()
def build(metric,tex,out_metric,out_tex,charmap_path,extra=None):
    ranges,gl=font.load_orig(metric,tex)
    nr,ng=struct.unpack_from('<2H',metric,0x10); ro,go=struct.unpack_from('<2I',metric,0x14)
    codes=kanji_codes(ranges); first=font.code_index(ranges,codes[0])
    hs=hangul2350()
    assert len(hs)<=len(codes)
    cmap={}
    newg=list(gl)
    for i,ch in enumerate(hs):
        bm,_=make_bitmap(ch)
        newg[font.code_index(ranges,codes[i])]=dict(bmp=bm,x0=0,w=bm.shape[1],adv=bm.shape[1]+1,p=0)
        cmap[ch]=codes[i]
    # ASCII 마침표를 2x2로 키움(한국어 문장부호 가독성)
    dot=np.zeros((12,2),np.uint8); dot[9:11,:]=1
    newg[font.code_index(ranges,0x2e)]=dict(bmp=dot,x0=1,w=2,adv=4,p=0)
    for i in range(len(hs),len(codes)):
        newg[font.code_index(ranges,codes[i])]=dict(bmp=np.zeros((12,1),np.uint8),x0=0,w=1,adv=4,p=0)
    # 패킹
    tex_a=np.zeros((512,1024),np.uint8); x=0;y=0
    md=bytearray(metric[:go])
    cache={}
    for k,g in enumerate(newg):
        bm=g['bmp']; h,w=bm.shape
        key=bm.tobytes()+bytes([h,w])
        if key in cache: X,Y=cache[key]
        else:
            if x+w>1024: x=0;y+=13
            assert y+12<=512,'texture full'
            tex_a[y:y+h,x:x+w]=bm; X,Y=x,y; cache[key]=(x,y); x+=w+1
        md+=struct.pack('<4f',X/1024,Y/512,(X+w)/1024,(Y+h)/512)+struct.pack('<4H',g['x0'],w,g['adv'],g['p'])
    md+=metric[go+24*ng:]
    assert len(md)==len(metric)
    packed=(tex_a[:,0::2]&15)|((tex_a[:,1::2]&15)<<4)
    nt=bytearray(tex); nt[0x20:0x40020]=packed.astype(np.uint8).tobytes()
    open(out_metric,'wb').write(md); open(out_tex,'wb').write(nt)
    json.dump(cmap,open(charmap_path,'w',encoding='utf-8'),ensure_ascii=False)
    print('font built; rows used',y//13+1,'REF',REF_TOP,REF_H)
    return cmap
if __name__=='__main__':
    build(open('orig/35.bin','rb').read(),open('orig/36.bin','rb').read(),'tmp/35_ko.bin','tmp/36_ko.bin','tmp/charmap.json')
