import struct
from . import focus_icons as G
F, E, hb1, sha = G.F, G.E, G.hb1, G.sha

BASE = hb1.BASE
EQ, NE, HI = G.EQ, G.NE, G.HI

# ---------------------------------------------------------------- 1. custom wide-area maximum
MAX_FN, MAX_STORE, MAX_RET, MAX_JT = 0x40F1CB94, 0x40F1CC38, 0x40F1CC40, 0xA02A27FA0
CAVE_MAX = 0x40B7C800
MAX_43 = (25, 17)
# ---------------------------------------------------------------- 2/3. corner box / lit points
GETPROP, PROP_AREA, PROP_MOVIE = 0x403EC398, 0x219E, 0x218C
CAVE_CORNER2 = 0x40B7C840
CELL = (32, 40, 32)          # stock cell width of layouts 0..2 (FX box width - 1:1 box width) / (2 * 5); test_a2h executes it
K43 = 2                      # (29 - 25) / 2, the A8 single-point cut


# ---------------------------------------------------------------- 4. live-view geometry descriptor
GEOM_FN, GEOM_JT, GEOM_DEFAULT, GEOM_11, GEOM_TAIL = 0x41065194, 0xA02A977B8, 0x410664EC, 0x41066150, 0x410664DC
CAVE_GEOM = 0x40B7C920
EVF_H, LCD_H, LCD_W_FX = 0x354, 0x360, 0x510          # 852, 864, 1296 (stock FX / 1:1 cases)
EVF_W43, LCD_W43 = EVF_H * 4 // 3, LCD_H * 4 // 3      # 1136, 1152
PAD43 = (LCD_W_FX - LCD_W43) // 2                      # 72


def stpw(t, t2, n, imm): return 0x29000000 | ((imm >> 2) & 0x7F) << 15 | t2 << 10 | n << 5 | t
def strw(t, n, imm): return 0xB9000000 | (imm >> 2) << 10 | n << 5 | t


def cave_geom():
    """The stock 1:1 case (41066150) with the 4:3 display values; same registers, same stack slots, same tail."""
    s = G.Asm(CAVE_GEOM); W = 31
    s.i(G.movzw(8, PAD43)); s.i(stpw(W, W, 31, 0x20)); s.i(G.movzw(9, LCD_H)); s.i(stpw(W, W, 31, 0xC))
    s.i(G.movzw(7, EVF_W43)); s.i(strw(W, 31, 8)); s.i(strw(8, 31, 0x14)); s.i(G.movzw(8, 8))
    for r in (16, 10, 12): s.i(G.movw(r, W))
    s.i(stpw(8, W, 31, 0x18))
    for r in (3, 5, 18, 2, 25): s.i(G.movw(r, W))
    for r, v in ((24, 0x72C), (26, 0xAC4), (17, 2), (15, 4), (8, LCD_W_FX), (4, 0x728), (1, 0xABC)): s.i(G.movzw(r, v))
    s.i(G.movzw(27, EVF_H)); s.i(G.movzw(28, LCD_W43)); s.i(G.movw(6, 9)); s.i(G.movw(30, 7)); s.i(G.movw(29, 27)); s.i(G.movzw(14, 6))
    s.i(lambda a: G.b_(a, GEOM_TAIL))
    return s.build()


GEOM_TEXT = ['mov w8, #0x48', 'stp wzr, wzr, [sp, #0x20]', 'mov w9, #0x360', 'stp wzr, wzr, [sp, #0xc]', 'mov w7, #0x470',
             'str wzr, [sp, #8]', 'str w8, [sp, #0x14]', 'mov w8, #8', 'mov w16, wzr', 'mov w10, wzr', 'mov w12, wzr',
             'stp w8, wzr, [sp, #0x18]', 'mov w3, wzr', 'mov w5, wzr', 'mov w18, wzr', 'mov w2, wzr', 'mov w25, wzr',
             'mov w24, #0x72c', 'mov w26, #0xac4', 'mov w17, #2', 'mov w15, #4', 'mov w8, #0x510', 'mov w4, #0x728', 'mov w1, #0xabc',
             'mov w27, #0x354', 'mov w28, #0x480', 'mov w6, w9', 'mov w30, w7', 'mov w29, w27', 'mov w14, #6', f'b #{GEOM_TAIL:#x}']
