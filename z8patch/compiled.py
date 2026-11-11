"""Compile original patch source or read its matching reviewed Release bytes.

No compiler fallback, downloads, firmware reads or writes to the repository.
"""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from z8prores.package import require, sha
from .linker import link, CAVE as OPENGATE_CAVE

ROOT = Path(__file__).resolve().parents[1]
FLAGS = ['--target=aarch64-none-elf','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector',
         '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-mgeneral-regs-only','-mstrict-align',
         '-Wall','-Wextra','-Werror']
SPECS = {
    'precapture': dict(source='z8precapture/firmware.c', flags=FLAGS, cave=0x409F0000, limit=0x40A00000, entry='precapture_history_entry'),
    'pixelshift': dict(source='z8pixelshift/src/ps8.c', flags=FLAGS+['-DPS11_REVIEW_LAYOUT=0x409ec800ull'], cave=0x40990000, limit=0x409D8000, entry='psm_menu_action'),
    'pixelshift-af': dict(source='z8pixelshift/src/af_unit.c', flags=[f for f in FLAGS if f!='-mgeneral-regs-only']+['-ffp-contract=off'], cave=0x409D8000, limit=0x409DA000, entry='ps8_af_one_batch'),
    'opengate': dict(source='z8opengate/src/d10_hooks.S', flags=['-target','aarch64-none-elf','-x','assembler-with-cpp','-DFULL_OUTPUT=1','-DWITH_Q3=1','-DQ3_STASH_RAM=0xa0ff50000','-DQ3_FINE_TABLE=0x40953000','-DQ3_BASIC_TABLE=0x409533f0','-DOG_TIER_DELTA=0x4000'],
                    asm_sources=('z8opengate/src/d10_hooks.S','z8opengate/src/d5_hooks.S','z8opengate/src/d6_hooks.S','z8opengate/src/d7_hooks.S','z8opengate/src/d8_hooks.S','z8opengate/src/d9_hooks.S','z8opengate/src/menu_repair_hooks.S','z8opengate/src/ui_hooks.S')),
}
SPECS.update({
    'anamorphic':dict(source='z8anamorphic/src/hooks.S', flags=['-target','aarch64-none-elf','-x','assembler-with-cpp'],asm_base=0x40970000,limit=0x40974000,folder='z8anamorphic',asm_sources=('z8anamorphic/src/hooks.S',)),
    'h265':dict(source='z8h265/src/hooks.S', flags=['-target','aarch64-none-elf','-x','assembler-with-cpp'],asm_base=0x40A10000,limit=0x40A12000,folder='z8h265',asm_sources=('z8h265/src/hooks.S',)),
    'log':dict(source='z8log/src/hooks.S', flags=['-target','aarch64-none-elf','-x','assembler-with-cpp'],asm_base=0x40B00000,limit=0x40B08000,folder='z8log',asm_sources=('z8log/src/hooks.S',)),
    'quality':dict(source='z8quality/src/hooks.S', flags=['-target','aarch64-none-elf','-x','assembler-with-cpp'],asm_base=0x40A41000,limit=0x40A50000,folder='z8quality',asm_sources=('z8quality/src/hooks.S',)),
    'video-orientation':dict(source='z8videoorientation/src/hooks.S', flags=['-target','aarch64-none-elf','-x','assembler-with-cpp'],asm_base=0x40A08000,limit=0x40A10000,folder='z8videoorientation',asm_sources=('z8videoorientation/src/hooks.S',)),
    'shared':dict(source='z8patch/src/shared.S', flags=['-target','aarch64-none-elf','-x','assembler-with-cpp'],asm_base=0x40980000,limit=0x40980F00,folder='z8patch/src',asm_sources=('z8patch/src/shared.S',)),
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
    if name=='video-orientation':
        from z8videoorientation.patcher import asm_defines
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


def unit_base(name):
    """Placement base VA of a compiled unit: asm_base for asm units, cave
    for C units, and the opengate code cave (z8patch/linker.py CAVE) for the
    opengate unit (its own linker is based there)."""
    spec = SPECS[name]
    if 'asm_base' in spec:
        return spec['asm_base']
    if 'cave' in spec:
        return spec['cave']
    require(name == 'opengate', 'No placement base for unit: ' + name)
    return OPENGATE_CAVE


def unit_sources(name):
    """Assembly sources whose .global directives register the unit's entry
    symbols; asm units declare their full source set in SPECS asm_sources
    (the opengate unit is the include closure of z8opengate/src, so every
    file in that folder belongs to it)."""
    if 'asm_sources' in SPECS[name]:
        return [ROOT / rel for rel in SPECS[name]['asm_sources']]
    return [ROOT / SPECS[name]['source']]


def assert_asm_sources_declared(declared, directories):
    """A1 completeness: every *.S anywhere under a registered unit's
    source directory tree must be declared in some unit's SPECS
    asm_sources.

    An undeclared source would silently escape the D1 .org scan while
    still reaching the image through .include or a future SPECS edit,
    so the build refuses instead of skipping it.  The sweep is
    recursive (rglob, the folder-keyed source-fingerprint precedent):
    a *.S nested in a subdirectory has no directory shape to hide in,
    and the directory set covers C-unit directories (z8precapture and
    friends) the same way.  Parameterized for tests; the build mount
    goes through unit_asm_sources().
    """
    declared = set(declared)
    for directory in directories:
        for path in sorted(directory.rglob('**/*.S')):
            if path not in declared:
                raise ValueError(
                    'Address coupling: %s is an assembly source under the '
                    'registered unit directory %s but no SPECS entry '
                    'declares it (asm_sources): declare it with the owning '
                    'unit or move it out of the unit directory, otherwise '
                    'it escapes the D1 .org scan' % (path, directory))


def unit_asm_sources():
    """Every assembly source declared by any SPECS unit -- the D1 scan
    list.

    The SPECS registry, not a filesystem glob, owns the enumeration: a
    unit enters the build only through SPECS, so scanning the declared
    sets leaves no escape for sources placed outside z8*/src.  The
    completeness check above runs first, so a source sitting undeclared
    anywhere in a unit directory tree is refused rather than silently
    skipped.
    """
    declared = sorted(ROOT / rel for spec in SPECS.values()
                      for rel in spec.get('asm_sources', ()))
    assert_asm_sources_declared(
        declared,
        sorted({ROOT / Path(spec['source']).parent for spec in SPECS.values()}))
    return declared


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
