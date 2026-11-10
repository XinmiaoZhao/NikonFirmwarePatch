"""Bounded ARM integration tests for the exact port payload, NOT full QEMU/RTOS."""
from pathlib import Path
import json,struct,re,hashlib,sys
from unicorn import *
from unicorn.arm64_const import *
C=Path(sys.argv[1])
PAYLOAD=(C/'payload.bin').read_bytes();BASE=0x40160000;P=0xa04b89000;K=P+1536;HOLDER=0xa028cb030;RAM=0x60000000;HEAP=0x61000000;STOP=0x70000000
SYMS={v[2]:int(v[0],16)for l in(C/'symbols.txt').read_text().splitlines()if len(v:=l.split())==3}
LAY={};cur=None
for l in(C/'record-layouts.txt').read_text().splitlines():
 m=re.match(r'\s*0 \| struct (state|picker)$',l)
 if m:cur=m[1];LAY[cur]={};continue
 if cur and '[sizeof='in l:cur=None
 if cur:
  m=re.match(r'\s*(\d+) \|   (?!  ).*\b(\w+)$',l)
  if m:LAY[cur][m[2]]=int(m[1])
def wav(n=192,seed=1,rate=48000):
 pcm=bytes((i+seed)%256 for i in range(n));body=b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,2,rate,rate*4,4,16)+b'data'+struct.pack('<I',n)+pcm
 return b'RIFF'+struct.pack('<I',len(body))+body,pcm
