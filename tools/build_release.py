#!/usr/bin/env python3
"""Package committed source with the reviewed patch units, and the F LUT download; never reads firmware."""
import argparse,hashlib,json,re,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.check_release import SOURCE_FILES,REPOSITORY_FILES,LUT_FILES,LUT_SUFFIX,MANIFEST,TAG,check_release,check_lut,need
from z8patch.compiled import compile_unit

def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def write_zip(target,prefix,files):
    """Deterministic archive: fixed timestamps and modes, sorted members under one folder."""
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,raw in sorted(files.items()):
            e=zipfile.ZipInfo(prefix+'/'+name,date_time=(2026,1,1,0,0,0));e.create_system=3;e.external_attr=0o100644<<16;e.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(e,raw)
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--tag',required=True)
    ap.add_argument('--compiler',default='clang');ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    need(re.fullmatch(TAG,a.tag),'Invalid release tag');need(not a.output.exists(),'Output directory already exists')
    need(not git('status','--porcelain','--untracked-files=normal').strip(),'Commit source changes before packaging')
    commit=git('rev-parse','HEAD').decode().strip()
    # Every tracked file is reviewed into exactly one list: shipped in the ZIP or kept in the repository.
    need(not set(SOURCE_FILES)&set(REPOSITORY_FILES),'A file is listed both for the toolkit and the repository only')
    need(set(git('ls-tree','-r','--name-only','HEAD').decode().splitlines())==set(SOURCE_FILES)|set(REPOSITORY_FILES),'Tracked source differs from release allowlist')
    subprocess.run([sys.executable,'-B',str(ROOT/'tools/check_repository.py'),'--all'],cwd=ROOT,check=True)
    files={n:git('show','HEAD:'+n) for n in SOURCE_FILES}
    need(all(raw==(ROOT/n).read_bytes() for n,raw in files.items()),'Working tree differs from committed source')
    units=json.loads(files['resources/compiled.json'])['units']
    for name,profile in units.items():
        code,detail=compile_unit(name,a.compiler)
        need(detail==profile,'Compiled unit differs from reviewed bytes/symbols/compiler/source: '+name)
        files[profile['resource']]=code
    record=dict(schema=2,tag=a.tag,source_commit=commit,compiled_units=units,files={n:dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()) for n,raw in sorted(files.items())})
    files[MANIFEST]=(json.dumps(record,indent=2)+'\n').encode()
    a.output.mkdir(parents=True,exist_ok=False);prefix='NikonFirmwarePatch-'+a.tag
    target=a.output/(prefix+'-toolkit.zip')
    write_zip(target,prefix,files)
    verified=check_release(target,commit)
    lut=a.output/(prefix+LUT_SUFFIX+'.zip')
    write_zip(lut,prefix+LUT_SUFFIX,{n:git('show','HEAD:'+source) for n,source in LUT_FILES.items()})
    lut_verified=check_lut(lut)
    with (a.output/'SHA256SUMS.txt').open('x') as f:
        for path,result in ((target,verified),(lut,lut_verified)):f.write(result['archive_sha256']+'  '+path.name+'\n')
    print(json.dumps(dict(toolkit=verified,f_lut=lut_verified),indent=2))
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.CalledProcessError) as e:raise SystemExit('ERROR: '+str(e))
