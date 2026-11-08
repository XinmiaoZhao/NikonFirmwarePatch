#!/usr/bin/env python3
"""Calibrated tkhd display matrices for the video-orientation feature (T4).

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
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from z8vrotate import matrices

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


if __name__ == '__main__':
    unittest.main(verbosity=2)
