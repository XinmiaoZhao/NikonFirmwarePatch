#!/usr/bin/env python3
"""Generate the project's RWG/Log3G10 saturation-map LUT, using only the stdlib.

Input/output are normalized Log3G10 RGB in REDWideGamutRGB. This is a colour
mapping, not a Rec.709 display LUT. The scale-free model omits an absolute
near-black activation threshold. See luts/README.md for node placement.
"""
import argparse,hashlib,json,math
from pathlib import Path
A,B,C,G=.224282,155.975327,.01,15.1927

def decode(v):
    return v/G-C if v<0 else math.expm1(v*math.log(10)/A)/B-C

def encode(v):
    v+=C
    return v*G if v<0 else A*math.log1p(v*B)/math.log(10)

def branch_map(rgb,threshold):
    peak=max(rgb)
    if peak<=0:return tuple(rgb)
    ratios=[x/peak for x in rgb];minimum=min(ratios)
    if minimum>=threshold:return tuple(rgb)
    mapped=0.0 if minimum < -1 else threshold*((minimum+1)/(threshold+1))**((threshold+1)/threshold)
    scale=(1-mapped)/(1-minimum)
    return tuple(peak*(1-scale*(1-v)) for v in ratios)

def transform(rgb):
    x=tuple(decode(v) for v in rgb);peak=max(x)
    # At a grid node with tied dominant channels, average adjacent branch
    # limits in Log code space. This prevents an isolated identity value on a
    # tie plane from turning into an interpolation stripe across a whole cell.
    thresholds=sorted({.5 if i==2 else .05 for i,v in enumerate(x) if v==peak})
    values=[tuple(encode(v) for v in branch_map(x,t)) for t in thresholds]
    return tuple(sum(v[k] for v in values)/len(values) for k in range(3))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--size',type=int,choices=[17,33,65],default=65)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();dest=a.output;meta=dest.with_suffix('.json')
    if dest.exists() or meta.exists():raise ValueError('Output or manifest already exists')
    dest.parent.mkdir(parents=True,exist_ok=True)
    minimum,maximum=1.0,0.0
    with dest.open('x',encoding='ascii',newline='\n') as out:
        out.write('# Project saturation-map model, version 1\n')
        out.write('# Input and output: REDWideGamutRGB / Log3G10, normalized 0..1\n')
        out.write('# Apply after white balance and before a display transform.\n')
        out.write('TITLE "NikonFirmwarePatch RWG Log3G10 F model"\n')
        out.write(f'LUT_3D_SIZE {a.size}\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n')
        # CUBE order: R changes fastest, G next, B slowest.
        for b in range(a.size):
            for g in range(a.size):
                for r in range(a.size):
                    values=transform((r/(a.size-1),g/(a.size-1),b/(a.size-1)))
                    assert all(math.isfinite(v) and -1e-12<=v<=1+1e-12 for v in values)
                    values=tuple(min(1.0,max(0.0,v)) for v in values)
                    minimum=min(minimum,*values);maximum=max(maximum,*values)
                    out.write(' '.join(f'{v:.6f}' for v in values)+'\n')
    info=dict(schema=1,title='RWG / Log3G10 F saturation-map model',model_version=1,lut_size=a.size,rows=a.size**3,input_space='REDWideGamutRGB / Log3G10',output_space='REDWideGamutRGB / Log3G10',domain_min=[0,0,0],domain_max=[1,1,1],order='red fastest, then green, then blue',recommended_interpolation='tetrahedral',file=dest.name,bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),output_min=minimum,output_max=maximum,near_black='Scale-free model; no absolute activation threshold',display_transform=False,tied_dominant_nodes='Mean of adjacent branch limits in Log code space; neutral axis preserved')
    meta.write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info))
if __name__=='__main__':main()
