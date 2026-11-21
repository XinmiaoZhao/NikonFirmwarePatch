// Entry immediately after CMP w11,#512. Preserve its flags and x12.
// Only photo live geometry (kind 1, area 3) takes the A40 low formula.
.text
.global crop_formula
crop_formula:
    str     x12, [sp, #-16]!
    ldr     w12, [x19, #0x40]
    eor     w12, w12, #1
    cbnz    w12, original
    ldr     w12, [x19, #0x44]
    eor     w12, w12, #3
    cbnz    w12, original
    ldr     x12, [sp], #16
    b       original_410B7C78
original:
    ldr     x12, [sp], #16
    b.lt    low
    b       original_410B7C68
low:
    b       original_410B7C78
// Pair the photo live-view transforms in Nikon's full-frame AF coordinates.
// Both sites are reached only after the factory wide cases (areas 4..7).
.text
.global crop_tracking_to_sensor
crop_tracking_to_sensor:
    cmp w14,#3
    b.ne 1f
    str x16,[sp,#-16]!
    ldr w16,[x22]                // geometry kind
    cmp w16,#1
    ldr x16,[sp],#16
    b.ne 1f
    b original_41056940       // center in a 3:2 canvas, restore full-height scale
1:  cmp w14,#8
    b original_4105697C

.global crop_tracking_from_sensor
crop_tracking_from_sensor:
    cmp w1,#3
    b.ne 1f
    str x16,[sp,#-16]!
    ldr w16,[x21]
    cmp w16,#1
    ldr x16,[sp],#16
    b.ne 1f
    mov w10,#0xd800              // 3456 << 4; native tail converts to Q8
    b original_41055B40          // subtract the centered margin, clamp, scale
1:  cmp w1,#8
    b original_41055B68
