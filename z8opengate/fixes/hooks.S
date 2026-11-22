/* Open-gate fixes for v0.5.1, linked at 0x40968000 in the free tail of the
 * open-gate code area (zero up to the private state at 0x4096F000).  The unit
 * extends the open-gate and anamorphic units and is entered from their sites:
 *
 *   0x000  4.1K N-RAW 3:2 AF geometry.  Standby (plan 11) and recording
 *          (plan 13) select the full-frame AF area, but the open-gate AF record
 *          kept four 1920x1080 AF planes and the 16:9 centre crop, so the AF
 *          rectangle reached row 3010 of a 2760-row range (standby, 50-120p)
 *          or row 6022 of 5520 (recording, 24-30p).  For an exact 4.1K 3:2
 *          state the private AF record gets 1920x1280 planes and both
 *          conversions skip the 16:9 crop.  Nothing else changes.
 *   0x260  The plan gate of the three checks above: plan 11 or plan 13.
 *   0x400  Movie playback fit.  A frame never needs more than one slot of the
 *          local output pool 6 (see 0x600 for the one enlarged case).
 *   0x600  Wide-area AF points on an open-gate 3:2 view: each cell keeps the
 *          height of a 16:9 cell (scaled by the source's own desqueeze); an
 *          exact 1280x848 open-gate EVF playback fit keeps full width, with
 *          the pool-6 slot raised to 1,628,160 B by the patcher.
 *   0x7C0  Wide-area AF point rows: the same bitmap row is drawn at the
 *          centre of the stock FX photo grid's row.
 *
 * Addresses of the units extended here; fix_sites.py checks each against
 * the open-gate and anamorphic symbols, or as a stock address, before use. */

#define OG_AF_GEOMETRY      original_40961D50   /* open-gate af_geometry_hook */
#define OG_AF_FORWARD       original_40961B00   /* open-gate af_forward_hook */
#define OG_AF_INVERSE       original_40961BD0   /* open-gate af_inverse_hook */
#define STOCK_FORWARD_FULL  original_41055BB4   /* stock forward conversion after its 16:9 crop */
#define STOCK_INVERSE_FULL  original_410569A8   /* stock inverse conversion after its 16:9 offset */
#define AP_PLAYBACK_FIT     original_409708F0   /* anamorphic ap_playback_fit_hook */
#define STOCK_MEMCPY        original_4127A900
#define AP_MAP              original_409702C0   /* anamorphic ap_map */
#define AP_POINTS_NEXT      original_409704B4   /* anamorphic ap_points_scale_next */
#define AP_POINTS_DONE      original_4097050C   /* anamorphic ap_points_done */
#define AP_RATIOS           0x40970C10          /* anamorphic ap_ratios (data) */

#define SLOT_PIXELS_LO 0x1000                   /* 921600 = 0xE1000 = 0x151800 / 1.5 */
#define SLOT_PIXELS_HI 0xE

.text
.balign 4

/* ---- 0x000: 4.1K N-RAW 3:2 AF geometry -------------------------------------
 * The two AF callers own a 0x6c-byte geometry record at sp+0x100.  Never
 * alter the shared geometry provider, grid selection or REC descriptors. */

.macro pair_value reg, width, height
    movz \reg, #\width
    movk \reg, #\height, lsl #16
.endm

/* The descriptor shape accepted by the 4.1K geometry provider: plan 11
 * (standby) or 13 (recording), FX area 4, rate 0-6, and a fourth word of 0
 * in the AF caller or type 6.  The plan comparison runs in \gate (0x260). */
.macro check_descriptor plan, fail, gate
    ldr w16, [\plan]
    b \gate
