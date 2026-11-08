"""Calibrated QuickTime tkhd display matrices for the video-orientation unit.

Each constant is the exact 36 bytes written into a tkhd atom: nine 32-bit
big-endian words of a QuickTime display matrix in row-major order
``a b u / c d v / x y w``.  Words a-b-c-d are 16.16 fixed point, w is stored
as 2^30 (0x40000000), and a track point (x, y) in the y-down QuickTime
coordinate system is displayed as::

    x' = a*x + c*y + x_off
    y' = b*x + d*y + y_off

Enum-to-matrix mapping (consumed by the matrix hook, T5)
--------------------------------------------------------
The camera orientation enum at state+0x2500 maps to EXIF orientation values
through the firmware getter at 0x406e4824 (docs/t14-video-orientation-re.md
section 4)::

    enum 0 -> EXIF 1 (landscape, normal)  -> IDENTITY_MATRIX
    enum 1 -> EXIF 6 (rotate 90 deg CW)   -> ROTATE_90_CW_MATRIX
    enum 2 -> EXIF 8 (rotate 90 deg CCW)  -> ROTATE_90_CCW_MATRIX
    enum 3 -> EXIF 3 (rotated 180 deg)    -> ROTATE_180_MATRIX

EXIF 6 means "rotate the stored image 90 degrees clockwise to display it
upright"; EXIF 8 means 90 degrees counterclockwise.  The chosen matrices
perform exactly that rotation, so players (ffmpeg displaymatrix side data,
QuickTime, Premiere, Resolve, FCP, VLC) show portrait footage upright while
tkhd width/height keep the encoded (landscape) dimensions.

Evidence for the byte sequences and the direction assignment
------------------------------------------------------------
1. Real iPhone files, Internet Archive item img-8627_202408 (fetched
   2026-11-08, head range + local ffprobe):
   - IMG_8627.mov (sha256
     dee06ccf18fded278cfb3f6c02c0a0424dcc6ef4d4d341b0ebbd294151c9665f):
     Apple metadata says make=Apple, model=iPhone 11 Pro Max,
     software=17.5.1.  Encoded 1920x1080, tkhd
     matrix words ``00000000 00010000 00000000 ffff0000 00000000 00000000
     04380000 00000000 40000000``; ffprobe reports ``rotation=-90``.  The
     file's own timed-metadata track stores Apple's
     com.apple.quicktime.video-orientation sample 10 bytes
     ``0000000a 00000001 0006`` -> EXIF-style value 6.
   - IMG_8615.mov (same item): same rotation words, Apple value 6.
   - IMG_8624.mov (same item): identity words, Apple value 1.
   Apple therefore pairs first-party EXIF 6 <-> {a=0, b=+1, c=-1}, which
   pins enum 1 to the b=+1/c=-1 pattern.  The +0x04380000 word is x_off =
   1080.0 in 16.16 (the encoded track height): rotating 1920x1080 content
   90 deg CW maps x into [-1080, 0], and Apple shifts it back positive --
   a geometric signature that independently confirms the CW direction.
2. ffmpeg 8.0.1 (local reference round-trip): muxing with
   ``-display_rotation -90`` (the CLI option is "pure counter-clockwise
   rotation in degrees") writes exactly ROTATE_90_CW's words (zero
   translation), ``-display_rotation 90`` writes ROTATE_90_CCW's, and 180
   writes ROTATE_180's; ffprobe reports rotation -90/+90/-180
   respectively.  libavutil/display.c derives rotation as
   ``-atan2(b, a)`` in degrees and documents it as "the angle ... by which
   the transformation rotates the frame counterclockwise".
3. ExifTool (lib/Image/ExifTool/QuickTime.pm, GetRotationMatrix for
   "degrees of clockwise camera rotation"): builds
   ``cos sin 0 -sin cos 0 0 0 1``, i.e. 90 CW -> b=+1, c=-1 -- identical
   words, again with zero x/y offsets.
4. The mirror leg (enum 2 / EXIF 8) is pinned by the sign symmetry shared
   by all of the above implementations plus Apple's EXIF-6 anchor.  No
   fetched public sample of the second portrait direction was located, so
   the mirror is marked for the T11 on-camera verification round, which
   ffprobes both portrait grips.

Dual-candidate caveat: a swapped mapping (enum 1 <-> b=-1/c=+1) was the
alternative hypothesis; it is excluded by the Apple first-party pairing
and by the translation-sign geometry, not merely by majority vote.

Real files may add translation words (Apple adds x=+height); ffmpeg and
ExifTool write zero-translation rotation matrices and every player
normalises extents, so the injected matrices keep x=y=0 per the plan spec
(t14 section "implementation design").  The 36 bytes replace the whole
matrix; tkhd width/height stay at encoded size (iPhone-style convention).
"""

# enum 0 / EXIF 1: landscape normal.
IDENTITY_MATRIX = bytes.fromhex(
    '00010000' '00000000' '00000000'
    '00000000' '00010000' '00000000'
    '00000000' '00000000' '40000000'
)

# enum 1 / EXIF 6: rotate 90 degrees clockwise to display upright.
ROTATE_90_CW_MATRIX = bytes.fromhex(
    '00000000' '00010000' '00000000'
    'ffff0000' '00000000' '00000000'
    '00000000' '00000000' '40000000'
)

# enum 2 / EXIF 8: rotate 90 degrees counterclockwise to display upright.
ROTATE_90_CCW_MATRIX = bytes.fromhex(
    '00000000' 'ffff0000' '00000000'
    '00010000' '00000000' '00000000'
    '00000000' '00000000' '40000000'
)

# enum 3 / EXIF 3: upside down.
ROTATE_180_MATRIX = bytes.fromhex(
    'ffff0000' '00000000' '00000000'
    '00000000' 'ffff0000' '00000000'
    '00000000' '00000000' '40000000'
)

# Camera orientation enum (state+0x2500) -> 36-byte tkhd matrix.
ORIENT_TO_MATRIX = {
    0: IDENTITY_MATRIX,
    1: ROTATE_90_CW_MATRIX,
    2: ROTATE_90_CCW_MATRIX,
    3: ROTATE_180_MATRIX,
}
