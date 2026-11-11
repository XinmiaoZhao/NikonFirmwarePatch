/* Menu-controlled RAW pre-capture; HN9 space fallback, HN10 remaining-count fixes, HN11 JPEG grade in the count.
 * HN12: the NEF's MakerNote 0x0044 (JPGCompression) is 0, as in a camera NEF.
 * HN13: the DX image area like FX: the C60 DX readout (5408 x 3608) in C15 and, with hook Z, in C30; NEF, P2, hook T and
 * the count follow the frame's geometry.
 * HN14: RAW recording "lossless compressed" (item 1) is encoded at HE* in C15/C30, like HE* (item 3).
 * HN15: the NEF header follows the stock NEF tag lists (0x440cbfa8[0]): six SubIFDs, which the camera's own NEF reader
 * (case 0x406cb040 of 0x406caea0) requires before Retouch > NEF (RAW) processing accepts a file; NEFInfo blocks 5, 6, 7,
 * 0xc, 0x10..0x13 from the stock leaves; MakerNote 0x0046, 0x008c, 0x00a4; no JPEG-only IFD0 0x013e/0x013f/0x0211,
 * Exif 0xa500 or MakerNote 0x0050.
 * Public adapter: no card configuration, diagnostic footer off by default. */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long u64;
typedef long s64;

#define LOAD8(a) (*(volatile const u8 *)(u64)(a))
#define LOAD16(a) (*(volatile const u16 *)(u64)(a))
#define LOAD32(a) (*(volatile const u32 *)(u64)(a))
#define LOAD64(a) (*(volatile const u64 *)(u64)(a))
#define STORE8(a,v) (*(volatile u8 *)(u64)(a)=(v))
#define STORE32(a,v) (*(volatile u32 *)(u64)(a)=(v))
#define STORE64(a,v) (*(volatile u64 *)(u64)(a)=(v))

/* Original firmware interfaces (byte-audited by the build). */
#define SUBMIT ((u64 (*)(void *,u32))0x40f93098ul)
#define FREE_E ((void (*)(u64))0x4104df5cul)
#define XLATE ((u64 (*)(u64))0x41186718ul)
#define OPEN ((int (*)(const char *,u32,u32))0x402daa4cul)
#define CREATE ((int (*)(const char *,u32))0x402dad04ul)
#define CLOSE ((int (*)(int))0x402daaacul)
#define READ ((int (*)(int,void *,u32,u32 *))0x402dab4cul)
#define WRITE ((int (*)(int,u64,u32,u32 *))0x402dabb8ul)
#define EXISTS ((int (*)(const char *))0x402db1acul)
#define RENAME ((int (*)(const char *,const char *))0x402dad58ul)
#define ALLOC ((void *(*)(u32,u32))0x40d2c408ul)
#define FREE ((void (*)(void *))0x40d2c448ul)
#define CLEAN ((void (*)(const void *,u32))0x40d2b8b8ul)
#define CLOCK ((void (*)(void *))0x40c7c778ul)
#define DCF_GET ((u64 (*)(u32))0x4085a8e0ul)
#define DCF_NAME ((u64 (*)(u64))0x4085bfe0ul)
#define DCF_PUT ((void (*)(u64))0x4085aa7cul)
/* HN2: the stock still-image writer and the stock DCF database interfaces. */
#define ORIG_WRITE ((u32 (*)(u32,u32,u64))0x406cc134ul)             /* (0, mode, J) -> status */
#define LOCK ((u32 (*)(u64,u32,u32))0x40875834ul)                   /* (lock, ticks, tries) */
#define UNLOCK ((u32 (*)(u64))0x408758b4ul)
#define DB_ADD ((u32 (*)(u64,u32,const void *))0x408602ccul)        /* (db, first id, entry) */
#define DB_REMAIN ((void (*)(u32))0x408648a8ul)
#define DB_CANCEL ((void (*)(u32))0x4085ac54ul)                     /* (file id), no result */
/* HN3: the stock rate-control parameter builder of the JPEG encodes. */
#define RC_PARAMS ((void (*)(u64,u32,u32,u64,u8 *))0x40eaecb4ul)   /* (R, mode, kind 0 main / 1 NEF preview / 2, template copy, rc) */
#define G_PREVIEW_Q 0xa029e9fd0ul  /* the (quality index, table half) pair the stock NEF preview encode puts at rc+0x14/+0x18 */
/* HN4: output resource Y, the JPEG engine and its channel locks, as used by 0x41048d78 and 0x40eaf398. */
#define Y_ALLOC ((u64 (*)(u32,u64))0x41048d78ul)                     /* (kind word of the step, M) -> Y */
#define Y_SIZE ((u32 (*)(u64,u64,u32))0x4104886cul)                  /* (M, M+0x26c, M+0x2570==0x1d) -> bytes */
#define CAPACITY ((u32 (*)(u32,u32,u32,u32))0x410457ccul)            /* table 0xa02a2460c[a][b][c][d] */
#define DESC_INIT ((u32 (*)(u32,u32,u64,u64))0x41060780ul)           /* (1, 0, M, descriptor): the RAW-preview descriptor */
#define MAIN_ENCODE ((u32 (*)(u64))0x40eaea0cul)                       /* main JPEG encode of one step context */
#define JOB_WORD ((u32 (*)(u64))0x40eaec6cul)                        /* first word of the engine parameter block */
#define CH_LOCK ((void (*)(u32,u32,u32,u32))0x40eb8854ul)
#define CH_UNLOCK ((void (*)(u32,u32,u32,u32))0x40eb88a4ul)
#define ENGINE ((void (*)(u32,u64))0x40e82090ul)                     /* (engine 0/1, parameter block) */
#define IS_JPEG_FORMAT ((u32 (*)(u64))0x4105903cul)                 /* (M+0x26c): format 0/3 and not HEIF; QEMU probe only */
/* HN15: stock NEFInfo leaves of the header writer (tag table 0x440cdcc8): (IFD entry, {-, M}, {.., base @+0x18,
 * cursor @+0x20}). Each of these eight reads only M scalars and ROM/initialised-data tables, writes "version" + body +
 * CRC16 at the cursor, the byte count at entry+4, and advances the cursor (at most 0xbc bytes). */
#define NI_LEAF(a) ((void (*)(u8 *,u8 *,u8 *))(u64)(a))
/* Original globals, only read. */
#define G_MODE 0xa03bc6bc8ul       /* HSFC release mode: 6 = C15, 3 = C30 */
#define G_LIMIT 0xa03bc6bacul      /* pre-capture count of the menu setting */
#define G_DRAINED 0xa03bc5638ul    /* history frames drained at this full press (stale when the history is empty) */
#define G_WRITER_JOB 0xa03b891b8ul /* job of the primary writer 0x40ea340c */
#define G_CREATE_LOCK 0xa048229f0ul /* creation lock of 0x40866260 */
#define G_DB 0xa04822af8ul         /* per-card DCF database pointers: slot 0, then slot 1 at +8 */
#define G_ROLE 0xa04841bc4ul       /* HN7: secondary slot role (DS 0x06000689): 0 overflow, 1 backup, 2 RAW primary - JPEG secondary */
#define G_PRIMARY 0xa04841bc8ul    /* HN7: primary slot (DS 0x02000688 != 0): 0 = A: CFexpress, 1 = B: SD */
#define G_QTYPE 0xa03d482c8ul      /* DS 0x06000604 Image quality file type: 0 RAW + JPEG, 1 RAW, 3 JPEG (group 6 RAM 0xa03d482b4 + 0x14) */
#define G_QGRADE 0xa03d482ccul     /* DS 0x06000605 JPEG grade: 0 fine, 1 normal, 2 basic (+0x18; a RAW setting leaves it) */
#define G_QSTAR 0xa03d482d0ul      /* DS 0x06000606 star: 1 optimal quality, 0 size priority (+0x1c) */
#define G_RAWREC 0xa03d482d8ul     /* DS 0x06000608 RAW recording: 1 lossless compressed, 3 HE*, 4 HE (+0x24) */
#define G_RELMODE 0xa03d7c7a4ul    /* DS 0x00002126 release mode as the GUI reads it: 3 C30, 4 C120, 5 C60, 6 C15 */
#define G_REQ 0xa03b703b8ul        /* Tenc request: +0xb8 budget selector (2 HE, 4 HE*), +0x88 budget bytes */
#define G_PHOTO 0xa03d74254ul      /* DS 0x00002200: 1 photo */
#define G_218C 0xa03d7c94cul       /* DS 0x0000218c: 0 in the stock HSFC test */
#define G_JPEG_STATS 0xa03b88c18ul /* per-engine statistics, 0x240 each; the preview job's template is entry +0x20 */
#define G_JPEG_FLAGS 0xa03b85920ul /* bit 3: single engine */

#define PAYLOAD 0x01058600u         /* HE: floor(8280*5520*30/80) & 0x3fffe00 (budget 2) */
#define OLD_ALLOCATION 0x01082400u  /* stock C15/C30 E request */
#define NEW_ALLOCATION 0x01082600u  /* + the record (P4) */
#define PAYLOAD_HS 0x01b3e000u      /* HE*: floor(8280*5520*50/80) & 0x3fffe00 (budget 4) */
#define OLD_ALLOCATION_HS (PAYLOAD_HS+(OLD_ALLOCATION-PAYLOAD))   /* the stock slack after the payload kept */
#define NEW_ALLOCATION_HS (OLD_ALLOCATION_HS+0x200u)
#define C_HE 2u                     /* frame class = budget selector */
#define C_HS 4u
#define FX_DIMS 0x15902058u        /* 5520 << 16 | 8280 */
#define DX_DIMS 0x0e181520u        /* HN13: 3608 << 16 | 5408, HSFC selector 4 (0x4106699c): the C60 readout */
#define PAYLOAD_DX 0x006fa600u      /* HE: floor(5408*3608*30/80) & 0x3fffe00 (budget 2) */
#define PAYLOAD_DX_HS 0x00ba1400u   /* HE*: floor(5408*3608*50/80) & 0x3fffe00 (budget 4) */
#define WORK_BYTES 0x40000u        /* one heap block per NEF, freed before return */
#define HDR_MAX 0x30000u           /* NEF header block */
#define TAB 0x30000u               /* entry table, ENT_MAX * 32 bytes */
#define NI 0x36000u                /* small values and NEFInfo blocks 8..f, 768 bytes; HN15 scratch up to FOOT below */
#define NI_CTX 0x36300u            /* HN15: entry (+0), context 1 (+0x10), context 2 (+0x30) of a stock leaf call */
#define NI_OUT 0x36400u            /* HN15: the NEFInfo sub-TIFF, NI_CAP bytes */
#define NI_CAP 0x600u
#define NI_CURVE 0x36a00u          /* HN15: MakerNote 0x008c, 578 bytes */
#define NI_STOCK 0x37000u          /* HN15: one NI_SLOT per stock leaf block */
#define NI_SLOT 0x100u
#define FOOT 0x38000u              /* 512-byte footer */
#define ZEROS 0x39000u             /* 4 KiB of zero for RAW alignment */
#define JP 0x3a000u                /* parameter block J' for the stock writer, 0x290 bytes */
#define JA 0x3a300u                /* descriptor pointer array, 4 x u64 */
#define JD 0x3a340u                /* descriptor 0: width/height pair, 16 bytes */
#define JT 0x3a360u                /* descriptor 3: thumbnail size, 32 bytes */
#define PLAN 0x3a400u              /* plan_t */
#define ENT_MAX 160u
#define SEG_MAX 27u                /* capacity of the J+0x68.. segment table */
#define CHUNK 0x100000u
#define DEFAULT_BUDGET 1500000u    /* about 3x the 18 MB write at the 39 MB/s seen in HS2 C */
#define FRESH_US 120000000ul
#define F_ENABLE 1u
#define F_C30 2u
#define F_FULL 4u
#define F_FOOTER 8u
#define F_DCF 0x10u                /* register the NEF in the stock database and use the stock writer */
#define F_RAWONLY 0x20u            /* RAW-only (needs F_DCF) */
#define F_PVQ 0x40u                /* RAW-only: main JPEG at the stock NEF-preview quality, embedded (needs F_RAWONLY and F_FULL) */
#define F_MENU 0x80u               /* HN4: every C15/C30 frame follows Image quality (needs 1|2|0x10, 30 frames; 4/0x20/0x40 not in the file) */
#define F_KNOWN 0xffu
#define F_NEFONLY 0x200u           /* build() only (never stored or in a file): this card gets only the NEF (ACT_NEF) */
#define F_PREV 0x100u              /* HN4, effective flags only (never in a file): RAW + JPEG with a second, preview-quality encode */
#define PVQ_MARK 0x31515650u       /* "PVQ1": record +0x7c, written by P7 after the parameters were replaced */
#define SPLIT_MARK 0x314c5053u     /* "SPL1": record A_SPLIT, HN7: the primary card's files are written, E kept for the secondary */
#define SUBMIT_MARK 0x53000000u    /* "S" in A_SUBMIT bits 24..31: the roles below were stored at submit */
#define PVJ_MARK 0x314a5650u       /* "PVJ1": aux +0xb8, written by hook J after the preview encode */
#define AUX_MAGIC 0x41344e48u      /* "HN4A" */
#define Q_MARKED 1u
#define Q_RETAINED 2u
#define K_HISTORY 1u
#define K_CURRENT 2u
#define T_JPEG 1u
#define T_RAWJPEG 2u
#define T_RAW 3u
#define S_DONE 1u
#define S_BUDGET 3u
#define S_WRITE_FAIL 4u
#define S_RENAME_FAIL 5u
#define S_MISSING 6u               /* the stock writer reported success but the NEF is not on the card */
#define DB_OK 0x4320080u           /* stock success code of the database interfaces */
#define RC_NO_DB 0xfff00001u       /* HN2 internal result codes, never produced by stock code */
#define RC_LOCK 0xfff00002u
#define RC_INTERNAL 0xfff00003u
/* aux block of the frame record (record +0x80..+0xff, own CRC at +0xfc over +0x80..+0xfb) */
#define A_MAGIC 0x80u
#define A_KIND 0x84u               /* K_HISTORY / K_CURRENT */
#define A_VALUE 0x88u              /* at submit: page value (bits 0..7, V_NONE if not one the menu gives), then file type,
                                      grade and star items (bits 8..15, 16..23, 24..31, each clamped to 0xff) */
#define V_NONE 0xffu
#define A_M290 0x8cu               /* M+0x290 / M+0x2a0 as the stock HSFC path set them */
#define A_M2A0 0x90u
#define A_QUAL 0x94u               /* applied by P2 (F_MENU): quality index, table half, file type */
#define A_HALF 0x98u
#define A_TYPE 0x9cu
#define A_YOFF 0xa0u               /* hook B: stock request bytes; preview capacity */
#define A_YCAP 0xa4u
#define A_Y 0xa8u                  /* hook A: Y and the preview region address */
#define A_YADDR 0xb0u
#define A_PMARK 0xb8u              /* hook J: PVJ_MARK, encoded bytes, engine, source offset in R */
#define A_PBYTES 0xbcu
#define A_PT0 0xc0u
#define A_PT1 0xc8u
#define A_ENGINE 0xd0u
#define A_SRC 0xd4u
#define A_YSTATE 0xd8u             /* 1 enlarged by B, 2 laid out by A */
#define A_CLASS 0xdcu              /* HN5: E allocation class at submit (C_HE / C_HS) */
#define A_RAWREC 0xe0u             /* HN5: RAW recording item at submit */
#define A_TENC 0xe4u               /* HN5: Tenc request budget word at submit */
#define A_SPLIT 0xe8u              /* HN7: SPLIT_MARK once the primary card's NEF is written and its JPEG member cancelled */
#define A_SPLIT_JID 0xecu          /* HN7: that NEF's group (the primary list's file id) */
#define A_DUAL_ROLE 0xf0u          /* HN7R: the secondary slot role (1..3) the primary entry acted on */
#define A_SUBMIT 0xf4u             /* HN8: at submit, SUBMIT_MARK | primary slot << 8 | secondary slot role (each clamped to 0xff) */
#define A_CRC 0xfcu
#define REC_BYTES 256u

static const u8 qual_magic[16] = "Z8PREQUALv5";
#if defined(NEG_T_FILE_IO) || defined(NEG_P2_FILE_IO)
static const u8 cfg_magic[16] = "Z8PRECFGv3";   /* HN5R card configuration, controls only */
#endif
static const u8 foot_magic[16] = "Z8PREFOOTv4";
static const u8 identity[8] = {'P','R','E','C','A','P','0','5'};   /* HN10: 'a' = 10 (8 bytes) */
/* MakerNote 0x0051 for HE (internal compression 4, budget 2): the original leaf 0x406ea044
 * writes this from M+0x2ac=2; identical in every camera HE NEF examined. */
