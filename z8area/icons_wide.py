#!/usr/bin/env python3
"""A12 icons: image-area icons for area 3 (2.39:1) and area 6 (65:24), to be applied by the A12 builder on top of the A2h
compose result (and after the pipeline edits, see 'playback' below).  Design and evidence: README.md; PNGs: make_icons_wide.py
-> new/*.png + icons-wide.json (this module only reads them and checks their SHA-256).

apply(img, eg, at=0x40B84000, limit=0x40B90000, playback_index=None) -> det
  img  hb1.Image (put(va_or_off, bytes, why, expect=stock bytes | expect_zero, offset=...)); eg = stock EG (img.old)
  at   start of the icon block (alloc.json 'icons' region); everything new lives in [at, limit)

New icon numbers 7100h..7105h (virtual, as HB2's 7000h..7014h; the stock table 431D96D0 has 6242 records and is neither
copied nor extended, so colour-red's copied table (6242..6245) and HB2's 7000h..7014h stay disjoint):
  7100h menu 36x36 '2.39'  7101h menu 36x36 '2.71' (65:24)
  7102h LV   36x32 '2.39'  7103h LV   36x32 '2.71'
  7104h pb   28x28 '2.39'  7105h pb   28x28 '2.71'
Edits (each names the stock bytes it expects; A2h's two value-icon switch edits are replaced, see below):
  4032DC64  icon accessor by number pointer: mov x9,#0xcd58 -> b icon_res_idx   (7100h..7105h -> new records, else stock)
  4032DD34  icon accessor by number value:   mov x8,#0xcd58 -> b icon_res_val
  42AE72B4  LV icon table 0x42ae72a0[5] (GUI 0x2507 = 5 = area 3): 0 -> 7102h
  42AE72BC  LV icon table [7] (0x2507 = 7 = area 6; stock padding after the 7-entry table): 0 -> 7103h
  4041A9C0  LV updater bound: cmp x8,#6 -> cmp x8,#7
  42B35290  playback jump table, entries at the file-area index of areas 3 and 6 (stock NEF codes: 3 and 7) -> two
            2-instruction caves 'mov w1,#7104h/7105h; b 4064E86C' (the stock cases are 'mov w1,#icon; b 4064E86C')
  405DBD78, 405D99F4  'Choose image area' value icon switches (page 1067; A2h: 1/8/4 stock, 2 -> D22h, else D25h, 13
            instructions in place): A2h's edit is removed (its bytes checked) and the range rewritten as a table lookup
            u16[9] = D25 D23 D22 7100 1173 D25 7101 D25 1132 (value > 8 -> D25h), still 13 instructions in place
Hook chaining: both hooks fall through by executing the displaced stock instruction and branching to site + 4, like HB2's
tier_star_res_idx/val at the same two sites; a combined package keeps one hook per site and chains the two ranges.
"""
import hashlib, json, struct, sys
from pathlib import Path

H = Path(__file__).resolve().parent
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM  # noqa: E402

md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
BASE = 0x40160000
sha = lambda x: hashlib.sha256(x).hexdigest()
RES_IDX, RES_VAL = 0x4032DC64, 0x4032DD34
LV_TABLE, LV_BOUND = 0x42AE72A0, 0x4041A9C0
PB_TABLE, PB_JOIN, PB_SWITCH = 0x42B35290, 0x4064E86C, 0x4064E770
NEF_CODE, CODE_TO_PB = 0x440C6D20, 0x440E56D0          # area -> file area code; code - 1 -> playback index (13 entries)
SWITCHES = {0x405DBD78: 21, 0x405D99F4: 1}             # entry (w21) / refresh (w1)
NEW_BASE, NEW_COUNT = 0x7110, 6
NUM = {('menu_36x36', 3): 0x7110, ('menu_36x36', 6): 0x7111, ('lv_36x32', 3): 0x7112, ('lv_36x32', 6): 0x7113,
       ('pb_28x28', 3): 0x7114, ('pb_28x28', 6): 0x7115}
