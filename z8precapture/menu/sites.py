"""Factory C 3.11 photo menu call sites and their displaced instructions."""
BASE = 0x409FF000   # the last 4 KiB of the pre-capture cave; the pre-capture unit may use 0x409F0000..0x409FF000
SITES = (
    (0x4049D674, 'raw_menu_size_alt', True, 0x403ACCCC),
    (0x405D9B40, 'raw_menu_value', True, 0x403EC398),
    (0x405DB6CC, 'raw_menu_enter', True, 0x403EC398),
    (0x405E6990, 'raw_menu_lossless', False, None),
    (0x405E69A0, 'raw_menu_star', False, None),
)

def apply(image, code, entries):
    import struct
    B = 0x40160000
    def branch(site,to,link):
        delta=to-site
        if delta%4 or not -(1<<27)<=delta<1<<27:raise ValueError('Invalid menu branch')
        return struct.pack('<I',(0x94000000 if link else 0x14000000)|((delta//4)&0x3ffffff))
    if BASE+len(code)>0x40A00000 or any(image[BASE-B:BASE-B+len(code)]):
        raise ValueError('RAW menu allocation is occupied')
    yield BASE,bytes(len(code)),code
    for site,name,link,original in SITES:
        old = branch(site,original,link) if original else bytes.fromhex('00c18052')
        if image[site-B:site-B+4]!=old: raise ValueError(f'Unexpected RAW menu bytes at {site:#x}')
        yield site,old,branch(site,entries[name],link)

    # The source-bank byte is read into w10 inside the live descriptor builder.
    # Each ordinary quality role has five callbacks; replace only callback 4
    # (secondary disabled), leaving the other roles sharing its stub untouched.
    for site, old, new in (
        (0x40441104, bytes.fromhex('4a014039'), branch(0x40441104, entries['raw_menu_size_live'], False)),
        (0x42AEA178, struct.pack('<Q', 0x4043EBA0), struct.pack('<Q', entries['raw_menu_size_disabled'])),
        (0x42AF6460, struct.pack('<Q', 0x4049B9B8), struct.pack('<Q', entries['raw_menu_size_disabled'])),
    ):
        if image[site-B:site-B+len(old)] != old:
            raise ValueError(f'Unexpected quality/size role bytes at {site:#x}')
        yield site, old, new
