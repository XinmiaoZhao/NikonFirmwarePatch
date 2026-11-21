import struct
from . import live_view as C
B, A, hb1, sha = C.B, C.A, C.hb1, C.sha

TABLES = (0x44B7FD68, 0x44B7FF48)          # W2 bit0 set / clear
LAYOUTS, CATS, CAT32, CAT43, CAT11 = 12, 5, 0, 3, 4
L3_43 = (456, 0, 7800, 5504)                # 4:3 JPEG crop 7344x5504 on the 8256x5504 plane
BLACKOUT_TABLE = 0xA029CAB80                # capture blackout: category of areas 2..8 (one reader, 0x40f9bf8c)


def rect(B_, t, lay, cat): return struct.unpack_from('<4H', B_, t + lay * 0x28 + cat * 8 - hb1.BASE)


def even_near(x):
    lo = int(x) // 2 * 2
    return lo if x - lo < lo + 2 - x else lo + 2


def window(r32, lay, num, den):
    """num/den = target aspect; returns the rectangle in the layout's 3:2 rectangle r32."""
    l, t, r, b = r32; W, Hh = r - l, b - t
    w = even_near(W * 2 * num / (3 * den)) if lay == 4 else even_near(Hh * num / den)
    left = l + (W - w) / 2
    left = int(left) + (int(left) & 1) if left == int(left) else int(left) + 1 + ((int(left) + 1) & 1)
    return (left, t, left + w, b)


def compose(eg):
    img, det = C.compose(eg)
    rows = []
    for t in TABLES:
        for lay in range(LAYOUTS):
            r32, r11 = rect(eg, t, lay, CAT32), rect(eg, t, lay, CAT11)
            want11 = (1376, 0, 6880, 5504) if lay == 3 else window(r32, lay, 1, 1)
            assert r11 == want11, ('rule does not reproduce stock 1:1', hex(t), lay, r11, want11)
            assert rect(eg, t, lay, CAT43) == (0, 0, 0, 0) and rect(eg, t, lay, 2) == (0, 0, 0, 0)
            new = L3_43 if lay == 3 else window(r32, lay, 4, 3)
            assert new[2] <= r32[2] and new[0] >= r32[0] and new[0] % 2 == 0 and (new[2] - new[0]) % 2 == 0
            at = t + lay * 0x28 + CAT43 * 8
            img.put(at, struct.pack('<4H', *new), f'LV window table {t:#x} layout {lay} category 3 (4:3): (0,0,0,0) -> {new}',
                    expect=bytes(8))
            rows.append(dict(table=hex(t), layout=lay, at=hex(at), stock_32=list(r32), stock_11=list(r11), new_43=list(new)))
    # capture blackout (0x40f9bf20..0x40f9c034) takes the category from setting 0x2124 through the per-area table
    # 0xa029cab80 (areas 2..8; areas 0/1 -> 0) instead of the classifier: area 2 is still the 5:4 category 2 -> zero window
    bo = [struct.unpack_from('<I', eg, hb1.data_off(BLACKOUT_TABLE) + 4 * i)[0] for i in range(7)]
    assert bo == [2, 0, 1, 1, 1, 1, 4], bo
    img.put(hb1.data_off(BLACKOUT_TABLE), struct.pack('<I', CAT43), 'capture blackout category table 0xa029cab80 area 2: 2 (5:4) -> 3 (4:3)',
            expect=struct.pack('<I', 2), offset=True)
    det['lv_window'] = dict(lookup='0x411871ac', classifier='0x41059d04', tables=[hex(t) for t in TABLES], category=CAT43, rows=rows,
                            blackout_table=hex(BLACKOUT_TABLE), blackout_reader='0x40f9bf8c', blackout_areas_2_8=[bo, [CAT43] + bo[1:]])
    return img, det
