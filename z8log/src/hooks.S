/* Integrated three-choice Log module with clip-driven playback view assist.
 *
 * Setting LOG_TYPE: 0=N-Log, 1=S-Log3, 2=Log3G10. All other values, including
 * the former private test value 3, read as N-Log. Menu rows store only 0..2.
 * Reads do not write settings. The clamp loader stays stock; no fourth row.
 *
 * Playback info at A032CDA00: +77C picture-control name, +1E78 tone, +1E7C codec.
 * Class >=5 retains N-Log. PB_TYPE = 0 outside Log playback; 80|type selects the
 * current clip, independently of the recording menu. Both info construction and
 * copy paths set it. The live-view constructor and shooting icon clear it.
 * Only the six view-assist hooks use EFFTYPE; recording always uses LOGTYPE.
 * VA_LAST keeps the last uploaded type so a changed type forces a table reload.
 * Three byte counters after PB_TYPE aid bounded verification and never gate code.
 *
 * Integrated code/data/state addresses come from asm_defines. Text slot 47 and
 * the shared bank/menu/string owners are retained. Colour tables are unchanged.
 * Hooks replay displaced instructions and return to the original continuations.
 */
#ifndef LOG_TYPE
#define LOG_TYPE    0xA03D5C0DD     /* QEMU-only builds pass a constant byte in the L2 data area instead */
#endif
#define LG_ITEM     0x2E38
#define VALUE_CHILD 0x4BA7
#define TEXT_SLOT   0x47            /* not used by the stock video menu refresh (02 11 13 14 17 18 19 4B 4C); ProRes T/U used it on stock */
#define DESC_COPY   0xA0460BE88     /* clip descriptor copy (4071E200); 406BD9FC's descriptor, +20h container class */
#define NAME_SLOG3_LO 0x4F4C2D53    /* "S-LO" */
#define NAME_SLOG3_HI 0x00003347    /* "G3\0\0" */
#define NAME_G10_LO   0x33474F4C    /* "LOG3" */
#define NAME_G10_HI   0x00303147    /* "G10\0" */

#define PB_INFO     0xA032CDA00     /* L3: GUI playback info (1F18h; 403FB4AC copies it, 403FB4CC returns it; L4: 407A7750 builds it) */
#define PB_NAME     0x77C           /* L3: picture control name, 20 bytes (407A7D48) */
#define PB_TONE     0xE78           /* L3: +1000h + E78h = tone (stock 4064D5EC; written at 407995CC) */

.macro LOGTYPE r                    // w\r = type 0..2; all invalid values -> 0; sets flags
    ldr x\r, =LOG_TYPE
    ldrb w\r, [x\r]
    cmp w\r, #2
    csel w\r, w\r, wzr, ls
.endm

.macro MOVW r, v                    // 32-bit constant
    movz w\r, #((\v) & 0xffff)
    movk w\r, #(((\v) >> 16) & 0xffff), lsl #16
.endm

.macro EFFTYPE r                    // L3: w\r = the playback clip's type while PB_TYPE bit 7 is set (values above 2 read 0),
    ldr x\r, =PB_TYPE                  // else LOGTYPE; x\r is the only register used; flags are not preserved
    ldrb w\r, [x\r]
    tbz w\r, #7, 86f
    and w\r, w\r, #0x7f
    cmp w\r, #2
    csel w\r, w\r, wzr, ls
    b 87f
86: LOGTYPE \r
87:
.endm

