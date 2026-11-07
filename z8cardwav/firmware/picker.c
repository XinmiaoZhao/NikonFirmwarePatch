/* SPDX-License-Identifier: GPL-3.0-or-later
 * Derived from s3lemming/z9-firmware-patch, commit 88a6f3e5195d7f38792dc8eddeb1526fde4096dc.
 * Z8 C3.11 adaptation: native interfaces, event IDs, state addresses and labels.
 * Experimental; complete native workflow qualification is performed separately.
 */
/* Native 5.32 menu -> directory task -> WAV import -> actual photo adapter.
 * Legacy builds reuse one unpublished scratch buffer; 04.23 uses two staging
 * buffers plus isolated native IO and a reusable pending allocation. At most 20 distinct
 * validated PCM contents are retained, immutable, for the session. Selection
 * rereads the card and compares all bytes; path-only cache hits are forbidden.
 * Published PCM is never overwritten/freed and no audio completion fence is assumed.
 */
#include <stdint.h>
#include <stddef.h>
#include "mark2_import.h"
#include "profile.h"
#define FN(a,t) ((t)(uintptr_t)(a))
#define K ((struct picker *)(uintptr_t)0xa04b89600ULL)
#define HOLDER ((uint8_t *)(uintptr_t)0xa028cb030ULL)
extern int m2_bind_file(uint8_t *,uint32_t,uint32_t);
extern int m2_native_selection(void);
extern uint32_t m2_custom_selected(void);
#define FILE_LIMIT 20u
#ifndef M2_CONFIRM_IMPORT
#define M2_CONFIRM_IMPORT 0
#endif
#ifndef M2_CONFIRM_RETRY
#define M2_CONFIRM_RETRY 0
#endif
#define M2_UNSTABLE 14
#if M2_STAGED_CONFIRM
#define M2_COPY_VERIFY 15
#endif
/* ASCII filename stored once as its native UTF-16 display label.  The mount
 * stays separate; construct the complete import/profile path on the stack. */
struct file {uint16_t label[112];char root;};
struct picker {
 uint32_t magic,calls,active,count,errors[2],overflow,scans;
 uint32_t import_status,selected,imports,attempts,native_selections,busy;
 struct m2_pcm_info info;
 uint32_t label_bytes[FILE_LIMIT];struct file files[FILE_LIMIT];uint8_t rows[6+FILE_LIMIT][44];
 void *retained[4];uint8_t *last_PCM;uint32_t last_bytes,published;char loaded_path[128];uint32_t restore_attempted,restore_status,persist_status,profile_commits;
 uint32_t directory_seen,directory_checks,directory_create_attempts,directory_create_status,directory_errors[2];
 uint8_t *cache_pcm[FILE_LIMIT];uint32_t cache_bytes[FILE_LIMIT];
 uint32_t cache_count,cache_hits,scratch_allocations,cache_allocations,cache_full;
#if M2_CONFIRM_IMPORT
 uint32_t confirm_attempts,confirm_failures,confirm_flushes;
#endif
#if M2_CONFIRM_RETRY
 uint32_t confirm_retries,confirm_mismatches,confirm_stage,confirm_error;
 uint32_t confirm_reason,confirm_diff,confirm_rc_first,confirm_rc_second;
 uint8_t *confirm_first,*confirm_second;
#endif
#if M2_STAGED_CONFIRM
 uint32_t confirm_round,raw_first_hash,raw_second_hash,first_recheck_hash;
 uint32_t copy_before_hash,copy_after_hash,copy_diff;
 uint32_t valid_first,valid_second,play_first,play_second;
 uint16_t diagnostic_label[20];
#endif
};
_Static_assert(sizeof(struct picker)<=6656,"picker fits original +8192 BSS reservation after 1536-byte adapter");
static void file_path(char path[128],const struct file *f){
 const char *prefix=":\\CUSTOM_SOUND\\";path[0]=f->root;
 for(unsigned i=0;i<15;i++)path[i+1]=prefix[i];
 unsigned n=0;do{path[16+n]=(char)f->label[n];}while(f->label[n++]);
}
static int wav(const uint8_t *s,uint32_t n){return n>=5 && s[n-4]=='.' && (s[n-3]|32)=='w' && (s[n-2]|32)=='a' && (s[n-1]|32)=='v';}
/* Native directory enumeration reports END as 80000030, not success=0. */
static int enumeration_ok(uint32_t rc){return !rc || rc==0x80000030u;}
static void directory_path(char *p,char root){
 const char *tail=":\\CUSTOM_SOUND";p[0]=root;unsigned i=0;
 do{p[i+1]=tail[i];}while(tail[i++]);
}
/* Original 5.32 ROM 40866C58 reads UTF-16 at +0x0e first, then
 * falls back to the 13-byte short-name field only if the long name is empty.
 * exFAT's synthesized 8.3 display name need not be an openable alias.
 * Bound the decoded name before writing a label or constructing a path. */
