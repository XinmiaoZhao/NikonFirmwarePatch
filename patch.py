#!/usr/bin/env python3
"""Build selected experimental Nikon Z8 features from a user-supplied update package."""
import argparse
import json
import os
from pathlib import Path
import sys
import subprocess

sys.dont_write_bytecode = True
from z8prores.package import Package, PACKAGE_BYTES, RESOURCES, require, require_official_input, sha
from features import build, compatibility, FEATURES


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('firmware', type=Path, help='User-supplied complete Z8 firmware .bin')
    ap.add_argument('--check', action='store_true', help='Read-only input compatibility and integrity check')
    ap.add_argument('--version', help='Output version NN.NN; choose a distinct identity for a different feature set')
    ap.add_argument('--tag', default='p0', help='Internal revision suffix: lowercase letter plus digit; default p0')
    group = ap.add_mutually_exclusive_group()
    group.add_argument('--features', nargs='+', choices=FEATURES, help='Any nonempty subset of the features; default prores')
    group.add_argument('--interactive', action='store_true', help='Choose one or more of the features')
    ap.add_argument('--code-source', choices=['prebuilt', 'source'], default='prebuilt',
                    help='Native patch code: reviewed prebuilt Release bytes (default), or explicitly compile from source')
    ap.add_argument('--compiler', help='Clang executable; requires --code-source source; default clang')
    ap.add_argument('--output', type=Path, help='New output directory; must not already exist')
    a = ap.parse_args()
    if a.compiler and a.code_source != 'source':
        ap.error('--compiler requires --code-source source')
    if not a.check and (not a.version or not a.output):
        ap.error('Building requires --version and --output; use --check for read-only inspection')
    if a.check and (a.output or a.version or a.tag != 'p0' or a.interactive or a.compiler or a.code_source != 'prebuilt'):
        ap.error('--check cannot be combined with output options')
    if a.interactive:
        # 1-5 keep their v0.3.0 meanings; the unreviewed prototype is only ever an explicit extra choice.
        print('1: ProRes quality / ProRes 画质\n2: RAW pre-capture / RAW 预拍摄\n3: Pixel shift merge / 像素偏移合成\n4: Open gate + N-RAW quality / 开放门＋N-RAW 四档\n5: All reviewed features (1-4) / 全选已审核功能（1-4）\n6: Locked menu banks (prototype) / 锁定菜单库（原型）')
        choice=input('Select numbers separated by commas / 用逗号分隔 [1,2,3,4 or 5; add 6 for the prototype]: ').strip()
        parts=[v.strip() for v in choice.split(',')]
        reviewed=[f for f in FEATURES if f!='locked-banks']
        base=[p for p in parts if p!='6']
        require(parts and len(parts)==len(set(parts)) and (base==['5'] or all(p in ('1','2','3','4') for p in base)),
                'Select 1,2,3,4 or 5 for all reviewed features; add 6 for locked banks')
        a.features=(reviewed if base==['5'] else [reviewed[int(p)-1] for p in base])+(['locked-banks'] if '6' in parts else [])
    selected = a.features or ['prores']
    require(a.firmware.is_file(), 'Input must be a regular firmware file')
    require(a.firmware.stat().st_size == PACKAGE_BYTES, 'Unsupported firmware length')
    if not a.check:
        require(not a.output.exists(), 'Output directory already exists; use a new directory')
    data = a.firmware.read_bytes()
    require_official_input(data)
    package = Package(data)
    profiles, identity = compatibility(package.eg, selected)
    if a.check:
        print(json.dumps(dict(status='COMPATIBLE', input_sha256=package.sha256,
                              identity=identity, features=selected,
                              profiles={f:p['id'] for f,p in profiles.items()}, modules=package.modules), indent=2))
        return
    eg, report = build(package.eg, a.version, a.tag, selected, a.compiler or 'clang', a.code_source)
    module_name = 'eg2070_' + a.version.replace('.', '') + a.tag + '.bi'
    packet, checked = package.replace_eg(eg, module_name)
    name = 'Z_8_' + a.version.replace('.', '') + '.bin'
    from verify import verify_pair
    independent = verify_pair(data, packet, selected, expected_version=a.version, expected_tag=a.tag)
    root=Path(__file__).resolve().parent
    release=root/'release-manifest.json'
    provenance={'source_commit':None, 'source_tree_clean':None}
    if release.is_file():
        record=json.loads(release.read_text())
        provenance.update(source_commit=record['source_commit'], release_tag=record['tag'], release_manifest_sha256=sha(release.read_bytes()))
    else:
        try:
            commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],stderr=subprocess.DEVNULL,text=True).strip()
            dirty=subprocess.check_output(['git','-C',str(root),'status','--porcelain'],stderr=subprocess.DEVNULL,text=True)
            provenance.update(source_commit=commit,source_tree_clean=not dirty.strip())
        except (OSError,subprocess.CalledProcessError):
            pass
    report.update(provenance=provenance, status='BUILT_AND_LOCALLY_VERIFIED', input_sha256=package.sha256,
                  input_filename=a.firmware.name, input_bytes=len(data), output_sha256=sha(packet),
                  output_bytes=len(packet), output_filename=name, output_eg_sha256=sha(eg),
                  input_modules=package.modules, output_modules=checked.modules,
                  source_hashes={str(p.relative_to(Path(__file__).resolve().parent)): sha(p.read_bytes())
                                 for p in sorted(Path(__file__).resolve().parent.rglob('*'))
                                 if p.is_file() and p.suffix in ('.py','.c','.h','.inc','.S','.json')
                                 and not any(x in p.relative_to(Path(__file__).resolve().parent).parts for x in ('.git','build','local_data','.venv','venv','__pycache__'))},
                  independent_verification=independent,
                  scope='Selected features plus their declared shared resources, identity and checksums only; this newly generated combination requires camera testing')
    if 'precapture' in selected:
        report['capture_control'] = dict(control='camera-menu', configuration_required=False,
                                        history_ceiling=30, c15=True, c30=True,
                                        raw_compression=['HE', 'HE-star'],
                                        diagnostic_footer=False, budget_us=1500000, space_refusal_fallback='stock JPEG only', remaining_count='NEF-aware plus ordinary JPEG grade/star estimate for eligible FX/L frames; release admission/overflow still use stock JPEG plan')
    # Create only after validation. Exclusive creation never replaces input or an earlier build.
    # On I/O failure the directory is kept, without a successful manifest, for inspection.
    a.output.mkdir(parents=True, exist_ok=False)
    with (a.output / name).open('xb') as f:
        f.write(packet)
        f.flush()
        os.fsync(f.fileno())
    require(sha((a.output / name).read_bytes()) == report['output_sha256'], 'Output readback mismatch')
    require(sha(a.firmware.read_bytes()) == package.sha256, 'Input changed during build')
    with (a.output / 'SHA256SUMS.txt').open('x') as f:
        f.write(report['output_sha256'] + '  ' + name + '\n')
    with (a.output / 'manifest.json').open('x') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps(dict(status=report['status'], output=str(a.output / name), sha256=report['output_sha256'],
                          features=selected, input_identity=identity, output_identity=report['output_identity']), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, ImportError, EOFError) as e:
        raise SystemExit('ERROR: ' + str(e))
