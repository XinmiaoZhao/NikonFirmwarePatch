#!/usr/bin/env python3
"""Compile the raw-precapture units and install them as resources/precapture.bin and resources/precapture-menu.bin.

For a toolkit whose other prebuilt units come from the v0.5.0 release: the pre-capture unit and the RAW recording
menu unit changed after that release, so they are compiled here and each must match the reviewed bytes pinned in
resources/compiled.json before it is written.
"""
import argparse
from pathlib import Path
import sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import json
from z8patch.compiled import compile_unit
from z8prores.package import require, sha

UNITS = ('precapture', 'precapture-menu')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--compiler', default='clang')
    a = ap.parse_args()
    units = json.loads((ROOT/'resources/compiled.json').read_text())['units']
    for name in UNITS:
        profile = units[name]
        code, meta = compile_unit(name, a.compiler)
        require(meta['source_sha256'] == profile['source_sha256'], f'{name}: source differs from the pinned recipe')
        require(meta['symbols'] == profile['symbols'], f'{name}: compiled symbols differ; use ' + profile['compiler'])
        require(len(code) == profile['bytes'] and sha(code) == profile['sha256'],
                f'{name}: compiled bytes differ; use ' + profile['compiler'])
        (ROOT/profile['resource']).write_bytes(code)
        print(profile['resource'], len(code), sha(code))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as e:
        raise SystemExit('ERROR: ' + str(e))
