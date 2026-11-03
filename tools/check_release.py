#!/usr/bin/env python3
"""Independently validate a toolkit ZIP; never imports a firmware builder/compiler."""
import argparse,hashlib,json,re,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
# Reviewed explicit allowlist. Original firmware, media, runtimes and arbitrary files have no entry.
SOURCE_FILES=(
    '.gitattributes',
    '.github/workflows/host-checks.yml',
    '.githooks/pre-commit',
    '.gitignore',
    'CHANGELOG.md',
    'LICENSE',
    'NOTICE.md',
    'README.md',
    'docs/images/prores-quality-options.png',
    'docs/images/prores-quality-value.png',
    'docs/images/pixelshift-groups.png',
    'docs/images/nraw-quality-tiers.png',
    'docs/images/opengate-frame-rates.png',
    'docs/known-issues.md',
    'docs/locked-banks.md',
    'docs/opengate-nraw.md',
    'docs/pixelshift.md',
    'docs/prores.md',
    'docs/raw-precapture.md',
    'docs/releases.md',
    'docs/stop-file.md',
    'docs/validation-summary.json',
    'docs/validation-v0.2.0.md',
    'docs/validation.md',
    'features.py',
    'patch.py',
    'requirements.txt',
    'resources/combinations.json',
    'resources/compiled.json',
    'resources/input.json',
    'resources/precapture.json',
    'resources/profile.json',
    'tests/test_compiled_paths.py',
    'tests/validate_prebuilt_cli.py',
    'tests/validate.py',
    'tests/validate_combinations.py',
    'tests/validate_distribution.py',
    'tests/validate_features.py',
    'tools/build_release.py',
    'tools/check_release.py',
    'tools/check_repository.py',
    'tools/review_recipes.py',
    'verify.py',
    'z8lockbank/__init__.py',
    'z8lockbank/patcher.py',
    'z8opengate/__init__.py',
    'z8opengate/a64x.py',
    'z8opengate/imenu.py',
    'z8opengate/linker.py',
    'z8opengate/patcher.py',
    'z8opengate/quality.py',
    'z8opengate/sites.py',
    'z8opengate/src/d10_hooks.S',
    'z8opengate/src/d5_hooks.S',
    'z8opengate/src/d6_hooks.S',
    'z8opengate/src/d7_hooks.S',
    'z8opengate/src/d8_hooks.S',
    'z8opengate/src/d9_hooks.S',
    'z8opengate/src/menu_repair_hooks.S',
    'z8opengate/src/ui_hooks.S',
    'z8patch/__init__.py',
    'z8patch/compiled.py',
    'z8patch/linker.py',
    'z8patch/shared.py',
    'z8pixelshift/__init__.py',
    'z8pixelshift/patcher.py',
    'z8pixelshift/src/af_unit.c',
    'z8pixelshift/src/af_window.c',
    'z8pixelshift/src/af_window.h',
    'z8pixelshift/src/afrow.c',
    'z8pixelshift/src/afrow.h',
    'z8pixelshift/src/afrow_fma_a64.c',
    'z8pixelshift/src/browser.c',
    'z8pixelshift/src/browser.h',
    'z8pixelshift/src/browser_fw.inc',
    'z8pixelshift/src/crc32_slice8.inc',
    'z8pixelshift/src/firmware.c',
    'z8pixelshift/src/group.c',
    'z8pixelshift/src/group.h',
    'z8pixelshift/src/io_pipe.c',
    'z8pixelshift/src/io_pipe.h',
    'z8pixelshift/src/job.c',
    'z8pixelshift/src/job.h',
    'z8pixelshift/src/nef.c',
    'z8pixelshift/src/nef.h',
    'z8pixelshift/src/nefx.c',
    'z8pixelshift/src/nefx.h',
    'z8pixelshift/src/ps8.c',
    'z8pixelshift/src/psm.c',
    'z8pixelshift/src/psm.h',
    'z8pixelshift/src/thumbnail.c',
    'z8pixelshift/src/thumbnail.h',
    'z8pixelshift/src/ui_strings.h',
    'z8precapture/__init__.py',
    'z8precapture/crc32_table.inc',
    'z8precapture/firmware.c',
    'z8precapture/linker.py',
    'z8precapture/patcher.py',
    'z8prores/__init__.py',
    'z8prores/a64.py',
    'z8prores/back_half.py',
    'z8prores/layout.py',
    'z8prores/menu.py',
    'z8prores/package.py',
    'z8prores/patcher.py',
)
CODE_FILES=('resources/precapture.bin','resources/pixelshift.bin','resources/pixelshift-af.bin','resources/opengate.bin')
MANIFEST='release-manifest.json'
TAG=r'v[0-9]+\.[0-9]+\.[0-9]+(?:-(?:rc\.[1-9][0-9]*|r[1-9][0-9]*))?'
def need(ok,message):
    if not ok:raise ValueError(message)
