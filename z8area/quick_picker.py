"""Install both quick area pickers and their native selection-limit page."""
import struct

from .thumbnail import branch
from . import grid

AT = 0x40B91800
ROWS, EVENTS, TOGGLE = 0x40B91400, 0x40B91540, 0x40B91580
ITEMS = (0x2C43, 0x3274, 0x32A7)
PHOTO_ROWS = 0x4BC2C10 + 0x50*1068
LIMIT = 0x4BC2C10 + 0x50*81
B = 0x40160000


def offset(va):
    return va-0xA02808000+0x4B13000 if va>=0xA02808000 else va-B


def word(w):
    return struct.pack('<I',w)


def edits(image, raw, symbols):
    def get(addr,n):
        start = offset(addr)
        return bytes(image[start:start+n])
    def q(addr):
        return struct.unpack('<Q',get(addr,8))[0]
    def ptrs(values):
        return struct.pack('<'+'Q'*len(values),*values)
    def empty(addr,data):
        return addr, bytes(len(data)), bytes(data)

    # Read labels and virtual icons from this owner's composed 7-row main
    # menu. Both allocations differ between standalone and the combination.
    main = struct.unpack_from('<Q',image,PHOTO_ROWS+16)[0]
    assert struct.unpack_from('<H',image,PHOTO_ROWS+32)[0]==7
    code = bytearray(raw)
    records = symbols['quick_records']-AT
    assert code[records:records+112] == bytes(112)
    options = [(0,0,0x84D),(1,0x1726,0x84C),(2,-1,0x84A),(8,0x1728,0x849),
               (4,0x1729,0x84B),(3,-2,None),(6,-3,None)]
    # Wide live-view icons (36x32) are two IDs above the 36x36 menu pair.
    labels = []
    icons = []
    for i,(value,setting,icon) in enumerate(options):
        row = struct.unpack('<11I',get(main+44*i,44))
        labels.append(row[0])
        icons.append(row[5]+2 if icon is None else icon)
        struct.pack_into('<IiII',code,records+16*i,value,setting,icons[-1],row[0])
    yield empty(AT,code)
    for va,expected,name in ((0x404E9EB0,'ff4301d1','quick_primary'),
                             (0x40443630,'098a9fd2','live_picker'),
                             (0x4043FFA8,'956295d2','live_disabled'),
                             (0x4049AAD4,'d5e48252','quick_alternate'),
                             (0x4049D374,'13000014','alternate_length')):
        yield va,bytes.fromhex(expected),branch(va,symbols[name])

    # Two separate lists. Relocate every live materialization, including
    # the cached label callbacks after entry, without disturbing interleaved instructions.
    # Store only the six selection bits in the original per-context list RAM.
    # A byte value always resolves to an immutable row, even before first use.
    p,a,live = 0xA028421A0,0xA028409A0,0xA032E53D8
    variants, trampolines = 0x40B95000,0x40B92000
    palette = bytearray()
    for mask in range(64):
        indices = [0] + [i for i in range(1,7) if mask & (1 << (i-1))]
        row = bytearray(128)
        row[:56] = b'\xff' * 56
        for index,i in enumerate(indices):
            struct.pack_into('<II',row,index*8,options[i][0],index)
            struct.pack_into('<H',row,56+2*index,icons[i])
            struct.pack_into('<I',row,72+4*index,labels[i])
        palette.extend(row)
    yield empty(variants,palette)
    glue = bytearray()
    for old,new,reg,sites in (
        (0xA032E53C8,live+72,8,(0x4043fee8,0x4043feec,0x4043fef0,0x4043fef4)),
        (0xA032E53D8,live,20,(0x4043ff70,0x4043ff74,0x4043ff78,0x4043ff7c)),
        (0xA032E53D8,live,21,(0x40446dd0,0x40446dd4,0x40446dd8,0x40446ddc)),
        (0xA028B5868,p+56,12,(0x4045134c,0x40451350,0x40451360,0x40451370)),
        (0xA028B5870,p+72,0,(0x404513f4,0x404513f8,0x404513fc,0x40451400)),
        (0xA028B5868,p+56,12,(0x4048cd30,0x4048cd34,0x4048cd44,0x4048cd54)),
        (0xA028B5870,p+72,20,(0x4048cde0,0x4048cde4,0x4048cde8,0x4048cdec)),
        (0xA028421A0,p,20,(0x404ea4a0,0x404ea4a4,0x404ea4ac,0x404ea4b0)),
        (0xA028421A0,p,27,(0x404ea5f0,0x404ea5f4,0x404ea5f8,0x404ea600)),
        (0xA028421A0,p,8,(0x404ea654,0x404ea658,0x404ea65c,0x404ea660)),
        (0xA028421A0,p,20,(0x404ea6e0,0x404ea6e4,0x404ea6e8,0x404ea6f0)),
        (0xA028B5868,a+56,12,(0x4049ac98,0x4049aca8,0x4049acac,0x4049acb0)),
        (0xA028B5870,a+72,8,(0x4049c9cc,0x4049c9d0,0x4049c9d4,0x4049c9d8)),
        (0xA028B5870,a+72,8,(0x4049efc0,0x4049efc4,0x4049efc8,0x4049efcc)),
        (0xA028409A0,a,9,(0x4049ca64,0x4049ca68,0x4049ca6c,0x4049ca74)),
        (0xA028409A0,a,19,(0x4049d360,0x4049d368,0x4049d36c,0x4049d370))):
        selector = next(start for start in (p,a,live) if new-start in (0,56,72))
        member = new-selector
        for i,site in enumerate(sites):
            op=(0xF2800000 if i else 0xD2800000) | (i<<21) | reg
            before=word(op | ((old>>(16*i))&65535)<<5)
            after=word(op | ((selector>>(16*i))&65535)<<5)
            if i==3:
                # Only the destination register is dead here. Preserve flags and
                # the scratch register across interleaved native instructions.
                entry=trampolines+len(glue)
                after=branch(site,entry)
                tmp=10 if reg==9 else 9
                delta=variants-(entry+12)
                instructions=(
                    0xf81f0fe0|tmp,                         # str Xt,[sp,#-16]!
                    0x39400000|(reg<<5)|reg,                # ldrb Wd,[Xd]
                    0x12001400|(reg<<5)|reg,                # and Wd,Wd,#63
                    0x10000000|((delta&3)<<29)|(((delta>>2)&0x7ffff)<<5)|tmp,
                    0x8b001c00|(reg<<16)|(tmp<<5)|reg,      # add Xd,Xt,Xd,lsl #7
                    0x91000000|(member<<10)|(reg<<5)|reg,
                    0xf84107e0|tmp,                         # ldr Xt,[sp],#16
                )
                glue.extend(b''.join(map(word,instructions)))
                glue.extend(branch(entry+28,site+4))
            if get(site,4)!=before: raise ValueError(f'Unexpected pointer at {site:#x}')
            if before!=after: yield site,before,after
    assert trampolines+len(glue)<=0x40B92800
    yield empty(trampolines,glue)
    for site in (0x4043ff88,0x404437b4,0x40446de4,0x40446dfc):
        yield site,word(0x321e03e1),word(0x528000e1)
    yield 0x40440008,word(0x7100229f)+word(0x54000060),word(0x7100069f)+word(0x54000068)
    yield 0x4049ACCC,bytes.fromhex('08020054'),branch(0x4049ACCC,0x4049AD0C)
    yield 0x404EA6F8,bytes.fromhex('e1031e32'),word(0x528000E1)   # search 7 initialized pairs
    # All five non-FX/DX values use the native restricted path.
    yield 0x404EA738,bytes.fromhex('3f2100712419447a81010054'),word(0x7100053f)+word(0xd503201f)+word(0x54000189)
    yield 0x4049CA80,bytes.fromhex('1f21007160feff54'),word(0x7100051f)+word(0x54fffe68)

    old_rows,old_events=struct.unpack_from('<QQ',image,LIMIT+16)
    assert struct.unpack_from('<H',image,LIMIT+32)[0]==4
    old=[get(old_rows+44*i,44) for i in range(4)]
    assert [struct.unpack_from('<I',r,24)[0] for r in old]==[0x33aa,0x33a7,0x33a8,0x33a9]
    custom=[]
    for i,label in zip(ITEMS,(labels[2],labels[5],labels[6])):
        row=bytearray(old[3])
        struct.pack_into('<I',row,0,label)
        struct.pack_into('<I',row,24,i)
        custom.append(row)
    pointers=[q(old_events+8*i) for i in range(4)]
    table=bytearray()
    for i in range(32):
        rec=bytearray(get(pointers[-1]+32*i,32))
        if struct.unpack_from('<Q',rec,8)[0]==0x4052AEE0:
            struct.pack_into('<Q',rec,8,symbols['limit_toggle'])
        table.extend(rec)
        if struct.unpack_from('<Q',rec)[0]==0x3bb:break
    else: raise ValueError('Missing native end event')
    assert TOGGLE+len(table)<=AT
    yield empty(ROWS,b''.join((old[0],old[1],custom[0],old[2],old[3],custom[1],custom[2])))
    yield empty(EVENTS,ptrs((pointers[0],pointers[1],TOGGLE,pointers[2],pointers[3],TOGGLE,TOGGLE)))
    yield empty(TOGGLE,table)
    record=0xA02808000+LIMIT-0x4B13000
    yield record+16,ptrs((old_rows,old_events))+b'\x04\0',ptrs((ROWS,EVENTS))+b'\x07\0'
    yield 0xA028EA7E8+32,ptrs([0x405216CC]),ptrs([symbols['limit_refresh']])
    yield 0x4052B018,bytes.fromhex('28758652'),word(0x52800008|(ITEMS[-1]<<5))
    # Native UP handling special-cases the row immediately after DX.
    yield 0x4052B040,word(0x52800008|(0x33A8<<5)),word(0x52800008|(ITEMS[0]<<5))
    # Camera-control Fn2 wheel transaction, separate from all display callbacks.
    yield 0x40d497e0,branch(0x40d497e0,0x40d46084,True),branch(0x40d497e0,symbols['physical_dial'])
    yield from grid.edits(image, labels, icons, symbols)
