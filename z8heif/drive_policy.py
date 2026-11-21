"""Patch the stable F9 code before its template and menu are installed."""
import struct

BASE = 0x40B70000
AT = 0x40B71B00
SITES = (
    (0x0D8, '699642b9', 'drive_snap', False),
    (0x2F8, '405790d2', 'drive_choice', False),
    (0x314, '495790d2', 'drive_choice', False),
    (0x3A8, 'dbffff97', 'drive_enter', True),
    (0x3E4, '090040f9', 'drive_ok', False),
    (0x670, '495790d2', 'drive_tone', False),
)


def redirect(code, entries):
    for offset, expected, name, link in SITES:
        if code[offset:offset+4] != bytes.fromhex(expected):
            raise ValueError(f'Unexpected F9 format instruction at {BASE+offset:#x}')
        delta = entries[name] - (BASE + offset)
        if delta % 4 or not -(1<<27) <= delta < (1<<27):
            raise ValueError('Drive hook outside branch range')
        word = (0x94000000 if link else 0x14000000) | ((delta//4) & 0x3ffffff)
        struct.pack_into('<I', code, offset, word)
