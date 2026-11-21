// F9 returns from f2_snap with the shutter-time derived tone still in w8 and
// the actual output format in M+2fc. M+516 is a halfword of alignment padding
// after the boolean at +514. Refresh it even when this shot reuses the buffer.
.text
.global srgb_shutter
srgb_shutter:
    str     w9, [sp, #0x78]          // displaced store
    cbnz    w8, clear_mark
    ldr     w9, [x19, #0x2fc]
    sub     w9, w9, #1
    cbnz    w9, clear_mark
    mov     w9, #0x5348
    strh    w9, [x19, #0x516]
    ldr     w9, [sp, #0x78]
    ret
clear_mark:
    strh    wzr, [x19, #0x516]
    ldr     w9, [sp, #0x78]
    ret

// F9 has already selected w1. w8 is the file colour originally calculated
// from this shot's +4d4 (1=sRGB). The original setter overwrites w9 on entry.
.global srgb_register
srgb_register:
    cmp     w1, #3
    ccmp    w8, #1, #0, eq
    b.ne    set_colour
    ldr     w9, [x20, #0x2570]
    cbnz    w9, set_colour
    ldrh    w9, [x20, #0x516]
    mov     w1, #0x5348
    cmp     w9, w1
    mov     w1, #3
    csinc   w1, w1, wzr, ne         // marked -> 1 (sRGB); otherwise F9 value 3
set_colour:
    b       original_406BC450