static int entry_name(const uint8_t *entry,uint8_t name[112],uint32_t *length){
 int wide=entry[14]||entry[15];
 for(uint32_t n=0;n<112;n++){
  if(!wide && n>=13)return 0;
  uint32_t c=wide?(uint32_t)entry[14+2*n]|((uint32_t)entry[15+2*n]<<8):entry[n];
  if(!c){name[n]=0;*length=n;return n!=0;}
  if(c<32 || c>126 || c=='/' || c=='\\' || c==':' || c=='*' ||
     c=='?' || c=='"' || c=='<' || c=='>' || c=='|')return 0;
  name[n]=(uint8_t)c;
 }
 return 0;
}
static uint32_t find_directory(const uint8_t *entry){
 const char *wanted="CUSTOM_SOUND";uint8_t name[112];uint32_t n;
 if(!entry_name(entry,name,&n)||n!=12)return 0;
 for(unsigned i=0;i<n;i++)if((name[i]|32)!=(uint8_t)(wanted[i]|32))return 0;
 K->directory_seen|=(entry[0x20e]&0x10)?1u:2u;return 0;
}
static int ensure_directory(char root){
 struct picker *p=K;char base[4]={root,':','\\',0},path[20];
 p->directory_checks++;p->directory_seen=0;directory_path(path,root);
 uint32_t rc=FN(0x402db09c,uint32_t(*)(const char *,uint32_t,uint32_t(*)(const uint8_t *)))(base,0xff,find_directory);
 if(!enumeration_ok(rc) || (p->directory_seen&2u))return 1;
 if(p->directory_seen==1)return 0;
 p->directory_create_attempts++;
 p->directory_create_status=FN(0x402daef0,uint32_t(*)(const char *,uint32_t))(path,0x10);
 /* Recheck native directory entry even on a concurrent already-created error. */
 p->directory_seen=0;
 rc=FN(0x402db09c,uint32_t(*)(const char *,uint32_t,uint32_t(*)(const uint8_t *)))(base,0xff,find_directory);
 return !enumeration_ok(rc) || p->directory_seen!=1;
}
static uint32_t collect(const uint8_t *entry){
 struct picker *p=K;uint8_t name[112];uint32_t n;
 if((entry[0x20e]&0x10)||!entry_name(entry,name,&n)||!wav(name,n))return 0;
 if(p->count==FILE_LIMIT){p->overflow=1;return 0;}
 struct file *f=&p->files[p->count];const char *mount=FN(0x4031bee0,const char *(*)(uint32_t))(p->active-1);
 f->root=mount[0];
 for(uint32_t i=0;i<=n;i++)f->label[i]=name[i];
 p->label_bytes[p->count]=n*2;p->count++;return 0;
}

