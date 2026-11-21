"""Public source adapted from the pinned research implementation; regular files only."""
from z8prores.package import require
import struct
from z8prores.menu import Image
BASE = 1075183616
CAVE, SLOT_END = (1083768832, 1084162048)
RUNTIME_SOURCE, RUNTIME = (1084149760, 43218030592)
UI_VA = 1084071936
AF_VA = 1084063744
TABLES_VA = 1083047936
LOADER = 1092111756
STOCK_LOADER = '081e9fd26811a8f2'
GAP = (7731440, 11141120)
STOCK_SHA = 'f85e0138e2f5e660ece8560de62e0d12cb795e0e14983e50f20b61dce906c46c'
FACTORY_SHA = 'd67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96'
INIT_VA, INIT_OFF = (42991648768, 78721024)
FLAGS = ['--target=aarch64-none-elf', '-O2', '-ffreestanding', '-fno-builtin', '-fno-stack-protector', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '-mgeneral-regs-only', '-mstrict-align', '-Wall', '-Wextra', '-Werror']
ENTRY = 'psm_menu_action'
SOURCES = ('ps8.c', 'firmware.c', 'job.c', 'job.h', 'nefx.c', 'nefx.h', 'nef.c', 'nef.h', 'psm.c', 'psm.h', 'crc32_slice8.inc', 'group.c', 'group.h', 'af_window.c', 'af_window.h', 'afrow.c', 'afrow.h', 'afrow_fma_a64.c', 'io_pipe.c', 'io_pipe.h', 'browser.c', 'browser.h', 'browser_fw.inc', 'thumbnail.c', 'thumbnail.h', 'ui_strings.h')
TABLE_DIR, BLOB_DIR, LANGUAGES, STOCK_ENTRIES = (51496352, 59223896, 36, 3137)
PIXEL_SHIFT_STRING = 2222
ROWS, ROW = (63371152, 45)
ROW_STOCK = (1082, 65535, 65535, 0, 1052741, 4903, 11283, 262148, 4294967295, 4294967295, 2)
ROW_AUTO_CAPTURE = (1794, 2620, 1794, 0, 1052736, 65535, 11533, 262148, 4294967295, 4294967295, 2)
ROW_ALL = 2
ROW_ALL_STOCK = (1082, 65535, 65535, 0, 1052737, 2884, 11434, 262148, 4294967295, 4294967295, 2)
ROW_EVENTS = 63373224
STATES, PAGES, PAGES_END = (79690944, 79440912, 79560192)
SUBMENU = 29
SUB_CALLBACKS, SUB_PAGE = (79632464, 79525312)
SUB_CALLBACKS_STOCK = (1079925436, 0, 1077617168, 1079925444, 0)
SUB_LAYOUT, SUB_TITLE = (63375352, 933)
CURSOR = 1077608520
TEMPLATE_STATE, TEMPLATE_PAGE = (30, 79525392)
TEMPLATE_LAYOUT, TEMPLATE_ROWS, TEMPLATE_TITLE = (63375664, 63375936, 346)
TEMPLATE_ROW = 2
TEMPLATE_ROW_STOCK = (748, 65535, 65535, 0, 1052736, 65535, 10640, 262148, 4294967295, 4294967295, 2)
TEMPLATE_OK = ((646, 34), (651, 34), (671, 34), (686, 34))
LAYOUT_BYTES = 272
PROGRESS_LAYOUT, FOOTER_RESOURCE, FOOTER_OK = (1136180440, 15, 2713)
REVIEW_LAYOUT_VA, TITLE_RESOURCE, LAYOUT_RESOURCES = (1084147712, 2, 17)
C5_PAGE_RAM = 42992466496
HIDE_SITE = 1079875348
HIDE_LIST = 1118992264
CALLBACKS = {79631984: (1079875332, 'psm_photo_entry'), 79632016: (1079875592, 'psm_photo_refresh')}
EVENTS, OK_EVENTS, EVENTS_END = (1138916160, (646, 651, 671, 686), 955)
OK_ACTION, OK_TARGET, NEW_TARGET = (1077615528, 197, 197)
ROW45_TARGET = SUBMENU
EVENTS_ALL, OK_EVENTS_ALL, OK_TARGET_ALL = (1138791584, (646, 671, 686), 29)
FS_DISPATCH = 1076734092
FS = {1076734540: ('open', 4), 1076734636: ('close', 5), 1076734796: ('read', 7), 1076734904: ('write', 8), 1076735012: ('seek', 9), 1076735236: ('create', 12), 1076735320: ('rename', 13), 1076735400: ('remove', 14), 1076736156: ('list', 23), 1076736428: ('exists', 26)}
STOCK_CALLS = {1087554568: 'heap allocate (bytes, 0)', 1087554632: 'heap free', 1087551672: 'dc cvac by line (clean before a write)', 1087551944: 'dc civac by line (around a read)', 1079027440: 'menu child by item id', 1077881120: 'set text slot', 1077042504: 'menu item content kind', 1079875332: 'stock photo menu entry callback', 1079875592: 'stock photo menu refresh callback', 1077445792: 'power timer kind', 1077445816: 'power timer hold', 1077445376: 'power timer set', 1077855128: 'settings get', 1077855132: 'settings set', 1077870296: 'redraw request'}
STOCK_CALLS.update({1087558808: 'create persistent worker task', 1087559116: 'start worker', 1087559252: 'sleep worker', 1077768324: 'arm GUI one-shot timer', 1077768516: 'cancel GUI timer', 1077536784: 'find page container', 1077037356: 'find child node', 1077895708: 'dynamic text', 1077877464: 'progress percentage', 1077536840: 'mark container', 1077597860: 'transition menu state', 1077872528: 'screen redraw setup', 1077896284: 'text content slot', 1077895860: 'mark enclosing progress container dirty', 1087552552: 'create persistent event flag (12 bytes, multiple waiters)', 1087552652: 'set event bits', 1087552712: 'clear event bits', 1087552940: 'timed OR event wait, auto-clear matched bits (0x21)', 1076797476: 'stock raw image submission', 1076786900: 'stock graphics completion fence', 1077011416: 'current drawing surface extent', 1077011504: 'native text/image intrinsic size', 1077466712: 'native menu orientation', 1077011112: 'native widget rectangle setter', 1077602420: 'arrange native list rows after a visibility change', 1077603128: 'rebuild native scroll view', 1077603364: 'native scrollbar geometry', 1077616336: 'set native row disabled state and colors', 1077613604: 'native previous row, focus and scroll', 1077613396: 'native next row, focus and scroll', 1077608148: 'native enabled row count', 1077608312: 'native focus state', 1077537988: 'set native drawing view rectangle', 1077874104: 'native drawing view id', 1077538156: 'native view rectangle'})
STOCK_CALLS.update({1077877228: 'append embedded primitive child to native row list', 1077076380: 'stock language-specific text font family', 1077010808: 'native text kind reset and rebind with glyph release', 1077074772: 'current native text language', 1077881432: 'bounded UTF-16 dynamic text slot'})
STOCK_CALLS.update({0x4032E2A0: 'menu text size for language and label',
                    0x4032E364: 'menu horizontal and vertical glyph scales',
                    0x4032E554: 'menu glyph tracking for language and label'})
