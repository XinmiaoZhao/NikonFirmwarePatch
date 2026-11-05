"""AP4 port: integral geometry extension of the D10/Q3 framing module."""
import hashlib, struct
from z8patch.image import Image, BASE, va, data_off, table_copy, branch
from z8prores.package import require
def bl(a,t,link=True): return branch(a,t,link)

sha=lambda b:hashlib.sha256(b).hexdigest()
BASE,AP,SUB_AT,AP_STATE_VA,AP_END=0x40160000,0x40970000,0x40974000,0x4097F000,0x40980000
# AP1 sites
WINDOW_SITES=[(0x40F32E58,'stock LV recompute 40F30108, first display'),(0x40F35174,'stock LV rebuild 40F35040, first display'),
              (0x40960C98,'open-gate view_commit_hook, snapshot +0x1B8'),(0x40962B58,'open-gate og_leave_display_hook')]
AF_RECT_SITES,AF_RECT=(0x40386BA4,0x40386D54,0x40386E30,0x40387890),0x40387648
AF_POINTS_SITE,AF_POINTS=0x40386BE8,0x403EB928
TOUCH_SITES,TOUCH=(0x4043BED4,0x4043BFA0,0x4043BFB8,0x4043BFC4,0x4043C0E8),0x4043C234
BANK_SITE,C3_BANK=0x410162EC,0x40980000
HIDE_SITE=0x40572968
ROWS_A,ROW,ITEM=0x3AA4758,12,0x310F
EVPTR_A=0x3AA4EE8
VIDEO_CALLBACKS,C3_REFRESH=0x4BF3A60,0x40A000A4
# AP2 sites
FRAME_SITE,MEMCPY=0x40F2870C,0x4127A900
CORNER_CALC_SITE,CORNER_TABLE_SITE,CORNER_DRAW,CORNER_SKIP=0x40416294,0x40415B7C,0x40415B80,0x40415E08
NAV_X9_SITE,NAV_X8_SITE=0x40413724,0x40413B58
PLAYBACK_SITE,C3_PLAYBACK_FIT=0x407138D0,0x40960A00
PREVIEW_SITE,PREVIEW_BODY=0x409616A4,0x407D2EAC
# submenu
DATA_OFF,DATA_END,DATA_VA=0x4B13000,0x4DC0000,0xA02808000          # data image and its RAM address (z8prores.layout)
STATES,STATE_SIZE,STATE_SUB,STATE_NRAW=0x4BFFCC0,0x60,0xB6,0x10D
SUB_STOCK=(0xA028E8128,0xA028CF590)                                 # B6h's stock callbacks and page record
NRAW_LAYOUT,NRAW_ROW,NRAW_EVENTS,NRAW_EVENT_COUNT,NRAW_PAGE=0x3AA81D0,0x3AA82E0,0x3AE69B0,14,0x4BCC760
NRAW_CALLBACKS_TAIL=(0x4056C954,0x403B2210,0x4056C958,0x4056C960)
NRAW_OK,OK_EVENTS=0x4056C964,(0x286,0x28B,0x2AE)
ROW_NRAW_MENU,ROW12_TABLE=9,0x43C2C250                              # C3 video menu row 8 = N-RAW quality; AP1 row 12's stock table
ENTER_EVENTS=(0x286,0x28B,0x29F,0x2AE)
OPTION_ITEMS=(0x35B5,0x35B6,0x35B7,0x35B8,0x35BB,0x35BC,0x35BE,0x35BF)
ID_OFF=375                                                          # stock "Off" (关闭, しない, OFF ...)
TABLE_DIR,BLOB_DIR,LANGUAGES=0x311C5A0,0x387AF58,36
TEXT,TABLES,TABLES_LIMIT=0x408D0000,0x408E0000,0x40950000
C3_IDS,LABEL_ID=3154,3153               # C3 tables: 3154 offsets (ids 0..3152); AP2 to AP4: 3162 (3153 label, 3154..3160 ratios)
RATIOS=('1.25x','1.30x','1.33x','1.50x','1.60x','1.80x','2.00x')
NEW_IDS=1+len(RATIOS)
LABELS={0:'デスクイーズ表示',1:'Anamorphic desqueeze',2:'Desqueeze-Anzeige',3:'Affichage désanamorphosé',
        4:'Desanamorfización',5:'Visualizz. desqueeze',6:'Anamorfisk visning',7:'Anamorfe weergave',8:'变形镜头还原显示',
        9:'變形鏡頭拉伸顯示',10:'아나모픽 표시',11:'Анаморфотный просмотр',13:'Tampilan anamorfik',14:'Exibição anamórfica',
        15:'Podgląd anamorficzny',16:'Anamorfinen näyttö',17:'Anamorfisk visning',18:'Anamorfisk visning',
        19:'Anamorfické zobrazení',20:'Anamorfik görüntü',21:'Anamorf megjelenítés',22:'Αναμορφική προβολή',
        23:'Afișare anamorfică',24:'Анаморфний перегляд',32:'Анаморфен преглед',33:'Anamorfni prikaz'}
