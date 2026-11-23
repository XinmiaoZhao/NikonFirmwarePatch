"""Factory C 3.11 photo menu call sites and their displaced instructions."""
import struct
from z8prores.package import require

BASE = 0x409FF000   # the last 4 KiB of the pre-capture cave; the pre-capture unit may use 0x409F0000..0x409FF000
SITES = (
    (0x4049D674, 'raw_menu_size_alt', True, 0x403ACCCC),
    (0x405D9B40, 'raw_menu_value', True, 0x403EC398),
    (0x405DB6CC, 'raw_menu_enter', True, 0x403EC398),
    (0x405E6990, 'raw_menu_lossless', False, None),
    (0x405E69A0, 'raw_menu_star', False, None),
)
MENU = 'pre-capture RAW recording menu'

# Turbo RAW: Photo shooting menu row 2 (item 0x2CAA), one of the two rows the stock entry callback hides.
TURBO = 'pre-capture Turbo RAW menu'
TURBO_STRINGS = (3250, 3251)                       # label, help (z8patch.shared.STRING_IDS['turbo-raw'])
PHOTO_ROWS, TURBO_ROW, SWITCH_ROW = 0x43DCF790, 2, 19   # row 19: Long exposure NR, a stock switch row
ROW_STOCK = (0x43A, 0xFFFF, 0xFFFF, 0, 0x101041, 0xB44, 0x2CAA, 0x40004, 0xFFFFFFFF, 0xFFFFFFFF, 2)
SWITCH_STOCK = (0x17C, 0x484, 0x17C, 0, 0x20901005, 0x1326, 0x2A14, 0x40004, 0xFFFFFFFF, 0xFFFFFFFF, 2)
ROW_EVENTS = 0x43E094A0                            # row 2's own transition table (photo page pointer 2)
STAY, BACK = 0x68C, 0x68D
TURBO_EVENTS = {                                   # stock entry -> the switch row's (row 19's) entry
    (0x285, 0x403B1BA4, 0, 0x1): (0x285, 0x403B1BA4, 0, BACK),
    (0x286, 0x403B1BA8, 0, 0x1D): (0x286, 'turbo_toggle', 0, STAY),
    (0x29F, 0x403B1BA8, 0x403B1C64, 0x1D): (0x28B, 'turbo_toggle', 0, STAY),
    (0x2A0, 0x403B1BA4, 0x403B1C64, 0x1): (0x2A0, 0x403B1BA4, 0x403B1C64, BACK),
    (0x2AE, 0x403B1BA8, 0, 0x1D): (0x2AE, 'turbo_toggle', 0, STAY),
    (0x3F, 0x405E2AD8, 0, STAY): (0x281, 0x403B1C3C, 0x403B1CB8, STAY),
}
# The photo menu entry callback 405D9704 hides the items of the list at 42B27788 (2CAAh, 2C13h, 1Ah, ...), count 2.
# Pixel shift (still-photo-tools) sets the count to 1 to show 2C13h; this group moves the list start instead:
# alone 42B2778C (2C13h, 1Ah: hides only 2C13h), with pixel shift 42B27784 (89h, not a photo menu item: hides nothing).
HIDE_LIST, HIDE_STOCK = 0x405D9704, 0xD28EF101    # movz x1,#0x7788
TURBO_TEXT = {      # one line of help: the shared text area has about 3.9 KiB left with every group selected
    'en': ('Turbo RAW', 'On: longer RAW bursts, some gray previews.'),
    'zh-CN': ('Turbo RAW', '开：RAW 连拍更长，部分预览为灰色。'),        # Chinese translated by AI from the English
    'zh-TW': ('Turbo RAW', '開：RAW 連拍更長，部分預覽為灰色。'),
}
LANGUAGES, TABLE_DIR, BLOB_DIR, FAMILY_STRING, STOCK_ENTRIES = 36, 0x311C5A0, 0x387AF58, 2222, 3137


def turbo_strings(eg):
    """Label and help for each of the 36 languages; the family (en, zh-CN, zh-TW) follows each language's stock
    "Pixel shift shooting" string, as pixel shift's own menu text does, and every glyph must occur in that language's
    stock strings."""
    out = []
    B = 0x40160000
    for k in range(LANGUAGES):
        table = struct.unpack_from('<Q', eg, TABLE_DIR + 8 * k)[0] - B
        blob = struct.unpack_from('<Q', eg, BLOB_DIR + 8 * k)[0] - B
        offsets = struct.unpack_from(f'<{STOCK_ENTRIES}i', eg, table)
        a, b = offsets[FAMILY_STRING], offsets[FAMILY_STRING + 1]
        family = eg[blob + a:blob + b].decode('utf-16le')
        texts = TURBO_TEXT['zh-TW' if '像素' in family and '攝' in family else 'zh-CN' if '像素' in family else 'en']
        pool = set(eg[blob + offsets[0]:blob + offsets[STOCK_ENTRIES - 1]].decode('utf-16le', 'replace'))
        missing = sorted({c for c in ''.join(texts) if c != ' ' and c not in pool})
        require(not missing, ('Turbo RAW: glyphs absent from the stock strings of language', k, missing))
        out.append(list(texts))
    return out