static const u8 he51[24] = {0x30,0x31,0x30,0x32,0x30,0x35,0x30,0x31,0,0,13,0,0,0,0,0,6,0,0,0,0,0,0,0};
static const u8 rat300[8] = {44,1,0,0,1,0,0,0};
static const u8 refbw[48] = {0,0,0,0,1,0,0,0, 255,0,0,0,1,0,0,0, 0,0,0,0,1,0,0,0,
                             255,0,0,0,1,0,0,0, 0,0,0,0,1,0,0,0, 255,0,0,0,1,0,0,0};
static const u8 tiffep[4] = {1,0,0,0};
static const u8 one8[1] = {1};
static const u8 cfa_dim[4] = {2,0,2,0};
static const u8 cfa_rggb[4] = {0,1,1,2};
static const u8 quality_raw[8] = {'R','A','W',' ',' ',' ',' ',0};
static const u8 xmp_ns[29] = "http://ns.adobe.com/xap/1.0/";
static const u8 nikon2[18] = {'N','i','k','o','n',0,2,0x11,0,0,'I','I',0x2a,0,8,0,0,0};
static const u8 nikon_ni[18] = {'N','i','k','o','n',0,1,3,0,0,'I','I',0x2a,0,8,0,0,0};
static const u8 type_size[13] = {0,1,1,2,4,8,1,1,2,4,8,4,8};
/* Tags the NEF header rebuilds, and (HN15) the tags only the stock JPEG lists carry: IFD0 0x013e WhitePoint, 0x013f
 * PrimaryChromaticities, 0x0211 YCbCrCoefficients; Exif 0xa500 Gamma; MakerNote 0x0050 (with 0x0016, 0x0035, 0x00a2). */
static const u16 skip0[] = {0x00fe,0x0103,0x013e,0x013f,0x014a,0x0201,0x0202,0x0211,0x0214,0x02bc,0x8769,0x8825,0x9003,0x9216};
static const u16 skipx[] = {0x9000,0x9101,0x9102,0xa000,0xa001,0xa002,0xa003,0xa005,0xa500,0x927c};
static const u16 skipm[] = {0x0004,0x0011,0x0016,0x0035,0x003d,0x0044,0x0045,0x0046,0x0050,0x0051,0x0058,0x008c,0x00a2,0x00a4};
/* HN15: MakerNote 0x00a4 of a NEF, the constant of leaf 0x406ec54c. */
static const u8 mn_a4[4] = {'0','5','0','1'};
/* HN15: NEFInfo blocks taken from the stock leaves, by tag. */
static const u8 ni_tag[8] = {0x05,0x06,0x07,0x0c,0x10,0x11,0x12,0x13};
static const u32 ni_leaf[8] = {0x406e7010u,0x406e70c0u,0x406e7170u,0x406e7510u,0x406e78a4u,0x406e795cu,0x406e7a24u,0x406e7bb8u};
/* MakerNote 0x0044 of a NEF: the camera's writer 0x406e9b30 gives 1 or 3 only to JPEG kinds, 0 to a NEF. */
static const u8 jpgc_nef[2] = {0,0};
static const u32 crc_table[256] = {
#include "crc32_table.inc"
};

static void copy(u8 *d,const u8 *s,u32 n) { while(n--) *d++=*s++; }
static void zero(u8 *d,u32 n) { while(n--) *d++=0; }
static int equal(const u8 *a,const u8 *b,u32 n) { u32 x=0; while(n--) x|=*a++^*b++; return x==0; }
static u32 get16(const u8 *p) { return (u32)p[0]|(u32)p[1]<<8; }
static u32 get32(const u8 *p) { return (u32)p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24; }
static u64 get64(const u8 *p) { return (u64)get32(p)|(u64)get32(p+4)<<32; }
static void set16(u8 *p,u32 v) { p[0]=(u8)v; p[1]=(u8)(v>>8); }
static void set32(u8 *p,u32 v) { for(u32 i=0;i<4;i++){p[i]=(u8)v;v>>=8;} }
static void set64(u8 *p,u64 v) { for(u32 i=0;i<8;i++){p[i]=(u8)v;v>>=8;} }
__attribute__((noinline)) static u32 crc32(const u8 *p,u32 n) {
    u32 c=0xffffffffu; while(n--) c=(c>>8)^crc_table[(c^*p++)&255]; return c^0xffffffffu;
}
static u32 crc16(const u8 *p,u32 n) {              /* CCITT-FALSE, as in NEFInfo blocks */
    u32 c=0xffff;
    while(n--){ c^=(u32)*p++<<8; for(u32 i=0;i<8;i++) c=(c&0x8000)?((c<<1)^0x1021)&0xffff:(c<<1)&0xffff; }
    return c;
}
static u64 now(void) { u64 t; CLOCK(&t); return t; }

/* ---------------- frame record in the E allocation tail ---------------- */
/* E is a resource descriptor: E+8 -> {data_base, data_bytes}; E+0x30 type/format/dims,
 * E+0x40 payload. The 512 bytes past OLD_ALLOCATION exist only because the build enlarges
 * the mode 3/6 request; no original code addresses them. Record: +0x00..+0x7f as HN3 (CRC at
 * +0x78 over +0x00..+0x77, P7 mark at +0x7c), +0x80..+0xff the HN4 aux block. */
/* HN5: the class of an E is the size of its own allocation: HE*-sized only when hook E allocated it while the
 * Tenc request carried budget 4, and hook D decodes such a frame with selector 4. */
static u32 e_class(u64 e) {
    u64 block=e?LOAD64(e+8):0; if(!block) return 0;
    u64 base=LOAD64(block),bytes=LOAD32(block+8);
    if(!base || base+bytes<base) return 0;
    if(bytes>=NEW_ALLOCATION_HS) return C_HS;
    if(bytes>=NEW_ALLOCATION) return C_HE;
    return 0;
}
/* HN13: the payload of a class in a geometry (FX_DIMS or DX_DIMS); 0 for any other geometry. */
static u32 payload_of(u32 cls,u32 dims) {
    if(dims==FX_DIMS) return cls==C_HS?PAYLOAD_HS:PAYLOAD;
    if(dims==DX_DIMS) return cls==C_HS?PAYLOAD_DX_HS:PAYLOAD_DX;
    return 0;
}
static u8 *record(u64 e) {
    u32 cls=e_class(e); if(!cls) return 0;
    u64 block=LOAD64(e+8),base=LOAD64(block),bytes=LOAD32(block+8);
    u64 q=(base+(cls==C_HS?OLD_ALLOCATION_HS:OLD_ALLOCATION)+63)&~63ul;
    if(q<base || q+REC_BYTES>base+bytes) return 0;
    return (u8 *)q;
}
static int e_shape(u64 e) {
    if(!e || LOAD32(e+0x30)!=3 || LOAD32(e+0x34)!=5) return 0;
    u32 cls=e_class(e),pay=payload_of(cls,LOAD32(e+0x38)); u64 d=LOAD64(e+0x40),block=LOAD64(e+8);
    if(!cls || !pay || !d || (d&511) || d+pay<d) return 0;
    return d>=LOAD64(block) && d+pay<=LOAD64(block)+LOAD32(block+8);
}
static void seal(u8 *q) { set32(q+0x78,crc32(q,0x78)); CLEAN(q,128); }
static void aux_seal(u8 *q) { set32(q+A_CRC,crc32(q+0x80,0x7c)); CLEAN(q+0x80,128); }
static int aux_ok(const u8 *q) { return get32(q+A_MAGIC)==AUX_MAGIC && get32(q+A_CRC)==crc32(q+0x80,0x7c); }
static void unbind(u8 *q) { zero(q,16); CLEAN(q,128); }
/* Valid record of this exact HSFC R/E/M in the given state, with a valid aux block. */
static u8 *bound(u64 r,u64 e,u32 state) {
    u64 m=LOAD64(r+0x790); u8 *q;
    if(!m || LOAD32(m)!=3 || !e_shape(e) || !(q=record(e))) return 0;
    if(!equal(q,qual_magic,16) || get32(q+0x10)!=1 || get32(q+0x14)!=state) return 0;
    if(get64(q+0x28)!=r || get64(q+0x30)!=e || get64(q+0x38)!=m || get64(q+0x40)!=LOAD64(e+0x40)) return 0;
    if(get32(q+0x78)!=crc32(q,0x78) || !aux_ok(q)) return 0;
    return q;
}
/* The retained frame of R whose M is still the frame the record was made for. */
__attribute__((unused)) static u8 *retained(u64 r) {
    u64 e; u8 *q;
    if(!r || !(e=LOAD64(r+0x748)) || !(q=bound(r,e,Q_RETAINED))) return 0;
    if(get32(q+0x70)!=LOAD32(LOAD64(r+0x790)+0x2508)) return 0;
    return q;
}

/* RAM only, inside the original release task. kind: K_HISTORY from P1, K_CURRENT from P8. */
/* The Image quality page value as the stock page composer 0x405dadd4 forms it from file type t (item 0x0604),
 * grade g (0x0605) and star c (0x0606): RAW + JPEG 2g + 1 - c, JPEG 2g + 7 - c, RAW 13. The composer also maps
 * t = 2 to 12 and invalid items to 8, 9 or 14 (fallback rows); none of those is a menu choice, so V_NONE (the
 * frame stays stock). */
static u32 menu_value(u32 t,u32 g,u32 c) {
    if(c>1) return V_NONE;
    if(t==1) return 13;
    if((t!=0 && t!=3) || g>2) return V_NONE;
    return (t==3?6u:0u)+2*g+1-c;
}
static u32 clamp8(u32 v) { return v>0xffu?0xffu:v; }
static u32 menu_word(void) {
    u32 t=LOAD32(G_QTYPE),g=LOAD32(G_QGRADE),c=LOAD32(G_QSTAR),v=menu_value(t,g,c);
#ifdef NEG_GRADE_ONLY                 /* negative-control builds only: HN4's read (the grade item taken as the value) */
    v=g;
#endif
    return v | clamp8(t)<<8 | clamp8(g)<<16 | clamp8(c)<<24;
}
__attribute__((noinline)) static void mark(void *rec,u32 kind) {
    u64 r=(u64)rec,m,e; u8 *q; u32 mode,seq,total;
    if(!r) return;
    m=LOAD64(r+0x790); e=LOAD64(r+0x748);
    if(!m || !e || LOAD32(m)!=3) return;
    mode=LOAD32(G_MODE); if(mode!=6 && mode!=3) return;
    seq=LOAD32(m+0x120);
    if(kind==K_HISTORY) { total=LOAD32(G_DRAINED); if(!seq || seq>total || total>30) return; }
    else total=0;                    /* G_DRAINED is stale for frames after the full press */
    if(!e_shape(e) || !(q=record(e))) return;
    zero(q,REC_BYTES); copy(q,qual_magic,16); set32(q+0x10,1); set32(q+0x14,Q_MARKED);
    set32(q+0x18,seq); set32(q+0x1c,total); set32(q+0x20,mode); set32(q+0x24,LOAD32(G_LIMIT));
    set64(q+0x28,r); set64(q+0x30,e); set64(q+0x38,m); set64(q+0x40,LOAD64(e+0x40));
    set32(q+0x48,LOAD32(e)); set32(q+0x4c,e_class(e)==C_HS?NEW_ALLOCATION_HS:NEW_ALLOCATION); CLOCK(q+0x50);
    set32(q+A_MAGIC,AUX_MAGIC); set32(q+A_KIND,kind); set32(q+A_VALUE,menu_word());
    set32(q+A_M290,LOAD32(m+0x290)); set32(q+A_M2A0,LOAD32(m+0x2a0));
    set32(q+A_CLASS,e_class(e)); set32(q+A_RAWREC,LOAD32(G_RAWREC)); set32(q+A_TENC,LOAD32(G_REQ+0xb8));
    /* HN8: the role and the primary slot the stock grouping uses inside the submit that follows */
    set32(q+A_SUBMIT,SUBMIT_MARK | clamp8(LOAD32(G_PRIMARY))<<8 | clamp8(LOAD32(G_ROLE)));
    seal(q); aux_seal(q);
}
__attribute__((used,section(".text.entry"))) u64 precapture_history_entry(void *rec,u32 keep) {
    mark(rec,K_HISTORY);             /* inside the original drain lock */
    return SUBMIT(rec,keep);
}
/* P8. Original: mov x0,x20; mov w1,w21 (set by the original code); bl 0x40f93098. */
__attribute__((used)) u64 precapture_current_entry(void *rec,u32 keep) {
    mark(rec,K_CURRENT);
    return SUBMIT(rec,keep);
}

/* ---------------- sticky stop (writer task only); the HN5R card configuration only in two controls ---------------- */
#if defined(NEG_T_FILE_IO) || defined(NEG_P2_FILE_IO)
static int read_cfg(char drive,u8 *out) {
    char path[16]="A:\\Z8PRE.CFG"; u32 count=0; int fd,rc,cl;
    path[0]=drive;
    fd=OPEN(path,0,0x20); if(fd<0) return 0;
    rc=READ(fd,out,65,&count); cl=CLOSE(fd);
    if(rc!=0 || cl!=0 || count!=64 || !equal(out,cfg_magic,16)) return 0;
    u32 flags=get32(out+0x10),pre=get32(out+0x14),budget=get32(out+0x18);
    if((flags&~F_KNOWN) || !(flags&F_ENABLE) || pre<1 || pre>30) return 0;
    if((flags&F_RAWONLY) && !(flags&F_DCF)) return 0;         /* RAW-only needs the stock writer */
    if((flags&F_PVQ) && (flags&(F_RAWONLY|F_FULL))!=(F_RAWONLY|F_FULL)) return 0;   /* the JPEG file must not be kept */
    if((flags&F_MENU) && ((flags&(F_ENABLE|F_C30|F_DCF))!=(F_ENABLE|F_C30|F_DCF) || (flags&(F_FULL|F_RAWONLY|F_PVQ)) || pre!=30)) return 0;
    if(budget && (budget<200000 || budget>5000000)) return 0;
    for(u32 i=0x20;i<0x3c;i++) if(out[i]) return 0;
    return get32(out+0x3c)==crc32(out,60);
}
#endif
static int stopped(char drive) { char p[20]="A:\\Z8PRESTP.BIN"; p[0]=drive; return EXISTS(p)>=0; }
__attribute__((noinline)) static void stop_file(char drive,u32 status,u32 shot) {
    char p[20]="A:\\Z8PRESTP.BIN"; u8 raw[64] __attribute__((aligned(64))); u32 n; int fd;
    p[0]=drive; if(EXISTS(p)>=0) return;
    zero(raw,64); copy(raw,(const u8 *)"Z8PRESTOP",9); set32(raw+16,status); set32(raw+20,shot);
    set64(raw+24,now()); CLEAN(raw,64);
    fd=CREATE(p,0x20); if(fd<0) return;
    WRITE(fd,(u64)raw,32,&n); CLOSE(fd);        /* never retried or deleted */
}

/* Image quality value -> file type, quality index (M+0x290: 0 fine, 1 normal, 2 basic) and table half
 * (M+0x2a0: 1 = "*", optimal quality). 0 = not a value HN4 takes over (V_NONE included). */
static u32 plan_of(u32 v,u32 *qi,u32 *half) {
    if(v<=11) { u32 k=v%6; *qi=k>>1; *half=(k&1)?0u:1u; return v<6?T_RAWJPEG:T_JPEG; }
    if(v==13) { *qi=0; *half=0; return T_RAW; }          /* fine FHD/VGA, as in a camera RAW-only NEF; P7 sets the main */
    return 0;
}
/* The frame is an ordinary stock HSFC C15/C30 JPEG frame, as the five real frames: JPEG only, not HEIF,
 * no special size, no second JPEG, FX or (HN13) DX L, and the HSFC item's own values (fine/normal, half 0). */
static int stock_hsfc_m(u64 m) {
    return LOAD32(m)==3 && LOAD32(m+0x294)==3 && LOAD32(m+0x2fc)==0 && LOAD32(m+0x2570)==0 && LOAD8(m+0x2ce)==0 &&
           LOAD32(m+0x26c)<=1 && LOAD32(m+0x290)<=1 && LOAD32(m+0x2a0)==0;
}

