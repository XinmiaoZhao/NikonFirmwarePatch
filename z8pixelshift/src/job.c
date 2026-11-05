/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "job.h"
#include "nefx.h"
#include "group.h"
#include "af_window.h"
#include "io_pipe.h"

#define HEADER_BYTES 384u
#define RECORD_BYTES 192u
#define CONFIG_MAX (HEADER_BYTES + RECORD_BYTES * PSM_MAX_FRAMES)
/* PS7: output batches of 512 KiB (PS6 256 KiB), still below the stock 0x88000 whole-cache maintenance threshold */
#define OUT_BYTES 0x80000u
/* PS7: each decoder reads 256 KiB at a time (PS6 64 KiB); if the heap cannot give the caches of all frames at once,
   PS6's 64 KiB */
#define CACHE_LARGE 0x40000u
#define CACHE_SMALL 0x10000u
#define LOG_BYTES 0x10000u
/* PS6: input files open at once, counting the one a reopening read holds. In QEMU the stock open refused the 31st
   file open at the same time (0x80000901, first-build run q32-sd-beside-8); the body has run 16 inputs plus the
   output (298NCZ_8). A group of more than INPUT_HANDLES frames keeps INPUT_HANDLES - 1 open; its other frames are
   opened, read and closed again for every read of their decoder. 4, 8 and 16 frames keep every handle. */
#define INPUT_HANDLES 16u

/* PS7: per-step times of the group being merged */
typedef struct {
    const psm_platform *platform;
    psm_times *times;
    uint32_t in_rows;
} job_clock;

typedef struct {
    const psm_platform *platform;
    job_clock *clock;
    int fd;
    const char *path;
    uint32_t bytes;
    uint32_t reopen;                        /* PS6: no handle kept; read_bridge opens the file per read */
} input_handle;

typedef struct {
    const psm_platform *platform;
    job_clock *clock;
    int fd;
    uint8_t *buffer;
    uint32_t offset, used;
} output_handle;

typedef struct {
    psm_plan plan;
    psm_metadata selected[PSM_MAX_FRAMES];
    uint32_t sizes[PSM_MAX_FRAMES];
    psm_nef nefs[PSM_MAX_FRAMES];
    input_handle handles[PSM_MAX_FRAMES];
    char paths[PSM_MAX_FRAMES][128];
    psm_times times;
    job_clock clock;
    /* PS1: read buffers own whole cache lines (they are cleaned and invalidated around reads) */
    uint8_t config[(CONFIG_MAX + 63u) & ~63u] __attribute__((aligned(64)));
    uint8_t probe_cache[PSM_SCAN_CACHE] __attribute__((aligned(64)));
    uint8_t out_buffer[OUT_BYTES] __attribute__((aligned(64)));
    int32_t fast[1u << PSM_FAST_BITS];
    char final_path[128];
} card_job;

static uint64_t now(const psm_platform *p)
{
    return p->ticks ? p->ticks(p->context) : 0;
}

static void *align64(void *pointer)
{
    return (void *)(((uintptr_t)pointer + 63u) & ~(uintptr_t)63u);
}

static uint32_t get16(const uint8_t *p)
{
    return p[0] | ((uint32_t)p[1] << 8);
}

