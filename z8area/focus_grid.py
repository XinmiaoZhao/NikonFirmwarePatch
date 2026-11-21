import struct
from . import playback as E
hb1, sha = E.hb1, E.sha

GRID_TABLES = {0xA02A5CE38: 9, 0xA02A4C470: 135}     # base: sets (0xFC each, 9 records of 0x1C)
SET, REC, AREA43_W, AREA11_W, FULL_W = 0xFC, 0x1C, 7344, 5504, 8256
pk = lambda v: (v & 0xFFFF, v >> 16)
up = lambda a, b_: a | b_ << 16


def derive(r0, area_w):
    """record for an image area that keeps the full height, cut from the FX record r0 by the stock 1:1 rule; None if none fits."""
    (l, t), (r, b) = pk(r0[0]), pk(r0[1]); pw = pk(r0[2])[0]; sx = pk(r0[4])[0]; n0 = r0[5]
    lim = (r - l) * area_w / FULL_W; n = n0
    while n >= 1 and (n - 1) * sx + pw > lim: n -= 2
    if n < 1: return None
    k = (n0 - n) // 2
    return (up(l + k * sx, t), up(r - k * sx, b), r0[2], r0[3], r0[4], n, r0[6])


def records(eg, base, s, r): return struct.unpack_from('<7I', eg, hb1.data_off(base + s * SET + r * REC))


def grid_edits(eg):
    """check the rule against every stock 1:1 record, then the record-2 contents for every set."""
    out, checked = [], 0
    for base, sets in GRID_TABLES.items():
        assert hb1.data_off(base + sets * SET) <= hb1.DATA_END
        for s in range(sets):
            r0, r2, r3, r8 = (records(eg, base, s, r) for r in (0, 2, 3, 8))
            assert not any(r2) and not any(r3), (hex(base), s)
            if not any(r0): continue
            d = derive(r0, AREA11_W)
            if d is None: assert not any(r8), (hex(base), s)
            else:
                assert all(abs(x - y) <= 1 for i in (0, 1) for x, y in zip(pk(d[i]), pk(r8[i]))) and d[2:] == r8[2:], (hex(base), s, d, r8)
            checked += 1
            n = derive(r0, AREA43_W)
            if n is not None: out.append((base, s, n))
    return out, checked


def compose(eg):
    img, det = E.compose(eg)
    edits, checked = grid_edits(eg)
    for base, s, rec in edits:
        at = base + s * SET + 2 * REC
        img.put(hb1.BASE + hb1.data_off(at), struct.pack('<7I', *rec),
                f'focus-point grid {base:#x} set {s} record 2 (4:3): {pk(rec[0])}-{pk(rec[1])} {rec[5]}x{rec[6]}', expect_zero=True)
    det['af_grid'] = dict(tables={hex(k): v for k, v in GRID_TABLES.items()}, rule_checked_sets=checked, records_written=len(edits),
                          single_point=[dict(table=hex(b_), set=s, top_left=pk(r[0]), bottom_right=pk(r[1]), cols=r[5], rows=r[6])
                                        for b_, s, r in edits if b_ == 0xA02A5CE38])
    return img, det