/* P2. Original: ldr x0,[x23,#0x748]; bl 0x4104df5c; str xzr,[x23,#0x748].
 * HN6: no card configuration and no file call. A marked C15/C30 frame whose Image quality (at submit) is RAW or
 * RAW + JPEG is retained with the fixed menu flags; a JPEG-only setting gets the menu grade and stays JPEG (stock path). */
#ifndef PRECAPTURE_DIAGNOSTIC_FOOTER
#define PRECAPTURE_DIAGNOSTIC_FOOTER 0
#endif
#define MENU_FLAGS (F_ENABLE|F_C30|F_DCF|F_MENU|(PRECAPTURE_DIAGNOSTIC_FOOTER?F_FOOTER:0u))    /* 0x9b, as M4_C15C30_MENU30 */
#define MENU_PRE 30u
#define MENU_LABEL 0u                                  /* "NA" (record +0x74, was the configuration label) */
__attribute__((used)) void precapture_tdec_release(u64 r) {
    u64 e=LOAD64(r+0x748); u8 *q=e?bound(r,e,Q_MARKED):0;
    if(q) {
        u64 t=now(),m=LOAD64(r+0x790);
        int ok=t-get64(q+0x50)<FRESH_US;
#ifdef NEG_P2_FILE_IO                 /* negative-control builds only: HN5R's per-frame card read and stop-file check */
        u8 ca[65] __attribute__((aligned(8))),cb[65] __attribute__((aligned(8)));
        int a=read_cfg('A',ca),b=read_cfg('B',cb);
        if(a==b || stopped(a?'A':'B')) ok=0;
#endif
        if(ok) {
            u32 flags=MENU_FLAGS,mode=get32(q+0x20),qi,half,type=plan_of(get32(q+A_VALUE)&0xffu,&qi,&half);
#ifdef NEG_MENU_IGNORED               /* negative-control builds only */
            type=0;
#endif
            if(type && (mode==6 || mode==3) && stock_hsfc_m(m) && get32(q+A_M290)==LOAD32(m+0x290) && get32(q+A_M2A0)==LOAD32(m+0x2a0)) {
                STORE32(m+0x290,qi); STORE32(m+0x2a0,half);
                set32(q+A_QUAL,qi); set32(q+A_HALF,half); set32(q+A_TYPE,type); aux_seal(q);
                if(type!=T_JPEG) {
                    flags|=F_FULL;
                    if(type==T_RAW) flags|=F_RAWONLY|F_PVQ;
                    else if(qi!=2 || half!=0) flags|=F_PREV;          /* basic (no *): the main JPEG is the preview */
                    set32(q+0x14,Q_RETAINED); set64(q+0x58,t); set32(q+0x60,flags); set32(q+0x64,MENU_PRE);
                    set32(q+0x68,DEFAULT_BUDGET); set32(q+0x6c,0); set32(q+0x70,LOAD32(m+0x2508));
                    set32(q+0x74,MENU_LABEL);         /* +0x6c drive: 0, the writer takes the JPEG's card */
                    seal(q);
                    return;                      /* R+0x748 kept for P3' or the R cleanup */
                }
            }
        }
        unbind(q);
    }
    FREE_E(e);
    STORE64(r+0x748,0);
}

/* ---------------- HN5: HE* (hooks T, E, S, D) ---------------- */
#define TENC_CONFIG ((void (*)(u64))0x40e8db3cul)                  /* (stage context): request type, budget, transform */
#define POOL_ALLOC ((u64 (*)(u32,u32,u32))0x41047478ul)            /* (frame, pool 0x39, bytes) -> E */
#define E_SIZE ((u32 (*)(u32,u32))0x4104df60ul)                    /* (capture kind, release mode) -> E request bytes */
/* HN14: the RAW recording items C15/C30 encode at HE*: HE* (3) and lossless compressed (1), which the HSFC path cannot
 * encode (budget selectors 2 and 4 only). HE (4) stays HE. */
static int rawrec_hs(void) {
    u32 v=LOAD32(G_RAWREC);
#ifdef NEG_LOSSLESS_HE                /* negative-control builds only: HN13 (lossless compressed falls back to HE) */
    return v==3;
#endif
    return v==3 || v==1;
}
/* The settings ask for HE*: C15/C30, RAW or RAW + JPEG in Image quality, RAW recording HE* or (HN14) lossless. */
static int hs_settings(u32 mode) {
    u32 t=LOAD32(G_QTYPE);
    return (mode==6 || mode==3) && rawrec_hs() && (t==0 || t==1);
}
/* Exactly one card holds a valid configuration with "follow Image quality" and no stop file (HN5R's P2 rule). HN5
 * called this from hook T; kept only for the negative control NEG_T_FILE_IO (file calls in the capture stage). */
#ifdef NEG_T_FILE_IO
static int menu_card(void) {
    u8 ca[65] __attribute__((aligned(8))),cb[65] __attribute__((aligned(8)));
    int a=read_cfg('A',ca),b=read_cfg('B',cb);
    if(a==b) return 0;
    return (get32((a?ca:cb)+0x10)&F_MENU) && !stopped(a?'A':'B');
}
#endif
/* T. Original: mov x0,x20; bl 0x40e8db3c in the Tenc start stage 0x40e99664; the request is read afterwards by
 * the E allocations of this capture (0x40e8dc28) and the parameter builder (0x40e8978c -> 0x40e89ac0). The stage runs
 * once per HSFC frame inside the capture cadence: no file calls here (HN5R). */
__attribute__((used)) void precapture_tenc_config(u64 ctx) {
    u64 i;
    TENC_CONFIG(ctx);
    if(!ctx || LOAD32(ctx+0x10)!=0xb || LOAD32(G_REQ+0xb8)!=2 || !(i=LOAD64(ctx+0x9e0))) return;
    if(LOAD32(i)!=3 || (LOAD32(i+8)!=0 && LOAD32(i+8)!=4) || !hs_settings(LOAD32(i+0x48))) return;   /* HSFC, FX or DX (HN13) */
#ifdef NEG_T_FILE_IO                  /* negative-control builds only: HN5's per-frame card read */
    if(!menu_card()) return;
#endif
    STORE32(G_REQ+0xb8,4);
}
/* E. Original: bl 0x41047478(w0 frame, w1 0x39, w2 table bytes) inside 0x4104dea4, the only E allocation. */
__attribute__((used)) u64 precapture_e_alloc(u32 frame,u32 pool,u32 size) {
#ifndef NEG_HS_SMALL_E                /* negative-control builds only: HE* encode into an HE-sized E */
    if(pool==0x39 && size==NEW_ALLOCATION && LOAD32(G_REQ+0xb8)==4) size=NEW_ALLOCATION_HS;
#endif
    return POOL_ALLOC(frame,pool,size);
}
/* S. Original: bl 0x4104df60(kind, mode) at 0x40e997c8 (start batch) and at 0x40f98c4c / 0x40f9a0b4 (free frames
 * in pool 0x39, the pre-capture availability). With the HE* size there the counts match the E that will be taken. */
__attribute__((used)) u32 precapture_e_size(u32 kind,u32 mode) {
    u32 size=E_SIZE(kind,mode);
    if(kind==1 && size==NEW_ALLOCATION && hs_settings(mode)) size=NEW_ALLOCATION_HS;
    return size;
}
/* D. Original: mov w9,#2 at 0x40ea9048 in the HSFC Tdec stage (x23 = R): the decode selector of the request.
 * The entry stub keeps x8 and x10, which the stage uses right after. */
__attribute__((used)) u32 hn5_tdec_sel(u64 r) {
    u64 e=r?LOAD64(r+0x748):0;
#ifndef NEG_TDEC_FIXED                /* negative-control builds only: the stock constant */
    if(e && e_class(e)==C_HS) return 4;
#else
    (void)e;
#endif
    return 2;
}
__asm__(".pushsection .text.hn5stub,\"ax\",%progbits\n"
        ".global precapture_tdec_sel_entry\n.type precapture_tdec_sel_entry,%function\n"
        "precapture_tdec_sel_entry:\n\tstp x29, x30, [sp, #-32]!\n\tstp x8, x10, [sp, #16]\n\tmov x0, x23\n"
        "\tbl hn5_tdec_sel\n\tmov w9, w0\n\tldp x8, x10, [sp, #16]\n\tldp x29, x30, [sp], #32\n\tret\n"
        ".popsection\n");
/* Z (HN13). Original 0x41059c60 (w0 = HSFC release mode, w1 = image area 0x2124; returns the mode the geometry follows):
 *   cmp w0,#6; b.ne ret; cmp w1,#1; mov w8,#5; cinc w8,w8,ne; cmp w1,#0; mov w9,#3; csel w0,w9,w8,eq; ret
 * i.e. C15 FX -> 3, C15 DX -> 5, C15 other -> 6, every other mode unchanged. Its first instruction becomes a branch here
 * (x30 is still the caller's); the C30 clause adds C30 DX -> 5. Same registers as the original (w0, w8, w9). */
__asm__(".pushsection .text.hn13stub,\"ax\",%progbits\n"
        ".global precapture_area_mode\n.type precapture_area_mode,%function\n"
        "precapture_area_mode:\n"
        "\tcmp w0, #3\n\tb.ne 1f\n\tcmp w1, #1\n\tmov w8, #5\n\tcsel w0, w8, w0, eq\n\tret\n"
        "1:\tcmp w0, #6\n\tb.ne 2f\n\tcmp w1, #1\n\tmov w8, #5\n\tcinc w8, w8, ne\n\tcmp w1, #0\n\tmov w9, #3\n"
        "\tcsel w0, w9, w8, eq\n2:\tret\n"
        ".popsection\n");
/* R. Original: bl 0x40ea21fc (-> 0x40e92ab0: mov w0,#12) at 0x40f96c90 in the ready gate 0x40f96c40, which clears the
 * "!" flag 0xa03bc6ba0 when 12 + [G_LIMIT] < budget [0xa03bc6bcc] (signed). The budget is at most the pool's frames
 * at the size hook S gives minus the pre-capture frames, so with HE* (64 frames) C30 1 s never became ready. For HE*
 * the sum becomes 12: ready when at least 13 frames fit after the ring. Other settings keep the stock rule. */
#define READY_MARGIN ((u32 (*)(void))0x40ea21fcul)
__attribute__((used)) u32 precapture_ready_margin(void) {
    u32 m=READY_MARGIN();
#ifndef NEG_READY_STOCK               /* negative-control builds only: the stock margin */
    if(hs_settings(LOAD32(G_MODE))) return m-LOAD32(G_LIMIT);
#endif
    return m;
}

/* ---------------- HN6: the quality controls and display in C15/C30 (hooks G, C, V) ---------------- */
#define DOP_GET ((u32 (*)(u32))0x40d52784ul)                       /* direct-operation property read */
static int follows_menu(u32 mode) {
#ifdef NEG_UI_STOCK                   /* negative-control builds only: the stock HSFC test */
    return 0;
#endif
    return mode==6 || mode==3;
}
/* G. Original: mov w0,#0x2126 (0x403acce4); bl 0x403ec398 at 0x403acce8 inside the GUI predicate 0x403acccc, which
 * returns 1 only for photo (0x2200 = 1), release mode 3..6 and 0x218c = 0, and then stores the mode to *x0. With
 * C15/C30 read as 0 the predicate is false for every caller, so the GUI treats C15/C30 like the other photo release
 * modes for the quality item (C60/C120 stay HSFC). The mode value is used only by the predicate's own test. */
#define GUI_GET ((u32 (*)(u32))0x403ec398ul)                      /* GUI property read */
__attribute__((used)) u32 precapture_gui_mode(u32 id) {
    u32 v=GUI_GET(id);
    if(id==0x2126 && follows_menu(v)) return 0;
    return v;
}
/* C. Original: bl 0x41014b2c(x0 = record pointers, w1 = count) at 0x40f24e08, where the capability engine stores the
 * records it computed (record: +0 id, +4 status, +8 value count, +0x10 values). In C15..C120 it gives the three Image
 * quality items status 1 (not offered to the dial and the i menu) and the HSFC item status 0; in the other release
 * modes the reverse; the value lists are complete in both. For C15/C30 HN5 swaps the statuses before the stock update
 * stores them, so the controls that read the capability offer the ordinary item there. HN6: at all five calls of the
 * store (one is the tail branch of the thunk 0x40ec4640); each passes (record pointers, count). */
#define CAP_UPDATE ((u32 (*)(u64,u32))0x41014b2cul)
__attribute__((used)) u32 precapture_cap_update(u64 recs,u32 n) {
    if(recs && n<=0x200 && LOAD32(G_PHOTO)==1 && LOAD32(G_218C)==0 && follows_menu(LOAD32(G_RELMODE))) {
        for(u32 k=0;k<n;k++) {
            u64 r=LOAD64(recs+8ul*k); u32 id;
            if(!r) continue;
            id=LOAD32(r);
            if((id==0x06000604u || id==0x06000605u || id==0x06000606u) && LOAD32(r+4)==1) STORE32(r+4,0);
            else if(id==0x0400650au && LOAD32(r+4)==0) STORE32(r+4,1);
        }
    }
    return CAP_UPDATE(recs,n);
}
/* V. Original: mov w0,#0x2126; bl 0x40d52784 where the quality role tests for C15..C120. */
__attribute__((used)) u32 precapture_ui_mode(u32 id) {
    u32 v=DOP_GET(id);
    if(id==0x2126 && follows_menu(v)) return 0;
    return v;
}

/* ---------------- HN8: the live-view quality indicator and the i-menu tile (GUI property records) ---------------- */
/* The GUI property service (pass 0x406ba124, in its own task) walks the record table and calls a record's callback as
 * cb(value, record) when the record's source changed; the callback writes the record's value (+0x48 pointer or +0x44)
 * and +0x58, and returns 1 if the value changed; the service then publishes it to the target property (+0x5c bit 0)
 * and the GUI slot (+0x5c bit 1). Records are RAM (initialised data); HN8 replaces callback pointers only. */
#define REC_TABLE 0xa0295c558ul    /* record table, 0x41d records of 0x68 bytes (0x406b21d8 returns it) */
#define REC(i) (REC_TABLE+(u64)(i)*0x68u)
#define R_M218C 93u                /* source 0x218c -> 0x251c (callback 0x406a90bc) */
#define R_QGRADE 112u              /* source 0x2119 effective JPEG grade -> 0x2503 quality code, slot 0x84 (0x406a890c) */
#define R_QKIND 113u               /* source 0x211a effective file type -> 0x2503 */
#define R_OGRADE 114u              /* source DS 0x06000605 -> slot 0x86, not published (0x406a89e8) */
#define R_OTYPE 115u               /* source DS 0x06000604 -> slot 0x86 */
#define R_QSTAR 116u               /* source 0x211c effective star -> 0x2504, slot 0x85 (0x406a8ac4) */
#define R_OSTAR 117u               /* source DS 0x06000606 -> slot 0x87, not published (0x406a8ac4) */
#define R_MPHOTO 129u              /* source 0x2200 -> 0x251c (0x406a90bc) */
#define R_MREL 130u                /* source 0x2126 release mode -> 0x251c (0x406a90bc) */
#define CB_QCODE ((u32 (*)(u32,u64))0x406a890cul)
#define CB_OCODE ((u32 (*)(u32,u64))0x406a89e8ul)
#define CB_STAR ((u32 (*)(u32,u64))0x406a8ac4ul)
#define CB_MODE ((u32 (*)(u32,u64))0x406a90bcul)
#define PROP_GET ((u32 (*)(u32))0x406a6e24ul)                    /* GUI property read, as the callbacks use it */
#define EVENT_SET ((void (*)(u64,u32))0x406a6d94ul)               /* (event object, bits) */
#define G_QCOUNT 0xa03e04bd0ul     /* records queued for the next pass (the stock code appends while count <= 0x7e) */
#define G_QLIST 0xa03e04bd4ul      /* their indexes */
#define G_QFULL 0xa03e04bccul      /* 1: the list overflowed, the next pass takes every record */
#define G_SVC_EVENT 0xa03e04610ul  /* the service's event object; bit 2: a pass over the list */
/* HN takes the frames of this setting over: photo, 0x218c = 0, C15/C30, an Image quality value HN follows (the frames
 * of any other quality, e.g. TIFF, stay stock HSFC JPEGs, so the indicator stays stock too). */
