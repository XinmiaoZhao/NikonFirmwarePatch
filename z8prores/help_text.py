"""Localize the 422 family heading without changing the actual recording grades."""
import re
import struct


def family_help(text):
    updated, count = re.subn(r'ProRes 422 ?HQ', 'ProRes 422', text)
    if count != 1:
        raise ValueError('Expected one ProRes 422 HQ heading in the file-type help')
    return updated


def apply_stock_help(img):
    # Each translation is length-delimited by two shared offsets. Keep the
    # line length on disk with trailing blanks, leaving every other ID intact.
    windows = {}
    for language in range(36):
        table = struct.unpack_from('<Q', img.old, 0x311C5A0 + 8 * language)[0] - 0x40160000
        blob = struct.unpack_from('<Q', img.old, 0x387AF58 + 8 * language)[0] - 0x40160000
        start, end = struct.unpack_from('<2i', img.old, table + 4 * 0xA17)
        text = img.old[blob + start:blob + end].decode('utf-16le')
        family_help(text)
        match = re.search(r'ProRes 422 ?HQ[^\n]*', text)
        line = match.group()
        fixed = family_help(line).ljust(len(line))
        offset = blob + start + len(text[:match.start()].encode('utf-16le'))
        windows[offset] = (line.encode('utf-16le'), fixed.encode('utf-16le'))
    for offset, (old, new) in sorted(windows.items()):
        img.put(offset, new, 'ProRes 422 family in video file-type help', expect=old)
