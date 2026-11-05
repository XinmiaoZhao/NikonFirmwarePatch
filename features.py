"""Compose four feature groups against one exact original C3.11 payload."""
import binascii
import json
import re
from pathlib import Path
from z8prores.package import require, sha
from z8prores.patcher import public_words
from z8prores.menu import Image
from z8patch.compiled import load
from z8patch.shared import Strings, VideoMenu, loader

FEATURES = ('framing','video-quality','log-colour','photo-tools')
ROOT = Path(__file__).resolve().parent
STOCK_SHA = 'f85e0138e2f5e660ece8560de62e0d12cb795e0e14983e50f20b61dce906c46c'


def selected_features(features):
    require(features and len(features)==len(set(features)) and set(features)<=set(FEATURES),
            'Select one or more supported features, without duplicates')
    return [f for f in FEATURES if f in features]


def compatibility(eg, features):
    chosen = selected_features(features)
    require(len(eg)==81807711 and sha(eg)==STOCK_SHA, 'Incompatible input: exact original C3.11 EG required')
    recipes=json.loads((ROOT/'resources/combinations.json').read_text())
    profile=dict(recipes['profiles']['+'.join(chosen)])
    profile['patches']=[recipes['patches'][i] for i in profile['patches']]
    return {'composition':profile}, eg[0x14EAA90:0x14EAA98].decode()


def compose(eg, features, compiler='clang', code_source='prebuilt', *, check_recipe=True):
    """Feature edits only. Maintainer recipe generation is explicit and separate."""
    chosen = selected_features(features)
    require(len(eg)==81807711 and sha(eg)==STOCK_SHA, 'Incompatible input: exact original C3.11 EG required')
    require(code_source in ('source','prebuilt'), 'Select prebuilt or source')
    img = Image(eg)
    strings,menu=Strings(),VideoMenu(eg)
    detail,callbacks={},{}

    def unit(name):
        code,meta=load(name,code_source,compiler)
        return code,{k:int(v['va'],16) for k,v in meta['symbols'].items()}

    def merge(feature,source,refinements=()):
        for e in source.edits:
            if menu.consumed(e):continue
            overlap=[x for x in img.edits if e['offset']<x['end'] and x['offset']<e['end']]
            if overlap:
                require(e['offset']+0x40160000 in refinements and len(overlap)==1,'Unregistered feature overlap')
                previous=overlap[0]
                require(previous['offset']<=e['offset'] and e['end']<=previous['end'],'Partial refinement')
                require(bytes(img.new[e['offset']:e['end']])==e['old'],'Refinement base mismatch')
                at=e['offset']-previous['offset'];data=bytearray(previous['new'])
                data[at:at+len(e['new'])]=e['new'];previous['new']=bytes(data)
                previous['purpose']+='; '+feature+': '+e['purpose']
                img.new[e['offset']:e['end']]=e['new']
            else:
                require(eg[e['offset']:e['end']]==e['old'],'Feature expects a non-stock base')
                img.put(e['offset'],e['new'],feature+': '+e['purpose'])

    if 'framing' in chosen:
        from z8opengate.patcher import build_main
        code,entries=unit('opengate')
        part,detail['opengate-nraw']=build_main(eg,code,entries,strings)
        merge('opengate-nraw',part)
        from z8anamorphic.patcher import build_main
        code,entries=unit('anamorphic')
        ap,detail['anamorphic']=build_main(bytes(part.new),code,entries,strings)
        menu.collect(ap,0x310F)
        merge('anamorphic',ap,(0x40960C98,0x40962B58,0x409616A4,0x407138D0))
        callbacks['anamorphic']=entries['ap_menu_refresh_hook']
    if 'video-quality' in chosen:
        star,star_entries=unit('quality')
        from z8prores.menu import build_main
        part,detail['prores']=build_main(eg,strings,star_entries['tier_hq_ok'])
        menu.collect(part,0x311B);merge('prores',part)
        callbacks['prores']=int(detail['prores']['entries']['refresh'],16)
        prores_ok=int(detail['prores']['entries']['ok'],16)
        from z8h265.patcher import build_main
        code,entries=unit('h265')
        part,detail['h265']=build_main(eg,code,entries,strings,star_entries['tier_ok_star'])
        m=detail['h265']['menu']
        menu.add(0x315A,bytes.fromhex(m['row_hex']),int(m['row_table'],16))
        merge('h265',part);callbacks['h265']=entries['tier_refresh_hook']
        from z8quality.patcher import build_main
        part,detail['stars']=build_main(eg,star,star_entries,entries['tier_ok_hook'],prores_ok)
        merge('stars',part)
    if 'log-colour' in chosen:
        from z8log.patcher import build_main
        code,entries=unit('log')
        part,detail['log']=build_main(eg,code,entries,strings)
        menu.collect(part,0x2E38);merge('log',part)
        callbacks['log']=entries['lg_menu_refresh_hook']
    if 'photo-tools' in chosen:
        from z8precapture.patcher import edits
        code,meta=load('precapture',code_source,compiler)
        for e in edits(code,meta['symbols']):img.put(e['offset'],e['new'],e['purpose'])
        detail['precapture']=dict(code_sha256=meta['sha256'],code_bytes=len(code),diagnostics=False,
                                  space_fallback=True,remaining_count=True,dx=True,lossless_fallback='HE*')
        from z8pixelshift.patcher import build_main
        code,meta=load('pixelshift',code_source,compiler)
        af,_=load('pixelshift-af',code_source,compiler)
        part,detail['pixelshift']=build_main(eg,code,meta['symbols'],af,strings)
        merge('pixelshift',part)
    detail['strings']=strings.emit(img)
    if callbacks:
        code,entries=unit('shared')
        detail['menu']=menu.emit(img,chosen,code,entries,callbacks)
    else:detail['menu']=None
    detail['loader']=loader(img,chosen)
    rows = [dict(offset=hex(e['offset']),bytes=len(e['new']),purpose=e['purpose'],
                 old_sha256=sha(e['old']),new_sha256=sha(e['new'])) for e in sorted(img.edits,key=lambda r:r['offset'])]
    if check_recipe:
        profile = compatibility(eg,chosen)[0]['composition']
        require(rows==profile['patches'], 'Generated edits differ from the reviewed combination recipe')
    return img, detail, rows


