import sys,os,struct,hashlib;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import bnd,tex
from PIL import Image,ImageDraw
f=open(bnd.ISO,'rb'); os.makedirs('tmp/tex2',exist_ok=True); seen=set(); out=[]
for p in os.listdir('tmp/tex'): seen.add(hashlib.md5(Image.open('tmp/tex/'+p).tobytes()).hexdigest())
def emit(x,tag):
    try: r=tex.decode(x)
    except Exception: return
    if r is None: return
    im=Image.fromarray(r[0],'RGBA'); bg=Image.new('RGBA',im.size,(40,40,90,255)); bg.alpha_composite(im); bg=bg.convert('RGB')
    hh=hashlib.md5(bg.tobytes()).hexdigest()
    if hh in seen: return
    seen.add(hh); p=f'tmp/tex2/{tag}.png'; bg.save(p); out.append(p)
def tpk(d,tag):
    if len(d)<0x20: return
    tot,n=struct.unpack_from('<2I',d,0)
    if not(tot==len(d) and 0<n<2000 and 0x10+16*n<=len(d)): return
    for k in range(n):
        o=struct.unpack_from('<I',d,0x10+16*k)[0]
        if not(0<o<=len(d)-0x20): return
        x=d[o:o+struct.unpack_from('<I',d,o)[0]]
        if tex.is_tex(x): emit(x,f'{tag}_{k}')
def walk(d,tag,dep=0):
    if d[:4]==b'BND\0':
        if dep>4: return
        for ii,oo,ss in bnd.sub_entries(d):
            if oo<0x10 or ss<=0 or oo+ss>len(d) or ss>=len(d): continue
            walk(d[oo:oo+ss],f'{tag}_{ii}',dep+1)
    elif tex.is_tex(d): emit(d,tag)
    else: tpk(d,tag)
for i,o,s in bnd.entries(f):
    if 2000<=i<5000 or 6000<=i<7000 or 42000<=i<43000 or 40000<=i<42000: continue
    if i in range(62050,62058) or i in range(38000,38007): continue
    d=bnd.read(f,o,s)
    if d[:4] in (b'VMD\0',b'MIC\0',b'PRM\0'): continue
    walk(d,str(i))
print(len(out))
cells=[]
for p in out:
    im=Image.open(p); im.thumbnail((300,150)); cells.append((os.path.basename(p)[:-4],im))
os.makedirs('tmp/sheet2',exist_ok=True)
for s in range(0,len(cells),24):
    sh=Image.new('RGB',(4*310,6*170)); d=ImageDraw.Draw(sh)
    for j,(n,im) in enumerate(cells[s:s+24]):
        x=(j%4)*310;y=(j//4)*170; sh.paste(im,(x,y)); d.text((x,y+152),n,fill=(255,255,0))
    sh.save(f'tmp/sheet2/{s//24:02d}.png')
print((len(cells)+23)//24)
