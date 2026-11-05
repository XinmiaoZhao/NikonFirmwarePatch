"""Build the reviewed ProRes patch from the caller's compatible MAIN image.
No filesystem reads, device access, test-default overrides or package output here.
"""
import struct
import re
from . import layout as fw
from .a64 import Block
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
BASE = fw.BASE

# ---- stock structures (payload offsets) ------------------------------------------------------
TABLE_DIR, BLOB_DIR, LANGUAGES, STRINGS = 0x311C5A0, 0x387AF58, 36, 3136
ROWS_A, EVPTR_A = 0x3AA4758, 0x3AA4EE8               # video recording menu: 44 rows, 44 pointers
ROW_DUP, ROW_FRAME, ROW_NRAW = 7, 8, 9               # hidden duplicate file type / frame size / N-RAW quality
STATE_TABLE, STATE_SIZE = 0x4BFFCC0, 0x60            # data image; RAM a028f4cc0
STATE_VIDEO, STATE_FILETYPE, STATE_NRAW = 0xFE, 0x10A, 0x10D
STATE_NEW = 0x102                                    # stub state behind the always-hidden row 2e38
STATE_NEW_STOCK = (0xA028E8C40, 0xA028C13F0)         # its stock callbacks and page record pointers
MOVIE_BLOCK, MOVIE_BLOCK_SIZE, MOVIE_DEFAULTS = 0xA03D5BFFC, 0x2D0, 0x3ED462C   # DS group 12h
VALUE_ITEM = 0xA03D5C028                             # WbMovieSameStill, one byte (DS type 0)
VIDEO_CALLBACKS = 0x4BF3A60                          # five pointers of state 0xfe (data image)
HIDE_SITE = 0x41294C                                 # mov w1,#0x311b in the video menu entry callback
NRAW_LAYOUT, NRAW_ROWS, NRAW_EVENTS = 0x3AA81D0, 0x3AA82E0, 0x3AE69B0
NRAW_PAGE = 0x4BCC760
ITEM_ROW = 0x311B                                    # item id of the hidden duplicate row, reused
ITEM_OPTION0 = 0x35B5                                # 0x35b5..0x35bc are unused in the item id range
VALUE_CHILD, TEXT_SLOT, TEXT_STYLE = 0x4BA7, 0x4A, 4
# stock routines (virtual addresses)
F_ENTRY_GUARD, F_SET_CURSOR, F_SET_MARK = 0x403AE0F8, 0x403B0048, 0x403B00B8
F_VIDEO_REFRESH, F_CHILD, F_SET_TEXT, F_SET_CONTENT = 0x40572B2C, 0x4050A6F0, 0x403F2920, 0x403F645C
NRAW_CALLBACKS = (0x4056C8F8, 0x4056C954, 0x403B2210, 0x4056C958, 0x4056C960)
NRAW_OK = 0x4056C964
# ---- new material in the text segment's zero gap 75f8f0..aa0000 --------------------------------
GAP = (0x75F8F0, 0xAA0000)
CODE_AT, GUI_AT, TEXT_AT, TABLES_AT = 0x8A0000, 0x8A1000, 0x8A4000, 0x780000
LOADER_END_SITE, LOADER_END = 0x1024D8C, 0x408BF8F0   # mov x8,#0xf8f0 ; movk x8,#0x408b,lsl#16
SECTION_VA, SECTION_ROOM = 0x40200000, 0xA00000       # RAM room the loader maps for this section
ID_DUMMY = STRINGS                                   # keeps the end of the last stock string
ID_LABEL = 3147                               # "Video quality (ProRes)"
ID_OPTION0 = 3148                             # four options
ID_FILETYPE = 3152                            # "ProRes 422 10-bit (MOV)"
NEW_IDS = 7                                          # dummy + label + four options + file type
STOCK_FILETYPE_ID = 0x707                            # "ProRes 422 HQ 10-bit (MOV)"
FILETYPE_ROWS = (0x3AA6AD8, 0x3AA6B04)               # the two option rows of the Video file type page
FILETYPE_VALUE_IDS = 0x29BFAB0                       # {value, string id} x 6, read by 4056c5b4
FILETYPE_DEFAULT = MOVIE_DEFAULTS + 0x18             # stock default of MovieFileType (2 = H.265 8-bit)
OPTIONS = ('ProRes 422 HQ', 'ProRes 422', 'ProRes 422 LT', 'ProRes 422 Proxy')
VALUE_TEXT = (b'HQ', b'422', b'LT', b'PROXY')        # shown at the right of the row, like HIGH/NORM


