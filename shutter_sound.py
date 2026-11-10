#!/usr/bin/env python3
"""Build the custom shutter-sound addition on top of selected Nikon Z8 features.

Approach A stacker: the four feature groups compose an equal-length base with
features.build(), the vendored z8shuttersound unit stacks on top of that base, and
stack.pack() repackages the container with the longer module 2. The four-group
recipes, verify.py and patch.py stay untouched. The shutter-sound unit honours its
own --code-source selection; the feature base always uses the reviewed
prebuilt units (matching patch.py's default distribution).
"""
import argparse
import binascii
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from features import FEATURES, build as features_build, compatibility, selected_features  # noqa: E402
from z8prores.package import Package, require, require_official_input, sha  # noqa: E402
from z8prores.patcher import public_words  # noqa: E402
from z8shuttersound import stack  # noqa: E402

STOCK_BYTES = 81807711
VERSION_AT = 0x14EAA90
CODE_VERSION_AT = 0xEB29FC
TAIL_BYTES = 13  # 'Ver.' + eight identity bytes + NUL


def identity(version, tag):
    require(re.fullmatch(r'[0-9]{2}\.[0-9]{2}', version), 'Version must be NN.NN')
    require(re.fullmatch(r'[a-z][0-9]', tag), 'Tag must be a lowercase letter and digit')
    return f'{version}.{tag}'.encode('ascii')


def version_base(stock_eg, version, tag):
    """WAV-only base: stock EG with the three version fields and CRC stamped."""
    ident = identity(version, tag)
    require(len(stock_eg) == STOCK_BYTES, 'Unexpected stock EG length')
    require(stock_eg[VERSION_AT:VERSION_AT + 8] == b'03.11.b0', 'Unexpected stock identity')
    require(stock_eg[-15:-2] == b'Ver.03.11.b0\0', 'Unexpected stock trailer')
    require(stock_eg[CODE_VERSION_AT:CODE_VERSION_AT + 12] == public_words('03.11'), 'Unexpected public version')
    out = bytearray(stock_eg)
    out[CODE_VERSION_AT:CODE_VERSION_AT + 12] = public_words(version)
    out[VERSION_AT:VERSION_AT + 8] = ident
    out[-11:-3] = ident
    out[-2:] = binascii.crc_hqx(out[:-2], 0).to_bytes(2, 'big')
    return bytes(out)


def module_name(version, tag):
    return 'eg2070_' + version.replace('.', '') + tag + '.bi'


def build_stacked(raw, features, version, tag, code_source='prebuilt', llvm=None, keep=None):
    """Return (packet, meta): feature base -> stacked shutter-sound EG -> repacked container."""
    require_official_input(raw)
    require(code_source in ('prebuilt', 'source'), 'Select prebuilt or source for the shutter-sound unit')
    chosen = selected_features(features) if features else []
    package = Package(raw)
    if chosen:
        base, base_report = features_build(package.eg, version, tag, chosen)
        base_kind = 'features'
    else:
        base, base_report = version_base(package.eg, version, tag), None
        base_kind = 'version-stamped stock'
    eg, sound_report = stack.stack(package.eg, base, llvm=llvm or stack.LLVM, keep=keep, code_source=code_source)
    name = module_name(version, tag)
    packet = stack.pack(package, eg, name)
    meta = dict(base_features=chosen, base_kind=base_kind, base_sha256=sha(base), base_report=base_report,
                shutter_sound=sound_report, module_name=name, output_identity=f'{version}.{tag}',
                input_sha256=package.sha256, output_sha256=sha(packet), output_bytes=len(packet),
                payload_sha256=sha(eg), payload_bytes=len(eg))
    return packet, meta


