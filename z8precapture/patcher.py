"""Pre-capture HN11 public adapter (HN13: DX): feature windows only; no identity or loader edits."""
import struct
from z8prores.package import require
BASE=0x40160000

def c20(symbols):
    """HN24 is built into the unit (PRECAPTURE_C20): C15 at 20 fps, its pre-release counts, label and icons."""
    return 'precapture_frame_skip' in symbols


def edits(code, symbols):
    entries = {k: int(v['va'], 16) for k, v in symbols.items()}

    def branch(at, to, tail=False):
        d = to-at
        require(d % 4 == 0 and -(1 << 27) <= d < (1 << 27), 'Branch target out of range')
        return struct.pack('<I', (0x14000000 if tail else 0x94000000) | ((d // 4) & 0x3ffffff))

    def bl(at, to):
        return branch(at, to)

    values = {
        0xe0fe90: bl(0x40f6fe90, entries['precapture_history_entry']),
        0xd4915c: bytes.fromhex('e00317aa') + bl(0x40ea9160, entries['precapture_tdec_release_entry']) + bytes.fromhex('1f2003d5'),
        0xd43638: bl(0x40ea3638, entries['precapture_write_file']),
        0xd4eb60: bl(0x40eaeb60, entries['precapture_main_rc']),
        0xe0ff38: bl(0x40f6ff38, entries['precapture_current_entry']),
        0xee8e1c: bl(0x41048e1c, entries['precapture_y_size_entry']),
        0xd49fac: bl(0x40ea9fac, entries['precapture_y_alloc_entry']),
        0xd4eeec: bl(0x40eaeeec, entries['precapture_main_step']),
        0xd4ef10: bl(0x40eaef10, entries['precapture_main_step']),
        0x4d2ffc0: struct.pack('<I', 0x1082600),
        0x4d2ffc8: struct.pack('<I', 0x70c200),     # HN23: C60's E request (stock 0x70c000) + the record
        0x4d2ffcc: struct.pack('<I', 0x1082600),
        0x890000: code,
    }
    # HN13 Z: first instruction of the HSFC mode normaliser 0x41059c60 (cmp w0,#6) -> b precapture_area_mode
    values[0x41059c60 - 0x40160000] = branch(0x41059c60, entries['precapture_area_mode'], tail=True)
    for at, entry in (
        (0x40e99798, 'precapture_tenc_config'),
        (0x4104df14, 'precapture_e_alloc'),
        (0x40e997c8, 'precapture_e_size'),
        (0x40f98c4c, 'precapture_e_size'),
        (0x40f9a0b4, 'precapture_e_size'),
        (0x40ea9048, 'precapture_tdec_sel_entry'),
        (0x40e8904c, 'precapture_dec_job'),      # HN18: decode job builder call
        (0x40eaa4ec, 'precapture_dev_run_entry'),  # HN21: synchronous development job call in 0x40eaa498
        (0x403acce8, 'precapture_gui_mode'),
        (0x40f96c90, 'precapture_ready_margin'),
        (0x40d49044, 'precapture_ui_mode'),
        (0x40d424f0, 'precapture_ui_mode'),
    ):
        values[at - 0x40160000] = bl(at, entries[entry])
    if c20(symbols):                               # HN24 (C15 at 20 fps) only when the unit is built with PRECAPTURE_C20
        values[0x4cd59f0] = struct.pack('<3I', 6, 10, 20)    # C15 pre-release frames for 0.3/0.5/1 s (stock 5, 8, 15)
        for at in (0x40f807bc, 0x40f80a2c):                  # photo-frame selector calls
            values[at - 0x40160000] = bl(at, entries['precapture_frame_skip'])
    for at in (0x40ec4640, 0x40ec6a8c, 0x40f24e08, 0x41014b1c, 0x410e71f8):
        values[at - 0x40160000] = branch(at, entries['precapture_cap_update'], tail=at == 0x40ec4640)
    # These are callback pointers in the initialized-data image, not AArch64 branches.
    callbacks = {93: 'precapture_display_mode', 112: 'precapture_quality_code',
                 113: 'precapture_quality_code', 114: 'precapture_ordinary_code',
                 115: 'precapture_ordinary_code', 116: 'precapture_quality_star',
                 117: 'precapture_ordinary_star', 129: 'precapture_display_mode',
                 130: 'precapture_display_mode'}
    for index, entry in callbacks.items():
        at = 0x4b13000 + 0xa0295c558 + 0x68 * index + 0x30 - 0xa02808000
        values[at] = struct.pack('<Q', entries[entry])
    # HN21: the second full-size pass in the C15/C30 pipeline's stage list (initialized-data image), stock 0x40eaafc0
    values[0x44f385a0 - 0x40160000] = struct.pack('<Q', entries['precapture_pass2_step'])
    values[0x704938] = bl(0x40864938,entries['precapture_expand'])
    values[0x7103E4] = bl(0x408703E4,entries['precapture_dcf_item'])
    ids=entries['precapture_dcf_ids']
    require(0x409F0000<=ids<0x40A00000 and ids%4==0,'Pre-capture subscription table')
    require(code[ids-0x409F0000:ids-0x409F0000+36]==struct.pack('<9I',0x601,0x2000688,0x6000689,0x200172A,0x2000600,0x6000604,0x6000608,0x6000605,0x6000606),'Pre-capture subscription contents')
    values[0x70E908]=struct.pack('<I',0xD2800002|((ids&65535)<<5))
    values[0x70E918]=struct.pack('<I',0xF2A00002|((ids>>16)<<5))
    values[0x70E94C]=struct.pack('<I',0x52800003|(9<<5))
    return [dict(offset=at,new=raw,purpose='pre-capture code' if at==0x890000 else 'pre-capture hook/data '+hex(at)) for at,raw in sorted(values.items())]


# HN24: C15 takes 20 photos per second, so its release-mode label (UI string 2371, "C15" in every language; Arabic has
# a right-to-left mark in front) reads "C20". Same length: the two digits are replaced in place in each language's text.
LANG_TABLES, LANG_TEXT, C15_LABEL = 0x311C5A0, 0x387AF58, 2371   # EG offsets of the 36 offset-table / text pointers
ICON_15, ICON_20 = 2650, 2670   # PNG table 0x431d96d0 indexes: frames symbol with 15 / with 20 (64x32 icon set)
# (EG offset, format, record {index, kind 1 = image} before the value or None, where)
ICONS = (
    (0x4BC0646, '<H', None, 'release-mode icon list RAM 0xa028b5640 [S, CL, CH, C15, C30, C60, C120], entry 3'),
    (0x4B8B698, '<I', (3, 1), 'release-mode selection options RAM 0xa02880660, option 3'),
    (0x4B7DC90, '<I', (13, 1), 'shooting-display release-mode icons RAM 0xa02872700, code 13'),
)
# The shooting display draws the high-speed modes from (outlined 68x36, plain 64x32) image pairs [C15, C30, C60, C120] at
# VA 0x42ae7984 (read-only data; the CH speeds have their own pairs earlier in the same table). C15's pair -> the 20 icons.
PAIRS = 0x2987986                                               # EG offset of C15's pair
PAIRS_STOCK = (2713, 2650, 2708, 2643, 5929, 5930, 2709, 2644)   # C15, C30, C60, C120 (outlined, plain)
PAIR_20 = (2714, 2670)


def label_edits(eg):
    out, seen = [], set()
    for language in range(36):
        table = struct.unpack_from('<Q', eg, LANG_TABLES + 8 * language)[0] - BASE
        text = struct.unpack_from('<Q', eg, LANG_TEXT + 8 * language)[0] - BASE
        start, end = struct.unpack_from('<2i', eg, table + 4 * C15_LABEL)
        label = eg[text + start:text + end]
        at = label.find('C15'.encode('utf-16le'))
        require(at >= 0 and at % 2 == 0 and label.decode('utf-16le').lstrip('\u202b') == 'C15',
                f'C15 label: unexpected stock text in language {language}')
        offset = text + start + at + 2
        if offset in seen:
            continue
        seen.add(offset)
        out.append(dict(offset=offset, old='15'.encode('utf-16le'), new='20'.encode('utf-16le'),
                        purpose=f'pre-capture: C15 label reads C20 (language {language})'))
    # The release-mode icon of C15 is the frames symbol with "15" (image 2650 of the 64x32 set, shared with CH 15 fps); the
    # same set has the frames symbol with "20" (image 2670, CH 20 fps). Only C15's own references change; CH keeps its own.
    for off, fmt, ident, why in ICONS:
        require(eg[off - 8:off] == struct.pack('<2I', *ident) if ident else True, f'C15 icon: unexpected record at {off:#x}')
        require(struct.unpack_from(fmt, eg, off)[0] == ICON_15, f'C15 icon: unexpected stock image at {off:#x}')
        out.append(dict(offset=off, old=struct.pack(fmt, ICON_15), new=struct.pack(fmt, ICON_20),
                        purpose='pre-capture: C15 icon shows 20 (' + why + ')'))
    require(struct.unpack_from('<8H', eg, PAIRS) == PAIRS_STOCK, 'C15 icon: unexpected shooting-display pair table')
    out.append(dict(offset=PAIRS, old=struct.pack('<2H', *PAIRS_STOCK[:2]), new=struct.pack('<2H', *PAIR_20),
                    purpose='pre-capture: C15 icon shows 20 (shooting-display icon pairs VA 0x42ae7984, outlined + plain)'))
    return out