def va(offset):
    return BASE + offset


def state_ram(index, field=0):
    return fw.ram(STATE_TABLE + STATE_SIZE * index) + field


VALUE_RAM = VALUE_ITEM + 1                           # the stored choice, 0..3 = hardware type
STASH_RAM = VALUE_ITEM + 2                           # grade of the ProRes clip last opened for playback


class Image:
    def __init__(self, data):
        self.old, self.new, self.edits = data, bytearray(data), []

    def put(self, offset, data, purpose, expect_zero=False, expect=None):
        if not 0 <= offset <= len(self.old) - len(data):
            raise ValueError(f"Out-of-range edit: {purpose}")
        old = self.old[offset:offset + len(data)]
        if expect_zero and any(old):
            raise ValueError(f'{purpose}: {offset:#x} is not free')
        if expect is not None and old != expect:
            raise ValueError(f'{purpose}: unexpected stock bytes at {offset:#x}')
        for other in self.edits:
            if offset < other['end'] and other['offset'] < offset + len(data):
                raise ValueError(f'{purpose}: overlaps {other["purpose"]}')
        self.new[offset:offset + len(data)] = data
        self.edits.append(dict(offset=offset, end=offset + len(data), purpose=purpose,
                               old=old, new=bytes(data)))

    def u32(self, o):
        return struct.unpack_from('<I', self.old, o)[0]

    def u64(self, o):
        return struct.unpack_from('<Q', self.old, o)[0]


def strings(img, context):
    tables = [img.u64(TABLE_DIR+8*k)-BASE for k in range(LANGUAGES)]
    blobs = [img.u64(BLOB_DIR+8*k)-BASE for k in range(LANGUAGES)]
    translations=[]
    for k in range(LANGUAGES):
        offsets=struct.unpack_from('<3137i',img.old,tables[k])
        def stock(i):return img.old[blobs[k]+offsets[i]:blobs[k]+offsets[i+1]].decode('utf-16le')
        value=stock(0x8A6)
        label=value.replace('RAW-N','ProRes') if 'RAW-N' in value else value.replace('N-RAW','ProRes')
        if label==value:raise ValueError('Missing stock N-RAW label')
        filetype,count=re.subn(r'(ProRes 422) ?HQ',r'\1',stock(STOCK_FILETYPE_ID))
        if count!=1 or 'HQ' in filetype:raise ValueError('Unexpected ProRes file type label')
        translations.append([label,*OPTIONS,filetype])
    ids=context.add('prores',translations)
    return dict(label_id=ids[0],option_ids=ids[1:5],file_type_id=ids[5])


def file_type_label(img, ids):
    """Show the new file type label wherever the Video file type page names string 707h."""
    old, new = struct.pack('<I', STOCK_FILETYPE_ID), struct.pack('<I', ids['file_type_id'])
    for row in FILETYPE_ROWS:
        fields = struct.unpack_from('<11I', img.old, row)
        if fields[0] != STOCK_FILETYPE_ID or fields[1] != 0xA17 or fields[6] not in (0x3058, 0x311C):
            raise ValueError('stock file type option row differs')
        img.put(row, new, f'Video file type page, option row at {row:#x}: label id', expect=old)
    pairs = struct.unpack_from('<12I', img.old, FILETYPE_VALUE_IDS)
    if pairs != (4, 0x707, 3, 0x7A5, 2, 0x6FD, 1, 0x6FE, 6, 0x7EE, 5, 0x7EF):
        raise ValueError('stock file type value-to-string table differs')
    img.put(FILETYPE_VALUE_IDS + 4, new, 'Video file type page, value-to-string table: entry of value 4', expect=old)
    return dict(rows=[hex(r) for r in FILETYPE_ROWS], table_entry=hex(FILETYPE_VALUE_IDS + 4))


