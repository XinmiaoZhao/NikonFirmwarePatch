"""Native i menu photo tile 01/50: seven choice editor, grid, cursor and inhibit rules."""
import struct
from .thumbnail import branch

START = 0x40B92800
LIMIT = 0x40B95000
B = 0x40160000


def edits(img, labels, icons, symbols):
    def off(a):return a-0xa02808000+0x4b13000 if a>=0xa02808000 else a-B
    def read(a,n):return bytes(img[off(a):off(a)+n])
    def q(a):return struct.unpack('<Q',read(a,8))[0]
    def qs(*v):return struct.pack('<'+'Q'*len(v),*v)
    def words(*v):return struct.pack('<'+'I'*len(v),*v)
    arena=bytearray()
    def store(data):
        addr=START+len(arena)
        arena.extend(data)
        arena.extend(bytes(-len(arena)%8))
        if START+len(arena)>LIMIT:raise ValueError('i menu storage exhausted')
        return addr
    def relocate(pc,hi,reg,old,new):
        for i,at in enumerate((pc,hi)):
            op=(0xf2a00000 if i else 0xd2800000)|reg
            yield at,words(op|(old>>(16*i)&65535)<<5),words(op|(new>>(16*i)&65535)<<5)
    values=(0,1,2,8,4,3,6)
    options=store(b''.join(words(v,i) for i,v in enumerate(values)))
    icon_cfg=store(b''.join(words(i,1,id_,0,0,0) for i,id_ in enumerate(icons)))
    text_cfg=store(b''.join(words(i,2,id_,0,0,0) for i,id_ in enumerate(labels)))
    active=store(b''.join(words(v,i) for i,v in enumerate((0,1,2,3,4,5,7))))
    cond=store(words(0x1e9,0x1e9,0x1a,0x1a,0x1b,0x1a,0x1a))
    yield 0x43a20150,qs(0x43a191c0,4),qs(options,7)
    yield 0x43a1d418,qs(0x404ea570),qs(symbols['grid_dial'])
    yield from relocate(0x404eabec,0x404eabf0,0,0x42b01ac8,active)
    yield 0x404eabfc,words(0x321e03e1),words(0x528000e1)
    yield from relocate(0x404cfa14,0x404cfa1c,27,0x43a1c238,cond)
    yield 0x404cfaa4,branch(0x404cfaa4,0x403a036c,True),branch(0x404cfaa4,symbols['grid_restrict'],True)
    # Select the factory seven-cell states rather than resizing shared four-cell states.
    for at,key,old,new in ((0x42b01ef8,0x50,0x5dc,0x5df),(0x42b022a8,0x50,0x623,0x626),
                           (0x42b02658,1,0x5dc,0x5df)):
        yield at,words(key,old),words(key,new)
    for at in (0x43a18350,0x43a18890):
        yield at,qs(0xa028707f8,4),qs(icon_cfg,7)
    for at in (0xa02876018,0xa02898c40):
        yield at,qs(0xa02876058,4),qs(text_cfg,7)
    # Item 12/61 also uses the standard seven-option, one-icon-per-cell page.
    # Reuse its widget IDs, coordinates and hit regions on all three display
    # templates. Only the image-area item points to the private selector copies.
    copies={}
    for dest,donor in ((0xa0284f748,0xa02851538),(0xa02855808,0xa02857508),(0xa02863078,0xa02864d78)):
        for i in range(7):
            entry=donor+16*(3+i)
            rec=q(entry)
            assert q(entry+8)==1
            if rec not in copies:
                original=bytearray(read(rec,40))
                widget=q(rec+8)
                obj=bytearray(read(widget,56))
                assert q(widget)==(0x49af if dest==0xa02863078 else 0x48ba)+i
                assert q(widget+16)==7
                struct.pack_into('<Q',obj,8,icon_cfg)
                struct.pack_into('<Q',original,8,store(obj))
                copies[rec]=store(original)
            site=dest+16*(3+i)
            before=read(site,16)
            assert (q(site+8)==1 if i<4 else before==bytes(16))
            yield site,before,qs(copies[rec],1)
    yield START,bytes(len(arena)),bytes(arena)
