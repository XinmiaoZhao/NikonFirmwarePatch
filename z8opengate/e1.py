"""E1: "N-RAW 3:2" as a menu-layer video file type; active N-RAW i-menu tables; 3:2-marked type icons.

All addresses are byte VAs (code VA 40160000 = EG offset 0; init data A02808000 = EG offset 4B13000).  Stock facts
are re-read and checked here, so a changed input stops the build instead of producing a different patch.
"""
import hashlib
import json
import struct
from pathlib import Path
from z8prores.package import require

B, INIT, IOFF = 0x40160000, 0xA02808000, 0x4B13000
OG_STATE = 0xA0FF6F000
FT_CTRL = 0x35CA
NEW_IDS = list(range(0x35C0, 0x35CA))            # ten 3:2 frame-size rows
OG32_STOCK_ROWS = list(range(53, 63))             # stock master/page rows: 8.3K 30/25/24p, 4.1K 120..24p
FT_LABEL = 3232
FT_HELP = 3233                                    # E2: the file-type help (stock 0xA17) with the 3:2 heading
STOCK_HELP = 0xA17
LABEL_IDS = [3137, 3138, 3139] + list(range(3225, 3232))
FT_ROWS, FT_EVENTS = 0x408C3800, 0x408C3A00
FT_PAGE, FT_REFRESH_SLOT = 0xA028C1670, 0xA028E8DF0
IM_ACTIVE, IM_BYTES = OG_STATE + 0x200, 0xB18
IM_SRC_STOCK, IM_SRC_32 = 0x408C4000, 0x408C5000
L = dict(opt_hdr=0x000, opt=0x010, dial=0x0A8, rows_h=0x0B0, rows_n=0x278, codes_h=0x440, codes_n=0x4D8,
         cond=0x570, cfg_t=0x5C0, cfg_h=0x788, cfg_n=0x950)
DESC = 0x43A1E828                                  # N-RAW i-menu item AB
OG_NEVER = 0x0E2E3A32                              # E2: condition number cond_never_hook reports unavailable
OG_BLANK_ICON = 0x7103
ICONS = Path(__file__).resolve().parent / 'icons'

p32 = lambda *v: struct.pack('<' + 'I' * len(v), *v)
p64 = lambda *v: struct.pack('<' + 'Q' * len(v), *v)


def off(a):
    return a - INIT + IOFF if a >= INIT else a - B


def raw(stock, a, n):
    return stock[off(a):off(a) + n]


# ---- strings -------------------------------------------------------------------------------------------------------
def labels(stock, table_at, blob_at):
    """Per language: 3 8.3K labels (stock 2034..2036 with the 3:2 height), 7 4.1K labels (2037..2043), file type."""
    out = []
    for lang in range(36):
        t = struct.unpack_from('<Q', stock, table_at + lang * 8)[0] - B
        b = struct.unpack_from('<Q', stock, blob_at + lang * 8)[0] - B

        def s(i):
            x, y = struct.unpack_from('<2i', stock, t + 4 * i)
            return stock[b + x:b + y].decode('utf-16le')
        row = []
        for idx, (old, new) in [(i, ('4644', '5504')) for i in (2034, 2035, 2036)] + \
                               [(i, ('2322', '2752')) for i in range(2037, 2044)]:
            native = s(idx)
            require(native.count('[FX]') == 1, 'Unexpected firmware structure')
            hits, label = 0, native
            for sep in ('', '.', ',', ' '):
                a, c = old[0] + sep + old[1:], new[0] + sep + new[1:]
                hits += label.count(a)
                label = label.replace(a, c)
            require(hits == 1, (lang, native))
            row.append(label)
        nraw = s(0x7EE)
        at = nraw.rfind('(NEV)')
        require(at > 0 and nraw.count('(NEV)') == 1, (lang, nraw))
        head = nraw[:at]
        row.append(head + '3:2 (NEV)' if head.endswith(' ') else head + ' 3:2(NEV)')
        # E2: help text = stock 0xA17 with "<3:2 label><suffix>" after its first line "<N-RAW label><suffix>"
        help_text = s(STOCK_HELP)
        first, nl, rest = help_text.partition('\n')
        suffix = first[len(nraw):]
        require(first.startswith(nraw) and nl and 1 <= len(suffix) <= 2 and suffix.strip() in (':', '\uff1a'), (lang, first))
        row.append(first + '\n' + row[-1] + suffix + '\n' + rest)
        pool = set(stock[b + struct.unpack_from('<i', stock, t)[0]:b + struct.unpack_from('<i', stock, t + 4 * 3136)[0]].decode('utf-16le'))
        missing = sorted({c for c in ''.join(row) if c not in pool})
        require(not missing, (lang, missing))
        out.append(row)
    return out


