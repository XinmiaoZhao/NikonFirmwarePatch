#!/usr/bin/env python3
"""Guard: WAV picker label IDs stay disjoint from feature string IDs.

The shutter-sound picker intercepts the stock text resolver for its label range.
Feature groups own string IDs 3137..STRING_END-1 through the extended shared
tables, so any overlap would silently replace feature text with picker
labels at runtime. Runs anywhere; needs no firmware or unicorn.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from z8patch.shared import STRING_END, STRING_IDS  # noqa: E402
from z8shuttersound.builder import WAV_LABEL_BASE, WAV_LABEL_COUNT  # noqa: E402


def main():
    used = set()
    for first, count in STRING_IDS.values():
        used.update(range(first, first + count))
    wav = set(range(WAV_LABEL_BASE, WAV_LABEL_BASE + WAV_LABEL_COUNT))
    overlap = used & wav
    assert not overlap, 'WAV label IDs overlap feature strings: ' + ', '.join(hex(i) for i in sorted(overlap))
    assert max(used) < STRING_END, 'Feature strings exceed the declared STRING_END'
    assert WAV_LABEL_BASE + WAV_LABEL_COUNT <= 4095, 'Label range exceeds the CMP 12-bit immediate limit'
    unit, blob = ROOT / 'resources' / 'shuttersound.json', ROOT / 'resources' / 'shuttersound.bin'
    assert unit.is_file(), 'Pinned shuttersound.json recipe missing from the repository'
    profile = json.loads(unit.read_text(encoding='utf-8'))
    assert {'bytes', 'sha256', 'filled_sha256'} <= set(profile), 'shuttersound.json is missing pinned recipe fields'
    if blob.is_file():
        data = blob.read_bytes()
        assert len(data) == profile['bytes'], 'Pinned shuttersound.bin size differs from shuttersound.json'
        assert hashlib.sha256(data).hexdigest() == profile['sha256'], 'Pinned shuttersound.bin hash differs'
        print('shuttersound unit pinned:', profile['bytes'], 'bytes,', profile['compiler'].splitlines()[0][:48])
    else:
        print('shuttersound prebuilt unit not bundled in git (source-only policy); pinned-hash checks skipped')
    print('OK: WAV labels %#x..%#x disjoint from feature strings %d..%d'
          % (WAV_LABEL_BASE, WAV_LABEL_BASE + WAV_LABEL_COUNT - 1, min(used), max(used)))


if __name__ == '__main__':
    main()
