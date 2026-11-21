#!/usr/bin/env python3
"""A12 menu: photo "Choose image area" (page 1068, state 0x2A) with 7 rows, the 4:3 row labelled with its sensor size, and
the 4:3 / 2.39:1 / 65:24 rows greyed like 1:1 in C15/C30.  A module for the A12 builder: apply(img, eg, ...) on top of
the A2h compose result (img = hb1.Image).  README.md has the design and the evidence; check_menu_wide.py checks a
composed payload without importing this file.

Rows (value of menu item 0x07000603 -> setting 0x2124):
  0 FX 0  1 DX 1  2 4:3 2  3 1:1 8  4 16:9 4      (rows 0..4 = the stock rows, row 2 as A2/A2g left it)
  5 2.39:1 3  6 65:24 6                             (new: copies of the 16:9 row, new items 0x2C35 / 0x2C37)

Edits:
  strings   ids 3137 "4:3 (32x24)", 3138 "2.39:1 (36x15)", 3139 "65:24 (36x13)" per language, derived from that
            language's own 1:1 / 16:9 label (3136 = spacer that keeps the end of stock 3135, as L1/HB1); text 0x408D0000,
            36 offset tables at 0x408E0000 (shared HB1/L1 layout), the 36 language-directory pointers
  rows      new 7-row table (44 B rows) and 7-entry per-row event-table pointer array in this module's region; page
            record 1068 (+0x10 rows, +0x18 event tables, +0x20 count 5 -> 7).  The stock row table and its A2/A2g
            in-place edits stay, unreferenced.
  events    rows 5/6: copies of the 16:9 row's event table (18 records up to 0x3BB) with the OK handlers
            (events 0x286, 0x28B, 0x2AE) pointing at two 4-instruction OK caves that set 0x07000603 = 3 / 6, written
            like the stock OK functions 0x405E69C0..0x405E6A1C
  entry     0x405DBE24 (20 words, A2's cursor-by-value rewrite, dropped and redone): cursor item by value for
            1/2/4/8/3/6, default FX
  grey      0x405DBD24 'bl 0x403B1A5C' (the 16:9 grey call of the page callback 0x405DBCD0) -> bl cave_grey: the
            stock 16:9 call, then rows 0x2BE9 (4:3), 0x2C35 (2.39:1), 0x2C37 (65:24) greyed by restriction code 0x1A
            (the 1:1 rule: photo and release mode 3 (C30) or 6 (C15)); C60/C120 keep the stock whole-item code 0x19
  icons     rows 5/6 icon field (+0x14) = icons[3] / icons[6] (default 0xFFFF; then the row flags are 0x101000, i.e.
            without the icon bit, so the body does not draw the hourglass A2 showed for an icon-less 0x101001 row)
Not changed here: the value-icon switches of page 1067 (0x405DBD78, 0x405D99F4: the icons branch), the i menu list.
"""
import struct, sys
from pathlib import Path

H = Path(__file__).resolve().parent
from capstone import CS_ARCH_ARM64, CS_MODE_ARM, Cs  # noqa: E402

BASE, DATA_VA, DATA_OFF, DATA_END = 0x40160000, 0xA02808000, 0x4B13000, 0x4DC0000
PAGES, PAGE = 0x4BC2C10, 1068
PAGE_REC = PAGES + 0x50 * PAGE                     # payload offset 0x4BD79D0 (RAM data image, VA 0xA028CC9D0)
STOCK_ROWS, STOCK_EVPTR, ROW_BYTES = 0x43DD2A8C, 0x43DD2B68, 44
EV16_9 = 0x43E30FE0                                # 16:9 row's event table (18 records, ends with 0x3BB)
OK_EVENTS = (0x286, 0x28B, 0x2AE)
OK_16_9, SETTER, MENU_ITEM = 0x405E6A10, 0x403EC39C, 0x07000603
GREY_SET, RESTRICT, GREY_SITE, GREY_CODE = 0x403B1A5C, 0x403A036C, 0x405DBD24, 0x1A
ENTRY_SITE, ENTRY_WORDS = 0x405DBE24, 20
ITEM_FX, ITEM_DX, ITEM_43, ITEM_11, ITEM_169 = 0x2BEB, 0x29B8, 0x2BE9, 0x2BEA, 0x2C5F
ITEM_239, ITEM_6524 = 0x2C35, 0x2C37                # census: in no row record, no MOVZ immediate, no aligned u32 of the payload
ROWS = [(0, ITEM_FX), (1, ITEM_DX), (2, ITEM_43), (8, ITEM_11), (4, ITEM_169), (3, ITEM_239), (6, ITEM_6524)]
# strings (layout of HB1 / L1)
TABLE_DIR, BLOB_DIR, LANGUAGES, STOCK_IDS = 0x311C5A0, 0x387AF58, 36, 3136
TEXT, TABLES, TABLES_LIMIT = 0x408D0000, 0x408E0000, 0x40950000
SPACER, ID_43, ID_239, ID_6524 = 3136, 3238, 3239, 3240
LABEL_11, LABEL_169, LABEL_784 = 0x534, 0x582, 0x784
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)