VALUE_ICONS = [0xD25, 0xD23, 0xD22, 0x7110, 0x1173, 0xD25, 0x7111, 0xD25, 0x1132]   # value 0..8 (5, 7: FX default as stock)
FAM_SIZE = {'menu_36x36': (36, 36), 'lv_36x32': (36, 32), 'pb_28x28': (28, 28)}
HOOK_IDX, HOOK_VAL, PB_CAVES, MENU_TAB, RECORDS, PNGS = 0x000, 0x080, 0x100, 0x120, 0x140, 0x200


# ---------------------------------------------------------------- A64 encoders (checked with capstone below)
def b_(at, to): d = (to - at) >> 2; assert -(1 << 25) <= d < 1 << 25; return 0x14000000 | d & 0x3FFFFFF
def bcond(at, to, c): d = (to - at) >> 2; assert -(1 << 18) <= d < 1 << 18; return 0x54000000 | (d & 0x7FFFF) << 5 | c
def adr(at, to, rd): o = to - at; assert -(1 << 20) <= o < 1 << 20; return 0x10000000 | (o & 3) << 29 | ((o >> 2) & 0x7FFFF) << 5 | rd
def subw_i(rd, rn, imm, sh=0): return 0x51000000 | sh << 22 | imm << 10 | rn << 5 | rd
def cmpw_i(rn, imm): return 0x7100001F | imm << 10 | rn << 5
def cmpx_i(rn, imm): return 0xF100001F | imm << 10 | rn << 5
def add_uxtw(rd, rn, rm, sh): return 0x8B204000 | rm << 16 | sh << 10 | rn << 5 | rd
def ldrw(t, n, imm): return 0xB9400000 | (imm >> 2) << 10 | n << 5 | t
def strw(t, n, imm): return 0xB9000000 | (imm >> 2) << 10 | n << 5 | t
def ldrx(t, n, imm): return 0xF9400000 | (imm >> 3) << 10 | n << 5 | t
def strx(t, n, imm): return 0xF9000000 | (imm >> 3) << 10 | n << 5 | t
def ldrh(t, n, imm): return 0x79400000 | (imm >> 1) << 10 | n << 5 | t
def strh(t, n, imm): return 0x79000000 | (imm >> 1) << 10 | n << 5 | t
def ldrh_uxtw1(t, n, m): return 0x78605800 | m << 16 | n << 5 | t
def movzw(rd, imm): return 0x52800000 | imm << 5 | rd
def movzx(rd, imm, hw=0): return 0xD2800000 | hw << 21 | imm << 5 | rd
def movkx(rd, imm, hw): return 0xF2800000 | hw << 21 | imm << 5 | rd
RET, NOP, HS, HI = 0xD65F03C0, 0xD503201F, 2, 8


def W(*ws): return struct.pack('<%dI' % len(ws), *ws)
def text(code, at): return [f'{i.mnemonic} {i.op_str}'.strip() for i in md.disasm(code, at)]


def hook_idx(at, rec):
    """4032DC64 (x0 = &number, x1 = out: u16 flags +0, u32 bytes +4, u64 PNG +10h, as the stock accessor writes)."""
    w = [ldrw(9, 0, 0), subw_i(9, 9, 7, 1), subw_i(9, 9, 0x110), cmpw_i(9, NEW_COUNT), None, None, add_uxtw(10, 10, 9, 4),
         ldrh(9, 10, 0), strh(9, 1, 0), ldrw(9, 10, 4), strw(9, 1, 4), ldrx(9, 10, 8), strx(9, 1, 0x10), RET,
         movzx(9, 0xCD58), None]
    w[4] = bcond(at + 16, at + 4 * 14, HS); w[5] = adr(at + 20, rec, 10); w[15] = b_(at + 60, RES_IDX + 4)
    want = ['ldr w9, [x0]', 'sub w9, w9, #7, lsl #12', 'sub w9, w9, #0x110', f'cmp w9, #{NEW_COUNT}', f'b.hs #{at + 56:#x}',
            f'adr x10, #{rec:#x}', 'add x10, x10, w9, uxtw #4', 'ldrh w9, [x10]', 'strh w9, [x1]', 'ldr w9, [x10, #4]',
            'str w9, [x1, #4]', 'ldr x9, [x10, #8]', 'str x9, [x1, #0x10]', 'ret', 'mov x9, #0xcd58', f'b #{RES_IDX + 4:#x}']
    c = W(*w); assert text(c, at) == want, text(c, at); return c, want


