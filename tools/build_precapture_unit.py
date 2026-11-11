#!/usr/bin/env python3
"""Compile the pre-capture unit and install it as resources/precapture.bin.

For a toolkit whose other eight prebuilt units come from the v0.4.0 release: the
pre-capture unit changed after that release, so it is compiled here and must match
the reviewed bytes pinned in resources/compiled.json before it is written.
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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--compiler', default='clang')
    a = ap.parse_args()
    profile = json.loads((ROOT/'resources/compiled.json').read_text())['units']['precapture']
    code, meta = compile_unit('precapture', a.compiler)
    require(meta['source_sha256'] == profile['source_sha256'], 'Pre-capture source differs from the pinned recipe')
    require(meta['symbols'] == profile['symbols'], 'Compiled pre-capture symbols differ; use ' + profile['compiler'])
    require(len(code) == profile['bytes'] and sha(code) == profile['sha256'],
            'Compiled pre-capture bytes differ; use ' + profile['compiler'])
    (ROOT/profile['resource']).write_bytes(code)
    print(profile['resource'], len(code), sha(code))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as e:
        raise SystemExit('ERROR: ' + str(e))