def verify_stacked(original, candidate, features, version, tag, code_source='prebuilt', llvm=None):
    """Independent audit: container readback plus full rebuild from the stock input."""
    require_official_input(original)
    chosen = selected_features(features) if features else []
    ident = identity(version, tag)
    package = Package(original)
    eg = stack.unpack(package, candidate, module_name(version, tag))
    require(len(eg) > STOCK_BYTES, 'Candidate module did not grow beyond stock')
    with tempfile.TemporaryDirectory() as tmp:
        if chosen:
            base, base_report = features_build(package.eg, version, tag, chosen)
        else:
            base, base_report = version_base(package.eg, version, tag), None
        expected, sound_report = stack.stack(package.eg, base, llvm=llvm or stack.LLVM,
                                           keep=Path(tmp) / 'build', code_source=code_source)
    require(eg == expected, 'Stacked EG differs from the independent rebuild')

    # Window audit over the stock prefix: everything outside the declared edits
    # must equal the stock bytes, whatever the manifests claim.
    windows = {(CODE_VERSION_AT, 12), (VERSION_AT, 8), (STOCK_BYTES - 11, 8), (STOCK_BYTES - 2, 2)}
    def as_offset(value):
        return int(value, 16) if isinstance(value, str) else int(value)

    if base_report:
        for row in base_report['edits']:
            windows.add((as_offset(row['offset']), row['bytes']))
    for row in sound_report['patches']:
        windows.add((as_offset(row['offset']), row['bytes']))
    ordered = sorted(windows)
    end = 0
    for offset, size in ordered:
        require(end <= offset and offset + size <= STOCK_BYTES, 'Overlapping or out-of-range patch window')
        require(eg[end:offset] == package.eg[end:offset], 'Unlisted change in preserved stock bytes')
        end = offset + size
    require(eg[end:STOCK_BYTES] == package.eg[end:STOCK_BYTES], 'Unlisted trailing stock change')
    require(eg[VERSION_AT:VERSION_AT + 8] == ident, 'Runtime identity mismatch')
    require(eg[CODE_VERSION_AT:CODE_VERSION_AT + 12] == public_words(version), 'Public identity mismatch')
    require(eg[-15:-2] == b'Ver.' + ident + b'\0', 'Trailer identity mismatch')
    require(eg[STOCK_BYTES - 15:STOCK_BYTES - 2] == b'Ver.' + ident + b'\0', 'Base trailer mismatch')
    return dict(status='PASS', features=chosen, version=version, tag=tag, module_bytes=len(eg),
                shutter_sound_patches=len(sound_report['patches']), base_windows=len(base_report['edits']) if base_report else 0,
                checks=['container roundtrip', 'independent rebuild', 'stock-prefix window audit',
                        'identity fields', 'EG CRC'])


