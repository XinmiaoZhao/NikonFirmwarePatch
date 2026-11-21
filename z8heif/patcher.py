"""Build the reviewed SDR HEIF menu, still-capture and playback edits on factory C3.11."""
import struct
from . import drive_policy
from z8patch.image import BASE, Image, branch, data_off, va
from z8prores.package import require

GROUP_ID = 198
CODE_AT, CODE_LIMIT = 0x40B70000, 0x40B718D0
W = lambda w: struct.pack('<I', w)
MOVZ = lambda rd, imm: struct.pack('<I', 0xD2800000 | imm << 5 | rd)
SITES = {
    0x403A036C: (W(0xA9BC63F9), 'f5_unavailable', False, 'HEIF: HDR and multiple exposure unavailable; other condition sets retain original evaluation'),
    0x403EC39C: (branch(0x403EC39C, 0x410D61D0), 'f5_set', False, 'reject unsafe mode enables via the stock setting thunk while SDR HEIF is selected'),
    0x406EA878: (W(0x39001688), 'f5_format59', True, '0059 offset 5 retains the format flag independently of SDR tone byte'),
    0x40CCF440: (branch(0x40CCF440, 0x40CD343C, link=True), 'f5_colr', True, 'Adobe RGB colr uses the factory Nikon ICC'),
    0x40EC8D24: (W(0xB902FE68), 'f2_snap', True, 'snapshot M+0x2fc store (str w8,[x19,#0x2fc]) -> bl f2_snap (F6: time-lapse frames excluded)'),
    0x40C98DD4: (MOVZ(1, 0xDD90), 'f2_tmpl', False, 'encoder template (2,1): mov x1,#0xdd90 -> b f2_tmpl'),
    0x40CCF368: (None, 'f2_nclx', True, 'HEIF item builder nclx call (bl 0x40C977A0) -> bl f2_nclx'),
    0x406EA85C: (W(0xB942FD08), 'f2_l59', True, 'MakerNote 0x0059 writer (ldr w8,[x8,#0x2fc]) -> bl f2_l59'),
    0x406E8988: (W(0xB942FD29), 'f2_cs1e', False, 'MakerNote 0x001e writer (ldr w9,[x9,#0x2fc]) -> b f2_cs1e'),
    0x406E5F1C: (W(0xB942FD29), 'f2_exif', False, 'Exif ColorSpace writer (ldr w9,[x9,#0x2fc]) -> b f2_exif'),
    0x40CB9D8C: (MOVZ(8, 0x5B14), 'f7_rec', False, 'conversion-record copy 0x40CB9D8C (mov x8,#0x5b14) -> b f7_rec: SDR HEIF modes 3/4 -> record 0 (BT.601)'),
    0x40EA7ED0: (branch(0x40EA7ED0, 0x410539B8, link=True), 'f6_dev', True, 'capture develop call (bl 0x410539B8) -> bl f6_dev: curve family 0 for SDR HEIF'),
    0x405D9B08: (W(0x910023E0), 'f6_tone_text', True, 'photo menu Tone mode value (add x0,sp,#0x8) -> bl f6_tone_text: SDR-J / SDR-H'),
    0x403D950C: (branch(0x403D950C, 0x403EB6A8, link=True), 'f7_key', True, 'control builder event-key lookup (bl 0x403EB6A8) -> bl f7_key: string 3140 -> key 7CBh'),
    0x40CD3E84: (branch(0x40CD3E84, 0x40CD3A60, link=True), 'f7_ipma', True, 'ipma box writer call (bl 0x40CD3A60) -> bl f7_ipma: tiles, grid, rest'),
    0x40ED04A8: (branch(0x40ED04A8, 0x40ED4880, link=True), 'f8_ftype', True, 'movie file-type selector call in 40ED0310 -> bl f8_ftype: interval and time-lapse movies HLG family with SDR HEIF'),
    0x40ED1590: (branch(0x40ED1590, 0x40ED4880, link=True), 'f8_ftype', True, 'movie file-type selector call in 40ED0E70 -> bl f8_ftype: interval and time-lapse movies HLG family with SDR HEIF'),
    0x40722F9C: (W(0xB941EFE8), 'f7_m2tone', True, 'movie service 40722ED0 mode 2 tone load (ldr w8,[sp,#0x1ec]) -> bl f7_m2tone: file type'),
    0x40723198: (W(0xB941EFE8), 'f7_m2tone', True, 'movie service 40722ED0 mode 2 tone load (ldr w8,[sp,#0x1ec]) -> bl f7_m2tone'),
    0x407232E8: (W(0xB941EFE8), 'f7_m2tone', True, 'movie service 40722ED0 mode 2 tone load (ldr w8,[sp,#0x1ec]) -> bl f7_m2tone'),
    0x40722FC0: (W(0xB941EFE8), 'f7_m2tone', True, 'movie service 40722ED0 mode 1 (time-lapse) tone load -> bl f7_m2tone: file type'),
    0x407231B8: (W(0xB941EFE8), 'f7_m2tone', True, 'movie service 40722ED0 mode 1 (time-lapse) tone load -> bl f7_m2tone'),
    0x407232B4: (W(0xB941EFE8), 'f7_m2tone', True, 'movie service 40722ED0 mode 1 (time-lapse) tone load -> bl f7_m2tone'),
    0x40723528: (W(0xB9400108), 'f8_depth', True, 'movie service 40722ED0 cached 10-bit setting (ldr w8,[x8]) -> bl f8_depth: out+0x2C 10-bit for file type 3 with SDR HEIF'),
    0x40CCFBB8: (branch(0x40CCFBB8, 0x40CD44C4, link=True), 'f8_thmb', True, 'HEIF item builder: iref thmb of 8194 (bl 0x40CD44C4) -> bl f8_thmb: SDR HEIF Adobe RGB: no thmb, item hidden (V4)'),
    0x40CCE6E0: (MOVZ(22, 0xD70D), 'f7_small', True, 'HEIF header parser after the thmb loop (mov x22,#0xd70d) -> bl f7_small: empty small slot <- item 8194 if small'),
    0x40EAD6E0: (W(0x1A9F0728), 'f8_mvmode', True, 'interval movie request builder 40EAD4B0 frame mode (csinc w8,w25,wzr,eq) -> bl f8_mvmode: SDR HEIF frames mode 1 (601->709)'),
    0x40EAD184: (W(0x1A9F0728), 'f8_mvmode', True, 'time-lapse movie request builder 40EACFC8 frame mode (csinc w8,w25,wzr,eq) -> bl f8_mvmode: SDR HEIF frames mode 1 (601->709)'),
    0x407C66D4: (W(0x320007E8), 'f8_pbcs_x20', True, 'playback request colour, HEIF kinds 5/7 (orr w8,wzr,#3) -> bl f8_pbcs_x20: Adobe RGB file record -> 1'),
    0x407C8640: (W(0x320007E8), 'f8_pbcs_x20', True, 'playback request colour, HEIF kinds 5/7 (orr w8,wzr,#3) -> bl f8_pbcs_x20: Adobe RGB file record -> 1'),
    0x407C93C8: (W(0x320007E8), 'f8_pbcs_x26', True, 'playback request colour, HEIF kinds 5/7 (orr w8,wzr,#3) -> bl f8_pbcs_x26: Adobe RGB file record -> 1'),
    0x40388508: (MOVZ(8, 0x1C58), 'f7_group', False, 'button group getter 0x40388508 (mov x8,#0x1c58) -> b f7_group: group 198 = [3140, ABDh]'),
}
EXTRA_SITES = {
    0x410162C4: (W(0xA94023EA), 'f5_bank', False, 'per-item bank copy 410161F0, type 3/7/9 case (ldp x10,x8,[sp]) -> b f5_bank'),
    0x41016940: (W(0xB9400028), 'f5_rbank', False, 'per-item bank reset 41016888, type-9 case (ldr w8,[x1]) -> b f5_rbank'),
    0x41016804: (W(0xB9400029), 'f5_rcur', False, 'per-item current reset 41016760, type-9 case (ldr w9,[x1]) -> b f5_rcur'),
}
# F5 sites that F6 returns to the factory words (checked to be untouched in the package): f5_gamma, f5_tone, f5_nlg, f2_gain, f5_flag
GET_CALL = 0x403EC398
# `bl 0x403EC398` (settings get) whose result (070006A5h, or the derived 040021E7h in the last two) only chooses JPEG or HEIF
# wording; each is checked in the raw payload as a bl to GET_CALL.  Static classification of all 59 readers of 070006A5h:
# tone_readers/README.md.  Every other reader (HLG-only displays, availability tests, PTP, the tone page itself) keeps the real value.
NAME_SITES = {
    0x404CD24C: 'image-size icon 404CD220: JPEG L/M/S 91Bh/91Ch/91Dh or HEIF 1566h/1567h/1568h (id read at 404CD244)',
    0x404F49E0: 'slot badge 404F5678, first read: 9F5h JPEG or 156Bh HEIF (id built at 404F59B4)',
    0x404F4AEC: 'slot badge 404F5678, second read: same two badges',
    0x405D9998: 'photo menu refresh 405D9808, secondary slot value 3: icon 145Bh JPEG+JPEG or 1578h HEIF+HEIF (control 2CFDh)',
    0x405D99B0: 'photo menu refresh 405D9808, secondary slot value 2: icon D30h RAW+JPEG or 1579h RAW+HEIF (control 2CFDh)',
    0x405DAA58: 'secondary slot function page 405DAA40: labels 15Eh/867h, 88Fh/868h and icons D30h/1579h, 145Bh/1578h',
    0x405E5E98: '2ry slot image size page 405E5C78: title 866h (JPEG basic) or 869h (HEIF basic)',
    0x4061323C: 'help screen 406131C0, help A12h -> A06h (RAW+HEIF)',
    0x4061325C: 'help screen 406131C0, help A05h -> A07h (HEIF+HEIF)',
    0x404CD90C: 'small slot badge 404CD8C4: 156Ah HEIF or 9D3h JPEG; reads the derived setting 040021E7h (built at 404CD904), 0 in SDR',
    0x404CDA34: 'small slot badge 404CD9EC: same choice, same derived setting (built at 404CDA2C)',
    # F7: the interval movie page and its frame-size page (f7_20261119/check_f7_static.py interval_menu_tone_reads): with SDR
    # HEIF they show the HLG family (H.265 10-bit only, HLG frame sizes) as the HLG tone does.
    0x405E20FC: 'interval movie page: file type source (040006AEh vs 06000559h)',
    0x405E2134: 'interval movie page: icon 128Ch H.265 10-bit',
    0x405E21BC: 'interval movie page: frame size source',
    0x405E2348: 'interval frame-size page: file type source',
    0x405E23B0: 'interval frame-size page: title 7A5h "H.265 10-bit (MOV)"',
    0x405E2408: 'interval frame-size page: frame-size ids',
    0x405E24E0: 'interval frame-size page: hide the rows of the other tone',
    0x405F8F1C: 'interval frame-size select action: table',
    0x405F8F60: 'interval frame-size select action: file type id',
    0x4061327C: 'help 9DFh -> A0Ah "H.265 10-bit"',
    # F8: the photo-menu time-lapse movie page, its frame-size page and select action (tone_readers sites 19, 20, 25): with SDR
    # HEIF they show the HLG family (040006AFh, H.265 10-bit only, HLG frame sizes) as the HLG tone does.
    0x405E3C54: 'time-lapse frame-size page 405E3C10: file type source (040006AFh vs 0600055Ch)',
    0x405E3CB8: 'time-lapse frame-size page: title node 5DBh = 7A5h "H.265 10-bit (MOV)"',
    0x405E3D10: 'time-lapse frame-size page: frame-size ids',
    0x405E3D50: 'time-lapse frame-size page: rows of the tone',
    0x405E3F90: 'time-lapse movie page 405E3ED0: file type source',
    0x405E3FC8: 'time-lapse movie page: icon 128Ch H.265 10-bit (control 2D5Fh)',
    0x405E4044: 'time-lapse movie page: frame size source',
    0x405F9090: 'time-lapse frame-size select action 405F903C: table',
    0x405F90D4: 'time-lapse frame-size select action: file type id (040006AFh)',
}
TMPL_BACK, NCLX_THUNK, NCLX = 0x40C98E10, 0x40C977A0, 0x40C99508
T8, T10 = 0x41F1DD18, 0x41F1DD90
SDR_TRIPLE = (1, 13, 6)
STATES, STATE_SIZE = 0x4BFFCC0, 0x60
TONE_STATE, SUB_STATE, NRAW_STATE = 0x2B, 0xAB, 0x10D
SUB_STOCK = (0xa028e7f98, 0xa028cf220)            # ABh's stock callbacks and page record (checked as in HB1)
TONE_PAGE = 0xA028CCA20                            # init data
TONE_CALLBACKS = (0x405DB130, 0x405DB2BC, 0x403B2210, 0x405DB2C0, 0)
SDR_ITEM, HLG_ITEM, SDR_LABEL, HLG_LABEL = 0x2D7A, 0x2D7B, 0x709, 0x70B
ARROW_STYLE, ARROW_WORD5 = 0x2010100D, 0         # stock file-type arrow rows (page 10Ah rows 0..5)
RIGHT, OK, ARROW_TAP, TAP = 0x286, 0x28B, 0x29F, 0x2AE
MOVES, TOUCH, MOVE_ACTION, TOUCH_ACTION = (0x283, 0x284, 0x29D, 0x29E), 0x303, 0x405DB2E4, 0x405DB360
GO, ARROW_GUARD = 0x403B1BA8, 0x403B1C64          # the file-type arrow rows: RIGHT (GO, no guard), ARROW_TAP (GO, guard)
SDR_ACTION, HLG_ACTION = 0x405E6A20, 0x405E6A30
NRAW_LAYOUT, NRAW_ROW, NRAW_EVENTS, NRAW_EVENT_COUNT, NRAW_PAGE = 0x3AA81D0, 0x3AA82E0, 0x3AE69B0, 14, 0x4BCC760
NRAW_CALLBACKS_TAIL = (0x4056C954, 0x403B2210, 0x4056C958, 0x4056C960)
NRAW_OK, OK_EVENTS, NRAW_LABEL = 0x4056C964, (0x286, 0x28B, 0x2AE), 0x8A6
JPEG_ITEM, HEIF_ITEM = 0x2DDE, 0x2DE1
STOCK_IDS, LANGUAGES = 3136, 36
JPEG_ID, HEIF_ID = 3234, 3235
TITLE_ID, FOOTER_ID = 3236, 3237
TONE_BUTTON_ID, GLYPH = 0x7CB, ''            # factory "<multi-selector glyph> Tone mode" button string
OPTIONS = ('JPEG', 'HEIF', 'SDR file format', 'File format')
# Tone page geometry (x | y << 16).  Factory tone page: help panel 6Ch/6Dh y 290..480, text 6Eh y 296..474, list bottom 288.
# F6: the same panel height moved up 56 px so it ends at 424 like the factory file-type page (footer band 426..480).
PANEL = (76 | 234 << 16, 720 | 424 << 16)
# F7 footer: both groups keep the factory rectangle (542,432)-(710,472) of the file-type page
OK_RECT = (542 | 432 << 16, 710 | 472 << 16)
HELP_TEXT = (98 | 240 << 16, 698 | 418 << 16)
LIST_BOTTOM = 232



