#ifndef MARK2_IMPORT_H
#define MARK2_IMPORT_H
#include <stdint.h>
#include <stddef.h>

#ifndef M2_STAGED_CONFIRM
#define M2_STAGED_CONFIRM 0
#endif
#if M2_STAGED_CONFIRM
#define M2_IO_BUFFER_BYTES 4096u
#endif

/* Prototype policy, not firmware-wide limits. Platform supplies staging storage. */
#define M2_PCM_MAX 288000u
#define M2_FILE_MAX 524288u
#define M2_SCAN_MAX 512u
enum m2_error {
    M2_OK=0, M2_ARGUMENT, M2_OPEN, M2_SIZE, M2_IO, M2_EOF,
    M2_CANCELLED, M2_CONTAINER, M2_FORMAT, M2_DUPLICATE,
    M2_MISSING, M2_LIMIT, M2_CLOSE, M2_BUSY
};
struct m2_pcm_info {
    uint32_t valid_bytes, play_bytes, frames, rate;
    uint16_t channels, bits;
};
/* Callbacks execute on a serialized menu/background task, never a shot ISR.
 * open must set owned even when post-open stat fails. read reports actual
 * independently; actual may be zero or less than requested on success.
 * No output info is committed before successful close. dst is staging only. */
struct m2_file_ops {
    int (*open)(void *ctx, const char *path, int *owned);
    int (*size)(void *ctx, uint64_t *bytes);
    int (*read)(void *ctx, uint8_t *dst, uint32_t request, uint32_t *actual);
    int (*close)(void *ctx);
    int (*cancelled)(void *ctx);
};
int m2_import(const struct m2_file_ops *, void *, const char *,
              uint8_t *, uint32_t, struct m2_pcm_info *);
/* Laboratory bridge using original 5.32 ROM wrappers. Not a firmware hook. */
int m2_native_import(const char *, uint8_t *, uint32_t, struct m2_pcm_info *);
#if M2_STAGED_CONFIRM
/* Caller owns a dedicated, 64-byte-aligned IO buffer for the entire import.
 * Native reads never target PCM or parser/stack storage in this route. */
int m2_native_import_buffered(const char *, uint8_t *, uint32_t,
                              struct m2_pcm_info *, uint8_t *, uint32_t);
#endif
#endif
