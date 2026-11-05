#!/usr/bin/env python3
"""Generate maintainer candidate recipes; independently validate before release."""
import argparse
import itertools
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from z8prores.package import Package,require_official_input
from features import FEATURES,compose

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stock',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    raw=a.stock.read_bytes();require_official_input(raw);package=Package(raw)
    profiles={}
    for bits in itertools.product((False,True),repeat=len(FEATURES)):
        names=[f for f,on in zip(FEATURES,bits) if on]
        if not names:continue
        _,detail,rows=compose(package.eg,names,check_recipe=False)
        key='+'.join(names)
        profiles[key]=dict(id='z8-c311-groups-v1-'+''.join('1' if b else '0' for b in bits),features=names,patches=rows)
        print(key,len(rows),flush=True)
    catalog=[];lookup={}
    for profile in profiles.values():
        ids=[]
        for row in profile['patches']:
            key=json.dumps(row,sort_keys=True)
            if key not in lookup:lookup[key]=len(catalog);catalog.append(row)
            ids.append(lookup[key])
        profile['patches']=ids
    with a.output.open('x') as f:
        json.dump(dict(schema=2,scope='Pinned feature-byte recipes; independent validation and camera coverage are documented separately.',profiles=profiles,patches=catalog),f,indent=2)
        f.write('\n')

if __name__=='__main__':main()
