/* vrotate patch unit (T5): pose-latched tkhd display matrices for movies.
 *
 * Two hooks plus a classifier in cave 0x40A20000..0x40A22000 (SPECS 'vrotate',
 * z8patch/compiled.py).  All firmware evidence addresses below are stock EG
 * virtual addresses (BASE 0x40160000) from the vrotate reports
 * .superpowers/sdd/2026-11-08-vrotate/reports/ (t1 anchor, t2 latch site,
 * t3 serialize trace).
 *
 * vr_matrix_hook -- replaces the stock `bl 0x40ce3fdc` (word 0x97ffd09f) at
 *   0x40cefd60, the single video-track tkhd matrix copy inside
 *   movie_build_videotrack_atoms (0x40cef3d0); every container mode
 *   (MOV/MP4/N-RAW) and codec funnels through it (t3 report).  Registers on
 *   entry: x0 = ctx+0x128 destination node, x1 = &stack identity blob,
 *   x2 = 0x24.  If the feature byte vr_enable is non-zero and the latch
 *   holds a valid code 1..3, x1 is redirected to vr_matrices+(code-1)*36
 *   (36-byte big-endian 16.16 QuickTime display matrix; 1 = 90 deg CW,
 *   2 = 90 deg CCW, 3 = 180; 0/invalid = passthrough).  Either way the
 *   latch byte is read and cleared first (one-shot read-and-clear), so a
 *   later playback-side finalize that reuses this site (the
 *   0x4034412c/0x403494d8 families -> movie_finalize_stop, t3 section 5.3)
 *   can never reuse a stale pose.  Tail-branches to 0x40ce3fdc with x30
 *   still 0x40cefd64, preserving x0/x2.  Touches only w8/w9/x10/x11
 *   (x8-x17 scratch budget; x18 platform register untouched); NZCV is
 *   clobbered, which the post-BL continuation at 0x40cefd64 cannot observe
 *   (condition flags do not survive calls under the AArch64 PCS).
 *
 * vr_latch_hook -- replaces the first 8 bytes of the recording-side file
 *   open marshaling trampoline at 0x40d17728 (stock: mov x8,#0x6f0 ;
 *   movk x8,#0x31c,lsl#16 -- two pure x8 scratch loads, bytes
 *   08de80d2 8863a0f2) with `b vr_latch_hook` + nop; no branch enters the
 *   trampoline mid-body (t2 report).  w1 is the open mode: 0 = read-back
 *   parse, 1 = main movie write (the two recording-start callers 0x40d1b3b8
 *   and 0x40d17c34), 2 = second file.  Latching fires only on w1 == 1
 *   (t2 ruling) so a stop-time second-file open cannot overwrite the pose
 *   captured at recording start.  The w1==1 path performs the idempotent
 *   first-run sentinel init (sentinel stays 0 across boots until the first
 *   recording; T7's bank-restore wiring may pre-set it), then calls the
 *   classifier through an x17 manual call: x30 must keep the original
 *   caller's return address because the stock trampoline tail-jumps at
 *   0x40d17748 and the service returns through x30.  The displaced pair is
 *   replayed verbatim under vr_latch_displaced and execution resumes at
 *   0x40d17730 with x0/x1 passed through untouched; NZCV may differ, but
 *   none of the resumed instructions consumes flags.
 *
 * vr_classify -- T1 ruling: classify the normalised gravity vector
 *   (f32 x3 at 0x0A02E560E0/E4/E8, published by the sensor fusion task at
 *   ~1 kHz) instead of reading the orientation enum (pinned to 3 by the
 *   all-zero factory calibration in emulation; the EXIF ctx+0x2500 lane is
 *   capture-scoped and unusable as an anchor).  The sensor-subsystem gate
 *   word 0x0A02E56018 must equal 1.  Each component's sign bit is stripped
 *   and magnitudes are compared as unsigned integers (IEEE754 non-negative
 *   ordering) -- no FPU needed.  The dominant axis (argmax with the
 *   x-beats-y-beats-z tie-break) must reach the cave threshold vr_threshold
 *   (0.70f = 0x3F333333); otherwise no mark (code 0).  The pose code is
 *   vr_axis_codes[axis*2 + sign], the unit's own code 0..3 (0 = landscape /
 *   no mark).  Returns w8; manual-call linkage (b in, br x17 out) so x30
 *   stays intact; clobbers only w8..w16.
 *
 * Axis assignment derivation (documented hypothesis; the T1 report shows the
 * pose->axis mapping cannot be pinned in emulation because the stock
 * classifier output is pinned by the zero calibration):
 *   The only anchor is the T1 boot observation: a level camera at rest
 *   reads (0, 0, +1), so +Z is the baseplate normal with the camera level
 *   in the normal landscape grip.
 *     code 0: +Z  level landscape grip (no mark, matches the boot anchor)
 *     code 3: -Z  rolled 180 deg (baseplate normal flips)
 *     code 1: +X  rolled 90 deg CW as seen from behind the camera; the
 *                stored image then needs a 90 deg CW rotation to display
 *                upright (EXIF-6 semantics -> ROTATE_90_CW_MATRIX)
 *     code 2: -X  rolled 90 deg CCW (EXIF-8 semantics -> ROTATE_90_CCW)
 *     no mark: +/-Y  assumed parallel to the lens axis (chip-mounting
 *                guess): a Y-dominant reading means the lens points up or
 *                down, which no roll code can express.
 *   T11 flip procedure: after on-camera ffprobe calibration, correct any
 *   pose by editing only vr_axis_codes bytes (swap bytes 0/1 if the
 *   portrait pair is mirrored, 4/5 if 180 lands on the wrong Z sign, move
 *   the pair onto the Y axis if the mounting guess is wrong); the threshold
 *   rides in vr_threshold the same way.  Calibration never needs a code
 *   change.
 *
 * Cave data, all patcher-filled at build time (z8vrotate/patcher.py):
 *   vr_matrices 108 B = ORIENT_TO_MATRIX[1..3] big-endian 16.16 words,
 *   vr_axis_codes 6 B, vr_threshold 4 B (0x3F333333), vr_latch 1 B (0),
 *   vr_enable 1 B (1; T7 wires it into the menu/bank storage),
 *   vr_sentinel 1 B (0; first-run marker, see the latch hook),
 *   vr_value 1 B (1 = on; the inline-toggle row byte, T7 relocates it
 *   into the per-bank storage), vr_row_events 44x32 B (the cloned stock
 *   transition table of the template row, see vr_row_hook).
 *
 * vr_row_hook -- T6: the OK/0x28B/touch action of the synthesized row
 *   0x315B in the video shooting menu.  Cloned from the stock audio
 *   attenuator row 0x2FC0 (row index 35 of the 44-row table at EG offset
 *   0x3AA4758; class word 0x20901005 = inline On/Off toggle; transition
 *   table at 0x43C33EF0 with 44 records ending in the 0x3BB terminator).
 *   In stock, events 0x286/0x28B/0x2AE all dispatch to 0x405707D4, which
 *   flips DS setting 0x700123C (0x405121EC -> write 0x410D61D0) and then
 *   redraws the focused row through 0x40512068 -> 0x405120E8 (boolean
 *   value widget) + 0x403B3DDC + 0x403B26C0.  The cave clone replaces
 *   only those three action words: it flips the cave byte vr_value, mirrors
 *   it into vr_enable so the matrix hook follows immediately, then shows
 *   the official localized On/Off pair by driving the row's value child
 *   (child id 0x4BA7, the same lookup the stock refresh 0x40572B2C uses
 *   for every row: 0x4050A6F0) with string id 2466 (On) or 2467 (Off)
 *   through 0x403F645C -- the value-child call the stock refresh uses for
 *   language-table ids (e.g. the 0x2E48 row feeding id 0x371).  The
 *   immediate redraw copies the stock tail of 0x40512068.  Entered as a
 *   transition action: x0 = action context, [x0] = menu state; saves
 *   x19/x20, otherwise AAPCS caller-saved only.
 *
 * vr_refresh_hook -- T6: the fifth shared-refresh row callback (CONFIG
 *   +0x28, dispatched after the native refresh 0x40572B2C).  Performs the
 *   sentinel fallback init (the latch hook holds the other check; the
 *   patcher also fills the defaults, so this only repairs a cleared
 *   sentinel with a corrupt value byte), then rewrites the row's value
 *   child exactly like vr_row_hook does, so nothing stale survives a bank
 *   switch or page re-entry.  x0 = menu state.
 */

