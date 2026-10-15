"""STR 청크: [0x10000][size][0][ngroup][nstr][tbl_off][0][0] + 그룹단어(3*ng-1) + u32 오프셋*nstr + 문자열(NUL)"""
import struct,re
def parse(d,o):
    if o+0x28>len(d) or d[o:o+4] not in (b'\x00\x00\x01\x00',b'\x00\x00\x00\x00'): return None
    sz,z,nc,ns,to,z2,z3=struct.unpack_from('<7I',d,o+4)
    if not(z==0 and z2==0 and z3==0 and 1<=nc<=64 and 0<ns<20000 and to==0x20+4*(3*nc-1) and o+sz<=len(d) and sz>=to+4*ns): return None
    gw=list(struct.unpack_from(f'<{3*nc-1}I',d,o+0x20))
    # 개수 검증
    idx=[0]+[gw[2+3*k] for k in range(nc-1)]+[ns]
    ids=[(gw[0],gw[1])]+[(gw[3+3*k],gw[4+3*k]) for k in range(nc-1)]
    for k in range(nc):
        if ids[k][1]-ids[k][0]+1!=idx[k+1]-idx[k]: return None
    offs=struct.unpack_from(f'<{ns}I',d,o+to)
    strs=[]
    for p in offs:
        if p==0: strs.append(None); continue
        if not(to+4*ns<=p<sz): return None
        e=d.find(b'\0',o+p,o+sz)
        if e<0: return None
        strs.append(d[o+p:e])
    idlist=[]
    for k in range(nc): idlist+=list(range(ids[k][0],ids[k][1]+1))
    return dict(off=o,size=sz,gw=gw,strs=strs,ids=idlist,magic=d[o:o+4])
def find_all(d):
    out=[]
    for m in re.finditer(rb'\x00\x00[\x00\x01]\x00(?=(?!\x00\x00\x00\x00)....\x00\x00\x00\x00[\x01-\x40]\x00\x00\x00)',d,re.S):
        o=m.start()
        if o%16: continue
        r=parse(d,o)
        if r: out.append(r)
    return out
def build(gw,strs,align=16,magic=0x10000):
    ns=len(strs);nc=(len(gw)+1)//3;to=0x20+4*len(gw)
    body=bytearray();offs=[];base=to+4*ns;seen={}
    for s in strs:
        if s is None: offs.append(0); continue
        offs.append(base+len(body)); body+=s+b'\0'
    raw=base+len(body); tot=(raw+align-1)//align*align
    if tot==raw: tot+=align
    out=bytearray(struct.pack('<8I',magic,tot,0,nc,ns,to,0,0))
    out+=struct.pack(f'<{len(gw)}I',*gw)+struct.pack(f'<{ns}I',*offs)+body
    out+=(b'\xcd' if magic==0 else b'\0')*(tot-len(out))
    return bytes(out)