def digest(data):return hashlib.sha256(data).hexdigest()

def check_release(path,expected_commit=None):
    need(path.stat().st_size<=8*1024*1024,'Toolkit archive exceeds size limit')
    with zipfile.ZipFile(path) as archive:
        entries=archive.infolist();names=[e.filename for e in entries]
        need(names and len(names)==len(set(names)),'Duplicate or missing ZIP members')
        prefix=names[0].split('/')[0]
        need(re.fullmatch('NikonFirmwarePatch-'+TAG,prefix),'Unexpected toolkit folder')
        need(set(names)=={prefix+'/'+n for n in (*SOURCE_FILES,*CODE_FILES,MANIFEST)},'Release member allowlist mismatch')
        need(sum(e.file_size for e in entries)<=8*1024*1024,'Expanded toolkit exceeds size limit')
        need(all((e.external_attr>>16)&0o170000==0o100000 for e in entries),'Non-regular ZIP member')
        files={n:archive.read(prefix+'/'+n) for n in (*SOURCE_FILES,*CODE_FILES)}
        record=json.loads(archive.read(prefix+'/'+MANIFEST))
    need(record['schema']==2 and record['tag']==prefix.removeprefix('NikonFirmwarePatch-'),'Release identity mismatch')
    need(re.fullmatch('[0-9a-f]{40}',record['source_commit']),'Invalid source commit')
    need(expected_commit is None or record['source_commit']==expected_commit,'Unexpected source commit')
    need(set(record['files'])==set(files),'Manifest member mismatch')
    for name,raw in files.items():
        need(record['files'][name]=={'bytes':len(raw),'sha256':digest(raw)},'Member digest mismatch: '+name)
    for name in SOURCE_FILES:
        need(files[name]==(ROOT/name).read_bytes(),'Source differs from this checkout: '+name)
    units=json.loads((ROOT/'resources/compiled.json').read_text())['units']
    need(set(CODE_FILES)=={u['resource'] for u in units.values()},'Code allowlist differs')
    need(record['compiled_units']==units,'Compiler/source provenance mismatch')
    for name,unit in units.items():
        raw=files[unit['resource']]
        need(len(raw)==unit['bytes'] and digest(raw)==unit['sha256'],'Unreviewed machine code: '+name)
    return dict(status='PASS',tag=record['tag'],source_commit=record['source_commit'],source_files=len(SOURCE_FILES),binary_files=list(CODE_FILES),code_bytes=sum(len(files[n]) for n in CODE_FILES),archive_sha256=digest(path.read_bytes()),firmware_included=False,scope='Archive members, source identity and pinned patch bytes')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('archive',type=Path);ap.add_argument('--commit');a=ap.parse_args()
    print(json.dumps(check_release(a.archive,a.commit),indent=2))
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,zipfile.BadZipFile) as e:raise SystemExit('ERROR: '+str(e))
