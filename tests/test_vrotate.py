#!/usr/bin/env python3
"""Calibrated tkhd display matrices for the video-orientation feature (T4).

Plus T5 unit-skeleton tests: the classify mirror (gravity-vector pose
codes), the one-shot latch semantics, and -- when the stock firmware
fixture and an aarch64-capable clang are present -- compilation, linking and
patcher edit generation for the vrotate cave unit.

The expected byte strings below are pinned offline evidence, independent of
z8vrotate.matrices itself, so a regression in the module cannot also rewrite
the reference:

* Apple iPhone files hosted by the Internet Archive (see matrices.py for the
  full evidence chain): a portrait iPhone 11 Pro Max (iOS 17.5.1) recording
  carries the tkhd words ``00000000 00010000 00000000 ffff0000 00000000
  00000000 04380000 00000000 40000000`` together with Apple's own
  ``com.apple.quicktime.video-orientation`` value 6, while landscape siblings
  carry the identity words with the Apple value 1.
* ffmpeg 8.0.1 reference round-trip: ``-display_rotation {-90,90,180}``
  produces exactly these words (minus the translation word Apple adds).
"""
import struct
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from z8vrotate import matrices

# Stock EG addresses used by the unit tests (BASE = 0x40160000).
EG_BASE = 0x40160000
FIRMWARE = ROOT / 'firmware' / 'Z_8_0311.bin'
# The matrix hook replaces the stock `bl 0x40ce3fdc` at 0x40cefd60 (t3 report).
MATRIX_SITE, MATRIX_STOCK_WORD = 0x40cefd60, 0x97FFD09F
# The latch hook replaces the first 8 bytes of the 0x40d17728 marshaling
# trampoline: mov x8,#0x6f0 ; movk x8,#0x31c,lsl#16 (t2 report).
LATCH_SITE = 0x40d17728
LATCH_STOCK = bytes.fromhex('08de80d28863a0f2')
CAVE_BASE, CAVE_LIMIT = 0x40A20000, 0x40A22000


def _clang():
    """Locate the maintainer clang for the aarch64 unit build, or None."""
    import shutil
    found = shutil.which('clang')
    if found:
        return found
    local = ROOT.parent / 'tools' / 'llvm-19.1.7' / 'bin' / 'clang'
    return str(local) if local.is_file() else None

# Nine 32-bit big-endian 16.16 words per matrix, in file order:
# a b u / c d v / x y w.  Reference byte sequences from the calibration above.
IDENTITY = bytes.fromhex(
    '00010000' '00000000' '00000000'
    '00000000' '00010000' '00000000'
    '00000000' '00000000' '40000000'
)
# Enum 1 (EXIF 6, "rotate 90 degrees CW to display upright"): b=+1, c=-1.
# Same rotation part as the iPhone portrait sample; translation zeroed like
# ffmpeg's movenc and ExifTool writers.
ROTATE_90_CW = bytes.fromhex(
    '00000000' '00010000' '00000000'
    'ffff0000' '00000000' '00000000'
    '00000000' '00000000' '40000000'
)
# Enum 2 (EXIF 8, "rotate 90 degrees CCW"): exact sign mirror of the above.
ROTATE_90_CCW = bytes.fromhex(
    '00000000' 'ffff0000' '00000000'
    '00010000' '00000000' '00000000'
    '00000000' '00000000' '40000000'
)
# Enum 3 (EXIF 3, upside down).
ROTATE_180 = bytes.fromhex(
    'ffff0000' '00000000' '00000000'
    '00000000' 'ffff0000' '00000000'
    '00000000' '00000000' '40000000'
)


class MatrixTests(unittest.TestCase):
    def test_matrices(self):
        """Four constants equal the documented 36-byte tkhd sequences."""
        self.assertEqual(matrices.IDENTITY_MATRIX, IDENTITY)
        self.assertEqual(matrices.ROTATE_90_CW_MATRIX, ROTATE_90_CW)
        self.assertEqual(matrices.ROTATE_90_CCW_MATRIX, ROTATE_90_CCW)
        self.assertEqual(matrices.ROTATE_180_MATRIX, ROTATE_180)
        for name in ('IDENTITY_MATRIX', 'ROTATE_90_CW_MATRIX',
                     'ROTATE_90_CCW_MATRIX', 'ROTATE_180_MATRIX'):
            self.assertEqual(len(getattr(matrices, name)), 36)

    def test_orient_to_matrix_mapping(self):
        """Orientation enum 0..3 maps to the calibrated matrices."""
        self.assertEqual(sorted(matrices.ORIENT_TO_MATRIX), [0, 1, 2, 3])
        self.assertIs(matrices.ORIENT_TO_MATRIX[0], matrices.IDENTITY_MATRIX)
        self.assertIs(matrices.ORIENT_TO_MATRIX[1], matrices.ROTATE_90_CW_MATRIX)
        self.assertIs(matrices.ORIENT_TO_MATRIX[2], matrices.ROTATE_90_CCW_MATRIX)
        self.assertIs(matrices.ORIENT_TO_MATRIX[3], matrices.ROTATE_180_MATRIX)


