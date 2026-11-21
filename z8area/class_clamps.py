#!/usr/bin/env python3
"""A14: fix the three confirmed LV/AF class clamps; no speculative freeze fix.

Applied after the A2i composition on the factory payload. The image-area class
tables and window lookup already support 0..6 in A2i. This changes the callers'
unsigned test from (class - 1) < 4 to (class - 1) < 6, preserving the rejection
of invalid classes. It does not widen other five-value enums.
"""
import struct

BASE = 0x40160000
SITES = {
    0x40F35FD0: (0x7100111F, 0x7100191F, 'LV display category, w8'),
    0x40DB3304: (0x7100113F, 0x7100193F, 'AF window caller 40DB2C3C, w9'),
    0x40DB5614: (0x7100113F, 0x7100193F, 'AF sensor-plane caller 40DB55C4, w9'),
}


def apply(img, stock):
    rows = []
    for va, (old, new, purpose) in SITES.items():
        offset = va - BASE
        before = struct.pack('<I', old)
        assert stock[offset:offset + 4] == before
        assert bytes(img.new[offset:offset + 4]) == before
        img.put(offset, struct.pack('<I', new),
                f'A14 {purpose}: preserve preview classes 1..6, else 0',
                expect=before, offset=True)
        rows.append(dict(va=hex(va), old=hex(old), new=hex(new), purpose=purpose))
    return dict(sites=rows, freeze_fix=False)
