"""테스트 전용: 작업 폴더의 포터블 PCSX2를 최소화·비활성 창으로 실행(사용자 PC 조작 방해 없음). PINE으로 RAM 읽기/상태 저장."""
import subprocess,sys,os,time,glob,zipfile,struct,ctypes,socket
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMU=os.path.join(R,'emu'); PIDF=os.path.join(EMU,'emu.pid'); PORT=28241
def elf_crc(iso):
    with open(iso,'rb') as f: f.seek(397*2048); d=f.read(2261168)
    c=0
    for (x,) in struct.iter_unpack('<I',d[:len(d)//4*4]): c^=x
    return c
def launch(iso,state=None,cheat=''):
    crc=elf_crc(iso)
    os.makedirs(os.path.join(EMU,'cheats'),exist_ok=True)
    open(os.path.join(EMU,'cheats','%08X.pnach'%crc),'w').write(cheat)
    si=subprocess.STARTUPINFO(); si.dwFlags=1; si.wShowWindow=7
    args=[os.path.join(EMU,'pcsx2-qt.exe'),'-batch','-nogui']
    if state: args+=['-statefile',state]
    p=subprocess.Popen(args+['--',os.path.abspath(iso)],cwd=EMU,startupinfo=si)
    open(PIDF,'w').write(str(p.pid)); print('pid',p.pid,'crc %08X'%crc)
    hide(p.pid)
def hide(pid):
    u=ctypes.windll.user32
    for _ in range(150):
        hs=[]
        @ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
        def cb(h,l):
            pp=ctypes.c_ulong(); u.GetWindowThreadProcessId(ctypes.c_void_p(h),ctypes.byref(pp))
            if pp.value==pid and u.IsWindowVisible(ctypes.c_void_p(h)): hs.append(h)
            return True
        u.EnumWindows(cb,0)
        if hs:
            time.sleep(1.0)
            for h in hs: u.ShowWindow(ctypes.c_void_p(h),7)
            return
        time.sleep(0.2)
def stop():
    if os.path.exists(PIDF):
        subprocess.run(['taskkill','/F','/PID',open(PIDF).read().strip()],capture_output=True); os.remove(PIDF)
def pine(payload):
    s=socket.create_connection(('127.0.0.1',PORT),timeout=20)
    s.sendall(struct.pack('<I',len(payload)+4)+payload)
    def rv(n):
        b=b''
        while len(b)<n:
            c=s.recv(n-len(b))
            if not c: raise EOFError
            b+=c
        return b
    n=struct.unpack('<I',rv(4))[0]; body=rv(n-4); s.close(); return body
def w32(a,v): return pine(struct.pack('<BII',6,a,v))
def r32(a): return struct.unpack_from('<I',pine(struct.pack('<BI',2,a)),1)[0]
def member(p,name):
    import zstandard
    with zipfile.ZipFile(p) as z: i=z.getinfo(name)
    with open(p,'rb') as f:
        f.seek(i.header_offset); h=f.read(30); n,e=struct.unpack_from('<HH',h,26); f.seek(n+e,1); raw=f.read(i.compress_size)
    if i.compress_type==0: return raw
    if i.compress_type==93: return zstandard.ZstdDecompressor().decompress(raw,max_output_size=i.file_size)
    with zipfile.ZipFile(p) as z: return z.read(name)
def latest():
    ps=glob.glob(os.path.join(EMU,'sstates','*.p2s'))
    return max(ps,key=os.path.getmtime) if ps else None
def snap(tag,slot=9,ram=False):
    old=latest(); t=os.path.getmtime(old) if old else 0
    pine(struct.pack('<BB',9,slot))
    for _ in range(300):
        p=latest()
        if p and os.path.getmtime(p)>t: time.sleep(1.0); break
        time.sleep(0.1)
    out=os.path.join(R,'tmp','shot_%s.png'%tag)
    open(out,'wb').write(member(p,'Screenshot.png'))
    if ram: open(os.path.join(R,'tmp','ram_%s.bin'%tag),'wb').write(member(p,'eeMemory.bin'))
    return out
if __name__=='__main__':
    c=sys.argv[1]
    if c=='launch':
        import vpad
        launch(sys.argv[2],sys.argv[3] if len(sys.argv)>3 and not sys.argv[3].startswith('-') else None,cheat=vpad.section())
    elif c=='stop': stop()
    elif c=='snap': print(snap(sys.argv[2],ram='--ram' in sys.argv))