def build(eg, version, tag, features, compiler='clang', code_source='prebuilt'):
    chosen = selected_features(features)
    profiles, old_identity = compatibility(eg,chosen)
    public_words(version)
    require(re.fullmatch(r'[a-z][0-9]',tag), 'Tag must be a lowercase letter and digit')
    img, detail, _ = compose(eg,chosen,compiler,code_source)
    text = f'{version}.{tag}'.encode()
    for at, raw, why in [(0xEB29FC,public_words(version),'public version'),
                         (0x14EAA90,text,'runtime identity'),(len(eg)-11,text,'trailer identity')]:
        img.put(at,raw,why)
    img.put(len(eg)-2,binascii.crc_hqx(img.new[:-2],0).to_bytes(2,'big'),'EG CRC16')
    result = bytes(img.new)
    require(binascii.crc_hqx(result,0)==0,'Invalid final payload CRC')
    end, rows, preserved = 0, [], []
    for e in sorted(img.edits,key=lambda r:r['offset']):
        at = e['offset']
        require(end<=at and result[end:at]==eg[end:at],'Change outside declared windows')
        if end<at:
            preserved.append(dict(start=end,end=at,sha256=sha(eg[end:at])))
        rows.append(dict(offset=at,bytes=len(e['new']),purpose=e['purpose'],
                         before_sha256=sha(e['old']),after_sha256=sha(e['new'])))
        end=e['end']
    require(result[end:]==eg[end:],'Unlisted final change')
    return result,dict(features=chosen,input_identity=old_identity,output_identity=text.decode(),
                       profiles={k:v['id'] for k,v in profiles.items()},edits=rows,preserved_ranges=preserved,
                       all_bytes_outside_edits_preserved=True,details=detail)