# the stock 1:1 case the cave is modelled on (checked in compose)
GEOM_11_TEXT = ['mov w8, #0xd8', 'stp wzr, wzr, [sp, #0x20]', 'mov w9, #0x360', 'stp wzr, wzr, [sp, #0xc]', 'mov w7, #0x354',
                'str wzr, [sp, #8]', 'str w8, [sp, #0x14]', 'mov w8, #6', 'mov w16, wzr', 'mov w10, wzr', 'mov w12, wzr',
                'stp w8, wzr, [sp, #0x18]', 'mov w3, wzr', 'mov w5, wzr', 'mov w18, wzr', 'mov w2, wzr', 'mov w25, wzr',
                'mov w24, #0x72c', 'mov w26, #0xac4', 'mov w17, #2', 'mov w15, #4', 'mov w8, #0x510', 'mov w4, #0x728', 'mov w1, #0xabc',
                'mov w27, w7', 'mov w28, w9', 'mov w6, w9', 'mov w30, w7', 'mov w29, w7', 'mov w14, #6', f'b #{GEOM_TAIL:#x}']


def strx(t, n, imm): return 0xF9000000 | (imm >> 3) << 10 | n << 5 | t
def ldrsh(t, n, imm): return 0x79C00000 | (imm >> 1) << 10 | n << 5 | t
def addx_lsl(d, n, m, s): return 0x8B000000 | m << 16 | s << 10 | n << 5 | d


def cave_max():
    s = G.Asm(CAVE_MAX)
    s.i(G.movzw(8, MAX_43[0])); s.i(G.movzw(9, MAX_43[1])); s.i(lambda a: G.b_(a, MAX_STORE))
    return s.build()


MAX_TEXT = [f'mov w8, #{MAX_43[0]:#x}', f'mov w9, #{MAX_43[1]:#x}', f'b #{MAX_STORE:#x}']


def cave_corner2(dl, dr):
    s = G.Asm(CAVE_CORNER2); L = lambda n: (lambda: s.labels[n])
    s.i(G.stp_pre(29, 30, -0x40)); s.i(G.stp(19, 20, 0x10)); s.i(G.stp(21, 22, 0x20))
    s.i(G.movx(19, 0)); s.i(G.movx(20, 1))
    s.i(G.ldrx(9, 20, 0)); s.i(strx(9, 31, 0x30)); s.i(G.addxi(1, 31, 0x30))
    s.i(lambda a: G.b_(a, G.CORNER_FN, True)); s.i(G.movw(21, 0))
    s.i(lambda a: G.cbz(a, L('store')(), 21))
    s.i(G.ldrb(9, 19, 8)); s.i(lambda a: G.cbz(a, L('store')(), 9, nz=True))
    s.i(G.ldrw(9, 19, 0)); s.i(G.cmpw(9, 2)); s.i(lambda a: G.bcond(a, L('store')(), HI))
    s.i(G.movx(0, 19)); s.i(lambda a: G.b_(a, G.IDX_FN, True)); s.i(lambda a: G.cbz(a, L('store')(), 0, nz=True))
    s.i(G.movzw(0, PROP_AREA)); s.i(lambda a: G.b_(a, GETPROP, True)); s.i(G.cmpw(0, 2)); s.i(lambda a: G.bcond(a, L('store')(), NE))
    s.i(G.movzw(0, PROP_MOVIE)); s.i(lambda a: G.b_(a, GETPROP, True)); s.i(G.cmpw(0, 1)); s.i(lambda a: G.bcond(a, L('store')(), EQ))
    s.i(G.ldrw(9, 19, 0)); s.i(lambda a: G.adr(a, L('dtab')(), 10)); s.i(addx_lsl(10, 10, 9, 2))
    s.i(ldrsh(11, 10, 0)); s.i(ldrsh(12, 10, 2))
    s.i(G.ldrh(13, 31, 0x30)); s.i(G.addw(13, 13, 11)); s.i(G.strh(13, 31, 0x30))
    s.i(G.ldrh(13, 31, 0x34)); s.i(G.addw(13, 13, 12)); s.i(G.strh(13, 31, 0x34))
    s.label('store'); s.i(G.ldrx(9, 31, 0x30)); s.i(strx(9, 20, 0)); s.i(G.movw(0, 21))
    s.i(G.ldp(21, 22, 0x20)); s.i(G.ldp(19, 20, 0x10)); s.i(G.ldp_post(29, 30, 0x40)); s.i(G.RET)
    s.label('dtab'); s.half(*sum(([a, b] for a, b in zip(dl, dr)), []), 0, 0)
    return s.build(), s.labels


