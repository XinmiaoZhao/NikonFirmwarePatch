/* Shared menu update and DS bank copy. CONFIG is read-only composition data:
 * +0 u32 mask (1 framing, 2 video-quality, 4 log-colour, 8 video-orientation),
 * +8 five row-callback slots. Compositions without video-orientation freeze
 * CONFIG after four slots; the fifth slot then reads the stock zero and the
 * cbz below skips it, so their recipes stay byte-identical.
 * Copy only the selected extra bytes: DS 120B +1/+3, 122C/1238 +1 and 1257 +1
 * as reviewed, plus -- video-orientation only -- 1257 +2, the vrotate
 * per-bank orientation byte (a full-image writer scan: stock only manages +0, and the
 * shipped tier byte at 1257 +1 rides the same record).
 * Each row callback omits its old call to the native refresh. Call native once here.
 */
#define CONFIG 0x40980F00
.text
.balign 16
.global shared_bank
shared_bank:
    ldp x10, x8, [sp]
    stp x12, x13, [sp, #-16]!
    ldr x12, =CONFIG
    ldr w12, [x12]
    and w13, w20, #0xffff
    mov w9, #0x120b
    cmp w13, w9
    b.ne 2f
    tbz w12, #1, 1f
    ldrb w9, [x8, #1]
    strb w9, [x10, #1]
1:  tbz w12, #0, 9f
    ldrb w9, [x8, #3]
    strb w9, [x10, #3]
    b 9f
2:  mov w9, #0x122c
    cmp w13, w9
    b.ne 3f
    tbz w12, #0, 9f
    b 8f
3:  mov w9, #0x1238
    cmp w13, w9
    b.ne 4f
    tbz w12, #2, 9f
    b 8f
4:  mov w9, #0x1257
    cmp w13, w9
    b.ne 9f
    tbz w12, #1, 5f
    ldrb w9, [x8, #1]        /* video-quality: H.265 tier */
    strb w9, [x10, #1]
5:  tbz w12, #3, 9f
    ldrb w9, [x8, #2]        /* video-orientation: vrotate value */
    strb w9, [x10, #2]
    b 9f
8:  ldrb w9, [x8, #1]
    strb w9, [x10, #1]
9:  ldp x12, x13, [sp], #16
    b original_410162F0

.balign 16
.global shared_refresh
shared_refresh:
    stp x29, x30, [sp, #-48]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    mov x19, x0
    bl original_40572B2C
    mov x20, x0
    cbz x19, 3f
    ldr x21, =(CONFIG + 8)
    mov w22, #5               /* CONFIG has five callback slots; stock-zero */
1:  ldr x8, [x21], #8        /* slots read 0 and cbz skips them */
    cbz x8, 2f
    mov x0, x19
    blr x8
2:  subs w22, w22, #1
    b.ne 1b
3:  mov x0, x20
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #48
    ret
.ltorg