#define VR_SENTINEL_VALUE 0x5A      /* must equal patcher.SENTINEL_VALUE; test_unit_builds pins it */

.text
.balign 16
.global vr_matrix_hook
vr_matrix_hook:
    adr  x10, vr_latch
    ldrb w8, [x10]
    strb wzr, [x10]                // one-shot: consume the latch on every pass
    adr  x11, vr_enable
    ldrb w9, [x11]
    cbz  w9, 2f                    // feature disabled: stock matrix
    sub  w8, w8, #1
    cmp  w8, #2
    b.hi 2f                        // latch not in 1..3: passthrough
    adr  x10, vr_matrices
    mov  w9, #36
    umaddl x1, w8, w9, x10         // x1 = &vr_matrices[(latch-1)*36]
2:  b    original_40ce3fdc         // tail branch; x30 still 0x40cefd64

.balign 16
.global vr_latch_hook
vr_latch_hook:                     // entered via b from 0x40d17728; x0/w1 pass through
    cmp  w1, #1
    b.ne 1f                        // only the main-movie write open latches
    adr  x9, vr_sentinel           // idempotent first-run init (T7 may pre-set)
    ldrb w10, [x9]
    cbnz w10, 2f
    mov  w10, #VR_SENTINEL_VALUE
    strb w10, [x9]