def data_off(v):
    assert DATA_VA <= v < DATA_VA + (DATA_END - DATA_OFF), hex(v)
    return v - DATA_VA + DATA_OFF


def text(code, at):
    return [f'{i.mnemonic} {i.op_str}'.strip() for i in md.disasm(code, at)]


def movz(rd, imm): assert 0 <= imm < 0x10000; return 0x52800000 | imm << 5 | rd
def movk16(rd, imm): return 0x72A00000 | imm << 5 | rd
def cmpw0(imm): return 0x7100001F | imm << 10
def br(src, dst, link=False):
    d = dst - src; assert d % 4 == 0 and -(1 << 27) <= d < (1 << 27)
    return (0x94000000 if link else 0x14000000) | ((d >> 2) & 0x3FFFFFF)
CSEL_W20_W8_EQ = 0x1A800000 | 20 << 16 | 8 << 5 | 20       # csel w20, w8, w20, eq
NOP, RET, STP, LDP = 0xD503201F, 0xD65F03C0, 0xA9BF7BFD, 0xA8C17BFD
MOV_X1_X19, MOV_X0_X19, AND_W2_W0_1 = 0xAA1303E1, 0xAA1303E0, 0x12000002
W = lambda *ws: struct.pack('<%dI' % len(ws), *ws)


def labels_for(old, k):
    """Language k: (4:3, 2.39:1, 65:24) labels from its own stock 1:1 and 16:9 labels, and the stock characters."""
    t = struct.unpack_from('<Q', old, TABLE_DIR + 8 * k)[0] - BASE
    b = struct.unpack_from('<Q', old, BLOB_DIR + 8 * k)[0] - BASE
    offs = struct.unpack_from(f'<{STOCK_IDS + 1}i', old, t)
    get = lambda i: old[b + offs[i]:b + offs[i + 1]].decode('utf-16le')   # noqa: E731
    one, wide = get(LABEL_11), get(LABEL_169)
    i = one.index('1:1'); j = one.index('24', i + 3)
    l43 = one[:i] + '4:3' + one[i + 3:j] + '32' + one[j + 2:]
    i = wide.index('16:9'); j = wide.index('20', i + 4)
    l239 = wide[:i] + '2.39:1' + wide[i + 4:j] + '15' + wide[j + 2:]
    l6524 = wide[:i] + '65:24' + wide[i + 4:j] + '13' + wide[j + 2:]
    return (l43, l239, l6524), offs, b, set(''.join(get(n) for n in range(STOCK_IDS)))


def drop(img, prefix):
    hit = [e for e in img.edits if e['purpose'].startswith(prefix)]
    assert len(hit) == 1, (prefix, len(hit))
    e = hit[0]; img.new[e['offset']:e['end']] = e['old']; img.edits.remove(e)
    return dict(offset=hex(e['offset']), bytes=e['end'] - e['offset'], purpose=e['purpose'], replaced_words=e['new'].hex())


class Area:
    def __init__(self, at, limit): self.at, self.limit, self.used = at, limit, 0
    def take(self, n, align=16):
        self.used = (self.used + align - 1) // align * align; va = self.at + self.used; self.used += n
        assert self.at + self.used <= self.limit, 'A12 menu region overflow'; return va


