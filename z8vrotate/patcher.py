"""vrotate: pose-latched tkhd display matrices for movies (T5 skeleton).

Builds the two hooks from z8vrotate/src/hooks.S into the stock EG:

* 0x40cefd60: the single video-track tkhd matrix copy (`bl 0x40ce3fdc`)
  becomes `bl vr_matrix_hook`; the hook redirects x1 to a cave matrix when
  the one-shot latch holds a valid pose code, otherwise passes x1 through.
* 0x40d17728: the recording-side file open marshaling trampoline entry
  becomes `b vr_latch_hook` + nop; on the main-movie write open (w1 == 1)
  the hook classifies the gravity vector and latches the pose code.

Menu and bank-storage wiring are T6/T7; this module only emits the unit and
the two gated edits.
"""
import struct

from z8patch.image import Image, BASE, branch
from z8prores.package import require

from . import matrices

CODE_AT, CODE_END = 0x40A20000, 0x40A22000
# Matrix hook: single video-track tkhd matrix copy site (t3 report).
MATRIX_SITE, WRITE_BYTES, MATRIX_STOCK_WORD = 0x40cefd60, 0x40ce3fdc, 0x97FFD09F
# Latch hook: recording-side file open marshaling trampoline entry (t2 report).
LATCH_SITE, LATCH_RESUME = 0x40d17728, 0x40d17730
LATCH_STOCK = bytes.fromhex('08de80d28863a0f2')
# T1 anchors: sensor-subsystem gate word and normalised gravity vector f32 x3.
ORIENT_VALID, GRAVITY_VEC = 0x0A02E56018, 0x0A02E560E0
THRESHOLD_BITS = 0x3F333333        # IEEE754 bits of 0.70f (dominant-axis gate)
SENTINEL_VALUE = 0x5A
NOP = struct.pack('<I', 0xD503201F)

# [axis*2 + sign] -> own pose code (hooks.S header derives the assignment):
# +X=1 (90 deg CW roll), -X=2 (90 deg CCW), +Y/-Y=0 (lens-axis family, no
# mark), +Z=0 (level landscape, the T1 boot anchor), -Z=3 (upside down).
# T11 on-camera calibration flips individual bytes only, never code.
AXIS_CODES = bytes((1, 2, 0, 0, 0, 3))

# Codes 1..3 only: code 0 / invalid is a passthrough, the stock identity
# blob already on the stack covers it.  Big-endian 16.16 words as written.
VR_MATRICES = (matrices.ORIENT_TO_MATRIX[1] + matrices.ORIENT_TO_MATRIX[2]
               + matrices.ORIENT_TO_MATRIX[3])


def classify(gate, x, y, z):
    """Mirror of the vr_classify cave routine; returns the pose code 0..3.

    Same algorithm and cave constants as the assembled unit: gate word must
    be 1, sign bits stripped, magnitudes compared as unsigned float bits,
    argmax with the x-beats-y-beats-z tie-break, dominant axis at or above
    THRESHOLD_BITS, code = AXIS_CODES[axis*2 + sign].  Byte-level agreement
    with the unit is asserted by the T10 emulation round.
    """
    if gate != 1:
        return 0
    words = [struct.unpack('<I', struct.pack('<f', c))[0] for c in (x, y, z)]
    signs = [w >> 31 for w in words]
    mags = [w & 0x7FFFFFFF for w in words]
    axis = 0 if mags[0] >= mags[1] else 1
    if mags[2] > mags[axis]:
        axis = 2
    if mags[axis] < THRESHOLD_BITS:
        return 0
    return AXIS_CODES[axis * 2 + signs[axis]]


def matrix_decision(latch, enable=1):
    """Mirror of vr_matrix_hook's one-shot read-and-clear decision.

    Returns (matrix or None, new_latch): the latch is consumed whatever it
    holds, so playback-side finalizes reusing 0x40cefd60 can never emit a
    stale pose; None means the hook passes the stock identity x1 through.
    """
    code, latch = latch, 0
    if enable and 1 <= code <= 3:
        return VR_MATRICES[(code - 1) * 36:code * 36], latch
    return None, latch


def build_main(eg, code, entries):
    """Emit the vrotate unit and its two gated edits (T5 skeleton)."""
    require(len(VR_MATRICES) == 108 and len(AXIS_CODES) == 6, 'vrotate cave constants')
    require(not any(eg[CODE_AT - BASE:CODE_END - BASE]), 'vrotate cave not free in stock image')
    img = Image(eg)
    code = bytearray(code)

    def fill(name, data):
        at = entries[name] - CODE_AT
        require(code[at:at + len(data)] == bytes(len(data)), 'vrotate fill not zero: ' + name)
        code[at:at + len(data)] = data

    fill('vr_matrices', VR_MATRICES)
    fill('vr_axis_codes', AXIS_CODES)
    fill('vr_threshold', struct.pack('<I', THRESHOLD_BITS))
    fill('vr_latch', b'\x00')
    fill('vr_enable', b'\x01')
    fill('vr_sentinel', b'\x00')
    require(CODE_AT + len(code) <= CODE_END, 'vrotate code capacity')
    img.put(MATRIX_SITE, branch(MATRIX_SITE, entries['vr_matrix_hook'], link=True),
            'movie tkhd matrix copy: bl 0x40ce3fdc -> bl vr_matrix_hook',
            expect=struct.pack('<I', MATRIX_STOCK_WORD))
    img.put(LATCH_SITE, branch(LATCH_SITE, entries['vr_latch_hook']) + NOP,
            'record file open trampoline: mov/movk x8 pair -> b vr_latch_hook + nop',
            expect=LATCH_STOCK)
    img.put(CODE_AT, code, 'vrotate unit: matrix hook, latch hook, classifier, cave constants',
            expect_zero=True)
    return img, dict(entries={k: hex(v) for k, v in entries.items()}, code_bytes=len(code),
                     cave=[hex(CODE_AT), hex(CODE_AT + len(code))],
                     axis_codes=list(AXIS_CODES), threshold=hex(THRESHOLD_BITS),
                     sentinel=hex(SENTINEL_VALUE), matrix_bytes=len(VR_MATRICES))
