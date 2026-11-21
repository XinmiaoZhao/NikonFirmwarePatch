/* E1 = D10 + "N-RAW 3:2" as a menu-layer video file type (open-gate line, 2026-11-11).
 *
 * Model.  The stored file type stays 6 (N-RAW); "3:2" is the open-gate flag OG_FLAG (byte +3 of DS item 120B, banked
 * and reset since D4).  Only the "Video file type" page changes the flag: its new row "N-RAW 3:2" sets it, every other
 * row clears it.  Invariant kept by the page and by setting_normal_e1_hook: flag 1 => (size, rate) is one of the ten
 * 3:2 choices (8256x5504 30/25/24p, 4128x2752 120/100/60/50/30/25/24p).  The frame-size list and the N-RAW i-menu
 * item then show either the 3:2 choices or the 19 stock N-RAW choices, never both, so the flag never changes inside an
 * i-menu session and the D7/D8 cancel machinery is not installed any more (its code stays in place, unreferenced, so
 * that every D4..D10 address and the anamorphic refinements into this cave are unchanged).
 *
 * New code only follows D10.  Hooks (sites are installed by patcher.py):
 *   list_hide_hook        4056C688  frame-size list: a type-6 row is also hidden when its flag column differs
 *   ft_cursor_hook        4056C9DC  file-type page entry: cursor on the 3:2 row when type 6 and flag 1
 *   ft_refresh_hook       (state callback, replaces 4056CD84) stock refresh, then the 3:2 row shows N-RAW's tone text
 *   ft_ok_hook            4056D2B0  file-type OK: type, flag, fitted size; flag-only change notifies like D4 dev-8
 *   setting_normal_e1_hook 41015D6C D4 forced change (guard 2) kept; a guard-0 write of 125A/125C that leaves the 3:2
 *                         set clears the flag (D4 cleared on every guard-0 125A/125B write)
 *   i_apply_q3_*_hook     404E4AB0 / 404D9B98  only the Q3 rule of D4's i_apply_transaction: N-RAW size/rate batches
 *                         do not write the GUI-projected quality back; no flag write
 *   im_*_hook             N-RAW i-menu item AB: descriptor callbacks sync the active tables first; dial counts
 *   menu_icon_hook        40572FA0  video menu "Video file type" row icon
 *   lv_icon_hook          4041E1F0  shooting-screen file-type icon pair (element 49h)
 *   lv_diff_hook          404F8C48  element 49h is also dirty when the drawn 3:2 state differs from the wanted one
 *   og_icon_idx_hook / og_icon_val_hook  4032DC7C / 4032DD5C  out-of-table icons 7100h+ (after video-quality's own
 *                         entry hooks at 4032DC64 / 4032DD34, which pass these numbers on unchanged)
 *   boot_reset_e1_hook    41184DE8  marks the active i-menu tables and the drawn icon state unsynced, then D7's hook
 */

#define FT_CTRL        0x35CA
#define ITEM_TYPE      0x06001206
#define ITEM_SIZE      0x0500125A
#define ITEM_RATE      0x0500125C
#define FILE_TYPE_RAM  0xA03D5C014          /* DS records 4400A5C0: 1206 -> A03D5C014, 125A -> A03D5C274, */
#define SIZE_RAM       0xA03D5C274          /* 125C -> A03D5C27C, all u32; 120B (flag at +3) -> A03D5C028   */
#define RATE_RAM       0xA03D5C27C
#define GUARD          (OG_STATE + 0x14)
#define IM_MODE        (OG_STATE + 0x1F8)   /* 0 unsynced, 1 = stock 19 choices, 2 = 3:2 choices */
#define ICON_DRAWN     (OG_STATE + 0x1F9)   /* 1 when element 49h was last drawn with the 3:2 pair */
#define IM_ACTIVE      (OG_STATE + 0x200)   /* active N-RAW i-menu tables, IM_BYTES */
#define IM_BYTES       0xB18
#define IM_SRC_STOCK   0x408C4000           /* ROM source blocks with the active layout, written by imenu.py */
#define IM_SRC_32      0x408C5000
#define IM_DIAL_COUNT  0xA8
#define IM_LAYOUT_N    0xA028B07C0          /* u16 cell count of the N-RAW i-menu list layout A028B07A0 (19 stock) */
#define OG_MEM         0xA03D5C0AE          /* DS 122C record +2/+3 (unused by stock): the other N-RAW mode's  */
                                            /* size + 1 | mode << 7 (0 = none), then its rate                   */
#define OG_ICON_BASE   0x7100
#define OG_ICON_COUNT  4                    /* E2: 7103 = blank i-menu cell */
#define OG_MENU_ICON   0x7100
#define OG_LV_SOLID    0x7101
#define OG_LV_OUTLINE  0x7102

.text
.ltorg
.balign 16

/* ---- frame-size list ------------------------------------------------------------------------------------------ */
/* replaces cset w29, ne after cmp w21 (row type), w20 (current type); x25 = row + 0x10 (flag column).  x0/x1 are
 * the arguments of the following call and stay untouched. */
