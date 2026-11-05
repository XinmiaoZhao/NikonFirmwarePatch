/* AP4: anamorphic desqueeze preview on the C3 04.81.c3 payload.  AP3 (../ap3/ap3_hooks.S, body steps passed:
 * ../ap3_body_20261104/README.md) with one body changed: ap_af_points_hook (item 3a), the lit AF points of wide-area AF,
 * which AP1 to AP3 mapped as screen rows although the stock draws them below the shown window's top.  Everything else is
 * AP3's source.
 *
 * AP3 was AP2 (../ap2/ap2_hooks.S) with two bodies changed after the AP2 body test (../ap2_body_20261104/README.md):
 * ap_corner_calc_tail (item 4) and ap_preview_tail (item 6).  The fixed-table corner path keeps AP2's behaviour (its loops
 * moved into the helpers ap_corner_edges and ap_corner_shift, shared with the new computed path).
 *
 * AP2 was AP1 (../ap1/ap1_hooks.S) with five changes: the frame reconcile (cold-boot fix), the corner marks of 404158D4, the zoom
 * navigator, movie playback and the submenu.  Linked at 0x40970000 like AP1; the page 0x4097F000 stays zero in the package
 * and its RAM alias A0FF7F000 holds the private words (AP_STATE +0, AP_LATCH +8).  The submenu tables are data written by
 * build_ap4.py after this code (they hold absolute pointers, which this linker does not relocate).
 *
 * Setting: byte A03D5C0AD as AP1 (0 = off, 1..7 = 1.25x 1.30x 1.33x 1.50x 1.60x 1.80x 2.00x; other values = off).
 *
 * 1. Window (AP1): ap_window_hook at the four first-display calls of 411871AC.  New: when the rectangle is the LV display
 *    object's first display (A03BB751C +0x20, written by the stock recompute 40F32E58 and by D9's og_leave_display_hook) it
 *    also writes AP_LATCH in one 64-bit store: output type | class << 8 | flag << 16 | desired setting << 24 | written y0 << 32
 *    | written y1 << 48 (desired = setting 1..7 in video, else 0); zero when the stock leaf wrote nothing or the output type is
 *    not 0/1.
 * 2. Frame reconcile (ap1_body_20261103 §2): the stock rewrites the first display only when its change mask (40F31B64) is
 *    set, and the setting byte is not compared, so after a cold start a menu change or a bank switch in video live view was
 *    not applied.  ap_frame_hook replaces the per-frame copy of the display object into the snapshot (40F2870C: bl 4127A900,
 *    x0 = snapshot +0x198, x1 = A03BB751C, x2 = 0x1F0; 40F28488 holds the object lock A03BB6BD0 from 40F28620 to 40F2B034,
 *    the same lock 40F30108 holds while it calls 411871AC and 40F36000).  Before the copy, when open gate is not active
 *    (OG_STATE +4 = 0 and nothing pending at +0x10; open gate rewrites every snapshot itself), the latch describes the
 *    object (its rows are the object's +0x22/+0x26, its type and flag are the current A0292A604 / A03BBA348) and the desired
 *    setting differs from the latched one, it redoes 40F32E58-40F32E74 with the latched type, class and flag: ap_window_hook
 *    (object +0x20), +0x14C = +0xC, 40F36000 into +0x150 with D9's argument block.  The copy then takes the new window.
 *    A latch left by an earlier power-on (OFF/ON keeps this RAM) is used only if it still matches the object.
 * 3. AF frame, touch, bank copy, value text: as AP1.
 * 3a. Lit AF points (AP4; ../ap3_body_20261104/README.md section 2): 40386BE8 calls 403EB928 (b 41186C68) with x1 = the
 *    point record (+0 grid output: 0 rear LCD, 1 EVF, 2 EVF small, others not the GUI screens; +4 AF mode, +8 flag, +9
 *    table set), which lays the lit points out on the grid A029C453C / A029C3F9C + output * 0xA0 + layout * 0x14 (layout
 *    from 41187104) and shrinks each by inset / 2 (44B7FD0C[output]).  Their rows are offsets below the window top: the
 *    drawer adds the GUI window (A03229BC8 +8, the 5th argument of 4037FF0C) when it draws them.  Layouts 3-7 are laid out
 *    for a 16:9 window as wide as the grid (Hd = 9 W / 16: 576 rows for W = 1024, 720 for 1280), layouts 0-2 for a 3:2
 *    one (Hd = round(2 W / 3)).  ap_af_points_hook moves each cell's top and bottom edge E to round(E * H / Hd) and keeps
 *    the inset: y0' = round((y0 - i) * H / Hd) + i, y1' = round((y1 + i) * H / Hd) - i, i = inset / 2 (half away from
 *    zero; x untouched), H = the GUI window's height, when the output is 0..2 and the GUI window is as wide as its grid
 *    (W = 1280 for output 1, else 1024), in video (property 218Ch = 1), and either open gate shows its 3:2 view
 *    (OG_STATE +4 != 0) or ap_map holds; a window within 1/64 of Hd (a stock window and its rounding) is left unchanged.
 *    This is the rule of the computed corner bars (item 4), applied in the grid's own space.
 * 4. Corner marks (404158D4, the four-corner AF area marks of wide-area AF and of AF-ON in zoom): it writes 8 bars
 *    (x0,y0,x1,y1 u16; one horizontal and one vertical per corner) for the output A032D0669 at A032E2B38 + output * 0x44,
 *    computed (404161F8-40416290) or from a fixed table (40415B54-40415B78), then compares and redraws from 40415B80.
 *    Both paths fill the same slots (slot i is redrawn as part 42AE7996[i]): top corners in slots 0 1 4 5, bottom corners
 *    in 2 3 6 7.  The bars are in the output's own space: output 0 is 720x480 for the rear LCD layout (1024x682), output 2
 *    is 1280x960 for the EVF layout (1280x960); output 1 is never changed.
 *    - Fixed table (zoom, AF-ON; native positions, right on the body with AP2): ap_corner_table_tail (40415B7C) moves the
 *      top bars by map(T) - T and the bottom bars by map(B) - B (T = smallest y0 of the top bars, B = largest y1 of the
 *      bottom bars; empty bars skipped) while ap_map holds and the GUI window is that output's layout (AP2).
 *    - Computed (wide-area box; AP3): the stock adds the shown window's top-left (sp+8: the window rectangle converted to
 *      the output at 40415EB0) to the box A03227818 converted from the source space A032CFF88+0x184 (Sw, Sh) to the whole
 *      output, and the box is laid out for a 16:9 window as wide as the source space, so its offsets from the window top
 *      do not follow the window's height (body photos: rows 49 and 527 below the window top with open gate, AP1 and AP2
 *      alike).  ap_corner_calc_tail (40416294) moves each group so that its outer edge E lands at
 *      Y0 + round((E - Y0) * H / H169), Y0 and H = the shown window's top and height (sp+8), H169 = Ho * Sw * 9 / (16 Sh)
 *      (405 on the rear layout), when the GUI window is that output's layout, in video (property 218Ch = 1), and either
 *      open gate shows its 3:2 view (OG_STATE +4 != 0) or ap_map holds.  A window within 1/64 of H169 (a 16:9 window and
 *      its rounding) is left unchanged.
 * 5. Zoom navigator (4041333C): the background rectangle from the layout table (stored to sp+0x48 at 40413724 and
 *    40413B58) keeps its width and bottom edge and gets height round(h * hs / hn) while ap_map holds.  The inner rectangle
 *    and the yellow window frame are derived from it with 40C7B988 (flags 0x60: x and y scaled independently), so the frame
 *    follows.
 * 6. Movie playback: 407138D0 (C3: b 40960A00, the open-gate playback_fit_hook) branches to ap_playback_fit_hook, which
 *    calls the C3 hook (and so the stock fit) and then, for a setting 1..7 and a display window at most 1280 wide (rear LCD
 *    1024, EVF 1280; HDMI stays stock), shrinks the result height (+4, multiple of 8) to 8 * round(h / (8 S)) and centres
 *    the rectangle (+8, +0xC) in the old one.  All 8 callers (40718484, 40718ED8) are the movie playback page.  The paused
 *    page shows the clip's 1920x1080 preview JPEG through another path (407D2EA8, the full-page static preview, where C3's
 *    open-gate hooks already widen the destination); ap_preview_tail shrinks that destination the same way.  AP2 took only
 *    the full-width single-image page; AP3 takes every destination of a movie preview request (the overview, highlights and
 *    RGB histogram pages draw the same 1920x1080 preview into smaller boxes; 160x120 thumbnails are another source).  The
 *    value is the current setting, read at every call (Sony, Panasonic: one setting for live view and playback).
 * 7. Submenu: the desqueeze row (item 310F) enters state B6h, whose page is a copy of the stock N-RAW quality list with 8
 *    rows (Off, 1.25x ... 2.00x).  ap_sub_entry puts the cursor and the mark on the stored value (as C3's ProRes entry);
 *    ap_sub_ok stores the cursor row 0..7 (as C3's ProRes OK, which keeps the stock return transition).
 */