static int hn_display(void) {
#ifdef NEG_DISPLAY_STOCK              /* negative-control builds only: the stock indicator */
    return 0;
#endif
    return LOAD32(G_PHOTO)==1 && LOAD32(G_218C)==0 && follows_menu(LOAD32(G_RELMODE)) &&
           menu_value(LOAD32(G_QTYPE),LOAD32(G_QGRADE),LOAD32(G_QSTAR))!=V_NONE;
}
/* The quality code of file type t and grade g, the rule of 0x406a890c and 0x406a89e8 (jump tables 0x440bf8a8 and
 * 0x440bf8c8): RAW + JPEG -> g, RAW -> 3, type 2 -> 4, JPEG -> g + 5; a grade above 2 or another type keeps old. */
static u32 ocode(u32 t,u32 g,u32 old) {
    if(t==0) return g<3 ? g : old;
    if(t==1) return 3;
    if(t==2) return 4;
    if(t==3) return g<3 ? g+5 : old;
    return old;
}
/* Q: records 112 and 113. */
__attribute__((used)) u32 precapture_quality_code(u32 v,u64 rec) {
    u64 p; u32 code;
    if(!hn_display() || !(p=LOAD64(rec+0x48))) return CB_QCODE(v,rec);
    code=ocode(LOAD32(G_QTYPE),LOAD32(G_QGRADE),LOAD32(p));
    if(code==LOAD32(p)) return 0;
    STORE32(p,code); STORE8(rec+0x58,1);             /* as the original's tail: value, changed flag, return 1 */
    return 1;
}
/* K: record 116 (the original keeps only 0 and 1). */
__attribute__((used)) u32 precapture_quality_star(u32 v,u64 rec) {
    if(hn_display()) v=LOAD32(G_QSTAR);
    return CB_STAR(v,rec);
}
/* Queue record i for the next pass with its source's current value, as the stock code queues a changed property. Runs
 * inside a pass (the service holds lock 0xa03e04668), so the list is written directly. */
__attribute__((unused)) static void requeue(u32 i,u32 source) {
    u64 r=REC(i); u32 n=LOAD32(G_QCOUNT);
    STORE32(r+0x10,PROP_GET(source)); STORE8(r+0x29,1);
    if(n<=0x7eu) { STORE32(G_QLIST+4ul*n,i); STORE32(G_QCOUNT,n+1u); }
    else STORE8(G_QFULL,1);
    EVENT_SET(G_SVC_EVENT,4);
}
/* O: records 114, 115 (ordinary type / grade) and 117 (ordinary star): the original, then the published record. */
__attribute__((used)) u32 precapture_ordinary_code(u32 v,u64 rec) {
    u32 r=CB_OCODE(v,rec);
#ifndef NEG_NO_REQUEUE                /* negative-control builds only: no trigger from the ordinary items */
    requeue(R_QKIND,0x211a);
#endif
    return r;
}
__attribute__((used)) u32 precapture_ordinary_star(u32 v,u64 rec) {
    u32 r=CB_STAR(v,rec);
#ifndef NEG_NO_REQUEUE
    requeue(R_QSTAR,0x211c);
#endif
    return r;
}
/* M: records 93, 129 and 130 (0x218c, photo, release mode): the original, then both published records. */
__attribute__((used)) u32 precapture_display_mode(u32 v,u64 rec) {
    u32 r=CB_MODE(v,rec);
#ifndef NEG_NO_REQUEUE
    requeue(R_QKIND,0x211a); requeue(R_QSTAR,0x211c);
#endif
    return r;
}

/* ---------------- HN10: the remaining count with the NEF (hooks X, N); HN11: the JPEG at the ordinary grade ---------------- */
#define EXPAND ((void (*)(u64,u64))0x4086f8fcul)                  /* (plan, per-card size lists) */
#define DCF_ITEM ((u32 (*)(u64,u64,u32))0x408700d0ul)              /* DCF settings handler: (&id, &value, 1) -> change flags */
#define JPEG_EST ((u32 (*)(u64))0x40ea5b8cul)                      /* HN11: the plan builder's JPEG estimate (input block) */
#define G_PLAN 0xa048419f0ul       /* DCF file plan: count, then 0x28-byte items {files @+0, {type, word, bytes u64} @+8, @+0x18} */
#define ITEM_BYTES 0x28u
#define F_TYPE_JPEG 0u             /* plan file types (0x40ea12c0): 0 JPEG, 1 HEIF, 2 NEF, 4 JPEG of a special kind */
#define F_TYPE_NEF 2u
#define NEF_EXTRA 0x500000u        /* header, both previews and the footer: 3.64..4.46 MB on 1,154 body NEFs (HN6..HN8) -> 5 MiB */
#define N_FLAG 0x100u              /* hook N: a flag the stock callback's steps do not test (0x11, 2) */
#define ID_QTYPE 0x06000604u       /* DS Image quality file type (G_QTYPE) */
#define ID_QGRADE 0x06000605u      /* DS JPEG grade (G_QGRADE), HN11 */
#define ID_QSTAR 0x06000606u       /* DS star (G_QSTAR), HN11 */
#define ID_RAWREC 0x06000608u      /* DS RAW recording (G_RAWREC) */
/* HN11: the release module's settings cache, from which it builds every plan item (0x40f97724 with w1 = 0 at the six
 * plan-installing calls and the two other one-item builds; refreshed by 0x40f97b60 / 0x40f974e4 under lock 0xa03bc69c8). */
#define G_RKIND 0xa03bc6b4cul      /* plan kind, block +0: 0 ordinary, 2 when 0x218c = 1, 3 photo C30..C15 */
#define G_RAREA 0xa03bc6ab8ul      /* image area (property 0x2124), block +4: 0 = FX */
#define G_RTHUMB 0xa03bc6ad8ul     /* row of the two thumbnail tables (0x40f2f96c), block +8 */
#define G_RGRADE 0xa03bc6adcul     /* effective JPEG grade (0x2834 / 0x2119), block +0x10: the HSFC item's in C15/C30 */
#define G_RSIZE 0xa03bc6ae4ul      /* effective image size (0x2833), block +0x14: 0 = L */
#define G_RSTAR 0xa03bc6aecul      /* effective star (0x2835 / 0x211c), block +0x1c */
/* The DCF settings subscription: the stock five ids (0x441871d8), HN10's two and HN11's two. Read only during 0x4086e900. */
__attribute__((used)) const u32 precapture_dcf_ids[9] = {0x601u, 0x2000688u, 0x6000689u, 0x200172au, 0x2000600u, ID_QTYPE, ID_RAWREC,
                                                   ID_QGRADE, ID_QSTAR};
/* NEF bytes of a C15/C30 frame under the current settings (HN5's class rule: HE* for RAW recording 3, HN14 also 1; HN13:
 * the DX payload for the cached image area DX, read the DX area in C15 and, with hook Z, in C30). */
static u32 nef_estimate(void) {
    return payload_of(rawrec_hs() ? C_HS : C_HE,LOAD32(G_RAREA)==1 ? DX_DIMS : FX_DIMS) + NEF_EXTRA;
}
/* 0 = the stock plan; else T_RAWJPEG / T_RAW / T_JPEG: the files HN writes per frame (the display's condition, hn_display).
 * HN11: JPEG too, since P2 gives a JPEG-only frame the ordinary grade and star as well. */
static u32 count_type(void) {
#ifdef NEG_COUNT_STOCK                /* negative-control builds only: the stock (JPEG-only) count */
    return 0;
#endif
    u32 t;
    if(!hn_display()) return 0;
    t=LOAD32(G_QTYPE);
#ifdef NEG_JPEG_STOCK                 /* negative-control builds only: HN10 (JPEG-only frames counted by the stock plan) */
    if(t==3) return 0;
#endif
    return t==0 ? T_RAWJPEG : t==1 ? T_RAW : t==3 ? T_JPEG : 0;
}
/* HN11. The bytes of the JPEG P2 writes: the stock estimate 0x40ea5b8c (what 0x40ea12c0 puts in the plan) of the cached
 * inputs with the ordinary grade and star. The estimate is T1[area][star][size][grade] (0xa02a2460c) + the two thumbnail
 * tables [row][grade] (0xa02a24c0c, 0xa02a24c48) + 248,512; it reads block +0, +4, +8, +0x10, +0x14, +0x1c (+0x2c for
 * kind 2 only) and writes nothing but its stack. 0 (keep the plan's bytes) unless the JPEG is one P2 re-grades
 * (stock_hsfc_m: FX or DX L, the HSFC grade fine or normal without star) and the estimate of the cached HSFC grade and star
 * reproduces the plan's bytes exactly, i.e. the plan was built from these inputs. */
static u64 jpeg_bytes(u64 stock) {
#ifdef NEG_JPEG_STOCK
    return 0;
#endif
    u32 blk[16] __attribute__((aligned(16)));
    u32 kind=LOAD32(G_RKIND),g=LOAD32(G_RGRADE),c=LOAD32(G_RSTAR);
    u32 area=LOAD32(G_RAREA);
    if((kind!=0 && kind!=3) || area>1 || LOAD32(G_RSIZE)!=0 || g>1 || c!=0) return 0;   /* HN13: FX or DX */
    zero((u8 *)blk,sizeof blk);
    blk[0]=kind; blk[1]=area; blk[2]=LOAD32(G_RTHUMB); blk[4]=g; blk[7]=c;    /* size (+0x14) is 0 */
#ifndef NEG_NO_CHECK                  /* negative-control builds only: no check that the plan came from the cache */
    if((u64)JPEG_EST((u64)blk)!=stock) return 0;
#else
    (void)stock;
#endif
    blk[4]=LOAD32(G_QGRADE); blk[7]=LOAD32(G_QSTAR);                   /* 0..2, 0..1: hn_display holds */
    return JPEG_EST((u64)blk);
}
/* X. Original: bl 0x4086f8fc(x0 = 0xa048419f0 from 0x4086ebc0, x1 = the caller's list) in 0x408648a8. HN11: only a
 * one-item plan of one JPEG (type 0): P2 leaves HEIF frames (M+0x2fc) and two-JPEG frames to the stock writer. */
__attribute__((used)) void precapture_expand(u64 plan,u64 out) {
    u8 cp[8+ITEM_BYTES] __attribute__((aligned(16)));
    u32 type=count_type(); u64 j;
#ifdef NEG_HEIF_TAKEN                 /* negative-control builds only: HN10's test, a HEIF plan taken over too */
    if(plan!=G_PLAN || !type || LOAD32(plan)!=1 || LOAD32(plan+8)!=1 || LOAD32(plan+0x10)>1) { EXPAND(plan,out); return; }
#else
    if(plan!=G_PLAN || !type || LOAD32(plan)!=1 || LOAD32(plan+8)!=1 || LOAD32(plan+0x10)!=F_TYPE_JPEG) { EXPAND(plan,out); return; }
#endif
    copy(cp,(const u8 *)plan,8+ITEM_BYTES);
    u8 *it=cp+8;
    j=type==T_RAW ? 0 : jpeg_bytes(get64(it+0x10));
    if(type==T_JPEG && !j) { EXPAND(plan,out); return; }     /* a JPEG P2 does not re-grade: the stock count */
    if(type==T_RAW) {                                  /* {NEF}: the JPEG member is cancelled */
        set32(it+8,F_TYPE_NEF); set32(it+0xc,0); set64(it+0x10,nef_estimate());
    } else {                                           /* {JPEG} or {JPEG, NEF}, the JPEG at the ordinary grade and star */
        if(j) set64(it+0x10,j);
        if(type==T_RAWJPEG) { set32(it,2); set32(it+0x18,F_TYPE_NEF); set32(it+0x1c,0); set64(it+0x20,nef_estimate()); }
    }
    EXPAND((u64)cp,out);
}
/* The ordinary items whose change in C15/C30 changes the count (HN11: also the grade and the star). */
__attribute__((unused)) static int recount_item(u32 k) {
#ifdef NEG_NO_GRADE_RECOUNT           /* negative-control builds only: HN10's two items */
    return k==ID_QTYPE || k==ID_RAWREC;
#endif
    return k==ID_QTYPE || k==ID_RAWREC || k==ID_QGRADE || k==ID_QSTAR;
}
/* N. Original: bl 0x408700d0 (x0 = &id, x1 = &value, w2 = 1) in the subscription handler 0x408703b4. */
__attribute__((used)) u32 precapture_dcf_item(u64 id,u64 value,u32 n) {
    u32 r=DCF_ITEM(id,value,n);
#ifndef NEG_NO_RECOUNT                /* negative-control builds only: no recount on an ordinary quality change */
    if(n==1 && recount_item(LOAD32(id)) && hn_display()) r|=N_FLAG;
#endif
    return r;
}

/* ---------------- HN4: the preview region in Y ---------------- */
#ifndef HN4_QEMU_PROBE
/* A retained frame of R that needs the second encode; M must be R's. */
static u8 *needs_preview(u64 r,u64 m) {
    u8 *q=retained(r);
    if(!q || LOAD64(r+0x790)!=m || !(get32(q+0x60)&F_PREV) || get32(q+A_TYPE)!=T_RAWJPEG) return 0;
    return q;
}
/* B. Original: bl 0x4104886c(x0, x1, w2) inside 0x41048d78; the entry stub passes x23 = R. */
__attribute__((used)) u32 hn4_y_size(u64 m,u64 m26c,u32 flag,u64 r) {
    u32 size=Y_SIZE(m,m26c,flag),cap,base,need; u8 *q;
    if(!r || m26c!=m+0x26c || !(q=needs_preview(r,m))) return size;      /* m26c != M+0x26c: the stock stack-copy path */
    cap=CAPACITY(LOAD32(m+0x26c),0,LOAD32(m+0x29c),2);
    base=(size+511u)&~511u; need=base+((cap+511u)&~511u)+512u;          /* +512: the block base need not be 512-aligned */
    if(!cap || cap>0x2000000u || base<size || need<base) return size;
    set32(q+A_YOFF,size); set32(q+A_YCAP,cap); set32(q+A_YSTATE,1); aux_seal(q);
    return need;
}
__attribute__((unused)) static int ends_by(u64 y,u32 addr_off,u32 cap_off,u64 limit) {          /* a stock region [addr, addr+cap) ends at or before limit */
    u64 a=LOAD64(y+addr_off); u32 c=LOAD32(y+cap_off);
    return !a || (a+c>=a && a+c<=limit);
}
/* A. Original: bl 0x41048d78(w0, x1=M) in 0x40ea9f3c; the entry stub passes x23 = R. */
__attribute__((used)) u64 hn4_y_alloc(u32 kind,u64 m,u64 r) {
    u64 y=Y_ALLOC(kind,m),blk,base,addr; u32 bytes,cap; u8 *q;
    if(!y || !r || !(q=needs_preview(r,m)) || get32(q+A_YSTATE)!=1) return y;
    blk=LOAD64(y+8); if(!blk) return y;
    base=LOAD64(blk); bytes=LOAD32(blk+8); cap=get32(q+A_YCAP);
    addr=(base+get32(q+A_YOFF)+511u)&~511ul;
    if(!base || addr<base || addr+cap<addr || addr+cap>base+bytes) return y;
#ifndef NEG_Y_OVERLAP
    /* every region of the stock JPEG-only layout (main, VGA, FHD, thumbnail) ends before the new one */
    if(!ends_by(y,0x40,0x30,addr) || !ends_by(y,0xa8,0x98,addr) || !ends_by(y,0xc8,0xb8,addr) || !ends_by(y,0xe8,0xd8,addr)) return y;
#else                                 /* negative-control builds only: the preview region on top of the main JPEG's */
    addr=LOAD64(y+0x40);
#endif
    if(LOAD64(y+0x108) || LOAD32(y+0xf8) || DESC_INIT(1,0,m,y+0x100)!=1) return y;
    STORE32(y+0xf8,cap); STORE64(y+0x108,addr);
    set64(q+A_Y,y); set64(q+A_YADDR,addr); set32(q+A_YSTATE,2); aux_seal(q);
    return y;
}
#else
/* QEMU probe only (never packaged). The emulator shoots RAW stills (the stock RAW-only NEF, M+0x294 = 1), whose
 * stock Y layout already has a preview region at Y+0x100. B enlarges that Y by the same preview capacity, A moves
 * the preview region to the end of Y, J runs preview_job there right after the (gated-off) main step; the stock
 * preview step then sees Y+0x1e set and skips. With A, B and J correct the NEF's JpgFromRaw equals the control's.
 * No record: A and J recompute the stock request size with the stock function. */
