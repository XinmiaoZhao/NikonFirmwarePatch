// The JPEG header composer uses x24 as base, w22 as used length, x27 as the
// allocation descriptor and x19 as the capture context (second qword is M).
// The Exif, XMP, MPF offsets and file-segment bookkeeping stay unchanged.
.text
.global jpeg_profile
jpeg_profile:
    ldr w1,[x27,#8]                  // displaced capacity load
    ldr w8,[sp,#0x88]                // header mode: JPEG=0, NDF=4
    cbnz w8,done
    ldr x8,[x19,#8]
    ldr w9,[x8,#0x4d4]               // Adobe RGB in this shot
    cmp w9,#1
    b.ne done
    ldr w9,[x8,#0x2fc]
    cbnz w9,done
    cmp w22,w1
    b.hi done
    and w8,w22,#0xffff
    mov w9,#0x9402
    cmp w8,w9
    b.ne no_mpf
    cmp w0,#3570                     // TIFF directory starts 16 bytes into MPF
    b.hi done
    sub w8,w22,#0x1000
    add x10,x24,w8,uxtw              // 4096-byte MPF segment
    ldr w9,[x10]
    mov w8,#0xe2ff
    movk w8,#0xfe0f,lsl #16
    cmp w9,w8
    b.ne done
    ldr w9,[x10,#4]
    mov w8,#0x504d
    movk w8,#0x46,lsl #16
    cmp w9,w8
    b.ne done
    // The factory clears the header buffer before constructing the MP index.
    // Keep any unexpectedly occupied tail; normal three-picture indices fit.
    add x11,x10,#3586
    mov x12,x11
    mov w13,#510
1:  ldrb w8,[x12],#1
    cbnz w8,done
    subs w13,w13,#1
    b.ne 1b
    mov w8,#14                        // big-endian segment length 3584
    strh w8,[x10,#2]
    b emit
no_mpf:
    mov w9,#0x8402
    cmp w8,w9
    b.ne done
    // Single-picture JPEG: no MP index or dependent offsets. Append using
    // the header descriptor's real capacity and publish the extended length.
    sub w9,w1,w22
    cmp w9,#510
    b.lo done
    add x11,x24,w22,uxtw
    add w22,w22,#510
emit:
    adr x12,marker
    mov w13,#18
2:  ldrb w8,[x12],#1
    strb w8,[x11],#1
    subs w13,w13,#1
    b.ne 2b
    movz x12,#0xa638
    movk x12,#0x440c,lsl #16          // immutable Nikon 492-byte Adobe RGB profile
    mov w13,#492
3:  ldrb w8,[x12],#1
    strb w8,[x11],#1
    subs w13,w13,#1
    b.ne 3b
done:
    b original_406C3680
marker:
    .byte 0xff,0xe2,0x01,0xfc
    .asciz "ICC_PROFILE"
    .byte 1,1
.balign 4
