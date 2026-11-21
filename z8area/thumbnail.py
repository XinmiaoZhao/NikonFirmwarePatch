"""HIF-only small preview dimensions plus matching compressed output capacity."""
import struct

BASE = 0x40160000
THUMB = 0x40B91200
CAPACITY = 0x40B9017C


def branch(at, target, link=False):
    delta = target-at
    if delta%4 or not -(1<<27) <= delta < (1<<27):
        raise ValueError('Branch out of range')
    return struct.pack('<I', (0x94000000 if link else 0x14000000) | (delta//4 & 0x3ffffff))


def edits(code, symbols):
    yield THUMB, bytes(len(code)), code
    site = 0x4105F9E8
    yield site, branch(site,0x410619F0,True), branch(site,symbols['hif_size'],True)
    for site in (0x41060678, 0x41060724):
        old = bytes.fromhex('008c42b9') + branch(site+4,0x410619F0,True)
        new = bytes.fromhex('1f2003d5') + branch(site+4,symbols['snapshot_size'],True)
        yield site, old, new
    # Both the size calculator and the partitioner call 41045894. The
    # reservation is shared with JPEG, whose visible dimensions stay intact.
    def capacity(w,h):
        fine = (((w+31)//32 * 2)*h*13 + 639)//640
        return struct.pack('<3I', *(512*((fine+d-1)//d) for d in (1,2,4)))
    yield CAPACITY, capacity(320,116), capacity(352,130)
