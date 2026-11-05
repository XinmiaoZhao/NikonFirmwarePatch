"""Three-choice Log colour module with per-clip playback; recording tables stay fixed."""
import hashlib,json,struct
from pathlib import Path
from z8patch.image import Image, BASE, va, data_off, table_copy, branch as enc_b, movz, movk
from z8prores.package import require
TEXT_STYLE=0x2CE
sha=lambda b:hashlib.sha256(b).hexdigest()
# blank area (zero in the stock payload, copied to RAM once the copy end is raised)
BLANK = (0x408BF8F0, 0x40C00000)
COPY_END_SITE, COPY_END = 0x41184D8C, 0x40C00000
LG_CODE, LG_DATA, LG_SUB, LG_ICONS, LG_PNG, TEXT, TABLES, TABLES_LIMIT = (
    0x40B00000, 0x40B08000, 0x40B10000, 0x40B20000, 0x40B48000, 0x40B50000, 0x40B60000, 0x40C00000)
DATA = dict(LG_RGB1=0x0000, LG_RGB2=0x0600, LG_NLG1=0x0C00, LG_NLG2=0x0E00, LG_M2_1=0x1000, LG_M2_2=0x1020,
            LG_M1_1=0x1040, LG_M1_2=0x1060, LG_CPXS1=0x1100, LG_CPXS2=0x1300, LG_CC_SLOG3=0x1500)
FORCE_AT = 0x1F00                                          # QEMU-only constant Log type byte (l2-force1/2)
VA_AT = 0x2000                                             # view assist: pointer tables, matrices, curves (LG_DATA + VA_AT)
VA_MAT_PTRS, VA_CB_PTRS = 0x4167A2A0, 0x4167A3C0           # stock mode-1 matrix / curve-B pointer tables (4 entries used)
LG_PRIV, ALIAS = 0x40B0E000, 0xA0F800000 - 0x40200000      # private page (zero in the stock payload) and its RAM alias
KEYS_BUF_SIZE = 0x1000
LOG_TYPE = 0xA03D5C0DD

# recording chain and file sites: (address, stock word, hook entry, kind)
B_SITES = [(0x4111A508, '0800e0f2', 'lg_rgb_hook'), (0x4111A6D4, '2129029b', 'lg_nlg_hook'),
           (0x41116CB4, '0b250b9b', 'lg_m2_hook'), (0x41116010, '0e00e0f2', 'lg_m1_hook'),
           (0x4111A198, '75a24039', 'lg_cpxs_hook'), (0x406D2D94, 'e0030032', 'lg_tag26_tail'),
           (0x406C1988, '3515891a', 'lg_keycount_hook'), (0x406C196C, '013d0054', 'lg_keyclass_hook'),
           (0x4071F5CC, '1f0d0071', 'lg_keys_gate'), (0x406D3994, 'ff0301d1', 'lg_pc_write'),
           (0x406D05FC, 'a1ffff17', 'lg_pc_parse_tail'), (0x4064D718, 'c9a98552', 'lg_pb_label'),
           (0x402D1AA4, 'd1ffff17', 'lg_va_sel0'), (0x402D1CF8, 'a6ffff17', 'lg_va_sel1'),
           (0x406C1FA8, '68ba0011', 'lg_cc_next_hook'), (0x4041A868, '3b000014', 'lg_icon_tail'),
           (0x410162EC, 'ea2340a9', 'lg_bank_hook'),
           (0x40EC78D0, 'ee820114', 'lg_lv_clear'), (0x407A831C, 'f37b48a9', 'lg_pb_build')]
BL_SITES = [(0x406C1FA4, 0x4127A900, 'lg_cc_copy_hook'), (0x406820F4, 0x403FB4AC, 'lg_pb_info')]
# non-call instructions replaced by bl (the enclosing functions save x30 and call others after these sites)
BLX_SITES = [(0x40D09384, 'e2031faa', 'lg_keys_close'), (0x402CE18C, 'c9764539', 'lg_va_cmp_a'),
             (0x402D5DBC, 'e8764539', 'lg_va_cmp_b'), (0x402CE1F0, 'ca760539', 'lg_va_store_a'),
             (0x402D5E10, 'e8760539', 'lg_va_store_b')]
