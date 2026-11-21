// F8 05.97.f8: still-format candidate on factory C3.11, derived from F7 (f7_20261119/f7_hooks.S).
// F8 against F7 (build_f8.py): the photo-menu time-lapse movie follows the factory HLG rule as the interval automatic
// movie does in F7 (f2_snap no longer exempts its frames, f8_ftype takes both movie branches, f7_m2tone also hooks the
// three mode-1 tone loads, condition set 53h grays its file type, nine more name reads); f8_depth gives both movies the
// 10-bit depth flag that the HLG path takes from 02000544h/02000545h; f8_thmb also sets the hidden flag of the Adobe RGB
// JPEG thumbnail 8194 (round 9 V4); f8_pbcs lets in-camera playback convert an Adobe RGB HIF like an Adobe RGB JPEG.
// f8_mvmode gives the SDR HEIF movie frames the factory SDR movie conversion (601 -> 709), matching their 709 labels.
// F7 header follows.
// F7 05.95.f7: still-format candidate on factory C3.11, derived from F6 (f6_20261117/f6_hooks.S).
// F7 against F6 (build_f7.py): f7_rec gives the SDR HEIF HEVC outputs (node 5 mode 3) and the 160x120 JPEG thumbnail
// (mode 4) record 0, so the HIF Y'CbCr is BT.601 like JPEG and matches the labels 6; C2' and its fit are removed.
// The interval automatic movie is allowed with SDR HEIF and follows the factory HLG rule (fixed H.265 10-bit):
// f5_set / f5_sub_ok no longer touch 0600053Dh, the 405E19E8 gray callback is factory again, f5_unavailable grays
// the movie file type (condition set 4Dh), f7_ftype and f7_m2tone pick the 040006AEh family.  f7_ipma writes ipma
// with the tiles first, then the grid, then the rest (Xiaomi gallery).  f7_key gives the Tone page footer button
// (string 3237) the event of the factory "Tone mode" footer key 7CBh; f7_group adds button group 198 = [3237, OK], which the
// Tone page footer record 753h uses like the factory file-type page's group AFh = [7CBh "Tone mode", ABDh "OK"].
// Unchanged F5/F6 routines keep their f2_/f5_/f6_ names.

#define F5_SLOT       0
#define F5_JPEG_ITEM  0x2DDE
#define F5_HEIF_ITEM  0x2DE1

    .text

