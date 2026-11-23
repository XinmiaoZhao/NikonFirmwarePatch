"""Release mode per photo shooting menu bank: S, CL, CH, C15, C30, C60, C120 and self-timer follow the bank.

Stock C3.11 keeps the release mode (DS 06000108h: 0 S, 1 continuous, 4 self-timer; DS 0600010Ah: 0 CL, 1 CH, 3 C30,
4 C120, 5 C60, 6 C15) outside the menu banks: its settings group (group 1) has no bank storage, so it cannot simply be
added to the bank list 0xA0299E888.  With Extended menu banks (0200054Bh) On, this module stores the release mode of
each bank in five spare saved bytes and restores it when the bank is selected.  Extended menu banks Off: stock
behaviour, and the release mode returns to its own "global" value, as the stock extended items (exposure mode, shutter
speed, aperture) do.  No strings, no menu rows; about 1 KiB of code in the last 2 KiB of the pre-capture cave.

Storage: padding of settings group 1Eh (storage 0xA03D70A14, saved with the group, not banked, defaults 0):
A..C at 0xA03D732B1..B3 (after the u8 setting 1E53h), D at 0xA03D732B9 and the global value at 0xA03D732BA (after the
u8 setting 1E55h).  Byte = 0x80 | mode << 4 | kind; 0 = never stored (the release mode is left as it is).

Four one-word hooks (each checked against the stock word):
  H1  410DD4D8  bl 41012CF0 in the photo-bank rule 410DD1EC (both callers: the rule dispatcher stub 410E958C and
                410DF7F8).  The batch get reads {06000108h, 0600010Ah, 06000109h} for the rule's own C-mode check
                (C15..C120 -> 07000685h and 0700050Eh to their defaults).  The hook saves the live release mode into
                the bank being left, queues the new bank's release mode into the rule's change list (x19) with the
                stock dependents (410E3408 = the 06000108h rule, 410EA108 = the 0600010Ah rule), and returns the new
                values to the C-mode check, so a C30 bank -> S bank switch does not reset the S bank's settings.
                Registers at the site: x19 = change list, w21 = old bank + 1, w24 = new bank + 1.
  H2  410E95A8  b 410DD84C, the Extended menu banks rule (its only caller): after the stock rule, Off -> On saves the
                live release mode as the global value and restores the bank's; On -> Off the reverse.
  H3  410D71E0  bl 410DDA64, Manage menu banks -> Copy (its only caller): the source bank's byte is copied to the target
                (after saving the live release mode first when the source is the selected bank).
  H3b 410DDE5C  bl 41012CF0 in the copy function's C-mode check, reached only when the target is the selected bank:
                restores the copied release mode into the copy's change list (x21 = 0xA0480B15C).

The settings engine runs rules one level deep (dispatcher 410EA70C: queue the request, call its rule; dependents are
applied without their own rules), so the hook queues each change together with the stock rule's dependents, exactly
as a release-mode request would.  Only changed values are queued; the kind is restored only for a continuous mode.
"""
import struct

from z8prores.a64 import Block
from z8prores.package import require

BASE = 0x40160000
CODE_AT = 0x409FF800                    # last 2 KiB of the pre-capture cave; the pre-capture and RAW menu units lie below
CODE_END = 0x40A00000

DS_GET = 0x41012C84                     # (id, file, line) -> value
BATCH_GET = 0x41012CF0                  # (ids, out, count, file, line)
PENDING = 0x410E9418                    # (id, list) -> queued value, else the stored value
QUEUE = 0x410E9318                      # (id, value, list): append to the change list
RULE_MODE = 0x410E3408                  # 06000108h rule body (value, list): value != 4 -> queue 06000109h = 0
RULE_KIND = 0x410EA108                  # 0600010Ah rule (id, value, list): C-mode resets, kind 2 case, 3902h mirror
BANK_RULE, EXT_RULE, COPY_BANK = 0x410DD1EC, 0x410DD84C, 0x410DDA64

ID_MODE, ID_KIND = 0x06000108, 0x0600010A
ID_BANK, ID_EXT = 0x02000546, 0x0200054B
FILE, LINE = 0x4417945A, 0xB00          # "SettingDataService_MenuBank.c" (the getter's log argument)
SLOT_AC, SLOT_D_GAP = 0xA03D732B1, 5     # slot k at SLOT_AC + k, + 5 from k = 3 (0xA03D732B9, 0xA03D732BA)
GLOBAL = 4
MODES = (0, 1, 4)                       # S, continuous, self-timer
KIND_MAX = 6

