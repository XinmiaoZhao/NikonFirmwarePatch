import math
import struct
import json
from pathlib import Path
H = Path(__file__).resolve().parent
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
from . import focus_grid as F
E, hb1, sha = F.E, F.hb1, F.sha

BASE = hb1.BASE

# ---------------------------------------------------------------- 1. distortion tables (u16 per area slot 0..8)
D6828, D683A, CC2C8 = 0xA029D6828, 0xA029D683A, 0xA029CC2C8
JPEG_L = [(8256, 5504), (5392, 3592), (0, 0), (0, 0), (8256, 4640), (5392, 3032), (1920, 1080), (3840, 2160), (5504, 5504)]
NOMINAL = {0: 3 / 2, 1: 3 / 2, 4: 16 / 9, 5: 16 / 9, 6: 16 / 9, 7: 16 / 9, 8: 1.0}
A43 = (7344, 5504)


def u16s(eg, va, n=9): return list(struct.unpack_from(f'<{n}H', eg, hb1.data_off(va)))


def distortion(eg):
    t1, t2, t3 = u16s(eg, D6828), u16s(eg, D683A), u16s(eg, CC2C8)
    diag = lambda w, h: math.hypot(w, h)
    for s, (w, h) in enumerate(JPEG_L):
        if t1[s]: assert t1[s] == math.floor(4096 * diag(w, h) / diag(*JPEG_L[0])), ('D6828', s)
        if t3[s]: assert t3[s] == math.floor(4096 / math.sqrt(1 + NOMINAL[s] ** 2)), ('CC2C8', s)
    assert t1[2] == t2[2] == t3[2] == 0
    v1 = math.floor(4096 * diag(*A43) / diag(*JPEG_L[0])); v3 = math.floor(4096 / math.sqrt(1 + (4 / 3) ** 2))
    ratio = min(t2[s] / t1[s] for s in range(9) if t1[s] and t2[s]); v2 = math.floor(v1 * ratio)
    assert (v1, v2, v3) == (3788, 3782, 2457), (v1, v2, v3)
    return [(D6828, v1, 'distortion: JPEG-L diagonal / FX diagonal x 4096 (floor), area 2 = 4:3 7344x5504'),
            (D683A, v2, f'distortion variant (mode 6): estimate 3788 x min stock ratio {ratio:.6f} (no exact rule)'),
            (CC2C8, v3, 'distortion: nominal half height / half diagonal x 4096 (floor), area 2 = 4:3')], dict(
        stock=dict(D6828=t1, D683A=t2, CC2C8=t3), area2=dict(D6828=v1, D683A=v2, CC2C8=v3), d683a_ratio_min=round(ratio, 6))


# ---------------------------------------------------------------- 2. icons
RES, NRES = 0x30796D0, 6242            # payload offset of the resource table: (flag u32, size u32, 0, 0, ptr u64) x 0x18
ICONS = {0xD22: 'menu 36x36', 0x84A: 'live view 36x32', 0x13C8: 'playback 28x28', 0x59F: '1-bit 42x36', 0x5A0: '1-bit 46x36'}
ROW_ICON = (0x43DD2AF8, 0xFFFF, 0xD22)  # page 1068 row 2 (4:3), icon field
SWITCHES = {0x405DBD78: 21, 0x405D99F4: 1}     # 'Choose image area' value icon: entry (w21) / refresh (w1)
SW_STOCK = lambda r: [f'cmp w0, #8', 'b.eq', 'cmp w0, #4', 'b.eq', 'cmp w0, #1', 'b.ne', f'mov w{r}, #0xd23', 'b',
                      f'mov w{r}, #0x1132', 'b', f'mov w{r}, #0x1173', 'b', f'mov w{r}, #0xd25']


def record(eg, i): return struct.unpack_from('<IIIIQ', eg, RES + 0x18 * i)


def png_size(p):
    assert p[:8] == b'\x89PNG\r\n\x1a\n' and p[12:16] == b'IHDR'; return struct.unpack('>II', p[16:24])


# ---------------------------------------------------------------- 3. corner marks / lit points
CORNER_HOOK, CORNER_FN = 0x403EB934, 0x41186FE4
POINTS_HOOK, POINTS_FN = 0x41186CA4, 0x41186ABC
IDX_FN, STATE_PTR, SEL_TABLE = 0x41187104, 0xA03227C50, 0x42AC19D0
WIN_TABLES = (0x44B7FD68, 0x44B7FF48)
CAVE_CORNER, CAVE_POINTS, CAVE_PNG, CAVE_END = 0x40B7C500, 0x40B7C580, 0x40B7C700, 0x40B7D000

