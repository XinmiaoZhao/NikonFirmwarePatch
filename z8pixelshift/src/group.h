/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef Z8_PSM_GROUP_H
#define Z8_PSM_GROUP_H
#include "job.h"
/* PS7: time (DateTimeOriginal) comes before wb so that the frames of a group, shot seconds apart, still compare
   equal from wb on (psm_group_config). identity: count, index, group, start, serial and time were read.
   PS12: group = 0x0056's start-file word (slot, folder, file number, type), the same in every frame of a group. */
typedef struct {
    uint32_t group, index, count, start;
    int32_t shift[2];
    uint32_t denominator[2];
    char time[20];
    uint32_t identity;
    uint32_t wb[8];
    uint16_t black[4], crop[4], dimensions[7];
    uint8_t exposure[26], serial[32];
} psm_metadata;

/* PS7 card scan: every DCIM folder and the root of both cards, one table of pixel-shift groups. */
#define PSM_SCAN_FILES 10000u          /* entries per folder (PS6) */
#define PSM_SCAN_DIRS 1000u            /* DCIM folders per card (PS6) */
#define PSM_SCAN_FRAMES 4096u          /* pixel-shift NEFs on both cards */
#define PSM_SCAN_GROUPS 512u
#define PSM_SCAN_MERGED 1024u          /* <stem>_MERGED[_n].NEFX names on both cards */
#define PSM_SCAN_CACHE 4096u
#define PSM_DIR_PATH 24u               /* "B:\DCIM\" + a folder name of at most 12 characters */
#define PSM_NO_FRAME 0xFFFFu

typedef struct { char name[13]; uint8_t attrs; uint16_t dir; uint64_t bytes; } psm_entry;
/* metadata: CRC-32 of the frame's psm_metadata at the scan; the merge reads it again and compares (PS6 compared the
   whole record between its scan and its read pass) */
typedef struct { uint32_t bytes, metadata; uint16_t dir; uint8_t status; char name[13]; } psm_frame_ref;
typedef struct { uint16_t dir; char stem[13]; } psm_merged_ref;
/* A group is one camera's frames of one pixel-shift sequence on one card: (card, serial, start, group id, count).
   PS12: group id = the start-file word (PS3-PS11: its high half). */
typedef struct {
    uint32_t start, group, count, mask;
    uint8_t card;                      /* 'A' or 'B' */
    uint8_t duplicate, merged;
    uint8_t status;                    /* first refusal of a frame of this group, 0 if none */
    char time[20];
    uint8_t serial[32];
    uint16_t frames[32];               /* index into psm_scan.frames per frame (1..count), PSM_NO_FRAME if absent */
} psm_group;
typedef struct {
    uint8_t present;
    uint32_t dirs, nefs, ordinary, candidates, unattributed, other;
    int32_t first_status;              /* first refused candidate whose group is unknown */
    char first_path[48];
    uint64_t ticks;
} psm_card_scan;
typedef struct {
    psm_entry files[PSM_SCAN_FILES], dirs[PSM_SCAN_DIRS];
    char dir_paths[2u * (PSM_SCAN_DIRS + 1u)][PSM_DIR_PATH];
    psm_frame_ref frames[PSM_SCAN_FRAMES];
    psm_group groups[PSM_SCAN_GROUPS];
    psm_merged_ref merged[PSM_SCAN_MERGED];
    uint16_t order[PSM_SCAN_GROUPS];   /* newest first: time, then start, then card A */
    uint32_t ndirs, nframes, ngroups, nmerged, probed;
    psm_card_scan cards[2];
    uint8_t cache[PSM_SCAN_CACHE] __attribute__((aligned(64)));
} psm_scan;

int psm_probe_metadata(const psm_platform *, int, uint32_t, psm_metadata *, void *);
int psm_scan_cards(const psm_platform *, psm_scan *);
int psm_group_mergeable(const psm_group *);
uint32_t psm_targets(const psm_scan *, uint32_t, uint16_t *);
/* Builds the PS2 config of one scanned group from metadata the caller probed from its open frames. */
int psm_group_config(const psm_scan *, const psm_group *, const psm_metadata *, const uint32_t *,
                     uint8_t *, uint32_t *);
int psm_frame_path(const psm_scan *, const psm_group *, uint32_t, char *);
void psm_group_reject(uint32_t, uint32_t, uint32_t, const char *);
/* Snapshot and target identities stay owned by the caller until return. Every
   frame is reopened and compared with the published size/metadata before use. */
int ps8_selected_job(const psm_platform *,const psm_scan *,const uint16_t *,uint32_t,psm_summary *);
#endif
