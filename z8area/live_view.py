import struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from . import raw_size as B
A = B.A
hb1, sha, W = A.hb1, A.sha, A.W

CAVE_A, CAVE_B = 0x40B7C400, 0x40B7C440
SITE_A, SITE_B = 0x410670E4, 0x410671C0
MASK_SITE = 0x41066ADC
LCD43, EVF43 = (1152, 864), (1136, 852)
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)


def text(code, at):
    return [f'{i.mnemonic} {i.op_str}'.strip() for i in md.disasm(code, at)]


def cmp_w8(imm): return 0x7100011F | imm << 10                     # subs wzr, w8, #imm
def movz(rd, imm): return 0x52800000 | imm << 5 | rd
def b(at, to): d = (to - at) >> 2; assert -(1 << 25) <= d < 1 << 25; return 0x14000000 | d & 0x3FFFFFF
def b_ne(at, to): d = (to - at) >> 2; assert -(1 << 18) <= d < 1 << 18; return 0x54000001 | (d & 0x7FFFF) << 5
RET = 0xD65F03C0


def cave(at, one_to_one, size, store, other):
    """cmp w8,#8; b.ne +8; b one_to_one; cmp w8,#2; b.ne other_slot; mov w8,W; mov w9,H; b store; other."""
    w = [cmp_w8(8), b_ne(at + 4, at + 12), b(at + 8, one_to_one), cmp_w8(2), b_ne(at + 16, at + 32),
         movz(8, size[0]), movz(9, size[1]), b(at + 28, store)]
    w.append(RET if other is None else b(at + 32, other))
    return w


def compose(eg):
    img, det = B.compose(eg)
    # stock instructions at and around the two sites (checked as text, then by bytes in img.put)
    want_a = ['cmp w8, #8', 'b.ne #0x41067080', 'mov w8, #0x360', 'strh w8, [x1]', 'strh w8, [x1, #2]', 'ret']
    assert text(eg[0x410670E0 - hb1.BASE:0x410670F8 - hb1.BASE], 0x410670E0) == want_a
    assert text(eg[0x410670BC - hb1.BASE:0x410670C8 - hb1.BASE], 0x410670BC) == ['strh w8, [x1]', 'strh w9, [x1, #2]', 'ret']
    want_b = ['cmp w8, #8', 'b.ne #0x4106711c', 'mov w8, #0x354', 'strh w8, [x19]', 'strh w8, [x19, #2]', 'b #0x4106711c']
    assert text(eg[0x410671BC - hb1.BASE:0x410671D4 - hb1.BASE], 0x410671BC) == want_b
    assert text(eg[0x4106716C - hb1.BASE:0x41067178 - hb1.BASE], 0x4106716C) == ['strh w8, [x19]', 'strh w9, [x19, #2]', 'b #0x4106711c']
    assert text(eg[0x4106711C - hb1.BASE:0x41067128 - hb1.BASE], 0x4106711C) == ['ldp x19, x30, [sp, #0x30]', 'add sp, sp, #0x40', 'ret']
    ca = cave(CAVE_A, 0x410670E8, LCD43, 0x410670BC, None)
    cb = cave(CAVE_B, 0x410671C4, EVF43, 0x4106716C, 0x4106711C)
    exp_a = ['cmp w8, #8', f'b.ne #{CAVE_A + 12:#x}', 'b #0x410670e8', 'cmp w8, #2', f'b.ne #{CAVE_A + 32:#x}',
             f'mov w8, #{LCD43[0]:#x}', f'mov w9, #{LCD43[1]:#x}', 'b #0x410670bc', 'ret']
    exp_b = ['cmp w8, #8', f'b.ne #{CAVE_B + 12:#x}', 'b #0x410671c4', 'cmp w8, #2', f'b.ne #{CAVE_B + 32:#x}',
             f'mov w8, #{EVF43[0]:#x}', f'mov w9, #{EVF43[1]:#x}', 'b #0x4106716c', 'b #0x4106711c']
    assert text(W(*ca), CAVE_A) == exp_a, text(W(*ca), CAVE_A)
    assert text(W(*cb), CAVE_B) == exp_b, text(W(*cb), CAVE_B)
    blocks_end = max(int(at, 16) + 4 * len(det['block_words'][k]) for k, at in det['blocks'].items())
    assert blocks_end <= CAVE_A and CAVE_B + 4 * len(cb) <= A.DATA_END
    img.put(CAVE_A, W(*ca), 'cave_a: photo LCD live-view size of area 2 = 1152x864 (0x41067078 tail)', expect_zero=True)
    img.put(CAVE_B, W(*cb), 'cave_b: photo EVF live-view size of area 2 = 1136x852 (0x410670f8 tail)', expect_zero=True)
    img.put(SITE_A, W(b(SITE_A, CAVE_A)), '0x41067078: b.ne 0x41067080 (area not 0,1,4,5,8: no size) -> b cave_a',
            expect=W(b_ne(SITE_A, 0x41067080)))
    img.put(SITE_B, W(b(SITE_B, CAVE_B)), '0x410670f8: b.ne 0x4106711c (area not 0,1,4,5,8: no size) -> b cave_b',
            expect=W(b_ne(SITE_B, 0x4106711C)))
    assert text(eg[MASK_SITE - hb1.BASE - 12:MASK_SITE - hb1.BASE + 12], MASK_SITE - 12) == [
        'cmp w8, #8', 'b.hi #0x41066ab0', 'mov w9, #1', 'mov w10, #0x111', 'lsl w8, w9, w8', 'tst w8, w10']
    img.put(MASK_SITE, W(movz(10, 0x115)), '0x41066aa8 photo readout window: area mask 0x111 -> 0x115 (area 2 on the FX readout)',
            expect=W(movz(10, 0x111)))
    det['lv_size'] = dict(readout_mask_site=hex(MASK_SITE), readout_mask=['0x111', '0x115'], cave_a=hex(CAVE_A), cave_b=hex(CAVE_B), site_a=hex(SITE_A), site_b=hex(SITE_B),
                          lcd_43=list(LCD43), evf_43=list(EVF43), cave_a_text=exp_a, cave_b_text=exp_b)
    return img, det
