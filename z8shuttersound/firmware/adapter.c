/* SPDX-License-Identifier: GPL-3.0-or-later
 * Derived from s3lemming/z9-firmware-patch, commit 88a6f3e5195d7f38792dc8eddeb1526fde4096dc.
 * Z8 C3.11 adaptation: native interfaces, event IDs, state addresses and labels.
 * Device-qualified: the full feature set passed complete on-camera verification.
 */
/* v13 Cxx: native C15 first50ms, other Cxx first40ms; original stop then finite remainder. Native imported PCM allocations are retained for the
 * entire guest lifetime. Upper callback registrations are reusable only after
 * the original final-notification consumer returns with both outputs idle.
 * That registration retirement does not grant a PCM/DMA reclamation fence.
 * Original SOD consumer owns stop/wait/restart; no native worker replacement.
 */
#include <stdint.h>
#include <stddef.h>
#define FN(a,t) ((t)(uintptr_t)(a))
#define P ((struct state *)(uintptr_t)0xa04b89000ULL)
#define BYTES 288000u
#define SLOTS 64u
#define NATIVE_U8(a) (*(volatile uint8_t *)(uintptr_t)(a))
#define NATIVE_U32(a) (*(volatile uint32_t *)(uintptr_t)(a))
/* Custom PCM is published only after native card read, RIFF validation and close. */
typedef void (*notice_fn)(uint32_t,const void *);
extern const notice_fn callback_slots[SLOTS];
struct slot { uint32_t kind,accepted,completed,error,bootstrap; };
struct state {
 uint32_t magic,route,active,armed,kind,inputs,phase,tail;
 uint32_t busy,accepts,completes,errors,pcm_hooks,last_flags,result,stops;
 void *allocation;uint8_t *pcm;notice_fn notice;
 uint32_t current,used,api_replies,api_failures,rejects,stale,duplicates,reserved;
 struct slot slots[SLOTS];
 uint32_t cxx_pending,cxx_enabled,cxx_epoch,cxx_frames,cxx_submits,cxx_dropped,cxx_boots,cxx_stops;
 uint32_t cxx_bad_native,cxx_duplicates,cxx_pcm,last_sequence;
 uintptr_t last_metadata;
 uint8_t *silence;
 uint32_t cxx_waiting,cxx_wakes,cxx_natural_retire;
 uint32_t selected,pcm_bytes,selected_file;
 uint32_t cxx_release,cxx_tail_pending,cxx_tail_active,cxx_loop_bytes,cxx_tail_bytes,cxx_tail_requests;
};
void m2_composite(void);
static void cxx_tail_request(void);
extern void m2_restore_for_audio(void);
_Static_assert(sizeof(struct state)<=1536,"adapter must end before v09 picker at A04E3D600");
void m2_notice_slot(uint32_t slot,uint32_t code,const void *data) {
 struct state *p=P;
 if(slot>=p->used || !data || (code!=0x4102004u && code!=0x4102005u))return;
 const uint32_t *w=data;struct slot *s=&p->slots[slot];
 if(w[0]!=s->kind){p->errors++;return;}
 if(code==0x4102004u) {
  if(s->accepted){p->duplicates++;return;}
  s->accepted=1;s->error=w[1];p->accepts++;
  if(w[1]){p->rejects++;if(p->current==slot+1){p->active=p->armed=0;p->cxx_enabled=p->cxx_tail_pending=p->cxx_tail_active=0;p->route=0;}}
 } else {
  if(s->completed){p->duplicates++;return;}
  s->completed=1;s->error|=w[1];p->completes++;
  if(p->current==slot+1)p->active=p->armed=0;else {p->stale++;return;}
 }
 /* Preserve each original camera notification once. No token is claimed in
  * its payload; identity comes from the immutable callback registration. */
 if(p->notice)p->notice(code,data);
 if(code==0x4102005u && p->current==slot+1){
  if(s->bootstrap){
   if(p->cxx_release && !w[1] && !NATIVE_U8(0xa03bc7009ULL) && !NATIVE_U32(0xa03bc7010ULL)){
    if(p->cxx_tail_bytes){p->cxx_tail_pending=1;cxx_tail_request();}
    else p->cxx_enabled=0;
   }else{p->cxx_enabled=0;p->cxx_tail_pending=0;if(!p->cxx_release)p->errors++;}
  }else if(p->cxx_tail_active){p->cxx_tail_active=0;p->cxx_enabled=0;}
 }

}
/* Runs at original final-notification return sites 40E395B0/40E39728,
 * after the original callback invocation (40E395AC/40E39724). Upper request
 * state and both output pending states must be zero. Only callbacks already
 * completed in that serialized native worker can retire. No PCM is freed. */
