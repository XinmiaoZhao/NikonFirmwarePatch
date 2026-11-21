/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "job.h"
#include "browser.h"
#include "thumbnail.h"

/* These interfaces are pinned to the original C3.11 MAIN SHA-256. */
#define FW_OPEN ((int (*)(const char *,uint32_t,uint32_t))(uintptr_t)0x402DAA4C)
#define FW_CLOSE ((int (*)(int))(uintptr_t)0x402DAAAC)
#define FW_READ ((int (*)(int,void *,uint32_t,uint32_t *))(uintptr_t)0x402DAB4C)
#define FW_WRITE ((int (*)(int,uintptr_t,uint32_t,uint32_t *))(uintptr_t)0x402DABB8)
#define FW_SEEK ((int (*)(int,uint32_t,uint32_t,uint32_t *))(uintptr_t)0x402DAC24)
#define FW_CREATE ((int (*)(const char *,uint32_t))(uintptr_t)0x402DAD04)
#define FW_RENAME ((int (*)(const char *,const char *))(uintptr_t)0x402DAD58)
#define FW_EXISTS ((int (*)(const char *))(uintptr_t)0x402DB1AC)
/* PS1: FS request 0x0E; the stock delete 0x40863BEC calls it, and on 0x80005000 clears the
   attributes with request 0x11 (0x20) and calls it again. 0 = removed. */
#define FW_REMOVE ((int (*)(const char *))(uintptr_t)0x402DADA8)
#define FW_ALLOC ((void *(*)(uint32_t,uint32_t))(uintptr_t)0x40D2C408)
#define FW_FREE ((void (*)(void *))(uintptr_t)0x40D2C448)
#define FW_CLEAN ((void (*)(const void *,uint32_t))(uintptr_t)0x40D2B8B8)
/* PS1: stock dc civac by 64-byte line below 0x88000 bytes (whole-cache clean+invalidate above) */
#define FW_CLEAN_INVALIDATE ((void (*)(const void *,uint32_t))(uintptr_t)0x40D2B9C8)
#define FW_CHILD ((void *(*)(void *,uint32_t,uint32_t))(uintptr_t)0x4050A6F0)
#define FW_SET_TEXT ((void (*)(const char *,uint32_t,uint32_t))(uintptr_t)0x403F2920)
#define FW_SET_CONTENT ((void (*)(void *,uint32_t))(uintptr_t)0x403F645C)
#define FW_CONTENT_KIND ((int (*)(void *,uint32_t,uint32_t))(uintptr_t)0x40325D48)
#define FW_PHOTO_ENTRY ((int (*)(void *))(uintptr_t)0x405D9704)
#define FW_PHOTO_REFRESH ((int (*)(void *))(uintptr_t)0x405D9808)
#define FW_TIMER_KIND ((uint32_t (*)(void))(uintptr_t)0x403884A0)
#define FW_TIMER_HOLD ((void (*)(uint32_t))(uintptr_t)0x403884B8)
#define FW_TIMER_SET ((void (*)(uint32_t))(uintptr_t)0x40388300)
#define FW_GET_SETTING ((uint32_t (*)(uint32_t))(uintptr_t)0x403EC398)
#define FW_SET_SETTING ((void (*)(uint32_t,uint32_t))(uintptr_t)0x403EC39C)
/* PS1: the tail of the stock in-place menu actions (e.g. 0x40577A18): current page, page refresh mark,
   redraw request with the stock predicate 0x403EFE74 (3, 7). */
#define FW_CURRENT_PAGE ((void *(*)(void))(uintptr_t)0x403DBDB4)
#define FW_MARK_PAGE ((void (*)(void *))(uintptr_t)0x403DB7B4)
#define FW_REDRAW ((void (*)(uintptr_t,uint32_t,uint32_t))(uintptr_t)0x403EFED8)
#define FW_REDRAW_PREDICATE 0x403EFE74u

#define FW_LIST ((int (*)(const char *,uint32_t,int (*)(const void *)))(uintptr_t)0x402DB09C)
#define FW_TASK_CREATE ((void (*)(void *,void (*)(void *),uint32_t *))(uintptr_t)0x40D2D498)
#define FW_TASK_START ((void (*)(void *,void *))(uintptr_t)0x40D2D5CC)
#define FW_EVENT_CREATE ((void (*)(void *,uint32_t,uint32_t,const char *))(uintptr_t)0x40D2BC28)
#define FW_EVENT_SET ((void (*)(void *,uint32_t))(uintptr_t)0x40D2BC8C)
#define FW_EVENT_CLEAR ((void (*)(void *,uint32_t))(uintptr_t)0x40D2BCC8)
#define FW_EVENT_WAIT ((int (*)(void *,uint32_t,uint32_t *,uint32_t))(uintptr_t)0x40D2BDAC)
#define FW_SLEEP ((void (*)(uint32_t))(uintptr_t)0x40D2D654)
#define FW_TIMER_START ((int (*)(uint32_t,uint32_t,void (*)(void)))(uintptr_t)0x403D7084)
#define FW_TIMER_CANCEL ((void (*)(uint32_t))(uintptr_t)0x403D7144)
#define FW_CONTAINER ((void *(*)(uint32_t,void *))(uintptr_t)0x4039E810)
#define FW_NODE ((void **(*)(void *,uint32_t))(uintptr_t)0x4032492C)
#define FW_DYNAMIC ((void (*)(void *,uint32_t))(uintptr_t)0x403F621C)
#define FW_BAR ((void (*)(void *,uint32_t))(uintptr_t)0x403F1AD8)
#define FW_DIRTY ((void (*)(void *,uint32_t))(uintptr_t)0x403F62B4)
#define FW_MARK ((void (*)(void *,uintptr_t))(uintptr_t)0x4039E848)
#define FW_TRANSITION ((void (*)(uint32_t,uint32_t))(uintptr_t)0x403AD6A4)
#define FW_SCREEN ((void (*)(uint32_t,uint32_t))(uintptr_t)0x403F0790)
#define FW_DRAW_IMAGE ((void (*)(const void *))(uintptr_t)0x402EA024)
#define FW_DRAW_FINISH ((void (*)(void))(uintptr_t)0x402E76D4)
#define FW_DRAW_SIZE ((uint32_t (*)(void))(uintptr_t)0x4031E3D8)
#define FW_TEXT_SIZE ((int (*)(void *,int16_t *))(uintptr_t)0x4031E430)
#define FW_ORIENTATION ((uint32_t (*)(void))(uintptr_t)0x4038D658)
#define FW_RECT ((void (*)(void *,const int16_t *))(uintptr_t)0x4031E2A8)
#define FW_LIST_LAYOUT ((void (*)(void *))(uintptr_t)0x403AE874)
#define FW_VIEW_LAYOUT ((void (*)(void *))(uintptr_t)0x403AEB38)
#define FW_SCROLLBAR ((void (*)(void *))(uintptr_t)0x403AEC24)
#define FW_ROW_DRAW ((int (*)(void *,void *))(uintptr_t)0x4031F060)
#define FW_ROW_DISABLE ((void (*)(void *,uint32_t,uint32_t))(uintptr_t)0x403B1ED0)
#define FW_ROW_UP ((void (*)(void *,void *))(uintptr_t)0x403B1424)
#define FW_ROW_DOWN ((void (*)(void *,void *))(uintptr_t)0x403B1354)
#define FW_ROW_COUNT ((uint32_t (*)(void *))(uintptr_t)0x403AFED4)
#define FW_ROW_FOCUS ((void (*)(void *,uint32_t,uint32_t))(uintptr_t)0x403AFF78)
#define FW_VIEW_ID ((uint32_t (*)(uint32_t))(uintptr_t)0x403F0DB8)
#define FW_VIEW_SET ((void (*)(uint32_t,const void *))(uintptr_t)0x4039ECC4)
#define FW_VIEW_RECT ((void (*)(uint32_t,void *))(uintptr_t)0x4039ED6C)
#define FD_LIMIT 40u
#define MERGE_ITEM 0x2C13u
/* PS7: row 45's OK opens a submenu (stock shell state 0x1D, build_ps7.py) whose two rows start the newest unmerged
   group (psm_menu_action) or every unmerged group (psm_menu_action_all) on this progress page. */
