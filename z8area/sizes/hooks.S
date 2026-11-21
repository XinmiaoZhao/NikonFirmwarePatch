.text
.balign 4
// Menu callbacks already queried 219Eh. Leave stock comparisons intact for other areas.
.macro choose name, reg, add, resume, fallback
.global \name
\name:
    cmp w0, #2
    b.eq 1f
    cmp w0, #3
    b.eq 2f
    cmp w0, #6
    b.eq 3f
    cmp w0, #8
    b \fallback
1:  mov \reg, #(3241 + \add)
    b \resume
2:  mov \reg, #(3244 + \add)
    b \resume
3:  mov \reg, #(3247 + \add)
    b \resume
.endm

.global lms_menu_hook
lms_menu_hook:
    cmp w0, #2
    b.eq 1f
    cmp w0, #3
    b.eq 2f
    cmp w0, #6
    b.eq 3f
    cmp w0, #8
    b original_405db4c0
1:  mov w23, #3241
    mov w22, #3242
    mov w20, #3243
    b original_405db510
2:  mov w23, #3244
    mov w22, #3245
    mov w20, #3246
    b original_405db510
3:  mov w23, #3247
    mov w22, #3248
    mov w20, #3249
    b original_405db510

choose lms_alt_l_hook, w21, 0, original_405e5cfc, original_405e5ccc
choose lms_alt_m_hook, w21, 1, original_405e5d9c, original_405e5d6c
choose lms_alt_s_hook, w21, 2, original_405e5e3c, original_405e5e0c

// Only ordinary-photo M[0]=0, area 6 bypasses the obsolete area-6/7 exclusion.
// All subsequent special-photo exclusions and L/M/S selection stay native.
.global lms_metadata_hook
lms_metadata_hook:
    ldr w8, [x20, #0x26c]
    cmp w8, #6
    b.ne 1f
    ldr w8, [x20]
    cbnz w8, 1f
    b original_406c2518
1:  ldr w8, [x20, #0x26c]
    and w8, w8, #0xfffffffe
    b original_406c2510

// Read-only GUI fallback for previously written XPan JPEGs with unknown size.
// This entry is on the ordinary still branch after native special-file tests.
// Require unknown size, native CropHiSpeed code 7, and an exact designed size.
.global lms_playback_hook
lms_playback_hook:
    cmp w0, #0x12
    b.ne 9f
    mov x0, x21
    bl original_407b58c0
    cmp w0, #7
    b.ne 8f
    mov w8, #8256
    cmp w20, w8
    b.ne 1f
    cmp w19, #3048
    b.ne 8f
    mov w0, #0
    b 9f
1:  mov w8, #6192
    cmp w20, w8
    b.ne 2f
    cmp w19, #2280
    b.ne 8f
    mov w0, #1
    b 9f
2:  mov w8, #4128
    cmp w20, w8
    b.ne 8f
    cmp w19, #1520
    b.ne 8f
    mov w0, #2
    b 9f
8:  mov w0, #0x12
9:  b original_40797110