static int probe_frame(u64 r,u64 m) {
    return r && m && LOAD64(r+0x790)==m && LOAD32(m)!=3 && LOAD32(m+0x294)==1 && LOAD32(m+0x2fc)!=1 && LOAD32(m+0x2570)==0;
}
static u32 probe_cap(u64 m) { return CAPACITY(LOAD32(m+0x26c),0,LOAD32(m+0x29c),2); }
static u64 probe_addr(u64 y,u64 m) {
    u64 blk=LOAD64(y+8); if(!blk) return 0;
    return (LOAD64(blk)+Y_SIZE(m,m+0x26c,0)+511u)&~511ul;
}
__attribute__((used)) u32 hn4_y_size(u64 m,u64 m26c,u32 flag,u64 r) {
    u32 size=Y_SIZE(m,m26c,flag);
    if(m26c!=m+0x26c || !probe_frame(r,m)) return size;
    return ((size+511u)&~511u)+((probe_cap(m)+511u)&~511u)+512u;
}
__attribute__((used)) u64 hn4_y_alloc(u32 kind,u64 m,u64 r) {
    u64 y=Y_ALLOC(kind,m),blk,addr; u32 cap;
    if(!y || !probe_frame(r,m) || !(blk=LOAD64(y+8))) return y;
    addr=probe_addr(y,m); cap=probe_cap(m);
    if(!addr || addr+cap>LOAD64(blk)+LOAD32(blk+8) || DESC_INIT(1,0,m,y+0x100)!=1) return y;
    STORE32(y+0xf8,cap); STORE64(y+0x108,addr);
    return y;
}
#endif
__asm__(".pushsection .text.hn4stub,\"ax\",%progbits\n"
        ".global precapture_y_size_entry\n.type precapture_y_size_entry,%function\n"
        "precapture_y_size_entry:\n\tmov x3, x23\n\tb hn4_y_size\n"
        ".global precapture_y_alloc_entry\n.type precapture_y_alloc_entry,%function\n"
        "precapture_y_alloc_entry:\n\tmov x2, x23\n\tb hn4_y_alloc\n"
        ".popsection\n");

/* The encode job of the stock NEF-preview step 0x40eaf398 (0x40eaf46c..0x40eaf570), on the same step
 * context, R, Y and source: engine, parameter block {job word, source+0x30, Y+0x100, capacity, rc
 * kind 1, scratch}, template from the engine's statistics entry, channel lock 0x23+engine. */
__attribute__((noinline)) static u32 preview_job(u64 ctx,u64 r,u64 y,u64 src,u32 *engine) {
    u8 blk[0x50] __attribute__((aligned(16))),sc[0x60] __attribute__((aligned(16))),tm[0x20] __attribute__((aligned(16)));
    u64 m=LOAD64(r+0x790); u32 eng=0,ch;
    if(LOAD32(m+0x2570)==0 && !(LOAD8(G_JPEG_FLAGS)&8)) eng=(~LOAD32(ctx))&1u;
    zero(blk,0x50); zero(sc,0x60); zero(tm,0x20);
    set32(blk,JOB_WORD(ctx));
    set64(blk+8,src+0x30); set64(blk+0x10,y+0x100); set32(blk+0x18,LOAD32(y+0xf8)); set64(blk+0x48,(u64)sc);
    for(u32 i=0;i<0x20;i++) tm[i]=LOAD8(G_JPEG_STATS+0x240ul*eng+0x20+i);
#ifndef NEG_PREVIEW_KIND0             /* negative-control builds only */
    RC_PARAMS(r,0,1,(u64)tm,blk+0x20);
#else
    RC_PARAMS(r,0,0,(u64)tm,blk+0x20);
#endif
    ch=0x23u+eng;
    CH_LOCK(ch,0,0,0);
    ENGINE(eng,(u64)blk);
    CH_UNLOCK(ch,0,0,0);
    STORE8(y+0x1e,1);
#if defined(HN4_QEMU_PROBE) && defined(PROBE_STATS)
    /* QEMU probe only: also the statistics writes of the stock preview step (0x40eaf574..0x40eaf618), which HN4 leaves out
     * (in a stock RAW + JPEG frame the main encode writes them and the preview step does not). */
    { u64 st=G_JPEG_STATS+0x240ul*eng,x23=LOAD64(m+0x2950);
      STORE32(st+0x38,LOAD32(m+0x180)); STORE32(st+0x3c,LOAD32(m+0x184)); STORE8(st+0x20,blk[0x24]);
      STORE32(st+0x30,LOAD32(m+0x2544)); STORE32(st+0x34,LOAD32(m+0x2548));
      STORE32(st+0x24,get32(blk+0x28)); STORE32(st+0x28,get32(sc+4)); STORE32(st+0x2c,get32(sc+8));
      STORE32(m+0x1970,get32(sc+0xc));
      if(x23 && !IS_JPEG_FORMAT(m+0x26c)) {
          for(u32 k=0;k<5;k++) {
              STORE32(x23+4*k,get32(sc+0x10+8*k)); STORE32(x23+0x14+4*k,get32(sc+0x14+8*k)); STORE64(x23+0x28+8*k,(u64)get32(blk+0x28));
          }
          STORE32(x23+0x8c,0); STORE32(m+0x2948,0x90);
      }
    }
#endif
    *engine=eng;
    return LOAD32(y+0x110);
}
#ifndef HN4_QEMU_PROBE
/* J. Original: bl 0x40eaea0c(ctx) in the main-JPEG step wrappers 0x40eaeed8 and 0x40eaeefc (result ignored). */
__attribute__((used)) u32 precapture_main_step(u64 ctx) {
    u32 st=MAIN_ENCODE(ctx),eng,bytes; u64 r,y,src,t0; u8 *q;
    r=LOAD64(ctx+0x18);
    if(!(q=needs_preview(r,LOAD64(r+0x790))) || get32(q+A_YSTATE)!=2) return st;
    y=LOAD64(r+0x6a8);
    if(!y || get64(q+A_Y)!=y || LOAD64(y+0x108)!=get64(q+A_YADDR) || LOAD32(y+0xf8)!=get32(q+A_YCAP)) return st;
    if(LOAD8(y+0x18)!=1 || LOAD8(y+0x1e)!=0) return st;                  /* main encoded, preview not yet */
    src=LOAD64(r+0x690); set32(q+A_SRC,0x690);
    if(!src) { src=LOAD64(r+0x688); set32(q+A_SRC,0x688); }               /* the stock preview's choice */
    if(!src) return st;
    t0=now(); bytes=preview_job(ctx,r,y,src,&eng);
    set64(q+A_PT0,t0); set64(q+A_PT1,now()); set32(q+A_ENGINE,eng); set32(q+A_PBYTES,bytes);
    if(bytes>=4 && bytes<=get32(q+A_YCAP)) set32(q+A_PMARK,PVJ_MARK);
    aux_seal(q);
    return st;
}
#else
__attribute__((used)) u32 precapture_main_step(u64 ctx) {
    u32 st=MAIN_ENCODE(ctx),eng; u64 r=LOAD64(ctx+0x18),m,y,src;
    if(!r || !(m=LOAD64(r+0x790)) || !probe_frame(r,m) || !(y=LOAD64(r+0x6a8))) return st;
    if(LOAD8(y+0x1e) || LOAD64(y+0x108)!=probe_addr(y,m) || LOAD32(y+0xf8)!=probe_cap(m)) return st;
    src=LOAD64(r+0x690); if(!src) src=LOAD64(r+0x688);
    if(src) preview_job(ctx,r,y,src,&eng);
    return st;
}
#endif

/* P7. Original: bl 0x40eaecb4 in 0x40eaea0c (x0=R, w1=mode, w2=0 main, x3=template copy, x4=rc), so the
 * stock parameters are always built first. rc layout (u32): +0 mode, byte +4 size-target flag, +8 target,
 * +0xc size class, +0x10 image size, +0x14 quality index, +0x18 table half, +0x1c, u64 +0x20 template.
 * The JPEG driver's rate control 0x40eb7318 takes the scale from the table at 0xa029d1378 by
 * (+0x18, size class, +0x10, +0x14) and, with the flag, may raise it from the template's statistics. */
#ifndef HN4_QEMU_PROBE
static void preview_quality(u8 *rc) {
    set32(rc+0x14,LOAD32(G_PREVIEW_Q)); set32(rc+0x18,LOAD32(G_PREVIEW_Q+4));
    rc[4]=0; set64(rc+0x20,0);       /* the table value exactly; the template written after this encode stays unusable */
}
__attribute__((used)) void precapture_main_rc(u64 r,u32 mode,u32 kind,u64 tmpl,u8 *rc) {
    u8 *q;
    RC_PARAMS(r,mode,kind,tmpl,rc);
#ifdef NEG_PVQ_ANY_FRAME              /* negative-control builds only: every main JPEG */
    if(kind==0) preview_quality(rc);
#endif
    if(kind!=0 || !(q=retained(r))) return;
    if((get32(q+0x60)&(F_PVQ|F_RAWONLY|F_FULL))!=(F_PVQ|F_RAWONLY|F_FULL)) return;
    preview_quality(rc);
#ifndef NEG_PVQ_NO_MARK               /* negative-control builds only */
    set32(q+0x7c,PVQ_MARK); CLEAN(q,128);   /* outside the record CRC (0..0x77); P1/P8 clear it for the next frame */
#endif
}
#else
/* QEMU probe only (never packaged): P7 passes through; B, A and J act on the emulator's RAW still (the stock
 * RAW-only NEF, M+0x294 = 1), whose stock layout already has a preview region: B enlarges Y, A moves the
 * preview region to the end of Y, J encodes the preview there before the stock preview step (which then sees
 * Y+0x1e set and skips). The NEF's JpgFromRaw must equal the control's. */
__attribute__((used)) void precapture_main_rc(u64 r,u32 mode,u32 kind,u64 tmpl,u8 *rc) { RC_PARAMS(r,mode,kind,tmpl,rc); }
#endif

/* ---------------- TIFF reading and writing ---------------- */
typedef struct { const u8 *b; u32 n; } src_t;      /* little-endian TIFF, offsets from b */
typedef struct {
    u16 tag,type; u32 count;
    const u8 *data; u32 bytes;
    u8 slot,dslot,eslot,pad;   /* record value / data / entry position into patch[] */
} ent_t;
typedef struct { u8 *o; u32 pos,cap,bad; u32 patch[16]; } out_t;
enum { P_SUB=1,P_THUMB,P_EXIF,P_GPS,P_JFR,P_OTHER,P_STRIP,P_MNENT,P_MNPV,P_PVSTART };

static u32 ifd_count(const src_t *s,u32 off) {
    if(off<8 || off>s->n-2) return 0;
    u32 n=get16(s->b+off);
    if(!n || n>200 || 2+12*n+4>s->n-off) return 0;
    return n;
}
static const u8 *ent_data(const src_t *s,u32 off,u32 i,u32 *bytes) {
    const u8 *e=s->b+off+2+12*i; u32 t=get16(e+2),c=get32(e+4),sz;
    if(t==0 || t>12 || c>0x100000) return 0;
    sz=type_size[t]*c; *bytes=sz;
    if(sz<=4) return e+8;
    u32 v=get32(e+8); if(v>s->n || sz>s->n-v) return 0;
    return s->b+v;
}
static const u8 *find(const src_t *s,u32 off,u32 tag,u32 type,u32 count) {
    u32 n=ifd_count(s,off),bytes;
    for(u32 i=0;i<n;i++) {
        const u8 *e=s->b+off+2+12*i;
        if(get16(e)!=tag) continue;
        if(get16(e+2)!=type || get32(e+4)!=count) return 0;
        return ent_data(s,off,i,&bytes);
    }
    return 0;
}
static void put(out_t *w,const u8 *p,u32 n) {
    if(w->bad || n>w->cap-w->pos) { w->bad=1; return; }
    if(p) copy(w->o+w->pos,p,n); else zero(w->o+w->pos,n);
    w->pos+=n;
}
static void pad2(out_t *w) { if(w->pos&1) put(w,0,1); }
static ent_t *add(ent_t *t,u32 *n,u32 tag,u32 type,u32 count,const u8 *data) {
    if(*n>=ENT_MAX) return 0;
    ent_t *e=t+(*n)++; zero((u8 *)e,sizeof(*e));
    e->tag=(u16)tag; e->type=(u16)type; e->count=count; e->data=data; e->bytes=type_size[type]*count;
    return e;
}
static int skipped(u32 tag,const u16 *skip,u32 ns) { for(u32 j=0;j<ns;j++) if(skip[j]==tag) return 1; return 0; }
static int copy_entries(const src_t *s,u32 off,ent_t *t,u32 *n,const u16 *skip,u32 ns) {
    u32 k=ifd_count(s,off),bytes; if(!k) return 0;
    for(u32 i=0;i<k;i++) {
        const u8 *e=s->b+off+2+12*i; u32 tag=get16(e);
        if(skipped(tag,skip,ns)) continue;
        const u8 *d=ent_data(s,off,i,&bytes); if(!d) return 0;
        if(!add(t,n,tag,get16(e+2),get32(e+4),d)) return 0;
    }
    return 1;
}
static void sort(ent_t *t,u32 n) {
    for(u32 i=1;i<n;i++) for(u32 j=i;j>0 && t[j-1].tag>t[j].tag;j--) {
        ent_t x; copy((u8 *)&x,(u8 *)&t[j],sizeof(x)); copy((u8 *)&t[j],(u8 *)&t[j-1],sizeof(x));
        copy((u8 *)&t[j-1],(u8 *)&x,sizeof(x));
    }
}
/* IFD then its out-of-line data; stored offsets are (position - rel). Returns position. */
static u32 emit(out_t *w,ent_t *t,u32 n,u32 rel) {
    sort(t,n);
    for(u32 i=1;i<n;i++) if(t[i].tag==t[i-1].tag) w->bad=1;
    pad2(w); if(w->bad) return 0;
    u32 at=w->pos; u8 b[2]; set16(b,n); put(w,b,2);
    u32 vals=w->pos; put(w,0,12*n+4);
    if(w->bad) return 0;
    for(u32 i=0;i<n;i++) {
        u8 *e=w->o+vals+12*i;
        set16(e,t[i].tag); set16(e+2,t[i].type); set32(e+4,t[i].count);
        if(t[i].eslot) w->patch[t[i].eslot]=vals+12*i;
        if(t[i].slot) w->patch[t[i].slot]=vals+12*i+8;
        if(t[i].bytes<=4) { if(t[i].data) copy(e+8,t[i].data,t[i].bytes); continue; }
        pad2(w); if(w->bad) return 0;
        set32(w->o+vals+12*i+8,w->pos-rel);
        if(t[i].dslot) w->patch[t[i].dslot]=w->pos;
        put(w,t[i].data,t[i].bytes);
    }
    return w->bad?0:at;
}
static void patch32(out_t *w,u32 slot,u32 v) { if(!w->patch[slot]) { w->bad=1; return; } set32(w->o+w->patch[slot],v); }

typedef struct { u64 addr; u32 size; } stream_t;
static int stream(u64 d,stream_t *s) {
    if(!d) return 0;
    s->addr=LOAD64(d+8); s->size=LOAD32(d+0x10);
    return s->addr && s->size>=4 && s->size<0x2000000 && s->addr+s->size>s->addr;
}
typedef struct {
    u32 hdr_end,vga_at,fhd_at,main_at,raw_at,end_at,mn_at,thumb_bytes;   /* main_at: where the embedded full-size JPEG goes */
    stream_t main,vga,fhd,jfr;           /* jfr: the embedded full-size JPEG (the main JPEG, or HN4's preview in Y) */
} lay_t;
static u8 *nb(u8 *p,const char *v,const u8 *body,u32 n,u32 zeros) {   /* "0100"+body[+0000]+CRC16 */
    copy(p,(const u8 *)v,4); copy(p+4,body,n); zero(p+4+n,zeros);
    set16(p+4+n+zeros,crc16(p,4+n+zeros)); return p;
}

/* HN15: block k of ni_tag[] from its stock leaf, into its own slot. Returns the byte count, or 0 when the result is
 * not "dddd" + body + CRC16 inside the slot; the block is then left out, as before HN15. */
