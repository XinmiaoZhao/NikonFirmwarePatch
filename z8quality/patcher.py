"""Combined HB2/PQ1 icon rules; the native icon table remains extensible by Log."""
import hashlib
import json
import struct
from pathlib import Path
from z8patch.image import Image, BASE, branch, movz
from z8prores.package import require

ROOT=Path(__file__).resolve().parent
CODE, CONFIG, FORCE, PNG=0x40A41000,0x40A40F00,0x40A40000,0x40A20000
STOCK_SHA='f85e0138e2f5e660ece8560de62e0d12cb795e0e14983e50f20b61dce906c46c'


def tables(eg):
    d=json.loads((ROOT/'h265-icons.json').read_text())
    require(d['stock_sha256']==STOCK_SHA and d['new_icons']==21,'Icon source identity')
    pairs,new,pngs=[],[],bytearray()
    for group in d['sets'].values():
        for e in group['icons']:
            star=int(e['star'],16)
            require(star<6242,'Invalid native star icon')
            flags,length,z0,z1,ptr=struct.unpack_from('<IIIIQ',eg,0x30796D0+24*star)
            require(flags==0x100 and z0==z1==0,'Native icon record')
            if 'plain' in e:
                plain=int(e['plain'],16)
                flags,length,z0,z1,ptr=struct.unpack_from('<IIIIQ',eg,0x30796D0+24*plain)
                require((flags,length,hex(ptr))==(e['plain_record']['flags'],e['plain_record']['bytes'],e['plain_record']['va']),'Native plain icon changed')
            else:
                raw=(ROOT/'icons'/e['new']).read_bytes()
                require(len(raw)==e['bytes'] and hashlib.sha256(raw).hexdigest()==e['sha256'],'Derived icon changed')
                plain=0x7000+len(new)
                new.append(struct.pack('<HHIQ',0x100,0,len(raw),PNG+len(pngs)))
                pngs+=raw;pngs+=bytes(-len(pngs)%8)
            pairs.append(struct.pack('<HH',star,plain))
    survey=json.loads((ROOT/'prores-icons.json').read_text())
    hq=[struct.pack('<HH',int(v['plain'],16),int(v['star'],16)) for m in survey['modes'] for v in m['sets'].values()]
    require(len(pairs)==51 and len(new)==21 and len(hq)==27 and len(pngs)<=0x10000,'Icon table sizes')
    return b''.join(pairs),b''.join(new),b''.join(hq),bytes(pngs)


def build_main(eg,code,entries,h265_ok,prores_ok):
    img=Image(eg);code=bytearray(code)
    pairs,new,hq,pngs=tables(eg)
    for name,data in (('tier_star_pairs',pairs),('tier_star_new',new),('tier_hq_pairs',hq)):
        off=entries[name]-CODE
        require(code[off:off+len(data)]==bytes(len(data)),'Nonempty star table')
        code[off:off+len(data)]=data
    require(len(code)<=0xF000 and not any(eg[FORCE-BASE:CONFIG-BASE]),'Star code or state allocation')
    for site,label,old in ((0x40325D48,'tier_star_set',struct.pack('<I',0xA9BE53F5)),
                           (0x4032DC64,'tier_star_res_idx',movz(9,0xCD58)),
                           (0x4032DD34,'tier_star_res_val',movz(8,0xCD58)),
                           (0x406AAD0C,'tier_star_force',struct.pack('<I',0x6B09037F))):
        img.put(site,branch(site,entries[label]),'shared star '+label,expect=old)
    for site,label,old in ((0x440C7B58,'tier_star_nctg',0x406D2CE8),(0x440C7B60,'tier_star_nctg',0x406D2CE8),
                           (0x440C7B68,'tier_hq_nctg',0x406D2CF4)):
        img.put(site,struct.pack('<Q',entries[label]),'NCTG 24h: '+label,expect=struct.pack('<Q',old))
    img.put(CONFIG,struct.pack('<QQ',h265_ok,prores_ok),'native H.265 and ProRes OK actions',expect_zero=True)
    img.put(CODE,code,'combined star code and icon maps',expect_zero=True)
    img.put(PNG,pngs,'derived H.265 plain icon PNGs',expect_zero=True)
    return img,dict(code_bytes=len(code),entries={k:hex(v) for k,v in entries.items()},
                    force_rom=hex(FORCE),force_ram='0xa10040000',h265_pairs=51,prores_pairs=27,new_icons=21)
