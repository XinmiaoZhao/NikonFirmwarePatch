"""Single owners for language resources, video menu, bank copy and loader."""
import struct
from z8prores.package import require
from z8patch.image import BASE, branch

STRING_IDS = {'opengate-nraw': (3137,5), 'pixelshift': (3142,5), 'prores': (3147,6),
              'anamorphic': (3153,8), 'h265': (3161,56), 'log': (3217,8), 'vrotate': (3225,1)}
TEXT, TABLES, TABLES_END = 0x40A50000, 0x40A70000, 0x40AF0000
# Highest allocated id + 1.  Compositions without vrotate keep the
# reviewed four-group string-table length (their unused ids stay empty
# strings, exactly as before), so their recipe bytes are unchanged until
# the vrotate release freezes the regenerated recipes.
STRING_END = max(first + count for first, count in STRING_IDS.values())
LEGACY_END = max(first + count for name, (first, count) in STRING_IDS.items()
                 if name != 'vrotate')
BANK, CONFIG = 0x40980000, 0x40980F00
ROWS, EVENTS, PAGE, CALLBACK = 0x3AA4758, 0x3AA4EE8, 0x4BCC2B0, 0x4BF3A80
VIDEO_ROWS, VIDEO_EVENTS = 0x40A30000, 0x40A31000


class Strings:
    def __init__(self):
        self.groups = {}

    def add(self, name, translations):
        first,count=STRING_IDS[name]
        require(name not in self.groups, 'Duplicate string provider')
        require(len(translations)==36 and all(len(t)==count for t in translations),'String provider shape')
        self.groups[name]=translations
        return list(range(first,first+count))

    def emit(self,img):
        if not self.groups:
            return {}
        end=STRING_END if 'vrotate' in self.groups else LEGACY_END
        text,tables=bytearray(),bytearray()
        for language in range(36):
            table=img.u64(0x311C5A0+8*language)-BASE
            blob=img.u64(0x387AF58+8*language)-BASE
            offsets=list(struct.unpack_from('<3137i',img.old,table))
            for ident in range(3137,end):
                value=''
                for name,translations in self.groups.items():
                    first,count=STRING_IDS[name]
                    if first<=ident<first+count:
                        value=translations[language][ident-first]
                offsets.append(TEXT+len(text)-BASE-blob)
                text.extend(value.encode('utf-16le'))
            offsets.append(TEXT+len(text)-BASE-blob)
            require(len(offsets)==end+1,'Shared string shape')
            at=TABLES+len(tables)
            tables.extend(struct.pack(f'<{len(offsets)}i',*offsets))
            img.put(0x311C5A0+8*language,struct.pack('<Q',at),f'shared language directory {language}')
        require(TEXT+len(text)<=TABLES and TABLES+len(tables)<=TABLES_END,'Shared strings overflow')
        img.put(TEXT-BASE,text,'shared selected-feature strings',expect_zero=True)
        img.put(TABLES-BASE,tables,'shared 36 language offset tables',expect_zero=True)
        return dict(features=sorted(self.groups),entries=end+1,text_bytes=len(text),table_bytes=len(tables),text=hex(TEXT),tables=hex(TABLES))


