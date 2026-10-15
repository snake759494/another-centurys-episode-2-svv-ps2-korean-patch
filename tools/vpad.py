"""테스트 전용 가상 패드(배포 안 함): 0x1D7FB0(sh v0,258(s0) = 눌림 마스크 저장) 앞에서 VPAD 값을 OR.
마스크(LE): SELECT=1 START=8 U=0x10 R=0x20 D=0x40 L=0x80 L2=0x100 R2=0x200 L1=0x400 R1=0x800 T=0x1000 O=0x2000 X=0x4000 S=0x8000"""
import sys,os,time,struct;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import emu
VPAD=0x000ff000; CAVE=0x000ff100; HOOK=0x1d7fb0; RET=0x1d7fb8
BTN=dict(SELECT=1,START=8,U=0x10,R=0x20,D=0x40,L=0x80,L2=0x100,R2=0x200,L1=0x400,R1=0x800,T=0x1000,O=0x2000,X=0x4000,S=0x8000)
def j(a): return (2<<26)|(a>>2)
def section():
    code=[0x3c010000|((VPAD+0x8000)>>16), 0x8c210000|(VPAD&0xffff), 0x00411025,  # lui at; lw at; or v0,v0,at
          0xa6020102, j(RET), 0]                                                    # sh v0,258(s0); j RET
    out=['gametitle=ACE2 (dev vpad)']
    out+=['patch=1,EE,%08x,word,%08x'%(CAVE+4*i,c) for i,c in enumerate(code)]
    out+=['patch=1,EE,%08x,word,%08x'%(HOOK,j(CAVE)),'patch=1,EE,%08x,word,00000000'%(HOOK+4)]
    return '\n'.join(out)+'\n'
def press(names,ms=150):
    m=0
    for n in names.split('+'): m|=BTN[n]
    emu.w32(VPAD,m); time.sleep(ms/1000); emu.w32(VPAD,0); time.sleep(0.25)
def seq(*keys):
    for k in keys:
        try: time.sleep(float(k))
        except ValueError: press(k)
if __name__=='__main__':
    c=sys.argv[1]
    if c=='press': seq(*sys.argv[2:])
    elif c=='hold': press(sys.argv[2],int(sys.argv[3]))