# video file type page refresh 4056CD84: inline "N-Log" -> "Log" (movz w9,#0x2d4e / movk w9,#0x6f4c,lsl #16 per 10-bit row)
FILE_TYPE_SITES = (0x4056CDE4, 0x4056CE58, 0x4056CED4, 0x4056CF50)
# menu
DATA_OFF, DATA_END, DATA_VA = 0x4B13000, 0x4DC0000, 0xA02808000
STATES, STATE_SIZE, STATE_SUB, STATE_NRAW = 0x4BFFCC0, 0x60, 0xB5, 0x10D
SUB_STOCK = (0xA028E8100, 0xA028CF540)                     # B5h's stock callbacks and page record
NRAW_LAYOUT, NRAW_ROW, NRAW_EVENTS, NRAW_EVENT_COUNT, NRAW_PAGE = 0x3AA81D0, 0x3AA82E0, 0x3AE69B0, 14, 0x4BCC760
NRAW_CALLBACKS = (0x4056C8F8, 0x4056C954, 0x403B2210, 0x4056C958, 0x4056C960)
NRAW_OK, OK_EVENTS, ENTER_EVENTS = 0x4056C964, (0x286, 0x28B, 0x2AE), (0x286, 0x28B, 0x29F, 0x2AE)
OPTION_ITEMS = (0x35C0, 0x35C1, 0x35C2)                    # reserved items -> generic string 43Ah (open gate D4..D9 used them on its own page)
ROWS_A, EVPTR_A, VIDEO_ROWS = 0x3AA4758, 0x3AA4EE8, 44
ROW_LOG, ROW_NRAW, ITEM_LOG, ITEM_NRAW = 2, 9, 0x2E38, 0x3118
ROTATE = (2, 3, 4, 5, 6)                                   # new rows 2..6 = stock rows 3, 4, 5, 6, 2
HIDE_SITE = 0x40572930                                     # mov w1, #0x2e38 -> mov w1, #0x311b
VIDEO_CALLBACKS, STOCK_REFRESH = 0x4BF3A60, 0x40572B2C
TONE_PAGE, TONE_ROWS_VA = 0x4BCC6C0, 0x43C06E64
BB2_SITES = ((0x40747E7C, 2), (0x4074C2E8, 3))            # mov w2/w3, #0xbb2 (message id)
# icons
ICON_TABLE, ICON_COUNT, ICON_SITE = 0x431D96D0, 6242, 0x403EE56C
ICON_KEYS = ('slog3_fill', 'slog3_outline', 'log3g10_fill', 'log3g10_outline')
# strings
TABLE_DIR, BLOB_DIR, LANGUAGES = 0x311C5A0, 0x387AF58, 36
STOCK_OFFSETS = 3137                                       # ids 0..3135 and the end mark
SPACER = 3136
NEW = ('log', 'log_settings', 'nlog_g', 'slog3_g', 'log3g10_g', 'help_9ac', 'help_9ad', 'msg_bb2')
IDS = {k: 3217 + i for i, k in enumerate(NEW)}             # 3137..3144
SUB_LABELS = {'nlog_g': 'N-Log / BT.2020', 'slog3_g': 'S-Log3 / S-Gamut3.Cine', 'log3g10_g': 'Log3G10 / REDWideGamutRGB'}
LABELS = {0: 'Log設定', 1: 'Log settings', 2: 'Log-Einstellungen', 3: 'Réglages Log', 4: 'Ajustes de Log', 5: 'Impostazioni Log',
          6: 'Log-inställningar', 7: 'Log-instellingen', 8: 'Log设定', 9: 'Log設定', 10: 'Log 설정', 11: 'Настройки Log',
          13: 'Pengaturan Log', 14: 'Configurações Log', 15: 'Ustawienia Log', 16: 'Log-asetukset', 17: 'Log-indstillinger',
          18: 'Log-innstillinger', 19: 'Nastavení Log', 20: 'Log ayarları', 21: 'Log beállítások', 22: 'Ρυθμίσεις Log',
          23: 'Setări Log', 24: 'Налаштування Log', 32: 'Настройки на Log', 33: 'Podešavanja Log'}
JAPANESE_SLOTS = (0, 25, 26, 28, 29, 30, 31, 35)
FALLBACK = 'Log settings'                                  # Thai (12), Hindi (27), Arabic (34) and any slot missing a glyph

