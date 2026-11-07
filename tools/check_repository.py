#!/usr/bin/env python3
"""Check index content without printing potential credential values."""
import argparse
import hashlib
import pathlib
import re
import subprocess
import sys
import zlib

MAX_BYTES = 512 * 1024
SCREENSHOTS = {
    'docs/images/prores-quality-options.png',
    'docs/images/log-settings.png',
    'docs/images/h265-bitrate.png',
    'docs/images/desqueeze-options.png',
    'docs/images/video-menu-values.png',
    'docs/images/prores-quality-value.png',
    'docs/images/pixelshift-groups.png',
    'docs/images/nraw-quality-tiers.png',
    'docs/images/opengate-frame-rates.png',
}
# Reviewed small UI source assets, not firmware inputs.
SCREENSHOTS.update({'z8log/icons/slog3_fill.png', 'z8quality/icons/fill_0a5e.png', 'z8quality/icons/menu_1289.png', 'z8log/icons/slog3_outline.png', 'z8quality/icons/outline_0769.png', 'z8quality/icons/fill_0a5b.png', 'z8quality/icons/fill_0a5c.png', 'z8quality/icons/fill_0a5d.png', 'z8log/icons/log3g10_fill.png', 'z8quality/icons/menu_1288.png', 'z8quality/icons/outline_0aa1.png', 'z8quality/icons/outline_0a9e.png', 'z8quality/icons/menu_1285.png', 'z8quality/icons/menu_1286.png', 'z8quality/icons/menu_10f4.png', 'z8quality/icons/outline_0765.png', 'z8quality/icons/menu_1287.png', 'z8quality/icons/outline_0a9f.png', 'z8quality/icons/fill_0a5f.png', 'z8log/icons/log3g10_outline.png', 'z8quality/icons/menu_10f0.png', 'z8quality/icons/menu_10f2.png', 'z8quality/icons/outline_0a9d.png', 'z8quality/icons/outline_0aa0.png', 'z8quality/icons/outline_0761.png'})


SCREENSHOTS.update({'docs/images/log-slog3-errors.png', 'docs/images/log-slog3-chromaticity.png', 'docs/images/log-slog3-errors-zh.png', 'docs/images/log-rwg-conditions-zh.png', 'docs/images/log-rwg-conditions.png', 'docs/images/log-colour-spaces-zh.png', 'docs/images/log-rwg-prediction.png', 'docs/images/log-colour-spaces.png', 'docs/images/log-slog3-chromaticity-zh.png', 'docs/images/log-rwg-prediction-zh.png'})

SCREENSHOTS.update({'docs/images/log-measured-conditions.png', 'docs/images/log-slog3-revised-codes-zh.png', 'docs/images/log-measured-distribution.png', 'docs/images/log-measured-conditions-zh.png', 'docs/images/log-measured-chromaticity-zh.png', 'docs/images/log-measured-chromaticity.png', 'docs/images/log-slog3-revised-codes.png', 'docs/images/log-measured-distribution-zh.png'})

SCREENSHOTS.update({
    'docs/images/log-camera-xy-zh.png',
    'docs/images/log-camera-xy.png',
    'docs/images/log-camera-de-cdf-zh.png',
    'docs/images/log-camera-de-cdf.png',
    'docs/images/log-camera-xy-log3g10-zh.png',
    'docs/images/log-camera-xy-log3g10.png',
    'docs/images/log-camera-xy-slog3-zh.png',
    'docs/images/log-camera-xy-slog3.png',
    'docs/images/log-control-xy-log3g10-zh.png',
    'docs/images/log-control-xy-log3g10.png',
    'docs/images/log-control-xy-slog3-zh.png',
    'docs/images/log-control-xy-slog3.png',
    'docs/images/log-control-errors-zh.png',
    'docs/images/log-control-errors.png',
    'docs/images/log-control-xy-zh.png',
    'docs/images/log-control-xy.png',
})

# Exact public colour-transform asset; never a general exemption for .cube inputs.
PUBLIC_LUT = "luts/RWG_Log3G10_F_v1_65.cube"
PUBLIC_LUT_SHA = "2862a0c6ee17f73d9e83fcee04a706413742b00d53bc538d224a6a70bb3f93da"
# Reviewed zero-slot card WAV unit: every displaced-instruction slot ships blank
# and is filled from the user's firmware at build time. Hash mirrors resources/cardwav.json.
CARDWAV_UNIT = "resources/cardwav.bin"
CARDWAV_UNIT_SHA = "369acfa607adcfb1b2b68b16ca79671d7069e78e5129d4fa4b361b04fea99fbe"

def plain_png(data):
    """Accept small screenshots with valid chunks and no embedded metadata."""
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        return False
    at, chunks = 8, []
    while at + 12 <= len(data):
        n = int.from_bytes(data[at:at+4], 'big')
        kind = data[at+4:at+8]
        if kind not in (b'IHDR', b'IDAT', b'IEND') or at + n + 12 > len(data):
            return False
        payload = data[at+8:at+8+n]
        stored = int.from_bytes(data[at+8+n:at+12+n], 'big')
        if zlib.crc32(kind + payload) & 0xffffffff != stored:
            return False
        if kind == b'IHDR':
            if chunks or n != 13 or not all(0 < int.from_bytes(payload[k:k+4], 'big') <= 4096 for k in (0, 4)):
                return False
        chunks.append(kind)
        at += n + 12
        if kind == b'IEND':
            return n == 0 and at == len(data) and chunks[0] == b'IHDR' and b'IDAT' in chunks
    return False


