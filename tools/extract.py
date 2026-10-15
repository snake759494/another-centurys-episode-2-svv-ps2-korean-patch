"""DATA.BIN 전체에서 STR 청크 문자열 추출 -> tmp/uniq.json {jp:[위치...]}"""
import sys,os,re,json,collections;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import bnd,strtab
SKIP={b'VMD\0',b'MIC\0',b'PRM\0'}
jp=re.compile('[ぁ-んァ-ヶ一-龥々ー]')
def iter_units(f):
    for i,o,s in bnd.entries(f):
        d=bnd.read(f,o,s)
        if d[:4] in SKIP: continue
        if d[:4]==b'BND\0':
            for ii,oo,ss in bnd.sub_entries(d):
                if d[oo:oo+4] in SKIP: continue
                yield (i,ii),d[oo:oo+ss]
        else: yield (i,None),d
if __name__=='__main__':
    f=open(bnd.ISO,'rb'); uniq=collections.OrderedDict(); n=0
    for (i,ii),d in iter_units(f):
        for r in strtab.find_all(d):
            for k,s in enumerate(r['strs']):
                if not s: continue
                try: t=s.decode('cp932')
                except UnicodeDecodeError: continue
                if jp.search(t) or re.search('[Ａ-Ｚ０-９！？]',t):
                    uniq.setdefault(t,[]).append(f'{i}' if ii is None else f'{i}/{ii}')
    json.dump(uniq,open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'tmp','uniq.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=0)
    print(len(uniq),sum(len(t) for t in uniq))
