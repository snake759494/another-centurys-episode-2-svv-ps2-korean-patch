import sys,os,struct;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import bnd,extract
def is_metric(d):
    if len(d)<0x40 or d[:4]!=b'\0\0\1\0': return False
    sz=struct.unpack_from('<I',d,4)[0]; nr,ng=struct.unpack_from('<2H',d,0x10); ro,go=struct.unpack_from('<2I',d,0x14)
    return ro==0x20 and go==0x20+12*nr and sz>=go+24*ng and ng>0 and sz<=len(d)
if __name__=='__main__':
    f=open(bnd.ISO,'rb')
    for (i,ii),d in extract.iter_units(f):
        if is_metric(d):
            nr,ng=struct.unpack_from('<2H',d,0x10)
            print(i,ii,hex(len(d)),'flag',struct.unpack_from('<I',d,8)[0],nr,ng)