def template(eg):
    t8, t10 = eg[T8 - BASE:T8 - BASE + 0x78], eg[T10 - BASE:T10 - BASE + 0x78]
    assert tuple(t10[0x38:0x3B]) == (9, 18, 9) and tuple(t8[0x38:0x3B]) == SDR_TRIPLE, 'stock VUI triples'
    assert (t10[0x24], t10[0x29], t10[0x2A], t10[0x2B], t10[0x2C]) == (1, 1, 5, 1, 1), 'stock VUI flags'
    return t10[:0x38] + bytes(SDR_TRIPLE) + t10[0x3B:]

def strings(old, context):
    translations = []
    for k in range(LANGUAGES):
        table = struct.unpack_from('<Q',old,0x311C5A0 + 8*k)[0] - BASE
        blob = struct.unpack_from('<Q',old,0x387AF58 + 8*k)[0] - BASE
        offs = list(struct.unpack_from(f'<{STOCK_IDS + 1}i', old, table))
        stock = lambda i: old[blob + offs[i]:blob + offs[i + 1]].decode('utf-16le')
        chars = set(''.join(stock(i) for i in range(STOCK_IDS)))
        button = stock(TONE_BUTTON_ID)
        g = button.index(GLYPH)
        prefix = button[:g + 1]                                   # glyph (after an RLM in Arabic), as the factory button
        assert prefix in (GLYPH, '‏' + GLYPH), (k, button)
        if k == 8:
            footer = prefix + '文件格式'
        elif k == 9:
            footer = prefix + '檔案格式'
        else:
            footer = prefix + ' File format'
        title = 'SDR文件格式' if k == 8 else 'SDR檔案格式' if k == 9 else 'SDR file format'
        options = ('JPEG', 'HEIF', title, footer)
        for s in options:
            assert set(s) <= chars, ('option characters missing', k, s)
        translations.append(list(options))
    require(context.add('sdr-heif', translations) == [JPEG_ID, HEIF_ID, TITLE_ID, FOOTER_ID], 'HEIF label allocation')

