/* E2 = E1 + the fixes from the E1 body test (open-gate line, 2026-11-12; analysis repository
 * research/open_gate_probe_20261018/e1_body_20261112).  New code only follows E1; D-series hooks whose test must
 * also accept 4128x2752 either get an E2 copy (site re-pointed by patcher.py) or an in-place check with the same
 * instruction count (og32_dims), so every earlier address stays where it was.
 *
 *   ft_ctrl_w22/w8/w21_hook  4056CB80 4056CC80 4056D0F0 4056D1A8 4056D3C8  file-type page: control 35CA (the 3:2 row)
 *                            reads as 30E5 (N-RAW) in the stock "tone-capable row" tests (description and tone hint
 *                            widgets, tone sub-page row filter)                                       (M2, M3)
 *   tone_ok_ctrl_hook        4056DAE0  tone sub-page OK: the 3:2 parent row selects N-RAW 3:2 with N-RAW's tone
 *                            item (flag, size memory and type as the file-type OK); other rows leave 3:2   (M3)
 *   ft_star_hook             4056C8E4  frame-size list star/no-star icons also for the ten 3:2 rows      (M5)
 *   og_*_low_hook            plan 13 (N-RAW 4.1K recording) chooses its front input, parameter template, two
 *                            plan tables, coordinates and D980 layout by rate (30/25/24p = oversampled full
 *                            readout).  Under 4.1K 3:2 (driver 14, 4140x2756 at every rate) these take the
 *                            50..120p variant, as plan 13 at 60p                                          (R1)
 *   film_icon_e2_hook        40797088  playback movie class: 4128x2752 N-RAW = stock 4.1K class 4        (P2)
 *   fx_icon_e2_hook          406C0280  crop 11 of a 4128x2752 N-RAW clip is FX, as 8256x5504              (P2)
 *   playback_capture_e2_hook 40711530  the 3:2 playback target also for 4128x2752 / 4140x2756              (P1)
 *   og32_dims                in-place helper for og_open_gate_file and the two preview hooks                (P1)
 *   setting_bank_normal_e2_hook 41015F80  D4 bank setter; clearing a bank's flag also clears its size memory
 */

#define STAR_TABLE     0x42B20318           /* 19 x {control, star icon, no-star icon} (stock N-RAW rows) */
#define QUALITY_ITEM   0x05001261

.text
.balign 16

/* ---- file-type page: the 3:2 row is an N-RAW row for the stock control tests ---------------------------------- */
/* \wr - 0x3000 == 0x5ca -> 0xe5; flags clobbered, no other register. */
.macro ctrl_map wr
    sub \wr, \wr, #3, lsl #12
    cmp \wr, #0x5ca
    b.ne 1f
    mov \wr, #0xe5
1:  add \wr, \wr, #3, lsl #12
.endm

