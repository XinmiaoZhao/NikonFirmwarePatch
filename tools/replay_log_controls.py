"""Reproduce all forward predictions using the user's stock C 3.11 firmware."""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
import numpy as np
from plot_colour_revision import E

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from verify import decode


def apply_cpxs(values, rows, origin):
    y,u,v=values.T
    angle=np.arctan2(v,u)%(2*np.pi)
    quadrant=np.floor(angle/(np.pi/2))
    sector=angle-quadrant*np.pi/2
    diamond=90*(quadrant+np.sin(sector)/(np.cos(sector)+np.sin(sector)))
    position=((diamond-origin)/11.25)%32
    index=np.floor(position).astype(int)%32
    fraction=(position-np.floor(position))[:,None]
    a,b,c,d,e,f=(((1-fraction)*rows[index]+fraction*rows[(index+1)%32])/256).T
    return np.column_stack([y+e*u+f*v,a*u+b*v,c*u+d*v])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stock',type=Path)
    args=ap.parse_args()
    raw=args.stock.read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96'
    payload=decode(raw)[581844:82389555]
    samples=json.loads((ROOT/'docs/data/log-controls.json').read_text())
    meta=samples['model']
    assert hashlib.sha256(payload).hexdigest()==meta['factory_payload_sha256']
    base=0x40160000
    addr=struct.unpack_from('<Q',payload,0x442e0bd8-base)[0]
    ring=np.zeros((32,6))
    ring[meta['ring_position_of_slot']]=np.frombuffer(payload,dtype='<i2',count=192,offset=addr-base).reshape(32,6)
    stock_m2=np.frombuffer(payload,dtype='<i2',count=9,offset=0x40456ba).reshape(3,3)/512
    stock_lut=np.frombuffer(payload,dtype='<u2',count=229,offset=0x4041010)/32
    stock_m1=np.array([[986,20,18],[20,975,29],[-2,29,997]])/1024
    cfg=json.loads((ROOT/'z8log/data.json').read_text())['types']
    output=E@np.array(meta['y2r'])
    for group,inputs in samples['groups'].items():
        x=np.array(inputs['pre_m1_grid'])
        def predict(m1,lut,m2,table):
            rgb=np.interp(x@m1.T,meta['grid'],lut)
            return apply_cpxs(rgb@m2.T,table,meta['phi_deg'])@output.T+[0,512,512]
        assert np.allclose(predict(stock_m1,stock_lut,stock_m2,ring),inputs['nlog_codes'],atol=1e-6,rtol=0)
        for mode,key in [('log3g10','2'),('slog3','1')]:
            info=samples['modes'][mode]
            current=cfg[key]
            curve=np.frombuffer(bytes.fromhex(current['rgb_hex']),dtype='<u2')[:229]/32
            m1=np.array(current['m1_body_this_camera']).reshape(3,3)/1024
            for arm,matrix,m2,table in [
                ('gamut_curve',np.array(info['simple_m1_q10'])/1024,stock_m2,ring),
                ('stock_cpxs',m1,E,ring),
                ('identity_cpxs',m1,E,np.tile([256,0,0,256,0,0],(32,1))),
                ('complete',m1,E,np.array(current['cpxs_by_slot']))]:
                result=predict(matrix,curve,m2,table)
                assert np.allclose(result,info['groups'][group][arm],atol=1e-6,rtol=0),(mode,group,arm)
    print('All N-Log inputs and simulated file-code means reproduced.')


if __name__=='__main__':main()
