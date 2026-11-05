#!/usr/bin/env python3
"""Run prebuilt CLI checks against a caller-supplied stock file; delete temporary outputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--all-version', default='00.02', help='Full-selection firmware identity to reproduce')
    parser.add_argument('--all-sha256', help='Expected SHA-256 of the reference full-selection package')
    args = parser.parse_args()
    if args.report.exists():
        raise ValueError('Report already exists')
    stock = args.stock.resolve()
    expected = json.loads((ROOT / 'resources/input.json').read_text(encoding='utf-8'))
    if stock.stat().st_size != expected['bytes'] or digest(stock) != expected['sha256']:
        raise ValueError('Stock fixture does not match the supported input')
    env = dict(os.environ, PATH='', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
    report = {'status': 'FAIL', 'python': sys.version, 'platform': platform.platform(),
              'input_sha256': expected['sha256'], 'compiler_on_path': False, 'tests': [],
              'scope': 'Real host prebuilt CLI and independent verification; no camera operations'}
    release = ROOT / 'release-manifest.json'
    if release.exists():
        report['release_source_commit'] = json.loads(release.read_text(encoding='utf-8'))['source_commit']

    def run(*arguments):
        result = subprocess.run([sys.executable, '-B', *map(str, arguments)], cwd=ROOT,
                                env=env, capture_output=True, text=True, encoding='utf-8')
        if result.returncode:
            raise RuntimeError(result.stderr[-6000:] or result.stdout[-6000:])
        return result.stdout

    try:
        with tempfile.TemporaryDirectory(prefix='nikon-prebuilt-cli-') as directory:
            for label, features, version in (
                    ('video-photo', ['video-quality', 'photo-tools'], '00.01'),
                    ('all', ['framing', 'video-quality', 'log-colour', 'photo-tools'], args.all_version)):
                check = json.loads(run(ROOT / 'patch.py', stock, '--features', *features, '--check'))
                if check['status'] != 'COMPATIBLE':
                    raise ValueError('Input compatibility check failed')
                output = Path(directory) / label
                run(ROOT / 'patch.py', stock, '--features', *features, '--version', version,
                    '--tag', 'p0', '--output', output)
                firmware = output / ('Z_8_' + version.replace('.', '') + '.bin')
                verified_text = run(ROOT / 'verify.py', stock, firmware, '--features', *features,
                                    '--version', version, '--tag', 'p0')
                verified = json.loads(verified_text)
                if verified['status'] != 'PASS':
                    raise ValueError('Independent verification failed')
                manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
                if manifest['output_sha256'] != digest(firmware):
                    raise ValueError('Output readback mismatch')
                if label == 'all' and args.all_sha256 and manifest['output_sha256'] != args.all_sha256:
                    raise ValueError('Full-selection firmware differs from the supplied regression reference')
                report['tests'].append({'name': label, 'features': features, 'identity': version + '.p0', 'status': 'PASS',
                                        'bytes': firmware.stat().st_size,
                                        'sha256': digest(firmware), 'independent_verification': 'PASS'})
            if digest(stock) != expected['sha256']:
                raise ValueError('Stock fixture changed')
        report.update(status='PASS', temporary_outputs_removed=True)
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