STOCK_POINTERS = {1077014624: 'stock native folder row draw including its children', 1077870196: 'GUI redraw predicate', 1077870152: 'container render predicate'}
REDRAW_TAIL = 1079474776
STOCK_CALLS.update({a: f'FS request {op:#x} ({name})' for a, (name, op) in FS.items()})
RAM_WORDS = [(43002800208 + 18432 - 10529, 43002800208 + 18432 - 10529 + 24, 'borrowed item disabled bytes; saved and restored'), (RUNTIME, RUNTIME + 12288, 'private task/UI state; zeroed by the cold-start copy only (PS5: revalidated each job)'), (43002877096 + 252 * 24, 43002877096 + 297 * 24, 'borrowed dynamic text slots; content and descriptor restored at browser exit'), (43002117640, 43002117640 + 769 * 16, 'stock task registry 0x40D2CAA8 kind 0 (read only)')]
RAM_WORDS += [(C5_PAGE_RAM + 8, C5_PAGE_RAM + 16, 'C5 page record layout pointer (RAM copy of image 0x4BDAA40): stock or PS11 review layout')]
RAM_WORDS += [(43002884296 + 16 * f, 43002884296 + 16 * (f + 1), 'native dynamic font cache; browser save/restore, persistent photo-row status at font 4') for f in (4, 519, 520, 522, 523, 525, 526, 528, 529, 531, 532, 543)]
DELETE_WRAPPER = 1082538988
MENU_TEXT = {'zh-TW': ('像素位移合成', '選擇兩張卡的 4/8/16/32 張組，選擇後確認合成。已合成的組可再次合成，原有檔案保留。MENU 返回。合成時按 MENU 取消。', '\uefff選擇', '\uea82\uea83返回', '上次合成結果'), 'zh-CN': ('像素变化合成', '选择两张卡的 4/8/16/32 张组，选择后确认合成。已合成的组可再次合成，原有文件保留。MENU 返回。合成时按 MENU 取消。', '\uefff选择', '\uea82\uea83返回', '上次合成结果'), 'en': ('Pixel shift merge', 'Browse 4/8/16/32-shot groups on both cards. Select groups, then confirm the merge. Merged groups can be merged again. Existing files are kept. MENU returns. MENU cancels a running merge.', '\uefffSelect', '\uea82\uea83Back', 'Last merge result')}

