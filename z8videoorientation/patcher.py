"""video-orientation: pose-latched tkhd display matrices for movies.

Builds the hooks from z8videoorientation/src/hooks.S into the stock EG:

* 0x40cefd60: the single video-track tkhd matrix copy (`bl 0x40ce3fdc`)
  becomes `bl orient_matrix_hook`; the hook redirects x1 to a cave matrix when
  the sticky latch holds a valid pose code, otherwise passes x1 through
  (the latch is never read-and-cleared here -- every
  moov build of the take must see the same pose).
* 0x40d17728: the recording-side file open marshaling trampoline entry
  becomes `b orient_latch_hook` + nop; the main-movie write open (w1 == 1)
  classifies the gravity vector and refreshes the pose latch, and the
  session-boundary opens (w1 == 0 read-parse, w1 == 2 post-finalize udta
  patch) clear it, so the sticky pose never outlives the take.
* 0x40ce4294: the stock add-track entry becomes `b orient_track_hook`;
  every movie writer -- including the 8-bit legacy pipeline's remux writer
  whose opens bypass the recording-side trampoline -- refreshes the pose
  at its track registration, so no deliverable can carry a previous take's
  frozen pose.
* The synthesized inline-toggle menu row 0x315B (title id 3225,
  36-language table in translations.py) cloned field-for-field from
  the stock attenuator row 0x2FC0, with its transition table cloned
  into the fixed cave sub-window and the three toggle
  actions rerouted to orient_row_hook.
* The row value is stored per movie shooting bank in byte +2 of the
  DS item 0x1257 record family (copy type 0, registered size 1 -- the
  same 4-byte slot whose +1 byte hosts the shipped H.265 tier constant).
  bank_records() re-pins the five record addresses from the stock bank
  tables and gates the build on them; the first-boot sentinel init
  (orient_default_on in hooks.S, mirrored by default_on()) defaults every
  bank to On.

State-window migration: the five unit data
labels (orient_matrices, orient_axis_codes, orient_threshold, orient_latch, orient_sentinel)
live in a 256 B window of the boot-loaded data mirror segment, not in
the read-only cave.  The window was picked by a four-leg zero-writer
census of the stock image; the boot segment loader record
{len=0x2AD000, dst=0xA02808000} re-copies it from the image every power
cycle, so the latch and sentinel mirror bytes ship 0 (fresh-boot state)
and the window tail carries the 0xA5 magic byte that witnesses a real
boot copy.  hooks.S receives the label VAs through -D defines
(asm_defines, the z8log asm_defines precedent).

Fixed events sub-window: the row-events transition-table clone
rides its own image edit at the fixed cave sub-window ORIENT_EVENTS_AT =
0x40A09000 (the z8h265 MENU_AT form) instead of an organic in-unit
slot -- unit growth is decoupled from the frozen external rows that
name the table.

The row value renders through the stock boolean value widget
0x405121E4(child, byte) -- the attenuator row's own path.  The string-id
call 0x403F645C(child, 2466/2467) is unusable here: the 0x1327
value-child template runs mode==3 and truncates string ids above 299.
"""
import struct

from z8patch.image import Image, BASE, branch, table_copy, data_off
from z8patch.shared import STRING_IDS
from z8patch.contract import assert_no_cave_store_targets
from z8prores.package import require

from . import matrices, translations

CODE_AT, CODE_END = 0x40A08000, 0x40A10000   # see hooks.S header and ReservationCensusTests
# Matrix hook: the single video-track tkhd matrix copy site.
MATRIX_SITE, MATRIX_STOCK_WORD = 0x40cefd60, 0x97FFD09F
# Latch hook: recording-side file open marshaling trampoline entry.
LATCH_SITE, LATCH_RESUME = 0x40d17728, 0x40d17730
LATCH_STOCK = bytes.fromhex('08de80d28863a0f2')
# Track hook: the stock add-track entry FUN_40ce4294.  Every movie
# writer registers its tracks here -- engine, PRF worker and the 8-bit
# legacy pipeline's remux writer whose file opens bypass the recording-side
# trampoline entirely (camera evidence: every 8-bit take carried
# the previous live take's frozen sticky pose).  The hook refreshes the pose
# at every writer start; the 8-bit deliverable writer registers post-stop,
# with the orientation sensors live again.
TRACK_SITE, TRACK_RESUME = 0x40ce4294, 0x40ce4298
TRACK_STOCK_WORD = 0xF81A0FFC      # str x28, [sp, #-0x60]!
# Sensor anchors: the subsystem enable byte and the gravity vector f32 x3.
ORIENT_VALID, GRAVITY_VEC = 0x0A02E56018, 0x0A02E560E0
THRESHOLD_BITS = 0x3F333333        # IEEE754 bits of 0.70f (dominant-axis gate)
SENTINEL_VALUE = 0x5A              # must equal ORIENT_SENTINEL_VALUE in hooks.S;
                                    # test_unit_builds pins both materializations
