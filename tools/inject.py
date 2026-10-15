"""번역 주입: STR 청크를 다시 만들고, 넘치면 컨테이너 끝으로 옮긴 뒤 헤더 슬롯/레코드 포인터만 수정"""
import sys,os,struct,json;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import bnd,strtab
class Enc:
    def __init__(self,cmap): self.cmap=cmap
    def __call__(self,text):
        out=bytearray()
        for ch in text:
            if ch in self.cmap: c=self.cmap[ch]; out+=bytes([c>>8,c&255])
            elif ch=='\n': out+=b'\n'
            else:
                try: out+=ch.encode('cp932')
                except UnicodeEncodeError: raise ValueError(f'인코딩 불가 문자 {ch!r} in {text!r}')
        return bytes(out)
def container_refs(d,old):
    """0x100 컨테이너에서 STR 오프셋을 가리키는 위치 목록(헤더[5],[6] + 레코드 +4)"""
    if struct.unpack_from('<I',d,0)[0]!=0x100: return None
    h=struct.unpack_from('<8I',d,0); cnt=h[7].to_bytes(4,'little')
    refs=[k*4 for k in (5,6) if h[k]==old]
    for slot,n in ((2,cnt[0]),(3,cnt[1]),(4,cnt[2]),(1,cnt[3])):
        base=h[slot]
        for r in range(n):
            p=base+16*r+4
            if p+4<=len(d) and struct.unpack_from('<I',d,p)[0]==old: refs.append(p)
    return refs
INPLACE={}
import re as _re
_PAT=_re.compile(rb'(?<=\x00)((?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\x20-\x7e\x0a])+)(?=\x00)')
_KANA=_re.compile('[ぁ-んァ-ヶ]')
TOO_LONG={}
def inplace(d,enc,stats,tr=None):
    """STR 밖에 직접 박힌 대사(<태그>로 시작)를 원래 바이트 길이 안에서 제자리 교체"""
    out=None
    cover=bytearray(len(d))
    for r in strtab.find_all(d): cover[r['off']:r['off']+r['size']]=b''*r['size']
    for m in _PAT.finditer(d):
        raw=m.group(1)
        if cover[m.start(1)] or not raw.startswith(b'<'): continue
        try: t=raw.decode('cp932')
        except UnicodeDecodeError: continue
        if not _KANA.search(t): continue
        ko=INPLACE.get(t) or (tr.get(t) if tr else None)
        if not ko: continue
        kb=enc(ko)
        if len(kb)>len(raw): TOO_LONG[t]=ko; continue
        if out is None: out=bytearray(d)
        out[m.start(1):m.end(1)]=kb+bytes(len(raw)-len(kb)); stats['inplace']=stats.get('inplace',0)+1
    return bytes(out) if out is not None else None
def patch_unit(d,tr,enc,stats):
    """d: 바이트(단일 파일). tr: {jp:ko}. 반환: 새 바이트 또는 None(변경 없음)"""
    r0=inplace(d,enc,stats,tr)
    if r0 is not None: d=r0
    chs=strtab.find_all(d)
    if not chs: return r0
    out=bytearray(d); changed=False; tail=[]
    for r in chs:
        news=[];hit=False
        for s in r['strs']:
            if s is None: news.append(None); continue
            try: t=s.decode('cp932')
            except UnicodeDecodeError: news.append(s); continue
            if t in tr and tr[t] is not None:
                news.append(enc(tr[t])); hit=True; stats['hit']+=1
            else:
                news.append(s)
        if not hit: continue
        nb=strtab.build(r['gw'],news,magic=int.from_bytes(r['magic'],'little'))
        o=r['off']; changed=True
        if r['off']==0 and len(chs)==1:
            return nb   # 단독 STR 파일: 통째로 교체
        if len(nb)<=r['size']:
            out[o:o+r['size']]=nb+b'\0'*(r['size']-len(nb))
        else:
            refs=container_refs(d,o)
            if not refs: raise RuntimeError(f'재배치 불가: 참조 없음 off={o:#x}')
            tail.append((refs,nb)); stats['reloc']+=1
    if not changed: return r0
    for refs,nb in tail:
        pos=(len(out)+15)//16*16; out+=b'\0'*(pos-len(out))+nb
        for p in refs: struct.pack_into('<I',out,p,pos)
    return bytes(out)
def rebuild_bnd(d,subs_new):
    """중첩 BND 재구성: subs_new {id:bytes}. 원본 정렬(0x20) 유지"""
    tot,n=struct.unpack_from('<2I',d,4)
    ents=bnd.sub_entries(d)
    hdr_end=ents[0][1]
    out=bytearray(d[:hdr_end]); table=[]
    for i,o,s in ents:
        data=subs_new.get(i,d[o:o+s])
        pos=len(out); table.append((i,pos)); out+=data
        pad=(-len(out))%0x20; out+=b'\0'*pad
    for k,(i,p) in enumerate(table): struct.pack_into('<2I',out,0x10+8*k,i,p)
    struct.pack_into('<I',out,4,len(out))
    return bytes(out)
def build_mods(tr,cmap,extra=None,only=None,font_subs=None):
    enc=Enc(cmap); f=open(bnd.ISO,'rb'); mods={}; stats={'hit':0,'reloc':0}
    for i,o,s in bnd.entries(f):
        if only and i not in only: continue
        d=bnd.read(f,o,s)
        if d[:4] in (b'VMD\0',b'MIC\0',b'PRM\0'): continue
        if d[:4]==b'BND\0':
            subs=dict(font_subs[i][1]) if font_subs and i in font_subs else {}
            for ii,oo,ss in bnd.sub_entries(d):
                if ii in subs: continue
                nd=patch_unit(d[oo:oo+ss],tr,enc,stats)
                if nd is not None: subs[ii]=nd
            if subs: mods[i]=rebuild_bnd(d,subs)
        else:
            nd=patch_unit(d,tr,enc,stats)
            if nd is not None: mods[i]=nd
    if extra: mods.update(extra)
    return mods,stats