JAPANESE_SLOTS=(0,25,26,28,29,30,31,35)
FALLBACK='Anamorphic display'
def tb(a,t,nz,rt,bit=0):
    d=(t-a)//4;require((t-a)%4==0 and -(1<<13)<=d<(1<<13) and bit<32, 'Unexpected firmware structure')
    return struct.pack('<I',(0x37000000 if nz else 0x36000000)|(bit<<19)|((d&0x3fff)<<5)|rt)

def str_sp48(rt):return struct.pack('<I',0xF9000000|(0x48//8)<<10|31<<5|rt)

def movw1(imm):return struct.pack('<I',0x52800001|imm<<5)

def submenu(img,entries):
    """State B6h: a copy of the stock N-RAW quality list page with 8 rows (built as C3's ProRes page)."""
    eg=img.old
    layout=bytearray(eg[NRAW_LAYOUT:NRAW_LAYOUT+0x110])
    require(struct.unpack_from('<I',layout,0x44)[0]==0x8A6, 'stock layout title')
    struct.pack_into('<I',layout,0x44,LABEL_ID)
    stock_row=struct.unpack_from('<11I',eg,NRAW_ROW)
    require(stock_row[0]==0x35E and stock_row[6]==0x3119, stock_row)
    labels=(ID_OFF,*range(LABEL_ID+1,LABEL_ID+NEW_IDS))
    rows=b''.join(struct.pack('<11I',labels[i],*stock_row[1:6],OPTION_ITEMS[i],*stock_row[7:]) for i in range(8))
    ok=entries['ap_sub_ok_hook'];seen=[]
    def ok_change(e,a,g,t):
        if a==NRAW_OK:seen.append(e);return e,ok,g,t
        return e,a,g,t
    table=table_copy(eg,va(NRAW_EVENTS),ok_change)
    require(len(table)==32*NRAW_EVENT_COUNT and tuple(seen)==OK_EVENTS, seen)
    stock_page=eg[NRAW_PAGE:NRAW_PAGE+0x50]
    require(struct.unpack_from('<4Q',stock_page)[:3]==(0x80001008,va(NRAW_LAYOUT),va(NRAW_ROW)) and struct.unpack_from('<H',stock_page,0x20)[0]==2, 'Unexpected firmware structure')
    at=SUB_AT
    layout_at=at;at+=len(layout)
    rows_at=at;at+=len(rows)
    at=(at+7)&~7
    tables_at=at;at+=8*len(table)
    evptr_at=at;at+=8*8
    callbacks_at=at;at+=5*8
    page_at=at;at+=0x50
    # row 12's transitions: copy of row 8's (N-RAW quality) table with 10Dh -> B6h
    nraw_ptr=struct.unpack_from('<Q',eg,EVPTR_A+8*ROW_NRAW_MENU)[0];entered=[]
    def enter(e,a,g,t):
        if t==STATE_NRAW:entered.append(e);return e,a,g,STATE_SUB
        return e,a,g,t
    row_table=table_copy(eg,nraw_ptr,enter)
    require(tuple(entered)==ENTER_EVENTS, entered)
    row_table_at=at;at+=len(row_table)
    require(at<=AP_STATE_VA, 'submenu tables overflow the AP area')
    page=bytearray(stock_page)
    struct.pack_into('<3Q',page,8,layout_at,rows_at,evptr_at)
    struct.pack_into('<H',page,0x20,8)
    callbacks=struct.pack('<5Q',entries['ap_sub_entry_hook'],*NRAW_CALLBACKS_TAIL)
    blob=bytearray(at-SUB_AT)
    for a,b in ((layout_at,layout),(rows_at,rows),(tables_at,table*8),(evptr_at,struct.pack('<8Q',*(tables_at+len(table)*i for i in range(8)))),
                (callbacks_at,callbacks),(page_at,page),(row_table_at,row_table)):
        blob[a-SUB_AT:a-SUB_AT+len(b)]=b
    img.put(SUB_AT,bytes(blob),'submenu tables: layout (stock N-RAW, title 3153), 8 rows, 8 option tables (OK -> ap_sub_ok_hook), '
            'their pointers, B6h callbacks, page record, row 12 transition table',expect_zero=True)
    # state B6h
    rec=STATES+STATE_SIZE*STATE_SUB
    st=struct.unpack_from('<12Q',eg,rec);nraw_st=struct.unpack_from('<12Q',eg,STATES+STATE_SIZE*STATE_NRAW)
    require(st[0]==(STATE_SUB<<16)|2 and st[1]==nraw_st[1] and (st[5],st[10])==SUB_STOCK and not any(st[2:5]+st[6:10]+st[11:]), st)
    img.put(rec+0x28,struct.pack('<Q',callbacks_at),f'state {STATE_SUB:#x}: callbacks -> desqueeze submenu',expect=struct.pack('<Q',SUB_STOCK[0]),offset=True)
    img.put(rec+0x50,struct.pack('<Q',page_at),f'state {STATE_SUB:#x}: page record -> desqueeze submenu',expect=struct.pack('<Q',SUB_STOCK[1]),offset=True)
    require(struct.unpack_from('<Q',eg,EVPTR_A+8*ROW)[0]==ROW12_TABLE, 'Unexpected firmware structure')
    img.put(EVPTR_A+8*ROW,struct.pack('<Q',row_table_at),'video menu row 12 transition table -> copy of row 8 (N-RAW quality) entering B6h',
            expect=struct.pack('<Q',ROW12_TABLE),offset=True)
    return dict(layout=hex(layout_at),rows=hex(rows_at),option_tables=hex(tables_at),option_table_pointers=hex(evptr_at),
                callbacks=hex(callbacks_at),page=hex(page_at),row12_table=hex(row_table_at),row12_template=hex(nraw_ptr),
                end=hex(at),option_items=[hex(i) for i in OPTION_ITEMS],option_labels=list(labels),state=hex(STATE_SUB))

def strings(img, context):
    labels, fallback, translations = [], [], []
    for k in range(36):
        t=img.u64(TABLE_DIR+8*k)-BASE; b=img.u64(BLOB_DIR+8*k)-BASE
        o=struct.unpack_from('<3137i',img.old,t)
        chars=set(img.old[b+o[0]:b+o[-1]].decode('utf-16le'))
        label=LABELS[0] if k in JAPANESE_SLOTS else LABELS.get(k,FALLBACK)
        if not set(label)<=chars:
            fallback.append(k); label=FALLBACK
        require(set(label)<=chars, 'Missing anamorphic glyph')
        labels.append(label); translations.append([label,*RATIOS])
    ids=context.add('anamorphic',translations)
    require(ids==list(range(3153,3161)), 'Anamorphic string allocation')
    return labels,fallback,dict(ids=ids)
def build_main(eg, code, entries, strings_context):
    img=Image(eg)
    require(AP+len(code)<=SUB_AT, 'Unexpected firmware structure')
    require(not any(eg[AP-BASE:AP_END-BASE]), 'AP area not free in C3')
    img.put(AP,code,'AP4 code (ap4_hooks.S)',expect_zero=True)
    for a,why in WINDOW_SITES:
        img.put(a,bl(a,entries['ap_window_hook']),why+': bl 411871AC -> bl ap_window_hook',expect=bl(a,0x411871AC))
    for a in AF_RECT_SITES:
        img.put(a,bl(a,entries['ap_af_rect_hook']),'GUI AF display: bl 40387648 -> bl ap_af_rect_hook',expect=bl(a,AF_RECT))
    img.put(AF_POINTS_SITE,bl(AF_POINTS_SITE,entries['ap_af_points_hook']),'GUI AF display, lit AF points: bl 403EB928 -> bl ap_af_points_hook',
            expect=bl(AF_POINTS_SITE,AF_POINTS))
    for a in TOUCH_SITES:
        img.put(a,bl(a,entries['ap_touch_point_hook']),'touch gesture handler: bl 4043C234 -> bl ap_touch_point_hook',expect=bl(a,TOUCH))
    img.put(FRAME_SITE,bl(FRAME_SITE,entries['ap_frame_hook']),'LV snapshot 40F28488: per-frame copy of the display object bl 4127A900 -> bl ap_frame_hook',
            expect=bl(FRAME_SITE,MEMCPY))
    img.put(CORNER_CALC_SITE,bl(CORNER_CALC_SITE,entries['ap_corner_calc_tail'],link=False),
            'corner marks 404158D4, computed bars: tbnz w20,#0,40415B80 -> b ap_corner_calc_tail',expect=tb(CORNER_CALC_SITE,CORNER_DRAW,True,20))
    img.put(CORNER_TABLE_SITE,bl(CORNER_TABLE_SITE,entries['ap_corner_table_tail'],link=False),
            'corner marks 404158D4, fixed-table bars: tbz w20,#0,40415E08 -> b ap_corner_table_tail',expect=tb(CORNER_TABLE_SITE,CORNER_SKIP,False,20))
    img.put(NAV_X9_SITE,bl(NAV_X9_SITE,entries['ap_nav_bg_x9']),'zoom navigator 4041333C background: str x9,[sp,#0x48] -> bl ap_nav_bg_x9',expect=str_sp48(9))
    img.put(NAV_X8_SITE,bl(NAV_X8_SITE,entries['ap_nav_bg_x8']),'zoom navigator 4041333C background: str x8,[sp,#0x48] -> bl ap_nav_bg_x8',expect=str_sp48(8))
    img.put(PLAYBACK_SITE,bl(PLAYBACK_SITE,entries['ap_playback_fit_hook'],link=False),'movie playback fit 407138D0: b 40960A00 (C3) -> b ap_playback_fit_hook',
            expect=bl(PLAYBACK_SITE,C3_PLAYBACK_FIT,link=False))
    img.put(PREVIEW_SITE,bl(PREVIEW_SITE,entries['ap_preview_tail'],link=False),'paused movie page, end of C3 full-page static preview hooks: b 407D2EAC -> b ap_preview_tail',
            expect=bl(PREVIEW_SITE,PREVIEW_BODY,link=False))
    labels,fallback,layout=strings(img, strings_context)
    row_at=ROWS_A+44*ROW
    old_row=struct.unpack_from('<11I',eg,row_at);prores_row=struct.unpack_from('<11I',eg,ROWS_A+44*9)
    require(old_row==(0x817,0x9F3,0x817,0,0x20901005,0x1326,ITEM,0x40004,0xFFFFFFFF,0xFFFFFFFF,2), old_row)
    require(prores_row[6]==0x3118 and prores_row[4]==0x10104D, prores_row)
    img.put(row_at,struct.pack('<11I',LABEL_ID,*prores_row[1:6],ITEM,*prores_row[7:]),'video menu row 12: label 3153, ProRes row style, item 310f',
            expect=struct.pack('<11I',*old_row),offset=True)
    sub=submenu(img,entries)
    img.put(VIDEO_CALLBACKS+32,struct.pack('<Q',entries['ap_menu_refresh_hook']),'video menu state value refresh: 40A000A4 (ProRes wrapper) -> ap_menu_refresh_hook',
            expect=struct.pack('<Q',0x40572B2C),offset=True)
    return img,dict(code_bytes=len(code),entries={k:hex(v) for k,v in entries.items()},
                    labels=labels,label_fallback=fallback,strings=layout,submenu=sub)