def strings(base, entries):
    """PS7: four new strings for all 36 languages (row 45's label and help, the submenu's two rows; PS11: a fifth, the
    progress page title for a result shown later), appended after the base's `entries`
    table entries (stock: 3136 strings + end); the language family is chosen from each language's stock "pixel shift"
    string (the collaborator's choice)."""
    tables, blobs, new_tables, labels = ([], [], [], [])
    for k in range(LANGUAGES):
        tables.append(struct.unpack_from('<Q', base, TABLE_DIR + 8 * k)[0] - BASE)
        blobs.append(struct.unpack_from('<Q', base, BLOB_DIR + 8 * k)[0] - BASE)
    for k in range(LANGUAGES):
        offsets = list(struct.unpack_from(f'<{entries}i', base, tables[k]))
        stock = base
        a, b = (offsets[PIXEL_SHIFT_STRING], offsets[PIXEL_SHIFT_STRING + 1])
        stock_label = stock[blobs[k] + a:blobs[k] + b].decode('utf-16le')
        texts = MENU_TEXT['zh-TW' if '像素' in stock_label and '攝' in stock_label else 'zh-CN' if '像素' in stock_label else 'en']
        pool = set(stock[blobs[k] + offsets[0]:blobs[k] + offsets[entries - 1]].decode('utf-16le', 'replace'))
        ok = stock[blobs[k] + offsets[FOOTER_OK]:blobs[k] + offsets[FOOTER_OK + 1]].decode('utf-16le')
        require(ok.lstrip('\u200f').startswith('\uefff'), ('stock OK button string', k, ok))
        missing = sorted({c for c in ''.join(texts) if c != ' ' and c not in pool})
        require(not missing, ('glyphs absent from the stock strings of language', k, missing))
        labels.append(dict(language=k, stock=stock_label, label=texts[0], help=texts[1], row_newest=texts[2], row_all=texts[3], review_title=texts[4], glyphs_in_stock_strings=True))
        new_tables.append((offsets, list(texts)))
    return (tables, blobs, new_tables, labels)