NOP = struct.pack('<I', 0xD503201F)

# State window (design facts, a four-leg zero-writer census):
# RAM [0xA0281A800,0xA0281A900) inside the boot-loaded data mirror segment,
# EG image [0x4B25800,0x4B25900).  The boot segment loader re-copies the
# window from the image every power cycle; EL0 code can write it.  The
# offsets below are the frozen window layout (facts.state_window, pinned
# by tests/test_videoorientation.py StateWindowTests).
ORIENT_STATE_VA, ORIENT_STATE_SIZE = 0xA0281A800, 0x100
ORIENT_STATE_END = ORIENT_STATE_VA + ORIENT_STATE_SIZE
ORIENT_STATE_IMG_OFF = 0x4B25800       # = ORIENT_STATE_VA - DATA_VA + DATA_OFF; build_main pins it
ORIENT_MATRICES_OFF, ORIENT_THRESHOLD_OFF = 0x00, 0x6C
ORIENT_AXIS_CODES_OFF, ORIENT_LATCH_OFF, ORIENT_SENTINEL_OFF = 0x70, 0x76, 0x77
ORIENT_MAGIC_OFF, ORIENT_MAGIC = 0xFF, 0xA5  # power-cycle boot-copy witness byte
STATE_LABELS = ('orient_matrices', 'orient_axis_codes', 'orient_threshold', 'orient_latch', 'orient_sentinel')

# Fixed sub-window for the row-events transition-table clone (the
# z8h265 MENU_AT form): the 44x32 B table rides its own expect_zero image
# edit at a patcher-constant cave address, so unit code/pool growth can
# never move any external frozen byte that names the table.  4K-aligned,
# inside the video-orientation cave, stock zero.
ORIENT_EVENTS_AT = 0x40A09000
ORIENT_EVENTS_END = ORIENT_EVENTS_AT + 44 * 32

# Store-target whitelist: store addresses whose base cannot be resolved in
# their basic block (the window ends at every control transfer) but are
# proven safe.  The shipped unit has exactly one such store: the sentinel-
# arm write at 0x40A08160 (strb w8, [x10]) -- its base def
# `ldr x10, #0x40a08250` at 0x40a08150 loads the STATE-WINDOW sentinel byte
# (0xA0281A877, outside the cave), and the only intervening transfer,
# `cbnz w8, #0x40a08190`, forwards past the whole 0x40a0815c..0x40a0818c
# init series -- every path reaching the store flows through the def.
# Any new entry needs a reason string that names the proof; a stale entry
# simply stops matching when unit code shifts (the shifted store then gets
# full checking again).  See z8patch.contract.assert_no_cave_store_targets.
STORE_TARGET_WHITELIST = {0x40A08160: 'sentinel-arm store: base is the state-window sentinel literal 0xA0281A877 loaded at 0x40a08150; the intervening cbnz (0x40a08158) forwards to 0x40a08190 past the entire init store series, so the def dominates the store on every path'}

