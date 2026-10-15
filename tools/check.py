"""번역 검사: python -I tools/check.py [배치번호...]  (없으면 전체)
검사: 누락, 태그·서식코드 일치, 사용 불가 문자, 일본어 잔존, 줄 폭(12px 글꼴 기준 px), 줄 수"""
import sys,os,json,re,glob;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import font
sys.stdout.reconfigure(encoding='utf-8')
W=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG=re.compile(r'<[a-z]+\([^)]*\)>|#c\[[0-9A-Fa-f]{6}\]|#c|%\d*[ds]')
HANGUL=set(bytes([a,b]).decode('cp949') for a in range(0xB0,0xC9) for b in range(0xA1,0xFF))
import bnd
_f=open(bnd.ISO,'rb');_E={i:(o,s) for i,o,s in bnd.entries(_f)}
r,g=font.load_orig(bnd.read(_f,*_E[35]),bnd.read(_f,*_E[36]))
JP=re.compile('[ぁ-んァ-ヶ一-龥々〆ヵヶ]')
def charw(ch):
    if ch in HANGUL: return 12
    if ch==' ': return 4
    if ch=='.': return 4
    b=ch.encode('cp932'); code=b[0] if len(b)==1 else (b[0]<<8)|b[1]
    k=font.code_index(r,code)
    return g[k]['adv'] if k is not None and k<len(g) else 12
def allowed(ch):
    if ch in HANGUL or ch=='\n': return True
    if JP.match(ch): return False
    try: b=ch.encode('cp932')
    except UnicodeEncodeError: return False
    return True
def check_one(e,ko):
    errs=[]
    if ko is None: return errs
    t1=TAG.findall(e['jp']); t2=TAG.findall(ko)
    if t1!=t2: errs.append(f'태그 불일치 {t1} → {t2}')
    bad=sorted(set(c for c in ko if not allowed(c)))
    if bad: errs.append(f'사용 불가 문자 {bad}')
    plain=TAG.sub('',ko); lines=plain.split('\n')
    if len(lines)>e['maxlines']: errs.append(f'줄 수 {len(lines)} > {e["maxlines"]}')
    lim=e['maxchars']*12
    for ln in lines:
        w=sum(charw(c) for c in ln if allowed(c))
        if w>lim: errs.append(f'줄 폭 {w}px > {lim}px: {ln}')
    return errs
def main(ids):
    tot=0;miss=0;bad=0
    for sp in sorted(glob.glob(os.path.join(W,'translation','src','*.json'))):
        k=os.path.basename(sp)[:3]
        if ids and k not in ids: continue
        src=json.load(open(sp,encoding='utf-8'))
        kp=os.path.join(W,'translation','ko',k+'.json')
        ko=json.load(open(kp,encoding='utf-8')) if os.path.exists(kp) else {}
        for e in src:
            tot+=1
            if e['jp'] not in ko: miss+=1; 
            if e['jp'] not in ko:
                if ids: print(f'[{k}] 누락: {e["jp"][:40]!r}')
                continue
            er=check_one(e,ko[e['jp']])
            if er: bad+=1; print(f'[{k}] {e["jp"][:50]!r}\n    → {str(ko[e["jp"]])[:80]!r}\n    '+'\n    '.join(er))
    print(f'전체 {tot} 누락 {miss} 오류 {bad}')
if __name__=='__main__': main(['%03d'%int(x) for x in sys.argv[1:]])
