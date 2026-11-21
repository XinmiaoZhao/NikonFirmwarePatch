/* E4 = E3 + 4.1K 3:2 at 29.97/25/23.976p records the full 8280x5520 readout scaled 2:1 in the front end, as stock
 * 4.1K 16:9 at those rates does with 8280x4688; proxy SPS for 50..120p; the file-type tone text follows log-colour
 * (open-gate line, 2026-11-14; analysis repository research/open_gate_probe_20261018/e4_20261114).  New code only
 * follows E3; every E1..E3 address stays (E3's ft_refresh3_hook reaches og_tone_text4 through two same-size bl
 * retargets).
 *
 * Oversample state: N-RAW 3:2 (flag 1, stored type 6, stored size 4) at rate codes 4..6.  Standby is E3's (readout 7,
 * driver 14, plan 11 = 4140x2756); the recording request takes the 8.3K 3:2 sensor path (readout 4 with the 5520-row
 * tables, driver 2) and the stock plan-13 low-rate front end, whose records and parameter template are plan 12's
 * (8.3K), with the secondary scaler state set to 5520 rows in, 2760 out.  Output, metadata, proxy and playback are
 * E3's 4.1K 3:2 (4140x2756 coded, 4128x2752 active).
 *   h14_readout_e4_hook      410666F8  recording request (byte +24h = 0) at rates 4..6 -> stock selection (readout 4
 *                            for 4.1K N-RAW); every other request -> E1's h14_readout_hook
 *   configuration_e4_hook    40F7938C  valid 4.1K 3:2 video snapshot at rates 4..6: the readout-4 tables 5520 and
 *                            active 5504 exactly as configuration_hook writes them for 8.3K 3:2, request 1, standby
 *                            tables 2756/2752 as configuration_e1_hook; everything else -> configuration_e1_hook
 *   driver_class2_e4_hook    4117190C  class-2 branch of the driver selector: readout 4 with readout-4 height 5520 and
 *                            flag/type/size of 4.1K 3:2 -> driver 2 (stock: A02AAA650[0] = 9)
 *   og_front_e4_hook         41062148  plan 13, area 4, rates 4..6 (E2's og32_low_plan test): secondary state
 *                            A0297A9DC +2/+19Eh = 5520, +1F4h = 2760 and the 8280x5520 block A02A97490 (stock plan
 *                            15, D-series plan 12 in 3:2); otherwise the stock values 4688/4688/2344 are written back
 *                            and the stock path (block A02A97450) runs
 *   h14_coordinates_e4_hook  41065194  E3's hook, then for plan 13 at rates 4..6 in 3:2: physical 8280x5520, scaled
 *                            plane 4140x2760, active 4128x2752 at (6, 4), +5Eh = 0 as stock plan 13
 *   raw_source_e4_hook       41066978  RAW source query, readout 4 in the oversample state: 4140x2760 (stock size 4:
 *                            4140x2344)
 *   h14_inner_e4_hook        41066A10  readout 4 in the oversample state: 4140x2756; else E2's h14_inner_hook
 *   h14_active_e4_hook       41066AA8  readout 4 in the oversample state: 4128x2752; else E2's h14_active_hook
 *   E2's plan-13 rate forks 41062698 41062BB8 41062CD8 41062FD0 410658F8 410B659C are not installed (stock bytes).
 * Proxy SPS: proxy_sps_e4_hook (40CED8EC) maps the stock 59.94p/50p SPS to D3's corrected SPS (they differ from the
 * 29.97p one only in VUI timing) and the stock 119.88p/100p SPS (level 5.1, one reference frame, no B frames) to
 * corrected_camera_sps_high (SAR 27:32, no timing, reorder 0, buffering 1), then enters D3's proxy_sps_hook, which
 * records the writer slot and leaves the corrected pointer as it is.
 * Tone text: og_tone_text4 gives "Log" when the log-colour group's edit of the stock refresh is in the image (4056CDE4
 * = movz w9, #6F4Ch, "Lo"), else "N-Log".
 */

