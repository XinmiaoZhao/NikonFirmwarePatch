#!/usr/bin/env python3
"""A12 playback: in-camera playback of this camera's 2.39:1 (area 3) and 65:24 (area 6) files, on top of A2h + pipeline.

Playback categories (r = 256 H / W through the 256-entry table 0x440E3398, readers 0x4078E150 / 0x4078E194 / 0x4078E1DC):
stock 0 3:2, 1 16:9, 2 4:3, 3 5:4, 4 1:1, 5 = r 88..103 (pan table value 0.375 = 8:3), 6 = everything else (the
'unknown' value: fit through the generic path 0x407A362C, 'unset' in the current-category global 0xA02983F20).
65:24 files (r 92..94 for all their images) already fall in category 5; 2.39:1 files (r 105..107) fall in 6.
This module gives 2.39:1 a category 7 (r 104..115) and makes 5 and 7 work where the files need it:

  ratio table   0x440E3398[104..115]: 6 -> 7
  pan table     0x440E4F70[5] (category 5 = 65:24): 0.375 -> 3048/8256 (only reader: the fit function 0x4079F124)
  fit function  0x4079F180 'b.eq' after 'cmp w0,#6' -> 'b.hs': categories 6 and 7 take the generic fit from the image size
  GUI boxes     0x4054180C / 0x4068E9DC 'cmp #2' -> 'cmp #3': categories 5, 6, 7 use entry 0 of the 6-entry GUI box
                tables (stock maps 5 and 6 there; 7 would read past the table)
  decode sizes  0x440E3A78 (rows = categories, 4 tiers) moved to the playback block with 8 rows: 5 = 65:24, 7 = 2.39:1
                (stock rule: tier widths 2304/1920/1280/960, height = nearest multiple of 8 of width x H/W); the lookup
                0x40795ABC/0x40795AC4 points at it; bounds 'cmp w0,#4; b.hi' -> 'cmp w0,#7', 'cmp w0,#2' -> 'cmp w0,#6' and
                A2e's nop of the next 'b.eq' is dropped (stock b.eq): 0..5 and 7 accepted, 6 rejected
  box rule      0x40790BAC set A / set B: front caves for categories 5 and 7 (w = W, h = W x H/W floor, as stock 16:9),
                other categories tail to the A2e caves unchanged
  records       preview record jump tables 0x440E92F8 / 0x440E92C0 (index slot - 2) and 0x440E9330 (index slot): slots 3
                and 6 -> caves with the capture's sizes (thumbnail / small / large)

apply(img, eg, at=0x40B7E000, limit=0x40B80000) -> det.  img is the hb1.Image of A2h + pipeline; every edit names the stock
bytes it replaces (an A2e edit is dropped first and the stock bytes are the expect).
"""
import struct
from pathlib import Path

ROM, DOFF, DVA = 0x40160000, 0x4B13000, 0xA02808000
AREAS = {3: dict(name='2.39:1', jpeg=(8256, 3456), cat=7, thumb=(320, 132), small=(640, 264), large=(1920, 800)),
         6: dict(name='65:24', jpeg=(8256, 3048), cat=5, thumb=(320, 116), small=(640, 236), large=(1920, 708))}
RATIO_TABLE, R7 = 0x440E3398, (104, 115)
PAN = 0x440E4F70
FIT_SITE, FIT_GENERIC = 0x4079F180, 0x4079F1E8
GUI_SITES = {0x4054180C: 9, 0x4068E9DC: 24}                       # 'cmp wN, #2' after 'sub wN, wcat, #5'
DECODE_TABLE, DECODE_LO, DECODE_HI, DECODE_TIERS = 0x440E3A78, 0x40795ABC, 0x40795AC4, (2304, 1920, 1280, 960)
DECODE_CMP4, DECODE_CMP2, DECODE_REJECT, DECODE_FAIL = 0x40795AAC, 0x40795AB4, 0x40795AB8, 0x40795B2C
BOX_A_SITE, BOX_B_SITE, CAVE_BOX_A, CAVE_BOX_B = 0x40790DF4, 0x40790E3C, 0x40B7C480, 0x40B7C4C0
BOX_A_STORE, BOX_B_STORE = 0x40790EB4, 0x40790FA4
REC_TABLES = {'thumb': (0x440E92F8, 2, 7, 0x407CD568), 'small': (0x440E92C0, 2, 7, 0x407CD568), 'large': (0x440E9330, 0, 9, 0x407CD5F8)}


