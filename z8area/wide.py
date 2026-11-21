#!/usr/bin/env python3
"""A12 pipeline: the capture and live-view side of the two full-width ratios, applied on top of the A2h composition.

  area 3 = 2.39:1  RAW 8280x3472 at (0,1024), JPEG L 8256x3456   (stock: empty slot, old 1.2x)
  area 6 = 65:24   RAW 8280x3064 at (0,1228), JPEG L 8256x3048   (stock: table values only, no select block)

Both are the FX frame with the top and bottom cut, so every rule below takes the stock 16:9 (area 4) entry, which is the
FX frame with less cut, as its model and is asserted to reproduce the stock 16:9 (and where it applies, FX) values first.
Preview classes: stock 0 3:2, 1 16:9, 2 5:4 (unused since A2), 3 4:3, 4 1:1; this module adds 5 = 2.39:1 and 6 = 65:24 and
leaves class 2 as stock, so the five class tables and both live-view window tables are moved to the private block with
7 classes.  Playback (preview records, playback categories, decode sizes) is not in this module.

apply(img, eg) -> det; img is the A2h hb1.Image.  Edits that replace an A2c/A2h hook site drop that edit first and
branch to a front cave that handles areas 3 and 6 and otherwise tail-branches to the unchanged A2c/A2h cave, so the 4:3
code path executes the same instructions as in A2h.
"""
import json, math, struct
from pathlib import Path

H = Path(__file__).resolve().parent
ALLOC = json.loads((H / 'alloc.json').read_text())
DESIGN = json.loads((H / 'design-sizes.json').read_text())['design']
CAVE_AT, CAVE_END = (int(x, 16) for x in ALLOC['regions']['pipeline'][:2])
TAB_AT, TAB_END = (int(x, 16) for x in ALLOC['regions']['tables'][:2])
LOADER_END = int(ALLOC['loader_end'], 16)
ROM, DOFF, DVA = 0x40160000, 0x4B13000, 0xA02808000
FX_JPEG = (8256, 5504)

AREAS = {3: dict(name='2.39:1', design='2.39:1', cls=5), 6: dict(name='65:24', design='65:24', cls=6)}
for a, s in AREAS.items():
    d = DESIGN[s['design']]
    s.update(raw=tuple(d['raw']), jpeg=tuple(d['jpeg_l']), origin=tuple(d['origin']), crop=tuple(d['crop']), words=d['words'], t1=d['t1'])
    s['R'] = s['jpeg'][0] / s['jpeg'][1]                       # JPEG L ratio, used for every derived height


