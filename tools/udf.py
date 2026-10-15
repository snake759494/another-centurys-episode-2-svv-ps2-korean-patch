"""UDF 1.02 최소 도구: 루트 디렉터리에서 파일 FE 찾기, 크기/할당(short_ad) 수정"""
import struct
def _sec(f,n): f.seek(n*2048); return f.read(2048)
def part_start(f):
    a=_sec(f,256); mvds=struct.unpack_from('<I',a,20)[0]
    for k in range(32):
        t=_sec(f,mvds+k); tid=struct.unpack_from('<H',t,0)[0]
        if tid==5: return struct.unpack_from('<I',t,188)[0]
        if tid==8: break
def lvd(f):
    a=_sec(f,256); mvds=struct.unpack_from('<I',a,20)[0]
    for k in range(32):
        t=_sec(f,mvds+k)
        if struct.unpack_from('<H',t,0)[0]==6: return t
def fe_ads(fe):
    tid=struct.unpack_from('<H',fe,0)[0]; assert tid==261,tid
    L_EA,L_AD=struct.unpack_from('<2I',fe,168); base=176+L_EA
    icb=struct.unpack_from('<H',fe,16+18)[0]&7
    return base,L_AD,icb
def find(f,name):
    ps=part_start(f); l=lvd(f)
    fsd_lb=struct.unpack_from('<I',l,248+4)[0]
    fsd=_sec(f,ps+fsd_lb); root_lb=struct.unpack_from('<I',fsd,400+4)[0]
    rfe=_sec(f,ps+root_lb); base,lad,icb=fe_ads(rfe)
    ln,pos=struct.unpack_from('<2I',rfe,base)
    f.seek((ps+pos)*2048); d=f.read(ln&0x3fffffff); o=0
    while o<len(d):
        tid=struct.unpack_from('<H',d,o)[0]
        if tid!=257: break
        lfi=d[o+19]; icbl,icblb=struct.unpack_from('<2I',d,o+20); liu=struct.unpack_from('<H',d,o+36)[0]
        nm=d[o+38+liu:o+38+liu+lfi]
        n=nm[1:].decode('latin1') if nm and nm[0]==8 else nm[1:].decode('utf-16-be') if nm else ''
        if n.lower()==name.lower(): return ps+icblb
        o+=(38+liu+lfi+3)//4*4
    return None