static int same_path(const char *a,const char *b){for(unsigned i=0;i<128;i++){if(a[i]!=b[i])return 0;if(!a[i])return 1;}return 0;}
static void slot_path(char *p,char root,unsigned slot){const char *tail=slot?":\\CUSTOM_SOUND\\M2SND1.CFG":":\\CUSTOM_SOUND\\M2SND0.CFG";p[0]=root;unsigned i=0;do{p[i+1]=tail[i];}while(tail[i++]);}
static int read_profile(char root,struct m2_profile *selected){
 if(ensure_directory(root))return -1;
 struct m2_profile a={0},b={0};uint8_t body[M2_PROFILE_BYTES];char path[40];
 slot_path(path,root,0);int av=!m2_native_profile_read(path,body)&&!m2_profile_decode(body,sizeof body,&a);
 slot_path(path,root,1);int bv=!m2_native_profile_read(path,body)&&!m2_profile_decode(body,sizeof body,&b);
 int i=m2_profile_newest(&a,av,&b,bv);if(i>=0)*selected=i?b:a;return i;
}
static int save_profile(char root,const char *path,uint32_t enabled){
 if(ensure_directory(root))return 1;
 struct m2_profile old={0};int prior=read_profile(root,&old);if(prior==-2)return 1;
 uint8_t body[M2_PROFILE_BYTES];char target[40];
 if(m2_profile_encode(body,prior>=0?old.sequence+1:1,enabled,path))return 1;
 slot_path(target,root,prior>=0?(unsigned)prior^1u:0);return m2_native_profile_write(target,body);
}
static void disable_profiles(void){
 struct picker *p=K;p->restore_attempted=1;p->persist_status=0;uint32_t was_active=p->active;p->active=3;
 for(unsigned card=0;card<2;card++){
  const char *mount=FN(0x4031bee0,const char *(*)(uint32_t))(card);struct m2_profile old={0};
  if(mount && mount[0]>='A'&&mount[0]<='Z'&&mount[1]==':'&&!mount[2]){
   int prior=read_profile(mount[0],&old);
   if((prior>=0&&old.enabled)||(prior<0&&p->published&&p->loaded_path[0]==mount[0]))
    p->persist_status|=save_profile(mount[0],0,0);
  }
 }
 p->active=was_active;
}
/* Scratch is never sent to the audio worker. Every published cache entry is
 * immutable until power-off; hits require equal padded PCM length and bytes.
 * Repeated choices/invalid files consume no extra retained buffers. */
static void *allocate_pcm(uint32_t bytes){
 uint32_t pool=FN(0x40d2c544,uint32_t(*)(uint32_t))(0)>=bytes?0:1;
 if(FN(0x40d2c544,uint32_t(*)(uint32_t))(pool)<bytes)return 0;
 return FN(0x40d2c408,void *(*)(uint32_t,uint32_t))(bytes,pool);
}
#if !M2_STAGED_CONFIRM
static int import_cached(const char *path,struct m2_pcm_info *info,uint8_t **out){
 struct picker *p=K;p->attempts++;p->cache_full=0;
 if(!p->retained[0]){
  p->retained[0]=allocate_pcm(M2_PCM_MAX+63);
  if(!p->retained[0]){p->cache_full=1;return M2_LIMIT;}
  p->scratch_allocations++;
 }
 uint8_t *scratch=(uint8_t *)(((uintptr_t)p->retained[0]+63u)&~(uintptr_t)63u);
 int rc=m2_native_import(path,scratch,M2_PCM_MAX,info);if(rc)return rc;
 for(uint32_t i=0;i<p->cache_count;i++){
  if(p->cache_bytes[i]!=info->play_bytes)continue;
  uint32_t j=0;while(j<info->play_bytes && p->cache_pcm[i][j]==scratch[j])j++;
  if(j==info->play_bytes){*out=p->cache_pcm[i];p->cache_hits++;return 0;}
 }
 if(p->cache_count==FILE_LIMIT){p->cache_full=1;return M2_LIMIT;}
 void *allocation=allocate_pcm(info->play_bytes+63);if(!allocation){p->cache_full=1;return M2_LIMIT;}
 uint8_t *pcm=(uint8_t *)(((uintptr_t)allocation+63u)&~(uintptr_t)63u);
 for(uint32_t i=0;i<info->play_bytes;i++)pcm[i]=scratch[i];
 FN(0x40d2b9e4,uint32_t(*)(void *,int32_t,int32_t))(pcm,(int32_t)info->play_bytes,0);
 uint32_t i=p->cache_count++;p->cache_pcm[i]=pcm;p->cache_bytes[i]=info->play_bytes;
 p->cache_allocations++;*out=pcm;return 0;
}
#endif
/* 04.21 candidate: reproduce the second content-cache read before publishing.
 * Both complete imports must agree; no audio API or duplicate GUI submit runs.
 * Reading the cleaned PCM back and cleaning it again is a cache/timing probe,
 * not proof that the first-selection noise is fixed on hardware. */
