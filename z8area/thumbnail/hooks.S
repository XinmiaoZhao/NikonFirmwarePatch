.text
// HIF plane preparation has already checked M+2fc == 1.
.global hif_size
hif_size:
.Lhif_size:
    cmp     w0, #6
    b.ne    original_size
    adr     x0, dimensions
    ret
original_size:
    b       original_410619F0
// Compressed-preview descriptors receive the snapshot before class selection.
.global snapshot_size
snapshot_size:
    ldr     w8, [x0, #0x2fc]
    ldr     w0, [x0, #0x28c]
    cmp     w8, #1
    b.eq    .Lhif_size
    b       original_size
.balign 4
dimensions:
    .hword 352, 130
