/* Integrated HB2/PQ1: mutually exclusive file-type rules; one refresh flag. */
#define TIER 0xA03D5C269
#define GRADE_RAM 0xA03D5C029
#define FILE_TYPE_RAM 0xA03D5C014
#define STAR_PAIRS    51            /* u16 star number, u16 plain number */
#define NEW_BASE      0x7000        /* 7 << 12, far above the 6242 stock numbers */
#define NEW_COUNT     21            /* u16 flags, u16 0, u32 bytes, u64 PNG pointer */
#define FORCE_RAM     0xA10040000   /* RAM alias of 40A1F000 (zero in the payload) */
#define LV_RECORD     0xA029635E0   /* A0295C558 + 277 * 68h */
#define LV_RECORD_ID  277
#define PROP_LOCK     0xA03E04668
#define PROP_COUNT    0xA03E04BD0
#define PROP_QUEUE    0xA03E04BD4
#define PROP_OVERFLOW 0xA03E04BCC
#define PROP_EVENT    0xA03E04610

.text
/* w12 = number -> w12 = plain twin when active and listed, else unchanged (uses x9..x11, x14) */
.macro star_map
    ldr x9, =FILE_TYPE_RAM
    ldr w9, [x9]
    cmp w9, #4
    b.eq 4f
    sub w9, w9, #2
    cmp w9, #1
    b.hi 7f
    ldr x9, =TIER
    ldrb w9, [x9]
    sub w9, w9, #1
    cmp w9, #3
    b.hi 7f
    adr x10, tier_star_pairs
    mov w11, #51
    b 6f
4:  ldr x9, =GRADE_RAM
    ldrb w9, [x9]
    tst w9, #3
    b.ne 7f
    adr x10, tier_hq_pairs
    mov w11, #27
6:  ldrh w14, [x10]
    cmp w14, w12
    b.eq 5f
    add x10, x10, #4
    subs w11, w11, #1
    b.ne 6b
    b 7f
