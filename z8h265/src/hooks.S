/* HB2 row-text fix: ../hb2_probe_20261104/hb2p_hooks.S (as included by HB2 05.24.h2) with ONE change, in tier_row_text:
 * when the current mode is not an H.265 mode (group GROUPS) the row value is HB1's plain "<share>%" instead of probe 3's
 * diagnostic "<share>% T<type><size><rate>", which HB2 shipped by mistake (body 11-04: "100% T542" with ProRes RAW 4.1K 60p).
 * The removed 24 instructions are replaced by 3 plus 21 nops, so the code keeps its size and every label its HB2 address.
 * Everything else, including the comments below, is the probe's text unchanged.  Design: README.md.
 *
 * HB2 probe: HB1 (../hb1_20261104/hb1_hooks.S) + the tier submenu and the row value show the bit rate of the current mode.
 * QEMU payload only (build_hb2p.py qemu); design: ../tier_text_20261104/README.md.
 *
 * Unchanged from HB1: tier_select_tail, tier_bank_hook, tier_entry_hook, tier_ok_hook, the setting byte A03D5C269.
 * New:
 * 1. tier_group: the mode as the stock video menu refresh reads it for the frame-size icon (40572DE8..40572E04): file type
 *    06001206h (403EC398), frame-rate index 40570198 (0..6 = 120/100/60/50/30/25/24) and frame-size index 40570154
 *    (1..3 = 1080/2160/4320), both per file type.  For an H.265 type, tier_mode_groups[size][rate] is the group within the
 *    depth (0..4, FFh = none); HEVC10_TYPE adds 5.  Anything else -> GROUPS, with w1 = type | rate << 8 | size << 16.
 *    (Probe 1 used the remaining-time block A031B6108 instead; in photo mode it never gave an H.265 mode, hb2p-a-1.)
 * 2. tier_refresh_hook (video menu value refresh): after the stock refresh, state 17Dh's page pointer (record +50h, init data
 *    in RAM) is set to tier_pages[group] (GROUPS = HB1's percent page), and the row value is tier_group_texts[group][tier]
 *    ("200M"; probe 2 wrote "60% 200M", which overflowed the value field) or, for GROUPS, HB1's "60%"
 *    followed by the probe's " T<type><size><rate>".  Both are rewritten at every
 *    refresh, so nothing stale survives a warm restart.
 * tier_mode_probe is a label for the QEMU observer only (w19 = type, w20 = rate index, w0 = size index).
 */
#define TIER        0xA03D5C269
#define ROW_ITEM    0x315A
#define VALUE_CHILD 0x4BA7
#define TEXT_SLOT   0x48
#define TEXT_STYLE  4
#define SUB_PAGE    0xA028FDBF0     /* state 17Dh record (init data 4C08BA0) +50h */
#define FILE_TYPE   0x06001206
#ifndef HEVC10_TYPE
#define HEVC10_TYPE 3               /* inferred (1 H.264 .. 6 N-RAW by rising quality); the QEMU text tells 8- from 10-bit */
#endif
#define GROUPS      10
#define TEXT_BYTES  12

