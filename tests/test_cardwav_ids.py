#!/usr/bin/env python3
"""Guard: WAV picker label IDs stay disjoint from feature string IDs.

The card WAV picker intercepts the stock text resolver for its label range.
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
from z8cardwav.builder import WAV_LABEL_BASE, WAV_LABEL_COUNT  # noqa: E402


def main():
    used = set()
    for first, count in STRING_IDS.values():
        used.update(range(first, first + count))
    wav = set(range(WAV_LABEL_BASE, WAV_LABEL_BASE + WAV_LABEL_COUNT))
    overlap = used & wav
    assert not overlap, 'WAV label IDs overlap feature strings: ' + ', '.join(hex(i) for i in sorted(overlap))
    assert max(used) < STRING_END, 'Feature strings exceed the declared STRING_END'
    assert WAV_LABEL_BASE + WAV_LABEL_COUNT <= 4095, 'Label range exceeds the CMP 12-bit immediate limit'
    unit, blob = ROOT / 'resources' / 'cardwav.json', ROOT / 'resources' / 'cardwav.bin'
    if unit.is_file() and blob.is_file():
        profile = json.loads(unit.read_text(encoding='utf-8'))
        data = blob.read_bytes()
        assert len(data) == profile['bytes'], 'Pinned cardwav.bin size differs from cardwav.json'
        assert hashlib.sha256(data).hexdigest() == profile['sha256'], 'Pinned cardwav.bin hash differs'
        print('cardwav unit pinned:', profile['bytes'], 'bytes,', profile['compiler'].splitlines()[0][:48])
    else:
        print('cardwav unit not pinned yet; file checks skipped')
    print('OK: WAV labels %#x..%#x disjoint from feature strings %d..%d'
          % (WAV_LABEL_BASE, WAV_LABEL_BASE + WAV_LABEL_COUNT - 1, min(used), max(used)))


if __name__ == '__main__':
    main()
