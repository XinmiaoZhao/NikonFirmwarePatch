/* Reuse the recorded D4 core; only the new i-menu transaction and getters are added. */
#define preview_full_page_hook preview_full_page_legacy
#define af_forward_hook af_forward_legacy
#define af_inverse_hook af_inverse_legacy
#define coordinate_family_hook coordinate_family_legacy
#define af_geometry_hook af_geometry_legacy
#define half_plan_hook half_plan_legacy
#define half_size_hook half_size_legacy
#define half_extent_hook half_extent_legacy
#include "menu_repair_hooks.S"
#undef preview_full_page_hook
#undef af_forward_hook
#undef af_inverse_hook
#undef coordinate_family_hook
#undef af_geometry_hook
#undef half_plan_hook
#undef half_size_hook
#undef half_extent_hook

/* Native matching tables still identify the 19 factory rows. OG has exactly
 * three leading indexes. Factory rows shift by three; canonical factory rows
 * 2..4 map to OG indexes 0..2 only when the banked flag is set. */
.balign 16
.global i_current_hook
i_current_hook:
    ldr w0, [x9, #8]
    cmp w20, #6
    b.ne 2f
    sub w14, w0, #2
    cmp w14, #2
    b.hi 1f
    ldr x14, =OG_FLAG
    ldrb w14, [x14]
    cmp w14, #1
    b.ne 1f
    sub w0, w0, #2
    b 2f
1:  add w0, w0, #3
2:  b original_404dc338
.global i_dial_current_hook
i_dial_current_hook:
    ldr w8, [x9]
    cmp w20, #6
    b.ne 2f
    sub w14, w8, #2
    cmp w14, #2
    b.hi 1f
    ldr x14, =OG_FLAG
    ldrb w14, [x14]
    cmp w14, #1
    b.ne 1f
    sub w8, w8, #2
    b 2f
1:  add w8, w8, #3
2:  b original_404e4cb4

.global i_dial_apply_hook
i_dial_apply_hook:
    ldr x16, =0x403ec3c8
    b i_apply_transaction
.global i_list_apply_hook
i_list_apply_hook:
    ldr x16, =0x403ec508
    b i_apply_transaction
/* These two native callers always allocate four input values. Their fourth
 * N-RAW value was unused. Private row tables put OG intent there; the native
 * count stays three and no fictitious value is sent to the data store. */
i_apply_transaction:
    stp x19, x20, [sp, #-64]!
    stp x21, x22, [sp, #16]
    stp x23, x30, [sp, #32]
    mov x23, x16
    mov w19, wzr
    cmp w2, #3
    b.ne 1f
    ldr w8, [x0]
    ldr w9, =0x0500125a
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
    // Size/rate selection must not write a projected GUI quality back to DS.
    // Q3 displays Fine as High and Basic as Normal while storing 2 and 3.
    // Keep the live quality unchanged; the native two-key batch remains intact.
    mov w2, #2
    ldr w8, [x1]
    cmp w8, #6
    b.ne 1f
    ldr w8, [x1, #4]
    sub w8, w8, #4
    cmp w8, #2
    b.hi 1f
    ldr w8, [x1, #8]
    cmp w8, #1
    b.hi 1f
    ldr w8, [x1, #12]
    cmp w8, #1
    cset w19, eq
1:  ldr x20, =OG_FLAG
    ldrb w21, [x20]
    ldr x9, =OG_STATE
    ldr w22, [x9, #0x14]
    cmp w19, w21
    cset w8, ne
    add w8, w8, #1
    str w8, [x9, #0x14]
    strb w19, [x20]
    blr x23
    ldr x9, =OG_STATE
    str w22, [x9, #0x14]
    tbnz w0, #0, 2f
    strb w21, [x20]
2:  ldp x23, x30, [sp, #32]
    ldp x21, x22, [sp, #16]
    ldp x19, x20, [sp], #64
    ret
.ltorg

/* Native type8 thumbnails apply an 8% horizontal crop to a decoded
 * 640x360 JPEG. Open-gate NCVW keeps the whole 3:2 scene in that raster;
 * the crop discards real scene content. Match the FILE, not shooting mode,
 * and only a 3:2 destination (within two raster units) with no rotation. */
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
    cmp w8, #8
    b.eq ui_preview_thumb
    cmp w8, #2
    b.ne ui_preview_done
    ldr w8, [x19, #0x50]
    cbnz w8, ui_preview_done
    ldr w8, [x19, #0x3c]
    mov w9, #1024
    movk w9, #682, lsl #16
    cmp w8, w9
    b.ne ui_preview_done
    ldr w8, [x19, #0x30]
    mov w9, #65
    movk w9, #47, lsl #16
    cmp w8, w9
    b.ne ui_preview_done
    ldr w8, [x19, #0x40]
    mov w9, #484
    movk w9, #272, lsl #16
    cmp w8, w9
    b.ne ui_preview_done
    mov w8, #2
    str w8, [sp, #56]
    mov w9, #1920
    movk w9, #1080, lsl #16
    b ui_preview_source
ui_preview_thumb:
    ldr w8, [x19, #0x50]
    cbnz w8, ui_preview_done
    ldrb w8, [x19, #0x48]
    cmp w8, #1
    b.ne ui_preview_done
    ldrh w8, [x19, #0x4a]
    cmp w8, #8
    b.ne ui_preview_done
    ldrh w8, [x19, #0x40]
    ldrh w9, [x19, #0x42]
    cbz w8, ui_preview_done
    cbz w9, ui_preview_done
    add w8, w8, w8
    add w9, w9, w9, lsl #1
    sub w8, w8, w9
    add w8, w8, #2
    cmp w8, #4
    b.hi ui_preview_done
    mov w8, #1
    str w8, [sp, #56]
    mov w9, #640
    movk w9, #360, lsl #16
ui_preview_source:
    ldr w8, [x20, #0x58]
    cbnz w8, ui_preview_done
    ldr w8, [x20, #0x60]
    cbnz w8, ui_preview_done
    ldr w8, [x20, #0x64]
    cmp w8, w9
    b.ne ui_preview_done
    ldr w8, [x20, #0x68]
    cmp w8, w9
    b.ne ui_preview_done
    stp xzr, xzr, [sp, #64]
    ldr w0, [x20]
    add x1, sp, #64
    add x2, sp, #72
    bl original_407cd844
    tbz w0, #0, ui_preview_release
    ldr x21, [sp, #72]
    cbz x21, ui_preview_release
    ldrh w8, [x21, #0xc]
    ldrh w9, [x21, #0xe]
    orr w8, w9, w8, lsl #16
    bl og32_dims                        // E2: 8256x5504 or 4128x2752 (same instruction count)
    cbz w8, ui_preview_release
    nop
    nop
    nop
    ldr w8, [x21, #4]
    ubfx w8, w8, #20, #3
    cmp w8, #6
    b.ne ui_preview_release
    ldr w8, [sp, #56]
    cmp w8, #2
    b.ne ui_preview_uncrop
    /* Keep the native overview's vertical slot and center a408x272 3:2
     * rectangle inside its484x272 box. Native filter alignment produces
     *406x270 pixels at(104,48); no metadata or source raster is rewritten. */
    mov w8, #103
    movk w8, #47, lsl #16
    str w8, [x19, #0x30]
    mov w8, #408
    movk w8, #272, lsl #16
    str w8, [x19, #0x40]
    b ui_preview_release
ui_preview_uncrop:
    strb wzr, [x19, #0x48]
ui_preview_release:
    ldr x0, [sp, #64]
    cbz x0, ui_preview_done
    bl original_4085aa7c
ui_preview_done:
    ldp x0, x1, [sp, #32]
    ldr x2, [sp, #48]
    ldp x21, x30, [sp, #16]
    ldp x19, x20, [sp], #96
    b preview_full_page_legacy
.ltorg


/* Ordinary magnification clears the transient effective-area state. Its
 * selected video identity remains valid, just as in the existing local AF
 * and display guards. Use the same selected-mode fallback for both native
 * coordinate directions and their private geometry/family readers. */
.macro ui_af_target plan, fallback
    stp x16, x17, [sp, #-32]!
    mrs x16, nzcv
    str x16, [sp, #16]
    ldr x16, =OG_STATE
    ldr w16, [x16]
    cbnz w16, 1f
    require_selected_video \fallback
1:  ldr w16, [\plan, #4]
    cmp w16, #4
    b.ne \fallback
    ldr w16, [\plan]
    cmp w16, #12
    b.eq 2f
    cmp w16, #10
    b.ne \fallback
2:  ldp x16, x17, [sp], #32
.endm
.balign 16
.global af_forward_hook
af_forward_hook:
    ui_af_target x21, ui_af_forward_stock
    b original_41055BB4
ui_af_forward_stock:
    ldr x16, [sp, #16]
    msr nzcv, x16
    ldp x16, x17, [sp], #32
    b.lo 1f
    b original_41055B64
1:  b original_41055B3C
.balign 16
.global af_inverse_hook
af_inverse_hook:
    ui_af_target x22, ui_af_inverse_stock
    b original_410569A8
ui_af_inverse_stock:
    ldr x16, [sp, #16]
    msr nzcv, x16
    ldp x16, x17, [sp], #32
    b.lo 1f
    b original_41056978
1:  b original_41056940
.balign 16
.global coordinate_family_hook
coordinate_family_hook:
    cmp w0, #10
    b.ne ui_coordinate_family_stock
    cmp w1, #4
    b.ne ui_coordinate_family_stock
    stp x16, x17, [sp, #-16]!
    ldr x8, =OG_STATE
    ldr w8, [x8]
    cbnz w8, 1f
    require_selected_video 2f
1:  ldp x16, x17, [sp], #16
    mov w0, #6
    ret
2:  ldp x16, x17, [sp], #16
ui_coordinate_family_stock:
    mov w8, w0
    b original_41064FA8
.ltorg
.balign 16
.global af_geometry_hook
af_geometry_hook:
    stp x19, x30, [sp, #-32]!
    stp x20, x21, [sp, #16]
    mov x19, x1
    ldp w20, w21, [x0]
    bl original_41065194
    stp x16, x17, [sp, #-16]!
    ldr x8, =OG_STATE
    ldr w8, [x8]
    cbnz w8, 1f
    require_selected_video ui_af_geometry_done
1:  cmp w21, #4
    b.ne ui_af_geometry_done
    cmp w20, #12
    b.eq 2f
    cmp w20, #10
    b.ne ui_af_geometry_done
2:  ldrh w8, [x19]
    cmp w8, #1920
    b.ne ui_af_geometry_done
    mov w8, #1280
    strh w8, [x19, #2]
    strh w8, [x19, #0x12]
    strh w8, [x19, #0x26]
    strh w8, [x19, #0x2a]
ui_af_geometry_done:
    ldp x16, x17, [sp], #16
    ldp x20, x21, [sp, #16]
    ldp x19, x30, [sp], #32
    ret
.ltorg

/* The half-readout plan/extent readers feed the same coordinate functions.
 * Keep their selected-mode condition coherent with the full-resolution path. */
.balign 16
.global half_plan_hook
half_plan_hook:
    mov w9, #2344
    mov x1, #0x7460
    stp x10, x11, [sp, #-32]!
    stp x16, x17, [sp, #16]
    ldr w10, [x20]
    cmp w10, #10
    b.ne ui_half_plan_done
    ldr w10, [x20, #4]
    cmp w10, #4
    b.ne ui_half_plan_done
    ldr x10, =OG_STATE
    ldr w11, [x10]
    cbnz w11, 1f
    require_selected_video ui_half_plan_done
1:  mov w9, #2756
    mov x1, #0x74a0
ui_half_plan_done:
    ldp x16, x17, [sp, #16]
    ldp x10, x11, [sp], #32
    b original_41062078
.balign 16
.global half_size_hook
half_size_hook:
    stp x8, x9, [sp, #-32]!
    stp x16, x17, [sp, #16]
    ldr w8, [x0]
    cmp w8, #10
    b.ne ui_half_size_done
    ldr w8, [x0, #4]
    cmp w8, #4
    b.ne ui_half_size_done
    ldr x8, =OG_STATE
    ldr w9, [x8]
    cbnz w9, 1f
    require_selected_video ui_half_size_done
1:  mov w24, #2756
    mov w4, #2752
    ldp x16, x17, [sp, #16]
    ldp x8, x9, [sp], #32
    mov w17, #2
    b original_410664BC
ui_half_size_done:
    ldp x16, x17, [sp, #16]
    ldp x8, x9, [sp], #32
    b original_410664BC
.balign 16
.global half_extent_hook
half_extent_hook:
    stp x8, x9, [sp, #-32]!
    stp x16, x17, [sp, #16]
    ldr x8, =OG_STATE
    ldr w9, [x8]
    cbnz w9, 1f
    require_selected_video ui_half_extent_done
1:  ldrh w8, [x19, #0x48]
    mov w9, #4140
    cmp w8, w9
    b.ne ui_half_extent_done
    ldrh w8, [x19, #0x4a]
    cmp w8, #2756
    b.ne ui_half_extent_done
    ldrh w8, [x19, #0x10]
    cmp w8, #1920
    b.ne ui_half_extent_done
    mov w22, #2760
    mov w25, #2
    strh w25, [x19, #0x5e]
ui_half_extent_done:
    ldp x16, x17, [sp, #16]
    ldp x8, x9, [sp], #32
    strh w22, [x19, #0x66]
    b original_410665F4
.ltorg