SITES = {                               # VA: (stock target, link, entry label, purpose)
    0x410DD4D8: (BATCH_GET, True, 'rb_switch', 'bank select: save the left bank\'s release mode, restore the new bank\'s'),
    0x410E95A8: (EXT_RULE, False, 'rb_extended', 'Extended menu banks On/Off: global release mode'),
    0x410D71E0: (COPY_BANK, True, 'rb_copy', 'Copy bank: the release mode is copied with the bank'),
    0x410DDE5C: (BATCH_GET, True, 'rb_copy_select', 'Copy bank into the selected bank: restore the copied release mode'),
}


def _branch(at, to, link):
    delta = to - at
    require(delta % 4 == 0 and -(1 << 27) <= delta < (1 << 27), 'release-mode banks: branch out of range')
    return struct.pack('<I', (0x94000000 if link else 0x14000000) | ((delta // 4) & 0x3FFFFFF))


# Forms the shared encoder lacks.
def _sub_wi(b, rd, rn, imm):
    b.raw(0x51000000 | (imm & 0xFFF) << 10 | rn << 5 | rd)


def _ubfx_w(b, rd, rn, lsb, width):
    b.raw(0x53000000 | lsb << 16 | (lsb + width - 1) << 10 | rn << 5 | rd)


def _orr_w(b, rd, rn, rm, lsl=0):
    b.raw(0x2A000000 | rm << 16 | lsl << 10 | rn << 5 | rd)


def _mov_w32(b, rd, value):
    b.mov_w(rd, value & 0xFFFF)
    if value >> 16:
        b.movk_w16(rd, value >> 16)


ZR = 31


def _prologue(b, pairs):
    """stp x29,x30,[sp,#-16*(1+pairs)]!; mov x29,sp; stp x19.. pairs"""
    size = 16 * (1 + pairs)
    b.stp_pre(29, 30, -size)
    b.add_xi(29, 31, 0)
    for i in range(pairs):
        b.stp(19 + 2 * i, 20 + 2 * i, 16 * (i + 1))
    return size


def _epilogue(b, pairs, size):
    for i in reversed(range(pairs)):
        b.ldp(19 + 2 * i, 20 + 2 * i, 16 * (i + 1))
    b.ldp_post(29, 30, size)
    b.ret()


def code():
    """(bytes, entry labels) of the module at CODE_AT."""
    b = Block(CODE_AT)

    # ---- rb_switch (H1): x0..x4 = the stock batch-get arguments; x19 list, w21 old + 1, w24 new + 1 (caller's) ----
    b.label('rb_switch')
    size = _prologue(b, 3)
    b.mov_x(20, 19)                     # list
    _sub_wi(b, 22, 21, 1)               # old bank
    _sub_wi(b, 23, 24, 1)               # new bank
    b.mov_x(21, 1)                      # out[] (mode, kind, flag 06000109h)
    b.bl(BATCH_GET)
    b.mov_wr(19, 0)
    b.bl('rb_ext_on')
    b.cbz_w(0, 'sw_out')
    b.mov_wr(0, 22)
    b.mov_x(1, 20)
    b.bl('rb_save')
    b.cmp_w(23, 22)
    b.b_cond('eq', 'sw_out')
    b.mov_wr(0, 23)
    b.mov_x(1, 20)
    b.mov_x(2, 21)
    b.bl('rb_apply')
    b.label('sw_out')
    b.mov_wr(0, 19)
    _epilogue(b, 3, size)

    # ---- rb_extended (H2): w0 = new Extended value, w1 = flag, x2 = list; returns the stock rule's result ----
    b.label('rb_extended')
    size = _prologue(b, 3)
    b.mov_wr(19, 0)
    b.mov_wr(24, 1)
    b.mov_x(20, 2)
    _mov_w32(b, 0, ID_EXT)
    b.mov_x(1, ZR)
    b.bl('rb_get')
    b.mov_wr(21, 0)                     # old Extended value
    _mov_w32(b, 0, ID_BANK)
    b.mov_x(1, ZR)
    b.bl('rb_get')
    b.mov_wr(22, 0)                     # selected bank
    b.mov_wr(0, 19)
    b.mov_wr(1, 24)
    b.mov_x(2, 20)
    b.bl(EXT_RULE)
    b.mov_wr(23, 0)
    b.tbz_w(23, 0, 'ext_out')
    b.cmp_wi(22, 3)
    b.b_cond('hi', 'ext_out')
    b.cmp_wi(19, 1)
    b.b_cond('ne', 'ext_off')
    b.cbnz_w(21, 'ext_out')             # Off -> On: global <- live, live <- bank
    b.mov_w(0, GLOBAL)
    b.mov_x(1, 20)
    b.bl('rb_save')
    b.mov_wr(0, 22)
    b.b('ext_apply')
    b.label('ext_off')
    b.cbnz_w(19, 'ext_out')
    b.cmp_wi(21, 1)                     # On -> Off: bank <- live, live <- global
    b.b_cond('ne', 'ext_out')
    b.mov_wr(0, 22)
    b.mov_x(1, 20)
    b.bl('rb_save')
    b.mov_w(0, GLOBAL)
    b.label('ext_apply')
    b.mov_x(1, 20)
    b.mov_x(2, ZR)
    b.bl('rb_apply')
    b.label('ext_out')
    b.mov_wr(0, 23)
    _epilogue(b, 3, size)

    # ---- rb_copy (H3): w0 = source bank, w1 = target bank; returns the stock copy's result ----
    b.label('rb_copy')
    size = _prologue(b, 2)
    b.mov_wr(19, 0)
    b.mov_wr(20, 1)
    b.cmp_wi(19, 3)
    b.b_cond('hi', 'copy_call')
    b.cmp_wi(20, 3)
    b.b_cond('hi', 'copy_call')
    b.cmp_w(19, 20)
    b.b_cond('eq', 'copy_call')
    b.bl('rb_ext_on')
    b.cbz_w(0, 'copy_call')
    _mov_w32(b, 0, ID_BANK)
    b.mov_x(1, ZR)
    b.bl('rb_get')
    b.cmp_w(0, 19)
    b.b_cond('ne', 'copy_slot')
    b.mov_wr(0, 19)                     # the source is the selected bank: store its live release mode first
    b.mov_x(1, ZR)
    b.bl('rb_save')
    b.label('copy_slot')
    b.mov_wr(0, 19)
    b.bl('rb_slot')
    b.ldrb_w(21, 9)
    b.mov_wr(0, 20)
    b.bl('rb_slot')
    b.strb_w(21, 9)
    b.label('copy_call')
    b.mov_wr(0, 19)
    b.mov_wr(1, 20)
    b.bl(COPY_BANK)
    _epilogue(b, 2, size)

    # ---- rb_copy_select (H3b): x0..x4 = batch-get arguments; x21 = the copy's change list (caller's) ----
    b.label('rb_copy_select')
    size = _prologue(b, 2)
    b.mov_x(20, 21)
    b.mov_x(22, 1)
    b.bl(BATCH_GET)
    b.mov_wr(19, 0)
    b.bl('rb_ext_on')
    b.cbz_w(0, 'cs_out')
    _mov_w32(b, 0, ID_BANK)
    b.mov_x(1, ZR)
    b.bl('rb_get')
    b.mov_x(1, 20)
    b.mov_x(2, 22)
    b.bl('rb_apply')
    b.label('cs_out')
    b.mov_wr(0, 19)
    _epilogue(b, 2, size)

    # ---- rb_save(w0 = slot 0..4, x1 = list or 0): slot <- current release mode (0 if not storable) ----
    b.label('rb_save')
    size = _prologue(b, 2)
    b.mov_wr(19, 0)
    b.mov_x(20, 1)
    b.cmp_wi(19, GLOBAL)
    b.b_cond('hi', 'save_out')
    _mov_w32(b, 0, ID_KIND)
    b.mov_x(1, 20)
    b.bl('rb_get')
    b.mov_wr(21, 0)
    _mov_w32(b, 0, ID_MODE)
    b.mov_x(1, 20)
    b.bl('rb_get')
    b.mov_wr(22, 0)
    b.mov_w(10, 0)
    b.cmp_wi(21, KIND_MAX)
    b.b_cond('hi', 'save_store')
    b.cmp_wi(22, 1)
    b.b_cond('ls', 'save_ok')
    b.cmp_wi(22, 4)
    b.b_cond('ne', 'save_store')
    b.label('save_ok')
    b.mov_w(10, 0x80)
    _orr_w(b, 10, 10, 21)
    _orr_w(b, 10, 10, 22, 4)
    b.label('save_store')
    b.mov_wr(0, 19)
    b.bl('rb_slot')                     # x9 only
    b.strb_w(10, 9)
    b.label('save_out')
    _epilogue(b, 2, size)

    # ---- rb_apply(w0 = slot 0..4, x1 = list, x2 = out[] or 0): queue the slot's release mode where it differs ----
    b.label('rb_apply')
    size = _prologue(b, 3)
    b.mov_x(20, 1)
    b.mov_x(23, 2)
    b.cmp_wi(0, GLOBAL)
    b.b_cond('hi', 'apply_out')
    b.bl('rb_slot')
    b.ldrb_w(19, 9)
    b.tbz_w(19, 7, 'apply_out')
    _ubfx_w(b, 21, 19, 4, 3)            # mode
    _ubfx_w(b, 22, 19, 0, 4)            # kind
    b.cmp_wi(22, KIND_MAX)
    b.b_cond('hi', 'apply_out')
    b.cmp_wi(21, 1)
    b.b_cond('ls', 'apply_valid')
    b.cmp_wi(21, 4)
    b.b_cond('ne', 'apply_out')
    b.label('apply_valid')
    _mov_w32(b, 0, ID_MODE)
    b.mov_x(1, 20)
    b.bl('rb_get')
    b.cmp_w(0, 21)
    b.b_cond('eq', 'apply_kind')
    _mov_w32(b, 0, ID_MODE)             # mode changes: queue it with the 06000108h rule's dependent
    b.mov_wr(1, 21)
    b.mov_x(2, 20)
    b.bl(QUEUE)
    b.mov_wr(0, 21)
    b.mov_x(1, 20)
    b.bl(RULE_MODE)
    b.cbz_x(23, 'apply_kind')
    b.str_w(21, 23, 0)                  # out[0] = mode
    b.cmp_wi(21, 4)
    b.b_cond('eq', 'apply_kind')
    b.str_w(ZR, 23, 8)                  # out[2] = 0: the rule cleared 06000109h
    b.label('apply_kind')
    b.cmp_wi(21, 1)                     # the kind only matters in continuous mode
    b.b_cond('ne', 'apply_out')
    _mov_w32(b, 0, ID_KIND)
    b.mov_x(1, 20)
    b.bl('rb_get')
    b.cmp_w(0, 22)
    b.b_cond('eq', 'apply_out')
    _mov_w32(b, 0, ID_KIND)             # kind changes: queue it with the 0600010Ah rule's dependents
    b.mov_wr(1, 22)
    b.mov_x(2, 20)
    b.bl(QUEUE)
    _mov_w32(b, 0, ID_KIND)
    b.mov_wr(1, 22)
    b.mov_x(2, 20)
    b.bl(RULE_KIND)
    b.cbz_x(23, 'apply_out')
    b.str_w(22, 23, 4)                  # out[1] = kind
    b.label('apply_out')
    _epilogue(b, 3, size)

    # ---- rb_ext_on: w0 = 1 when Extended menu banks is On, else 0 ----
    b.label('rb_ext_on')
    b.stp_pre(29, 30, -16)
    _mov_w32(b, 0, ID_EXT)
    b.mov_x(1, ZR)
    b.bl('rb_get')
    b.cmp_wi(0, 1)
    b.raw(0x1A9F17E0)                   # cset w0, eq
    b.ldp_post(29, 30, 16)
    b.ret()

    # ---- rb_get(w0 = id, x1 = list or 0): queued value from the list, else the stored value (tail calls) ----
    b.label('rb_get')
    b.cbz_x(1, 'get_stored')
    b.b(PENDING)
    b.label('get_stored')
    b.mov_x64(1, FILE)
    b.mov_w(2, LINE)
    b.b(DS_GET)

    # ---- rb_slot(w0 = slot 0..4): x9 = its address; leaf, changes x9 and the flags only ----
    b.label('rb_slot')
    b.mov_x64(9, SLOT_AC)
    b.cmp_wi(0, 3)
    b.b_cond('lo', 'slot_add')
    b.add_xi(9, 9, SLOT_D_GAP)
    b.label('slot_add')
    b.add_x(9, 9, 0)
    b.ret()

    raw = b.bytes()
    require(CODE_AT + len(raw) <= CODE_END, 'release-mode banks: code exceeds the cave')
    return raw, dict(b.labels), b


def edits(eg):
    """Byte edits (offset, old, new, purpose) against the stock C3.11 EG."""
    raw, labels, _ = code()
    out = []

    def add(va, old, new, why):
        o = va - BASE
        require(eg[o:o + len(old)] == old, f'release-mode banks: unexpected stock bytes at {va:#x}')
        out.append(dict(offset=o, old=old, new=new, purpose='release-mode banks: ' + why))

    add(CODE_AT, bytes(len(raw)), raw, 'code')
    for va, (target, link, entry, why) in SITES.items():
        add(va, _branch(va, target, link), _branch(va, labels[entry], link), why)
    return out