static u32 stock_block(u32 k,u64 m,u8 *wk) {
    u8 *c=wk+NI_CTX,*o=wk+NI_STOCK+NI_SLOT*k;
    zero(c,0x60); zero(o,NI_SLOT);
    set64(c+0x18,m); set64(c+0x48,(u64)o); set64(c+0x50,(u64)o);       /* M; base and cursor of the block data */
    NI_LEAF(ni_leaf[k])(c,c+0x10,c+0x30);
    u32 n=get16(c+4); u64 used=get64(c+0x50)-(u64)o;
    if(get16(c+6) || n<8 || n>used || used>NI_SLOT) return 0;
    for(u32 i=0;i<4;i++) if(o[i]<'0' || o[i]>'9') return 0;
    if(get16(o+n-2)!=crc16(o,n-2)) return 0;
    return n;
}
/* HN15: MakerNote 0x008c as leaf 0x406eb8e4 writes it: 'I','0' and zeros, unless the Picture Control contrast is "User"
 * (M+0x330 == 1) or M+0x42c == 1; the leaf then copies the 578-byte curve from M+0x259c (M+0x2570 != 0) or through the
 * pointer at M+0x420. Only a curve inside M is taken here: any other pointer leaves the tag out, as before HN15,
 * instead of being read through. */
static const u8 *curve(u64 m,u8 *o) {
    zero(o,578);
    if(LOAD32(m+0x330)!=1 && LOAD8(m+0x42c)!=1) { o[0]='I'; o[1]='0'; return o; }
    if(!LOAD32(m+0x2570) && LOAD64(m+0x420)!=m+0x259c) return 0;
    for(u32 i=0;i<578;i++) o[i]=LOAD8(m+0x259c+i);
    return o;
}
/* HN15: SubIFD 3..5 as the stock leaves 0x406edab4.. write them when the frame has no such image (descriptors 5..7
 * absent): 0 x 0, no strip. The stock reader needs the three IFDs to exist; its retouch path frees a buffer whose
 * StripByteCounts is 0 (0x407ca340..). */
static u32 placeholder(out_t *w,ent_t *t,const u8 *v,const u8 *bits,const u8 *comp) {
    u32 n=0;
    add(t,&n,0x00fe,4,1,v+68); add(t,&n,0x0100,4,1,v+72); add(t,&n,0x0101,4,1,v+72);
    add(t,&n,0x0102,3,1,bits); add(t,&n,0x0103,3,1,comp); add(t,&n,0x0106,3,1,v+62);
    add(t,&n,0x0111,4,1,v+72); add(t,&n,0x0115,3,1,v+62); add(t,&n,0x0116,4,1,v+72);
    add(t,&n,0x0117,4,1,v+72); add(t,&n,0x011a,5,1,rat300); add(t,&n,0x011b,5,1,rat300);
    add(t,&n,0x011c,3,1,v+62); add(t,&n,0x0128,3,1,v+64);
    return emit(w,t,n,0);
}

/* Header block: TIFF, IFD0, SubIFDs, GPS, Exif, thumbnail, MakerNote (+PreviewIFD); the
 * VGA preview stream follows directly as the MakerNote's last bytes.
 * h is the CPU view of the stock JPEG header buffer: SOI, APP1 Exif, APP1 XMP, APP2 MPF. */
/* MakerNote 0x0056 (stock writer 0x406ea4e8): version, burst-start file id, shot number, burst flag at +12.
 * The stock header was made for the JPEG plan, so the start id has type 0 (JPG). When this card gets only the NEF,
 * give the start id the NEF type, as prepare() does for nid. Only the type nibble changes, and only for an id the
 * stock validator 0x4086cd5c accepts (bits 4, 30, 31 clear). buf: 16 bytes that outlive emit(). */
static void fix56(ent_t *t,u32 n,u32 flags,u8 *buf) {
    if(!(flags&F_NEFONLY)) return;
    for(u32 i=0;i<n;i++) {
        if(t[i].tag!=0x0056 || t[i].type!=7 || t[i].count!=16 || !t[i].data) continue;
        copy(buf,t[i].data,16); u32 st=get32(buf+4);
        if(buf[12] && st && !(st&0xC0000010u)) { set32(buf+4,(st&~15u)|2u); t[i].data=buf; }
        return;
    }
}
static int build(out_t *w,const u8 *h,u32 hl,const u32 *hlen,u64 m,lay_t *L,u32 flags,u8 *wk,u32 cls,u32 dims) {
    ent_t *t=(ent_t *)(wk+TAB); u32 n;
    if(hl<0x400 || get32(h)!=0xe1ffd8ffu || LOAD32(m+0x2bc)!=0) return 0;   /* M+0x2bc=0: RGGB */
    if(cls!=C_HE && cls!=C_HS) return 0;
    u32 payload=payload_of(cls,dims),code=cls==C_HS?14u:13u;   /* NEF compression: 13 HE, 14 HE* (leaf 0x406ea044) */
    u32 rw=dims&0xffffu,rh=dims>>16;                          /* HN13: the frame's geometry, FX or DX */
    if(!payload) return 0;
    u32 l1=(u32)h[4]<<8|h[5];
    if(l1<16 || 4+l1>hl || !equal(h+6,(const u8 *)"Exif\0\0",6)) return 0;
    src_t T={h+12,l1-8};
    if(get32(T.b)!=0x002a4949u) return 0;
    const u8 *xmp=0; u32 xmpn=0,at=4+l1,mpf=0;
    while(at+4<=hl && h[at]==0xff && (h[at+1]==0xe1 || h[at+1]==0xe2)) {
        u32 len=(u32)h[at+2]<<8|h[at+3]; if(len<2 || len>hl-at-2) return 0;
        if(h[at+1]==0xe1 && len>2+29 && equal(h+at+4,xmp_ns,29)) { xmp=h+at+4+29; xmpn=len-2-29; }
        if(h[at+1]==0xe2 && len>16 && equal(h+at+4,(const u8 *)"MPF\0",4)) mpf=at+8;
        at+=2+len;
    }
    if(!mpf || at!=hl) return 0;
    /* MPF index must describe exactly this header plus the three descriptor streams. */
    { src_t P={h+mpf,hl-mpf};
      if(get32(P.b)!=0x002a4949u) return 0;
      const u8 *mp=find(&P,get32(P.b+4),0xb002,7,48);
      if(!mp) return 0;
      if(get32(mp+4)!=hlen[0]+L->main.size-2 || get32(mp+20)!=hlen[1]+L->vga.size-2 ||
         get32(mp+36)!=hlen[2]+L->fhd.size-2) return 0; }
    u32 i0=get32(T.b+4),n0=ifd_count(&T,i0); if(!n0) return 0;
    u32 i1=get32(T.b+i0+2+12*n0);
    const u8 *x0=find(&T,i0,0x8769,4,1); if(!x0) return 0;
    u32 ix=get32(x0); if(!ifd_count(&T,ix)) return 0;
    const u8 *g0=find(&T,i0,0x8825,4,1); u32 ig=g0?get32(g0):0;
    if(g0 && !ifd_count(&T,ig)) return 0;
    const u8 *tho=find(&T,i1,0x0201,4,1),*thl=find(&T,i1,0x0202,4,1);
    if(!tho || !thl) return 0;
    u32 thumb=get32(tho),thn=get32(thl);
    if(thn<4 || thumb>T.n || thn>T.n-thumb || get16(T.b+thumb)!=0xd8ff || get16(T.b+thumb+thn-2)!=0xd9ff) return 0;
    const u8 *dto=find(&T,ix,0x9003,2,20);
    /* MakerNote */
    u32 mnc=0,mnoff=0,nx=ifd_count(&T,ix);
    for(u32 i=0;i<nx;i++) if(get16(T.b+ix+2+12*i)==0x927c) { mnc=get32(T.b+ix+2+12*i+4); mnoff=get32(T.b+ix+2+12*i+8); }
    if(mnc<64 || mnoff>T.n || mnc>T.n-mnoff || !equal(T.b+mnoff,nikon2,14)) return 0;
    src_t MN={T.b+mnoff+10,mnc-10}; u32 im=get32(MN.b+4); if(!ifd_count(&MN,im)) return 0;
    const u8 *wb=find(&MN,im,0x000c,5,4),*v54=find(&MN,im,0x0054,7,20),*bnd=find(&MN,im,0x0016,3,4);
    if(!wb || !v54 || !bnd) return 0;
    u32 bx=get16(bnd),by=get16(bnd+2),iw=get16(bnd+4)-bx,ih=get16(bnd+6)-by;
    if(get16(bnd+4)<=bx || get16(bnd+6)<=by || iw>rw || ih>rh || (rw-iw)&1 || (rh-ih)&1) return 0;
    u8 *v=wk+NI;                    /* small computed values */
    for(u32 k=0;k<4;k++) set16(v+k*2,LOAD16(m+0x2b4+2*k));                 /* black   v+0  */
    set16(v+8,(rw-iw)/2); set16(v+10,(rh-ih)/2); set16(v+12,iw); set16(v+14,ih);     /* crop v+8 */
    copy(v+16,(const u8 *)"0100",4); set32(v+20,payload); set32(v+24,1);  /* 0x0058  v+16 */
    u32 jfr=(flags&F_FULL)?L->jfr.size:L->fhd.size;
    set32(v+28,rw); set32(v+32,rh); set32(v+36,payload); set32(v+40,jfr);
    set32(v+44,thn); set32(v+48,L->fhd.size); set32(v+52,L->vga.size); set16(v+56,14); set16(v+58,34713);
    set16(v+60,32803); set16(v+62,1); set16(v+64,2); set16(v+66,6); set32(v+68,1); set32(v+72,0);
    set16(v+76,8); set16(v+78,12);                                           /* HN15: placeholder bits  v+76 */
    set16(v+80,LOAD16(m+0x288)); set16(v+82,LOAD16(m+0x28a));                /* HN15: MakerNote 0x0046 (leaf 0x406e9c48)  v+80 */
    u8 *m51=v+96; copy(m51,he51,24); m51[10]=(u8)code;                       /* MakerNote 0x0051  v+96 */
    u8 *ncode=v+120; ncode[0]=(u8)code; ncode[1]=0;                          /* NEFInfo 0xd body  v+120 */
    /* NEFInfo (RAW IFD 0xc7d5): blocks 8,9,a,b,d,f; CRC16 per block. Adobe needs 9 and d.
     * HN15: and 5, 6, 7, 0xc, 0x10..0x13 from the stock leaves (the stock NEF list; 0xe is not in an HE file). */
    u8 *nib=v+128; u8 *b8=nb(nib,"0100",v54+4,16,2),*b9=nib+32,*ba=nib+80,*bb=nib+96,*bd=nib+112,*bf=nib+128;
    copy(b9,wb,32); zero(b9+32,2); set16(b9+34,crc16(b9,34));
    nb(ba,"0100",v,8,0); nb(bb,"0100",v+8,8,0); nb(bd,"0100",ncode,2,0); nb(bf,"0100",v+20,8,0);
    out_t ni; zero((u8 *)&ni,sizeof(ni)); ni.o=wk+NI_OUT; ni.cap=NI_CAP; put(&ni,nikon_ni,18); n=0;
    add(t,&n,0x8,7,24,b8); add(t,&n,0x9,7,36,b9); add(t,&n,0xa,7,14,ba);
    add(t,&n,0xb,7,14,bb); add(t,&n,0xd,7,8,bd); add(t,&n,0xf,7,14,bf);
    for(u32 k=0;k<8;k++) { u32 c=stock_block(k,m,wk); if(c) add(t,&n,ni_tag[k],7,c,wk+NI_STOCK+NI_SLOT*k); }
    if(emit(&ni,t,n,10)!=18 || ni.bad) return 0;
    const u8 *nefinfo=wk+NI_OUT; u32 nin=ni.pos;
    const u8 *cc=curve(m,wk+NI_CURVE);
    /* ---- emission ---- */
    u8 hd[8]={'I','I',0x2a,0,8,0,0,0}; put(w,hd,8);
    n=0; if(!copy_entries(&T,i0,t,&n,skip0,sizeof(skip0)/2)) return 0;
    add(t,&n,0x00fe,4,1,v+68); add(t,&n,0x0103,3,1,v+66);
    ent_t *e=add(t,&n,0x014a,4,6,0); if(!e) return 0; e->dslot=P_SUB;   /* HN15: always the six of a camera NEF */
    e=add(t,&n,0x0201,4,1,0); if(!e) return 0; e->slot=P_THUMB;
    add(t,&n,0x0202,4,1,v+44); add(t,&n,0x0214,5,6,refbw);
    if(xmp) add(t,&n,0x02bc,1,xmpn,xmp);
    e=add(t,&n,0x8769,4,1,0); if(!e) return 0; e->slot=P_EXIF;
    if(g0) { e=add(t,&n,0x8825,4,1,0); if(!e) return 0; e->slot=P_GPS; }
    if(dto) add(t,&n,0x9003,2,20,dto);
    if(!add(t,&n,0x9216,1,4,tiffep)) return 0;
    if(emit(w,t,n,0)!=8) return 0;
    u32 sub[6];
    n=0; add(t,&n,0x00fe,4,1,v+68); add(t,&n,0x0103,3,1,v+66); add(t,&n,0x011a,5,1,rat300);
    add(t,&n,0x011b,5,1,rat300); add(t,&n,0x0128,3,1,v+64);
    e=add(t,&n,0x0201,4,1,0); e->slot=P_JFR; add(t,&n,0x0202,4,1,v+40); add(t,&n,0x0213,3,1,v+64);
    sub[0]=emit(w,t,n,0);
    n=0; add(t,&n,0x00fe,4,1,v+72); add(t,&n,0x0100,4,1,v+28); add(t,&n,0x0101,4,1,v+32);
    add(t,&n,0x0102,3,1,v+56); add(t,&n,0x0103,3,1,v+58); add(t,&n,0x0106,3,1,v+60);
    e=add(t,&n,0x0111,4,1,0); e->slot=P_STRIP; add(t,&n,0x0115,3,1,v+62); add(t,&n,0x0116,4,1,v+32);
    add(t,&n,0x0117,4,1,v+36); add(t,&n,0x011a,5,1,rat300); add(t,&n,0x011b,5,1,rat300);
    add(t,&n,0x011c,3,1,v+62); add(t,&n,0x0128,3,1,v+64); add(t,&n,0x828d,3,2,cfa_dim);
    add(t,&n,0x828e,1,4,cfa_rggb); add(t,&n,0x9217,3,1,v+64); add(t,&n,0xc7d5,7,nin,nefinfo);
    add(t,&n,0xc7d6,1,1,one8);
    sub[1]=emit(w,t,n,0);
    /* SubIFD 2: the FHD JPEG. HN15: also without F_FULL, where SubIFD 0 is the same stream. */
    n=0; add(t,&n,0x00fe,4,1,v+68); add(t,&n,0x0103,3,1,v+66); add(t,&n,0x011a,5,1,rat300);
    add(t,&n,0x011b,5,1,rat300); add(t,&n,0x0128,3,1,v+64);
    e=add(t,&n,0x0201,4,1,0); e->slot=P_OTHER; add(t,&n,0x0202,4,1,v+48); add(t,&n,0x0213,3,1,v+64);
    sub[2]=emit(w,t,n,0);
    sub[3]=placeholder(w,t,v,v+76,v+62);          /* 8 bit, uncompressed */
    sub[4]=placeholder(w,t,v,v+78,v+58);          /* 12 bit, NEF compressed (34713) */
    sub[5]=placeholder(w,t,v,v+76,v+62);
    u32 gat=0;
    if(g0) { n=0; if(!copy_entries(&T,ig,t,&n,0,0)) return 0; gat=emit(w,t,n,0); }
    n=0; if(!copy_entries(&T,ix,t,&n,skipx,sizeof(skipx)/2)) return 0;
    e=add(t,&n,0x927c,7,4,0); if(!e) return 0; e->eslot=P_MNENT;
    u32 xat=emit(w,t,n,0);
    pad2(w); u32 tat=w->pos; put(w,T.b+thumb,thn);
    /* MakerNote rebuilt with its IFD at offset 8; every value relocated into it. */
    pad2(w); L->mn_at=w->pos; u32 mb=w->pos+10; put(w,nikon2,18);
    n=0; if(!copy_entries(&MN,im,t,&n,skipm,sizeof(skipm)/2)) return 0;
    fix56(t,n,flags,v+384);                                               /* 0x0056  v+384 (free: NEFInfo uses v+0..v+272, v+512..) */
    add(t,&n,0x0004,2,8,quality_raw);
    add(t,&n,0x0044,3,1,jpgc_nef);
    e=add(t,&n,0x0011,4,1,0); if(!e) return 0; e->slot=P_MNPV;
    add(t,&n,0x003d,3,4,v); add(t,&n,0x0045,3,4,v+8); add(t,&n,0x0046,3,2,v+80); add(t,&n,0x0051,7,24,m51);
    if(cc) add(t,&n,0x008c,7,578,cc);
    add(t,&n,0x00a4,7,4,mn_a4);
    if(!add(t,&n,0x0058,7,12,v+16)) return 0;
    if(emit(w,t,n,mb)!=mb+8) return 0;
    n=0; add(t,&n,0x0103,3,1,v+66); add(t,&n,0x011a,5,1,rat300); add(t,&n,0x011b,5,1,rat300);
    add(t,&n,0x0128,3,1,v+64); e=add(t,&n,0x0201,4,1,0); e->slot=P_PVSTART;
    add(t,&n,0x0202,4,1,v+52); add(t,&n,0x0213,3,1,v+64);
    u32 pat=emit(w,t,n,mb);
    pad2(w); if(w->bad || !sub[0] || !sub[1] || !sub[2] || !sub[3] || !sub[4] || !sub[5] || !xat || !pat) return 0;
    /* ---- layout of the streams after the header block ---- */
    L->hdr_end=w->pos; L->vga_at=w->pos; L->fhd_at=L->vga_at+L->vga.size;
    L->main_at=L->fhd_at+L->fhd.size;
    u32 end=L->main_at+((flags&F_FULL)?L->jfr.size:0);
    L->raw_at=(end+4095)&~4095u; L->end_at=L->raw_at+payload; L->thumb_bytes=thn;
    if(!w->patch[P_SUB]) return 0;
    for(u32 k=0;k<6;k++) set32(w->o+w->patch[P_SUB]+4*k,sub[k]);
    patch32(w,P_OTHER,L->fhd_at);
    patch32(w,P_THUMB,tat); patch32(w,P_EXIF,xat); if(g0) patch32(w,P_GPS,gat);
    patch32(w,P_JFR,(flags&F_FULL)?L->main_at:L->fhd_at); patch32(w,P_STRIP,L->raw_at);
    patch32(w,P_MNPV,pat-mb); patch32(w,P_PVSTART,L->vga_at-mb);
    if(!w->patch[P_MNENT]) return 0;
    set32(w->o+w->patch[P_MNENT]+4,L->vga_at+L->vga.size-L->mn_at);
    set32(w->o+w->patch[P_MNENT]+8,L->mn_at);
    return !w->bad;
}