CORNER2_TEXT = [
    'stp x29, x30, [sp, #-0x40]!', 'stp x19, x20, [sp, #0x10]', 'stp x21, x22, [sp, #0x20]', 'mov x19, x0', 'mov x20, x1',
    'ldr x9, [x20]', 'str x9, [sp, #0x30]', 'add x1, sp, #0x30', f'bl #{G.CORNER_FN:#x}', 'mov w21, w0', 'cbz w21, #{store}',
    'ldrb w9, [x19, #8]', 'cbnz w9, #{store}', 'ldr w9, [x19]', 'cmp w9, #2', 'b.hi #{store}', 'mov x0, x19', f'bl #{G.IDX_FN:#x}',
    'cbnz w0, #{store}', f'mov w0, #{PROP_AREA:#x}', f'bl #{GETPROP:#x}', 'cmp w0, #2', 'b.ne #{store}', f'mov w0, #{PROP_MOVIE:#x}',
    f'bl #{GETPROP:#x}', 'cmp w0, #1', 'b.eq #{store}', 'ldr w9, [x19]', 'adr x10, #{dtab}', 'add x10, x10, x9, lsl #2',
    'ldrsh w11, [x10]', 'ldrsh w12, [x10, #2]', 'ldrh w13, [sp, #0x30]', 'add w13, w13, w11', 'strh w13, [sp, #0x30]',
    'ldrh w13, [sp, #0x34]', 'add w13, w13, w12', 'strh w13, [sp, #0x34]', 'ldr x9, [sp, #0x30]', 'str x9, [x20]', 'mov w0, w21',
    'ldp x21, x22, [sp, #0x20]', 'ldp x19, x20, [sp, #0x10]', 'ldp x29, x30, [sp], #0x40', 'ret ']


def cave_points2(D):
    """A2g's cave_points43 with the area criterion read from the GUI properties instead of the AF state."""
    s = G.Asm(G.CAVE_POINTS); L = lambda n: (lambda: s.labels[n])
    s.i(G.stp_pre(29, 30, -48)); s.i(G.stp(19, 20, 16)); s.i(G.stp(21, 22, 32))
    s.i(G.movx(19, 1)); s.i(G.movx(20, 3)); s.i(G.movw(21, 2))
    s.i(lambda a: G.b_(a, G.POINTS_FN, True)); s.i(G.movw(22, 0))
    s.i(G.movzw(0, PROP_AREA)); s.i(lambda a: G.b_(a, GETPROP, True)); s.i(G.cmpw(0, 2)); s.i(lambda a: G.bcond(a, L('done')(), NE))
    s.i(G.movzw(0, PROP_MOVIE)); s.i(lambda a: G.b_(a, GETPROP, True)); s.i(G.cmpw(0, 1)); s.i(lambda a: G.bcond(a, L('done')(), EQ))
    s.i(G.ldrb(9, 19, 8)); s.i(lambda a: G.cbz(a, L('done')(), 9, nz=True))
    s.i(G.ldrw(9, 19, 0)); s.i(G.cmpw(9, 2)); s.i(lambda a: G.bcond(a, L('done')(), HI))
    s.i(G.movx(0, 19)); s.i(lambda a: G.b_(a, G.IDX_FN, True)); s.i(lambda a: G.cbz(a, L('done')(), 0, nz=True))
    s.i(G.ldrw(9, 19, 0)); s.i(lambda a: G.adr(a, L('dtab')(), 10)); s.i(G.ldrsh_lsl1(10, 10, 9))
    s.i(lambda a: G.cbz(a, L('done')(), 21)); s.i(G.movw(11, 21)); s.i(G.movx(12, 20))
    s.label('loop')
    s.i(G.ldrh(13, 12, 0)); s.i(G.addw(13, 13, 10)); s.i(G.strh(13, 12, 0))
    s.i(G.ldrh(13, 12, 4)); s.i(G.addw(13, 13, 10)); s.i(G.strh(13, 12, 4))
    s.i(G.addxi(12, 12, 8)); s.i(G.subsw_i(11, 11, 1)); s.i(lambda a: G.bcond(a, L('loop')(), NE))
    s.label('done'); s.i(G.movw(0, 22)); s.i(G.ldp(21, 22, 32)); s.i(G.ldp(19, 20, 16)); s.i(G.ldp_post(29, 30, 48)); s.i(G.RET)
    s.label('dtab'); s.half(*D, 0)
    return s.build(), s.labels