BLOCKED_SUFFIXES = {
    '.bin', '.payload', '.bi', '.elf', '.dtb', '.img', '.iso', '.dmg',
    '.zip', '.tar', '.tgz', '.7z', '.cube', '.dylib', '.so', '.dll', '.a',
    '.o', '.class', '.nef', '.dng', '.dmp', '.cfg', '.mov', '.mp4', '.nev', '.r3d', '.rmd', '.exr', '.mxf', '.avi', '.wav',
    '.yuv', '.rgb', '.npz', '.npy', '.gpr', '.gzf', '.idb', '.i64', '.pem', '.key',
}
BLOCKED_PARTS = {
    'vendor', '.runtime', 'ghidra_work', '.ghidra', '.venv', 'venv',
    'node_modules', '__pycache__', '.aws', '.ssh', 'frames', 'cache', 'local_data', '.codex', '.agents',
}
SECRET_PATTERNS = [
    re.compile(rb'-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----'),
    re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
    re.compile(rb'\bgithub_pat_[A-Za-z0-9_]{50,}\b'),
    re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    re.compile(rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}\b'),
    re.compile(rb'\bolp_[A-Za-z0-9]{25,}\b'),
]
EXECUTABLE_MAGIC = (b'\x7fELF', b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe',
                    b'\xfe\xed\xfa\xcf', b'\xfe\xed\xfa\xce', b'\xca\xfe\xba\xbe')


def git(*args, data=None):
    return subprocess.run(['git', *args], input=data, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--staged', action='store_true')
    group.add_argument('--all', action='store_true')
    args = parser.parse_args()
    command = ('ls-files', '-z', '--cached') if args.all else (
        'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z')
    names = sorted(set(filter(None, git(*command).split(b'\0'))))
    if any(b'\n' in name or b'\r' in name for name in names):
        raise ValueError('Newline-containing filenames are not supported')
    raw = git('cat-file', '--batch', data=b''.join(b':'+name+b'\n' for name in names)) if names else b''
    position = 0
    total = 0
    issues = []
    largest = ('', 0)
    for name in names:
        end = raw.index(b'\n', position)
        header = raw[position:end].rsplit(b' ', 2)
        if len(header) != 3 or header[1] != b'blob':
            raise ValueError('Unexpected index object: '+name.decode('utf-8', 'replace'))
        size = int(header[2])
        content = raw[end+1:end+1+size]
        if len(content) != size or raw[end+1+size:end+2+size] != b'\n':
            raise ValueError('Truncated Git object stream')
        position = end+2+size
        path = name.decode('utf-8', 'strict')
        item = pathlib.PurePosixPath(path)
        total += size
        if size > largest[1]:
            largest = (path, size)
        blocked = item.suffix.lower() in BLOCKED_SUFFIXES or any(p in BLOCKED_PARTS for p in item.parts)
        blocked |= item.name in {'.DS_Store', '.env', 'credentials.json', 'secrets.json'}
        blocked |= item.name.startswith('.env.') and item.name != '.env.example'
        public_lut = path == PUBLIC_LUT and hashlib.sha256(content).hexdigest() == PUBLIC_LUT_SHA
        if public_lut:
            blocked = False
        cardwav_unit = path == CARDWAV_UNIT and hashlib.sha256(content).hexdigest() == CARDWAV_UNIT_SHA
        if cardwav_unit:
            blocked = False
        if blocked:
            issues.append((path, 'excluded input, private record, or runtime path'))
        if size > (8 * 1024 * 1024 if public_lut else MAX_BYTES):
            issues.append((path, 'file exceeds the 512 KiB source-resource limit'))
        screenshot = path in SCREENSHOTS and plain_png(content)
        if path in SCREENSHOTS and not screenshot:
            issues.append((path, 'invalid screenshot or embedded PNG metadata'))
        if not screenshot and not cardwav_unit:
            try:
                content.decode('utf-8')
            except UnicodeDecodeError:
                issues.append((path, 'only reviewed PNG figures, screenshots and UI assets may contain binary content'))
            if b'\0' in content:
                issues.append((path, 'NUL bytes suggest binary content'))
        if content.startswith(EXECUTABLE_MAGIC):
            issues.append((path, 'compiled executable magic'))
        for pattern in SECRET_PATTERNS:
            match = pattern.search(content)
            if match:
                line = content.count(b'\n', 0, match.start())+1
                issues.append((path, f'possible credential at line {line} (value withheld)'))
    if position != len(raw):
        raise ValueError('Unconsumed Git object data')
    for path, reason in issues:
        print(f'{path}: {reason}', file=sys.stderr)
    print(f'Checked {len(names)} indexed files, {total/1024**2:.2f} MiB; issues: {len(issues)}.')
    if largest[0]:
        print(f'Largest: {largest[0]} ({largest[1]/1024**2:.2f} MiB).')
    return 1 if issues else 0


if __name__ == '__main__':
    raise SystemExit(main())
