from z8patch.image import BASE, DATA_END, Image, data_off, va
from z8prores.package import sha

GAP = (0x408BF8F0, 0x40C00000)
LOADER_END = GAP[0]
LOADER_SITE = 0x1024D8C

SECTION_VA, SECTION_ROOM = 0x40200000, 0xA00000