# Menu row: cloned from the stock audio attenuator row (item 0x2FC0,
# row index 35 of the 44-row video menu table, class word 0x20901005).
ROW_ITEM, TITLE_ID = 0x315B, 3225
# Value-render path: the stock boolean value widget takes the row's
# value child and the value byte itself (1 = On / 0 = Off; internal ids
# 0x125A/0x125C) -- the attenuator row's own path.  The retired string-id
# call truncated ids above 299 on the mode==3 0x1327 child template
# (the mode==3 truncation).
VALUE_WIDGET, RETIRED_VALUE_ID_CALL = 0x405121E4, 0x403F645C
ATTEN_ITEM = 0x2FC0
ATTEN_ROW = (0x567, 0xFFFF, 0xFFFF, 0, 0x20901005, 0x1327, 0x2FC0,
             0x40004, 0xFFFFFFFF, 0xFFFFFFFF, 2)
ATTEN_EVENTS = 0x43C33EF0          # the template row's transition table
TOGGLE_ACTION = 0x405707D4         # stock inline-toggle action (flip DS + redraw)
TOGGLE_EVENTS = (0x286, 0x28B, 0x2AE)   # OK / press-and-hold / touch
ROW_EVENT_COUNT = 44               # transition records incl. the 0x3BB terminator
ROWS_AT, EVENTS_AT = 0x3AA4758, 0x3AA4EE8   # stock row / pointer tables (EG offsets)
TABLE_DIR, BLOB_DIR, STOCK_IDS = 0x311C5A0, 0x387AF58, 3137

# Per-bank storage: byte +2 of the DS item 0x1257 record family.  The
# item is registered with copy type 0 and size 1, so the stock bank-copy
# engine and the settings engine only ever touch byte +0; +1 already hosts
# the shipped H.265 tier byte (0xA03D5C269) and +2 is proven stock-unused
# in every copy (a zero-hit scan of literal and movz-chain materializations
# of any spare byte address across the whole EG).  Bank 0 is the active
# working record the menu reads and writes; banks 1..4 are the movie
# shooting-bank storages A-D (0x2d0 apart).  bank_records() re-derives
# these five addresses from the stock tables at build time.
BANK_ITEM, VALUE_OFF = 0x1257, 2
BANK_RECORDS = (0xA03D5C268, 0xA03D5C538, 0xA03D5C808, 0xA03D5CAD8, 0xA03D5CDA8)
VALUE_ADDR = BANK_RECORDS[0] + VALUE_OFF   # the active-record byte (0xA03D5C26A)
CATEGORY_TABLE, ITEM_TYPE_TABLE = 0x440244C8, 0x4400A5C0

# [axis*2 + sign] -> own pose code.  On-camera evidence (the NEV take
# matrices identify the fired lanes exactly): chip X is the camera vertical
# axis and chip Y is the roll axis,
#   +X=3 (upside-down grip -> 180 deg), -X=0 (level landscape, no mark),
#   +Y=1 / -Y=2 (the two portrait grips; EXIF-6/-8 semantics).
# The portrait pair order follows the camera rounds: the first confirmed
# the X lanes, the second marked both grips with swapped
# directions and settled the byte 2/3 order.  Fully empirical.
AXIS_CODES = bytes((3, 0, 1, 2, 0, 0))

# Codes 1..3 only: code 0 / invalid is a passthrough, the stock identity
# blob already on the stack covers it.  Big-endian 16.16 words as written.
ORIENT_MATRICES = (matrices.ORIENT_TO_MATRIX[1] + matrices.ORIENT_TO_MATRIX[2]
               + matrices.ORIENT_TO_MATRIX[3])


def asm_defines():
    """-D defines for hooks.S: the absolute RAM VAs of the five unit data
    labels inside the state window (z8patch.compiled injects these when it
    compiles the video-orientation unit, the z8log asm_defines precedent)."""
    return dict(ORIENT_MATRICES_RAM=ORIENT_STATE_VA + ORIENT_MATRICES_OFF,
                ORIENT_THRESHOLD_RAM=ORIENT_STATE_VA + ORIENT_THRESHOLD_OFF,
                ORIENT_AXIS_CODES_RAM=ORIENT_STATE_VA + ORIENT_AXIS_CODES_OFF,
                ORIENT_LATCH_RAM=ORIENT_STATE_VA + ORIENT_LATCH_OFF,
                ORIENT_SENTINEL_RAM=ORIENT_STATE_VA + ORIENT_SENTINEL_OFF)


