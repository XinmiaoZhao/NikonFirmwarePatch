/* E3 = E2 + the fixes from the E2 body test (open-gate line, 2026-11-13; analysis repository
 * research/open_gate_probe_20261018/e2_body_20261113).  New code only follows E2; every E1/E2 address stays.
 *
 *   fs_title_hook            4056C64C  frame-size page subtitle (control 6B9) = the file-type name; in 3:2 the
 *                            file-type page's own 3:2 label (text 3232, "N-RAW 12-bit 3:2 (NEV)")          (T1)
 *   og_mode_switch3          the E2 size memory also keeps each N-RAW mode's tone (callers: og_mode_switch,
 *                            og_mode_switch_keep_tone from the tone sub-page OK)                          (tone)
 *   ft_refresh3_hook         file-type page refresh: the N-RAW and N-RAW 3:2 rows show their own tone     (tone)
 *   tone_cursor_hook         4056D66C  tone sub-page cursor starts on the parent row's own tone          (tone)
 *   strip32_hook             40458EA0  i-menu main-dial strip: the ten 3:2 choices with their icons and labels  (B2)
 */

#define FT_LABEL_TEXT  3232                 /* e1.FT_LABEL: the file-type row label of N-RAW 3:2 */
#define TONE32_TEXT    0x12A                /* dynamic text entry of the 3:2 row tone: QEMU surveys of boot, menus, i menu,
                                               dial and playback write entries 0..115 only (analysis e3_20261113) */

.text
.balign 16

/* ---- frame-size page subtitle ------------------------------------------------------------------------------------ */
/* 4056C64C (bl; replaces ldr w1, [x8, #4]) in the frame-size page refresh 4056C5B4: x8 = the {type, text} entry of the
 * ROM name table 42B1FAB0 found for the stored type w20 (06001206); the stock code then sets control 6B9's text with
 * 403F645C(x0 = control, w1).  The function saved x30 in its frame; x9-x17 are dead (a call follows). */
