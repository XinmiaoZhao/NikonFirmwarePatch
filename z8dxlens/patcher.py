"""FX image area with DX lenses (upstream issue #45): fixed byte edits only, no code cave.

Stock C3.11 forces DX whenever an electronic DX lens is attached: lens kind 0x04002d0c in {1 Z, 3 F/FTZ}
and lens-covers-FX 0x04002d13 == 0.  These edits make the image-area logic treat such a lens like an FX
lens, so the user's own image-area choice is used.  The camera no longer switches to DX by itself; the
user selects DX when wanted.  The lens is still reported truthfully (PTP LensType DX bit, EXIF), and
Image Dust Off ref photo stays unavailable with DX lenses (UI predicate #38 is left intact).
"""
import struct
from z8prores.package import require

BASE = 0x40160000
B_ALWAYS = 0x14000000
NOP = 0xd503201f


def _b(at, to):
    return B_ALWAYS | (((to - at) // 4) & 0x3ffffff)


# (VA, stock word, new word, purpose)
CODE = (
    (0x40ed91c0, 0x35000069, _b(0x40ed91c0, 0x40ed91cc),
     'image-area resolver keeps the chosen area with a DX lens (cbnz w9 -> b)'),
    (0x40ed9174, 0x35fffe69, _b(0x40ed9174, 0x40ed9140),
     'image-area resolver, video at 120p/100p and slow motion: no DX crop for a DX lens (cbnz w9 -> b)'),
    (0x40ed8f9c, 0x0a080128, 0x2a1f03e8,
     'video frame-size helper treats a DX lens as FX (and w8,w9,w8 -> mov w8,wzr)'),
    (0x4067c478, 0x340000c0, _b(0x4067c478, 0x4067c490),
     'button command 0x95 not blocked by a DX lens'),
    (0x405e0560, 0x350000a0, _b(0x405e0560, 0x405e0574),
     'image-area button event not ignored with a DX lens'),
    (0x4081c728, 0x34000200, NOP, 'PTP photo image-area set allowed with a DX lens'),
    (0x4081cde4, 0x34000160, NOP, 'PTP video image-area set allowed with a DX lens'),
    (0x4083ffd4, 0x34000120, NOP, 'PTP movie frame-size set allowed with a DX lens'),
)

# UI disable lists: table 0x42dedf78, 16-byte entries {u64 list, u16 count}; predicate 38 = DX lens attached.
TABLE = 0x42dedf78
PRED_DX = 38
# Multi-predicate lists: replace 38 with a predicate already present in the same list.
LIST_SLOTS = (
    (25, 1, 7, 'photo Choose image area row'),
    (430, 1, 7, 'photo image-area button function'),
    (107, 1, 97, 'video Choose image area row'),
    (459, 2, 97, 'video image-area button function'),
)
# Single-predicate lists (38,): count -> 0.
COUNT_ITEMS = ((82, 'time-lapse movie Choose image area'),) + tuple(
    (i, 'FX-only video frame size option') for i in range(109, 132))


def edits(eg):
    out = []

    def add(va, old, new, why):
        o = va - BASE
        require(eg[o:o + len(old)] == old, f'dx-lens-fx: unexpected stock bytes at {va:#x}')
        out.append(dict(offset=o, old=old, new=new, purpose='dx-lens-fx: ' + why))

    for va, old, new, why in CODE:
        add(va, struct.pack('<I', old), struct.pack('<I', new), why)

    def entry(item):
        ptr, count = struct.unpack_from('<QH', eg, TABLE - BASE + 16 * item)
        return ptr, count

    for item, slot, repl, why in LIST_SLOTS:
        ptr, count = entry(item)
        lst = struct.unpack_from(f'<{count}I', eg, ptr - BASE)
        require(lst[slot] == PRED_DX and repl in lst and lst.count(PRED_DX) == 1,
                f'dx-lens-fx: item {item} list layout')
        add(ptr + 4 * slot, struct.pack('<I', PRED_DX), struct.pack('<I', repl),
            f'UI item {item} ({why}) not greyed by a DX lens')

    for item, why in COUNT_ITEMS:
        ptr, count = entry(item)
        require(count == 1 and struct.unpack_from('<I', eg, ptr - BASE)[0] == PRED_DX,
                f'dx-lens-fx: item {item} list layout')
        add(TABLE + 16 * item + 8, struct.pack('<H', 1), struct.pack('<H', 0),
            f'UI item {item} ({why}) not greyed by a DX lens')
    return out