def va_blob(d, eg):
    """LG_DATA + VA_AT: matrix and curve-B pointer tables of types 1, 2 (4 entries each, as 4167A2A0 / 4167A3C0: index
    A02E70DF2 * 2 + [A02810470]; entries 2/3 keep the stock pointers), then the four matrices and four curves."""
    at = LG_DATA + VA_AT
    mats, curves = at + 0x80, at + 0x100
    stock = lambda table, i: struct.unpack_from('<Q', eg, table - BASE + 8 * i)[0]  # noqa: E731
    blob = bytearray(0x300)
    for t in (1, 2):
        v = d['view_assist']['types'][str(t)]['variants']
        ptr_m, ptr_c = [], []
        for var in (0, 1):
            k = 2 * (t - 1) + var
            m, c = bytes.fromhex(v[str(var)]['matrix_hex']), bytes.fromhex(v[str(var)]['curve_b_hex'])
            require(len(m) == 0x18 and len(c) == 0x80 and m[:2] == b'\1\1', 'Unexpected firmware structure')
            blob[0x80 + 0x18 * k:0x80 + 0x18 * (k + 1)] = m
            blob[0x100 + 0x80 * k:0x100 + 0x80 * (k + 1)] = c
            ptr_m.append(mats + 0x18 * k)
            ptr_c.append(curves + 0x80 * k)
        ptr_m += [stock(VA_MAT_PTRS, 2), stock(VA_MAT_PTRS, 3)]
        ptr_c += [stock(VA_CB_PTRS, 2), stock(VA_CB_PTRS, 3)]
        blob[0x20 * (t - 1):0x20 * t] = struct.pack('<4Q', *ptr_m)
        blob[0x40 + 0x20 * (t - 1):0x40 + 0x20 * t] = struct.pack('<4Q', *ptr_c)
    return bytes(blob), dict(LG_VA_MAT1=at, LG_VA_MAT2=at + 0x20, LG_VA_CB1=at + 0x40, LG_VA_CB2=at + 0x60)

def colour_blob(d):
    """LG_DATA contents: both types' tables at the DATA offsets."""
    blob = bytearray(0x1F00)
    for t, suffix in (('1', '1'), ('2', '2')):
        x = d['types'][t]
        for key, raw in ((f'LG_RGB{suffix}', bytes.fromhex(x['rgb_hex'])), (f'LG_NLG{suffix}', bytes.fromhex(x['nlg_hex'])),
                         (f'LG_M2_{suffix}', struct.pack('<9h', *x['m2'])), (f'LG_M1_{suffix}', struct.pack('<9h', *x['m1_base'])),
                         (f'LG_CPXS{suffix}', struct.pack('<192h', *[v for row in x['cpxs_by_slot'] for v in row]))):
            o = DATA[key]
            require(not any(blob[o:o + len(raw)]), 'Unexpected firmware structure')
            blob[o:o + len(raw)] = raw
    cc = d['types']['1']['customcolor'].encode()
    require(len(cc) == 20, 'Unexpected firmware structure')
    blob[DATA['LG_CC_SLOG3']:DATA['LG_CC_SLOG3'] + 20] = cc
    keys = sorted(DATA, key=DATA.get)
    sizes = dict(LG_RGB1=1374, LG_RGB2=1374, LG_NLG1=458, LG_NLG2=458, LG_M2_1=18, LG_M2_2=18, LG_M1_1=18, LG_M1_2=18,
                 LG_CPXS1=384, LG_CPXS2=384, LG_CC_SLOG3=20)
    for a, b in zip(keys, keys[1:]):
        require(DATA[a] + sizes[a] <= DATA[b], (a, b))
    require(DATA[keys[-1]] + sizes[keys[-1]] <= FORCE_AT, 'Unexpected firmware structure')
    return bytes(blob)