/* 4056CB80 / 4056CC80 (bl; replaces ldr w22, [x8, #0x18]): page entry helpers.  Both functions save x30. */
.global ft_ctrl_w22_hook
ft_ctrl_w22_hook:
    ldr w22, [x8, #0x18]
    ctrl_map w22
    ret
/* 4056D0F0 / 4056D1A8 (bl; replaces ldr w8, [x8, #0x18]): cursor moved.  w9/w10 are set before and kept. */
.global ft_ctrl_w8_hook
ft_ctrl_w8_hook:
    ldr w8, [x8, #0x18]
    ctrl_map w8
    ret
/* 4056D3C8 (bl; replaces ldr w21, [x8, #0x18]): tone sub-page entry, parent row -> which rows stay visible. */
.global ft_ctrl_w21_hook
ft_ctrl_w21_hook:
    ldr w21, [x8, #0x18]
    ctrl_map w21
    ret

/* 4056DAE0 (bl; replaces ldr w2, [x8, #0x18]): tone sub-page OK, w2 = parent row control; w19 = stored type read at
 * the function entry.  The stock code then writes [type of the parent row, tone] and runs its "type changed" tail
 * when w19 differs.  x0-x18 are dead here except x2 (the result); x19-x23 and the frame are the caller's. */
.balign 16
.global tone_ok_ctrl_hook
tone_ok_ctrl_hook:
    ldr w2, [x8, #0x18]
    stp x29, x30, [sp, #-48]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    mov w21, w2
    ldr x22, =OG_FLAG
    ldrb w20, [x22]                     // flag before
    mov w8, #FT_CTRL
    cmp w21, w8
    b.ne 5f
    cmp w19, #6                         // the 3:2 row: N-RAW 3:2 with the chosen (N-RAW) tone
    ccmp w20, #1, #0, eq
    b.eq 4f                             // already N-RAW 3:2
    mov w8, #1
    strb w8, [x22]
    dsb ishst
    bl imenu_sync
    mov w0, #1
    mov w1, w20
    bl og_mode_switch_keep_tone         // E3: the chosen tone follows (stock write)
    cmp w19, #6
    b.eq 3f
    ldr x9, =GUARD                      // type change: flag and size first, then the type (as ft_ok_hook)
    ldr w20, [x9]
    mov w8, #1
    str w8, [x9]
    ldr w0, =ITEM_TYPE
    mov w1, #6
    bl original_403ec39c
    ldr x9, =GUARD
    str w20, [x9]
    bl imenu_sync                       // the type is 6 only now
    b 4f
3:  cbnz w0, 4f                         // the size/rate changed: notified
    bl ft_notify_same                   // only the flag changed
4:  mov w2, #0x30e5
    b 9f
5:  cmp w20, #1                         // a stock row leaves 3:2
    b.ne 6f
    strb wzr, [x22]
    dsb ishst
    bl imenu_sync
6:  mov w8, #0x30e5
    cmp w21, w8
    b.ne 8f
    mov w0, wzr
    mov w1, w20
    bl og_mode_switch_keep_tone         // E3: the chosen tone follows (stock write)
    cmp w19, #6
    b.ne 8f
    cbnz w0, 8f
    cmp w20, #1
    b.ne 8f
    bl ft_notify_same
8:  mov w2, w21
9:  ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #48
    ret
.ltorg

/* ---- frame-size list: star icons of the 3:2 rows ---------------------------------------------------------------- */
/* 4056C8E4 (b; replaces ldp x19, x30, [sp, #0x30]): epilogue of 4056C85C, x19 = page.  x20-x25 and x30 are reloaded
 * by the epilogue, so they are free here.  Rows 35C0+p use entry 2+p (stock rows 53..62, checked by e1.py). */
.balign 16
.global ft_star_hook
ft_star_hook:
    ldr w0, =ITEM_TYPE
    bl original_403ec398
    cmp w0, #6
    b.ne 9f
    ldr w0, =QUALITY_ITEM
    bl original_403ec398
    mov w20, w0
    mov w21, wzr
1:  mov x0, x19
    mov w1, #0x35c0
    add w1, w1, w21
    mov w2, #0x4ba7
    bl original_4050a6f0
    cbz x0, 3f
    ldr x8, =(STAR_TABLE + 2 * 12)
    mov w9, #12
    umaddl x8, w21, w9, x8
    cmp w20, #1
    b.ne 2f
    ldr w1, [x8, #4]
    bl original_403f645c
    b 3f
2:  ldr w1, [x8, #8]
    bl original_403f645c
3:  add w21, w21, #1
    cmp w21, #10
    b.lo 1b
9:  ldp x19, x30, [sp, #0x30]
    b original_4056c8e8
.ltorg

/* ---- 4.1K 3:2 at 30/25/24p: plan 13 takes its 50..120p variants ------------------------------------------------- */
/* Flags EQ when the plan descriptor x16 {plan, size, rate, type} is N-RAW 4.1K recording plan 13 at 30/25/24p under
 * 4.1K 3:2 (flag 1, stored type 6 and size 4, LV mode cache [4, rate, rate]); the type field is 6 or 0 (the
 * coordinate service passes 0), as h14_coordinates_hook.  Preserves every general register. */
.balign 16
og32_low_plan:
    stp x8, x9, [sp, #-32]!
    stp x10, x11, [sp, #16]
    ldr w8, [x16]
    cmp w8, #13
    b.ne 8f
    ldr w8, [x16, #4]
    cmp w8, #4
    b.ne 8f
    ldr w9, [x16, #8]
    sub w8, w9, #4
    cmp w8, #2
    b.hi 8f
    ldr w8, [x16, #12]
    cmp w8, #6
    b.eq 1f
    cbnz w8, 8f
1:  half_og 8f, x8, w8
    lv_cache_half w9, x10, w10, w11, 8f
    mov w8, #1
    b 9f
8:  mov w8, wzr
9:  cmp w8, #1
    ldp x10, x11, [sp, #16]
    ldp x8, x9, [sp], #32
    ret

.macro low_plan desc
    stp x16, x30, [sp, #-16]!
    mov x16, \desc
    bl og32_low_plan
    ldp x16, x30, [sp], #16
.endm

/* 41062148 (b; replaces b 410621E8): front input, plan 13 at 30/25/24p -> the half block path 4106206C, where
 * half_plan_e1_hook (41062070) gives 4140x2756 and block A02A974A0 as at 60p; else the secondary full block. */
.global og_front_low_hook
og_front_low_hook:
    low_plan x20
    b.eq 1f
    b original_410621e8
1:  b original_4106206c

/* 41062698 (b; replaces csel x8, x9, x8, lo): parameter template, x9 = A0297B640 (50..120p), x8 = A0297B7B8. */
.global og_param_low_hook
og_param_low_hook:
    b.lo 2f
    low_plan x0
    b.ne 1f
2:  mov x8, x9
1:  b original_4106269c

/* 41062BB8 (b; replaces csel x8, x9, x8, lo): plan table A02A95CE8, x9 = A0297D9BC (50..120p), x8 = A0297D9F4. */
.global og_table_ce8_low_hook
og_table_ce8_low_hook:
    b.lo 2f
    low_plan x0
    b.ne 1f
2:  mov x8, x9
1:  b original_41062bbc

/* Rate loads of the remaining plan-13 size-4 branches: report 60p (code 2) for 4.1K 3:2 at 30/25/24p.  The loaded
 * rate is only compared there.  \desc is the descriptor, \wr the destination of the replaced ldr \wr, [\desc, #8]. */
.macro low_rate name, desc, wr, back
.global \name
\name:
    low_plan \desc
    ldr \wr, [\desc, #8]
    b.ne 1f
    mov \wr, #2
1:  b \back
.endm
low_rate og_table_db0_low_hook, x8, w8, original_41062cdc      /* 41062CD8: A0297DEB6 (low) / A0297DEA8 */
low_rate og_table_ea8_low_hook, x8, w8, original_41062fd4      /* 41062FD0: A0297DFA0 (low, sets its byte) / DFB4 */
low_rate og_coord_low_hook, x0, w8, original_410658fc          /* 410658F8: front width 8280/4140, height 4688/2344 */
low_rate og_d980_low_hook, x2, w8, original_410b65a0           /* 410B659C: D980 layout 6000h/0 (low) or 1000h/39000h */
.ltorg

/* ---- playback ----------------------------------------------------------------------------------------------------- */
/* w8 = (width << 16) | height of a file record -> w8 = 1 for 8256x5504 or 4128x2752, else 0.  Leaf; clobbers w9. */
.balign 16
og32_dims:
    mov w9, #0x1580                     // 5504
    movk w9, #0x2040, lsl #16           // 8256
    cmp w8, w9
    b.eq 1f
    mov w9, #0x0ac0                     // 2752
    movk w9, #0x1020, lsl #16           // 4128
    cmp w8, w9
    b.eq 1f
    mov w8, wzr
    ret
1:  mov w8, #1
    ret

/* 40797088 (b; was film_icon_hook): x21 record object, w20 width, w19 height; the frame is set up, x0-x18 free. */
.global film_icon_e2_hook
film_icon_e2_hook:
    mov w8, #8256
    cmp w20, w8
    b.ne 1f
    mov w8, #5504
    cmp w19, w8
    b.ne 2f
    mov w8, #3                          // 8256x5504: as 8256x4644 (D-series)
    b 3f
1:  mov w8, #4128
    cmp w20, w8
    b.ne 2f
    mov w8, #2752
    cmp w19, w8
    b.ne 2f
    mov w8, #4                          // 4128x2752: as 4128x2322
3:  str w8, [sp, #-16]!
    mov x0, x21
    mov x1, xzr
    bl original_407b6958
    ldr w8, [sp], #16
    cmp w0, #6
    b.ne 2f
    mov w0, w8
    b original_40797110
2:  mov x0, x21
    b original_4079708c

/* 406C0280 (b; was fx_icon_hook): crop code 11 of a full-height 3:2 N-RAW clip (8256x5504 or 4128x2752) is FX. */
.global fx_icon_e2_hook
fx_icon_e2_hook:
    ldrh w8, [sp, #0x44]
    cmp w8, #11
    b.ne 1f
    ldrh w8, [sp, #0x16]
    ldrh w9, [sp, #0x18]
    orr w8, w9, w8, lsl #16
    mov w9, #0x1580
    movk w9, #0x2040, lsl #16
    cmp w8, w9
    b.eq 2f
    mov w9, #0x0ac0
    movk w9, #0x1020, lsl #16
    cmp w8, w9
    b.ne 1f
2:  ldr w9, [sp, #0x48]
    cmp w9, #0x31
    b.ne 1f
    mov x0, x19
    mov w1, #1
    b original_406c02ac
1:  ldrh w8, [sp, #0x44]                // the replaced instruction's result for the stock path
    b original_406c0284

/* 40711530 (b; was playback_capture_hook): as D4, plus the 4.1K 3:2 sizes (main 4128x2752 or coded 4140x2756; proxy
 * whose main record is 4128x2752). */
.balign 16
.global playback_capture_e2_hook
playback_capture_e2_hook:
    stp x8, x9, [sp, #-32]!
    stp x10, x11, [sp, #16]
    ldr x8, =0xA045F08F8
    cmp x19, x8
    b.ne 9f
    ldr x8, =OG_STATE
    str xzr, [x8, #8]
    ldr w9, [x23, #0x23c]
    cmp w9, #0x31
    b.ne 4f
    ldp w10, w11, [x23]
    orr w10, w11, w10, lsl #16
    mov w9, #0x1580                     // 8256x5504
    movk w9, #0x2040, lsl #16
    cmp w10, w9
    b.eq 7f
    mov w9, #0x1588                     // 8268x5512
    movk w9, #0x204c, lsl #16
    cmp w10, w9
    b.eq 7f
    mov w9, #0x0ac0                     // 4128x2752
    movk w9, #0x1020, lsl #16
    cmp w10, w9
    b.eq 7f
    mov w9, #0x0ac4                     // 4140x2756
    movk w9, #0x102c, lsl #16
    cmp w10, w9
    b.eq 7f
    b 9f
4:  cmp w9, #2
    b.ne 9f
    ldr w9, [x23]
    cmp w9, #1920
    b.ne 9f
    ldr w9, [x23, #4]
    cmp w9, #1080
    b.ne 9f
    ldr x10, =0xA0456A820
    ldrh w9, [x10, #0xa0]
    cmp w9, #2
    b.ne 9f
    ldrh w9, [x10, #0xa4]
    cmp w9, #1920
    b.ne 9f
    ldrh w9, [x10, #0xa6]
    cmp w9, #1080
    b.ne 9f
    ldrh w9, [x10, #0xfa]
    cmp w9, #1
    b.ne 9f
    ldrh w9, [x10, #0xfc]
    cmp w9, #0x31
    b.ne 9f
    ldrh w9, [x10, #0x102]
    ldrh w11, [x10, #0x104]
    orr w11, w11, w9, lsl #16
    mov w9, #0x1580
    movk w9, #0x2040, lsl #16
    cmp w11, w9
    b.eq 7f
    mov w9, #0x0ac0
    movk w9, #0x1020, lsl #16
    cmp w11, w9
    b.ne 9f
7:  ldr w9, [sp, #32]                   // media ID in the original native request
    cbz w9, 9f
    orr x9, x9, #0x100000000
    str x9, [x8, #8]
    dmb ishst
9:  ldp x10, x11, [sp, #16]
    ldp x8, x9, [sp], #32
    ldr w8, [x23, #0x240]
    b original_40711534
.ltorg

/* ---- D4 bank setter: a cleared bank flag also clears that bank's size memory ------------------------------------- */
/* 41015F80 (bl; was setting_bank_normal_hook): D4's rule unchanged (guard-0 write of 125A/125B in bank w19 clears its
 * flag), plus OG_MEM of that bank (same 2D0h stride); with the bank's flag 0 the E1/E2 setter rule for a stored 3:2
 * spec (OG_MEM holds a 16:9 spec) applies too. */
.balign 16
.global setting_bank_normal_e2_hook
setting_bank_normal_e2_hook:
    stp x19, x20, [sp, #-48]!
    stp x21, x22, [sp, #16]
    stp x23, x30, [sp, #32]
    mov w19, w0
    mov w20, w1
    mov x21, x3
    bl setting_bank_normal_body
    tbz w0, #0, 2f
    and w9, w20, #0xffff
    mov w10, #0x125a
    sub w9, w9, w10
    cmp w9, #1
    b.hi 2f
    cmp w19, #4
    b.hi 2f
    ldr x9, =OG_STATE
    ldr w9, [x9, #0x14]
    cmp w9, #2
    b.eq 3f
    cbnz w9, 2f
    ldr x9, =OG_FLAG
    mov w10, #0x2d0
    umaddl x9, w19, w10, x9
    ldrb w10, [x9]
    cbz w10, 4f
    strb wzr, [x9]
    sturh wzr, [x9, #(OG_MEM - OG_FLAG)]
3:  mov w10, #1
    strb w10, [x21]
2:  ldp x23, x30, [sp, #32]
    ldp x21, x22, [sp, #16]
    ldp x19, x20, [sp], #48
    ret
4:  ldrb w10, [x9, #(OG_MEM - OG_FLAG)]
    tst w10, #0x7f
    b.eq 2b
    tbnz w10, #7, 2b
    sturh wzr, [x9, #(OG_MEM - OG_FLAG)]
    b 2b
.ltorg

/* ---- i menu: top-right file-type mark ----------------------------------------------------------------------------- */
/* 404CA1D0 (bl; replaces bl 403F645C): i-menu file-type mark widget (objects 24E3/24E4, 86x36 slot), w1 = icon from
 * list A028885E8 (0x15BC = N-RAW solid 82x32, only at the type-6 index).  N-RAW 3:2 shows E1's 3:2 solid icon. */
.balign 16
.global im_ft_icon_hook
im_ft_icon_hook:
    mov w16, #0x15bc
    cmp w1, w16
    b.ne 1f
    ldr x16, =OG_FLAG
    ldrb w16, [x16]
    cmp w16, #1
    b.ne 1f
    ldr x16, =FILE_TYPE_RAM
    ldr w16, [x16]
    cmp w16, #6
    b.ne 1f
    mov w1, #OG_LV_SOLID
1:  b original_403f645c
.ltorg

/* ---- i menu: unused cells of the 3:2 list ------------------------------------------------------------------------- */
/* 403A036C entry (b; replaces stp x25, x24, [sp, #-0x40]!): availability of condition w0 (1 = not available; stock
 * ids above 1E8h are always available).  The 3:2 list lays out only 10 cells (imenu_sync sets the layout count);
 * choices 10..18 carry OG_NEVER as well, so a path that still walks 19 choices (the dial's next/prev helpers
 * 404E3518/404E349C skip unavailable entries) cannot land on them. */
#define OG_NEVER 0x0E2E3A32
.balign 16
.global cond_never_hook
cond_never_hook:
    mov w16, #(OG_NEVER & 0xffff)
    movk w16, #(OG_NEVER >> 16), lsl #16
    cmp w0, w16
    b.ne 1f
    mov w0, #1
    ret
1:  stp x25, x24, [sp, #-0x40]!
    b original_403a0370