# A64 encoders (checked against capstone below)
def b_(at, to, link=False):
    d = (to - at) >> 2; assert -(1 << 25) <= d < 1 << 25; return (0x94000000 if link else 0x14000000) | d & 0x3FFFFFF
def bcond(at, to, c): d = (to - at) >> 2; assert -(1 << 18) <= d < 1 << 18; return 0x54000000 | (d & 0x7FFFF) << 5 | c
def cbz(at, to, rt, nz=False, x=False): d = (to - at) >> 2; return (0x35000000 if nz else 0x34000000) | (0x80000000 if x else 0) | (d & 0x7FFFF) << 5 | rt
def stp_pre(t, t2, imm): return 0xA9800000 | ((imm >> 3) & 0x7F) << 15 | t2 << 10 | 31 << 5 | t
def stp(t, t2, imm): return 0xA9000000 | ((imm >> 3) & 0x7F) << 15 | t2 << 10 | 31 << 5 | t
def ldp(t, t2, imm): return 0xA9400000 | ((imm >> 3) & 0x7F) << 15 | t2 << 10 | 31 << 5 | t
def ldp_post(t, t2, imm): return 0xA8C00000 | ((imm >> 3) & 0x7F) << 15 | t2 << 10 | 31 << 5 | t
def movx(d, m): return 0xAA0003E0 | m << 16 | d
def movw(d, m): return 0x2A0003E0 | m << 16 | d
def ldrw(t, n, imm): return 0xB9400000 | (imm >> 2) << 10 | n << 5 | t
def ldrx(t, n, imm): return 0xF9400000 | (imm >> 3) << 10 | n << 5 | t
def ldrb(t, n, imm): return 0x39400000 | imm << 10 | n << 5 | t
def ldrh(t, n, imm): return 0x79400000 | (imm >> 1) << 10 | n << 5 | t
def strh(t, n, imm): return 0x79000000 | (imm >> 1) << 10 | n << 5 | t
def ldrsh_lsl1(t, n, m): return 0x78E07800 | m << 16 | n << 5 | t
def cmpw(n, imm): return 0x7100001F | imm << 10 | n << 5
def addw(d, n, m): return 0x0B000000 | m << 16 | n << 5 | d
def addxi(d, n, imm): return 0x91000000 | imm << 10 | n << 5 | d
def subsw_i(d, n, imm): return 0x71000000 | imm << 10 | n << 5 | d
def adr(at, to, d): o = to - at; return 0x10000000 | (o & 3) << 29 | ((o >> 2) & 0x7FFFF) << 5 | d
def movz(d, imm, hw): return 0xD2800000 | hw << 21 | imm << 5 | d
def movk(d, imm, hw): return 0xF2800000 | hw << 21 | imm << 5 | d
def movzw(d, imm): return 0x52800000 | imm << 5 | d
def cselw(d, n, m, c): return 0x1A800000 | m << 16 | c << 12 | n << 5 | d
RET = 0xD65F03C0
EQ, NE, HI = 0, 1, 8


class Asm:
    """two-pass list of (label | callable(at) -> word | ('word', w))."""
    def __init__(self, at): self.at, self.items, self.labels = at, [], {}
    def label(self, n): self.items.append(('label', n))
    def i(self, f): self.items.append(('ins', f))
    def half(self, *v): self.items.append(('half', v))
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


def cave_corner(D):
    s = Asm(CAVE_CORNER); L = lambda n: (lambda: s.labels[n])
    s.i(stp_pre(29, 30, -32)); s.i(stp(19, 20, 16)); s.i(movx(19, 0)); s.i(movx(20, 1))
    s.i(lambda a: b_(a, CORNER_FN, True))
    s.i(lambda a: cbz(a, L('done')(), 0))
    s.i(ldrw(9, 19, 4)); s.i(cmpw(9, 3)); s.i(lambda a: bcond(a, L('done')(), NE))
    s.i(ldrb(9, 19, 8)); s.i(lambda a: cbz(a, L('done')(), 9, nz=True))
    s.i(ldrw(9, 19, 0)); s.i(cmpw(9, 2)); s.i(lambda a: bcond(a, L('done')(), HI))
    s.i(lambda a: adr(a, L('dtab')(), 10)); s.i(ldrsh_lsl1(10, 10, 9))
    s.i(ldrh(11, 20, 0)); s.i(addw(11, 11, 10)); s.i(strh(11, 20, 0))
    s.i(ldrh(11, 20, 4)); s.i(addw(11, 11, 10)); s.i(strh(11, 20, 4))
    s.label('done'); s.i(ldp(19, 20, 16)); s.i(ldp_post(29, 30, 32)); s.i(RET)
    s.label('dtab'); s.half(*D, 0)
    return s.build(), s.labels