class ClassifyMirrorTests(unittest.TestCase):
    """Python mirror of the vr_classify cave routine (T1 ruling, T5).

    The latch hook classifies the normalised gravity vector (f32 x3 at
    0x0A02E560E0) itself; z8vrotate.patcher.classify mirrors the assembly
    algorithm (sign-bit strip, unsigned magnitude compare, argmax with the
    x > y > z tie-break, cave threshold, axis*2+sign table lookup) against
    the same cave constants.  Byte-level agreement with the assembled unit
    is exercised by the T10 emulation round.
    """

    def test_six_canonical_vectors(self):
        """The T1 report's six single-axis vectors map to pose codes."""
        from z8vrotate import patcher
        canonical = (
            ((0.0, 0.0, 1.0), patcher.AXIS_CODES[4]),   # level rest (T1 anchor)
            ((1.0, 0.0, 0.0), patcher.AXIS_CODES[0]),   # X+
            ((-1.0, 0.0, 0.0), patcher.AXIS_CODES[1]),   # X-
            ((0.0, 1.0, 0.0), patcher.AXIS_CODES[2]),   # Y+
            ((0.0, -1.0, 0.0), patcher.AXIS_CODES[3]),   # Y-
            ((0.0, 0.0, -1.0), patcher.AXIS_CODES[5]),   # Z- (upside down)
        )
        for vector, expected in canonical:
            self.assertEqual(patcher.classify(1, *vector), expected, vector)
        # The shipped assignment is the documented hypothesis from the T1
        # boot anchor (+Z = level landscape); a T11 calibration flip must
        # change these bytes deliberately.
        self.assertEqual(patcher.AXIS_CODES, bytes((1, 2, 0, 0, 0, 3)))

    def test_threshold_and_argmax(self):
        """Dominant-axis argmax plus the 0.70 threshold gate."""
        from z8vrotate import patcher
        # Every axis below 0.70 after normalisation: no dominant axis.
        self.assertEqual(patcher.classify(1, 0.58, 0.58, 0.58), 0)
        # 45-degree edge: BOTH X and Y stay at/above 0.70 (bits 0x3f33879c
        # and 0x3f360eee vs threshold 0x3f333333) while Y dominates -- a
        # first-component-above-threshold implementation would wrongly
        # return the X+ code 1; the correct answer is the Y+ code 0.
        self.assertEqual(patcher.classify(1, 0.71, 0.72, 0.05), patcher.AXIS_CODES[2])
        # Mirror of the asm x-beats-y tie-break: equal components pick X.
        self.assertEqual(patcher.classify(1, 0.71, 0.71, 0.02), patcher.AXIS_CODES[0])
        # Zero vector: nothing dominant, no mark.
        self.assertEqual(patcher.classify(1, 0.0, 0.0, 0.0), 0)
        # A NaN component has magnitude bits above every finite threshold;
        # the mirror (like the asm) then classifies by that axis, so the
        # result is still a valid code 0..3 rather than a crash.
        self.assertIn(patcher.classify(1, float('nan'), 0.0, 0.0), range(4))

    def test_enable_gate(self):
        """The sensor-subsystem gate word must read 1 for any mark."""
        from z8vrotate import patcher
        for gate in (0, 2, 0xFFFFFFFF):
            self.assertEqual(patcher.classify(gate, 0.0, 0.0, -1.0), 0, hex(gate))


class OneShotLatchTests(unittest.TestCase):
    """One-shot latch hygiene (review carry-item T3-F1): read-and-clear.

    Playback/transfer-side finalises reuse the matrix site
    (0x4034412c/0x403494d8 families -> movie_finalize_stop), so the matrix
    hook must consume the latch byte on every pass; a stale portrait latch
    must never leak into a later non-recording finalise.
    """

    def test_stale_latch_cleared(self):
        from z8vrotate import patcher
        # Portrait recording opened: the latch hook stores the pose code.
        latch = patcher.classify(1, 1.0, 0.0, 0.0)
        self.assertEqual(latch, 1)
        # Stop-recording finalise: the matrix hook consumes and clears.
        used, latch = patcher.matrix_decision(latch, enable=1)
        self.assertEqual(used, matrices.ROTATE_90_CW_MATRIX)
        self.assertEqual(latch, 0)
        # A later playback-side finalise through the same site sees identity.
        used, latch = patcher.matrix_decision(latch, enable=1)
        self.assertIsNone(used)
        self.assertEqual(latch, 0)

    def test_read_and_clear_always(self):
        from z8vrotate import patcher
        # An invalid/stale value is consumed too, not just valid codes.
        for stale in (0, 4, 0xFF):
            used, latch = patcher.matrix_decision(stale, enable=1)
            self.assertIsNone(used, stale)
            self.assertEqual(latch, 0, stale)
        # Feature disabled: no matrix, but the latch is still cleared so a
        # later re-enable cannot emit a pose captured while disabled.
        used, latch = patcher.matrix_decision(3, enable=0)
        self.assertIsNone(used)
        self.assertEqual(latch, 0)