/* ---------------- P3' file write ---------------- */
#ifdef NEG_RAW_ROUTE                 /* negative-control builds only: HN8's fallback */
static int write_all(int fd,u64 p,u32 n) { u32 c=0; return WRITE(fd,p,n,&c)==0 && c==n; }
#endif
static int jpg_name(u32 id,char *fin,char *tmp) {
    u64 fo=DCF_GET(id); if(!fo) return 0;
    u64 nm=DCF_NAME(fo); u32 len=nm?LOAD32(nm+0x20):0; int ok=0;
    if(nm && len>=12 && len<60) {
        for(u32 i=0;i<len;i++) fin[i]=(char)LOAD8(nm+i);
        fin[len]=0; ok=1;
        for(u32 i=0;i<len;i++) if(!fin[i]) ok=0;
        char *x=fin+len-4;
        if(x[0]!='.' || (x[1]|32)!='j' || (x[2]|32)!='p' || (x[3]|32)!='g') ok=0;
        if(ok) { x[1]='N'; x[2]='E'; x[3]='F'; copy((u8 *)tmp,(const u8 *)fin,len+1); tmp[len-1]='_'; }
    }
    DCF_PUT(fo);
    return ok;
}

/* What the writer task's call identifies: the retained frame, its record and the JPEG's card. */
typedef struct {
    u64 r,m,e,J,t_enter;
    u8 *q;
    u32 flags,budget,shot,jid;
    u32 dual,second,role;                /* HN7R: a two-card frame (dual_list), the secondary card's entry, the role */
    char drive;
} job_t;
/* Everything one NEF needs; lives in the work block so the task stack stays shallow. */
typedef struct {
    u64 r,m,e,J,data;
    u64 t_enter,t_header,t_reg0,t_reg1,t_jpeg0,t_jpeg1,t_nef0,t_raw0,t_raw1,t_raw2;
    u8 *q,*raw,*wk;
    u32 flags,budget,shot,jid,nid,hl,hlen[3],hdr_bytes,total,nsegs,chunks,raw_status,reg_rc,st_jpeg,st_nef,cancel_ok,payload_bytes;
    u32 mtype,stock_mode;                /* registered member type (NEF = 2) and the stock file's writer mode (JPEG = 0) */
    u32 cls,rawrec;                      /* HN5: payload class of the frame's E (C_HE / C_HS), RAW recording item at submit */
    u64 dims_src;                        /* the stock JPEG's descriptor 0 (width/height words), 0 if none */
    u32 dual,second,role;                /* HN7R: as job_t */
    char drive,fin[64],tmp[64];
    lay_t L;
} plan_t;

/* HN7R: R lists of a C15/C30 frame on two cards in roles 1..3 (the stock grouping's "backup style" for a one-JPEG plan):
 * two lists of one JPEG each, list 0 on the primary slot and list 1 on the other card, nothing in the second list set
 * (R+0x38). HN7 took role 2 only. */
static int two_lists(u64 r,u32 pri) {
    u32 a=LOAD32(r+0x1c),b=LOAD32(r+0x28);
#ifdef NEG_NO_SPLIT                   /* negative-control builds only: HN6's writer (no two-card frames) */
    return 0;
#endif
    return pri<=1 && LOAD32(r+0x14)==2 && LOAD32(r+0x18)==1 && LOAD32(r+0x24)==1 && LOAD32(r+0x38)==0 &&
           (a&15)==0 && (b&15)==0 && (a>>29)==pri && (b>>29)==(pri^1u);
}
/* HN8: the role and the primary slot of the frame's submit (A_SUBMIT); a record without them (never made by HN8's mark)
 * is not a two-card frame. */
static u32 submit_role(const u8 *q) {
#ifdef NEG_ROLE_AT_WRITE              /* negative-control builds only: HN7R's read in the writer task */
    return LOAD32(G_ROLE);
#endif
    u32 v=get32(q+A_SUBMIT); return (v&0xff000000u)==SUBMIT_MARK ? (v&0xffu) : 0u;
}
static u32 submit_primary(const u8 *q) {
#ifdef NEG_ROLE_AT_WRITE
    return LOAD32(G_PRIMARY);
#endif
    u32 v=get32(q+A_SUBMIT); return (v&0xff000000u)==SUBMIT_MARK ? ((v>>8)&0xffu) : 0xffu;
}
static int dual_list(u64 r,const u8 *q) { u32 role=submit_role(q); return role>=1 && role<=3 && two_lists(r,submit_primary(q)); }
/* HN7R: what one card of a two-card frame gets, as the stock camera writes a single shot of that quality and role. */
#define ACT_NEF 1u                    /* the NEF; this card's JPEG member cancelled */
#define ACT_BOTH 2u                   /* the JPEG and the NEF (HN6's RAW + JPEG flow) */
#define ACT_JPEG 3u                   /* the stock JPEG only */
static u32 dual_action(u32 flags,u32 role,u32 second) {
#ifdef NEG_HN7_SECOND                 /* negative-control builds only: HN7's secondary card (cancelled for RAW, JPEG otherwise) */
    if(second) return (flags&F_RAWONLY)?0u:ACT_JPEG;
#endif
    if(flags&F_RAWONLY) return ACT_NEF;
    if(role==2) return second?ACT_JPEG:ACT_NEF;
    return ACT_BOTH;
}
/* The flags a frame's NEF is made with: the record's, without the full-size preview whose mark is missing. */
static u32 nef_flags(const u8 *q) {
    u32 flags=get32(q+0x60);
    /* HN3: without P7's mark the main JPEG has the menu quality; keep the NEF FHD-only (the S3 layout) */
    if((flags&F_PVQ) && get32(q+0x7c)!=PVQ_MARK) flags&=~F_FULL;
    /* HN4: without hook J's mark there is no preview; the NEF is FHD-only (the S2 layout), never the main JPEG */
    if((flags&F_PREV) && get32(q+A_PMARK)!=PVJ_MARK) flags&=~F_FULL;
    return flags;
}

/* The file the writer task is about to write is the JPEG of a retained frame. */
__attribute__((unused)) static int eligible(u64 J,u32 mode,job_t *jb) {
    u64 job,r,m,e,fe; u32 idx,flags,dual=0; u8 *q;
    if(mode!=0) return 0;
    job=LOAD64(G_WRITER_JOB); if(!job || LOAD8(job+4)) return 0;
    r=LOAD64(job+0x18); idx=LOAD32(job+0xbc)-1;
    if(!r || idx>=4) return 0;
    m=LOAD64(r+0x790); e=LOAD64(r+0x748);
    if(!m || !e || LOAD32(m)!=3) return 0;
    fe=job+0xc0+(u64)idx*0x2d8;
    if(J!=fe+0x48) return 0;
    q=bound(r,e,Q_RETAINED);
    if(!q || LOAD64(J+8)!=m || (LOAD32(J)&15)!=0 || get32(q+0x70)!=LOAD32(m+0x2508)) return 0;
    flags=nef_flags(q);
    /* HN7: the primary card's entry of a two-card frame (list 0 = entry 1, written first); the record not marked yet */
    if(dual_list(r,q) && LOAD32(r+0x1c)==LOAD32(J) && idx==1 && get32(q+A_SPLIT)==0) dual=1;
    /* the stock database path handles exactly one group of one file on the primary list; HN9: only the stock database
       path is left (P2 always sets F_DCF), a frame without it stays stock */
    if(!(flags&F_DCF)) return 0;
    if(!dual && !(LOAD32(r+0x14)==1 && LOAD32(r+0x18)==1 && LOAD32(r+0x1c)==LOAD32(J) && LOAD32(r+0x38)==0)) return 0;
    /* HN6: the card of the JPEG's file id (bits 29..31: 0 = A:, 1 = B:), the slot the stock registration uses */
    if((LOAD32(J)>>29)>1) return 0;
    jb->r=r; jb->m=m; jb->e=e; jb->J=J; jb->q=q; jb->flags=flags; jb->budget=get32(q+0x68);
    jb->shot=get32(q+0x70); jb->jid=LOAD32(J); jb->drive=(char)('A'+(LOAD32(J)>>29)); jb->t_enter=now();
    jb->dual=dual; jb->second=0; jb->role=dual?submit_role(q):0u;
    return 1;
}

/* HN4: the preview hook J encoded into this frame's own Y: the record's Y, the stock JPEG's descriptors are that
 * Y's (descriptor 0 = Y+0x38), Y+0x1e set, the region and byte count hook J recorded, within the capacity. */
static int preview_stream(plan_t *p,u64 d0) {
    u64 y=LOAD64(p->r+0x6a8); const u8 *q=p->q;
    if(!y || get64(q+A_Y)!=y || d0!=y+0x38 || LOAD8(y+0x1e)!=1 || LOAD32(y+0x100)!=1) return 0;
    if(!stream(y+0x100,&p->L.jfr) || p->L.jfr.addr!=get64(q+A_YADDR) || p->L.jfr.size!=get32(q+A_PBYTES) ||
       p->L.jfr.size>LOAD32(y+0xf8) || LOAD32(y+0xf8)!=get32(q+A_YCAP)) return 0;
    return 1;
}

/* Parse the JPEG's own buffers, check the names and build the NEF header block. CPU only:
 * no card, database or lock is touched. Returns 0 (work block freed) when no NEF can be made. */
__attribute__((noinline)) static plan_t *prepare(const job_t *jb) {
    u64 J=jb->J,lp=LOAD64(J+0x18),da=LOAD64(J+0x10),hp; u32 hcap,hl;
    u8 *raw,*wk; plan_t *p; out_t w;
    if(!lp || !da) return 0;
    hp=LOAD64(lp); hcap=LOAD32(lp+8); hl=LOAD32(lp+0xc);
    if(!hp || hl<0x400 || hl>hcap || hl>0x40000) return 0;
    raw=(u8 *)ALLOC(WORK_BYTES+63,0); if(!raw) return 0;
    wk=(u8 *)(((u64)raw+63)&~63ul);
    zero(wk+TAB,WORK_BYTES-TAB);
    p=(plan_t *)(wk+PLAN);
    p->raw=raw; p->wk=wk; p->r=jb->r; p->m=jb->m; p->e=jb->e; p->J=J; p->q=jb->q; p->flags=jb->flags;
    p->budget=jb->budget; p->shot=jb->shot; p->jid=jb->jid; p->drive=jb->drive; p->t_enter=jb->t_enter;
    p->dual=jb->dual; p->second=jb->second; p->role=jb->role;
    p->nid=(jb->jid&~15u)|2u; p->data=LOAD64(jb->e+0x40);
    p->hl=hl; p->hlen[0]=hl; p->hlen[1]=LOAD32(lp+0x1c); p->hlen[2]=LOAD32(lp+0x2c);
    p->cls=e_class(jb->e); p->rawrec=get32(jb->q+A_RAWREC);
    if(p->cls!=get32(jb->q+A_CLASS)) { FREE(raw); return 0; }         /* the record was made for this allocation */
    p->reg_rc=0; p->st_jpeg=0xffffffffu; p->st_nef=0xffffffffu; p->cancel_ok=0xffffffffu; p->payload_bytes=payload_of(p->cls,LOAD32(jb->e+0x38));
    p->mtype=2; p->stock_mode=0; p->dims_src=LOAD64(da);
    if(!stream(LOAD64(da),&p->L.main) || !stream(LOAD64(da+8),&p->L.vga) || !stream(LOAD64(da+16),&p->L.fhd)) goto bad;
    if(p->flags&F_FULL) {
        if(!(p->flags&F_PREV)) p->L.jfr=p->L.main;
        else if(!preview_stream(p,LOAD64(da))) p->flags&=~F_FULL;    /* no valid preview: FHD-only, as without hook J's mark */
    }
    if(!jpg_name(p->jid,p->fin,p->tmp) || p->fin[0]!=p->drive || p->fin[1]!=':' || EXISTS(p->fin)>=0 || EXISTS(p->tmp)>=0) goto bad;
    zero((u8 *)&w,sizeof(w)); w.o=wk; w.cap=HDR_MAX;
    u32 only=(p->dual?dual_action(p->flags,p->role,p->second):((p->flags&F_RAWONLY)?ACT_NEF:ACT_BOTH))==ACT_NEF?F_NEFONLY:0u;   /* as flow() */
    if(!build(&w,(const u8 *)XLATE(hp),hl,p->hlen,p->m,&p->L,p->flags|only,wk,p->cls,LOAD32(jb->e+0x38)) || p->L.end_at<p->L.raw_at) goto bad;
    p->hdr_bytes=w.pos; p->total=p->L.end_at+((p->flags&F_FOOTER)?512u:0u); p->t_header=now();
    return p;
bad:
    FREE(raw);
    return 0;
}

static void build_footer(plan_t *p,u32 route) {
    u8 *f=p->wk+FOOT;
    zero(f,512); copy(f,foot_magic,16);
    /* +0x18: bit 0 RAW-only; HN7R: bit 1 two-card frame, bit 2 the secondary card's file, bits 8..11 the role */
    set32(f+0x10,4); set32(f+0x14,route);
    set32(f+0x18,((p->flags&F_RAWONLY)?1u:0u)|(p->dual?2u|(p->second?4u:0u)|(p->role&15u)<<8:0u)); set32(f+0x1c,p->flags);
    set64(f+0x20,p->t_enter); set64(f+0x28,p->t_header); set64(f+0x30,p->t_reg0); set64(f+0x38,p->t_reg1);
    set64(f+0x40,p->t_jpeg0); set64(f+0x48,p->t_jpeg1); set64(f+0x50,p->t_nef0);
    set32(f+0x58,p->reg_rc); set32(f+0x5c,p->st_jpeg);
    set32(f+0x60,p->hdr_bytes); set32(f+0x64,p->L.vga.size); set32(f+0x68,p->L.fhd.size);
    set32(f+0x6c,(p->flags&F_FULL)?p->L.jfr.size:0u); set32(f+0x70,p->L.raw_at); set32(f+0x74,p->L.end_at);
    set32(f+0x78,p->shot); set32(f+0x7c,get32(p->q+0x18));
    set32(f+0x80,p->jid); set32(f+0x84,p->nid); set32(f+0x88,p->hl); set32(f+0x8c,p->nsegs);
    set64(f+0x90,p->r); set64(f+0x98,p->e); set64(f+0xa0,p->m); set64(f+0xa8,p->data); set64(f+0xb0,p->J);
    set64(f+0xb8,(u64)(p->wk+JP));
    set64(f+0xc0,p->L.vga.addr); set64(f+0xc8,p->L.fhd.addr); set64(f+0xd0,(p->flags&F_FULL)?p->L.jfr.addr:0ul);
    set64(f+0xd8,p->t_raw0); set64(f+0xe0,p->t_raw1); set64(f+0xe8,p->t_raw2);
    set32(f+0xf0,p->chunks); set32(f+0xf4,p->raw_status); set64(f+0xf8,p->L.main.addr);
    set32(f+0x100,p->cls); set32(f+0x104,p->rawrec);    /* v4: payload class (2 HE, 4 HE*) and RAW recording item */
    copy(f+0x108,identity,8); copy(f+0x110,(const u8 *)p->fin,48);
    copy(f+0x140,p->q,128);
    copy(f+0x1c0,p->q+A_KIND,0x3c);              /* aux +0x84..+0xbf: kind, value, M before, applied, Y, preview */
    set32(f+0x1fc,crc32(f,0x1fc));
}

