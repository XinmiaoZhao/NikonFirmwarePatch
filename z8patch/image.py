"""Checked byte edits using ROM addresses, or explicitly marked EG offsets."""
import struct
from z8prores.menu import Image as OffsetImage
from z8prores.package import require

BASE = 0x40160000
DATA_OFF, DATA_END, DATA_VA = 0x4B13000, 0x4DC0000, 0xA02808000


class Image(OffsetImage):
    def put(self, address, data, purpose, expect=None, expect_zero=False, offset=False):
        at = address if offset else address - BASE
        super().put(at, data, purpose, expect_zero=expect_zero, expect=expect)

    def u32(self, address):
        return struct.unpack_from('<I', self.old, address - BASE)[0]


def va(offset):
    return BASE + offset


def data_off(address):
    if DATA_VA <= address < DATA_VA + DATA_END - DATA_OFF:
        return address - DATA_VA + DATA_OFF
    require(BASE <= address < BASE + 0x6000000, 'Unknown address')
    return address - BASE


def branch(address, target, link=False):
    delta = target - address
    require(delta % 4 == 0 and -(1 << 27) <= delta < (1 << 27), 'Branch outside range')
    return struct.pack('<I', (0x94000000 if link else 0x14000000) | ((delta // 4) & 0x3ffffff))


def movz(rd, imm, w=False, shift=0):
    require(0 <= imm < 65536, 'MOVZ immediate')
    return struct.pack('<I', (0x52800000 if w else 0xD2800000) | (shift // 16) << 21 | imm << 5 | rd)


def movk(rd, imm, shift):
    return struct.pack('<I', 0xF2800000 | (shift // 16) << 21 | imm << 5 | rd)


def table_copy(eg, pointer, change, limit=64):
    out = bytearray()
    for i in range(limit):
        record = struct.unpack_from('<4Q', eg, data_off(pointer) + 32 * i)
        out += struct.pack('<4Q', *change(*record))
        if record[0] == 0x3BB:
            return bytes(out)
    raise ValueError('Transition table lacks its terminator')
