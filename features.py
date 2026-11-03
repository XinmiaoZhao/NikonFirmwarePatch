"""Compose independent choices against one exact original C3.11 payload; locked-banks is a prototype."""
import binascii
import json
import re
from pathlib import Path
from z8prores.package import require, sha
from z8prores.patcher import public_words
from z8prores.menu import Image
from z8patch.compiled import load
from z8patch.shared import Strings, bank, loader

FEATURES = ('prores','precapture','pixelshift','opengate-nraw','locked-banks')
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
    strings = Strings()
    detail = {}

    def merge(feature, source):
        for e in source.edits:
            img.put(e['offset'],e['new'],feature+': '+e['purpose'])

    if 'prores' in chosen:
        from z8prores.menu import build_main
        part, detail['prores'] = build_main(eg,strings)
        merge('prores',part)
    if 'precapture' in chosen:
        from z8precapture.patcher import edits
        code, meta = load('precapture',code_source,compiler)
        for e in edits(code,meta['symbols']):
            img.put(e['offset'],e['new'],e['purpose'])
        detail['precapture'] = dict(code_sha256=meta['sha256'],code_bytes=len(code),
                                    diagnostics=False,space_fallback=True,remaining_count=True)
    if 'pixelshift' in chosen:
        from z8pixelshift.patcher import build_main
        code, meta = load('pixelshift',code_source,compiler)
        af, _ = load('pixelshift-af',code_source,compiler)
        part, detail['pixelshift'] = build_main(eg,code,meta['symbols'],af,strings)
        merge('pixelshift',part)
    if 'opengate-nraw' in chosen:
        from z8opengate.patcher import build_main
        code, meta = load('opengate',code_source,compiler)
        entries = {k:int(v['va'],16) for k,v in meta['symbols'].items()}
        part, detail['opengate-nraw'] = build_main(eg,code,entries,strings)
        merge('opengate-nraw',part)
    if 'locked-banks' in chosen:
        from z8lockbank.patcher import build_main
        part, detail['locked-banks'] = build_main(eg)
        merge('locked-banks',part)
    detail['strings'] = strings.emit(img)
    detail['bank'] = bank(img,chosen)
    detail['loader'] = loader(img,chosen)
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