#define MENU_DELAY_SETTING 0x0200171Eu
/* Leaving the busy page (half shutter: GUI kind 2, enabled by the stock retouch-progress input profile 0x11)
   waits for the worker as the stock retouch completion waits for its mode events: at most 2000 ms. */
#define EXIT_WAIT_POLLS 200u
#define EXIT_WAIT_MS 10u

/* PS11: row 45 has no value column (as the stock "Auto capture" row 46); results stay on the progress page and
   in the group browser. */
#include "ui_strings.h"
#define FW_LANGUAGE ((uint32_t (*)(void))(uintptr_t)0x4032DB54)
#define FW_SET_WIDE ((void (*)(const uint16_t *,uint32_t,uint32_t))(uintptr_t)0x403F2A58)
#define FW_BIND_TEXT ((int (*)(void *,uint32_t,uint32_t))(uintptr_t)0x4031E178)
#define FW_ATTACH_CHILD ((int (*)(void *,void *))(uintptr_t)0x403F19EC)
#define FW_TEXT_FONT ((uint32_t (*)(uint32_t,uint32_t))(uintptr_t)0x4032E19C)
#define DYNAMIC_FONTS 0xA032BF0C8ull
static uint32_t ui_language(void){uint32_t n=FW_LANGUAGE();return n==8?1u:n==9?2u:0u;}
static const char *ui_label(uint32_t id){return ps9_labels[ui_language()][id];}
static const char *ui_status(uint32_t id){return ps9_status[ui_language()][id<19?id:1];}
static int ui_equal(const void *a,const void *b,unsigned bytes){
    const uint8_t *x=a,*y=b;for(unsigned i=0;i<bytes;++i)if(x[i]!=y[i])return 0;return 1;
}
static void ui_set_menu_text(const char *text,uint32_t slot,uint32_t font){
    uint16_t wide[25];
    if(!ps9_utf16(text,wide)){wide[0]='?';wide[1]=0;}
    FW_SET_WIDE(wide,slot,font);
    /* Match the menu label's language family while preserving preset size and spacing. */
    *(uint8_t *)(uintptr_t)(DYNAMIC_FONTS+16ull*font)=(uint8_t)FW_TEXT_FONT(FW_LANGUAGE(),0x8ae);
}
static void ui_set_text(const char *text,uint32_t slot,uint32_t font){
    if(ui_language())ui_set_menu_text(text,slot,font);
    else FW_SET_TEXT(text,slot,font);
}
static void ui_bind_text(void *node,uint32_t slot){
    /* The generic 40325D48 setter refuses 3 -> 0, so it cannot switch an
       ASCII resource to wide text. The stock 4031E178 path explicitly permits
       reset-to-0, releases the old glyph object, then binds kind 3 or 4. */
    FW_BIND_TEXT(node,0,0);FW_BIND_TEXT(node,slot,ui_language()?4:3);
}
/* PS5: a posted job that no worker took within GIVEUP_POLLS (firmware-only status, not in psm.h). */
#define STATUS_BUSY 17u
#define STATUS_COUNT 19u

typedef struct {
    int fd;
    uint32_t position;
} native_file;

typedef struct {
    native_file files[FD_LIMIT];
    uint32_t cancel_polls, rows, total;
    uint32_t phase, phase_first, phase_second; /* PS4: last step reported before the first row */
    uint32_t serial;                           /* PS5: the job this worker took */
    char drive;
    psm_list_fn listing;
    void *listing_context;
} native_context;
/* PS5: this page is zeroed by the cold-start ROM -> RAM copy only. An ordinary power OFF/ON is a warm start
   (stock loader 0x41184CF0 with W1 != 0 skips the copy): the page survives, while the OS and every task start
   again. PS4 kept "worker task created" here and, after a warm start, posted jobs to a task that no longer
   existed (body runs: "Starting" / "Stopping" for good). Nothing here is trusted across a power cycle now: each
   job gets a number (serial) that a live worker must take (claimed, compare-and-swap); the GUI creates a worker
   when the last one is not in the stock task registry, or when nobody takes the job within CLAIM_POLLS. */