.macro CLIPTYPE i, o, t1, t2        // L3: w\o = Log type of the clip whose playback info is at x\i: 1 for the picture control
    mov w\o, #0                        // name S-LOG3, 2 for LOG3G10, else 0.  L6: for every codec class (L3..L5 gave ProRes RAW /
    ldr w\t1, [x\i, #PB_NAME]          // N-RAW, class >= 5, type 0; their playback shows the proxy, encoded in the named Log).
    MOVW \t2, NAME_SLOG3_LO
    cmp w\t1, w\t2
    b.ne 88f
    ldr w\t1, [x\i, #(PB_NAME + 4)]
    MOVW \t2, NAME_SLOG3_HI
    cmp w\t1, w\t2
    cset w\o, eq
    b 89f
88: MOVW \t2, NAME_G10_LO
    cmp w\t1, w\t2
    b.ne 89f
    ldr w\t1, [x\i, #(PB_NAME + 4)]
    MOVW \t2, NAME_G10_HI
    cmp w\t1, w\t2
    cset w\o, eq
    lsl w\o, w\o, #1
89:
.endm

.text
.balign 16
.global lg_rgb_hook
lg_rgb_hook:                        // 4111A508: movk x8, #0, lsl #48
    movk x8, #0, lsl #48
    cmp x9, #1
    b.ne 9f                         // SDR is not this path; 2 = HLG
    stp x10, x11, [sp, #-16]!
    LOGTYPE 10
    ldr x11, =LG_RGB1
    cmp w10, #1
    b.eq 1f
    ldr x11, =LG_RGB2
    cmp w10, #2
    b.ne 2f
1:  mov x8, x11
2:  ldp x10, x11, [sp], #16
9:  b original_4111A50C             // the next stock instruction sets the flags again (4111A514)

.balign 16
.global lg_nlg_hook
lg_nlg_hook:                        // 4111A6D4: madd x1, x9, x2, x10 (x9, x10 dead after; x2 = 1CAh is the copy length)
    madd x1, x9, x2, x10
    cmp w9, #1
    b.ne 9f
    LOGTYPE 10
    ldr x9, =LG_NLG1
    cmp w10, #1
    b.eq 1f
    ldr x9, =LG_NLG2
    cmp w10, #2
    b.ne 9f
1:  mov x1, x9
9:  b original_4111A6D8             // mov w9, #0x16a2; then the copy call

.balign 16
.global lg_m2_hook
lg_m2_hook:                         // 41116CB4: madd x11, x8, x11, x9 (x9 = 441A56A8 row base, x8 = row)
    stp x12, x13, [sp, #-16]!
    mrs x13, nzcv
    cmp x8, #1
    b.ne 8f
    LOGTYPE 12
    cmp w12, #1
    b.ne 1f
    ldr x9, =(LG_M2_1 - 0x12)
    b 8f
1:  cmp w12, #2
    b.ne 8f
    ldr x9, =(LG_M2_2 - 0x12)
8:  msr nzcv, x13
    ldp x12, x13, [sp], #16
    madd x11, x8, x11, x9
    b original_41116CB8

.balign 16
.global lg_m1_hook
lg_m1_hook:                         // 41116010: movk x14, #0, lsl #48 (x14 = 441A0A4A base, x13 = row, w11 = S+BCh)
    movk x14, #0, lsl #48
    stp x15, x16, [sp, #-16]!
    mrs x16, nzcv
    cmp w11, #1
    b.ne 8f                         // N-Log: S+BCh = 1, row 2
    LOGTYPE 15
    cmp w15, #1
    b.ne 1f
    ldr x14, =(LG_M1_1 - 0x24)
    b 8f
1:  cmp w15, #2
    b.ne 8f
    ldr x14, =(LG_M1_2 - 0x24)
8:  msr nzcv, x16
    ldp x15, x16, [sp], #16
    b original_41116014

.balign 16
.global lg_cpxs_hook
lg_cpxs_hook:                       // 4111A198: ldrb w21, [x19, #0x28], right after bl 411179CC (record -> ctx+A8h)
    stp x8, x9, [sp, #-32]!
    stp x10, x11, [sp, #16]
    mrs x11, nzcv
    ldr x8, [x19, #0x98]            // T, read by the stock code at 4111A188 too
    ldrb w9, [x8, #0x31]
    cmp w9, #1
    b.ne 8f
    LOGTYPE 10
    ldr x9, =LG_CPXS1
    cmp w10, #1
    b.eq 1f
    ldr x9, =LG_CPXS2
    cmp w10, #2
    b.ne 8f
1:  str x9, [x19, #0xb0]            // the selected record's Pa..Pf table pointer
8:  msr nzcv, x11
    ldp x10, x11, [sp, #16]
    ldp x8, x9, [sp], #32
    ldrb w21, [x19, #0x28]
    b original_4111A19C

.balign 16
.global lg_tag26_tail
lg_tag26_tail:                      // 406D2D94: mov w0, #1; then str w8, [x1, #0xb0]; ret (leaf).  Entered before the
    cmp w8, #2                      // mov, while x0 is still the clip descriptor; x9 scratch as in the stock leaf
    b.ne 9f
    ldr w9, [x0, #0x20]             // container class
    cmp w9, #5
    b.hs 9f                         // ProRes RAW, N-RAW keep N-Log (L1 rule; with 1 Resolve decodes N-RAW as Rec.709)
    LOGTYPE 9
    cbz w9, 9f
    mov w8, #1                      // S-Log3, Log3G10: Rec.709 tone tag (Resolve shows Rec709 (Scene))
9:  mov w0, #1
    str w8, [x1, #0xb0]
    ret

.balign 16
.global lg_keyclass_hook
lg_keyclass_hook:                   // 406C196C: b.ne 406C210C after cmp w21, #4 (w21 = container class of [x13+10h])
    b.ne 1f                         // (the linker relocates b/bl only)
    b original_406C1970             // ProRes 422: stock
1:  cmp w21, #3
    b.ne 2f
    b original_406C1970             // H.265 10-bit: the ProRes 422 key table and count rule (flags are set again there)
2:  b original_406C210C

.balign 16
.global lg_keys_gate
lg_keys_gate:                       // 4071F5CC: cmp w8, #3 (w8 = container mode [A04613104]; x23 = this clip's udta).
    ldr x9, =KEYS_G                 // x0..x18 are free here: the stock ProRes path calls 40722E18 at the same point
    str wzr, [x9, #8]               // KEYS_G.len = 0 for every clip and mode
    cmp w8, #3
    b.ne 1f
    b original_4071F5FC             // RAW: stock
1:  cmp w8, #2
    b.ne 2f
    b original_4071F5DC             // ProRes: stock
2:  cmp w8, #1
    b.ne 9f
    ldr x10, =DESC_COPY
    ldr w10, [x10, #0x20]
    cmp w10, #3
    b.ne 9f                         // H.264, H.265 8-bit: no keys, as stock
    sub sp, sp, #0x30               // 406BD9FC(&{buf, size, desc}, &len), as 40722E18 (which uses region 10's last 4 KiB)
    stp xzr, xzr, [sp]
    stp xzr, xzr, [sp, #0x10]
    str xzr, [sp, #0x20]
    ldr x10, =KEYS_BUF
    str x10, [sp, #8]
    mov w11, #KEYS_BUF_SIZE
    str w11, [sp, #0x10]
    ldr x11, =DESC_COPY
    str x11, [sp, #0x18]
    add x0, sp, #8
    mov x1, sp
    bl original_406BD9FC
    ldr w11, [sp]
    add sp, sp, #0x30
    tbz w0, #0, 9f
    cbz w11, 9f
    ldr x9, =KEYS_G
    ldr x10, =KEYS_BUF
    str x10, [x9]
    str x23, [x9, #0x10]
    str w11, [x9, #8]               // len last: KEYS_G is valid only once complete
9:  b original_4071F630

.balign 16
.global lg_keys_close
lg_keys_close:                      // 40D09384: mov x2, xzr (module B close, no keys); x9 = this message's udta pointer.
    ldr x2, =KEYS_G                 // Only x2 changes (x1, x3, x8, x9, x10 are still used); flags are not read after
    stp x10, x11, [sp, #-16]!
    ldr w10, [x2, #8]
    cbz w10, 1f
    ldr x11, [x2, #0x10]
    cmp x11, x9
    b.eq 2f
1:  mov x2, xzr
2:  ldp x10, x11, [sp], #16
    ret

.balign 16
.global lg_keycount_hook
lg_keycount_hook:                   // 406C1988: cinc w21, w9, eq (w9 = 2, flags of cmp w8, #2; w8 = tone)
    cinc w21, w9, eq
    b.ne 9f
    str x9, [sp, #-16]!
    LOGTYPE 9
    cmp w9, #2
    b.ne 8f
    mov w21, #2                     // Log3G10: manufacturer and model only
8:  ldr x9, [sp], #16
    cmp w8, #2                      // the stock flags again
9:  b original_406C198C

.balign 16
.global lg_cc_copy_hook
lg_cc_copy_hook:                    // 406C1FA4: bl 4127A900 (x0 value area, x1 = "com.nikon.bt2020.n-log", x2 = 22)
    LOGTYPE 9                       // x9: caller-saved across the replaced call
    cmp w9, #1
    b.ne 1f
    ldr x1, =LG_CC_SLOG3
    mov x2, #20
1:  b original_4127A900

.balign 16
.global lg_cc_next_hook
lg_cc_next_hook:                    // 406C1FA8: add w8, w19, #0x2e (next offset = value area 0x18 + length), after the call
    add w8, w19, #0x2e
    LOGTYPE 9
    cmp w9, #1
    b.ne 9f
    sub w8, w8, #2
9:  b original_406C1FAC

.balign 16
.global lg_pc_write
lg_pc_write:                        // 406D3994 (whole function): NCTG 2000023h writer.  Stock: descriptor {d0 = [4164B558],
    sub sp, sp, #0x50               // u32 4, u16 23h, [x0], x1 + 354h, 0, 0} -> bl 406E369C, whose tag 23h handler 406E8C24
    stp x19, x20, [sp, #0x30]       // builds the 6Ch-byte picture control block into that pointer from [x0] before it returns;
    str x30, [sp, #0x40]            // return 1.  L2: same call; afterwards, for tone 2 and types 1, 2, the block's name
    add x19, x1, #0x354             // (+8, 20 bytes) is replaced in place in the record
    ldr w20, [x0, #0x30]            // tone of the clip descriptor (406D2D6C reads the same field)
    cmp w20, #2
    b.ne 1f
    LOGTYPE 20
    b 2f
1:  mov w20, #0
2:  stp xzr, xzr, [sp]
    stp xzr, xzr, [sp, #0x10]
    stp xzr, xzr, [sp, #0x20]
    ldr x9, =0x4164B558
    ldr d0, [x9]
    str d0, [sp]
    mov w9, #4
    str w9, [sp, #8]
    mov w9, #0x23
    strh w9, [sp, #0xc]
    ldr x10, [x0]
    str x10, [sp, #0x10]
    str x19, [sp, #0x18]
    mov x0, sp
    bl original_406E369C
    cbz w20, 9f
    stp wzr, wzr, [x19, #8]         // name: 20 bytes, zero padded (record +354h is only 4-byte aligned)
    stp wzr, wzr, [x19, #0x10]
    str wzr, [x19, #0x18]
    cmp w20, #1
    b.ne 3f
    MOVW 11, NAME_SLOG3_LO
    MOVW 12, NAME_SLOG3_HI
    b 4f
3:  MOVW 11, NAME_G10_LO
    MOVW 12, NAME_G10_HI
4:  stp w11, w12, [x19, #8]
9:  ldp x19, x20, [sp, #0x30]
    ldr x30, [sp, #0x40]
    mov w0, #1
    add sp, sp, #0x50
    ret

.balign 16
.global lg_pc_parse_tail
lg_pc_parse_tail:                   // 406D05FC: b 406D0480 at the end of the 2000023h parse (406D0458).  [x20+8] = parse
    ldr x9, [x20, #8]               // record +354h; its name is at +8 and the tone tag 26h at record +B0h (= -2A4h).
    ldr w10, [x9, #8]               // w8 (= 8, the offset step) is used at 406D0480; x9..x12 are not
    ldr w11, [x9, #0xc]
    MOVW 12, NAME_SLOG3_LO
    cmp w10, w12
    b.ne 1f
    MOVW 12, NAME_SLOG3_HI
    cmp w11, w12
    b.eq 2f
    b 9f
1:  MOVW 12, NAME_G10_LO
    cmp w10, w12
    b.ne 9f
    MOVW 12, NAME_G10_HI
    cmp w11, w12
    b.ne 9f
2:  sub x9, x9, #0x2a4
    ldr w10, [x9]
    cmp w10, #1
    b.ne 9f
    mov w10, #2                     // an L2 Log clip (tag 1 for Resolve) is a Log clip for the camera's playback
    str w10, [x9]
9:  b original_406D0480

.balign 16
.global lg_pb_label
lg_pb_label:                        // 4064D718 (playback detail page, tone 2; stock writes "N-Log" and strncpy's 6 bytes
    CLIPTYPE 21, 9, 10, 11          // to sp+118h, w21 = 1, then 4064D768).  x21 = the playback info (4064C6B0 4063468C ->
    adr x12, lg_pb_names            // A032CDA00).  L3: the name at +77Ch (L2 read +2124h, outside the 1F18h struct)
    ldr x13, [x12, w9, uxtw #3]
    str x13, [sp, #0x118]           // 8 bytes with the terminator (the buffer is 16 bytes, zeroed at 4064C6BC)
    mov w21, #1
    b original_4064D768

.balign 16
.global lg_pb_info
lg_pb_info:                         // L3 406820F4: bl 403FB4AC (copy x0 -> the playback info, 1F18h bytes) -> bl here.
    stp x29, x30, [sp, #-16]!       // The caller 40681E9C sets w0 again after the call (40682100 / 40682128) and keeps
    bl original_403FB4AC            // nothing in x9..x12; x0 (the copy's return) is left as the stock call leaves it
    ldp x29, x30, [sp], #16
    ldr x9, =PB_INFO
    add x10, x9, #0x1, lsl #12
    ldr w10, [x10, #PB_TONE]
    mov w11, #0                     // not a Log clip: 0 (view assist does not apply; the menu's type stays in use)
    cmp w10, #2
    b.ne 1f
    CLIPTYPE 9, 11, 10, 12
    orr w11, w11, #0x80
1:  ldr x9, =PB_TYPE
    strb w11, [x9]
    ldrb w10, [x9, #1]              // PB_SETS
    add w10, w10, #1
    strb w10, [x9, #1]
    ret


.balign 16
.global lg_pb_build
lg_pb_build:                        // L4 407A831C: ldp x19, x30, [sp, #0x80], first instruction of the only exit of the
    ldr x9, =PB_INFO                // playback info builder 407A7750; x19 = its destination (x2, kept from 407A7764), with
    cmp x19, x9                     // the name (+77Ch, 407A7D48) and tone/class (+1E78h/+1E7Ch, 407995CC/D4) written.  Only
    b.ne 9f                         // the GUI playback info A032CDA00 is classified, by lg_pb_info's rule.  x9..x12 and the
    add x10, x9, #0x1, lsl #12      // flags are free: the epilogue reads none, and both callers (407A7518, 407A8F08) write
    ldr w10, [x10, #PB_TONE]        // x8..x12 before reading them after the call
    mov w11, #0
    cmp w10, #2
    b.ne 1f
    CLIPTYPE 9, 11, 10, 12
    orr w11, w11, #0x80
1:  ldr x9, =PB_TYPE
    strb w11, [x9]
    ldrb w10, [x9, #1]              // PB_SETS
    add w10, w10, #1
    strb w10, [x9, #1]
9:  ldp x19, x30, [sp, #0x80]
    b original_407A8320


.balign 16
.global lg_lv_clear
lg_lv_clear:                        // L3 40EC78D0: b 40F28488 (live-view display control builder, thunk 40EC78CC after
    ldr x9, =PB_TYPE                // and w1, w1, #1; x0 and w1 are its arguments, x9 and x10 are written before any read
    strb wzr, [x9]                  // in 40F28488)
    ldrb w10, [x9, #2]              // PB_LV
    add w10, w10, #1
    strb w10, [x9, #2]
    b original_40F28488


.balign 16
.global lg_va_sel0
lg_va_sel0:                         // 402D1AA4: b 402D19E8 in 402D197C, mode 1: x10 = matrix pointer table 4167A2A0
    EFFTYPE 11                      // (x8 = A02E70DF2, w9 = [A02810470]); x11 is free, flags are not read after
    cbz w11, 9f
    ldr x10, =LG_VA_MAT1
    cmp w11, #1
    b.eq 9f
    ldr x10, =LG_VA_MAT2
9:  b original_402D19E8

.balign 16
.global lg_va_sel1
lg_va_sel1:                         // 402D1CF8: b 402D1B90 in 402D1AD0, mode 1: x10 = 4167A2A0 + x8 * 10h, x11 = curve A
    EFFTYPE 14                      // table (stays), x12 = 4167A3C0 (indexed at 402D1B90); x14 is free here
    cbz w14, 9f
    ldr x10, =LG_VA_MAT1
    ldr x12, =LG_VA_CB1
    cmp w14, #1
    b.eq 1f
    ldr x10, =LG_VA_MAT2
    ldr x12, =LG_VA_CB2
1:  add x10, x10, x8, lsl #4
9:  b original_402D1B90

.balign 16
.global lg_va_cmp_a
lg_va_cmp_a:                        // 402CE18C: ldrb w9, [x22, #0x15d] (cached variant of device 0), then cmp with +15Ah;
    ldrb w9, [x22, #0x15d]          // x10 is loaded by the next instruction
    str x11, [sp, #-16]!
    EFFTYPE 10
    ldr x11, =VA_LAST
    ldrb w11, [x11]
    cmp w10, w11
    b.eq 1f
    orr w9, w9, #0x80               // the type changed since the last upload: force a mismatch
1:  ldr x11, [sp], #16
    ret

.balign 16
.global lg_va_cmp_b
lg_va_cmp_b:                        // 402D5DBC: ldrb w8, [x23, #0x15d]; x9 is loaded by the next instruction
    ldrb w8, [x23, #0x15d]
    str x10, [sp, #-16]!
    EFFTYPE 9
    ldr x10, =VA_LAST
    ldrb w10, [x10]
    cmp w9, w10
    b.eq 1f
    orr w8, w8, #0x80
1:  ldr x10, [sp], #16
    ret

.balign 16
.global lg_va_store_a
lg_va_store_a:                      // 402CE1F0: strb w10, [x22, #0x15d] after a successful upload; x9 is free
    strb w10, [x22, #0x15d]
    str x11, [sp, #-16]!
    EFFTYPE 9
    ldr x11, =VA_LAST
    strb w9, [x11]
    ldr x11, [sp], #16
    ret

.balign 16
.global lg_va_store_b
lg_va_store_b:                      // 402D5E10: strb w8, [x23, #0x15d] after a successful upload; x9 is free
    strb w8, [x23, #0x15d]
    str x10, [sp, #-16]!
    EFFTYPE 9
    ldr x10, =VA_LAST
    strb w9, [x10]
    ldr x10, [sp], #16
    ret

.balign 16
.global lg_icon_tail
lg_icon_tail:                       // 4041A868: b 4041A954 (Log branch: w0 = 24h element, w3/w4 = A7Dh/A7Eh N-LOG pair)
    stp x9, x10, [sp, #-16]!
    ldr x9, =PB_TYPE                // L3: the shooting screen is live view: PB_TYPE = 0 (no flag-setting instruction
    strb wzr, [x9]                  // before the mrs)
    ldrb w10, [x9, #3]              // PB_ICON
    add w10, w10, #1
    strb w10, [x9, #3]
    mrs x10, nzcv
    LOGTYPE 9
    cmp w9, #1
    b.ne 1f
    mov w3, #ICON_BASE
    mov w4, #(ICON_BASE + 1)
    b 8f
1:  cmp w9, #2
    b.ne 8f
    mov w3, #(ICON_BASE + 2)
    mov w4, #(ICON_BASE + 3)
8:  msr nzcv, x10
    ldp x9, x10, [sp], #16
    b original_4041A954

.balign 16
.global lg_menu_refresh_hook
lg_menu_refresh_hook:               // value refresh callback of the video menu state FEh (x0 = state)
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    mov x19, x0
    nop                            // shared dispatcher calls native once
    mov x20, x0
    cbz x19, 9f
    mov x0, x19
    mov w1, #LG_ITEM
    mov w2, #VALUE_CHILD
    bl original_4050A6F0            // the row's value text child
    cbz x0, 9f
    mov x19, x0
    LOGTYPE 9
    adr x10, lg_value_texts
    add x0, x10, w9, uxtw #3
    mov w1, #TEXT_SLOT
    mov w2, #TEXT_STYLE
    bl original_403F2920            // ASCII text into the slot, as the stock N-RAW quality row (40572D28..40572D44)
    mov x0, x19
    mov w1, #TEXT_SLOT
    bl original_403F645C
9:  mov x0, x20
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #32
    ret

.balign 16
.global lg_sub_entry_hook
lg_sub_entry_hook:                  // entry callback of state B5h (x0 = state): cursor and mark on the stored type (stock 4056C8F8)
    stp x19, x30, [sp, #-32]!
    str x20, [sp, #16]
    mov x19, x0
    LOGTYPE 8
    adr x9, lg_option_items
    ldrh w20, [x9, w8, uxtw #1]
    bl original_403AE0F8            // entry guard: 1 = keep the cursor
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
.global lg_sub_ok_hook
lg_sub_ok_hook:                     // OK action of the three option rows (x0 = context): store the cursor row 0..2 (AP2's rule)
    ldr x9, [x0]                    // state
    ldrh w11, [x9, #0x58]           // first shown row
    ldrh w10, [x9, #0x32]           // cursor within the shown rows
    add w10, w10, w11
    cmp w10, #2
    b.hi 1f
    ldr x8, =LOG_TYPE
    strb w10, [x8]
1:  ret

.ltorg
.balign 4
lg_option_items:                    // item ids of the three option rows (type 0..2); see build_l2.py
    .hword OPTION_ITEM0, OPTION_ITEM1, OPTION_ITEM2
.balign 8
lg_value_texts:                     // value text of the Log settings row, type 0..2 (8 bytes each, ASCII as the stock HIGH/NORM)
    .ascii "N-Log\0\0\0"
    .ascii "S-Log3\0\0"
    .ascii "Log3G10\0"
lg_pb_names:                        // playback detail page labels (8 bytes each, with the terminator)
    .ascii "N-Log\0\0\0"
    .ascii "S-Log3\0\0"
    .ascii "Log3G10\0"
