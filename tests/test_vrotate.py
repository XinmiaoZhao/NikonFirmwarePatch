#!/usr/bin/env python3
"""Calibrated tkhd display matrices for the video-orientation feature (T4).

Plus T5 unit tests (classify mirror, one-shot latch, unit build), the
T6 menu-row tests (the 36-language title table, the 0x2FC0 transition-table
clone, the z8patch/shared.py extensions) and -- when the stock firmware
fixture and an aarch64-capable clang are present -- compilation, linking
and patcher edit generation for the vrotate cave unit with its synthesized
inline-toggle menu row.

T7 adds the per-bank storage tests: the pure-Python default-on mirror
(first-boot sentinel init, idempotence, user-off preservation), the value
byte wiring (row toggle and matrix hook reference the active DS record
byte; the T6 cave vr_value/vr_enable bytes are retired), and the Step-0
candidate-byte evidence encoded as test data (pinned bank-record addresses
plus a fresh writer scan over the stock image, so a firmware change that
touches the record bytes fails loudly).

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
CAVE_BASE, CAVE_LIMIT = 0x40A08000, 0x40A10000

# A+ state window (2026-11-09 vrotate-fix t1 report, four-leg zero-writer
# census): the five unit data labels moved out of the read-only cave into a
# 256 B window of the boot-loaded data mirror segment.  RAM window and its
# EG image offsets below are pinned literals, independent of the patcher.
VR_STATE_VA, VR_STATE_END = 0xA0281A800, 0xA0281A900
VR_STATE_IMG_OFF, VR_STATE_SIZE = 0x4B25800, 0x100
# Frozen window layout (facts.state_window in the build facts):
VR_MATRICES_OFF, VR_THRESHOLD_OFF = 0x00, 0x6C
VR_AXIS_CODES_OFF, VR_LATCH_OFF, VR_SENTINEL_OFF = 0x70, 0x76, 0x77
VR_MAGIC_OFF, VR_MAGIC = 0xFF, 0xA5

# T2b (2026-11-09 user ruling): the row-events clone lives at a patcher-
# constant fixed sub-window of the cave (the z8h265 MENU_AT form), not at an
# organic in-unit slot behind .org padding -- unit growth is decoupled from
# the frozen transition-pointer recipe rows.  4K-aligned, inside the cave,
# stock zero; table body 44x32 B incl. the 0x3BB terminator.
VR_EVENTS_AT, VR_EVENTS_SIZE = 0x40A09000, 44 * 32
VR_EVENTS_END = VR_EVENTS_AT + VR_EVENTS_SIZE


# The SPECS-declared unit assembly sources at the A1 freeze (14 files
# across seven folders; pinned independently of SPECS so a registry edit
# cannot silently reshape the D1 scan list).
UNIT_ASM_SOURCE_LIST = [
    'z8anamorphic/src/hooks.S',
    'z8h265/src/hooks.S',
    'z8log/src/hooks.S',
    'z8opengate/src/d10_hooks.S',
    'z8opengate/src/d5_hooks.S',
    'z8opengate/src/d6_hooks.S',
    'z8opengate/src/d7_hooks.S',
    'z8opengate/src/d8_hooks.S',
    'z8opengate/src/d9_hooks.S',
    'z8opengate/src/menu_repair_hooks.S',
    'z8opengate/src/ui_hooks.S',
    'z8patch/src/shared.S',
    'z8quality/src/hooks.S',
    'z8vrotate/src/hooks.S',
]


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
    x > y > z tie-break, state-window threshold, axis*2+sign table lookup)
    against the same state-window constants.  Byte-level agreement with
    the assembled unit is exercised by the T10 emulation round.
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
        # 45-degree edge: BOTH X and Y stay at/above 0.70 (float32 bits of 0.71 and
        # 0.72 are 0x3F35C28F and 0x3F3851EB, both above the 0x3F333333
        # threshold) while Y dominates -- a
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


class TranslationTests(unittest.TestCase):
    """36-language title table for the vrotate row (T6).

    The table is the user-confirmed verbatim baseline of 2026-11-08
    (docs/t14-video-orientation-re.md §7 in the outer repo); it descends
    from the official id 2458 "Record camera orientation" translations
    with each language's video word from id 2214, and z8vrotate/
    translations.py documents the derivation plus the confirmed-table
    overrides and carries the frozen-table fingerprint.
    """

    def test_spec_baseline_verbatim(self):
        """All 36 titles equal the user-confirmed table verbatim.

        The expected strings below are transcribed from docs/
        t14-video-orientation-re.md §7 "用户确认的 36 语言行标题表"
        (outer repo, 2026-11-08 session confirmation) as literal test
        data; any deviation from that table is a spec defect.  Slot 34
        (Arabic) must carry no trailing right-to-left mark.
        """
        from z8vrotate import translations
        confirmed = (
            '動画の縦横位置情報の記録',            # 0  ja
            'Record video orientation',           # 1  en
            'Video-Ausrichtung speichern',        # 2  de
            'Enreg. orientation vidéo',           # 3  fr
            'Grabar orientación vídeo',           # 4  es
            'Registra orient. video',             # 5  it
            'Spara filmorientering',              # 6  sv
            'Videorichting vastleggen',           # 7  nl
            '记录视频方向',                        # 8  zh-CN
            '記錄短片方向',                        # 9  zh-TW
            '동영상 방향 기록',                    # 10 ko
            'Ориентация видео',                   # 11 ru
            'บันทึกมุมวิดีโอ',                   # 12 th
            'Rekam orientasi film',               # 13 id
            'Gravar orientação do vídeo',         # 14 pt
            'Rejestruj orientację video',         # 15 pl
            'Tallenna videon suunta',             # 16 fi
            'Optag videoretning',                 # 17 da
            'Registrer filmretning',              # 18 no
            'Záznam orientace videa',             # 19 cs
            'Video yönünü kaydet',                # 20 tr
            'Video tájolásának rögzítése',        # 21 hu
            'Καταγρ. προσανατ. video',            # 22 el
            'Înregistrare orientare video',       # 23 ro
            'Зберігати орієнт. відео',            # 24 uk
            '動画の縦横位置情報の記録',            # 25 ja fallback
            '動画の縦横位置情報の記録',            # 26 ja fallback
            'वीडियो समन्वयन रिकॉर्ड करें',          # 27 hi
            '動画の縦横位置情報の記録',            # 28 ja fallback
            '動画の縦横位置情報の記録',            # 29 ja fallback
            '動画の縦横位置情報の記録',            # 30 ja fallback
            '動画の縦横位置情報の記録',            # 31 ja fallback
            'Запис ориент. на видеото',           # 32 bg
            'Smer snimanja videa',                # 33 hr
            'تسجيل اتجاه الفيديو',                 # 34 ar (no trailing RLM)
            '動画の縦横位置情報の記録',            # 35 ja fallback
        )
        titles = translations.TITLES
        self.assertEqual(len(confirmed), 36)
        self.assertEqual(len(titles), 36)
        for index, (title, expected) in enumerate(zip(titles, confirmed)):
            self.assertEqual(title, expected, (index, title, expected))
        # No hidden control or bidirectional-format characters anywhere.
        import unicodedata
        for index, title in enumerate(titles):
            self.assertNotIn(
                [c for c in title if unicodedata.category(c) in ('Cf', 'Cc')],
                (index, title))

    def test_lengths_fallbacks_and_fingerprint(self):
        """Every title fits the row, fallback slots are Japanese, no drift."""
        import hashlib
        from z8vrotate import translations
        for index, title in enumerate(translations.TITLES):
            self.assertGreater(len(title), 0, index)
            self.assertLessEqual(len(title), 32, (index, title))
        for index in translations.JAPANESE_SLOTS:
            self.assertEqual(translations.TITLES[index], translations.TITLES[0], index)
        digest = hashlib.sha256('\n'.join(translations.TITLES).encode()).hexdigest()
        self.assertEqual(digest, translations.FINGERPRINT)


class RowEventsTests(unittest.TestCase):
    """Transition-table clone of the 0x2FC0 template row (T6 Step 0).

    The stock video-menu row for the audio attenuator (item 0x2FC0, row
    class 0x20901005) carries its per-row transition table at 0x43C33EF0:
    44 records of (event, action, guard, target) ending in the 0x3BB
    terminator.  OK (0x286), 0x28B and touch (0x2AE) all dispatch to the
    stock inline-toggle action 0x405707D4 (flip DS 0x700123C via
    0x405121EC/0x410D61D0, then the immediate focused-row redraw
    0x40512068).  The clone keeps every stock record verbatim and moves
    only those three actions into the cave.
    """

    def test_template_row_and_table(self):
        from z8vrotate import patcher
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        from z8prores.package import Package
        eg = Package(FIRMWARE.read_bytes()).eg
        template, pointer = patcher.menu_row(eg)
        self.assertEqual(template, patcher.ATTEN_ROW)
        self.assertEqual(pointer, 0x43C33EF0)
        # The stock 0x2FC0 row is one of the 44 stock video rows and its
        # class word matches every other inline On/Off row.
        self.assertEqual(template[4], 0x20901005)
        self.assertEqual(template[6], 0x2FC0)

    def test_row_events_clone(self):
        from z8vrotate import patcher
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        import struct
        from z8prores.package import Package
        eg = Package(FIRMWARE.read_bytes()).eg
        template, pointer = patcher.menu_row(eg)
        hook = CAVE_BASE + 0x1080              # arbitrary in-cave stand-in (never emitted)
        table = patcher.row_events(eg, pointer, hook)
        self.assertEqual(len(table), 32 * 44)
        seen = []
        # 0x43C33EF0 is a plain ROM VA: EG offset = VA - EG_BASE.
        data_off = pointer - EG_BASE
        for i in range(44):
            record = struct.unpack_from('<4Q', table, 32 * i)
            if record[1] == hook:
                seen.append(record[0])
                self.assertNotEqual(record[0], 0x3BB)
                continue
            # Every non-toggle record is byte-identical to stock.
            self.assertEqual(record, struct.unpack_from('<4Q', eg, data_off + 32 * i), i)
        self.assertEqual(tuple(seen), patcher.TOGGLE_EVENTS)
        # The terminator record stays last and untouched.
        self.assertEqual(struct.unpack_from('<Q', table, 32 * 43)[0], 0x3BB)


class SharedExtensionTests(unittest.TestCase):
    """z8patch/shared.py extensions for the fifth feature group (T6).

    STRING_IDS gains 'vrotate': (3225, 1); the shared string table only
    grows when the vrotate provider is actually composed, so every existing
    combination keeps its reviewed recipe bytes; VideoMenu.emit inserts the
    synthesized row 0x315B immediately before the stock image-area row
    0x30A6; CONFIG gains the fifth row-callback slot at +0x28, written only
    for video-orientation compositions until the recipe freeze (T8).
    """

    def test_string_allocation(self):
        from z8patch.shared import STRING_IDS, Strings
        from z8vrotate import translations
        self.assertEqual(STRING_IDS['vrotate'], (3225, 1))
        context = Strings()
        ids = context.add('vrotate', [[t] for t in translations.TITLES])
        self.assertEqual(ids, [3225])
        with self.assertRaises(ValueError):
            context.add('vrotate', [[t] for t in translations.TITLES])

    def test_emit_end_follows_providers(self):
        """Without vrotate the shared string table keeps its old shape."""
        from z8patch.shared import Strings
        from z8prores.menu import Image
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        from z8prores.package import Package
        eg = Package(FIRMWARE.read_bytes()).eg
        context = Strings()
        context.add('log', [['Log'] * 8 for _ in range(36)])
        meta = context.emit(Image(eg))
        self.assertEqual(meta['entries'], 3226)   # pre-vrotate end 3225 + 1
        self.assertNotIn('vrotate', meta['features'])
        context = Strings()
        context.add('vrotate', [['X'] for _ in range(36)])
        meta = context.emit(Image(eg))
        self.assertEqual(meta['entries'], 3227)   # vrotate end 3226 + 1
        self.assertEqual(meta['features'], ['vrotate'])

    def test_video_menu_insertion_and_config(self):
        import struct
        from z8patch.shared import CONFIG, PAGE, VIDEO_EVENTS, VIDEO_ROWS, VideoMenu
        from z8prores.menu import Image
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        from z8prores.package import Package
        eg = Package(FIRMWARE.read_bytes()).eg
        from z8vrotate import patcher
        template, pointer = patcher.menu_row(eg)
        row = struct.pack('<11I', 3225, *template[1:6], 0x315B, *template[7:])
        events_va = CAVE_BASE + 0x1800
        entries = {'shared_refresh': 0x40980100, 'shared_bank': 0x40980200}
        callbacks = {'vrotate': CAVE_BASE + 0x1300}
        menu = VideoMenu(eg)
        menu.add(0x315B, row, events_va)
        img = Image(eg)
        detail = menu.emit(img, ['video-orientation'], bytes(248), entries, callbacks)
        # Row order: 45 rows, 0x315B immediately before the image-area row.
        items = [struct.unpack_from('<I', img.new, VIDEO_ROWS - EG_BASE + 44 * i + 24)[0]
                 for i in range(detail['count'])]
        self.assertEqual(items.count(0x315B), 1)
        self.assertEqual(items[items.index(0x315B) + 1], 0x30A6)
        self.assertEqual(detail['count'], 45)
        self.assertEqual(detail['mask'], 8)
        # Page record points at the moved tables with the new row count
        # (PAGE is an EG offset, not a VA).
        page_rows, page_events, page_count = struct.unpack_from('<QQH', img.new, PAGE + 0x10)
        self.assertEqual((page_rows, page_events, page_count), (VIDEO_ROWS, VIDEO_EVENTS, 45))
        # CONFIG layout: +0 mask, +8 four stock slots, +0x28 the vrotate slot.
        config = img.new[CONFIG - EG_BASE:CONFIG - EG_BASE + 48]
        self.assertEqual(struct.unpack_from('<I', config)[0], 8)
        for offset, value in ((8, 0), (16, 0), (24, 0), (32, 0), (40, callbacks['vrotate'])):
            self.assertEqual(struct.unpack_from('<Q', config, offset)[0], value, offset)
        self.assertEqual(struct.unpack_from('<Q', img.new, VIDEO_EVENTS - EG_BASE
                                            + 8 * items.index(0x315B))[0], events_va)

    def test_video_menu_unchanged_without_vrotate(self):
        """Without video-orientation the emitted layout stays four slots."""
        import struct
        from z8patch.shared import CONFIG, PAGE, VIDEO_ROWS, VideoMenu
        from z8prores.menu import Image
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        from z8prores.package import Package
        eg = Package(FIRMWARE.read_bytes()).eg
        menu = VideoMenu(eg)
        img = Image(eg)
        detail = menu.emit(img, ['framing'], bytes(248),
                           {'shared_refresh': 0x40980100, 'shared_bank': 0x40980200}, {})
        self.assertEqual(detail['count'], 44)
        self.assertEqual(detail['mask'], 1)
        page_rows, page_events, page_count = struct.unpack_from('<QQH', img.new, PAGE + 0x10)
        self.assertEqual(page_count, 44)
        edit = next(e for e in img.edits if e['offset'] == CONFIG - EG_BASE)
        self.assertEqual(len(edit['new']), 40)   # <II4Q: unchanged record shape
        self.assertEqual(struct.unpack_from('<I', edit['new'])[0], 1)
        items = [struct.unpack_from('<I', img.new, VIDEO_ROWS - EG_BASE + 44 * i + 24)[0]
                 for i in range(44)]
        self.assertEqual(items, menu.items)     # stock order untouched


class DefaultOnTests(unittest.TestCase):
    """Pure-Python mirror of the vr_default_on first-boot init (T7).

    The cave sentinel byte boots 0 (the text loader re-copies the patched
    image every boot); the first hook pass -- from either the latch hook
    or the row-refresh hook, whichever runs first -- arms the sentinel
    FIRST, then writes 1 to the value byte in the active record and all
    four bank storage records.  Arm before write is the power-loss
    property: an init interrupted between the two steps at worst leaves a
    user Off in place until the next boot, and never lets a later
    re-initialization overwrite a stored user value.  Later passes must
    be no-ops, so a user's Off survives the whole session; a power cycle
    resets the sentinel and re-defaults every bank to On.
    """

    def test_default_on_mirror(self):
        from z8vrotate import patcher
        # Boot: sentinel 0, all five record bytes start from zeroed RAM.
        copies, sentinel = patcher.default_on([0] * 5, 0)
        self.assertEqual(copies, [1] * 5)
        self.assertEqual(sentinel, patcher.SENTINEL_VALUE)
        # Same boot, second pass (either entry point): nothing changes.
        copies, sentinel = patcher.default_on(copies, sentinel)
        self.assertEqual(copies, [1] * 5)
        self.assertEqual(sentinel, patcher.SENTINEL_VALUE)
        # The user turns the feature off in the active record and in bank
        # C's storage (record 3); no later pass may overwrite either.
        copies[0] = 0
        copies[3] = 0
        copies, sentinel = patcher.default_on(copies, sentinel)
        self.assertEqual(copies, [0, 1, 1, 0, 1])
        self.assertEqual(sentinel, patcher.SENTINEL_VALUE)
        # Even garbage record contents (a corrupted byte) stay untouched
        # once the sentinel is armed: the init is strictly first-boot.
        copies[1] = 0xFF
        copies, sentinel = patcher.default_on(copies, sentinel)
        self.assertEqual(copies[1], 0xFF)
        # A fresh boot (sentinel back to 0) re-defaults everything to 1.
        copies, sentinel = patcher.default_on(copies, 0)
        self.assertEqual(copies, [1] * 5)
        self.assertEqual(sentinel, patcher.SENTINEL_VALUE)


class CandidateByteEvidenceTests(unittest.TestCase):
    """Step-0 candidate-byte evidence encoded as test data (T7).

    The vrotate value byte is byte +2 of the DS item 0x1257 record family.
    The five record addresses below are pinned from the stock bank tables
    (category record at 0x440244C8 + 0x12*0x30 -> bank descriptor ->
    record-pointer array; the same tables the stock bank-copy engine
    indexes at 0x410157e0).  Bank 0 is the active/working record -- the
    4-byte slot whose +1 byte already hosts the shipped H.265 tier
    constant 0xA03D5C269 -- and banks 1..4 are the movie-shooting-bank
    storages A-D (bank-switch call sites at 0x410dd2ec..0x410dd958 pass
    (w0, w1) source/target bank ids with 0 = active).

    Spareness: the item is registered with copy type 0 and size 1, so the
    DS engine only ever reads/writes byte +0 of each record; the writer
    scan re-proves per run that no code path materializes any of the
    +1/+2/+3 byte addresses (u64 literal or movz/movk chain -- ADRP
    cannot reach the 0xa03d5cxxx RAM window from EG code, ~0x5F0000000
    beyond its +-4 GiB range).  See reports/t7-report.md for the full
    evidence chain including the negative controls.
    """

    def test_candidate_byte_evidence(self):
        import struct as _struct
        from z8vrotate import patcher
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        from z8prores.package import Package
        from z8patch.image import movz
        eg = Package(FIRMWARE.read_bytes()).eg
        # 1) The pinned record addresses re-derive from the stock tables.
        self.assertEqual(patcher.BANK_ITEM, 0x1257)
        self.assertEqual(patcher.VALUE_OFF, 2)
        self.assertEqual(patcher.VALUE_ADDR, 0xA03D5C26A)
        self.assertEqual(tuple(patcher.bank_records(eg)), patcher.BANK_RECORDS)
        self.assertEqual(patcher.BANK_RECORDS,
                         (0xA03D5C268, 0xA03D5C538, 0xA03D5C808, 0xA03D5CAD8, 0xA03D5CDA8))
        # 2) Record-base pointers appear only inside the two stock data
        #    tables that hold them by design (item type records and the
        #    per-bank record-pointer arrays) -- never in a code pool.
        tables = ((0x4400A000, 0x44012000), (0x44DB8000, 0x44DE0000))
        for record in patcher.BANK_RECORDS:
            needle = _struct.pack('<Q', record)
            at = eg.find(needle)
            self.assertNotEqual(at, -1, hex(record))   # pinned in the tables
            while at != -1:
                va = EG_BASE + at
                self.assertTrue(any(lo <= va < hi for lo, hi in tables),
                                'record base literal outside data tables: %#x' % va)
                at = eg.find(needle, at + 1)
        # 3) No spare byte (+1 tier neighborhood, +2 our candidate, +3) of
        #    any copy appears as a u64 literal anywhere in the image.
        spare = [r + off for r in patcher.BANK_RECORDS for off in (1, 2, 3)]
        for address in spare:
            self.assertEqual(eg.find(_struct.pack('<Q', address)), -1, hex(address))
        # 4) No movz/movk chain builds any spare byte address (the other
        #    way stock code could materialize a 64-bit RAM constant).
        for address in spare:
            low = address & 0xFFFF
            for reg in range(31):
                needle = movz(reg, low)
                at = eg.find(needle)
                while at != -1:
                    if at % 4 == 0:
                        value = low
                        for step in (1, 2, 3):
                            word = _struct.unpack_from('<I', eg, at + 4 * step)[0]
                            if word & 0xFF800000 == 0xF2800000 and (word & 0x1F) == reg \
                                    and (word >> 21) & 3 == step:
                                value |= ((word >> 5) & 0xFFFF) << (16 * step)
                                if value == address:
                                    self.fail('movz/movk chain builds %s at %#x'
                                              % (hex(address), EG_BASE + at))
                                break
                    at = eg.find(needle, at + 1)


class StorageWiringTests(unittest.TestCase):
    """The value byte wiring: DS record byte in, cave bytes out (T7).

    The row toggle flips and the value text reads the ACTIVE record byte
    (literal-address access like the H.265 TIER byte); the matrix hook's
    enable check reads the same byte; the first-boot init writes 1 to the
    active record and all four bank storages.  The T6 cave bytes vr_value
    and vr_enable are retired: one byte, one source of truth.
    """

    def _unit_instructions(self, code):
        from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
        md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
        md.skipdata = True
        return list(md.disasm(bytes(code), CAVE_BASE))

    def test_value_byte_wiring(self):
        import struct as _struct
        from z8patch.shared import Strings
        from z8vrotate import patcher
        from z8patch import compiled
        from z8prores.package import Package
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        compiler = _clang()
        if not compiler:
            self.skipTest('no clang for the aarch64 unit build')
        eg = Package(FIRMWARE.read_bytes()).eg
        code, observed = compiled.compile_unit('vrotate', compiler)
        entries = {name: int(sym['va'], 16) for name, sym in observed['symbols'].items()}
        # The retired cave bytes are gone from the unit.
        self.assertNotIn('vr_value', entries)
        self.assertNotIn('vr_enable', entries)
        code_bytes = bytes(code)
        for name in ('vr_value', 'vr_enable'):
            self.assertNotIn(name.encode(), code_bytes)
        # The active-record byte and all four bank copies ride as 64-bit
        # literals: the default-on init needs all five, the toggle and
        # the matrix hook the active byte.
        self.assertIn(_struct.pack('<Q', patcher.VALUE_ADDR), code_bytes)
        for record in patcher.BANK_RECORDS[1:]:
            self.assertIn(_struct.pack('<Q', record + patcher.VALUE_OFF), code_bytes)
        # Disassemble and follow every 64-bit literal load: at least one
        # load of the active byte feeds an ldrb (matrix-hook enable read
        # / row value read) and at least one feeds a strb (row toggle /
        # default-on write); every bank-copy literal feeds a strb.
        insns = self._unit_instructions(code)
        readers, writers = [], []
        bank_writers = 0
        for i, ins in enumerate(insns):
            if ins.mnemonic != 'ldr' or not ins.op_str.startswith('x') or '#' not in ins.op_str:
                continue
            reg = ins.op_str.split(',')[0]
            try:
                literal_va = int(ins.op_str.split('#')[1], 16)
            except ValueError:
                continue
            slot = literal_va - CAVE_BASE
            if not 0 <= slot <= len(code_bytes) - 8:
                continue
            value = _struct.unpack_from('<Q', code_bytes, slot)[0]
            following = insns[i + 1:i + 5]
            for nxt in following:
                base = '[%s]' % reg
                if nxt.mnemonic == 'ldrb' and nxt.op_str.split(', ')[-1] == base \
                        and value == patcher.VALUE_ADDR:
                    readers.append(nxt.address)
                if nxt.mnemonic == 'strb' and nxt.op_str.split(', ')[-1] == base:
                    if value == patcher.VALUE_ADDR:
                        writers.append(nxt.address)
                    if value in [r + patcher.VALUE_OFF for r in patcher.BANK_RECORDS[1:]]:
                        bank_writers += 1
        self.assertTrue(readers, 'no literal-address read of the value byte')
        self.assertTrue(writers, 'no literal-address write of the value byte')
        self.assertGreaterEqual(bank_writers, 4, 'bank copies are not written')
        # The build gates on the pinned record addresses and reports them.
        img, meta = patcher.build_main(eg, code, entries, Strings())
        storage = meta['storage']
        self.assertEqual(storage['item'], hex(patcher.BANK_ITEM))
        self.assertEqual(storage['value_off'], patcher.VALUE_OFF)
        self.assertEqual(storage['value_addr'], hex(patcher.VALUE_ADDR))
        self.assertEqual([int(a, 16) for a in storage['records']], list(patcher.BANK_RECORDS))
        self.assertEqual(len(img.edits), 5)   # unit, two hook sites, state window, events window


class MenuRowBuildTests(unittest.TestCase):
    """Full T6 build: unit + synthesized row + 36-language string (Step 1)."""

    def test_menu_row(self):
        from z8patch.shared import Strings
        from z8vrotate import patcher
        from z8patch import compiled
        from z8prores.package import Package
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        compiler = _clang()
        if not compiler:
            self.skipTest('no clang for the aarch64 unit build')
        eg = Package(FIRMWARE.read_bytes()).eg
        code, observed = compiled.compile_unit('vrotate', compiler)
        entries = {name: int(sym['va'], 16) for name, sym in observed['symbols'].items()}
        context = Strings()
        img, meta = patcher.build_main(eg, code, entries, context)
        menu = meta['menu']
        self.assertEqual(menu['item'], '0x315b')
        self.assertEqual(menu['title_id'], 3225)
        self.assertEqual(tuple(menu['value_ids']), (2466, 2467))
        row = struct.unpack_from('<11I', bytes.fromhex(menu['row_hex']))
        # The synthesized row clones the 0x2FC0 template field-for-field
        # (behavior class 0x20901005 incl.) with the new title and item ids.
        template, _ = patcher.menu_row(eg)
        self.assertEqual(row, (3225, *template[1:6], 0x315B, *template[7:]))
        self.assertEqual(row[4], 0x20901005)
        # The transition table clone lands at the fixed events sub-window and
        # is registered there (T2b: no organic in-unit slot any more).
        self.assertEqual(menu['row_table'], hex(VR_EVENTS_AT))
        events = next(e for e in img.edits if e['offset'] == VR_EVENTS_AT - EG_BASE)
        self.assertEqual(len(events['new']), VR_EVENTS_SIZE)
        self.assertEqual(events['new'], patcher.row_events(
            eg, patcher.menu_row(eg)[1], entries['vr_row_hook']))
        unit = bytes(img.new[CAVE_BASE - EG_BASE:CAVE_BASE - EG_BASE + len(code)])
        # The value byte now lives in the DS record family (T7): the build
        # pins the five record addresses and reports the storage wiring.
        self.assertEqual(meta['storage']['value_addr'], hex(patcher.VALUE_ADDR))
        self.assertEqual(meta['storage']['item'], hex(patcher.BANK_ITEM))
        from z8vrotate import translations
        self.assertEqual(meta['strings']['ids'], [3225])
        self.assertEqual(context.groups['vrotate'], [[t] for t in translations.TITLES])
        # The value pair ids ride as immediates in the cave hooks (both the
        # toggle and the refresh path must show them, sourced from patcher).
        from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
        md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
        md.skipdata = True                  # step over the zero-filled cave data
        immediates = {int(i.op_str.split('#')[-1], 16) for i in md.disasm(unit, CAVE_BASE)
                      if i.mnemonic in ('mov', 'movz') and '#' in i.op_str}
        for value in (patcher.ON_ID, patcher.OFF_ID, patcher.ROW_ITEM):
            self.assertIn(value, immediates, value)


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
        # Pure code + literal pool unit: it must stop short of the fixed
        # events sub-window (T2b capacity bound; no .org slot any more).
        self.assertLessEqual(CAVE_BASE + len(code), VR_EVENTS_AT)
        entries = {name: int(sym['va'], 16) for name, sym in observed['symbols'].items()}
        for name in ('vr_matrix_hook', 'vr_latch_hook', 'vr_latch_displaced'):
            self.assertIn(name, entries, name)
            self.assertTrue(CAVE_BASE <= entries[name] < CAVE_LIMIT, name)
        # A+ migration: the five data labels left the cave for the data
        # mirror state window; T2b moves the row-events clone to the fixed
        # events sub-window -- neither may come back as unit symbols.
        for name in ('vr_matrices', 'vr_axis_codes', 'vr_threshold', 'vr_latch',
                     'vr_sentinel', 'vr_row_events'):
            self.assertNotIn(name, entries, name)
        # T7: the retired cave bytes must stay out of the unit.
        for name in ('vr_value', 'vr_enable'):
            self.assertNotIn(name, entries, name)
        # Stock gate bytes (t2/t3 reports) are present in the fixture.
        self.assertEqual(eg[MATRIX_SITE - EG_BASE:MATRIX_SITE - EG_BASE + 4],
                         struct.pack('<I', MATRIX_STOCK_WORD))
        self.assertEqual(eg[LATCH_SITE - EG_BASE:LATCH_SITE - EG_BASE + 8], LATCH_STOCK)
        # The displaced pair replayed in the cave equals the stock bytes.
        at = entries['vr_latch_displaced'] - CAVE_BASE
        self.assertEqual(bytes(code[at:at + 8]), LATCH_STOCK)
        # Patch generation applies to the stock image: the two expect-byte
        # gates and the zero-cave / zero-window checks all pass.
        from z8patch.shared import Strings
        img, meta = patcher.build_main(eg, code, entries, Strings())
        self.assertEqual(len(img.edits), 5)
        sites = sorted(e['offset'] for e in img.edits)
        self.assertEqual(sites, sorted((MATRIX_SITE - EG_BASE, LATCH_SITE - EG_BASE,
                                        CAVE_BASE - EG_BASE, VR_STATE_IMG_OFF,
                                        VR_EVENTS_AT - EG_BASE)))
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
        # T5 review carry-items plus the A+ migration: the threshold word in
        # the state window must stay 4-byte aligned; the gravity-vector and
        # state-window literals in the pool must equal the patcher constants;
        # the assembled sentinel immediate must equal patcher.SENTINEL_VALUE
        # (both 0x5A materializations agree).
        self.assertEqual((VR_STATE_VA + VR_THRESHOLD_OFF) % 4, 0, VR_THRESHOLD_OFF)
        self.assertIn(struct.pack('<Q', patcher.ORIENT_VALID), code)
        self.assertIn(struct.pack('<Q', patcher.GRAVITY_VEC), code)
        for off in (VR_MATRICES_OFF, VR_THRESHOLD_OFF, VR_AXIS_CODES_OFF,
                    VR_LATCH_OFF, VR_SENTINEL_OFF):
            self.assertIn(struct.pack('<Q', VR_STATE_VA + off), code, hex(off))
        movz_immediates = set()
        from capstone import Cs as _Cs, CS_ARCH_ARM64 as _ARM64, CS_MODE_LITTLE_ENDIAN as _LE
        scan = _Cs(_ARM64, _LE)
        scan.skipdata = True             # step over the zero-filled cave data
        for i in scan.disasm(bytes(code), CAVE_BASE):
            if i.mnemonic in ('mov', 'movz') and '#' in i.op_str:
                movz_immediates.add(int(i.op_str.split('#')[-1], 16))
        self.assertIn(patcher.SENTINEL_VALUE, movz_immediates)
        # Negative gates: stock bytes that differ must fail the build.
        for bad_site in (MATRIX_SITE, LATCH_SITE + 4):
            bad = bytearray(eg)
            bad[bad_site - EG_BASE] ^= 1
            with self.assertRaises(ValueError, msg=hex(bad_site)):
                patcher.build_main(bytes(bad), code, entries, Strings())


class StateWindowTests(unittest.TestCase):
    """A+ migration (2026-11-09 vrotate-fix t1/t2): the five unit data
    labels live in a window of the boot-loaded data mirror segment, not in
    the read-only cave.

    The t1 report picked RAM [0xA0281A800,0xA0281A900) (EG image
    [0x4B25800,0x4B25900)) after a four-leg zero-writer census of the stock
    image; the boot segment loader record {len=0x2AD000, dst=0xA02808000}
    re-copies the window from the image every power cycle, which is what
    makes the zero-shipped latch/sentinel bytes a fresh-boot state and the
    window tail magic byte (0xA5) a witness of a real boot copy.  These
    tests pin the label addresses, the assembled unit's literal addressing
    of the window and the asm<->mirror constant parity.
    """

    def _build(self):
        from z8patch.shared import Strings
        from z8vrotate import patcher
        from z8patch import compiled
        from z8prores.package import Package
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        compiler = _clang()
        if not compiler:
            self.skipTest('no clang for the aarch64 unit build')
        eg = Package(FIRMWARE.read_bytes()).eg
        code, observed = compiled.compile_unit('vrotate', compiler)
        entries = {name: int(sym['va'], 16) for name, sym in observed['symbols'].items()}
        img, meta = patcher.build_main(eg, code, entries, Strings())
        return patcher, bytes(code), entries, img, meta

    def test_labels_inside_the_data_mirror_window(self):
        """The five label VAs fall inside the window; the patcher agrees
        with the pinned literals and the window maps into the segment."""
        from z8patch.image import DATA_OFF, DATA_END, DATA_VA, data_off
        patcher, _, _, _, _ = self._build()
        labels = dict(matrices=VR_MATRICES_OFF, threshold=VR_THRESHOLD_OFF,
                      axis_codes=VR_AXIS_CODES_OFF, latch=VR_LATCH_OFF,
                      sentinel=VR_SENTINEL_OFF)
        for name, off in labels.items():
            self.assertTrue(VR_STATE_VA <= VR_STATE_VA + off < VR_STATE_END, name)
        self.assertEqual((patcher.VR_STATE_VA, patcher.VR_STATE_END,
                          patcher.VR_STATE_SIZE, patcher.VR_STATE_IMG_OFF),
                         (VR_STATE_VA, VR_STATE_END, VR_STATE_SIZE, VR_STATE_IMG_OFF))
        self.assertEqual((patcher.VR_MATRICES_OFF, patcher.VR_THRESHOLD_OFF,
                          patcher.VR_AXIS_CODES_OFF, patcher.VR_LATCH_OFF,
                          patcher.VR_SENTINEL_OFF, patcher.VR_MAGIC_OFF),
                         (VR_MATRICES_OFF, VR_THRESHOLD_OFF, VR_AXIS_CODES_OFF,
                          VR_LATCH_OFF, VR_SENTINEL_OFF, VR_MAGIC_OFF))
        self.assertEqual(patcher.VR_MAGIC, VR_MAGIC)
        # The window sits inside the boot-copied data mirror segment and the
        # EG image offset is the segment arithmetic from the t1 fact block.
        self.assertTrue(DATA_VA <= VR_STATE_VA and VR_STATE_END <= DATA_VA + DATA_END - DATA_OFF)
        self.assertEqual(data_off(VR_STATE_VA), VR_STATE_IMG_OFF)
        self.assertEqual(VR_STATE_VA - DATA_VA + DATA_OFF, VR_STATE_IMG_OFF)
        self.assertEqual(VR_STATE_IMG_OFF + VR_STATE_SIZE, 0x4B25900)

    def test_unit_addresses_the_window_not_the_cave(self):
        """The assembled unit carries the five window literals and no
        residual cave data reference."""
        import struct as _struct
        patcher, code, entries, _, _ = self._build()
        for off in (VR_MATRICES_OFF, VR_THRESHOLD_OFF, VR_AXIS_CODES_OFF,
                    VR_LATCH_OFF, VR_SENTINEL_OFF):
            self.assertIn(_struct.pack('<Q', VR_STATE_VA + off), code, hex(off))
        # The unit is pure code + literal pool (T2b: the row-events clone is
        # gone to the fixed events sub-window), so no qword anywhere in the
        # unit may point into the cave: the five labels and the events table
        # used to ride there, and any in-cave pointer in the pool would be a
        # residual or reappeared data reference.
        self.assertNotIn('vr_row_events', entries)
        for at in range(0, len(code) - 7):
            q = _struct.unpack_from('<Q', code, at)[0]
            self.assertFalse(CAVE_BASE <= q < CAVE_LIMIT,
                             'cave pointer %#x at unit+%#x' % (q, at))

    def test_mirror_parity_six_vectors(self):
        """The constants the assembled unit will read from the window are
        the ones the build materialized there (asm<->mirror parity).

        Reclassifies the t1 six single-axis canonical vectors using ONLY
        bytes taken from the built state window edit, exactly the way
        vr_classify consumes them (threshold word at +0x6C, axis codes at
        +0x70), and checks the matrices the matrix hook would redirect to.
        """
        import struct as _struct
        from z8vrotate import matrices
        patcher, code, entries, img, _ = self._build()
        window = next(e for e in img.edits if e['offset'] == VR_STATE_IMG_OFF)['new']
        self.assertEqual(len(window), VR_STATE_SIZE)
        threshold = _struct.unpack_from('<I', window, VR_THRESHOLD_OFF)[0]
        codes = window[VR_AXIS_CODES_OFF:VR_AXIS_CODES_OFF + 6]
        self.assertEqual(threshold, patcher.THRESHOLD_BITS)
        self.assertEqual(bytes(codes), patcher.AXIS_CODES)
        self.assertEqual(codes, bytes((1, 2, 0, 0, 0, 3)))

        def mirror_classify(gate, x, y, z):
            # vr_classify's algorithm with the window as the only constant
            # source: gate, sign strip, unsigned argmax with the
            # x-beats-y-beats-z tie-break, threshold, axis*2+sign lookup.
            if gate != 1:
                return 0
            words = [_struct.unpack('<I', _struct.pack('<f', c))[0] for c in (x, y, z)]
            signs = [w >> 31 for w in words]
            mags = [w & 0x7FFFFFFF for w in words]
            axis = 0 if mags[0] >= mags[1] else 1
            if mags[2] > mags[axis]:
                axis = 2
            if mags[axis] < threshold:
                return 0
            return codes[axis * 2 + signs[axis]]

        canonical = (
            ((0.0, 0.0, 1.0), codes[4]),   # level rest (t1 anchor)
            ((1.0, 0.0, 0.0), codes[0]),   # X+
            ((-1.0, 0.0, 0.0), codes[1]),   # X-
            ((0.0, 1.0, 0.0), codes[2]),   # Y+
            ((0.0, -1.0, 0.0), codes[3]),   # Y-
            ((0.0, 0.0, -1.0), codes[5]),   # Z- (upside down)
        )
        for vector, expected in canonical:
            self.assertEqual(mirror_classify(1, *vector), expected, vector)
        self.assertEqual(mirror_classify(0, 0.0, 0.0, -1.0), 0)
        # The matrices the hook would select for the latched codes ride in
        # the same window, at the offset the pool literal points to.
        self.assertEqual(bytes(window[VR_MATRICES_OFF:VR_MATRICES_OFF + 108]),
                         patcher.VR_MATRICES)
        self.assertEqual(patcher.VR_MATRICES,
                         matrices.ORIENT_TO_MATRIX[1] + matrices.ORIENT_TO_MATRIX[2]
                         + matrices.ORIENT_TO_MATRIX[3])

    def test_window_ships_fresh_boot_state(self):
        """Latch and sentinel mirror bytes ship 0; the magic byte ships 0xA5."""
        patcher, code, entries, img, _ = self._build()
        window = next(e for e in img.edits if e['offset'] == VR_STATE_IMG_OFF)['new']
        self.assertEqual(window[VR_LATCH_OFF], 0)
        self.assertEqual(window[VR_SENTINEL_OFF], 0)
        self.assertEqual(window[VR_MAGIC_OFF], VR_MAGIC)
        # Everything past the 121 B payload up to the magic byte stays zero
        # (window headroom), and the stock image bytes were zero there.
        self.assertEqual(window[VR_SENTINEL_OFF + 1:VR_MAGIC_OFF], bytes(VR_MAGIC_OFF - VR_SENTINEL_OFF - 1))
        stock = None
        from z8prores.package import Package
        if FIRMWARE.is_file():
            stock = Package(FIRMWARE.read_bytes()).eg
        if stock is not None:
            self.assertEqual(stock[VR_STATE_IMG_OFF:VR_STATE_IMG_OFF + VR_STATE_SIZE],
                             bytes(VR_STATE_SIZE))


class EventsWindowTests(unittest.TestCase):
    """T2b (2026-11-09 user ruling): the row-events clone lives at a
    patcher-constant fixed sub-window of the cave (the z8h265 MENU_AT form)
    instead of an organic in-unit slot behind .org padding.

    VR_EVENTS_AT = 0x40A09000 (4K-aligned, stock zero, table 44x32 B with the
    0x3BB terminator).  This decouples unit code/pool growth from the frozen
    transition-pointer recipe rows: the unit stops at its own end, the table
    rides its own expect_zero image edit, and the only external bytes that
    name the table are the 8 B emit-region pointer (pinned below).
    """

    def _build(self):
        from z8patch.shared import Strings
        from z8vrotate import patcher
        from z8patch import compiled
        from z8prores.package import Package
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        compiler = _clang()
        if not compiler:
            self.skipTest('no clang for the aarch64 unit build')
        eg = Package(FIRMWARE.read_bytes()).eg
        code, observed = compiled.compile_unit('vrotate', compiler)
        entries = {name: int(sym['va'], 16) for name, sym in observed['symbols'].items()}
        img, meta = patcher.build_main(eg, code, entries, Strings())
        return patcher, bytes(code), entries, img, meta

    def test_events_window_constants_and_stock_state(self):
        """Pinned constants; the window and the whole cave tail past the
        table are stock zero; the unit stops short of the window."""
        from z8prores.package import Package
        patcher, code, _, _, meta = self._build()
        self.assertEqual((patcher.VR_EVENTS_AT, patcher.VR_EVENTS_END),
                         (VR_EVENTS_AT, VR_EVENTS_END))
        self.assertEqual(VR_EVENTS_SIZE, 44 * 32)
        self.assertEqual(VR_EVENTS_AT % 0x1000, 0)
        self.assertTrue(CAVE_BASE < VR_EVENTS_AT and VR_EVENTS_END <= CAVE_LIMIT)
        # The unit is pure code + pool and must stop before the window; the
        # gap between them stays stock zero in the built image.
        self.assertLess(CAVE_BASE + len(code), VR_EVENTS_AT)
        self.assertEqual(meta['events_window'], [hex(VR_EVENTS_AT), hex(VR_EVENTS_END)])
        if FIRMWARE.is_file():
            eg = Package(FIRMWARE.read_bytes()).eg
            self.assertEqual(eg[VR_EVENTS_AT - EG_BASE:VR_EVENTS_END - EG_BASE],
                             bytes(VR_EVENTS_SIZE))
            self.assertEqual(eg[VR_EVENTS_END - EG_BASE:CAVE_LIMIT - EG_BASE],
                             bytes(CAVE_LIMIT - VR_EVENTS_END))

    def test_events_table_rides_its_own_image_edit(self):
        """The 0x580-byte clone is a dedicated expect_zero edit at the fixed
        window, registered as the menu row table, and the cave gap plus tail
        stay zero in the built image."""
        from z8vrotate import patcher
        patcher, code, entries, img, meta = self._build()
        events = next(e for e in img.edits if e['offset'] == VR_EVENTS_AT - EG_BASE)
        self.assertEqual(len(events['new']), VR_EVENTS_SIZE)
        self.assertEqual(events['new'], patcher.row_events(
            img.old, patcher.menu_row(img.old)[1], entries['vr_row_hook']))
        self.assertEqual(meta['menu']['row_table'], hex(VR_EVENTS_AT))
        # Terminator record last and untouched; the three toggle actions are
        # the only in-cave pointers (they name vr_row_hook code).
        import struct as _struct
        self.assertEqual(_struct.unpack_from('<Q', events['new'], 32 * 43)[0], 0x3BB)
        hook_slots = [i for i in range(44)
                      if _struct.unpack_from('<Q', events['new'], 32 * i + 8)[0]
                      == entries['vr_row_hook']]
        self.assertEqual(len(hook_slots), 3)
        # Gap and tail zero in the new image.
        gap = img.new[CAVE_BASE - EG_BASE + len(code):VR_EVENTS_AT - EG_BASE]
        tail = img.new[VR_EVENTS_END - EG_BASE:CAVE_LIMIT - EG_BASE]
        self.assertEqual(gap, bytes(VR_EVENTS_AT - CAVE_BASE - len(code)))
        self.assertEqual(tail, bytes(CAVE_LIMIT - VR_EVENTS_END))

    def test_emit_region_pointer_targets_the_events_window(self):
        """The shared transition-pointer emit names VR_EVENTS_AT (the one
        external frozen row that carries the table address)."""
        import struct as _struct
        import features
        from z8patch.shared import VIDEO_EVENTS
        from z8prores.package import Package
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        compiler = _clang()
        if not compiler:
            self.skipTest('no clang for the aarch64 unit build')
        eg = Package(FIRMWARE.read_bytes()).eg
        img, detail, rows = features.compose(eg, ['video-orientation'], compiler,
                                             'source', check_recipe=False)
        items = [int(i, 16) for i in detail['menu']['items']]
        at = VIDEO_EVENTS - EG_BASE + 8 * items.index(0x315B)
        self.assertEqual(_struct.unpack_from('<Q', img.new, at)[0], VR_EVENTS_AT)


class OldCombinationFreezeTests(unittest.TestCase):
    """The 15 non-vrotate combinations keep their frozen recipes byte-exact.

    The eight selections that also contain photo-tools cannot build on this
    machine (the Apple-clang-reviewed precapture/pixelshift units do not
    reproduce under LLVM 19.1.7 and the reviewed prebuilt binaries are not
    present), so this suite exercises the seven buildable ones with
    check_recipe=True; the recipe refreeze audit (build/vrfix) covers all 15
    including the photo-tools eight.
    """

    OLD_COMBOS = (['framing'], ['video-quality'], ['log-colour'],
                  ['framing', 'video-quality'], ['framing', 'log-colour'],
                  ['video-quality', 'log-colour'],
                  ['framing', 'video-quality', 'log-colour'])

    def test_old_combinations_match_frozen_recipes(self):
        import features
        from z8prores.package import Package
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        compiler = _clang()
        if not compiler:
            self.skipTest('no clang for the aarch64 unit build')
        eg = Package(FIRMWARE.read_bytes()).eg
        for names in self.OLD_COMBOS:
            with self.subTest(features='+'.join(names)):
                _, _, rows = features.compose(eg, names, compiler, 'source',
                                              check_recipe=True)
                self.assertGreater(len(rows), 0)


class ReservationCensusTests(unittest.TestCase):
    """The text-gap reservation census (T8): the vrotate cave must be disjoint
    from every other feature's reserved window.

    Both T8 cave collisions (0x40A20000 with the quality icon PNG area,
    0x40A12000 with the H.265 menu-data area) were patcher-level reservations
    invisible to any single registry.  This census hardcodes the windows as
    documented by their owning modules and asserts the vrotate reservation is
    disjoint from each, so a third collision of the same class fails loudly
    here -- before any build or recipe freeze.
    """

    # (start, end, owner) -- all stock EG virtual addresses (BASE 0x40160000).
    CENSUS = (
        (0x408D0000, 0x40950000, 'anamorphic standalone string text/tables (z8anamorphic/patcher.py TEXT/TABLES/TABLES_LIMIT; superseded by the shared string system in compositions, kept for standalone builds)'),
        (0x40953000, 0x40955000, 'opengate Q3 fine/basic tables (-DQ3_FINE_TABLE/-DQ3_BASIC_TABLE)'),
        (0x40960000, 0x40970000, 'opengate code cave (z8patch/linker.py CAVE/CAVE_END; opengate caps code below 0xF000)'),
        (0x40970000, 0x40974000, 'anamorphic unit (SPECS asm_base/limit)'),
        (0x4097F000, 0x40980000, 'opengate AP state (zero-state contract window)'),
        (0x40980000, 0x40981000, 'shared bank/refresh code and CONFIG (z8patch/shared.py BANK/CONFIG, unit below 0x40980F00)'),
        (0x40990000, 0x409D8000, 'pixelshift unit (SPECS cave/limit)'),
        (0x409D8000, 0x409DA000, 'pixelshift-af unit (SPECS cave/limit)'),
        (0x409F0000, 0x40A00000, 'precapture unit (SPECS cave/limit)'),
        (0x40A00000, 0x40A04000, 'prores code, back-half code and sub-page GUI area (z8prores/menu.py CODE_AT/GUI_AT, ceiling TEXT_AT = VA 0x40A04000, enforced by its own overflow guard)'),
        (0x40A10000, 0x40A1F000, 'H.265 code and menu data (z8h265/patcher.py CODE_AT/MENU_AT/AREA_END)'),
        (0x40A20000, 0x40A30000, 'quality derived icon PNGs (z8quality/patcher.py PNG, 0x10000 design limit; frozen v0.4.0 recipe data)'),
        (0x40A30000, 0x40A40000, 'shared final video menu rows and transition pointers (z8patch/shared.py VIDEO_ROWS/VIDEO_EVENTS plus the capacity ceiling)'),
        (0x40A40000, 0x40A50000, 'quality force/config/code (z8quality/patcher.py FORCE/CONFIG/CODE; SPECS limit)'),
        (0x40A50000, 0x40AF0000, 'shared 36-language strings (z8patch/shared.py TEXT/TABLES/TABLES_END)'),
        (0x40B00000, 0x40B08000, 'log unit (SPECS asm_base/limit)'),
        (0x40B08000, 0x40B10000, 'log private state (loader floor region beyond the unit)'),
    )

    def test_vrotate_cave_disjoint_from_reservation_census(self):
        from z8vrotate import patcher
        cave = (patcher.CODE_AT, patcher.CODE_END, 'vrotate unit (z8vrotate/patcher.py CODE_AT/CODE_END)')
        for start, end, owner in self.CENSUS:
            with self.subTest(owner=owner.split(' (')[0]):
                self.assertTrue(cave[1] <= start or end <= cave[0],
                                f'vrotate cave {cave[0]:#x}-{cave[1]:#x} overlaps {owner}')

    def test_vrotate_cave_disjoint_from_other_unit_caves(self):
        from z8vrotate import patcher
        from z8patch.compiled import SPECS
        for name, spec in SPECS.items():
            if 'asm_base' not in spec or name == 'vrotate':
                continue
            base, limit = spec['asm_base'], spec['limit']
            with self.subTest(unit=name):
                self.assertTrue(patcher.CODE_END <= base or limit <= patcher.CODE_AT,
                                f'vrotate cave overlaps SPECS unit {name} {base:#x}-{limit:#x}')


class IntegrationTests(unittest.TestCase):
    """End-to-end composition of the video-orientation feature group (T8).

    Full features.compose of the vrotate-only selection in source mode:
    the five-group FEATURES tuple, the shared five-slot CONFIG with mask 8,
    the 0x315B row inserted immediately before the image-area row, the
    state window bytes (constants, zero latch/sentinel, 0xA5 magic) in the
    boot-copied data mirror segment, and the loader boundary covering the
    vrotate cave.  Needs the stock firmware fixture and an aarch64 clang;
    skipped otherwise like the other build legs.
    """

    def _compose(self, check_recipe):
        import features
        from z8prores.package import Package
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        compiler = _clang()
        if not compiler:
            self.skipTest('no clang for the aarch64 unit build')
        eg = Package(FIRMWARE.read_bytes()).eg
        return features.compose(eg, ['video-orientation'], compiler, 'source',
                                check_recipe=check_recipe)

    def test_vrotate_only_composition(self):
        import struct
        from z8vrotate import patcher
        img, detail, rows = self._compose(check_recipe=False)
        self.assertEqual(detail['menu']['mask'], 8)
        self.assertEqual(detail['menu']['count'], 45)
        items = [int(i, 16) for i in detail['menu']['items']]
        self.assertEqual(items[items.index(0x30A6) - 1], patcher.ROW_ITEM)
        config = next(e for e in img.edits
                      if e['purpose'] == 'shared feature mask and row callbacks')
        self.assertEqual(struct.unpack_from('<II', config['new']), (8, 0))
        self.assertEqual(len(config['new']), 48)   # five callback slots
        slots = struct.unpack_from('<5Q', config['new'], 8)
        self.assertEqual(slots[:4], (0, 0, 0, 0))
        refresh = int(detail['menu']['callbacks']['vrotate'], 16)
        self.assertEqual(slots[4], refresh)
        # Fresh-boot state fill: the five labels live in the data mirror
        # window; the one-shot latch and first-boot sentinel mirror bytes
        # ship 0 and the window tail carries the 0xA5 magic byte.
        window = next(e for e in img.edits if e['offset'] == VR_STATE_IMG_OFF)
        self.assertEqual(len(window['new']), VR_STATE_SIZE)
        self.assertEqual(window['new'][VR_MATRICES_OFF:VR_MATRICES_OFF + 108],
                         patcher.VR_MATRICES)
        self.assertEqual(struct.unpack_from('<I', window['new'], VR_THRESHOLD_OFF)[0],
                         patcher.THRESHOLD_BITS)
        self.assertEqual(window['new'][VR_AXIS_CODES_OFF:VR_AXIS_CODES_OFF + 6],
                         patcher.AXIS_CODES)
        self.assertEqual(window['new'][VR_LATCH_OFF], 0)
        self.assertEqual(window['new'][VR_SENTINEL_OFF], 0)
        self.assertEqual(window['new'][VR_MAGIC_OFF], VR_MAGIC)
        entries = detail['vrotate']['entries']
        for name in ('vr_sentinel', 'vr_latch'):
            self.assertNotIn(name, entries, name)
        self.assertEqual(detail['vrotate']['state_window'],
                         [hex(VR_STATE_VA), hex(VR_STATE_END)])
        # T2b: the row-events clone rides its own edit at the fixed events
        # sub-window and is absent from the unit symbols.
        events = next(e for e in img.edits if e['offset'] == VR_EVENTS_AT - EG_BASE)
        self.assertEqual(len(events['new']), VR_EVENTS_SIZE)
        self.assertNotIn('vr_row_events', entries)
        self.assertEqual(detail['vrotate']['events_window'],
                         [hex(VR_EVENTS_AT), hex(VR_EVENTS_END)])
        self.assertEqual(detail['vrotate']['menu']['row_table'], hex(VR_EVENTS_AT))
        self.assertEqual(detail['vrotate']['state'],
                         dict(matrices=hex(VR_STATE_VA + VR_MATRICES_OFF),
                              threshold=hex(VR_STATE_VA + VR_THRESHOLD_OFF),
                              axis_codes=hex(VR_STATE_VA + VR_AXIS_CODES_OFF),
                              latch=hex(VR_STATE_VA + VR_LATCH_OFF),
                              sentinel=hex(VR_STATE_VA + VR_SENTINEL_OFF),
                              magic='0xa5@+0xff'))
        loader_end = int(detail['loader']['end'], 16)
        self.assertGreaterEqual(loader_end, 0x40A10000)   # covers the vrotate cave
        self.assertEqual(loader_end % 4096, 0)
        self.assertEqual(detail['strings']['entries'], 3227)
        self.assertIn('vrotate', detail['strings']['features'])
        # The two gated stock hook sites are part of the composition.
        purposes = [r['purpose'] for r in rows]
        self.assertTrue(any('movie tkhd matrix copy' in p for p in purposes))
        self.assertTrue(any('record file open trampoline' in p for p in purposes))

    def test_vrotate_recipe_frozen(self):
        """The vrotate-only composition matches the frozen recipe (T8 freeze)."""
        _, _, rows = self._compose(check_recipe=True)
        self.assertGreater(len(rows), 0)


class ContractPinTests(unittest.TestCase):
    """T8 review carry-item M1: the fifth-slot stock-zero build gate.

    The unfrozen shared unit runs an unconditional five-slot callback ring
    reading CONFIG+0x28 (0x40980F28) even in four-group builds, where the
    fifth slot keeps its stock bytes; a nonzero stock byte there would be
    blr'd as a callback.  The contract pins the stock fact at build time
    instead of leaving it to manual verification.
    """

    def test_fifth_slot_stock_zero_pin(self):
        from features import compose
        from z8prores.package import Package
        from z8patch.contract import verify_contract
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        compiler = _clang()
        if not compiler:
            self.skipTest('no clang for the aarch64 unit build')
        old = Package(FIRMWARE.read_bytes()).eg
        img, _, _ = compose(old, ['video-orientation'], compiler, 'source',
                            check_recipe=False)
        new = bytes(img.new)
        contract = verify_contract(old, new, ['video-orientation'])
        self.assertEqual(contract['status'], 'PASS')
        doctored = bytearray(old)
        doctored[0x40980F28 - 0x40160000] = 1
        with self.assertRaisesRegex(ValueError, 'fifth callback slot stock zero'):
            verify_contract(bytes(doctored), new, ['video-orientation'])


class BuildTimeGuardTests(unittest.TestCase):
    """T3 build-time guards (2026-11-09 vrotate-fix): the three architecture
    iron rules become standing assertions that refuse the build.

    * A -- the vrotate unit store census: every data write in the assembled
      unit must resolve its base register to a non-cave target (the cave is
      read-only at EL0; a store into it is the original crash class).
    * C -- window-fact doctored negatives: verify_contract must reject a
      corrupted state-window magic byte and a corrupted window base literal.
    * D1 -- unit assembly sources must not use .org (unit source pinning is
      the bright-line ban; .balign/.space stay legal for in-unit data).
    * D2 -- cross-region pointer sweep: emit-region qwords outside unit
      spans may only name registered entry symbols of a unit.
    """

    CAVE_WINDOW = (0x40A08000, 0x40A10000)

    # --- minimal AArch64 encoders for synthetic census units (self-checking:
    # every test that uses one also round-trips it through capstone).
    @staticmethod
    def _adr(rd, delta):
        immlo, immhi = delta & 3, (delta >> 2) & 0x7FFFF
        return struct.pack('<I', (immlo << 29) | (0x10 << 24) | (immhi << 5) | rd)

    @staticmethod
    def _ldr_literal(rt, delta):
        return struct.pack('<I', 0x58000000 | ((delta // 4) << 5) | rt)

    @staticmethod
    def _movz(rd, imm, shift=0):
        return struct.pack('<I', 0xD2800000 | ((shift // 16) << 21) | (imm << 5) | rd)

    @staticmethod
    def _movk(rd, imm, shift):
        return struct.pack('<I', 0xF2800000 | ((shift // 16) << 21) | (imm << 5) | rd)

    @staticmethod
    def _movzw(rd, imm, shift=0):
        return struct.pack('<I', 0x52800000 | ((shift // 16) << 21) | (imm << 5) | rd)

    @staticmethod
    def _movkw(rd, imm, shift):
        return struct.pack('<I', 0x72800000 | ((shift // 16) << 21) | (imm << 5) | rd)

    @staticmethod
    def _cbnz(rt, delta):
        return struct.pack('<I', 0x35000000 | ((delta // 4) << 5) | rt)

    @staticmethod
    def _strb(rt, rn, imm=0):
        return struct.pack('<I', 0x39000000 | (imm << 10) | (rn << 5) | rt)

    @staticmethod
    def _decode(code):
        from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
        md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
        return [i.mnemonic + ' ' + i.op_str for i in md.disasm(bytes(code), 0)]

    def _census(self, code):
        from z8patch.contract import assert_no_cave_store_targets
        return assert_no_cave_store_targets(bytes(code), self.CAVE_WINDOW[0], self.CAVE_WINDOW)

    def test_store_census_rejects_adr_into_cave(self):
        """A store whose base register is an in-block adr of a cave target
        (the original T2 crash shape: adr of an in-unit data label) must
        fail the build."""
        code = self._adr(10, 8) + self._strb(8, 10)
        self.assertEqual(self._decode(code)[0], 'adr x10, #8')
        with self.assertRaisesRegex(ValueError, 'cave window'):
            self._census(code)

    def test_store_census_rejects_literal_pool_cave_address(self):
        """A store fed by an ldr = literal naming a cave VA must fail; the
        same shape with an outside-cave literal (the DS record byte family)
        passes."""
        from z8patch.contract import assert_no_cave_store_targets
        bad = self._ldr_literal(10, 8) + self._strb(8, 10) + struct.pack('<Q', 0x40A08080)
        with self.assertRaisesRegex(ValueError, 'cave window'):
            assert_no_cave_store_targets(bad, self.CAVE_WINDOW[0], self.CAVE_WINDOW)
        good = self._ldr_literal(10, 8) + self._strb(8, 10) + struct.pack('<Q', 0xA03D5C26A)
        assert_no_cave_store_targets(good, self.CAVE_WINDOW[0], self.CAVE_WINDOW)
        # A non-cave 0x40xxxxxx stock-table literal passes too.
        stock = self._ldr_literal(10, 8) + self._strb(8, 10) + struct.pack('<Q', 0x43C33EF0)
        assert_no_cave_store_targets(stock, self.CAVE_WINDOW[0], self.CAVE_WINDOW)

    def test_store_census_rejects_movz_movk_cave_chain(self):
        """A movz/movk chain materializing a cave VA must fail even though no
        literal pool is involved; an immediate offset folds into the check."""
        chain = (self._movz(10, 0x8000) + self._movk(10, 0x40A0, 16)
                 + self._strb(8, 10))
        with self.assertRaisesRegex(ValueError, 'cave window'):
            self._census(chain)
        offset = (self._movz(10, 0x8000) + self._movk(10, 0x40A0, 16)
                  + self._strb(8, 10, 0x10))          # 0x40A08010, still the cave
        with self.assertRaisesRegex(ValueError, 'cave window'):
            self._census(offset)

    def test_store_census_argument_and_stack_stores_pass(self):
        """Stores based on incoming argument registers and on the stack are
        the two pass-through classes (the hooks never own those targets)."""
        arg = self._strb(8, 0)                        # strb w8, [x0]: parameter
        self._census(arg)
        stack = struct.pack('<I', 0xA9BE7BFD)        # stp x29, x30, [sp, #-0x20]!
        self.assertEqual(self._decode(stack)[0], 'stp x29, x30, [sp, #-0x20]!')
        self._census(stack)

    def test_store_census_rejects_w_view_argument_alias_chain(self):
        """I-1: a cave address built through the W view of an argument
        register (movz/movk w0, store through x0) must be rejected -- the
        zero-extended X view carries the same value, so the store is a
        resolved in-block redefinition, never a pass-through parameter."""
        chain = (self._movzw(0, 0x8000) + self._movkw(0, 0x40A0, 16)
                 + self._strb(31, 0))          # strb wzr, [x0]
        self.assertEqual(self._decode(chain),
                         ['mov w0, #0x8000', 'movk w0, #0x40a0, lsl #16',
                          'strb wzr, [x0]'])
        with self.assertRaisesRegex(ValueError, 'cave window'):
            self._census(chain)

    def test_store_census_conditional_branch_ends_the_window(self):
        """M-1: a conditional branch between the base def and the store
        ends the basic block -- the def is outside the window and the
        store is conservatively rejected (whitelist escape applies)."""
        from z8patch.contract import assert_no_cave_store_targets
        code = (self._ldr_literal(10, 12) + self._cbnz(8, 8) + self._strb(8, 10)
                + struct.pack('<Q', 0x40A08080))
        self.assertEqual(self._decode(code)[:3],
                         ['ldr x10, #0xc', 'cbnz w8, #0xc', 'strb w8, [x10]'])
        with self.assertRaisesRegex(ValueError, 'cannot resolve'):
            assert_no_cave_store_targets(code, self.CAVE_WINDOW[0], self.CAVE_WINDOW)
        whitelist = {self.CAVE_WINDOW[0] + 8: 'test-only: proven-safe store shape'}
        assert_no_cave_store_targets(code, self.CAVE_WINDOW[0], self.CAVE_WINDOW,
                                      whitelist=whitelist)

    def test_store_census_treats_every_store_family_member_as_a_store(self):
        """M-2: unscaled/exclusive/atomic store forms (sturb, sttrb, swp,
        cas, stadd) are stores -- an unresolvable base is rejected, never
        silently passed.  Encodings verified against clang + capstone."""
        from z8patch.contract import assert_no_cave_store_targets
        forms = ((0x3800013F, 'sturb wzr, [x9]'),
                 (0x38000943, 'sttrb w3, [x10]'),
                 (0xF8218120, 'swp x1, x0, [x9]'),
                 (0xC8A17D20, 'cas x1, x0, [x9]'),
                 (0xF825017F, 'stadd x5, [x11]'))
        for word, text in forms:
            code = struct.pack('<I', word)
            self.assertEqual(self._decode(code), [text])
            with self.subTest(store=text):
                with self.assertRaisesRegex(ValueError, 'cannot resolve'):
                    assert_no_cave_store_targets(code, self.CAVE_WINDOW[0],
                                                 self.CAVE_WINDOW)

    def test_store_census_unresolvable_base_is_conservative(self):
        """A store whose base cannot be resolved in-block (register loaded
        from memory, or a live-in non-argument register) is rejected unless
        the address is explicitly whitelisted with a reason."""
        from z8patch.contract import assert_no_cave_store_targets
        indirect = struct.pack('<I', 0xF9400009) + self._strb(31, 9)   # ldr x9,[x0]; strb wzr,[x9]
        with self.assertRaisesRegex(ValueError, 'cannot resolve'):
            assert_no_cave_store_targets(indirect, self.CAVE_WINDOW[0], self.CAVE_WINDOW)
        whitelist = {self.CAVE_WINDOW[0] + 4: 'test-only: proven-safe store shape'}
        assert_no_cave_store_targets(indirect, self.CAVE_WINDOW[0], self.CAVE_WINDOW,
                                      whitelist=whitelist)
        live_in = self._strb(8, 9)                   # strb w8,[x9], x9 never defined
        with self.assertRaisesRegex(ValueError, 'cannot resolve'):
            assert_no_cave_store_targets(live_in, self.CAVE_WINDOW[0], self.CAVE_WINDOW)

    def test_store_census_passes_the_real_vrotate_unit(self):
        """The shipped vrotate unit (664 B pure code + pool) passes the
        census: its data stores ride state-window/DS-record literals and
        the stack, plus exactly ONE whitelisted store -- the sentinel arm,
        whose literal def is separated from the store by a forward cbnz
        that skips past the whole init series (dominance proof in the
        whitelist entry)."""
        from z8patch import compiled
        from z8vrotate import patcher
        compiler = _clang()
        if not compiler:
            self.skipTest('no clang for the aarch64 unit build')
        code, _ = compiled.compile_unit('vrotate', compiler)
        self.assertEqual(sorted(patcher.STORE_TARGET_WHITELIST), [0x40A08160])
        self.assertIn('state-window sentinel',
                      patcher.STORE_TARGET_WHITELIST[0x40A08160])
        from z8patch.contract import assert_no_cave_store_targets
        assert_no_cave_store_targets(bytes(code), CAVE_BASE, (CAVE_BASE, CAVE_LIMIT),
                                      patcher.STORE_TARGET_WHITELIST)
        # Without the whitelist the conservative window rejects exactly the
        # sentinel-arm store (its def sits before the forward cbnz).
        with self.assertRaisesRegex(ValueError, '0x40a08160'):
            assert_no_cave_store_targets(bytes(code), CAVE_BASE,
                                         (CAVE_BASE, CAVE_LIMIT))

    def test_org_directive_rejected_in_unit_sources(self):
        """D1 (A1 negative 1): any .org in a SPECS-declared unit source
        refuses the build; .balign/.space (legal in-unit padding/data)
        stay tolerated.  The scan takes the declared source set itself,
        never a filesystem glob."""
        import tempfile
        from z8patch.contract import assert_no_org_directives
        with tempfile.TemporaryDirectory() as folder:
            clean = Path(folder) / 'clean.S'
            clean.write_text('.balign 4\n.space 16\nlabel:\n nop\n')
            self.assertEqual(assert_no_org_directives([clean]), 1)
        # Each offending shape gets its own file: the scan raises on the
        # first hit, so shared files would couple the assertions.
        for name, source in (('pinned.S', 'start:\n nop\n.org 0x2F0\ntable:\n nop\n'),
                             # M-4: a label on the same line must not hide
                             # the directive.
                             ('inlined.S', 'entry: nop\ntable: .org 0x100\n nop\n')):
            with tempfile.TemporaryDirectory() as folder, \
                    self.subTest(source=name):
                doctored = Path(folder) / name
                doctored.write_text(source)
                with self.assertRaisesRegex(ValueError, name + r'.*\.org'):
                    assert_no_org_directives([doctored])
        # An empty declared set is a broken registry, not a clean scan.
        with self.assertRaisesRegex(ValueError, 'no unit assembly sources'):
            assert_no_org_directives([])

    def test_undeclared_asm_source_in_unit_directory_rejected(self):
        """D1 (A1 negative 2): a *.S sitting under a registered unit's
        source directory without a SPECS asm_sources declaration refuses
        the build -- an undeclared source silently escapes the .org scan
        even while carrying .org itself."""
        import tempfile
        from z8patch.compiled import assert_asm_sources_declared
        with tempfile.TemporaryDirectory() as folder:
            unit_dir = Path(folder) / 'z8probe' / 'src'
            unit_dir.mkdir(parents=True)
            declared = unit_dir / 'hooks.S'
            declared.write_text('start:\n nop\n')
            stray = unit_dir / 'extra.S'
            stray.write_text('entry: nop\n.org 0x100\n nop\n')
            with self.assertRaisesRegex(ValueError, r'extra\.S.*z8probe'):
                assert_asm_sources_declared([declared], [unit_dir])
            # Declared, the same file passes the completeness check (its
            # .org then fails the D1 scan itself, covered above).
            assert_asm_sources_declared([declared, stray], [unit_dir])

    def test_repo_assembly_sources_are_org_free(self):
        """The SPECS-driven scan list is exactly the 14 shipped unit
        sources (pinned above as transcribed evidence, independent of
        SPECS) and the real tree passes D1 on all of them."""
        from z8patch import compiled
        from z8patch.contract import assert_no_org_directives
        sources = compiled.unit_asm_sources()
        self.assertEqual([p.relative_to(ROOT).as_posix() for p in sources],
                         UNIT_ASM_SOURCE_LIST)
        self.assertEqual(len(UNIT_ASM_SOURCE_LIST), 14)
        self.assertEqual(assert_no_org_directives(sources), 14)

    def test_cross_region_pointer_rejects_non_entry_target(self):
        """D2: an emit-region qword inside a unit span that does not name a
        registered entry symbol refuses the build; the same qword naming a
        registered entry passes."""
        from z8patch.contract import assert_no_cross_region_pointers
        placements = [('vrotate', 0x40A08000, 0x40A08298,
                       {'vr_row_hook': 0x40A08070})]
        rows = [dict(offset=0x40A09000 - EG_BASE, end=0x40A09008 - EG_BASE,
                     new=struct.pack('<Q', 0x40A08074))]     # unit interior, not an entry
        with self.assertRaisesRegex(ValueError, '0x40a09000.*0x40a08074.*vrotate'):
            assert_no_cross_region_pointers(rows, placements)
        good = [dict(offset=0x40A09000 - EG_BASE, end=0x40A09008 - EG_BASE,
                     new=struct.pack('<Q', 0x40A08070))]     # vr_row_hook
        assert_no_cross_region_pointers(good, placements)

    def test_cross_region_pointer_skips_unit_span_bytes(self):
        """Qwords inside a unit's own span are the unit's business (internal
        self-references); only emit-region bytes outside unit spans sweep."""
        from z8patch.contract import assert_no_cross_region_pointers
        placements = [('vrotate', 0x40A08000, 0x40A08298,
                       {'vr_row_hook': 0x40A08070})]
        rows = [dict(offset=0x40A08000 - EG_BASE, end=0x40A08008 - EG_BASE,
                     new=struct.pack('<Q', 0x40A08074))]     # inside the unit span
        assert_no_cross_region_pointers(rows, placements)

    def test_registered_entry_mechanism(self):
        """Asm units register their .global hook labels; the C-unit contract
        names all exist in the frozen symbol tables inside their spans."""
        import json
        from z8patch import compiled
        from z8patch.contract import (C_UNIT_ENTRY_CONTRACT, asm_global_declarations,
                                      registered_unit_entries)
        sources = compiled.unit_sources('vrotate')
        self.assertTrue(all(p.name.endswith('.S') for p in sources))
        declared = asm_global_declarations(sources)
        self.assertEqual(sorted(n for n in declared if n.startswith('vr_')),
                         ['vr_latch_hook', 'vr_matrix_hook', 'vr_refresh_hook',
                          'vr_row_hook'])
        units = json.loads((ROOT / 'resources' / 'compiled.json').read_text())['units']
        for name, contract in C_UNIT_ENTRY_CONTRACT.items():
            symbols = {k: int(v['va'], 16) for k, v in units[name]['symbols'].items()}
            base = compiled.unit_base(name)
            registered = registered_unit_entries(name, symbols, compiled.unit_sources(name))
            self.assertEqual(sorted(registered), sorted(contract), name)
            for symbol, va in registered.items():
                self.assertTrue(base <= va < base + units[name]['bytes'], (name, symbol))

    def test_state_window_magic_doctored(self):
        """C: corrupting the fresh-boot magic byte in the built image must
        fail the composition contract."""
        from features import compose
        from z8prores.package import Package
        from z8patch.contract import verify_contract
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        compiler = _clang()
        if not compiler:
            self.skipTest('no clang for the aarch64 unit build')
        old = Package(FIRMWARE.read_bytes()).eg
        img, _, _ = compose(old, ['video-orientation'], compiler, 'source',
                            check_recipe=False)
        doctored = bytearray(img.new)
        doctored[VR_STATE_IMG_OFF + VR_MAGIC_OFF] ^= 1
        with self.assertRaisesRegex(ValueError, 'state window magic byte'):
            verify_contract(old, bytes(doctored), ['video-orientation'])

    def test_state_window_literal_doctored(self):
        """C: replacing the state-window base literal in the unit pool must
        fail the composition contract."""
        from features import compose
        from z8prores.package import Package
        from z8patch.contract import verify_contract
        if not FIRMWARE.is_file():
            self.skipTest('stock firmware fixture not present: %s' % FIRMWARE)
        compiler = _clang()
        if not compiler:
            self.skipTest('no clang for the aarch64 unit build')
        old = Package(FIRMWARE.read_bytes()).eg
        img, _, _ = compose(old, ['video-orientation'], compiler, 'source',
                            check_recipe=False)
        doctored = bytearray(img.new)
        unit = doctored[CAVE_BASE - EG_BASE:CAVE_BASE - EG_BASE + 664]
        needle = struct.pack('<Q', VR_STATE_VA)
        at = bytes(unit).find(needle)
        self.assertGreaterEqual(at, 0)
        doctored[CAVE_BASE - EG_BASE + at:CAVE_BASE - EG_BASE + at + 8] = \
            struct.pack('<Q', 0xDEAD0000DEAD0000)
        with self.assertRaisesRegex(ValueError, 'state window literal in the unit'):
            verify_contract(old, bytes(doctored), ['video-orientation'])


class DataMirrorReservationTests(unittest.TestCase):
    """T3 B: the two vrotate windows registered in the patcher-level
    reservation census (cave dimension and data-mirror segment dimension).

    The data-mirror table transcribes the t1 report Step 0b window census
    (32 documented module windows in EG [0x4B13000,0x4DC0000); the t1
    prose counted 33 but its own table holds 32 -- 28 rows, four of them
    dual-entry) -- the vrotate state window must be disjoint from all of
    them, and both vrotate windows must be stock zero at 8 B and 4 B
    granularity (dual caliber).
    """

    # (eg_start, eg_end, owner) -- data-mirror segment windows (t1 report
    # Step 0b, cross-checked against each owning patcher's constants).
    DATA_MIRROR_CENSUS = (
        (0x4B68258, 0x4B68298, 'opengate spare groups 22..25 (z8opengate/imenu.py)'),
        (0x4B75AC8, 0x4B75B08, 'opengate spare groups, second set (z8opengate/imenu.py)'),
        (0x4B95110, 0x4B95118, 'opengate i-menu title widget (z8opengate/imenu.py)'),
        (0x4B95150, 0x4B95318, 'opengate config read/write base (z8opengate/imenu.py)'),
        (0x4B95320, 0x4B95718, 'opengate N-RAW widget config pointers (z8opengate/imenu.py)'),
        (0x4B95748, 0x4B95B40, 'opengate widget config pointers 2 (z8opengate/imenu.py)'),
        (0x4B95B68, 0x4B95D30, 'opengate config base 2 (z8opengate/imenu.py)'),
        (0x4B95D30, 0x4B95EF8, 'opengate config base 3 (z8opengate/imenu.py)'),
        (0x4BB1770, 0x4BB1778, 'opengate title widget 2 (z8opengate/imenu.py)'),
        (0x4BB17B8, 0x4BB1BB0, 'opengate widget cfg pointers 3 (z8opengate/imenu.py)'),
        (0x4BB1BE0, 0x4BB1FD8, 'opengate widget cfg pointers 4 (z8opengate/imenu.py)'),
        (0x4BCC2C0, 0x4BCC2D0, 'shared video menu page rows/pointers/count (z8patch/shared.py PAGE+0x10)'),
        (0x4BCC720, 0x4BCC732, 'opengate frame-size page (z8opengate/patcher.py)'),
        (0x4BDAA40, 0x4BDAA90, 'pixelshift C5 page record (z8pixelshift/patcher.py)'),
        (0x4BF1670, 0x4BF1678, 'pixelshift photo menu entry callback (z8pixelshift/patcher.py)'),
        (0x4BF1690, 0x4BF1698, 'pixelshift refresh callback (z8pixelshift/patcher.py)'),
        (0x4BF1850, 0x4BF1878, 'pixelshift PS8 browser state callbacks (z8pixelshift/patcher.py)'),
        (0x4BF3380, 0x4BF33A8, 'pixelshift modal state callbacks (z8pixelshift/patcher.py)'),
        (0x4BF3A80, 0x4BF3A88, 'video 0xfe state refresh slot (z8prores/menu.py)'),
        (0x4BFFCC0, 0x4C08C00, 'menu state table, 0x60B x 0x17E records (z8prores/menu.py)'),
        (0x4C007F0, 0x4C007F8, 'pixelshift state 1Dh page pointer (z8pixelshift/patcher.py)'),
        (0x4C040C8, 0x4C040D0, 'log state B5h callbacks (z8log/patcher.py)'),
        (0x4C040F0, 0x4C040F8, 'log state B5h page pointer (z8log/patcher.py)'),
        (0x4C04128, 0x4C04130, 'anamorphic state B6h callbacks (z8anamorphic/patcher.py)'),
        (0x4C04150, 0x4C04158, 'anamorphic state B6h page pointer (z8anamorphic/patcher.py)'),
        (0x4C05DA8, 0x4C05DB0, 'prores state 0x102 callbacks (z8prores/menu.py)'),
        (0x4C05DD0, 0x4C05DD8, 'prores state 0x102 page pointer (z8prores/menu.py)'),
        (0x4C08BC8, 0x4C08BD0, 'h265 state 17Dh callbacks (z8h265/patcher.py)'),
        (0x4C08BE8, 0x4C08BF0, 'h265 state 17Dh page pointer (z8h265/patcher.py)'),
        (0x4C69B50, 0x4C6AA60, 'precapture callback slots 93,112..117,129,130 (z8precapture/patcher.py)'),
        (0x4D2FFC0, 0x4D2FFC4, 'precapture config word (z8precapture/patcher.py)'),
        (0x4D2FFCC, 0x4D2FFD0, 'precapture config word 2 (z8precapture/patcher.py)'),
    )

    def test_vrotate_state_window_disjoint_and_stock_zero(self):
        """The state window is inside the boot-copied data mirror segment,
        disjoint from every documented module window, and stock zero at both
        granularities; the patcher facts carry the same window."""
        from z8patch.image import DATA_OFF, DATA_END
        from z8vrotate import patcher
        self.assertEqual(patcher.VR_STATE_IMG_OFF, 0x4B25800)
        window = (patcher.VR_STATE_IMG_OFF,
                  patcher.VR_STATE_IMG_OFF + patcher.VR_STATE_SIZE)
        self.assertTrue(DATA_OFF <= window[0] and window[1] <= DATA_END)
        for start, end, owner in self.DATA_MIRROR_CENSUS:
            with self.subTest(owner=owner.split(' (')[0]):
                self.assertTrue(window[1] <= start or end <= window[0],
                                f'state window {window[0]:#x}-{window[1]:#x} overlaps {owner}')
        self.assertEqual(patcher.VR_STATE_VA + VR_STATE_SIZE, VR_STATE_END)
        if FIRMWARE.is_file():
            from z8prores.package import Package
            eg = Package(FIRMWARE.read_bytes()).eg
            span = eg[window[0]:window[1]]
            self.assertEqual(struct.unpack(f'<{len(span) // 8}Q', span),
                             (0,) * (len(span) // 8))
            self.assertEqual(struct.unpack(f'<{len(span) // 4}I', span),
                             (0,) * (len(span) // 4))

    def test_events_sub_window_registered_and_stock_zero(self):
        """The row-events fixed sub-window sits inside the vrotate cave
        reservation (a sub-window of it, so disjointness with other modules
        follows from the cave census row), is stock zero at both
        granularities, and the patcher facts carry the same window."""
        from z8vrotate import patcher
        self.assertEqual((patcher.VR_EVENTS_AT, patcher.VR_EVENTS_END),
                         (VR_EVENTS_AT, VR_EVENTS_END))
        self.assertTrue(patcher.CODE_AT < VR_EVENTS_AT
                        and VR_EVENTS_END <= patcher.CODE_END)
        # The sub-window must not eat into the unit's own capacity region:
        # it starts past every emitted unit end observed so far.
        self.assertGreaterEqual(VR_EVENTS_AT, patcher.CODE_AT + 664)
        if FIRMWARE.is_file():
            from z8prores.package import Package
            eg = Package(FIRMWARE.read_bytes()).eg
            span = eg[VR_EVENTS_AT - EG_BASE:VR_EVENTS_END - EG_BASE]
            self.assertEqual(struct.unpack(f'<{len(span) // 8}Q', span),
                             (0,) * (len(span) // 8))
            self.assertEqual(struct.unpack(f'<{len(span) // 4}I', span),
                             (0,) * (len(span) // 4))
            tail = eg[VR_EVENTS_END - EG_BASE:patcher.CODE_END - EG_BASE]
            self.assertEqual(tail, bytes(len(tail)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
