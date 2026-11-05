"""H.265 HB2 with the row-text correction; shared menu and star ownership."""
import hashlib, json, struct
from pathlib import Path
from z8patch.image import Image, BASE, va, data_off, table_copy, branch
from z8prores.package import require
sha=lambda b:hashlib.sha256(b).hexdigest()
TIERS=Path(__file__).with_name('tiers.json')
CODE_AT,MENU_AT,AREA_END=0x40A10000,0x40A12000,0x40A1F000
SELECT_SITE,MEMCPY=0x402F3360,0x4127A900
ROWS_A,EVPTR_A,ROWS,ROW_BYTES=0x3AA4758,0x3AA4EE8,44,44
ROW_NRAW,ROW_ITEM=9,0x315A
STATES,STATE_SIZE,STATE_SUB,STATE_NRAW=0x4BFFCC0,0x60,0x17D,0x10D
SUB_STOCK=(0xA028E9FA0,0xA028B84D0)
SUB_PAGE_RAM=0xA028FDBF0
DATA_OFF,DATA_VA=0x4B13000,0xA02808000
NRAW_LAYOUT,NRAW_ROW,NRAW_EVENTS,NRAW_EVENT_COUNT,NRAW_PAGE=0x3AA81D0,0x3AA82E0,0x3AE69B0,14,0x4BCC760
NRAW_CALLBACKS_TAIL=(0x4056C954,0x403B2210,0x4056C958,0x4056C960)
NRAW_OK,OK_EVENTS,ENTER_EVENTS=0x4056C964,(0x286,0x28B,0x2AE),(0x286,0x28B,0x29F,0x2AE)
OPTION_ITEMS=(0x35B5,0x35B6,0x35B7,0x35B8,0x35B9)
NRAW_LABEL,LABEL_ID=0x8A6,3161
OPTIONS=('100%','60%','45%','30%','20%')
OPTION_IDS=tuple(range(3162,3167));GROUP_BASE=3167
SHARES=[100,60,45,30,20]
ICONS,SIZES,RATES=0x42B1FAE0,{3:4320,2:2160,1:1080},{0:'120000/1001',1:'100000/1000',2:'60000/1001',3:'50000/1000',4:'30000/1001',5:'25000/1000',6:'24000/1001'}
def groups():
    t=json.loads(TIERS.read_text());require(t['shares_percent']==SHARES, 'Unexpected firmware structure')
    out={}
    for r in t['rows']:
        key=(r['depth'],r['tiers'][0]['nominal_bps'])
        g=out.setdefault(key,dict(depth=r['depth'],rows=[],nominals=[x['nominal_bps'] for x in r['tiers']],targets=[x['target_kbps'] for x in r['tiers']]))
        require([x['nominal_bps'] for x in r['tiers']]==g['nominals'] and [x['target_kbps'] for x in r['tiers']]==g['targets'], r['row'])
        g['rows'].append(r['row'])
    gs=sorted(out.values(),key=lambda g:(g['depth'],-g['nominals'][0]))
    require(len(gs)==10 and [g['depth'] for g in gs]==[8]*5+[10]*5, 'Unexpected firmware structure')
    for g in gs:
        g['mbps']=[(k+500)//1000 for k in g['targets']]
        g['rows_text']=[f'{s}%  {m} Mbps' for s,m in zip(SHARES,g['mbps'])]
        g['value_text']=[f'{m}M' for m in g['mbps']]          # row value: the rate only (probe 2's "60% 200M" overflowed the field)
    return gs

def mode_table(eg,gs):
    """[size][rate] -> group index within the depth (FFh none), checked against the stock icon table and tiers.json."""
    t=json.loads(TIERS.read_text());pairs={}
    for i in range(80):
        item,typ,rate,size,slow,icon=struct.unpack_from('<6I',eg,ICONS-BASE+24*i)
        if typ in (2,3):require(slow==0, 'Unexpected firmware structure');pairs.setdefault(typ,set()).add((size,rate))
    require(pairs[2]==pairs[3] and len(pairs[2])==17, pairs)
    table=bytearray(b'\xff'*28)
    for size,rate in sorted(pairs[2]):
        found=[]
        for d,base in ((8,0),(10,5)):
            rows=[r for r in t['rows'] if r['depth']==d and r['height']==SIZES[size] and r['fps']==RATES[rate]]
            require(len(rows)==1, (size,rate,d))
            g=[i for i,x in enumerate(gs) if rows[0]['row'] in x['rows']];require(len(g)==1 and base<=g[0]<base+5, 'Unexpected firmware structure')
            found.append(g[0]-base)
        require(found[0]==found[1], (size,rate,found))                         # the same group pattern in both depths
        table[size*7+rate]=found[0]
    return bytes(table),sorted(pairs[2])

def menu(img,labels_va):
    """HB1's submenu with 11 page records and row 45 inserted at ROW_AT; returns the page addresses (groups 0..9, percent)."""
    eg=img.old;at=MENU_AT;blob={}
    def place(name,data,align=8):
        nonlocal at
        at=(at+align-1)&~(align-1);blob[name]=(at,bytes(data));at+=len(data);return blob[name][0]
    layout=bytearray(eg[NRAW_LAYOUT:NRAW_LAYOUT+0x110])
    require(struct.unpack_from('<I',layout,0x44)[0]==NRAW_LABEL, 'Unexpected firmware structure');struct.pack_into('<I',layout,0x44,LABEL_ID)
    stock_row=struct.unpack_from('<11I',eg,NRAW_ROW)
    require(stock_row==(0x35E,0xFFFF,0xFFFF,0,0x101000,0xFFFF,0x3119,0x20002,0xFFFFFFFF,0xFFFFFFFF,2), stock_row)
    ok=labels_va['tier_ok_hook'];seen=[]
    def ok_change(e,a,g,t):
        if a==NRAW_OK:seen.append(e);return e,ok,g,t
        return e,a,g,t
    option_table=table_copy(eg,va(NRAW_EVENTS),ok_change)
    require(len(option_table)==32*NRAW_EVENT_COUNT and tuple(seen)==OK_EVENTS, seen)
    stock_page=eg[NRAW_PAGE:NRAW_PAGE+0x50]
    require(struct.unpack_from('<4Q',stock_page)[:3]==(0x80001008,va(NRAW_LAYOUT),va(NRAW_ROW)) and struct.unpack_from('<H',stock_page,0x20)[0]==2, 'Unexpected firmware structure')
    layout_at=place('layout',layout)
    labelsets=[[GROUP_BASE+5*g+t for t in range(5)] for g in range(10)]+[list(OPTION_IDS)]
    rows_at=[place(f'rows{p}',b''.join(struct.pack('<11I',ids[i],*stock_row[1:6],OPTION_ITEMS[i],*stock_row[7:]) for i in range(5)),4)
             for p,ids in enumerate(labelsets)]
    tables_at=place('option_tables',option_table*5)
    evptr_at=place('option_pointers',struct.pack('<5Q',*(tables_at+len(option_table)*i for i in range(5))))
    callbacks_at=place('callbacks',struct.pack('<5Q',labels_va['tier_entry_hook'],*NRAW_CALLBACKS_TAIL))
    pages=[]
    for p,r in enumerate(rows_at):
        page=bytearray(stock_page);struct.pack_into('<3Q',page,8,layout_at,r,evptr_at);struct.pack_into('<H',page,0x20,5)
        pages.append(place(f'page{p}',page))
    stock_rows=eg[ROWS_A:ROWS_A+ROW_BYTES*ROWS];stock_ptrs=struct.unpack_from(f'<{ROWS}Q',eg,EVPTR_A)
    nraw=struct.unpack_from('<11I',stock_rows,ROW_BYTES*ROW_NRAW)
    require(nraw==(NRAW_LABEL,0xFFFF,0xFFFF,0,0x10104D,0,0x3118,0x40004,0xFFFFFFFF,0xFFFFFFFF,2), nraw)
    entered=[]
    def enter(e,a,g,t):
        if t==STATE_NRAW:entered.append(e);return e,a,g,STATE_SUB
        return e,a,g,t
    row_table=table_copy(eg,stock_ptrs[ROW_NRAW],enter);require(tuple(entered)==ENTER_EVENTS, entered)
    row_table_at=place('row_table',row_table)
    new_row=struct.pack('<11I',LABEL_ID,*nraw[1:6],ROW_ITEM,*nraw[7:])
    require(at<=AREA_END, 'menu data overflow')
    whole=bytearray(at-MENU_AT)
    for a,b in blob.values():whole[a-MENU_AT:a-MENU_AT+len(b)]=b
    img.put(MENU_AT,bytes(whole),'menu data: submenu layout, 11 x 5 rows, 5 option tables (OK -> tier_ok_hook), pointers, 17Dh callbacks, '
            '11 page records; row 45 transition table; 45-row video menu table (new row at index 10) and pointers',expect_zero=True)
    rec=STATES+STATE_SIZE*STATE_SUB
    st=struct.unpack_from('<12Q',eg,rec);nraw_st=struct.unpack_from('<12Q',eg,STATES+STATE_SIZE*STATE_NRAW)
    require(st[0]==(STATE_SUB<<16)|2 and st[1]==nraw_st[1] and (st[5],st[10])==SUB_STOCK and not any(st[2:5]+st[6:10]+st[11:]), st)
    require(DATA_VA+rec+0x50-DATA_OFF==SUB_PAGE_RAM, 'Unexpected firmware structure')
    img.put(rec+0x28,struct.pack('<Q',callbacks_at),'state 17Dh: callbacks -> tier submenu',expect=struct.pack('<Q',SUB_STOCK[0]),offset=True)
    img.put(rec+0x50,struct.pack('<Q',pages[10]),'state 17Dh: page record -> percent page (tier_refresh_hook rewrites it in RAM)',
            expect=struct.pack('<Q',SUB_STOCK[1]),offset=True)
    return pages,dict({k:hex(v[0]) for k,v in blob.items()},end=hex(at),row_item=hex(ROW_ITEM),
                      pages=[hex(p) for p in pages],sub_page_ram=hex(SUB_PAGE_RAM),
                      row_hex=new_row.hex(),row_table=hex(row_table_at))


def tier_table():
    t=json.loads(TIERS.read_text());require(t['shares_percent']==SHARES, 'Unexpected firmware structure')
    rows=t['rows'];require([r['row'] for r in rows]==list(range(11,45)), 'Unexpected firmware structure')
    blob=b''.join(x['nominal_bps'].to_bytes(4,'little') for r in rows for x in r['tiers'][1:])
    require(len(blob)==544 and sha(blob)==t['hook_table_sha256'], 'Unexpected firmware structure')
    return blob,dict(source='z8h265/tiers.json',source_sha256=sha(TIERS.read_bytes()),table_sha256=sha(blob))

def strings(img, gs, context):
    translations=[]
    for k in range(36):
        t=img.u64(0x311C5A0+8*k)-BASE;b=img.u64(0x387AF58+8*k)-BASE
        o=struct.unpack_from('<3137i',img.old,t)
        original=img.old[b+o[NRAW_LABEL]:b+o[NRAW_LABEL+1]].decode('utf-16le')
        label=original.replace('RAW-N','H.265') if 'RAW-N' in original else original.replace('N-RAW','H.265')
        require(label!=original,'H.265 translated label')
        translations.append([label,*OPTIONS,*[s for g in gs for s in g['rows_text']]])
    ids=context.add('h265',translations)
    require(ids==list(range(3161,3217)),'H.265 string allocation')
    return dict(ids=ids)

def build_main(eg, code, entries, context, ok_star):
    img=Image(eg);gs=groups();code=bytearray(code)
    def fill(name,data):
        at=entries[name]-CODE_AT
        require(code[at:at+len(data)]==bytes(len(data)),name)
        code[at:at+len(data)]=data
    table,table_info=tier_table();fill('tier_nominals',table)
    fill('tier_group_texts',b''.join(s.encode().ljust(12,b'\0') for g in gs for s in g['value_text']))
    modes,pairs=mode_table(eg,gs);fill('tier_mode_groups',modes)
    strings(img,gs,context)
    pages,sub=menu(img,dict(entries,tier_ok_hook=ok_star))
    fill('tier_pages',struct.pack('<11Q',*pages))
    img.put(SELECT_SITE,branch(SELECT_SITE,entries['tier_select_tail']),'H.265 bitrate selector',expect=branch(SELECT_SITE,MEMCPY))
    for at,old,new in ((0x402F6124,0x53077D6B,0x53067D6B),(0x402F6128,0x711D497F,0x7130D17F),(0x402F6158,0x711D497F,0x7130D17F)):
        img.put(at,struct.pack('<I',new),'HB2 protection timer',expect=struct.pack('<I',old))
    require(CODE_AT+len(code)<=MENU_AT,'H.265 code capacity')
    img.put(CODE_AT,code,'H.265 code and mode tables',expect_zero=True)
    return img,dict(entries={k:hex(v) for k,v in entries.items()},code_bytes=len(code),menu=sub,groups=gs,table=table_info)