#define SETTING     0xA03D5C0AD
#define MOVIE_218C  0xA03D7C94C
#define AP_STATE    0xA0FF7F000
#define AP_LATCH    0xA0FF7F008
#define GUI_LV      0xA03229BC8
#define AP_ITEM     0x310F
#define VALUE_CHILD 0x4BA7
#define TEXT_SLOT   0x49
#define TEXT_STYLE  4
#define LV_DISPLAY  0xA03BB751C
#define LV_FIRST    0xA03BB753C
#define LV_RECORD   0xA03BB74B4
#define LV_TYPE1    0xA0292A604
#define LV_FLAG     0xA03BBA348
#define OG_STATE    0xA0FF6F000
#define CORNER_BARS 0xA032E2B38
#define CORNER_OUT  0xA032D0669
#define CORNER_SRC  0xA032D010C                   // A032CFF88 + 0x184: source space (w, h) of the computed box
#define POINT_INSET 0x44B7FD0C                   // s16 per grid output: the shrink of the lit points (41186C68)

.text
.balign 16
.global ap_window_hook
ap_window_hook:
    stp x29, x30, [sp, #-96]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    stp x25, x26, [sp, #64]
    stp x27, x28, [sp, #80]
    mov x19, x3
    mov w20, w0
    mov w27, w1                     // class
    mov w28, w2                     // flag
    bl original_411871AC
    mov w21, w0                     // stock result
    cbz w21, 8f                     // no rectangle written
    cmp w20, #1
    b.hi 8f                         // external layouts: unchanged, no record
    ldrh w22, [x19, #2]             // native y0
    ldrh w23, [x19, #6]             // native y1
    mov w10, w22                    // shown y0
    mov w11, w23                    // shown y1
    ldr x8, =MOVIE_218C
    ldr w8, [x8]
    cmp w8, #1
    b.ne 5f                         // not video
    ldr x8, =SETTING
    ldrb w8, [x8]
    sub w8, w8, #1
    cmp w8, #6
    b.hi 5f                         // off or not a setting value
    adr x9, ap_ratios
    add x9, x9, w8, uxtw #2
    ldrh w25, [x9]                  // num
    ldrh w26, [x9, #2]              // den
    subs w24, w23, w22              // h
    b.ls 5f
    mul w8, w24, w26                // h * den
    lsl w9, w25, #1                 // 2 num
    udiv w26, w8, w9                // q
    msub w8, w26, w9, w8            // r
    lsl w8, w8, #1
    cmp w8, w9                      // 2r against 2num
    b.lo 2f
    b.hi 1f
    tbz w26, #0, 2f                 // tie: keep the even q
1:  add w26, w26, #1
2:  lsl w26, w26, #1                // h' (even)
    cbz w26, 5f
    cmp w26, w24
    b.hs 5f
    sub w8, w24, w26
    lsr w8, w8, #2
    add w10, w22, w8, lsl #1        // y0'
    add w11, w10, w26               // y1'
    strh w10, [x19, #2]
    strh w11, [x19, #6]
5:  mov w8, w22
    bfi x8, x23, #16, #16
    bfi x8, x10, #32, #16
    bfi x8, x11, #48, #16
    ldr x9, =AP_STATE
    str x8, [x9]                    // one 64-bit store: readers never see half a pair
    ldr x9, =LV_FIRST
    cmp x19, x9
    b.ne 9f                         // not the display object's first display: no latch
    ldr x8, =MOVIE_218C
    ldr w8, [x8]
    cmp w8, #1
    ldr x9, =SETTING
    ldrb w9, [x9]
    csel w9, w9, wzr, eq
    sub w8, w9, #1
    cmp w8, #6
    csel w9, w9, wzr, ls            // desired setting, the rule above
    and w8, w20, #0xff
    bfi x8, x27, #8, #8
    bfi x8, x28, #16, #8
    bfi x8, x9, #24, #8
    bfi x8, x10, #32, #16
    bfi x8, x11, #48, #16
    ldr x9, =AP_LATCH
    str x8, [x9]
    b 9f
8:  ldr x9, =LV_FIRST
    cmp x19, x9
    b.ne 9f
    ldr x9, =AP_LATCH
    str xzr, [x9]                   // the object's first display is not ours to reconcile
9:  mov w0, w21
    ldp x27, x28, [sp, #80]
    ldp x25, x26, [sp, #64]
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #96
    ret

.balign 16
.global ap_frame_hook
ap_frame_hook:                      // 40F2870C: bl 4127A900 (memcpy snapshot +0x198 <- A03BB751C, 0x1F0); object lock held
    stp x29, x30, [sp, #-112]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    str x23, [sp, #48]
    mov x19, x0
    mov x20, x1
    mov x21, x2
    ldr x8, =OG_STATE
    ldr w9, [x8, #4]
    cbnz w9, 9f                     // open gate: view_commit_hook rewrites every snapshot
    ldr w9, [x8, #0x10]
    cbnz w9, 9f                     // open gate restore pending
    ldr x8, =AP_LATCH
    ldr x22, [x8]
    cbz x22, 9f
    ldr x23, =LV_DISPLAY
    ldrh w9, [x23, #0x22]
    ubfx x10, x22, #32, #16
    cmp w9, w10
    b.ne 9f                         // the object's rows are not the latched ones
    ldrh w9, [x23, #0x26]
    lsr x10, x22, #48
    cmp w9, w10
    b.ne 9f
    ldr x8, =LV_TYPE1
    ldr w9, [x8]
    cmp w9, #0xb
    csel w9, wzr, w9, hi            // as 40F32E30
    and w10, w22, #0xff
    cmp w9, w10
    b.ne 9f                         // output type changed: the stock recompute will run
    ldr x8, =LV_FLAG
    ldrb w9, [x8]
    ubfx w10, w22, #16, #8
    cmp w9, w10
    b.ne 9f
    ldr x8, =MOVIE_218C
    ldr w8, [x8]
    cmp w8, #1
    ldr x9, =SETTING
    ldrb w9, [x9]
    csel w9, w9, wzr, eq
    sub w8, w9, #1
    cmp w8, #6
    csel w9, w9, wzr, ls            // desired setting now
    ubfx w10, w22, #24, #8
    cmp w9, w10
    b.eq 9f                         // already applied
    and w0, w22, #0xff              // redo 40F32E58: type, class, flag, object +0x20
    ubfx w1, w22, #8, #8
    ubfx w2, w22, #16, #8
    add x3, x23, #0x20
    bl ap_window_hook
    ldr w9, [x23, #0xc]
    str w9, [x23, #0x14c]           // 40F32E70
    ldp w9, w10, [x23, #0x64]
    stp w9, w10, [sp, #56]          // +0, +4: external output size
    add x9, x23, #0x6c
    str x9, [sp, #64]               // +8: output record (as D9)
    ldr x9, =LV_RECORD
    add x10, x9, #4
    stp x9, x10, [sp, #72]          // +0x10, +0x18: A03BB74B4, A03BB74B8
    str xzr, [sp, #88]              // +0x20, +0x24: area 0, as the stock placement call (40F32E68)
    add x9, x23, #0x18
    add x10, x23, #0x150
    stp x9, x10, [sp, #96]          // +0x28, +0x30
    add x0, sp, #56
    bl original_40F36000            // placement, object +0x150
    dsb ishst
9:  mov x0, x19
    mov x1, x20
    mov x2, x21
    ldr x23, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #112
    b original_4127A900             // the replaced copy

/* w0 = 1 with w1 = native y0, w2 = native h, w3 = shown y0, w4 = shown h when the GUI's copy of the LV window is the shown
 * window of AP_STATE and that window is squeezed; otherwise w0 = 0.  Leaf; clobbers x0-x4, x8-x10.  (AP1) */
.balign 16
ap_map:
    ldr x8, =AP_STATE
    ldr x8, [x8]
    ubfx x1, x8, #0, #16
    ubfx x9, x8, #16, #16
    ubfx x3, x8, #32, #16
    lsr x10, x8, #48
    subs w2, w9, w1
    b.ls 8f
    subs w4, w10, w3
    b.ls 8f
    cmp w4, w2
    b.hs 8f                         // not squeezed
    ldr x8, =GUI_LV
    ldrh w9, [x8, #0xA]
    cmp w9, w3
    b.ne 8f
    ldrh w9, [x8, #0xE]
    cmp w9, w10
    b.ne 8f
    mov w0, #1
    ret
8:  mov w0, #0
    ret

/* w8 = y0s + round((w8 - y0n) * hs / hn), half away from zero; w1-w4 as ap_map leaves them, w9 = hn / 2.  Leaf; clobbers w8.  (AP1) */
.balign 16
ap_map_y:
    sub w8, w8, w1
    mul w8, w8, w4
    cmp w8, #0
    b.lt 1f
    add w8, w8, w9
    b 2f
1:  sub w8, w8, w9
2:  sdiv w8, w8, w2
    add w8, w8, w3
    ret

.balign 16
.global ap_af_rect_hook
ap_af_rect_hook:                    // bl 40387648 (x0 out rectangle, x1 &centre x/y, x2 &size w/h)  (AP1)
    stp x29, x30, [sp, #-48]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    str x21, [sp, #32]
    mov x19, x0
    mov x20, x1
    mov x21, x2
    bl ap_map
    cbz w0, 8f
    lsr w9, w2, #1                  // hn / 2
    ldrh w8, [x20, #2]
    bl ap_map_y                     // cy'
    ldrh w10, [x20]
    strh w10, [sp, #40]
    strh w8, [sp, #42]
    ldrh w8, [x21, #2]
    mul w8, w8, w4
    add w8, w8, w9
    udiv w8, w8, w2
    mov w10, #2
    cmp w8, #2
    csel w8, w8, w10, hs            // h'
    ldrh w10, [x21]
    strh w10, [sp, #44]
    strh w8, [sp, #46]
    add x20, sp, #40                // the copies: the caller's centre and size stay native
    add x21, sp, #44
8:  mov x0, x19
    mov x1, x20
    mov x2, x21
    bl original_40387648
    ldr x21, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #48
    ret

.balign 16
.global ap_af_points_hook
ap_af_points_hook:                  // 40386BE8: bl 403EB928 (b 41186C68: x0 AF point bits, x1 &point record, w2 count, x3 out)
    stp x29, x30, [sp, #-64]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    mov w19, w2
    mov x20, x3
    mov x22, x1
    bl original_403EB928
    mov w21, w0                     // stock result
    tbz w21, #0, 9f                 // nothing written (a null argument)
    mov w8, #0x195
    cmp w19, w8
    csel w19, w19, w8, ls           // as 41186C68: at most 0x195 rectangles
    cbz w19, 9f
    ldr w8, [x22]                   // grid output
    cmp w8, #2
    b.hi 9f                         // not a GUI screen grid
    mov w9, #1024
    mov w10, #1280
    cmp w8, #1
    csel w23, w10, w9, eq           // grid width W
    ldr x9, =GUI_LV
    ldrh w10, [x9, #8]
    ldrh w11, [x9, #0xC]
    sub w10, w11, w10
    cmp w10, w23
    b.ne 9f                         // the GUI window is not as wide as the grid
    ldrh w10, [x9, #0xA]
    ldrh w11, [x9, #0xE]
    subs w24, w11, w10              // H
    b.le 9f
    ldr x8, =MOVIE_218C
    ldr w8, [x8]
    cmp w8, #1
    b.ne 9f                         // not video
    ldr x8, =OG_STATE
    ldr w8, [x8, #4]
    cbnz w8, 3f                     // open gate shows its 3:2 view
    bl ap_map
    cbz w0, 9f
3:  mov x0, x22
    bl original_41187104            // layout (leaf: reads +4 and +8; clobbers x8-x10)
    cmp w0, #2
    b.hi 4f
    lsl w9, w23, #1
    add w9, w9, #1
    mov w10, #3
    udiv w23, w9, w10               // Hd = round(2 W / 3): a 3:2 grid (layouts 0-2)
    b 5f
4:  add w23, w23, w23, lsl #3
    lsr w23, w23, #4                // Hd = 9 W / 16: a 16:9 grid (layouts 3-7)
5:  subs w9, w24, w23
    cneg w9, w9, mi
    cmp w9, w23, lsr #6
    b.ls 9f                         // within 1/64 of Hd: unchanged
    ldr w8, [x22]
    ldr x9, =POINT_INSET
    ldrsh w10, [x9, x8, lsl #1]
    add w10, w10, w10, lsr #31
    asr w10, w10, #1                // i = inset / 2, as 41186C68
    lsr w11, w23, #1                // Hd / 2
1:  ldrsh w8, [x20, #2]
    sub w8, w8, w10
    bl ap_point_y
    add w8, w8, w10
    strh w8, [x20, #2]
    ldrsh w8, [x20, #6]
    add w8, w8, w10
    bl ap_point_y
    sub w8, w8, w10
    strh w8, [x20, #6]
    add x20, x20, #8
    subs w19, w19, #1
    b.ne 1b
9:  mov w0, w21
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #64
    ret

/* w8 = round(w8 * H / Hd), half away from zero; w24 = H, w23 = Hd, w11 = Hd / 2.  Leaf; clobbers w8.  (AP4) */
.balign 16
ap_point_y:
    mul w8, w8, w24
    cmp w8, #0
    b.lt 1f
    add w8, w8, w11
    b 2f
1:  sub w8, w8, w11
2:  sdiv w8, w8, w23
    ret

.balign 16
.global ap_touch_point_hook
ap_touch_point_hook:                // bl 4043C234 (x0 &screen point x/y; 4043C234 itself checks for null)  (AP1)
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    str x19, [sp, #16]
    mov x19, x0
    cbz x19, 8f
    bl original_40395DFC            // fresh GUI copy of the LV information (4043C234 takes it again)
    bl ap_map
    cbz w0, 8f
    lsr w9, w4, #1                  // hs / 2
    ldrh w8, [x19, #2]
    sub w8, w8, w3
    mul w8, w8, w2
    cmp w8, #0
    b.lt 1f
    add w8, w8, w9
    b 2f
1:  sub w8, w8, w9
2:  sdiv w8, w8, w4
    add w8, w8, w1
    cmp w8, w1
    csel w8, w8, w1, ge             // not above the native window
    add w9, w1, w2
    sub w9, w9, #1
    cmp w8, w9
    csel w8, w8, w9, le             // not below it
    ldrh w10, [x19]
    strh w10, [sp, #24]
    strh w8, [sp, #26]
    add x19, sp, #24                // the copy: the gesture handler's point stays as touched
8:  mov x0, x19
    bl original_4043C234
    ldr x19, [sp, #16]
    ldp x29, x30, [sp], #32
    ret

/* x8 = y in the output's space (signed), w1-w4 as ap_map, x13 = output height Ho, x14 = layout height Hl:
 * w8 = round((y0s*Ho*hn + (y*Hl - y0n*Ho)*hs) / (Hl*hn)), half away from zero (the ap_map_y map in layout space, carried
 * to the output space).  Leaf; clobbers x8-x10. */
.balign 16
ap_map_out_y:
    mul x9, x8, x14
    mul x10, x1, x13
    sub x9, x9, x10
    mul x9, x9, x4
    mul x10, x3, x13
    madd x9, x10, x2, x9            // numerator
    mul x10, x14, x2                // denominator
    cmp x9, #0
    b.lt 1f
    add x9, x9, x10, lsr #1
    b 2f
1:  sub x9, x9, x10, lsr #1
2:  sdiv x8, x9, x10
    ret

/* Corner bar groups of the bars at x16 (8 slots of x0,y0,x1,y1 s16; top corners in slots 0 1 4 5, bottom in 2 3 6 7):
 * w11 = T, the smallest y0 of the top bars (0x7fff if none), w12 = B, the largest y1 of the bottom bars (-0x8000 if none);
 * empty (all-zero) bars are skipped.  Leaf; clobbers x7-x10. */
.balign 16
ap_corner_edges:
    mov w11, #0x7fff
    mov w12, #-0x8000
    mov x7, xzr
3:  ldr x8, [x16, x7, lsl #3]
    cbz x8, 4f                      // empty bar
    tbnz w7, #1, 31f
    sbfx x9, x8, #16, #16
    cmp w9, w11
    csel w11, w9, w11, lt
    b 4f
31: asr x10, x8, #48
    cmp w10, w12
    csel w12, w10, w12, gt
4:  add x7, x7, #1
    cmp x7, #8
    b.lo 3b
    ret

/* Move the top bars at x16 by w5 rows and the bottom bars by w6 rows (y0 and y1; x untouched; empty bars skipped).
 * Leaf; clobbers x3, x7-x10. */
.balign 16
ap_corner_shift:
    mov x7, xzr
5:  add x9, x16, x7, lsl #3
    ldr x8, [x9]
    cbz x8, 6f
    tst w7, #2
    csel w3, w5, w6, eq             // top bar or bottom bar, by slot
    ldrh w10, [x9, #2]
    add w10, w10, w3
    strh w10, [x9, #2]
    ldrh w10, [x9, #6]
    add w10, w10, w3
    strh w10, [x9, #6]
6:  add x7, x7, #1
    cmp x7, #8
    b.lo 5b
    ret

/* Fixed-table corner bars of the current output (AP2): each group's outer edge through ap_map.  Called with bl from
 * ap_corner_table_tail; uses x0-x17 only (x30 kept in x17). */
.balign 16
ap_corner_map:
    mov x17, x30
    ldr x8, =CORNER_OUT
    ldrb w15, [x8]
    ldr x8, =GUI_LV
    ldrh w9, [x8, #0xC]             // x1 of the GUI window: 1024 rear LCD layout, 1280 EVF layout
    cbnz w15, 1f
    cmp w9, #1024
    b.ne 9f
    mov x13, #480                   // output 0: 720x480 for the 1024x682 layout
    mov x14, #682
    b 2f
1:  cmp w15, #2
    b.ne 9f
    cmp w9, #1280
    b.ne 9f
    mov x13, #960                   // output 2: 1280x960, the EVF layout itself
    mov x14, #960
2:  bl ap_map
    cbz w0, 9f
    ldr x16, =CORNER_BARS
    mov w8, #0x44
    madd x16, x15, x8, x16
    bl ap_corner_edges
    mov w5, wzr                     // dT
    mov w6, wzr                     // dB
    mov w8, #0x7fff
    cmp w11, w8
    b.eq 41f                        // no top bars
    sxtw x8, w11
    bl ap_map_out_y
    sub w5, w8, w11
41: mov w8, #-0x8000
    cmp w12, w8
    b.eq 42f                        // no bottom bars
    sxtw x8, w12
    bl ap_map_out_y
    sub w6, w8, w12
42: bl ap_corner_shift
9:  mov x30, x17
    ret

/* x8 = Y0 + round((x8 - Y0) * num / den), half away from zero; x14 = Y0, x5 = num, x6 = den (> 0).  Leaf; clobbers x9. */
.balign 16
ap_corner_place:
    sub x8, x8, x14
    mul x8, x8, x5
    lsr x9, x6, #1
    cmp x8, #0
    b.lt 1f
    add x8, x8, x9
    b 2f
1:  sub x8, x8, x9
2:  sdiv x8, x8, x6
    add x8, x8, x14
    ret

/* Computed corner bars of the current output (AP3, header item 4): each group's outer edge E to
 * Y0 + round((E - Y0) * H / H169), H / H169 = (16 H Sh) / (9 Ho Sw).  Called with bl from ap_corner_calc_tail, so sp is
 * 404158D4's frame (sp+8: the shown window converted to the output, x0,y0,x1,y1 u16); uses x0-x17 only (x30 kept in x17). */
.balign 16
ap_corner_calc_map:
    mov x17, x30
    ldr x8, =CORNER_OUT
    ldrb w15, [x8]
    ldr x8, =GUI_LV
    ldrh w9, [x8, #0xC]             // x1 of the GUI window: 1024 rear LCD layout, 1280 EVF layout
    cbnz w15, 1f
    cmp w9, #1024
    b.ne 9f
    mov x13, #480                   // output 0: 720x480
    b 2f
1:  cmp w15, #2
    b.ne 9f
    cmp w9, #1280
    b.ne 9f
    mov x13, #960                   // output 2: 1280x960
2:  ldr x8, =MOVIE_218C
    ldr w8, [x8]
    cmp w8, #1
    b.ne 9f                         // not video
    ldr x8, =OG_STATE
    ldr w8, [x8, #4]
    cbnz w8, 3f                     // open gate shows its 3:2 view
    bl ap_map
    cbz w0, 9f
3:  ldrh w14, [sp, #0xA]            // Y0
    ldrh w9, [sp, #0xE]
    subs w9, w9, w14                // H
    b.le 9f
    ldr x8, =CORNER_SRC
    ldrh w10, [x8]                  // Sw
    ldrh w11, [x8, #2]              // Sh
    cbz w10, 9f
    cbz w11, 9f
    mul x5, x9, x11
    lsl x5, x5, #4                  // num = 16 H Sh
    mul x6, x13, x10
    add x6, x6, x6, lsl #3          // den = 9 Ho Sw
    subs x8, x5, x6
    cneg x8, x8, mi
    cmp x8, x6, lsr #6
    b.ls 9f                         // within 1/64 of 16:9 (a stock window, rounding): unchanged
    ldr x16, =CORNER_BARS
    mov w8, #0x44
    madd x16, x15, x8, x16
    bl ap_corner_edges
    mov w1, wzr                     // dT
    mov w2, wzr                     // dB
    mov w8, #0x7fff
    cmp w11, w8
    b.eq 41f                        // no top bars
    sxtw x8, w11
    bl ap_corner_place
    sub w1, w8, w11
41: mov w8, #-0x8000
    cmp w12, w8
    b.eq 42f                        // no bottom bars
    sxtw x8, w12
    bl ap_corner_place
    sub w2, w8, w12
42: mov w5, w1
    mov w6, w2
    bl ap_corner_shift
9:  mov x30, x17
    ret

.balign 16
.global ap_corner_calc_tail
ap_corner_calc_tail:                // 40416294: tbnz w20, #0, 40415B80 (then 40416298: b 40415E08), after the computed bars
    bl ap_corner_calc_map
    tbnz w20, #0, 1f
    b original_40415E08
1:  b original_40415B80

.balign 16
.global ap_corner_table_tail
ap_corner_table_tail:               // 40415B7C: tbz w20, #0, 40415E08 (else 40415B80), after the fixed-table bars
    bl ap_corner_map
    tbz w20, #0, 1f
    b original_40415B80
1:  b original_40415E08

.balign 16
.global ap_nav_bg_x9
ap_nav_bg_x9:                       // 40413724: str x9, [sp, #0x48] (navigator background x0|y0|x1|y1)
    mov x15, x9
    b ap_nav_bg
.global ap_nav_bg_x8
ap_nav_bg_x8:                       // 40413B58: str x8, [sp, #0x48]
    mov x15, x8
ap_nav_bg:                          // entered by bl: sp is the navigator's; uses x0-x4, x8-x11, x15, x16
    mov x16, x30
    bl ap_map
    cbz w0, 8f
    ubfx x9, x15, #16, #16          // y0
    lsr x10, x15, #48               // y1
    subs w11, w10, w9               // h
    b.ls 8f
    mul w11, w11, w4
    add w11, w11, w2, lsr #1
    udiv w11, w11, w2               // round(h * hs / hn)
    cbz w11, 8f
    sub w9, w10, w11                // bottom edge kept
    bfi x15, x9, #16, #16
8:  str x15, [sp, #0x48]            // the replaced store
    mov x30, x16
    ret

.balign 16
.global ap_playback_fit_hook
ap_playback_fit_hook:               // 407138D0 (C3: b 40960A00): w0/w1 media size, w2 mode, x3 window record, x4 result
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    mov x19, x4
    mov x20, x3
    bl original_40960A00            // C3 open-gate fit, then the stock fit (returns here)
    ldr x8, =SETTING
    ldrb w8, [x8]
    sub w9, w8, #1
    cmp w9, #6
    b.hi 9f                         // off
    ldrb w10, [x19]
    cbz w10, 9f                     // no fit (the stock copy of an empty record)
    ldrsh w10, [x20, #6]
    ldrsh w11, [x20, #0xa]
    sub w10, w11, w10
    cmp w10, #1280
    b.gt 9f                         // wider than the EVF window: HDMI, stock
    adr x10, ap_ratios
    add x10, x10, w9, uxtw #2
    ldrh w11, [x10]                 // num
    ldrh w12, [x10, #2]             // den
    ldrh w13, [x19, #4]             // stock height (multiple of 8)
    mul w14, w13, w12
    add w14, w14, w11, lsl #2
    lsl w15, w11, #3
    udiv w14, w14, w15
    lsl w14, w14, #3                // h' = 8 * round(h * den / (8 num))
    cbz w14, 9f
    cmp w14, w13
    b.hs 9f
    sub w15, w13, w14
    lsr w15, w15, #2
    ldrsh w10, [x19, #8]
    add w10, w10, w15, lsl #1       // y0' = y0 + 2 * floor((h - h') / 4)
    add w11, w10, w14
    strh w14, [x19, #4]
    strh w10, [x19, #8]
    strh w11, [x19, #0xc]
9:  ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #32
    ret

/* Paused movie page: the full-page static preview request (407D2EA8: x0 request, dest x/y +0x30/+0x32, canvas w/h
 * +0x3C/+0x3E, dest w/h +0x40/+0x42; x1 source).  C3's hooks (40961960 -> 409615A0, open gate: full canvas) end with
 * 409616A4: b 407D2EAC after pushing 407D2EA8's frame; that branch comes here.  For a setting 1..7, the movie preview
 * (C3's own test: request kind 2, +0x50 = 0, source +0x58 = +0x60 = 0, source +0x64 = +0x68 = 1920x1080) and a canvas at
 * most 1280 wide, the destination height becomes 2*round_half_even(h / 2S) and moves down by 2*floor((h - h') / 4) (the
 * window rule), whatever the box: the single-image page and (AP3) the overview, highlights and RGB histogram boxes.  Uses x9-x15 only (function entry: arguments x0-x8 untouched). */
.balign 16
.global ap_preview_tail
ap_preview_tail:
    ldr x9, =SETTING
    ldrb w9, [x9]
    sub w9, w9, #1
    cmp w9, #6
    b.hi 9f
    ldr w10, [x0, #0x34]
    cmp w10, #2
    b.ne 9f
    ldr w10, [x0, #0x50]
    cbnz w10, 9f
    ldr w10, [x1, #0x58]
    cbnz w10, 9f
    ldr w10, [x1, #0x60]
    cbnz w10, 9f
    mov w11, #0x780
    movk w11, #0x438, lsl #16       // 1920x1080
    ldr w10, [x1, #0x64]
    cmp w10, w11
    b.ne 9f
    ldr w10, [x1, #0x68]
    cmp w10, w11
    b.ne 9f
    ldrh w10, [x0, #0x3c]
    cmp w10, #1280
    b.hi 9f                         // HDMI canvas: stock
    adr x10, ap_ratios
    add x10, x10, w9, uxtw #2
    ldrh w14, [x10]                 // num
    ldrh w15, [x10, #2]             // den
    ldrh w12, [x0, #0x42]           // h
    ldrh w13, [x0, #0x32]           // y
    mul w10, w12, w15
    lsl w11, w14, #1
    udiv w9, w10, w11               // q
    msub w10, w9, w11, w10          // r
    lsl w10, w10, #1
    cmp w10, w11
    b.lo 2f
    b.hi 1f
    tbz w9, #0, 2f                  // tie: keep the even q
1:  add w9, w9, #1
2:  lsl w9, w9, #1                  // h'
    cbz w9, 9f
    cmp w9, w12
    b.hs 9f
    sub w10, w12, w9
    lsr w10, w10, #2
    add w13, w13, w10, lsl #1
    strh w9, [x0, #0x42]
    strh w13, [x0, #0x32]
9:  b original_407D2EAC

.balign 16
/* x0 = video menu state: write the value text of row AP_ITEM.  (AP1) */
.balign 16
ap_row_text:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    str x19, [sp, #16]
    mov w1, #AP_ITEM
    mov w2, #VALUE_CHILD
    bl original_4050A6F0
    cbz x0, 9f
    mov x19, x0
    ldr x8, =SETTING
    ldrb w8, [x8]
    cmp w8, #7
    csel w8, w8, wzr, ls
    adr x9, ap_value_texts
    add x0, x9, w8, uxtw #3
    mov w1, #TEXT_SLOT
    mov w2, #TEXT_STYLE
    bl original_403F2920
    mov x0, x19
    mov w1, #TEXT_SLOT
    bl original_403F645C
9:  ldr x19, [sp, #16]
    ldp x29, x30, [sp], #32
    ret

.balign 16
.global ap_menu_refresh_hook
ap_menu_refresh_hook:               // value refresh callback of the video menu state (x0 = state)  (AP1)
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    mov x19, x0
    nop                            // native refresh is called once by the shared dispatcher
    mov x20, x0
    cbz x19, 1f
    mov x0, x19
    bl ap_row_text
1:  mov x0, x20
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #32
    ret

.balign 16
.global ap_sub_entry_hook
ap_sub_entry_hook:                  // entry callback of state B6h (x0 = state): cursor and mark on the stored value
    stp x19, x30, [sp, #-32]!
    str x20, [sp, #16]
    mov x19, x0
    ldr x8, =SETTING
    ldrb w8, [x8]
    cmp w8, #7
    csel w8, w8, wzr, ls
    adr x9, ap_option_items
    ldrh w20, [x9, w8, uxtw #1]
    bl original_403AE0F8            // entry guard (C3 ProRes entry: 1 = keep the cursor)
    cmp w0, #1
    b.eq 1f
    mov x0, x19
    mov w1, w20
    bl original_403B0048            // cursor on the item
1:  mov x0, x19
    mov w1, w20
    mov w2, #1
    ldr x20, [sp, #16]
    ldp x19, x30, [sp], #32
    b original_403B00B8             // mark on the item

.balign 16
.global ap_sub_ok_hook
ap_sub_ok_hook:                     // OK action of the 8 option rows (x0 = context): store the cursor row 0..7
    ldr x9, [x0]                    // state
    ldrh w11, [x9, #0x58]           // first shown row
    ldrh w10, [x9, #0x32]           // cursor within the shown rows
    add w10, w10, w11
    cmp w10, #7
    b.hi 1f
    ldr x8, =SETTING
    strb w10, [x8]
1:  ret

.ltorg
.balign 4
ap_ratios:                          // num, den for setting 1..7
    .hword 5, 4,  13, 10,  4, 3,  3, 2,  8, 5,  9, 5,  2, 1
ap_option_items:                    // item ids of the 8 option rows (setting 0..7); see build_ap2.py
    .hword 0x35B5, 0x35B6, 0x35B7, 0x35B8, 0x35BB, 0x35BC, 0x35BE, 0x35BF
.balign 8
ap_value_texts:                     // 8 bytes each, setting 0..7
    .ascii "OFF\0\0\0\0\0"
    .ascii "1.25x\0\0\0"
    .ascii "1.30x\0\0\0"
    .ascii "1.33x\0\0\0"
    .ascii "1.50x\0\0\0"
    .ascii "1.60x\0\0\0"
    .ascii "1.80x\0\0\0"
    .ascii "2.00x\0\0\0"
