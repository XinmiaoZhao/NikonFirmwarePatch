/* SPDX-License-Identifier: GPL-3.0-or-later
 * Derived from s3lemming/z9-firmware-patch, commit 88a6f3e5195d7f38792dc8eddeb1526fde4096dc.
 * Z8 C3.11 adaptation: native interfaces, event IDs, state addresses and labels.
 * Experimental; complete native workflow qualification is performed separately.
 */
#include "mark2_import.h"

/* Fixed to original EG 5.32, exact wrapper ABI recovered in P1.
 * This bridge is executed only in an isolated laboratory address map.
 * ROM calls depend on initialized native RTOS file task on real firmware.
 */
struct native_file {
    const char *path; uint32_t flags, fd; uint64_t cursor, length, auxiliary;
};
_Static_assert(sizeof(struct native_file)==0x28,"native file object size");
_Static_assert(offsetof(struct native_file,fd)==0xc,"native fd field");
_Static_assert(offsetof(struct native_file,length)==0x18,"native length field");
#define CALL(address,type) ((type)(uintptr_t)(address))
#define SUCCESS UINT32_C(0x4320080)
static int native_open(void *ctx,const char *path,int *owned) {
    struct native_file *f=ctx;
    CALL(0x40863838,uint64_t (*)(void *,const char *,uint64_t,uint64_t))(f,path,0,0);
    uint32_t status=CALL(0x40863860,uint32_t (*)(void *,uint32_t,uint32_t))(f,0,0);
    *owned=f->fd!=UINT32_MAX;
    return status!=SUCCESS;
}
static int native_size(void *ctx,uint64_t *bytes) {
    *bytes=CALL(0x40863b14,uint64_t (*)(void *))(ctx);return 0;
}
static int native_read(void *ctx,uint8_t *dst,uint32_t request,uint32_t *actual) {
    return CALL(0x40863b38,uint32_t (*)(void *,uint8_t *,uint32_t,uint32_t *))(ctx,dst,request,actual)!=SUCCESS;
}
static int native_close(void *ctx) {
    return CALL(0x408638e8,uint32_t (*)(void *))(ctx)!=SUCCESS;
}
int m2_native_import(const char *path,uint8_t *dst,uint32_t capacity,struct m2_pcm_info *info) {
    struct native_file f;
    const struct m2_file_ops op={native_open,native_size,native_read,native_close,0};
    return m2_import(&op,&f,path,dst,capacity,info);
}

#if M2_STAGED_CONFIRM
struct buffered_file {
    struct native_file file;
    uint8_t *buffer;
    uint32_t buffer_bytes;
};
_Static_assert(offsetof(struct buffered_file,file)==0,"native file remains first");
static void sync_io(struct buffered_file *f) {
    /* 40D2B9E4 performs DC CIVAC + DSB SY when this region is cacheable.
     * Both ends of the rounded cache range belong to the dedicated buffer.
     * Before IO, remove dirty CPU lines; afterwards observe completed native
     * writes (CPU or DMA) before copying into ordinary CPU-owned storage. */
    CALL(0x40d2b9e4,uint32_t (*)(void *,int32_t,int32_t))
        (f->buffer,(int32_t)f->buffer_bytes,0);
}
static int buffered_read(void *ctx,uint8_t *dst,uint32_t request,uint32_t *actual) {
    struct buffered_file *f=ctx;uint32_t got=0;
    *actual=0;
    if(request>f->buffer_bytes)return 1;
    sync_io(f);
    int rc=native_read(&f->file,f->buffer,request,&got);
    sync_io(f);
    if(rc || got>request)return 1;
    for(uint32_t i=0;i<got;i++)dst[i]=f->buffer[i];
    *actual=got;return 0;
}
int m2_native_import_buffered(const char *path,uint8_t *dst,uint32_t capacity,
                              struct m2_pcm_info *info,uint8_t *io,uint32_t io_bytes) {
    if(!io || ((uintptr_t)io&63u) || io_bytes!=M2_IO_BUFFER_BYTES)return M2_ARGUMENT;
    struct buffered_file f={0};f.buffer=io;f.buffer_bytes=io_bytes;
    const struct m2_file_ops op={native_open,native_size,buffered_read,native_close,0};
    return m2_import(&op,&f,path,dst,capacity,info);
}
#endif
