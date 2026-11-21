/* D10 = D9 + the playback composer lays out an open-gate clip as the 3:2 image it is.
 *
 * Body evidence (D9 04.75.d9, 2026-10-28 evening, screens IMG_0214-0219): on the highlights and RGB-histogram pages the
 * open-gate clip is drawn squeezed into a 16:9 box; on the overview page it is 3:2 only because D5's preview hook
 * narrows the 16:9 box (408x272 centred in 484x272) instead of using the 3:2 box a photo gets.
 *
 * Stock facts (C3.11, ../playback_aspect_20261028/README.md §2):
 *   - the composer's aspect class 4078E150(obj) = table 440E3398[min(255, h*256/w)] with (w, h) = obj +0x39A/+0x39C;
 *     ratio 137..159 -> class 1 (16:9), 160..180 -> class 0 (3:2).  4078E1DC is the same with the stock 160x120
 *     thumbnail rule (+0x396/+0x398 instead);
 *   - +0x39A/+0x39C are copied from +0x3A8/+0x3AC, the size of the embedded image the composer selected (4078F628,
 *     407A08EC, 407A0A18, 407A0BA0).  An open-gate clip's preview JPEG (NCVW) is the 1920x1080 raster that holds the
 *     whole 3:2 scene squeezed, so the class is 1, while its file record is 8256x5504 N-RAW;
 *   - the box of a page follows the class, e.g. 40790BAC: class 1 -> h = w*9 >> 4 (overview 484 -> 272), class 0 and
 *     the default -> h = w*0xAA >> 8 (484 -> 321), same origin and width.  +0x3A8/+0x3AC (the true raster) stay the
 *     source of the scaling, so a 3:2 box shows the 1920x1080 raster unsqueezed, as D4's full page already does.
 *
 * Change: both class functions are entered through a wrapper that runs the stock body unchanged.  Only when the stock
 * result is 1 (16:9 raster) the image's own file is looked up exactly as D4/D5's preview hooks do (407CD844 with the
 * object's file id +0, record released with 4085AA7C) and an 8256x5504 N-RAW file (record +0x0C/+0x0E, kind bits 20..22
 * of +4 = 6) gets class 0, the class of a 3:2 photo.  Every other image keeps the stock class without a lookup.  The
 * wrapper keeps x1-x7 and x12-x30 of the caller (the stock leaf only clobbers x8-x11), so callers built with any
 * register assumption about the leaf are unaffected.  D9 is included unchanged and first; D5's overview narrowing stays
 * as it is (it matches only the 16:9 overview request, which no longer occurs for these files).
 */
#include "d9_hooks.S"

.text
.balign 16
.global og_aspect_class_hook
og_aspect_class_hook:                   // 4078E150 (15 callers in the playback composer)
    ldrh w8, [x0, #0x39a]               // replaced instruction
    stp x29, x30, [sp, #-32]!
    str x0, [sp, #16]
    bl original_4078E154                // rest of the stock leaf; its ret comes back here with the class in w0
    b og_aspect_class_common

.balign 16
.global og_aspect_class_thumb_hook
og_aspect_class_thumb_hook:             // 4078E1DC (2 callers): same with the 160x120 thumbnail rule
    ldrh w8, [x0, #0x39a]               // replaced instruction
    stp x29, x30, [sp, #-32]!
    str x0, [sp, #16]
    bl original_4078E1E0

og_aspect_class_common:
    cmp w0, #1                          // stock says 16:9 raster
    b.ne og_aspect_class_done
    ldr x0, [sp, #16]
    bl og_open_gate_file
    eor w0, w0, #1                      // open-gate file -> class 0 (3:2), otherwise 1
og_aspect_class_done:
    ldp x29, x30, [sp], #32
    ret

/* w0 = 1 when the file of composer image x0 is an 8256x5504 N-RAW file (the D4/D5 preview test), else 0.
 * Keeps x1-x7 and x12-x30. */
.balign 16
og_open_gate_file:
    stp x29, x30, [sp, #-176]!
    stp x1, x2, [sp, #16]
    stp x3, x4, [sp, #32]
    stp x5, x6, [sp, #48]
    stp x7, x12, [sp, #64]
    stp x13, x14, [sp, #80]
    stp x15, x16, [sp, #96]
    stp x17, x18, [sp, #112]
    stp x19, x20, [sp, #128]
    stp xzr, xzr, [sp, #144]            // file record, file information
    mov w19, wzr
    ldr w0, [x0]                        // file id, as 407D2D48 passes it
    add x1, sp, #144
    add x2, sp, #152
    bl original_407cd844
    tbz w0, #0, og_open_gate_file_release
    ldr x20, [sp, #152]
    cbz x20, og_open_gate_file_release
    ldrh w8, [x20, #0xc]
    ldrh w9, [x20, #0xe]
    orr w8, w9, w8, lsl #16
    bl og32_dims                        // E2: 8256x5504 or 4128x2752 (same instruction count)
    cbz w8, og_open_gate_file_release
    nop
    nop
    nop
    ldr w8, [x20, #4]
    ubfx w8, w8, #20, #3
    cmp w8, #6                          // N-RAW
    cset w19, eq
og_open_gate_file_release:
    ldr x0, [sp, #144]
    cbz x0, og_open_gate_file_out
    bl original_4085aa7c
og_open_gate_file_out:
    mov w0, w19
    ldp x19, x20, [sp, #128]
    ldp x17, x18, [sp, #112]
    ldp x15, x16, [sp, #96]
    ldp x13, x14, [sp, #80]
    ldp x7, x12, [sp, #64]
    ldp x5, x6, [sp, #48]
    ldp x3, x4, [sp, #32]
    ldp x1, x2, [sp, #16]
    ldp x29, x30, [sp], #176
    ret

#include "e1_hooks.S"
