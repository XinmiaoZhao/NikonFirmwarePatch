import struct
from . import display as D
C = D.C
hb1, sha = D.hb1, D.sha
W, text, movz = C.A.W, C.text, C.movz

NOP = 0xD503201F
RECORD_SIZES = [(0x407CD540, 10, 0x100, 0xF0, 'thumbnail height 256 -> 240 (320x240)'),
                (0x407CD554, 9, 0x258, 0x280, 'small preview width 600 -> 640 (640x480)'),
                (0x407CD5F0, 9, 0x546, 0x5A0, 'large preview width 1350 -> 1440 (1440x1080)')]
JUMP_TABLES = {0x440E92F8: (0, 0x407CD53C), 0x440E92C0: (0, 0x407CD554), 0x440E9330: (2, 0x407CD5F0)}   # table: (slot index, target)
DECODE_TABLE, DECODE_ROW2 = 0x440E3A78, [(2304, 1728), (1920, 1440), (1280, 960), (960, 720)]
REJECT_SITE = 0x40795AB8
# box rule 0x40790bac (overview / highlights / RGB pages, open-gate D10 sec. 2): both branch sets handle categories 1, 4, 3
# and give the rest the 3:2 height; category 2 (4:3) gets a height-fixed box like 5:4: w = floor(4H/3) & 0xfff0.
BOX_A_SITE, BOX_B_SITE = 0x40790DF4, 0x40790E3C          # 'cmp w0, #3' of set A / set B -> b cave
CAVE_BOX_A, CAVE_BOX_B = 0x40B7C480, 0x40B7C4C0          # A2 extended the text loader to 0x40B7D000; used up to 0x40B7C463


def b(at, to): d = (to - at) >> 2; assert -(1 << 25) <= d < 1 << 25; return 0x14000000 | d & 0x3FFFFFF
def b_cond(at, to, cond): d = (to - at) >> 2; assert -(1 << 18) <= d < 1 << 18; return 0x54000000 | (d & 0x7FFFF) << 5 | cond
def cmp_w0(imm): return 0x7100001F | imm << 10                    # subs wzr, w0, #imm


def four_thirds(at):
    """w8 = ldrsh [sp,#0x42] (H); w10 = 4H; w9 = (4H * 0x55555556) >> 32 = floor(4H/3) for 0 <= 4H < 2^31; w9 &= 0xfff0."""
    return [0x79C087E8,                  # ldrsh w8, [sp, #0x42]
            0x531E750A,                  # lsl w10, w8, #2
            0x528AAAC9,                  # mov w9, #0x5556
            0x72AAAAA9,                  # movk w9, #0x5555, lsl #16
            0x9B297D49,                  # smull x9, w10, w9
            0xD360FD29,                  # lsr x9, x9, #0x20
            0x121C2D29]                  # and w9, w9, #0xfff0


def box_caves():
    a = CAVE_BOX_A        # set A: cat 3 -> 0x40790dfc; cat 2 -> 4:3 box, w8 = H & 0xffff, [sp+0x66] = w9, b 0x40790eb8; else 0x40790ea0
    ca = [cmp_w0(3), b_cond(a + 4, a + 12, 1), b(a + 8, 0x40790DFC), cmp_w0(2), b_cond(a + 16, a + 24, 0), b(a + 20, 0x40790EA0)]
    ca += four_thirds(a + 24) + [0x12003D08,                       # and w8, w8, #0xffff
                                 0x7900CFE9]                       # strh w9, [sp, #0x66]
    ca.append(b(a + 4 * len(ca), 0x40790EB8))
    c = CAVE_BOX_B        # set B: cat 3 -> 0x40790e44; cat 2 -> 4:3 box, [sp+0x68] = H, [sp+0x66] = w9, b 0x40790fac; else 0x40790f94
    cb = [cmp_w0(3), b_cond(c + 4, c + 12, 1), b(c + 8, 0x40790E44), cmp_w0(2), b_cond(c + 16, c + 24, 0), b(c + 20, 0x40790F94)]
    fb = four_thirds(c + 24); cb += fb[:1] + [0x7900D3E8] + fb[1:] + [0x7900CFE9]   # strh w8, [sp, #0x68] after the load
    cb.append(b(c + 4 * len(cb), 0x40790FAC))
    return ca, cb


def r8(x):
    lo = int(x) // 8 * 8
    return lo if x - lo < lo + 8 - x else lo + 8