def table_copy(eg, ptr, change, limit=64):
    """Copy a transition table (32-byte records up to and including event 3BBh); change(e,a,g,t) edits one record."""
    out = bytearray()
    o = data_off(ptr)
    for i in range(limit):
        rec = struct.unpack_from('<4Q', eg, o + 32 * i)
        out += struct.pack('<4Q', *change(*rec))
        if rec[0] == 0x3BB:
            return bytes(out)
    raise AssertionError('no 3BBh record')

def menu(img, labels, at):
    """Tone mode page 2Bh (arrow SDR row, value refresh, footer button, help box, move/303h actions) and the JPEG / HEIF
    sub-page in SUB_STATE.  Data placed from `at`."""
    eg = img.old
    start, blob = at, {}

    def place(name, data, align=8):
        nonlocal at
        at = (at + align - 1) & ~(align - 1)
        blob[name] = (at, bytes(data))
        at += len(data)
        return blob[name][0]

    st = lambda n: struct.unpack_from('<12Q', eg, STATES + STATE_SIZE * n)
    # -- 2Bh: rows, transitions, callbacks
    tone = st(TONE_STATE)
    assert tone[10] == TONE_PAGE, hex(tone[10])
    tone_cb = struct.unpack_from('<5Q', eg, data_off(tone[5]))
    assert tone_cb == TONE_CALLBACKS, [hex(x) for x in tone_cb]
    page = eg[data_off(TONE_PAGE):data_off(TONE_PAGE) + 0x50]
    rows_va, ptrs_va = struct.unpack_from('<QQ', page, 0x10)
    assert struct.unpack_from('<H', page, 0x20)[0] == 2
    assert struct.unpack_from('<HHHH', page, 0x28) == (0x120, 0x4C, 0x3A, 0x2C4) and struct.unpack_from('<Q', page, 0x30)[0] == 0x120
    sdr = list(struct.unpack_from('<11I', eg, data_off(rows_va)))
    hlg = struct.unpack_from('<11I', eg, data_off(rows_va) + 44)
    assert sdr == [SDR_LABEL, 0xFFFF, 0xFFFF, 0, 0x101000, 0xFFFF, SDR_ITEM, 0x20002, 0xFFFFFFFF, 0xFFFFFFFF, 2], sdr
    assert hlg == (HLG_LABEL, 0xFFFF, 0xFFFF, 0, 0x101000, 0xFFFF, HLG_ITEM, 0x20002, 0xFFFFFFFF, 0xFFFFFFFF, 2), hlg
    arrow_row = struct.unpack_from('<11I', eg, 0x43C06A80 - BASE)
    assert arrow_row[4:6] == (ARROW_STYLE, ARROW_WORD5) and arrow_row[7] == 0x40004
    # Word 7 selects the child geometry via 40695E60; tone's geometry 2 has
    # no value/arrow children. Stock file-type geometry 4 has both.
    sdr[4], sdr[5], sdr[7] = ARROW_STYLE, ARROW_WORD5, arrow_row[7]
    sdr_ptr, hlg_ptr = struct.unpack_from('<QQ', eg, data_off(ptrs_va))
    seen = {}

    def moves(e, a, g, t):
        if e in MOVES:
            assert a == MOVE_ACTION and t == 0x68C, (hex(e), hex(a))
            seen[e] = seen.get(e, 0) + 1
            return e, labels['f6_move'], g, t
        if e == TOUCH:
            assert (a, g, t) == (TOUCH_ACTION, 0, 0x68C), (hex(a), hex(g), hex(t))
            seen[e] = seen.get(e, 0) + 1
            return e, labels['f6_touch'], g, t
        return e, a, g, t

    def arrow(e, a, g, t):
        if e == RIGHT:
            assert (a, g, t) == (SDR_ACTION, 0, 0x68D), (hex(a), hex(g), hex(t))
            seen[e] = seen.get(e, 0) + 1
            return e, GO, 0, SUB_STATE
        if e == ARROW_TAP:
            assert (a, t) == (0, 0x68C), (hex(a), hex(t))
            seen[e] = seen.get(e, 0) + 1
            return e, GO, ARROW_GUARD, SUB_STATE
        if e in (OK, TAP):
            assert (a, t) == (SDR_ACTION, 0x68D)
        return moves(e, a, g, t)

    sdr_table = table_copy(eg, sdr_ptr, arrow)
    hlg_table = table_copy(eg, hlg_ptr, moves)
    assert seen == {RIGHT: 1, ARROW_TAP: 1, **{e: 2 for e in MOVES}, TOUCH: 2}, seen
    rows_at = place('tone_rows', struct.pack('<11I', *sdr) + struct.pack('<11I', *hlg), 4)
    sdr_table_at = place('tone_sdr_table', sdr_table)
    hlg_table_at = place('tone_hlg_table', hlg_table)
    ptrs_at = place('tone_pointers', struct.pack('<QQ', sdr_table_at, hlg_table_at))
    tone_cb_at = place('tone_callbacks', struct.pack('<5Q', *TONE_CALLBACKS[:4], labels['f5_tone_refresh']))
    # Layout: factory tone records 0..4 (help panel 6Ch/6Dh and text 6Eh moved up), the factory file-type footer band 568h,
    # its button group 753h with group 198 (f7_group: "File format" + OK) in place of AFh ("Tone mode" + OK) and its OK group
    # 390h, then the factory tone record 5 (back button) and the terminator.
    stock_tone_layout = eg[0x43DD2B90 - BASE:0x43DD2D6C - BASE]
    stock_file_layout = eg[0x43C067D8 - BASE:0x43C06A80 - BASE]
    tone_layout = bytearray(stock_tone_layout[:5 * 68] + stock_file_layout[5 * 68:8 * 68] + stock_tone_layout[5 * 68:])
    assert len(tone_layout) == 10 * 68
    rec = lambda i: list(struct.unpack_from('<17I', tone_layout, i * 68))
    assert rec(1)[0] == 0x708 and [rec(i)[14] for i in (2, 3, 4, 5, 6, 7, 8)] == [0x6C, 0x6D, 0x6E, 0x568, 0x753, 0x390, 6]
    for i in (2, 3):
        assert rec(i)[6:10] == [76 | 290 << 16, 720 | 480 << 16] * 2
        struct.pack_into('<4I', tone_layout, i * 68 + 24, *PANEL, *PANEL)
    assert rec(4)[6:10] == [98 | 296 << 16, 698 | 474 << 16] * 2
    struct.pack_into('<4I', tone_layout, 4 * 68 + 24, *HELP_TEXT, *HELP_TEXT)
    assert rec(5)[6:8] == [76 | 426 << 16, 720 | 480 << 16]
    assert rec(6)[:4] == [0xAF, 0xB, 2, 2] and rec(7)[:4] == [0xD, 0xB, 2, 2] and rec(6)[6:14] == rec(7)[6:14]
    assert rec(7)[6:10] == [*OK_RECT, *OK_RECT]
    struct.pack_into('<I', tone_layout, 6 * 68, GROUP_ID)
    tone_layout_at = place('tone_layout_with_footer', tone_layout, 4)
    # -- sub-page (copy of the stock N-RAW quality list page, as HB1)
    layout = bytearray(eg[NRAW_LAYOUT:NRAW_LAYOUT + 0x110])
    assert struct.unpack_from('<I', layout, 0x44)[0] == NRAW_LABEL, 'stock layout title'
    struct.pack_into('<I', layout, 0x44, TITLE_ID)
    stock_row = struct.unpack_from('<11I', eg, NRAW_ROW)
    assert stock_row == (0x35E, 0xFFFF, 0xFFFF, 0, 0x101000, 0xFFFF, 0x3119, 0x20002, 0xFFFFFFFF, 0xFFFFFFFF, 2), stock_row
    sub_rows = b''.join(struct.pack('<11I', lab, *stock_row[1:6], item, *stock_row[7:])
                        for lab, item in ((JPEG_ID, JPEG_ITEM), (HEIF_ID, HEIF_ITEM)))
    oks = []

    def ok_change(e, a, g, t):
        if a == NRAW_OK:
            assert t == 0x68D
            oks.append(e)
            return e, labels['f5_sub_ok'], g, 0x68E
        return e, a, g, t

    option_table = table_copy(eg, va(NRAW_EVENTS), ok_change)
    assert len(option_table) == 32 * NRAW_EVENT_COUNT and tuple(oks) == OK_EVENTS, oks
    stock_page = eg[NRAW_PAGE:NRAW_PAGE + 0x50]
    assert struct.unpack_from('<4Q', stock_page)[:3] == (0x80001008, va(NRAW_LAYOUT), va(NRAW_ROW))
    assert struct.unpack_from('<H', stock_page, 0x20)[0] == 2
    layout_at = place('sub_layout', layout)
    sub_rows_at = place('sub_rows', sub_rows, 4)
    tables_at = place('sub_option_tables', option_table * 2)
    sub_ptrs_at = place('sub_option_pointers', struct.pack('<2Q', tables_at, tables_at + len(option_table)))
    sub_cb_at = place('sub_callbacks', struct.pack('<5Q', labels['f5_sub_entry'], *NRAW_CALLBACKS_TAIL))
    sub_page = bytearray(stock_page)
    struct.pack_into('<3Q', sub_page, 8, layout_at, sub_rows_at, sub_ptrs_at)
    struct.pack_into('<H', sub_page, 0x20, 2)
    sub_page_at = place('sub_page', sub_page)
    assert at <= CODE_LIMIT, 'menu data overflow'
    whole = bytearray(at - start)
    for a, d in blob.values():
        whole[a - start:a - start + len(d)] = d
    img.put(start, bytes(whole), 'menu data: Tone mode rows (SDR = arrow row), SDR and HLG transition tables (moves -> f6_move, 303h -> '
            'f6_touch), pointers, 2Bh callbacks, layout (help box above the bottom bar, button group 198 = File format + OK); sub-page layout '
            '(title), 2 rows, 2 option tables (OK -> f5_sub_ok, 68Eh), pointers, callbacks, page record', expect_zero=True)
    # -- state and page records
    tone_rec = STATES + STATE_SIZE * TONE_STATE
    img.put(tone_rec + 0x28, struct.pack('<Q', tone_cb_at), 'state 2Bh: callbacks -> copy with value refresh f5_tone_refresh',
            expect=struct.pack('<Q', tone[5]), offset=True)
    img.put(data_off(TONE_PAGE) + 8, struct.pack('<QQQ', tone_layout_at, rows_at, ptrs_at),
            'Tone mode page record (init data): layout with footer, rows, transition pointers', expect=page[8:32], offset=True)
    img.put(data_off(TONE_PAGE) + 0x28, struct.pack('<HHHHQ', LIST_BOTTOM, 0x4C, 0x3A, 0x2C4, LIST_BOTTOM),
            f'Tone mode page record: list bottom {LIST_BOTTOM} (help panel top - 2, as the factory file-type page)',
            expect=page[0x28:0x38], offset=True)
    img.put(data_off(TONE_PAGE) + 0x40, struct.pack('<QQ', 0x43ED15F8, 2), 'Tone mode: factory secondary-action touch rectangles',
            expect=page[0x40:0x50], offset=True)
    sub = st(SUB_STATE)
    nraw = st(NRAW_STATE)
    assert sub[0] == (SUB_STATE << 16) | 2 and sub[1] == nraw[1] and (sub[5], sub[10]) == SUB_STOCK and not any(sub[2:5] + sub[6:10] + sub[11:]), sub
    rec = STATES + STATE_SIZE * SUB_STATE
    img.put(rec + 0x28, struct.pack('<Q', sub_cb_at), f'state {SUB_STATE:#x}: callbacks -> JPEG / HEIF sub-page',
            expect=struct.pack('<Q', SUB_STOCK[0]), offset=True)
    img.put(rec + 0x50, struct.pack('<Q', sub_page_at), f'state {SUB_STATE:#x}: page record -> JPEG / HEIF sub-page',
            expect=struct.pack('<Q', SUB_STOCK[1]), offset=True)
    return at, dict({k: hex(v[0]) for k, v in blob.items()}, end=hex(at), sub_state=hex(SUB_STATE), tone_state=hex(TONE_STATE),
                    items=dict(jpeg=hex(JPEG_ITEM), heif=hex(HEIF_ITEM)), sdr_row=[hex(x) for x in sdr],
                    stock_sdr_table=hex(sdr_ptr), stock_hlg_table=hex(hlg_ptr), panel=[hex(x) for x in PANEL],
                    help_text=[hex(x) for x in HELP_TEXT], list_bottom=LIST_BOTTOM,
                    footer=dict(group_753=GROUP_ID, group_390=0xD, rect=[hex(x) for x in OK_RECT]))

