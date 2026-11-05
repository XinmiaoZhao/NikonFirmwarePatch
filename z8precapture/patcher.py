"""Pre-capture HN11 public adapter (HN13: DX): feature windows only; no identity or loader edits."""
import struct
from z8prores.package import require
BASE=0x40160000

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
        0xd4915c: bytes.fromhex('e00317aa') + bl(0x40ea9160, entries['precapture_tdec_release']) + bytes.fromhex('1f2003d5'),
        0xd43638: bl(0x40ea3638, entries['precapture_write_file']),
        0xd4eb60: bl(0x40eaeb60, entries['precapture_main_rc']),
        0xe0ff38: bl(0x40f6ff38, entries['precapture_current_entry']),
        0xee8e1c: bl(0x41048e1c, entries['precapture_y_size_entry']),
        0xd49fac: bl(0x40ea9fac, entries['precapture_y_alloc_entry']),
        0xd4eeec: bl(0x40eaeeec, entries['precapture_main_step']),
        0xd4ef10: bl(0x40eaef10, entries['precapture_main_step']),
        0x4d2ffc0: struct.pack('<I', 0x1082600),
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
        (0x403acce8, 'precapture_gui_mode'),
        (0x40f96c90, 'precapture_ready_margin'),
        (0x40d49044, 'precapture_ui_mode'),
        (0x40d424f0, 'precapture_ui_mode'),
    ):
        values[at - 0x40160000] = bl(at, entries[entry])
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
    values[0x704938] = bl(0x40864938,entries['precapture_expand'])
    values[0x7103E4] = bl(0x408703E4,entries['precapture_dcf_item'])
    ids=entries['precapture_dcf_ids']
    require(0x409F0000<=ids<0x40A00000 and ids%4==0,'Pre-capture subscription table')
    require(code[ids-0x409F0000:ids-0x409F0000+36]==struct.pack('<9I',0x601,0x2000688,0x6000689,0x200172A,0x2000600,0x6000604,0x6000608,0x6000605,0x6000606),'Pre-capture subscription contents')
    values[0x70E908]=struct.pack('<I',0xD2800002|((ids&65535)<<5))
    values[0x70E918]=struct.pack('<I',0xF2A00002|((ids>>16)<<5))
    values[0x70E94C]=struct.pack('<I',0x52800003|(9<<5))
    return [dict(offset=at,new=raw,purpose='pre-capture code' if at==0x890000 else 'pre-capture hook/data '+hex(at)) for at,raw in sorted(values.items())]
