"""Compose still-picture geometry, display, menu and file metadata from stock C3.11."""
from . import quick_picker, thumbnail
import re
import struct
from . import blocks, class_clamps, focus_bounds, icons_wide, layout, menu, playback_wide, wide
from z8patch.image import BASE, branch, data_off
from z8prores.package import require

def size_labels(base, stock):
    wh = {}
    for area in (2, 3, 6):
        ptr = struct.unpack_from('<Q', base, data_off(0xA0297A568 + area * 8))[0]
        wh[area] = [struct.unpack_from('<HH', base, data_off(ptr) + size * 4) for size in range(3)]
    labels = {}
    for lang in range(36):
        tab = struct.unpack_from('<Q', base, 0x311C5A0 + lang * 8)[0] - BASE
        blob = struct.unpack_from('<Q', base, 0x387AF58 + lang * 8)[0] - BASE
        offs = list(struct.unpack_from('<3137i', stock, tab))
        get = lambda i: stock[blob + offs[i]:blob + offs[i + 1]].decode('utf-16le')
        template = get(0x535)
        # Preserve language-specific grouping, decimal separator, unit and RTL marker.
        match = re.search(r'8([., ]?)256(.*?)5([., ]?)504(.*?)45([.,])4', template)
        assert match, (lang, template)
        fmt = lambda value, sep: f'{value // 1000}{sep}{value % 1000:03}' if sep else str(value)
        labs = []
        for area in (2, 3, 6):
            for w, h in wh[area]:
                mp = (w * h + 50000) // 100000
                replacement = (fmt(w, match[1]) + match[2] + fmt(h, match[3]) + match[4]
                               + str(mp // 10) + match[5] + str(mp % 10))
                label = template[:match.start()] + replacement + template[match.end():]
                labs.append(label)
        labels[lang] = labs
    return [list(menu.labels_for(stock,k)[0])+labels[k] for k in range(36)]

def refine(img, va, data, expected, purpose):
    start = data_off(va)
    stop = start+len(data)
    require(bytes(img.new[start:stop])==expected and len(expected)==len(data),purpose+' preimage')
    matches = [e for e in img.edits if e['offset'] < stop and start < e['end']]
    if not matches:
        img.put(start, data, purpose, expect=expected, offset=True)
        return
    require(len(matches)==1 and matches[0]['offset']<=start and stop<=matches[0]['end'],purpose+' coverage')
    row = matches[0]
    img.new[start:stop] = data
    row['new'] = bytes(img.new[row['offset']:row['end']])
    row['purpose'] += ' / '+purpose


def build_main(stock, strings, unit, star_entries=None):
    img, _ = focus_bounds.compose(stock)
    wide.apply(img,stock,blocks,layout,dict(cave_a=0x40B7C400,cave_b=0x40B7C440,
                                           corner=focus_bounds.CAVE_CORNER2,points=focus_bounds.G.CAVE_POINTS))
    icons = icons_wide.apply(img,stock)
    if star_entries is not None:
        # Unknown photo icons retain the entire video star and open-gate lookup chain.
        for site, name, old in ((0x40B84038,'tier_star_res_idx',0xD299AB09),
                                (0x40B840AC,'tier_star_res_val',0xD299AB08)):
            refine(img,site,branch(site,star_entries[name]),struct.pack('<I',old),'fall through to video icons')
    menu_info = menu.apply(img,stock,icons={int(k):int(v,16) for k,v in icons['menu_row_icon'].items()})
    playback_wide.apply(img,stock)
    class_clamps.apply(img,stock)
    ids = strings.add('photo-areas',size_labels(img.new,stock))
    require(ids==list(range(3238,3250)), 'Crop labels')
    code, entries = unit('area-sizes')
    img.put(0x40B82000,code,'localized image sizes and native playback size rules',expect_zero=True)
    sites = [(0x405DB4BC, 'lms_menu_hook', 0x7100201F),
             (0x405E5CC8, 'lms_alt_l_hook', 0x7100201F),
             (0x405E5D68, 'lms_alt_m_hook', 0x7100201F),
             (0x405E5E08, 'lms_alt_s_hook', 0x7100201F),
             (0x406C2508, 'lms_metadata_hook', 0xB9426E88),
             (0x407970E8, 'lms_playback_hook', 0x1400000A)]
    for va, name, expected in sites:
        img.put(va,branch(va,entries[name]),name,expect=struct.pack('<I',expected))
    for va, fmt, old, new in (
        (0xA029CB68C, 'I', 2, 0), (0x40B90854, 'I', 0x01560480, 0x01520488),
        (0x40B90864, 'I', 0x002C0000, 0x002C0002), (0x40B9096A, 'H', 257, 256),
        (0x40B90972, 'H', 286, 288), (0x40B90A14, 'I', 0x01560002, 0x01520002),
        (0x40B90A44, 'I', 0x04800AC0, 0x04880AC0), (0x40B90A32, 'H', 286, 288),
        (0xA02A96288, 'Q', 0x40B90A10, 0x40B91040)):
        refine(img, va, struct.pack('<'+fmt,new), struct.pack('<'+fmt,old),'single-arm geometry / crop metadata')
    block = bytearray(img.new[0x40B90D90-BASE:0x40B90DC8-BASE])
    for at, value in ((6,338),(0x36,1160),(10,576),(14,576),(0x32,576)):
        struct.pack_into('<H', block, at, value)
    img.put(0x40B91040,block,'C-low descriptor for every quality',expect_zero=True)
    code, labels = unit('area-formula')
    img.put(0x40B7D800,code,'C-low formula and 2.39 AF coordinate transforms',expect_zero=True)
    img.put(0x410B7C64,branch(0x410B7C64,0x40B7D800),'C-low formula dispatch',expect=struct.pack('<I',0x540000AB))
    for site, word, name in (
        (0x41056978, 0x710021df, 'crop_tracking_to_sensor'),
        (0x41055b64, 0x7100203f, 'crop_tracking_from_sensor'),
    ):
        img.put(site, branch(site, labels[name]), name, expect=struct.pack('<I', word))
    code, labels = unit('area-thumbnail')
    for va, before, after in thumbnail.edits(code, labels):
        refine(img, va, after, before, 'XPan HIF small preview and buffer reservation')
    code, labels = unit('area-quick')
    for va, before, after in quick_picker.edits(img.new, code, labels):
        refine(img, va, after, before, 'quick crop controls')
    return img, dict(rows=menu_info['rows'], area_icons=icons['menu_row_icon'], labels=ids,
                     geometry=[1368,576], loader_floor=hex(0x40BA0000))
