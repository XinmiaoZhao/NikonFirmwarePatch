#!/usr/bin/env python3
"""Calibrated tkhd display matrices for the video-orientation feature (T4).

Plus T5 unit tests (classify mirror, one-shot latch, unit build) and the
T6 menu-row tests: the 36-language title table, the 0x2FC0 transition-table
clone, the z8patch/shared.py extensions, and -- when the stock firmware
fixture and an aarch64-capable clang are present -- compilation, linking
and patcher edit generation for the vrotate cave unit with its synthesized
inline-toggle menu row.

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
    """36-language title table for the vrotate row (T6 Step 1).

    The titles derive offline from the official id 2458 ("Record camera
    orientation", the photo-side row of the same function) by swapping each
    language's camera word for its video word from id 2214 ("Video quality
    (N-RAW)"); the Japanese slot takes the 動画の prefix instead, and the
    seven Japanese fallback slots repeat it.  z8vrotate/translations.py
    documents the per-language derivation and carries the frozen-table
    fingerprint.
    """

    def test_spec_baseline_verbatim(self):
        """The four spec-baseline languages are pinned verbatim."""
        from z8vrotate import translations
        titles = translations.TITLES
        self.assertEqual(len(titles), 36)
        self.assertEqual(titles[0], '動画の縦横位置情報の記録')            # ja
        self.assertEqual(titles[1], 'Record video orientation')   # en
        self.assertEqual(titles[8], '记录视频方向')                # zh-CN
        self.assertEqual(titles[9], '記錄短片方向')                 # zh-TW

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
        hook = 0x40A20080                       # arbitrary in-cave stand-in
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
        events_va = 0x40A20800
        entries = {'shared_refresh': 0x40980100, 'shared_bank': 0x40980200}
        callbacks = {'vrotate': 0x40A20300}
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
        # The transition table clone landed in the cave and is registered.
        self.assertEqual(menu['row_table'], hex(entries['vr_row_events']))
        unit = bytes(img.new[CAVE_BASE - EG_BASE:CAVE_BASE - EG_BASE + len(code)])
        at = entries['vr_row_events'] - CAVE_BASE
        self.assertEqual(unit[at:at + 32 * 44], patcher.row_events(
            eg, patcher.menu_row(eg)[1], entries['vr_row_hook']))
        # The row value byte boots enabled; the string provider is registered
        # at id 3225 with the frozen title table.
        at = entries['vr_value'] - CAVE_BASE
        self.assertEqual(unit[at], 1)
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
        # Patch generation applies to the stock image: the two expect-byte
        # gates and the zero-cave check all pass.
        from z8patch.shared import Strings
        img, meta = patcher.build_main(eg, code, entries, Strings())
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
        # T5 review carry-items: the threshold load must be 4-byte aligned;
        # the gravity-vector literals in the pool must equal the patcher
        # constants; the assembled sentinel immediate must equal
        # patcher.SENTINEL_VALUE (both 0x5A materializations agree).
        self.assertEqual(entries['vr_threshold'] % 4, 0, entries['vr_threshold'])
        self.assertIn(struct.pack('<Q', patcher.ORIENT_VALID), code)
        self.assertIn(struct.pack('<Q', patcher.GRAVITY_VEC), code)
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
