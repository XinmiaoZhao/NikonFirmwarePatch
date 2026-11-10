"""Calibrated QuickTime tkhd display matrices for the video-orientation unit.

Each constant is the exact 36 bytes written into a tkhd atom: nine 32-bit
big-endian words of a QuickTime display matrix in row-major order
``a b u / c d v / x y w``.  Words a-b-c-d are 16.16 fixed point, w is stored
as 2^30 (0x40000000), and a track point (x, y) in the y-down QuickTime
coordinate system is displayed as::

    x' = a*x + c*y + x_off
    y' = b*x + d*y + y_off

Own pose code -> matrix (consumed by the matrix hook)
-------------------------------------------------------
The keys 0..3 of ORIENT_TO_MATRIX are the patch unit's own pose codes, not
the firmware enum.  The latch hook (z8vrotate/src/hooks.S) classifies the
normalised gravity vector (f32 x3 at 0x0A02E560E0, published ~1 kHz by the
sensor fusion task) at recording start, because
the stock orientation enum is pinned to 3 by the all-zero factory calibration
in emulation and the EXIF ctx+0x2500 lane is capture-scoped and unusable as
an anchor::

    0 = landscape / no dominant axis / invalid -> IDENTITY_MATRIX (passthrough)
    1 = camera rolled 90 deg CW (image needs 90 deg CW to display upright)
    2 = camera rolled 90 deg CCW
    3 = upside down (180 deg)

Code 1 keeps the matrix calibrated against Apple's first-party
EXIF 6 <-> {a=0, b=+1, c=-1} pairing; codes 2/3 follow by the sign symmetry
of every reference implementation.  For the record, the firmware's own
orientation enum -> EXIF getter lane table at 0x406e4824 decodes to
{0 -> 1, 1 -> 8, 2 -> 6, 3 -> 1}, verified at the instruction level
(lane3 is 1 and enum 3 falls back to no rotation) -- but the enum is no
longer consumed, so that table is reference material only.

Axis assignment (which gravity-vector direction means which pose): it follows
on-camera evidence and is not derived here.  The historical derivation
assumed a level camera reading (0, 0, +1) with +Z the baseplate normal:
+Z = code 0, -Z = code 3 (rolled 180), +X = code 1 (rolled 90 deg CW as seen
from behind the camera), -X = code 2, and +/-Y (assumed parallel to the lens
axis) carries no roll code.  This assignment cannot be pinned in emulation
and ships as the state-window constant vr_axis_codes (z8vrotate/patcher.py
AXIS_CODES); the on-camera calibration flips individual bytes only, as
documented in the hooks.S header.

EXIF 6 means "rotate the stored image 90 degrees clockwise to display it
upright"; EXIF 8 means 90 degrees counterclockwise.  The chosen matrices
perform exactly that rotation, so players (ffmpeg displaymatrix side data,
QuickTime, Premiere, Resolve, FCP, VLC) show portrait footage upright while
tkhd width/height keep the encoded (landscape) dimensions.

Evidence for the byte sequences and the direction assignment
------------------------------------------------------------
1. Real iPhone files, Internet Archive item img-8627_202408 (fetched
   head range + local ffprobe):
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
   pins pose code 1 to the b=+1/c=-1 pattern.  The +0x04380000 word is x_off =
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
4. The code-2 matrix is pinned by the sign symmetry shared
   by all of the above implementations plus Apple's EXIF-6 anchor.  No
   fetched public sample of the second portrait direction was located, so
   any residual mismatch is marked for the on-camera verification round, which
   ffprobes both portrait grips.

Dual-candidate caveat: a swapped mapping (code 1 <-> b=-1/c=+1) was the
alternative hypothesis; it is excluded by the Apple first-party pairing
and by the translation-sign geometry, not merely by majority vote.

Real files may add translation words (Apple adds x=+height); ffmpeg and
ExifTool write zero-translation rotation matrices and every player
normalises extents, so the injected matrices keep x=y=0 per the plan spec
(the design notes).  The 36 bytes replace the whole
matrix; tkhd width/height stay at encoded size (iPhone-style convention).
"""

# Pose code 0: landscape normal (passthrough; the stock identity blob covers it).
IDENTITY_MATRIX = bytes.fromhex(
    '00010000' '00000000' '00000000'
    '00000000' '00010000' '00000000'
    '00000000' '00000000' '40000000'
)

# Pose code 1: image needs 90 deg clockwise rotation to display upright
# (calibrated against Apple's first-party EXIF-6 pairing).
ROTATE_90_CW_MATRIX = bytes.fromhex(
    '00000000' '00010000' '00000000'
    'ffff0000' '00000000' '00000000'
    '00000000' '00000000' '40000000'
)

# Pose code 2: image needs 90 deg counterclockwise rotation to display upright.
ROTATE_90_CCW_MATRIX = bytes.fromhex(
    '00000000' 'ffff0000' '00000000'
    '00010000' '00000000' '00000000'
    '00000000' '00000000' '40000000'
)

# Pose code 3: upside down (180 deg).
ROTATE_180_MATRIX = bytes.fromhex(
    'ffff0000' '00000000' '00000000'
    '00000000' 'ffff0000' '00000000'
    '00000000' '00000000' '40000000'
)

# Own pose code (gravity-vector classification, see above) -> 36-byte tkhd
# matrix.  The state-window table vr_matrices carries only codes 1..3;
# code 0 is the passthrough identity.
ORIENT_TO_MATRIX = {
    0: IDENTITY_MATRIX,
    1: ROTATE_90_CW_MATRIX,
    2: ROTATE_90_CCW_MATRIX,
    3: ROTATE_180_MATRIX,
}
