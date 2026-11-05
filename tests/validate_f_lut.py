#!/usr/bin/env python3
"""Independent CUBE layout, all-node and interpolation checks. No builder imports.
Only stdlib; reads published numerical samples, no footage or firmware.
"""
import argparse,hashlib,itertools,json,math,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def linear(c):
    return c/15.1927-.01 if c<0 else (10**(c/.224282)-1)/155.975327-.01

def log(v):
    return (v+.01)*15.1927 if v<-.01 else .224282*math.log10(1+155.975327*(v+.01))

def reference(c):
    x=[linear(v) for v in c];hi=max(x);lo=min(x)
    thresholds={.5 if i==2 else .05 for i,v in enumerate(x) if v==hi}
    branches=[]
    for threshold in thresholds:
        y=x
        if hi>0 and lo<hi*threshold:
            ratio=lo/hi
            knee=0 if ratio < -1 else threshold*math.pow((1+ratio)/(1+threshold),1+1/threshold)
            y=[hi-(hi-v)*(1-knee)/(1-ratio) for v in x]
        branches.append(tuple(log(v) for v in y))
    return tuple(sum(v[i] for v in branches)/len(branches) for i in range(3))

def read_cube(path):
    size=None;rows=[];lo=hi=None
    for line in path.read_text('ascii').splitlines():
        p=line.split()
        if not p or p[0].startswith('#') or p[0]=='TITLE':continue
        if p[0]=='LUT_3D_SIZE':size=int(p[1]);continue
        if p[0]=='DOMAIN_MIN':lo=list(map(float,p[1:]));continue
        if p[0]=='DOMAIN_MAX':hi=list(map(float,p[1:]));continue
        assert len(p)==3,'CUBE row length';v=tuple(map(float,p));assert all(math.isfinite(x) and 0<=x<=1 for x in v),'CUBE value'
        rows.append(v)
    assert size in (17,33,65) and len(rows)==size**3,'CUBE size/count'
    assert lo==[0,0,0] and hi==[1,1,1],'CUBE domain'
    return size,rows

def tetra(n,rows,c):
    xyz=[max(0,min(1,v))*(n-1) for v in c];i=[min(n-2,int(v)) for v in xyz];r,g,b=[v-k for v,k in zip(xyz,i)]
    if r>=g:
        if g>=b:pts=((0,0,0),(1,0,0),(1,1,0),(1,1,1));w=(1-r,r-g,g-b,b)
        elif r>=b:pts=((0,0,0),(1,0,0),(1,0,1),(1,1,1));w=(1-r,r-b,b-g,g)
        else:pts=((0,0,0),(0,0,1),(1,0,1),(1,1,1));w=(1-b,b-r,r-g,g)
    else:
        if r>=b:pts=((0,0,0),(0,1,0),(1,1,0),(1,1,1));w=(1-g,g-r,r-b,b)
        elif g>=b:pts=((0,0,0),(0,1,0),(0,1,1),(1,1,1));w=(1-g,g-b,b-r,r)
        else:pts=((0,0,0),(0,0,1),(0,1,1),(1,1,1));w=(1-b,b-g,g-r,r)
    v=[rows[(i[0]+p[0])+n*(i[1]+p[1])+n*n*(i[2]+p[2])] for p in pts]
    return tuple(sum(a*q[k] for a,q in zip(w,v)) for k in range(3))

def stats(v):
    v=sorted(v);n=len(v)
    def percentile(q):
        p=(n-1)*q;k=int(p);f=p-k;return v[k]*(1-f)+v[min(k+1,n-1)]*f
    return dict(rms=math.sqrt(sum(x*x for x in v)/n),median=percentile(.5),p99=percentile(.99),max=max(v))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--lut',type=Path,default=ROOT/'luts/RWG_Log3G10_F_v1_65.cube');p.add_argument('--report',type=Path);a=p.parse_args()
    n,rows=read_cube(a.lut);manifest=json.loads(a.lut.with_suffix('.json').read_text())
    digest=hashlib.sha256(a.lut.read_bytes()).hexdigest();assert digest==manifest['sha256'] and a.lut.stat().st_size==manifest['bytes']
    worst=0
    for idx,row in enumerate(rows):
        c=((idx%n)/(n-1),((idx//n)%n)/(n-1),(idx//(n*n))/(n-1))
        error=max(abs(v-w) for v,w in zip(row,reference(c)));worst=max(worst,error)
    assert worst<5.01e-7,(worst,'node or channel ordering error')
    for k in range(n):assert max(abs(v-k/(n-1)) for v in rows[k*(1+n+n*n)])<5.01e-7
    sample_file=ROOT/'docs/data/log-colour-samples.json';data=json.loads(sample_file.read_text())
    code_errors=[];colour_errors=[];node_errors=[]
    for row in data['log3g10']['samples']:
        c=tuple(log(v) for v in row['reference_linear_rwg']);assert all(0<=v<=1 for v in c)
        approx=tetra(n,rows,c);exact=reference(c)
        code_errors.extend(abs(v-w)*1023 for v,w in zip(approx,exact))
        ap=list(map(linear,approx));ex=list(map(linear,exact))
        colour_errors.extend(abs(math.log2(ap[k]/ap[1])-math.log2(ex[k]/ex[1])) for k in (0,2))
    rng=random.Random(20261105);grid_errors=[]
    for _ in range(10000):
        c=tuple(rng.random() for _ in range(3));ap=tetra(n,rows,c);ex=reference(c)
        grid_errors.extend(abs(v-w)*1023 for v,w in zip(ap,ex))
    out=dict(status='PASS',scope='CUBE syntax, domain, red-fastest storage, every grid node and neutral ramp; numerical interpolation only, no editing-app UI test',lut=a.lut.name,sha256=digest,grid_size=n,grid_nodes=n**3,node_max_normalized_error=worst,reference_samples=288,reference_sample_code_error_10bit=stats(code_errors),reference_sample_colour_ratio_error_stops=stats(colour_errors),uniform_cube_samples=10000,uniform_cube_code_error_10bit=stats(grid_errors),interpolation='tetrahedral; all six tetrahedra',model_boundary='Blue-dominant threshold differs from red/green; interpolation smooths its discontinuity. Tied grid nodes use adjacent-limit averages; neutral ramp preserved. Scale-free near-black handling.',sample_data_sha256=hashlib.sha256(sample_file.read_bytes()).hexdigest(),checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if a.report:a.report.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