// w0 = 1 when 0x40F18358 would take its plain branch (not forced to 0, w14 == 0), the photo tone mode
// (cache +0xa8) and the current derived 0x21e7 (cache +0x2f4) are both 0, and the F5 byte 0xA03D482BA is 1; else w0 = 0.  The w14 lines repeat the
// stock instructions 0x40F183EC..0x40F1843C (w18 there is w13 here).  Uses x9, x11..x17 only.  (F1's f1_sdr_plain.)
f2_sdr_plain:
    movz    x9, #0x8570
    movk    x9, #0x3b9, lsl #16
    movk    x9, #0xa, lsl #32                // calculation cache 0xA03B98570
    movz    x11, #0x915c
    movk    x11, #0x3b9, lsl #16
    movk    x11, #0xa, lsl #32               // state block 0xA03B9915C
    ldr     w12, [x11, #0x10]
    ldr     w13, [x11, #0x34]
    and     w14, w12, #0x8000
    orr     w13, w13, w14
    cbnz    w13, 9f                          // stock forces 0x21e7 = 0 here
    mov     w14, #0x2a0
    tst     w12, w14
    b.ne    1f
    ldp     w15, w14, [x11, #8]
    tbnz    w12, #0, 2f
    ldr     w17, [x11, #4]
    ldr     w13, [x9, #0x30]
    movz    x16, #0xd57c
    movk    x16, #0x3b9, lsl #16
    movk    x16, #0xa, lsl #32
    ldr     w16, [x16]                       // 0xA03B9D57C
    cmp     w15, #0
    csel    w14, w14, w16, ne
    cmp     w17, #0
    csel    w14, w14, w13, eq
    b       3f
2:  cmp     w15, #0
    csel    w14, w14, wzr, ne
    b       3f
1:  mov     w14, wzr
3:  cbnz    w14, 9f                          // stock takes the mode 3..6 sources
    ldr     w13, [x9, #0xa8]
    cbnz    w13, 9f                          // photo tone mode HLG
    ldr     w13, [x9, #0x2f4]
    cbnz    w13, 9f                          // derived 0x21e7 not 0
    movz    x13, #0x82ba
    movk    x13, #0x3d4, lsl #16
    movk    x13, #0xa, lsl #32               // F5 byte 0xA03D482BA (group 6 +6)
    ldrb    w13, [x13]
    cmp     w13, #1
    b.ne    9f                               // JPEG chosen (stock)
    mov     w0, #1
    ret
9:  mov     w0, wzr
    ret

// Replaces str w8,[x19,#0x2fc] in the snapshot 0x40EC8408 (x19 = M, x20 = the setting slots 0xA03B93760; M+0x294 and
// M+0x2ce are already written).  Stores 1 instead of w8 when w8 == 0, M+0x294 == 3 (JPEG only) or 0 (RAW + JPEG),
// M+0x2ce == 0 and f2_sdr_plain (F5: colour space no longer checked, Adobe RGB is tried).  F8: time-lapse movie frames
// (derived 40000100h bits 0x60) are forced too, as the factory HLG path does (F6/F7 exempted them; the movie is now H.265
// 10-bit).  Every register but x30 is kept (x0, x1, w9 are live after the site); NZCV is dead there.
    .global f2_snap
f2_snap:
    sub     sp, sp, #0x60
    stp     x0, x8, [sp]
    stp     x9, x10, [sp, #0x10]
    stp     x11, x12, [sp, #0x20]
    stp     x13, x14, [sp, #0x30]
    stp     x15, x16, [sp, #0x40]
    stp     x17, x30, [sp, #0x50]
    cbnz    w8, 8f
    ldr     w9, [x19, #0x294]
    cmp     w9, #3
    ccmp    w9, #0, #4, ne                   // 3 (JPEG only) or 0 (RAW + JPEG)
    b.ne    8f
    ldrb    w9, [x19, #0x2ce]
    cbnz    w9, 8f
    bl      f2_sdr_plain
    cbz     w0, 8f
    mov     w8, #1
8:  str     w8, [x19, #0x2fc]
    ldp     x0, x8, [sp]
    ldp     x9, x10, [sp, #0x10]
    ldp     x11, x12, [sp, #0x20]
    ldp     x13, x14, [sp, #0x30]
    ldp     x15, x16, [sp, #0x40]
    ldp     x17, x30, [sp, #0x50]
    add     sp, sp, #0x60
    ret

// Replaces mov x1,#0xdd90 (+3 movk) in 0x40C98DA4, reached for request (+0x64,+0x68) == (2,1).  x1 = the stock
// template 0x41F1DD90, or f2_template when f2_sdr_plain; then back to the stock memcpy at 0x40C98E10.  x0, x8..x17
// and x30 are dead here (x30 is restored from the stack at 0x40C98F9C).  (F1's f1_tmpl.)
    .global f2_tmpl
f2_tmpl:
    bl      f2_sdr_plain
    movz    x1, #0xdd90
    movk    x1, #0x41f1, lsl #16
    cbz     w0, 1f
    adr     x1, f2_template
    movz    x9, #0x3818
    movk    x9, #0x3b9, lsl #16
    movk    x9, #0xa, lsl #32
    ldr     w9, [x9]                       // cached photo colour space, same source as M+4d4
    cmp     w9, #1
    adr     x8, f5_adobe_template
    csel    x1, x8, x1, eq
1:  b       original_40C98E10

// Replaces bl 0x40C977A0 (b 0x40C99508) in the HEIF item builder 0x40CCF2CC: w0, w1 = descriptor [0], [1], x2 = out.
// With f2_sdr_plain, w0 = 1, so 0x40C99508 takes its default branch (1/13/6, full range).  (F1's f1_nclx.)
    .global f2_nclx
f2_nclx:
    stp     x0, x1, [sp, #-0x20]!
    stp     x2, x30, [sp, #0x10]
    bl      f2_sdr_plain
    mov     w9, w0
    ldp     x2, x30, [sp, #0x10]
    ldp     x0, x1, [sp], #0x20
    cbz     w9, 1f
    mov     w0, #1
1:  b       original_40C99508

// x0 = M -> w0 = M+0x2fc as stored, except 0 when M+0x2fc == 1, M+0x2570 == 0 (a capture, not a playback-side job)
// and f2_sdr_plain, i.e. the HIF that F2 forced.  Keeps x1..x30; NZCV is not kept.
f2_label:
    sub     sp, sp, #0x60
    stp     x1, x9, [sp]
    stp     x10, x11, [sp, #0x10]
    stp     x12, x13, [sp, #0x20]
    stp     x14, x15, [sp, #0x30]
    stp     x16, x17, [sp, #0x40]
    str     x30, [sp, #0x50]
    ldr     w1, [x0, #0x2fc]
    cmp     w1, #1
    b.ne    8f
    ldr     w9, [x0, #0x2570]
    cbnz    w9, 8f
    bl      f2_sdr_plain
    cmp     w0, #0
    csel    w1, w1, wzr, eq
8:  mov     w0, w1
    ldp     x1, x9, [sp]
    ldp     x10, x11, [sp, #0x10]
    ldp     x12, x13, [sp, #0x20]
    ldp     x14, x15, [sp, #0x30]
    ldp     x16, x17, [sp, #0x40]
    ldr     x30, [sp, #0x50]
    add     sp, sp, #0x60
    ret

// Replaces ldr w8,[x8,#0x2fc] at 0x406EA85C in the MakerNote 0x0059 writer 0x406EA7F0 (x8 = M; the function saved
// x30 in its prologue).  w8 = f2_label(M): bytes 5/6 of the tag become 1/1 for the forced HIF.  Keeps every other
// register; NZCV is dead (cmp w8,#1 follows).
    .global f2_l59
f2_l59:
    stp     x0, x30, [sp, #-0x10]!
    mov     x0, x8
    bl      f2_label
    mov     w8, w0
    ldp     x0, x30, [sp], #0x10
    ret

// Replaces ldr w9,[x9,#0x2fc] at 0x406E8988 in the leaf MakerNote 0x001e writer 0x406E897C (x9 = M, x30 = the
// caller's return address, kept): w9 = f2_label(M), so the tag is 1 or 2 from M+0x4d4 instead of 4 (BT.2100).
    .global f2_cs1e
f2_cs1e:
    stp     x0, x30, [sp, #-0x10]!
    mov     x0, x9
    bl      f2_label
    mov     w9, w0
    ldp     x0, x30, [sp], #0x10
    b       original_406E898C

// Replaces ldr w9,[x9,#0x2fc] at 0x406E5F1C in the leaf Exif ColorSpace writer 0x406E5F10 (as above): w9 =
// f2_label(M), so ColorSpace is 1 (sRGB) instead of 0xffff (uncalibrated).
    .global f2_exif
f2_exif:
    stp     x0, x30, [sp, #-0x10]!
    mov     x0, x9
    bl      f2_label
    mov     w9, w0
    ldp     x0, x30, [sp], #0x10
    b       original_406E5F20


// ---- F5 / F7 ----

// Replaces the first instruction (mov x8,#0x5b14) of the leaf 0x40CB9D8C: w0 = conversion mode, x1 = destination; the stock
// code copies 0x4e bytes from 0x42AA5B14 + mode * 0x4e (0x40CB9DA0 umaddl) by a tail call of 0x4127A900.
// F7: when the mode is 3 (601 -> 2020, the HEVC outputs) or 4 (2020 -> 601, the JPEG thumbnail), f2_sdr_plain and
// [0xA03B93A88] (the source of M+0x294, as f2_snap) is 3 or 0, the mode becomes 0: record 0, no block enabled, the record
// a JPEG request carries.  Every grade.  Only w0 changes; x0..x2 and x30 are kept around f2_sdr_plain (x9..x17 scratch).
    .global f7_rec
f7_rec:
    cmp     w0, #3
    b.eq    1f
    cmp     w0, #4
    b.ne    9f
1:  stp     x0, x1, [sp, #-0x20]!
    stp     x2, x30, [sp, #0x10]
    mov     w10, wzr
    bl      f2_sdr_plain
    cbz     w0, 2f
    movz    x9, #0x3760
    movk    x9, #0x3b9, lsl #16
    movk    x9, #0xa, lsl #32
    ldr     w11, [x9, #0x328]                // 0xA03B93A88 image quality selector
    cmp     w11, #3
    ccmp    w11, #0, #4, ne
    cset    w10, eq
2:  ldp     x2, x30, [sp, #0x10]
    ldp     x0, x1, [sp], #0x20
    cbz     w10, 9f
    mov     w0, wzr                          // record 0
9:  movz    x8, #0x5b14
    b       original_40CB9D90

// ---- settings: the F5 byte follows the photo tone mode 070006A5h (group 6 +0x298; byte = its address - 0x292) ----

// Bank copy: replaces ldp x10,x8,[sp] at 0x410162C4, the type 3/7/9 case of the per-item copy 0x410161F0 (bank select
// 0x410DD1EC and copy-bank 0x410DDA64 go 0x41013A14 -> 0x41013578 -> 0x410135C0, its only caller).  x8 = the source bank's
// item, x10 = the target's, w20 = the item id.  For tone mode the F5 byte is copied too; x11, x12 are dead (tail 0x41016338).
    .global f5_bank
f5_bank:
    ldp     x10, x8, [sp]
    and     w11, w20, #0xffff
    mov     w12, #0x6a5
    cmp     w11, w12
    b.ne    1f
    sub     x11, x8, #0x292
    ldrb    w11, [x11]
    sub     x12, x10, #0x292
    strb    w11, [x12]
1:  b       original_410162C8

// Reset of a stored bank: replaces ldr w8,[x1] at 0x41016940, the type-9 case of the per-item bank reset 0x41016888
// (reached from "Reset photo shooting menu" 0x410D79B0 and the factory reset).  w20 = item id, [sp+8] = the bank's item
// pointer, x1 = ROM default.  For tone mode the F5 byte is set to 0 (JPEG, its stock default); x9 is reloaded at
// 0x41016944, x11, x12 are dead (tail 0x410169B0).
    .global f5_rbank
f5_rbank:
    and     w11, w20, #0xffff
    mov     w12, #0x6a5
    cmp     w11, w12
    b.ne    1f
    ldr     x9, [sp, #8]
    sub     x9, x9, #0x292
    strb    wzr, [x9]
1:  ldr     w8, [x1]
    b       original_41016944

// Reset of the current settings: replaces ldr w9,[x1] at 0x41016804, the type-9 case of the per-item reset 0x41016760
// (x8 = active address, x1 = ROM default; the item id is not kept there).  When x8 is tone mode's active address
// 0xA03D4854C the F5 byte 0xA03D482BA is set to 0.  x10..x12 are dead (tail 0x4101685C).
    .global f5_rcur
f5_rcur:
    movz    x10, #0x854c
    movk    x10, #0x3d4, lsl #16
    movk    x10, #0xa, lsl #32
    cmp     x8, x10
    b.ne    1f
    sub     x10, x8, #0x292
    strb    wzr, [x10]
1:  ldr     w9, [x1]
    b       original_41016808

// ---- format names ----

// Replaces bl 0x403EC398 (settings get) at the eleven call sites in NAME_SITES (build_f5.py), where the value (w0 = the tone
// mode 070006A5h, or the derived 040021E7h at the two small badges 404CD90C / 404CDA34) only decides whether the screen says
// JPEG or HEIF (icons, labels, help texts; static classification in tone_readers/README.md).  Returns w0 = the value, but 1
// (the HEIF wording of HLG) when it is 0 (SDR) and the F5 byte 0xA03D482BA is 1.  Only x0 and NZCV are changed (what the stock getter call already does); x30 is kept.  All other
// readers of 070006A5h, HLG-only displays, availability tests and the tone page itself, keep the real value.
    .global f5_name_get
f5_name_get:
    str     x30, [sp, #-16]!
    bl      original_403EC398
    ldr     x30, [sp], #16
    cbnz    w0, 1f
    movz    x0, #0x82ba
    movk    x0, #0x3d4, lsl #16
    movk    x0, #0xa, lsl #32                // F5 byte 0xA03D482BA (group 6 +6)
    ldrb    w0, [x0]
    cmp     w0, #1
    cset    w0, eq
1:  ret

// ---- menu ----

// w0 = the F5 byte (0 or 1; anything else reads as 0).  Uses x9 only.
f5_choice:
    movz    x9, #0x82ba
    movk    x9, #0x3d4, lsl #16
    movk    x9, #0xa, lsl #32
    ldrb    w0, [x9]
    cmp     w0, #1
    csel    w0, w0, wzr, eq
    ret

// Value refresh callback (slot 4) of the Tone mode state 2Bh, which has none in stock (x0 = state): writes "JPEG" or
// "HEIF" into text slot F5_SLOT and binds the value child 4BA7h of the SDR row (item 2D7Ah) to it, the way the stock
// file-type page refresh 4056CD84 does for its arrow rows (4050A6F0, 403F62D8, 403F1A44, 403F2920(text, slot, 46h),
// 403F61EC(node, 3, slot)).
    .global f5_tone_refresh
f5_tone_refresh:
    stp     x29, x30, [sp, #-32]!
    mov     x29, sp
    stp     x19, x20, [sp, #16]
    mov     x19, x0
    bl      f5_footer
    mov     x0, x19
    mov     w1, #0x2d7a
    mov     w2, #0x4ba7
    bl      original_4050A6F0
    cbz     x0, 9f
    mov     x20, x0
    bl      original_403F62D8
    mov     x0, x20
    bl      original_403F1A44
    bl      f5_choice
    adr     x9, f5_texts
    add     x0, x9, w0, uxtw #3
    mov     w1, #F5_SLOT
    mov     w2, #0x46
    bl      original_403F2920
    mov     x0, x20
    mov     w1, #3
    mov     w2, #F5_SLOT
    bl      original_403F61EC
9:  ldp     x19, x20, [sp, #16]
    ldp     x29, x30, [sp], #32
    ret

// Entry callback of the sub-page state (x0 = state): cursor and mark on the stored choice, as HB1's tier_entry_hook
// (stock N-RAW quality entry 4056C8F8 with our item ids).
    .global f5_sub_entry
f5_sub_entry:
    stp     x19, x30, [sp, #-32]!
    str     x20, [sp, #16]
    mov     x19, x0
    bl      f5_choice
    adr     x9, f5_items
    ldrh    w20, [x9, w0, uxtw #1]
    bl      original_403AE0F8               // entry guard (1 = keep the cursor)
    cmp     w0, #1
    b.eq    1f
    mov     x0, x19
    mov     w1, w20
    bl      original_403B0048
1:  mov     x0, x19
    mov     w1, w20
    mov     w2, #1
    ldr     x20, [sp, #16]
    ldp     x19, x30, [sp], #32
    b       original_403B00B8

// OK action of the two sub-page rows (x0 = context; [x0] = state, cursor row = [state+0x58] + [state+0x32], as HB1's
// tier_ok_hook): stores the row (0 JPEG, 1 HEIF) in the F5 byte, then sets the photo tone mode 070006A5h to 0 (SDR)
// through the stock setter, as the stock SDR action 405E6A20 does; the row's stock transition follows.
    .global f5_sub_ok
f5_sub_ok:
    ldr     x9, [x0]
    ldrh    w11, [x9, #0x58]
    ldrh    w10, [x9, #0x32]
    add     w10, w10, w11
    cmp     w10, #1
    b.hi    1f
    stp     x10, x30, [sp, #-0x10]!
    cbz     w10, 2f
    // The factory tone-mode change already clears HDR/multiple exposure.
    // Apply the same rule when changing only the new format sub-option.
    // (F7: the interval automatic movie 0600053Dh is left as set: it is allowed with SDR HEIF.)
    mov     w0, #0x685
    movk    w0, #0x700, lsl #16
    mov     w1, wzr
    bl      original_403EC39C
    mov     w0, #0x50e
    movk    w0, #0x700, lsl #16
    mov     w1, wzr
    bl      original_403EC39C
2:  ldp     x10, x30, [sp], #0x10
    movz    x9, #0x82ba
    movk    x9, #0x3d4, lsl #16
    movk    x9, #0xa, lsl #32
    strb    w10, [x9]
    mov     w0, #0x6a5
    movk    w0, #0x700, lsl #16
    mov     w1, wzr
    b       original_403EC39C
1:  ret

// Selected SDR HEIF, even while menu state makes the capture predicate false.
// Scratch x9 only; calls f5_choice and must therefore preserve LR.
f5_selected:
    str     x30, [sp, #-16]!
    bl      f5_choice
    ldr     x30, [sp], #16
    cbz     w0, 1f
    movz    x9, #0x8570
    movk    x9, #0x3b9, lsl #16
    movk    x9, #0xa, lsl #32
    ldr     w9, [x9, #0xa8]
    cmp     w9, #0
    cset    w0, eq
1:  ret

// Condition-set evaluator 403A036C (w0 = set, x1 = context): with SDR HEIF selected, sets 39h (HDR) and 44h (multiple
// exposure) and (F7) 4Dh (the interval movie page's "Video file type" row 2D40h, whose only leaf is 403A1360 tone == 1:
// gray and fixed as under HLG) and (F8) 53h (the photo-menu time-lapse page's "Video file type" row 2D5Fh, same single
// leaf) report unavailable; the claimed-leaf word 0xA0282C1E0 gets 138h (no factory leaf).
    .global f5_unavailable
f5_unavailable:
    cmp     w0, #0x39
    b.eq    1f
    cmp     w0, #0x4d
    b.eq    1f
    cmp     w0, #0x53
    b.eq    1f
    cmp     w0, #0x44
    b.ne    8f
1:  stp     x0, x30, [sp, #-16]!
    bl      f5_selected
    mov     w9, w0
    ldp     x0, x30, [sp], #16
    cbz     w9, 8f
    movz    x9, #0xc1e0
    movk    x9, #0x282, lsl #16
    movk    x9, #0xa, lsl #32
    mov     w0, #0x138
    str     w0, [x9]                       // no stock condition leaf claimed
    mov     w0, #1
    ret
8:  stp     x25, x24, [sp, #-0x40]!
    b       original_403A0370

    .global f5_set
f5_set:
    mov     w9, #0x685
    movk    w9, #0x700, lsl #16
    cmp     w0, w9
    b.eq    1f
    mov     w9, #0x50e
    movk    w9, #0x700, lsl #16
    cmp     w0, w9
    b.ne    8f                             // F7: 0600053Dh (interval auto movie) is no longer refused
1:  cbz     w1, 8f
    stp     x0, x30, [sp, #-16]!
    bl      f5_selected
    mov     w9, w0
    ldp     x0, x30, [sp], #16
    cbz     w9, 8f
    mov     w0, wzr                        // original setter returns success bit
    ret
8:  b       original_410D61D0

// Bottom bar of the Tone mode page (factory video file-type page rule 4056CB2C / 4056D078): the two button groups share one
// rectangle; the row whose item is the SDR row (2D7Ah) shows group 753h ("File format" + OK, f7_group), every other row the
// factory OK group (390h).
// f5_footer: current row ([state+0x58] + [state+0x32]).  f6_footer_row: x0 = state, w1 = row.  Each control is looked
// up in the page's control list (state + 0x18); nothing is changed when one of the three is missing (as 4056D078).
    .global f5_footer
f5_footer:
    ldrh    w9, [x0, #0x58]
    ldrh    w10, [x0, #0x32]
    add     w1, w9, w10
f6_footer_row:
    stp     x19, x20, [sp, #-0x40]!
    stp     x21, x22, [sp, #0x10]
    stp     x23, x30, [sp, #0x20]
    mov     x19, x0
    and     w9, w1, #0xffff
    ldr     x10, [x19, #0x50]                // page record
    ldrh    w11, [x10, #0x20]                // row count
    mov     w21, wzr
    cmp     w9, w11
    b.hs    1f
    ldr     x10, [x10, #0x10]                // rows, 0x2c bytes each
    mov     w11, #0x2c
    umaddl  x10, w9, w11, x10
    ldr     w10, [x10, #0x18]                // row item id
    mov     w11, #0x2d7a
    cmp     w10, w11
    cset    w21, eq
1:  mov     w0, #0x568
    add     x1, x19, #0x18
    bl      original_4039E810
    mov     x20, x0
    mov     w0, #0x753
    add     x1, x19, #0x18
    bl      original_4039E810
    mov     x22, x0
    mov     w0, #0x390
    add     x1, x19, #0x18
    bl      original_4039E810
    mov     x23, x0
    cbz     x20, 9f
    cbz     x22, 9f
    cbz     x23, 9f
    mov     x0, x22
    mov     x1, x20
    mov     w2, w21
    bl      original_4051253C
    mov     x0, x23
    mov     x1, x20
    eor     w2, w21, #1                      // as the factory file-type page: one of the two groups
    bl      original_4051253C
9:  ldp     x23, x30, [sp, #0x20]
    ldp     x21, x22, [sp, #0x10]
    ldp     x19, x20, [sp], #0x40
    ret

// Tone mode page cursor moves (transition events 283h/29Dh up, 284h/29Eh down; both row tables).  x0 = event context
// ([x0] = state, [x0+8] = event).  As the factory file-type action 4056CFE0: the bottom bar is set for the row the cursor
// is about to reach (factory step 403AF8BC with the same arguments as 4056CB2C), then the factory tone action 405DB2E4
// moves the cursor and redraws the help text.
    .global f6_move
f6_move:
    stp     x19, x30, [sp, #-0x10]!
    mov     x19, x0
    ldr     w8, [x19, #8]
    mov     w4, #0xffff
    cmp     w8, #0x283
    b.eq    1f
    cmp     w8, #0x29d
    b.eq    1f
    mov     w4, #1
    cmp     w8, #0x284
    b.eq    1f
    cmp     w8, #0x29e
    b.ne    2f
1:  ldr     x0, [x19]
    ldr     x9, [x0, #0x50]
    ldrh    w2, [x9, #0x20]
    ldrh    w10, [x0, #0x58]
    ldrh    w11, [x0, #0x32]
    add     w3, w11, w10
    mov     w1, #2
    bl      original_403AF8BC
    mov     w1, w0
    ldr     x0, [x19]
    bl      f6_footer_row
2:  mov     x0, x19
    ldp     x19, x30, [sp], #0x10
    b       original_405DB2E4

// Tone mode page event 303h (factory 405DB360 redraws the help text; the file-type page's 4056D078 also sets its bottom
// bar there): bottom bar for the current row, then the factory action.
    .global f6_touch
f6_touch:
    stp     x19, x30, [sp, #-0x10]!
    mov     x19, x0
    ldr     x0, [x19]
    bl      f5_footer
    mov     x0, x19
    ldp     x19, x30, [sp], #0x10
    b       original_405DB360

// Photo shooting menu value of the Tone mode row (refresh 405D9808): replaces add x0,sp,#0x8 at 405D9B08, where [sp+8]
// holds the factory 4-byte text "SDR" or "HLG" and the factory 403F2920(x0, 49h, 4) follows.  x0 = "SDR-J" or "SDR-H"
// (F5 byte) for "SDR"; the factory buffer otherwise.  Uses x9, x10 (dead: the next call clobbers them); x30 is not live
// here (bl 403F2920 follows).  The text is copied by 403F2920 into its slot.
    .global f6_tone_text
f6_tone_text:
    add     x0, sp, #0x8
    ldr     w9, [x0]
    movz    w10, #0x4453
    movk    w10, #0x52, lsl #16              // "SDR\0"
    cmp     w9, w10
    b.ne    1f
    movz    x9, #0x82ba
    movk    x9, #0x3d4, lsl #16
    movk    x9, #0xa, lsl #32
    ldrb    w9, [x9]                         // F5 byte 0xA03D482BA
    adr     x0, f6_sdr_j
    adr     x10, f6_sdr_h
    cmp     w9, #1
    csel    x0, x10, x0, eq
1:  ret

// Capture develop call 40EA7ED0 (bl 0x410539B8 in 40EA7D6C; x0 = args, [x0] = R, [x0+8] = develop input, x30 saved by
// the caller).  The parameter packer 411135F4 copies input +0xBC into the capture parameter block +0x31 at 4111381C (the
// curve family: 0 SDR, 2 the family a HIF capture gets); the tone-table copy 4111A160 and the Q12/other tables follow it.
// For an SDR HEIF capture (M = [R+0x790]: M+0x2fc == 1, M+0x2570 == 0, M+0x2ce == 0, M+0x294 in {0,3}, f2_sdr_plain) whose
// input +0xBC is 2, the word is 0 for the duration of this synchronous call and the original word is put back after it,
// so the develop parameters are the JPEG ones and nothing outside the call sees a changed input.  w0 of 410539B8 kept.
    .global f6_dev
f6_dev:
    sub     sp, sp, #0x40
    stp     x0, x1, [sp]
    stp     x19, x20, [sp, #0x10]
    stp     x21, x30, [sp, #0x20]
    str     xzr, [sp, #0x30]
    ldr     x9, [x0]
    cbz     x9, 1f
    ldr     x9, [x9, #0x790]
    cbz     x9, 1f
    ldr     w10, [x9, #0x2fc]
    cmp     w10, #1
    b.ne    1f
    ldr     w10, [x9, #0x2570]
    cbnz    w10, 1f
    ldrb    w10, [x9, #0x2ce]
    cbnz    w10, 1f
    ldr     w10, [x9, #0x294]
    cmp     w10, #0
    ccmp    w10, #3, #4, ne
    b.ne    1f
    ldr     x20, [x0, #8]
    cbz     x20, 1f
    ldr     w21, [x20, #0xbc]
    cmp     w21, #2
    b.ne    1f
    bl      f2_sdr_plain
    cbz     w0, 1f
    str     wzr, [x20, #0xbc]
    str     x20, [sp, #0x30]
    str     w21, [sp, #0x38]
1:  ldp     x0, x1, [sp]
    bl      original_410539B8
    ldr     x9, [sp, #0x30]
    cbz     x9, 2f
    ldr     w10, [sp, #0x38]
    str     w10, [x9, #0xbc]
2:  ldp     x19, x20, [sp, #0x10]
    ldp     x21, x30, [sp, #0x20]
    add     sp, sp, #0x40
    ret

// Offset +4 remains SDR. Offset +5 is the actual M format flag, as in stock;
// RAW+HIF also carries that snapshot flag in stock. Do not infer file type
// from 005B (NEF shares it), or from the current menu on a cold read.
    .global f5_format59
f5_format59:
    ldr     x8, [x19, #0x10]
    ldr     w8, [x8, #0x2fc]
    cmp     w8, #1
    b.ne    1f
    mov     w8, #3
    b       2f
1:  mov     w8, #1
2:
    strb    w8, [x20, #5]
    ret

// SDK descriptor: type, padding, uint64 length, const void *profile.
// Profile bytes are immutable factory ROM; serializer consumes them later.
    .global f5_colr
f5_colr:
    stp     x0, x1, [sp, #-0x30]!
    stp     x2, x30, [sp, #0x10]
    bl      f2_sdr_plain
    cbz     w0, 1f
    movz    x9, #0x3818
    movk    x9, #0x3b9, lsl #16
    movk    x9, #0xa, lsl #32
    ldr     w9, [x9]
    cmp     w9, #1
    b.ne    1f
    ldr     x2, [sp, #0x10]
    mov     w9, #2
    str     w9, [x2]
    mov     x9, #492
    str     x9, [x2, #8]
    movz    x9, #0xa638
    movk    x9, #0x440c, lsl #16
    str     x9, [x2, #0x10]
1:  ldp     x2, x30, [sp, #0x10]
    ldp     x0, x1, [sp], #0x30
    b       original_40CD343C


// ---- F7 ----

// Replaces bl 0x403EB6A8 at 0x403D950C in the control builder 0x403D94DC (x0 = event-key table 0x42AD0110, w1 = 164 entries,
// w2 = the control's key [x19+8], w3 = -1): the index of the first entry whose key is w2, else -1.  The Tone page footer
// button 753h carries the new string 3237 (F6), which is not a key: it then gets index 140 (key 7CBh, the factory "Tone mode"
// footer text, event 286h = RIGHT, which the SDR row already takes into the JPEG / HEIF sub-page).  Every other key keeps
// the factory result.  x0..x3 of the lookup, then w0 only; x8/x9 are dead after the call (0x403D9518, 0x403D9524).
    .global f7_key
f7_key:
    stp     x2, x30, [sp, #-0x10]!
    bl      original_403EB6A8
    ldp     x2, x30, [sp], #0x10
    cmn     w0, #1
    b.ne    1f
    mov     w9, #3237
    cmp     w2, w9
    b.ne    1f
    mov     w0, #140
1:  ret

// Replaces bl 0x40CD3A60 (write the ipma box) at 0x40CD3E84: x0 = writer, x1 = ipma object (+0x38 entry count, entries of
// 0x28 bytes from +0x3C, id at +0, self-contained; 0x40CD39B8 appends in first-use order 8192, 8193, 8194, 4096, tiles).
// For an SDR HEIF (f2_sdr_plain) the entries are stably sorted by rank (tile ids below 4096: 0, the grid 4096: 1, the rest:
// 2) before the factory writer runs: tiles, grid, then 8192, 8193, 8194 in their order (hif_label_test M3).  In place,
// count unchanged; sorting an already sorted array changes nothing.  x0, x1 kept; x2..x17 scratch (a call site).
    .global f7_ipma
f7_ipma:
    stp     x0, x1, [sp, #-0x40]!
    str     x30, [sp, #0x10]
    bl      f2_sdr_plain
    mov     w9, w0
    ldr     x30, [sp, #0x10]
    ldp     x0, x1, [sp]
    cbz     w9, 9f
    ldr     w3, [x1, #0x38]                  // n
    cmp     w3, #32
    b.hi    9f                               // never above the factory capacity; leave untouched
    add     x2, x1, #0x3c                    // entries
    add     x7, sp, #0x18                    // 0x28-byte holding slot
    mov     w4, #1                           // i
1:  cmp     w4, w3
    b.hs    9f
    mov     w10, #0x28
    umaddl  x8, w4, w10, x2                  // &e[i]
    ldr     w11, [x8]
    cmp     w11, #1, lsl #12
    cset    w5, hs
    cinc    w5, w5, hi                       // rank(e[i])
    mov     w6, w4                           // j
2:  cbz     w6, 3f
    sub     w12, w6, #1
    umaddl  x9, w12, w10, x2
    ldr     w11, [x9]
    cmp     w11, #1, lsl #12
    cset    w13, hs
    cinc    w13, w13, hi                     // rank(e[j-1])
    cmp     w13, w5
    b.ls    3f
    mov     w6, w12
    b       2b
3:  cmp     w6, w4
    b.eq    6f
    ldp     w14, w15, [x8]                   // hold e[i]
    stp     w14, w15, [x7]
    ldp     w14, w15, [x8, #8]
    stp     w14, w15, [x7, #8]
    ldp     w14, w15, [x8, #16]
    stp     w14, w15, [x7, #16]
    ldp     w14, w15, [x8, #24]
    stp     w14, w15, [x7, #24]
    ldp     w14, w15, [x8, #32]
    stp     w14, w15, [x7, #32]
    mov     w12, w4                          // k = i .. j+1: e[k] = e[k-1]
4:  cmp     w12, w6
    b.ls    5f
    umaddl  x16, w12, w10, x2
    sub     x17, x16, #0x28
    ldp     w14, w15, [x17]
    stp     w14, w15, [x16]
    ldp     w14, w15, [x17, #8]
    stp     w14, w15, [x16, #8]
    ldp     w14, w15, [x17, #16]
    stp     w14, w15, [x16, #16]
    ldp     w14, w15, [x17, #24]
    stp     w14, w15, [x16, #24]
    ldp     w14, w15, [x17, #32]
    stp     w14, w15, [x16, #32]
    sub     w12, w12, #1
    b       4b
5:  umaddl  x16, w6, w10, x2                 // e[j] = held
    ldp     w14, w15, [x7]
    stp     w14, w15, [x16]
    ldp     w14, w15, [x7, #8]
    stp     w14, w15, [x16, #8]
    ldp     w14, w15, [x7, #16]
    stp     w14, w15, [x16, #16]
    ldp     w14, w15, [x7, #24]
    stp     w14, w15, [x16, #24]
    ldp     w14, w15, [x7, #32]
    stp     w14, w15, [x16, #32]
6:  add     w4, w4, #1
    b       1b
9:  ldp     x0, x1, [sp], #0x40
    b       original_40CD3A60

// Replaces bl 0x40ED4880 at 0x40ED04A8 (in 40ED0310) and 0x40ED1590 (in 40ED0E70).  40ED4880(w0 default, w1 derived
// 40000100h, w2 0600053Dh, w3 06000559h, w4 040006AEh, w5 0600055Ch, w6 040006AFh, w7 tone) is a leaf: for the interval
// automatic movie (w1 bit 7 and w2 == 1) it returns w4 when w7 == 1 (HLG) else w3; for the photo-menu time-lapse movie
// (w1 & 60h) w6 when w7 == 1 else w5; otherwise w0, w7 unused.  F8: with SDR HEIF selected (f5_selected) w7 is passed as 1
// whenever w1 & E0h (both movie branches), so both movies get the HLG family (H.265 10-bit) like their forced HIF frames.
// x0..x7 are kept for the leaf; x9 scratch.
    .global f8_ftype
f8_ftype:
    tst     w1, #0xe0
    b.eq    9f
    sub     sp, sp, #0x50
    stp     x0, x1, [sp]
    stp     x2, x3, [sp, #0x10]
    stp     x4, x5, [sp, #0x20]
    stp     x6, x7, [sp, #0x30]
    str     x30, [sp, #0x40]
    bl      f5_selected
    mov     w9, w0
    ldp     x0, x1, [sp]
    ldp     x2, x3, [sp, #0x10]
    ldp     x4, x5, [sp, #0x20]
    ldp     x6, x7, [sp, #0x30]
    ldr     x30, [sp, #0x40]
    add     sp, sp, #0x50
    cbz     w9, 9f
    mov     w7, #1
9:  b       original_40ED4880

// Replaces ldr w8,[sp,#0x1ec] at the three mode-2 (interval automatic movie) branches of the movie service 40722ED0
// (0x40722F9C, 0x40723198, 0x407232E8) and (F8) the three mode-1 (photo-menu time-lapse movie) branches (0x40722FC0,
// 0x407231B8, 0x407232B4, which read 040006AFh / 0600055Ch and the HLG frame sizes the same way; sp = its frame, 0x1EC = the photo tone in the stack copy of the 4072417C cache;
// cmp w8,#1 follows, so NZCV is dead; 40722ED0 saved x30 in its prologue).  w8 = the stored tone, but 1 when it is 0 and
// SDR HEIF is selected: file type and frame size come from the HLG family (040006AEh, 06000565h/66h).  The colour-field
// load 0x407233E4 (table 440D120Ch[tone], modes 1 and 2) is not hooked, so the movie keeps the SDR colour field.  Only w8,
// x30 and NZCV change.
    .global f7_m2tone
f7_m2tone:
    ldr     w8, [sp, #0x1ec]                 // the factory load, before anything is pushed
    cbnz    w8, 1f
    stp     x0, x9, [sp, #-0x20]!
    str     x30, [sp, #0x10]
    bl      f5_selected
    mov     w8, w0
    ldr     x30, [sp, #0x10]
    ldp     x0, x9, [sp], #0x20
1:  ret

// F8.  Replaces ldr w8,[x8] at 0x40723528 in the movie service 40722ED0: x8 = sp + 7Ch / 80h / 84h for mode w20 = 0 / 1 / 2,
// the cached 02001245h / 02000544h / 02000545h (4072417C); 0x4072352C..0x40723540 store out+0x2C = 1 when it is 1, else 0.
// out+0x2C is the descriptor bit-depth index (406D2D18: table 440C7CF4 = 8, 10, 12, 12 -> NCTG 25h).  With SDR HEIF F7
// gave the interval movie file type 3 (H.265 10-bit) but the cached value stayed 0, so the Main 10 file said 8 bits (F7
// body: NCTG 25h = 8, in-camera playback striped).  How the factory sets 02000545h under HLG is not traced (menu actions
// 405ECD2C / 405ECD5C store 0 / 1 with 0600053Dh = 1); F8 ties the flag to the file type instead.  w8 = the cached value,
// but 1 when it is 0, w20 is 1 or 2, out+0x20 (x19) == 3 and SDR HEIF is selected.  Only w8, w9, x30 and NZCV change
// (w8 and the flags are set again before use, w9 is dead, 40722ED0 saved x30); x0 is kept.
    .global f8_depth
f8_depth:
    ldr     w8, [x8]                         // the factory load
    cbnz    w8, 1f
    sub     w9, w20, #1
    cmp     w9, #1
    b.hi    1f                               // mode 0 (ordinary movie) untouched
    ldr     w9, [x19, #0x20]
    cmp     w9, #3
    b.ne    1f                               // not H.265 10-bit
    stp     x0, x30, [sp, #-0x10]!
    bl      f5_selected
    mov     w8, w0
    ldp     x0, x30, [sp], #0x10
1:  ret


// Adobe RGB JPEG thumbnail, round 9 of hif_label_test_20261117 (V2): Windows 11 Photos opens an ICC-colr HIF only when no
// JPEG item is a 'thmb' of the primary; V2 (8194 kept, its thmb reference dropped) opens, V1 (hidden) and V3 (moved last)
// do not.  Replaces bl 0x40CD44C4 (iref add: x0 iref, x1 "thmb", w2 from = the 8194 id [sp+0xEC], x3 &to, w4 1) at
// 0x40CCFBB8, the block that only runs for 8194 (0x40CCFB88/0x40CCFB8C skip it when the id is 0).  With SDR HEIF
// (f2_sdr_plain) and Adobe RGB (cached colour space 0xA03B93818 == 1, as f5_colr) the reference is not added and w0 = 0
// (no error bit for orr w21,w0,w21); otherwise the factory call.  The item, its data, ispe and ipma stay.
// F8 (round 9 V4; F7 body: macOS Preview listed the V2 thumbnail as a second image): in that case the item is also marked
// hidden with the factory 0x40CD2188(iinf = x19 + 0x8D8, id, 1), the call the builder makes for Exif (0x40CCF4CC), XMP
// (0x40CCF584) and the tiles (0x40CCFAA8); it sets infe flags bit 0 (entry +0x33, 0x40CD0554).  Its result (0, or 8 when
// the id is not in iinf) is returned for orr w21,w0,w21 like theirs.  x19 is the builder's context throughout 0x40CCF2CC.
    .global f8_thmb
f8_thmb:
    stp     x0, x1, [sp, #-0x30]!
    stp     x2, x3, [sp, #0x10]
    stp     x4, x30, [sp, #0x20]
    bl      f2_sdr_plain
    cbz     w0, 8f
    movz    x9, #0x3818
    movk    x9, #0x3b9, lsl #16
    movk    x9, #0xa, lsl #32
    ldr     w9, [x9]
    cmp     w9, #1
    b.ne    8f
    add     x0, x19, #0x8d8                  // iinf object, as 0x40CCF6BC / 0x40CCF530
    ldr     w1, [sp, #0x10]                  // the 8194 id (w2 at the site)
    mov     w2, #1
    bl      original_40CD2188
    ldp     x4, x30, [sp, #0x20]
    add     sp, sp, #0x30
    ret
8:  ldp     x2, x3, [sp, #0x10]
    ldp     x4, x30, [sp, #0x20]
    ldp     x0, x1, [sp], #0x30
    b       original_40CD44C4

// The camera reads its 160x120 JPEG thumbnail (read role 4, 0x40CCE8F4) only from ctx+0x3D38, which the header parser
// 0x40CCE4AC fills from the primary's 'thmb' references (0x40CCE6D8 .. 0x40CCE80C, by ispe size).  A V2 file has no such
// reference, so the slot would stay 0 and the three kind-2 readers would fail (f7_pbgate_20261119/thumb-slots.json).
// Replaces mov x22,#0xd70d at 0x40CCE6E0, the join after the thmb loop (x19 = ctx; x0..x18 are set again before their next
// use; 0x40CCE4AC saved x30): when +0x3D38 is still 0, the item info of id 8194 (the camera's JPEG thumbnail id) is read
// with the parser's own 0x40CCEDB8 and, if its ispe is small by the loop's own rule (width < 0xA1 or height <= 0xA0, both
// non-zero), the slot gets 8194.  Files that already have a small thumbnail, or no item 8194, are unchanged.
    .global f7_small
f7_small:
    ldr     w9, [x19, #0x3d38]
    cbnz    w9, 9f
    sub     sp, sp, #0x50
    str     x30, [sp, #0x40]
    stp     xzr, xzr, [sp]
    stp     xzr, xzr, [sp, #0x10]
    stp     xzr, xzr, [sp, #0x20]
    stp     xzr, xzr, [sp, #0x30]
    mov     x0, x19
    mov     w1, #8194
    mov     x2, sp
    bl      original_40CCEDB8
    ldp     w8, w9, [sp, #8]                 // width, height (as [sp+0xA0], [sp+0xA4] of the loop)
    ldr     x30, [sp, #0x40]
    add     sp, sp, #0x50
    cbz     w8, 9f
    cbz     w9, 9f
    cmp     w8, #0xa1
    b.lo    1f
    cmp     w9, #0xa0
    b.hi    9f
1:  mov     w8, #8194
    str     w8, [x19, #0x3d38]
9:  movz    x22, #0xd70d
    ret

// F8 movie-frame colour (F7 body: the interval movie frames were BT.601-coded while the movie says 709 (VUI 1/1/1, NCTG 26h
// 1); hue off 3.96 deg when decoded by the label).  The two movie request builders 0x40EAD4B0 (interval automatic movie,
// sequence B) and 0x40EACFC8 (photo-menu time-lapse, sequence A) set the node-5 mode of their only frame output R+0x6F8 to
// (M+0x2FC == 1) ? 3 : 1 with cmp w8,#1 / csinc w8,w25,wzr,eq (w25 = 3): factory SDR movies take mode 1 (601 -> 709), HLG
// mode 3 (601 -> 2020).  With F7/F8 the SDR HEIF frames have M+0x2FC = 1 (f2_snap), so they took mode 3, which f7_rec turns
// into record 0 (601).  Replaces the csinc at 0x40EAD6E0 (B) and 0x40EAD184 (A): w8 = 1 when ne (stock) or when eq and
// f2_sdr_plain (only F-series forcing gives M+0x2FC = 1 there), else 3.  Every register but w8 and x30 is kept (x0..x2 are
// the arguments of the next call at both sites); NZCV is dead after the site.
    .global f8_mvmode
f8_mvmode:
    b.ne    1f
    sub     sp, sp, #0x50
    stp     x0, x9, [sp]
    stp     x11, x12, [sp, #0x10]
    stp     x13, x14, [sp, #0x20]
    stp     x15, x16, [sp, #0x30]
    stp     x17, x30, [sp, #0x40]
    bl      f2_sdr_plain
    mov     w8, #3
    cbz     w0, 2f
    mov     w8, #1
2:  ldp     x0, x9, [sp]
    ldp     x11, x12, [sp, #0x10]
    ldp     x13, x14, [sp, #0x20]
    ldp     x15, x16, [sp, #0x30]
    ldp     x17, x30, [sp, #0x40]
    add     sp, sp, #0x50
    ret
1:  mov     w8, #1
    ret

// F8 playback colour (F7 body: Adobe RGB HIF looked paler than the Adobe RGB JPEG in the camera, sRGB HIF = sRGB JPEG).
// The playback request builders give the display-conversion descriptor (407D2EA8, [sp+0x4EC] -> +0x50) an input colour: for
// ordinary files the file record's colour bits (406BC444; from MakerNote 001E via 406C2B68 / 440C7660: sRGB 1, Adobe RGB 2,
// BT.2100 3) mapped Adobe -> 1, BT.2100 -> 2, else 0 (407D2D48 does this by file id); for request kinds 5/7 with the HEIF
// class bit (407D2CF4) they store 3, which the selector 407C1194 converts like sRGB (records 4 / 2), so an Adobe RGB HIF
// misses the Adobe records 5 / 3 that an Adobe RGB JPEG gets.  Replaces orr w8,wzr,#3 at the three HEIF stores 0x407C66D4,
// 0x407C8640 (file id [x20]) and 0x407C93C8 (file id [[x26]]): w8 = 1 when 407D2D48(id) == 1 (Adobe RGB), else 3.  Factory
// HLG HIF (001E 4 -> 2) and sRGB HIF keep 3.  Each site follows a bl 0x407D2CF4 and joins a str w8,[sp,#0x4EC] / bl path,
// so x0..x18, x30 (the enclosing functions saved it) and NZCV are dead; x19..x29 are kept.
    .global f8_pbcs_x20
f8_pbcs_x20:
    ldr     w0, [x20]
    b       1f
    .global f8_pbcs_x26
f8_pbcs_x26:
    ldr     x8, [x26]
    ldr     w0, [x8]
1:  str     x30, [sp, #-16]!
    bl      original_407D2D48
    ldr     x30, [sp], #16
    cmp     w0, #1
    mov     w8, #3
    csinc   w8, w8, wzr, ne                  // Adobe RGB -> 1, else 3
    ret

// Replaces mov x8,#0x1c58 at 0x40388508, the factory leaf "button group list of id w0" (table 0x42AC1C58 of 198 pointers
// into init data; each list is u32 string ids ending with FFFFh; read by the layout builder 403A682C for type-0Bh records).
// Id 198, one past the factory table, returns f7_group_list; every factory id goes to the factory leaf unchanged.  x0 and
// x8 as the factory leaf (x8 scratch); the flags are clobbered (the callers reach the leaf with bl).
    .global f7_group
f7_group:
    cmp     w0, #198
    b.ne    1f
    adr     x0, f7_group_list
    ret
1:  movz    x8, #0x1c58
    b       original_4038850C

    .balign 4
f7_group_list:                               // the Tone page footer: string 3237 ("<glyph> File format"), ABDh ("OK")
    .word   3237, 0xabd, 0xffff
    .balign 4
f5_items:                                    // sub-page item ids, choice 0 / 1
    .hword  F5_JPEG_ITEM, F5_HEIF_ITEM
    .balign 8
f5_texts:                                    // 8 bytes each, choice 0 / 1
    .ascii  "JPEG\0\0\0\0"
    .ascii  "HEIF\0\0\0\0"
f6_sdr_j:
    .asciz  "SDR-J"
f6_sdr_h:
    .asciz  "SDR-H"

// 0x78-byte copy of the stock template 0x41F1DD90 with +0x38..+0x3a = 1, 13, 6 (filled by build_f5.py); F2's label
    .balign 8
f5_adobe_template:
    .space  0x78
f2_template:
    .space  0x78
