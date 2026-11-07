#!/usr/bin/env python3
"""Card WAV stacked builds and integrity failures using an external stock fixture."""
import argparse
import binascii
import itertools
import json
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from features import FEATURES  # noqa: E402
from z8prores.package import Package, require_official_input, sha  # noqa: E402
from card_wav import build_stacked, verify_stacked  # noqa: E402

STOCK_LEN = 81807711


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def reject(name, fn):
    try:
        fn()
    except (ValueError, KeyError, RuntimeError, AssertionError):
        return dict(test=name, result='REJECTED')
    raise RuntimeError('Accepted negative control: ' + name)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stock', type=Path, required=True)
    ap.add_argument('--report', type=Path, required=True)
    ap.add_argument('--llvm-bin', default='/home/gjk/git-repos/Nikon_Z8_RE/tools/llvm-19.1.7/bin')
    a = ap.parse_args()
    need(not a.report.exists(), 'Report exists')
    original = a.stock.read_bytes()
    require_official_input(original)
    pkg = Package(original)
    rows = []

    with tempfile.TemporaryDirectory() as tmp:
        keep = Path(tmp) / 'keep'
        from z8cardwav.stack import unpack

        # Full matrix: 15 feature combinations plus WAV, prebuilt unit.
        import time
        for bits in itertools.product((False, True), repeat=4):
            names = [f for f, on in zip(FEATURES, bits) if on]
            if not names:
                continue
            t0 = time.time()
            mpacket, mmeta = build_stacked(original, names, '00.00', 't0',
                                           code_source='prebuilt', llvm=a.llvm_bin, keep=None)
            mverified = verify_stacked(original, mpacket, names, '00.00', 't0',
                                       code_source='prebuilt', llvm=a.llvm_bin)
            need(mverified['status'] == 'PASS', 'Stacked verification failed for ' + '+'.join(names))
            need(mmeta['base_features'] == names and mmeta['card_wav']['confirmed_import'], 'Meta mismatch')
            need(mmeta['card_wav']['module_bytes'] > STOCK_LEN, 'Module did not grow')
            rows.append(dict(test='+'.join(names) + '+card-wav', result='PASS',
                             payload_sha256=mmeta['payload_sha256'], package_sha256=sha(mpacket)))
            print('+'.join(names) + '+card-wav: PASS (%.1fs)' % (time.time() - t0), flush=True)

        # Detailed controls against the photo-tools packet.
        packet, meta = build_stacked(original, ['photo-tools'], '00.00', 't0',
                                     code_source='prebuilt', llvm=a.llvm_bin, keep=keep / 'a')
        verified = verify_stacked(original, packet, ['photo-tools'], '00.00', 't0',
                                  code_source='prebuilt', llvm=a.llvm_bin)
        need(verified['status'] == 'PASS', 'Stacked verification failed')
        stacked_eg = unpack(pkg, packet, 'eg2070_0000t0.bi')
        stacked_len = len(stacked_eg)
        need(stacked_len > STOCK_LEN, 'Stacked module did not grow')
        need(meta['card_wav']['module_bytes'] > STOCK_LEN, 'Reported module length did not grow')
        need(meta['base_features'] == ['photo-tools'] and meta['card_wav']['confirmed_import'], 'Meta mismatch')
        rows.append(dict(test='photo-tools+card-wav prebuilt (detailed)', result='PASS',
                         payload_sha256=sha(stacked_eg), package_sha256=sha(packet)))
        print('photo-tools+card-wav: PASS', flush=True)

        # WAV-only build on a version-stamped stock base.
        wav_only, wav_meta = build_stacked(original, [], '00.00', 't0',
                                           code_source='prebuilt', llvm=a.llvm_bin, keep=keep / 'b')
        wav_verified = verify_stacked(original, wav_only, [], '00.00', 't0',
                                      code_source='prebuilt', llvm=a.llvm_bin)
        need(wav_verified['status'] == 'PASS', 'WAV-only verification failed')
        need(wav_meta['base_features'] == [], 'WAV-only base features mismatch')
        rows.append(dict(test='card-wav-only prebuilt', result='PASS', package_sha256=sha(wav_only)))
        print('card-wav-only: PASS', flush=True)

        # Source/prebuilt parity for all features plus WAV under the pinned LLVM.
        t0 = time.time()
        src_packet, _ = build_stacked(original, list(FEATURES), '00.00', 't0',
                                      code_source='source', llvm=a.llvm_bin, keep=keep / 'src')
        pre_packet, _ = build_stacked(original, list(FEATURES), '00.00', 't0',
                                      code_source='prebuilt', llvm=a.llvm_bin, keep=keep / 'pre')
        need(src_packet == pre_packet, 'Source/prebuilt stacked package mismatch')
        rows.append(dict(test='all features+card-wav source/prebuilt equivalence', result='PASS'))
        print('all features+card-wav source/prebuilt equivalence: PASS (%.1fs)' % (time.time() - t0), flush=True)

        # Negative controls.
        rows.append(reject('patched input', lambda: build_stacked(packet, ['photo-tools'], '00.00', 't0')))
        rows.append(reject('wrong version', lambda: verify_stacked(original, packet, ['photo-tools'], '00.01', 't0',
                                                                   code_source='prebuilt', llvm=a.llvm_bin)))
        rows.append(reject('wrong tag', lambda: verify_stacked(original, packet, ['photo-tools'], '00.00', 't1',
                                                               code_source='prebuilt', llvm=a.llvm_bin)))
        rows.append(reject('wrong features', lambda: verify_stacked(original, packet, ['framing'], '00.00', 't0',
                                                                    code_source='prebuilt', llvm=a.llvm_bin)))
        rows.append(reject('unknown feature', lambda: build_stacked(original, ['not-a-feature'], '00.00', 't0')))

        def tampered_append():
            bad = bytearray(packet)
            # Flip a byte inside the appended native-code region near the module tail.
            eg_len = len(unpack(pkg, packet, 'eg2070_0000t0.bi'))
            at = 581844 + eg_len - 64
            bad[at] ^= 1
            verify_stacked(original, bytes(bad), ['photo-tools'], '00.00', 't0',
                           code_source='prebuilt', llvm=a.llvm_bin)

        rows.append(reject('tampered append byte', tampered_append))

        def tampered_window():
            bad = bytearray(packet)
            # A stock-prefix byte far from any declared window (menu text area padding).
            bad[581844 + 0x1400000] ^= 1
            verify_stacked(original, bytes(bad), ['photo-tools'], '00.00', 't0',
                           code_source='prebuilt', llvm=a.llvm_bin)

        rows.append(reject('tampered preserved byte', tampered_window))

        def tampered_other_module():
            bad = bytearray(packet)
            bad[700000] ^= 1  # Inside a non-EG module.
            verify_stacked(original, bytes(bad), ['photo-tools'], '00.00', 't0',
                           code_source='prebuilt', llvm=a.llvm_bin)

        rows.append(reject('tampered other module', tampered_other_module))

        def grown_base():
            # A feature base longer than stock must be refused by the stacker itself.
            import z8cardwav.stack as zs
            long_base = Package(packet).eg + b'\x00'
            zs.stack(pkg.eg, long_base, llvm=a.llvm_bin, code_source='prebuilt')

        rows.append(reject('non-stock-length base', grown_base))

        # CLI end-to-end for one selection.
        import subprocess
        out = Path(tmp) / 'cli'
        r = subprocess.run([sys.executable, '-B', str(ROOT / 'card_wav.py'), str(a.stock),
                            '--features', 'photo-tools', '--version', '00.00', '--tag', 't0',
                            '--output', str(out)], capture_output=True, text=True)
        need(r.returncode == 0, 'CLI failed: ' + r.stderr[-400:])
        got = (out / 'Z_8_0000.bin').read_bytes()
        need(got == packet, 'CLI output differs from library build')
        need({p.name for p in out.iterdir()} == {'Z_8_0000.bin', 'manifest.json', 'SHA256SUMS.txt'},
              'Unexpected CLI output members')
        rows.append(dict(test='CLI photo-tools+card-wav', result='PASS'))
        print('CLI photo-tools+card-wav: PASS', flush=True)

    failures = [row for row in rows if row.get('result') not in ('PASS', 'REJECTED')]
    need(not failures, 'Unexpected results: ' + json.dumps(failures))
    a.report.write_text(json.dumps(dict(status='PASS', rows=rows), indent=2) + '\n', encoding='utf-8')
    print('ALL PASS: %d rows' % len(rows), flush=True)


if __name__ == '__main__':
    main()