# ---- relocation helpers --------------------------------------------------------------------------------------------
def reloc48(stock, put, site, addr, why):
    """MOVZ xd,#lo at site plus its MOVK xd,#..,lsl16 / lsl32 / lsl48 among the next 12 words -> addr."""
    w = struct.unpack('<I', raw(stock, site, 4))[0]
    require(w & 0xFFE00000 == 0xD2800000, (hex(site), hex(w)))
    rd = w & 31
    put(site, p32((w & ~(0xFFFF << 5)) | ((addr & 0xFFFF) << 5)), why)
    seen = set()
    for k in range(1, 13):
        if seen == {1, 2, 3}:
            break
        a = site + 4 * k
        v = struct.unpack('<I', raw(stock, a, 4))[0]
        require(v & 0xFF80001F != 0xD2800000 | rd, (hex(a), 'second MOVZ before the MOVKs'))
        if v & 0xFF80001F == 0xF2800000 | rd:
            hw = (v >> 21) & 3
            require(hw in (1, 2, 3) and hw not in seen, (hex(a), hex(v)))
            seen.add(hw)
            part = (addr >> (16 * hw)) & 0xFFFF
            put(a, p32((v & ~(0xFFFF << 5)) | (part << 5)), why)
    require(seen == {1, 2, 3}, (hex(site), seen))