class UnitBuildTests(unittest.TestCase):
    """Compile, link and patch-generate the vrotate unit (T5 Step 1).

    Needs the stock firmware fixture plus clang; skipped otherwise so the
    suite stays green on machines without them.
    """

    def test_unit_builds(self):
        from z8vrotate import patcher
        from z8patch import compiled
        from z8prores.package import Package
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        compiler = _clang()
        if not compiler:
            self.skipTest('no clang for the aarch64 unit build')
        pkg = Package(FIRMWARE.read_bytes())
        eg = pkg.eg
        code, observed = compiled.compile_unit('vrotate', compiler)
        self.assertEqual(compiled.SPECS['vrotate']['asm_base'], CAVE_BASE)
        self.assertLessEqual(CAVE_BASE + len(code), CAVE_LIMIT)   # cave bounds
        entries = {name: int(sym['va'], 16) for name, sym in observed['symbols'].items()}
        for name in ('vr_matrix_hook', 'vr_latch_hook', 'vr_latch_displaced', 'vr_latch',
                     'vr_enable', 'vr_sentinel', 'vr_matrices', 'vr_axis_codes', 'vr_threshold'):
            self.assertIn(name, entries, name)
            self.assertTrue(CAVE_BASE <= entries[name] < CAVE_LIMIT, name)
        # Stock gate bytes (t2/t3 reports) are present in the fixture.
        self.assertEqual(eg[MATRIX_SITE - EG_BASE:MATRIX_SITE - EG_BASE + 4],
                         struct.pack('<I', MATRIX_STOCK_WORD))
        self.assertEqual(eg[LATCH_SITE - EG_BASE:LATCH_SITE - EG_BASE + 8], LATCH_STOCK)
        # The displaced pair replayed in the cave equals the stock bytes.
        at = entries['vr_latch_displaced'] - CAVE_BASE
        self.assertEqual(bytes(code[at:at + 8]), LATCH_STOCK)
        # Skeleton patch generation applies to the stock image: the two
        # expect-byte gates and the zero-cave check all pass.
        img, meta = patcher.build_main(eg, code, entries)
        self.assertEqual(len(img.edits), 3)
        sites = sorted(e['offset'] + EG_BASE for e in img.edits)
        self.assertEqual(sites, sorted((MATRIX_SITE, LATCH_SITE, CAVE_BASE)))
        # Offline disassembly (capstone) of the edited sites and the unit.
        from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
        md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
        edited = [bytes(img.edits[i]['new']) for i in range(len(img.edits))]
        by_va = {e['offset'] + EG_BASE: bytes(e['new']) for e in img.edits}
        bl = next(md.disasm(by_va[MATRIX_SITE], MATRIX_SITE))
        self.assertEqual(bl.mnemonic, 'bl')
        self.assertEqual(int(bl.op_str.removeprefix('#'), 16), entries['vr_matrix_hook'])
        b = next(md.disasm(by_va[LATCH_SITE], LATCH_SITE))
        self.assertEqual(b.mnemonic, 'b')
        self.assertEqual(int(b.op_str.removeprefix('#'), 16), entries['vr_latch_hook'])
        self.assertEqual(by_va[LATCH_SITE][4:], b'\x1f\x20\x03\xd5')    # trailing nop
        # Inside the unit: the matrix hook tail-branches to write_bytes and
        # only ever redirects x1; the latch hook gates on w1 and resumes at
        # 0x40d17730.
        def region(start, end):
            return list(md.disasm(bytes(code[start - CAVE_BASE:end - CAVE_BASE]), start))
        matrix_ins = region(entries['vr_matrix_hook'], entries['vr_latch_hook'])
        self.assertTrue(any(i.mnemonic == 'umaddl' and i.op_str.startswith('x1,')
                            for i in matrix_ins))
        self.assertTrue(any(i.mnemonic == 'b' and i.op_str == '#0x40ce3fdc'
                            for i in matrix_ins))
        latch_ins = region(entries['vr_latch_hook'], CAVE_BASE + len(code))
        self.assertTrue(any(i.mnemonic == 'cmp' and i.op_str == 'w1, #1'
                            for i in latch_ins))
        self.assertTrue(any(i.mnemonic == 'b' and i.op_str == '#0x40d17730'
                            for i in latch_ins))
        # Negative gates: stock bytes that differ must fail the build.
        for bad_site in (MATRIX_SITE, LATCH_SITE + 4):
            bad = bytearray(eg)
            bad[bad_site - EG_BASE] ^= 1
            with self.assertRaises(ValueError, msg=hex(bad_site)):
                patcher.build_main(bytes(bad), code, entries)


if __name__ == '__main__':
    unittest.main(verbosity=2)