def menu(img, entries):
    eg = img.old
    # video menu rows: stock layout checks, then the rotation and the Log row
    rows = [struct.unpack_from('<11I', eg, ROWS_A + 44 * i) for i in range(VIDEO_ROWS)]
    ptrs = [img.u64(EVPTR_A + 8 * i) for i in range(VIDEO_ROWS)]
    require(rows[ROW_LOG] == (0x43A, 0xFFFF, 0xFFFF, 0, 0x101045, 0xB44, ITEM_LOG, 0x40004, 0xFFFFFFFF, 0xFFFFFFFF, 2) and ptrs[ROW_LOG] == 0x43C28990, 'Unexpected firmware structure')
    require(rows[ROW_NRAW][6] == ITEM_NRAW and ptrs[ROW_NRAW] == 0x43C2B1B0, 'Unexpected firmware structure')
    require([rows[i][6] for i in ROTATE] == [0x2E38, 0x30D2, 0x2E3B, 0x3055, 0x2FC1], 'Unexpected firmware structure')   # Disable, Storage folder, File naming, Destination, Video file type
    entered = []

    def enter(e, a, g, t):
        if t == STATE_NRAW:
            entered.append(e)
            return e, a, g, STATE_SUB
        return e, a, g, t
    row_table = table_copy(eg, ptrs[ROW_NRAW], enter)
    require(tuple(entered) == ENTER_EVENTS, entered)
    # submenu page (copy of the stock N-RAW quality list page, 3 rows)
    layout = bytearray(eg[NRAW_LAYOUT:NRAW_LAYOUT + 0x110])
    require(struct.unpack_from('<I', layout, 0x44)[0] == 0x8A6, 'stock layout title')
    struct.pack_into('<I', layout, 0x44, IDS['log_settings'])
    stock_row = struct.unpack_from('<11I', eg, NRAW_ROW)
    require(stock_row == (0x35E, 0xFFFF, 0xFFFF, 0, 0x101000, 0xFFFF, 0x3119, 0x20002, 0xFFFFFFFF, 0xFFFFFFFF, 2), stock_row)
    labels = (IDS['nlog_g'], IDS['slog3_g'], IDS['log3g10_g'])
    opt_rows = b''.join(struct.pack('<11I', labels[i], *stock_row[1:6], OPTION_ITEMS[i], *stock_row[7:]) for i in range(3))
    ok = entries['lg_sub_ok_hook']
    seen = []

    def ok_change(e, a, g, t):
        if a == NRAW_OK:
            seen.append(e)
            return e, ok, g, t
        return e, a, g, t
    table = table_copy(eg, va(NRAW_EVENTS), ok_change)
    require(len(table) == 32 * NRAW_EVENT_COUNT and tuple(seen) == OK_EVENTS, seen)
    stock_page = eg[NRAW_PAGE:NRAW_PAGE + 0x50]
    require(struct.unpack_from('<4Q', stock_page)[:3] == (0x80001008, va(NRAW_LAYOUT), va(NRAW_ROW)) and struct.unpack_from('<H', stock_page, 0x20)[0] == 2, 'Unexpected firmware structure')
    nraw_state = struct.unpack_from('<12Q', eg, STATES + STATE_SIZE * STATE_NRAW)
    require(struct.unpack_from('<5Q', eg, data_off(nraw_state[5])) == NRAW_CALLBACKS, 'Unexpected firmware structure')
    at = LG_SUB
    layout_at = at; at += len(layout)
    rows_at = at; at += len(opt_rows)
    at = (at + 7) & ~7
    tables_at = at; at += 3 * len(table)
    evptr_at = at; at += 3 * 8
    callbacks_at = at; at += 5 * 8
    page_at = at; at += 0x50
    row_table_at = at; at += len(row_table)
    require(at <= LG_ICONS, 'Unexpected firmware structure')
    page = bytearray(stock_page)
    struct.pack_into('<3Q', page, 8, layout_at, rows_at, evptr_at)
    struct.pack_into('<H', page, 0x20, 3)
    callbacks = struct.pack('<5Q', entries['lg_sub_entry_hook'], *NRAW_CALLBACKS[1:])
    blob = bytearray(at - LG_SUB)
    for a, b in ((layout_at, layout), (rows_at, opt_rows), (tables_at, table * 3),
                 (evptr_at, struct.pack('<3Q', *(tables_at + len(table) * i for i in range(3)))),
                 (callbacks_at, callbacks), (page_at, page), (row_table_at, row_table)):
        blob[a - LG_SUB:a - LG_SUB + len(b)] = b
    img.put(LG_SUB, bytes(blob), 'submenu tables: layout (stock N-RAW, title "Log settings"), 3 rows, 3 option tables (OK -> lg_sub_ok_hook), '
            'their pointers, B5h callbacks, page record, Log row transition table', expect_zero=True)
    rec = STATES + STATE_SIZE * STATE_SUB
    st = struct.unpack_from('<12Q', eg, rec)
    require(st[0] == (STATE_SUB << 16) | 2 and st[1] == nraw_state[1] and (st[5], st[10]) == SUB_STOCK and not any(st[2:5] + st[6:10] + st[11:]), st)
    img.put(rec + 0x28, struct.pack('<Q', callbacks_at), 'state B5h: callbacks -> Log settings submenu', expect=struct.pack('<Q', SUB_STOCK[0]), offset=True)
    img.put(rec + 0x50, struct.pack('<Q', page_at), 'state B5h: page record -> Log settings submenu', expect=struct.pack('<Q', SUB_STOCK[1]), offset=True)
    # rows 2..6 rotated (Log row after Video file type), the Log row's label and transitions
    new_rows = {p: rows[q] for p, q in zip(ROTATE, ROTATE[1:] + ROTATE[:1])}
    new_ptrs = {p: ptrs[q] for p, q in zip(ROTATE, ROTATE[1:] + ROTATE[:1])}
    log_pos = ROTATE[-1]
    # style of the N-RAW quality row (fields 1..5: text value child); stock row 2's style 101045h has an icon child (QEMU dev run)
    require(rows[ROW_NRAW][1:6] == (0xFFFF, 0xFFFF, 0, 0x10104D, 0) and rows[ROW_NRAW][7:] == rows[ROW_LOG][7:], 'Unexpected firmware structure')
    new_rows[log_pos] = (IDS['log_settings'], *rows[ROW_NRAW][1:6], ITEM_LOG, *rows[ROW_LOG][7:])
    new_ptrs[log_pos] = row_table_at
    img.put(ROWS_A + 44 * ROTATE[0], b''.join(struct.pack('<11I', *new_rows[p]) for p in ROTATE),
            'video menu rows 2..6: Storage folder, File naming, Destination, Video file type, Log settings (item 2E38, new label)',
            expect=b''.join(struct.pack('<11I', *rows[p]) for p in ROTATE), offset=True)
    img.put(EVPTR_A + 8 * ROTATE[0], b''.join(struct.pack('<Q', new_ptrs[p]) for p in ROTATE),
            'video menu row transition pointers 2..6, the Log row -> copy of the N-RAW quality row table entering B5h',
            expect=b''.join(struct.pack('<Q', ptrs[p]) for p in ROTATE), offset=True)
    # tone page 495: N-Log rows -> "Log", help texts -> the L1 copies
    pg = struct.unpack_from('<4Q', eg, TONE_PAGE)
    require(pg[2] == TONE_ROWS_VA and struct.unpack_from('<H', eg, TONE_PAGE + 0x20)[0] == 9, 'Unexpected firmware structure')
    tone = [struct.unpack_from('<11I', eg, TONE_ROWS_VA - BASE + 44 * i) for i in range(9)]
    require([r[0] for r in tone] == [0x709, 0x70A, 0x709, 0x70A, 0x709, 0x70A, 0x709, 0x70B, 0x70A], 'Unexpected firmware structure')
    require([r[1] for r in tone] == [0x9AC] * 6 + [0x9AD] * 3 and all(r[2] == 0x708 for r in tone), 'Unexpected firmware structure')
    help_id = {0x9AC: IDS['help_9ac'], 0x9AD: IDS['help_9ad']}
    new_tone = [(IDS['log'] if r[0] == 0x70A else r[0], help_id[r[1]], *r[2:]) for r in tone]
    img.put(TONE_ROWS_VA, b''.join(struct.pack('<11I', *r) for r in new_tone), 'tone page 495: N-Log rows labelled "Log", help 9AC/9AD -> L1 copies',
            expect=b''.join(struct.pack('<11I', *r) for r in tone))
    for a, rd in BB2_SITES:
        img.put(a, movz(rd, IDS['msg_bb2'], w=True), f'HDMI 8-bit message id BB2h -> L1 copy (w{rd})', expect=movz(rd, 0xBB2, w=True))
    return dict(layout=hex(layout_at), rows=hex(rows_at), option_tables=hex(tables_at), option_table_pointers=hex(evptr_at),
                callbacks=hex(callbacks_at), page=hex(page_at), log_row_table=hex(row_table_at), log_row_template=hex(ptrs[ROW_NRAW]),
                end=hex(at), option_items=[hex(i) for i in OPTION_ITEMS], option_labels=[hex(i) for i in labels], state=hex(STATE_SUB),
                video_rows_2_6=[hex(new_rows[p][6]) for p in ROTATE], log_row=log_pos)