def llvm_folder(value):
    folder = value or os.environ.get('Z8_LLVM_BIN') or stack.LLVM
    require(folder, 'Set --llvm-bin or Z8_LLVM_BIN for the shutter-sound unit')
    return folder


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('firmware', type=Path, help='User-supplied complete Z8 firmware .bin')
    ap.add_argument('--check', action='store_true', help='Read-only input compatibility and integrity check')
    ap.add_argument('--version', help='Output version NN.NN shared by the base and the stacked firmware')
    ap.add_argument('--tag', default='w0', help='Internal revision suffix: lowercase letter plus digit; default w0')
    group = ap.add_mutually_exclusive_group()
    group.add_argument('--features', nargs='+', choices=FEATURES, help='Feature groups for the base; any nonempty subset')
    group.add_argument('--shutter-sound-only', action='store_true', help='Stack the shutter-sound unit on a version-stamped stock base')
    group.add_argument('--interactive', action='store_true', help='Choose feature groups interactively')
    ap.add_argument('--code-source', choices=['prebuilt', 'source'], default='prebuilt',
                    help='Shutter-sound unit: reviewed prebuilt zero-slot bytes (default) or compile with LLVM')
    ap.add_argument('--llvm-bin', help='LLVM bin directory for the shutter-sound unit; also Z8_LLVM_BIN')
    ap.add_argument('--keep', type=Path, help='Directory receiving the shutter-sound build working files')
    ap.add_argument('--output', type=Path, help='New output directory; must not already exist')
    a = ap.parse_args()
    if a.check and (a.output or a.version or a.tag != 'w0' or a.interactive or a.shutter_sound_only or a.keep
                    or a.llvm_bin or a.code_source != 'prebuilt'):
        ap.error('--check cannot be combined with output options')
    if a.interactive:
        labels = ['Framing / 画幅', 'Video quality / 视频品质', 'Log colour / Log 色彩', 'Photo tools / 照片工具']
        print('\n'.join(f'{i}: {name}' for i, name in enumerate(labels, 1)) + '\n5: All / 全选\n0: Shutter sound only / 仅快门声')
        choice = input('Select numbers separated by commas / 用逗号分隔: ').strip()
        parts = [p.strip() for p in choice.split(',')]
        require(parts and len(parts) == len(set(parts)) and all(p in ('0', '1', '2', '3', '4', '5') for p in parts),
                'Select 0-4 or 5 for all')
        if parts == ['5']:
            a.features = list(FEATURES)
        elif parts == ['0']:
            a.shutter_sound_only = True
        else:
            a.features = [FEATURES[int(p) - 1] for p in parts]
    selected = selected_features(a.features) if getattr(a, 'features', None) else ([] if a.shutter_sound_only else None)
    if selected is None and not a.check:
        ap.error('Select --features, --shutter-sound-only or --interactive')
    require(a.firmware.is_file(), 'Input must be a regular firmware file')
    require(a.firmware.stat().st_size == 99051117, 'Unsupported firmware length')
    if not a.check:
        require(a.version and a.output, 'Building requires --version and --output; use --check for read-only inspection')
        require(not a.output.exists(), 'Output directory already exists; use a new directory')
        if not a.keep:
            a.keep = a.output.with_name(a.output.name + '-shutter-sound-build')
    raw = a.firmware.read_bytes()
    require_official_input(raw)
    package = Package(raw)
    if a.check:
        info = dict(status='COMPATIBLE', input_sha256=package.sha256,
                    identity=package.eg[VERSION_AT:VERSION_AT + 8].decode(), modules=package.modules,
                    shutter_sound_unit='prebuilt' if (ROOT / 'resources' / 'shuttersound.bin').is_file() else 'missing')
        if selected:
            profiles, identity = compatibility(package.eg, selected)
            info.update(features=selected, profiles={f: p['id'] for f, p in profiles.items()})
        print(json.dumps(info, indent=2))
        return
    llvm = llvm_folder(a.llvm_bin) if a.code_source == 'source' else (a.llvm_bin or os.environ.get('Z8_LLVM_BIN') or stack.LLVM)
    packet, meta = build_stacked(raw, selected, a.version, a.tag, a.code_source, llvm, a.keep)
    independent = verify_stacked(raw, packet, selected, a.version, a.tag, a.code_source, llvm)
    name = 'Z_8_' + a.version.replace('.', '') + '.bin'
    provenance = dict(source_commit=None, source_tree_clean=None)
    release = ROOT / 'release-manifest.json'
    if release.is_file():
        record = json.loads(release.read_text())
        provenance.update(source_commit=record['source_commit'], release_tag=record['tag'],
                          release_manifest_sha256=sha(release.read_bytes()))
    else:
        try:
            commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
                                             stderr=subprocess.DEVNULL, text=True).strip()
            dirty = subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'],
                                            stderr=subprocess.DEVNULL, text=True)
            provenance.update(source_commit=commit, source_tree_clean=not dirty.strip())
        except (OSError, subprocess.CalledProcessError):
            pass
    report = dict(base_features=meta['base_features'], output_identity=meta['output_identity'],
                  provenance=provenance, status='BUILT_AND_LOCALLY_VERIFIED',
                  input_sha256=meta['input_sha256'], input_filename=a.firmware.name, input_bytes=len(raw),
                  output_sha256=meta['output_sha256'], output_bytes=meta['output_bytes'], output_filename=name,
                  output_eg_sha256=meta['payload_sha256'], input_modules=package.modules,
                  shutter_sound=dict(code_source=a.code_source, module_bytes=meta['payload_bytes'],
                                confirmed_import=meta['shutter_sound']['confirmed_import'],
                                confirmation_retry=meta['shutter_sound']['confirmation_retry'],
                                staged_confirmation=meta['shutter_sound']['staged_confirmation'],
                                patches=len(meta['shutter_sound']['patches']), compiler=meta['shutter_sound']['compiler']),
                  independent_verification=independent,
                  scope='Selected features plus the shutter-sound addition; camera-verified on the v0.4.0-rc.2 four-group prebuilt base')
    if meta['base_report']:
        report['base_details'] = meta['base_report']['details']
        if 'photo-tools' in meta['base_features']:
            report['capture_control'] = dict(control='camera-menu', configuration_required=False,
                                             history_ceiling=30, c15=True, c30=True,
                                             raw_compression=['HE', 'HE-star'], diagnostic_footer=False)
    a.output.mkdir(parents=True, exist_ok=False)
    with (a.output / name).open('xb') as f:
        f.write(packet)
        f.flush()
        os.fsync(f.fileno())
    require(sha((a.output / name).read_bytes()) == report['output_sha256'], 'Output readback mismatch')
    require(sha(a.firmware.read_bytes()) == meta['input_sha256'], 'Input changed during build')
    with (a.output / 'SHA256SUMS.txt').open('x') as f:
        f.write(report['output_sha256'] + ' ' + name + '\n')
    with (a.output / 'manifest.json').open('x') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps(dict(status=report['status'], output=str(a.output / name), sha256=report['output_sha256'],
                          features=meta['base_features'] or ['shutter-sound-only'],
                          output_identity=report['output_identity']), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