# ---- i menu --------------------------------------------------------------------------------------------------------
def imenu_active(stock, put):
    """Two ROM source blocks with the active layout; the readers and the descriptor point at IM_ACTIVE (RAM)."""
    stock_rows = {q: [list(struct.unpack('<6I', raw(stock, t + 24 * i, 24))) for i in range(19)]
                  for q, t in ((1, 0x42B0662C), (0, 0x42B067F4))}
    stock_codes = {q: [list(struct.unpack('<2I', raw(stock, t + 8 * i, 8))) for i in range(19)]
                   for q, t in ((1, 0x42B06B84), (0, 0x42B06C1C))}
    cond = list(struct.unpack('<19I', raw(stock, 0x43A1C478, 76)))
    cfg = {k: [list(struct.unpack('<6I', raw(stock, a + 24 * i, 24))) for i in range(19)]
           for k, a in (('t', 0xA0288A150), ('h', 0xA0288AB68), ('n', 0xA0288AD30))}
    opt_ptr, opt_count = struct.unpack('<QQ', raw(stock, 0x43A20EF8, 16))
    pairs = list(struct.unpack('<38I', raw(stock, opt_ptr, 152)))
    require(opt_count == 19 and pairs == [i // 2 for i in range(38)], 'Unexpected firmware structure')
    for q in (0, 1):
        for i, r in enumerate(stock_rows[q]):
            require(r[3] == q and r[4] == i and r[2] == 0, 'Unexpected firmware structure')
        for i, c in enumerate(stock_codes[q]):
            require(c[0] == i, 'Unexpected firmware structure')
    for i in range(10):
        s = i + 2
        size, rate = stock_rows[1][s][:2]
        require((size, rate) == ((6, 4 + i) if i < 3 else (4, i - 3)), 'Unexpected firmware structure')
    for k in cfg:
        for i, r in enumerate(cfg[k]):
            require(r[0] == i, 'Unexpected firmware structure')

    def block(n, rows, codes, conds, cfgs, opts):
        b = bytearray(IM_BYTES)
        b[L['opt_hdr']:L['opt_hdr'] + 16] = p64(IM_ACTIVE + L['opt'], n)
        b[L['opt']:L['opt'] + 8 * len(opts)] = b''.join(p32(*o) for o in opts)
        b[L['dial']:L['dial'] + 4] = p32(n)
        for q, key in ((1, 'rows_h'), (0, 'rows_n')):
            b[L[key]:L[key] + 456] = b''.join(p32(*r) for r in rows[q])
        for q, key in ((1, 'codes_h'), (0, 'codes_n')):
            b[L[key]:L[key] + 152] = b''.join(p32(*c) for c in codes[q])
        b[L['cond']:L['cond'] + 76] = p32(*conds)
        for k, key in (('t', 'cfg_t'), ('h', 'cfg_h'), ('n', 'cfg_n')):
            b[L[key]:L[key] + 456] = b''.join(p32(*r) for r in cfgs[k])
        return bytes(b)

    stock_block = block(19, stock_rows, stock_codes, cond, cfg, [(i, i) for i in range(19)])
    pad_row = [0xFF, 0xFF, 0xFF, 0xFF, 0xFFFF, 0]
    rows32, codes32, cfg32 = {}, {}, {}
    for q in (0, 1):
        rows32[q] = [stock_rows[q][p + 2][:4] + [p, stock_rows[q][p + 2][5]] for p in range(10)] + [pad_row] * 9
        codes32[q] = [[p, stock_codes[q][p + 2][1]] for p in range(10)] + [[0xFFFF, 0]] * 9
    # E2: the 3:2 list lays out 10 cells (imenu_sync writes the layout count, see below); choices 10..18 are also never
    # available (cond_never_hook) and carry a blank icon, so no 19-choice path can land on them (E1 body test I1/I2)
    cond32 = [cond[p + 2] for p in range(10)] + [OG_NEVER] * 9
    require(489 in cond and OG_NEVER not in cond, 'Unexpected firmware structure')
    cfg32['t'] = [[p, 2, LABEL_IDS[p], 0, 0, 0] for p in range(10)] + [[0xFFFF, 2, 2032, 0, 0, 0]] * 9
    for k in ('h', 'n'):
        require(cfg[k][0][1] == 1, 'Unexpected firmware structure')
        cfg32[k] = [[p] + cfg[k][p + 2][1:] for p in range(10)] + [[0xFFFF, 1, OG_BLANK_ICON, 0, 0, 0]] * 9
    block32 = block(10, rows32, codes32, cond32, cfg32, [(p, p) for p in range(10)])
    require(IM_BYTES <= 0x1000 and IM_ACTIVE + IM_BYTES <= OG_STATE + 0x1000, 'Unexpected firmware structure')
    # E2: the N-RAW list's layout A028B07A0 (init data, read live by the list layout 404D84DC): 19 cell elements of
    # 2Ch at 43A2E004 (objects 48BA..48CC), count u16 at +20h; imenu_sync writes 10 there in 3:2 and 19 otherwise
    lay = raw(stock, 0xA028B07A0, 0x28)
    require(struct.unpack_from('<QQQQI', lay, 0) == (0x80000000, 0x43A2CA20, 0x43A2E004, 0, 19), 'Unexpected firmware structure')
    require([struct.unpack_from('<H', raw(stock, 0x43A2E004 + 0x2C * i + 0x18, 2))[0] for i in range(19)]
            == list(range(0x48BA, 0x48BA + 19)), 'Unexpected firmware structure')
    require(lay.count(struct.pack('<Q', 0x43A2E004)) == 1 and stock.count(struct.pack('<Q', 0x43A2E004)) == 1,
            'Unexpected firmware structure')
    put(IM_SRC_STOCK, stock_block, 'N-RAW i-menu source block: the 19 stock choices (active layout)')
    put(IM_SRC_32, block32, 'N-RAW i-menu source block: the 10 3:2 choices (active layout)')

    a = lambda key: IM_ACTIVE + L[key]
    for site, key in [(0x404D9AC4, 'rows_n'), (0x404D9AC8, 'rows_h'), (0x404E49B8, 'rows_n'), (0x404E49BC, 'rows_h'),
                      (0x404DC2A0, 'rows_n'), (0x404DC2A4, 'rows_h'), (0x404E4C10, 'rows_n'), (0x404E4C14, 'rows_h'),
                      (0x404D9994, 'codes_n'), (0x404D9998, 'codes_h'), (0x404E49C8, 'cond')]:
        reloc48(stock, put, site, a(key), 'N-RAW i-menu reader -> active table ' + key)
    require(raw(stock, 0x42B03098, 8) == p64(0x43A1C478), 'Unexpected firmware structure')
    put(0x42B03098, p64(a('cond')), 'N-RAW selected-row availability -> active table')
    require(raw(stock, DESC + 8, 8) == p64(0x43A20EF8), 'Unexpected firmware structure')
    put(DESC + 8, p64(a('opt_hdr')), 'N-RAW i-menu option set -> active {pointer, count}')
    widgets = 0
    for title, first, normal in ((0xA0288A108, 0xA0288A318, 0xA0288A740), (0xA028A6768, 0xA028A67B0, 0xA028A6BD8)):
        require(raw(stock, title + 8, 16) == p64(0xA0288A150, 19), 'Unexpected firmware structure')
        put(B + off(title + 8), p64(a('cfg_t'), 19), 'N-RAW i-menu title selectors -> active')
        for base, src, key in ((first, 0xA0288AB68, 'cfg_h'), (normal, 0xA0288AD30, 'cfg_n')):
            for i in range(19):
                w = base + 56 * i
                require(raw(stock, w + 8, 16) == p64(src, 19), 'Unexpected firmware structure')
                put(B + off(w + 8), p64(a(key), 19), 'N-RAW i-menu cell selectors -> active')
                widgets += 1
    return dict(active=hex(IM_ACTIVE), bytes=IM_BYTES, sources={'stock': hex(IM_SRC_STOCK), '3:2': hex(IM_SRC_32)},
                layout={k: hex(v) for k, v in L.items()}, widgets=widgets, choices={'stock': 19, '3:2': 10},
                order='3:2: 8256x5504 30/25/24p, 4128x2752 120/100/60/50/30/25/24p (stock positions 2..11)')


# ---- file-type page ------------------------------------------------------------------------------------------------
def file_type_rows(image):
    """The 11-row table built from the 10 rows of `image` (stock, or the composed image after every group, so that
    another group's edits of those rows, e.g. ProRes T's row labels, are carried into the relocated table)."""
    rows = [bytearray(raw(image, 0x43C06A80 + 44 * i, 44)) for i in range(10)]
    require(struct.unpack_from('<I', rows[0], 0)[0] == 0x7EE and struct.unpack_from('<I', rows[0], 24)[0] == 0x30E5,
            'Unexpected firmware structure')
    require(all(struct.unpack_from('<I', r, 24)[0] != FT_CTRL for r in rows), 'Unexpected firmware structure')
    new = bytearray(rows[0])
    struct.pack_into('<I', new, 0, FT_LABEL)
    struct.pack_into('<I', new, 24, FT_CTRL)
    out = [rows[0], new] + rows[1:]
    for r in out:                                 # E2: one help page per row (stock: all 0xA17)
        require(struct.unpack_from('<I', r, 4)[0] == STOCK_HELP, 'Unexpected firmware structure')
        struct.pack_into('<I', r, 4, FT_HELP)
    return b''.join(bytes(r) for r in out)


def refresh_file_type_rows(img):
    """Composer step after all groups: rebuild the relocated rows from the final 10-row table."""
    rows = file_type_rows(bytes(img.new))
    hits = [e for e in img.edits if e['offset'] == FT_ROWS - B]
    require(len(hits) == 1 and len(hits[0]['new']) == len(rows), 'Unexpected firmware structure')
    e = hits[0]
    changed = e['new'] != rows
    e['new'] = rows
    img.new[e['offset']:e['offset'] + len(rows)] = rows
    if changed:
        e['purpose'] += '; rows rebuilt from the composed table (other groups\' row edits carried over)'
    return changed


def file_type_page(stock, put, entries):
    rows_ptr, ev_ptr = struct.unpack('<QQ', raw(stock, FT_PAGE + 0x10, 16))
    count = struct.unpack('<H', raw(stock, FT_PAGE + 0x20, 2))[0]
    require((rows_ptr, ev_ptr, count) == (0x43C06A80, 0x43C06C38, 10), 'Unexpected firmware structure')
    rows = [bytearray(raw(stock, rows_ptr + 44 * i, 44)) for i in range(10)]
    evs = list(struct.unpack('<10Q', raw(stock, ev_ptr, 80)))
    require(struct.unpack_from('<I', rows[0], 0)[0] == 0x7EE and struct.unpack_from('<I', rows[0], 24)[0] == 0x30E5,
            'Unexpected firmware structure')
    require(all(struct.unpack_from('<I', r, 24)[0] != FT_CTRL for r in rows), 'Unexpected firmware structure')
    rows = file_type_rows(stock)
    evs = [evs[0], evs[0]] + evs[1:]
    put(FT_ROWS, rows, 'video file type page: 11 rows, N-RAW 3:2 below N-RAW; help page with the 3:2 heading')
    put(FT_EVENTS, p64(*evs), 'video file type page: row events (3:2 row shares N-RAW events)')
    put(B + off(FT_PAGE + 0x10), p64(FT_ROWS, FT_EVENTS), 'video file type page rows and events')
    put(B + off(FT_PAGE + 0x20), struct.pack('<H', 11), 'video file type page: 11 rows')
    # E2: the video menu row "Video file type" (item 2FC1, stock row 6) opens the same help (features.py collects it)
    vrow = 0x43C04860
    require(raw(stock, vrow + 24, 4) == p32(0x2FC1) and raw(stock, vrow + 4, 4) == p32(STOCK_HELP), 'Unexpected firmware structure')
    put(vrow + 4, p32(FT_HELP), 'video menu row Video file type: help with the 3:2 heading')
    require(raw(stock, FT_REFRESH_SLOT, 8) == p64(0x4056CD84), 'Unexpected firmware structure')
    put(B + off(FT_REFRESH_SLOT), p64(entries['ft_refresh3_hook']), 'video file type page refresh -> ft_refresh3_hook (E3: each N-RAW mode shows its own tone)')
    return dict(rows=hex(FT_ROWS), events=hex(FT_EVENTS), count=11, control=hex(FT_CTRL), label=FT_LABEL)


# ---- icons ---------------------------------------------------------------------------------------------------------
def icon_blob(entries):
    meta = json.loads((ICONS / 'og32-icons.json').read_text())
    recs, pngs = bytearray(), bytearray()
    base = entries['og_icon_png_hook']
    for k, e in enumerate(meta['icons']):
        require(int(e['number'], 16) == 0x7100 + k, 'Icon order')
        b = (ICONS / e['file']).read_bytes()
        require(len(b) == e['bytes'] and hashlib.sha256(b).hexdigest() == e['sha256'], 'Derived icon changed')
        recs += struct.pack('<HHIQ', 0x100, 0, len(b), base + len(pngs))
        pngs += b + bytes(-len(b) % 8)
    require(len(pngs) <= 0x3000 and entries['og_icon_png_hook'] - entries['og_icon_records_hook'] == len(recs), 'Icon area')
    return bytes(recs), bytes(pngs), [dict(number=e['number'], role=e['role'], bytes=e['bytes'], sha256=e['sha256']) for e in meta['icons']]


# ---- sites ---------------------------------------------------------------------------------------------------------
NEW_SITES = [(0x4056C688, 'fd079f1a', 'list_hide_hook', True), (0x4056C9DC, '34d968b8', 'ft_cursor_hook', False),
             (0x4056D2B0, 'f553bea9', 'ft_ok_hook', False), (0x40572FA0, 'e00316aa', 'menu_icon_hook', True),
             (0x4041E1F0, '20098052', 'lv_icon_hook', False), (0x404F8C48, '3f010a6b', 'lv_diff_hook', False),
             (0x4032DC7C, '1f01096b', 'og_icon_idx_hook', False), (0x4032DD5C, '1f01006b', 'og_icon_val_hook', False),
             (0x404E49F0, '61028052', 'im_dial_count_hook', True), (0x404E4AE8, '08d979b8', 'im_wrap_count_hook', True),
             # 4.1K 3:2 (H14 route under the flag, all rates)
             (0x410666F8, 'f37bbfa9', 'h14_readout_hook', False), (0x41066A10, '08004039', 'h14_inner_hook', False),
             (0x41066AA8, '08004039', 'h14_active_hook', False), (0x41067274, '1f1c0071', 'h14_route_hook', False),
             (0x41065194, 'ffc302d1', 'h14_coordinates_hook', False), (0x410A6C88, '087381d2', 'h14_crop_hook', False),
             (0x410A58E4, '3f000039', 'h14_frame_height_hook', False), (0x406D2C8C, '48228152', 'h14_nctg_height_hook', False),
             (0x406D3138, '49228152', 'h14_main_height_hook', False),
             # E2 (E1 body test): file-type page control tests, tone OK, 3:2 star icons
             (0x4056CB80, '161940b9', 'ft_ctrl_w22_hook', True), (0x4056CC80, '161940b9', 'ft_ctrl_w22_hook', True),
             (0x4056D0F0, '081940b9', 'ft_ctrl_w8_hook', True), (0x4056D1A8, '081940b9', 'ft_ctrl_w8_hook', True),
             (0x4056D3C8, '151940b9', 'ft_ctrl_w21_hook', True), (0x4056DAE0, '021940b9', 'tone_ok_ctrl_hook', True),
             (0x4056C8E4, 'f37b43a9', 'ft_star_hook', False), (0x404CA1D0, 'a3b0fc97', 'im_ft_icon_hook', True),
             (0x403A036C, 'f963bca9', 'cond_never_hook', False),
             # E2: plan 13 at 30/25/24p takes the 50..120p variants under 4.1K 3:2
             (0x41062148, '28000014', 'og_front_low_hook', False), (0x41062698, '2831889a', 'og_param_low_hook', False),
             (0x41062BB8, '2831889a', 'og_table_ce8_low_hook', False),
             (0x41062CD8, '080940b9', 'og_table_db0_low_hook', False),
             (0x41062FD0, '080940b9', 'og_table_ea8_low_hook', False),
             (0x410658F8, '080840b9', 'og_coord_low_hook', False), (0x410B659C, '480840b9', 'og_d980_low_hook', False),
             # E3 (E2 body test): frame-size page subtitle in 3:2
             (0x4056C64C, '010540b9', 'fs_title_hook', True),
             # E3: the tone sub-page cursor starts on the parent row's own tone (N-RAW / N-RAW 3:2)
             (0x4056D66C, '4bfbf997', 'tone_cursor_hook', True),
             # E3: the i-menu main-dial strip walks the ten 3:2 choices (E2 body test B2)
             (0x40458EA0, '69028052', 'strip32_hook', True),
             # E4: 4.1K 3:2 at 30/25/24p records the full 8280x5520 readout scaled 2:1 (RAW source, class-2 driver)
             (0x41066978, '08004039', 'raw_source_e4_hook', False), (0x4117190C, '080540b9', 'driver_class2_e4_hook', False)]
# E4: earlier sites whose hook becomes an E4 wrapper (the wrapper enters the earlier hook for every other case)
E4_HOOKS = {0x410666F8: 'h14_readout_e4_hook', 0x41066A10: 'h14_inner_e4_hook', 0x41066AA8: 'h14_active_e4_hook',
            0x41065194: 'h14_coordinates_e4_hook', 0x41062148: 'og_front_e4_hook'}
# E4: E2's plan-13 rate forks stay stock, so plan 13 at 30/25/24p takes its low-rate (plan-12) records and template
E4_STOCK = {0x41062698: 'og_param_low_hook', 0x41062BB8: 'og_table_ce8_low_hook', 0x41062CD8: 'og_table_db0_low_hook',
            0x41062FD0: 'og_table_ea8_low_hook', 0x410658F8: 'og_coord_low_hook', 0x410B659C: 'og_d980_low_hook'}
# D-series sites whose hook becomes an E1 wrapper that handles 4.1K 3:2 and otherwise enters the D-series hook
RENAME = {'boot_reset_hook': 'boot_reset_e1_hook', 'configuration_hook': 'configuration_e4_hook',
          'view_commit_hook': 'view_commit_e1_hook', 'half_plan_hook': 'half_plan_e1_hook',
          'nctg_crop_hook': 'nctg_crop_e1_hook', 'playback_capture_hook': 'playback_capture_e2_hook',
          'proxy_sps_hook': 'proxy_sps_e4_hook'}     # E4: configuration_e4_hook enters configuration_e1_hook
HALF_W, HALF_H, HALF_STOCK_H = 4140, 2756, 2330


def half_rows(table, count, why, rows):
    """4.1K records (4140x2330) of an open-gate record copy -> 4140x2756, bit rate scaled by 2756/2330."""
    import math
    t = bytearray(table)
    n = 0
    for i in range(count):
        w, h, num, den, res, bps = struct.unpack_from('<HHIIIQ', t, 24 * i)
        if (w, h) != (HALF_W, HALF_STOCK_H):
            continue
        new = math.ceil(bps * HALF_H / HALF_STOCK_H / 1e6) * 1000000 if bps else 0
        struct.pack_into('<H', t, 24 * i + 2, HALF_H)
        struct.pack_into('<Q', t, 24 * i + 16, new)
        rows.append(dict(table=why, index=i, numerator=num, denominator=den, stock_bps=bps, og32_bps=new))
        n += 1
    return bytes(t), n
DESC_SLOTS = [(0x10, 0x404E4848, 'im_dial_hook'), (0x18, 0x404DC124, 'im_grid_hook'),
              (0x20, 0x404DDE74, 'im_selected_hook'), (0x30, 0x404DB3BC, 'im_cancel_hook')]
RETIRED = {0x4057038C: 'menu_apply_hook (main menu no longer writes the flag)',
           0x404DC334: 'i_current_hook (current-row search reads the active table)',
           0x404E4CB0: 'i_dial_current_hook (same)'}
REPLACED = {0x41015D6C: 'setting_normal_e1_hook', 0x404E4AB0: 'i_apply_q3_dial_hook', 0x404D9B98: 'i_apply_q3_list_hook',
            0x40797088: 'film_icon_e2_hook', 0x406C0280: 'fx_icon_e2_hook', 0x41015F80: 'setting_bank_normal_e2_hook'}


def install_sites(stock, put, entries):
    bl = lambda a, t, call: struct.pack('<I', (0x94000000 if call else 0x14000000) | ((t - a) // 4) & 0x3FFFFFF)
    # ft_star_hook: 3:2 row 35C0+p takes star-table entry 2+p = stock master row 53+p (its default icon is the star)
    for p, src in enumerate(OG32_STOCK_ROWS):
        ctrl, star, plain = struct.unpack('<3I', raw(stock, 0x42B20318 + 12 * (2 + p), 12))
        row = struct.unpack('<11I', stock[61501836 + 44 * src:61501836 + 44 * (src + 1)])
        require(row[6] == ctrl and row[5] == star and plain != star, 'Unexpected firmware structure')
    done = []
    for a, old, name, call in NEW_SITES:
        require(raw(stock, a, 4) == bytes.fromhex(old), 'Unexpected firmware structure')
        if a in E4_STOCK:
            require(E4_STOCK[a] == name, 'E4 stock site table out of step')
            done.append(dict(site=hex(a), hook=None, stock_kept=name))
            continue
        name = E4_HOOKS.get(a, name)
        put(a, bl(a, entries[name], call), name)
        done.append(dict(site=hex(a), hook=name))
    for slot, old, name in DESC_SLOTS:
        require(raw(stock, DESC + slot, 8) == p64(old), 'Unexpected firmware structure')
        put(DESC + slot, p64(entries[name]), 'N-RAW i-menu descriptor -> ' + name)
        done.append(dict(site=hex(DESC + slot), hook=name))
    return done