def icon_table(img, icons):
    eg = img.old
    o = ICON_TABLE - BASE
    stock = eg[o:o + 0x18 * ICON_COUNT]
    require(struct.unpack_from('<IIIIQ', stock, 0x18 * 0xA7D) == (0x100, 0x245, 0, 0, 0x42F6C607), 'Unexpected firmware structure')
    require(not any(eg[o + 0x18 * ICON_COUNT:o + 0x18 * ICON_COUNT + 8]), 'Unexpected firmware structure')     # the stock table ends here (zero record)
    pngs, entries, at = bytearray(), [], LG_PNG
    for k in ICON_KEYS:
        b = icons[k]
        entries.append(struct.pack('<IIIIQ', 0x100, len(b), 0, 0, at + len(pngs)))
        pngs += b
        pngs += bytes(-len(pngs) % 16)
    table = stock + b''.join(entries) + bytes(0x18)
    require(LG_ICONS + len(table) <= LG_PNG and LG_PNG + len(pngs) <= TEXT, 'Unexpected firmware structure')
    img.put(LG_ICONS, table, f'icon table: stock {ICON_COUNT} entries + {len(ICON_KEYS)} L2 icons ({ICON_COUNT}..{ICON_COUNT + 3}) + end record', expect_zero=True)
    img.put(LG_PNG, bytes(pngs), 'L2 icon PNGs: S-Log3 and Log3G10 fill/outline (icons/make_icons.py)', expect_zero=True)
    img.put(ICON_SITE, movz(0, LG_ICONS & 0xffff) + movk(0, LG_ICONS >> 16, 16), 'icon table address (403EE56C, 4032DC34 stores it) -> L1 copy',
            expect=movz(0, ICON_TABLE & 0xffff) + movk(0, ICON_TABLE >> 16, 16))
    return dict(table=hex(LG_ICONS), entries=ICON_COUNT + len(ICON_KEYS), ids={k: ICON_COUNT + i for i, k in enumerate(ICON_KEYS)},
                pngs={k: dict(va=hex(struct.unpack_from('<Q', e, 16)[0]), bytes=len(icons[k]), sha256=sha(icons[k])) for k, e in zip(ICON_KEYS, entries)})

