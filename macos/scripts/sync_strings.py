#!/usr/bin/env python3
"""Update macos/Resources/Localizable.xcstrings from the strings the app's code uses.

Builds the debug configuration (it also compiles the DEBUG-only documentation renderer) with the
Swift compiler's string extraction, then lets xcstringstool add new keys and mark removed ones
stale. Translate new entries in Xcode or in the JSON, delete stale ones, and run
tests/validate_gui_catalog.py. With --check the catalog is left unchanged and the script fails if a
sync would change it.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
MACOS = Path(__file__).resolve().parents[1]
STRINGS = MACOS / 'Resources/Localizable.xcstrings'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true', help='fail instead of writing when the catalog is out of date')
    a = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='z8gui-strings-') as tmp:
        tmp = Path(tmp)
        (tmp / 'stringsdata').mkdir()
        flags = [f for arg in ('-emit-localized-strings', '-emit-localized-strings-path', tmp / 'stringsdata')
                 for f in ('-Xswiftc', str(arg))]
        subprocess.run(['swift', 'build', '--package-path', str(MACOS), '--scratch-path', str(tmp / 'swift'), *flags],
                       check=True, stdout=subprocess.DEVNULL)
        data = sorted(str(p) for p in (tmp / 'stringsdata').glob('*.stringsdata'))
        if not data:
            raise SystemExit('ERROR: the compiler reported no localizable strings')
        target = tmp / STRINGS.name if a.check else STRINGS
        if a.check:
            shutil.copy2(STRINGS, target)
        subprocess.run(['xcrun', 'xcstringstool', 'sync', str(target), '--stringsdata', *data], check=True)
        before = json.loads(STRINGS.read_text(encoding='utf-8'))['strings'] if a.check else None
        after = json.loads(target.read_text(encoding='utf-8'))['strings']
    stale = sorted(k for k, v in after.items() if v.get('extractionState') == 'stale')
    if a.check and before != after:
        added = sorted(set(after) - set(before))
        raise SystemExit('FAIL: Localizable.xcstrings is out of date; new keys: %r; stale keys: %r' % (added, stale))
    print(json.dumps(dict(status='CURRENT' if a.check else 'SYNCED', strings=len(after), stale=stale), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