def compose(eg):
    img, det = D.compose(eg)
    at = lambda a, n: eg[a - hb1.BASE:a - hb1.BASE + n]
    # the slot-2 targets: stock text, and each is reached only from slot 2 of its table (all 9/7-entry tables listed)
    assert text(at(0x407CD53C, 12), 0x407CD53C) == ['mov w9, #0x140', 'mov w10, #0x100', 'b #0x407cd568']
    assert text(at(0x407CD554, 12), 0x407CD554) == ['mov w9, #0x258', 'mov w10, #0x1e0', 'b #0x407cd568']
    assert text(at(0x407CD5F0, 12), 0x407CD5F0) == ['mov w9, #0x546', 'mov w10, #0x438', 'mov w13, #5']
    for tab, (slot, target) in JUMP_TABLES.items():
        n = 9 if tab == 0x440E9330 else 7
        entries = struct.unpack_from(f'<{n}Q', eg, tab - hb1.BASE)
        assert entries[slot] == target and entries.count(target) == 1, (hex(tab), [hex(e) for e in entries])
    for a, rd, old, new, what in RECORD_SIZES:      # stock words may be ORR-immediate aliases: check the text, keep the bytes
        assert text(at(a, 4), a) == [f'mov w{rd}, #{old:#x}'] and text(W(movz(rd, new)), a) == [f'mov w{rd}, #{new:#x}']
        img.put(a, W(movz(rd, new)), f'playback preview record of area slot 2 (code 3): {what}', expect=at(a, 4))
    # decode-size table row 2 (category 2, 4:3) by the stock rule
    rows = [[struct.unpack_from('<HH', eg, DECODE_TABLE - hb1.BASE + c * 16 + k * 4) for k in range(4)] for c in range(5)]
    for c, (num, den) in ((0, (2, 3)), (1, (9, 16)), (3, (4, 5)), (4, (1, 1))):
        assert rows[c] == [(w, r8(w * num / den)) for w in (2304, 1920, 1280, 960)], (c, rows[c])
    assert rows[2] == [(0, 0)] * 4 and DECODE_ROW2 == [(w, r8(w * 3 / 4)) for w in (2304, 1920, 1280, 960)]
    img.put(DECODE_TABLE + 32, b''.join(struct.pack('<HH', *x) for x in DECODE_ROW2),
            'playback decode-size table 0x440e3a78 row 2 (category 2, 4:3): zero -> 2304x1728, 1920x1440, 1280x960, 960x720',
            expect=bytes(16))
    assert text(at(0x40795AA4, 24), 0x40795AA4) == ['cmp w8, #3', 'b.hi #0x40795b2c', 'cmp w0, #4', 'b.hi #0x40795b2c',
                                                     'cmp w0, #2', 'b.eq #0x40795b2c']
    img.put(REJECT_SITE, W(NOP), '0x40795a9c: category 2 no longer sent to the failure branch (b.eq -> nop)', expect=at(REJECT_SITE, 4))
    # box rule caves
    assert text(at(0x40790DE0, 32), 0x40790DE0) == ['cmp w0, #1', 'tbz w24, #0, #0x40790e30', 'b.eq #0x40790e78', 'cmp w0, #4',
                                                     'b.eq #0x40790e8c', 'cmp w0, #3', 'b.ne #0x40790ea0', 'ldrsh w8, [sp, #0x42]']
    assert text(at(0x40790E30, 24), 0x40790E30) == ['b.eq #0x40790f70', 'cmp w0, #4', 'b.eq #0x40790f80', 'cmp w0, #3',
                                                     'b.ne #0x40790f94', 'ldrsh w8, [sp, #0x42]']
    assert text(at(0x40790E20, 16), 0x40790E20) == ['and w9, w9, #0xfff0', 'and w8, w8, #0xffff', 'strh w9, [sp, #0x66]', 'b #0x40790eb8']
    assert text(at(0x40790E6C, 12), 0x40790E6C) == ['and w9, w9, #0xfff0', 'strh w9, [sp, #0x66]', 'b #0x40790fac']
    ca, cb = box_caves()
    ft = ['ldrsh w8, [sp, #0x42]', 'lsl w10, w8, #2', 'mov w9, #0x5556', 'movk w9, #0x5555, lsl #16', 'smull x9, w10, w9',
          'lsr x9, x9, #0x20', 'and w9, w9, #0xfff0']
    a, c = CAVE_BOX_A, CAVE_BOX_B
    exp_a = ['cmp w0, #3', f'b.ne #{a + 12:#x}', 'b #0x40790dfc', 'cmp w0, #2', f'b.eq #{a + 24:#x}', 'b #0x40790ea0'] + ft + \
            ['and w8, w8, #0xffff', 'strh w9, [sp, #0x66]', 'b #0x40790eb8']
    exp_b = ['cmp w0, #3', f'b.ne #{c + 12:#x}', 'b #0x40790e44', 'cmp w0, #2', f'b.eq #{c + 24:#x}', 'b #0x40790f94'] + ft[:1] + \
            ['strh w8, [sp, #0x68]'] + ft[1:] + ['strh w9, [sp, #0x66]', 'b #0x40790fac']
    assert text(W(*ca), a) == exp_a, text(W(*ca), a)
    assert text(W(*cb), c) == exp_b, text(W(*cb), c)
    assert not any(eg[0x40B7C464 - hb1.BASE:0x40B7C480 - hb1.BASE]) and a + 4 * len(ca) <= c and c + 4 * len(cb) <= 0x40B7D000
    img.put(a, W(*ca), 'box rule set A cave: category 2 (4:3) box w = floor(4H/3) & 0xfff0, h = H (like 5:4)', expect_zero=True)
    img.put(c, W(*cb), 'box rule set B cave: category 2 (4:3) box w = floor(4H/3) & 0xfff0, h = H (like 5:4)', expect_zero=True)
    img.put(BOX_A_SITE, W(b(BOX_A_SITE, a)), '0x40790bac set A: cmp w0,#3 -> b cave (cave keeps 3 / default and adds 2)', expect=at(BOX_A_SITE, 4))
    img.put(BOX_B_SITE, W(b(BOX_B_SITE, c)), '0x40790bac set B: cmp w0,#3 -> b cave (cave keeps 3 / default and adds 2)', expect=at(BOX_B_SITE, 4))
    det['playback'] = dict(box=dict(sites=[hex(BOX_A_SITE), hex(BOX_B_SITE)], caves=[hex(a), hex(c)], cave_a_text=exp_a, cave_b_text=exp_b),
                           record_sizes=[dict(at=hex(a), stock=hex(o), new=hex(n), what=w) for a, _, o, n, w in RECORD_SIZES],
                           jump_tables={hex(t): dict(slot=s, target=hex(g)) for t, (s, g) in JUMP_TABLES.items()},
                           decode_table=hex(DECODE_TABLE), decode_row2=DECODE_ROW2, reject_site=hex(REJECT_SITE))
    return img, det
