"""Recall shooting functions (roles 0x3D / 0x58): add C15, C30, C60 and C120 release modes (issue #41 item 2).

Stock C 3.11 stores the RSF release mode in DS 0x06001A92 (u32 at 0xA03D6DC80, unbanked/banked with group 1Ah)
using 0 = Single frame, 1 = Continuous L, 2 = Continuous H, while live continuous sub-modes (DS 0x0600010A and
effective property 0x2126 / G_RELMODE) use 0 = CL, 1 = CH, 3 = C30, 4 = C120, 5 = C60, 6 = C15. Four stock
places block C15..C120 in RSF:
  1. "Save current settings" (0x410D6F20) maps DS 0x0600010A through 0x440F71E0 = [1, 2, 1, 0, 0, 0, 0].
  2. Effective release-mode category 0x2200 (0x40ED4744) vetoes RSF when 0x40000139 (currently in C15..C120)
     is set — which would oscillate if RSF itself switched 0x2126 into 3..6 — and maps 3..6 to legacy DSLR codes.
     The hook skips that veto only for RSF values 3..6; for 0..2 (S / CL / CH) the stock veto stays, so a live
     C15..C120 mode never meets RSF Single with 0x2200 = 0 while 0x2126 is still 3..6.
  3. Effective continuous sub-mode 0x2126 (0x40ED490C) also vetoes on 0x40000139 and only maps 1 -> 0, 2 -> 1;
     the hook passes 3..6 through and keeps the same 0..2-only veto.
  4. The RSF main-page row-11 icon switch (0x405130FC) and the two RSF Release mode sub-pages (State 0x24E page
     0xA028BC620 for body controls, State 0x308 page 0xA028CC390 for lens/grip controls; shared callbacks
     0x40515FBC / 0x40516028 / 0x405178D8) only offer CH, CL and Single frame.

Once 0x2200 = 1 and 0x2126 = 3..6, ContinuousReleaseControl (0x40F958FC, subscribed to 0x2126) updates G_MODE
and configures the Pool 0x39 pre-release ring buffer from d4 (0x02001C11 / 0x02001C12), and raw-precapture's
existing G_RELMODE / G_MODE / HN14 hooks engage automatically for C15/C30 RAW pre-capture.
"""
import struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from z8prores.a64 import Block
from z8prores.package import require

BASE = 0x40160000
DATA_OFF, DATA_VA = 0x4B13000, 0xA02808000
CAVE, LIMIT = 0x409FF200, 0x409FF800

SAVE_TABLE_TAIL = 0x440F71EC
SITE_EFF_MODE = 0x40ED4768
SITE_EFF_KIND = 0x40ED4918
SITE_MAIN_ICON = 0x405131A4
SITE_SUB_ENTRY = 0x40515FD8
SITE_SUB_OK = 0x405178F4

ICON_S, ICON_C15, ICON_C30, ICON_PRE = 0x1656, 0x147E, 0x17E3, 0x160C
STR_C15, STR_C30, STR_C60, STR_C120 = 0x0943, 0x0724, 0x081C, 0x0725

# Rows 0..2 stay [CH (2), CL (1), S (0)] so 0x40516028 (+0x18 / +0x44 dynamic CH/CL FPS icons) is untouched.
# Rows 3..6 append [C15 (6), C30 (3), C60 (5), C120 (4)], reusing each page's Single-frame event table.
# Item IDs index the global grey-state bytes 0xA032CAC8[id - 0x2921] (0x403B1A5C), so each must be unused by stock
# menu rows and stock code and by every other patch in this repository (0x2DE1 is z8heif's HEIF item).
VAL_TO_ROW = (2, 1, 0, 4, 6, 5, 3)
ROW_TO_VAL = (2, 1, 0, 6, 3, 5, 4)

SUBPAGES = (
    ('body_0x24e', 0xA028BC620, 0x43AC9628, 0x43AC96B0, (0x3B97, 0x2DE7, 0x378F, 0x3903)),
    ('lens_0x308', 0xA028CC390, 0x43D74004, 0x43D74088, (0x3995, 0x3B87, 0x3B8D, 0x3B93)),
)
# Item IDs added by other patches in this repository (z8heif JPEG/HEIF items, video-recording quality row 0x315A).
RESERVED_ITEMS = {0x2DDE, 0x2DE1, 0x315A}
EXTRA_SPEC = (
    (6, STR_C15, ICON_C15),
    (3, STR_C30, ICON_C30),
    (5, STR_C60, ICON_PRE),
    (4, STR_C120, ICON_PRE),
)


def _data_off(va):
    return va - DATA_VA + DATA_OFF