.text
.balign 16
.global tier_select_tail
tier_select_tail:                   // 402F3360 (stock: b 4127A900); as HB1
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    mov x19, x0
    mov w20, w9
    bl original_4127A900
    sub w9, w20, #11
    cmp w9, #33
    b.hi 1f
    ldr x8, =TIER
    ldrb w8, [x8]
    sub w8, w8, #1
    cmp w8, #3
    b.hi 1f
    adr x10, tier_nominals
    add w9, w8, w9, lsl #2
    ldr w9, [x10, w9, uxtw #2]
    str w9, [x19, #0x1C]
1:  mov x0, x19
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #32
    ret

.balign 16
/* w0 = group 0..9 of the current H.265 mode, or GROUPS with w1 = type | rate << 8 | size << 16. */
.balign 16
tier_group:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    mov w0, #(FILE_TYPE & 0xFFFF)
    movk w0, #(FILE_TYPE >> 16), lsl #16
    bl original_403EC398            // video file type
    mov w19, w0
    bl original_40570198            // frame-rate index of this file type
    mov w20, w0
    bl original_40570154            // frame-size index of this file type
.global tier_mode_probe
tier_mode_probe:
    sub w9, w19, #2
    cmp w9, #1
    b.hi 8f                         // not H.265 (types 2, 3)
    cmp w0, #3
    b.hi 8f
    cmp w20, #6
    b.hi 8f
    mov w10, #7
    madd w10, w0, w10, w20
    adr x11, tier_mode_groups
    ldrb w10, [x11, w10, uxtw]
    cmp w10, #5
    b.hs 8f
    mov w11, #5
    cmp w19, #HEVC10_TYPE
    csel w11, w11, wzr, eq
    add w0, w10, w11
    b 9f
8:  and w1, w19, #0xFF
    bfi w1, w20, #8, #8
    bfi w1, w0, #16, #8
    mov w0, #GROUPS
9:  ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #32
    ret

/* x0 = video menu state, w1 = group, w2 = packed mode (for GROUPS): write the value text of row ROW_ITEM. */
.balign 16
tier_row_text:
    stp x29, x30, [sp, #-64]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    str x21, [sp, #32]
    mov w20, w1
    mov w21, w2
    mov w1, #ROW_ITEM
    mov w2, #VALUE_CHILD
    bl original_4050A6F0            // child of the row
    cbz x0, 9f
    mov x19, x0
    ldr x8, =TIER
    ldrb w8, [x8]
    cmp w8, #4
    csel w8, w8, wzr, ls
    cmp w20, #GROUPS
    b.hs 1f
    add w9, w20, w20, lsl #2
    add w9, w9, w8
    mov w10, #TEXT_BYTES
    adr x11, tier_group_texts
    umaddl x0, w9, w10, x11
    b 2f
1:  adr x9, tier_value_texts        // not an H.265 mode: HB1's plain "<share>%" (probe 3 appended " T<type><size><rate>")
    add x0, x9, w8, uxtw #3
    b 2f
    .rept 21                        // keeps every later label at its HB2 address (never executed)
    nop
    .endr
2:  mov w1, #TEXT_SLOT
    mov w2, #TEXT_STYLE
    bl original_403F2920            // copies up to 50 characters into the slot
    mov x0, x19
    mov w1, #TEXT_SLOT
    bl original_403F645C
9:  ldr x21, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #64
    ret

.balign 16
.global tier_refresh_hook
tier_refresh_hook:                  // value refresh callback of the video menu state (x0 = state)
    stp x29, x30, [sp, #-48]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    str x21, [sp, #32]
    mov x19, x0
    nop                            // shared dispatcher calls native once
    mov x20, x0
    cbz x19, 1f
    bl tier_group
    mov w21, w0
    mov w2, w1
    adr x8, tier_pages
    ldr x8, [x8, w21, uxtw #3]
    ldr x9, =SUB_PAGE
    str x8, [x9]                    // the page state 17Dh opens with
    mov x0, x19
    mov w1, w21
    bl tier_row_text
1:  mov x0, x20
    ldr x21, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #48
    ret

.balign 16
.global tier_entry_hook
tier_entry_hook:                    // entry callback of state 17Dh; as HB1 (all 11 pages use the same five option items)
    stp x19, x30, [sp, #-32]!
    str x20, [sp, #16]
    mov x19, x0
    ldr x8, =TIER
    ldrb w8, [x8]
    cmp w8, #4
    csel w8, w8, wzr, ls
    adr x9, tier_option_items
    ldrh w20, [x9, w8, uxtw #1]
    bl original_403AE0F8
    cmp w0, #1
    b.eq 1f
    mov x0, x19
    mov w1, w20
    bl original_403B0048
1:  mov x0, x19
    mov w1, w20
    mov w2, #1
    ldr x20, [sp, #16]
    ldp x19, x30, [sp], #32
    b original_403B00B8

.balign 16
.global tier_ok_hook
tier_ok_hook:                       // OK action of the five option rows; as HB1
    ldr x9, [x0]
    ldrh w11, [x9, #0x58]
    ldrh w10, [x9, #0x32]
    add w10, w10, w11
    cmp w10, #4
    b.hi 1f
    ldr x8, =TIER
    strb w10, [x8]
1:  ret

.ltorg
.balign 4
tier_option_items:
    .hword 0x35B5, 0x35B6, 0x35B7, 0x35B8, 0x35B9
.balign 8
tier_value_texts:
    .ascii "100%\0\0\0\0"
    .ascii "60%\0\0\0\0\0"
    .ascii "45%\0\0\0\0\0"
    .ascii "30%\0\0\0\0\0"
    .ascii "20%\0\0\0\0\0"
.balign 8
tier_pages:                         // 11 page records (groups 0..9, percent page); filled by build_hb2p.py
    .space 88
tier_group_texts:                   // 10 groups x 5 tiers, 12-byte ASCII; filled by build_hb2p.py
    .space 600
tier_mode_groups:                   // [size index 0..3][rate index 0..6] -> group within the depth, FFh none; filled by build_hb2p.py
    .space 28
.balign 16
tier_nominals:                      // as HB1: 34 rows x tiers 1..4; filled by build_hb2p.py
    .space 544