def events(img, source, count, change):
    """Copy `count` 32-byte transition records; `change(event, action, guard, target)` edits one."""
    out = bytearray()
    for i in range(count):
        record = struct.unpack_from('<4Q', img.old, source + 32 * i)
        out += struct.pack('<4Q', *change(*record))
    if struct.unpack_from('<Q', out, len(out) - 32)[0] != 0x3BB:
        raise ValueError('transition table does not end with event 3bb')
    return bytes(out)


def code(cs):
    blk = Block(va(CODE_AT))
    # entry(state): put the cursor and the mark on the stored choice (stock 4056c8f8 with our value)
    blk.label('entry')
    blk.stp_pre(19, 30, -0x20)
    blk.str_x(20, 31, 0x10)
    blk.mov_x(19, 0)
    blk.mov_x64(8, VALUE_RAM)
    blk.ldrb_w(8, 8)
    blk.and_w3(8, 8)
    blk.mov_w(20, ITEM_OPTION0)
    blk.add_w(20, 20, 8)
    blk.bl(F_ENTRY_GUARD)
    blk.cmp_wi(0, 1)
    blk.b_cond('eq', 'entry_mark')
    blk.mov_x(0, 19)
    blk.mov_wr(1, 20)
    blk.bl(F_SET_CURSOR)
    blk.label('entry_mark')
    blk.mov_x(0, 19)
    blk.mov_wr(1, 20)
    blk.mov_w(2, 1)
    blk.ldr_x(20, 31, 0x10)
    blk.ldp_post(19, 30, 0x20)
    blk.b(F_SET_MARK)
    # ok(context): store the chosen row's item id - first option id (stock 4056c964 without SetDS)
    blk.label('ok')
    blk.ldr_x(9, 0)
    blk.mov_w(8, 0x2C)
    blk.ldr_x(10, 9, 0x50)
    blk.ldrh_w(11, 9, 0x58)
    blk.ldrh_w(9, 9, 0x32)
    blk.ldr_x(10, 10, 0x10)
    blk.add_x(9, 9, 11)
    blk.madd_x(8, 9, 8, 10)
    blk.ldr_w(8, 8, 0x18)
    blk.mov_w(9, ITEM_OPTION0)
    blk.sub_w(8, 8, 9)
    blk.and_w3(8, 8)
    blk.mov_x64(9, VALUE_RAM)
    blk.strb_w(8, 9)
    blk.ret()
    # refresh(state): stock video-menu value refresh, then our row's text
    blk.label('refresh')
    blk.stp_pre(19, 30, -0x20)
    blk.str_x(20, 31, 0x10)
    blk.mov_x(19, 0)
    blk.nop()  # shared dispatcher calls the native refresh once
    blk.mov_x(20, 0)                                  # keep the stock return value
    blk.cbz_x(19, 'refresh_done')
    blk.mov_x(0, 19)
    blk.mov_w(1, ITEM_ROW)
    blk.mov_w(2, VALUE_CHILD)
    blk.bl(F_CHILD)
    blk.cbz_x(0, 'refresh_done')
    blk.mov_x(19, 0)
    blk.mov_x64(8, VALUE_RAM)
    blk.ldrb_w(8, 8)
    blk.and_w3(8, 8)
    blk.adr(9, 'texts')
    blk.add_x(0, 9, 8, lsl=3)
    blk.mov_w(1, TEXT_SLOT)
    blk.mov_w(2, TEXT_STYLE)
    blk.bl(F_SET_TEXT)
    blk.mov_x(0, 19)
    blk.mov_w(1, TEXT_SLOT)
    blk.bl(F_SET_CONTENT)
    blk.label('refresh_done')
    blk.mov_x(0, 20)
    blk.ldr_x(20, 31, 0x10)
    blk.ldp_post(19, 30, 0x20)
    blk.ret()
    blk.label('texts')
    listing = blk.listing(cs)
    data = blk.bytes() + b''.join(t.ljust(8, b'\0') for t in VALUE_TEXT)
    return blk, data, listing