def asm_defines():
    defs={k:LG_DATA+v for k,v in DATA.items()}
    at=LG_DATA+VA_AT
    defs.update(ICON_BASE=ICON_COUNT,OPTION_ITEM0=OPTION_ITEMS[0],OPTION_ITEM1=OPTION_ITEMS[1],OPTION_ITEM2=OPTION_ITEMS[2],
                LG_VA_MAT1=at,LG_VA_MAT2=at+0x20,LG_VA_CB1=at+0x40,LG_VA_CB2=at+0x60,
                TEXT_STYLE=TEXT_STYLE,KEYS_G=LG_PRIV+ALIAS,VA_LAST=LG_PRIV+0x20+ALIAS,PB_TYPE=LG_PRIV+0x21+ALIAS,KEYS_BUF=LG_PRIV+0x100+ALIAS,KEYS_BUF_SIZE=KEYS_BUF_SIZE)
    return defs

def load_data():
    d=json.loads(Path(__file__).with_name('data.json').read_text())
    icons={k:(Path(__file__).parent/'icons'/f'{k}.png').read_bytes() for k in ICON_KEYS}
    return d,icons
def strings(img, context):
    """Stock strings with ids 3137..3143 (3136 = spacer: it keeps the end of stock id 3135, as ProRes)."""
    old = img.old
    text, tables, labels, fallback, help_changed = bytearray(), bytearray(), [], [], {}
    translations = []
    for k in range(LANGUAGES):
        table = img.u64(TABLE_DIR + 8 * k) - BASE
        blob = img.u64(BLOB_DIR + 8 * k) - BASE
        offs = list(struct.unpack_from(f'<{STOCK_OFFSETS}i', old, table))
        get = lambda i: old[blob + offs[i]:blob + offs[i + 1]].decode('utf-16le')  # noqa: E731
        stock = ''.join(get(i) for i in range(STOCK_OFFSETS - 1))
        want = LABELS[0] if k in JAPANESE_SLOTS else LABELS.get(k, FALLBACK)
        if not set(want) <= set(stock):
            fallback.append(dict(slot=k, text=want, missing=''.join(sorted(set(want) - set(stock)))))
            want = FALLBACK
        require(set(want) <= set(stock), 'Unexpected firmware structure')
        labels.append(want)
        new_text = {'log': 'Log', 'log_settings': want, **SUB_LABELS}
        for key, sid in (('help_9ac', 0x9AC), ('help_9ad', 0x9AD), ('msg_bb2', 0xBB2)):
            s = get(sid)
            new_text[key] = s.replace('N-Log', 'Log').replace('N-log', 'Log')          # es/da write "N-log" in BB2h
            if new_text[key] != s:
                help_changed.setdefault(key, []).append(k)
        for key in ('log', *SUB_LABELS):
            require(set(new_text[key]) <= set(stock), ('glyphs missing', k, key))
        translations.append([new_text[key] for key in NEW])
    ids=context.add('log',translations)
    require(ids==[IDS[k] for k in NEW],'Log string allocation')
    return dict(ids=IDS, spacer=SPACER, labels=labels, label_fallback=fallback, help_n_log_replaced_in_slots=help_changed,
                )