PLAYBACK = [
    (0x4063d468, '68f65eb9', '68fa5eb9', 'playback HLG decision reads the tone class +0x1EF8 (0059 +4) instead of the format class +0x1EF4'),
    (0x4063d4e4, '08f45eb9', '08f85eb9', 'playback HLG decision reads the tone class +0x1EF8 (0059 +4) instead of the format class +0x1EF4'),
    (0x4063f5f8, '08f45eb9', '08f85eb9', 'playback HLG decision reads the tone class +0x1EF8 (0059 +4) instead of the format class +0x1EF4'),
    (0x40cd4974, 'e00313aa883a00b9d3040094802600f9e00313aae10314aaa4eeff97804200b9', '883a00b9692a40a96b0a40f929010b8b892600f94b010bcb8b4200b96a0a00f9', 'HEIF colr parser 40CD48A0'),
]

def build_main(stock, context, unit):
    img = Image(stock)
    raw, entries = unit('heif-format')
    code = bytearray(raw)
    drive_code, drive_entries = unit('heif-drive')
    drive_policy.redirect(code, drive_entries)
    img.put(drive_policy.AT, drive_code, 'SDR JPEG fallback for high-speed frame capture', expect_zero=True)
    icc,icc_entries=unit('heif-icc')
    from hashlib import sha256
    require(sha256(stock[0x440CA638-BASE:0x440CA638-BASE+492]).hexdigest() ==
            'bafcac914b3117df458dcb1e9d86cd36454b78172707509b3ebe5cee8c9f4556', 'Unexpected Nikon Adobe RGB profile')
    img.put(0x40B71D00,icc,'JPEG ICC header writer',expect_zero=True)
    img.put(0x406C367C,branch(0x406C367C,icc_entries['jpeg_profile']),'SDR Adobe RGB JPEG embeds Nikon ICC',
            expect=bytes.fromhex('610b40b9'))
    tmpl = template(stock)
    for name, value in [('f2_template', tmpl), ('f5_adobe_template', tmpl[:0x38]+bytes((2,2,6))+tmpl[0x3B:])]:
        start = entries[name]-CODE_AT
        require(code[start:start+len(value)] == bytes(len(value)), 'HEIF template preimage')
        code[start:start+len(value)] = value
    img.put(CODE_AT, bytes(code), 'HEIF capture, conversion, playback and UI code', expect_zero=True)
    for site, (expected, name, link, purpose) in {**SITES, **EXTRA_SITES}.items():
        if expected is None:
            expected = branch(site,NCLX_THUNK,link=True)
        img.put(site,branch(site,entries[name],link=link),purpose,expect=expected)
    for site, purpose in NAME_SITES.items():
        img.put(site,branch(site,entries['f5_name_get'],link=True),purpose,expect=branch(site,GET_CALL,link=True))
    for site, before, after, purpose in PLAYBACK:
        img.put(site,bytes.fromhex(after),purpose,expect=bytes.fromhex(before))
    strings(stock, context)
    end, detail = menu(img, entries, (CODE_AT+len(code)+15) & ~15)
    require(end <= 0x40B718D0, 'HEIF menu outside its allocation')
    for name, start in [('heif-capture',0x40B718D0),('heif-srgb',0x40B71950)]:
        code, labels = unit(name)
        img.put(start,code,name,expect_zero=True)
        entries.update(labels)
    for site, name, before in (
        (0x40ED0D7C,'f9_movie_info','69b20529'),(0x406C2300,'f9_capture_colour','2101881a'),
        (0x40EC8D28,'srgb_shutter','e97b00b9'),(0x406C2304,'srgb_register',branch(0x406C2304,0x406BC450,link=True).hex())):
        img.put(site,branch(site,entries[name],link=True),name,expect=bytes.fromhex(before))
    return img, detail