def build_main(stock, code, symbols, af_code, strings_context):
    base = stock
    img = Image(stock)
    facts = {}

    def put(why, at, new, zero=False):
        img.put(at, new, why, expect_zero=zero)

    def data_off(va):
        return va - INIT_VA + INIT_OFF if va >= INIT_VA else va - BASE
    entries = strings(stock, STOCK_ENTRIES)[2]
    strings_context.add('pixelshift', [r[1] for r in entries])
    ids = dict(zip(('label', 'help', 'row_newest', 'row_all', 'review_title'), range(3142, 3147)))
    events = EVENTS - BASE
    ok_rows = []
    for i in range(256):
        event, action, guard, target = struct.unpack_from('<4Q', stock, events + 32 * i)
        if event in OK_EVENTS:
            require(action == OK_ACTION and target == OK_TARGET, 'Pixel shift stock transition')
            ok_rows.append((i, event, guard))
        if event == EVENTS_END:
            break
    require([e for _, e, _ in ok_rows] == list(OK_EVENTS), 'Pixel shift OK events')
    entry = {k: int(symbols[k]['va'], 16) for k in (ENTRY, 'psm_photo_entry', 'psm_photo_refresh')}
    put('P1 PS3 code and read-only tables (merge, NEF decoder, NEFX writer, native adapter)', CAVE - BASE, code, zero=True)
    put('PS11 AF kernel', AF_VA - BASE, af_code, zero=True)
    row = list(ROW_STOCK)
    row[0], row[1], row[2] = (ids['label'], ids['help'], ids['label'])
    row[4], row[5] = (ROW_AUTO_CAPTURE[4], ROW_AUTO_CAPTURE[5])
    put('P3 photo menu row 45 (item 0x2C13): PS3 label and help; PS11 no value column (as row 46)', ROWS + ROW * 44, struct.pack('<11I', *row))
    put('P3 photo menu entry: hide only 0x2CAA (mov w2,#1)', HIDE_SITE - BASE, struct.pack('<I', 1384120354))
    for at, (_, name) in CALLBACKS.items():
        put(f'P3 photo menu callback -> {name}', at, struct.pack('<Q', entry[name]))
    for i, event, guard in ok_rows:
        put(f'P3 item 0x2C13 OK transition {event:#x} -> {ENTRY}, target {ROW45_TARGET:#x} (submenu)', events + 32 * i, struct.pack('<4Q', event, entry[ENTRY], int(symbols['psm_menu_available']['va'], 16), ROW45_TARGET))
    page = list(struct.unpack_from('<10Q', stock, 79464272))
    require(page[:5] == [2147754248, PROGRESS_LAYOUT, 1136181596, 1136181640, 1], 'Unexpected firmware structure')
    footer = struct.unpack_from('<17I', stock, PROGRESS_LAYOUT - BASE + 68 * FOOTER_RESOURCE)
    require(footer[0] == 2786 and footer[1] == 35 and (footer[14] == 4929), 'stock progress footer button')
    c5 = struct.unpack_from('<12Q', base, STATES + 96 * 197)
    require(c5[0] == 12910594 and c5[10] == C5_PAGE_RAM and (data_off(C5_PAGE_RAM) == 79538752), 'state C5 page record')
    title = struct.unpack_from('<17I', stock, PROGRESS_LAYOUT - BASE + 68 * TITLE_RESOURCE)
    require(title[0] == 2638 and title[1] == 31 and (title[14] == 4915), 'stock progress title resource')
    require(not any(stock[PROGRESS_LAYOUT - BASE + 68 * 16:PROGRESS_LAYOUT - BASE + 68 * 17]), 'resource 16 ends the layout')
    facts['progress_footer'] = dict(layout=hex(PROGRESS_LAYOUT), resource=FOOTER_RESOURCE, words=[hex(x) for x in footer], running_string='0xae2', result_string=hex(FOOTER_OK))
    events_ui = []
    for i in range(64):
        e, action, guard, target = struct.unpack_from('<4Q', stock, 1136503936 - BASE + 32 * i)
        if e == 638:
            action = int(symbols['psm_modal_action']['va'], 16)
            guard = 0
        elif e in (646, 651, 686):
            action = int(symbols['psm_modal_ok']['va'], 16)
            guard = 0
        else:
            action = 1077615528
            guard = 1077615708
        events_ui.extend((e, action, guard, 1676))
        if e == 955:
            break
    else:
        raise AssertionError('progress event terminator')
    ui = struct.pack('<Q', UI_VA + 8) + struct.pack('<' + 'Q' * len(events_ui), *events_ui)
    sub_at = UI_VA + (len(ui) + 15 & ~15)

    def resource(va, index=0):
        return list(struct.unpack_from('<17I', stock, va - BASE + index * 68))

    def rect(r, coords):
        x0, y0, x1, y1 = coords
        r[6:10] = [x0 | y0 << 16, x1 | y1 << 16] * 2
        return r
    title = resource(1138697736, 1)
    title[0] = ids['label']
    title[14] = 5120
    background = rect(resource(1138697736, 0), (0, 56, 720, 426))
    background[10:14] = [35] * 4
    background[14] = 5121
    footer = resource(1138697736, 7)
    footer[14] = 5122
    # Factory two-button group 149 builds distinct touch targets from real keys.
    # Its designer supplies icon spacing and right-to-left ordering.
    buttons = resource(0x43DF0E74)
    require(buttons[:3] == [149, 11, 2], 'Unexpected native footer group')
    group_ptr, = struct.unpack_from('<Q', stock, 0x42AC1C58 - BASE + 8 * 149)
    require(struct.unpack_from('<3I', stock, data_off(group_ptr)) == (0xAE2, 0xABD, 0xFFFF),
            'Unexpected native MENU and OK key list')
    keys = struct.iter_unpack('<2I', stock[0x42AD0110-BASE:0x42AD0110-BASE+164*8])
    first_event = {}
    for key, event in keys:
        first_event.setdefault(key, event)
    require((first_event[0xAE2], first_event[0xABD]) == (0x27E, 0x2AE),
            'Unexpected native footer actions')
    buttons[14] = 5123
    counter = rect(resource(1138697736, 5), (592, 8, 714, 48))
    counter[0] = 276
    counter[14] = 5125
    counter[10:14] = [56, 56, 39, 39]
    layout = b''.join((struct.pack('<17I', *r) for r in [resource(1138697736, 0), title, footer, buttons, counter])) + bytes(68)
    rows_va = sub_at + len(layout)
    count = 24
    rows_blob = bytearray()
    template = list(struct.unpack_from('<11I', stock, 1139930884 - BASE))
    for i in range(count):
        row = template.copy()
        row[0] = 252 + i
        row[4] |= 65
        row[6] = 18432 + i
        rows_blob += struct.pack('<11I', *row)
    ptrs_va = rows_va + len(rows_blob)
    table_va = ptrs_va + 8 * count
    browser_events = (638, 643, 644, 645, 646, 651, 669, 670, 671, 672, 686, 955)
    tables_blob = b''.join((struct.pack('<4Q', e, int(symbols['ps8_browser_event']['va'], 16) if e != 955 else 0, 0, 1676) for e in browser_events))
    page_va = table_va + len(tables_blob)
    sub_page = bytearray(stock[79558672:79558672 + 80])
    struct.pack_into('<4Q', sub_page, 0, 2147489816, sub_at, rows_va, ptrs_va)
    struct.pack_into('<H', sub_page, 32, count)
    struct.pack_into('<4h', sub_page, 34, 6, 60, 714, 418)
    sub_blob = layout + rows_blob + struct.pack('<' + 'Q' * count, *[table_va] * count) + tables_blob + sub_page
    ui += bytes(sub_at - UI_VA - len(ui)) + sub_blob
    submenu_page = dict(page=hex(page_va), layout=hex(sub_at), rows=hex(rows_va), row_tables=[hex(table_va)], template_page='0x4bdf810', template_row=0, row_count=count, frame_template='0x43df2608')
    require(UI_VA + len(ui) <= REVIEW_LAYOUT_VA, 'Unexpected firmware structure')
    review_layout = bytearray(stock[PROGRESS_LAYOUT - BASE:PROGRESS_LAYOUT - BASE + 68 * LAYOUT_RESOURCES])
    struct.pack_into('<I', review_layout, 68 * TITLE_RESOURCE, ids['review_title'])
    require(REVIEW_LAYOUT_VA + len(review_layout) <= RUNTIME_SOURCE, 'Unexpected firmware structure')
    page[3] = UI_VA
    put('P5 private progress events; P6 submenu page (layout, rows, row tables, page record)', UI_VA - BASE, ui, zero=True)
    put(f'P6 state {SUBMENU:#x} page -> the new submenu page {page_va:#x}', STATES + 96 * SUBMENU + 80, struct.pack('<Q', page_va))
    put('P6 PS8 browser state callbacks', SUB_CALLBACKS, struct.pack('<5Q', int(symbols['ps8_browser_entry']['va'], 16), int(symbols['ps8_browser_exit']['va'], 16), 1079280800, 0, int(symbols['ps8_browser_refresh']['va'], 16)))
    put('P5 hidden C5 page becomes modal progress page', 79538752, struct.pack('<10Q', *page))
    put('P7 PS11 review copy of the progress layout (title resource 2 -> "Last merge result")', REVIEW_LAYOUT_VA - BASE, bytes(review_layout), zero=True)
    callbacks = [int(symbols[k]['va'], 16) for k in ('psm_modal_entry', 'psm_modal_exit')]
    callbacks += [1079280800, 0, int(symbols['psm_modal_refresh']['va'], 16)]
    require(struct.unpack_from('<5Q', stock, 79639424) == (1079913516, 1079913612, 1077617168, 1079913616, 0), 'Unexpected firmware structure')
    put('P5 private modal state callbacks', 79639424, struct.pack('<5Q', *callbacks))
    return (img, dict(code_bytes=len(code), af_code_bytes=len(af_code), string_ids=ids))