STAGED='raw_first_hash' in LAY['picker']
class Lab:
 def __init__(self,files=None,dirs=None,present=(True,True)):
  self.u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u=self.u
  u.mem_map(BASE,(len(PAYLOAD)+4095)&~4095);u.mem_write(BASE,PAYLOAD)
  u.mem_map(0xa02808000,0x2ad000);u.mem_write(0xa02808000,PAYLOAD[0x4b13000:0x4b13000+0x2ad000])
  u.mem_map(P,0x3000);u.mem_write(P+8192,bytes([0xA5])*32)
  u.mem_map(0xa038fe000,4096);u.mem_map(0xa03bc6000,8192)
  u.mem_map(RAM,0x200000);u.mem_map(HEAP,0x1000000);u.mem_map(STOP,4096)
  u.reg_write(UC_ARM64_REG_CPACR_EL1,3<<20)
  self.files=dict(files or {});self.dirs=set(dirs or []);self.present=list(present);self.fds={};self.nextfd=100;self.heap=HEAP
  self.ds=0;self.calls=[];self.enum_stack=[];self.return_address=STOP;self.read_fail=False;self.write_fail=False;self.alloc_fail=False;self.fail_api=False
  self.events=[];self.import_calls=0;self.before_import=None
  if STAGED:self.instruction_limit=80000000
  self.notifications=[];self.pcm_requests=[];self.api_requests=[];self.tail_requests=0;self.native_stops=0;self.draw=[]
  u.mem_write(RAM+0x100,b'A:\0B:\0');u.hook_add(UC_HOOK_CODE,self.hook)
 def r32(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def r64(self,a):return struct.unpack('<Q',self.u.mem_read(a,8))[0]
 def w32(self,a,n):self.u.mem_write(a,struct.pack('<I',n&0xffffffff))
 def w64(self,a,n):self.u.mem_write(a,struct.pack('<Q',n))
 def field(self,n,picker=False):return self.r32((K if picker else P)+LAY['picker'if picker else'state'][n])
 def pointer(self,n,picker=False):return self.r64((K if picker else P)+LAY['picker'if picker else'state'][n])
 def cstr(self,a):return bytes(self.u.mem_read(a,256)).split(b'\0',1)[0].decode('ascii')
 def ret(self,value=0):self.u.reg_write(UC_ARM64_REG_X0,value&0xffffffffffffffff);self.u.reg_write(UC_ARM64_REG_PC,self.u.reg_read(UC_ARM64_REG_LR))
 def call(self,fn,*args,lr=STOP):
  u=self.u;self.return_address=lr
  u.reg_write(UC_ARM64_REG_SP,RAM+0x1f0000);u.reg_write(UC_ARM64_REG_LR,lr)
  for i,v in enumerate(args):u.reg_write(UC_ARM64_REG_X0+i,v)
  u.emu_start(SYMS[fn]if isinstance(fn,str)else fn,0,count=getattr(self,'instruction_limit',5000000))
  assert u.reg_read(UC_ARM64_REG_PC)==lr,('did not return',fn,hex(u.reg_read(UC_ARM64_REG_PC)))
  assert bytes(u.mem_read(P+8192,32))==bytes([0xA5])*32,'BSS overrun'
  return u.reg_read(UC_ARM64_REG_X0)&0xffffffff
 def enumerate_next(self):
  s=self.enum_stack[-1]
  if s['entries']:
   name,folder=s['entries'].pop(0);entry=RAM+0xb0000+len(self.enum_stack)*0x1000
   b=bytearray(0x220);enc=name.encode('utf-16le');b[14:14+len(enc)]=enc;b[0x20e]=0x10 if folder else 0
   self.u.mem_write(entry,bytes(b));self.u.reg_write(UC_ARM64_REG_X0,entry);self.u.reg_write(UC_ARM64_REG_LR,STOP+0x100);self.u.reg_write(UC_ARM64_REG_PC,s['callback'])
  else:
   self.enum_stack.pop();self.u.reg_write(UC_ARM64_REG_LR,s['lr']);self.ret(0x80000030)
 def hook(self,u,a,size,user):
  if a==self.return_address:u.emu_stop();return
  if a==STOP+0x100:self.enumerate_next();return
  if a==SYMS['m2_native_import_buffered' if STAGED else 'm2_native_import']:
   self.import_calls+=1;self.events.append(('import',self.import_calls))
   if self.before_import:self.before_import(self)
  if a==SYMS['m2_bind_file']:self.events.append(('bind',u.reg_read(UC_ARM64_REG_X0)))
  if a not in {0x4031bee0,0x402db09c,0x402daef0,0x40d2c544,0x40d2c408,0x40d2b9e4,0x40863770,0x408637b0,0x40863610,0x402dab4c,0x402dabb8,0x402daaac,0x403ec398,0x403ec39c,0x403ae0f8,0x403b00b8,0x403b0048,0x403f2920,0x40f9d194,0x40c7c778,0x40f9cccc,0x40f9d09c,0x40e31340,0x40d23c50}:return
  x=[u.reg_read(UC_ARM64_REG_X0+i)for i in range(8)]
  if a==0x4031bee0:self.ret(RAM+0x100+x[0]*3 if x[0]<2 and self.present[x[0]]else 0);return
  if a==0x402db09c:
   p=self.cstr(x[0]);entries=[]
   if p in ['A:\\','B:\\']:
    if p[0]in self.dirs:entries=[('CUSTOM_SOUND',True)]
   elif p.endswith('\\CUSTOM_SOUND') and p[0]in self.dirs:
    prefix=p+'\\';entries=[(key[len(prefix):],False)for key in self.files if key.startswith(prefix)]
   self.enum_stack.append({'entries':entries,'callback':x[2],'lr':u.reg_read(UC_ARM64_REG_LR)});self.enumerate_next();return
  if a==0x402daef0:self.dirs.add(self.cstr(x[0])[0]);self.ret(0);return
  if a==0x40d2c544:self.ret(0x1000000);return
  if a==0x40d2c408:
   if self.alloc_fail:self.ret(0);return
   out=self.heap;self.heap=(out+x[0]+63)&~63;assert self.heap<HEAP+0x1000000;self.ret(out);return
  if a==0x40d2b9e4:self.events.append(('flush',x[0],x[1]));self.ret(1);return
  if a in [0x40863770,0x408637b0]:
   obj=x[0];p=self.cstr(self.r64(obj));create=a==0x408637b0
   if create and not self.write_fail:self.files[p]=b''
   if p not in self.files or(create and self.write_fail):self.ret(0x04320082);return
   fd=self.nextfd;self.nextfd+=1;self.fds[fd]={'path':p,'pos':0};u.mem_write(obj+8,struct.pack('<II',0,fd));self.w64(obj+24,len(self.files[p]));self.ret(0x04320080);return
  if a==0x40863610:
   p=self.cstr(self.r64(x[0]));self.w64(x[0]+24,len(self.files.get(p,b'')));self.ret(0x04320080);return
  if a==0x402dab4c:
   f=self.fds[x[0]]
   if self.read_fail:self.ret(0x80000002);return
   data=self.files[f['path']][f['pos']:f['pos']+min(x[2],997)];f['pos']+=len(data)
   if data:u.mem_write(x[1],data)
   self.w32(x[3],len(data));self.ret(0);return
  if a==0x402dabb8:
   f=self.fds[x[0]]
   if self.write_fail:self.ret(0x80000002);return
   old=self.files[f['path']];data=bytes(u.mem_read(x[1],x[2]));n=f['pos'];self.files[f['path']]=old[:n]+data+old[n+len(data):];f['pos']+=len(data);self.w32(x[3],len(data));self.ret(0);return
  if a==0x402daaac:self.fds.pop(x[0]);self.ret(0);return
  if a==0x403ec398:assert x[0]==0x02006101;self.ret(self.ds);return
  if a==0x403ec39c:assert x[0]==0x02006101;self.ds=x[1];self.ret(1);return
  if a==0x403ae0f8:self.ret(1);return
  if a in [0x403b00b8,0x403b0048]:self.calls.append(('highlight',x[:3]));self.ret(0);return
  if a==0x403f2920:self.draw.append(self.cstr(x[0]));self.ret(0);return
  if a==0x40f9d194:self.notifications.append((x[0],self.r32(x[1]),self.r32(x[1]+4)));self.ret(0);return
  if a==0x40c7c778:self.w64(x[0],12345678);self.ret(0);return
  if a==0x40f9cccc:
   assert bytes(u.mem_read(x[0],16))==struct.pack('<IIQ',192,1536,1);self.tail_requests+=1;self.ret(1);return
  if a==0x40f9d09c:self.native_stops+=1;self.ret(0);return
  if a==0x40e31340:
   self.api_requests.append(x[:4]);sp=u.reg_read(UC_ARM64_REG_SP);u.reg_write(UC_ARM64_REG_X24,self.r64(sp));u.reg_write(UC_ARM64_REG_SP,sp+64);self.ret(0 if self.fail_api else 1);return
  if a==0x40d23c50:
   self.pcm_requests.append(x[:7]);u.reg_write(UC_ARM64_REG_SP,u.reg_read(UC_ARM64_REG_SP)+0x90);self.ret(1);return
 def select(self,index):
  ctx=RAM+0x2000;outer=RAM+0x2100;self.w64(outer,ctx);self.w64(ctx+0x50,HOLDER);self.u.mem_write(ctx+0x32,struct.pack('<H',index));self.u.mem_write(ctx+0x58,bytes(2));return self.call(self.r64(0x43d9ee68),outer)
 def choose_setup(self,n=192,seed=1):
  self.files['A:\\CUSTOM_SOUND\\tone.wav']=wav(n,seed)[0];self.select(5);self.select(6);assert self.field('selected')==1 and self.field('import_status',True)==0
 def api(self,kind=0,loops=0,caller=0x40e314a8,budget=0):return self.call(0x40e3133c,kind,loops,budget,0x40f9d194,lr=caller)
 def pcm(self,kind=0):return self.call(0x40d23c4c,0xA000,4800 if kind else 9600,1,0,0,0,0)
 def notice(self,code,error=0):
  data=RAM+0x3000;self.u.mem_write(data,struct.pack('<II',self.field('kind'),error));return self.call('m2_notice_slot',self.field('current')-1,code,data)
 def finish(self):
  self.notice(0x04102004);self.notice(0x04102005);self.call('m2_notice_retired')
rows=[]
def passed(name,**extra):rows.append({'name':name,'passed':True,**extra});print('PASS',name,flush=True)
# Reuse Lab for focused staged regressions without rerunning the shared suite.
if '--staged-only' not in sys.argv:
 # Native menu + card discovery + real importer and original file wrappers.
 a=Lab();a.choose_setup(288000);assert a.dirs=={'A','B'};assert a.field('pcm_bytes')==288000
 pcm=a.pointer('pcm');assert bytes(a.u.mem_read(pcm,288000))==wav(288000)[1];assert a.ds==0;assert not a.fds
 profiles={k:v for k,v in a.files.items()if k.endswith('.CFG')};assert profiles and all(len(v)==160 for v in profiles.values())
 passed('native_menu_scan_import_1500ms_and_profile_write_readback')
 # New labels work in all 36 languages through the patched native text resolver.
 for language in range(36):
  a.call(0x4032e130,language,0xD01,RAM+0x4000,RAM+0x4010);ptr=a.r64(RAM+0x4000);size=a.r32(RAM+0x4010)
  assert bytes(a.u.mem_read(ptr,size)).decode('utf-16le')=='tone.wav'
 a.call('mark2_outer_type_text',0x42b2f692,0,70);assert a.draw[-1]=='CUS'
 passed('patched_text_resolver_all_36_languages_and_CUS')
 # Busy/invalid imports preserve selected PCM and last successfully saved profile.
 old=(a.pointer('pcm'),dict(profiles));a.w32(P+LAY['state']['active'],1);a.select(6);assert a.field('import_status',True)==13 and a.pointer('pcm')==old[0]
 a.w32(P+LAY['state']['active'],0);a.files['A:\\CUSTOM_SOUND\\tone.wav']=b'ID3'+bytes(128);a.select(6);assert a.field('import_status',True)==7 and a.pointer('pcm')==old[0]
 assert {k:v for k,v in a.files.items()if k.endswith('.CFG')}==old[1]
 passed('busy_and_invalid_selection_preserve_PCM_and_saved_profile')
 # Cold-start lazy restoration rereads the chosen card file.
 saved=dict(a.files);saved['A:\\CUSTOM_SOUND\\tone.wav']=wav(288000)[0]
 b=Lab(saved,{'A','B'});b.call('m2_restore_for_audio');assert b.field('selected')==1 and b.field('pcm_bytes')==288000
 passed('lazy_restore_from_CRC_configuration')
 # Original choices still use original handler and settings IDs.
 b.select(5)
 for i in range(5):b.select(i);assert b.field('selected')==0 and b.ds==i
 passed('all_original_Type_A_to_E_menu_choices')
 # Dual card save, import failures and persistence fallback.
 c=Lab({'A:\\CUSTOM_SOUND\\a.wav':wav(192,1)[0],'B:\\CUSTOM_SOUND\\b.wav':wav(192,2)[0]});c.select(5);c.select(6);c.select(7)
 assert c.field('selected')==1 and c.field('persist_status',True)==0
 fresh=Lab(c.files,c.dirs);fresh.call('m2_restore_for_audio');assert fresh.field('selected')==1 and bytes(fresh.u.mem_read(fresh.pointer('pcm'),192))==wav(192,2)[1]
 passed('dual_card_commit_disables_previous_card_profile')
 # Twenty immutable contents; failed/new choices at capacity do not replace current.
 d=Lab();d.choose_setup();first=d.pointer('pcm');first_bytes=bytes(d.u.mem_read(first,192))
 for seed in range(2,21):d.files['A:\\CUSTOM_SOUND\\tone.wav']=wav(192,seed)[0];d.select(6);assert d.field('import_status',True)==0
 assert d.field('cache_count',True)==20;last=d.pointer('pcm');d.files['A:\\CUSTOM_SOUND\\tone.wav']=wav(192,21)[0];d.select(6)
 assert d.field('cache_full',True)==1 and d.pointer('pcm')==last and bytes(d.u.mem_read(first,192))==first_bytes
 d.files['A:\\CUSTOM_SOUND\\tone.wav']=wav(192,1)[0];d.select(6);assert d.pointer('pcm')==first and d.field('import_status',True)==0
 passed('twenty_content_cache_bound_immutable_old_PCM_and_cached_retry')
 # Actual installed API and PCM trampolines preserve original paths when custom is off.
 e=Lab();assert e.api()==1;e.pcm();assert e.pcm_requests[-1][0:3]==[0xA000,9600,1]
 passed('installed_hooks_pass_through_without_custom_selection')
 e.choose_setup(288000);assert e.api(0,0)==1;e.pcm();assert e.pcm_requests[-1][0:3]==[e.pointer('pcm'),144000,2]
 e.finish();assert e.field('active')==0
 assert e.api(1,1,0x40e31308)==1;e.pcm(1);assert e.pcm_requests[-1][0:3]==[e.pointer('pcm'),144000,2];e.finish()
 passed('installed_fast_and_slow_hooks_full_PCM_beyond_65535_frames')
 # Retirement waits for all three original pending states to clear.
 e.api();e.pcm();e.notice(0x04102004);e.notice(0x04102005);slot=e.field('current')-1
 for state_addr in [0xa038feb74,0xa038feb78,0xa038febb4]:
  e.w32(state_addr,1);e.call('m2_notice_retired');assert e.r32(P+120+slot*20+8)==1;e.w32(state_addr,0)
 e.call('m2_notice_retired');assert e.r32(P+120+slot*20+8)==2
 passed('callback_retirement_waits_for_three_native_pending_states')
 for i in range(160):assert e.api()==1;e.pcm();e.finish()
 assert e.field('used')==64 and e.field('reserved')>0
 passed('native_callback_registration_reuse_after_64_requests',requests=160)
 # C15 and other Cxx: native loop prefix, stop then one finite remainder.
 for mode,caller,kind,prefix,budget in [('C15',0x40e31514,0,9600,66),('C30_C60_C120',0x40e314a8,6,7680,0)]:
  f=Lab();f.choose_setup(288000);f.call('m2_composite');assert f.api(kind,0,caller,budget)==1;f.pcm()
  assert f.pcm_requests[-1][0:3]==[f.pointer('pcm'),prefix,1]
  f.call('m2_cxx_stop');assert f.call('m2_flags',2)==1 and f.native_stops==1
  f.notice(0x04102004);f.notice(0x04102005);assert f.tail_requests==1 and f.field('cxx_tail_pending')==1
  f.call('m2_notice_retired');assert f.api(0,0)==1;f.pcm()
  assert f.pcm_requests[-1][0:3]==[f.pointer('pcm')+prefix,(288000-prefix)//2,2]
  f.finish();assert f.field('cxx_enabled')==0 and f.tail_requests==1
  passed(mode+'_loop_stop_and_single_full_remainder')
 # Short clips loop whole padded content and emit no tail.
 f=Lab();f.choose_setup(192);f.call('m2_composite');f.api(6,0);f.pcm();assert f.pcm_requests[-1][1:3]==[192,1];f.call('m2_cxx_stop');f.notice(0x04102004);f.notice(0x04102005);assert f.tail_requests==0
 passed('short_Cxx_clip_no_artificial_40ms_padding_or_tail')
 # Upper native API failure and allocation/read/save failures remain bounded.
 f=Lab();f.choose_setup();f.fail_api=True;assert f.api()==0;assert f.field('active')==0 and f.field('api_failures')==1
 passed('upper_API_failure_releases_active_route')
 f=Lab();f.files['A:\\CUSTOM_SOUND\\tone.wav']=wav()[0];f.alloc_fail=True;f.select(5);f.select(6);assert f.field('selected')==0
 passed('allocation_failure_keeps_native_sound')
 f=Lab();f.choose_setup();old=f.pointer('pcm');f.read_fail=True;f.select(6);assert f.pointer('pcm')==old and not f.fds
 passed('read_failure_preserves_selection_and_closes_handle')

 # Execute the installed common synchronous and asynchronous retirement trampolines.
 f=Lab();f.w32(P+LAY['state']['used'],1);f.w32(P+120+8,1);sp=RAM+0x1f0000
 f.u.mem_write(sp+0x10,struct.pack('<QQQQ',0x2121,0x2020,0x1919,STOP))
 assert f.call(0x40e35420,1)==1 and f.r32(P+128)==2
 assert f.u.reg_read(UC_ARM64_REG_SP)==sp+0x30 and f.u.reg_read(UC_ARM64_REG_X19)==0x1919
 f.w32(P+128,1);f.w64(sp,STOP);assert f.call(0x40e35590,99)==1 and f.r32(P+128)==2
 assert f.u.reg_read(UC_ARM64_REG_SP)==sp+0x10
 passed('installed_sync_common_epilogue_and_async_retirement_hooks')
 # Failed cross-card save leaves the previous card's valid profile intact.
 f=Lab({'A:\\CUSTOM_SOUND\\a.wav':wav(192,1)[0],'B:\\CUSTOM_SOUND\\b.wav':wav(192,2)[0]});f.select(5);f.select(6)
 old={k:v for k,v in f.files.items()if k.startswith('A:')and k.endswith('.CFG')};f.write_fail=True;f.select(7)
 assert f.field('persist_status',True)!=0 and {k:v for k,v in f.files.items()if k.startswith('A:')and k.endswith('.CFG')}==old
 passed('failed_new_card_profile_commit_preserves_old_card_profile')
 f=Lab(f.files,f.dirs,present=(False,False));f.call('m2_restore_for_audio');assert f.field('selected')==0
 passed('missing_card_restore_keeps_native_sound_route')


 # 04.21 confirmation executes the actual compiled importer twice before bind.
 if 'confirm_attempts' in LAY['picker']:
  f=Lab();f.choose_setup(237696)
  assert f.field('confirm_attempts',True)==1 and f.field('confirm_flushes',True)==1
  assert f.field('attempts',True)==2 and f.field('cache_hits',True)==(0 if STAGED else 1)
  assert f.field('scratch_allocations',True)==(2 if STAGED else 1) and f.field('cache_allocations',True)==1
  if STAGED:
   names=[e[0] for e in f.events];assert names.count('import')==2 and names[-2:]==['flush','bind']
   assert f.pointer('confirm_first',True)!=f.pointer('confirm_second',True)
  else:assert [e[0] for e in f.events]==['import','flush','import','flush','bind']
  assert not f.api_requests and not f.pcm_requests
  first=f.pointer('pcm');f.select(6)
  assert f.pointer('pcm')==first and f.field('cache_allocations',True)==1
  assert f.field('attempts',True)==4 and f.field('cache_hits',True)==(1 if STAGED else 3)
  passed('confirmed_import_two_reads_flush_before_bind_no_audio_or_extra_allocation')
  # A card error during the confirmation pass must not publish or persist.
  for failure in ['read','changed']:
   f=Lab();f.choose_setup();old=f.pointer('pcm')
   profiles={k:v for k,v in f.files.items()if k.endswith('.CFG')}
   f.files[r'A:\CUSTOM_SOUND\tone.wav']=wav(192,2)[0]
   target=f.import_calls+2
   def on_import(lab):
    if failure=='changed' and 'confirm_retries' in LAY['picker'] and lab.import_calls>=target:
     lab.files[r'A:\CUSTOM_SOUND\tone.wav']=wav(192,3+lab.import_calls%2)[0]
    elif lab.import_calls==target:
     if failure=='read':lab.read_fail=True
     else:lab.files[r'A:\CUSTOM_SOUND\tone.wav']=wav(192,3)[0]
   f.before_import=on_import;f.events=[];f.select(6)
   retrying='confirm_retries' in LAY['picker'] and failure=='changed'
   assert f.field('import_status',True)==(14 if retrying else 4) and f.pointer('pcm')==old
   assert f.field('confirm_failures',True)==(2 if retrying else 1) and not any(e[0]=='bind' for e in f.events)
   assert {k:v for k,v in f.files.items()if k.endswith('.CFG')}==profiles and not f.fds
   passed('confirmation_'+failure+'_failure_keeps_previous_PCM_and_profile')
  # Lazy restore uses the same confirmation, without submitting an audio request.
  f=Lab(profiles,{'A'});f.files[r'A:\CUSTOM_SOUND\tone.wav']=wav()[0]
  f.call('m2_restore_for_audio')
  assert f.field('selected')==1 and f.field('confirm_flushes',True)==1
  if STAGED:assert [e[0] for e in f.events][-2:]==['flush','bind']
  else:assert [e[0] for e in f.events]==['import','flush','import','flush','bind']
  passed('restoration_also_confirms_before_binding')


 # 04.22: one complete fresh pair may recover a one-time PCM discrepancy.
 if 'confirm_retries' in LAY['picker']:
  class TransientPCM(Lab):
   def __init__(self):
    self.injected=False
    super().__init__()
   def hook(self,u,a,size,user):
    # Inject at the second import boundary before publishing staging.
    if STAGED and a==SYMS['m2_native_import_buffered'] and self.import_calls==1 and not self.injected:
     ptr=self.pointer('confirm_first',True);old=bytes(u.mem_read(ptr+64,1))
     u.mem_write(ptr+64,bytes([old[0]^1]));self.injected=True
    elif not STAGED and a==0x40d2b9e4 and not self.injected:
     ptr=u.reg_read(UC_ARM64_REG_X0);old=bytes(u.mem_read(ptr+64,1))
     u.mem_write(ptr+64,bytes([old[0]^1]));self.injected=True
    return super().hook(u,a,size,user)
  f=TransientPCM();f.instruction_limit=80000000 if STAGED else 12000000;f.choose_setup(237696)
  assert f.field('attempts',True)==4 and f.field('imports',True)==1
  assert f.field('confirm_retries',True)==1 and f.field('confirm_mismatches',True)==1
  assert f.field('confirm_diff',True)==64 and f.field('confirm_reason',True)==(129 if STAGED else 1)
  assert f.field('confirm_stage',True)==5 and f.field('confirm_error',True)==0
  assert f.field('profile_commits',True)==1 and sum(e[0]=='bind' for e in f.events)==1
  assert bytes(f.u.mem_read(f.pointer('pcm'),237696))==wav(237696)[1]
  assert not f.api_requests and not f.pcm_requests
  passed('one_selection_recovers_transient_PCM_difference_with_fresh_matching_pair')
  # Persistent changing contents have a finite four-import bound and never bind.
  f=Lab();f.files[r'A:\CUSTOM_SOUND\tone.wav']=wav()[0];f.select(5)
  def alternate(lab):lab.files[r'A:\CUSTOM_SOUND\tone.wav']=wav(192,lab.import_calls)[0]
  f.before_import=alternate;f.select(6)
  assert f.field('selected')==0 and f.field('attempts',True)==4
  assert f.field('confirm_retries',True)==1 and f.field('confirm_mismatches',True)==2
  assert f.field('import_status',True)==14 and not any(e[0]=='bind' for e in f.events)
  f.call('mark2_picker_label',0,0xD00,RAM+0x4000,RAM+0x4010)
  assert bytes(f.u.mem_read(f.r64(RAM+0x4000),f.r32(RAM+0x4010))).decode('utf-16le')==('WAV diff 01 @000000' if STAGED else 'WAV mismatch - retry')
  passed('persistent_mismatch_stops_after_four_imports_with_specific_error')
  # A first-pass read error is not silently replaced by a later successful pair.
  f=Lab();f.files[r'A:\CUSTOM_SOUND\tone.wav']=wav()[0];f.select(5);f.read_fail=True;f.select(6)
  assert f.field('attempts',True)==1 and f.field('confirm_stage',True)==1
  assert f.field('confirm_error',True)==4 and f.field('selected')==0
  f.call('mark2_picker_label',0,0xD00,RAM+0x4000,RAM+0x4010)
  assert bytes(f.u.mem_read(f.r64(RAM+0x4000),f.r32(RAM+0x4010))).decode('utf-16le')=='WAV read failed - retry'
  passed('first_read_error_keeps_native_selection_and_reports_read_failure')

 report={'status':'PASS_BOUNDED_ARM_INTEGRATION','payload_sha256':hashlib.sha256(PAYLOAD).hexdigest(),'tests':len(rows),'rows':rows,'executed':['actual installed trampolines','actual adapted C','original Z8 menu selection/refresh consumers','original Z8 file wrappers and status conversion'],'mocked':['card mount/enumeration','lower filesystem and stat','allocator/cache maintenance','native upper audio worker/API body','original audio notification consumer','UI drawing and DSID storage'],'full_QEMU':False,'hardware':False}
 (C/'arm-integration-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('ALL_PASS',len(rows),flush=True)