def menu(img, ids, blk, ok_action=None):
    # ---- sub-page tables -------------------------------------------------------------------
    layout = bytearray(img.old[NRAW_LAYOUT:NRAW_LAYOUT + 0x110])
    if struct.unpack_from('<I', layout, 0x44)[0] != 0x8A6:
        raise ValueError('stock layout: title id not where expected')
    struct.pack_into('<I', layout, 0x44, ids['label_id'])
    stock_row = struct.unpack_from('<11I', img.old, NRAW_ROWS)
    if stock_row[0] != 0x35E or stock_row[6] != 0x3119:
        raise ValueError('stock N-RAW option row differs')
    rows = b''.join(struct.pack('<11I', ids['option_ids'][i], *stock_row[1:6], ITEM_OPTION0 + i, *stock_row[7:])
                    for i in range(4))
    ok = blk.labels['ok'] if ok_action is None else ok_action
    table = events(img, NRAW_EVENTS, 14, lambda e, a, g, t: (e, ok if a == NRAW_OK else a, g, t))
    if table.count(struct.pack('<Q', ok)) != 3:
        raise ValueError('expected three OK transitions in the stock option table')
    at = GUI_AT
    layout_at = at; at += len(layout)
    rows_at = at; at += len(rows)
    at = (at + 7) & ~7
    tables_at = at; at += 4 * len(table)
    evptr_at = at; at += 4 * 8
    callbacks_at = at; at += 5 * 8
    page_at = at; at += 0x50
    if at > TEXT_AT:
        raise ValueError('GUI area too small')
    page = bytearray(img.old[NRAW_PAGE:NRAW_PAGE + 0x50])
    struct.pack_into('<3Q', page, 8, va(layout_at), va(rows_at), va(evptr_at))
    struct.pack_into('<H', page, 0x20, 4)
    callbacks = struct.pack('<5Q', blk.labels['entry'], *NRAW_CALLBACKS[1:])
    img.put(layout_at, layout, 'sub-page layout (stock N-RAW quality layout, new title id)', expect_zero=True)
    img.put(rows_at, rows, 'sub-page rows: four options', expect_zero=True)
    img.put(tables_at, table * 4, 'sub-page transition tables, one per row', expect_zero=True)
    img.put(evptr_at, struct.pack('<4Q', *(va(tables_at + len(table) * i) for i in range(4))),
            'sub-page transition table pointers', expect_zero=True)
    img.put(callbacks_at, callbacks, 'sub-page state callbacks', expect_zero=True)
    img.put(page_at, page, 'sub-page page record', expect_zero=True)
    # ---- the new state ------------------------------------------------------------------------
    record = STATE_TABLE + STATE_SIZE * STATE_NEW
    stock_state = struct.unpack_from('<HHI11Q', img.old, record)
    nraw_state = struct.unpack_from('<HHI11Q', img.old, STATE_TABLE + STATE_SIZE * STATE_NRAW)
    if stock_state[:2] != (2, STATE_NEW) or stock_state[3] != nraw_state[3] or \
            (stock_state[7], stock_state[12]) != STATE_NEW_STOCK or any(stock_state[4:7] + stock_state[8:12] + stock_state[13:]):
        raise ValueError('stock state record differs')
    img.put(record + 0x28, struct.pack('<Q', va(callbacks_at)), f'state {STATE_NEW:#x}: callbacks -> ProRes quality sub-page',
            expect=struct.pack('<Q', STATE_NEW_STOCK[0]))
    img.put(record + 0x50, struct.pack('<Q', va(page_at)), f'state {STATE_NEW:#x}: page record -> ProRes quality sub-page',
            expect=struct.pack('<Q', STATE_NEW_STOCK[1]))
    at = MOVIE_DEFAULTS + (VALUE_ITEM - MOVIE_BLOCK)
    if img.old[at:at + 4] != b'\x01\0\0\0' or not MOVIE_BLOCK < VALUE_RAM < MOVIE_BLOCK + MOVIE_BLOCK_SIZE:
        raise ValueError('stock defaults: the value byte is not a zero padding byte')
    # ---- the row in the video recording menu ----------------------------------------------------
    stock = [img.old[ROWS_A + 44 * i:ROWS_A + 44 * i + 44] for i in (ROW_DUP, ROW_FRAME, ROW_NRAW)]
    nraw = struct.unpack('<11I', stock[2])
    dup = struct.unpack('<11I', stock[0])
    if dup[6] != ITEM_ROW or nraw[6] != 0x3118 or nraw[0] != 0x8A6:
        raise ValueError('stock video menu rows differ')
    new_row = struct.pack('<11I', ids['label_id'], *nraw[1:6], ITEM_ROW, *nraw[7:])
    img.put(ROWS_A + 44 * ROW_DUP, stock[1] + stock[2] + new_row,
            'video menu rows 7..9: frame size, N-RAW quality, new ProRes quality row', expect=b''.join(stock))
    pointers = struct.unpack_from('<3Q', img.old, EVPTR_A + 8 * ROW_DUP)
    img.put(EVPTR_A + 8 * ROW_DUP, struct.pack('<3Q', pointers[1], pointers[2], pointers[0]),
            'video menu transition table pointers 7..9, same order as the rows')
    dup_table = pointers[0] - BASE
    changed = []

    def retarget(e, a, g, t):
        if t == STATE_FILETYPE:
            changed.append(e)
            return e, a, g, STATE_NEW
        return e, a, g, t
    table7 = events(img, dup_table, 46, retarget)
    if changed != [0x286, 0x28B, 0x29F, 0x2AE]:
        raise ValueError(f'unexpected transitions to the file type page: {changed}')
    img.put(dup_table, table7, 'transition table of the reused row: enter the new state instead of the file type page')
    img.put(HIDE_SITE, struct.pack('<I', 0x52800001 | 0x2E38 << 5),
            'video menu entry callback: hide item 2e38 again instead of hiding item 311b',
            expect=struct.pack('<I', 0x52800001 | ITEM_ROW << 5))
    stock_refresh = img.u64(VIDEO_CALLBACKS + 32)
    if stock_refresh != F_VIDEO_REFRESH:
        raise ValueError('stock video menu refresh callback differs')
    img.put(VIDEO_CALLBACKS + 32, struct.pack('<Q', blk.labels['refresh']),
            'video menu value refresh callback -> wrapper')
    return dict(layout=hex(va(layout_at)), rows=hex(va(rows_at)), tables=hex(va(tables_at)),
                pointers=hex(va(evptr_at)), callbacks=hex(va(callbacks_at)), page=hex(va(page_at)),
                state=hex(state_ram(STATE_NEW)), value=hex(VALUE_RAM))


