import struct
E=open(r'D:\ps2\ACE_어나더센츄리즈에피소드2_스페셜보컬버전\work\orig\SLPS_258.29','rb').read()
OFF=0x80;VA=0x100000;FS=0x227e80
def w(va): return struct.unpack_from('<I',E,OFF+va-VA)[0]
R=['zero','at','v0','v1','a0','a1','a2','a3','t0','t1','t2','t3','t4','t5','t6','t7','s0','s1','s2','s3','s4','s5','s6','s7','t8','t9','k0','k1','gp','sp','fp','ra']
def dis(x,va=0):
    op=x>>26;rs=(x>>21)&31;rt=(x>>16)&31;rd=(x>>11)&31;sa=(x>>6)&31;fn=x&63;imm=x&0xffff;simm=imm-0x10000 if imm&0x8000 else imm
    if x==0: return 'nop'
    if op==0:
        names={0x21:'addu',0x23:'subu',0x24:'and',0x25:'or',0x26:'xor',0x27:'nor',0x2a:'slt',0x2b:'sltu',0x2d:'daddu',0x0:'sll',0x2:'srl',0x3:'sra',0x8:'jr',0x9:'jalr',0x4:'sllv',0x6:'srlv'}
        n=names.get(fn,'sp%02x'%fn)
        if fn in (0,2,3): return f'{n} {R[rd]},{R[rt]},{sa}'
        if fn==8: return f'jr {R[rs]}'
        return f'{n} {R[rd]},{R[rs]},{R[rt]}'
    ops={0x09:'addiu',0x0c:'andi',0x0d:'ori',0x0e:'xori',0x0f:'lui',0x20:'lb',0x21:'lh',0x23:'lw',0x24:'lbu',0x25:'lhu',0x28:'sb',0x29:'sh',0x2b:'sw',0x37:'ld',0x3f:'sd',0x1e:'lq',0x1f:'sq',0x0a:'slti',0x0b:'sltiu'}
    if op in (2,3): return ('j ' if op==2 else 'jal ')+hex((x&0x3ffffff)<<2)
    if op in (4,5,6,7,1): return f'b{op} {R[rs]},{R[rt]},{hex(va+4+simm*4)}'
    n=ops.get(op,'op%02x'%op)
    if op==0x0f: return f'lui {R[rt]},{hex(imm)}'
    if op in (0x09,0x0c,0x0d,0x0e,0x0a,0x0b): return f'{n} {R[rt]},{R[rs]},{hex(imm) if op in (0xc,0xd,0xe) else simm}'
    return f'{n} {R[rt]},{simm}({R[rs]})'
def show(a,n=20):
    for k in range(n): print(hex(a+4*k),dis(w(a+4*k),a+4*k))