.global list_hide_hook
list_hide_hook:
    cset w29, ne
    cbnz w29, 1f
    cmp w20, #6
    b.ne 1f
    ldr x16, =OG_FLAG
    ldrb w16, [x16]
    cmp w16, #1
    cset w16, eq
    ldr w17, [x25]
    cmp w16, w17
    cset w29, ne
1:  ret

/* ---- file-type page --------------------------------------------------------------------------------------------- */
/* replaces ldr w20, [x9, w8, sxtw #2] (w8 = type - 1 on this path). */
.global ft_cursor_hook
ft_cursor_hook:
    ldr w20, [x9, w8, sxtw #2]
    cmp w8, #5
    b.ne 1f
    ldr x16, =OG_FLAG
    ldrb w16, [x16]
    cmp w16, #1
    b.ne 1f
    mov w20, #FT_CTRL
1:  b original_4056c9e0

.global ft_refresh_hook
ft_refresh_hook:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    mov x19, x0
    bl original_4056cd84
    mov w20, w0
    mov x0, x19
    mov w1, #FT_CTRL
    mov w2, #0x4ba7
    bl original_4050a6f0
    cbz x0, 1f
    mov x19, x0
    bl original_403f62d8
    mov x0, x19
    bl original_403f1a44
    mov x0, x19
    mov w1, #3
    mov w2, wzr                         // text entry 0 of slot 46h = the N-RAW row's tone text
    bl original_403f61ec
1:  mov w0, w20
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #32
    ret

/* w0 = 1 when (w0 size, w1 rate) is a 3:2 choice.  Leaf. */
og32_member:
    cmp w0, #4
    b.eq 1f
    cmp w0, #6
    b.ne 2f
    sub w1, w1, #4
    cmp w1, #2
    b.hi 2f
1:  mov w0, #1
    ret
2:  mov w0, wzr
    ret

/* Native batch [125A, 125C] = [w0, w1] with guard w2; returns the native result. */
ft_write_size:
    stp x29, x30, [sp, #-48]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    stp w0, w1, [sp, #40]
    ldr w8, =ITEM_SIZE
    ldr w9, =ITEM_RATE
    stp w8, w9, [sp, #32]
    ldr x9, =GUARD
    ldr w19, [x9]
    str w2, [x9]
    add x0, sp, #32
    add x1, sp, #40
    mov w2, #2
    bl original_403ec3c8
    ldr x9, =GUARD
    str w19, [x9]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #48
    ret

/* Flag-only change: rewrite the current size/rate with guard 2, so setting_normal_e1_hook marks the native value
 * changed and the native batch emits its one setting notification (D4 dev-8). */
ft_notify_same:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    str x19, [sp, #16]
    ldr w0, =ITEM_SIZE
    bl original_403ec398
    mov w19, w0
    ldr w0, =ITEM_RATE
    bl original_403ec398
    mov w1, w0
    mov w0, w19
    mov w2, #2
    bl ft_write_size
    ldr x19, [sp, #16]
    ldp x29, x30, [sp], #32
    ret

/* w0 = 1 when (w0 size, w1 rate) is valid for mode w2: 3:2 = the ten 3:2 choices, 16:9 = one of the 19 stock N-RAW
 * choices (rows of the stock High i-menu table, +0 size, +4 rate).  Leaf; clobbers x8-x11. */
og_valid:
    cbz w2, 2f
    cmp w1, #6
    b.hi 8f
    cmp w0, #4
    b.eq 9f
    cmp w0, #6
    b.ne 8f
    cmp w1, #4
    b.hs 9f
    b 8f
2:  ldr x8, =0x42B0662C
    mov w9, #19
3:  ldp w10, w11, [x8]
    add x8, x8, #24
    cmp w10, w0
    ccmp w11, w1, #0, eq
    b.eq 9f
    subs w9, w9, #1
    b.ne 3b
8:  mov w0, wzr
    ret
9:  mov w0, #1
    ret

/* E2 (board card open-gate-20261112-nraw32-shared-size-memory): N-RAW and N-RAW 3:2 each keep their own size/rate.
 * The stored 125A/125C belong to one mode; OG_MEM keeps the other mode's (size + 1 | mode << 7, rate).  The stored
 * spec's mode is the opposite of OG_MEM's, or the flag before the change when OG_MEM is empty.
 * og_mode_switch(w0 = target mode, w1 = flag before): when the stored spec belongs to the other mode, it goes to
 * OG_MEM and a valid memory of the target mode comes back; entering 3:2 with a spec outside the 3:2 set fits it to
 * 4128x2752 at the same rate (as E1).  Leaving 3:2 for another file type does not call this (the spec stays with
 * its mode until N-RAW or N-RAW 3:2 is chosen again).  w0 = 1 when the stored size/rate changed (guard 1 write,
 * the native batch has notified). */
og_mode_switch:
    mov w2, #1                          // E3: og_mode_switch3 restores the tone too (e3_hooks.S); the E2 body
    b og_mode_switch3                   // below is kept in place, unreached, so later addresses do not move
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    stp x25, x26, [sp, #64]
    str x27, [sp, #80]
    mov w19, w0
    mov w20, w1
    ldr x21, =OG_MEM
    ldrb w22, [x21]
    ldrb w23, [x21, #1]
    tst w22, #0x7f
    b.eq 1f
    ubfx w20, w22, #7, #1
    eor w20, w20, #1                    // stored spec's mode
1:  ldr w0, =ITEM_SIZE
    bl original_403ec398
    mov w24, w0
    ldr w0, =ITEM_RATE
    bl original_403ec398
    mov w25, w0
    mov w26, w24                        // target spec
    mov w27, w25
    cmp w20, w19
    b.eq 6f
    add w8, w24, #1                     // swap: the stored spec is remembered for its mode
    orr w8, w8, w20, lsl #7
    strb w8, [x21]
    strb w25, [x21, #1]
    dsb ishst
    and w8, w22, #0x7f
    cbz w8, 6f
    ubfx w9, w22, #7, #1
    cmp w9, w19
    b.ne 6f
    sub w0, w8, #1
    mov w1, w23
    mov w2, w19
    bl og_valid
    cbz w0, 6f
    and w26, w22, #0x7f
    sub w26, w26, #1
    mov w27, w23
6:  cbz w19, 7f                         // 16:9 takes every stored N-RAW spec (3:2 sizes are 16:9 sizes)
    mov w0, w26
    mov w1, w27
    mov w2, #1
    bl og_valid
    cbnz w0, 7f
    mov w26, #4
7:  mov w0, wzr
    cmp w26, w24
    ccmp w27, w25, #0, eq
    b.eq 9f
    mov w0, w26
    mov w1, w27
    mov w2, #1
    bl ft_write_size
    mov w0, #1
9:  ldr x27, [sp, #80]
    ldp x25, x26, [sp, #64]
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #96
    ret

/* replaces the first instruction of 4056D2B0 (stp x21, x20, [sp, #-0x20]!); x0 = page context. */
.global ft_ok_hook
ft_ok_hook:
    stp x29, x30, [sp, #-64]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    mov x19, x0
    ldr x8, [x0]                        // selected row's control, as 4056D2CC..4056D30C
    ldr x9, [x8, #0x50]
    ldrh w10, [x8, #0x58]
    ldrh w8, [x8, #0x32]
    ldr x9, [x9, #0x10]
    add x8, x8, x10
    mov w10, #0x2c
    madd x8, x8, x10, x9
    ldr w20, [x8, #0x18]
    ldr w0, =ITEM_TYPE
    bl original_403ec398
    mov w21, w0                         // type before
    ldr x22, =OG_FLAG
    ldrb w23, [x22]                     // flag before
    mov w8, #FT_CTRL
    cmp w20, w8
    b.eq ft_ok_new
    cmp w23, #1
    b.ne 1f
    strb wzr, [x22]                     // any other row leaves 3:2
    dsb ishst
    bl imenu_sync
1:  mov w8, #0x30e5
    cmp w20, w8
    b.ne ft_ok_stock                    // other file types: the N-RAW spec stays with its mode
    mov w0, wzr                         // N-RAW row: the 16:9 spec comes back (E2)
    mov w1, w23
    bl og_mode_switch
    cmp w21, #6
    b.ne ft_ok_stock                    // type change: the stock path writes the type and notifies
    cbnz w0, ft_ok_changed              // the size/rate changed: the native batch has notified
    cmp w23, #1
    b.ne ft_ok_stock                    // nothing changed: the stock path
    bl ft_notify_same                   // only the flag changed
    b ft_ok_changed
ft_ok_stock:
    mov x0, x19
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #64
    stp x21, x20, [sp, #-0x20]!         // replaced instruction
    b original_4056d2b4
ft_ok_new:
    cmp w21, #6
    b.ne 1f
    cmp w23, #1
    b.eq ft_ok_same                     // already N-RAW 3:2: the stock "unchanged" path
1:  mov w8, #1
    strb w8, [x22]
    dsb ishst
    bl imenu_sync
    mov w0, #1                          // the 3:2 spec comes back, or the stored spec is fitted (E2)
    mov w1, w23
    bl og_mode_switch
    mov w24, w0
    cmp w21, #6
    b.eq 2f
    ldr x9, =GUARD                      // type change: flag and size first, then the type
    ldr w24, [x9]
    mov w8, #1
    str w8, [x9]
    ldr w0, =ITEM_TYPE
    mov w1, #6
    bl original_403ec39c
    ldr x9, =GUARD
    str w24, [x9]
    bl imenu_sync                       // E2: the type is 6 only now (the sync above saw the old type)
    b ft_ok_changed
2:  cbnz w24, ft_ok_changed             // size rewritten: the native batch has notified
    bl ft_notify_same
ft_ok_changed:                          // the stock tail after a changed type (4056D34C..4056D380)
    mov w0, #0x16c
    bl original_403d3938
    ldr x0, =0x403efe74
    mov w1, #3
    mov w2, #7
    bl original_403efed8
    mov w0, #0x1388
    bl original_403e82bc
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #64
    b original_403d4ad4
ft_ok_same:
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #64
    ret
.ltorg

/* ---- size/rate setter ------------------------------------------------------------------------------------------- */
.balign 16
.global setting_normal_e1_hook
setting_normal_e1_hook:
    stp x19, x20, [sp, #-32]!
    stp x21, x30, [sp, #16]
    mov w19, w0
    mov x20, x2
    bl setting_normal_e1_body
    tbz w0, #0, 9f
    mov w21, w0
    and w9, w19, #0xffff
    ldr x10, =GUARD
    ldr w10, [x10]
    mov w11, #0x125a
    sub w11, w9, w11
    cmp w11, #1
    b.hi 2f
    cmp w10, #2                         // file-type page, flag-only change: report the native value changed
    b.ne 2f
    mov w11, #1
    strb w11, [x20]
2:  cbnz w10, 8f                        // own transactions never clear
    ldr x11, =OG_FLAG
    ldrb w11, [x11]
    cmp w11, #1
    b.eq 5f
    /* E2, flag 0: a native write while the stored spec still belongs to 3:2 (3:2 was left for another file type
     * and OG_MEM holds the 16:9 spec) makes the stored spec a 16:9 one; the old 16:9 memory is dropped. */
    ldr w14, =ITEM_SIZE
    cmp w19, w14
    ldr w14, =ITEM_RATE
    ccmp w19, w14, #4, ne
    b.ne 8f
    ldr x11, =OG_MEM
    ldrb w12, [x11]
    tst w12, #0x7f
    b.eq 8f
    tbnz w12, #7, 8f
    strh wzr, [x11]
    b 8f
5:
    /* Native batches write 125A (size) before 125C (rate), so each write is judged by its own item only: a size
     * write leaves the set only with a size other than 4 or 6; a rate write only when the size is 6 and the rate is
     * not 30/25/24p.  (QEMU e1-s6r4-2: judging the pair after the size write saw (6, 60p) on the way from 4.1K 60p
     * to 8.3K 30p and cleared the flag.) */
    ldr x11, =SIZE_RAM                  // DS RAM words; no getter inside the setter path
    ldr w12, [x11]
    ldr w13, [x11, #(RATE_RAM - SIZE_RAM)]
    ldr w14, =ITEM_SIZE
    cmp w19, w14
    b.ne 3f
    cmp w12, #4
    b.eq 8f
    cmp w12, #6
    b.eq 8f
    b 4f
3:  ldr w14, =ITEM_RATE
    cmp w19, w14
    b.ne 8f
    cmp w12, #6
    b.ne 8f
    sub w13, w13, #4
    cmp w13, #2
    b.ls 8f
4:
    ldr x11, =OG_FLAG                   // left the 3:2 set (reset, shortcut, import): plain N-RAW
    strb wzr, [x11]
    ldr x11, =OG_MEM                    // E2: the stored spec is now a 16:9 one, no memory is trusted
    strh wzr, [x11]
    dsb ishst
    bl imenu_sync
8:  mov w0, w21
9:  ldp x21, x30, [sp, #16]
    ldp x19, x20, [sp], #32
    ret
setting_normal_e1_body:
    mov w8, w0
    b original_41015d70
.ltorg

/* ---- i menu ----------------------------------------------------------------------------------------------------- */
/* Keep only the Q3 rule of D4's i_apply_transaction (x0 keys, x1 values, w2 count). */
.balign 16
.global i_apply_q3_dial_hook
i_apply_q3_dial_hook:
    ldr x16, =0x403ec3c8
    b i_apply_q3
.global i_apply_q3_list_hook
i_apply_q3_list_hook:
    ldr x16, =0x403ec508
i_apply_q3:
    cmp w2, #3
    b.ne 1f
    ldr w8, [x0]
    ldr w9, =ITEM_SIZE
    cmp w8, w9
    b.ne 1f
    ldr w8, [x0, #4]
    add w9, w9, #2
    cmp w8, w9
    b.ne 1f
    ldr w8, [x0, #8]
    add w9, w9, #5
    cmp w8, w9
    b.ne 1f
    mov w2, #2
1:  br x16

/* Make the active N-RAW i-menu tables (IM_ACTIVE, RAM) match the current mode.  Leaf; clobbers x8-x13. */
.balign 16
imenu_sync:
    ldr x8, =FILE_TYPE_RAM
    ldr w8, [x8]
    cmp w8, #6
    cset w9, eq
    ldr x8, =OG_FLAG
    ldrb w8, [x8]
    cmp w8, #1
    cset w8, eq
    and w9, w9, w8
    add w9, w9, #1                      // 1 stock, 2 = 3:2
    /* E2: the list lays out the first n cells of its layout (A028B07A0: 19 cell elements, count at +20h, read
     * live; QEMU e2v3-scene-1).  Written on every call: init data is recopied on a loader-copy boot. */
    cmp w9, #2
    mov w11, #19
    mov w12, #10
    csel w11, w12, w11, eq
    ldr x12, =IM_LAYOUT_N
    strh w11, [x12]
    ldr x10, =IM_MODE
    ldrb w11, [x10]
    cmp w11, w9
    b.eq 3f
    ldr x12, =IM_SRC_STOCK
    ldr x13, =IM_SRC_32
    cmp w9, #2
    csel x12, x13, x12, eq
    ldr x13, =IM_ACTIVE
    mov x11, #IM_BYTES
1:  ldr x8, [x12], #8
    str x8, [x13], #8
    subs x11, x11, #8
    b.ne 1b
    dsb ish
    strb w9, [x10]
    dsb ish
3:  ret

.macro im_wrap name, target
.balign 16
.global \name
\name:
    stp x29, x30, [sp, #-80]!
    mov x29, sp
    stp x0, x1, [sp, #16]
    stp x2, x3, [sp, #32]
    stp x4, x5, [sp, #48]
    stp x6, x7, [sp, #64]
    bl imenu_sync
    ldp x0, x1, [sp, #16]
    ldp x2, x3, [sp, #32]
    ldp x4, x5, [sp, #48]
    ldp x6, x7, [sp, #64]
    ldp x29, x30, [sp], #80
    b \target
.endm
im_wrap im_dial_hook, original_404e4848
im_wrap im_grid_hook, original_404dc124
im_wrap im_selected_hook, original_404dde74
im_wrap im_cancel_hook, original_404db3bc

/* 404E49F0 (N-RAW branch only): mov w1, #19 -> the active count. */
.balign 16
.global im_dial_count_hook
im_dial_count_hook:
    ldr x16, =IM_ACTIVE
    ldr w1, [x16, #IM_DIAL_COUNT]
    ret
/* 404E4AE8: ldr w8, [x8, w25, sxtw #2] (per-type count, w25 = type - 1). */
.global im_wrap_count_hook
im_wrap_count_hook:
    ldr w8, [x8, w25, sxtw #2]
    cmp w25, #5
    b.ne 1f
    ldr x16, =IM_ACTIVE
    ldr w8, [x16, #IM_DIAL_COUNT]
1:  ret
.ltorg

/* ---- icons ------------------------------------------------------------------------------------------------------ */
/* 40572FA0: mov x0, x22 before bl 403F645C; w1 = stock icon, w8 = type - 1 on the table path. */
.balign 16
.global menu_icon_hook
menu_icon_hook:
    mov x0, x22
    cmp w8, #5
    b.ne 1f
    ldr x16, =OG_FLAG
    ldrb w16, [x16]
    cmp w16, #1
    b.ne 1f
    mov w1, #OG_MENU_ICON
1:  ret

/* 4041E1F0: mov w0, #0x49 before the tail call 4041ECB4(49h, 1, 0, solid w3, outline w4); w8 = type - 1. */
.global lv_icon_hook
lv_icon_hook:
    mov w16, wzr
    cmp w8, #5
    b.ne 1f
    ldr x17, =OG_FLAG
    ldrb w17, [x17]
    cmp w17, #1
    b.ne 1f
    mov w3, #OG_LV_SOLID
    mov w4, #OG_LV_OUTLINE
    mov w16, #1
1:  ldr x17, =ICON_DRAWN
    strb w16, [x17]
    str x30, [sp, #-16]!                // E2: keep the i-menu tables (and list layout) in step with the file type
    bl imenu_sync                       // before any i-menu scene is built (cold boot, type changes); x8-x13 only
    ldr x30, [sp], #16
    mov w0, #0x49
    b original_4041e1f4

/* 404F8C48: cmp w9 (new type), w10 (old type); x8 = element record; leaf, returns to its caller. */
.global lv_diff_hook
lv_diff_hook:
    cmp w9, w10
    b.ne 2f
    mov w11, wzr
    cmp w9, #6
    b.ne 1f
    ldr x12, =OG_FLAG
    ldrb w12, [x12]
    cmp w12, #1
    cset w11, eq
1:  ldr x12, =ICON_DRAWN
    ldrb w12, [x12]
    cmp w11, w12
    b.eq 3f
2:  mov w9, #0x101
    strh w9, [x8, #0x54]
3:  ret

/* 4032DC7C: cmp w8 (number), w9 (stock count); x1 = output record. */
.global og_icon_idx_hook
og_icon_idx_hook:
    sub w12, w8, #(OG_ICON_BASE >> 12), lsl #12
    sub w12, w12, #(OG_ICON_BASE & 0xfff)
    cmp w12, #OG_ICON_COUNT
    b.hs 1f
    adr x13, og_icon_records
    add x13, x13, w12, uxtw #4
    ldrh w12, [x13]
    strh w12, [x1]
    ldr w12, [x13, #4]
    str w12, [x1, #4]
    ldr x12, [x13, #8]
    str x12, [x1, #0x10]
    ret
1:  cmp w8, w9
    b original_4032dc80

/* 4032DD5C: cmp w8 (stock count), w0 (number); w10 = 18h is live; outputs [x1] bytes, [x2] pointer. */
.global og_icon_val_hook
og_icon_val_hook:
    sub w12, w0, #(OG_ICON_BASE >> 12), lsl #12
    sub w12, w12, #(OG_ICON_BASE & 0xfff)
    cmp w12, #OG_ICON_COUNT
    b.hs 1f
    adr x13, og_icon_records
    add x13, x13, w12, uxtw #4
    ldr w12, [x13, #4]
    str w12, [x1]
    ldr x12, [x13, #8]
    str x12, [x2]
    ret
1:  cmp w8, w0
    b original_4032dd60

/* ---- boot ------------------------------------------------------------------------------------------------------- */
.balign 16
.global boot_reset_e1_hook
boot_reset_e1_hook:
    cmp w19, #1
    b.ne 1f
    stp x8, x9, [sp, #-16]!
    ldr x8, =IM_MODE
    strh wzr, [x8]                      // IM_MODE and ICON_DRAWN
    dsb ishst
    ldp x8, x9, [sp], #16
1:  b boot_reset_hook
.ltorg

/* ---- 4.1K 3:2: the H14 driver-14 route (../half_raw_geometry_20261031), under the flag, all seven rates ---------- */
/* flag 1, stored type 6, stored N-RAW size 4 (DS RAM); clobbers \xr. */
.macro half_og fail, xr, wr
    ldr \xr, =OG_FLAG
    ldrb \wr, [\xr]
    cmp \wr, #1
    b.ne \fail
    ldr \xr, =FILE_TYPE_RAM
    ldr \wr, [\xr]
    cmp \wr, #6
    b.ne \fail
    ldr \xr, =SIZE_RAM
    ldr \wr, [\xr]
    cmp \wr, #4
    b.ne \fail
.endm
/* LV mode cache A03BB71D8 = [4, rate, rate] with w\rate = header/plan rate; clobbers x\xa, x\xb. */
.macro lv_cache_half rate, xa, wa, wb, fail
    mov \xa, #0x71d8
    movk \xa, #0x3bb, lsl #16
    movk \xa, #0xa, lsl #32
    ldr \wb, [\xa]
    cmp \wb, #4
    b.ne \fail
    ldr \wb, [\xa, #4]
    cmp \wb, \rate
    b.ne \fail
    ldr \wb, [\xa, #8]
    cmp \wb, \rate
    b.ne \fail
.endm
.macro image_half ptr, fail
    ldr w8, [\ptr]
    cmp w8, #1
    b.ne \fail
    ldr w8, [\ptr, #0x388]
    cmp w8, #4
    b.ne \fail
    ldr w8, [\ptr, #0x38c]
    cmp w8, #4
    b.ne \fail
    ldr w8, [\ptr, #0x390]
    cmp w8, #6
    b.hi \fail
    ldr w8, [\ptr, #0x39c]
    cmp w8, #6
    b.ne \fail
    ldr w8, [\ptr, #0x3a0]
    cmp w8, #4
    b.ne \fail
    half_og \fail, x8, w8
.endm
.macro raw_half fail
    ldrb w8, [x0]
    cbnz w8, \fail
    ldr w8, [x0, #4]
    cmp w8, #7
    b.ne \fail
    ldr w8, [x0, #0x14]
    cmp w8, #1
    b.ne \fail
    ldr w8, [x0, #0x20]
    cmp w8, #4
    b.ne \fail
    ldr w8, [x0, #0x24]
    cmp w8, #4
    b.ne \fail
    half_og \fail, x8, w8
.endm
.macro save_args
    stp x19, x20, [sp, #-32]!
    stp x21, x30, [sp, #16]
    mov x19, x0
    mov x20, x1
.endm
.macro restore_return
    mov x0, x21
    ldp x21, x30, [sp, #16]
    ldp x19, x20, [sp], #32
    ret
.endm

/* 40F7938C (replaces mov w20, w0): a valid FX N-RAW 4.1K video snapshot with the flag sets the open-gate request
 * and the half-height standby tables, and leaves every readout-4 table at its stock value (the 8.3K path and every
 * other snapshot go to the D-series configuration_hook unchanged). */
.balign 16
.global configuration_e1_hook
configuration_e1_hook:
    tbz w0, #0, 9f
    stp x8, x9, [sp, #-16]!
    ldr w8, [x19]
    cmp w8, #1
    b.ne 8f
    ldr w8, [x19, #0x388]
    cmp w8, #4
    b.ne 8f
    ldr w8, [x19, #0x38c]
    cmp w8, #4
    b.ne 8f
    ldr w8, [x19, #0x390]
    cmp w8, #6
    b.hi 8f
    ldr w8, [x19, #0x3a0]
    cmp w8, #4
    b.ne 8f
    half_og 8f, x9, w9
    ldp x8, x9, [sp], #16
    mov w20, w0
    stp x8, x9, [sp, #-32]!
    stp x10, x11, [sp, #16]
    mov w11, #4688
    ldr x9, =0xA02A979EE
    strh w11, [x9]
    ldr x9, =0xA02A97CDA
    strh w11, [x9]
    strh w11, [x9, #4]
    ldr x9, =0xA02A979C2
    strh w11, [x9]
#if FULL_OUTPUT
    mov w10, #4644
    ldr x9, =0xA02A97A1A
    strh w10, [x9]
#endif
    ldr x9, =OG_STATE
    mov w10, #1
    str w10, [x9]
    ldr w8, [x9, #4]
    cbz w8, 1f
    str w8, [x9, #0x10]
1:  str wzr, [x9, #4]
#if VIEW_IDLE
    mov w8, #2756
    ldr x9, =0xA02A979D2
    strh w8, [x9]
    ldr x9, =0xA02A979FE
    strh w8, [x9]
    ldr x9, =0xA02A97D12
    strh w8, [x9]
    strh w8, [x9, #4]
    mov w8, #2752
    ldr x9, =0xA02A97A2A
    strh w8, [x9]
#endif
    dsb ishst
    ldp x10, x11, [sp, #16]
    ldp x8, x9, [sp], #32
    b original_40f79390
8:  ldp x8, x9, [sp], #16
9:  b configuration_hook

/* 40F7A08C (replaces str w0, [x19, #8]): readout 7 in a valid snapshot with the 4.1K request is the recording view
 * (kind 2), like readout 4 for 8.3K; everything else goes to the D-series view_commit_hook. */
.global view_commit_e1_hook
view_commit_e1_hook:
    cmp w0, #7
    b.ne 9f
    tbz w20, #0, 9f
    stp x8, x9, [sp, #-16]!
    ldr x8, =OG_STATE
    ldr w8, [x8]
    cbz w8, 1f
    half_og 1f, x9, w9
    ldp x8, x9, [sp], #16
    str w0, [x19, #8]
    stp x0, x30, [sp, #-32]!
    stp x8, x9, [sp, #16]
    ldr x9, =OG_STATE
    mov w8, #2
    b view_commit_store
1:  ldp x8, x9, [sp], #16
9:  b view_commit_hook
.ltorg

/* 410666F8 entry: N-RAW FX 4.1K video recording -> readout 7 (class 2 maps it to driver 14 natively). */
.balign 16
.global h14_readout_hook
h14_readout_hook:
    ldrb w8, [x0]
    cbnz w8, 1f
    ldr w8, [x0, #0x10]
    cbnz w8, 1f
    ldr w8, [x0, #0xc]
    cmp w8, #1
    b.ne 1f
    ldr w8, [x0, #0x14]
    cmp w8, #4
    b.ne 1f
    ldr w8, [x0, #0x18]
    cmp w8, #6
    b.hi 1f
    ldr w8, [x0, #0x1c]
    cmp w8, #4
    b.ne 1f
    ldr w8, [x0, #0x20]
    cmp w8, #4
    b.ne 1f
    half_og 1f, x8, w8
    mov w0, #7
    ret
1:  stp x19, x30, [sp, #-0x10]!
    b original_410666fc

.global h14_inner_hook
h14_inner_hook:
    raw_half 1f
    mov w8, #4140
    strh w8, [x1]
    mov w8, #2756
    strh w8, [x1, #2]
    ret
1:  ldrb w8, [x0]
    b original_41066a14

.global h14_active_hook
h14_active_hook:
    raw_half 1f
    mov w8, #4128
    strh w8, [x1]
    mov w8, #2752
    strh w8, [x1, #2]
    ret
1:  ldrb w8, [x0]
    b original_41066aac

.global h14_route_hook
h14_route_hook:
    cmp w0, #4
    b.ne 1f
    image_half x1, 1f
    ldr w8, [x1, #8]
    cmp w8, #7
    b.ne 1f
    adr x0, h14_half_video_route
    ret
1:  cmp w0, #7
    b original_41067278
.balign 4
h14_half_video_route:
    .hword 1920,1080,4140,2756,4140,2756,480,270,480,270,1920,1080,1920,1080
.ltorg

/* 41062070 (two words; was D-series half_plan_hook): recording plans 11/13 of the 4.1K request use the 2756-row
 * front-end block; everything else goes to half_plan_hook unchanged. */
.balign 16
.global half_plan_e1_hook
half_plan_e1_hook:
    stp x10, x11, [sp, #-32]!
    stp x16, x17, [sp, #16]
    ldr w10, [x20]
    cmp w10, #11
    b.eq 2f
    cmp w10, #13
    b.ne 1f
2:  ldr w10, [x20, #4]
    cmp w10, #4
    b.ne 1f
    ldr w10, [x20, #8]
    cmp w10, #6
    b.hi 1f
    ldr w10, [x20, #12]
    cmp w10, #6
    b.ne 1f
    half_og 1f, x10, w10
    ldp x16, x17, [sp, #16]
    ldp x10, x11, [sp], #32
    mov w9, #2756
    mov x1, #0x74a0
    b original_41062078
1:  ldp x16, x17, [sp, #16]
    ldp x10, x11, [sp], #32
    b half_plan_hook

.global h14_coordinates_hook
h14_coordinates_hook:
    save_args
    bl h14_coordinates_original
    mov x21, x0
    ldr w8, [x19]
    cmp w8, #11
    b.eq 2f
    cmp w8, #13
    b.ne 1f
2:  ldr w8, [x19, #4]
    cmp w8, #4
    b.ne 1f
    ldr w8, [x19, #8]
    cmp w8, #6
    b.hi 1f
    ldr w8, [x19, #12]
    cmp w8, #6
    b.eq 3f
    cbnz w8, 1f
3:  half_og 1f, x9, w9
    ldr w8, [x19, #8]
    lv_cache_half w8, x9, w9, w10, 1f
    mov w8, #2752
    strh w8, [x20, #0xe]
    mov w8, #2756
    strh w8, [x20, #0x4a]
    strh w8, [x20, #0x4e]
    mov w8, #2
    strh w8, [x20, #0x16]
    strh w8, [x20, #0x5e]
    mov w8, #2760
    strh w8, [x20, #0x66]
1:  restore_return
h14_coordinates_original:
    sub sp, sp, #0xb0
    b original_41065198

.global h14_crop_hook
h14_crop_hook:
    save_args
    bl h14_crop_original
    mov x21, x0
    image_half x19, 1f
    mov w8, #2
    strh w8, [x20, #10]
    mov w8, #2752
    strh w8, [x20, #14]
1:  restore_return
h14_crop_original:
    mov x8, #0xb98
    b original_410a6c8c

.global h14_frame_height_hook
h14_frame_height_hook:
    save_args
    bl h14_frame_height_original
    mov x21, x0
    image_half x19, 1f
    mov w8, #0xa
    strb w8, [x20, #3]
    mov w8, #0xc4
    strb w8, [x20, #4]
1:  restore_return
h14_frame_height_original:
    strb wzr, [x1]
    b original_410a58e8
.ltorg

/* Movie-level metadata (x0 = movie header copy): main media, size 4, the 4.1K request and its LV mode cache. */
.macro metadata_half fail
    ldrb w9, [x0, #0xe0]
    cbnz w9, \fail
    ldr w9, [x0, #0xc]
    cmp w9, #4
    b.ne \fail
    ldr w9, [x0, #0x10]
    cmp w9, #6
    b.hi \fail
    half_og \fail, x10, w10
    lv_cache_half w9, x10, w10, w11, \fail
.endm

/* 406D2C8C: NCTG 23h, size-4 branch (mov w8, #2322). */
.balign 16
.global h14_nctg_height_hook
h14_nctg_height_hook:
    mov w8, #2322
    metadata_half 1f
    mov w8, #2752
1:  b original_406d2c90

/* 406D3824 entry (was D-series nctg_crop_hook): CropHiSpeed of a 4.1K 3:2 clip = the full-FX record, as 8.3K 3:2. */
.global nctg_crop_e1_hook
nctg_crop_e1_hook:
    metadata_half 1f
    mov w8, #11
    strh w8, [x1, #0x332]
    mov w8, #8280
    strh w8, [x1, #0x334]
    strh w8, [x1, #0x338]
    mov w8, #5520
    strh w8, [x1, #0x336]
    strh w8, [x1, #0x33a]
    strh wzr, [x1, #0x33c]
    strh wzr, [x1, #0x33e]
    mov w0, #1
    ret
1:  b nctg_crop_hook

/* 406D3138: 1015h proxy-associated main height, size-4 branch (mov w9, #2322); w8 = width is live. */
.global h14_main_height_hook
h14_main_height_hook:
    mov w9, #2322
    stp x10, x11, [sp, #-32]!
    str x12, [sp, #16]
    half_og 1f, x10, w10
    ldr w10, [x0, #0x10]
    cmp w10, #6
    b.hi 1f
    lv_cache_half w10, x11, w11, w12, 1f
    mov w9, #2752
1:  ldr x12, [sp, #16]
    ldp x10, x11, [sp], #32
    b original_406d313c
.ltorg

/* Icon records filled by patcher.py: u16 flags, u16 0, u32 bytes, u64 PNG pointer; then the PNG bytes. */
.balign 16
.global og_icon_records_hook
og_icon_records_hook:
og_icon_records:
    .space OG_ICON_COUNT * 16
.global og_icon_png_hook
og_icon_png_hook:
    .space 0x3000

#include "e2_hooks.S"
#include "e3_hooks.S"
#include "e4_hooks.S"
