"""vrotate: pose-latched tkhd display matrices for movies (T5 + T6).

Builds the hooks from z8vrotate/src/hooks.S into the stock EG:

* 0x40cefd60: the single video-track tkhd matrix copy (`bl 0x40ce3fdc`)
  becomes `bl vr_matrix_hook`; the hook redirects x1 to a cave matrix when
  the one-shot latch holds a valid pose code, otherwise passes x1 through.
* 0x40d17728: the recording-side file open marshaling trampoline entry
  becomes `b vr_latch_hook` + nop; on the main-movie write open (w1 == 1)
  the hook classifies the gravity vector and latches the pose code.
* T6: the synthesized inline-toggle menu row 0x315B (title id 3225,
  36-language table in translations.py, value pair = official ids
  2466/2467) cloned field-for-field from the stock attenuator row 0x2FC0,
  with its transition table cloned into the cave and the three toggle
  actions rerouted to vr_row_hook.  Bank storage is T7.
"""
import struct

from z8patch.image import Image, BASE, branch, table_copy
from z8patch.shared import STRING_IDS
from z8prores.package import require

from . import matrices, translations

CODE_AT, CODE_END = 0x40A20000, 0x40A22000
# Matrix hook: single video-track tkhd matrix copy site (t3 report).
MATRIX_SITE, MATRIX_STOCK_WORD = 0x40cefd60, 0x97FFD09F
# Latch hook: recording-side file open marshaling trampoline entry (t2 report).
LATCH_SITE, LATCH_RESUME = 0x40d17728, 0x40d17730
LATCH_STOCK = bytes.fromhex('08de80d28863a0f2')
# T1 anchors: sensor-subsystem gate word and normalised gravity vector f32 x3.
ORIENT_VALID, GRAVITY_VEC = 0x0A02E56018, 0x0A02E560E0
THRESHOLD_BITS = 0x3F333333        # IEEE754 bits of 0.70f (dominant-axis gate)
SENTINEL_VALUE = 0x5A              # must equal VR_SENTINEL_VALUE in hooks.S;
                                    # test_unit_builds pins both materializations
NOP = struct.pack('<I', 0xD503201F)

# T6 menu row: cloned from the stock audio attenuator row (item 0x2FC0,
# row index 35 of the 44-row video menu table, class word 0x20901005).
ROW_ITEM, TITLE_ID = 0x315B, 3225
ON_ID, OFF_ID = 2466, 2467          # official localized On/Off, all 36 languages
ATTEN_ITEM = 0x2FC0
ATTEN_ROW = (0x567, 0xFFFF, 0xFFFF, 0, 0x20901005, 0x1327, 0x2FC0,
             0x40004, 0xFFFFFFFF, 0xFFFFFFFF, 2)
ATTEN_EVENTS = 0x43C33EF0          # the template row's transition table
TOGGLE_ACTION = 0x405707D4         # stock inline-toggle action (flip DS + redraw)
TOGGLE_EVENTS = (0x286, 0x28B, 0x2AE)   # OK / press-and-hold / touch
ROW_EVENT_COUNT = 44               # transition records incl. the 0x3BB terminator
ROWS_AT, EVENTS_AT = 0x3AA4758, 0x3AA4EE8   # stock row / pointer tables (EG offsets)
TABLE_DIR, BLOB_DIR, STOCK_IDS = 0x311C5A0, 0x387AF58, 3137

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


def menu_row(eg):
    """The 0x2FC0 template row and its transition-table pointer (T6 Step 0)."""
    rows = [struct.unpack_from('<11I', eg, ROWS_AT + 44 * i) for i in range(44)]
    found = [i for i, r in enumerate(rows) if r[6] == ATTEN_ITEM]
    require(found == [35] and rows[35] == ATTEN_ROW, 'vrotate attenuator template row')
    pointer = struct.unpack_from('<Q', eg, EVENTS_AT + 8 * 35)[0]
    require(pointer == ATTEN_EVENTS, 'vrotate attenuator transition table')
    return rows[35], pointer


def row_events(eg, pointer, hook):
    """Clone the template transition table; only the toggle action moves to the cave."""
    seen = []

    def change(event, action, guard, target):
        if action == TOGGLE_ACTION:
            seen.append(event)
            return event, hook, guard, target
        return event, action, guard, target

    table = table_copy(eg, pointer, change)
    require(len(table) == 32 * ROW_EVENT_COUNT and tuple(seen) == TOGGLE_EVENTS,
            'vrotate row transition table')
    return table


def strings(eg, context):
    """Register the 36-language title at id 3225 after proving every glyph.

    Each title recombines words of the same language's own stock strings
    (ids 2458 and 2214 among them), so the glyph containment below should
    never fail on the genuine C3.11 payload; it guards a bad table edit.
    """
    require(STRING_IDS['vrotate'] == (TITLE_ID, 1), 'vrotate string slot')
    for language, title in enumerate(translations.TITLES):
        table = struct.unpack_from('<Q', eg, TABLE_DIR + 8 * language)[0] - BASE
        blob = struct.unpack_from('<Q', eg, BLOB_DIR + 8 * language)[0] - BASE
        offsets = struct.unpack_from(f'<{STOCK_IDS}i', eg, table)
        corpus = ''.join(eg[blob + offsets[i]:blob + offsets[i + 1]].decode('utf-16le')
                         for i in range(STOCK_IDS - 1))
        require(set(title) <= set(corpus), 'vrotate title glyph missing: %d' % language)
    ids = context.add('vrotate', [[title] for title in translations.TITLES])
    require(ids == [TITLE_ID], 'vrotate string allocation')
    return dict(ids=ids, fingerprint=translations.FINGERPRINT)


def build_main(eg, code, entries, context):
    """Emit the vrotate unit, its two gated edits and the synthesized menu row."""
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
    fill('vr_value', b'\x01')
    template, pointer = menu_row(eg)
    fill('vr_row_events', row_events(eg, pointer, entries['vr_row_hook']))
    text = strings(eg, context)
    row = struct.pack('<11I', TITLE_ID, *template[1:6], ROW_ITEM, *template[7:])
    require(CODE_AT + len(code) <= CODE_END, 'vrotate code capacity')
    img.put(MATRIX_SITE, branch(MATRIX_SITE, entries['vr_matrix_hook'], link=True),
            'movie tkhd matrix copy: bl 0x40ce3fdc -> bl vr_matrix_hook',
            expect=struct.pack('<I', MATRIX_STOCK_WORD))
    img.put(LATCH_SITE, branch(LATCH_SITE, entries['vr_latch_hook']) + NOP,
            'record file open trampoline: mov/movk x8 pair -> b vr_latch_hook + nop',
            expect=LATCH_STOCK)
    img.put(CODE_AT, code, 'vrotate unit: matrix hook, latch hook, classifier, row hooks, cave constants',
            expect_zero=True)
    return img, dict(entries={k: hex(v) for k, v in entries.items()}, code_bytes=len(code),
                     cave=[hex(CODE_AT), hex(CODE_AT + len(code))],
                     axis_codes=list(AXIS_CODES), threshold=hex(THRESHOLD_BITS),
                     sentinel=hex(SENTINEL_VALUE), matrix_bytes=len(VR_MATRICES),
                     strings=text,
                     menu=dict(item=hex(ROW_ITEM), title_id=TITLE_ID, value_ids=(ON_ID, OFF_ID),
                               row_hex=row.hex(), row_table=hex(entries['vr_row_events']),
                               toggle_events=[hex(e) for e in TOGGLE_EVENTS],
                               template=hex(ATTEN_ITEM), value_byte=1))
