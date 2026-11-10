/* vrotate patch unit (T5): pose-latched tkhd display matrices for movies.
 *
 * Two hooks plus a classifier in cave 0x40A08000..0x40A10000 (SPECS 'vrotate',
 * z8patch/compiled.py).  Cave choice (T8, controller-approved after two
 * collisions): 0x40A20000 is the quality group's icon PNG area
 * (z8quality/patcher.py PNG=0x40A20000, reserved to 0x40A30000, frozen
 * v0.4.0 recipe data) and 0x40A12000-0x40A1F000 is the H.265 menu-data
 * area (z8h265/patcher.py MENU_AT/AREA_END) -- do not reuse either.  This
 * cave sits between the ProRes GUI ceiling (z8prores/menu.py TEXT_AT = VA
 * 0x40A04000, enforced by that module's own overflow guard) and the H.265
 * code base 0x40A10000; ReservationCensusTests in tests/test_vrotate.py
 * pins the full reservation census and fails loudly on any overlap.
 * All firmware evidence addresses below are stock EG
 * virtual addresses (BASE 0x40160000) from the vrotate reports
 * .superpowers/sdd/2026-11-08-vrotate/reports/ (t1 anchor, t2 latch site,
 * t3 serialize trace, t7 storage).
 *
 * vr_matrix_hook -- replaces the stock `bl 0x40ce3fdc` (word 0x97ffd09f) at
 *   0x40cefd60, the single video-track tkhd matrix copy inside
 *   movie_build_videotrack_atoms (0x40cef3d0); every container mode
 *   (MOV/MP4/N-RAW) and codec funnels through it (t3 report).  Registers on
 *   entry: x0 = ctx+0x128 destination node, x1 = &stack identity blob,
 *   x2 = 0x24.  If the per-bank value byte at VR_VALUE is non-zero and the
 *   latch holds a valid code 1..3, x1 is redirected to
 *   vr_matrices+(code-1)*36 (36-byte big-endian 16.16 QuickTime display
 *   matrix; 1 = 90 deg CW, 2 = 90 deg CCW, 3 = 180; 0/invalid =
 *   passthrough).  The latch is STICKY (2026-11-10 t15 fix): the hook
 *   reads it but never clears it, so every moov build of the same take
 *   (placeholder/recovery rebuilds into the reserved front-slot, a proxy
 *   writer finalising in the same stop window, a staged remux) sees the
 *   same pose -- the file's final bytes come from the LAST pass and the
 *   retired read-and-clear fed every pass after the first the stock
 *   identity matrix (the on-camera H.265/H.264/MP4/ProRes loss while
 *   single-build N-RAW kept its mark).  Stale-pose protection moved to
 *   the recording-session boundaries in vr_latch_hook: a later
 *   non-recording finalize that reuses this site (the MOVF transcode
 *   family 0x4034407c/0x403494d8 -> movie_finalize_stop) sees latch 0
 *   because the take tail clears the byte and its own session never
 *   passes w1==1.  Tail-branches to 0x40ce3fdc with x30 still 0x40cefd64,
 *   preserving x0/x2.  Touches only w8/w9/x10/x11 (x8-x17 scratch
 *   budget; x18 platform register untouched); NZCV is clobbered, which
 *   the post-BL continuation at 0x40cefd64 cannot observe (condition
 *   flags do not survive calls under the AArch64 PCS).
 *
 * vr_latch_hook -- replaces the first 8 bytes of the recording-side file
 *   open marshaling trampoline at 0x40d17728 (stock: mov x8,#0x6f0 ;
 *   movk x8,#0x31c,lsl#16 -- two pure x8 scratch loads, bytes
 *   08de80d2 8863a0f2) with `b vr_latch_hook` + nop; no branch enters the
 *   trampoline mid-body (t2 report).  w1 is the open mode: 0 = read-parse
 *   (the engine's bit-0 session init and bit-7 post-take parse), 1 = main
 *   movie write (the two recording-start callers 0x40d1b3b8 and
 *   0x40d17c34), 2 = the post-finalize udta-patch open (engine bit-8;
 *   FUN_40ceecc4 walks the FINALISED atom layout of the take's
 *   deliverable, and every container family's file carries moov/udta/NCDT,
 *   so it always runs after all finalizes of the take).  w1 == 1
 *   REFRESHES the latch: the idempotent first-boot default-on init
 *   (vr_default_on below) runs first, then the classifier through an x17
 *   manual call: x30 must keep the original caller's return address
 *   because the stock trampoline tail-jumps at 0x40d17748 and the service
 *   returns through x30.  w1 != 1 CLEARS the latch (t15 fix): those opens
 *   are recording-session boundaries -- read-parse brackets the recording
 *   and the udta patch is the take tail -- so the sticky pose never leaks
 *   past the take into a later non-recording finalize.  The clear path
 *   clobbers only x9: the resumed stock trampoline reloads w9 from w1 at
 *   0x40d17738.  The displaced pair is
 *   replayed verbatim under vr_latch_displaced and execution resumes at
 *   0x40d17730 with x0/x1 passed through untouched; NZCV may differ, but
 *   none of the resumed instructions consumes flags.
 *
 * vr_classify -- T1 ruling: classify the normalised gravity vector
 *   (f32 x3 at 0x0A02E560E0/E4/E8, published by the sensor fusion task at
 *   ~1 kHz) instead of reading the orientation enum (pinned to 3 by the
 *   all-zero factory calibration in emulation; the EXIF ctx+0x2500 lane is
 *   capture-scoped and unusable as an anchor).  The sensor-subsystem
 *   enable byte 0x0A02E56018 must equal 1, read as a BYTE exactly like
 *   every stock consumer (ldrb + compare; the bytes past +0 are not part
 *   of the contract).  Each component's sign bit is stripped
 *   and magnitudes are compared as unsigned integers (IEEE754 non-negative
 *   ordering) -- no FPU needed.  The dominant axis (argmax with the
 *   x-beats-y-beats-z tie-break) must reach the threshold vr_threshold
 *   (0.70f = 0x3F333333) in the state window; otherwise no mark (code 0).
 *   The pose code is
 *   vr_axis_codes[axis*2 + sign], the unit's own code 0..3 (0 = landscape /
 *   no mark).  Returns w8; manual-call linkage (b in, br x17 out) so x30
 *   stays intact; clobbers only w8..w16.
 *
 * Axis assignment (2026-11-10 t15 on-camera evidence; the retired T1
 *   "boot anchor" was circular -- the QEMU orientation model injected the
 *   very vector the guess assumed).  The first hardware truth is the NEV
 *   take set: the tkhd matrices of landscape/upside-down/portrait takes
 *   identify the fired lanes exactly, so the chip's real convention is
 *     code 3: +X  upside-down grip (landscape rolled 180 deg) -> 180
 *     code 0: -X  level landscape grip (no mark)
 *     code 1: +Y  portrait, shutter-bottom (EXIF-6 semantics -> 90 deg CW)
 *     code 2: -Y  portrait, shutter-top (EXIF-8 semantics -> 90 deg CCW)
 *     no mark: +/-Z  lens axis (pointing straight up/down: no roll code
 *                can express it)
 *   i.e. chip X = the camera vertical axis (sign inverted vs the old
 *   guess), chip Y = the roll axis the guess had zeroed (which is why both
 *   portrait takes carried no mark at all), chip Z = the lens axis.
 *   Both camera rounds confirmed the X lanes; the portrait pair shipped
 *   as the derived tentative (+Y/-Y -> 2/1) came out mirrored on camera
 *   (2026-11-10 second round: both grips marked, directions swapped), so
 *   bytes 2/3 are flipped -- the table is now fully empirical.
 *
 * Per-bank value storage (T7): the value byte is byte +2 of the DS item
 *   0x1257 record family -- the 4-byte slot whose +1 byte hosts the shipped
 *   H.265 tier constant 0xA03D5C269 (z8h265 TIER).  The item registers
 *   copy type 0 size 1, so stock only manages byte +0; the t7 report's
 *   writer scan proves +2 unused in every copy.  Bank 0 (VR_VALUE) is the
 *   active working record the menu reads/writes; VR_COPY_B1..B4 are the
 *   movie-shooting-bank storages A-D.  Every access is a literal-address
 *   load/store, exactly the TIER idiom.
 *
 * vr_default_on -- first-boot default-on init, entered by a manual x17 call
 *   (b in, br x17 out; x30 untouched) from BOTH the latch hook and the
 *   row-refresh hook, whichever runs first.  The sentinel byte in the
 *   state window ships 0 in the image and boots 0 (the boot segment
 *   loader re-copies the data mirror window from the image every power
 *   cycle), so the first pass arms the sentinel to VR_SENTINEL_VALUE
 *   FIRST and then writes 1 to the value byte in the active record and
 *   all four bank storages: arm-before-write is the power-loss property
 *   -- an init interrupted between the two steps at worst leaves a user
 *   Off in place until the next boot, and never lets a later
 *   re-initialization overwrite a stored user value.  Later passes are
 *   no-ops, keeping a user's Off alive for the whole session; a power
 *   cycle re-copies the window (sentinel back to 0) and every bank
 *   defaults to On again.  Clobbers w8/w9/x10/x17 only.
 *
 * Unit state, in the boot-loaded data mirror window (A+ migration, the
 *   2026-11-09 vrotate-fix t1 report): a 256 B window of the boot data
 *   segment (RAM 0xA0281A800, EG image 0x4B25800) holds all five unit data
 *   labels -- vr_matrices 108 B = ORIENT_TO_MATRIX[1..3] big-endian 16.16
 *   words at +0x00, vr_threshold 4 B (0x3F333333) at +0x6C,
 *   vr_axis_codes 6 B at +0x70, vr_latch 1 B (0) at +0x76, vr_sentinel
 *   1 B (0; first-boot marker, see vr_default_on) at +0x77 -- plus the
 *   0xA5 magic byte at +0xFF that proves on camera that the boot segment
 *   loader really copies the window from the image (zero-initialized RAM
 *   cannot read 0xA5 back).  The window is ordinary EL0-writable RAM: the
 *   stock crash was the sentinel/latch stores hitting the read-only cave.
 *   The labels are addressed through `ldr =` literals injected via -D
 *   (VR_*_RAM from patcher.asm_defines, the z8log asm_defines precedent);
 *   a naked assemble without the defines fails at link.
 *
 * Cave layout (T2b, 2026-11-09 user ruling): the unit is pure code plus its
 *   literal pool from 0x40A08000, capacity-checked against VR_EVENTS_AT
 *   (patcher.py).  The read-only vr_row_events 44x32 B transition-table
 *   clone lives at the patcher-constant fixed sub-window VR_EVENTS_AT =
 *   0x40A09000 (the z8h265 MENU_AT form), emitted as its own image edit --
 *   unit growth no longer moves any external frozen byte that names the
 *   table (the 8 B emit-region transition pointer is the only one).
 *
 * vr_row_hook -- T6: the OK/0x28B/touch action of the synthesized row
 *   0x315B in the video shooting menu.  Cloned from the stock audio
 *   attenuator row 0x2FC0 (row index 35 of the 44-row table at EG offset
 *   0x3AA4758; class word 0x20901005 = inline On/Off toggle; transition
 *   table at 0x43C33EF0 with 44 records ending in the 0x3BB terminator).
 *   In stock, events 0x286/0x28B/0x2AE all dispatch to 0x405707D4, which
 *   flips DS setting 0x700123C (0x405121EC -> write 0x410D61D0) and then
 *   redraws the focused row through 0x40512068 -> 0x405120E8 (boolean
 *   value widget) + 0x403B3DDC + 0x403B26C0.  The events-window clone
 *   replaces only those three action words: it flips the active-record
 *   value byte at VR_VALUE, then renders the value through the stock
 *   boolean widget 0x405121E4(child, byte) -- the attenuator row's own
 *   path (internal ids 0x125A = On / 0x125C = Off) -- after looking up the
 *   row's value child (child id 0x4BA7, the same lookup the stock refresh
 *   0x40572B2C uses for every row: 0x4050A6F0).  The immediate redraw
 *   copies the stock tail of 0x40512068.  Entered as a transition action:
 *   x0 = action context, [x0] = menu state; saves x19/x20, otherwise AAPCS
 *   caller-saved only.
 *
 *   Value-render path history (T4, adopted 2026-11-09): the original T6
 *   design drove the value child through 0x403F645C(child, 2466/2467) --
 *   the value-child call the stock refresh uses for language-table ids
 *   (e.g. the 0x2E48 row feeding id 0x371) -- but the 0x1327 value-child
 *   template runs mode==3 and truncates string ids above 299 (2026-11-08
 *   arc t6 report section 2), and the 2026-11-09 leg-0 menu probe showed
 *   the broken render live (OFF-styled text unselected, hourglass icon
 *   highlighted) while the toggle and the storage byte kept working.
 *   The hooks now feed the value byte itself (1/0) to 0x405121E4.  The
 *   toggle and the storage are unaffected.
 *
 * vr_refresh_hook -- T6: the fifth shared-refresh row callback (CONFIG
 *   +0x28, dispatched after the native refresh 0x40572B2C).  Runs the
 *   first-boot default-on init (the latch hook holds the other entry
 *   point), then rewrites the row's value child exactly like vr_row_hook
 *   does, so nothing stale survives a bank switch or page re-entry.
 *   x0 = menu state.
 */