def off(va): return va - DVA + DOFF if va >= DVA else va - ROM
def P(lo, hi): return (lo & 0xFFFF) | (hi & 0xFFFF) << 16
def pk(w): return (w & 0xFFFF, w >> 16)
def W(*ws): return struct.pack('<%dI' % len(ws), *ws)
def floor4(x): return int(x) // 4 * 4
def floor_even(x): return int(x) // 2 * 2
def ceil_even(x): return -(-math.ceil(x - 1e-9) // 2) * 2
def even_near(x):
    lo = int(x) // 2 * 2
    return lo if x - lo < lo + 2 - x else lo + 2
def near8(x): return int(round(x / 8)) * 8
def f8(v): return v // 8 * 8
def f16(v): return v // 16 * 16


class Ctx:
    """reads stock (img.old) and current (img.new) words; puts with the stock bytes as expect."""
    def __init__(self, img, eg): self.img, self.eg, self.rows = img, eg, []
    def u(self, f, va, n=1, new=False):
        src = self.img.new if new else self.eg
        return list(struct.unpack_from('<%d%s' % (n, f), src, off(va)))
    def put(self, va, data, why, zero=False):
        o = off(va); old = bytes(self.eg[o:o + len(data)])
        self.img.put(o, data, why, expect=None if zero else old, expect_zero=zero, offset=True)
        self.rows.append(dict(va=hex(va), bytes=len(data), why=why, stock=old.hex() if len(old) <= 64 else None))
    def drop(self, prefix):
        hit = [e for e in self.img.edits if e['purpose'].startswith(prefix)]
        assert len(hit) == 1, (prefix, len(hit))
        e = hit[0]; self.img.new[e['offset']:e['end']] = e['old']; self.img.edits.remove(e)
        return dict(offset=hex(e['offset']), bytes=e['end'] - e['offset'], purpose=e['purpose'])


class Alloc:
    def __init__(self, at, end): self.at, self.end, self.used = at, end, []
    def take(self, n, why, align=16):
        self.at = -(-self.at // align) * align; a = self.at; self.at += n
        assert self.at <= self.end, ('region full', why); self.used.append((hex(a), n, why)); return a


# ----------------------------------------------------------------------------------------------- A64 encoders
def b_(at, to, link=False):
    d = (to - at) >> 2; assert -(1 << 25) <= d < 1 << 25; return (0x94000000 if link else 0x14000000) | d & 0x3FFFFFF
def bcond(at, to, c): d = (to - at) >> 2; assert -(1 << 18) <= d < 1 << 18; return 0x54000000 | (d & 0x7FFFF) << 5 | c
def cbz(at, to, rt, nz=False): d = (to - at) >> 2; return (0x35000000 if nz else 0x34000000) | (d & 0x7FFFF) << 5 | rt
def cmpw(n, imm): return 0x7100001F | imm << 10 | n << 5
def movzw(d, imm): return 0x52800000 | imm << 5 | d
def movz(d, imm, hw): return 0xD2800000 | hw << 21 | imm << 5 | d
def movk(d, imm, hw): return 0xF2800000 | hw << 21 | imm << 5 | d
def movw(d, m): return 0x2A0003E0 | m << 16 | d
def movx(d, m): return 0xAA0003E0 | m << 16 | d
def stp_pre(t, t2, imm): return 0xA9800000 | ((imm >> 3) & 0x7F) << 15 | t2 << 10 | 31 << 5 | t
def stp(t, t2, imm): return 0xA9000000 | ((imm >> 3) & 0x7F) << 15 | t2 << 10 | 31 << 5 | t
def ldp(t, t2, imm): return 0xA9400000 | ((imm >> 3) & 0x7F) << 15 | t2 << 10 | 31 << 5 | t
def ldp_post(t, t2, imm): return 0xA8C00000 | ((imm >> 3) & 0x7F) << 15 | t2 << 10 | 31 << 5 | t
def ldrw(t, n, imm): return 0xB9400000 | (imm >> 2) << 10 | n << 5 | t
def ldrx(t, n, imm): return 0xF9400000 | (imm >> 3) << 10 | n << 5 | t
def strx(t, n, imm): return 0xF9000000 | (imm >> 3) << 10 | n << 5 | t
def ldrb(t, n, imm): return 0x39400000 | imm << 10 | n << 5 | t
def ldrh(t, n, imm): return 0x79400000 | (imm >> 1) << 10 | n << 5 | t
def strh(t, n, imm): return 0x79000000 | (imm >> 1) << 10 | n << 5 | t
def ldrsh(t, n, imm): return 0x79C00000 | (imm >> 1) << 10 | n << 5 | t
def addw(d, n, m): return 0x0B000000 | m << 16 | n << 5 | d
def addxi(d, n, imm): return 0x91000000 | imm << 10 | n << 5 | d
def addx_lsl(d, n, m, s): return 0x8B000000 | m << 16 | s << 10 | n << 5 | d
def subsw_i(d, n, imm): return 0x71000000 | imm << 10 | n << 5 | d
def adr(at, to, d): o = to - at; return 0x10000000 | (o & 3) << 29 | ((o >> 2) & 0x7FFFF) << 5 | d
def stpw(t, t2, n, imm): return 0x29000000 | ((imm >> 2) & 0x7F) << 15 | t2 << 10 | n << 5 | t
def strw(t, n, imm): return 0xB9000000 | (imm >> 2) << 10 | n << 5 | t
RET, NOP = 0xD65F03C0, 0xD503201F
ORR_W0_1 = 0x320003E0                                         # orr w0, wzr, #1
EQ, NE, HS, LO, HI, LS = 0, 1, 2, 3, 8, 9


from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM  # noqa: E402
_md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
def text(code, at): return [f'{i.mnemonic} {i.op_str}'.strip() for i in _md.disasm(code, at)]


class Asm:
    def __init__(self, at): self.at, self.items, self.labels = at, [], {}
    def label(self, n): self.items.append(('label', n))
    def i(self, f): self.items.append(('ins', f))
    def half(self, *v): self.items.append(('half', v))
    def L(self, n): return lambda: self.labels[n]
    def size(self): return sum(4 if k == 'ins' else 2 * len(v) if k == 'half' else 0 for k, v in self.items)
    def build(self):
        a = self.at
        for k, v in self.items:
            if k == 'label': self.labels[v] = a
            elif k == 'ins': a += 4
            else: a += 2 * len(v)
        out, a = b'', self.at
        for k, v in self.items:
            if k == 'ins': out += struct.pack('<I', v(a) if callable(v) else v); a += 4
            elif k == 'half': out += struct.pack(f'<{len(v)}h', *v); a += 2 * len(v)
        return out


def movx64(rd, v):
    """mov/movk sequence for a 64-bit address (4 words)."""
    return [movz(rd, v & 0xFFFF, 0), movk(rd, v >> 16 & 0xFFFF, 1), movk(rd, v >> 32 & 0xFFFF, 2), movk(rd, v >> 48 & 0xFFFF, 3)]


# ----------------------------------------------------------------------------------------------- 1. sizes
SIZE_TABLES = {'raw': (0xA0297A520, 3), 'jpeg_lms': (0xA0297A568, 3), 'window': (0xA0297A5B0, 3), 'jpeg_out': (0xA0297A688, 6)}
QUARTER = {'quarter_raw': 0xA0297A5F8, 'quarter_jpeg': 0xA0297A640}
CROP_TABLES = (0xA0297A6D0, 0xA0297A718)
ORIGIN, T1, RAWOUT = 0xA02A948A0, 0xA02A2460C, 0xA02A244A4


def rawout(w, h):
    """A2b rule (reproduces every stock RAW-output row): see ../../a2b_43_20261110/build_a2b.py."""
    r32 = lambda x: (x + 31) & ~31
    c512 = lambda x: -(-x // 512) * 512
    b12, b14 = r32(w * 12 // 8) * h, r32(w * 14 // 8) * h
    b5, b3 = r32(w * 5 // 8) * h, r32(w * 3 // 8) * h
    return [b12, b12, c512(-(-b12 * 7 // 10)), b5, b3, b14, b14, c512(-(-b14 * 26 // 35)), b5, b3]


def sizes(c):
    out = {}
    for area in (0, 1, 4, 8):                                   # the rule reproduces the stock RAW-output rows
        w, h = pk(c.u('I', c.u('Q', SIZE_TABLES['raw'][0] + 8 * area)[0])[0])
        assert c.u('I', RAWOUT + 0x28 * area, 10) == rawout(w, h), area
    for a, s in AREAS.items():
        ws = s['words']; rec = {}
        for name, (table, n) in SIZE_TABLES.items():
            p = c.u('Q', table + 8 * a)[0]; assert p
            c.put(p, W(*[int(x, 16) for x in ws[name]][:n]), f'{name} table {table:#x} slot {a} ({s["name"]})'); rec[name] = hex(p)
        for name, table in QUARTER.items():
            p = c.u('Q', table + 8 * a)[0]
            c.put(p, W(int(ws[name], 16)), f'{name} table {table:#x} slot {a} ({s["name"]})')
        p = c.u('Q', CROP_TABLES[0] + 8 * a)[0]; assert p == c.u('Q', CROP_TABLES[1] + 8 * a)[0]
        c.put(p, W(*[int(x, 16) for x in ws['crop']]), f'crop-edge tables {CROP_TABLES[0]:#x}/{CROP_TABLES[1]:#x} slot {a} (shared entry)')
        c.put(ORIGIN + 4 * a, W(int(ws['origin'], 16)), f'origin table slot {a}: {s["origin"]}')
        c.put(T1 + 0x48 * a, W(*s['t1']), f'JPEG size estimate T1 slot {a} (18 words)')
        c.put(RAWOUT + 0x28 * a, W(*rawout(*s['raw'])), f'RAW output size table {RAWOUT:#x} area {a}: {s["raw"][0]}x{s["raw"][1]}')
        out[a] = rec
    return out


# ----------------------------------------------------------------------------------------------- 2. 9x9 display sizes
DISPLAY = 0xA0297A760
BOX_W = (640, 320, 1024, 1280, 1920, 1280, 640, 384)            # rows 0..7: box width (every stock 16:9 entry is width-limited)


def display_rule(w, R): return (w, floor4(w / R))


def display(c):
    rows = c.u('Q', DISPLAY, 8); out = {}
    for r in range(8):
        assert pk(c.u('I', rows[r] + 16)[0]) == display_rule(BOX_W[r], 16 / 9), r          # stock 16:9 (area 4)
        if r < 4: assert pk(c.u('I', rows[r])[0]) == display_rule(BOX_W[r], 1.5), r          # stock FX, width-limited rows
    for a, s in AREAS.items():
        out[a] = []
        for r in range(8):
            v = display_rule(BOX_W[r], s['R'])
            c.put(rows[r] + 4 * a, W(P(*v)), f'display-size row {r} area {a}: {pk(c.u("I", rows[r] + 4 * a)[0])} -> {v}')
            out[a].append(v)
    return out


# ----------------------------------------------------------------------------------------------- 3. class tables (7 classes)
CLASS_GETTERS = {0x410619D8: 0xA02A947DC, 0x410619F0: 0xA02A947F0, 0x41061A08: 0xA02A94804, 0x41061A20: 0xA02A94818}
CLASS_T5, CLASS_PTRS = 0xA02A94C1C, 0xA0297A7A0
# per table: (box width, rounding) for a width-limited class; the rule is asserted on stock 16:9
CLASS_RULE = {0xA02A947DC: (640, floor4), 0xA02A947F0: (320, floor4), 0xA02A94804: (1920, floor4), 0xA02A94818: (160, floor_even),
              CLASS_T5: (3840, floor4)}


def class_tables(c, al):
    new = {}
    for t, (bw, rnd) in CLASS_RULE.items():
        stock = [pk(x) for x in c.u('I', t, 5)]
        assert stock[1] == (bw, rnd(bw * 9 / 16)), (hex(t), stock)                          # 16:9 = the width-limited rule
        vals = stock + [None, None]
        for a, s in AREAS.items(): vals[s['cls']] = (bw, rnd(bw / s['R']))
        at = al.take(4 * 7, f'class table {t:#x} (7 classes)', 4)
        c.put(at, W(*[P(*v) for v in vals]), f'class table {t:#x} moved to {at:#x} with classes 5 (2.39:1) {vals[5]}, 6 (65:24) {vals[6]}', zero=True)
        new[t] = (at, vals)
    for fn, t in CLASS_GETTERS.items():                       # mov x8,#lo; movk x8,#hi,lsl16; movk x8,#0xa,lsl32; movk x8,#0,lsl48
        old = c.u('I', fn, 4); assert old == movx64(8, t), (hex(fn), [hex(x) for x in old])
        c.put(fn, W(*movx64(8, new[t][0])), f'class getter {fn:#x}: table {t:#x} -> {new[t][0]:#x}')
    ptrs = c.u('Q', CLASS_PTRS, 3); assert ptrs == [0xA02A947DC, 0xA02A94804, CLASS_T5], [hex(p) for p in ptrs]
    c.put(CLASS_PTRS, struct.pack('<3Q', *(new[p][0] for p in ptrs)), f'class pointer table {CLASS_PTRS:#x} (getter 0x41061d54): 3 pointers -> moved tables')
    return {hex(t): dict(at=hex(a), values=v) for t, (a, v) in new.items()}


# ----------------------------------------------------------------------------------------------- 3b. preview JPEG capacities
# [class][quality] u32 (fine, normal, basic) per preview size, 5 classes back to back, read by three getters used by the
# capture buffer allocator 0x41048a.. / 0x410490..; found in QEMU (A2i dev1: class 5 read the next table's 44544 B and the
# 1920x800 preview did not fit).  Rule (reproduces all 45 stock words): units = ceil(ceil32(w)/16 * h * 13 / 640) for fine,
# ceil(units / 2), ceil(units / 4) for normal and basic, bytes = units * 512.
CAP_GETTERS = {0x41045854: (0xA02A24C0C, 0xA02A947DC), 0x41045874: (0xA02A24C48, 0xA02A94804), 0x41045894: (0xA02A24C84, 0xA02A947F0)}


def capacity(w, h):
    u = math.ceil(((w + 31) // 32 * 2) * h * 13 / 640)
    return [u * 512, math.ceil(u / 2) * 512, math.ceil(u / 4) * 512]


def capacities(c, al, classes):
    out = {}
    for fn, (t, sizes_t) in CAP_GETTERS.items():
        st = c.u('I', t, 15); sz = [pk(x) for x in c.u('I', sizes_t, 5)]
        assert all(st[3 * k:3 * k + 3] == capacity(*sz[k]) for k in range(5)), (hex(t), st, sz)
        vals = list(st)
        new_sizes = classes[hex(sizes_t)]['values']
        for k in (5, 6): vals += capacity(*new_sizes[k])
        at = al.take(4 * 21, f'preview JPEG capacity table {t:#x} (7 classes x 3 qualities)', 4)
        c.put(at, W(*vals), f'preview JPEG capacity table {t:#x} moved to {at:#x}: classes 5 {vals[15:18]}, 6 {vals[18:21]}', zero=True)
        code = c.u('I', fn, 5)
        assert code[0] == movz(8, t & 0xFFFF, 0) and code[1] == movk(8, t >> 16 & 0xFFFF, 1) and code[2] == movk(8, t >> 32, 2), hex(fn)
        assert code[3] == 0x321E07E9 and code[4] == movk(8, 0, 3)                   # orr w9, wzr, #0xc (mov w9, #0xc)
        c.put(fn, W(movz(8, at & 0xFFFF, 0), movk(8, at >> 16, 1), movk(8, 0, 2)), f'preview capacity getter {fn:#x}: table {t:#x} -> {at:#x}')
        out[hex(t)] = dict(at=hex(at), getter=hex(fn), sizes=hex(sizes_t), values=vals)
    return out


# ----------------------------------------------------------------------------------------------- 4. live-view windows (7 classes)
WIN_TABLES, WIN_FN = (0x44B7FD68, 0x44B7FF48), 0x411871AC
LAYOUTS, STRIDE_OLD, STRIDE_NEW = 12, 0x28, 0x38


def wide_rect(r169, lay, R, layout3):
    """full-width rectangle of ratio R from the stock 16:9 rectangle: same left/right, height from the width (layout 4,
    720x480 with non-square pixels: the 16:9 height scaled by 16/9 / R), centred on the 16:9 centre, top rounded up to even."""
    if lay == 3: return layout3
    l, t, r, b = r169; Wd = r - l
    h = even_near((b - t) * (16 / 9) / R) if lay == 4 else even_near(Wd / R)
    top2 = t + b - h; top = top2 // 2; top += top & 1
    return (l, top, r, top + h)


def windows(c, al):
    new_tabs, rows = {}, []
    for t in WIN_TABLES:
        data = bytearray()
        for lay in range(LAYOUTS):
            cur = [struct.unpack_from('<4H', c.img.new, off(t) + lay * STRIDE_OLD + k * 8) for k in range(5)]   # incl. A2d's class 3
            r169 = cur[1]
            # the rule on stock: 16:9 of layout 3 is the 16:9 JPEG crop on the 8256x5504 plane
            if lay == 3: assert r169 == (0, 432, 8256, 5072)
            add = []
            for a, s in sorted(AREAS.items(), key=lambda kv: kv[1]['cls']):
                y0 = (FX_JPEG[1] - s['jpeg'][1]) // 2
                add.append(wide_rect(r169, lay, s['R'], (0, y0, 8256, y0 + s['jpeg'][1])))
            for rr in cur + add: data += struct.pack('<4H', *rr)
            rows.append(dict(table=hex(t), layout=lay, r169=list(r169), r239=list(add[0]), r6524=list(add[1])))
        at = al.take(len(data), f'live-view window table {t:#x} (12 layouts x 7 classes)', 8)
        c.put(at, bytes(data), f'live-view window table {t:#x} moved to {at:#x}: 12 layouts x 7 classes, stride 0x38', zero=True)
        new_tabs[t] = at
    # lookup 0x411871AC: mov x8,#ff48 / mov x9,#fd68 / movk x8,#0x44b7 / movk x9,#0x44b7 / ... / mov w10,#0x28
    code = c.u('I', WIN_FN + 4, 10)
    assert code[:4] == [movz(8, 0xFF48, 0), movz(9, 0xFD68, 0), movk(8, 0x44B7, 1), movk(9, 0x44B7, 1)] and code[9] == movzw(10, 0x28)
    assert code[4:8] == [movk(8, 0, 2), movk(9, 0, 2), movk(8, 0, 3), movk(9, 0, 3)]
    a8, a9 = new_tabs[0x44B7FF48], new_tabs[0x44B7FD68]
    assert a8 >> 32 == 0 and a9 >> 32 == 0
    c.put(WIN_FN + 4, W(movz(8, a8 & 0xFFFF, 0), movz(9, a9 & 0xFFFF, 0), movk(8, a8 >> 16, 1), movk(9, a9 >> 16, 1)),
          f'live-view window lookup {WIN_FN:#x}: table addresses -> {a9:#x} (flag set) / {a8:#x} (clear)')
    c.put(WIN_FN + 4 + 9 * 4, W(movzw(10, STRIDE_NEW)), f'live-view window lookup {WIN_FN:#x}: layout stride 0x28 -> 0x38 (7 classes)')
    return dict(tables={hex(k): hex(v) for k, v in new_tabs.items()}, rows=rows)


# ----------------------------------------------------------------------------------------------- 5. ratio classifier
CLASSIFIER, CLS_SITE = 0x41059D04, 0x41059D18                # r = 36 W / H; stock: >59 -> 1, >51 -> 0, >46 -> 3, >40 -> 2, else 4
T6, T5 = 91, 75                                               # 65:24 r = 97, 2.39:1 r = 86, 16:9 r = 64


def classifier(c, al):
    want = [cmpw(8, 0x3B), bcond(CLS_SITE + 4, 0x41059D28, LS), ORR_W0_1, RET]      # stock 'mov w0, #1' is the ORR alias
    assert c.u('I', CLS_SITE, 4) == want
    at = al.take(4 * 13, 'ratio classifier cave')
    s = Asm(at)
    s.i(cmpw(8, T6)); s.i(lambda a: bcond(a, s.L('le6')(), LS)); s.i(movzw(0, 6)); s.i(RET)
    s.label('le6'); s.i(cmpw(8, T5)); s.i(lambda a: bcond(a, s.L('le5')(), LS)); s.i(movzw(0, 5)); s.i(RET)
    s.label('le5'); s.i(cmpw(8, 0x3B)); s.i(lambda a: bcond(a, s.L('far')(), LS)); s.i(ORR_W0_1); s.i(RET)
    s.label('far'); s.i(lambda a: b_(a, 0x41059D28))           # b.cond cannot reach the stock code
    code = s.build(); assert len(code) <= 52
    c.put(at, code, f'ratio classifier cave: r > {T6} -> 6 (65:24), r > {T5} -> 5 (2.39:1), else the stock chain', zero=True)
    c.put(CLS_SITE, W(b_(CLS_SITE, at)), f'ratio classifier {CLASSIFIER:#x}: cmp w8,#0x3b -> b cave (classes 5, 6 before 16:9)')
    return dict(cave=hex(at), t6=T6, t5=T5, words=code.hex())


# ----------------------------------------------------------------------------------------------- 6. per-area small tables
AREA_CLASS, BLACKOUT = 0xA02A5E490, 0xA029CAB80              # areas 2..8
AREA_CODE, CROP_FACTOR = 0x44004810, 0x440CA824               # slots 1..8; (factor, area) pairs
CODE_169 = 7


def small_tables(c):
    out = {}
    for t, what in ((AREA_CLASS, 'area -> preview class'), (BLACKOUT, 'capture blackout class')):
        cur = c.u('I', t, 7, new=True); assert cur == [3, 0, 1, 1, 1, 1, 4], (hex(t), cur)    # A2 / A2d set area 2 -> 3
        for a, s in AREAS.items():
            c.put(t + 4 * (a - 2), W(s['cls']), f'{what} table {t:#x} area {a}: {cur[a - 2]} -> {s["cls"]} ({s["name"]})')
    codes = c.u('I', AREA_CODE, 8); assert codes == [2, 3, 1, 7, 8, 9, 9, 4], codes
    for a, s in AREAS.items():
        c.put(AREA_CODE + 4 * (a - 1), W(CODE_169), f'area code table {AREA_CODE:#x} slot {a}: {codes[a - 1]} -> {CODE_169} (FX 16:9; full width)')
    pairs = c.u('I', CROP_FACTOR, 18); assert pairs == [10, 0, 15, 1, 11, 2, 12, 3, 10, 4, 15, 5, 30, 6, 23, 7, 13, 8, 0][:18], pairs
    fx_diag = math.hypot(36, 24)
    factor = lambda w_mm, h_mm: round(10 * fx_diag / math.hypot(w_mm, h_mm))
    for area, mm in ((0, (36, 24)), (1, (23.5, 15.7)), (2, (30, 24)), (4, (36, 20.25)), (8, (24, 24))):   # the rule on stock
        assert pairs[pairs.index(area, 1) - 1] == factor(*mm), area
    for a, s in AREAS.items():
        h_mm = 36 / s['R']; f = factor(36, h_mm); assert f == 11
        i = pairs.index(a, 1) - 1
        c.put(CROP_FACTOR + 4 * i, W(f), f'crop factor pair (area {a}): {pairs[i]} -> {f} (FX diagonal / 36x{h_mm:.2f} diagonal)')
    out = dict(area_class={a: s['cls'] for a, s in AREAS.items()}, area_code=CODE_169, crop_factor=11)
    return out


# ----------------------------------------------------------------------------------------------- 7. parameter blocks
T_BLOCKS = dict(k0=0xA02A960A0, k1=0xA02A96160, s0=0xA02A961B0, s1=0xA02A96270)
X18 = (0xA02A96110, 0xA02A96220)
BW_STILL, BW_LIVE = 136, 44
LIVE_W, LIVE_OX, READOUT_H = 2752, 2, 1836


def cells(Wh, Hh, bw):
    """stock rule (FX/16:9 still, FX/16:9/DX live): at most 30 x 20 cells, even counts, cell height stretched to fill."""
    nx = min(30, Wh // bw // 2 * 2); ny = min(20, Hh // bw // 2 * 2); bh = max(bw, f8(Hh // ny)); return nx, ny, bw, bh


def grid_y(w, Hh, ny, bw, bh):
    """height-dependent words of the two statistics grids (rule of blocks.block178)."""
    cnt_lo = w[0x1C // 4] >> 16 & 0xFF; nx = cnt_lo
    cnt, cnt2 = nx | ny << 8, (2 * nx) | (2 * ny) << 8
    ys1 = (Hh - ny * bh) // 2; ys2 = ((Hh - ny * bw) // 2) // 8 * 8
    xs1 = pk(w[0x10 // 4])[1]; xs2 = pk(w[0x7C // 4])[0]
    w[0x14 // 4] = P(ys1, bw); w[0x18 // 4] = P(bh, bw); w[0x1C // 4] = P(bh, cnt)
    w[0x7C // 4] = P(xs2, ys2); w[0x84 // 4] = P(cnt, xs2); w[0x88 // 4] = P(ys2, bw // 2)
    w[0x8C // 4] = P(bw // 2, cnt2); w[0x90 // 4] = w[0x7C // 4]; w[0x98 // 4] = P(cnt2, xs2)
    w[0x9C // 4] = w[0x88 // 4]; w[0xA0 // 4] = w[0x8C // 4]
    return dict(ny=ny, bh=bh, ys1=ys1, ys2=ys2)


def recs(R):
    return dict(rec0=(176, ceil_even(176 / R)), rec1=(682, ceil_even(682 / R)), rec2=(384, near8(384 / R)))


def blocks(c, al, blk):
    t = {k: c.u('Q', v, 9) for k, v in T_BLOCKS.items()}
    d169 = {k: c.u('I', t[k][4], 0x178 // 4 if k[0] == 'k' else 14) for k in t}
    # the record rules on stock 16:9 and FX
    assert recs(16 / 9)['rec0'] == pk(d169['k0'][0x10C // 4]) and recs(1.5)['rec0'] == (176, 118)
    assert recs(16 / 9)['rec1'] == pk(d169['k1'][0x120 // 4]) and recs(16 / 9)['rec2'] == pk(d169['k0'][0x134 // 4])
    # cell rule on stock (still 16:9, FX; live 16:9, FX, DX)
    assert cells(4128, 2320, 136) == (30, 16, 136, 144) and cells(4128, 2752, 136) == (30, 20, 136, 136)
    assert cells(1376, 772, 44)[1:] == (16, 44, 48) and cells(1374, 916, 44)[1:] == (20, 44, 44) and cells(1796, 1196, 54)[1:] == (20, 54, 56)
    out = {}
    for a, s in AREAS.items():
        jw, jh = s['jpeg']; cx, cy = s['crop']; x0, y0 = s['origin']; rc = recs(s['R'])
        g = dict(W=jw, H=jh, cx=cx, cy=cy, x0=x0, y0=y0)
        cl = cells(jw // 2, jh // 2, BW_STILL)
        k0 = blk.block178(0, g, cl, rc['rec0'], rc['rec2'], d169['k0'], 2)
        # live view: 16:9 live block with the height-dependent words; width words stay (same 2752 source width)
        LH = f8(round(LIVE_W / s['R'])); oy = (READOUT_H - LH) // 2 // 2 * 2
        k1 = list(d169['k1']); k1[1] = P(LH, oy)
        lc = cells(LIVE_W // 2, LH // 2, BW_LIVE); gy = grid_y(k1, LH // 2, lc[1], lc[2], lc[3])
        sw = 64 * 2736; sh = f16(LH)
        for o, rec in ((0x104, rc['rec0']), (0x118, rc['rec1']), (0x12C, rc['rec2'])):
            k1[o // 4] = P(pk(k1[o // 4])[0], 64 * sh // rec[1])
        k1[0x10C // 4] = P(*rc['rec0']); k1[0x120 // 4] = P(*rc['rec1']); k1[0x134 // 4] = P(*rc['rec2']); k1[0x15C // 4] = P(*rc['rec2'])
        # record 3: stock 16:9 crops a 3:2 384x256 image from the middle of the source (ratio 384, x start 52); same here
        r3 = 64 * sh // 256; k1[0x140 // 4] = P(r3, r3)
        k1[0x138 // 4] = P(pk(d169['k1'][0x138 // 4])[0] + (2304 - 384 * r3 // 64) // 8, 0)
        hp = f16(LH // 2)                                     # processing height (stock 16:9 768 = f16(772), FX 912)
        k1[0x164 // 4] = P(0, hp); k1[0x170 // 4] = P((1 << 20) // (hp * 4), 0)
        # 0x38 geometry blocks
        s0 = list(d169['s0']); hw, hh = jw // 2, jh // 2
        s0[1] = P(x0 + cx, y0 + cy); s0[2] = P(hw, hh); s0[3] = P(hw - 8, hh); s0[12] = s0[3]; s0[13] = P(jw, jh)
        s0[4] = P(cl[0] * cl[2], cl[1] * cl[3]); s0[5] = P(cl[0] * cl[2], cl[1] * cl[2]); s0[6] = P(2 * cl[0], 2 * cl[1])
        s0[7] = P(*rc['rec0']); s0[9] = P(*rc['rec2']); s0[11] = P(*rc['rec2'])
        s1 = list(d169['s1']); lh2 = f8(LH // 2)
        s1[1] = P(LIVE_OX, oy); s1[2] = P(pk(s1[2])[0], lh2); s1[3] = P(pk(s1[3])[0], lh2); s1[12] = s1[3]; s1[13] = P(LIVE_W, LH)
        s1[4] = P(pk(s1[4])[0], lc[1] * lc[3]); s1[5] = P(pk(s1[5])[0], lc[1] * lc[2]); s1[6] = P(pk(s1[6])[0], 2 * lc[1])
        s1[7] = P(*rc['rec0']); s1[8] = P(*rc['rec1']); s1[9] = P(*rc['rec2']); s1[11] = P(*rc['rec2'])
        at = {}
        for name, ws in (('k0', k0), ('k1', k1), ('s0', s0), ('s1', s1)):
            at[name] = al.take(4 * len(ws), f'area {a} block {name}')
            c.put(at[name], W(*ws), f'area {a} ({s["name"]}) parameter block {name} ({4 * len(ws):#x} bytes)', zero=True)
            assert t[name][a] == 0
            c.put(T_BLOCKS[name] + 8 * a, struct.pack('<Q', at[name]), f'block table {T_BLOCKS[name]:#x} slot {a} -> {name}')
        for tab in X18:
            fx = c.u('Q', tab)[0]; assert c.u('Q', tab + 32)[0] == fx                      # 16:9 uses the FX block
            c.put(tab + 8 * a, struct.pack('<Q', fx), f'kind 0x18 table {tab:#x} slot {a} -> FX block {fx:#x} (as 16:9)')
        out[a] = dict(at={k: hex(v) for k, v in at.items()}, still_cells=cl, live=dict(H=LH, oy=oy, cells=lc, **gy, processing_h=hp,
                      record3_ratio=r3), records=rc, words={k: [hex(x) for x in v] for k, v in (('k0', k0), ('k1', k1), ('s0', s0), ('s1', s1))})
    return out


# ----------------------------------------------------------------------------------------------- 8. live-view display sizes
SITE_A, SITE_B, MASK_SITE = 0x410670E4, 0x410671C0, 0x41066ADC
LCD_W, EVF_W = 1296, 1280


def lv_sizes(c, al, a2c):
    dropped = [c.drop('0x41067078: b.ne'), c.drop('0x410670f8: b.ne'), c.drop('0x41066aa8 photo readout window')]
    sizes = {a: dict(lcd=(LCD_W, even_near(LCD_W / s['R'])), evf=(EVF_W, even_near(EVF_W / s['R']))) for a, s in AREAS.items()}
    R169 = 8256 / 4640; assert (even_near(LCD_W / R169), even_near(EVF_W / R169)) == (728, 720)   # the stock 16:9 sizes (JPEG ratio)
    caves = {}
    for name, key, store, other in (('lcd', 'lcd', 0x410670BC, a2c['cave_a']), ('evf', 'evf', 0x4106716C, a2c['cave_b'])):
        at = al.take(4 * 12, f'live-view {name} size front cave'); s = Asm(at)
        for a in AREAS:
            s.i(cmpw(8, a)); s.i(lambda x, a=a: bcond(x, s.L(f'a{a}')(), EQ))
        s.i(lambda x: b_(x, other))
        for a in AREAS:
            s.label(f'a{a}'); s.i(movzw(8, sizes[a][key][0])); s.i(movzw(9, sizes[a][key][1])); s.i(lambda x: b_(x, store))
        code = s.build(); c.put(at, code, f'{name} live-view size front cave: areas 3/6 -> {[sizes[a][key] for a in AREAS]}, else A2c cave {other:#x}', zero=True)
        caves[name] = hex(at)
    c.put(SITE_A, W(b_(SITE_A, int(caves['lcd'], 16))), '0x41067078: b.ne 0x41067080 -> b lcd front cave (areas 3/6, then A2c cave_a)')
    c.put(SITE_B, W(b_(SITE_B, int(caves['evf'], 16))), '0x410670f8: b.ne 0x4106711c -> b evf front cave (areas 3/6, then A2c cave_b)')
    mask = 0x111 | 1 << 2 | sum(1 << a for a in AREAS)
    c.put(MASK_SITE, W(movzw(10, mask)), f'0x41066aa8 photo readout window: area mask 0x111 -> {mask:#x} (areas 2, 3, 6 on the FX readout)')
    return dict(sizes=sizes, caves=caves, mask=hex(mask), dropped=dropped)


# ----------------------------------------------------------------------------------------------- 9. live-view geometry descriptor
GEOM_JT, GEOM_169, GEOM_TAIL, GEOM_DEFAULT = 0xA02A977B8, 0x41066068, 0x410664DC, 0x410664EC
GEOM_169_TEXT = ['mov w8, #0x44', 'stp wzr, wzr, [sp, #0x20]', 'mov w7, #0x500', 'stp wzr, wzr, [sp, #8]', 'mov w27, #0x2d0',
                 'stp w8, wzr, [sp, #0x10]', 'mov w8, #8', 'mov w16, wzr', 'mov w10, wzr', 'stp w8, wzr, [sp, #0x18]', 'mov w8, #0x510',
                 'mov w12, wzr', 'mov w3, wzr', 'mov w5, wzr', 'mov w18, wzr', 'mov w2, wzr', 'mov w25, wzr', 'mov w24, #0x72c',
                 'mov w26, #0xac4', 'mov w6, #0x2d8', 'mov w17, #2', 'mov w15, #4', 'mov w9, #0x360', 'mov w4, #0x728', 'mov w1, #0xabc',
                 'mov w28, w8', 'mov w30, w7', 'mov w29, w27', 'mov w14, #4', 'b #0x410664dc']


def geometry(c, al, sizes):
    """the stock 16:9 case with the wide display values; same registers, same stack slots, same tail."""
    stock = c.u('I', GEOM_169, 30)
    st = text(W(*stock), GEOM_169)
    assert st == GEOM_169_TEXT, st
    out = {}
    for a, s in AREAS.items():
        lcd, evf = sizes[a]['lcd'], sizes[a]['evf']; assert lcd[0] == 1296 and evf[0] == 1280
        pad = (0x360 - lcd[1]) // 2; rows = 3
        ws = list(stock)
        ws[0] = movzw(8, pad); ws[4] = movzw(27, evf[1]); ws[19] = movzw(6, lcd[1]); ws[28] = movzw(14, rows)
        at = al.take(4 * len(ws), f'geometry case area {a}')
        ws[29] = b_(at + 4 * 29, GEOM_TAIL)
        c.put(at, W(*ws), f'geometry 41065194 case for area {a} ({s["name"]}) = stock 16:9 case with LCD {lcd}, EVF {evf}, top pad {pad}, rows {rows}', zero=True)
        cur = c.u('Q', GEOM_JT + 8 * a)[0]; assert cur == GEOM_DEFAULT
        c.put(GEOM_JT + 8 * a, struct.pack('<Q', at), f'live-view geometry jump table {GEOM_JT:#x} slot {a}: {GEOM_DEFAULT:#x} (all-zero descriptor) -> case')
        out[a] = dict(cave=hex(at), pad=pad, lcd=lcd, evf=evf, rows=rows)
    return out


# ----------------------------------------------------------------------------------------------- 10. focus-point grids
GRID_TABLES = {0xA02A5CE38: 9, 0xA02A4C470: 135}
SET, REC = 0xFC, 0x1C


def grid_rule(r0, top, bottom):
    """record of a full-width area: the FX record r0 with k rows taken off top and bottom, k the least that puts the grid's
    outer edges inside [top, bottom] of the 8256x5504 plane; None when no row is left (reproduces 143 of 144 stock 16:9
    records; the 51x29 set has 2 rows more cut in stock)."""
    (l, t), (r, b) = pk(r0[0]), pk(r0[1]); sy = pk(r0[4])[1]; n0 = r0[6]; k = 0
    while 2 * k < n0 and (t + k * sy < top or b - k * sy > bottom): k += 1
    if n0 - 2 * k < 1: return None
    return (P(l, t + k * sy), P(r, b - k * sy), r0[2], r0[3], r0[4], r0[5], n0 - 2 * k)


def grids(c):
    hit = miss = 0; edits = []; single = {}
    for base, sets in GRID_TABLES.items():
        for s_ in range(sets):
            r0 = c.u('I', base + s_ * SET, 7); r4 = c.u('I', base + s_ * SET + 4 * REC, 7)
            if not any(r0): continue
            d = grid_rule(r0, 432, 5072)
            near = d is not None and any(r4) and list(d[2:]) == r4[2:] and all(abs(x - y) <= 1 for i in (0, 1) for x, y in zip(pk(d[i]), pk(r4[i])))
            if (d is None and not any(r4)) or near: hit += 1                     # within 1 unit, as A2f's 1:1 check
            else: miss += 1
            for a, s in AREAS.items():
                y0 = (FX_JPEG[1] - s['jpeg'][1]) // 2
                n = grid_rule(r0, y0, y0 + s['jpeg'][1])
                at = base + s_ * SET + a * REC
                if n is None: n = (0,) * 7
                if list(n) != c.u('I', at, 7): edits.append((at, n, base, s_, a))
                if base == 0xA02A4C470 and s_ == 0: single[a] = (n[5], n[6])
    assert hit == 143 and miss == 1, (hit, miss)
    for at, n, base, s_, a in edits:
        c.put(at, W(*n), f'focus-point grid {base:#x} set {s_} record {a} ({AREAS[a]["name"]}): {pk(n[0])}-{pk(n[1])} {n[5]}x{n[6]}')
    return dict(rule_hits_169=hit, rule_misses_169=miss, records_written=len(edits), single_point=single)


# ----------------------------------------------------------------------------------------------- 11. custom wide-area maximum
MAX_JT, MAX_STORE, MAX_RET = 0xA02A27FA0, 0x40F1CC38, 0x40F1CC40


def custom_max(c, al, single):
    out = {}
    for a, s in AREAS.items():
        assert c.u('Q', MAX_JT + 8 * a)[0] == MAX_RET
        at = al.take(12, f'custom max area {a}'); mx = single[a]
        code = W(movzw(8, mx[0]), movzw(9, mx[1]), b_(at + 8, MAX_STORE))
        c.put(at, code, f'custom wide-area maximum for area {a} = {mx[0]}x{mx[1]} (largest size with a {s["name"]} grid record)', zero=True)
        c.put(MAX_JT + 8 * a, struct.pack('<Q', at), f'custom wide-area maximum jump table {MAX_JT:#x} slot {a}: {MAX_RET:#x} (no write -> 1x1) -> cave')
        out[a] = dict(cave=hex(at), max=mx)
    return out


# ----------------------------------------------------------------------------------------------- 12. distortion
D6828, D683A, CC2C8 = 0xA029D6828, 0xA029D683A, 0xA029CC2C8


def distortion(c):
    t1, t2, t3 = c.u('H', D6828, 9), c.u('H', D683A, 9), c.u('H', CC2C8, 9)
    ratio = min(t2[s] / t1[s] for s in range(9) if t1[s] and t2[s])
    out = {}
    for a, s in AREAS.items():
        v1 = math.floor(4096 * math.hypot(*s['jpeg']) / math.hypot(*FX_JPEG)); v3 = math.floor(4096 / math.sqrt(1 + s['R'] ** 2))
        v2 = math.floor(v1 * ratio)
        c.put(D6828 + 2 * a, struct.pack('<H', v1), f'distortion: JPEG-L diagonal / FX diagonal x 4096, area {a} = {v1}')
        c.put(D683A + 2 * a, struct.pack('<H', v2), f'distortion variant (mode 6): estimate {v1} x min stock ratio {ratio:.6f}, area {a} = {v2}')
        c.put(CC2C8 + 2 * a, struct.pack('<H', v3), f'distortion: nominal half height / half diagonal x 4096, area {a} = {v3}')
        out[a] = dict(D6828=v1, D683A=v2, CC2C8=v3, stock=[t1[a], t2[a], t3[a]])
    return out


# ----------------------------------------------------------------------------------------------- 13. corner box / lit points
CORNER_HOOK, CORNER_FN, POINTS_HOOK, POINTS_FN, IDX_FN = 0x403EB934, 0x41186FE4, 0x41186CA4, 0x41186ABC, 0x41187104
GETPROP, PROP_AREA, PROP_MOVIE = 0x403EC398, 0x219E, 0x218C
CELL_H = (36, 44, 36)                                          # FX display row cell height, layouts 0..2 (A029C453C)


def corners(c, al, win, gridinfo, a2h):
    """D = top(3:2 window) - top(wide window) per layout 0..2; k = the single-point grid cut (17 rows -> n)."""
    tabs = {int(k, 16): int(v, 16) for k, v in win['tables'].items()}
    new = bytes(c.img.new); dt = {}
    for a, s in AREAS.items():
        D = []
        for lay in range(3):
            r = {t: struct.unpack_from('<4H', new, off(tabs[t]) + lay * STRIDE_NEW + s['cls'] * 8) for t in WIN_TABLES}
            r32 = {t: struct.unpack_from('<4H', new, off(tabs[t]) + lay * STRIDE_NEW) for t in WIN_TABLES}
            assert r[WIN_TABLES[0]] == r[WIN_TABLES[1]] and r32[WIN_TABLES[0]] == r32[WIN_TABLES[1]]
            D.append(r32[WIN_TABLES[0]][1] - r[WIN_TABLES[0]][1])
        k = (17 - gridinfo['single_point'][a][1]) // 2
        dt[a] = dict(D=D, k=k, y0=[d + k * ch for d, ch in zip(D, CELL_H)], y1=[d - k * ch for d, ch in zip(D, CELL_H)])
    for lay in range(3):                                       # the FX row really has these cell heights
        for t in (0xA029C453C, 0xA029C3F9C): assert c.u('H', t + lay * 0xA0 + 10)[0] == CELL_H[lay]
    # corner box front cave: area (0x219E) 3/6 and not movie -> own path (stock call into a stack temporary, y adjust, one
    # 64-bit store); otherwise tail to the A2h corner cave with the original x0/x1/x30
    at = al.take(4 * 64, 'corner front cave'); s = Asm(at); L = s.L
    s.i(stp_pre(29, 30, -0x40)); s.i(stp(19, 20, 0x10)); s.i(stp(21, 22, 0x20))
    s.i(movx(19, 0)); s.i(movx(20, 1))
    s.i(movzw(0, PROP_AREA)); s.i(lambda x: b_(x, GETPROP, True)); s.i(movw(22, 0))
    s.i(cmpw(22, 3)); s.i(lambda x: bcond(x, L('wide')(), EQ)); s.i(cmpw(22, 6)); s.i(lambda x: bcond(x, L('wide')(), EQ))
    s.label('tail'); s.i(movx(0, 19)); s.i(movx(1, 20)); s.i(ldp(21, 22, 0x20)); s.i(ldp(19, 20, 0x10)); s.i(ldp_post(29, 30, 0x40))
    s.i(lambda x: b_(x, a2h['corner']))
    s.label('wide')
    s.i(movzw(0, PROP_MOVIE)); s.i(lambda x: b_(x, GETPROP, True)); s.i(cmpw(0, 1)); s.i(lambda x: bcond(x, L('tail')(), EQ))
    s.i(ldrx(9, 20, 0)); s.i(strx(9, 31, 0x30)); s.i(movx(0, 19)); s.i(addxi(1, 31, 0x30))
    s.i(lambda x: b_(x, CORNER_FN, True)); s.i(movw(21, 0)); s.i(lambda x: cbz(x, L('store')(), 21))
    s.i(ldrb(9, 19, 8)); s.i(lambda x: cbz(x, L('store')(), 9, nz=True))
    s.i(ldrw(9, 19, 0)); s.i(cmpw(9, 2)); s.i(lambda x: bcond(x, L('store')(), HI))
    s.i(movx(0, 19)); s.i(lambda x: b_(x, IDX_FN, True)); s.i(lambda x: cbz(x, L('store')(), 0, nz=True))
    s.i(ldrw(9, 19, 0)); s.i(cmpw(22, 6)); s.i(lambda x: adr(x, L('d3')(), 10)); s.i(lambda x: bcond(x, L('pick')(), NE))
    s.i(lambda x: adr(x, L('d6')(), 10))
    s.label('pick'); s.i(addx_lsl(10, 10, 9, 2)); s.i(ldrsh(11, 10, 0)); s.i(ldrsh(12, 10, 2))
    s.i(ldrh(13, 31, 0x32)); s.i(addw(13, 13, 11)); s.i(strh(13, 31, 0x32))
    s.i(ldrh(13, 31, 0x36)); s.i(addw(13, 13, 12)); s.i(strh(13, 31, 0x36))
    s.label('store'); s.i(ldrx(9, 31, 0x30)); s.i(strx(9, 20, 0)); s.i(movw(0, 21))
    s.i(ldp(21, 22, 0x20)); s.i(ldp(19, 20, 0x10)); s.i(ldp_post(29, 30, 0x40)); s.i(RET)
    s.label('d3'); s.half(*sum(([y0, y1] for y0, y1 in zip(dt[3]['y0'], dt[3]['y1'])), []))
    s.label('d6'); s.half(*sum(([y0, y1] for y0, y1 in zip(dt[6]['y0'], dt[6]['y1'])), []))
    cc = s.build(); assert len(cc) <= 4 * 64; corner_labels = dict(s.labels)
    c.put(at, cc, f'corner box front cave: areas 3/6 (0x219E), photo, idx 0, layout <= 2: y0/y1 + D + k*cell / D - k*cell {dt}; else A2h cave', zero=True)
    # lit points front cave: areas 3/6, photo -> stock 41186ABC then y0/y1 of each rect + D (idx 0, +8 = 0, layout <= 2)
    pa = al.take(4 * 80, 'points front cave'); p = Asm(pa); L = p.L
    p.i(stp_pre(29, 30, -0x40)); p.i(stp(19, 20, 0x10)); p.i(stp(21, 22, 0x20)); p.i(stp(23, 24, 0x30))
    p.i(movx(19, 1)); p.i(movx(20, 3)); p.i(movw(21, 2)); p.i(movx(23, 0))
    p.i(movzw(0, PROP_AREA)); p.i(lambda x: b_(x, GETPROP, True)); p.i(movw(24, 0))
    p.i(cmpw(24, 3)); p.i(lambda x: bcond(x, L('wide')(), EQ)); p.i(cmpw(24, 6)); p.i(lambda x: bcond(x, L('wide')(), EQ))
    p.label('tail'); p.i(movx(0, 23)); p.i(movx(1, 19)); p.i(movw(2, 21)); p.i(movx(3, 20))
    p.i(ldp(23, 24, 0x30)); p.i(ldp(21, 22, 0x20)); p.i(ldp(19, 20, 0x10)); p.i(ldp_post(29, 30, 0x40))
    p.i(lambda x: b_(x, a2h['points']))
    p.label('wide'); p.i(movzw(0, PROP_MOVIE)); p.i(lambda x: b_(x, GETPROP, True)); p.i(cmpw(0, 1)); p.i(lambda x: bcond(x, L('tail')(), EQ))
    p.i(movx(0, 23)); p.i(movx(1, 19)); p.i(movw(2, 21)); p.i(movx(3, 20)); p.i(lambda x: b_(x, POINTS_FN, True)); p.i(movw(22, 0))
    p.i(ldrb(9, 19, 8)); p.i(lambda x: cbz(x, L('done')(), 9, nz=True))
    p.i(ldrw(9, 19, 0)); p.i(cmpw(9, 2)); p.i(lambda x: bcond(x, L('done')(), HI))
    p.i(movx(0, 19)); p.i(lambda x: b_(x, IDX_FN, True)); p.i(lambda x: cbz(x, L('done')(), 0, nz=True))
    p.i(ldrw(9, 19, 0)); p.i(cmpw(24, 6)); p.i(lambda x: adr(x, L('d3')(), 10)); p.i(lambda x: bcond(x, L('pick')(), NE))
    p.i(lambda x: adr(x, L('d6')(), 10))
    p.label('pick'); p.i(addx_lsl(10, 10, 9, 1)); p.i(ldrsh(10, 10, 0))
    p.i(lambda x: cbz(x, L('done')(), 21)); p.i(movw(11, 21)); p.i(movx(12, 20))
    p.label('loop'); p.i(ldrh(13, 12, 2)); p.i(addw(13, 13, 10)); p.i(strh(13, 12, 2))
    p.i(ldrh(13, 12, 6)); p.i(addw(13, 13, 10)); p.i(strh(13, 12, 6))
    p.i(addxi(12, 12, 8)); p.i(subsw_i(11, 11, 1)); p.i(lambda x: bcond(x, L('loop')(), NE))
    p.label('done'); p.i(movw(0, 22)); p.i(ldp(23, 24, 0x30)); p.i(ldp(21, 22, 0x20)); p.i(ldp(19, 20, 0x10)); p.i(ldp_post(29, 30, 0x40)); p.i(RET)
    p.label('d3'); p.half(*dt[3]['D'], 0)
    p.label('d6'); p.half(*dt[6]['D'], 0)
    pc = p.build(); assert len(pc) <= 4 * 80
    c.put(pa, pc, f'lit points front cave: areas 3/6, photo: 41186ABC then y0/y1 of each rect + D (idx 0, +8 = 0, layout <= 2); else A2h points cave', zero=True)
    dropped = [c.drop('GUI corner box trampoline'), c.drop('GUI lit points 41186C68')]
    c.put(CORNER_HOOK, W(b_(CORNER_HOOK, at)), 'GUI corner box trampoline: b 41186FE4 -> b corner front cave (then A2h cave)')
    c.put(POINTS_HOOK, W(b_(POINTS_HOOK, pa, True)), 'GUI lit points 41186C68: bl 41186ABC -> bl points front cave (then A2h cave)')
    return dict(corner_cave=hex(at), points_cave=hex(pa), per_area=dt, dropped=dropped, corner_labels={k: hex(v) for k, v in corner_labels.items()})


# ----------------------------------------------------------------------------------------------- 14. loader
LOADER_SITE, SECTION_VA = 0x1024D8C, 0x40200000


def loader(c, hb1):
    d = c.drop('text loader: copy section')
    mov = lambda v: struct.pack('<II', 0xD2800008 | (v & 0xFFFF) << 5, 0xF2A00008 | (v >> 16) << 5)
    assert hb1.LOADER_END < LOADER_END <= hb1.GAP[1]
    o = LOADER_SITE; old = bytes(c.eg[o:o + 8]); assert old == mov(hb1.LOADER_END)
    c.img.put(o, mov(LOADER_END), f'text loader: copy section {SECTION_VA:#x} up to {LOADER_END:#x} instead of {hb1.LOADER_END:#x}', expect=old, offset=True)
    return dict(end=hex(LOADER_END), dropped=d)


def apply(img, eg, blk, hb1, a2h_caves):
    c = Ctx(img, eg); al = Alloc(CAVE_AT, CAVE_END); tl = Alloc(TAB_AT, TAB_END); det = {}
    det['sizes'] = sizes(c)
    det['display'] = display(c)
    det['class_tables'] = class_tables(c, tl)
    det['capacities'] = capacities(c, tl, det['class_tables'])
    det['windows'] = windows(c, tl)
    det['classifier'] = classifier(c, al)
    det['small_tables'] = small_tables(c)
    det['blocks'] = blocks(c, tl, blk)
    det['lv_size'] = lv_sizes(c, al, a2h_caves)
    det['geometry'] = geometry(c, al, det['lv_size']['sizes'])
    det['grid'] = grids(c)
    det['custom_max'] = custom_max(c, al, det['grid']['single_point'])
    det['distortion'] = distortion(c)
    det['corners'] = corners(c, al, det['windows'], det['grid'], a2h_caves)
    det['loader'] = loader(c, hb1)
    det['regions'] = dict(pipeline=al.used, tables=tl.used)
    det['edit_rows'] = len(c.rows)
    return det
