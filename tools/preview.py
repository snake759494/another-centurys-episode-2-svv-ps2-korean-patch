import sys,os,json,numpy as np;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import font
from PIL import Image
def encode(text,cmap):
    out=bytearray()
    for ch in text:
        if ch in cmap: c=cmap[ch]; out+=bytes([c>>8,c&255])
        else: out+=ch.encode('cp932')
    return bytes(out)
def render(b,ranges,gl,width=480):
    line=np.zeros((14,width),np.uint8);x=2;i=0
    while i<len(b):
        c=b[i]
        if c>=0x81: code=(c<<8)|b[i+1]; i+=2
        else: code=c;i+=1
        g=gl[font.code_index(ranges,code)]; h,w=g['bmp'].shape
        if x+g['x0']+w<width: line[1:1+h,x+g['x0']:x+g['x0']+w]=g['bmp']*255
        x+=g['adv']
    return line,x
