"""Independent structural checks, using fixed firmware facts and group semantics.

No composer, assembler, linker or resource-generator imports; the only
inputs are the two images, the feature list and (for the vrotate unit
bound) the frozen reviewed recipe resources/compiled.json.
"""
import json, struct
from pathlib import Path


def verify_contract(old,new,features):
    def need(ok,message):
        if not ok:raise ValueError('Composition contract: '+message)
    base=0x40160000
    read=lambda image,fmt,at:struct.unpack_from(fmt,image,at)
    framing,quality,log,photo,vr=(s in features for s in ('framing','video-quality','log-colour','photo-tools','video-orientation'))
    video=framing or quality or log or vr
    if video:
        rows,events,count=read(new,'<QQH',0x4BCC2C0)
        need((rows,events,count)==(0x40A30000,0x40A31000,44+int(quality)+int(vr)),'video menu allocation/count')
        ids=[read(new,'<I',rows-base+44*i+24)[0] for i in range(count)]
        original=[read(old,'<I',0x3AA4758+44*i+24)[0] for i in range(44)]
        need(len(ids)==len(set(ids)) and set(ids)==set(original)|({0x315A} if quality else set())|({0x315B} if vr else set()),'video menu items')
        if log:need(ids.index(0x2E38)==ids.index(0x2FC1)+1,'Log after file type')
        if quality:need(ids.index(0x311B)==ids.index(0x3118)+1 and ids.index(0x315A)==ids.index(0x311B)+1,'quality rows order')
        if vr:need(ids.index(0x315B)==ids.index(0x30A6)-1,'orientation row directly before the image-area row')
        for enabled,site,item,load in ((log,0x40572940,0x2E38,0x40572930),(quality,0x4057295C,0x311B,0x4057294C),(framing,0x40572978,0x310F,0x40572968)):
            need(new[load-base:load-base+4]==old[load-base:load-base+4],f'original hidden-item identity {item:#x}')
            need(new[site-base:site-base+4]==(bytes.fromhex('02008052') if enabled else old[site-base:site-base+4]),f'visibility {item:#x}')
        mask=read(new,'<I',0x40980F00-base)[0]
        need(mask==int(framing)+2*int(quality)+4*int(log)+8*int(vr),'shared feature mask')
        ptrs=read(new,'<5Q',0x40980F08-base)
        need([bool(p) for p in ptrs]==[quality,quality,framing,log,vr],'shared callback presence')
        # The unfrozen shared unit runs an unconditional five-slot callback
        # ring reading CONFIG+0x28 even in four-group builds, where that
        # slot keeps its stock bytes -- pin the stock firmware fact those
        # builds rely on (a nonzero stock byte would be blr'd as a callback).
        need(not any(old[0x40980F28-base:0x40980F30-base]),'fifth callback slot stock zero')
        need(0x40980000<=read(new,'<Q',0x4BF3A80)[0]<0x40980F00,'shared refresh entry')
    else:
        need(new[0x4BCC2B0:0x4BCC300]==old[0x4BCC2B0:0x4BCC300],'photo-only video page preservation')
        need(new[0xEB62EC:0xEB62F0]==old[0xEB62EC:0xEB62F0],'photo-only bank preservation')
    # 36 offset arrays: native text offsets are byte-for-byte retained, added IDs
    # are present exactly for their selected modules. String IDs stay fixed across masks.
    entries=3227 if vr else 3226
    ranges=[(3137,3142,framing),(3142,3147,photo),(3147,3153,quality),
            (3153,3161,framing),(3161,3217,quality),(3217,3225,log)]+([(3225,3226,vr)] if vr else [])
    for language in range(36):
        table=read(new,'<Q',0x311C5A0+8*language)[0]
        original_table=read(old,'<Q',0x311C5A0+8*language)[0]
        need(table==0x40A70000+language*entries*4,'language table position')
        offsets=read(new,f'<{entries}i',table-base)
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
    vrotate=None
    if vr:
        # Fixed facts of the vrotate unit (cave 0x40A08000-0x40A10000;
        # symbol offsets below are fixed facts of the reviewed recipe).
        # The unit length comes from the frozen compiled.json itself, so
        # the reservation-tail bound cannot drift from the shipped bytes.
        units=json.loads((Path(__file__).resolve().parents[1]/'resources/compiled.json').read_text())['units']
        cave=0x40A08000;unit_end=cave+units['vrotate']['bytes']
        need(not any(old[cave-base:0x40A10000-base]),'vrotate cave free in stock')
        # T2b: the row-events clone rides its own fixed sub-window
        # 0x40A09000-0x40A09580; the gap between the unit and that window and
        # the tail past it stay stock zero.
        need(not any(new[unit_end-base:0x40A09000-base]),'vrotate cave gap stays stock zero')
        need(not any(new[0x40A09580-base:0x40A10000-base]),'vrotate cave tail stays stock zero')
        def branch_target(site,word):
            need(word>>26 in (0x05,0x25),f'vrotate hook branch shape at {site:#x}')
            delta=word&0x3FFFFFF
            if delta&0x2000000:delta-=0x4000000
            return site+delta*4
        need(read(old,'<I',0x40cefd60-base)[0]==0x97FFD09F,'vrotate matrix site stock word')
        need(cave<=branch_target(0x40cefd60,read(new,'<I',0x40cefd60-base)[0])<unit_end,'vrotate matrix hook branch into the cave')
        need(old[0x40d17728-base:0x40d17730-base]==bytes.fromhex('08de80d28863a0f2'),'vrotate latch site stock bytes')
        need(cave<=branch_target(0x40d17728,read(new,'<I',0x40d17728-base)[0])<unit_end,'vrotate latch hook branch into the cave')
        need(read(new,'<I',0x40d1772C-base)[0]==0xD503201F,'vrotate latch site trailing nop')
        need(struct.pack('<Q',0xA03D5C26A) in new[cave-base:unit_end-base],'vrotate active value byte literal in the unit')
        # A+ migration (2026-11-09 vrotate-fix t1 report): the unit state
        # lives in the boot-copied data mirror window EG [0x4B25800,0x4B25900)
        # (RAM 0xA0281A800).  Fixed facts: the window base literal rides in
        # the unit, the threshold and axis codes sit at the frozen offsets,
        # the one-shot latch and first-boot sentinel mirror bytes ship 0 and
        # the window tail byte is the 0xA5 magic (a boot-copy witness that
        # zero-initialized RAM cannot fake).
        need(struct.pack('<Q',0xA0281A800) in new[cave-base:unit_end-base],'vrotate state window literal in the unit')
        window=new[0x4B25800:0x4B25900]
        need(struct.unpack_from('<I',window,0x6C)[0]==0x3F333333,'vrotate threshold in the state window')
        need(window[0x70:0x76]==bytes((1,2,0,0,0,3)),'vrotate axis codes in the state window')
        need(window[0x76]==0 and window[0x77]==0,'vrotate one-shot latch and sentinel mirror bytes ship zero')
        need(window[0xFF]==0xA5,'vrotate state window magic byte')
        # T2b fixed events sub-window: the 44-record clone with its 0x3BB
        # terminator, three actions into the unit code, and the 8 B
        # emit-region pointer naming the window (the only external byte that
        # carries the table address).  `events` above is the VIDEO_EVENTS
        # pointer-table VA.
        table=new[0x40A09000-base:0x40A09580-base]
        need(read(table,'<Q',32*43)[0]==0x3BB,'vrotate events window terminator')
        need(sum(1 for i in range(44) if read(table,'<Q',32*i+8)[0] in range(cave,unit_end))==3,
            'vrotate events window toggle actions into the unit')
        need(read(new,'<Q',events-base+8*ids.index(0x315B))[0]==0x40A09000,'vrotate row transition table at the fixed events window')
        imms={ (w>>5)&0xFFFF for w in struct.unpack_from(f'<{(0x2EC)//4}I',new,cave-base) if w&0xFFE00000==0x52800000 }
        need({2466,2467}<=imms,'vrotate On/Off value ids in cave code')
        row_at=rows-base+44*ids.index(0x315B)
        need(read(new,'<I',row_at)[0]==3225,'vrotate row title id 3225')
        need(read(new,'<I',row_at+16)[0]==0x20901005,'vrotate row class word')
        need(read(new,'<I',row_at+20)[0]==0x1327,'vrotate row value sub-widget')
        vrotate=dict(cave=hex(cave),unit_end=hex(unit_end),events_window='0x40a09000-0x40a09580 (fixed cave sub-window)',state_window='0xa0281a800-0xa0281a900 (boot-copied data mirror, EG 0x4b25800)',row='0x315b',title_id=3225,value_ids=[2466,2467],sentinel='0x5A armed at first boot, mirror byte ships 0')
        need(end>=0x40A10000,'copy boundary covers the vrotate cave')
    return dict(status='PASS',video_menu=video,language_tables=36,offsets_per_language=entries,
                exact_group_visibility=True,zero_state=True,loader_end=hex(end),vrotate=vrotate)