typedef struct {
    uint32_t magic, state, cancel, status; /* state 0 idle, 1 job posted or running, 2 finished */
    uint32_t serial, claimed;              /* job number posted by the GUI / taken by a worker */
    uint32_t modal, menu_delay, timer_kind, wait_polls;
    void *page;
    void *worker;                          /* task block of the newest worker (heap, never freed or read) */
    uint32_t worker_id, workers, spawned, abandoned;
    native_context context;
    uint32_t gui_polls, timer_result;
    uintptr_t seen_container, seen_text, seen_bar;
    uint32_t exit_polls;
    /* PS7: the row that was confirmed (request) and the mode of the posted job; the worker's progress and result */
    uint32_t request, job_mode;
    uint32_t group_index, group_count, merged, targets, attempted, seconds;
    void *io_control;
    uint32_t io_worker_id,io_waits[2],io_timeout;
    psb_browser browser;
    void *scan_memory,*thumb_memory,*browser_page;
    psm_scan *scan;
    uint8_t *thumb_pixels;
    uint32_t browser_open,operation,return_to_list,thumb_requested,thumb_generation,merge_pending;
    uint32_t thumb_bank,thumb_readers[2],thumb_page[2],thumb_gen[2],thumb_valid[2],thumb_no_memory;
    uint32_t text_length[45],text_format[45];
    char saved_text[45][51];
    uint8_t saved_fonts[12][16];
    uint8_t saved_disabled[24];
    uint32_t native_phase,native_count,native_cursor,window_first;
    psb_identity focus;uint32_t focus_valid,restore_cursor;
    /* Original folder children are 0x118-byte embedded primitive nodes. Keep
       twenty additional leaves in private RAM; native list links and glyph
       caches retain their original ownership. Never allocate a fake pool node. */
    uint8_t status_nodes[20][0x118] __attribute__((aligned(8)));
    void *status_parent[20];
    /* PS11: the merge the progress page posted (modal_serial) and the result published for it. Only merge jobs
       publish here (serial last), so a browser scan or thumbnail job can never show as a finished merge. */
    uint32_t modal_serial;
    struct {uint32_t status,merged,targets,serial;} result;
    /* PS11: a merge that ended without its result on screen (the page was left while it ran, or the power went off):
       review_serial until the next OK on row 45 shows it once (review: this page instance only shows it). leaving:
       the page is left by its own OK/MENU. */
    uint32_t review_serial, review, leaving;
} psm_runtime;
#define PS8_SCAN 1u
#define PS8_THUMB 2u
#define PS8_MERGE 3u
#define BROWSER_TEXT_BASE 0xFCu
#define BROWSER_TEXT_COUNT 45u
#define BROWSER_ROW_BASE 0x4800u
#define BROWSER_ROWS 24u
#define BROWSER_GROUP_ROWS 20u
#define BROWSER_THUMBS 8u
#define R ((psm_runtime *)(uintptr_t)0xA0FFED000ull)
#define PSM_MAGIC 0x42534d50u              /* PS11: do not reuse earlier runtime layouts. */
_Static_assert(sizeof(psm_runtime)<=12288,"reserved private RAM");
_Static_assert(__builtin_offsetof(psm_runtime,io_control)==0x200&&__builtin_offsetof(psm_runtime,io_worker_id)==0x208,"stale-state fixture I/O offsets");
/* Offsets read by host/psm_stream.py and written by the stale-page QEMU images (make_stale_main.py). */
_Static_assert(__builtin_offsetof(psm_runtime,serial)==0x10&&__builtin_offsetof(psm_runtime,page)==0x28&&
               __builtin_offsetof(psm_runtime,worker)==0x30&&__builtin_offsetof(psm_runtime,worker_id)==0x38&&
               __builtin_offsetof(psm_runtime,context)==0x48&&__builtin_offsetof(psm_runtime,gui_polls)==0x1B8&&
               __builtin_offsetof(native_context,rows)==0x144&&__builtin_offsetof(native_context,phase)==0x14C&&
               __builtin_offsetof(native_context,serial)==0x158,"runtime layout");
/* Stock task wrapper 0x40D2D498 registers each task it creates (0x40D2CAA8, kind 0): 16-byte entries for ids
   1..0x300, the id at +0 and the task block at +8. */
#define TASK_REGISTRY 0xA03203E08ull
#define CLAIM_POLLS 10u                    /* 1 s of 100 ms GUI polls before another worker is created */
#define GIVEUP_POLLS 50u                   /* 5 s: the job ends as "Busy" */
static uint32_t load32(uint32_t *p){return __atomic_load_n(p,__ATOMIC_ACQUIRE);}
static void store32(uint32_t *p,uint32_t v){__atomic_store_n(p,v,__ATOMIC_RELEASE);}
static int browser_work(const psm_platform *,psm_summary *);
static void browser_release(void);
static void browser_save_text(int);
static int browser_post(uint32_t);
static void browser_poll(void);
static void psm_worker(void *);
int ps8_browser_refresh(void *);
int ps8_browser_entry(void *);
int ps8_browser_exit(void *);
int ps8_browser_event(void *,uint32_t);


/* Read-only debugger observation point; it preserves the failing return. */
__attribute__((noinline,used)) int psm_io_error(uint32_t operation, uint32_t first,
                                              uint32_t second, uint32_t third)
{
    __asm__ volatile("" : : "r"(operation), "r"(first), "r"(second), "r"(third) : "memory");
    return 1;
}

void *memcpy(void *destination, const void *source, size_t size)
{
    uint8_t *d = destination;
    const uint8_t *s = source;
    while (size--) *d++ = *s++;
    return destination;
}

void *memset(void *destination, int value, size_t size)
{
    uint8_t *d = destination;
    while (size--) *d++ = (uint8_t)value;
    return destination;
}

static void *allocate(void *context, uint32_t bytes)
{
    (void)context;
    return FW_ALLOC(bytes, 0);
}

static void release(void *context, void *pointer)
{
    (void)context;
    FW_FREE(pointer);
}

static int attach_fd(native_context *context, int fd, uint32_t position)
{
    if (fd < 0) return -1;
    for (uint32_t i = 0; i < FD_LIMIT; ++i) {
        if (context->files[i].fd < 0) {
            context->files[i].fd = fd;
            context->files[i].position = position;
            return (int)i;
        }
    }
    FW_CLOSE(fd);
    psm_io_error(1, (uint32_t)fd, FD_LIMIT, 0);
    return -1;
}

static int open_file(void *opaque, const char *path, uint32_t *size)
{
    native_context *context = opaque;
    uint32_t end = UINT32_MAX, beginning = UINT32_MAX;
    int fd = FW_OPEN(path, 0, 0x20);
    if (fd < 0) {
        psm_io_error(2, (uint32_t)fd, 0, 0);
        return -1;
    }
    FW_SEEK(fd, 0, 2, &end);
    FW_SEEK(fd, 0, 0, &beginning);
    if (end >= 0x80000000u || beginning != 0) {
        FW_CLOSE(fd);
        psm_io_error(3, end, beginning, 0);
        return -1;
    }
    *size = end;
    return attach_fd(context, fd, 0);
}

static int seek_to(native_file *file, uint32_t offset)
{
    uint32_t actual = UINT32_MAX;
    if (file->position == offset) return 0;
    FW_SEEK(file->fd, offset, 0, &actual);
    if (actual != offset) return psm_io_error(4, actual, offset, (uint32_t)file->fd);
    file->position = offset;
    return 0;
}

static int read_at(void *opaque, int index, uint32_t offset, void *out, uint32_t bytes)
{
    native_context *context = opaque;
    native_file *file;
    uint32_t count = 0;
    if (index < 0 || index >= (int)FD_LIMIT) return 1;
    file = &context->files[index];
    if (file->fd < 0) return 1;
    if (seek_to(file, offset)) return 1;
    /* PS1: no dirty line may be written back over the transfer, and no stale line may be read after it */
    FW_CLEAN_INVALIDATE(out, bytes);
    {
        int result = FW_READ(file->fd, out, bytes, &count);
        FW_CLEAN_INVALIDATE(out, bytes);
        if (result || count != bytes)
            return psm_io_error(5, (uint32_t)result, count, bytes);
    }
    file->position += count;
    return 0;
}

static int create_file(void *opaque, const char *path)
{
    native_context *context = opaque;
    if (FW_EXISTS(path) >= 0) return -1;
    return attach_fd(context, FW_CREATE(path, 0x20), 0);
}

static int write_at(void *opaque, int index, uint32_t offset, const void *data, uint32_t bytes)
{
    native_context *context = opaque;
    native_file *file;
    uint32_t count = 0;
    if (index < 0 || index >= (int)FD_LIMIT) return 1;
    file = &context->files[index];
    if (file->fd < 0) return 1;
    if (seek_to(file, offset)) return 1;
    FW_CLEAN(data, bytes);
    {
        int result = FW_WRITE(file->fd, (uintptr_t)data, bytes, &count);
        if (result || count != bytes)
            return psm_io_error(7, (uint32_t)result, count, bytes);
    }
    file->position += count;
    return 0;
}