def build_main(eg, code, entries, strings_context):
    d,icons=load_data()
    img = Image(eg)
    require(not any(eg[BLANK[0] - BASE:BLANK[1] - BASE]), 'blank area not zero')
    va,va_defs=va_blob(d,eg)
    require(LG_CODE+len(code)<=LG_DATA,'Log code capacity')
    img.put(LG_CODE, code, 'Log code: three-choice recording and per-clip playback', expect_zero=True)
    blob = bytearray(colour_blob(d))
    img.put(LG_DATA, bytes(blob), 'L1 colour tables (unchanged): RGB, NLG, M2 row, M1 base, Cpxs for S-Log3 (1) and Log3G10 (2); S-Log3 customcolor', expect_zero=True)
    img.put(LG_DATA + VA_AT, va, 'view assist: matrix / curve-B pointer tables of S-Log3 and Log3G10, 4 matrices, 4 curves (l2-data.json)',
            expect_zero=True)
    for a, word, entry in B_SITES:
        if a==0x410162EC: continue  # shared bank owns this site
        img.put(a, enc_b(a, entries[entry]), f'{a:08X}: {word} -> b {entry}', expect=bytes.fromhex(word))
    for a, t, entry in BL_SITES:
        img.put(a, enc_b(a, entries[entry], True), f'{a:08X}: bl {t:08X} -> bl {entry}', expect=enc_b(a, t, True))
    for a, word, entry in BLX_SITES:
        img.put(a, enc_b(a, entries[entry], True), f'{a:08X}: {word} -> bl {entry}', expect=bytes.fromhex(word))
    for a in FILE_TYPE_SITES:
        img.put(a, movz(9, 0x6F4C, w=True), f'{a:08X}: file type row value "N-Log" -> "Log": movz w9,#0x2d4e -> #0x6f4c ("Lo")',
                expect=movz(9, 0x2D4E, w=True))
        img.put(a + 8, struct.pack('<I', 0x72A00000 | 0x67 << 5 | 9), f'{a + 8:08X}: movk w9,#0x6f4c,lsl #16 -> #0x67 ("g", NUL)',
                expect=struct.pack('<I', 0x72A00000 | 0x6F4C << 5 | 9))
    sub = menu(img, entries)
    icon = icon_table(img, icons)
    text = strings(img, strings_context)
    return img,dict(code_bytes=len(code),entries={k:hex(v) for k,v in entries.items()},submenu=sub,icons=icon,strings=text,
                    colour_policy=d['policy'])
