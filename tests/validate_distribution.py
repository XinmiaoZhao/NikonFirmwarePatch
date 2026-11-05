#!/usr/bin/env python3
"""Test pinned loaders and archive rejection; stock fixture stays outside the repository."""
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from z8patch.compiled import load
from tools.check_release import CODE_FILES,MANIFEST,check_release

def need(ok,message):
    if not ok:raise RuntimeError(message)
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--stock',type=Path);ap.add_argument('--archive',type=Path)
    ap.add_argument('--archive-only',action='store_true');ap.add_argument('--report',type=Path,required=True);a=ap.parse_args()
    need(not a.report.exists(),'Report exists');need(a.archive if a.archive_only else a.stock,'Provide stock or archive-only')
    rows=[];failures=[]
    def reject(name,fn):
        try:fn()
        except (ValueError,KeyError,zipfile.BadZipFile):rows.append(dict(test=name,result='REJECTED'))
        else:raise RuntimeError('Accepted negative control: '+name)
    try:
      with tempfile.TemporaryDirectory(prefix='nikon-distribution-') as folder:
        temp=Path(folder)
        if not a.archive_only:
            # Clone source only into an isolated test tree, excluding all full firmware and runtimes.
            from tools.check_release import SOURCE_FILES
            isolated=temp/'toolkit'
            for n in SOURCE_FILES:
                target=isolated/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/n).read_bytes())
            units=json.loads((ROOT/'resources/compiled.json').read_text())['units']
            with patch('z8patch.compiled.ROOT',isolated):
                for name,u in units.items():
                    path=isolated/u['resource']
                    reject(name+' missing asset, no fallback',lambda:load(name))
                    path.write_bytes(b'x');reject(name+' truncated asset',lambda:load(name))
                    raw=(ROOT/u['resource']).read_bytes();path.write_bytes(bytes([raw[0]^1])+raw[1:])
                    reject(name+' corrupt asset',lambda:load(name));path.unlink()
            out=temp/'missing-output'
            cmd=[sys.executable,'-B',str(isolated/'patch.py'),str(a.stock.resolve()),'--features','framing','video-quality','log-colour','photo-tools','--version','00.00','--tag','t0','--output',str(out)]
            result=subprocess.run(cmd,capture_output=True,text=True,env=dict(os.environ,PATH=''))
            need(result.returncode!=0 and 'Precompiled patch missing' in result.stderr and not out.exists(),'Missing prebuilt must stop CLI before output')
            rows.append(dict(test='missing asset CLI no compiler/no output',result='PASS'))
            # Compile from source without any prebuilt asset; exact code/symbol fingerprints are checked by load().
            with patch('z8patch.compiled.ROOT',isolated):
                for name in units:
                    code,_=load(name,'source','/usr/bin/clang')
                    need(code==(ROOT/units[name]['resource']).read_bytes(),'Source-only byte mismatch')
                    rows.append(dict(test=name+' source checkout without assets',result='PASS'))
        if a.archive:
            rows.append(dict(test='exact archive',**check_release(a.archive)))
            with zipfile.ZipFile(a.archive) as archive:members=[(e,archive.read(e)) for e in archive.infolist()]
            prefix=members[0][0].filename.split('/')[0];bad=temp/'bad.zip'
            def write(entries):
                with zipfile.ZipFile(bad,'w') as archive:
                    for e,raw in entries:archive.writestr(e,raw)
            write(members+[(prefix+'/Z_8_0311.bin',b'excluded')]);reject('extra firmware',lambda:check_release(bad))
            write(members[:-1]);reject('missing member',lambda:check_release(bad))
            write(members+[members[0]]);reject('duplicate member',lambda:check_release(bad))
            for code in CODE_FILES:
                altered=[(e,bytes([raw[0]^1])+raw[1:] if e.filename==prefix+'/'+code else raw) for e,raw in members]
                write(altered);reject('damaged '+code,lambda:check_release(bad))
                # A self-consistent archive manifest must not redefine reviewed machine code.
                def reseal(e,raw):
                    if e.filename==prefix+'/'+MANIFEST:
                        record=json.loads(raw)
                        newraw=next(r for i,r in altered if i.filename==prefix+'/'+code)
                        record['files'][code]['sha256']=hashlib.sha256(newraw).hexdigest()
                        return json.dumps(record).encode()
                    return raw
                write([(e,reseal(e,raw)) for e,raw in altered]);reject('resealed changed '+code,lambda:check_release(bad))
            reject('wrong source commit',lambda:check_release(a.archive,'0'*40))
    except Exception as e:
        failures.append(str(e));raise
    finally:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps(dict(status='FAIL' if failures else 'PASS',tests=rows,failures=failures,checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
    print('PASS:',len(rows),'distribution checks')
if __name__=='__main__':main()
