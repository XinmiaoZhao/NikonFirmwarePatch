#!/usr/bin/env python3
"""Check the macOS app text: the feature catalog against the toolkit and its documents, and the
interface String Catalog for complete translations. No firmware, compiler or capstone."""
import ast
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'resources/gui-catalog.json'
APP_STRINGS = ROOT / 'macos/Resources/Localizable.xcstrings'
TEXT_FIELDS = ('name', 'summary', 'intro', 'camera_entry')
LANGS = ('en', 'zh-Hans', 'zh-Hant')
# Characters that exist only in one Chinese script, to catch text pasted into the wrong language.
# Characters shared by both scripts (之, 于, 里, 后, 准, 范 ...) are deliberately left out.
SIMPLIFIED_ONLY = set('与丢两个为产仅从仓仪会体侧储关内写冲决况减则创删别动区单压厂发变叠号启围图坏块处备复头夹实审对导将属带帧帮库应开'
                      '张当录护报担拟择挤损换摄数断无旧时显暂机来构标栏档检残没浅测满点独现电画盖码确积种称签简类级纹线组细绍经结'
                      '绘统继绪续缓编缘缩脑节荐蓝补装见观视计认议记许设证识译试该详语误说请读贝负败质软载辅辑输边过运还这进连选逻'
                      '键镜长门闭问间阅阵际险随隐隶顶项顺须预频题风饱馈验')
TRADITIONAL_ONLY = set('並佈佔來個側偵備僅儀儲內兩別刪則劃動匯區問啟單圍圖執報壓壞夾實審寫將專對導屬帶幀庫廠張後從復應採換損擇擔擬攝'
                       '敗數斷時暫會條標機檔檢權決沒況淺減測準滿為無獨現產畫疊發確碼種稱積節範簡籤紋細紹組結統經緒線緣編緩縮繪繼續'
                       '腦與舊藍處號衝補裝裡製複見規視觀計訊記設許試詳認語誤說請證譯議護讀變讓貝負資質軟載輔輯輸這連進運過適選遺還'
                       '邊邏錄鍵鏡長門閉開間閱關陣階際隨險隱隸離電韌頂項順須預頭頻題類顯風飽餘驗體點')
SPEC = re.compile(r'%(?:(\d+)\$)?(lld|ld|d|@|lf|f)')


def need(ok, message):
    if not ok:
        raise SystemExit('FAIL: ' + message)


def features_tuple():
    """Read features.FEATURES without importing the builder (which needs capstone)."""
    tree = ast.parse((ROOT / 'features.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'FEATURES' for t in node.targets):
            return tuple(ast.literal_eval(node.value))
    raise SystemExit('FAIL: features.FEATURES not found')


def script(text, lang, where):
    wrong = {'zh-Hans': TRADITIONAL_ONLY, 'zh-Hant': SIMPLIFIED_ONLY}.get(lang, set()) & set(text)
    need(not wrong, f'{where}: {lang} text has characters of the other script: ' + ''.join(sorted(wrong)))


def localized(value, where):
    need(isinstance(value, dict) and set(value) == set(LANGS), where + ': expected exactly ' + ', '.join(LANGS))
    for lang in LANGS:
        need(isinstance(value[lang], str) and value[lang].strip() == value[lang] and value[lang], where + ': empty or padded ' + lang)
        script(value[lang], lang, where)


def specifiers(text):
    """Format arguments in order of position, e.g. ['@', 'lld'] for '%2$lld … %1$@'."""
    found = SPEC.findall(text.replace('%%', ''))
    if any(n for n, _ in found):
        need(all(n for n, _ in found), 'mixed positional and plain specifiers in ' + repr(text))
        return [t for _, t in sorted(found, key=lambda f: int(f[0]))]
    return [t for _, t in found]


def check_app_strings():
    """Every interface string has a translated zh-Hans and zh-Hant value with the key's arguments."""
    record = json.loads(APP_STRINGS.read_text(encoding='utf-8'))
    need(record.get('sourceLanguage') == 'en', 'Localizable.xcstrings: source language must be en')
    count = plurals = 0
    for key, entry in record['strings'].items():
        where = 'Localizable.xcstrings ' + repr(key)
        need(entry.get('extractionState') != 'stale', where + ': stale (no longer in the code)')
        if entry.get('shouldTranslate') is False:
            continue
        args = specifiers(key)
        locs = entry.get('localizations', {})
        for lang in LANGS[1:]:
            unit = locs.get(lang, {}).get('stringUnit', {})
            need(unit.get('state') == 'translated' and unit.get('value', '').strip(), f'{where}: no {lang} translation')
            need(specifiers(unit['value']) == args, f'{where}: {lang} arguments differ from the key')
            script(unit['value'], lang, where)
        en = locs.get('en', {})
        for name, sub in en.get('substitutions', {}).items():
            forms = sub['variations']['plural']
            need({'one', 'other'} <= set(forms), f'{where}: plural {name} needs one and other')
            plurals += 1
        count += 1
    return count, plurals


def main():
    record = json.loads(CATALOG.read_text(encoding='utf-8'))
    need(record.get('schema') == 2, 'schema must be 2')
    rows = record['features']
    need(tuple(r['id'] for r in rows) == features_tuple(), 'feature ids/order differ from features.FEATURES')
    checked = dict(limits=0, quotes=0, docs=0, guide_steps=0)
    for row in rows:
        fid = row['id']
        for field in TEXT_FIELDS:
            localized(row[field], f'{fid}.{field}')
        need(row['includes'], fid + ': includes empty')
        for i, item in enumerate(row['includes']):
            localized(item, f'{fid}.includes[{i}]')
        need(row['limits'], fid + ': no limits listed')
        for i, limit in enumerate(row['limits']):
            where = f'{fid}.limits[{i}]'
            need(limit['level'] in ('caution', 'note'), where + ': level')
            localized(limit['title'], where + '.title')
            localized(limit['detail'], where + '.detail')
            source = ROOT / limit['source']['path']
            need(source.is_file() and source.resolve().is_relative_to(ROOT), where + ': missing source ' + limit['source']['path'])
            need(limit['source']['quote'] in source.read_text(encoding='utf-8'), where + ': quote not found in ' + limit['source']['path'])
            checked['limits'] += 1
            checked['quotes'] += 1
        need(row['docs'], fid + ': no documents')
        for i, doc in enumerate(row['docs']):
            localized(doc['title'], f'{fid}.docs[{i}].title')
            need((ROOT / doc['path']).is_file(), f'{fid}.docs[{i}]: missing ' + doc['path'])
            checked['docs'] += 1
        need(3 <= len(row['guide']) <= 6, fid + ': guide needs 3-6 steps')
        for i, step in enumerate(row['guide']):
            localized(step, f'{fid}.guide[{i}]')
            checked['guide_steps'] += 1
    checked['app_strings'], checked['app_plurals'] = check_app_strings()
    print(json.dumps(dict(status='PASS', features=len(rows), languages=list(LANGS), **checked), indent=2))


if __name__ == '__main__':
    main()
