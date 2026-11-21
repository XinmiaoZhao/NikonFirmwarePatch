"""The single condition-entry writer for video recording and still imaging together."""
import struct
from .image import BASE, branch
from z8prores.package import require

CONDITION = 0x403A036C
DISPATCH = 0x40B71A00


def branch_target(edit):
    word, = struct.unpack('<I',edit['new'])
    require(word >> 26 == 0b000101, 'Condition adapter must tail-branch')
    imm = word & 0x3ffffff
    if imm & 0x2000000:
        imm -= 1 << 26
    return BASE + edit['offset'] + 4*imm


def emit_condition(image, targets):
    # E4's sentinel -> its original handler; all other numbers -> HEIF, whose
    # ordinary fallback replays the stock prologue once and resumes at +4.
    require(set(targets)=={'opengate-nraw','sdr-heif'},'Missing shared condition provider')
    code = struct.pack('<4I', 0x52800010 | (0x3A32<<5), 0x72A00010 | (0x0E2E<<5),
                       0x6B10001F, 0x54000041)  # cmp w0,w16; b.ne .+8
    code += branch(DISPATCH+16,targets['opengate-nraw'])
    code += branch(DISPATCH+20,targets['sdr-heif'])
    image.put(DISPATCH-BASE,code,'joint E4 and still HEIF menu conditions',expect_zero=True)
    image.put(CONDITION-BASE,branch(CONDITION,DISPATCH),'joint condition entry',expect=bytes.fromhex('f963bca9'))
