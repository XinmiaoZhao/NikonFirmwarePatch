import struct
from . import geometry as A
hb1, sha, data_off, W = A.hb1, A.sha, A.data_off, A.W

RAWOUT, STRIDE = 0xA02A244A4, 0x28
RAW43 = (7360, 5520)


def rawout(w, h):
    r32 = lambda x: (x + 31) & ~31
    c512 = lambda x: -(-x // 512) * 512
    b12, b14 = r32(w * 12 // 8) * h, r32(w * 14 // 8) * h
    b5, b3 = r32(w * 5 // 8) * h, r32(w * 3 // 8) * h
    return [b12, b12, c512(-(-b12 * 7 // 10)), b5, b3, b14, b14, c512(-(-b14 * 26 // 35)), b5, b3]


def compose(eg):
    img, det = A.compose(eg)
    rawtab = A.SIZE_TABLES['raw'][0]; rule = {}
    for area in (0, 1, 4, 8):                       # areas with a stock RAW size entry
        word = A.u32(eg, A.u64(eg, rawtab + 8 * area)); w, h = word & 0xFFFF, word >> 16
        stock = list(struct.unpack_from('<10I', eg, data_off(RAWOUT + STRIDE * area)))
        assert stock == rawout(w, h), (area, w, h, stock, rawout(w, h)); rule[area] = [w, h]
    word = A.u32(eg, A.u64(eg, rawtab + 8 * 2)) if A.u64(eg, rawtab + 8 * 2) else None
    assert word is None or word == 0, 'stock slot-2 RAW size entry is expected empty'
    assert int(A.SIZES['words']['raw'][0], 16) == RAW43[0] | RAW43[1] << 16    # same RAW size as A2 writes to the size table
    words = rawout(*RAW43)
    img.put(data_off(RAWOUT + STRIDE * 2), W(*words), f'RAW output size table {RAWOUT:#x} (getter 0x410457a4) area 2: 4:3 {RAW43[0]}x{RAW43[1]}',
            expect_zero=True, offset=True)
    det['raw_out'] = dict(table=hex(RAWOUT), stride=hex(STRIDE), area2=words, rule_reproduces=rule)
    return img, det