def classify(gate, x, y, z):
    """Mirror of the orient_classify routine; returns the pose code 0..3.

    Same algorithm and state-window constants as the assembled unit: gate
    word must be 1, sign bits stripped, magnitudes compared as unsigned
    float bits, argmax with the x-beats-y-beats-z tie-break, dominant axis
    at or above THRESHOLD_BITS, code = AXIS_CODES[axis*2 + sign].  Byte-level
    agreement with the unit is asserted by the emulator rounds and the
    StateWindowTests mirror-parity vectors.
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
    """Mirror of orient_matrix_hook's sticky-latch decision.

    Returns (matrix or None, latch): the latch is returned UNCHANGED --
    every moov build of the same take (placeholder/recovery rebuilds into
    the reserved front-slot, a proxy writer finalising in the same stop
    window, a staged remux) must see the same pose, because the file's
    final bytes come from the LAST pass (the retired read-and-clear fed
    every pass after the first the stock identity -- the on-camera
    H.265/H.264/MP4/ProRes loss).  Stale-pose protection lives in
    latch_open(): the recording-session boundaries (read-parse open
    w1==0, post-finalize udta-patch open w1==2) clear the byte, so
    non-recording finalizes that reuse the matrix site see 0.
    None means the hook passes the stock identity x1 through.
    """
    if enable and 1 <= latch <= 3:
        return ORIENT_MATRICES[(latch - 1) * 36:latch * 36], latch
    return None, latch


def latch_open(mode, gate, x, y, z):
    """Mirror of orient_latch_hook's session-scoped refresh/clear.

    mode is the open mode word (w1 at 0x40d17728): 1 = main-movie write
    open (recording start) refreshes the pose through the classifier;
    0 = read-parse and 2 = the post-finalize udta-patch open are
    recording-session boundaries and clear the sticky latch so the pose
    never leaks into a later non-recording finalize.
    """
    if mode != 1:
        return 0
    return classify(gate, x, y, z)


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
    require(kind == 0 and size == 1, 'video-orientation bank item is no longer one byte')
    descriptor = struct.unpack_from('<Q', eg, record + 0x20)[0]
    banks = eg[data_off(descriptor)]
    array = data_off(struct.unpack_from('<Q', eg, data_off(descriptor) + 0x10)[0])
    require(index < count and banks == len(BANK_RECORDS), 'video-orientation bank category shape')
    records = struct.unpack_from('<%dQ' % banks, eg, array + 8 * (index * banks))
    require(records == BANK_RECORDS, 'video-orientation bank record addresses moved')
    return records


def default_on(copies, sentinel):
    """Mirror of the orient_default_on first-boot init (hooks.S).

    copies models the five record bytes (active record first, then bank
    storages A-D).  A zero sentinel (fresh boot: the boot segment loader
    re-copies the data mirror state window from the image, so the sentinel
    byte starts 0 every power cycle) defaults every copy to 1 and arms the
    sentinel; an armed sentinel changes
    nothing, which is what keeps a user's Off alive for the session.
    """
    if sentinel == 0:
        return [1] * len(copies), SENTINEL_VALUE
    return list(copies), sentinel


def menu_row(eg):
    """The 0x2FC0 template row and its transition-table pointer ."""
    rows = [struct.unpack_from('<11I', eg, ROWS_AT + 44 * i) for i in range(44)]
    found = [i for i, r in enumerate(rows) if r[6] == ATTEN_ITEM]
    require(found == [35] and rows[35] == ATTEN_ROW, 'video-orientation attenuator template row')
    pointer = struct.unpack_from('<Q', eg, EVENTS_AT + 8 * 35)[0]
    require(pointer == ATTEN_EVENTS, 'video-orientation attenuator transition table')
    return rows[35], pointer


def row_events(eg, pointer, hook):
    """Clone the template transition table; only the toggle action moves to orient_row_hook."""
    seen = []

    def change(event, action, guard, target):
        if action == TOGGLE_ACTION:
            seen.append(event)
            return event, hook, guard, target
        return event, action, guard, target

    table = table_copy(eg, pointer, change)
    require(len(table) == 32 * ROW_EVENT_COUNT and tuple(seen) == TOGGLE_EVENTS,
            'video-orientation row transition table')
    return table


def strings(eg, context):
    """Register the 36-language title at id 3225 after proving every glyph.

    Each title recombines words of the same language's own stock strings
    (ids 2458 and 2214 among them), so the glyph containment below should
    never fail on the genuine C3.11 payload; it guards a bad table edit.
    """
    require(STRING_IDS['video-orientation'] == (TITLE_ID, 1), 'video-orientation string slot')
    for language, title in enumerate(translations.TITLES):
        table = struct.unpack_from('<Q', eg, TABLE_DIR + 8 * language)[0] - BASE
        blob = struct.unpack_from('<Q', eg, BLOB_DIR + 8 * language)[0] - BASE
        offsets = struct.unpack_from(f'<{STOCK_IDS}i', eg, table)
        corpus = ''.join(eg[blob + offsets[i]:blob + offsets[i + 1]].decode('utf-16le')
                         for i in range(STOCK_IDS - 1))
        require(set(title) <= set(corpus), 'video-orientation title glyph missing: %d' % language)
    ids = context.add('video-orientation', [[title] for title in translations.TITLES])
    require(ids == [TITLE_ID], 'video-orientation string allocation')
    return dict(ids=ids, fingerprint=translations.FINGERPRINT)


def build_main(eg, code, entries, context):
    """Emit the video-orientation unit, its two gated edits, the state window and the synthesized menu row."""
    require(len(ORIENT_MATRICES) == 108 and len(AXIS_CODES) == 6, 'video-orientation unit constants')
    require(not any(eg[CODE_AT - BASE:CODE_END - BASE]), 'video-orientation cave not free in stock image')
    require(data_off(ORIENT_STATE_VA) == ORIENT_STATE_IMG_OFF
            and ORIENT_STATE_IMG_OFF + ORIENT_STATE_SIZE == 0x4B25900, 'video-orientation state window image offset')
    require(not any(eg[ORIENT_STATE_IMG_OFF:ORIENT_STATE_IMG_OFF + ORIENT_STATE_SIZE]),
            'video-orientation state window not free in stock image')
    records = bank_records(eg)
    img = Image(eg)
    code = bytearray(code)
    # Store-target census: refuse the build if any data store in the assembled unit
    # resolves into the read-only cave -- the original EL0 crash class.
    assert_no_cave_store_targets(bytes(code), CODE_AT, (CODE_AT, CODE_END),
                                 STORE_TARGET_WHITELIST)
    # State-window guards: the data labels must not live in the cave unit
    # any more, and the unit must address the window through pool literals.
    for name in STATE_LABELS:
        require(name not in entries, 'video-orientation state label must not stay in the cave: ' + name)
    for off in (ORIENT_MATRICES_OFF, ORIENT_THRESHOLD_OFF, ORIENT_AXIS_CODES_OFF, ORIENT_LATCH_OFF,
                ORIENT_SENTINEL_OFF):
        require(struct.pack('<Q', ORIENT_STATE_VA + off) in code,
                'video-orientation state window literal missing from the unit: +%#x' % off)
    # The row-events clone rides its own fixed sub-window ; the unit is
    # pure code + pool and must stop short of that window, whose tail stays
    # stock zero.
    require(ORIENT_EVENTS_AT % 0x1000 == 0 and CODE_AT < ORIENT_EVENTS_AT
            and ORIENT_EVENTS_END <= CODE_END, 'video-orientation events window placement')
    require(not any(eg[ORIENT_EVENTS_AT - BASE:CODE_END - BASE]),
            'video-orientation events window not free in stock image')

    template, pointer = menu_row(eg)
    events = row_events(eg, pointer, entries['orient_row_hook'])
    text = strings(eg, context)
    row = struct.pack('<11I', TITLE_ID, *template[1:6], ROW_ITEM, *template[7:])
    require(CODE_AT + len(code) <= ORIENT_EVENTS_AT, 'video-orientation code capacity')
    # State window fill: constants land in the boot-copied data mirror image;
    # the sticky latch and the first-boot sentinel ship 0 (fresh boot), and
    # the window tail byte is the 0xA5 magic (a power-cycle boot-copy
    # witness -- zero-initialized RAM cannot read 0xA5 back).
    window = bytearray(ORIENT_STATE_SIZE)
    window[ORIENT_MATRICES_OFF:ORIENT_MATRICES_OFF + len(ORIENT_MATRICES)] = ORIENT_MATRICES
    window[ORIENT_THRESHOLD_OFF:ORIENT_THRESHOLD_OFF + 4] = struct.pack('<I', THRESHOLD_BITS)
    window[ORIENT_AXIS_CODES_OFF:ORIENT_AXIS_CODES_OFF + len(AXIS_CODES)] = AXIS_CODES
    window[ORIENT_LATCH_OFF] = 0
    window[ORIENT_SENTINEL_OFF] = 0
    window[ORIENT_MAGIC_OFF] = ORIENT_MAGIC
    img.put(MATRIX_SITE, branch(MATRIX_SITE, entries['orient_matrix_hook'], link=True),
            'movie tkhd matrix copy: bl 0x40ce3fdc -> bl orient_matrix_hook',
            expect=struct.pack('<I', MATRIX_STOCK_WORD))
    img.put(LATCH_SITE, branch(LATCH_SITE, entries['orient_latch_hook']) + NOP,
            'record file open trampoline: mov/movk x8 pair -> b orient_latch_hook + nop',
            expect=LATCH_STOCK)
    img.put(TRACK_SITE, branch(TRACK_SITE, entries['orient_track_hook']),
            'movie add-track entry: str x28,[sp,#-0x60]! -> b orient_track_hook (pose refresh at every writer start)',
            expect=struct.pack('<I', TRACK_STOCK_WORD))
    img.put(CODE_AT, code, 'video-orientation unit: matrix hook, latch hook, classifier, row hooks, default-on init',
            expect_zero=True)
    img.put(ORIENT_EVENTS_AT, events,
            'video-orientation row transition table: 44-record clone of the 0x2FC0 table, three toggle actions -> orient_row_hook (fixed cave sub-window)',
            expect_zero=True)
    img.put(ORIENT_STATE_IMG_OFF, bytes(window),
            'video-orientation state window: display matrices, threshold, axis codes, sticky latch, first-boot sentinel and magic byte (boot-copied data mirror segment)',
            expect_zero=True, offset=True)
    return img, dict(entries={k: hex(v) for k, v in entries.items()}, code_bytes=len(code),
                     cave=[hex(CODE_AT), hex(CODE_AT + len(code))],
                     events_window=[hex(ORIENT_EVENTS_AT), hex(ORIENT_EVENTS_END)],
                     state_window=[hex(ORIENT_STATE_VA), hex(ORIENT_STATE_VA + ORIENT_STATE_SIZE)],
                     state=dict(matrices=hex(ORIENT_STATE_VA + ORIENT_MATRICES_OFF),
                                threshold=hex(ORIENT_STATE_VA + ORIENT_THRESHOLD_OFF),
                                axis_codes=hex(ORIENT_STATE_VA + ORIENT_AXIS_CODES_OFF),
                                latch=hex(ORIENT_STATE_VA + ORIENT_LATCH_OFF),
                                sentinel=hex(ORIENT_STATE_VA + ORIENT_SENTINEL_OFF),
                                magic='%s@+%#x' % (hex(ORIENT_MAGIC), ORIENT_MAGIC_OFF)),
                     axis_codes=list(AXIS_CODES), threshold=hex(THRESHOLD_BITS),
                     sentinel=hex(SENTINEL_VALUE), matrix_bytes=len(ORIENT_MATRICES),
                     storage=dict(item=hex(BANK_ITEM), value_off=VALUE_OFF,
                                  value_addr=hex(VALUE_ADDR),
                                  records=[hex(a) for a in records],
                                  power_off='default on (the boot loader re-copies the state window each power cycle)'),
                     strings=text,
                     menu=dict(item=hex(ROW_ITEM), title_id=TITLE_ID,
                               value_widget=hex(VALUE_WIDGET),
                               row_hex=row.hex(), row_table=hex(ORIENT_EVENTS_AT),
                               toggle_events=[hex(e) for e in TOGGLE_EVENTS],
                               template=hex(ATTEN_ITEM)))
