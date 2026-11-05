"""Independent structural checks, using fixed firmware facts and group semantics.

No composer, assembler, linker or resource-generator imports.
"""
import struct


def verify_contract(old,new,features):
    def need(ok,message):
        if not ok:raise ValueError('Composition contract: '+message)
    base=0x40160000
    read=lambda image,fmt,at:struct.unpack_from(fmt,image,at)
    framing,quality,log,photo=(s in features for s in ('framing','video-quality','log-colour','photo-tools'))
    video=framing or quality or log
    if video:
        rows,events,count=read(new,'<QQH',0x4BCC2C0)
        need((rows,events,count)==(0x40A30000,0x40A31000,45 if quality else 44),'video menu allocation/count')
        ids=[read(new,'<I',rows-base+44*i+24)[0] for i in range(count)]
        original=[read(old,'<I',0x3AA4758+44*i+24)[0] for i in range(44)]
        need(len(ids)==len(set(ids)) and set(ids)==set(original)|({0x315A} if quality else set()),'video menu items')
        if log:need(ids.index(0x2E38)==ids.index(0x2FC1)+1,'Log after file type')
        if quality:need(ids.index(0x311B)==ids.index(0x3118)+1 and ids.index(0x315A)==ids.index(0x311B)+1,'quality rows order')
        for enabled,site,item,load in ((log,0x40572940,0x2E38,0x40572930),(quality,0x4057295C,0x311B,0x4057294C),(framing,0x40572978,0x310F,0x40572968)):
            need(new[load-base:load-base+4]==old[load-base:load-base+4],f'original hidden-item identity {item:#x}')
            need(new[site-base:site-base+4]==(bytes.fromhex('02008052') if enabled else old[site-base:site-base+4]),f'visibility {item:#x}')
        mask=read(new,'<I',0x40980F00-base)[0]
        need(mask==int(framing)+2*int(quality)+4*int(log),'shared feature mask')
        ptrs=read(new,'<4Q',0x40980F08-base)
        need([bool(p) for p in ptrs]==[quality,quality,framing,log],'shared callback presence')
        need(0x40980000<=read(new,'<Q',0x4BF3A80)[0]<0x40980F00,'shared refresh entry')
    else:
        need(new[0x4BCC2B0:0x4BCC300]==old[0x4BCC2B0:0x4BCC300],'photo-only video page preservation')
        need(new[0xEB62EC:0xEB62F0]==old[0xEB62EC:0xEB62F0],'photo-only bank preservation')
    # 36 offset arrays: native text offsets are byte-for-byte retained, added IDs
    # are present exactly for their selected modules. String IDs stay fixed across masks.
    ranges=[(3137,3142,framing),(3142,3147,photo),(3147,3153,quality),
            (3153,3161,framing),(3161,3217,quality),(3217,3225,log)]
    for language in range(36):
        table=read(new,'<Q',0x311C5A0+8*language)[0]
        original_table=read(old,'<Q',0x311C5A0+8*language)[0]
        need(table==0x40A70000+language*3226*4,'language table position')
        offsets=read(new,'<3226i',table-base)
        need(offsets[:3137]==read(old,'<3137i',original_table-base),'native string offsets')
        blob=read(new,'<Q',0x387AF58+8*language)[0]
        for lo,hi,enabled in ranges:
            for ident in range(lo,hi):
                a,b=blob+offsets[ident],blob+offsets[ident+1]
                need(0x40A50000<=a<=b<=0x40A70000,'added string bounds')
                need(bool(b-a)==enabled,'selected string presence')
                new[a-base:b-base].decode('utf-16le')
    loader=read(new,'<II',0x1024D8C)
    end=((loader[0]>>5)&65535)|(((loader[1]>>5)&65535)<<16)
    need(0x40AE2000<=end<=0x40C00000 and end%4096==0,'copy boundary covers strings')
    if log:need(end>=0x40B50000 and not any(new[0x40B0E000-base:0x40B0F100-base]),'Log private state initialized')
    if quality:need(new[0x40A40000-base]==0,'star force initially clear')
    if framing:need(not any(new[0x4097F000-base:0x40980000-base]),'AP state initialized')
    return dict(status='PASS',video_menu=video,language_tables=36,offsets_per_language=3226,
                exact_group_visibility=True,zero_state=True,loader_end=hex(end))