static uint32_t get32(const uint8_t *p)
{
    return p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void clear(void *pointer, uint32_t size)
{
    uint8_t *p = pointer;
    while (size--)
        *p++ = 0;
}

static uint32_t length(const char *text)
{
    uint32_t count = 0;
    while (text[count])
        ++count;
    return count;
}

static int same_path(const char *a, const char *b)
{
    while (*a && *b) {
        int x = *a++, y = *b++;
        if (x >= 'a' && x <= 'z') x -= 32;
        if (y >= 'a' && y <= 'z') y -= 32;
        if (x != y) return 0;
    }
    return *a == *b;
}

static int path_valid(const uint8_t *p, uint8_t drive)
{
    uint32_t i = 3, component = 0;
    if (p[0] != drive || p[1] != ':' || p[2] != '\\')
        return 0;
    while (i < 128 && p[i]) {
        uint8_t c = p[i++];
        if (c == '\\') {
            if (!component) return 0;
            component = 0;
            continue;
        }
        if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
              (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.'))
            return 0;
        if (c == '.' && !component)
            return 0;
        ++component;
    }
    if (i == 128 || !component)
        return 0;
    for (; i < 128; ++i) {
        if (p[i]) return 0;
    }
    return 1;
}

uint32_t psm_crc32(const void *data, uint32_t size, uint32_t previous)
{
    static const uint32_t table[8][256] = {
#include "crc32_slice8.inc"
    };
    const uint8_t *p = data;
    uint32_t value = previous ^ 0xFFFFFFFFu;
    while (size >= 8) {
        uint32_t a = value ^ get32(p), b = get32(p + 4);
        value = table[7][a & 255] ^ table[6][(a >> 8) & 255] ^
                table[5][(a >> 16) & 255] ^ table[4][a >> 24] ^
                table[3][b & 255] ^ table[2][(b >> 8) & 255] ^
                table[1][(b >> 16) & 255] ^ table[0][b >> 24];
        p += 8;
        size -= 8;
    }
    while (size--) value = (value >> 8) ^ table[0][(value ^ *p++) & 255u];
    return value ^ 0xFFFFFFFFu;
}

static int parse_config(card_job *j, uint32_t bytes, uint8_t drive)
{
    static const uint8_t magic[16] = {'Z','8','P','S','M','E','R','G','E','v','1',0,0,0,0,0};
    const uint8_t *c = j->config;
    psm_plan *p = &j->plan;
    uint32_t crc;
    for (uint32_t i = 0; i < 16; ++i) {
        if (c[i] != magic[i]) return PSM_BAD_CONFIG;
    }
    if (get32(c + 16) != 1 || get32(c + 20))
        return PSM_BAD_CONFIG;
    p->group_id = get32(c + 24) | ((uint64_t)get32(c + 28) << 32);
    p->frame_count = get32(c + 32);
    if (p->frame_count > PSM_MAX_FRAMES || bytes != HEADER_BYTES + p->frame_count * RECORD_BYTES)
        return PSM_BAD_CONFIG;
    crc = psm_crc32(c, 380, 0);
    crc = psm_crc32(c + HEADER_BYTES, bytes - HEADER_BYTES, crc);
    if (crc != get32(c + 380))
        return PSM_BAD_CONFIG;
    for (uint32_t i = 0; i < 3; ++i) {
        uint32_t numerator = get32(c + 64 + 8 * i);
        uint32_t denominator = get32(c + 68 + 8 * i);
        if (!numerator || !denominator || numerator > 1000000 || denominator > 1000000)
            return PSM_BAD_CONFIG;
    }
    if (!path_valid(c + 88, drive) || !path_valid(c + 216, drive) ||
        same_path((const char *)c + 88, (const char *)c + 216))
        return PSM_BAD_CONFIG;
    for (uint32_t i = 344; i < 380; ++i) {
        if (c[i]) return PSM_BAD_CONFIG;
    }
    p->sensor_width = get32(c + 36);
    p->sensor_height = get32(c + 40);
    p->scale = get32(c + 44);
    p->x0 = (int32_t)get32(c + 48);
    p->y0 = (int32_t)get32(c + 52);
    p->width = get32(c + 56);
    p->height = get32(c + 60);
    for (uint32_t i = 0; i < p->frame_count; ++i) {
        const uint8_t *r = c + HEADER_BYTES + i * RECORD_BYTES;
        psm_frame *f = &p->frames[i];
        f->frame_id = get32(r);
        f->dx2 = (int32_t)get32(r + 4);
        f->dy2 = (int32_t)get32(r + 8);
        if (!path_valid(r + 40, drive) || same_path((const char *)r + 40, (const char *)c + 88) ||
            same_path((const char *)r + 40, (const char *)c + 216))
            return PSM_BAD_CONFIG;
        for (uint32_t k = 0; k < i; ++k) {
            if (same_path((const char *)r + 40,
                          (const char *)c + HEADER_BYTES + k * RECORD_BYTES + 40)) {
                psm_group_reject(10, i, k, (const char *)r + 40);
                return PSM_BAD_GROUP;
            }
        }
        for (uint32_t k = 0; k < 4; ++k) {
            f->black[k] = (uint16_t)get16(r + 16 + 2 * k);
            f->white[k] = (uint16_t)get16(r + 24 + 2 * k);
            f->cfa[k] = r[32 + k];
        }
        for (uint32_t k = 168; k < RECORD_BYTES; ++k) {
            if (r[k]) return PSM_BAD_CONFIG;
        }
    }
    return psm_validate(p);
}


static int read_bridge(void *context, uint32_t offset, void *out, uint32_t bytes)
{
    input_handle *h = context;
    const psm_platform *p = h->platform;
    psm_times *t = h->clock->times;
    uint64_t t0 = now(p), spent;
    uint32_t size = 0;
    int fd, status;
    if (h->fd >= 0) {
        status = p->read_at(p->context, h->fd, offset, out, bytes);
    } else if (!h->reopen) {
        return 1;
    } else {
        /* PS6: a frame without a kept handle; its length must still be the one opened before */
        ++t->reopens;
        fd = p->open(p->context, h->path, &size);
        if (fd < 0) return 1;
        status = size != h->bytes || p->read_at(p->context, fd, offset, out, bytes);
        if (p->close(p->context, fd)) status = 1;
    }
    spent = now(p) - t0;
    t->read += spent;
    if (h->clock->in_rows) t->read_rows += spent;
    ++t->reads;
    t->read_bytes += bytes;
    return status;
}

static int row_bridge(void *context, uint32_t frame, uint32_t row, uint16_t *out, uint32_t width)
{
    card_job *j = context;
    uint64_t t0 = now(j->clock.platform);
    int status = psm_nef_row(&j->nefs[frame], row, out, width);
    j->times.decode += now(j->clock.platform) - t0;
    psm_nef *n=&j->nefs[frame];input_handle *h=&j->handles[frame];
    if(!status&&h->platform->prefetch&&n->cursor>=n->cache_offset&&
       n->cursor-n->cache_offset>=n->cache_bytes/2u){
        uint32_t off=n->cache_offset+n->cache_bytes;
        if(off<n->strip_offset+n->strip_bytes){
            uint32_t bytes=n->file.size-off;if(bytes>n->cache_size)bytes=n->cache_size;
            h->platform->prefetch(h->platform->context,h->fd,off,bytes);
        }
    }
    return status;
}

static int cancel_bridge(void *context)
{
    card_job *j = context;
    const psm_platform *p = j->clock.platform;
    return p->cancelled && p->cancelled(p->context);
}

static int out_flush(output_handle *o)
{
    uint64_t t0, spent;
    int failed;
    if (!o->used) return 0;
    t0 = now(o->clock->platform);
    failed = o->platform->write_at(o->platform->context, o->fd, o->offset, o->buffer, o->used);
    spent = now(o->clock->platform) - t0;
    o->clock->times->write += spent;
    if (o->clock->in_rows) o->clock->times->write_rows += spent;
    ++o->clock->times->writes;
    o->clock->times->write_bytes += o->used;
    if (failed) return 1;
    o->used = 0;
    return 0;
}

/* Freestanding ARM code has no libc memcpy and deliberately uses general registers only.
   Copy aligned words without imposing uint64_t effective-type aliasing on byte buffers. */
static void out_copy(uint8_t *dst, const uint8_t *src, uint32_t bytes)
{
    typedef uint64_t alias_word __attribute__((may_alias));
    if ((((uintptr_t)dst | (uintptr_t)src) & 7u) == 0) {
        while (bytes >= 8) {
            *(alias_word *)dst = *(const alias_word *)src;
            dst += 8;
            src += 8;
            bytes -= 8;
        }
    }
    while (bytes--) *dst++ = *src++;
}

static int out_bridge(void *context, uint32_t offset, const void *data, uint32_t bytes)
{
    output_handle *o = context;
    const uint8_t *src = data;
    /* A random header/map write must follow all previous buffered writes in file order. */
    if (o->used && offset != o->offset + o->used && out_flush(o)) return 1;
    while (bytes) {
        uint32_t n = OUT_BYTES - o->used;
        if (n > bytes) n = bytes;
        if (!o->used) o->offset = offset;
        if (o->buffer + o->used != src) out_copy(o->buffer + o->used, src, n);
        o->used += n;
        offset += n;
        src += n;
        bytes -= n;
        if (o->used == OUT_BYTES && out_flush(o)) return 1;
    }
    return 0;
}

static int ends_with(const char *path, const char *extension)
{
    uint32_t a = length(path), b = length(extension);
    if (a <= b) return 0;
    return same_path(path + a - b, extension);
}

/* PS1: the configured output name, or the first free NAME_2 .. NAME_99 of it. */
static int choose_output(card_job *j, const psm_platform *p)
{
    const char *want = (const char *)j->config + 88;
    uint32_t n = length(want), dot = n;
    for (uint32_t k = n; k > 3; --k) {
        if (want[k - 1] == '\\') break;
        if (want[k - 1] == '.') {
            dot = k - 1;
            break;
        }
    }
    for (uint32_t i = 0; i <= n; ++i)
        j->final_path[i] = want[i];
    if (!p->exists(p->context, j->final_path))
        return PSM_OK;
    if (n + 3 >= sizeof(j->final_path))
        return PSM_OUTPUT_EXISTS;
    for (uint32_t number = 2; number < 100; ++number) {
        uint32_t at = dot;
        j->final_path[at++] = '_';
        if (number >= 10) j->final_path[at++] = (char)('0' + number / 10);
        j->final_path[at++] = (char)('0' + number % 10);
        for (uint32_t i = dot; i <= n; ++i)
            j->final_path[at++] = want[i];
        if (!p->exists(p->context, j->final_path))
            return PSM_OK;
    }
    return PSM_OUTPUT_EXISTS;
}

/* Read-only observation points: a frame opened and checked (no whole-file read since PS7), a group finished. */
__attribute__((noinline,used)) void psm_frame_opened(uint32_t frame, uint32_t bytes, uint32_t cache) {
    __asm__ volatile("" : : "r"(frame), "r"(bytes), "r"(cache) : "memory");
}
__attribute__((noinline,used)) void psm_group_done(uint32_t index, uint32_t status, uint32_t rows) {
    __asm__ volatile("" : : "r"(index), "r"(status), "r"(rows) : "memory");
}

/* PS7: one scanned group, from its open frames to the renamed output. PS6's psm_card_job without the whole-file
   read pass: each frame is opened once, its metadata read and compared with the scan, its decoder set up. */
static int merge_group(const psm_platform *p, const psm_scan *s, const psm_group *g, card_job *j,
                       uint32_t *rows_done, void *preferred_cache, uint32_t cache_size)
{
    void *scratch = 0, *nx_memory = 0, *cache_memory = preferred_cache, *af_memory = 0;
    ps8_af_window af_window;
    nefx *nx = 0;
    uint8_t *packed, *caches;
    uint16_t *rgb;
    const char *temporary;
    uint32_t config_size = 0, opened = 0, scratch_bytes, n = g->count, row = 0;
    int status = PSM_BAD_GROUP, created = 0;
    uint64_t t0 = now(p), t1;
    output_handle out;
    psm_times *t = &j->times;
    clear(t, sizeof(*t));
    j->clock.in_rows = 0;
    out.platform = p;
    out.clock = &j->clock;
    out.fd = -1;
    out.buffer = j->out_buffer;
    out.used = out.offset = 0;
    for (uint32_t i = 0; i < PSM_MAX_FRAMES; ++i) {
        clear(&j->handles[i], sizeof(j->handles[i]));
        j->handles[i].fd = -1;
    }
    if (p->progress) p->progress(p->context, 0, 0);
    t->cache_bytes = cache_size;
    if(!cache_memory)cache_memory = p->allocate(p->context, n * cache_size + 64u);
    if (!cache_memory) {
        t->memory_stage=1;t->memory_bytes=n*cache_size+64u;
        status = PSM_NO_MEMORY;
        goto finished;
    }
    caches = align64(cache_memory);
    for (uint32_t i = 0; i < n; ++i) {
        uint32_t bytes = 0;
        psm_file file;
        input_handle *h = &j->handles[i];
        psm_nef *nef = &j->nefs[i];
        if (p->cancelled && p->cancelled(p->context)) {
            status = PSM_CANCELLED;
            goto finished;
        }
        /* PS4 step, PS7 meaning: opening and checking frame i of n */
        PSM_PHASE(p, PSM_PHASE_READ, (i + 1) | (n << 8), 100u * i / n);
        status = PSM_BAD_GROUP;
        if (psm_frame_path(s, g, i, j->paths[i])) goto finished;
        h->platform = p;
        h->clock = &j->clock;
        h->path = j->paths[i];
        h->fd = p->open(p->context, h->path, &bytes);
        status = PSM_READ_ERROR;
        if (h->fd < 0) goto finished;
        ++opened;
        h->bytes = j->sizes[i] = bytes;
        if (bytes != s->frames[g->frames[i]].bytes || bytes >= 0x80000000u) {
            psm_group_reject(3, bytes, s->frames[g->frames[i]].bytes, h->path);
            status = PSM_BAD_GROUP;
            goto finished;
        }
        status = psm_probe_metadata(p, h->fd, bytes, &j->selected[i], j->probe_cache);
        if (status) goto finished;
        if (psm_crc32(&j->selected[i], sizeof(psm_metadata), 0) != s->frames[g->frames[i]].metadata) {
            psm_group_reject(11, i, j->selected[i].index, h->path);
            status = PSM_BAD_GROUP;
            goto finished;
        }
        clear(nef, sizeof(*nef));
        nef->cache = caches + i * cache_size;
        nef->cache_size = cache_size;
        nef->fast = j->fast;
        file.read_at = read_bridge;
        file.context = h;
        file.size = bytes;
        status = psm_nef_open(nef, &file);
        if (status) goto finished;
        psm_frame_opened(i, bytes, cache_size);
        if (!p->io_mode && n > INPUT_HANDLES && i >= INPUT_HANDLES - 1u) {
            /* PS6: release the handle; the decoder's reads reopen the file (read_bridge) */
            status = PSM_READ_ERROR;
            if (p->close(p->context, h->fd)) goto finished;
            h->fd = -1;
            h->reopen = 1;
        }
    }
    status = psm_group_config(s, g, j->selected, j->sizes, j->config, &config_size);
    if (status) goto finished;
    status = parse_config(j, config_size, g->card);
    if (status) goto finished;
    temporary = (const char *)j->config + 216;
    /* PS2: only NEFX is supported */
    if (!ends_with((const char *)j->config + 88, ".NEFX") || j->plan.frame_count != n ||
        j->plan.frames[0].frame_id != 0) {
        status = PSM_BAD_CONFIG;
        goto finished;
    }
    for (uint32_t i = 0; i < n; ++i) {
        if (j->nefs[i].width != j->plan.sensor_width || j->nefs[i].height != j->plan.sensor_height) {
            status = PSM_BAD_GROUP;
            goto finished;
        }
        for (uint32_t k = 0; k < 4; ++k) {
            if (j->nefs[i].cfa[k] != j->plan.frames[i].cfa[k]) {
                status = PSM_BAD_GROUP;
                goto finished;
            }
        }
    }
    PSM_PHASE(p, PSM_PHASE_NAME, 0, 0);
    status = choose_output(j, p);
    if (status) goto finished;
    /* PS1: a temporary file left by an interrupted run is removed instead of blocking every later run */
    if (p->exists(p->context, temporary)) {
        p->remove(p->context, temporary);
        if (p->exists(p->context, temporary)) {
            status = PSM_OUTPUT_EXISTS;
            goto finished;
        }
    }
    PSM_PHASE(p, PSM_PHASE_SETUP, 0, 0);
    scratch_bytes = (uint32_t)psm_scratch_size(&j->plan);
    scratch = p->allocate(p->context, scratch_bytes + j->plan.width * 6u + 16u);
    if (!scratch) {
        t->memory_stage=2;t->memory_bytes=scratch_bytes+j->plan.width*6u+16u;
        status = PSM_NO_MEMORY;
        goto finished;
    }
    /* PS7: rgb is the merge accumulator, cleared with 64-bit stores */
    rgb = (uint16_t *)(((uintptr_t)scratch + scratch_bytes + 7u) & ~(uintptr_t)7u);
    uint32_t lag = n == 4 || n == 16 ? j->plan.scale : 0;
    if (lag) {
        size_t bytes=ps8_af_window_bytes(&j->plan);
        af_memory=p->allocate(p->context,(uint32_t)bytes+64u);
        if (!af_memory) {t->memory_stage=3;t->memory_bytes=(uint32_t)bytes+64u;status=PSM_NO_MEMORY;goto finished;}
        status=ps8_af_window_init(&af_window,&j->plan,align64(af_memory),bytes);
        if (status) goto finished;
    }
    {
        /* PS1: the first frame supplies every tag, preview and the layout of the NEFX */
        psm_file file;
        nx_memory = p->allocate(p->context, sizeof(nefx) + 64u);
        if (!nx_memory) {
            t->memory_stage=4;t->memory_bytes=sizeof(nefx)+64u;
            status = PSM_NO_MEMORY;
            goto finished;
        }
        nx = align64(nx_memory);
        file.read_at = read_bridge;
        file.context = &j->handles[0];
        file.size = j->handles[0].bytes;
        status = nefx_plan(nx, &file, j->plan.width, j->plan.height, j->plan.scale, j->plan.frame_count);
        if (status) goto finished;
    }
    if (nx->row_bytes > OUT_BYTES) {
        status = PSM_BAD_PLAN;
        goto finished;
    }
    PSM_PHASE(p, PSM_PHASE_CREATE, 0, 0);
    out.fd = p->create(p->context, temporary);
    if (out.fd < 0) {
        status = PSM_WRITE_ERROR;
        goto finished;
    }
    created = 1;
    PSM_PHASE(p, PSM_PHASE_HEADER, 0, 0);
    status = nefx_header(nx, out_bridge, &out);
    if (status) goto finished;
    /* PS7: the rows start at the beginning of the output buffer, so every packed row is 8-byte aligned */
    if (out_flush(&out)) {
        status = PSM_WRITE_ERROR;
        goto finished;
    }
    t1 = now(p);
    t->open = t1 - t0;
    t0 = t1;
    j->clock.in_rows = 1;
    for (uint32_t source_row=0;source_row<j->plan.height+lag;++source_row) {
        uint64_t m0 = now(p), m1;
        if (p->cancelled && p->cancelled(p->context)) {status=PSM_CANCELLED;goto finished;}
        if (source_row<j->plan.height) {
            uint32_t slot=lag ? source_row%af_window.slots : 0;
            status=psm_merge_row_af(&j->plan,source_row,row_bridge,cancel_bridge,j,scratch,scratch_bytes,
                                   lag ? af_window.rgb[slot] : rgb,lag ? af_window.green[slot] : 0);
            if (status) goto finished;
            if (lag) af_window.row_id[slot]=source_row;
        }
        m1 = now(p);
        t->merge += m1 - m0;
        if (source_row<lag) continue;
        if (lag) {
            status=ps8_af_render(&af_window,&j->plan,row,rgb);
            if (status) goto finished;
            t->af+=now(p)-m1;
        }
        m1=now(p);
        /* Pack raw data straight into the next free part of the output buffer. The NEFX
           writer emits that row before it emits a map update, so a random map write can
           flush the raw bytes without invalidating any still-used row data. */
        if (out.used && (out.offset + out.used != nx->raw_pos + row * nx->row_bytes ||
                         OUT_BYTES - out.used < nx->row_bytes) && out_flush(&out)) {
            status = PSM_WRITE_ERROR;
            goto finished;
        }
        packed = out.buffer + out.used;
        status = nefx_row(nx, row, rgb, packed);
        if (status) goto finished;
        t->pack += now(p) - m1;
        if (p->progress)
            p->progress(p->context, row + 1, j->plan.height);
        ++row;
    }
    j->clock.in_rows = 0;
    t1 = now(p);
    t->rows = t1 - t0;
    t0 = t1;
    if (out_flush(&out)) {
        status = PSM_WRITE_ERROR;
        goto finished;
    }
    for (uint32_t i = 0; i < opened; ++i) {
        if (j->handles[i].fd < 0) continue;
        if (p->close(p->context, j->handles[i].fd)) {
            status = PSM_READ_ERROR;
            goto finished;
        }
        j->handles[i].fd = -1;
    }
    if (p->close(p->context, out.fd)) {
        status = PSM_WRITE_ERROR;
        goto finished;
    }
    out.fd = -1;
    status = PSM_OUTPUT_EXISTS;
    if (p->exists(p->context, j->final_path))
        goto finished;
    /* the merged file is complete from here on: a failed rename keeps it under the temporary name */
    created = 0;
    status = p->rename(p->context, temporary, j->final_path) ? PSM_WRITE_ERROR : PSM_OK;
    t->finish = now(p) - t0;
finished:
    j->clock.in_rows = 0;
    if (out.fd >= 0) p->close(p->context, out.fd);
    /* PS1: no partial output is left behind */
    if (created && status != PSM_OK) p->remove(p->context, (const char *)j->config + 216);
    for (uint32_t i = 0; i < opened; ++i) {
        if (j->handles[i].fd >= 0)
            p->close(p->context, j->handles[i].fd);
        j->handles[i].fd = -1;
    }
    if (nx_memory) p->release(p->context, nx_memory);
    if (scratch) p->release(p->context, scratch);
    if (cache_memory) p->release(p->context, cache_memory);
    if (af_memory) p->release(p->context, af_memory);
    *rows_done = row;
    return status;
}

/* ---- PS7 log: X:\PSMERGE.LOG at the root of the card of the first group merged (else the first card present).
   Each job appends its lines to the last LOG_BYTES of the earlier jobs' (cut at a line start). Times in
   milliseconds of the platform tick counter. ---- */
typedef struct {
    char *text;
    uint32_t used;
    uint64_t hz;
} job_log;

static void lput(job_log *l, const char *s)
{
    while (*s && l->used + 1u < LOG_BYTES) l->text[l->used++] = *s++;
}

static void lnum(job_log *l, uint64_t v)
{
    char b[21];
    uint32_t n = 0;
    do b[n++] = (char)('0' + v % 10u); while (v /= 10u);
    while (n && l->used + 1u < LOG_BYTES) l->text[l->used++] = b[--n];
}

static void lkey(job_log *l, const char *key, uint64_t v)
{
    lput(l, " ");
    lput(l, key);
    lput(l, " ");
    lnum(l, v);
}

static void lms(job_log *l, const char *key, uint64_t ticks)
{
    lkey(l, key, l->hz ? ticks * 1000u / l->hz : ticks);
}

static void lstatus(job_log *l, int status)
{
    lput(l, " status ");
    if (status < 0) {
        lput(l, "-");
        status = -status;
    }
    lnum(l, (uint32_t)status);
}

static void log_group(job_log *l, const psm_scan *s, const psm_group *g)
{
    char path[128];
    uint32_t found = 0;
    for (uint32_t k = 0; k < g->count; ++k) found += (g->mask >> k) & 1u;
    lput(l, " ");
    for (uint32_t k = 0; k < g->count; ++k) {
        if (!psm_frame_path(s, g, k, path)) {
            lput(l, path);
            break;
        }
    }
    lkey(l, "frames", found);
    lput(l, "/");
    lnum(l, g->count);
    lkey(l, "start", g->start);
    lkey(l, "id", g->group);
    lput(l, " time ");
    for (uint32_t k = 0; k < 19; ++k) {
        char c[2] = {g->time[k] == ' ' ? '_' : g->time[k], 0};
        lput(l, c);
    }
    lput(l, g->merged ? " merged" : " unmerged");
    if (g->duplicate) lput(l, " duplicate");
    if (g->status) lstatus(l, g->status);
    else if (!psm_group_mergeable(g)) lput(l, " incomplete");
    lput(l, "\n");
}

static void log_times(job_log *l, const psm_times *t)
{
    lkey(l, "memory_stage", t->memory_stage);
    lkey(l, "memory_bytes", t->memory_bytes);
    lkey(l, "cache_kib", t->cache_bytes / 1024u);
    lms(l, "open_ms", t->open);
    lms(l, "rows_ms", t->rows);
    lms(l, "finish_ms", t->finish);
    lms(l, "merge_ms", t->merge);
    lms(l, "decode_ms", t->decode);
    lms(l, "af_ms", t->af);
    lkey(l, "async", t->io_mode);
    lkey(l, "io_fallback", t->io_fallback);
    lms(l, "io_service_ms", t->io_service);
    lms(l, "input_wait_ms", t->input_wait);
    lms(l, "output_wait_ms", t->output_wait);
    lkey(l, "prefetch_slots", t->io_read_slots);
    lkey(l, "write_buffer_kib", t->io_write_bytes / 1024u);
    lkey(l, "prefetch_hits", t->prefetch_hits);
    lkey(l, "prefetch_misses", t->prefetch_misses);
    lkey(l, "queue_high", t->queue_high);
    lms(l, "pack_ms", t->pack);
    lms(l, "read_ms", t->read);
    lms(l, "read_rows_ms", t->read_rows);
    lms(l, "write_ms", t->write);
    lms(l, "write_rows_ms", t->write_rows);
    lkey(l, "reads", t->reads);
    lkey(l, "read_kib", t->read_bytes / 1024u);
    lkey(l, "reopens", t->reopens);
    lkey(l, "writes", t->writes);
    lkey(l, "write_kib", t->write_bytes / 1024u);
}

/* Rotate [new][old] into [old][new] inside the already reserved log block.
   A single write from offset zero avoids the stock SD append path's observed
   byte shift when a write starts at an odd file offset (native QEMU fixture). */
static void reverse_log(uint8_t *p, uint32_t n)
{
    for (uint32_t i = 0; i < n / 2u; ++i) {
        uint8_t c = p[i]; p[i] = p[n - 1u - i]; p[n - 1u - i] = c;
    }
}

static void write_log(const psm_platform *p, char card, const job_log *l)
{
    char path[] = "A:\\PSMERGE.LOG";
    /* PS9: reserve this with the job log, before attempting the large group.
       Reporting a failed allocation must not require another allocation. */
    uint8_t *old = (uint8_t *)l->text + LOG_BYTES;
    uint32_t size = 0, keep = 0, from = 0;
    int fd;
    path[0] = card;
    if (old && p->exists(p->context, path)) {
        fd = p->open(p->context, path, &size);
        if (fd >= 0) {
            keep = size < LOG_BYTES ? size : LOG_BYTES;
            if (p->read_at(p->context, fd, size - keep, old, keep)) keep = 0;
            p->close(p->context, fd);
            if (keep < size) {
                while (from < keep && old[from] != '\n') ++from;
                if (from < keep) ++from;
            }
        }
        p->remove(p->context, path);
    }
    fd = p->create(p->context, path);
    if (fd >= 0) {
        uint8_t *text = (uint8_t *)l->text;
        uint32_t retained = keep - from;
        /* Destination precedes source, including overlapping large logs. */
        for (uint32_t i = 0; i < retained; ++i) text[l->used + i] = old[from + i];
        reverse_log(text, l->used);
        reverse_log(text + l->used, retained);
        reverse_log(text, l->used + retained);
        p->write_at(p->context, fd, 0, text, l->used + retained);
        p->close(p->context, fd);
    }
}

/* "B:300NCZ_8" (the folder of the first frame; ROOT for the card root) and the last four characters of its stem */
static void group_label(const psm_scan *s, const psm_group *g, char *where, char *frame)
{
    const psm_frame_ref *f = &s->frames[g->frames[0]];
    const char *dir = s->dir_paths[f->dir], *last = dir;
    uint32_t n = 0, stem = length(f->name) - 4u;
    for (const char *c = dir; *c; ++c)
        if (*c == '\\' && c[1]) last = c + 1;
    where[n++] = (char)g->card;
    where[n++] = ':';
    if (last == dir) last = "ROOT";
    while (*last && n < 14) where[n++] = *last++;
    where[n] = 0;
    for (n = 0; n < 4 && n < stem; ++n)
        frame[n] = f->name[stem - (stem < 4 ? stem : 4) + n];
    frame[n] = 0;
}

/* PS7: one job = scan both cards, then the newest unmerged complete group (PSM_MODE_NEWEST) or every unmerged complete
   group, newest first (PSM_MODE_ALL). An error of one group ends the job only when the next group could not do
   better (cancel, write error, no memory); the result is PSM_OK when every target was merged, else the first error. */
static int camera_job(const psm_platform *p, uint32_t mode, const psm_scan *published,
                      const uint16_t *chosen,uint32_t chosen_count,psm_summary *summary)
{
    const psm_scan *s = 0;
    card_job *j = 0;
    void *scan_memory = 0, *job_memory = 0, *log_memory = 0;
    uint16_t targets[PSM_SCAN_GROUPS];
    uint32_t ntargets = 0;
    int status;
    char log_card = 0;
    job_log l = {0, 0, 0};
    uint64_t t0;
    psm_summary local;
    if (!summary) summary = &local;
    clear(summary, sizeof(*summary));
    summary->mode = mode;
    if (!p || !p->allocate || !p->release || !p->open || !p->read_at || !p->create || !p->write_at ||
        !p->close || !p->exists || !p->rename || !p->remove || !p->list || mode > PSM_MODE_ALL)
        return PSM_BAD_PLAN;
    t0 = now(p);
    summary->ticks_per_second = l.hz = p->ticks_per_second ? p->ticks_per_second(p->context) : 0;
    log_memory = p->allocate(p->context, 2u * LOG_BYTES);
    l.text = log_memory;
    if(!published)scan_memory = p->allocate(p->context, sizeof(psm_scan) + 64u);
    if ((!scan_memory&&!published) || !log_memory) {
        status = PSM_NO_MEMORY;
        goto finished;
    }
    s = published?published:align64(scan_memory);
    if(!published)clear((void *)s, sizeof(*s));
    lput(&l, "PS12 AF pixel shift merge\nmode ");
    lput(&l, mode == PSM_MODE_ALL ? "all" : "newest");
    lput(&l, "\nclock_hz ");
    lnum(&l, l.hz);
    lput(&l, "\n");
    status = published?PSM_OK:psm_scan_cards(p,(psm_scan *)s);
    for (uint32_t c = 0; c < 2; ++c) {
        const psm_card_scan *k = &s->cards[c];
        char name[] = "card A";
        name[5] = (char)('A' + c);
        lput(&l, name);
        if (!k->present) {
            lput(&l, " absent\n");
            continue;
        }
        if (!log_card) log_card = (char)('A' + c);
        lkey(&l, "folders", k->dirs);
        lkey(&l, "nef", k->nefs);
        lkey(&l, "ordinary", k->ordinary);
        lkey(&l, "frames", k->candidates);
        lkey(&l, "other", k->other);
        lkey(&l, "refused", k->unattributed);
        if (k->unattributed) {
            lstatus(&l, k->first_status);
            lput(&l, " first ");
            lput(&l, k->first_path);
        }
        lms(&l, "scan_ms", k->ticks);
        lput(&l, "\n");
    }
    if (status) {
        lstatus(&l, status);
        lput(&l, " scan\n");
        goto finished;
    }
    summary->groups = s->ngroups;
    lput(&l, "groups ");
    lnum(&l, s->ngroups);
    lput(&l, "\n");
    for (uint32_t i = 0; i < s->ngroups; ++i) {
        lput(&l, "group ");
        lnum(&l, i + 1u);
        log_group(&l, s, &s->groups[s->order[i]]);
    }
    if(published){
        if(!chosen||!chosen_count||chosen_count>PSM_SCAN_GROUPS||s->ngroups>PSM_SCAN_GROUPS){status=PSM_BAD_PLAN;goto finished;}
        for(uint32_t i=0;i<chosen_count;++i){
            if(chosen[i]>=s->ngroups||!psm_group_mergeable(&s->groups[chosen[i]])){status=PSM_BAD_GROUP;goto finished;}
            for(uint32_t k=0;k<i;++k)if(chosen[i]==chosen[k]){status=PSM_BAD_GROUP;goto finished;}
            targets[i]=chosen[i];
        }
        ntargets=chosen_count;
    }else ntargets=psm_targets(s, mode, targets);
    summary->targets=ntargets;
    if (!s->ngroups) {
        status = PSM_BAD_CONFIG;
        goto finished;
    }
    if (!ntargets) {
        status = PSM_NO_NEW;
        goto finished;
    }
    log_card = (char)s->groups[targets[0]].card;
    job_memory = p->allocate(p->context, sizeof(card_job) + 64u);
    if (!job_memory) {
        lput(&l,"allocation_failed stage 5 bytes ");lnum(&l,sizeof(card_job)+64u);lput(&l,"\n");
        status = PSM_NO_MEMORY;
        goto finished;
    }
    j = align64(job_memory);
    clear(j, sizeof(*j));
    j->clock.platform = p;
    j->clock.times = &j->times;
    psm_nef_fast_table(j->fast);
    status = PSM_OK;
    for (uint32_t i = 0; i < ntargets; ++i) {
        const psm_group *g = &s->groups[targets[i]];
        uint32_t rows = 0;
        int result;
        char where[16], frame[5];
        group_label(s, g, where, frame);
        if (p->group) p->group(p->context, i + 1u, ntargets, where, frame);
        ++summary->attempted;
        /* PS9: a cache allocation succeeding does not prove the complete
           working set will fit. Retry only a NO_MEMORY setup failure: every
           such return precedes create/header/rows, closes the inputs, and frees
           its caches/workspaces. Join the I/O owner before another attempt.
           No decode, I/O error, cancellation or partial output is retried. */
        for(uint32_t attempt=0;attempt<4;++attempt){
            uint32_t cache_size=attempt<3?CACHE_LARGE>>attempt:CACHE_SMALL;
            void *preferred_cache=p->allocate(p->context,g->count*cache_size+64u);
            uint32_t fallback=preferred_cache?(attempt==3?6u:0u):7u;
            ps8_io *pipe=preferred_cache&&attempt<3?ps8_io_begin(p,g->count,&fallback):0;
            const psm_platform *active=pipe?ps8_io_platform(pipe):p;
            j->clock.platform=active;
            result=merge_group(active,s,g,j,&rows,preferred_cache,cache_size);
            if(pipe){int io_status=ps8_io_end(pipe,&j->times);if(io_status&&result!=PSM_CANCELLED)result=io_status;}
            j->times.io_fallback=fallback;
            lput(&l,"setup_attempt ");lnum(&l,attempt+1);lkey(&l,"target",i+1);
            lstatus(&l,result);log_times(&l,&j->times);lput(&l,"\n");
            if(result!=PSM_NO_MEMORY||rows||!j->times.memory_stage||attempt==3||
               (p->cancelled&&p->cancelled(p->context)))break;
        }
        j->clock.platform=p;
        psm_group_done(i, (uint32_t)result, rows);
        lput(&l, "target ");
        lnum(&l, i + 1u);
        lput(&l, "/");
        lnum(&l, ntargets);
        lput(&l, " ");
        if (!psm_frame_path(s, g, 0, j->paths[0])) lput(&l, j->paths[0]);
        lstatus(&l, result);
        if (!result) {
            lput(&l, " output ");
            lput(&l, j->final_path);
        }
        lkey(&l, "rows", rows);
        log_times(&l, &j->times);
        lput(&l, "\n");
        if (!result) {
            ++summary->merged;
            continue;
        }
        if (!summary->first_error) summary->first_error = result;
        if (result == PSM_CANCELLED || result == PSM_WRITE_ERROR || result == PSM_NO_MEMORY || result == PSM_NO_CARD ||
            (p->cancelled && p->cancelled(p->context)))
            break;
    }
    if (p->cancelled && p->cancelled(p->context) && summary->merged < ntargets)
        status = PSM_CANCELLED;
    else if (summary->merged < ntargets)
        status = summary->first_error;
finished:
    summary->ticks = now(p) - t0;
    if (log_memory) {
        lput(&l, "job");
        lstatus(&l, status);
        lkey(&l, "merged", summary->merged);
        lput(&l, "/");
        lnum(&l, summary->targets);
        lms(&l, "ms", summary->ticks);
        lput(&l, "\n");
        if (log_card) write_log(p, log_card, &l);
    }
    if (job_memory) p->release(p->context, job_memory);
    if (scan_memory) p->release(p->context, scan_memory);
    if (log_memory) p->release(p->context, log_memory);
    return status;
}

int psm_camera_job(const psm_platform *p,uint32_t mode,psm_summary *summary){
    return camera_job(p,mode,0,0,0,summary);
}
int ps8_selected_job(const psm_platform *p,const psm_scan *s,const uint16_t *targets,
                     uint32_t count,psm_summary *summary){
    return camera_job(p,PSM_MODE_ALL,s,targets,count,summary);
}
