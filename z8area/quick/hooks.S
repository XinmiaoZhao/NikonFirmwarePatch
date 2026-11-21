.text
.macro addr r, low, mid, high=0
    movz    \r, #\low
    movk    \r, #\mid, lsl #16
    movk    \r, #\high, lsl #32
.endm
// The unused native 5:4 visibility slot is copied/reset by the custom bank.
// Keep 0/1 as the two legacy states. Tagged values carry three independent bits.
get_mask:
    str     x30, [sp, #-16]!
    mov     w0, #0x1727
    movk    w0, #0x600, lsl #16
    bl      original_403EC398
    sub     w8, w0, #0x10
    cmp     w8, #7
    b.ls    tagged
    cmp     w0, #0
    mov     w8, #7
    csel    w8, wzr, w8, eq
tagged:
    mov     w0, w8
    ldr     x30, [sp], #16
    ret

// Mutable selectors and forced indices stay in the native picker's RAM.
// Every list of pairs, icons and labels resides in an immutable 128-byte row.
fill_list:
    stp x19,x20,[sp,#-80]!
    stp x21,x22,[sp,#16]
    stp x23,x24,[sp,#32]
    stp x25,x26,[sp,#48]
    str x30,[sp,#64]
    mov x19,x0
    mov w20,w1
    mov x21,x2
    mov w8,#7
    str w8,[x21]
    mov w22,wzr
    mov w23,wzr
    mov w26,wzr
    adr x24,.Lquick_records
    bl get_mask
    mov w25,w0
next_option:
    ldr w0,[x24,#4]
    cbz w0,enabled
    tbnz w0,#31,custom
    movk w0,#0x600,lsl #16
    bl original_403EC398
    cmp w0,#1
    b.eq enabled
    b disabled
custom:
    mvn w8,w0
    lsr w8,w25,w8
    tbnz w8,#0,enabled
disabled:
    ldr w8,[x24]
    cmp w8,w20
    b.ne advance
    str w22,[x21]
enabled:
    mov w8,#1
    lsl w8,w8,w23
    orr w26,w26,w8
    add w22,w22,#1
advance:
    add x24,x24,#16
    add w23,w23,#1
    cmp w23,#7
    b.lo next_option
    lsr w8,w26,#1
    strb w8,[x19]
    movz x1,#0x5000
    movk x1,#0x40b9,lsl #16
    add x1,x1,x8,lsl #7
    mov w0,w22
    ldr x30,[sp,#64]
    ldp x25,x26,[sp,#48]
    ldp x23,x24,[sp,#32]
    ldp x21,x22,[sp,#16]
    ldp x19,x20,[sp],#80
    ret

.global quick_primary
quick_primary:
    stp     x19,x30,[sp,#-16]!
    mov     x19,x0
    mov     w0,#0x603
    movk    w0,#0x700,lsl #16
    bl      original_403EC398
    mov     w1,w0
    addr    x0,0x21a0,0x284,0xa
    addr    x2,0x8628,0x032f,0xa
    bl      fill_list
    strb    w0,[x19]
    addr    x8,0x8624,0x032f,0xa
    strb    w0,[x8]
    ldp     x19,x30,[sp],#16
    ret

.global quick_alternate
quick_alternate:
    addr    x1,0x4200,0x032f,0xa
    ldrb    w1,[x1,#0x17c]
    addr    x0,0x09a0,0x284,0xa
    addr    x2,0x65c8,0x032f,0xa
    bl      fill_list
    mov     w9,w0
    b       original_4049AC78
.global alternate_length
alternate_length:
    mov     w20,#7
    b       original_4049D3F8

.global live_picker
live_picker:
    addr    x9,0xfc50,0x32c,0xa
    ldrb    w20,[x9,#0xfc]
    addr    x19,0x53d8,0x32e,0xa
    mov     w1,w20
    mov     x0,x19
    add     x2,x19,#24
    bl      fill_list
    mov     w26,w0
    mov     x19,x1
    add     x21,x19,#56
    b       original_404437A0
.global live_disabled
live_disabled:
    ldr     w20,[x20,x8]
    addr    x9,0x53f0,0x32e,0xa
    ldr     w9,[x9]
    cmp     w9,w21
    cset    w0,eq
    b       original_4043FFFC

// The factory refresh paints the three stock checkboxes. Paint the extra
// controls on the same refresh so scrolling and returning redraw their state.
.global limit_refresh
limit_refresh:
    stp     x19,x30,[sp,#-48]!
    stp     x20,x21,[sp,#16]
    str     x22,[sp,#32]
    mov     x22,x0
    bl      original_405216CC
    bl      get_mask
    mov     w20,w0
    adr     x19,custom_items
    mov     w21,wzr
paint:
    ldr     w0,[x19,w21,uxtw #2]
    add     x1,x22,#0x18
    bl      original_4039E810
    cbz     x0,paint_next
    mov     w1,#0x4ba7
    bl      original_403F19F0
    cbz     x0,paint_next
    lsr     w1,w20,w21
    and     w1,w1,#1
    mov     w8,#0x126d
    sub     w1,w8,w1
    bl      original_403F645C
paint_next:
    add     w21,w21,#1
    cmp     w21,#3
    b.lo    paint
    ldr     x22,[sp,#32]
    ldp     x20,x21,[sp,#16]
    ldp     x19,x30,[sp],#48
    ret

.global limit_toggle
limit_toggle:
    ldr     x9,[x0]
    ldrh    w10,[x9,#0x58]
    ldrh    w11,[x9,#0x32]
    add     w10,w10,w11
    ldr     x9,[x9,#0x50]
    ldr     x9,[x9,#0x10]
    mov     w11,#44
    umaddl  x9,w10,w11,x9
    ldr     w9,[x9,#24]
    adr     x10,custom_items
    mov     w11,wzr
lookup:
    ldr     w12,[x10,w11,uxtw #2]
    cmp     w9,w12
    b.eq    toggle
    add     w11,w11,#1
    cmp     w11,#3
    b.lo    lookup
    ret
toggle:
    stp     x19,x30,[sp,#-32]!
    stp     x20,x21,[sp,#16]
    mov     w19,w11
    mov     w20,w9
    bl      get_mask
    mov     w1,#1
    lsl     w1,w1,w19
    eor     w21,w0,w1
    orr     w1,w21,#0x10
    mov     w0,#0x1727
    movk    w0,#0x600,lsl #16
    bl      original_403EC39C
    bl      get_mask
    lsr     w1,w0,w19
    and     w1,w1,#1
    mov     w0,w20
    bl      original_4050A5F8
    ldp     x20,x21,[sp,#16]
    ldp     x19,x30,[sp],#32
    ret

.balign 8
custom_items:
    .word   0x2c43,0x3274,0x32a7
.balign 8
.global quick_records
quick_records:
.Lquick_records:
    .space 112
// The i-grid dial can fire before the Fn overlay has initialized its list.
.global grid_dial
grid_dial:
    sub     sp,sp,#64
    stp     x0,x1,[sp]
    stp     x2,x3,[sp,#16]
    stp     x4,x30,[sp,#32]
    add     x0,sp,#48
    bl      quick_primary
    ldp     x0,x1,[sp]
    ldp     x2,x3,[sp,#16]
    ldp     x4,x30,[sp,#32]
    add     sp,sp,#64
    b       original_404EA570

.global grid_restrict
grid_restrict:
    stp     x19,x30,[sp,#-16]!
    bl      original_403A036C
    tbnz    w0,#0,restricted_done
    cmp     w20,#6
    b.hi    restricted_done
    adr     x8,.Lquick_records
    add     x8,x8,w20,uxtw #4
    ldr     w19,[x8,#4]
    cbz     w19,restricted_done
    tbnz    w19,#31,restricted_custom
    mov     w0,w19
    movk    w0,#0x600,lsl #16
    bl      original_403EC398
    cmp     w0,#1
    cset    w0,ne
    b       restricted_done
restricted_custom:
    bl      get_mask
    mvn     w19,w19
    lsr     w0,w0,w19
    eor     w0,w0,#1
    and     w0,w0,#1
restricted_done:
    ldp     x19,x30,[sp],#16
    ret

// Fn2 + command dial runs in the capture-control task. Its seven stock
// records include inactive legacy areas and movie-specific secondary fields.
// Keep the movie branch intact. In photo mode take native eligibility for
// the four factory choices and run the factory dial stepper on a stack copy.
.global physical_dial
physical_dial:
    cbz     w21,physical_photo
physical_stock:
    bl      original_40D46084
    b       original_40D497E4
physical_photo:
    addr    x8,0x82c4,0x3d4,0xa
    ldr     w9,[x8]                       // active 07000603
    adr     x8,physical_records
    mov     w10,wzr
find_current:
    add     x11,x8,w10,uxtw #4
    ldr     w12,[x11]
    cmp     w12,w9
    b.eq    physical_list
    add     w10,w10,#1
    cmp     w10,#7
    b.lo    find_current
    b       physical_stock                 // unknown factory source value
physical_list:
    mov     w24,w10
    sub     sp,sp,#128
    str     x3,[sp,#112]                   // native signed dial delta
    // The native table still owns FX, DX, square and wide eligibility.
    // Private rows require a selectable FX window and ordinary release.
    addr    x8,0xc750,0x3d6,0xa
    ldr     w9,[x8]
    sub     w10,w9,#0x10
    cmp     w10,#7
    b.ls    physical_mask
    cmp     w9,#0
    mov     w10,#7
    csel    w10,wzr,w10,eq
physical_mask:
    addr    x8,0xc7a4,0x3d7,0xa
    ldr     w9,[x8]
    sub     w9,w9,#3
    cmp     w9,#3
    csel    w10,wzr,w10,ls
    ldrb    w9,[x22,#12]
    cmp     w9,#0
    csel    w10,wzr,w10,eq
    adr     x8,physical_records
    adr     x9,physical_source
    mov     w11,wzr
physical_copy:
    lsl     x12,x11,#4
    add     x13,x8,x12
    ldp     x14,x15,[x13]
    add     x13,sp,x12
    stp     x14,x15,[x13]
    ldrsb   w12,[x9,x11]
    tbnz    w12,#31,physical_custom
    add     x12,x22,w12,uxtw #4
    ldrb    w12,[x12,#12]
    b       physical_enabled
physical_custom:
    mvn     w12,w12
    lsr     w12,w10,w12
    and     w12,w12,#1
physical_enabled:
    strb    w12,[x13,#12]
    add     w11,w11,#1
    cmp     w11,#7
    b.lo    physical_copy
    mov     x0,sp
    mov     w1,#7
    mov     w2,w24
    ldr     w3,[sp,#112]
    mov     w4,#1
    bl      original_40D46084
    add     sp,sp,#128
    adr     x22,physical_records
    cmp     w0,w24
    // The stock cache indexes a different table. The setting transaction
    // later refreshes it in native order. Do not store a private index there.
    b       original_40D497EC
.balign 8
physical_records:
    .irp value,0,1,2,8,4,3,6
        .word \value,0,0x7fffffff,1
    .endr
physical_source:
    .byte 0,2,-1,4,5,-2,-3
.balign 4