#if M2_CONFIRM_IMPORT
/* One bounded retry of the complete pair, only after a consistency mismatch.
 * A failed read is not reclassified as a match. Neither pair publishes audio.
 * Preserve mismatch diagnostics even when the fresh pair succeeds. */
#if M2_STAGED_CONFIRM
/* 04.23: native IO owns its cache lines; two CPU-owned staging buffers are
 * compared before either can enter the immutable audio cache. A rejected
 * import never consumes a permanent cache slot. */
static uint8_t *stage_buffer(unsigned slot,uint32_t bytes){
 struct picker *p=K;
 if(!p->retained[slot]){
  p->retained[slot]=allocate_pcm(bytes+63u);
  if(!p->retained[slot]){p->cache_full=1;return 0;}
  if(slot<2)p->scratch_allocations++;
 }
 return (uint8_t *)(((uintptr_t)p->retained[slot]+63u)&~(uintptr_t)63u);
}
static uint32_t pcm_hash(const uint8_t *pcm,uint32_t bytes){
 /* Diagnostic only: positive confirmation always compares every PCM byte. */
 const volatile uint8_t *p=pcm;uint32_t h=2166136261u;
 for(uint32_t i=0;i<bytes;i++)h=(h^p[i])*16777619u;
 return h;
}
static uint32_t first_difference(const uint8_t *a,const uint8_t *b,uint32_t n){
 for(uint32_t i=0;i<n;i++)if(a[i]!=b[i])return i;
 return UINT32_MAX;
}
static int read_staged(const char *path,uint8_t *pcm,struct m2_pcm_info *info){
 struct picker *p=K;uint8_t *io=stage_buffer(2,M2_IO_BUFFER_BYTES);
 if(!io)return M2_LIMIT;
 p->attempts++;
 return m2_native_import_buffered(path,pcm,M2_PCM_MAX,info,io,M2_IO_BUFFER_BYTES);
}
static int prepare_confirmed(const uint8_t *source,const struct m2_pcm_info *info,uint8_t **out){
 struct picker *p=K;
 for(uint32_t i=0;i<p->cache_count;i++){
  if(p->cache_bytes[i]==info->play_bytes &&
     first_difference(p->cache_pcm[i],source,info->play_bytes)==UINT32_MAX){
   p->cache_hits++;*out=p->cache_pcm[i];return 0;
  }
 }
 if(p->cache_count==FILE_LIMIT){p->cache_full=1;return M2_LIMIT;}
 uint8_t *pcm=stage_buffer(3,M2_PCM_MAX);if(!pcm)return M2_LIMIT;
 for(uint32_t i=0;i<info->play_bytes;i++)pcm[i]=source[i];
 p->copy_before_hash=pcm_hash(pcm,info->play_bytes);
 p->copy_diff=first_difference(pcm,source,info->play_bytes);
 if(p->copy_diff!=UINT32_MAX || p->copy_before_hash!=p->raw_first_hash)return M2_COPY_VERIFY;
 FN(0x40d2b9e4,uint32_t(*)(void *,int32_t,int32_t))(pcm,(int32_t)info->play_bytes,0);
 p->confirm_flushes++;
 p->copy_after_hash=pcm_hash(pcm,info->play_bytes);
 p->copy_diff=first_difference(pcm,source,info->play_bytes);
 if(p->copy_diff!=UINT32_MAX || p->copy_after_hash!=p->raw_first_hash)return M2_COPY_VERIFY;
 *out=pcm;return 0;
}
static void commit_confirmed(uint8_t *pcm,uint32_t bytes){
 struct picker *p=K;
 /* m2_bind_file's failure path has not published the pending allocation.
  * Transfer its ownership only after a successful bind. Never reuse it again. */
 if(p->retained[3] && pcm==(uint8_t *)(((uintptr_t)p->retained[3]+63u)&~(uintptr_t)63u)){
  uint32_t i=p->cache_count++;p->cache_pcm[i]=pcm;p->cache_bytes[i]=bytes;
  p->cache_allocations++;p->retained[3]=0;
 }
}
static int import_confirmed(const char *path,struct m2_pcm_info *info,uint8_t **out){
 struct picker *p=K;p->cache_full=0;p->confirm_error=0;p->confirm_stage=0;*out=0;
 p->confirm_rc_first=p->confirm_rc_second=0;
 uint8_t *first=stage_buffer(0,M2_PCM_MAX),*second=stage_buffer(1,M2_PCM_MAX);
 if(!first || !second){p->confirm_error=M2_LIMIT;return M2_LIMIT;}
 p->confirm_first=first;p->confirm_second=second;
 for(unsigned round=0;round<2;round++){
  struct m2_pcm_info check={0};p->confirm_round=round+1;p->confirm_stage=1;
  int rc=read_staged(path,first,info);p->confirm_rc_first=(uint32_t)rc;
  if(rc){p->confirm_error=(uint32_t)rc;return rc;}
  p->raw_first_hash=pcm_hash(first,info->play_bytes);
  p->confirm_attempts++;p->confirm_stage=2;
  rc=read_staged(path,second,&check);p->confirm_rc_second=(uint32_t)rc;
  if(rc){p->confirm_failures++;p->confirm_error=(uint32_t)rc;return rc;}
  p->raw_second_hash=pcm_hash(second,check.play_bytes);
  p->first_recheck_hash=pcm_hash(first,info->play_bytes);
  p->valid_first=info->valid_bytes;p->valid_second=check.valid_bytes;
  p->play_first=info->play_bytes;p->play_second=check.play_bytes;
  uint32_t n=info->play_bytes<check.play_bytes?info->play_bytes:check.play_bytes;
  uint32_t diff=first_difference(first,second,n);
  uint32_t reason=(diff!=UINT32_MAX?1u:0u)|(info->valid_bytes!=check.valid_bytes?2u:0u)|
   (info->play_bytes!=check.play_bytes?4u:0u)|(info->frames!=check.frames?8u:0u)|
   (info->rate!=check.rate?16u:0u)|(info->channels!=check.channels?32u:0u)|
   (info->bits!=check.bits?64u:0u)|(p->raw_first_hash!=p->first_recheck_hash?128u:0u);
  if(!reason){
   p->confirm_stage=4;rc=prepare_confirmed(first,info,out);p->confirm_error=(uint32_t)rc;
   if(!rc)p->confirm_stage=5;
   return rc;
  }
  p->confirm_failures++;p->confirm_mismatches++;p->confirm_stage=3;
  p->confirm_reason=reason;p->confirm_diff=diff;
  if(round==0){p->confirm_retries++;continue;}
  p->confirm_error=M2_UNSTABLE;return M2_UNSTABLE;
 }
 return M2_UNSTABLE;
}
#elif M2_CONFIRM_RETRY
static int import_confirmed(const char *path,struct m2_pcm_info *info,uint8_t **out){
 struct picker *p=K;p->confirm_error=0;p->confirm_stage=0;
 p->confirm_rc_first=p->confirm_rc_second=0;
 for(unsigned round=0;round<2;round++){
  uint8_t *first=0,*second=0;struct m2_pcm_info check={0};
  p->confirm_stage=1;
  int rc=import_cached(path,info,&first);p->confirm_rc_first=(uint32_t)rc;
  if(rc){p->confirm_error=(uint32_t)rc;return rc;}
  p->confirm_attempts++;p->confirm_stage=2;
  rc=import_cached(path,&check,&second);p->confirm_rc_second=(uint32_t)rc;
  if(rc){p->confirm_failures++;p->confirm_error=(uint32_t)rc;return rc;}
  uint32_t reason=(first!=second?1u:0u)|(info->valid_bytes!=check.valid_bytes?2u:0u)|
   (info->play_bytes!=check.play_bytes?4u:0u)|(info->frames!=check.frames?8u:0u)|
   (info->rate!=check.rate?16u:0u)|(info->channels!=check.channels?32u:0u)|
   (info->bits!=check.bits?64u:0u);
  if(!reason){
   FN(0x40d2b9e4,uint32_t(*)(void *,int32_t,int32_t))(first,(int32_t)info->play_bytes,0);
   p->confirm_flushes++;p->confirm_stage=5;*out=first;return 0;
  }
  p->confirm_failures++;p->confirm_mismatches++;p->confirm_stage=3;
  p->confirm_reason=reason;p->confirm_first=first;p->confirm_second=second;
  p->confirm_diff=UINT32_MAX;
  uint32_t n=info->play_bytes<check.play_bytes?info->play_bytes:check.play_bytes;
  for(uint32_t i=0;i<n;i++)if(first[i]!=second[i]){p->confirm_diff=i;break;}
  if(round==0){p->confirm_retries++;continue;}
  p->confirm_error=M2_UNSTABLE;return M2_UNSTABLE;
 }
 return M2_UNSTABLE;
}
#else
static int import_confirmed(const char *path,struct m2_pcm_info *info,uint8_t **out){
 struct picker *p=K;uint8_t *first=0,*second=0;struct m2_pcm_info check={0};
 int rc=import_cached(path,info,&first);if(rc)return rc;
 p->confirm_attempts++;
 rc=import_cached(path,&check,&second);
 if(!rc && (first!=second || info->valid_bytes!=check.valid_bytes ||
    info->play_bytes!=check.play_bytes || info->frames!=check.frames ||
    info->rate!=check.rate || info->channels!=check.channels || info->bits!=check.bits))rc=M2_IO;
 if(rc){p->confirm_failures++;return rc;}
 FN(0x40d2b9e4,uint32_t(*)(void *,int32_t,int32_t))(first,(int32_t)info->play_bytes,0);
 p->confirm_flushes++;*out=first;return 0;
}
#endif
#else
#define import_confirmed import_cached
#endif
void m2_restore_for_audio(void){
 struct picker *p=K;if(p->restore_attempted || p->active)return;p->restore_attempted=1;
 /* Only the original Type A mapping may own the persisted custom route. */
 if(FN(0x403ec398,uint32_t(*)(uint32_t))(0x2006101)!=0){p->restore_status=1;return;}
 p->magic=0x4d325049u;p->active=3;struct m2_profile choice={0};unsigned found=0;
 for(unsigned card=0;card<2;card++){
  const char *mount=FN(0x4031bee0,const char *(*)(uint32_t))(card);struct m2_profile f={0};
  if(mount && mount[0]>='A'&&mount[0]<='Z'&&mount[1]==':'&&!mount[2]&&read_profile(mount[0],&f)>=0&&f.enabled&&f.path[0]==mount[0]){choice=f;found++;}
 }
 if(found!=1){p->restore_status=found?3:2;p->active=0;return;}
 uint8_t *pcm=0;struct m2_pcm_info info={0};
 int rc=import_confirmed(choice.path,&info,&pcm);
 if(!rc)rc=m2_bind_file(pcm,info.play_bytes,UINT32_MAX);
#if M2_STAGED_CONFIRM
 if(!rc)commit_confirmed(pcm,info.play_bytes);
#endif
 p->restore_status=rc?5:0;
 if(!rc){p->info=info;p->last_PCM=pcm;p->last_bytes=info.play_bytes;p->imports++;p->published=1;for(unsigned i=0;i<128;i++)p->loaded_path[i]=choice.path[i];}
 p->active=0;
}
static void publish_rows(void){
 struct picker *p=K;const uint8_t *builtin=(const uint8_t *)(uintptr_t)0x43d64d94;
 for(uint32_t i=0;i<5*44;i++)((uint8_t *)p->rows)[i]=builtin[i];
 for(uint32_t r=5;r<6+p->count;r++){
  for(uint32_t i=0;i<44;i++)p->rows[r][i]=builtin[4*44+i];
  *(uint16_t *)p->rows[r]=(uint16_t)(r==5?0xc54:0xc55+r-6);
  *(uint32_t *)(p->rows[r]+24)=r==5?0x7e20:0x7e21+r-6;
 }
 *(uint8_t **)(HOLDER+0x10)=(uint8_t *)p->rows;*(uint16_t *)(HOLDER+0x20)=(uint16_t)(6+p->count);
}
void mark2_discovery_submit(void **outer){
 if(!outer || !*outer)return;
 const uint8_t *ctx=*outer;const uint8_t *holder=*(const uint8_t *const *)(ctx+0x50);
 uint32_t index=*(const uint16_t *)(ctx+0x32)+*(const uint16_t *)(ctx+0x58);
 if(holder!=HOLDER || index>=*(const uint16_t *)(holder+0x20))return;
 const uint8_t *rows=*(const uint8_t *const *)(holder+0x10);uint32_t id=*(const uint32_t *)(rows+index*44+24);
 struct picker *p=K;if((p->magic && p->magic!=0x4d325049u)||p->active)return;
 p->magic=0x4d325049u;p->calls++;
 if(id<0x7e20 || id>=0x7e21+FILE_LIMIT){
  if(m2_native_selection()){p->busy++;return;}
  disable_profiles();p->native_selections++;FN(0x405a5878,void(*)(void **))(outer);return;
 }
 if(id==0x7e20){
  p->count=0;p->overflow=0;p->scans++;p->import_status=0;
  for(uint32_t storage=0;storage<2;storage++){
   const char *mount=FN(0x4031bee0,const char *(*)(uint32_t))(storage);char path[20];
   if(!mount || mount[0]<'A' || mount[0]>'Z' || mount[1]!=':' || mount[2]){p->errors[storage]=0xffffffffu;continue;}
   p->active=storage+1;p->directory_errors[storage]=ensure_directory(mount[0]);
   if(p->directory_errors[storage]){p->errors[storage]=0xffffffffu;continue;}
   directory_path(path,mount[0]);
   p->errors[storage]=FN(0x402db09c,uint32_t(*)(const char *,uint32_t,uint32_t(*)(const uint8_t *)))(path,0xef,collect);
  }
  p->active=0;publish_rows();return;
 }
 uint32_t file=id-0x7e21;if(file>=p->count)return;
 p->active=3;uint8_t *pcm=0;struct m2_pcm_info info={0};
 char path[128];file_path(path,&p->files[file]);
 p->import_status=import_confirmed(path,&info,&pcm);
 if(!p->import_status){
  if(m2_bind_file(pcm,info.play_bytes,file)){p->import_status=M2_BUSY;p->busy++;}
  else{
#if M2_STAGED_CONFIRM
   commit_confirmed(pcm,info.play_bytes);
#endif
   p->restore_attempted=1;for(unsigned i=0;i<128;i++){p->loaded_path[i]=path[i];if(!path[i])break;}
   p->persist_status=save_profile(p->loaded_path[0],p->loaded_path,1);
   /* Commit the newly selected card first. Only then disable an older enabled
    * profile on the other mounted card, so a failed new save cannot erase the
    * last persisted selection. A failed secondary write remains visible. */
   if(!p->persist_status)for(unsigned card=0;card<2;card++){
    const char *mount=FN(0x4031bee0,const char *(*)(uint32_t))(card);struct m2_profile old={0};
    if(mount && mount[0]>='A' && mount[0]<='Z' && mount[0]!=p->loaded_path[0] && mount[1]==':' && !mount[2] &&
       read_profile(mount[0],&old)>=0 && old.enabled)p->persist_status|=save_profile(mount[0],0,0);
   }
   if(!p->persist_status)p->profile_commits++;
   p->info=info;p->selected=file;p->last_PCM=pcm;p->last_bytes=info.play_bytes;p->imports++;p->published=1;
   /* Recovered original handler maps extra UI values to native Type A=0;
    * no unknown DSID value is introduced. Original dispatch/notifications run. */
   FN(0x405a5878,void(*)(void **))(outer);
  }
 }
 p->active=0;
}
void mark2_sound_refresh(void *ctx){
 FN(0x405a57f4,void(*)(void *))(ctx);
 if(m2_custom_selected())for(unsigned i=0;i<K->count;i++){
  char path[128];file_path(path,&K->files[i]);
  if(same_path(K->loaded_path,path))FN(0x403b00b8,void(*)(void *,uint32_t,uint32_t))(ctx,0x7e21+i,1);
 }
}
/* Hook only the Camera sounds -> Type value consumer (405A5584).  The
 * native DSID enum and the five built-in Type submenu names stay intact. */