POINTS2_TEXT = [
    'stp x29, x30, [sp, #-0x30]!', 'stp x19, x20, [sp, #0x10]', 'stp x21, x22, [sp, #0x20]', 'mov x19, x1', 'mov x20, x3',
    'mov w21, w2', f'bl #{G.POINTS_FN:#x}', 'mov w22, w0', f'mov w0, #{PROP_AREA:#x}', f'bl #{GETPROP:#x}', 'cmp w0, #2',
    'b.ne #{done}', f'mov w0, #{PROP_MOVIE:#x}', f'bl #{GETPROP:#x}', 'cmp w0, #1', 'b.eq #{done}', 'ldrb w9, [x19, #8]',
    'cbnz w9, #{done}', 'ldr w9, [x19]', 'cmp w9, #2', 'b.hi #{done}', 'mov x0, x19', f'bl #{G.IDX_FN:#x}', 'cbnz w0, #{done}',
    'ldr w9, [x19]', 'adr x10, #{dtab}', 'ldrsh w10, [x10, x9, lsl #1]', 'cbz w21, #{done}', 'mov w11, w21', 'mov x12, x20',
    'ldrh w13, [x12]', 'add w13, w13, w10', 'strh w13, [x12]', 'ldrh w13, [x12, #4]', 'add w13, w13, w10', 'strh w13, [x12, #4]',
    'add x12, x12, #8', 'subs w11, w11, #1', 'b.ne #{loop}', 'mov w0, w22', 'ldp x21, x22, [sp, #0x20]', 'ldp x19, x20, [sp, #0x10]',
    'ldp x29, x30, [sp], #0x30', 'ret ']


def drop(img, prefix):
    """Remove an A2g edit (restore the stock bytes) so that A2h can redo that range; returns the removed edit."""
    hit = [e for e in img.edits if e['purpose'].startswith(prefix)]
    assert len(hit) == 1, (prefix, len(hit))
    e = hit[0]; img.new[e['offset']:e['end']] = e['old']; img.edits.remove(e)
    return dict(offset=hex(e['offset']), bytes=e['end'] - e['offset'], purpose=e['purpose'], a2g_sha256=sha(e['new']))


def fmt(tl, lab):
    out = []
    for x in tl:
        for k, v in lab.items(): x = x.replace('{' + k + '}', f'{v:#x}')
        out.append(x)
    return out


