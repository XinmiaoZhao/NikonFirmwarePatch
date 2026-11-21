// Snapshot-local fixes. Both enclosing functions save LR. Preserve incoming
// arguments and temporaries at the new call sites, except the intended results.
.text
.global f9_movie_info
f9_movie_info:
    cbnz    w12, 1f                  // +30: original derived tone, SDR = 0
    stp     x13, x14, [sp, #-16]!
    ldr     x13, [x19]              // captured M, same one used for the source planes
    ldr     w14, [x13, #0x2fc]
    cmp     w14, #1
    b.ne    2f
    ldr     w14, [x19, #0x20]
    sub     w14, w14, #1
    cmp     w14, #2                 // AVC / HEVC types only
    b.hi    2f
    ldr     w13, [x13, #0x2c0]
    sub     w14, w13, #1
    cmp     w14, #2                 // 1080p, 4K or 8K
    b.hi    2f
    str     w13, [x19, #0xc]
    mov     w14, #3
    str     w14, [x19, #0x20]
    mov     w9, #1                  // depth index 1 => NCTG 25h = 10
2:  ldp     x13, x14, [sp], #16
1:  stp     w9, w12, [x19, #0x2c]  // displaced depth/tone pair
    ret

.global f9_capture_colour
f9_capture_colour:
    csel    w1, w9, w8, eq          // displaced assignment: format 1 => 3
    b.ne    1f
    cmp     w8, #2                  // colour derived from captured M+4D4 = Adobe
    b.ne    1f
    ldr     w1, [x20, #0x2570]
    cmp     w1, #0                  // ordinary capture
    csel    w1, w8, w9, eq
1:  ret
