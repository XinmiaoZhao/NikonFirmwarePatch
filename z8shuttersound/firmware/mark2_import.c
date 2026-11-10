#include "mark2_import.h"

struct stream { const struct m2_file_ops *op; void *ctx; uint64_t pos; };
static uint16_t le16(const uint8_t *p) { return (uint16_t)((uint16_t)p[0] | (uint16_t)p[1]<<8); }
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static int four(const uint8_t *p, const char *s) {
    return p[0]==(uint8_t)s[0] && p[1]==(uint8_t)s[1] && p[2]==(uint8_t)s[2] && p[3]==(uint8_t)s[3];
}
static int cancelled(struct stream *s) { return s->op->cancelled && s->op->cancelled(s->ctx); }
static int exact(struct stream *s, uint8_t *p, uint32_t n) {
    while (n) {
        uint32_t actual=0, request=n>4096u ? 4096u:n;
        if (cancelled(s)) return M2_CANCELLED;
        if (s->op->read(s->ctx,p,request,&actual)) return M2_IO;
        if (actual>request) return M2_IO;
        if (!actual) return M2_EOF;
        s->pos+=actual; p+=actual; n-=actual;
    }
    return cancelled(s) ? M2_CANCELLED:M2_OK;
}
static int skip(struct stream *s, uint32_t n) {
    uint8_t scratch[128];
    while (n) {
        uint32_t k=n>sizeof scratch ? (uint32_t)sizeof scratch:n;
        int e=exact(s,scratch,k); if (e) return e; n-=k;
    }
    return M2_OK;
}
static int parse(struct stream *s, uint64_t bytes, uint8_t *pcm, uint32_t capacity,
                 struct m2_pcm_info *info) {
    uint8_t head[16]; uint32_t seen=0,chunks=0,data_bytes=0;
    uint64_t end; int e;
    if (bytes<12u) return M2_CONTAINER;
    if (bytes>M2_FILE_MAX) return M2_LIMIT;
    e=exact(s,head,12); if (e) return e;
    if (!four(head,"RIFF") || !four(head+8,"WAVE")) return M2_CONTAINER;
    end=(uint64_t)le32(head+4)+8u;
    /* Reject trailing undeclared bytes, concatenated containers and truncation. */
    if (end!=bytes || end<12u) return M2_CONTAINER;
    while (s->pos<end) {
        uint32_t n, padded;
        if (++chunks>M2_SCAN_MAX) return M2_LIMIT;
        if (end-s->pos<8u) return M2_CONTAINER;
        e=exact(s,head,8); if (e) return e;
        n=le32(head+4);
        /* Subtraction before addition avoids overflow, including 0xffffffff. */
        if ((uint64_t)n+(n&1u)>end-s->pos) return M2_CONTAINER;
        padded=n+(n&1u);
        if (four(head,"fmt ")) {
            if (seen&1u) return M2_DUPLICATE;
            seen|=1u;
            if (n!=16u && n!=18u) return M2_FORMAT;
            e=exact(s,head,16); if (e) return e;
            if (le16(head)!=1u || le16(head+2)!=2u || le32(head+4)!=48000u ||
                le32(head+8)!=192000u || le16(head+12)!=4u || le16(head+14)!=16u)
                return M2_FORMAT;
            if (n==18u) {
                e=exact(s,head,2); if (e) return e;
                if (le16(head)!=0u) return M2_FORMAT;
            }
        } else if (four(head,"data")) {
            if (seen&2u) return M2_DUPLICATE;
            seen|=2u;
            if (!n || (n&3u)) return M2_FORMAT;
            if (n>M2_PCM_MAX) return M2_LIMIT;
            /* Pad to original candidate 192-byte timing quantum with silence. */
            info->play_bytes=((n+191u)/192u)*192u;
            if (info->play_bytes>capacity || info->play_bytes>M2_PCM_MAX) return M2_LIMIT;
            e=exact(s,pcm,n); if (e) return e;
            data_bytes=n;
            for (uint32_t i=n;i<info->play_bytes;i++) pcm[i]=0;
        } else {
            e=skip(s,n); if (e) return e;
        }
        if (padded!=n) { e=exact(s,head,1); if (e) return e; }
    }
    if (seen!=3u) return M2_MISSING;
    info->valid_bytes=data_bytes; info->frames=data_bytes/4u;
    info->rate=48000u; info->channels=2u; info->bits=16u;
    return M2_OK;
}
int m2_import(const struct m2_file_ops *op, void *ctx, const char *path,
              uint8_t *pcm, uint32_t capacity, struct m2_pcm_info *out) {
    int owned=0,e; uint64_t bytes=0; struct m2_pcm_info info={0};
    struct stream s={op,ctx,0};
    if (!op || !op->open || !op->size || !op->read || !op->close ||
        !path || !pcm || !out || !capacity) return M2_ARGUMENT;
    if (cancelled(&s)) return M2_CANCELLED;
    e=op->open(ctx,path,&owned) ? M2_OPEN:M2_OK;
    if (!e && !owned) e=M2_OPEN;
    if (!e && cancelled(&s)) e=M2_CANCELLED;
    if (!e && op->size(ctx,&bytes)) e=M2_SIZE;
    if (!e) e=parse(&s,bytes,pcm,capacity,&info);
    if (owned && op->close(ctx) && !e) e=M2_CLOSE;
    if (!e && cancelled(&s)) e=M2_CANCELLED;
    if (!e) *out=info;
    return e;
}