void mark2_outer_type_text(const char *text,uint32_t slot,uint32_t label){
 if(m2_custom_selected() && text==(const char *)(uintptr_t)0x42b2f692)text="CUS";
 FN(0x403f2920,void(*)(const char *,uint32_t,uint32_t))(text,slot,label);
}
void mark2_picker_label(uint32_t language,uint32_t label,const uint16_t **out,uint32_t *bytes){
 if(label==0xc54){
  static const uint16_t scan[]={'L','o','a','d',' ','W','A','V',' ','f','r','o','m',' ','c','a','r','d'};
  static const uint16_t fail[]={'S','a','v','e',' ','f','a','i','l','e','d',' ','-',' ','c','h','e','c','k',' ','c','a','r','d'};
  if(language>=36){*out=0;*bytes=0;return;}
  static const uint16_t loadfail[]={'L','o','a','d',' ','f','a','i','l','e','d',' ','-',' ','c','h','e','c','k',' ','W','A','V'};
  static const uint16_t full[]={'C','a','c','h','e',' ','f','u','l','l',' ','-',' ','r','e','s','t','a','r','t'};
  static const uint16_t busy[]={'A','u','d','i','o',' ','b','u','s','y',' ','-',' ','r','e','t','r','y'};
#if M2_CONFIRM_RETRY
#if M2_STAGED_CONFIRM
  static const uint16_t copyfail[]={'W','A','V',' ','c','o','p','y',' ','d','i','f','f',' ','-',' ','r','e','t','r','y'};
  if(K->import_status==M2_COPY_VERIFY){*out=copyfail;*bytes=sizeof copyfail;return;}
  if(K->import_status==M2_UNSTABLE){
   const char *prefix="WAV diff ",*hex="0123456789ABCDEF";
   for(unsigned i=0;i<9;i++)K->diagnostic_label[i]=(uint8_t)prefix[i];
   K->diagnostic_label[9]=hex[(K->confirm_reason>>4)&15u];
   K->diagnostic_label[10]=hex[K->confirm_reason&15u];
   K->diagnostic_label[11]=' ';K->diagnostic_label[12]='@';
   for(unsigned i=0;i<6;i++)K->diagnostic_label[13+i]=K->confirm_diff==UINT32_MAX?'-':hex[(K->confirm_diff>>(20-4*i))&15u];
   *out=K->diagnostic_label;*bytes=19u*2u;return;
  }
#else
  static const uint16_t mismatch[]={'W','A','V',' ','m','i','s','m','a','t','c','h',' ','-',' ','r','e','t','r','y'};
#endif
  static const uint16_t readfail[]={'W','A','V',' ','r','e','a','d',' ','f','a','i','l','e','d',' ','-',' ','r','e','t','r','y'};
#if !M2_STAGED_CONFIRM
  if(K->import_status==M2_UNSTABLE){*out=mismatch;*bytes=sizeof mismatch;return;}
#endif
  if(K->import_status && (K->confirm_stage==1 || K->confirm_stage==2) &&
     (K->import_status==M2_OPEN || K->import_status==M2_SIZE || K->import_status==M2_IO ||
      K->import_status==M2_EOF || K->import_status==M2_CLOSE)){
   *out=readfail;*bytes=sizeof readfail;return;
  }
#endif
  if(K->import_status){
   if(K->cache_full){*out=full;*bytes=sizeof full;}
   else if(K->import_status==M2_BUSY){*out=busy;*bytes=sizeof busy;}
   else{*out=loadfail;*bytes=sizeof loadfail;}
  }else{*out=K->persist_status?fail:scan;*bytes=K->persist_status?sizeof fail:sizeof scan;}return;
 }
 uint32_t i=label-0xc55;
 if(language<36 && i<K->count){*out=K->files[i].label;*bytes=K->label_bytes[i];}
 else{*out=0;*bytes=0;}
}
