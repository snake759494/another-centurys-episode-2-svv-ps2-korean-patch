"""ISO 생성: 원본 복사 → 수정 항목을 ISO 끝에 추가 → DATA.BIN BND 표/크기, ISO9660 레코드, PVD, UDF FE 갱신"""
import sys,os,struct,shutil;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import bnd,udf
DATA_REC=0x8290a   # 루트 디렉터리 내 DATA.BIN 레코드 위치
def crc_ccitt(b):
    c=0
    for x in b:
        c^=x<<8
        for _ in range(8): c=((c<<1)^0x1021)&0xffff if c&0x8000 else (c<<1)&0xffff
    return c
def fix_tag(buf):
    ln=struct.unpack_from('<H',buf,10)[0]
    struct.pack_into('<H',buf,8,crc_ccitt(buf[16:16+ln]))
    s=sum(buf[0:4])+sum(buf[5:16]); buf[4]=s&0xff
def build(out,mods):
    src=bnd.ISO
    if os.path.exists(out): os.remove(out)
    shutil.copyfile(src,out)
    f=open(out,'r+b')
    f.seek(0,2); end=f.tell(); assert end%2048==0
    base=bnd.DATA_LBA*2048
    f.seek(base); hdr=bytearray(f.read(0x24)); n=struct.unpack_from('<I',hdr,0x10)[0]
    tbl=bytearray(f.read(n*12))
    pos=end
    for k in range(n):
        i,o,s=struct.unpack_from('<3I',tbl,12*k)
        if i in mods:
            d=mods[i]; f.seek(pos); f.write(d); f.write(b'\0'*((-len(d))%2048))
            struct.pack_into('<3I',tbl,12*k,i,pos-base,len(d)); pos+=(len(d)+2047)//2048*2048
    pos+=2048   # 마지막 섹터: UDF 앵커(AVDP) 사본
    newsize=pos-2048-base; assert newsize<2**32
    struct.pack_into('<I',hdr,0x0c,newsize)
    f.seek(base); f.write(hdr); f.write(tbl)
    total=pos//2048
    # ISO9660
    f.seek(DATA_REC); rec=bytearray(f.read(0x3a)); assert rec[33:33+10]==b'DATA.BIN;1'
    struct.pack_into('<I',rec,10,newsize); struct.pack_into('>I',rec,14,newsize)
    f.seek(DATA_REC); f.write(rec)
    f.seek(16*2048); pvd=bytearray(f.read(2048)); struct.pack_into('<I',pvd,80,total); struct.pack_into('>I',pvd,84,total)
    f.seek(16*2048); f.write(pvd)
    # UDF: 파티션 길이, DATA.BIN FE 크기
    a=udf._sec(f,256); mvds,=struct.unpack_from('<I',a,20)
    for seq in (mvds,struct.unpack_from('<I',a,28)[0]):
        for k in range(32):
            t=bytearray(udf._sec(f,seq+k)); tid=struct.unpack_from('<H',t,0)[0]
            if tid==5:
                ps=struct.unpack_from('<I',t,188)[0]; struct.pack_into('<I',t,192,total-ps); fix_tag(t); f.seek((seq+k)*2048); f.write(t)
            if tid==8 or tid==0: break
    lba=udf.find(f,'DATA.BIN'); fe=bytearray(udf._sec(f,lba))
    b_,lad,icb=udf.fe_ads(fe)
    struct.pack_into('<Q',fe,56,newsize); struct.pack_into('<Q',fe,64,(newsize+2047)//2048)
    struct.pack_into('<I',fe,b_,newsize)
    fix_tag(fe); f.seek(lba*2048); f.write(fe)
    # UDF 앵커를 마지막 섹터에 복사
    av=bytearray(udf._sec(f,256)); struct.pack_into('<I',av,12,total-1); fix_tag(av)
    f.seek((total-1)*2048); f.write(av)
    f.close()
    return total