def hook_val(at, rec):
    """4032DD34 (w0 = number, x1 = out u32 bytes, x2 = out u64 PNG, as the stock accessor writes)."""
    w = [subw_i(9, 0, 7, 1), subw_i(9, 9, 0x110), cmpw_i(9, NEW_COUNT), None, None, add_uxtw(10, 10, 9, 4), ldrw(9, 10, 4),
         strw(9, 1, 0), ldrx(9, 10, 8), strx(9, 2, 0), RET, movzx(8, 0xCD58), None]
    w[3] = bcond(at + 12, at + 44, HS); w[4] = adr(at + 16, rec, 10); w[12] = b_(at + 48, RES_VAL + 4)
    want = ['sub w9, w0, #7, lsl #12', 'sub w9, w9, #0x110', f'cmp w9, #{NEW_COUNT}', f'b.hs #{at + 44:#x}', f'adr x10, #{rec:#x}',
            'add x10, x10, w9, uxtw #4', 'ldr w9, [x10, #4]', 'str w9, [x1]', 'ldr x9, [x10, #8]', 'str x9, [x2]', 'ret',
            'mov x8, #0xcd58', f'b #{RES_VAL + 4:#x}']
    c = W(*w); assert text(c, at) == want, text(c, at); return c, want


def switch(site, r, table):
    w = [movzw(r, 0xD25), cmpw_i(0, 8), bcond(site + 8, site + 52, HI), movzx(8, table & 0xFFFF), movkx(8, table >> 16, 1),
         ldrh_uxtw1(r, 8, 0)] + [NOP] * 7
    want = [f'mov w{r}, #0xd25', 'cmp w0, #8', f'b.hi #{site + 52:#x}', f'mov x8, #{table & 0xFFFF:#x}',
            f'movk x8, #{table >> 16:#x}, lsl #16', f'ldrh w{r}, [x8, w0, uxtw #1]'] + ['nop'] * 7
    c = W(*w); assert len(c) == 52 and text(c, site) == want, text(c, site); return c, want


def a2h_switch_text(r, site):
    """A2g/A2h form of the switch (build_a2g.py): mov wR,#0xd25 + (v, icon) in (1,D23) (8,1132) (4,1173) (2,D22)."""
    return [f'mov w{r}, #0xd25'] + sum(([f'cmp w0, #{v}', f'mov w8, #{ic:#x}', f'csel w{r}, w8, w{r}, eq']
                                        for v, ic in ((1, 0xD23), (8, 0x1132), (4, 0x1173), (2, 0xD22))), [])