.global fs_title_hook
fs_title_hook:
    ldr w1, [x8, #4]
    cmp w20, #6
    b.ne 1f
    ldr x16, =OG_FLAG
    ldrb w16, [x16]
    cmp w16, #1
    b.ne 1f
    mov w1, #FT_LABEL_TEXT
1:  ret
.ltorg

/* ---- N-RAW / N-RAW 3:2: each mode keeps its own tone (board card open-gate-20261113-nraw32-shared-tone) --------- */
/* Stock keeps one tone item per file type (N-RAW 04001258, ProRes RAW 04001259, types 4/3 06001249/0600124A; tone
 * sub-page OK 4056DA28).  E2 lets both N-RAW modes share 1258.  E3 stores the other mode's tone with its size/rate:
 * OG_MEM byte 1 = rate | (tone + 1) << 4 (rate 0..6 uses bits 0-2; N-RAW tone is 0 SDR or 2 N-Log, table 42B2044C);
 * tone bits 0 = no tone remembered (E2 memories), so the first swap after the update fills them.  The other writers
 * of OG_MEM clear the whole halfword (strh wzr) and need no change.
 *
 * og_mode_switch3(w0 = target mode, w1 = flag before, w2 = 1 restore the target mode's tone / 0 keep the current
 * one): as E2's og_mode_switch, plus the current tone goes to OG_MEM with the stored spec, and with w2 = 1 a valid
 * remembered tone comes back in the same native batch [125A, 125C, 1258] (guard 1).  The tone sub-page OK passes 0:
 * the stock code writes the chosen tone right after.  w0 = 1 when anything was written (the batch has notified). */
#define ITEM_TONE      0x04001258
.balign 16
.global og_mode_switch3
og_mode_switch3:
    stp x29, x30, [sp, #-112]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    stp x25, x26, [sp, #64]
    stp x27, x28, [sp, #80]
    str w2, [sp, #96]                   // restore the tone
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
    ldr w0, =ITEM_TONE
    bl original_403ec398
    mov w28, w0                         // current tone
    str w28, [sp, #100]                 // target tone
    mov w26, w24                        // target spec
    mov w27, w25
    cmp w20, w19
    b.eq 6f
    add w8, w24, #1                     // swap: the stored spec and tone are remembered for their mode
    orr w8, w8, w20, lsl #7
    and w9, w25, #7
    cmp w28, #14
    b.hi 2f
    add w10, w28, #1
    orr w9, w9, w10, lsl #4
2:  strb w8, [x21]
    strb w9, [x21, #1]
    dsb ishst
    and w8, w22, #0x7f
    cbz w8, 6f
    ubfx w9, w22, #7, #1
    cmp w9, w19
    b.ne 6f
    sub w0, w8, #1
    and w1, w23, #7
    mov w2, w19
    bl og_valid
    cbz w0, 6f
    and w26, w22, #0x7f
    sub w26, w26, #1
    and w27, w23, #7
    ldr w8, [sp, #96]
    cbz w8, 6f                          // tone sub-page: the chosen tone follows
    lsr w9, w23, #4
    cbz w9, 6f                          // memory without a tone (E2): the current tone stays
    sub w9, w9, #1
    cmp w9, #0
    ccmp w9, #2, #4, ne
    b.ne 6f                             // only SDR / N-Log
    str w9, [sp, #100]
6:  cbz w19, 7f                         // 16:9 takes every stored N-RAW spec (3:2 sizes are 16:9 sizes)
    mov w0, w26
    mov w1, w27
    mov w2, #1
    bl og_valid
    cbnz w0, 7f
    mov w26, #4
7:  mov w0, wzr
    ldr w9, [sp, #100]
    cmp w26, w24
    ccmp w27, w25, #0, eq
    ccmp w9, w28, #0, eq
    b.eq 9f
    mov w0, w26
    mov w1, w27
    mov w2, w9
    mov w3, #1
    bl ft_write_spec3
    mov w0, #1
9:  ldp x27, x28, [sp, #80]
    ldp x25, x26, [sp, #64]
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #112
    ret

/* tone sub-page OK (tone_ok_ctrl_hook): same switch, tone kept for the stock write that follows. */
.global og_mode_switch_keep_tone
og_mode_switch_keep_tone:
    mov w2, wzr
    b og_mode_switch3

/* Native batch [125A, 125C, 1258] = [w0, w1, w2] with guard w3 (as ft_write_size). */
ft_write_spec3:
    stp x29, x30, [sp, #-64]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    stp w0, w1, [sp, #48]
    str w2, [sp, #56]
    ldr w8, =ITEM_SIZE
    ldr w9, =ITEM_RATE
    stp w8, w9, [sp, #32]
    ldr w8, =ITEM_TONE
    str w8, [sp, #40]
    ldr x9, =GUARD
    ldr w19, [x9]
    str w3, [x9]
    add x0, sp, #32
    add x1, sp, #48
    mov w2, #3
    bl original_403ec3c8
    ldr x9, =GUARD
    str w19, [x9]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #64
    ret
.ltorg

/* og_row_tone(w0 = row mode, 0 N-RAW / 1 N-RAW 3:2) -> w0 = the tone that row stands for: the live 1258 when the
 * stored spec belongs to that mode (or nothing valid is remembered), else the tone remembered in OG_MEM.  The stored
 * spec's mode follows og_mode_switch: the opposite of OG_MEM's mode bit, or OG_FLAG when OG_MEM is empty.  No
 * private state; reads DS RAM and the getter only.  Clobbers x0-x17. */
.balign 16
og_row_tone:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    str x19, [sp, #16]
    mov w19, w0
    ldr w0, =ITEM_TONE
    bl original_403ec398                // live tone
    ldr x9, =OG_MEM
    ldrb w10, [x9]
    ldrb w11, [x9, #1]
    tst w10, #0x7f
    b.eq 9f                             // nothing remembered: every row shows the live tone
    ubfx w12, w10, #7, #1               // remembered mode
    cmp w12, w19
    b.ne 9f                             // this row's mode is the stored one
    lsr w11, w11, #4
    cbz w11, 9f                         // E2 memory without a tone
    sub w11, w11, #1
    cmp w11, #0
    ccmp w11, #2, #4, ne
    b.ne 9f
    mov w0, w11
9:  ldr x19, [sp, #16]
    ldp x29, x30, [sp], #32
    ret

/* x0 = "SDR" or "N-Log" for tone w0 (the stock refresh's strings). */
og_tone_text:
    cmp w0, #2
    adr x0, og_text_sdr
    adr x9, og_text_nlog
    csel x0, x9, x0, eq
    ret
og_text_sdr:  .asciz "SDR"
og_text_nlog: .asciz "N-Log"
.balign 4

/* File-type page state callback (slot A028E8DF0, E2's ft_refresh_hook bound the 3:2 row to N-RAW's text entry 0):
 * stock refresh 4056CD84 writes the live tone of every tone-capable row into dynamic texts 0..3 (403F2920(text, n,
 * 46h)) and binds the rows to them (403F61EC(control, 3, n)).  E3: the N-RAW row (text 0) and the 3:2 row (its own
 * text TONE32_TEXT) each show og_row_tone of their mode. */
.balign 16
.global ft_refresh3_hook
ft_refresh3_hook:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    mov x19, x0
    bl original_4056cd84
    mov w20, w0
    mov w0, wzr                         // N-RAW row: text 0, rebound in the stock order (text, then binding)
    bl og_row_tone
    bl og_tone_text4                    // E4: "Log" with log-colour (e4_hooks.S)
    mov w1, wzr
    mov w2, #0x46
    bl original_403f2920
    mov x0, x19
    mov w1, #0x30e5
    mov w2, wzr
    bl ft_bind_tone
    mov w0, #1                          // N-RAW 3:2 row: its own text TONE32_TEXT
    bl og_row_tone
    bl og_tone_text4                    // E4: "Log" with log-colour (e4_hooks.S)
    mov w1, #TONE32_TEXT
    mov w2, #0x46
    bl original_403f2920
    mov x0, x19
    mov w1, #FT_CTRL
    mov w2, #TONE32_TEXT
    bl ft_bind_tone
    mov w0, w20
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #32
    ret

/* ft_bind_tone(x0 = page, w1 = row control, w2 = dynamic text): the row's tone widget shows that text, with the stock
 * refresh's calls (4056CDB0..4056CE14: 4050A6F0(page, row, 4BA7), 403F62D8, 403F1A44, 403F61EC(widget, 3, text)). */
ft_bind_tone:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    mov w20, w2
    mov w2, #0x4ba7
    bl original_4050a6f0
    cbz x0, 1f
    mov x19, x0
    bl original_403f62d8
    mov x0, x19
    bl original_403f1a44
    mov x0, x19
    mov w1, #3
    mov w2, w20
    bl original_403f61ec
1:  ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #32
    ret

/* 4056D66C (bl; replaces bl 403EC398 with w0 = 04001258) in the tone sub-page entry 4056D384: the cursor starts on
 * 30E7 (SDR) or 30E8 (N-Log) by the returned tone.  E2's ft_ctrl_w21_hook maps the 3:2 parent row to 30E5 earlier in
 * this function, so the original parent row is read again from the page object at the caller's [sp, #8], as
 * 4056D3A0..4056D3C8 do.  A call follows the stock bl, so x0-x17 are free; x30 is the bl's. */
.balign 16
.global tone_cursor_hook
tone_cursor_hook:
    ldr x8, [sp, #8]
    ldr x9, [x8, #0x50]
    ldrh w10, [x8, #0x58]
    ldrh w8, [x8, #0x32]
    ldr x9, [x9, #0x10]
    add x8, x8, x10
    mov w10, #0x2c
    madd x8, x8, x10, x9
    ldr w8, [x8, #0x18]                 // original parent row control
    mov w9, #FT_CTRL
    cmp w8, w9
    cset w0, eq
    b og_row_tone
.ltorg

/* ---- i menu: the main-dial strip on the frame-size cell (E2 body test B2) ---------------------------------------- */
/* The strip shown while the main dial turns on an i-menu cell is set up by 40458D50..40458F04 per file type (jump
 * table 42AEC148): an icon array (u16, High or Normal quality), a label array (u32 text ids) and a count go to the
 * strip state A032E6478 {count, 1, current index, ...; icons at +18h} and 404517A4 (labels).  The N-RAW case
 * (40458E64) takes A028B6798 / A028B67BE / A028B67E4 and 19; E1 moved every i-menu reader to the active tables but not
 * this one, so in 3:2 the strip walked the 19 stock choices (16:9 icons and labels, cells 10..18 greyed by the active
 * availability) while the dial itself (404E4848) walked the ten 3:2 choices.  The current index already comes from
 * the active table.
 * 40458EA0 (bl; replaces mov w9, #0x13): in 3:2 the count is 10, the icons start at stock choice 2 (the ten 3:2 sizes
 * are stock choices 2..11, as the active cells use) and the labels are the 3:2 frame-size labels (e1.LABEL_IDS,
 * checked by patcher.py).  The function saved x30; x16/x17 only. */
.balign 16
.global strip32_hook
strip32_hook:
    mov w9, #0x13
    ldr x16, =OG_FLAG
    ldrb w16, [x16]
    cmp w16, #1
    b.ne 1f
    add x8, x8, #4
    adr x21, og32_strip_labels
    mov w9, #10
1:  ret
.ltorg
.balign 4
og32_strip_labels:
    .word 3137, 3138, 3139, 3225, 3226, 3227, 3228, 3229, 3230, 3231