#define VR_SENTINEL_VALUE 0x5A      /* must equal patcher.SENTINEL_VALUE; test_unit_builds pins it */
#define VR_VALUE    0x0A03D5C26A    /* DS 0x1257 active record +2; patcher.VALUE_ADDR */
#define VR_COPY_B1  0x0A03D5C53A    /* bank A storage record +2 */
#define VR_COPY_B2  0x0A03D5C80A    /* bank B storage record +2 */
#define VR_COPY_B3  0x0A03D5CADA    /* bank C storage record +2 */
#define VR_COPY_B4  0x0A03D5CDAA    /* bank D storage record +2 */
/* State window RAM VAs of the five unit data labels: injected via -D from
 * patcher.asm_defines (the window layout is frozen there); no local default,
 * so a naked assemble without the defines cannot silently target the cave. */
/* VR_MATRICES_RAM, VR_THRESHOLD_RAM, VR_AXIS_CODES_RAM, VR_LATCH_RAM,
 * VR_SENTINEL_RAM -- provided by the build. */

.text
.balign 16
.global vr_matrix_hook
vr_matrix_hook:
    ldr  x10, =VR_LATCH_RAM        // sticky latch in the state window (t15:
    ldrb w8, [x10]                 // never cleared here -- every moov build
    ldr  x11, =VR_VALUE            // of the take must see the same pose)
    ldrb w9, [x11]
    cbz  w9, 2f                    // feature disabled: stock matrix
    sub  w8, w8, #1
    cmp  w8, #2
    b.hi 2f                        // latch not in 1..3: passthrough
    ldr  x10, =VR_MATRICES_RAM     // display matrices in the state window
    mov  w9, #36
    umaddl x1, w8, w9, x10         // x1 = &vr_matrices[(latch-1)*36]
