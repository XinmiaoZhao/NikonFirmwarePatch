/* B1/B2: full-03 hooks (video_pipeline_20261021/hooks.S) plus two changes.
 * 1. The snapshot hook also writes the readout-4 height of table A02A979B0,
 *    which 4106694C reads for the RAW stream descriptor (D980, resources
 *    13/18/27/38/51). full-03/O3 left it at 4688 while Tenc read 5520 rows.
 * 2. D3 target rates 4..6: 29.97, 25, 23.976; 50/59.94 keep factory paths.
 *    The NCTG header checks use the same rate code.
 * Keeps video readout index 4 and plan type 12. No audio, timecode or colour
 * coefficient patches. The native frame snapshot selects one geometry state;
 * leaf queries (including rate=0) consume that state rather than infer fps.
 * The existing readout-4 height is both actual geometry and the state marker.
 */
#ifndef OG_ENABLED
#define OG_ENABLED 1
#endif
#ifndef VIEW_IDLE
#define VIEW_IDLE 1
#endif
#ifndef VIEW_REC
#define VIEW_REC 1
#endif
#ifndef PROXY_TKHD
#define PROXY_TKHD 0
#endif
#ifndef PROXY_SPS
#define PROXY_SPS 1
#endif
#ifndef PLAYBACK_FIT
#define PLAYBACK_FIT 1
#endif
#define OG_STATE 0xA0FF6F000
/* State: +0 request; +4 view kind (0 none, 1 idle, 2 REC); +8 media tag;
 * +0x10 restore-local-rectangle pending; +0x14 menu transaction guard;
 * +0x18 last policy seen by the native capture-setting cache; +0x1c reserved;
 * +0x20..+0x120: sixteen {writer ctx u64, target u64} records.
 * Explicitly reset after the original text mapping on both boot paths. */