static int close_file(void *opaque, int index)
{
    native_context *context = opaque;
    int result;
    if (index < 0 || index >= (int)FD_LIMIT || context->files[index].fd < 0)
        return 1;
    result = FW_CLOSE(context->files[index].fd);
    if (!result) context->files[index].fd = -1;
    else psm_io_error(6, (uint32_t)result, (uint32_t)context->files[index].fd, 0);
    return result;
}

static int exists(void *opaque, const char *path)
{
    (void)opaque;
    return FW_EXISTS(path) >= 0;
}

static int rename_file(void *opaque, const char *from, const char *to)
{
    (void)opaque;
    if (FW_EXISTS(to) >= 0) return 1;
    return FW_RENAME(from, to);
}

static int remove_file(void *opaque, const char *path)
{
    int result;
    (void)opaque;
    result = FW_REMOVE(path);
    if (result) psm_io_error(8, (uint32_t)result, 0, 0);
    return result != 0;
}

/* Read-only observation point: an entry whose long name is not its 8.3 field (the observer dumps it). */
__attribute__((noinline,used)) void psm_list_entry(const void *entry, uint32_t long_length)
{
    __asm__ volatile("" : : "r"(entry), "r"(long_length) : "memory");
}
/* An entry holds an 8.3 field at +0, the UTF-16LE long name at +0x0E (256 units) and the attributes at +0x20E.
   exFAT keeps long names only, and the 8.3 field is a truncation that can collide: QEMU run s3-repeat11 listed
   DSC_0001_MERGED.NEFX as "DSC_0001.NEF" with the NEFX size. Discovery takes the long name; the 8.3 field only
   when no long name is present. A long name that is not printable ASCII is passed empty (never a candidate).
   PS7: one of up to 31 characters is passed whole (DSC_0001_MERGED_99.NEFX has 23), a longer one as its first 32,
   which discovery skips (PS6 passed 13). */
#define LONG_NAME 0x0Eu
#define NAME_PASSED 32u
static int native_listing(const void *entry) {
    const uint8_t *b=entry;uint64_t bytes=0;char name[NAME_PASSED+1];uint32_t n=0,printable=1;
    for(unsigned i=0;i<8;++i)bytes|=(uint64_t)b[0x218+i]<<(8*i);
    while(n<256){uint32_t ch=b[LONG_NAME+2*n]|(uint32_t)b[LONG_NAME+1+2*n]<<8;if(!ch)break;
        if(ch<0x20||ch>0x7e)printable=0;if(n<NAME_PASSED)name[n]=(char)ch;++n;}
    if(!n){for(;n<13&&b[n];++n)name[n]=(char)b[n];}
    else {
        uint32_t k=0;while(k<13&&k<n&&b[k]==(uint8_t)name[k])++k;
        if(k!=n||(n<13&&b[n]))psm_list_entry(entry,n);
        if(!printable)n=0;
    }
    name[n<NAME_PASSED?n:NAME_PASSED]=0;
    native_context *c=&R->context;
    return c->listing(c->listing_context,name,bytes,b[0x20e]);
}
static int list_files(void *opaque,const char *path,uint32_t attrs,psm_list_fn callback,void *context) {
    native_context *c=opaque;c->listing=callback;c->listing_context=context;
    int result=FW_LIST(path,attrs,native_listing);
    c->listing=0;c->listing_context=0;
    /* End-of-directory is the stock find-next sentinel, not an I/O failure. */
    return result!=0 && (uint32_t)result!=0x80000030u;
}
static int cancelled(void *opaque) {
    native_context *c=opaque;++c->cancel_polls;return load32(&R->cancel)!=0||load32(&R->serial)!=c->serial;
}
/* PS7: the generic timer's virtual count, which the stock kernel reads too (0x40176BBC, its tick at 0x40176C54),
   and its rate (0x40176BD4). */
static uint64_t ticks(void *opaque) {
    uint64_t v;(void)opaque;__asm__ volatile("mrs %0, cntvct_el0" : "=r"(v));return v;
}
static uint64_t ticks_per_second(void *opaque) {
    uint64_t v;(void)opaque;__asm__ volatile("mrs %0, cntfrq_el0" : "=r"(v));return v&0xFFFFFFFFu;
}
/* PS7: the group the job starts (its number and the number of groups); the progress line shows it when merging all.
   The page's title stays the stock "Processing in progress." (QEMU dev3-r2-all: the title node PS1-PS6 wrote,
   0x1332, is not drawn), so the group's folder and name go to PSMERGE.LOG only. */
static void group_report(void *opaque,uint32_t index,uint32_t count,const char *where,const char *frame) {
    (void)opaque;(void)where;(void)frame;
    store32(&R->group_count,count);store32(&R->group_index,index);
}
/* PS4: values first, the step last, so the GUI never pairs a new step with old values. */
__attribute__((noinline,used)) static void phase_report(void *opaque,uint32_t phase,uint32_t first,uint32_t second) {
    native_context *c=opaque;store32(&c->phase_second,second);store32(&c->phase_first,first);store32(&c->phase,phase);
}
__attribute__((noinline,used)) static void progress(void *opaque,uint32_t rows,uint32_t total) {
    native_context *c=opaque;store32(&c->total,total);store32(&c->rows,rows);
}

__attribute__((noinline,used)) int psm_job_complete(int status, uint32_t rows, uint32_t total)
{
    __asm__ volatile("" : : "r"(status), "r"(rows), "r"(total) : "memory");
    return status;
}

__attribute__((noinline,used)) void psm_power_settings(uint32_t original, uint32_t during,
                                                     uint32_t restored)
{
    __asm__ volatile("" : : "r"(original), "r"(during), "r"(restored) : "memory");
}

/* PS5 read-only observation points (the observer records their arguments). */
__attribute__((noinline,used)) void psm_job_posted(uint32_t serial, uint32_t worker_id, uint32_t spawned)
{
    __asm__ volatile("" : : "r"(serial), "r"(worker_id), "r"(spawned) : "memory");
}
__attribute__((noinline,used)) void psm_worker_spawned(int id, uint32_t workers, uint32_t serial)
{
    __asm__ volatile("" : : "r"(id), "r"(workers), "r"(serial) : "memory");
}
__attribute__((noinline,used)) void psm_job_claimed(uint32_t serial, uint32_t previous)
{
    __asm__ volatile("" : : "r"(serial), "r"(previous) : "memory");
}
__attribute__((noinline,used)) void psm_job_unclaimed(uint32_t serial, uint32_t status, uint32_t polls)
{
    __asm__ volatile("" : : "r"(serial), "r"(status), "r"(polls) : "memory");
}
__attribute__((noinline,used)) void psm_job_abandoned(uint32_t serial, uint32_t worker_id, uint32_t abandoned)
{
    __asm__ volatile("" : : "r"(serial), "r"(worker_id), "r"(abandoned) : "memory");
}

/* PS5: the newest worker is alive if the stock task registry still holds its id and task block. A live task
   always does (ids are unique among live tasks), so this never calls a live worker dead. After a warm start it
   says dead unless the registry kept the old entry; the claim timeout in psm_poll covers that case. */
