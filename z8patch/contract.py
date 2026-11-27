"""Independent structural checks, using fixed firmware facts and group semantics.

No composer, assembler, linker or resource-generator imports.
"""
import struct
STRING_TABLES = 0x40A7C000   # shared language offset tables (E2: moved up from 0x40A70000)


def verify_contract(old,new,features):
    def need(ok,message):
        if not ok:raise ValueError('Composition contract: '+message)
    base=0x40160000
    read=lambda image,fmt,at:struct.unpack_from(fmt,image,at)
    framing = quality = 'video-recording' in features
    log, photo, raw = (s in features for s in ('log-colour','still-photo-tools','raw-precapture'))
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
            (3153,3161,framing),(3161,3217,quality),(3217,3225,log),(3225,3234,framing),(3234,3238,photo),(3238,3250,photo)]
    entries=3251 if photo else (3235 if framing else 3226)             # the open-gate E1/E2 strings extend the table only with framing
    for language in range(36):
        table=read(new,'<Q',0x311C5A0+8*language)[0]
        original_table=read(old,'<Q',0x311C5A0+8*language)[0]
        if not (photo or video):
            need(table==original_table,'RAW-only keeps factory language directory')
            continue
        need(table==STRING_TABLES+language*entries*4,'language table position')
        offsets=read(new,f'<{entries}i',table-base)
        need(offsets[:3137]==read(old,'<3137i',original_table-base),'native string offsets')
        blob=read(new,'<Q',0x387AF58+8*language)[0]
        for lo,hi,enabled in ranges:
            if hi>entries-1:continue
            for ident in range(lo,hi):
                a,b=blob+offsets[ident],blob+offsets[ident+1]
                need(0x40A50000<=a<=b<=STRING_TABLES,'added string bounds')
                need(bool(b-a)==enabled,'selected string presence')
                new[a-base:b-base].decode('utf-16le')
    loader=read(new,'<II',0x1024D8C)
    end=((loader[0]>>5)&65535)|(((loader[1]>>5)&65535)<<16)
    if video or photo:
        need(0x40AE2000<=end<=0x40C00000 and end%4096==0,'copy boundary covers resources')
    else:
        # The RAW-only pre-capture cave includes the RSF release-mode block at 0x409FF200..0x409FF800.
        need(end==0x40A00000,'RAW-only loader')
    need((new[0xE0FE90:0xE0FE94]!=old[0xE0FE90:0xE0FE94])==raw,'pre-capture hook ownership')
    for va in (0x40ED4768,0x40ED4918,0x405131A4,0x40515FD8,0x405178F4,0x440F71EC):
        at = va-base
        need((new[at:at+4]!=old[at:at+4])==raw,'RSF pre-capture hook ownership')
    for pos in (0x4B13000+0xA028BC620-0xA02808000,0x4B13000+0xA028CC390-0xA02808000):
        need(read(new,'<H',pos+32)[0]==(7 if raw else 3),'RSF release-mode subpage row count')
    if raw:
        # Item IDs index the global grey-state bytes 0xA032CAC8[id-0x2921]: they must not be shared, in
        # particular not with the HEIF item 0x2DE1 / JPEG 0x2DDE (still-photo-tools) or ProRes HQ 0x315A.
        rsf_ids=[]
        for pos in (0x4B13000+0xA028BC620-0xA02808000,0x4B13000+0xA028CC390-0xA02808000):
            rows=read(new,'<Q',pos+16)[0]
            rsf_ids+=[read(new,'<I',rows-base+44*i+24)[0] for i in range(7)]
        need(len(set(rsf_ids))==14 and not set(rsf_ids)&{0x2DDE,0x2DE1,0x315A},'RSF release-mode item IDs')
    for va in (0x40EC8D24,0x40EC8D28,0x406C2304,0x410B7C64):
        at = va-base
        need((new[at:at+4]!=old[at:at+4])==photo,'photo capture hook ownership')
    for state, present in ((0xAB,photo),(0x17D,quality)):
        pos = 0x4BFFCC0+96*state
        for delta in (40,80):
            need((new[pos+delta:pos+delta+8]!=old[pos+delta:pos+delta+8])==present,'submenu ownership')
    if photo:
        need(end>=0x40BA0000,'crop data and zero-state loader floor')
        need(read(new,'<Q',0x4DA1288)[0]==0x40B91040,'fixed C-low geometry pointer')
        need(read(new,'<H',0x40B91040-base+10)[0]==576,'fixed crop height')
        groups = read(new,'<II',0x40B80000-base+44*2)
        need(groups[0]==3238 and read(new,'<I',0x40B80000-base+44*5)[0]==3239,'crop label references')
        for row,icon in ((5,0x7110),(6,0x7111)):
            need(read(new,'<I',0x40B80000-base+44*row+20)[0]==icon,'still menu icon')
        need(read(new,'<H',0x40B84000-base+0x140)[0]==0x100,'still icon descriptors')
        need(read(new,'<H',0x4BD79D0+32)[0]==7,'crop menu row count')
        need(new[0x409ED000-base:0x409F0000-base]==bytes(0x3000),'pixel shift initial worker state')
    if log:need(end>=0x40B50000 and not any(new[0x40B0E000-base:0x40B0F100-base]),'Log private state initialized')
    if quality:need(new[0x40A40000-base]==0,'star force initially clear')
    if framing:need(not any(new[0x4097F000-base:0x40980000-base]),'AP state initialized')
    if framing:
        need(not any(new[0x4096F000-base:0x40970000-base]),'open-gate private state initialized')
        need(read(new,'<H',0x4B13000+0xA028C1690-0xA02808000)[0]==11,'video file type page: 11 rows')
    # v0.5.1, video recording only: the local movie output slot holds one 1280x848 NV12 frame, and both 4.1K 3:2
    # AF geometry calls enter the fix unit in the open-gate code tail. Without the group both stay stock.
    lo,hi=read(new,'<I',0x40CF4620-base)[0],read(new,'<I',0x40CF4630-base)[0]
    need(lo&0xFFE0001F==0x5280000D and hi&0xFFE0001F==0x72A0000D,'movie output slot instruction shape')
    need(((lo>>5)&65535)|(((hi>>5)&65535)<<16)==(0x18D800 if framing else 0x151800),'movie output slot size')
    for site in (0x41055AC0,0x410567DC):
        word=read(new,'<I',site-base)[0]
        target=site+(((word&0x3FFFFFF)^0x2000000)-0x2000000)*4
        need((word>>26==0x25 and target==0x40968000) if framing else new[site-base:site-base+4]==old[site-base:site-base+4],
             '4.1K 3:2 AF geometry entry')
    return dict(status='PASS',video_menu=video,language_tables=36 if photo or video else 0,offsets_per_language=entries if photo or video else 3137,
                exact_group_visibility=True,zero_state=True,loader_end=hex(end))