\gate\()_resume:
    b.ne \fail
    ldr w16, [\plan, #4]
    cmp w16, #4
    b.ne \fail
    ldr w16, [\plan, #8]
    cmp w16, #6
    b.hi \fail
    ldr w16, [\plan, #12]
    cbz w16, 1f
    cmp w16, #6
    b.ne \fail
1:
.endm

.global af_geometry
af_geometry:                        // 41055AC0, 410567DC: bl af_geometry
    stp x19, x20, [sp, #-32]!
    str x30, [sp, #16]
    mov x19, x0
    mov x20, x1
    bl OG_AF_GEOMETRY               // open-gate geometry, including the stock return value
    stp x16, x17, [sp, #-32]!
    mrs x16, nzcv
    str x16, [sp, #16]
    check_descriptor x19, geometry_done, geometry_plan
    ldr x17, =0xA03D7C94C
    ldr w16, [x17]                  // physical selector must still be in video mode
    cmp w16, #1
    b.ne geometry_done
    ldr x17, =0xA03D5C000
    ldrb w16, [x17, #0x2b]          // selected OpenGate
    cmp w16, #1
    b.ne geometry_done
    ldr w16, [x17, #0x14]           // stored N-RAW
    cmp w16, #6
    b.ne geometry_done
    ldr w16, [x17, #0x274]          // stored 4.1K
    cmp w16, #4
    b.ne geometry_done
    ldr x17, =0xA03BB71D8
    ldr w16, [x17]                  // published size/rate/rate must agree
    cmp w16, #4
    b.ne geometry_done
    ldr w16, [x17, #4]
    ldr w17, [x17, #8]
    cmp w16, w17
    b.ne geometry_done
    ldr w17, [x19, #8]
    cmp w16, w17
    b.ne geometry_done
    pair_value w17, 4128, 2752
    ldr w16, [x20, #0x0c]
    cmp w16, w17
    b.ne geometry_done
    pair_value w17, 1920, 1080
    .irp offset,0,0x10,0x24,0x28
        ldr w16, [x20, #\offset]
        cmp w16, w17
        b.ne geometry_done
    .endr
    mov w16, #1280
    .irp offset,0x2,0x12,0x26,0x2a
        strh w16, [x20, #\offset]
    .endr
geometry_done:
    ldr x16, [sp, #16]
    msr nzcv, x16
    ldp x16, x17, [sp], #32
    ldr x30, [sp, #16]
    ldp x19, x20, [sp], #32
    ret
.ltorg

/* Base the two crop decisions on the private record from this call, so a
 * settings transition cannot make a second global lookup disagree with it.
 * Preserve flags from the stock area comparison on the legacy path. */
.macro direction name, plan, legacy, uncropped, gate
.global \name
\name:
    stp x16, x17, [sp, #-32]!
    mrs x16, nzcv
    str x16, [sp, #16]
    check_descriptor \plan, 2f, \gate
    ldr w16, [sp, #0x120]            // original sp+0x100
    pair_value w17, 1920, 1280
    cmp w16, w17
    b.ne 2f
    ldr w16, [sp, #0x12c]            // original record+0x0c, active size
    pair_value w17, 4128, 2752
    cmp w16, w17
    b.ne 2f
    ldr x16, [sp, #16]
    msr nzcv, x16
    ldp x16, x17, [sp], #32
    b \uncropped
2:  ldr x16, [sp, #16]
    msr nzcv, x16
    ldp x16, x17, [sp], #32
    b \legacy
.endm

direction af_forward, x21, OG_AF_FORWARD, STOCK_FORWARD_FULL, forward_plan   // 41055B38
direction af_inverse, x22, OG_AF_INVERSE, STOCK_INVERSE_FULL, inverse_plan   // 4105693C

/* ---- 0x260: plan gate --------------------------------------------------------
 * Continue each check at its conditional branch.  For plan 13 return the
 * flags of equality; for all other plans reproduce cmp w16,#11, including
 * NZCV.  Registers, stack and link register are untouched. */
.org 0x260
.macro allow_record name
\name:
    cmp w16, #13
    ccmp w16, #11, #6, ne
    b \name\()_resume
.endm

allow_record geometry_plan
allow_record forward_plan
allow_record inverse_plan

/* ---- 0x400: movie playback fit (#34) -----------------------------------------
 * 407138D0 is the stock playback fit: w0/w1 media size, w2 mode, x3 window
 * record, x4 result record.  Both records are 0x1c bytes: +0 active, +2 pitch,
 * +4 rows, +6/+8/+A/+C rect x0,y0,x1,y1 (signed halfwords), +E/+10 pixel
 * aspect.  The anamorphic hook 409708F0 calls the open-gate hook (3:2 for an
 * open-gate clip) and then the stock body.  Every local frame goes to one slot
 * of the stock output pool 6.
 *
 * This hook runs that chain unchanged.  Only for a window at most 1280 wide
 * (rear LCD, EVF; HDMI windows are wider) whose result needs more than one
 * stock 1280x720 slot, and that is not the exact open-gate EVF case granted at
 * 0x600, it fits the same request again into the window shrunk by 64 px of
 * width per step, its height scaled in the window's own proportion (multiple
 * of 16), centred, and keeps the first result that fits.  If none of 8 steps
 * fits, the chain's result is restored.  No state; the window is read from a
 * private copy. */
.org 0x400
.balign 16

.macro fits_goto label
    ldrh w8, [x19, #2]
    ldrh w11, [x19, #4]
    mul w8, w8, w11
    movz w11, #SLOT_PIXELS_LO
    movk w11, #SLOT_PIXELS_HI, lsl #16
    cmp w8, w11
    b.ls \label
.endm

.macro chain window
    mov w0, w20
    mov w1, w21
    mov w2, w22
    add x3, sp, #\window
    mov x4, x19
    bl AP_PLAYBACK_FIT
.endm

.global evf_fit_hook
evf_fit_hook:                         // 407138D0: b evf_fit_hook
    stp x29, x30, [sp, #-0x80]!
    mov x29, sp
    stp x19, x20, [sp, #0x10]
    stp x21, x22, [sp, #0x20]
    stp x23, x24, [sp, #0x30]
    mov x19, x4
    mov w20, w0
    mov w21, w1
    mov w22, w2
    add x0, sp, #0x40                 // window snapshot at sp+0x40, scratch window at sp+0x60;
    mov x1, x3                        // records sit 0x1c apart, so copy with the stock memcpy
    mov w2, #0x1c                     // the stock fit itself uses (407138FC)
    bl STOCK_MEMCPY
    chain 0x40                        // the chain's result
    ldrb w8, [sp, #0x40]
    cbz w8, evf_fit_done              // inactive window: the stock copy
    ldrsh w9, [sp, #0x46]
    ldrsh w10, [sp, #0x4a]
    sub w10, w10, w9                  // window width
    cmp w10, #128
    b.lt evf_fit_done
    cmp w10, #1280
    b.gt evf_fit_done                 // HDMI and wider: unchanged
    ldrsh w11, [sp, #0x48]
    ldrsh w12, [sp, #0x4c]
    sub w12, w12, w11                 // window height
    cmp w12, #16
    b.lt evf_fit_done
    ldrh w8, [x19, #2]
    ldrh w11, [x19, #4]
    mul w8, w8, w11
    b evf_full                        // 0x600: the exact open-gate EVF fit keeps full width
evf_fit_slot_check:
    movk w11, #SLOT_PIXELS_HI, lsl #16
    cmp w8, w11
    b.ls evf_fit_done
    mov w23, #1
1:  ldp x8, x9, [sp, #0x40]           // scratch = snapshot, then a smaller centred rect
    stp x8, x9, [sp, #0x60]
    ldr x8, [sp, #0x50]
    str x8, [sp, #0x70]
    ldr w8, [sp, #0x58]
    str w8, [sp, #0x78]
    ldrsh w9, [sp, #0x46]             // x0
    ldrsh w10, [sp, #0x4a]
    sub w10, w10, w9                  // W
    ldrsh w11, [sp, #0x48]            // y0
    ldrsh w12, [sp, #0x4c]
    sub w12, w12, w11                 // H
    sub w13, w10, w23, lsl #6         // W' = W - 64 n
    cmp w13, #64
    b.lt 8f
    mul w14, w12, w13
    udiv w14, w14, w10
    and w14, w14, #0xfffffff0         // H' = 16 floor(H W' / W / 16)
    cbz w14, 8f
    sub w15, w10, w13
    add w15, w9, w15, lsr #1          // x0' = x0 + 32 n
    strh w15, [sp, #0x66]
    add w15, w15, w13
    strh w15, [sp, #0x6a]
    sub w15, w12, w14
    lsr w15, w15, #1
    and w15, w15, #0xfffffffe
    add w15, w11, w15                 // y0' = y0 + even floor((H - H') / 2)
    strh w15, [sp, #0x68]
    add w15, w15, w14
    strh w15, [sp, #0x6c]
    chain 0x60
    fits_goto evf_fit_done
    add w23, w23, #1
    cmp w23, #8
    b.ls 1b
8:  chain 0x40                        // nothing fits: keep the chain's result
evf_fit_done:
    ldp x23, x24, [sp, #0x30]
    ldp x21, x22, [sp, #0x20]
    ldp x19, x20, [sp, #0x10]
    ldp x29, x30, [sp], #0x80
    ret

/* ---- 0x600: wide-area AF cell height and open-gate EVF full width ------------
 * Entered from the anamorphic AF point routine (ap_af_points_hook) at its
 * scale step.  There w23 is the grid's design height, w24 the shown height,
 * x22 the native point record, x20/w19 the rectangles and their count. */
.org 0x600
.balign 4
.global points_source
points_source:                      // 409704B0: b points_source
    bl AP_MAP                       // matched AP native/shown pair, if squeezed
    cbnz w0, 1f
    // AP state is shared between outputs.  During a switch it may describe
    // the other screen.  Recover a live open-gate source only when its GUI
    // height matches the indicated ratio, using the same even rounding as AP4.
    ldr w8, [x22]
    cmp w8, #1
    mov w9, #852
    mov w10, #682
    csel w2, w9, w10, eq
    mov w15, w2
    ldr x9, =0xa03d5c0ad            // desqueeze ratio setting
    ldrb w10, [x9]
    subs w10, w10, #1
    cmp w10, #6
    b.hi 10f
    ldr x9, =AP_RATIOS              // halfword ratio pairs, numerator then denominator
    add x9, x9, x10, lsl #2
    ldrh w10, [x9]
    ldrh w11, [x9, #2]
    lsl w10, w10, #1
    mul w11, w11, w2
    udiv w15, w11, w10
    msub w11, w15, w10, w11
    lsl w11, w11, #1
    cmp w11, w10
    b.lo 11f
    b.hi 12f
    tbz w15, #0, 11f
12: add w15, w15, #1
11: lsl w15, w15, #1
10: cmp w24, w15
    b.ne 8f
1:  // If grid and source agree, preserve AP4's exact edge rounding.
    subs w9, w2, w23
    cneg w9, w9, mi
    cmp w9, #1
    b.ls 7f
    ldr w8, [x22]
    ldr x9, =0x44b7fd0c             // stock per-output point inset
    ldrsh w10, [x9, x8, lsl #1]
    add w10, w10, w10, lsr #31
    asr w10, w10, #1                // native per-edge inset, as in AP4
    b pitch_setup                   // 0x7C0: row origin, then the centre denominator
points_loop:
2:  ldrsh w8, [x20, #2]
    ldrsh w9, [x20, #6]
    sub w13, w9, w8
    add w13, w13, w10, lsl #1       // uninset cell height
    cmp w13, #0
    b.le 5f                         // unfilled / degenerate cell
    add w14, w8, w9
    madd w14, w14, w24, w15         // (top + bottom) * shown + 2 * row origin delta * shown
    cmp w14, #0
    cneg w14, w14, mi
    add w14, w14, w23
    udiv w14, w14, w12
    cneg w14, w14, mi               // round signed centre half away from zero
    mul w13, w13, w24
    add w13, w13, w2, lsr #1
    udiv w13, w13, w2               // rounded raw height at this desqueeze
    sub w13, w13, w10, lsl #1
    cmp w13, #1
    csinc w13, w13, wzr, ge         // non-empty outline
    sub w8, w14, w13, lsr #1
    add w9, w8, w13
    strh w8, [x20, #2]
    strh w9, [x20, #6]
5:  add x20, x20, #8
    subs w19, w19, #1
    b.ne 2b
6:  b AP_POINTS_DONE                // restore AP4 callee-saved registers
7:  subs w9, w24, w23               // displaced instruction for AP4's own loop
    b AP_POINTS_NEXT
8:  b AP_POINTS_DONE                // unknown unsqueezed window during a switch

/* The fit at 0x400 has already run and verified a live, local window.  Grant
 * only the exact open-gate EVF fit (stock 1280x960 window, mode 0, result
 * 1280x848, current file is the associated open-gate clip).  Every other case
 * keeps the one-slot ceiling. */
.global evf_full
evf_full:                           // from evf_fit_hook
    cbnz w22, 9f
    ldrh w9, [sp, #0x46]
    ldrh w10, [sp, #0x48]
    orr w9, w9, w10
    cbnz w9, 9f
    ldrh w9, [sp, #0x4a]
    cmp w9, #1280
    b.ne 9f
    ldrh w9, [sp, #0x4c]
    cmp w9, #960
    b.ne 9f
    ldrh w9, [x19, #2]
    cmp w9, #1280
    b.ne 9f
    ldrh w9, [x19, #4]
    cmp w9, #848
    b.ne 9f
    ldr x9, =0xa0ff6f008            // open-gate private state: associated clip id and valid bit
    ldr x9, [x9]
    tbz x9, #32, 9f
    ldr x10, =0xa045f07d8           // current playback media record
    ldr w11, [x10]
    cmp w9, w11
    b.ne 9f
    ldrb w11, [x10, #0x14]
    cbz w11, 9f
    b evf_fit_done
9:  movz w11, #SLOT_PIXELS_LO       // the displaced slot check
    b evf_fit_slot_check
.ltorg

/* ---- 0x7C0: wide-area AF point rows ------------------------------------------
 * Inside the cell routine above, after it recognises the native/shown window
 * and computes the per-side inset.  Prepare the centre mapping once.
 * w2 native height, w23 grid height, w24 shown height, x22 point record.
 * The loop computes (top + bottom) * shown + w15, then divides by 2*grid.
 * w15 is free throughout that loop.  It holds 2*row_origin_delta*shown. */
.org 0x7c0
.balign 4
.global pitch_setup
pitch_setup:
    mov w15, wzr
    ldr x9, =0xa0ff6f004           // open-gate view: 1 standby, 2 recording
    ldr w9, [x9]
    sub w9, w9, #1
    cmp w9, #1
    b.hi 1f
    ldr w9, [x22, #4]
    cmp w9, #4                     // FX movie, layout 3 in both table banks
    b.ne 1f
    ldrb w9, [x22, #8]
    cbnz w9, 1f                    // independently masked special layouts
    ldr w8, [x22]
    cmp w8, #1
    mov w9, #852
    mov w11, #682
    csel w9, w9, w11, eq
    cmp w2, w9
    b.ne 1f
    // Same bitmap row and column in the factory FX photo table.  The native
    // step is unchanged.  Its first row has a different origin, and the
    // movie table numbers its first nominal row 1, not 0.
    cmp w8, #1
    mov w9, #132                   // 2*(97 - 75 + 44), standard EVF
    mov w11, #104                  // 2*(71 - 55 + 36), rear/small EVF
    csel w9, w9, w11, eq
    mul w15, w9, w24
    mov w23, w2
1:
    lsl w12, w23, #1
    b points_loop
.ltorg