def apply(img, eg, at=0x40B80000, limit=0x40B84000, icons=None):
    icons = {3: 0xFFFF, 6: 0xFFFF, **(icons or {})}
    eg = bytes(eg); cur = bytes(img.new); det = dict(region=[hex(at), hex(limit)])
    # page record (stock values; the record itself is not edited by A2..A2h)
    rec = eg[PAGE_REC:PAGE_REC + 0x50]
    assert struct.unpack_from('<4Q', rec, 0) == (0x80001008, 0x43DD2938, STOCK_ROWS, STOCK_EVPTR), 'page 1068 record'
    assert struct.unpack_from('<H', rec, 0x20)[0] == 5 and cur[PAGE_REC:PAGE_REC + 0x50] == rec
    # 1. strings
    # 2. rows: rows 0..4 as composed so far (row 2 = A2 label/flags + A2g icon), row 2 label -> 3137, rows 5/6 from row 4
    o = STOCK_ROWS - BASE
    rows = [list(struct.unpack_from('<11I', cur, o + ROW_BYTES * r)) for r in range(5)]
    stock_rows = [list(struct.unpack_from('<11I', eg, o + ROW_BYTES * r)) for r in range(5)]
    assert [r[6] for r in rows] == [ITEM_FX, ITEM_DX, ITEM_43, ITEM_11, ITEM_169]
    assert rows[2][0] == LABEL_784 and rows[2][4] == 0x101001, ('row 2 not as A2 left it', [hex(x) for x in rows[2]])
    assert rows[4] == stock_rows[4] and rows[4][0] == LABEL_169 and rows[4][4] == 0x101001
    rows[2][0] = ID_43
    for value, label in ((3, ID_239), (6, ID_6524)):
        r = list(rows[4]); r[0] = label; r[5] = icons[value]; r[4] = 0x101001 if icons[value] != 0xFFFF else 0x101000
        r[6] = ITEM_239 if value == 3 else ITEM_6524; rows.append(r)
    area = Area(at, limit)
    rows_va = area.take(ROW_BYTES * 7)
    # 3. event tables
    ev = []
    p = EV16_9 - BASE
    for j in range(64):
        e = struct.unpack_from('<4Q', eg, p + 32 * j); ev.append(e)
        if e[0] == 0x3BB: break
    assert ev[-1][0] == 0x3BB and len(ev) == 18
    assert {e[0]: e[1] for e in ev if e[0] in OK_EVENTS} == {k: OK_16_9 for k in OK_EVENTS}
    ok_caves, ev_tables = {}, {}
    for value in (3, 6):
        ok = area.take(16)
        words = W(movz(0, MENU_ITEM & 0xFFFF), movk16(0, MENU_ITEM >> 16), movz(1, value), br(ok + 12, SETTER))
        assert text(words, ok) == ['mov w0, #0x603', 'movk w0, #0x700, lsl #16', f'mov w1, #{value}', f'b #{SETTER:#x}']
        stock_ok = eg[OK_16_9 - BASE:OK_16_9 - BASE + 16]
        assert text(stock_ok, OK_16_9)[:2] == text(words, ok)[:2] and text(stock_ok, OK_16_9)[3] == f'b #{SETTER:#x}'
        img.put(ok, words, f'A12 OK cave: choose image area row value {value} (as stock 0x405E6A10 with w1 = {value})', expect_zero=True)
        ok_caves[value] = ok
        tab = b''.join(struct.pack('<4Q', e[0], ok if e[0] in OK_EVENTS else e[1], e[2], e[3]) for e in ev)
        tv = area.take(len(tab)); ev_tables[value] = tv
        img.put(tv, tab, f'A12 event table of the value-{value} row: 16:9 row table 0x43E30FE0 with OK 0x286/0x28B/0x2AE -> {ok:#x}',
                expect_zero=True)
    evptr_va = area.take(8 * 7, align=8)
    stock_ptrs = list(struct.unpack_from('<5Q', eg, STOCK_EVPTR - BASE))
    assert stock_ptrs[4] == EV16_9
    ptrs = stock_ptrs + [ev_tables[3], ev_tables[6]]
    img.put(rows_va, b''.join(W(*r) for r in rows), 'A12 page 1068 row table (7 rows): FX, DX, 4:3 (3137), 1:1, 16:9, '
            f'2.39:1 (3138, item {ITEM_239:#x}), 65:24 (3139, item {ITEM_6524:#x})', expect_zero=True)
    img.put(evptr_va, struct.pack('<7Q', *ptrs), 'A12 page 1068 per-row event-table pointers (rows 0..4 stock, rows 5/6 new)',
            expect_zero=True)
    img.put(PAGE_REC + 0x10, struct.pack('<2Q', rows_va, evptr_va), 'page 1068 record +0x10/+0x18: row table and event pointers -> A12 copies',
            expect=struct.pack('<2Q', STOCK_ROWS, STOCK_EVPTR), offset=True)
    img.put(PAGE_REC + 0x20, struct.pack('<H', 7), 'page 1068 record +0x20 row count 5 -> 7', expect=struct.pack('<H', 5), offset=True)
    det['rows'] = [dict(row=i, value=v, item=hex(rows[i][6]), label=hex(rows[i][0]), flags=hex(rows[i][4]), icon=hex(rows[i][5]))
                   for i, (v, _) in enumerate(ROWS)]
    det['row_table'], det['event_pointers'] = hex(rows_va), hex(evptr_va)
    det['ok_caves'] = {str(k): hex(v) for k, v in ok_caves.items()}; det['event_tables'] = {str(k): hex(v) for k, v in ev_tables.items()}
    det['icons_placeholder'] = {str(k): icons[k] == 0xFFFF for k in (3, 6)}
    det['stock_row_table_unreferenced'] = dict(va=hex(STOCK_ROWS), note='A2 row-2 label/flags and A2g row-2 icon edits stay in place')
    # 4. entry callback: cursor by value (drop A2's 20 words, redo with 3 and 6)
    det['entry_dropped'] = drop(img, 'choose-image-area entry 0x405DBE0C')
    stock_entry = eg[ENTRY_SITE - BASE:ENTRY_SITE - BASE + 4 * ENTRY_WORDS]
    assert text(stock_entry, ENTRY_SITE)[:2] == ['cmp w0, #8', 'b.eq #0x405dbe44'] and text(stock_entry, ENTRY_SITE)[-1] == 'bl #0x403b1ed0'
    words = [movz(20, ITEM_FX)]
    for value, item in ((1, ITEM_DX), (2, ITEM_43), (4, ITEM_169), (8, ITEM_11), (3, ITEM_239), (6, ITEM_6524)):
        words += [cmpw0(value), movz(8, item), CSEL_W20_W8_EQ]
    words += [NOP] * (ENTRY_WORDS - len(words))
    code = W(*words)
    want = [f'mov w20, #{ITEM_FX:#x}'] + sum([[f'cmp w0, #{v}', f'mov w8, #{it:#x}', 'csel w20, w8, w20, eq'] for v, it in
                                               ((1, ITEM_DX), (2, ITEM_43), (4, ITEM_169), (8, ITEM_11), (3, ITEM_239), (6, ITEM_6524))], []) + ['nop']
    assert text(code, ENTRY_SITE) == want, text(code, ENTRY_SITE)
    img.put(ENTRY_SITE, code, 'choose-image-area entry 0x405DBE0C (A12): cursor by value 1/2/4/8/3/6, default FX; stock hide of 0x2be9 '
            'removed (as A2)', expect=stock_entry)
    det['entry'] = dict(site=hex(ENTRY_SITE), words=len(words), code=want)
    # 5. grey: 16:9 call -> cave
    assert text(eg[GREY_SITE - BASE:GREY_SITE - BASE + 4], GREY_SITE) == [f'bl #{GREY_SET:#x}']
    assert cur[GREY_SITE - BASE:GREY_SITE - BASE + 4] == eg[GREY_SITE - BASE:GREY_SITE - BASE + 4]
    assert text(eg[0x405DBD0C - BASE:0x405DBD28 - BASE], 0x405DBD0C) == ['mov w0, #0x1b', 'mov x1, x19', f'bl #{RESTRICT:#x}',
                                                                        'and w2, w0, #1', 'mov w1, #0x2c5f', 'mov x0, x19', f'bl #{GREY_SET:#x}']
    cv = area.take(4 * 25)
    g = [STP, br(cv + 4, GREY_SET, True)]
    for item in (ITEM_43, ITEM_239, ITEM_6524):
        s = cv + 4 * len(g)
        g += [movz(0, GREY_CODE), MOV_X1_X19, br(s + 8, RESTRICT, True), AND_W2_W0_1, movz(1, item), MOV_X0_X19, br(s + 24, GREY_SET, True)]
    g += [LDP, RET]
    assert len(g) == 25
    gtext = text(W(*g), cv)
    assert gtext == ['stp x29, x30, [sp, #-0x10]!', f'bl #{GREY_SET:#x}'] + sum(
        [['mov w0, #0x1a', 'mov x1, x19', f'bl #{RESTRICT:#x}', 'and w2, w0, #1', f'mov w1, #{it:#x}', 'mov x0, x19', f'bl #{GREY_SET:#x}']
         for it in (ITEM_43, ITEM_239, ITEM_6524)], []) + ['ldp x29, x30, [sp], #0x10', 'ret'], gtext
    img.put(cv, W(*g), 'A12 cave_grey: stock 16:9 grey call, then rows 0x2be9 / 0x2c35 / 0x2c37 greyed by restriction code 0x1a (as 1:1)',
            expect_zero=True)
    img.put(GREY_SITE, W(br(GREY_SITE, cv, True)), f'page 1068 callback 0x405DBCD0: 16:9 grey call bl 0x403b1a5c -> bl cave_grey {cv:#x}',
            expect=eg[GREY_SITE - BASE:GREY_SITE - BASE + 4])
    det['grey'] = dict(site=hex(GREY_SITE), cave=hex(cv), code=gtext, code_rule='0x1a: photo and release mode 3 (C30) or 6 (C15)')
    det['region_used'] = [hex(at), hex(at + area.used)]
    return det