void m2_notice_retired(void){
 if(NATIVE_U32(0xa038feb74ULL) || NATIVE_U32(0xa038feb78ULL) || NATIVE_U32(0xa038febb4ULL))return;
 struct state *p=P;
 for(uint32_t i=0;i<p->used;i++)if(p->slots[i].completed==1)
  __atomic_store_n(&p->slots[i].completed,2,__ATOMIC_RELEASE);
}
uint32_t m2_api(uint64_t *args) {
 struct state *p=P;uint64_t caller=args[8];
 if(args[3]==0x40f9d194u && !p->selected)m2_restore_for_audio();
 if(p->selected && !p->used && !p->cxx_enabled && ((caller==0x40e314a8u && args[0]==6)||(caller==0x40e31514u && args[0]==0)))p->cxx_pending=1;

 if(args[3]!=0x40f9d194u || !p->selected || !p->pcm || !p->pcm_bytes)return 0;
 uint32_t bootstrap=p->cxx_pending && args[1]==0 &&
  ((caller==0x40e314a8u && args[0]==6) || (caller==0x40e31514u && args[0]==0));
 if(bootstrap && NATIVE_U8(0xa03bc7009ULL)>1) {
  p->cxx_bad_native++;p->cxx_pending=0;return 0;
 }
 if(!bootstrap && !((caller==0x40e31308u && args[0]==1 && args[1]==1) ||
      (caller==0x40e314a8u && args[0]==0 && args[1]==0)))return 0;
 p->magic=0x4d325313u;p->route=1;
 if(p->active){p->busy++;p->rejects++;return 1;}
 uint32_t slot;
 if(p->used<SLOTS)slot=p->used++;
 else{
  for(slot=0;slot<SLOTS;slot++)if(__atomic_load_n(&p->slots[slot].completed,__ATOMIC_ACQUIRE)==2)break;
  if(slot==SLOTS){p->rejects++;return 1;}p->reserved++;
 }
 struct slot *s=&p->slots[slot];s->kind=(uint32_t)args[0];s->accepted=s->completed=s->error=s->bootstrap=0;
 p->inputs++;args[10]=p->inputs;
 p->notice=(notice_fn)(uintptr_t)args[3];p->route=1;
 p->slots[slot].bootstrap=bootstrap;
 p->current=slot+1;p->kind=(uint32_t)args[0];p->active=1;p->armed=bootstrap?3:1;
 if(bootstrap){
  p->route=2;p->cxx_pending=0;p->cxx_enabled=1;p->cxx_boots++;p->cxx_release=0;
  p->cxx_tail_pending=p->cxx_tail_active=0;
  uint32_t prefix_limit=caller==0x40e31514u?9600u:7680u;
  p->cxx_loop_bytes=p->pcm_bytes<prefix_limit?p->pcm_bytes:prefix_limit;
  p->cxx_tail_bytes=p->pcm_bytes-p->cxx_loop_bytes;args[1]=0;
  /* Extended C15 uses a cycle budget measured above this PCM hook against
   * the original 50ms resource. Retain its native interval; compensate a
   * shorter custom prefix so output duration plus wait keeps that budget.
   * Other Cxx arrive with zero budget and use a prefix of at most 40ms. */
  if(args[2])args[2]=(uint32_t)args[2]+50u-p->cxx_loop_bytes/192u;
 }else{
  uint32_t bytes=p->pcm_bytes;
  if(p->cxx_tail_pending){p->cxx_tail_pending=0;p->cxx_tail_active=1;bytes=p->cxx_tail_bytes;p->cxx_tail_requests++;}
  args[1]=bytes/4u>65535u?2u:1u;
 }
 args[3]=(uintptr_t)callback_slots[slot];return 0;
}
void m2_api_result(uint64_t *args) {
 struct state *p=P;uint32_t slot;
 for(slot=0;slot<p->used;slot++)if(args[3]==(uintptr_t)callback_slots[slot])break;
 if(slot==p->used || args[10]!=p->inputs)return;
 p->api_replies++;
 if(!(args[9]&1u)) {
  p->api_failures++;p->rejects++;
  if(p->current==slot+1){p->active=p->armed=0;p->cxx_enabled=p->cxx_tail_pending=p->cxx_tail_active=0;p->route=0;}
 }
}
void m2_pcm(uint64_t *args) {
 struct state *p=P;
 if(p->active && p->route==2 && (p->armed==3 || p->armed==4)) {
  if(args[1] && args[2] && args[1]<=9600 && args[2]<=9600/args[1]) {
   args[0]=(uintptr_t)p->pcm;args[2]=1;args[1]=p->cxx_loop_bytes;p->armed=4;p->cxx_pcm++;
  } else p->errors++;
  return;
 }
 if(!p->active || p->armed!=1 || args[1]!=(p->kind?4800u:9600u))return;
 uint32_t bytes=p->cxx_tail_active?p->cxx_tail_bytes:p->pcm_bytes;
 p->armed=2;args[0]=(uintptr_t)(p->pcm+(p->cxx_tail_active?p->cxx_loop_bytes:0));args[2]=bytes/4u>65535u?2u:1u;args[1]=bytes/args[2];p->pcm_hooks++;
}
uint32_t m2_flags(uint32_t flags) {
 struct state *p=P;p->last_flags=flags;
 if(flags&~7u)return 0;
 if(flags&1u)p->stops++;
 if(flags&2u){
  if(p->route==2 && p->active){
   p->cxx_waiting=1;FN(0x40f9d09c,void(*)(void))();return 1;
  }
  p->route=0;return 0;
 }
 if(p->route && (flags&4u)) {
  /* Combined stop+phase must retain explicit native stop, without kind2. */
  if(flags&1u)FN(0x40f9d09c,void(*)(void))();
  p->phase++;return 1;
 }
 return 0;
}
uint32_t m2_terminal(uintptr_t caller){
 if(caller==0x40f80eb0u){m2_composite();return 0;}
 if(P->route){P->tail++;return 1;}return 0;
}
uint32_t m2_fast_timer(uintptr_t timer) {
 if(timer==0xa03bc6fc0ULL && P->route && P->kind==0 && P->active){P->result++;return 1;}
 return 0;
}
void m2_composite(void) {
 struct state *p=P;
 p->route=0;p->cxx_pending=p->selected;p->cxx_enabled=0;p->cxx_epoch++;
 p->last_metadata=0;p->last_sequence=0;
}
void m2_cxx_stop(void) {
 struct state *p=P;
 if(p->cxx_enabled && !p->cxx_release){p->cxx_release=1;p->cxx_stops++;}
 /* The displaced original 40FA0198 body owns the stop and ending state. */
}
static void cxx_tail_request(void){
 struct { uint32_t control0,control1;uint64_t control2,timestamp; } request={192,1536,1,0};
 FN(0x40c7c778,void(*)(uint64_t *))(&request.timestamp);
 FN(0x40f9cccc,void(*)(const void *))(&request);
}
/* Legacy hook symbols remain inert in the build. No downstream frame event
 * may retrigger the loop or tail; the original native loop owns recurrence. */
void m2_frame_snapshot(uint64_t *args){args[10]=args[11]=args[12]=0;}
void m2_frame_commit(uint64_t *args){(void)args;}

int m2_bind_file(uint8_t *pcm,uint32_t bytes,uint32_t file){
 struct state *p=P;
 if(!pcm || !bytes || bytes>BYTES || bytes%192u || p->active || p->armed || p->cxx_enabled || p->cxx_tail_pending)return 1;
 p->pcm=pcm;p->pcm_bytes=bytes;p->selected_file=file;p->route=0;
 __atomic_store_n(&p->selected,1,__ATOMIC_RELEASE);return 0;
}
int m2_native_selection(void){
 struct state *p=P;if(p->active || p->armed || p->cxx_enabled || p->cxx_tail_pending)return 1;
 p->selected=0;p->route=0;p->cxx_pending=0;return 0;
}
uint32_t m2_custom_selected(void){return __atomic_load_n(&P->selected,__ATOMIC_ACQUIRE);}