def cave_points(D):
    s = Asm(CAVE_POINTS); L = lambda n: (lambda: s.labels[n])
    s.i(stp_pre(29, 30, -48)); s.i(stp(19, 20, 16)); s.i(stp(21, 22, 32))
    s.i(movx(19, 1)); s.i(movx(20, 3)); s.i(movw(21, 2))
    s.i(lambda a: b_(a, POINTS_FN, True)); s.i(movw(22, 0))
    s.i(movz(9, STATE_PTR & 0xFFFF, 0)); s.i(movk(9, STATE_PTR >> 16 & 0xFFFF, 1)); s.i(movk(9, STATE_PTR >> 32 & 0xFFFF, 2))
    s.i(ldrx(9, 9, 0)); s.i(lambda a: cbz(a, L('done')(), 9, x=True))
    s.i(ldrw(9, 9, 0x1C8)); s.i(cmpw(9, 2)); s.i(lambda a: bcond(a, L('done')(), NE))
    s.i(ldrb(9, 19, 8)); s.i(lambda a: cbz(a, L('done')(), 9, nz=True))
    s.i(ldrw(9, 19, 0)); s.i(cmpw(9, 2)); s.i(lambda a: bcond(a, L('done')(), HI))
    s.i(movx(0, 19)); s.i(lambda a: b_(a, IDX_FN, True)); s.i(lambda a: cbz(a, L('done')(), 0, nz=True))
    s.i(ldrw(9, 19, 0)); s.i(lambda a: adr(a, L('dtab')(), 10)); s.i(ldrsh_lsl1(10, 10, 9))
    s.i(lambda a: cbz(a, L('done')(), 21)); s.i(movw(11, 21)); s.i(movx(12, 20))
    s.label('loop')
    s.i(ldrh(13, 12, 0)); s.i(addw(13, 13, 10)); s.i(strh(13, 12, 0))
    s.i(ldrh(13, 12, 4)); s.i(addw(13, 13, 10)); s.i(strh(13, 12, 4))
    s.i(addxi(12, 12, 8)); s.i(subsw_i(11, 11, 1)); s.i(lambda a: bcond(a, L('loop')(), NE))
    s.label('done'); s.i(movw(0, 22)); s.i(ldp(21, 22, 32)); s.i(ldp(19, 20, 16)); s.i(ldp_post(29, 30, 48)); s.i(RET)
    s.label('dtab'); s.half(*D, 0)
    return s.build(), s.labels


def text(code, at, n=None):
    return [f'{i.mnemonic} {i.op_str}' for i in md.disasm(code[:4 * n] if n else code, at)]


CORNER_TEXT = lambda D: [
    'stp x29, x30, [sp, #-0x20]!', 'stp x19, x20, [sp, #0x10]', 'mov x19, x0', 'mov x20, x1', f'bl #{CORNER_FN:#x}',
    'cbz w0, #{done}', 'ldr w9, [x19, #4]', 'cmp w9, #3', 'b.ne #{done}', 'ldrb w9, [x19, #8]', 'cbnz w9, #{done}',
    'ldr w9, [x19]', 'cmp w9, #2', 'b.hi #{done}', 'adr x10, #{dtab}', 'ldrsh w10, [x10, x9, lsl #1]',
    'ldrh w11, [x20]', 'add w11, w11, w10', 'strh w11, [x20]', 'ldrh w11, [x20, #4]', 'add w11, w11, w10', 'strh w11, [x20, #4]',
    'ldp x19, x20, [sp, #0x10]', 'ldp x29, x30, [sp], #0x20', 'ret ']