static int worker_alive(void)
{
    uint32_t id = R->worker_id;
    if (!R->worker || id - 1u > 0x2FFu) return 0;
    const uint8_t *entry = (const uint8_t *)(uintptr_t)(TASK_REGISTRY + 16ull * id);
    if(__atomic_load_n((const uint32_t *)entry,__ATOMIC_ACQUIRE)!=id||
       __atomic_load_n((void *const *)(entry+8),__ATOMIC_ACQUIRE)!=R->worker)return 0;
    /* Registry validation makes the 64-byte stock task block safe to read;
       verify its entry as well, in case a warm boot reused both id and address. */
    return *(uintptr_t *)((uint8_t *)R->worker+8)==(uintptr_t)psm_worker;
}

static void psm_worker(void *argument);
/* noinline: its own function, so the build's linear constant walk does not carry a register loaded on the
   success path of spawn_worker (R + 0x3C) into this call, where the compiler forms FW_FREE as FW_ALLOC + 0x40. */
__attribute__((noinline)) static void discard_block(void *block) { FW_FREE(block); }
/* PS5: a new worker in a new heap block (an older worker that may still be alive keeps its own block). */
static int spawn_worker(void)
{
    uint32_t parameters[7];
    void *task = FW_ALLOC(64, 0);
    if (!task) return 0;
    memset(task, 0, 64);
    memset(parameters, 0, sizeof(parameters));
    parameters[0] = 2; parameters[1] = 40; parameters[2] = 32768;
    memcpy((char *)parameters + 12, "PS5Merge", 9);
    FW_TASK_CREATE(task, psm_worker, parameters);
    int id = *(int *)task;
    if (id <= 0) { discard_block(task); return 0; }
    R->worker = task; R->worker_id = (uint32_t)id; ++R->workers;
    FW_TASK_START(task, 0);
    psm_worker_spawned(id, R->workers, load32(&R->serial));
    return 1;
}

/* One persistent I/O task and event object per power-on. Their heap block is
   never reclaimed under a live OS task/registry entry. Per-group pipe buffers
   are separate and are released only after the callback has returned. */
typedef struct {
    uint8_t task[64];
    int32_t event[4];
    void (*function)(void *);
    void *argument;
    uint32_t request,claimed,completed,disabled;
} native_io;
static void native_io_task(void *);
static int native_io_alive(void){
    uint32_t id=R->io_worker_id;
    if(!R->io_control||!id||id>0x300)return 0;
    const uint8_t *e=(const uint8_t *)(uintptr_t)(TASK_REGISTRY+16ull*id);
    if(__atomic_load_n((const uint32_t *)e,__ATOMIC_ACQUIRE)!=id||
       __atomic_load_n((void *const *)(e+8),__ATOMIC_ACQUIRE)!=R->io_control)return 0;
    const uint8_t *task=R->io_control;
    return *(const uintptr_t *)(task+8)==(uintptr_t)native_io_task&&
           (!*(void *const *)(task+0x28)||*(void *const *)(task+0x28)==R->io_control);
}
__attribute__((noinline,used)) void ps8_io_timeout(uint32_t who,uint32_t count){
    __asm__ volatile("" : : "r"(who),"r"(count) : "memory");
}
static void native_io_task(void *argument){
    native_io *c=argument;
    for(;;){
        uint32_t expected=1;
        if(!__atomic_compare_exchange_n(&c->request,&expected,2,0,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE)){
            FW_EVENT_WAIT(c->event,2,0,1000);continue;
        }
        void (*fn)(void *)=c->function;void *arg=c->argument;
        store32(&c->claimed,1);FW_EVENT_SET(c->event,1);
        fn(arg);
        /* No access to arg, including a wake through it, after completed. */
        c->argument=0;c->function=0;store32(&c->request,0);store32(&c->completed,1);FW_EVENT_SET(c->event,1);
    }
}
static int native_io_start(void *context,void (*function)(void *),void *argument){
    (void)context;native_io *c;
    if(!native_io_alive()){
        uint32_t parameters[7]={2,40,16384,0,0,0,0};
        c=FW_ALLOC(sizeof(*c),0);if(!c)return 0;memset(c,0,sizeof(*c));
        memcpy((char *)parameters+12,"PS8IOwrk",8);
        FW_TASK_CREATE(c->task,native_io_task,parameters);
        int id=*(int *)c->task;if(id<=0){discard_block(c);return 0;}
        R->io_control=c;R->io_worker_id=(uint32_t)id;
        FW_EVENT_CREATE(c->event,0,1,"PS8IOevt");
        if(c->event[0]<=0){c->disabled=1;return 0;}
        FW_TASK_START(c->task,c);
    }
    c=R->io_control;if(c->disabled||load32(&c->request))return 0;
    FW_EVENT_CLEAR(c->event,3);store32(&c->claimed,0);store32(&c->completed,0);
    c->function=function;c->argument=argument;store32(&c->request,1);FW_EVENT_SET(c->event,2);
    for(unsigned i=0;i<10&&!load32(&c->claimed);++i)FW_EVENT_WAIT(c->event,1,0,100);
    if(!load32(&c->claimed)){
        uint32_t expected=1;
        if(__atomic_compare_exchange_n(&c->request,&expected,0,0,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE)){
            c->function=0;c->argument=0;return 0; /* revoked before worker ownership */
        }
        while(!load32(&c->claimed))FW_EVENT_WAIT(c->event,1,0,100);
    }
    R->io_waits[0]=R->io_waits[1]=R->io_timeout=0;return 1;
}
static void native_io_join(void *context){
    (void)context;native_io *c=R->io_control;
    while(!load32(&c->completed)){
        if(!FW_EVENT_WAIT(c->event,1,0,1000)){
            ++R->io_waits[0];uint32_t n=load32(&R->io_timeout)+1;store32(&R->io_timeout,n);
            if(n>=30)store32(&R->cancel,1);ps8_io_timeout(2,R->io_waits[0]);
        }else store32(&R->io_timeout,0);
    }
}
static void native_io_wait(void *context,uint32_t who){
    (void)context;native_io *c=R->io_control;
    if(!FW_EVENT_WAIT(c->event,1u<<who,0,1000)){
        ++R->io_waits[who];
        /* Idle I/O wait is normal. A compute wait is a visible timeout and
           requests cancellation, but cannot free a still-owned DMA buffer. */
        if(!who){uint32_t n=load32(&R->io_timeout)+1;store32(&R->io_timeout,n);
            if(n>=30)store32(&R->cancel,1);ps8_io_timeout(who,R->io_waits[who]);}
    }else if(!who)store32(&R->io_timeout,0);
}
static void native_io_wake(void *context,uint32_t who){
    (void)context;native_io *c=R->io_control;FW_EVENT_SET(c->event,1u<<who);
}

/* PS11: the result of merge job `serial` for the progress page; the serial goes last. */
static void publish_result(uint32_t serial,uint32_t status,uint32_t merged,uint32_t targets)
{
    R->result.status=status;R->result.merged=merged;R->result.targets=targets;store32(&R->result.serial,serial);
}

