"""Locked menu banks (prototype): leaving a bank no longer stores the live settings into it.

Stock C3.11 keeps the live settings in DS slot 0 and banks A-D in slots 1-4. The live pointer of every
banked item (item table 4400A5C0, +8) is its slot-0 storage, and ordinary setting changes write slot 0 only.
The bank routines below copy slot 0 back into a bank. Five one-word edits gate those copies:

  photo   410dd26c  photo shooting menu bank select 410dd1ec(new, save, list): the save of slot 0 into the
                    bank being left (465 items 0A0299E888, plus 11 extended-bank items 0A0299EFCC) runs only
                    when the chosen bank is the current one, so re-selecting the current bank stores the
                    live settings. Both callers (410df7ec, 410e9590) pass save = 1.
  custom  410de0a8  custom settings bank select 410de050: the same rule for its 609 items (0A0299EFF8).
  copy    410ddafc  copy photo bank 410dda64: no save of slot 0 into the source first when the source is
                    the current bank; the copy takes the stored bank.
  ccopy   410de62c  copy custom settings bank 410de5a0: the same.
  ext     410dd8bc  extended photo menu banks off 410dd84c: no save of the live extended items into the
                    current bank. Switching it on still saves them into the shared slot 5.

The two select gates jump to a short routine in the text gap below the open-gate menu (408BF900). It lies
under the loader end of every other feature, so their shared loader edit is unchanged.
Used by features.compose; offline only.
"""
import struct

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from z8prores.a64 import Block
from z8prores.menu import Image
from z8prores.package import require

BASE = 0x40160000
CODE = 0x408BF900                                       # gap 408BF8F0..408C0000 is unused by every feature
PHOTO_SITE, PHOTO_SAVE, PHOTO_SKIP = 0x410DD26C, 0x410DD270, 0x410DD2E8
CUSTOM_SITE, CUSTOM_SAVE, CUSTOM_SKIP = 0x410DE0A8, 0x410DE0AC, 0x410DE0FC
COPY_SITE, COPY_SKIP = 0x410DDAFC, 0x410DDB68
CCOPY_SITE, CCOPY_SKIP = 0x410DE62C, 0x410DE680
EXT_SITE, EXT_SKIP = 0x410DD8BC, 0x410DD8E8
STOCK = {PHOTO_SITE: 0x360003F8,        # tbz w24,#0,410dd2e8   (w24 = save flag)
         PHOTO_SITE - 4: 0x11000415,    # add w21,w0,#1        (w21 = current bank slot; w23 = new bank 0..3)
         CUSTOM_SITE: 0x360002B7,       # tbz w23,#0,410de0fc   (w23 = save flag)
         CUSTOM_SITE - 4: 0x11000416,   # add w22,w0,#1        (w22 = current bank slot; w21 = new bank 0..3)
         COPY_SITE: 0x54000361,         # b.ne 410ddb68         (source slot != current slot)
         CCOPY_SITE: 0x540002A1,        # b.ne 410de680
         EXT_SITE: 0x36000176}          # tbz w22,#0,410dd8e8   (w22 = save flag)


def va(offset):
    return BASE + offset


def branch(at, to):
    d = to - at
    require(d % 4 == 0 and -(1 << 27) <= d < (1 << 27), 'Branch target out of range')
    return struct.pack('<I', 0x14000000 | ((d // 4) & 0x3FFFFFF))


def code():
    blk = Block(CODE)
    # photo: save only for a re-select of the current bank; w16 is dead on both paths
    blk.label('photo')
    blk.tbz_w(24, 0, 'photo_skip')
    blk.add_xi(16, 23, 1)
    blk.cmp_w(16, 21)
    blk.b_cond('ne', 'photo_skip')
    blk.b(PHOTO_SAVE)
    blk.label('photo_skip')
    blk.b(PHOTO_SKIP)
    # custom: same with w21 = new bank, w22 = current slot
    blk.label('custom')
    blk.tbz_w(23, 0, 'custom_skip')
    blk.add_xi(16, 21, 1)
    blk.cmp_w(16, 22)
    blk.b_cond('ne', 'custom_skip')
    blk.b(CUSTOM_SAVE)
    blk.label('custom_skip')
    blk.b(CUSTOM_SKIP)
    return blk


def build_main(data):
    """Return Image edits and review metadata; input is immutable MAIN without CRC."""
    img = Image(data)
    for at, word in STOCK.items():
        require(img.u32(at - BASE) == word, f'Unexpected stock bank code at {at:#x}')
    blk = code()
    raw = blk.bytes()
    require(CODE + len(raw) <= 0x408C0000, 'Locked-bank routine too large')
    img.put(CODE - BASE, raw, 'routine: save on re-select of the current bank only', expect_zero=True)
    for site, target, why in [
            (PHOTO_SITE, blk.labels['photo'], 'photo bank select: save gate -> routine'),
            (CUSTOM_SITE, blk.labels['custom'], 'custom settings bank select: save gate -> routine'),
            (COPY_SITE, COPY_SKIP, 'copy photo bank: never save slot 0 into the source'),
            (CCOPY_SITE, CCOPY_SKIP, 'copy custom settings bank: never save slot 0 into the source'),
            (EXT_SITE, EXT_SKIP, 'extended banks off: never save slot 0 into the current bank')]:
        img.put(site - BASE, branch(site, target), why, expect=struct.pack('<I', STOCK[site]))
    listing = blk.listing(Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN))
    return img, dict(prototype=True, routine=hex(CODE), labels={k: hex(v) for k, v in blk.labels.items()},
                     code=[dict(va=hex(x), word=w, text=t) for x, w, t in listing])