def _b(at, to):
    delta = to - at
    require(delta % 4 == 0 and -(1 << 27) <= delta < (1 << 27), 'RSF branch out of range')
    return struct.pack('<I', 0x14000000 | ((delta // 4) & 0x3FFFFFF))


def _assemble(map_val_va, map_row_va):
    b = Block(CAVE)

    # 1. 0x40ED4768 -> eff_mode_hook: w10 = DS 0x06001A92 (<= 6), w8 = w0 (live 0x06000108), w9 = [sp+0x10].
    b.label('eff_mode_hook')
    b.ldr_w(11, 31, 0x30)                       # ldr w11, [sp, #0x30] (DS 0x060017D7)
    b.tbz_w(11, 11, 'eff_mode_out')             # bit 11 = Release mode checkbox
    b.cmp_wi(10, 3)
    b.b_cond('hs', 'eff_mode_set')              # 3..6: no veto (RSF itself makes 0x40000139 true)
    b.ldrb_w(11, 31, 0x28)                      # ldrb w11, [sp, #0x28] (0x40000139: live C15..C120)
    b.tbz_w(11, 0, 'eff_mode_set')
    b.b('eff_mode_out')                         # 0..2 with a live C15..C120: stock veto, w8 = w0
    b.label('eff_mode_set')
    b.cmp_wi(10, 0)
    b.raw(0x1A9F07E8)                           # cset w8, ne (0 -> 0 Single, 1..6 -> 1 Continuous)
    b.label('eff_mode_out')
    b.b(0x40ED47A8)

    # 2. 0x40ED4918 -> eff_kind_hook: w0 = live 0x0600010A, w6 = DS 0x06001A92, w8 = [sp+0x18].
    # w7 bit 0 = 0x40000139 (live C15..C120), the stock veto replaced at the hook site.
    b.label('eff_kind_hook')
    b.ldr_w(9, 31, 0x10)                        # ldr w9, [sp, #0x10] (DS 0x060017D7)
    b.tbz_w(9, 11, 'eff_kind_keep')
    b.raw(0x51000C00 | (6 << 5) | 9)            # sub w9, w6, #3
    b.cmp_wi(9, 4)
    b.b_cond('lo', 'eff_kind_hsfc')             # 3..6: no veto
    b.tbz_w(7, 0, 'eff_kind_stock')
    b.b('eff_kind_keep')                        # 0..2 with a live C15..C120: stock veto
    b.label('eff_kind_stock')
    b.cmp_wi(6, 1)
    b.b_cond('eq', 'eff_kind_cl')               # 1 -> CL (w1 = 0)
    b.cmp_wi(6, 2)
    b.b_cond('eq', 'eff_kind_ch')               # 2 -> CH (w1 = 1)
    b.b('eff_kind_keep')                        # 0 -> keep live w0
    b.label('eff_kind_hsfc')
    b.mov_wr(1, 6)                              # 3..6 -> w1 = 3..6 (C30, C120, C60, C15)
    b.b(0x40ED493C)
    b.label('eff_kind_cl')
    b.b(0x40ED4974)
    b.label('eff_kind_ch')
    b.mov_w(1, 1)
    b.b(0x40ED493C)
    b.label('eff_kind_keep')
    b.b(0x40ED4944)

    # 3. 0x405131A4 -> main_icon_hook: w0 = DS 0x06001A92 (not 1 or 2), sets w21 = 72x36 icon ID.
    b.label('main_icon_hook')
    b.mov_w(21, ICON_S)
    b.cmp_wi(0, 6)
    b.b_cond('eq', 'icon_c15')
    b.cmp_wi(0, 3)
    b.b_cond('eq', 'icon_c30')
    b.cmp_wi(0, 4)
    b.b_cond('eq', 'icon_pre')
    b.cmp_wi(0, 5)
    b.b_cond('ne', 'icon_done')
    b.label('icon_pre')
    b.mov_w(21, ICON_PRE)
    b.b(0x405131B8)
    b.label('icon_c15')
    b.mov_w(21, ICON_C15)
    b.b(0x405131B8)
    b.label('icon_c30')
    b.mov_w(21, ICON_C30)
    b.label('icon_done')
    b.b(0x405131B8)

    # 4. 0x40515FD8 -> sub_entry_hook: x8 = page ptr (preserved), w0 = DS 0x06001A92 -> x9 = row index 0..6.
    b.label('sub_entry_hook')
    b.mov_w(9, 2)
    b.cmp_wi(0, 6)
    b.b_cond('hi', 'sub_entry_done')
    b.adr(10, map_val_va)
    b.raw(0x38604949)                           # ldrb w9, [x10, w0, uxtw]
    b.label('sub_entry_done')
    b.b(0x40515FE8)

    # 5. 0x405178F4 -> sub_ok_hook: w0 = 0x06001A92 (preserved), w9 = row index 0..6 -> w1 = DS value.
    b.label('sub_ok_hook')
    b.mov_w(1, 0)
    b.cmp_wi(9, 6)
    b.b_cond('hi', 'sub_ok_done')
    b.adr(10, map_row_va)
    b.raw(0x38694941)                           # ldrb w1, [x10, w9, uxtw]
    b.label('sub_ok_done')
    b.b(0x403EC39C)

    return b


def _unused_item(eg, item_id):
    """No stock menu row (item ID at row +24) or other aligned u32 in the EG carries this ID."""
    pat, at = struct.pack('<I', item_id), 0
    while (at := eg.find(pat, at)) >= 0:
        if at % 4 == 0:
            return False
        at += 1
    return True


def apply(img, eg):
    require(tuple(ROW_TO_VAL[VAL_TO_ROW[v]] for v in range(7)) == tuple(range(7)), 'RSF row/value bijection')
    added = [i for *_, items in SUBPAGES for i in items]
    require(len(set(added)) == len(added) and all(0x2921 <= i <= 0x4B98 for i in added),
            'RSF item IDs must be distinct and inside the grey-state table')
    require(not set(added) & RESERVED_ITEMS, 'RSF item ID used by another patch')
    require(all(_unused_item(eg, i) for i in added), 'RSF item ID already used by a stock menu row')
    probe = _assemble(CAVE + 0x100, CAVE + 0x108)
    code_len = len(probe.items) * 4
    map_val_va = (CAVE + code_len + 7) & ~7
    map_row_va = map_val_va + 8
    blk = _assemble(map_val_va, map_row_va)
    cs = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    listing = blk.listing(cs)
    code = blk.bytes()
    require(len(code) == code_len, 'RSF code size drift')

    cave = bytearray(map_row_va + 8 - CAVE)
    cave[:code_len] = code
    cave[map_val_va - CAVE:map_val_va - CAVE + 7] = bytes(VAL_TO_ROW)
    cave[map_row_va - CAVE:map_row_va - CAVE + 7] = bytes(ROW_TO_VAL)

    subpage_info = {}
    for name, page_va, stock_rows_va, stock_evs_va, items in SUBPAGES:
        cave.extend(bytes((-len(cave)) % 8))
        rows_va = CAVE + len(cave)
        stock_rows = [list(struct.unpack_from('<11I', eg, stock_rows_va - BASE + 44 * r)) for r in range(3)]
        require([r[0] for r in stock_rows] == [0x416, 0x417, 0x3C0] and stock_rows[2][5] == ICON_S,
                f'Unexpected stock RSF rows for {name}')
        rows = list(stock_rows)
        for (_, label_id, icon_id), item_id in zip(EXTRA_SPEC, items):
            r = list(stock_rows[2])
            r[0], r[5], r[6] = label_id, icon_id, item_id
            rows.append(r)
        for r in rows:
            cave.extend(struct.pack('<11I', *r))

        cave.extend(bytes((-len(cave)) % 8))
        evs_va = CAVE + len(cave)
        stock_ptrs = list(struct.unpack_from('<3Q', eg, stock_evs_va - BASE))
        ptrs = stock_ptrs + [stock_ptrs[2]] * 4
        cave.extend(struct.pack('<7Q', *ptrs))

        page_off = _data_off(page_va)
        img.put(page_off + 0x10, struct.pack('<QQH', rows_va, evs_va, 7),
                f'RSF release-mode subpage {name}: 7 rows and event pointers',
                expect=struct.pack('<QQH', stock_rows_va, stock_evs_va, 3))
        subpage_info[name] = dict(page=hex(page_va), rows=hex(rows_va), events=hex(evs_va), count=7)

    require(CAVE + len(cave) <= LIMIT, 'RSF pre-capture cave exceeds reserved area')
    img.put(CAVE - BASE, bytes(cave), 'RSF pre-capture code, maps and 7-row subpage tables', expect_zero=True)

    # "Save current settings" table tail 0x440F71EC: [0, 0, 0, 0] -> [3, 4, 5, 6] for C30/C120/C60/C15.
    img.put(SAVE_TABLE_TAIL - BASE, struct.pack('<4I', 3, 4, 5, 6),
            'RSF save-current-settings C30/C120/C60/C15 mapping', expect=bytes(16))

    hooks = (
        (SITE_EFF_MODE, 'eff_mode_hook', 'eba34039', 'RSF effective release-mode category (0x2200)'),
        (SITE_EFF_KIND, 'eff_kind_hook', '67010037', 'RSF effective continuous sub-mode (0x2126)'),
        (SITE_MAIN_ICON, 'main_icon_hook', 'd5ca8252', 'RSF main-page release-mode icon'),
        (SITE_SUB_ENTRY, 'sub_entry_hook', 'e9031f32', 'RSF release-mode subpage cursor'),
        (SITE_SUB_OK, 'sub_ok_hook', '0801094b', 'RSF release-mode subpage OK'),
    )
    for site, label, old_hex, why in hooks:
        img.put(site - BASE, _b(site, blk.labels[label]), why, expect=bytes.fromhex(old_hex))

    return dict(
        cave=hex(CAVE),
        cave_bytes=len(cave),
        entries={k: hex(v) for k, v in blk.labels.items()},
        subpages=subpage_info,
        listing=[f'{a:#x}: {w} {t}' for a, w, t in listing],
    )