/* PS5: the GUI ends a posted job that no worker has taken; taking it first keeps a late worker out. */
static int settle_unclaimed(uint32_t status)
{
    uint32_t serial = load32(&R->serial), seen = load32(&R->claimed);
    if (seen == serial || !__atomic_compare_exchange_n(&R->claimed, &seen, serial, 0, __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE))
        return 0;
    R->status = status;
    if (serial == R->modal_serial) publish_result(serial, status, 0, 0);
    store32(&R->state, 2);
    psm_job_unclaimed(serial, status, R->wait_polls);
    return 1;
}

/* PS5: a job left posted or running by a worker that no longer exists (it was in an earlier power-on) ends as
   "Stop"; the serial moves on so that a worker never takes or publishes it. */
static void reap_stale(void)
{
    if (R->magic != PSM_MAGIC || load32(&R->state) != 1 || worker_alive()) return;
    uint32_t serial = load32(&R->serial);
    store32(&R->serial, serial + 1);
    R->status = PSM_CANCELLED;
    ++R->abandoned;
    /* PS11: a merge cut by the power going off is shown at the next OK on row 45 as "Stop" */
    if (serial == R->modal_serial && (!R->operation || R->operation == PS8_MERGE)) {
        publish_result(serial, PSM_CANCELLED, 0, 0);
        R->review_serial = serial;
    }
    store32(&R->state, 2);
    psm_job_abandoned(serial, R->worker_id, R->abandoned);
}

/* A job whose page was left (half shutter) finishes without the result page; PS11: its result is in PSMERGE.LOG
   and the group browser (the row has no value column). */
static void settle_row(void)
{
    if (R->magic != PSM_MAGIC || R->modal || load32(&R->state) != 2) return;
    store32(&R->state, 0);
}

int psm_photo_entry(void *state)
{
    int result = FW_PHOTO_ENTRY(state);
    reap_stale();
    settle_row();
    return result;
}

int psm_photo_refresh(void *state)
{
    int result = FW_PHOTO_REFRESH(state);
    reap_stale();
    settle_row();
    return result;
}

static void psm_worker(void *argument) {
    (void)argument;
    for (;;) {
        if(load32(&R->state)!=1){FW_SLEEP(20);continue;}
        /* PS5: take the posted job by its number; another worker or the GUI may have taken it first. */
        uint32_t serial=load32(&R->serial),seen=load32(&R->claimed);
        if(seen==serial||!__atomic_compare_exchange_n(&R->claimed,&seen,serial,0,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE)){FW_SLEEP(20);continue;}
        psm_job_claimed(serial,seen);
        native_context *c=&R->context;psm_platform p;psm_summary summary;
        memset(c,0,sizeof(*c));c->serial=serial;for(unsigned i=0;i<FD_LIMIT;++i)c->files[i].fd=-1;
        memset(&p,0,sizeof(p));p.context=c;p.allocate=allocate;p.release=release;p.open=open_file;
        p.read_at=read_at;p.create=create_file;p.write_at=write_at;p.close=close_file;p.exists=exists;
        p.rename=rename_file;p.remove=remove_file;p.cancelled=cancelled;p.progress=progress;p.list=list_files;p.phase=phase_report;
        p.ticks=ticks;p.ticks_per_second=ticks_per_second;p.group=group_report;
        p.io_start=native_io_start;p.io_join=native_io_join;p.io_wait=native_io_wait;p.io_wake=native_io_wake;
        memset(&summary,0,sizeof(summary));
        int status=R->operation?browser_work(&p,&summary):psm_camera_job(&p,R->job_mode,&summary);
        for(unsigned i=0;i<FD_LIMIT;++i)if(c->files[i].fd>=0)FW_CLOSE(c->files[i].fd);
        if(!R->operation||R->operation==PS8_MERGE)status=psm_job_complete(status,load32(&c->rows),load32(&c->total));
        if(load32(&R->serial)==serial){
            R->merged=summary.merged;R->targets=summary.targets;R->attempted=summary.attempted;
            R->seconds=summary.ticks_per_second?(uint32_t)((summary.ticks+summary.ticks_per_second/2)/summary.ticks_per_second):0;
            if(!R->operation||R->operation==PS8_MERGE)publish_result(serial,(uint32_t)status,summary.merged,summary.targets);
            if(R->operation&&!load32(&R->browser_open))browser_release();
            R->status=(uint32_t)status;store32(&R->state,2);
        }
        /* Permanent sleeping task within one power-on: no object/stack reclamation race. */
    }
}
__attribute__((noinline)) static void modal_text(void *container,uint32_t id,uint32_t slot,const char *text) {
    void **node=FW_NODE(container,id);if(!node||!*node)return;
    ui_set_text(text,slot,0x21f);ui_bind_text(*node,slot);FW_SET_CONTENT(*node,slot);FW_DYNAMIC(*node,1);
}
static char *decimal(char *s,uint32_t v) {
    char b[10];unsigned n=0;do{b[n++]=(char)('0'+v%10);v/=10;}while(v);
    while(n)*s++=b[--n];return s;
}
static char *copy(char *s,const char *t){while(*t)*s++=*t++;return s;}
/* PS4: the step on the progress page, at most 12 characters (PS3's 19-character "Scanning / checking" overran
   the fixed counter box in Chinese menus, where ASCII is drawn monospaced). While running:
   "Starting", "Scan B 1234" (NEF files probed on card B), "Prepare 1" (output name), "Check 2/4" (reading
   frame 2 of 4; the bar shows the read pass), "Prepare 2".."4" (buffers and plan, create, header), "2667/5504".
   After OK/MENU: "Stop " + the same step in short form (S1234, R2/4, P1..P4, the row), or "Stopping". */
/* noinline: its own function, so the build's per-function constant walk does not carry psm_modal_refresh's
   redraw-call register (0x403EFED8 in x8 before its tail call) into this copy loop. */
__attribute__((noinline)) static char *step_text(char *s,uint32_t cancel,uint32_t rows,uint32_t total){
    if(load32(&R->io_timeout))return copy(s,ui_label(UI_WAIT));
    uint32_t phase=load32(&R->context.phase),first=load32(&R->context.phase_first),second=load32(&R->context.phase_second);
    if(cancel){
        if(!total&&!phase)return copy(s,ui_label(UI_STOPPING));
        s=copy(s,ui_label(UI_STOP));
    }
    if(total&&R->job_mode==PSM_MODE_ALL){
        /* PS7, merging all: "2/3 25%" (group 2 of 3, a quarter of its rows) */
        s=decimal(s,load32(&R->group_index));*s++='/';s=decimal(s,load32(&R->group_count));*s++=' ';
        s=decimal(s,rows*100u/total);*s++='%';return s;
    }
    if(total){s=decimal(s,rows);if(!cancel){*s++='/';s=decimal(s,total);}return s;}
    switch(phase){
    case PSM_PHASE_SCAN:
        if(!cancel){s=copy(s,ui_label(UI_SCAN_SHORT));*s++=(char)(first>='A'&&first<='Z'?first:'?');*s++=' ';}else*s++='S';
        return decimal(s,second);
    case PSM_PHASE_READ:
        /* PS7: opening and checking frame i of n (PS4-PS6: "Check", the whole-file read) */
        s=copy(s,cancel?"O":ui_label(UI_OPEN));s=decimal(s,first&255);*s++='/';return decimal(s,first>>8);
    case PSM_PHASE_NAME:return copy(copy(s,cancel?"P":ui_label(UI_PREPARE)),"1");
    case PSM_PHASE_SETUP:return copy(copy(s,cancel?"P":ui_label(UI_PREPARE)),"2");
    case PSM_PHASE_CREATE:return copy(copy(s,cancel?"P":ui_label(UI_PREPARE)),"3");
    case PSM_PHASE_HEADER:return copy(copy(s,cancel?"P":ui_label(UI_PREPARE)),"4");
    default:return copy(s,cancel?"?":ui_label(UI_STARTING));
    }
}
/* PS11: the result line, at most 12 characters: "1/1 Done" when every target was merged; otherwise the status and
   the groups merged ("Stop 0/1", "No mem 2/3"), or the status alone when nothing was tried ("No new"). No seconds
   (PSMERGE.LOG keeps the times). Only the result published for this page's merge is shown; without it the page
   says "Plan?", never "Done" (PS9's "Done - OK" was a zero summary of another job). */
