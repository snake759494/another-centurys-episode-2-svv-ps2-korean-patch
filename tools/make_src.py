"""번역 원문 배치 생성: 문맥 순서대로 중복 제거 → translation/src/NNN.json"""
import sys,os,json,re,collections;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import bnd,strtab,extract,font
W=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_f=open(bnd.ISO,'rb');_E={i:(o,s) for i,o,s in bnd.entries(_f)}
r,g=font.load_orig(bnd.read(_f,*_E[35]),bnd.read(_f,*_E[36]))
TAG=re.compile(r'<[a-z]+\([^)]*\)>|#c\[[0-9A-Fa-f]{6}\]|#c|%\d*[ds]')
def width(s):
    b=s.encode('cp932');i=0;w=0
    while i<len(b):
        c=b[i]
        if 0x81<=c<=0x9f or 0xe0<=c<=0xfc: code=(c<<8)|b[i+1];i+=2
        else: code=c;i+=1
        k=font.code_index(r,code)
        w+=g[k]['adv'] if k is not None and k<len(g) else 12
    return w
def cat(i):
    if 63000<=i<64000: return 'brief'
    if 6000<=i<7000 or 42000<=i<43000: return 'mission'
    return 'menu'
CAP={'brief':(363,3),'mission':(228,2)}
jp=re.compile('[ぁ-んァ-ヶ一-龥々ー]')
if __name__=='__main__':
    f=open(bnd.ISO,'rb'); seen={}; order=[]
    for (i,ii),d in extract.iter_units(f):
        for r_ in strtab.find_all(d):
            for k,s in enumerate(r_['strs']):
                if not s: continue
                try: t=s.decode('cp932')
                except UnicodeDecodeError: continue
                if not (jp.search(t) or re.search('[Ａ-Ｚ０-９！？]',t)): continue
                loc=f'{i}' if ii is None else f'{i}/{ii}'
                if t in seen: seen[t]['loc'].append(loc); continue
                plain=TAG.sub('',t); lines=plain.split('\n')
                w0=max(width(x) for x in lines); n0=len(lines)
                c=cat(i)
                if c in CAP: mw,ml=max(w0,CAP[c][0]),max(n0,CAP[c][1])
                else: mw,ml=w0+12,n0
                e=dict(jp=t,loc=[loc],id=r_['ids'][k],cat=c,maxchars=mw//12,maxlines=ml)
                seen[t]=e; order.append(e)
    # 배치 분할: 같은 상위 파일은 가능한 한 묶음, 약 4000자 단위
    os.makedirs(os.path.join(W,'translation','src'),exist_ok=True)
    batches=[];cur=[];n=0;last=None
    for e in order:
        top=e['loc'][0].split('/')[0]
        if cur and (n>=4000 or (n>=2500 and top!=last)):
            batches.append(cur);cur=[];n=0
        cur.append(e);n+=len(TAG.sub('',e['jp']));last=top
    if cur: batches.append(cur)
    for k,b in enumerate(batches):
        json.dump(b,open(os.path.join(W,'translation','src','%03d.json'%k),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    print('strings',len(order),'batches',len(batches))
    print([ (k,len(b),b[0]['loc'][0]) for k,b in enumerate(batches)])