#define OS_FRONT_STATE 0xA0297A9DC          /* plan 13 low-rate secondary front state (540 bytes, init data) */
#define OS_FRONT_BLOCK 0xA02A97490          /* 16-byte front block of the 8280x5520 input */
#define LOG_REFRESH_W9 0x4056CDE4           /* stock refresh 4056CD84: movz w9, #2D4Eh ("N-"); log-colour: #6F4Ch */

.text
.balign 16

/* ---- readout -------------------------------------------------------------------------------------------------- */
/* 410666F8 entry (b; was h14_readout_hook).  x0 = request: +18h rate code, +24h byte nonzero for the standby view
 * (the stock selection returns 8 there), 0 for recording. */
.global h14_readout_e4_hook
h14_readout_e4_hook:
    ldrb w8, [x0, #0x24]
    cbnz w8, 1f
    ldr w8, [x0, #0x18]
    sub w8, w8, #4
    cmp w8, #2
    b.hi 1f
    stp x19, x30, [sp, #-0x10]!         // replaced instruction; stock selection
    b original_410666fc
1:  b h14_readout_hook

/* ---- configuration snapshot ----------------------------------------------------------------------------------- */
/* 40F7938C (b; replaces mov w20, w0; was configuration_e1_hook). */
.balign 16
.global configuration_e4_hook
configuration_e4_hook:
    tbz w0, #0, 9f
    stp x8, x9, [sp, #-16]!
    ldr w8, [x19]
    cmp w8, #1                          // video snapshot
    b.ne 8f
    ldr w8, [x19, #0x388]
    cmp w8, #4                          // FX video nominal readout
    b.ne 8f
    ldr w8, [x19, #0x38c]
    cmp w8, #4                          // 4.1K
    b.ne 8f
    ldr w8, [x19, #0x390]
    sub w8, w8, #4
    cmp w8, #2                          // rates 4..6
    b.hi 8f
    ldr w8, [x19, #0x3a0]
    cmp w8, #4                          // N-RAW request kind
    b.ne 8f
    half_og 8f, x9, w9
    ldp x8, x9, [sp], #16
    mov w20, w0
    stp x8, x9, [sp, #-32]!
    stp x10, x11, [sp, #16]
    mov w11, #5520
    ldr x9, =0xA02A979EE                // readout geometry[4].height
    strh w11, [x9]
    ldr x9, =0xA02A97CDA                // video route of readout 4, inputs 1 and 2
    strh w11, [x9]
    strh w11, [x9, #4]
    ldr x9, =0xA02A979C2                // RAW stream readout[4].height (D980)
    strh w11, [x9]
#if FULL_OUTPUT
    mov w10, #5504
    ldr x9, =0xA02A97A1A                // active output[4].height
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
9:  b configuration_e1_hook
.ltorg

/* ---- driver --------------------------------------------------------------------------------------------------- */
/* 4117190C (b; replaces ldr w8, [x8, #4]) in the driver selector 411717F4 (leaf, w0 = 0, x8 = request, class 2).
 * The stock code continues with w8 = readout. */
.balign 16
.global driver_class2_e4_hook
driver_class2_e4_hook:
    ldr w8, [x8, #4]
    cmp w8, #4
    b.ne 1f
    ldr x9, =0xA02A979EE
    ldrh w9, [x9]
    sub w9, w9, #1, lsl #12
    cmp w9, #1424                       // 5520
    b.ne 1f
    half_og 1f, x9, w9
    mov w0, #2                          // the full-height continuous driver of 8.3K 3:2 recording
    ret
1:  b original_41171910
.ltorg

/* ---- front end ------------------------------------------------------------------------------------------------ */
/* 41062148 (b; was og_front_low_hook; replaces b 410621E8): plan 13, area 4, rate 4..6.  x20 = descriptor; x8-x10
 * are free (the stock path sets x19/x1 and copies the 16-byte block to state +202h, then reloads w8/w9/w10). */
.balign 16
.global og_front_e4_hook
og_front_e4_hook:
    low_plan x20
    ldr x8, =OS_FRONT_STATE
    b.eq 1f
    mov w9, #4688                       // stock values (a 3:2 session before a warm restart may have left 5520)
    strh w9, [x8, #0x2]
    strh w9, [x8, #0x19e]
    mov w9, #2344
    strh w9, [x8, #0x1f4]
    b original_410621e8
1:  mov w9, #5520                       // input height
    strh w9, [x8, #0x2]
    strh w9, [x8, #0x19e]
    mov w9, #2760                       // scaled output height
    strh w9, [x8, #0x1f4]
    mov x19, x8
    ldr x1, =OS_FRONT_BLOCK
    b original_41062274
.ltorg

/* 41065194 entry (b; was h14_coordinates_hook).  x0 = {plan, area, rate, type}, x1 = record. */
.balign 16
.global h14_coordinates_e4_hook
h14_coordinates_e4_hook:
    save_args
    bl h14_coordinates_hook             // stock record with E3's 4.1K 3:2 values
    mov x21, x0
    low_plan x19
    b.ne 1f
    mov w8, #2752
    strh w8, [x20, #0xe]                // active 4128x2752
    mov w8, #4
    strh w8, [x20, #0x16]               // at (6, 4) in the scaled plane
    mov w8, #5520
    strh w8, [x20, #0x4a]               // physical 8280x5520
    strh w8, [x20, #0x66]
    mov w8, #2760
    strh w8, [x20, #0x4e]               // scaled plane 4140x2760
    strh wzr, [x20, #0x5e]
1:  restore_return

/* ---- RAW geometry --------------------------------------------------------------------------------------------- */
/* Query x0 of the oversample state: valid, readout 4, video, 4.1K, N-RAW, readout-4 height 5520, 4.1K 3:2.
 * Clobbers x8 only. */
.macro raw_os fail
    ldrb w8, [x0]
    cbnz w8, \fail
    ldr w8, [x0, #4]
    cmp w8, #4
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
    ldr x8, =0xA02A979EE
    ldrh w8, [x8]
    sub w8, w8, #1, lsl #12
    cmp w8, #1424
    b.ne \fail
    half_og \fail, x8, w8
.endm

.balign 16
.global raw_source_e4_hook
raw_source_e4_hook:                     // 41066978 entry (replaces ldrb w8, [x0])
    raw_os 1f
    mov w8, #4140
    strh w8, [x1]
    mov w8, #2760
    strh w8, [x1, #2]
    ret
1:  ldrb w8, [x0]
    b original_4106697c

.global h14_inner_e4_hook
h14_inner_e4_hook:                      // 41066A10 entry (was h14_inner_hook)
    raw_os 1f
    mov w8, #4140
    strh w8, [x1]
    mov w8, #2756
    strh w8, [x1, #2]
    ret
1:  b h14_inner_hook

.global h14_active_e4_hook
h14_active_e4_hook:                     // 41066AA8 entry (was h14_active_hook)
    raw_os 1f
    mov w8, #4128
    strh w8, [x1]
    mov w8, #2752
    strh w8, [x1, #2]
    ret
1:  b h14_active_hook
.ltorg

/* ---- proxy SPS ------------------------------------------------------------------------------------------------ */
/* 40CED8EC entry (b; was proxy_sps_hook): x0 writer context, x1 SPS, w2 length.  Same writer test as D3 (main
 * writer kinds 1..2, 1920x1080, open-gate request); a matching stock 50..120p SPS is replaced, then D3's hook runs
 * unchanged (slot record; its three 24..30p SPS do not match a corrected one). */
.balign 16
.global proxy_sps_e4_hook
proxy_sps_e4_hook:
    stp x8, x9, [sp, #-48]!
    stp x10, x11, [sp, #16]
    stp x12, x13, [sp, #32]
    cbz x0, 9f
    cbz x1, 9f
    cmp w2, #24
    b.ne 9f
    ldr w8, [x0]
    sub w8, w8, #1
    cmp w8, #1
    b.hi 9f
    ldr w8, [x0, #0x518]
    cmp w8, #1920
    b.ne 9f
    ldr w8, [x0, #0x51c]
    cmp w8, #1080
    b.ne 9f
    ldr x8, =OG_STATE
    ldr w8, [x8]
    cbz w8, 9f
    adr x10, og_sps_rates
    adr x13, og_sps_rates_end
1:  mov w11, #0
2:  ldrb w8, [x1, x11]
    ldrb w9, [x10, x11]
    cmp w8, w9
    b.ne 3f
    add w11, w11, #1
    cmp w11, #24
    b.ne 2b
    ldr w8, [x10, #24]                  // 0: D3's corrected SPS, 1: the level-5.1 one
    adr x9, corrected_camera_sps
    adr x12, corrected_camera_sps_high
    cmp w8, #1
    csel x1, x12, x9, eq
    b 9f
3:  add x10, x10, #32
    cmp x10, x13
    b.lo 1b
9:  ldp x12, x13, [sp, #32]
    ldp x10, x11, [sp, #16]
    ldp x8, x9, [sp], #48
    b proxy_sps_hook
.balign 8
/* Stock camera SPS of the 4.1K 3:2 proxies at 50..120p (E1 body clips DSC_5807..5810, avcC), each with its kind. */
og_sps_rates:
    .byte 0x67,0x64,0x00,0x2a,0xac,0xd3,0x01,0xe0,0x08,0x9f,0x96,0x6e,0x02,0x02,0x02,0x80,0x00,0x01,0xf4,0x80,0x00,0xea,0x60,0x42
    .word 0, 0                          // 59.94p
    .byte 0x67,0x64,0x00,0x2a,0xac,0xd3,0x01,0xe0,0x08,0x9f,0x96,0x6e,0x02,0x02,0x02,0x80,0x00,0x01,0xf4,0x00,0x00,0xc3,0x50,0x42
    .word 0, 0                          // 50p
    .byte 0x67,0x64,0x00,0x33,0xac,0xd2,0x01,0xe0,0x08,0x9f,0x96,0x6e,0x02,0x02,0x02,0x80,0x00,0x01,0xf4,0x80,0x01,0xd4,0xc0,0x42
    .word 1, 0                          // 119.88p
    .byte 0x67,0x64,0x00,0x33,0xac,0xd2,0x01,0xe0,0x08,0x9f,0x96,0x6e,0x02,0x02,0x02,0x80,0x00,0x01,0xf4,0x00,0x01,0x86,0xa0,0x42
    .word 1, 0                          // 100p
og_sps_rates_end:
/* The level-5.1 stock SPS without VUI timing, with SAR 27:32 and bitstream restriction (reorder 0, buffering 1). */
corrected_camera_sps_high:
    .byte 0x67,0x64,0x00,0x33,0xac,0xd2,0x01,0xe0,0x08,0x9f,0x97,0xff,0x00,0x1b,0x00,0x20,0x6e,0x02,0x02,0x02,0x0f,0x1c,0x32,0xa0
.balign 4
.ltorg

/* ---- file-type tone text -------------------------------------------------------------------------------------- */
/* x0 = text of tone w0 for E3's ft_refresh3_hook: "SDR", or the stock refresh's N-Log text ("Log" with log-colour).
 * Clobbers x9, x10. */
.balign 16
og_tone_text4:
    cmp w0, #2
    b.ne 1f
    ldr x9, =LOG_REFRESH_W9
    ldr w9, [x9]
    mov w10, #0xe989
    movk w10, #0x528d, lsl #16          // movz w9, #0x6f4c
    cmp w9, w10
    adr x0, og_text_nlog
    adr x9, og_text_log4
    csel x0, x9, x0, eq
    ret
1:  adr x0, og_text_sdr
    ret
og_text_log4: .asciz "Log"
.balign 4
.ltorg