class VideoMenu:
    def __init__(self,stock):
        self.stock=stock
        self.rows=[stock[ROWS+44*i:ROWS+44*(i+1)] for i in range(44)]
        self.pointers=list(struct.unpack_from('<44Q',stock,EVENTS))
        self.items=[struct.unpack_from('<I',r,24)[0] for r in self.rows]
        require(len(set(self.items))==44,'Stock video item identities')
        self.replacements={}

    def collect(self,part,item):
        matches=[i for i in range(44) if struct.unpack_from('<I',part.new,ROWS+44*i+24)[0]==item]
        require(len(matches)==1,'Feature row missing or duplicated')
        i=matches[0]
        self.add(item,bytes(part.new[ROWS+44*i:ROWS+44*(i+1)]),struct.unpack_from('<Q',part.new,EVENTS+8*i)[0])

    def add(self,item,row,pointer):
        require(item not in self.replacements and len(row)==44 and struct.unpack_from('<I',row,24)[0]==item,'Duplicate or invalid feature row')
        self.replacements[item]=(row,pointer)

    @staticmethod
    def consumed(edit):
        at,end=edit['offset'],edit['end']
        for start,stop in ((ROWS,ROWS+44*44),(EVENTS,EVENTS+44*8),(CALLBACK,CALLBACK+8)):
            if at<stop and start<end:
                require(start<=at and end<=stop,'Partial shared-menu edit')
                return True
        # Standalone wrappers used another hidden item. Keep original item IDs
        # and set each selected item's hide bit to zero instead.
        if at in (0x40572930-BASE,0x4057294C-BASE,0x40572968-BASE):
            require(end==at+4,'Unexpected hide edit')
            return True
        return False

    def emit(self,img,chosen,code,entries,callbacks):
        mask=sum(bit for name,bit in (('framing',1),('video-quality',2),('log-colour',4),('video-orientation',8)) if name in chosen)
        if not mask:
            require(not self.replacements,'Unexpected video menu without video features')
            return None
        records={item:(row,ptr) for item,row,ptr in zip(self.items,self.rows,self.pointers)}
        records.update(self.replacements)
        order=list(self.items)
        if 'log-colour' in chosen:
            order.remove(0x2E38);order.insert(order.index(0x2FC1)+1,0x2E38)
        if 'video-quality' in chosen:
            order.remove(0x311B);pos=order.index(0x3118)+1
            order[pos:pos]=[0x311B,0x315A]
        if 'video-orientation' in chosen:
            require(0x315B in self.replacements and callbacks.get('vrotate'),'vrotate row or refresh callback missing')
            order.insert(order.index(0x30A6),0x315B)   # before the image-area row
        require(set(order)==set(records) and len(order)==len(set(order)),'Video menu loses or duplicates an item')
        rows=b''.join(records[i][0] for i in order)
        pointers=struct.pack(f'<{len(order)}Q',*(records[i][1] for i in order))
        require(VIDEO_ROWS+len(rows)<=VIDEO_EVENTS and VIDEO_EVENTS+len(pointers)<=0x40A40000,'Shared video menu capacity')
        img.put(VIDEO_ROWS-BASE,rows,'shared final video menu rows',expect_zero=True)
        img.put(VIDEO_EVENTS-BASE,pointers,'shared final video menu transition pointers',expect_zero=True)
        old=struct.pack('<QQH',BASE+ROWS,BASE+EVENTS,44)
        img.put(PAGE+0x10,struct.pack('<QQH',VIDEO_ROWS,VIDEO_EVENTS,len(order)),'shared video menu page: final rows and count',expect=old)
        hides=[]
        for feature,site,item in (('log-colour',0x40572940,0x2E38),('video-quality',0x4057295C,0x311B),('framing',0x40572978,0x310F)):
            if feature in chosen:
                img.put(site-BASE,struct.pack('<I',0x52800002),f'show selected menu item {item:#x}',expect=bytes.fromhex('e2030032'))
                hides.append(hex(item))
        require(len(code)<=CONFIG-BANK,'Shared code reaches configuration')
        img.put(BANK-BASE,code,'shared bank and refresh code',expect_zero=True)
        # Row-callback slots at CONFIG+8: prores, h265, anamorphic, log, and --
        # only for video-orientation compositions, whose recipe freezes with
        # the vrotate release -- the fifth vrotate slot at CONFIG+0x28.
        slots=('prores','h265','anamorphic','log')+(('vrotate',) if 'video-orientation' in chosen else ())
        ptrs=[callbacks.get(k,0) for k in slots]
        img.put(CONFIG-BASE,struct.pack(f'<II{len(slots)}Q',mask,0,*ptrs),'shared feature mask and row callbacks',expect_zero=True)
        img.put(CALLBACK,struct.pack('<Q',entries['shared_refresh']),'shared video refresh dispatcher',expect=struct.pack('<Q',0x40572B2C))
        img.put(0x410162EC-BASE,branch(0x410162EC,entries['shared_bank']),'shared menu-bank copy dispatcher',expect=bytes.fromhex('ea2340a9'))
        return dict(items=[hex(i) for i in order],count=len(order),visible_custom_items=hides,rows=hex(VIDEO_ROWS),events=hex(VIDEO_EVENTS),mask=mask,
                    callbacks={k:hex(v) for k,v in callbacks.items()},entries={k:hex(v) for k,v in entries.items()},native_refresh_calls=1,
                    text_slots=dict(prores='0x4a',h265='0x48',anamorphic='0x49',log='0x47'))


def loader(img,features):
    floor=0x408BF8F0
    if 'framing' in features:floor=max(floor,0x40980000)
    if 'photo-tools' in features:floor=max(floor,0x409F0000)
    if 'video-orientation' in features:floor=max(floor,0x40A10000)
    if 'video-quality' in features:floor=max(floor,0x40A42000)
    if 'log-colour' in features:floor=max(floor,0x40B50000)
    used=max([floor]+[BASE+e['end'] for e in img.edits if 0x75F8F0<=e['offset']<0xAA0000])
    end=(used+4095)&~4095
    require(end<=0x40C00000,'Text loader exceeds original mapped section')
    data=struct.pack('<II',0xD2800008|((end&65535)<<5),0xF2A00008|((end>>16)<<5))
    img.put(0x1024D8C,data,'shared text copy boundary',expect=bytes.fromhex('081e9fd26811a8f2'))
    return dict(end=hex(end),includes_zero_state=True)