2:  b    original_40ce3fdc         // tail branch; x30 still 0x40cefd64

.balign 16
.global vr_latch_hook
vr_latch_hook:                     // entered via b from 0x40d17728; x0/w1 pass through
    cmp  w1, #1
    b.ne 1f                        // read-parse (0) / udta-patch (2) opens
    adr  x17, 2f                   // first-boot default-on (idempotent)
    b    vr_default_on
2:  adr  x17, 3f                   // manual call: x30 must stay the caller's
    b    vr_classify
3:  ldr  x9, =VR_LATCH_RAM
    strb w8, [x9]                  // pose code; 0 = no mark / invalid
    b    4f
1:  ldr  x9, =VR_LATCH_RAM         // session boundary (t15): the sticky
    strb wzr, [x9]                 // pose never outlives the take
4:                                  // displaced pair from 0x40d17728 (t2 report)
vr_latch_displaced:
    mov  x8, #0x6f0
    movk x8, #0x31c, lsl #16
    b    original_40d17730         // back into the stock trampoline

.balign 16
.global vr_row_hook
vr_row_hook:                       // transition action of row 0x315B; x0 = ctx
    stp  x29, x30, [sp, #-32]!
    stp  x19, x20, [sp, #16]
    ldr  x19, [x0]                 // x0 = action context, [x0] = menu state
    ldr  x10, =VR_VALUE            // flip the active-record value byte 0 <-> 1
    ldrb w11, [x10]
    eor  w11, w11, #1
    strb w11, [x10]                // the matrix hook reads the same byte
    mov  x0, x19
    mov  w1, #0x315B               // our row item
    mov  w2, #0x4BA7               // the row's value child id
    bl   original_4050A6F0         // stock row-child lookup
    cbz  x0, 1f
    mov  x20, x0                   // value child widget
    ldr  x10, =VR_VALUE            // value render (T4): drive the row's own
    ldrb w1, [x10]                 // boolean widget with the byte itself
    cmp  w1, #1                    // (1 = On, 0 = Off).  The retired T6
    b.ne 2f                        // string-id call 0x403F645C(child,
    mov  w1, #1                    // 2466/2467) truncated ids above 299 on
    b    3f                        // the mode==3 0x1327 child template
2:  mov  w1, #0                    // (2026-11-08 t6 report section 2)
3:  mov  x0, x20
    bl   original_405121E4         // stock boolean widget: the attenuator row's own path
1:  mov  x0, x19
    mov  w1, #0x315B
    bl   original_403B3DDC         // mark the row value changed (stock tail)
    mov  x0, x19
    bl   original_403B26C0         // repaint the page (stock tail)
    ldp  x19, x20, [sp, #16]
    ldp  x29, x30, [sp], #32
    ret

.balign 16
.global vr_refresh_hook
vr_refresh_hook:                   // shared_refresh fifth callback; x0 = state
    stp  x29, x30, [sp, #-32]!
    stp  x19, x20, [sp, #16]
    mov  x19, x0
    adr  x17, 1f                   // first-boot default-on (idempotent)
    b    vr_default_on
1:  cbz  x19, 9f
    mov  x0, x19
    mov  w1, #0x315B
    mov  w2, #0x4BA7
    bl   original_4050A6F0
    cbz  x0, 9f
    ldr  x10, =VR_VALUE            // same boolean value render as vr_row_hook
    ldrb w1, [x10]                 // (T4): the byte itself through the stock
    cmp  w1, #1                    // boolean widget, not string ids
    b.ne 2f
    mov  w1, #1
    b    8f
2:  mov  w1, #0
8:  bl   original_405121E4         // x0 still holds the value child
9:  ldp  x19, x20, [sp, #16]
    ldp  x29, x30, [sp], #32
    ret

.balign 16
vr_default_on:                     // b in / br x17 out; first-boot init
    ldr  x10, =VR_SENTINEL_RAM     // first-boot marker in the state window
    ldrb w8, [x10]
    cbnz w8, 9f                    // already armed this boot: change nothing
    mov  w8, #VR_SENTINEL_VALUE
    strb w8, [x10]                 // arm before writing (idempotence)
    mov  w9, #1
    ldr  x10, =VR_VALUE
    strb w9, [x10]                 // active record (bank 0)
    ldr  x10, =VR_COPY_B1
    strb w9, [x10]                 // bank A storage
    ldr  x10, =VR_COPY_B2
    strb w9, [x10]                 // bank B storage
    ldr  x10, =VR_COPY_B3
    strb w9, [x10]                 // bank C storage
    ldr  x10, =VR_COPY_B4
    strb w9, [x10]                 // bank D storage
9:  br   x17

.balign 16
vr_classify:                       // b in / br x17 out; returns w8 = code 0..3
    ldr  x9, =0x0A02E56018         // sensor-subsystem enable byte (t1 report)
    ldrb w10, [x9]                 // stock consumers read the BYTE (ldrb)
    cmp  w10, #1
    b.ne 8f                        // subsystem invalid: no mark
    ldr  x11, =0x0A02E560E0        // normalised gravity vector f32 x3 (t1)
    ldr  w12, [x11]
    ldr  w13, [x11, #4]
    ldr  w14, [x11, #8]
    lsr  w10, w12, #31             // w10 = sx | sy<<1 | sz<<2
    lsr  w15, w13, #31
    orr  w10, w10, w15, lsl #1
    lsr  w15, w14, #31
    orr  w10, w10, w15, lsl #2
    and  w12, w12, #0x7fffffff     // |x|,|y|,|z| as unsigned float bits
    and  w13, w13, #0x7fffffff
    and  w14, w14, #0x7fffffff
    mov  w16, #1
    cmp  w12, w13
    csel w15, w12, w13, hs         // max(|x|, |y|)
    csel w16, wzr, w16, hs         // axis 0 = x, 1 = y (x wins exact ties)
    mov  w9, #2
    cmp  w15, w14
    csel w15, w15, w14, hs         // overall dominant magnitude
    csel w16, w16, w9, hs          // axis 2 = z (needs to be strictly larger)
    ldr  x9, =VR_THRESHOLD_RAM     // threshold word in the state window
    ldr  w9, [x9]                  // threshold bits (0.70f)
    cmp  w15, w9
    b.lo 8f                        // no dominant axis: no mark
    lsr  w9, w10, w16              // winner's sign bit to bit 0
    and  w9, w9, #1
    add  w16, w16, w16
    orr  w16, w16, w9              // vr_axis_codes index = axis*2 + sign (0..5)
    ldr  x9, =VR_AXIS_CODES_RAM    // pose-code table in the state window
    ldrb w8, [x9, x16]             // own pose code 0..3
    b    9f
8:  mov  w8, wzr                   // gate off / no dominant axis / invalid
9:  br   x17

.balign 16
.global vr_track_hook
vr_track_hook:                     // entered via b from 0x40ce4294 (FUN entry); x0 = muxer ctx
    adr  x17, 2f                   // t15c pose refresh at every writer's track
    b    vr_default_on             // registration: engine, PRF worker and the 8-bit
2:  adr  x17, 3f                   // legacy pipeline's remux writer (whose file opens
    b    vr_classify               // bypass the recording-side trampoline entirely,
3:  ldr  x9, =VR_LATCH_RAM         // so its sticky latch never refreshed -- camera
    strb w8, [x9]                  // evidence: every 8-bit take carried the previous
    str  x28, [sp, #-0x60]!        // live take's pose) all register tracks here.
    b    original_40ce4298         // displaced first stock instruction; resume

.ltorg
/* End of the unit: pure code plus the literal pool above.  The row-events
 * transition-table clone moved to the fixed sub-window VR_EVENTS_AT
 * (0x40A09000, see the header); patcher.py emits it as its own image edit
 * and capacity-checks the unit against that window. */