POINTS_TEXT = [
    'stp x29, x30, [sp, #-0x30]!', 'stp x19, x20, [sp, #0x10]', 'stp x21, x22, [sp, #0x20]', 'mov x19, x1', 'mov x20, x3',
    'mov w21, w2', f'bl #{POINTS_FN:#x}', 'mov w22, w0', 'mov x9, #0x7c50', 'movk x9, #0x322, lsl #16', 'movk x9, #0xa, lsl #32',
    'ldr x9, [x9]', 'cbz x9, #{done}', 'ldr w9, [x9, #0x1c8]', 'cmp w9, #2', 'b.ne #{done}', 'ldrb w9, [x19, #8]',
    'cbnz w9, #{done}', 'ldr w9, [x19]', 'cmp w9, #2', 'b.hi #{done}', 'mov x0, x19', f'bl #{IDX_FN:#x}', 'cbnz w0, #{done}',
    'ldr w9, [x19]', 'adr x10, #{dtab}', 'ldrsh w10, [x10, x9, lsl #1]', 'cbz w21, #{done}', 'mov w11, w21', 'mov x12, x20',
    'ldrh w13, [x12]', 'add w13, w13, w10', 'strh w13, [x12]', 'ldrh w13, [x12, #4]', 'add w13, w13, w10', 'strh w13, [x12, #4]',
    'add x12, x12, #8', 'subs w11, w11, #1', 'b.ne #{loop}', 'mov w0, w22', 'ldp x21, x22, [sp, #0x20]', 'ldp x19, x20, [sp, #0x10]',
    'ldp x29, x30, [sp], #0x30', 'ret ']


def window_d(img):
    """D per layout 0..2 = left(category 0, 3:2) - left(category 3, 4:3) in the composed (A2d) window tables."""
    new = bytes(img.new); D = []
    for lay in range(3):
        l = {t: [struct.unpack_from('<4H', new, t + lay * 0x28 + c * 8 - BASE) for c in (0, 3)] for t in WIN_TABLES}
        assert l[WIN_TABLES[0]] == l[WIN_TABLES[1]]
        r32, r43 = l[WIN_TABLES[0]]
        assert r43[1] == r32[1] and r43[3] == r32[3] and r43[0] > r32[0], (lay, r32, r43)
        D.append(r32[0] - r43[0])
    assert D == [-58, -72, -58], D
    return D


def using_stock_palette(mask, stock):
    """Encode our one-bit glyph in the camera's original two-color palette and transparency."""
    def parts(png):
        at = 8
        while at < len(png):
            size, kind = struct.unpack_from('>I4s',png,at)
            yield kind,png[at:at+size+12]
            at += size+12
    original = list(parts(stock))
    authored = dict(parts(mask))
    assert [kind for kind,_ in original]==[b'IHDR',b'sBIT',b'PLTE',b'tRNS',b'IDAT',b'IEND']
    assert set(authored)=={b'IHDR',b'IDAT',b'IEND'} and mask[24:26]==b'\x01\x00'
    assert stock[16:25]==mask[16:25] and stock[25]==3
    return stock[:8]+b''.join(authored[kind] if kind==b'IDAT' else chunk for kind,chunk in original)


