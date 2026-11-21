// Photo/drive properties read by the factory GUI and the RAW pre-capture patch.
// A single scratch register retains the calling contracts of the F9 name hooks.
.macro branch_if_hsfc reg, word, dest
    movz    \reg, #0x4254
    movk    \reg, #0x03d7, lsl #16
    movk    \reg, #0xa, lsl #32
    ldr     \word, [\reg]
    cmp     \word, #1
    b.ne    99f
    movz    \reg, #0xc7a4
    movk    \reg, #0x03d7, lsl #16
    movk    \reg, #0xa, lsl #32
    ldr     \word, [\reg]
    sub     \word, \word, #3
    cmp     \word, #3
    b.ls    \dest
99:
.endm

.text
.global drive_choice
drive_choice:
    branch_if_hsfc x0, w0, jpeg
    movz    x0, #0x82ba
    movk    x0, #0x3d4, lsl #16
    movk    x0, #0xa, lsl #32
    ldrb    w0, [x0]
    cmp     w0, #1
    cset    w0, eq
    ret
jpeg:
    mov     w0, wzr
    ret

.global drive_tone
drive_tone:
    str     x30, [sp, #-16]!
    bl      drive_choice
    mov     w9, w0
    ldr     x30, [sp], #16
    b       original_40B70680

.global drive_enter
drive_enter:
    str     x30, [sp, #-16]!
    branch_if_hsfc x2, w2, grey
    mov     w2, wzr
    b       set_grey
grey:
    mov     w2, #1
set_grey:
    mov     x0, x19
    mov     w1, #0x2de1
    bl      original_403B1A5C
    ldr     x30, [sp], #16
    b       drive_choice

.global drive_ok
drive_ok:
    branch_if_hsfc x9, w9, keep_preference
    ldr     x9, [x0]
    b       original_40B703E8
keep_preference:
    ret

.global drive_snap
drive_snap:
    // Use the captured kind as well as the drive at submission. An in-flight
    // frame keeps its format for later encoding and metadata processing.
    ldr     w9, [x19]
    cmp     w9, #3
    b.eq    keep_native
    branch_if_hsfc x9, w9, keep_native
    ldr     w9, [x19, #0x294]
    b       original_40B700DC
keep_native:
    b       original_40B700FC
