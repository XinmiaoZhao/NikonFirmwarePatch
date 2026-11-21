import struct
import json
from pathlib import Path
H = Path(__file__).resolve().parent
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from . import blocks as blk, layout as hb1
sha, BASE, data_off = hb1.sha, hb1.BASE, hb1.data_off


DATA_AT, DATA_END = 0x40B7C000, 0x40B7D000
SIZES = json.loads((H / 'design-sizes.json').read_text())['design']['4:3']
P = blk.P
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)

# 4:3 geometry (A0 design): JPEG L 7344x5504, crop edge (8, 8), origin (460, 0); live view 2444x1832 at (156, 2)
STILL43 = dict(W=7344, H=5504, cx=8, cy=8, x0=460, y0=0)
LIVE43 = dict(W=2444, H=1832, ox=156, oy=2)
CELLS43 = (26, 20, 136, 136)      # still statistics grid: 26 x 20 cells of 136 (half-size units), 3536 x 2720 of 3672 x 2752
REC0, REC2 = (160, 120), (336, 256)
DISPLAY43 = [(640, 480), (320, 240), (1024, 768), (1280, 960), (1440, 1080), (960, 720), (480, 360), (256, 192)]
DISPLAY54 = [(600, 480), (300, 240), (960, 768), (1200, 960), (1320, 1056), (880, 704), (440, 352), (240, 192)]
SIZE_TABLES = {'raw': (0xA0297A520, 3), 'jpeg_lms': (0xA0297A568, 3), 'window': (0xA0297A5B0, 3),
               'jpeg_out': (0xA0297A688, 6)}
CROP_TABLES = (0xA0297A6D0, 0xA0297A718)


def u32(eg, va): return struct.unpack_from('<I', eg, data_off(va))[0]
def u64(eg, va): return struct.unpack_from('<Q', eg, data_off(va))[0]
def W(*ws): return struct.pack('<%dI' % len(ws), *ws)
def text(word, at): return ' '.join(next(md.disasm(struct.pack('<I', word), at))[i] for i in (2, 3)).strip() if False else \
    (lambda i: f'{i.mnemonic} {i.op_str}'.strip())(next(md.disasm(struct.pack('<I', word), at)))