def compose(eg):
    img, det = F.compose(eg)
    # 1 distortion
    edits, dd = distortion(eg)
    for va, v, why in edits: img.put(hb1.data_off(va) + 4, struct.pack('<H', v), why + f' = {v}', expect=b'\0\0', offset=True)
    det['distortion'] = dd
    # 2 icons
    fam = json.loads((H / 'icons/icon-43.json').read_text())['families']
    stock_sha = {int(f['icon'], 16): f['stock_png']['sha256'] for f in fam.values()}
    rows = []
    png_cave = CAVE_PNG
    for i, what in ICONS.items():
        flag, size, z0, z1, ptr = record(eg, i); old = eg[ptr - BASE:ptr - BASE + size]
        assert sha(old) == stock_sha[i] and z0 == z1 == 0, hex(i)
        new = (H / f'icons/new/{i:04x}_43.png').read_bytes(); assert png_size(new) == png_size(old), hex(i)
        if i in (0x59F,0x5A0):
            new = using_stock_palette(new,old)
        if len(new) <= size:
            img.put(ptr, new + bytes(size - len(new)), f'icon {i:#x} ({what}) PNG 5:4 -> 4:3 in place, {size} -> {len(new)} bytes (tail zero)')
            img.put(RES + 0x18 * i + 4, struct.pack('<I', len(new)), f'icon {i:#x} resource record: size {size} -> {len(new)}',
                    expect=struct.pack('<I', size), offset=True)
            rows.append(dict(icon=hex(i), what=what, how='in place', ptr=hex(ptr), old_bytes=size, new_bytes=len(new), new_sha256=sha(new)))
        else:
            assert png_cave + len(new) <= CAVE_END
            img.put(png_cave, new, f'icon {i:#x} ({what}) PNG 4:3 in the loader-copied cave ({len(new)} bytes)', expect_zero=True)
            img.put(RES + 0x18 * i + 4, struct.pack('<IIIQ', len(new), 0, 0, png_cave),
                    f'icon {i:#x} resource record: size {size} -> {len(new)}, ptr {ptr:#x} -> {png_cave:#x}',
                    expect=struct.pack('<IIIQ', size, 0, 0, ptr), offset=True)
            rows.append(dict(icon=hex(i), what=what, how='moved to cave', old_ptr=hex(ptr), ptr=hex(png_cave), old_bytes=size,
                             new_bytes=len(new), new_sha256=sha(new)))
            png_cave += (len(new) + 15) & ~15
    va, o, n = ROW_ICON
    img.put(va, struct.pack('<I', n), 'menu page 1068 row 2 (4:3, item 2be9): icon 0xffff -> 0xd22 (4:3 after the PNG swap)',
            expect=struct.pack('<I', o))
    sw = {}
    for at, r in SWITCHES.items():
        t = [x.split(' #')[0] if x.startswith('b') else x for x in text(eg[at - BASE:at - BASE + 52], at)]
        assert t == SW_STOCK(r), (hex(at), t)
        words = [movzw(r, 0xD25)]
        for v, ic in ((1, 0xD23), (8, 0x1132), (4, 0x1173), (2, 0xD22)):
            words += [cmpw(0, v), movzw(8, ic), cselw(r, 8, r, EQ)]
        code = struct.pack('<13I', *words)
        assert text(code, at) == [f'mov w{r}, #0xd25'] + sum(([f'cmp w0, #{v}', f'mov w8, #{ic:#x}', f'csel w{r}, w8, w{r}, eq']
                                                             for v, ic in ((1, 0xD23), (8, 0x1132), (4, 0x1173), (2, 0xD22))), [])
        img.put(at, code, f'"Choose image area" value icon switch at {at:#x}: values 1/8/4 as stock, value 2 (4:3) -> 0xd22, else 0xd25',
                expect=eg[at - BASE:at - BASE + 52])
        sw[hex(at)] = dict(register=f'w{r}', words=code.hex())
    det['icons'] = dict(resources=rows, menu_row_icon=dict(va=hex(va), old=hex(o), new=hex(n)), switches=sw)
    # 3 corner marks / lit points
    assert struct.unpack_from('<8i', eg, SEL_TABLE - BASE) == (1, 3, 0, 4, 5, 0, 6, 2)      # sel 3 only for area code 2
    D = window_d(img)
    cc, cl = cave_corner(D); pc, pl = cave_points(D)
    fmt = lambda tl, lab: [x.replace('{done}', f'{lab["done"]:#x}').replace('{dtab}', f'{lab["dtab"]:#x}').replace('{loop}', f'{lab.get("loop", 0):#x}') for x in tl]
    assert text(cc[:cl['dtab'] - CAVE_CORNER], CAVE_CORNER) == fmt(CORNER_TEXT(D), cl), text(cc, CAVE_CORNER)
    assert text(pc[:pl['dtab'] - CAVE_POINTS], CAVE_POINTS) == fmt(POINTS_TEXT, pl), text(pc, CAVE_POINTS)
    assert CAVE_CORNER + len(cc) <= CAVE_POINTS and CAVE_POINTS + len(pc) <= CAVE_PNG
    img.put(CAVE_CORNER, cc, f'cave_corner43: 41186FE4, then x0/x1 + D{D} when sel 3 (area 2), +8 = 0, layout <= 2', expect_zero=True)
    img.put(CAVE_POINTS, pc, f'cave_points43: 41186ABC, then x0/x1 of each rect + D{D} when area code 2, idx 0, +8 = 0, layout <= 2',
            expect_zero=True)
    img.put(CORNER_HOOK, struct.pack('<I', b_(CORNER_HOOK, CAVE_CORNER)), 'GUI corner box trampoline: b 41186FE4 -> b cave_corner43',
            expect=struct.pack('<I', b_(CORNER_HOOK, CORNER_FN)))
    img.put(POINTS_HOOK, struct.pack('<I', b_(POINTS_HOOK, CAVE_POINTS, True)), 'GUI lit points 41186C68: bl 41186ABC -> bl cave_points43',
            expect=struct.pack('<I', b_(POINTS_HOOK, POINTS_FN, True)))
    det['af_display'] = dict(D_by_layout=D, cave_corner=dict(at=hex(CAVE_CORNER), bytes=len(cc), sha256=sha(cc)),
                             cave_points=dict(at=hex(CAVE_POINTS), bytes=len(pc), sha256=sha(pc)),
                             hooks={hex(CORNER_HOOK): 'b cave_corner43', hex(POINTS_HOOK): 'bl cave_points43'})
    return img, det
