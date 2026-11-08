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
  actions rerouted to vr_row_hook.
* T7: the row value is stored per movie shooting bank in byte +2 of the
  DS item 0x1257 record family (copy type 0, registered size 1 -- the
  same 4-byte slot whose +1 byte hosts the shipped H.265 tier constant).
  bank_records() re-pins the five record addresses from the stock bank
  tables and gates the build on them; the first-boot sentinel init
  (vr_default_on in hooks.S, mirrored by default_on()) defaults every
  bank to On.
"""
import struct

from z8patch.image import Image, BASE, branch, table_copy, data_off
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

# T7 per-bank storage: byte +2 of the DS item 0x1257 record family.  The
# item is registered with copy type 0 and size 1, so the stock bank-copy
# engine and the settings engine only ever touch byte +0; +1 already hosts
# the shipped H.265 tier byte (0xA03D5C269) and +2 is proven stock-unused
# in every copy (t7 report Step 0: zero literal / movz-chain materializations
# of any spare byte address across the whole EG).  Bank 0 is the active
# working record the menu reads and writes; banks 1..4 are the movie
# shooting-bank storages A-D (0x2d0 apart).  bank_records() re-derives
# these five addresses from the stock tables at build time.
BANK_ITEM, VALUE_OFF = 0x1257, 2
BANK_RECORDS = (0xA03D5C268, 0xA03D5C538, 0xA03D5C808, 0xA03D5CAD8, 0xA03D5CDA8)
VALUE_ADDR = BANK_RECORDS[0] + VALUE_OFF   # the active-record byte (0xA03D5C26A)
CATEGORY_TABLE, ITEM_TYPE_TABLE = 0x440244C8, 0x4400A5C0

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


def bank_records(eg):
    """Pin the five DS BANK_ITEM record addresses from the stock tables.

    Walks exactly what the stock bank machinery walks: the category record
    at CATEGORY_TABLE + (item >> 8) * 0x30 holds the bank descriptor at
    +0x20 (first byte = bank count, +0x10 = the record-pointer array, both
    RAM addresses inside the loader-copied data window); the resolver at
    0x410157e0 indexes that array with (item & 0xff) * banks + bank.  The
    item's type record (ITEM_TYPE_TABLE, 0x18-byte stride, global index =
    category base + item index) must stay copy type 0 size 1 -- the proof
    that only byte +0 of every record is stock-managed.
    """
    category, index = (BANK_ITEM >> 8) & 0xFF, BANK_ITEM & 0xFF
    record = CATEGORY_TABLE - BASE + category * 0x30
    first, count = struct.unpack_from('<HH', eg, record + 0x18)
    kind, size = struct.unpack_from('<II', eg,
                                    ITEM_TYPE_TABLE - BASE + (first + index) * 0x18)
    require(kind == 0 and size == 1, 'vrotate bank item is no longer one byte')
    descriptor = struct.unpack_from('<Q', eg, record + 0x20)[0]
    banks = eg[data_off(descriptor)]
    array = data_off(struct.unpack_from('<Q', eg, data_off(descriptor) + 0x10)[0])
    require(index < count and banks == len(BANK_RECORDS), 'vrotate bank category shape')
    records = struct.unpack_from('<%dQ' % banks, eg, array + 8 * (index * banks))
    require(records == BANK_RECORDS, 'vrotate bank record addresses moved')
    return records


def default_on(copies, sentinel):
    """Mirror of the vr_default_on first-boot init (hooks.S).

    copies models the five record bytes (active record first, then bank
    storages A-D).  A zero sentinel (fresh boot: the text loader re-copies
    the patched cave, so vr_sentinel starts 0 every power cycle) defaults
    every copy to 1 and arms the sentinel; an armed sentinel changes
    nothing, which is what keeps a user's Off alive for the session.
    """
    if sentinel == 0:
        return [1] * len(copies), SENTINEL_VALUE
    return list(copies), sentinel


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
    records = bank_records(eg)
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
    fill('vr_sentinel', b'\x00')
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
    img.put(CODE_AT, code, 'vrotate unit: matrix hook, latch hook, classifier, row hooks, default-on init, cave constants',
            expect_zero=True)
    return img, dict(entries={k: hex(v) for k, v in entries.items()}, code_bytes=len(code),
                     cave=[hex(CODE_AT), hex(CODE_AT + len(code))],
                     axis_codes=list(AXIS_CODES), threshold=hex(THRESHOLD_BITS),
                     sentinel=hex(SENTINEL_VALUE), matrix_bytes=len(VR_MATRICES),
                     storage=dict(item=hex(BANK_ITEM), value_off=VALUE_OFF,
                                  value_addr=hex(VALUE_ADDR),
                                  records=[hex(a) for a in records],
                                  power_off='default on (loader re-copies the cave each boot)'),
                     strings=text,
                     menu=dict(item=hex(ROW_ITEM), title_id=TITLE_ID, value_ids=(ON_ID, OFF_ID),
                               row_hex=row.hex(), row_table=hex(entries['vr_row_events']),
                               toggle_events=[hex(e) for e in TOGGLE_EVENTS],
                               template=hex(ATTEN_ITEM)))
