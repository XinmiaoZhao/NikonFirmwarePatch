"""Public source adapted from the pinned research implementation; regular files only."""
from z8prores.package import require
import struct
CAVE = 1083572224

def link_elf(raw, base):
    CAVE = base
    require(raw[:6] == b'\x7fELF\x02\x01', 'Unexpected firmware structure')
    require(struct.unpack_from('<H', raw, 18)[0] == 183, 'Unexpected firmware structure')
    shoff = struct.unpack_from('<Q', raw, 40)[0]
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', raw, 58)
    require(shentsize == 64, 'Unexpected firmware structure')
    sections = [struct.unpack_from('<IIQQQQIIQQ', raw, shoff + i * 64) for i in range(shnum)]

    def data(s):
        return raw[s[4]:s[4] + s[5]]

    def string(blob, at):
        return blob[at:blob.index(0, at)].decode()
    names = data(sections[shstrndx])
    byname = {string(names, s[0]): i for i, s in enumerate(sections)}
    for section in sections:
        require(not (section[2]&2 and section[5]) or string(names,section[0])=='.text', 'Unexpected allocated assembly section')
    ti = byname['.text']
    text = bytearray(data(sections[ti]))
    ss = sections[byname['.symtab']]
    strings = data(sections[ss[6]])
    symbols = []
    for at in range(ss[4], ss[4] + ss[5], ss[9]):
        name, info, other, section, value, size = struct.unpack_from('<IBBHQQ', raw, at)
        symbols.append(dict(name=string(strings, name), section=section, value=value, size=size))
    relocated = []
    for s in sections:
        if s[1] != 4:
            continue
        require(s[7] == ti and s[9] == 24, 'Unexpected firmware structure')
        for at in range(s[4], s[4] + s[5], 24):
            off, info, addend = struct.unpack_from('<QQq', raw, at)
            kind, si = (info & 4294967295, info >> 32)
            sym = symbols[si]
            require(kind in (282, 283), (kind, sym))
            if sym['section'] == ti:
                target = CAVE + sym['value'] + addend
            else:
                require(sym['section'] == 0 and sym['name'].startswith('original_'), sym)
                target = int(sym['name'].removeprefix('original_'), 16) + addend
            pc = CAVE + off
            delta = target - pc
            require(delta % 4 == 0 and -(1 << 27) <= delta < 1 << 27, 'Unexpected firmware structure')
            word = struct.unpack_from('<I', text, off)[0]
            require(word & 4227858432 == (335544320 if kind == 282 else 2483027968), 'Unexpected firmware structure')
            struct.pack_into('<I', text, off, word & 4227858432 | delta // 4 & 67108863)
            relocated.append(dict(pc=hex(pc), target=hex(target), kind=kind, symbol=sym['name']))
    entries = {s['name']: CAVE + s['value'] for s in symbols if s['section'] == ti and s['name'] and not s['name'].startswith('$')}
    return (bytes(text), entries, relocated)
