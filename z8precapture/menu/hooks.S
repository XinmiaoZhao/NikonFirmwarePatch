// UI-only view of RAW recording. Leave the saved shooting-bank value intact.
.text
c_photo:
    movz x8,#0x4254
    movk x8,#0x03d7,lsl #16
    movk x8,#0xa,lsl #32
    ldr w9,[x8]
    cmp w9,#1
    b.ne 1f
    movz x8,#0xc7a4
    movk x8,#0x03d7,lsl #16
    movk x8,#0xa,lsl #32
    ldr w9,[x8]
    cmp w9,#3             // C30
    ccmp w9,#6,#4,ne      // C15, or retain Z=1 for C30
    cset w0,eq
    ret
1:  mov w0,wzr
    ret

.global raw_menu_value
raw_menu_value:
    str x30,[sp,#-16]!
    bl original_403EC398
    cmp w0,#1
    b.ne 1f
    bl c_photo
    cmp w0,#0
    mov w0,#1
    mov w8,#3
    csel w0,w8,w0,ne
1:  ldr x30,[sp],#16
    ret

.global raw_menu_enter
raw_menu_enter:
    str x30,[sp,#-16]!
    bl c_photo
    mov w2,w0
    mov x0,x19
    mov w1,#0x29b6
    bl original_403B1A5C
    mov w0,#0x608
    movk w0,#0x600,lsl #16
    ldr x30,[sp],#16
    b raw_menu_value

.global raw_menu_lossless
raw_menu_lossless:
    str x30,[sp,#-16]!
    bl c_photo
    ldr x30,[sp],#16
    cbnz w0,2f
    mov w0,#0x608
    b original_405E6994
2:  ret

.global raw_menu_star
raw_menu_star:
    str x30,[sp,#-16]!
    bl c_photo
    cbz w0,3f
    mov w0,#0x608
    movk w0,#0x600,lsl #16
    bl original_403EC398
    cmp w0,#1
    b.eq 4f
3:  ldr x30,[sp],#16
    mov w0,#0x608
    b original_405E69A4
4:  ldr x30,[sp],#16
    ret

// Only these two quality/size role records call this predicate. The native
// painter and the input handler both pass the secondary index in w1.
.global raw_menu_size_disabled
raw_menu_size_disabled:
    sub w8,w1,#1
    cmp w8,#1
    b.ls c_photo
    mov w0,wzr
    ret

// Live overlay: substitute L in the UI descriptor, after the bank/area
// selected which cached size to read. Preserve the original property result.
.global raw_menu_size_live
raw_menu_size_live:
    ldrb w10,[x10]
    stp x0,x30,[sp,#-32]!
    stp x8,x9,[sp,#16]
    bl c_photo
    cbz w0,1f
    mov w10,wzr
1:  ldp x8,x9,[sp,#16]
    ldp x0,x30,[sp],#32
    b original_40441108

// Alternate layout: use its native size-index-zero return. Its primary
// quality lookup still uses the ordinary 13-entry menu in C15/C30.
.global raw_menu_size_alt
raw_menu_size_alt:
    str x30,[sp,#-16]!
    bl c_photo
    ldr x30,[sp],#16
    cbnz w0,1f
    mov x0,xzr
    b original_403ACCCC
1:  ret