.text
.balign 16
.global configuration_hook
configuration_hook:
    mov w20, w0                         // replaced original instruction
    tbz w0, #0, config_invalid             // invalid native snapshot: no update
    stp x8, x9, [sp, #-48]!
    stp x10, x11, [sp, #16]
    stp x0, x30, [sp, #32]
    bl og_policy_hook
    mov w8, w0
    ldp x0, x30, [sp, #32]
    mov w11, #4688
    cbz w8, config_write
    ldr w8, [x19]
    cmp w8, #1                         // native video snapshot
    b.ne config_write
    ldr w8, [x19, #0x388]
    cmp w8, #4                         // FX video nominal readout
    b.ne config_write
    ldr w8, [x19, #0x38c]
    cmp w8, #6                         // 8.3K
    b.ne config_write
    ldr w8, [x19, #0x390]
    sub w8, w8, #4
    cmp w8, #2                         // rates 4..6
    b.hi config_write
    ldr w8, [x19, #0x3a0]
    cmp w8, #4                         // native N-RAW request kind
    b.ne config_write
    ldr x9, =0xA03D5C014
    ldr w8, [x9]
    cmp w8, #6                         // observed N-RAW file type
    b.ne config_write
    mov w11, #5520
config_write:
    ldr x9, =0xA02A979EE                // readout geometry[4].height
    strh w11, [x9]
    ldr x9, =0xA02A97CDA                // native video route input 1
    strh w11, [x9]
    strh w11, [x9, #4]                 // native video route input 2
    ldr x9, =0xA02A979C2                // RAW stream readout[4].height (D980)
    strh w11, [x9]
#if FULL_OUTPUT
    mov w10, #4644
    mov w8, #5520
    cmp w11, w8
    b.ne config_output
    mov w10, #5504
config_output:
    ldr x9, =0xA02A97A1A                // video active output[4].height
    strh w10, [x9]
#endif
    ldr x9, =OG_STATE
    mov w8, #5520
    cmp w11, w8
    cset w10, eq
    str w10, [x9]
    ldr w8, [x9, #4]
    cbz w8, config_view_clear
    str w8, [x9, #0x10]             // preserve need to restore copied 3:2 rectangle
config_view_clear:
    str wzr, [x9, #4]              // actual readout is assigned later, at 40F7A08C
#if VIEW_IDLE
    ldr w10, [x9]
    mov w8, #2344
    cbz w10, config_half_write
    mov w8, #2756
config_half_write:
    ldr x9, =0xA02A979D2
    strh w8, [x9]
    ldr x9, =0xA02A979FE
    strh w8, [x9]
    ldr x9, =0xA02A97D12
    strh w8, [x9]
    strh w8, [x9, #4]
    mov w8, #2322
    cbz w10, config_half_active
    mov w8, #2752
config_half_active:
    ldr x9, =0xA02A97A2A
    strh w8, [x9]
#endif
    dsb ishst
    ldp x10, x11, [sp, #16]
    ldp x8, x9, [sp], #48
config_done:
    b original_40f79390
config_invalid:
    stp x8, x9, [sp, #-16]!
    ldr x8, =OG_STATE
    ldr w9, [x8, #4]
    cbz w9, config_invalid_clear
    str w9, [x8, #0x10]
config_invalid_clear:
    str wzr, [x8, #4]
    ldp x8, x9, [sp], #16
    b original_40f79390

.balign 16
.global driver_hook
driver_hook:
    mov w9, #7                         // replaced original; video default
#if VIEW_IDLE
    cmp w8, #8
    b.ne driver_record
    ldr x10, =0xA02A979FE
    ldrh w10, [x10]
    cmp w10, #2756
    b.ne driver_done
    mov w0, #14
    ret
#endif
driver_record:
    cmp w8, #4
    b.ne driver_done
    ldr x10, =0xA02A979EE
    ldrh w10, [x10]
    sub w10, w10, #1, lsl #12
    cmp w10, #1424
    b.ne driver_done
    mov w9, #2                         // original full-height continuous driver
driver_done:
    b original_41171860                // original writes w10, then selects

.balign 16
.global plan_height_hook
plan_height_hook:
    mov w9, #4688                      // replaced original instruction
    ldr w11, [x20]
    cmp w11, #12                       // preserve video plan identity
    b.ne plan_height_done
    ldr w11, [x20, #4]
    cmp w11, #4
    b.ne plan_height_done
    ldr x10, =0xA02A979EE
    ldrh w11, [x10]
    sub w11, w11, #1, lsl #12
    cmp w11, #1424
    b.ne plan_height_done
    mov w9, #5520
plan_height_done:
    b original_41062104

.balign 16
.global frontend_block_hook
frontend_block_hook:
    mov x1, #0x7450                    // replaced original instruction
    ldr w8, [x20]
    cmp w8, #12
    b.ne frontend_block_done
    ldr w8, [x20, #4]
    cmp w8, #4
    b.ne frontend_block_done
    ldr x9, =0xA02A979EE
    ldrh w8, [x9]
    sub w8, w8, #1, lsl #12
    cmp w8, #1424
    b.ne frontend_block_done
    mov x1, #0x7490                    // paired native 16-byte frontend block
frontend_block_done:
    b original_4106226c

.balign 16
.global size_hook
size_hook:
    ldr w8, [x0, #4]
    cmp w8, #4
    b.ne size_done
    ldr x8, =0xA02A979EE
    ldrh w9, [x8]
    sub w9, w9, #1, lsl #12
    cmp w9, #1424
    b.ne size_done
    mov w24, #5520
#if FULL_OUTPUT
    mov w4, #5504
    mov w17, #8                        // (5520 - 5504) / 2
#else
    mov w17, #438                      // (5520 - 4644) / 2
#endif
size_done:
    b original_410664bc

#if FULL_OUTPUT
// All consumers use the geometry installed by the successful native snapshot.
// Scratch registers are restored; continuation sites do not consume NZCV.
.macro require_full fallback
    stp x10, x11, [sp, #-16]!
    ldr x10, =0xA02A979EE
    ldrh w11, [x10]
    sub w11, w11, #1, lsl #12
    cmp w11, #1424
    ldp x10, x11, [sp], #16
    b.ne \fallback
.endm

.balign 16
.global inner_hook
inner_hook:
    mov w9, #4652
    require_full inner_done
    ldr w10, [x0, #4]
    cmp w10, #4
    b.ne inner_done
    mov w9, #5512
inner_done:
    b original_41066a9c

.balign 16
.global rate_hook
rate_hook:
    b.ne rate_extended
    b original_40e8dbb0                // original 50/60 High tier
rate_extended:
    require_full rate_stock
    ldr x9, [x19, #0x9e0]
    ldr w9, [x9, #8]
    cmp w9, #4
    b.ne rate_stock
    b original_40e8dbb0                // native tier 8, 2.5 bpp
rate_stock:
    b original_40e8dbc0

.balign 16
.global record_hook
record_hook:
    require_full record_done
    ldr w9, [x19]
    mov w10, #8268
    movk w10, #4652, lsl #16
    cmp w9, w10
    b.ne record_done
    ldr w9, [x19, #4]
    mov w10, #30000
    cmp w9, w10
    b.hi record_done
    mov w9, #5512
    strh w9, [x19, #2]
record_done:
    ldp x19, x30, [sp, #0x10]
    b original_40d1e668

.balign 16
.global nrmt_hook
nrmt_hook:
    ldr w8, [x8, w9, sxtw #2]
    require_full nrmt_done
    ldr w10, [x0, #8]
    cmp w10, #4
    b.ne nrmt_done
    ldr w10, [x0, #0x38c]
    cmp w10, #6
    b.ne nrmt_done
    mov w8, #5512
nrmt_done:
    b original_410a5910

.balign 16
.global crop_hook
crop_hook:
    ldr w8, [x10, x8, lsl #2]
    require_full crop_done
    ldr w10, [x0, #8]
    cmp w10, #4
    b.ne crop_done
    ldr w10, [x0, #0x38c]
    cmp w10, #6
    b.ne crop_done
    mov w8, #5504
crop_done:
    b original_410a6d10

.balign 16
.global nctg_height_hook
nctg_height_hook:
    mov w8, #4644
    require_full nctg_height_done
    ldr w9, [x0, #0x10]
    sub w9, w9, #4
    cmp w9, #2                         // same rates 4..6 as snapshot
    b.hi nctg_height_done
    mov w8, #5504
nctg_height_done:
    b original_406d2c3c

.balign 16
.global nctg_crop_hook
nctg_crop_hook:
    require_full nctg_crop_stock
    ldrb w9, [x0, #0xe0]
    cbnz w9, nctg_crop_stock           // preserve proxy callback
    ldr w9, [x0, #0xc]
    cmp w9, #6
    b.ne nctg_crop_stock
    ldr w9, [x0, #0x10]
    sub w9, w9, #4
    cmp w9, #2                         // same rates 4..6 as snapshot
    b.hi nctg_crop_stock
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
nctg_crop_stock:
    sub sp, sp, #0x40
    b original_406d3828
#endif

.ltorg

/* One policy seam for a future independent menu setting. For this probe only,
 * enable selection: FX NRAW 8.3K 29.97/25/23.976p. */
.balign 16
.global og_policy_hook
og_policy_hook:
#if OG_ENABLED
    ldr x0, =0xA03D5C02B
    ldrb w0, [x0]
    cmp w0, #1
    cset w0, eq
#else
    mov w0, wzr
#endif
    ret

.balign 16
.global boot_reset_hook
boot_reset_hook:
    cmp w19, #1
    b.ne boot_reset_done
    stp x8, x9, [sp, #-16]!
    ldr x8, =OG_STATE
    mov w9, #0x120
boot_reset_loop:
    str xzr, [x8], #8
    subs w9, w9, #8
    b.ne boot_reset_loop
    dsb ishst
    ldp x8, x9, [sp], #16
boot_reset_done:
    cmp w19, #1
    b original_41184DEC

.balign 16
.global half_plan_hook
half_plan_hook:
    mov w9, #2344
    mov x1, #0x7460
#if VIEW_IDLE
    stp x10, x11, [sp, #-16]!
    ldr w10, [x20]
    cmp w10, #10
    b.ne half_plan_done
    ldr w10, [x20, #4]
    cmp w10, #4
    b.ne half_plan_done
    ldr x10, =OG_STATE
    ldr w11, [x10]
    cbz w11, half_plan_done
    mov w9, #2756
    mov x1, #0x74a0
half_plan_done:
    ldp x10, x11, [sp], #16
#endif
    b original_41062078

.balign 16
.global half_size_hook
half_size_hook:
#if VIEW_IDLE
    stp x8, x9, [sp, #-16]!
    ldr w8, [x0]
    cmp w8, #10
    b.ne half_size_done
    ldr w8, [x0, #4]
    cmp w8, #4
    b.ne half_size_done
    ldr x8, =OG_STATE
    ldr w9, [x8]
    cbz w9, half_size_done
    mov w24, #2756
    mov w4, #2752
    mov w17, #2
half_size_done:
    ldp x8, x9, [sp], #16
#endif
    b original_410664BC

/* Separate logical sensor extent from physical input at the common store tail.
 * W13 (plan type) is caller-clobbered by memcpy; infer only from the exact
 * fields this invocation has just emitted, and the active request. */
.balign 16
.global half_extent_hook
half_extent_hook:
#if VIEW_IDLE
    stp x8, x9, [sp, #-16]!
    ldr x8, =OG_STATE
    ldr w9, [x8]
    cbz w9, half_extent_done
    ldrh w8, [x19, #0x48]
    mov w9, #4140
    cmp w8, w9
    b.ne half_extent_done
    ldrh w8, [x19, #0x4a]
    cmp w8, #2756
    b.ne half_extent_done
    ldrh w8, [x19, #0x10]
    cmp w8, #1920                    // video outputs retained, not C120
    b.ne half_extent_done
    mov w22, #2760
    mov w25, #2
    strh w25, [x19, #0x5e]
half_extent_done:
    ldp x8, x9, [sp], #16
#endif
    strh w22, [x19, #0x66]
    b original_410665F4

/* Shared wrapper for local display classification and placement. Copy the
 * 56-byte display argument, leaving ImgInfo and external-output records intact. */
.macro display_prepare fallback
    ldr x8, =OG_STATE
    ldr w8, [x8, #4]
    cbz w8, \fallback
    ldp w8, w9, [x0]
    orr w8, w8, w9
    cbnz w8, \fallback
    ldr w8, [x0, #0x24]
    cmp w8, #4
    b.ne \fallback
    stp x19, x30, [sp, #-80]!
    ldp x8, x9, [x0]
    stp x8, x9, [sp, #16]
    ldp x8, x9, [x0, #16]
    stp x8, x9, [sp, #32]
    ldp x8, x9, [x0, #32]
    stp x8, x9, [sp, #48]
    ldr x8, [x0, #48]
    str x8, [sp, #64]
    str wzr, [sp, #52]              // private arg+24: full-frame aspect only
    add x0, sp, #16
.endm
.balign 16
.global display_class_hook
display_class_hook:
    display_prepare display_class_stock
    bl original_40F35F3C
    ldp x19, x30, [sp], #80
    ret
display_class_stock:
    b original_40F35F3C
.balign 16
.global display_place_hook
display_place_hook:
    display_prepare display_place_stock
    bl original_40F36000
    ldp x19, x30, [sp], #80
    ret
display_place_stock:
    b original_40F36000

.balign 16
.global display_size_hook
display_size_hook:
    cmp w0, #4
    b.ne display_size_stock
    cmp w1, #2
    b.ne display_size_stock
    ldr x8, =OG_STATE
    ldr w8, [x8, #4]
    cbz w8, display_size_stock
    adr x0, local_display_size
    ret
display_size_stock:
    b original_41061CCC
.balign 4
local_display_size:
    .short 1024,680

/* Writer context is latched when the AVC sample entry is created, before
 * the file's final tkhd. The close path never re-reads current menu state. */
.balign 16
.global proxy_sps_hook
proxy_sps_hook:
    stp x8, x9, [sp, #-48]!
    stp x10, x11, [sp, #16]
    stp x12, x13, [sp, #32]
    cbz x0, proxy_sps_done
    ldr w8, [x0]
    sub w8, w8, #1
    cmp w8, #1
    b.hi proxy_sps_done
    ldr w8, [x0, #0x518]
    cmp w8, #1920
    b.ne proxy_sps_done
    ldr w8, [x0, #0x51c]
    cmp w8, #1080
    b.ne proxy_sps_done
    ldr x8, =OG_STATE
    ldr w9, [x8]
    add x8, x8, #0x20
    mov w10, #16
    mov x13, #0
proxy_slot_loop:
    ldr x11, [x8]
    cmp x11, x0
    b.eq proxy_slot_found
    cbnz x11, proxy_slot_next
    cbnz x13, proxy_slot_next
    mov x13, x8
proxy_slot_next:
    add x8, x8, #16
    subs w10, w10, #1
    b.ne proxy_slot_loop
    cbz x13, proxy_sps_done          // no unsafe eviction
    mov x8, x13
proxy_slot_found:
    str x9, [x8, #8]
    dmb ishst
    str x0, [x8]
#if !PROXY_SPS
    b proxy_sps_done
#endif
    cbz w9, proxy_sps_done
    cbz x1, proxy_sps_done
    cmp w2, #24
    b.ne proxy_sps_done
    adr x10, original_camera_sps
    mov w11, #0
proxy_compare:
    ldrb w12, [x1, x11]
    ldrb w13, [x10, x11]
    cmp w12, w13
    b.ne proxy_compare_next
    add w11, w11, #1
    cmp w11, #24
    b.ne proxy_compare
    adr x1, corrected_camera_sps
    b proxy_sps_done
proxy_compare_next:
    add x10, x10, #24
    adr x11, original_camera_sps_end
    cmp x10, x11
    b.hs proxy_sps_done
    mov w11, #0
    b proxy_compare
proxy_sps_done:
    ldp x12, x13, [sp, #32]
    ldp x10, x11, [sp, #16]
    ldp x8, x9, [sp], #48
    sub sp, sp, #0x70               // original first instruction
    b original_40CED8F0
.balign 8
original_camera_sps:
    .byte 0x67,0x64,0x00,0x2a,0xac,0xd3,0x01,0xe0,0x08,0x9f,0x96,0x6e,0x02,0x02,0x02,0x80,0x00,0x01,0xf4,0x80,0x00,0x75,0x30,0x42
    // Original camera SPS at 25p and 23.976p, from D2 body negative controls.
    .byte 0x67,0x64,0x00,0x2a,0xac,0xd3,0x01,0xe0,0x08,0x9f,0x96,0x6e,0x02,0x02,0x02,0x80,0x00,0x01,0xf4,0x00,0x00,0x61,0xa8,0x42
    .byte 0x67,0x64,0x00,0x2a,0xac,0xd3,0x01,0xe0,0x08,0x9f,0x96,0x6e,0x02,0x02,0x02,0x80,0x00,0x01,0xf4,0x80,0x00,0x5d,0xc0,0x42
original_camera_sps_end:
corrected_camera_sps:
    .byte 0x67,0x64,0x00,0x2a,0xac,0xd3,0x01,0xe0,0x08,0x9f,0x97,0xff,0x00,0x1b,0x00,0x20,0x6e,0x02,0x02,0x02,0x0f,0x1c,0x31,0x96

.balign 16
.global proxy_tkhd_hook
proxy_tkhd_hook:
    ldr w1, [x19, #0x518]
#if !PROXY_TKHD
    b original_40CEFD68
#endif
    cmp w1, #1920
    b.ne proxy_tkhd_done
    stp x8, x9, [sp, #-32]!
    stp x10, x11, [sp, #16]
    ldr w8, [x19, #0x51c]
    cmp w8, #1080
    b.ne proxy_tkhd_restore
    ldr x8, =OG_STATE + 0x20
    mov w9, #16
proxy_tkhd_scan:
    ldr x10, [x8]
    cmp x10, x19
    b.eq proxy_tkhd_found
    add x8, x8, #16
    subs w9, w9, #1
    b.ne proxy_tkhd_scan
    b proxy_tkhd_restore
proxy_tkhd_found:
    ldr x11, [x8, #8]
    cbz x11, proxy_tkhd_restore
    mov w1, #1620
proxy_tkhd_restore:
    ldp x10, x11, [sp, #16]
    ldp x8, x9, [sp], #32
proxy_tkhd_done:
    b original_40CEFD68

/* Release writer slots only after the final native writer operation returns. */
.balign 16
.global writer_close_hook
writer_close_hook:
    stp x19, x30, [sp, #-16]!
    mov x19, x0
    bl writer_close_original
    cbnz w0, writer_close_done
    ldr x8, =OG_STATE + 0x20
    mov w9, #16
writer_close_scan:
    ldr x10, [x8]
    cmp x10, x19
    b.eq writer_close_found
    add x8, x8, #16
    subs w9, w9, #1
    b.ne writer_close_scan
    b writer_close_done
writer_close_found:
    stp xzr, xzr, [x8]
writer_close_done:
    ldp x19, x30, [sp], #16
    ret
writer_close_original:
    str x20, [sp, #-0x20]!          // original 40CEEF10 entry
    b original_40CEEF14

.balign 16
.global playback_begin_hook
playback_begin_hook:
    mov x19, x1
    stp x8, x9, [sp, #-16]!
    ldr x8, =0xA045F08F8
    cmp x19, x8
    b.ne playback_begin_done
    ldr x9, =OG_STATE
    str xzr, [x9, #8]
playback_begin_done:
    ldp x8, x9, [sp], #16
    b original_40711320

.balign 16
.global playback_capture_hook
playback_capture_hook:
    stp x8, x9, [sp, #-32]!
    stp x10, x11, [sp, #16]
    ldr x8, =0xA045F08F8
    cmp x19, x8
    b.ne playback_capture_done
    ldr x8, =OG_STATE
    str xzr, [x8, #8]
    ldr w9, [x23, #0x23c]
    cmp w9, #0x31
    b.ne playback_proxy
    ldp w10, w11, [x23]
    mov w9, #8256
    cmp w10, w9
    b.ne playback_coded
    mov w9, #5504
    cmp w11, w9
    b.eq playback_target
playback_coded:
    mov w9, #8268
    cmp w10, w9
    b.ne playback_capture_done
    mov w9, #5512
    cmp w11, w9
    b.ne playback_capture_done
    b playback_target
playback_proxy:
    cmp w9, #2
    b.ne playback_capture_done
    ldr w9, [x23]
    cmp w9, #1920
    b.ne playback_capture_done
    ldr w9, [x23, #4]
    cmp w9, #1080
    b.ne playback_capture_done
    ldr x10, =0xA0456A820
    ldrh w9, [x10, #0xa0]
    cmp w9, #2
    b.ne playback_capture_done
    ldrh w9, [x10, #0xa4]
    cmp w9, #1920
    b.ne playback_capture_done
    ldrh w9, [x10, #0xa6]
    cmp w9, #1080
    b.ne playback_capture_done
    ldrh w9, [x10, #0xfa]
    cmp w9, #1
    b.ne playback_capture_done
    ldrh w9, [x10, #0xfc]
    cmp w9, #0x31
    b.ne playback_capture_done
    ldrh w9, [x10, #0x102]
    mov w11, #8256
    cmp w9, w11
    b.ne playback_capture_done
    ldrh w9, [x10, #0x104]
    mov w11, #5504
    cmp w9, w11
    b.ne playback_capture_done
playback_target:
    ldr w9, [sp, #32]               // media ID in original native request
    cbz w9, playback_capture_done
    orr x9, x9, #0x100000000
    str x9, [x8, #8]
    dmb ishst
playback_capture_done:
    ldp x10, x11, [sp, #16]
    ldp x8, x9, [sp], #32
    ldr w8, [x23, #0x240]
    b original_40711534

.balign 16
.global playback_fit_hook
playback_fit_hook:
#if !PLAYBACK_FIT
    b playback_fit_stock
#endif
    ldr x8, =OG_STATE
    ldr x9, [x8, #8]
    tbz x9, #32, playback_fit_stock
    ldr x8, =0xA045F07D8
    ldr w10, [x8]
    cmp w9, w10
    b.ne playback_fit_stock
    ldrb w10, [x8, #0x14]
    cbz w10, playback_fit_stock
    mov w0, #3
    mov w1, #2
    mov w2, #1
playback_fit_stock:
    stp x23, x22, [sp, #-0x30]!
    b original_407138D4

/* Only suppress the fixed 16:9 crop in AF transforms; keep the actual area
 * and plan identity for all subsequent native processing and lens transforms. */
.macro af_target plan, fallback
    stp x16, x17, [sp, #-32]!
    mrs x16, nzcv
    str x16, [sp, #16]
    ldr x16, =OG_STATE
    ldr w16, [x16]
    cbz w16, \fallback
    ldr w16, [\plan, #4]
    cmp w16, #4
    b.ne \fallback
    ldr w16, [\plan]
    cmp w16, #12
    b.eq 1f
#if VIEW_IDLE
    cmp w16, #10
    b.ne \fallback
#else
    b \fallback
#endif
1:
    ldp x16, x17, [sp], #32
.endm
.balign 16
.global af_forward_hook
af_forward_hook:
    af_target x21, af_forward_stock
    b original_41055BB4
af_forward_stock:
    ldr x16, [sp, #16]
    msr nzcv, x16
    ldp x16, x17, [sp], #32
    b.lo 1f
    b original_41055B64
1:  b original_41055B3C
.balign 16
.global af_inverse_hook
af_inverse_hook:
    af_target x22, af_inverse_stock
    b original_410569A8
af_inverse_stock:
    ldr x16, [sp, #16]
    msr nzcv, x16
    ldp x16, x17, [sp], #32
    b.lo 1f
    b original_41056978
1:  b original_41056940
.balign 16
.global coordinate_family_hook
coordinate_family_hook:
#if VIEW_IDLE
    cmp w0, #10
    b.ne coordinate_family_stock
    cmp w1, #4
    b.ne coordinate_family_stock
    ldr x8, =OG_STATE
    ldr w8, [x8]
    cbz w8, coordinate_family_stock
    mov w0, #6
    ret
#endif
coordinate_family_stock:
    mov w8, w0
    b original_41064FA8
.ltorg
/* AF receives a private coordinate plane. Keep original 1920x1080 encoder
 * buffers; only these two local transform descriptors use square 3:2 units. */
.balign 16
.global af_geometry_hook
af_geometry_hook:
    stp x19, x30, [sp, #-32]!
    stp x20, x21, [sp, #16]
    mov x19, x1
    ldp w20, w21, [x0]
    bl original_41065194
    ldr x8, =OG_STATE
    ldr w8, [x8]
    cbz w8, af_geometry_done
    cmp w21, #4
    b.ne af_geometry_done
    cmp w20, #12
    b.eq af_geometry_apply
#if VIEW_IDLE
    cmp w20, #10
    b.ne af_geometry_done
#else
    b af_geometry_done
#endif
af_geometry_apply:
    ldrh w8, [x19]
    cmp w8, #1920
    b.ne af_geometry_done
    mov w8, #1280
    strh w8, [x19, #2]
    strh w8, [x19, #0x12]
    strh w8, [x19, #0x26]
    strh w8, [x19, #0x2a]
af_geometry_done:
    ldp x20, x21, [sp, #16]
    ldp x19, x30, [sp], #32
    ret
.ltorg

/* Native 40F79348 calculates actual readout only at its end. Publish the view
 * from that result, then recompute only the normal local rectangle before the
 * snapshot is returned to allocators. Do not re-enter the whole display reset. */
.balign 16
.global view_commit_hook
view_commit_hook:
    str w0, [x19, #8]
    stp x0, x30, [sp, #-32]!
    stp x8, x9, [sp, #16]
    ldr x9, =OG_STATE
    mov w8, #0
    tbz w20, #0, view_commit_store
    ldr w10, [x9]
    cbz w10, view_commit_store
#if VIEW_REC
    cmp w0, #4
    b.ne view_commit_idle
    mov w8, #2
    b view_commit_store
#endif
view_commit_idle:
#if VIEW_IDLE
    cmp w0, #8
    cset w8, eq
#endif
view_commit_store:
    str w8, [x9, #4]
    tbz w20, #0, view_commit_done
    cbnz w8, view_commit_rectangle
    ldr w10, [x9, #0x10]
    cbz w10, view_commit_done
view_commit_rectangle:
    ldr w8, [x19, #0x1fc]
    ldr w9, [x19, #0x200]
    orr w8, w8, w9
    cbnz w8, view_commit_done
    sub sp, sp, #64
    stp xzr, xzr, [sp]
    add x8, x19, #0x204
    str x8, [sp, #8]
    ldr x8, =0xA03BB9C64
    str x8, [sp, #16]
    add x8, x8, #4
    str x8, [sp, #24]
    str xzr, [sp, #32]
    ldr x8, =OG_STATE
    ldr w8, [x8, #4]
    cbnz w8, view_commit_area_ready
    ldr w8, [x19, #0x35c]           // native local area for target -> ordinary
    str w8, [sp, #36]
view_commit_area_ready:
    add x8, x19, #0x1b0
    str x8, [sp, #40]
    add x8, x19, #0x1b8
    str x8, [sp, #48]
    mov x0, sp
    bl original_40F35F3C
    mov w1, w0
    ldr x8, =0xA03BB74CC
    ldr w8, [x8]
    cmp w8, #12
    csel w0, w8, wzr, lo
    mov w2, wzr
    add x3, x19, #0x1b8
    bl original_411871AC
    ldr w8, [x19, #0x1a4]
    str w8, [x19, #0x2e4]
    add x8, x19, #0x2e8
    str x8, [sp, #48]
    mov x0, sp
    bl original_40F36000
    add sp, sp, #64
    ldr x8, =OG_STATE
    str wzr, [x8, #0x10]
    dsb ishst
view_commit_done:
    ldp x8, x9, [sp, #16]
    ldp x0, x30, [sp], #32
    b original_40F7A090
.ltorg

/* D3 1015h proxy-associated main height. Preserve W8 = native width. */
.balign 16
.global proxy_main_height_hook
proxy_main_height_hook:
    mov w9, #4644
    require_full proxy_main_height_done
    stp x10, x11, [sp, #-16]!
    ldr w10, [x0, #0x10]
    sub w10, w10, #4
    cmp w10, #2
    b.hi proxy_main_height_restore
    mov w9, #5504
proxy_main_height_restore:
    ldp x10, x11, [sp], #16
proxy_main_height_done:
    b original_406D3154

/* Native 40f28488 copies property218c/2124 and 400211e/4002120 to
 * A03BB71EC/71F0 and 71D8/71DC. Magnification then clears only the effective
 * ImgInfo area (native +388), so transient OG_STATE drops while this selected
 * video mode remains. Require selector1; the GUI caller separately gates UI6.
 * Scratch X17 only; callers preserve registers/NZCV where required. */
.macro require_selected_video fail
    ldr x17, =0xA03D5C02B
    ldrb w17, [x17]
    cmp w17, #1
    b.ne \fail
    ldr x17, =0xA03D7C94C
    ldr w17, [x17]
    cmp w17, #1
    b.ne \fail
    ldr x17, =0xA03D5C014
    ldr w17, [x17]
    cmp w17, #6
    b.ne \fail
    ldr x17, =0xA03BB71D8
    ldr w17, [x17]
    cmp w17, #6
    b.ne \fail
    ldr x17, =0xA03BB71DC
    ldr w17, [x17]
    sub w17, w17, #4
    cmp w17, #2
    b.hi \fail
    ldr x17, =0xA03BB71EC
    ldr w17, [x17]
    cmp w17, #1
    b.ne \fail
    ldr x17, =0xA03BB71F0
    ldr w17, [x17]
    cmp w17, #4
    b.ne \fail
.endm

/* Keep 2124h and ImgInfo+388h native. Only project local AF consumers.
 * 04.50's batch rewrite made +388h=0 and incorrectly disabled the next
 * video snapshot. These sites never alter that recording identity. */
.macro project_af_register reg
    stp x16, x17, [sp, #-32]!
    mrs x16, nzcv
    str x16, [sp, #16]
    cmp \reg, #4
    b.ne 1f
    ldr x17, =OG_STATE
    ldr w17, [x17, #4]
    cbnz w17, 2f
    require_selected_video 1f
2:  mov \reg, #0
1:
    ldr x16, [sp, #16]
    msr nzcv, x16
    ldp x16, x17, [sp], #32
.endm
.balign 16
.global af_local_area_hook
af_local_area_hook:
    project_af_register w8
    str w8, [sp, #0x88]
    b original_40F302FC
.balign 16
.global af_grid_hook
af_grid_hook:
    ldp w8, w10, [x20, #0xc]
    project_af_register w8
    b original_40F34A4C
.balign 16
.global af_custom_grid_hook
af_custom_grid_hook:
    ldp w9, w10, [x20, #0xc]
    project_af_register w9
    b original_40F349C0
.macro project_af_class info
    stp x16, x17, [sp, #-32]!
    mrs x16, nzcv
    str x16, [sp, #16]
    ldr w17, [\info, #0x388]
    cmp w17, #4
    b.ne 1f
    ldr x17, =OG_STATE
    ldr w17, [x17, #4]
    cbnz w17, 2f
    require_selected_video 1f
2:  mov w8, #0
1:
    ldr x16, [sp, #16]
    msr nzcv, x16
    ldp x16, x17, [sp], #32
.endm
.balign 16
.global af_class1_hook
af_class1_hook:
    project_af_class x19
    str w8, [x19, #0x3c0]
    b original_40F28928
.balign 16
.global af_class2_hook
af_class2_hook:
    project_af_class x21
    str w8, [x21, #0x3c0]
    b original_40F350EC

/* Four identified GUI magnify reads. Native availability checks execute first. */
.balign 16
.global zoom_area_hook
zoom_area_hook:
    stp x19, x30, [sp, #-16]!
    bl original_403EC398
    cmp w0, #4
    b.ne zoom_area_done
    ldr x8, =OG_STATE
    ldr w8, [x8, #4]
    cbnz w8, zoom_area_project
    require_selected_video zoom_area_done
zoom_area_project:
    mov w0, #0
zoom_area_done:
    ldp x19, x30, [sp], #16
    ret
.ltorg

/* D4: independent virtual rows, stock size/rate identity with a banked flag.
 * DATA constants are fixed allocations checked by the builder. */
#define OG_FLAG 0xA03D5C02B
#define OG_MENU 0x408C0000
#define OG_RATE 0x408C1000
.balign 16
.global menu_list_base_hook
menu_list_base_hook:
    ldr x26, =OG_MENU
    b original_4056c660
.global menu_select_base_hook
menu_select_base_hook:
    ldr x21, =OG_MENU
    b original_40570334
.global menu_summary_base_hook
menu_summary_base_hook:
    mov w29, w0
    mov w0, w21
    ldr x8, =OG_MENU
    b original_40572e28

/* Both match loops have already matched the canonical type/size/rate. */
.global menu_list_match_hook
menu_list_match_hook:
    cmp w20, #6
    b.ne 1f
    ldr x8, =OG_FLAG
    ldrb w8, [x8]
    cmp w8, #1
    cset w8, eq
    ldr w9, [x25]
    cmp w8, w9
    b.eq 1f
    b original_4056c738
1:  str w28, [sp, #8]
    b original_4056c738
.global menu_summary_match_hook
menu_summary_match_hook:
    cmp w26, #6
    b.ne 1f
    ldr x8, =OG_FLAG
    ldrb w8, [x8]
    cmp w8, #1
    cset w8, eq
    ldr w9, [x20, #4]
    cmp w8, w9
    b.eq 1f
    b original_40572ef0
1:  ldur w3, [x20, #-0xc]
    mov w8, #0x35c0
    sub w8, w3, w8
    cmp w8, #9                          // E1: ten 3:2 rows (35C0..35C9) -> stock N-RAW rows 2..11
    b.hi 2f
    // New rows reuse the same rate/quality resource as stock N-RAW 8.3K.
    // The parent control is an image widget; a dynamic text slot is not its resource ID.
    add w8, w8, #2
    mov w9, #12
    umaddl x8, w8, w9, x24
    cmp w23, #1
    b.ne 3f
    ldr w1, [x8, #4]
    b original_40572ef0
3:  ldr w1, [x8, #8]
    b original_40572ef0
2:  add x8, x21, #0x20
    b original_40572ea4

/* x0 keys, x1 values, w2 count. Flag published before the synchronous native
 * update; restored on failure. Guard 2 marks the native DS setter changed
 * even when canonical values are equal. The original batch notification runs
 * exactly once. No transient fake size/rate is ever written. */
.global menu_apply_hook
menu_apply_hook:
    stp x19, x20, [sp, #-64]!
    stp x21, x22, [sp, #16]
    stp x23, x30, [sp, #32]
    mov x21, x0
    mov w22, w2
    ldr x20, =OG_FLAG
    ldrb w23, [x20]
    mov w9, wzr
    cmp w19, #6
    b.ne 1f
    ldr w9, [x8, #8]
    cmp w9, #1
    cset w9, eq
1:  str w9, [sp, #48]
    ldr x10, =OG_STATE
    ldr w11, [x10, #0x14]
    str w11, [sp, #52]
    cmp w9, w23
    cset w11, ne
    add w11, w11, #1
    str w11, [x10, #0x14]
    strb w9, [x20]
    bl original_403ec3c8
    ldr x10, =OG_STATE
    ldr w11, [sp, #52]
    str w11, [x10, #0x14]
    mov w19, w0
    tbz w0, #0, 3f
    b 4f
3:  strb w23, [x20]
4:  mov w0, w19
    ldp x23, x30, [sp, #32]
    ldp x21, x22, [sp, #16]
    ldp x19, x20, [sp], #64
    ret

/* Copy only byte +3 when the native one-byte WbMovieSameStill bank item moves.
 * Bytes +1/+2 are reserved by the independent ProRes line and are untouched. */
.global menu_bank_hook
menu_bank_hook:
    ldp x10, x8, [sp]
    and w9, w20, #0xffff
    mov w11, #0x120b
    cmp w9, w11
    b.ne 1f
    ldrb w9, [x8, #3]
    strb w9, [x10, #3]
1:  b original_410162f0

.global remaining_table_hook
remaining_table_hook:
    ldr x10, =0x42AB3C90
    stp x0, x30, [sp, #-16]!
    bl og_policy_hook
    cbz w0, 1f
    ldr x10, =OG_RATE
1:  ldp x0, x30, [sp], #16
    ldr w9, [sp, #4]
    mov w8, #0x18
    b original_40d1e650

/* The special summary marker is never an icon-table index. */
.global menu_summary_draw_hook
menu_summary_draw_hook:
    tbnz w1, #31, 1f
    mov x0, x25
    b original_40572f54
1:  stp x19, x30, [sp, #-16]!
    mov x19, x25
    and w8, w1, #3
    adr x0, og_summary_strings
    add x0, x0, x8, lsl #5
    mov w1, #0x4a
    mov w2, #4
    bl original_403f2920
    mov x0, x19
    mov w1, #0x4a
    bl original_403f645c
    ldp x19, x30, [sp], #16
    b original_40572f58
.balign 8
og_summary_strings:
    .asciz "8256x5504 30p 3:2"
    .space 14
    .asciz "8256x5504 25p 3:2"
    .space 14
    .asciz "8256x5504 24p 3:2"
    .space 14

/* File-based display only. Attribute record keeps its actual size and crop tag.
 * Film classifier: x21 record object, w20 width, w19 height, movie predicate true. */
.global film_icon_hook
film_icon_hook:
    mov w8, #8256
    cmp w20, w8
    b.ne 1f
    mov w8, #5504
    cmp w19, w8
    b.ne 1f
    mov x0, x21
    mov x1, xzr
    bl original_407b6958
    cmp w0, #6
    b.ne 1f
    mov w0, #3
    b original_40797110
1:  mov x0, x21
    b original_4079708c

/* Crop code 11 only maps to FX when case-0 media is N-RAW, exact full height.
 * Codec projection at sp+48h is NCTG 1015h/main codec, retained by original parser. */
.global fx_icon_hook
fx_icon_hook:
    ldrh w8, [sp, #0x44]
    cmp w8, #11
    b.ne 1f
    ldrh w9, [sp, #0x16]
    mov w10, #8256
    cmp w9, w10
    b.ne 1f
    ldrh w9, [sp, #0x18]
    mov w10, #5504
    cmp w9, w10
    b.ne 1f
    ldr w9, [sp, #0x48]
    cmp w9, #0x31
    b.ne 1f
    mov x0, x19
    mov w1, #1
    b original_406c02ac
1:  b original_406c0284
.ltorg

/* Ordinary native size/rate writes (including reset and shortcut setters)
 * choose an ordinary row. Main virtual-row transaction is explicitly guarded.
 * Force the native changed-byte when only our flag changed, so the original
 * transaction emits its setting notification with unchanged canonical values. */
.balign 16
.global setting_normal_hook
setting_normal_hook:
    stp x19, x20, [sp, #-32]!
    stp x21, x30, [sp, #16]
    mov w19, w0
    mov x20, x2
    bl setting_normal_body
    tbz w0, #0, 2f
    and w9, w19, #0xffff
    mov w10, #0x125a
    sub w9, w9, w10
    cmp w9, #1
    b.hi 2f
    ldr x9, =OG_STATE
    ldr w9, [x9, #0x14]
    cmp w9, #2
    b.eq 3f
    cbnz w9, 2f
    ldr x9, =OG_FLAG
    ldrb w10, [x9]
    cbz w10, 2f
    strb wzr, [x9]
3:  mov w10, #1
    strb w10, [x20]
2:  ldp x21, x30, [sp, #16]
    ldp x19, x20, [sp], #32
    ret
setting_normal_body:
    mov w8, w0
    b original_41015d70

.balign 16
.global setting_bank_normal_hook
setting_bank_normal_hook:
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
    cbz w10, 2f
    strb wzr, [x9]
3:  mov w10, #1
    strb w10, [x21]
2:  ldp x23, x30, [sp, #32]
    ldp x21, x22, [sp, #16]
    ldp x19, x20, [sp], #48
    ret
setting_bank_normal_body:
    sub sp, sp, #0x30
    b original_41015f84
.ltorg

/* The native capture notifier independently suppresses unchanged scalar values.
 * Track the auxiliary policy alongside its existing size/rate cache, so a
 * menu or bank change with equal canonical values emits one normal capture
 * event. Do not forge size/rate values or add a second notification call. */
.balign 16
.global menu_capture_cache_hook
menu_capture_cache_hook:
    stp x9, x10, [sp, #-48]!
    stp x11, x12, [sp, #16]
    mrs x9, nzcv
    str x9, [sp, #32]
    cset w12, ne
    ldr w9, [x23, x20, lsl #2]
    and w9, w9, #0xffff
    mov w10, #0x125a
    sub w9, w9, w10
    cmp w9, #1
    b.hi 1f
    ldr x9, =OG_FLAG
    ldrb w9, [x9]
    cmp w9, #1
    cset w9, eq
    ldr x10, =OG_STATE
    ldr w11, [x10, #0x18]
    cmp w9, w11
    cset w11, ne
    orr w12, w12, w11
    str w9, [x10, #0x18]
1:  cbnz w12, 2f
    ldr x9, [sp, #32]
    msr nzcv, x9
    ldp x11, x12, [sp, #16]
    ldp x9, x10, [sp], #48
    b original_40f25c94
2:  ldr x9, [sp, #32]
    msr nzcv, x9
    ldp x11, x12, [sp, #16]
    ldp x9, x10, [sp], #48
    b original_40f25c54
.ltorg

/* Full-page static preview: actual native request uses a 1024x682 NV16
 * canvas but fits the squashed 1920x1080 JPEG into y=53/h=576. Source
 * pixels and strides remain 1920x1080. Only exact full-height N-RAW file
 * attributes expand the destination rectangle to the existing canvas.
 * No current shooting-mode predicate and no thumbnail/rotation override. */
.balign 16
.global preview_full_page_hook
preview_full_page_hook:
    stp x19, x20, [sp, #-96]!
    stp x21, x30, [sp, #16]
    stp x0, x1, [sp, #32]
    str x2, [sp, #48]
    mov x19, x0
    mov x20, x1
    ldr w8, [x19, #0x34]
    cmp w8, #2
    b.ne preview_full_page_done
    ldr w8, [x19, #0x50]
    cbnz w8, preview_full_page_done
    ldr w8, [x19, #0x3c]
    mov w9, #1024
    movk w9, #682, lsl #16
    cmp w8, w9
    b.ne preview_full_page_done
    ldrh w8, [x19, #0x30]
    cbnz w8, preview_full_page_done
    ldrh w8, [x19, #0x40]
    cmp w8, #1024
    b.ne preview_full_page_done
    ldr w8, [x20, #0x58]
    cbnz w8, preview_full_page_done
    ldr w8, [x20, #0x60]
    cbnz w8, preview_full_page_done
    ldr w8, [x20, #0x64]
    mov w9, #1920
    movk w9, #1080, lsl #16
    cmp w8, w9
    b.ne preview_full_page_done
    ldr w8, [x20, #0x68]
    cmp w8, w9
    b.ne preview_full_page_done
    stp xzr, xzr, [sp, #64]
    ldr w0, [x20]
    add x1, sp, #64
    add x2, sp, #72
    bl original_407cd844
    tbz w0, #0, preview_full_page_release
    ldr x21, [sp, #72]
    cbz x21, preview_full_page_release
    ldrh w8, [x21, #0xc]
    ldrh w9, [x21, #0xe]
    orr w8, w9, w8, lsl #16
    bl og32_dims                        // E2: 8256x5504 or 4128x2752 (same instruction count)
    cbz w8, preview_full_page_release
    nop
    nop
    nop
    ldr w8, [x21, #4]
    ubfx w8, w8, #20, #3
    cmp w8, #6
    b.ne preview_full_page_release
    str wzr, [x19, #0x30]
    mov w8, #1024
    movk w8, #682, lsl #16
    str w8, [x19, #0x40]
preview_full_page_release:
    ldr x0, [sp, #64]
    cbz x0, preview_full_page_done
    bl original_4085aa7c
preview_full_page_done:
    ldp x0, x1, [sp, #32]
    ldr x2, [sp, #48]
    ldp x21, x30, [sp, #16]
    ldp x19, x20, [sp], #96
    stp x28, x27, [sp, #-0x60]!
    b original_407d2eac
.ltorg

/* Ordinary rear-LCD zoom requests also use 40389a14 with x1=0. In that
 * branch native property218c=1 crops 1024x682 to y54..630 even when x2=0.
 * D3's four dual-window getters do not cover this consumer. Preserve all
 * native display selection and projection, then widen only the current
 * selected open-gate 3:2 source rectangle. The 1280x960 full/inset
 * rectangles exactly match this same function's original photo branches. */
.balign 16
.global zoom_display_bounds_hook
zoom_display_bounds_hook:
    stp x8, x9, [sp, #-48]!
    str x17, [sp, #32]
    mrs x8, nzcv
    str x8, [sp, #16]
    cbz x19, zoom_display_bounds_done
    ldr x17, =0xA03228FA8
    ldr w17, [x17]
    cmp w17, #6
    b.ne zoom_display_bounds_done
    require_selected_video zoom_display_bounds_done
    ldr w8, [x19]
    mov w9, #1024
    movk w9, #682, lsl #16
    cmp w8, w9
    b.ne zoom_display_large
    str wzr, [x19, #4]
    b zoom_display_bounds_observe_hook
zoom_display_large:
    mov w9, #1280
    movk w9, #960, lsl #16
    cmp w8, w9
    b.ne zoom_display_bounds_done
    ldrh w8, [x19, #4]
    cbnz w8, zoom_display_inset
    ldrh w8, [x19, #8]
    cmp w8, #1280
    b.ne zoom_display_bounds_done
    mov w9, #0
    movk w9, #54, lsl #16
    str w9, [x19, #4]
    mov w8, #1280
    movk w8, #906, lsl #16
    b zoom_display_bounds_observe_hook
zoom_display_inset:
    cmp w8, #128
    b.ne zoom_display_bounds_done
    ldrh w8, [x19, #8]
    cmp w8, #1152
    b.ne zoom_display_bounds_done
    mov w9, #128
    movk w9, #138, lsl #16
    str w9, [x19, #4]
    mov w8, #1152
    movk w8, #820, lsl #16
.global zoom_display_bounds_observe_hook
zoom_display_bounds_observe_hook:
    str w8, [x19, #8]
zoom_display_bounds_done:
    ldr x8, [sp, #16]
    msr nzcv, x8
    ldr x17, [sp, #32]
    ldp x8, x9, [sp], #48
    ldp x19, x30, [sp, #0x20]
    b original_40389b6c
.ltorg