def compose(eg):
    img, det = G.compose(eg)
    dropped = [drop(img, 'cave_corner43:'), drop(img, 'GUI corner box trampoline'), drop(img, 'cave_points43:')]
    # 1 custom wide-area maximum
    jt = struct.unpack_from('<9Q', eg, hb1.data_off(MAX_JT))
    assert jt[2] == MAX_RET and eg[MAX_RET - BASE:MAX_RET - BASE + 4] == struct.pack('<I', G.RET)
    assert G.text(eg[MAX_STORE - BASE:MAX_STORE - BASE + 12], MAX_STORE) == ['strh w8, [x1]', 'strh w9, [x1, #2]', 'ret ']
    mc = cave_max(); assert G.text(mc, CAVE_MAX) == MAX_TEXT, G.text(mc, CAVE_MAX)
    img.put(CAVE_MAX, mc, f'cave_max43: custom wide-area maximum for area 2 = {MAX_43[0]}x{MAX_43[1]} (largest size with a 4:3 grid record)',
            expect_zero=True)
    img.put(BASE + hb1.data_off(MAX_JT + 2 * 8), struct.pack('<Q', CAVE_MAX),
            f'custom wide-area maximum jump table A02A27FA0 slot 2: {MAX_RET:#x} (no write -> 1x1) -> cave_max43',
            expect=struct.pack('<Q', MAX_RET))
    # 2 corner box
    D = det['af_display']['D_by_layout']; assert D == [-58, -72, -58]
    dl = [d + K43 * c for d, c in zip(D, CELL)]; dr = [d - K43 * c for d, c in zip(D, CELL)]
    assert (dl, dr) == ([6, 8, 6], [-122, -152, -122]), (dl, dr)
    cc, cl = cave_corner2(dl, dr)
    assert G.text(cc[:cl['dtab'] - CAVE_CORNER2], CAVE_CORNER2) == fmt(CORNER2_TEXT, cl), G.text(cc, CAVE_CORNER2)
    assert CAVE_MAX + len(mc) <= CAVE_CORNER2 and CAVE_CORNER2 + len(cc) <= G.CAVE_END
    img.put(CAVE_CORNER2, cc, f'cave_corner43v2: 41186FE4 into a stack temporary; x0 + {dl}, x1 + {dr} (layouts 0..2) when 0x219E == 2, '
            f'0x218C != 1, idx 0, +8 = 0; one 64-bit store to the output', expect_zero=True)
    img.put(G.CORNER_HOOK, struct.pack('<I', G.b_(G.CORNER_HOOK, CAVE_CORNER2)), 'GUI corner box trampoline: b 41186FE4 -> b cave_corner43v2',
            expect=struct.pack('<I', G.b_(G.CORNER_HOOK, G.CORNER_FN)))
    # 3 lit points
    pc, pl = cave_points2(D)
    assert G.text(pc[:pl['dtab'] - G.CAVE_POINTS], G.CAVE_POINTS) == fmt(POINTS2_TEXT, pl), G.text(pc, G.CAVE_POINTS)
    assert G.CAVE_POINTS + len(pc) <= G.CAVE_PNG
    img.put(G.CAVE_POINTS, pc, f'cave_points43v2: 41186ABC, then x0/x1 of each rect + D{D} when 0x219E == 2, 0x218C != 1, idx 0, '
            f'+8 = 0, layout <= 2', expect_zero=True)
    # 4 live-view geometry descriptor
    gj = struct.unpack_from('<9Q', eg, hb1.data_off(GEOM_JT))
    assert gj[2] == gj[3] == gj[6] == gj[7] == GEOM_DEFAULT and gj[8] == GEOM_11, [hex(x) for x in gj]
    assert G.text(eg[GEOM_11 - BASE:GEOM_11 - BASE + 4 * len(GEOM_11_TEXT)], GEOM_11) == GEOM_11_TEXT
    gc = cave_geom(); assert G.text(gc, CAVE_GEOM) == GEOM_TEXT, G.text(gc, CAVE_GEOM)
    assert CAVE_CORNER2 + len(cc) <= CAVE_GEOM and CAVE_GEOM + len(gc) <= G.CAVE_END
    img.put(CAVE_GEOM, gc, f'cave_geom43: 41065194 type-1 case for area 2 = stock 1:1 case with 4:3 display values (EVF {EVF_W43}x{EVF_H}, '
            f'LCD {LCD_W43}x{LCD_H}, side pad {PAD43}); sensor fields as FX', expect_zero=True)
    img.put(BASE + hb1.data_off(GEOM_JT + 2 * 8), struct.pack('<Q', CAVE_GEOM),
            f'live-view geometry jump table A02A977B8 slot 2: {GEOM_DEFAULT:#x} (all-zero descriptor) -> cave_geom43',
            expect=struct.pack('<Q', GEOM_DEFAULT))
    det['a10_af'] = dict(geometry=dict(cave=hex(CAVE_GEOM), words=gc.hex(), jump_table_slot2=hex(GEOM_JT + 16),
                                       evf=[EVF_W43, EVF_H], lcd=[LCD_W43, LCD_H], pad=PAD43, status='candidate, not proven on the body'))
    det['a10_display'] = dict(dropped_a2g_edits=dropped, custom_max=dict(cave=hex(CAVE_MAX), max=MAX_43, words=mc.hex(),
                                                                        jump_table_slot2=hex(MAX_JT + 16)),
                              corner=dict(cave=hex(CAVE_CORNER2), bytes=len(cc), sha256=sha(cc), delta_left=dl, delta_right=dr, k=K43, cell=CELL),
                              points=dict(cave=hex(G.CAVE_POINTS), bytes=len(pc), sha256=sha(pc), D=D),
                              properties=dict(getter=hex(GETPROP), area=hex(PROP_AREA), movie=hex(PROP_MOVIE)))
    return img, det