def loader(img):
    """Make the stock text loader copy the gap up to the end of the new material."""
    used = max(e['end'] for e in img.edits if GAP[0] <= e['offset'] < GAP[1])
    end = va((used + 0xFFF) & ~0xFFF)
    if not LOADER_END < end <= SECTION_VA + SECTION_ROOM or end > va(GAP[1]):
        raise ValueError('new material does not fit the section room')
    old = struct.pack('<II', 0xD2800008 | (LOADER_END & 0xFFFF) << 5, 0xF2A00008 | (LOADER_END >> 16) << 5)
    new = struct.pack('<II', 0xD2800008 | (end & 0xFFFF) << 5, 0xF2A00008 | (end >> 16) << 5)
    img.put(LOADER_END_SITE, new, f'text loader: copy section {SECTION_VA:#x} up to {end:#x} instead of {LOADER_END:#x}',
            expect=old)
    return dict(site=hex(va(LOADER_END_SITE)), old_end=hex(LOADER_END), new_end=hex(end),
                copied_bytes=hex(end - SECTION_VA), room=hex(SECTION_ROOM))


def build_main(data, strings_context, ok_action=None):
    """Return Image edits and review metadata; input is immutable MAIN without CRC."""
    cs = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    img = Image(data)
    if any(data[GAP[0]:GAP[1]]):
        raise ValueError('Required text gap is occupied (already patched or incompatible)')
    ids = strings(img, strings_context)
    ids['file_type_sites'] = file_type_label(img, ids)
    blk, code_bytes, listing = code(cs)
    if CODE_AT + len(code_bytes) > GUI_AT:
        raise ValueError('Code area too small')
    img.put(CODE_AT, code_bytes, 'code: sub-page entry, OK, refresh wrapper, value texts', expect_zero=True)
    where = menu(img, ids, blk, ok_action)
    from . import back_half
    back = back_half.apply(img, cs, VALUE_RAM, STASH_RAM, CODE_AT + len(code_bytes), GUI_AT, bank=False)
    return img, dict(strings=ids, menu=where, back_half=back, entries={k:hex(v) for k,v in blk.labels.items()},
                    code=[dict(va=hex(x), word=w, text=t) for x, w, t in listing])