def apply(image, code, entries, photo=False):
    B = 0x40160000
    def branch(site,to,link):
        delta=to-site
        if delta%4 or not -(1<<27)<=delta<1<<27:raise ValueError('Invalid menu branch')
        return struct.pack('<I',(0x94000000 if link else 0x14000000)|((delta//4)&0x3ffffff))
    if BASE+len(code)>0x40A00000 or any(image[BASE-B:BASE-B+len(code)]):
        raise ValueError('RAW menu allocation is occupied')
    yield BASE,bytes(len(code)),code,MENU
    for site,name,link,original in SITES:
        old = branch(site,original,link) if original else bytes.fromhex('00c18052')
        if image[site-B:site-B+4]!=old: raise ValueError(f'Unexpected RAW menu bytes at {site:#x}')
        yield site,old,branch(site,entries[name],link),MENU

    # The source-bank byte is read into w10 inside the live descriptor builder.
    # Each ordinary quality role has five callbacks; replace only callback 4
    # (secondary disabled), leaving the other roles sharing its stub untouched.
    for site, old, new in (
        (0x40441104, bytes.fromhex('4a014039'), branch(0x40441104, entries['raw_menu_size_live'], False)),
        (0x42AEA178, struct.pack('<Q', 0x4043EBA0), struct.pack('<Q', entries['raw_menu_size_disabled'])),
        (0x42AF6460, struct.pack('<Q', 0x4049B9B8), struct.pack('<Q', entries['raw_menu_size_disabled'])),
    ):
        if image[site-B:site-B+len(old)] != old:
            raise ValueError(f'Unexpected quality/size role bytes at {site:#x}')
        yield site, old, new, MENU

    # Turbo RAW row: label and help, the switch row's style and switch resource, item 0x2CAA kept.
    at = PHOTO_ROWS + 44 * TURBO_ROW
    require(struct.unpack_from('<11I', image, at - B) == ROW_STOCK, 'Turbo RAW: unexpected photo menu row 2')
    require(struct.unpack_from('<11I', image, PHOTO_ROWS + 44 * SWITCH_ROW - B) == SWITCH_STOCK, 'Turbo RAW: unexpected switch row')
    row = list(ROW_STOCK)
    row[0], row[1], row[2] = TURBO_STRINGS[0], TURBO_STRINGS[1], TURBO_STRINGS[0]
    row[4], row[5] = SWITCH_STOCK[4], SWITCH_STOCK[5]
    yield at, struct.pack('<11I', *ROW_STOCK), struct.pack('<11I', *row), TURBO + ': row 2 (item 0x2CAA) label, help, switch style'
    # Row 2's transitions: OK, right and touch flip the switch (turbo_toggle), as row 19's do with 0x4051226C.
    seen = set()
    for k in range(128):
        entry = struct.unpack_from('<4Q', image, ROW_EVENTS - B + 32 * k)
        if entry[0] == 0x3BB:
            break
        if entry in TURBO_EVENTS:
            new = tuple(entries[v] if isinstance(v, str) else v for v in TURBO_EVENTS[entry])
            seen.add(entry)
            yield ROW_EVENTS + 32 * k, struct.pack('<4Q', *entry), struct.pack('<4Q', *new), \
                TURBO + f': row 2 transition {entry[0]:#x} -> {new[0]:#x}'
    require(seen == set(TURBO_EVENTS), 'Turbo RAW: unexpected row 2 transitions')
    # Show row 2: move the hidden-item list start (see HIDE_LIST).
    old = struct.pack('<I', HIDE_STOCK)
    require(image[HIDE_LIST - B:HIDE_LIST - B + 4] == old, 'Turbo RAW: unexpected photo menu entry callback')
    start = 0x7784 if photo else 0x778C
    yield HIDE_LIST, old, struct.pack('<I', 0xD2800001 | (start << 5)), \
        TURBO + (': hidden-item list from 42B27784 (pixel shift shows 2C13h)' if photo else ': hidden-item list from 42B2778C (only 2C13h)')
    # Photo menu refresh: set the Turbo RAW switch after the Extended menu banks one.
    site = 0x405D98A4
    old = branch(site, 0x405121E4, True)
    require(image[site - B:site - B + 4] == old, 'Turbo RAW: unexpected photo menu refresh')
    yield site, old, branch(site, entries['turbo_refresh'], True), TURBO + ': switch state in the photo menu refresh'