def pngs(icons_json=None):
    """icons_json: another icon set in the icons-wide.json format (files relative to that JSON); default = A12's set."""
    jp = Path(icons_json) if icons_json else H / 'icons/wide.json'
    d = json.loads(jp.read_text()); out = {}
    for e in d['icons']:
        data = (jp.parent / e['file']).read_bytes(); assert sha(data) == e['png']['sha256'] and len(data) == e['png']['bytes'], e['file']
        assert data[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', data[16:24]) == FAM_SIZE[e['family']], e['file']
        assert int(e['number'], 16) == NUM[(e['family'], e['area'])]
        out[(e['family'], e['area'])] = (data, e)
    assert len(out) == NEW_COUNT; return out, sha(jp.read_bytes()), jp.name


def u32(img, va): return struct.unpack_from('<I', img.new, va - BASE)[0]
def u64(img, va): return struct.unpack_from('<Q', img.new, va - BASE)[0]


def apply(img, eg, at=0x40B84000, limit=0x40B90000, playback_index=None, icons_json=None):
    assert at % 0x100 == 0 and not any(img.new[at - BASE:limit - BASE]), 'icon block not zero'
    icons, json_sha, json_name = pngs(icons_json); det = dict(numbers={}, block=dict(at=hex(at), limit=hex(limit)))
    # 1 PNGs and virtual records (u16 flags, u16 0, u32 bytes, u64 PNG; flags 100h as every stock record of the families)
    order = sorted(icons, key=lambda k: NUM[k]); blob, recs, rows = bytearray(), bytearray(), []
    for k in order:
        data, e = icons[k]; p = at + PNGS + len(blob)
        recs += struct.pack('<HHIQ', 0x100, 0, len(data), p); blob += data; blob += bytes(-len(blob) % 16)
        rows.append(dict(number=hex(NUM[k]), family=k[0], area=k[1], text=e['text'], png_va=hex(p), bytes=len(data), sha256=e['png']['sha256']))
        det['numbers'].setdefault(k[0], {})[k[1]] = hex(NUM[k])
    end = at + PNGS + len(blob); assert end <= limit
    for fam in ('menu_36x36', 'lv_36x32', 'pb_28x28'):
        f, s, z0, z1, p = struct.unpack_from('<IIIIQ', eg, 0x30796D0 + 0x18 * {'menu_36x36': 0x1173, 'lv_36x32': 0x84B, 'pb_28x28': 0x1434}[fam])
        assert f == 0x100 and z0 == z1 == 0
    rec = at + RECORDS
    img.put(rec, bytes(recs), f'A12 icon records {NEW_BASE:#x}..{NEW_BASE + NEW_COUNT - 1:#x} (u16 flags 100h, u16 0, u32 bytes, u64 PNG)', expect_zero=True)
    texts = ' / '.join(dict.fromkeys(icons[k][1]['text'] for k in order))
    img.put(at + PNGS, bytes(blob), f'A12 icon PNGs ({texts} for menu 36x36, LV 36x32, playback 28x28; {json_name} {json_sha[:12]})', expect_zero=True)
    # 2 accessor hooks
    hooks = {}
    for site, cave, fn, stock_txt in ((RES_IDX, at + HOOK_IDX, hook_idx, 'mov x9, #0xcd58'), (RES_VAL, at + HOOK_VAL, hook_val, 'mov x8, #0xcd58')):
        assert text(eg[site - BASE:site - BASE + 4], site) == [stock_txt]
        c, want = fn(cave, rec)
        img.put(cave, c, f'A12 icon accessor hook for {site:#x}: numbers {NEW_BASE:#x}..{NEW_BASE + NEW_COUNT - 1:#x} -> A12 records, '
                f'else the displaced "{stock_txt}" and b {site + 4:#x}', expect_zero=True)
        img.put(site, W(b_(site, cave)), f'icon accessor {site:#x}: {stock_txt} -> b {cave:#x} (A12 numbers {NEW_BASE:#x}+)',
                expect=eg[site - BASE:site - BASE + 4])
        hooks[hex(site)] = dict(cave=hex(cave), words=c.hex(), text=want)
    # 3 shooting screen (element 0x25)
    assert u32(img, LV_TABLE + 20) == 0 and u32(img, LV_TABLE + 28) == 0 and u32(img, LV_TABLE + 32) == 0xA02
    assert text(eg[LV_BOUND - BASE:LV_BOUND - BASE + 8], LV_BOUND) == ['cmp x8, #6', 'b.hi #0x4041a9e0']
    img.put(LV_TABLE + 20, W(NUM[('lv_36x32', 3)]), 'LV image-area icon table 0x42ae72a0[5] (GUI 0x2507 = 5 = area 3): 0 -> 2.39 icon', expect=W(0))
    img.put(LV_TABLE + 28, W(NUM[('lv_36x32', 6)]), 'LV image-area icon table 0x42ae72a0[7] (0x2507 = 7 = area 6; stock padding): 0 -> 65:24 icon', expect=W(0))
    img.put(LV_BOUND, W(cmpx_i(8, 7)), 'LV image-area icon updater 0x4041a9ac bound: cmp x8,#6 -> #7 (index 7 = area 6)', expect=eg[LV_BOUND - BASE:LV_BOUND - BASE + 4])
    # 4 playback (index of the file area code; follows the NEF code table as it is in img at this point)
    idx = {}
    for area in (3, 6):
        code = u32(img, NEF_CODE + 4 * area)
        assert 1 <= code <= 13, f'area {area}: file area code {code} outside the playback table 0x440e56d0 (codes 1..13)'
        idx[area] = playback_index[area] if playback_index else u32(img, CODE_TO_PB + 4 * (code - 1))
        assert 0 <= idx[area] <= 13
    assert idx[3] != idx[6]
    pb = {}
    for k, area in enumerate((3, 6)):
        cave = at + PB_CAVES + 8 * k; n = NUM[('pb_28x28', area)]; c = W(movzw(1, n), b_(cave + 4, PB_JOIN))
        assert text(c, cave) == [f'mov w1, #{n:#x}', f'b #{PB_JOIN:#x}']
        e = PB_TABLE + 8 * idx[area]; old = eg[e - BASE:e - BASE + 8]; t = struct.unpack('<Q', old)[0]
        img.put(cave, c, f'A12 playback icon case area {area}: mov w1,#{n:#x}; b {PB_JOIN:#x}', expect_zero=True)
        img.put(e, struct.pack('<Q', cave), f'playback image-area icon jump table 0x42b35290[{idx[area]}] (area {area} files): {t:#x} -> {cave:#x}', expect=old)
        pb[area] = dict(file_area_code=u32(img, NEF_CODE + 4 * area), index=idx[area], stock_target=hex(t), stock_case=text(eg[t - BASE:t - BASE + 4], t)[0],
                        cave=hex(cave), number=hex(n))
    # 5 page 1067 value icon switches (replace A2h's in-place switch)
    tab = at + MENU_TAB
    img.put(tab, struct.pack('<9H', *VALUE_ICONS), 'A12 "Choose image area" value icon table u16[9] by value 0..8', expect_zero=True)
    sw = {}
    for site, r in SWITCHES.items():
        hit = [e for e in img.edits if e['offset'] == site - BASE and e['end'] == site - BASE + 52]
        assert len(hit) == 1 and hit[0]['purpose'].startswith(f'"Choose image area" value icon switch at {site:#x}'), (hex(site), [e['purpose'] for e in hit])
        e = hit[0]; assert text(bytes(img.new[site - BASE:site - BASE + 52]), site) == a2h_switch_text(r, site)
        assert e['old'] == eg[site - BASE:site - BASE + 52]
        img.new[e['offset']:e['end']] = e['old']; img.edits.remove(e)
        c, want = switch(site, r, tab)
        img.put(site, c, f'"Choose image area" value icon switch at {site:#x} (A12): table {tab:#x} by value 0..8 '
                f'(3 -> {VALUE_ICONS[3]:#x}, 6 -> {VALUE_ICONS[6]:#x}; 2 -> D22h as A2h), > 8 -> D25h', expect=eg[site - BASE:site - BASE + 52])
        sw[hex(site)] = dict(register=f'w{r}', words=c.hex(), text=want, replaced_a2h_edit=dict(purpose=e['purpose'], sha256=sha(e['new'])))
    det.update(menu_row_icon={3: hex(NUM[('menu_36x36', 3)]), 6: hex(NUM[('menu_36x36', 6)])},
               records=rows, records_va=hex(rec), hooks=hooks,
               lv=dict(table=hex(LV_TABLE), index={3: 5, 6: 7}, bound=hex(LV_BOUND)), playback=pb,
               value_icon_switches=dict(table=hex(tab), values=[hex(x) for x in VALUE_ICONS], sites=sw),
               icons_json_sha256=json_sha, block_used=[hex(at), hex(end)])
    return det


if __name__ == '__main__':
    # self-test of the encoders against capstone only (no image)
    hook_idx(0x40B84000, 0x40B84140); hook_val(0x40B84080, 0x40B84140); [switch(s, r, 0x40B84120) for s, r in SWITCHES.items()]
    print('encoders ok;', len(pngs()[0]), 'PNGs')
