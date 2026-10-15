"""전체 빌드: 글꼴(12px 전역 + 부분집합 글꼴) + 번역 주입 → ISO"""
import sys,os,json,glob,time,re,collections;sys.stdout.reconfigure(encoding="utf-8");sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import bnd,inject,isobuild,build_font,subfont,images
W=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TTF=subfont.ROOT+r'\NanumSquareNeo-cBd.ttf'
TAG=re.compile(r'<[a-z]+\([^)]*\)>|#c\[[0-9A-Fa-f]{6}\]|#c|%\d*[ds]')
def load_tr():
    tr={}
    for p in sorted(glob.glob(os.path.join(W,'translation','ko','*.json'))):
        for k,v in json.load(open(p,encoding='utf-8')).items():
            if v: tr[k]=v
    return tr
def is_mission(loc):
    top=int(loc.split('/')[0]); return 6000<=top<7000 or 42000<=top<43000 or 38000<=top<38007 or top==5000
def prio_lists(tr,cmap):
    src=[e for p in sorted(glob.glob(os.path.join(W,'translation','src','*.json'))) for e in json.load(open(p,encoding='utf-8'))]
    allc=collections.Counter(); mis=collections.Counter(); menu=collections.Counter(); hud=collections.Counter(); extra=set()
    for e in src:
        ko=tr.get(e['jp'])
        if not ko: continue
        plain=TAG.sub('',ko)
        for ch in plain:
            if ch in cmap:
                allc[ch]+=1
                if any(is_mission(l) for l in e['loc']): mis[ch]+=1
                if not all(is_mission(l) for l in e['loc']): menu[ch]+=1
                if any(is_mission(l) for l in e['loc']) and '<' not in e['jp'] and len(plain)<=24: hud[ch]+=1
            elif ch not in '\n': extra.add(ch)
    def order(first):
        a=[c for c,_ in first.most_common()]; s=set(a)
        return a+[c for c,_ in allc.most_common() if c not in s]
    return order(mis),order(menu),order(hud),sorted(extra)
def font_mods(f,E,cmap,tr):
    pm,pmenu,phud,extra=prio_lists(tr,cmap)
    print('한글 종류:',len(set(pm)),'추가 문자',''.join(extra))
    out={}
    def sub(top,mid):
        d=bnd.read(f,*E[top]); S={ii:(oo,ss) for ii,oo,ss in bnd.sub_entries(d)}
        return d,S,d[S[mid][0]:S[mid][0]+S[mid][1]]
    # 미션 HUD: 38000의 19px 글꼴 하나를 만들어 슬롯 0·1(2500/2501, 2000/2001) 모두에 쓴다
    d,S,m=sub(38000,2500); t=d[S[2000][0]:S[2000][0]+S[2000][1]]
    n,(mm,tt,info)=subfont.build_fit(m,t,cmap,pm,extra,TTF)
    print(f'  미션 19px: 한글 {n}/{len(pm)}')
    for top in range(38000,38007):
        out[top]=(bnd.read(f,*E[top]),{2500:mm,2501:mm,2000:tt,2001:tt})
    for top in range(62050,62058):
        d=bnd.read(f,*E[top]); S={ii:(oo,ss) for ii,oo,ss in bnd.sub_entries(d)}
        if 2500 not in S: continue
        m=d[S[2500][0]:S[2500][0]+S[2500][1]]; t=d[S[2000][0]:S[2000][0]+S[2000][1]]
        n,(m2,t2,info)=subfont.build_fit(m,t,cmap,pmenu,extra,TTF)
        print(f'  {top}/2500: 한글 {n}/{len(pmenu)}')
        out[top]=(d,{2500:m2,2000:t2})
    return out
if __name__=='__main__':
    out=sys.argv[1]
    f=open(bnd.ISO,'rb'); E={i:(o,s) for i,o,s in bnd.entries(f)}
    m35=bnd.read(f,*E[35]); m36=bnd.read(f,*E[36])
    cmap=build_font.build(m35,m36,os.path.join(W,'tmp','35_ko.bin'),os.path.join(W,'tmp','36_ko.bin'),os.path.join(W,'tmp','charmap.json'))
    extra={35:open(os.path.join(W,'tmp','35_ko.bin'),'rb').read(),36:open(os.path.join(W,'tmp','36_ko.bin'),'rb').read()}
    tr=load_tr(); t=time.time()
    inject.INPLACE.update(json.load(open(os.path.join(W,'translation','extra_inplace.json'),encoding='utf-8')))
    fm=font_mods(f,E,cmap,tr)
    for top,subs in images.build(f,E).items():
        if top in fm: fm[top][1].update(subs)
        else: fm[top]=(None,subs)
    extra.update(images.build_cards(f,E))
    mods,st=inject.build_mods(tr,cmap,extra,font_subs=fm)
    json.dump(inject.TOO_LONG,open(os.path.join(W,'tmp','too_long.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1); print('제자리 교체 불가(길이 초과)',len(inject.TOO_LONG))
    print('translations',len(tr),'stats',st,'mods',len(mods),'%.0fs'%(time.time()-t))
    total=isobuild.build(out,mods); print('iso sectors',total)
    mv=os.path.join(W,'tmp','mv','MOVIE002_ko.pss')
    if os.path.exists(mv):
        d=open(mv,'rb').read()[:167575556]
        with open(out,'r+b') as g: g.seek(1568954*2048); g.write(d)
        print('MOVIE002 자막 적용')