__attribute__((noinline)) static char *result_text(char *e) {
    if(!R->modal_serial||load32(&R->result.serial)!=R->modal_serial)return copy(e,ui_status(PSM_BAD_PLAN));
    uint32_t st=R->result.status,merged=R->result.merged,targets=R->result.targets;
    if(st>=STATUS_COUNT||(st==PSM_OK&&(!targets||merged!=targets)))st=PSM_BAD_PLAN;
    if(!targets)return copy(e,ui_status(st));
    if(st==PSM_OK){e=decimal(e,merged);*e++='/';e=decimal(e,targets);*e++=' ';return copy(e,ui_status(st));}
    e=copy(e,ui_status(st));*e++=' ';e=decimal(e,merged);*e++='/';return decimal(e,targets);
}
/* PS11: the footer button of the stock layout 0x43B8BCD8 (node 0x1341, right-aligned) keeps its resource, frame and
   place; only its stock string changes: 0xAE2 "MENU Cancel" while merging, 0xA99 "OK OK" (zh-CN "确定") once the
   merge has ended. The node's own text kind is kept (0x4031E178 refuses kind changes). */
#define FOOTER_NODE 0x1341u
#define FOOTER_MENU_CANCEL 0xAE2u
#define FOOTER_OK 0xA99u
/* PS11: the dialog frame and title are no nodes: 0x403D3708 draws them from the page's layout (state +0x50 -> page
   record +8 -> resources 0x1E and 0x1F; the title is resource 2's string id). A result shown later uses a copy of the
   stock layout whose only difference is that string ("Last merge result", build_ps11.py), selected by the layout
   pointer of the C5 page record in RAM (0xA028CFA40 = image 0x4BDAA40) before every transition into C5. */
#define PROGRESS_LAYOUT_POINTER ((uint64_t *)(uintptr_t)0xA028CFA48ull)
#define PROGRESS_LAYOUT_STOCK 0x43B8BCD8ull
#ifndef PS11_REVIEW_LAYOUT
#define PS11_REVIEW_LAYOUT 0x409EC800ull
#endif
static void progress_layout(uint32_t review){*PROGRESS_LAYOUT_POINTER=review?PS11_REVIEW_LAYOUT:PROGRESS_LAYOUT_STOCK;}
/* Read-only observation point: the node, the string id asked for, and the node's id and kind before. */
__attribute__((noinline,used)) void ps11_static(void *node,uint32_t text,uint32_t id,uint32_t kind)
{
    __asm__ volatile("" : : "r"(node), "r"(text), "r"(id), "r"(kind) : "memory");
}
__attribute__((noinline)) static void modal_static(void *container,uint32_t which,uint32_t text){
    void **node=FW_NODE(container,which);if(!node||!*node)return;
    uint8_t *n=*node;uint32_t id=*(uint32_t *)(n+8),kind=*(uint32_t *)(n+0xc);
    if(id==text)return;
    ps11_static(n,text,id,kind);FW_BIND_TEXT(n,text,kind);FW_SET_CONTENT(n,text);
}
__attribute__((noinline,used)) int psm_modal_refresh(void *page) {
    if(!page||!R->modal)return 0;
    void *container=FW_CONTAINER(0x4bac,(uint8_t *)page+0x18);R->seen_container=(uintptr_t)container;if(!container)return 0;
    uint32_t rows=load32(&R->context.rows),total=load32(&R->context.total),state=load32(&R->state);
    char text[40];char *end=text;
    if(state!=1) end=result_text(end);
    else end=step_text(end,load32(&R->cancel),rows,total);
    *end=0;
    modal_text(container,0x1332,1,ui_label(UI_TITLE));modal_text(container,0x133f,0,text);
    modal_static(container,FOOTER_NODE,state!=1?FOOTER_OK:FOOTER_MENU_CANCEL);
    uint32_t percent=total?rows*100/total:load32(&R->context.phase)==PSM_PHASE_READ?load32(&R->context.phase_second):0;
    void **bar=FW_NODE(container,0x1334);R->seen_bar=bar?(uintptr_t)*bar:0;if(bar&&*bar)FW_BAR(*bar,percent>100?100:percent);
    void **node=FW_NODE(container,0x133f);R->seen_text=node?(uintptr_t)*node:0;
    /* Stock RAW refresh 0x4055CF14..20 invalidates the enclosing cached container.
       Marking child text/bar alone leaves the first rendered bitmap on screen. */
    *((uint8_t *)container+0xce)=0;FW_DIRTY(container,1);
    FW_MARK((uint8_t *)page+0x18,0x403efe48u);FW_REDRAW(FW_REDRAW_PREDICATE,3,7);return 0;
}
static void psm_poll(void) {
    if(!R->modal)return;
    ++R->gui_polls;
    if(load32(&R->state)==1&&load32(&R->claimed)!=load32(&R->serial)){
        /* PS5: nobody has taken the posted job yet */
        ++R->wait_polls;
        if(R->wait_polls==CLAIM_POLLS&&R->spawned!=load32(&R->serial)){
            if(spawn_worker())R->spawned=load32(&R->serial);else settle_unclaimed(PSM_NO_MEMORY);
        } else if(R->wait_polls>=GIVEUP_POLLS)settle_unclaimed(STATUS_BUSY);
    }
    psm_modal_refresh(R->page);R->timer_result=(uint32_t)FW_TIMER_START(0x1b,100,psm_poll);
}
/* PS11: the browser's merge for this page. A browser job still running (scan, thumbnails) is stopped first, bounded
   as at exit; if it does not stop, the page ends with "Busy" instead of showing that job as the merge. */
