"""Compile original patch source or read its matching reviewed Release bytes.

No compiler fallback, downloads, firmware reads or writes to the repository.
"""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from z8prores.package import require, sha
from .linker import link

ROOT = Path(__file__).resolve().parents[1]
FLAGS = ['--target=aarch64-none-elf','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector',
         '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-mgeneral-regs-only','-mstrict-align',
         '-Wall','-Wextra','-Werror']
SPECS = {
    'precapture': dict(source='z8precapture/firmware.c', flags=FLAGS, cave=0x409F0000, limit=0x40A00000, entry='precapture_history_entry'),
    'pixelshift': dict(source='z8pixelshift/src/ps8.c', flags=FLAGS+['-DPS11_REVIEW_LAYOUT=0x409ec800ull'], cave=0x40990000, limit=0x409D8000, entry='psm_menu_action'),
    'pixelshift-af': dict(source='z8pixelshift/src/af_unit.c', flags=[f for f in FLAGS if f!='-mgeneral-regs-only']+['-ffp-contract=off'], cave=0x409D8000, limit=0x409DA000, entry='ps8_af_one_batch'),
    'opengate': dict(source='z8opengate/src/d10_hooks.S', flags=['-target','aarch64-none-elf','-x','assembler-with-cpp','-DFULL_OUTPUT=1','-DWITH_Q3=1','-DQ3_STASH_RAM=0xa0ff50000','-DQ3_FINE_TABLE=0x40953000','-DQ3_BASIC_TABLE=0x409533f0','-DOG_TIER_DELTA=0x4000']),
}
SPECS.update({
    'anamorphic':dict(source='z8anamorphic/src/hooks.S', flags=['-target','aarch64-none-elf','-x','assembler-with-cpp'],asm_base=0x40970000,limit=0x40974000,folder='z8anamorphic'),
    'h265':dict(source='z8h265/src/hooks.S', flags=['-target','aarch64-none-elf','-x','assembler-with-cpp'],asm_base=0x40A10000,limit=0x40A12000,folder='z8h265'),
    'log':dict(source='z8log/src/hooks.S', flags=['-target','aarch64-none-elf','-x','assembler-with-cpp'],asm_base=0x40B00000,limit=0x40B08000,folder='z8log'),
    'quality':dict(source='z8quality/src/hooks.S', flags=['-target','aarch64-none-elf','-x','assembler-with-cpp'],asm_base=0x40A41000,limit=0x40A50000,folder='z8quality'),
    'vrotate':dict(source='z8vrotate/src/hooks.S', flags=['-target','aarch64-none-elf','-x','assembler-with-cpp'],asm_base=0x40A08000,limit=0x40A10000,folder='z8vrotate'),
    'shared':dict(source='z8patch/src/shared.S', flags=['-target','aarch64-none-elf','-x','assembler-with-cpp'],asm_base=0x40980000,limit=0x40980F00,folder='z8patch/src'),
})


def source_files(name):
    if 'folder' in SPECS[name]:
        folder=ROOT/SPECS[name]['folder']
        return {p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in sorted(folder.rglob('*'))
                if p.is_file() and p.suffix in ('.py','.S','.json','.png')}
    folder = ROOT/('z8precapture' if name=='precapture' else 'z8opengate/src' if name=='opengate' else 'z8pixelshift/src')
    return {p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in sorted(folder.iterdir()) if p.suffix in ('.c','.h','.inc','.S')}



def compile_unit(name, compiler='clang'):
    """Maintainer primitive; callers must compare output against a reviewed recipe."""
    spec = dict(SPECS[name])
    if name=='log':
        from z8log.patcher import asm_defines
        spec['flags']=[*spec['flags'],*[f'-D{k}={v:#x}' for k,v in sorted(asm_defines().items())]]
    with tempfile.TemporaryDirectory(prefix='nikon-patch-compile-') as folder:
        obj = Path(folder)/'patch.o'
        cmd = [compiler,*spec['flags'],'-c',str(ROOT/spec['source']),'-o',str(obj)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        require(result.returncode==0, 'Compiler failed: '+result.stderr[-5000:])
        if 'asm_base' in spec:
            from .asm import link_elf
            code, entries, relocations=link_elf(obj.read_bytes(),spec['asm_base'])
            require(spec['asm_base']+len(code)<=spec['limit'],'Assembly exceeds its reserved area')
            symbols={k:dict(va=hex(v),bytes=0) for k,v in entries.items()}
        elif name=='opengate':
            from z8opengate.linker import link_elf
            raw, entries, relocations = link_elf(obj.read_bytes())
            code = bytearray(raw)
            offset = 0x40960CBC-0x40960000
            require(code[offset:offset+4]==bytes.fromhex('1f1100b9'), 'D9 display seam differs')
            target = entries['og_leave_display_hook']
            struct.pack_into('<I', code, offset, 0x94000000 | (((target-0x40960CBC)//4)&0x3FFFFFF))
            code = bytes(code)
            require(len(code)<0xF000, 'Open-gate code reaches private state')
            symbols = {k:dict(va=hex(v),bytes=0) for k,v in entries.items()}
        else:
            code, sections, symbols, relocations = link(obj.read_bytes(), spec['cave'], spec['limit'], spec['entry'])
    return code, dict(bytes=len(code),sha256=sha(code),symbols=symbols,source_sha256=source_files(name),
                      compiler=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0],
                      flags=spec['flags'],resource='resources/'+name+'.bin')


def load(name, code_source='prebuilt', compiler='clang'):
    profile = json.loads((ROOT/'resources/compiled.json').read_text())['units'][name]
    require(source_files(name)==profile['source_sha256'], 'Compiled patch source does not match the reviewed recipe: '+name)
    if code_source=='source':
        code, observed = compile_unit(name, compiler)
        require(observed['symbols']==profile['symbols'], 'Compiled symbols differ: '+name)
    else:
        require(code_source=='prebuilt', 'Select prebuilt or source code')
        path = ROOT/profile['resource']
        require(path.is_file(), 'Precompiled patch missing: '+profile['resource']+'; extract the complete matching Release toolkit or explicitly select --code-source source')
        require(path.stat().st_size==profile['bytes'], 'Precompiled patch size differs: '+name)
        code = path.read_bytes()
    require(len(code)==profile['bytes'] and sha(code)==profile['sha256'], 'Patch code differs from the reviewed recipe: '+name)
    return code, profile