def off(va): return va - DVA + DOFF if va >= DVA else va - ROM
def W(*ws): return struct.pack('<%dI' % len(ws), *ws)
def b_(at, to): d = (to - at) >> 2; assert -(1 << 25) <= d < 1 << 25; return 0x14000000 | d & 0x3FFFFFF
def bcond(at, to, c): d = (to - at) >> 2; assert -(1 << 18) <= d < 1 << 18; return 0x54000000 | (d & 0x7FFFF) << 5 | c
def cmpw(n, imm): return 0x7100001F | imm << 10 | n << 5
def movzw(d, imm): return 0x52800000 | imm << 5 | d
def movz(d, imm, hw): return 0xD2800000 | hw << 21 | imm << 5 | d
def movk(d, imm, hw): return 0xF2800000 | hw << 21 | imm << 5 | d
def ldrsh(t, n, imm): return 0x79C00000 | (imm >> 1) << 10 | n << 5 | t
def mulw(d, n, m): return 0x1B007C00 | m << 16 | n << 5 | d
def udivw(d, n, m): return 0x1AC00800 | m << 16 | n << 5 | d
AND_W9_W10_FFFF = 0x12003D49                                        # and w9, w10, #0xffff (stock 16:9 set A)
EQ, NE, HS = 0, 1, 2


def ratio_hd(cat):
    """h = W * num / den of the category's JPEG L ratio (reduced)."""
    from math import gcd
    w, h = next(s['jpeg'] for s in AREAS.values() if s['cat'] == cat); g = gcd(w, h); return h // g, w // g


def near8(x):
    lo = int(x) // 8 * 8
    return lo if x - lo < lo + 8 - x else lo + 8


class Ctx:
    def __init__(self, img, eg): self.img, self.eg, self.rows = img, eg, []
    def u(self, f, va, n=1, new=False):
        return list(struct.unpack_from('<%d%s' % (n, f), self.img.new if new else self.eg, off(va)))
    def put(self, va, data, why, zero=False):
        o = off(va); old = bytes(self.eg[o:o + len(data)])
        self.img.put(o, data, why, expect=None if zero else old, expect_zero=zero, offset=True)
        self.rows.append(dict(va=hex(va), bytes=len(data), why=why))
    def drop(self, prefix):
        hit = [e for e in self.img.edits if e['purpose'].startswith(prefix)]
        assert len(hit) == 1, (prefix, len(hit))
        e = hit[0]; self.img.new[e['offset']:e['end']] = e['old']; self.img.edits.remove(e)
        return dict(offset=hex(e['offset']), bytes=e['end'] - e['offset'], purpose=e['purpose'])