def s2_block(kind, g, cells, rec0, rec1, rec2, donor):
    """0x38 geometry block of 0x410627f4 (rules: README section 2.3)."""
    w = list(donor)
    if kind == 0:
        nx, ny, bw, bh = cells
        w[1] = P(g['x0'] + g['cx'], g['y0'] + g['cy'])
        hw, hh = g['W'] // 2, g['H'] // 2
        w[2] = P(hw, hh); w[3] = P(hw - 8, hh); w[12] = w[3]; w[13] = P(g['W'], g['H'])
        w[4] = P(nx * bw, ny * bh); w[5] = P(nx * bw, ny * bw); w[6] = P(2 * nx, 2 * ny)
        w[7] = P(*rec0); w[9] = P(*rec2); w[11] = P(*rec2)
    else:
        w[1] = P(g['ox'], g['oy'])
        hw = blk.f8(g['W'] // 2)
        w[2] = P(hw, blk.f8(g['H'] // 2)); w[3] = w[2]; w[12] = w[3]; w[13] = P(g['W'], g['H'])
        w[7] = P(*rec0); w[8] = P(*rec1); w[9] = P(*rec2); w[11] = P(*rec2)
    return w


def s2_check(eg):
    """Rebuild the stock kind-0 0x38 blocks of FX/DX/16:9/1:1 from geometry; return differing words."""
    t0, k0 = blk.ptrs(eg, blk.T['s0']), blk.ptrs(eg, blk.T['k0']); diffs = []
    for a, g in blk.STILL.items():
        stock = blk.words(eg, t0[a], 14); k = blk.words(eg, k0[a], 0x178 // 4)
        c = k[0x1c // 4] >> 16; cells = (c & 0xff, c >> 8, k[0x18 // 4] >> 16, k[0x18 // 4] & 0xffff)
        rec0 = (k[0x10c // 4] & 0xffff, k[0x10c // 4] >> 16); rec2 = (k[0x134 // 4] & 0xffff, k[0x134 // 4] >> 16)
        got = s2_block(0, g, cells, rec0, None, rec2, stock)
        hh = g['H'] // 2
        if a == 1: got[2] = P(g['W'] // 2, hh // 16 * 16); got[3] = P(g['W'] // 2 - 8, hh // 16 * 16); got[12] = got[3]
        diffs += [(a, hex(4 * i), hex(x), hex(y)) for i, (x, y) in enumerate(zip(stock, got)) if x != y]
    return diffs


def live_block(eg):
    """4:3 live-view 0x178 block: the stock 1:1 live-view block (full height, full readout) with the width-dependent fields
    recomputed: crop, grid x origins (20 x 20 cells of 44 kept, centred), scaler records 0/1/2/3/4 for a 2432 x 1824 source,
    processing width and its reciprocal."""
    w = list(blk.words(eg, blk.ptrs(eg, blk.T['k1'])[8], 0x178 // 4))
    g = LIVE43
    w[0] = P(g['W'], g['ox']); w[1] = P(g['H'], g['oy'])
    nx, ny, bw = 20, 20, 44
    xs1 = ((g['W'] // 2 - nx * bw) // 2) & ~1; xs2 = xs1 - 2
    w[0x10 // 4] = P(0xa7, xs1)
    for o in (0x7c, 0x90): w[o // 4] = P(xs2, w[o // 4] >> 16)
    for o in (0x84, 0x98): w[o // 4] = P(w[o // 4] & 0xffff, xs2)
    sw, sh = blk.f16(g['W']), blk.f16(g['H'])                     # 2432 x 1824
    ratio = lambda ow, oh: P(64 * sw // ow, 64 * sh // oh)
    w[0x104 // 4], w[0x10c // 4] = ratio(*REC0), P(*REC0)
    w[0x118 // 4], w[0x120 // 4] = ratio(592, 448), P(592, 448)
    w[0x12c // 4], w[0x134 // 4] = ratio(*REC2), P(*REC2)
    w[0x140 // 4], w[0x144 // 4] = ratio(*REC2), P(*REC2)
    w[0x15c // 4] = P(*REC2)
    wp = blk.f8(g['W'] // 2)                                      # 1216
    w[0x160 // 4] = wp << 16; w[0x168 // 4] = ((1 << 20) // (wp * 4)) << 16
    return w, dict(xs1=xs1, xs2=xs2, source=[sw, sh], processing_width=wp, record1=[592, 448])


def compose(eg):
    img = hb1.Image(eg); det = {}
    # 1. per-slot size tables (slot 2 entries are stock zero)
    for name, (table, n) in SIZE_TABLES.items():
        p = u64(eg, table + 16)
        img.put(data_off(p), W(*[int(x, 16) for x in SIZES['words'][name]][:n]), f'{name} table {table:#x} slot 2', expect_zero=True, offset=True)
    for name, table in (('quarter_raw', 0xA0297A5F8), ('quarter_jpeg', 0xA0297A640)):
        p = u64(eg, table + 16); img.put(data_off(p), W(int(SIZES['words'][name], 16)), f'{name} table {table:#x} slot 2', expect_zero=True, offset=True)
    p = u64(eg, CROP_TABLES[0] + 16); assert p == u64(eg, CROP_TABLES[1] + 16)   # both crop-edge tables share slots 1..8
    img.put(data_off(p), W(*[int(x, 16) for x in SIZES['words']['crop']]), 'crop-edge tables 0xa0297a6d0/0xa0297a718 slot 2 (shared entry)', expect_zero=True, offset=True)
    img.put(data_off(0xA02A948A0 + 8), W(int(SIZES['words']['origin'], 16)), 'origin table slot 2: (460, 0)', expect_zero=True, offset=True)
    img.put(data_off(0xA02A2460C + 0x48 * 2), W(*SIZES['t1']), 'JPEG size estimate T1 slot 2 (18 words)', expect_zero=True, offset=True)
    # 2. preview class of area 2: 5:4 -> 4:3
    img.put(data_off(0xA02A5E490), W(3), 'area -> preview class table, area 2: 2 (5:4) -> 3 (4:3)', expect=W(2), offset=True)
    # 3. 9x9 display sizes, column 2
    rows = struct.unpack_from('<9Q', eg, data_off(0xA0297A760))
    for r in range(8):
        img.put(data_off(rows[r] + 8), W(P(*DISPLAY43[r])), f'display-size row {r} area 2: {DISPLAY54[r]} -> {DISPLAY43[r]}',
                expect=W(P(*DISPLAY54[r])), offset=True)
    # 4. blocks
    k0 = blk.block178(0, STILL43, CELLS43, REC0, REC2, blk.words(eg, blk.ptrs(eg, blk.T['k0'])[0], 0x178 // 4), 2)
    k1, live = live_block(eg)
    s0 = s2_block(0, STILL43, CELLS43, REC0, None, REC2, blk.words(eg, blk.ptrs(eg, blk.T['s0'])[8], 14))
    s1 = s2_block(1, LIVE43, None, REC0, (592, 448), REC2, blk.words(eg, blk.ptrs(eg, blk.T['s1'])[8], 14))
    s1[4] = P(880, 880); s1[5] = P(880, 880); s1[6] = P(40, 40)    # 1:1 live grid (20 x 20 of 44, half units) kept
    data = bytearray()
    at = {}
    for name, ws in (('k0_still_178', k0), ('k1_live_178', k1), ('s0_still_38', s0), ('s1_live_38', s1)):
        at[name] = DATA_AT + len(data); data += W(*ws)
        while len(data) % 16: data += b'\0'
    assert DATA_AT + len(data) <= DATA_END and hb1.GAP[0] <= DATA_AT and DATA_END <= hb1.GAP[1]
    img.put(DATA_AT, bytes(data), '4:3 parameter blocks (kind 0/1 of 0x410622d4 and 0x410627f4)', expect_zero=True)
    for table, name in ((blk.T['k0'], 'k0_still_178'), (blk.T['k1'], 'k1_live_178'), (blk.T['s0'], 's0_still_38'), (blk.T['s1'], 's1_live_38')):
        img.put(data_off(table + 16), struct.pack('<Q', at[name]), f'block table {table:#x} slot 2 -> {name}', expect=bytes(8), offset=True)
    for table in (0xA02A96110, 0xA02A96220):                      # kind 0x18: FX-readout block, as 16:9 and 1:1
        fx = u64(eg, table)
        img.put(data_off(table + 16), struct.pack('<Q', fx), f'kind 0x18 table {table:#x} slot 2 -> FX block {fx:#x}', expect=bytes(8), offset=True)
    det['blocks'] = {k: hex(v) for k, v in at.items()}; det['live'] = live
    det['block_words'] = dict(k0_still_178=[hex(x) for x in k0], k1_live_178=[hex(x) for x in k1], s0_still_38=[hex(x) for x in s0], s1_live_38=[hex(x) for x in s1])
    # 5. menu: page 1068 row 2
    rows_va = struct.unpack_from('<Q', eg, 0x4BC2C10 + 0x50 * 1068 + 0x10)[0]; row2 = rows_va + 44 * 2
    stock_row = struct.unpack_from('<11I', eg, data_off(row2))
    assert stock_row == (0x43A, 0xFFFF, 0xFFFF, 0, 0x101000, 0xFFFF, 0x2BE9, 0x50005, 0xFFFFFFFF, 0xFFFFFFFF, 2), stock_row
    img.put(data_off(row2), W(0x784), 'page 1068 row 2 label: 0x43a "Disable" -> 0x784 "4:3"', expect=W(0x43A), offset=True)
    img.put(data_off(row2 + 0x10), W(0x101001), 'page 1068 row 2 flags 0x101000 -> 0x101001 (as the other rows)', expect=W(0x101000), offset=True)
    # entry callback: cursor by value (0 FX, 1 DX, 2 4:3, 4 16:9, 8 1:1); no hide of 0x2be9
    site, n = 0x405DBE24, 20
    stock = ['cmp w0, #8', 'b.eq #0x405dbe44', 'cmp w0, #4', 'b.eq #0x405dbe4c', 'cmp w0, #1', 'b.ne #0x405dbe54',
             'mov w20, #0x29b8', 'b #0x405dbe58', 'mov w20, #0x2bea', 'b #0x405dbe58', 'mov w20, #0x2c5f', 'b #0x405dbe58',
             'mov w20, #0x2beb', 'mov w1, #0x2be9', 'mov x0, x19', 'bl #0x403af870', 'mov w1, w0', 'mov w2, #1', 'mov x0, x19',
             'bl #0x403b1ed0']
    old = struct.unpack_from('<%dI' % n, eg, site - BASE)
    assert [text(x, site + 4 * i) for i, x in enumerate(old)] == stock, [text(x, site + 4 * i) for i, x in enumerate(old)]
    movz = lambda rd, imm: 0x52800000 | imm << 5 | rd
    cmp = lambda imm: 0x7100001F | imm << 10
    csel_eq = 0x1A800000 | 20 << 16 | 8 << 5 | 20                 # csel w20, w8, w20, eq
    new = [movz(20, 0x2BEB)]
    for value, item in ((1, 0x29B8), (2, 0x2BE9), (4, 0x2C5F), (8, 0x2BEA)): new += [cmp(value), movz(8, item), csel_eq]
    new += [0xD503201F] * (n - len(new))
    want = ['mov w20, #0x2beb'] + sum([[f'cmp w0, #{v}', f'mov w8, #{it:#x}', 'csel w20, w8, w20, eq'] for v, it in
                                       ((1, 0x29B8), (2, 0x2BE9), (4, 0x2C5F), (8, 0x2BEA))], []) + ['nop'] * 7
    assert [text(x, site + 4 * i) for i, x in enumerate(new)] == want
    img.put(site, W(*new), 'choose-image-area entry 0x405DBE0C: cursor by value incl. 2 -> row 0x2be9; stock hide of 0x2be9 removed',
            expect=W(*old))
    det['menu'] = dict(row=hex(row2), entry_site=hex(site), entry_code=want)
    # 6. loader end
    mov = lambda v: struct.pack('<II', 0xD2800008 | (v & 0xFFFF) << 5, 0xF2A00008 | (v >> 16) << 5)
    assert hb1.LOADER_END < DATA_END <= min(hb1.SECTION_VA + hb1.SECTION_ROOM, hb1.GAP[1])
    img.put(hb1.LOADER_SITE, mov(DATA_END), f'text loader: copy section {hb1.SECTION_VA:#x} up to {DATA_END:#x} instead of {hb1.LOADER_END:#x}',
            expect=mov(hb1.LOADER_END), offset=True)
    return img, det