2:  adr  x17, 3f                   // manual call: x30 must stay the caller's
    b    vr_classify
3:  adr  x9, vr_latch
    strb w8, [x9]                  // pose code; 0 = no mark / invalid
1:                                  // displaced pair from 0x40d17728 (t2 report)
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
    adr  x10, vr_value
    ldrb w11, [x10]
    eor  w11, w11, #1
    strb w11, [x10]                // flip the row value byte 0 <-> 1
    adr  x10, vr_enable
    strb w11, [x10]                // the matrix hook follows at once (T7: banks)
    mov  x0, x19
    mov  w1, #0x315B               // our row item
    mov  w2, #0x4BA7               // the row's value child id
    bl   original_4050A6F0         // stock row-child lookup
    cbz  x0, 1f
    mov  x20, x0                   // value child widget
    adr  x10, vr_value
    ldrb w1, [x10]
    cmp  w1, #1
    b.ne 2f
    mov  w1, #2466                 // official localized On (id 2466)
    b    3f
2:  mov  w1, #2467                 // official localized Off (id 2467)
3:  mov  x0, x20
    bl   original_403F645C         // set the value child's display id
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
    adr  x10, vr_sentinel          // sentinel fallback init (idempotent)
    ldrb w11, [x10]
    cbnz w11, 1f
    mov  w11, #VR_SENTINEL_VALUE
    strb w11, [x10]
    adr  x10, vr_value
    mov  w12, #1
    strb w12, [x10]                // default on
    adr  x10, vr_enable
    strb w12, [x10]
1:  cbz  x19, 9f
    mov  x0, x19
    mov  w1, #0x315B
    mov  w2, #0x4BA7
    bl   original_4050A6F0
    cbz  x0, 9f
    adr  x10, vr_value
    ldrb w1, [x10]
    cmp  w1, #1
    b.ne 2f
    mov  w1, #2466
    b    8f
2:  mov  w1, #2467
8:  bl   original_403F645C         // x0 still holds the value child
9:  ldp  x19, x20, [sp, #16]
    ldp  x29, x30, [sp], #32
    ret

.balign 16
vr_classify:                       // b in / br x17 out; returns w8 = code 0..3
    ldr  x9, =0x0A02E56018         // sensor-subsystem gate word (t1 report)
    ldr  w10, [x9]
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
    adr  x9, vr_threshold
    ldr  w9, [x9]                  // cave threshold bits (0.70f)
    cmp  w15, w9
    b.lo 8f                        // no dominant axis: no mark
    lsr  w9, w10, w16              // winner's sign bit to bit 0
    and  w9, w9, #1
    add  w16, w16, w16
    orr  w16, w16, w9              // vr_axis_codes index = axis*2 + sign (0..5)
    adr  x9, vr_axis_codes
    ldrb w8, [x9, x16]             // own pose code 0..3
    b    9f
8:  mov  w8, wzr                   // gate off / no dominant axis / invalid
9:  br   x17

.ltorg
.balign 4
vr_axis_codes:                     /* 6 bytes: [axis*2 + sign] -> pose code; T11 flip = bytes only */
    .space 6
.balign 4                          /* keep the threshold word aligned for its ldr */
vr_threshold:                      /* u32 IEEE754 bits (0.70f = 0x3F333333); patcher-filled */
    .space 4
.balign 8
vr_matrices:                       /* 3 x 36 B big-endian 16.16 matrices, codes 1..3; patcher-filled */
    .space 108
vr_latch:                          /* latched pose code at recording open; 0 = none */
    .space 1
vr_enable:                         /* feature switch byte; 1 = on (T7 wires the menu/bank) */
    .space 1
vr_sentinel:                       /* first-run marker; boots 0, set to VR_SENTINEL_VALUE */
    .space 1
vr_value:                          /* inline-toggle row byte; 1 = on; T7 moves it to bank storage */
    .space 1
.balign 8
.global vr_row_events
vr_row_events:                     /* 44 x 32 B transition table cloned from 0x2FC0; patcher-filled */
    .space 44*32
