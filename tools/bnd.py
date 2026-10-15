import struct,sys
ISO=r"D:\ps2\ACE_어나더센츄리즈에피소드2_스페셜보컬버전\Another Century's Episode 2 - Special Vocal Version (Japan).iso"
DATA_LBA=1848; DATA_SIZE=1315378208
def entries(f=None):
    f=f or open(ISO,'rb'); f.seek(DATA_LBA*2048); h=f.read(0x24)
    n=struct.unpack_from('<I',h,0x10)[0]
    t=f.read(n*12); return [struct.unpack_from('<3I',t,i*12) for i in range(n)]
def read(f,off,size):
    f.seek(DATA_LBA*2048+off); return f.read(size)
def sub_entries(d):
    if len(d)<0x10: return []
    """nested BND: 'BND\0', u32 total, u32 count, u32 0, (id,off)*count"""
    tot,n=struct.unpack_from('<2I',d,4)
    es=[struct.unpack_from('<2I',d,0x10+8*k) for k in range(n)]
    out=[]
    for k,(i,o) in enumerate(es):
        end=es[k+1][1] if k+1<n else tot
        out.append((i,o,end-o))
    return out
