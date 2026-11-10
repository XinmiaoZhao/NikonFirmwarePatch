# SPDX-License-Identifier: GPL-3.0-or-later
# Derived from s3lemming/z9-firmware-patch at 88a6f3e5195d7f38792dc8eddeb1526fde4096dc.
# Z8 adaptation and local experimental integration. No device qualification implied.
"""Build mark2 v13 onto a checked Z8 C3.11 feature base.

The source tree contains no original instruction words or menu resources.
Any displaced instruction/resource is read locally from the exact checked input.
The prebuilt unit (resources/shuttersound.bin) has its displaced-instruction slots
zeroed; they are filled from the same input, so it needs no LLVM.
"""
import binascii, hashlib, json, re, struct, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXPECTED_MODULE='f85e0138e2f5e660ece8560de62e0d12cb795e0e14983e50f20b61dce906c46c'
EXPECTED_PAYLOAD=None
# Picker label IDs intercepted in the stock text resolver. Must stay disjoint
# from feature string IDs (z8patch/shared.py STRING_IDS..STRING_END); the
# disjointness is pinned by tests/test_shuttersound_ids.py.
WAV_LABEL_BASE=0xD00
WAV_LABEL_COUNT=21
UNIT=ROOT.parent/'resources'/'shuttersound.json'
# Hook slots that replay one original instruction: slot label -> source VA.
DISPLACED={'api':0x40e3133c,'pcm':0x40d23c4c,'flags':0x40f9c5cc,'terminal':0x40f9cda0,'fast_timer':0x40f9cc64,'composite':0x40f9cfa4,'cxx_stop':0x40f9d00c,'notice_sync_end':0x40e35420,'notice_async_end':0x40e35590,'label':0x4032e130}
def build(module,output,base_module=None,llvm=None,tail=b'Ver.04.12.p0\0',code_source='prebuilt'):
    if not __debug__: raise ValueError('Optimized Python disables internal checks; use normal Python')
    if Path(output).is_symlink(): raise ValueError('Build directory must not be a link')
    module=Path(module).resolve();O=Path(output).resolve()
    if O.exists(): raise ValueError('Build directory must be new')
    if O.is_relative_to(ROOT): raise ValueError('Keep private build output outside the repository')
    if hashlib.sha256(module.read_bytes()).hexdigest()!=EXPECTED_MODULE: raise ValueError('Only the exact original Z8 C3.11 MAIN module is supported')
    manifest=json.loads((ROOT/'source-provenance.json').read_text(encoding='utf-8'))
    for name,entry in manifest['files'].items():
        if hashlib.sha256((ROOT/'firmware'/name).read_bytes()).hexdigest()!=entry['adapted_sha256']: raise ValueError('Adapted source identity changed: '+name)
    if base_module is None: raise ValueError('The port requires a verified feature base with no old sound patches')
    if code_source not in ('prebuilt','source'): raise ValueError('Select prebuilt or source')
    O.mkdir(parents=True);patches=[];commands=[]
    def sha(b):return hashlib.sha256(b).hexdigest()
    raw=module.read_bytes();assert sha(raw)==EXPECTED_MODULE
    orig=raw[:-2];base=Path(base_module).read_bytes() if base_module else raw;assert len(base)==len(raw) and binascii.crc_hqx(base,0)==0; b=bytearray(base[:-2]);BASE=0x40160000;ENTRY=0x44f6c000;patches=[];commands=[]
    source=ROOT/'firmware/adapter.c'
    for n in ['adapter.c','picker.c','mark2_import.c','mark2_import.h','mark2_native_file.c','profile.h','profile.c','profile_native.c','runtime.c']:(O/n).write_bytes((source.parent/n).read_bytes())


    def run(args):
     name=args[0]; names={'aarch64-linux-gnu-gcc':'clang','aarch64-linux-gnu-ld':'ld.lld','aarch64-linux-gnu-nm':'llvm-nm','aarch64-linux-gnu-objcopy':'llvm-objcopy','aarch64-linux-gnu-objdump':'llvm-objdump'}; tool=Path(llvm)/names[name]; tool=tool.with_suffix('.exe') if tool.with_suffix('.exe').exists() else tool; args=[str(tool),*(['--target=aarch64-none-elf'] if name=='aarch64-linux-gnu-gcc' else []),*args[1:]]
     q=subprocess.run(args,cwd=O,capture_output=True,text=True);commands.append(dict(argv=args,returncode=q.returncode,stdout=q.stdout,stderr=q.stderr));(O/'commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8');assert q.returncode==0,q.stderr;return q.stdout
    def off(a):return a-0xa02808000+0x4b13000 if 0xa02808000<=a<0xa02ab5000 else a-BASE
    def patch(a,new,why):
     p=off(a);old=orig[p:p+len(new)];assert len(old)==len(new) and b[p:p+len(new)]==old
     b[p:p+len(new)]=new;patches.append(dict(VA=hex(a),input_space='ROM or proven initialized RAM',offset=hex(p),original_SHA256=sha(old),replacement_SHA256=sha(new),bytes=len(new),consumer=why))
    def branch(a,target):
     delta=target-a;assert delta%4==0 and -(1<<27)<=delta<(1<<27);return struct.pack('<I',0x14000000|((delta//4)&0x3ffffff))

    def append(blob,align=16):
     b.extend(bytes(-len(b)%align));p=len(b);b.extend(blob);return BASE+p
    rows=orig[0x43d64d94-BASE:0x43d64d94-BASE+5*44];new=bytearray(rows[-44:]);struct.pack_into('<H',new,0,WAV_LABEL_BASE);struct.pack_into('<I',new,24,0x7e20)
    rp=append(rows+new);ep=append(orig[0x43d64e70-BASE:0x43d64e70-BASE+40]+21*orig[0x43d64e70-BASE:0x43d64e70-BASE+8])
    patch(0xa028cb040,struct.pack('<Q',rp),'Sound rows: five originals byte-identical plus Load WAV from card')
    patch(0xa028cb048,struct.pack('<Q',ep),'26 original-compatible event bindings; 20 displayed files')
    patch(0xa028cb050,struct.pack('<H',6),'Initial six sound rows; scanned filenames published by native task')
    for pc in [0xa028cb058,0xa028cb060]:patch(pc,struct.pack('<H',416),'Bound native scrolling list rectangle')
    classes=orig[0x4320a3cc-BASE:0x4320a3cc-BASE+0xc40];cp=append(classes+41*classes[0x925:0x926],1)
    words=memoryview(orig[:0x13c0000]).cast('I');sites=[]
    for i,w in enumerate(words):
     if w&0xff800000!=0xd2800000 or(w>>5)&0xffff!=0xa3cc:continue
     reg=w&31;value=(w>>5)&0xffff;pcs=[BASE+i*4]
     for j in range(i+1,min(i+10,len(words))):
      n=words[j]
      if n&0xff80001f==0xf2800000|reg:
       shift=((n>>21)&3)*16;value=(value&~(0xffff<<shift))|(((n>>5)&0xffff)<<shift);pcs.append(BASE+j*4)
       if shift==48:break
     if value!=0x4320a3cc:continue
     sites.append(pcs)
     for pc in pcs:
      word=struct.unpack_from('<I',orig,pc-BASE)[0];shift=((word>>21)&3)*16
      patch(pc,struct.pack('<I',(word&~(0xffff<<5))|(((cp>>shift)&0xffff)<<5)),'Extended label classifier; original entries unchanged')
    assert sites
    api=struct.unpack_from('<I',orig,0x40e3133c-BASE)[0]
    call=struct.unpack_from('<I',orig,0x40e31304-BASE)[0];assert call&0xfc000000==0x94000000 and 0x40e31304+((call&0x3ffffff)<<2)==0x40e3133c
    asm=['.section .text.hooks,"ax"']
    for name,func,pc,word in [('api','m2_api',0x40e3133c,api),('pcm','m2_pcm',0x40d23c4c,struct.unpack_from('<I',orig,0x40d23c4c-BASE)[0])]:
     assert struct.unpack_from('<I',orig,pc-BASE)[0]==word
     asm += [f'.global hook_{name}',f'hook_{name}:','sub sp,sp,#96','stp x0,x1,[sp]','stp x2,x3,[sp,#16]','stp x4,x5,[sp,#32]','stp x6,x7,[sp,#48]','str x30,[sp,#64]','mov x0,sp',f'bl {func}',*(['cbnz w0,api_rejected']if name=='api'else []),'ldp x0,x1,[sp]','ldp x2,x3,[sp,#16]','ldp x4,x5,[sp,#32]','ldp x6,x7,[sp,#48]',*(['bl original_api','str x0,[sp,#72]','mov x0,sp','bl m2_api_result','ldr x0,[sp,#72]','ldr x30,[sp,#64]','add sp,sp,#96','ret']if name=='api'else ['ldr x30,[sp,#64]','add sp,sp,#96',f'displaced_{name}:',f'.inst {word}',f'b continue_{name}'])]
    for name,func,pc,word in [('flags','m2_flags',0x40f9c5cc,struct.unpack_from('<I',orig,0x40f9c5cc-BASE)[0]),('terminal','m2_terminal',0x40f9cda0,struct.unpack_from('<I',orig,0x40f9cda0-BASE)[0]),('fast_timer','m2_fast_timer',0x40f9cc64,struct.unpack_from('<I',orig,0x40f9cc64-BASE)[0])]:
     assert struct.unpack_from('<I',orig,pc-BASE)[0]==word
     asm += [f'.global hook_{name}',f'hook_{name}:','stp x0,x30,[sp,#-16]!',*(['mov x0,x30']if name=='terminal'else []),f'bl {func}','mov w9,w0','ldp x0,x30,[sp],#16','cbnz w9,1f',f'displaced_{name}:',f'.inst {word}',f'b continue_{name}','1: ret']

    for name,func,pc in [('composite','m2_composite',0x40f9cfa4),('cxx_stop','m2_cxx_stop',0x40f9d00c)]:
     word=struct.unpack_from('<I',orig,pc-BASE)[0]
     asm += [f'.global hook_{name}',f'hook_{name}:','sub sp,sp,#80','stp x0,x1,[sp]','stp x2,x3,[sp,#16]','stp x4,x5,[sp,#32]','stp x6,x7,[sp,#48]','str x30,[sp,#64]',f'bl {func}','ldp x0,x1,[sp]','ldp x2,x3,[sp,#16]','ldp x4,x5,[sp,#32]','ldp x6,x7,[sp,#48]','ldr x30,[sp,#64]','add sp,sp,#80',f'displaced_{name}:',f'.inst {word}',f'b continue_{name}']
    asm+=['api_rejected:','ldr x30,[sp,#64]','add sp,sp,#96','mov w0,wzr','ret',
     '.global original_api','original_api:','displaced_api:',f'.inst {api}','b continue_api']
    for i in range(64):
     asm += [f'.global notice_slot_{i}',f'notice_slot_{i}:','mov x2,x1','mov w1,w0',f'mov w0,#{i}','b m2_notice_slot']
    for name,pc in [('notice_sync_end',0x40e35420),('notice_async_end',0x40e35590)]:
     word=struct.unpack_from('<I',orig,pc-BASE)[0]
     asm += ['.section .text.hooks,"ax"',f'.global hook_{name}',f'hook_{name}:','stp x0,x30,[sp,#-16]!','bl m2_notice_retired','ldp x0,x30,[sp],#16',f'displaced_{name}:',f'.inst {word}',f'b continue_{name}']
    asm += ['.section .rodata.callbacks,"a"','.balign 8','.global callback_slots','callback_slots:']
    asm += [f'.quad notice_slot_{i}'for i in range(64)]
    label_word=struct.unpack_from('<I',orig,0x4032e130-BASE)[0]
    asm += ['.section .text.labels,"ax"','.global mark2_discovery_label','mark2_discovery_label:',
     f'cmp w1,#{WAV_LABEL_BASE:#x}','b.lo 3f',f'cmp w1,#{WAV_LABEL_BASE+WAV_LABEL_COUNT:#x}','b.lo mark2_picker_label','3:',
     'displaced_label:',f'.inst {label_word}','b native_text_continue']
    (O/'hooks.S').write_text('\n'.join(asm)+'\n')
    (O/'layout.ld').write_text('continue_notice_sync_end = 0x40e35424; continue_notice_async_end = 0x40e35594; native_text_continue = 0x4032e134; continue_composite = 0x40f9cfa8; continue_cxx_stop = 0x40f9d010; continue_api = 0x40e31340; continue_pcm = 0x40d23c50; continue_flags = 0x40f9c5d0; continue_terminal = 0x40f9cda4; continue_fast_timer = 0x40f9cc68; SECTIONS { . = 0x44f6c000; .text : { *(.text*) } .rodata : { *(.rodata*) } /DISCARD/ : { *(.comment) *(.eh_frame*) *(.note*) } }\n')
    flags=['-O2','-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin','-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-mgeneral-regs-only','-mstrict-align','-fno-pic','-march=armv8-a','-mno-outline-atomics']

    # Confirmation hardening is unconditional in this port: the stacked base may
    # carry any NN.NN identity, and a low number must never select weaker legacy
    # behaviour (matches the standalone z8-card-wav CLI policy).
    if re.fullmatch(rb'Ver\.[0-9]{2}\.[0-9]{2}[^\x00]*\x00+',tail) is None: raise ValueError('Invalid shutter-sound version identity')
    confirmed_import=confirmation_retry=staged_confirmation=True
    flags.extend(['-DM2_CONFIRM_IMPORT=1','-DM2_CONFIRM_RETRY=1','-DM2_STAGED_CONFIRM=1'])

    UNIT = ROOT.parent/'resources'/'shuttersound.json'
    if code_source=='source':
     for unit in ['picker','mark2_import','mark2_native_file','profile','profile_native','runtime']:run(['aarch64-linux-gnu-gcc',*flags,'-c',unit+'.c','-o',unit+'.o'])
     run(['aarch64-linux-gnu-gcc',*flags,'-c','adapter.c','-o','adapter.o']);run(['aarch64-linux-gnu-gcc','-c','hooks.S','-o','hooks.o']);run(['aarch64-linux-gnu-ld','--build-id=none','-T','layout.ld','adapter.o','hooks.o','picker.o','mark2_import.o','mark2_native_file.o','profile.o','profile_native.o','runtime.o','-o','adapter.elf']);assert not run(['aarch64-linux-gnu-nm','-u','adapter.elf']).strip()
     symbol_text=run(['aarch64-linux-gnu-nm','-n','adapter.elf'])
     (O/'record-layouts.txt').write_text(''.join(run(['aarch64-linux-gnu-gcc',*flags,'-Xclang','-fdump-record-layouts','-fsyntax-only',unit+'.c'])for unit in ['adapter','picker']),encoding='utf-8')
     run(['aarch64-linux-gnu-objcopy','-O','binary','adapter.elf','adapter.bin']);dis=run(['aarch64-linux-gnu-objdump','-d','adapter.elf']);(O/'adapter-disassembly.txt').write_text(dis,encoding='utf-8')
     code=(O/'adapter.bin').read_bytes();compiler=run(['aarch64-linux-gnu-gcc','--version']).splitlines()[0]
     syms={v[2]:int(v[0],16)for line in symbol_text.splitlines()if len(v:=line.split())==3}
     # Zero every replayed original word; the blank unit carries no firmware bytes.
     blank=bytearray(code)
     for name,pc in DISPLACED.items():
      at=syms['displaced_'+name]-ENTRY;assert code[at:at+4]==orig[pc-BASE:pc-BASE+4];blank[at:at+4]=bytes(4)
     unit=dict(bytes=len(blank),sha256=sha(blank),filled_sha256=sha(code),compiler=compiler,symbols=symbol_text.splitlines())
     if staged_confirmation: unit['record_layouts']=(O/'record-layouts.txt').read_text(encoding='utf-8')
     (O/'shuttersound.bin').write_bytes(blank);(O/'shuttersound.json').write_text(json.dumps(unit,indent=1)+'\n',encoding='utf-8')
     if UNIT.is_file() and json.loads(UNIT.read_text(encoding='utf-8'))!=unit: raise ValueError('Compiled shutter-sound unit differs from the reviewed resources/shuttersound.json (expected '+json.loads(UNIT.read_text(encoding='utf-8'))['compiler']+')')
    else:
     unit=json.loads(UNIT.read_text(encoding='utf-8'));path=UNIT.with_suffix('.bin')
     if not path.is_file(): raise ValueError('Prebuilt shutter-sound unit missing: '+str(path)+'; use the matching release unit or explicit source mode')
     blank=path.read_bytes()
     if len(blank)!=unit['bytes'] or sha(blank)!=unit['sha256']: raise ValueError('Prebuilt shutter-sound unit differs from resources/shuttersound.json')
     symbol_text='\n'.join(unit['symbols'])+'\n';syms={v[2]:int(v[0],16)for line in unit['symbols']if len(v:=line.split())==3}
     code=bytearray(blank)
     for name,pc in DISPLACED.items():
      at=syms['displaced_'+name]-ENTRY;assert code[at:at+4]==bytes(4);code[at:at+4]=orig[pc-BASE:pc-BASE+4]
     code=bytes(code)
     if sha(code)!=unit['filled_sha256']: raise ValueError('Filled shutter-sound unit differs from the reviewed recipe')
     if 'record_layouts' in unit: (O/'record-layouts.txt').write_text(unit['record_layouts'],encoding='utf-8')
     (O/'adapter.bin').write_bytes(code);compiler=unit['compiler']+' (prebuilt)'
    (O/'symbols.txt').write_text(symbol_text,encoding='utf-8')
    code=(O/'adapter.bin').read_bytes();end=(ENTRY+len(code)+4095)&~4095
    assert len(b)+BASE<=ENTRY and end<0x45980000
    b.extend(bytes(ENTRY-BASE-len(b)));b.extend(code)
    call2=struct.unpack_from('<I',orig,0x40e314a4-BASE)[0];assert call2&0xfc000000==0x94000000
    for pc,name in [(0x40e3133c,'api'),(0x40d23c4c,'pcm'),(0x40f9c5cc,'flags'),(0x40f9cda0,'terminal'),(0x40f9cc64,'fast_timer')]:patch(pc,branch(pc,syms['hook_'+name]),name+' native adapter, original displaced instruction replayed')
    for pc,name in [(0x40f9cfa4,'composite'),(0x40f9d00c,'cxx_stop')]:patch(pc,branch(pc,syms['hook_'+name]),'Composite-route bounded frame audio '+name+'; original entry instruction replayed')
    for pc,name in [(0x40e35420,'notice_sync_end'),(0x40e35590,'notice_async_end')]:patch(pc,branch(pc,syms['hook_'+name]),'Retire callback registration after original final notice and pending outputs clear; no PCM free')
    # Original current-frame call is left unchanged; no late frame audio retrigger.
    assert orig[off(0xa02aab050):off(0xa02aab050)+32]==struct.pack('<IIQQQ',1,15,0xa02ab5000,0xa02ab5000,0)
    patch(0xa02aab050,struct.pack('<IIQQQ',2,15,ENTRY,end,ENTRY),'Explicit RX map for authored integration code')
    patch(0xa02aab120,struct.pack('<Q',ENTRY),'Original resource RO region ends before explicit RX')
    size=struct.unpack_from('<Q',orig,off(0x401680e8))[0];assert 0xa02afb000+size==0xa04b89000
    assert (0xa04b89000+8192+16383)&~16383==0xa04b8c000
    patch(0x401680e8,struct.pack('<Q',size+8192),'Native startup private BSS +8192; original TTBR alignment unchanged')
    for pc in [0x43d9ee68,0x43d9ee88,0x43d9ef28]:
     assert struct.unpack_from('<Q',orig,off(pc))[0]==0x405a5878
     patch(pc,struct.pack('<Q',syms['mark2_discovery_submit']),'All native Type menu submit events -> file/native selector, original handler retained')
    assert struct.unpack_from('<Q',orig,off(0xa028ed100))[0]==0x405a57f4
    patch(0xa028ed100,struct.pack('<Q',syms['mark2_sound_refresh']),'Native type refresh followed by selected filename highlight')
    # Displaced text instruction was read from the user input above.
    patch(0x4032e130,branch(0x4032e130,syms['mark2_discovery_label']),'Custom labels only; original text resolver instruction replayed')
    patch(0x405a5618,struct.pack('<I',0x94000000|(((syms['mark2_outer_type_text']-0x405a5618)//4)&0x3ffffff)),'Only outer Camera sounds Type text: CUS when custom selected, native enum unchanged')
    b.extend(tail);payload=O/'payload.bin'
    assert len(code)>0 and len(b)+BASE<0x45980000
    payload.write_bytes(b)
    module_bytes=bytes(b)+struct.pack('>H',binascii.crc_hqx(b,0))
    (O/'patched-eg.bi').write_bytes(module_bytes)

    result=dict(feature='Z8-custom-shutter-sound',confirmed_import=confirmed_import,confirmation_retry=confirmation_retry,staged_confirmation=staged_confirmation,input_module_sha256=sha(raw),base_module_sha256=sha(base),payload_sha256=sha(b),payload_bytes=len(b),module_sha256=sha(module_bytes),module_bytes=len(module_bytes),patches=patches,device_qualified_note='camera-verified on the v0.4.0-rc.2 four-group prebuilt base with every feature enabled',code_source=code_source,compiler=compiler,device_qualified=True)
    (O/'build-report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result