static void modal_post(void) {
    uint32_t polls=0;
    if(load32(&R->state)==1){
        store32(&R->cancel,1);settle_unclaimed(PSM_CANCELLED);
        while(load32(&R->state)==1&&polls<EXIT_WAIT_POLLS){FW_SLEEP(EXIT_WAIT_MS);++polls;}
    }
    if(load32(&R->state)==1){R->modal_serial=load32(&R->serial);publish_result(R->modal_serial,STATUS_BUSY,0,0);return;}
    browser_post(PS8_MERGE);R->modal_serial=load32(&R->serial);
    if(load32(&R->state)!=1)publish_result(R->modal_serial,R->status,0,0);   /* no worker: browser_post ended it */
}
int psm_modal_entry(void *page) {
    R->page=page;R->modal=1;R->leaving=0;FW_SCREEN(3,7);
    if(R->review){
        /* PS11: show the result of review_serial only; nothing is posted and no setting or timer is held */
        R->modal_serial=R->review_serial;FW_TIMER_CANCEL(0x1b);psm_poll();return 0;
    }
    if(R->browser_open&&R->browser.phase==PSB_RUNNING){
        R->job_mode=PSM_MODE_ALL;modal_post();FW_TIMER_CANCEL(0x1b);psm_poll();return 0;
    }
    R->menu_delay=FW_GET_SETTING(MENU_DELAY_SETTING);R->timer_kind=FW_TIMER_KIND();
    FW_TIMER_HOLD(UINT32_MAX);FW_SET_SETTING(MENU_DELAY_SETTING,8);
    /* PS5: post job serial+1; it starts when a live worker takes it (psm_worker) */
    uint32_t serial=load32(&R->serial)+1;R->modal_serial=serial;
    if(FW_GET_SETTING(MENU_DELAY_SETTING)!=8||load32(&R->state)==1){
        store32(&R->serial,serial);R->status=PSM_BAD_PLAN;publish_result(serial,PSM_BAD_PLAN,0,0);store32(&R->state,2);
    } else {
        /* PS7: the mode of the confirmed row; progress and result of the previous job cleared */
        R->job_mode=R->request==PSM_MODE_ALL?PSM_MODE_ALL:PSM_MODE_NEWEST;R->operation=0;
        R->merged=R->targets=R->attempted=R->seconds=0;store32(&R->group_index,0);store32(&R->group_count,0);
        store32(&R->cancel,0);R->context.rows=R->context.total=0;store32(&R->context.phase,0);
        R->wait_polls=0;R->spawned=0;store32(&R->serial,serial);
        if(!worker_alive()&&spawn_worker())R->spawned=serial;
        if(worker_alive()){store32(&R->state,1);psm_job_posted(serial,R->worker_id,R->spawned==serial);}
        else {R->status=PSM_NO_MEMORY;publish_result(serial,PSM_NO_MEMORY,0,0);store32(&R->state,2);}
    }
    FW_TIMER_CANCEL(0x1b);psm_poll();return 0;
}
/* Read-only observation point: polls spent waiting at exit and the state/status reached. */
__attribute__((noinline,used)) void psm_exit_settled(uint32_t polls, uint32_t state, uint32_t status)
{
    __asm__ volatile("" : : "r"(polls), "r"(state), "r"(status) : "memory");
}
int psm_modal_exit(void *page) {
    uint32_t polls=0,own=R->leaving;
    (void)page;R->modal=0;R->page=0;R->leaving=0;FW_TIMER_CANCEL(0x1b);
    /* PS11: a shown review is done however the page is left */
    if(R->review){R->review=0;R->review_serial=0;progress_layout(0);return 0;}
    /* PS11: left by anything but its own OK/MENU while the merge ran: show the result at the next OK on row 45 */
    if(!own&&load32(&R->state)==1)R->review_serial=R->modal_serial;
    /* Unexpected exits also request orderly worker cancellation; the worker closes its handles and removes
       the partial output before shooting resumes, unless that takes longer than the bounded wait. */
    if(load32(&R->state)==1){
        store32(&R->cancel,1);settle_unclaimed(PSM_CANCELLED);
        while(load32(&R->state)==1&&polls<EXIT_WAIT_POLLS){FW_SLEEP(EXIT_WAIT_MS);++polls;}
    }
    uint32_t settled=load32(&R->state);R->exit_polls=polls;psm_exit_settled(polls,settled,R->status);
    if(!R->browser_open||!R->return_to_list){
        if(R->browser_open){store32(&R->browser_open,0);browser_save_text(0);if(settled!=1)browser_release();}
        FW_SET_SETTING(MENU_DELAY_SETTING,R->menu_delay);
        psm_power_settings(R->menu_delay,8,FW_GET_SETTING(MENU_DELAY_SETTING));FW_TIMER_SET(R->timer_kind);
    }
    return 0;
}
static int modal_leave(void) {
    R->leaving=1;
    if(R->browser_open){R->return_to_list=1;FW_TRANSITION(2,0x1d);return 0;}
    store32(&R->state,0);FW_TRANSITION(2,0x19);return 0;
}
/* MENU (event 0x27E): cancels a running merge; after the result it leaves the page like OK. A review goes back to
   the photo menu. */
int psm_modal_action(void *event) {
    (void)event;
    if(load32(&R->state)==1){if(!R->review){store32(&R->cancel,1);settle_unclaimed(PSM_CANCELLED);}return 0;}
    if(R->review){R->leaving=1;FW_TRANSITION(2,0x19);return 0;}
    return modal_leave();
}
/* PS11: OK (events 0x286/0x28B/0x2AE) does nothing while merging; no OK button is shown then. A review goes on to
   the group list, where row 45's OK was going. */
int psm_modal_ok(void *event) {
    (void)event;
    if(load32(&R->state)==1)return 0;
    if(R->review){R->leaving=1;FW_TRANSITION(2,0x1d);return 0;}
    return modal_leave();
}
/* PS7: each submenu row has its own guard and action; both record the row (request) that the progress page then posts.
   Row 45's OK into the submenu uses psm_menu_available and psm_menu_action too (the row chosen next overrides). */
static int available(uint32_t request) {
    reap_stale();
    if(R->magic==PSM_MAGIC&&load32(&R->state)==1)return 0;
    if(R->magic==PSM_MAGIC)R->request=request;
    return 1;
}
int psm_menu_available(void *event) {
    (void)event;return available(PSM_MODE_NEWEST);
}
int psm_menu_available_all(void *event) {
    (void)event;return available(PSM_MODE_ALL);
}
static void initialize(uint32_t request) {
    if(R->magic!=PSM_MAGIC){memset(R,0,sizeof(*R));R->magic=PSM_MAGIC;}
    R->request=request;
}
/* PS11: the stock dispatcher passes its transition request (0x403DB910: page, event, target at +0xC) to the action
   and goes to the target read back after it (0x40508E04 -> 0x403AF53C). A result waiting for review turns row 45's
   OK from the group list (0x1D) to the progress page (0xC5), the stock row 45 target of PS3-PS6. */
#define REQUEST_TARGET 0xCu
__attribute__((section(".text.entry"),used)) int psm_menu_action(void *event) {
    initialize(PSM_MODE_NEWEST);
    R->review=0;
    if(R->review_serial&&event&&*(uint32_t *)((uint8_t *)event+REQUEST_TARGET)==0x1Du){
        R->review=1;*(uint32_t *)((uint8_t *)event+REQUEST_TARGET)=0xC5u;
    }
    progress_layout(R->review);
    return 0;
}
__attribute__((used)) int psm_menu_action_all(void *event) {
    (void)event;initialize(PSM_MODE_ALL);return 0;
}

#include "browser_fw.inc"
