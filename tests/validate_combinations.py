#!/usr/bin/env python3
"""All feature selections and integrity failures using an external stock fixture."""
import argparse,binascii,itertools,json,os,subprocess,sys,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from features import FEATURES,build,compatibility,selected_features
from z8prores.package import Package,require_official_input,sha
from verify import verify_pair

def need(ok,message):
    if not ok:raise RuntimeError(message)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--stock',type=Path,required=True)
    ap.add_argument('--report',type=Path,required=True);ap.add_argument('--compiler',default='/usr/bin/clang');a=ap.parse_args()
    need(not a.report.exists(),'Report exists')
    original=a.stock.read_bytes();require_official_input(original);pkg=Package(original)
    rows=[];failures=[]
    def reject(name,fn):
        try:fn()
        except (ValueError,KeyError):rows.append(dict(test=name,result='REJECTED'))
        else:raise RuntimeError('Accepted negative control: '+name)
    try:
        for bits in itertools.product((False,True),repeat=len(FEATURES)):
            names=[f for f,on in zip(FEATURES,bits) if on]
            if not names:continue
            eg,meta=build(pkg.eg,'00.00','t0',names)
            packet,_=pkg.replace_eg(eg,'eg2070_0000t0.bi')
            verified=verify_pair(original,packet,names,expected_version='00.00',expected_tag='t0')
            auto=verify_pair(original,packet)
            need(set(auto['features'])==set(names) and not auto['requested_features_checked'],'Automatic detection')
            need(meta['features']==names and verified['status']=='PASS','Selection mismatch')
            rows.append(dict(test='+'.join(names),result='PASS',payload_sha256=sha(eg),package_sha256=sha(packet)))
            print('+'.join(names)+': PASS',flush=True)
            wrong=[f for f in FEATURES if f not in names] or ['prores']
            reject('+'.join(names)+' wrong feature claim',lambda:verify_pair(original,packet,wrong))
        # Last iteration is all features. Source mode must give the same bytes.
        source,_=build(pkg.eg,'00.00','t0',list(FEATURES),a.compiler,'source')
        need(source==eg,'Source/prebuilt mismatch')
        rows.append(dict(test='all features source/prebuilt equivalence',result='PASS',payload_sha256=sha(source)))
        reject('empty selection',lambda:selected_features([]))
        reject('duplicate selection',lambda:selected_features(['pixelshift','pixelshift']))
        reject('unknown selection',lambda:selected_features(['unknown']))
        reject('patched input',lambda:compatibility(eg,list(FEATURES)))
        reject('wrong version',lambda:verify_pair(original,packet,list(FEATURES),expected_version='00.01',expected_tag='t0'))
        reject('wrong tag',lambda:verify_pair(original,packet,list(FEATURES),expected_version='00.00',expected_tag='t1'))
        reject('tag without version',lambda:verify_pair(original,packet,list(FEATURES),expected_tag='t0'))
        for name,at in [('unrelated data',0x2400000),('pre-capture code',0x890010),('shared strings',0x770010),('shared bank',0x820000),('D10 hook',0x62E150),('PS11 callback',0x4BF1670),('locked-bank routine',0x75F904),('locked-bank custom gate',0xF7E0A8)]:
            bad=bytearray(eg);bad[at]^=1;bad[-2:]=binascii.crc_hqx(bad[:-2],0).to_bytes(2,'big')
            damaged,_=pkg.replace_eg(bytes(bad),'eg2070_0000t0.bi')
            reject('valid checksums with '+name+' changed',lambda:verify_pair(original,damaged,list(FEATURES)))
        with tempfile.TemporaryDirectory(prefix='nikon-combinations-') as folder:
            temp=Path(folder);out=temp/'cli'
            cmd=[sys.executable,'-B',str(ROOT/'patch.py'),str(a.stock.resolve()),'--features',*FEATURES,'--version','00.00','--tag','t0','--output',str(out)]
            r=subprocess.run(cmd,capture_output=True,text=True,env=dict(os.environ,PATH=''))
            need(r.returncode==0,r.stderr)
            got=(out/'Z_8_0000.bin').read_bytes();need(got==packet,'CLI output differs')
            need({p.name for p in out.iterdir()}=={'Z_8_0000.bin','manifest.json','SHA256SUMS.txt'},'Unexpected CLI output')
            manifest=json.loads((out/'manifest.json').read_text())
            need(not manifest['capture_control']['diagnostic_footer'] and not manifest['capture_control']['configuration_required'],'Public capture options')
            r=subprocess.run(cmd,capture_output=True,text=True)
            need(r.returncode!=0 and (out/'Z_8_0000.bin').read_bytes()==got,'Existing output overwritten')
            rows.append(dict(test='CLI prebuilt with empty PATH; readback; exclusive output',result='PASS'))
            invalid=temp/'wrong.bin';invalid.write_bytes(original[:-1]+bytes([original[-1]^1]))
            cmd=[sys.executable,'-O',str(ROOT/'patch.py'),str(invalid),'--features','prores','--version','00.00','--output',str(temp/'rejected')]
            r=subprocess.run(cmd,capture_output=True,text=True)
            need(r.returncode!=0 and not (temp/'rejected').exists(),'Optimized Python skipped input guard')
            rows.append(dict(test='input guard under python -O; no output',result='PASS'))
    except Exception as exc:
        failures.append(str(exc));raise
    finally:
        a.report.write_text(json.dumps(dict(status='FAIL' if failures else 'PASS',scope=f'{2**len(FEATURES)-1} offline build/envelope checks and explicit negative controls; no camera or CPU execution',tests=rows,failures=failures,checker_sha256=sha(Path(__file__).read_bytes()),input_sha256=sha(original)),indent=2)+'\n')

if __name__=='__main__':main()