/* HN1 route: raw file calls under a temporary name, then rename. HN8 used it as the fallback when registration failed;
 * the NEF then took card space the database had not reserved. HN9: only in the control NEG_RAW_ROUTE. */
#ifdef NEG_RAW_ROUTE
__attribute__((noinline)) static void raw_route(plan_t *p) {
    u8 *wk=p->wk; const lay_t *L=&p->L;
    u32 flags=p->flags,budget=p->budget,status=S_DONE,written=0,chunks=0,payload=p->payload_bytes;
    u32 mainsz=(flags&F_FULL)?L->jfr.size:0u,pad=L->raw_at-L->main_at-mainsz;
    u64 t0=now(),after; int fd;
#ifndef NEG_NO_CLEAN                 /* negative-control builds only */
    CLEAN(wk,p->hdr_bytes);
#endif
    CLEAN(wk+ZEROS,4096);
    fd=CREATE(p->tmp,0x20);
    if(fd<0) { stop_file(p->drive,S_WRITE_FAIL,p->shot); return; }
    p->t_raw0=now();
    if(!write_all(fd,(u64)wk,p->hdr_bytes) || !write_all(fd,L->vga.addr,L->vga.size) || !write_all(fd,L->fhd.addr,L->fhd.size) ||
       (mainsz && !write_all(fd,L->jfr.addr,mainsz)) || (pad && !write_all(fd,(u64)(wk+ZEROS),pad)))
        status=S_WRITE_FAIL;
    p->t_raw1=now();
    if(status==S_DONE && p->t_raw1-t0>=budget) status=S_BUDGET;
#ifdef NEG_READ_PAYLOAD               /* negative-control builds only */
    if(LOAD32(p->data+0x1000)==0x12345678u) status=S_WRITE_FAIL;
#endif
    while(status==S_DONE && written<payload) {
        u32 part=payload-written,c=0; int rc;
        if(part>CHUNK) part=CHUNK;
        rc=WRITE(fd,p->data+written,part,&c);
        written+=c<=part?c:0u; chunks++;
        after=now();
        if(rc!=0 || c!=part) status=S_WRITE_FAIL;
        else if(after-t0>=budget && written<payload) status=S_BUDGET;
    }
    p->t_raw2=now(); p->chunks=chunks; p->raw_status=status;
    if(flags&F_FOOTER) {
        build_footer(p,2); CLEAN(wk+FOOT,512);
        if(!write_all(fd,(u64)(wk+FOOT),512) && status==S_DONE) status=S_WRITE_FAIL;
    }
    if(CLOSE(fd)!=0 && status==S_DONE) status=S_WRITE_FAIL;
    if(status==S_DONE && RENAME(p->tmp,p->fin)!=0) status=S_RENAME_FAIL;
    if(status!=S_DONE) stop_file(p->drive,status,p->shot);
}
#endif

/* Add a member of the given DCF type (NEF = 2) to the group keyed by the first file id, exactly as the
 * stock creation does for a RAW+JPEG shot: creation lock held around the member add and the
 * remaining-shots update. */
__attribute__((noinline)) static u32 register_member(const plan_t *p,u32 type) {
    u32 drive=p->jid>>29,rc; u64 db; u8 ent[16] __attribute__((aligned(8)));
    if(drive>1) return RC_NO_DB;
    db=LOAD64(G_DB+8ul*drive); if(!db) return RC_NO_DB;
    zero(ent,16); set32(ent,type); set64(ent+8,p->total);       /* {type, 0, exact file bytes} */
    if(LOCK(G_CREATE_LOCK,0xc8,10)!=DB_OK) return RC_LOCK;
    rc=DB_ADD(db,p->jid,ent);
#ifndef NEG_NO_REMAIN                 /* negative-control builds only */
    if(rc==DB_OK) DB_REMAIN(1);
#endif
#ifndef NEG_NO_UNLOCK                 /* negative-control builds only */
    UNLOCK(G_CREATE_LOCK);
#endif
    return rc;
}

static int seg(u8 *jp,u32 *n,u64 addr,u32 size,u64 *sum) {
    if(!size) return 1;                                         /* empty segments never enter the table */
    if(*n>=SEG_MAX || !addr) return 0;
    set64(jp+0x68+16*(*n),addr); set32(jp+0x70+16*(*n),size); (*n)++; *sum+=size;
    return 1;
}
/* Write the registered NEF with the stock writer in its explicit-segment mode 3. */
__attribute__((noinline)) static u32 stock_nef(plan_t *p,u32 raw_only) {
    u8 *wk=p->wk,*jp=wk+JP,*a=wk+JA,*d=wk+JD,*t=wk+JT;
    const lay_t *L=&p->L;
    u32 n=0,mainsz=(p->flags&F_FULL)?L->jfr.size:0u,pad=L->raw_at-L->main_at-mainsz,nst;
    u64 sum=0,c0,c1;
    zero(jp,0x290); zero(a,32); zero(d,16); zero(t,32);
    set32(jp,p->nid); set64(jp+8,p->m); set64(jp+0x10,(u64)a);
    /* descriptor 0: the stock attribute step stores these two words as the object's width and
     * height; they are the JPEG's own, so a sibling write leaves the values unchanged */
#ifndef NEG_DIMS_ZERO                 /* negative-control builds only */
    if(p->dims_src) { set16(d+8,LOAD16(p->dims_src+4)); set16(d+10,LOAD16(p->dims_src+6)); }
#endif
    set64(a,(u64)d);
    if(raw_only && L->thumb_bytes && L->thumb_bytes<0x10000u) { set32(t+0x10,L->thumb_bytes); set64(a+0x18,(u64)t); }
    if(pad>4096 || !seg(jp,&n,(u64)wk,p->hdr_bytes,&sum) || !seg(jp,&n,L->vga.addr,L->vga.size,&sum) ||
       !seg(jp,&n,L->fhd.addr,L->fhd.size,&sum) || !seg(jp,&n,L->jfr.addr,mainsz,&sum) ||
       !seg(jp,&n,(u64)(wk+ZEROS),pad,&sum) || !seg(jp,&n,p->data,p->payload_bytes,&sum)) goto bad;
    p->t_nef0=now();
    if(p->flags&F_FOOTER) {
        p->nsegs=n+1;
        build_footer(p,1); CLEAN(wk+FOOT,512);
        if(!seg(jp,&n,(u64)(wk+FOOT),512,&sum)) goto bad;
    } else p->nsegs=n;
    if(sum!=p->total) goto bad;
#ifdef NEG_BAD_TOTAL                  /* negative-control builds only */
    sum+=1;
#endif
    set64(jp+0x30,sum); set16(jp+0x218,n);
#ifndef NEG_NO_CLEAN                  /* negative-control builds only */
    CLEAN(wk,p->hdr_bytes);
#endif
    CLEAN(wk+ZEROS,4096);
#ifdef NEG_READ_PAYLOAD               /* negative-control builds only */
    if(LOAD32(p->data+0x1000)==0x12345678u) goto bad;
#endif
#ifdef TEST_FORCE_BAD                 /* test builds only: take the internal-failure exit after registration */
    goto bad;
#endif
    /* The stock writer's completion (0x406cd6f8) reads M+0x118/+0x11c/+0x120 again for the playback file list
     * (callback 0x4070a6a8). Give it the NEF-typed start id the file carries (fix56), for this file's slot as
     * the stock selection picks it, and put the word back afterwards. */
    u64 sw=0; u32 sv=0;
    if(raw_only && LOAD32(p->m+0x120)) {
        u32 s0=LOAD32(p->m+0x118),s1=LOAD32(p->m+0x11c);
        sw=(s1 && ((s0>>29)&3u)!=((p->nid>>29)&3u))?p->m+0x11c:p->m+0x118;
        sv=LOAD32(sw);
        if(sv && !(sv&0xC0000010u)) STORE32(sw,(sv&~15u)|2u); else sw=0;
    }
    c0=now(); nst=ORIG_WRITE(0,3,(u64)jp); c1=now();
    if(sw) STORE32(sw,sv);
    if(nst!=0) stop_file(p->drive,S_WRITE_FAIL,p->shot);        /* the stock writer cancelled the member itself */
    else if(EXISTS(p->fin)<0) stop_file(p->drive,S_MISSING,p->shot);
    else if(c1-c0>=p->budget) stop_file(p->drive,S_BUDGET,p->shot);
    return nst;
bad:
#ifndef NEG_NO_CANCEL                 /* negative-control builds only */
    DB_CANCEL(p->nid);                                          /* never leave a reservation nobody writes */
#endif
    stop_file(p->drive,S_WRITE_FAIL,p->shot);
    return RC_INTERNAL;
}

/* RAW-only: the JPEG reservation is cancelled after the NEF is on the card. The cancel has no
 * result, so look at the object afterwards: gone, or no longer in a reserved state (2, 3, 8). */
__attribute__((noinline)) static int jpeg_cancelled(u32 jid) {
    u64 o; u32 st;
    DB_CANCEL(jid);
    o=DCF_GET(jid); if(!o) return 1;
    st=LOAD32(o+0x70); DCF_PUT(o);
    return !(st==2 || st==3 || st==8);
}

static void release_e(const job_t *jb) { unbind(jb->q); FREE_E(jb->e); STORE64(jb->r+0x748,0); }

/* Everything after the header is built: register, write the JPEG and the NEF, or fall back. */
__attribute__((noinline)) static u32 flow(plan_t *p,u64 J) {
    u32 st,act=p->dual?dual_action(p->flags,p->role,p->second):((p->flags&F_RAWONLY)?ACT_NEF:ACT_BOTH);
    p->t_reg0=now(); p->reg_rc=register_member(p,p->mtype); p->t_reg1=now();
    if(p->reg_rc!=DB_OK) {             /* HN9: no registration (no room on the card, or no lock): the stock JPEG only */
        st=ORIG_WRITE(0,p->stock_mode,J); p->st_jpeg=st;
#ifdef NEG_RAW_ROUTE                  /* negative-control builds only: HN8's NEF outside the database */
        if(st==0) raw_route(p);
#endif
    } else if(act==ACT_BOTH) {                                            /* RAW+JPEG: stock order JPEG, NEF */
#ifdef NEG_ORDER                      /* negative-control builds only: NEF before JPEG */
        p->st_nef=stock_nef(p,0);
#endif
        p->t_jpeg0=now(); st=ORIG_WRITE(0,p->stock_mode,J); p->t_jpeg1=now(); p->st_jpeg=st;
#ifndef NEG_ORDER
        p->st_nef=stock_nef(p,0);
#endif
    } else {                         /* RAW-only, or role 2's primary card: NEF first, then drop this card's JPEG member */
        p->st_nef=stock_nef(p,1);
        if(p->st_nef==0) p->cancel_ok=jpeg_cancelled(p->jid);
        if(p->st_nef==0 && p->cancel_ok==1) st=0;
        else { p->t_jpeg0=now(); st=ORIG_WRITE(0,p->stock_mode,J); p->t_jpeg1=now(); p->st_jpeg=st; }   /* NEF failed or the cancel did not hold */
    }
    return st;
}

__attribute__((noinline,unused)) static u32 take(const job_t *jb,u64 J) {
    plan_t *p; u32 st,act,kept=0;
    if(stopped(jb->drive)) { st=ORIG_WRITE(0,0,J); release_e(jb); return st; }   /* an earlier failure: JPEG only */
    p=prepare(jb);
    if(!p) { st=ORIG_WRITE(0,0,J); release_e(jb); return st; }          /* JPEG only, E released below */
    st=flow(p,J);
    /* HN7R: the primary card of a two-card frame written as planned: mark the record, keep E for the secondary entry */
    if(p->dual && !p->second && p->reg_rc==DB_OK && p->st_nef==0) {
        act=dual_action(p->flags,p->role,0);
        if((act==ACT_NEF && p->cancel_ok==1) || (act==ACT_BOTH && p->st_jpeg==0)) {
            set32(jb->q+A_SPLIT,SPLIT_MARK); set32(jb->q+A_SPLIT_JID,jb->jid); set32(jb->q+A_DUAL_ROLE,p->role);
            aux_seal(jb->q); kept=1;
        }
    }
    FREE(p->raw);
#ifndef NEG_LEAK_E                    /* negative-control builds only */
    if(!kept) release_e(jb);
#else
    (void)kept;
#endif
    return st;
}

/* HN7R: the secondary card's entry of a two-card frame whose primary entry was written: entry 0 (list 1, written after
 * list 0), same R, still retained, the record marked for this frame's primary file. The shape is checked against the
 * marked primary file and the role is the marked one, so a menu change between the two entries changes nothing. */
static int dual_second(u64 J,job_t *jb) {
    u64 job,r,m,e; u32 pj; u8 *q;
    job=LOAD64(G_WRITER_JOB); if(!job || LOAD8(job+4)) return 0;
    r=LOAD64(job+0x18);
    if(!r || LOAD32(job+0xbc)!=1 || J!=job+0xc0+0x48) return 0;
    m=LOAD64(r+0x790); e=LOAD64(r+0x748);
    if(!m || !e || LOAD64(J+8)!=m || !(q=bound(r,e,Q_RETAINED))) return 0;
    pj=get32(q+A_SPLIT_JID);
    if(get32(q+A_SPLIT)!=SPLIT_MARK || pj!=LOAD32(r+0x1c) || !two_lists(r,pj>>29) || LOAD32(J)!=LOAD32(r+0x28) ||
       get32(q+0x70)!=LOAD32(m+0x2508)) return 0;
    jb->r=r; jb->m=m; jb->e=e; jb->J=J; jb->q=q; jb->flags=nef_flags(q); jb->budget=get32(q+0x68);
    jb->shot=get32(q+0x70); jb->jid=LOAD32(J); jb->drive=(char)('A'+(LOAD32(J)>>29)); jb->t_enter=now();
    jb->dual=1; jb->second=1; jb->role=get32(q+A_DUAL_ROLE);
    return 1;
}
/* RAW (any role) and RAW + JPEG in roles 1 and 3: this card's own NEF from this entry (its own header, the frame's Y
 * descriptors), as on the primary card; E is released by take. Role 2 RAW + JPEG, or a separately sized secondary
 * JPEG (entry +4 set by the stock preparer, other descriptors): the stock JPEG, then E is released. */
__attribute__((noinline)) static u32 second(const job_t *jb,u64 J) {
    u64 da=LOAD64(J+0x10),y=LOAD64(jb->r+0x6a8); u32 act=dual_action(jb->flags,jb->role,1),st;
    if((act==ACT_NEF || act==ACT_BOTH) && LOAD8(J+4)==0 && da && y && LOAD64(da)==y+0x38) return take(jb,J);
#ifdef NEG_HN7_SECOND
    if(act==0 && jpeg_cancelled(LOAD32(J))) st=0; else
#endif
    st=ORIG_WRITE(0,0,J);
    release_e(jb);
    return st;
}

/* P3'. Original: mov w0,wzr; mov w1,w21; mov x2,x20; bl 0x406cc134 (result stored by the caller). */
__attribute__((used)) u32 precapture_write_file(u32 op,u32 mode,u64 J) {
    job_t jb;
    if(op==0 && mode==0 && dual_second(J,&jb)) return second(&jb,J);    /* HN7R */
    if(op!=0 || !eligible(J,mode,&jb)) return ORIG_WRITE(op,mode,J);
    return take(&jb,J);
}