class Alloc:
    def __init__(self, at, end): self.at, self.end, self.used = at, end, []
    def take(self, n, why, align=16):
        self.at = -(-self.at // align) * align; a = self.at; self.at += n
        assert self.at <= self.end, ('playback block full', why); self.used.append([hex(a), n, why]); return a


def apply(img, eg, at=0x40B7E000, limit=0x40B80000):
    c = Ctx(img, eg); al = Alloc(at, limit); det = {}
    # ---- 1. ratio table: r 104..115 -> category 7
    t = c.u('B', RATIO_TABLE, 256)
    runs = []; s = 0
    for i in range(1, 257):
        if i == 256 or t[i] != t[s]: runs.append((s, i - 1, t[s])); s = i
    assert runs == [(0, 11, 4), (12, 87, 6), (88, 103, 5), (104, 136, 6), (137, 159, 1), (160, 180, 0), (181, 197, 2), (198, 210, 3), (211, 255, 4)], runs
    for a, sp in AREAS.items():                                       # every image of the file falls in its category
        for w, h in (sp['thumb'], sp['small'], sp['large'], sp['jpeg']):
            r = min(255, 256 * h // w); assert (R7[0] <= r <= R7[1]) if sp['cat'] == 7 else (88 <= r <= 103), (a, w, h, r)
    c.put(RATIO_TABLE + R7[0], bytes([7]) * (R7[1] - R7[0] + 1), f'playback ratio table {RATIO_TABLE:#x} r {R7[0]}..{R7[1]}: 6 -> 7 (2.39:1)')
    det['ratio_table'] = dict(stock_runs=runs, new=f'{R7[0]}..{R7[1]} -> 7')
    # ---- 2. pan table: category 5 = the 65:24 H/W
    pan = c.u('f', PAN, 8); assert [round(x, 4) for x in pan] == [0.6667, 0.5625, 0.75, 0.8, 1.0, 0.375, 0.0, 0.0], pan
    v5 = 3048 / 8256
    c.put(PAN + 4 * 5, struct.pack('<f', v5), f'playback pan table {PAN:#x}[5] (category 5 = 65:24): 0.375 (8:3) -> {v5:.6f}')
    det['pan'] = dict(stock=pan, new5=struct.unpack('<f', struct.pack('<f', v5))[0])
    # ---- 3. fit function: >= 6 -> generic fit
    assert c.u('I', FIT_SITE - 4, 2) == [cmpw(0, 6), bcond(FIT_SITE, FIT_GENERIC, EQ)]
    c.put(FIT_SITE, W(bcond(FIT_SITE, FIT_GENERIC, HS)), '0x4079f124 fit: cmp w0,#6; b.eq generic -> b.hs (category 7 takes the generic fit like 6)')
    # ---- 4. GUI box tables: categories 5, 6, 7 -> entry 0
    for site, reg in GUI_SITES.items():
        assert c.u('I', site)[0] == cmpw(reg, 2), hex(site)
        c.put(site, W(cmpw(reg, 3)), f'GUI box category index {site:#x}: (cat - 5) < 2 -> < 3 (categories 5, 6, 7 -> entry 0; 7 would read past the 6-entry table)')
    det['gui_sites'] = [hex(x) for x in GUI_SITES]
    # ---- 5. decode-size table with 8 rows
    rows = [[struct.unpack_from('<HH', c.img.new, off(DECODE_TABLE) + 16 * r + 4 * k) for k in range(4)] for r in range(6)]
    for r, (num, den) in ((0, (2, 3)), (1, (9, 16)), (2, (3, 4)), (3, (4, 5)), (4, (1, 1))):   # stock rule (row 2 = A2e)
        assert rows[r] == [(w, near8(w * num / den)) for w in DECODE_TIERS], (r, rows[r])
    assert rows[5] == [(0, 0)] * 4
    new_rows = rows[:5] + [[(0, 0)] * 4] * 3
    for a, sp in AREAS.items():
        num, den = sp['jpeg'][1], sp['jpeg'][0]
        new_rows[sp['cat']] = [(w, near8(w * num / den)) for w in DECODE_TIERS]
    data = b''.join(struct.pack('<HH', *x) for row in new_rows for x in row)
    tab = al.take(len(data), 'decode-size table (8 categories x 4 tiers)')
    c.put(tab, data, f'playback decode-size table {DECODE_TABLE:#x} moved to {tab:#x}: rows 0..4 as before, 5 (65:24) {new_rows[5]}, 7 (2.39:1) {new_rows[7]}', zero=True)
    assert c.u('I', DECODE_LO)[0] == movz(9, 0x3A78, 0) and c.u('I', DECODE_HI)[0] == movk(9, 0x440E, 1)
    assert tab >> 32 == 0
    c.put(DECODE_LO, W(movz(9, tab & 0xFFFF, 0)), f'decode-size lookup 0x40795a9c: table low half -> {tab:#x}')
    c.put(DECODE_HI, W(movk(9, tab >> 16, 1)), f'decode-size lookup 0x40795a9c: table high half -> {tab:#x}')
    assert c.u('I', DECODE_CMP4, 4) == [cmpw(0, 4), bcond(DECODE_CMP4 + 4, DECODE_FAIL, 8), cmpw(0, 2), bcond(DECODE_REJECT, DECODE_FAIL, EQ)]
    dropped = [c.drop('0x40795a9c: category 2 no longer sent')]
    c.put(DECODE_CMP4, W(cmpw(0, 7)), 'decode-size selection 0x40795a9c: category bound 4 -> 7 (rows 5 and 7 present)')
    c.put(DECODE_CMP2, W(cmpw(0, 6)), 'decode-size selection 0x40795a9c: cmp w0,#2 -> cmp w0,#6 (the stock b.eq then rejects only 6; A2e nop dropped)')
    det['decode'] = dict(table=hex(tab), rows=new_rows, dropped=dropped)
    # ---- 6. box rule front caves
    box = {}
    for name, site, cave, store, load_reg in (('A', BOX_A_SITE, CAVE_BOX_A, BOX_A_STORE, 10), ('B', BOX_B_SITE, CAVE_BOX_B, BOX_B_STORE, 8)):
        assert c.u('I', site)[0] == cmpw(0, 3)
        fa = al.take(4 * 32, f'box rule set {name} front cave'); code = []
        # layout: cmp #5; b.eq c5; cmp #7; b.eq c7; b a2e; c5: 7 words; c7: 7 words
        c5 = fa + 20; c7 = c5 + 28
        code += [cmpw(0, 5), bcond(fa + 4, c5, EQ), cmpw(0, 7), bcond(fa + 12, c7, EQ), b_(fa + 16, cave)]
        for cat, base in ((5, c5), (7, c7)):
            num, den = ratio_hd(cat)
            if name == 'A':      # w10 = W, w8 = h, w9 = W & 0xffff, then the stock 'strh w10,[sp,#0x66]' at 0x40790eb4
                code += [ldrsh(10, 31, 0x40), movzw(11, num), mulw(8, 10, 11), movzw(11, den), udivw(8, 8, 11), AND_W9_W10_FFFF,
                         b_(base + 24, store)]
            else:                # w8 = W, w9 = h, then the stock stores at 0x40790fa4
                code += [ldrsh(8, 31, 0x40), movzw(11, num), mulw(9, 8, 11), movzw(11, den), udivw(9, 9, 11), 0xD503201F,
                         b_(base + 24, store)]
        blob = W(*code); assert len(blob) == 4 * 19
        c.put(fa, blob, f'box rule set {name} front cave: categories 5 (65:24) and 7 (2.39:1) -> w = W, h = W x H/W (floor), else A2e cave {cave:#x}', zero=True)
        box[name] = dict(cave=hex(fa), a2e_cave=hex(cave), words=blob.hex())
    box['dropped'] = [c.drop('0x40790bac set A'), c.drop('0x40790bac set B')]
    c.put(BOX_A_SITE, W(b_(BOX_A_SITE, int(box['A']['cave'], 16))), '0x40790bac set A: cmp w0,#3 -> b front cave (5, 7; then A2e cave)')
    c.put(BOX_B_SITE, W(b_(BOX_B_SITE, int(box['B']['cave'], 16))), '0x40790bac set B: cmp w0,#3 -> b front cave (5, 7; then A2e cave)')
    det['box'] = box
    # ---- 7. preview records for slots 3 and 6
    rec = {}
    for kind, (tabva, base, n, cont) in REC_TABLES.items():
        ent = c.u('Q', tabva, n)
        for a, sp in AREAS.items():
            w, h = sp[kind]; cave = al.take(12, f'{kind} record slot {a}')
            c.put(cave, W(movzw(9, w), movzw(10, h), b_(cave + 8, cont)), f'preview record ({kind}) of slot {a} ({sp["name"]}): {w}x{h}', zero=True)
            i = a - base; old = ent[i]
            c.put(tabva + 8 * i, struct.pack('<Q', cave), f'preview record jump table {tabva:#x} [{i}] (slot {a}): {old:#x} -> {cave:#x}')
            rec[f'{kind}_{a}'] = dict(cave=hex(cave), size=[w, h], stock_target=hex(old))
    det['records'] = rec
    det['regions'] = al.used
    det['edits'] = len(c.rows)
    det['edit_rows'] = c.rows
    return det