5:  ldrh w12, [x10, #2]
7:
.endm

.balign 16
.global tier_star_set
tier_star_set:                      // 40325D48 (x0 = element, w1 = type, w2 = number; stock: stp x21, x20, [sp, #-0x20]!)
    cmp w1, #1
    b.ne 1f
    mov w12, w2
    star_map
    mov w2, w12
1:  stp x21, x20, [sp, #-0x20]!
    b original_40325D4C

.balign 16
.global tier_star_res_idx
tier_star_res_idx:                  // 4032DC64 (stock: mov x9, #0xcd58)
    ldr w12, [x0]
    star_map
    str w12, [x0]
    sub w9, w12, #(NEW_BASE >> 12), lsl #12
    cmp w9, #NEW_COUNT
    b.hs 1f
    adr x10, tier_star_new
    add x10, x10, w9, uxtw #4
    ldrh w9, [x10]
    strh w9, [x1]
    ldr w9, [x10, #4]
    str w9, [x1, #4]
    ldr x9, [x10, #8]
    str x9, [x1, #0x10]
    ret
1:  mov x9, #0xcd58
    b original_4032DC68

.balign 16
.global tier_star_res_val
tier_star_res_val:                  // 4032DD34 (stock: mov x8, #0xcd58)
    mov w12, w0
    star_map
    mov w0, w12
    sub w9, w12, #(NEW_BASE >> 12), lsl #12
    cmp w9, #NEW_COUNT
    b.hs 1f
    adr x10, tier_star_new
    add x10, x10, w9, uxtw #4
    ldr w9, [x10, #4]
    str w9, [x1]
    ldr x9, [x10, #8]
    str x9, [x2]
    ret
1:  mov x8, #0xcd58
    b original_4032DD38

.balign 16
.global tier_ok_star
tier_ok_star:                       // OK action of the five tier rows (x0 = context)
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    ldr x8, =TIER
    ldrb w19, [x8]
    ldr x8, =0x40A40F00
    ldr x8, [x8]
    blr x8                          // H.265 native tier OK, supplied by composition
    mov x20, x0
    ldr x8, =TIER
    ldrb w8, [x8]
    cmp w8, w19
    b.eq 1f
    bl tier_star_republish
1:  mov x0, x20
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #32
    ret

.balign 16
.global tier_star_republish
tier_star_republish:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    str x19, [sp, #16]
    ldr x8, =FORCE_RAM
    mov w9, #1
    strb w9, [x8]                   // next 0x253E compare reports a change
    ldr x19, =PROP_LOCK
    mov x0, x19
    bl original_406A6DBC            // lock
    ldr x8, =LV_RECORD
    mov w9, #1
    strb w9, [x8, #0x29]            // record pending
    ldr x8, =PROP_COUNT
    ldr w9, [x8]
    cmp w9, #0x7e
    b.hi 1f
    ldr x10, =PROP_QUEUE
    mov w11, #LV_RECORD_ID
    str w11, [x10, x9, lsl #2]
    add w9, w9, #1
    str w9, [x8]
    b 2f
1:  ldr x8, =PROP_OVERFLOW          // queue full: the pass then scans every record
    mov w9, #1
    strb w9, [x8]
2:  mov x0, x19
    bl original_406A6DC0            // unlock
    ldr x0, =PROP_EVENT
    mov w1, #4
    bl original_406A6D94            // wake the property pass
    ldr x19, [sp, #16]
    ldp x29, x30, [sp], #32
    ret

.balign 16
.global tier_star_force
tier_star_force:                    // 406AAD0C in callback 406AA7A0 (stock: cmp w27, w9; b.ne 406AAD1C); x10, x11 are dead here
    ldr x10, =FORCE_RAM
    ldrb w11, [x10]
    cbz w11, 1f
    strb wzr, [x10]
    b original_406AAD1C             // changed: store w27, flag +58h, return 1
1:  cmp w27, w9
    b original_406AAD10

.balign 16
.global tier_star_nctg
tier_star_nctg:                     // jump table 440C7B50 entries for file types 2, 3 (stock 406D2CE8: mov w0,#1; str w0,[x1,#0xa8])
    ldr x9, =TIER
    ldrb w9, [x9]
    sub w9, w9, #1
    cmp w9, #3
    mov w8, #1
    mov w10, #2
    csel w8, w10, w8, ls
    mov w0, #1
    str w8, [x1, #0xa8]
    ret


.balign 16
.global tier_hq_ok
tier_hq_ok:                         // OK action of the toolkit's four grade rows (x0 = context)
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    ldr x8, =GRADE_RAM
    ldrb w19, [x8]
    ldr x8, =0x40A40F08
    ldr x8, [x8]
    blr x8                          // ProRes native grade OK, supplied by composition
    mov x20, x0
    ldr x8, =GRADE_RAM
    ldrb w8, [x8]
    cmp w8, w19
    b.eq 1f
    bl tier_star_republish
1:  mov x0, x20
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #32
    ret


.balign 16
.global tier_hq_nctg
tier_hq_nctg:                       // jump table 440C7B50 entry of file type 4 (stock 406D2CF4: mov w0,#1; str wzr,[x1,#0xa8])
    ldr x9, =GRADE_RAM
    ldrb w9, [x9]
    tst w9, #3
    cset w8, eq                     // HQ -> 1, 422/LT/Proxy -> 0
    mov w0, #1
    str w8, [x1, #0xa8]
    ret

.ltorg
.balign 16
tier_star_new:                      // 21 x 16 bytes: records of the new PNGs (7000h + k); filled by build_hb2.py
    .space NEW_COUNT*16
tier_star_pairs:                    // 51 x (star, plain) u16; filled by build_hb2.py
    .space STAR_PAIRS*4

.balign 16
tier_hq_pairs:
    .space 27*4
