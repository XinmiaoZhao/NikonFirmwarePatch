"""v0.5.1 open-gate fixes: enter the unit linked at 0x40968000 (z8opengate/fixes/hooks.S).

Applied after the open-gate and anamorphic units, on their composed bytes:
- 4.1K N-RAW 3:2 AF geometry, standby and recording: the two AF geometry
  calls and the two conversion branches enter the unit instead of the
  open-gate AF hooks, which the unit then calls.
- Movie playback fit 407138D0 enters the slot-limited fit, which runs the
  anamorphic/open-gate chain.
- The anamorphic AF point routine enters the cell height and row mapping.
- The stock local movie output pool 6 slot grows from 0x151800 to 0x18D800
  bytes (1,628,160 B, one 1280x848 NV12 frame), so an open-gate clip plays
  full width in the EVF.  The template serves every local movie playback.
"""
import struct
from z8patch.image import Image, branch, movz
from z8prores.package import require

CAVE, CAVE_END = 0x40968000, 0x4096F000
# Addresses the unit was linked against (its #defines); each must still name
# the same open-gate or anamorphic symbol.
OPENGATE = {'af_geometry_hook': 0x40961D50, 'af_forward_hook': 0x40961B00, 'af_inverse_hook': 0x40961BD0}
ANAMORPHIC = {'ap_playback_fit_hook': 0x409708F0, 'ap_map': 0x409702C0, 'ap_ratios': 0x40970C10,
              'ap_points_scale': 0x409704B0, 'ap_points_scale_next': 0x409704B4, 'ap_points_done': 0x4097050C}
GEOMETRY_CALLS = (0x41055AC0, 0x410567DC)
FORWARD, INVERSE = 0x41055B38, 0x4105693C
PLAYBACK_FIT = 0x407138D0
POOL_SLOT_LO, POOL_SLOT_HI = 0x40CF4620, 0x40CF4630
SLOT, STOCK_SLOT = 0x18D800, 0x151800
REFINED = (*GEOMETRY_CALLS, FORWARD, INVERSE, PLAYBACK_FIT, ANAMORPHIC['ap_points_scale'])


def movk_w(rd, imm, shift):
    return struct.pack('<I', 0x72800000 | (shift // 16) << 21 | imm << 5 | rd)


def build_main(eg, code, entries, opengate, anamorphic):
    for names, unit in ((OPENGATE, opengate), (ANAMORPHIC, anamorphic)):
        for name, address in names.items():
            require(unit.get(name) == address, 'Open-gate fixes: extended unit moved: ' + name)
    require(entries['af_geometry'] == CAVE and CAVE + len(code) <= CAVE_END, 'Open-gate fixes: unit placement')
    img = Image(eg)
    img.put(CAVE, code, '3:2 AF geometry, playback fit, AF points', expect_zero=True)
    for site in GEOMETRY_CALLS:
        img.put(site, branch(site, entries['af_geometry'], link=True), '3:2 AF planes',
                expect=branch(site, OPENGATE['af_geometry_hook'], link=True))
    img.put(FORWARD, branch(FORWARD, entries['af_forward']), '3:2 AF forward',
            expect=branch(FORWARD, OPENGATE['af_forward_hook']))
    img.put(INVERSE, branch(INVERSE, entries['af_inverse']), '3:2 AF inverse',
            expect=branch(INVERSE, OPENGATE['af_inverse_hook']))
    img.put(PLAYBACK_FIT, branch(PLAYBACK_FIT, entries['evf_fit_hook']), 'one-slot playback fit',
            expect=branch(PLAYBACK_FIT, ANAMORPHIC['ap_playback_fit_hook']))
    scale = ANAMORPHIC['ap_points_scale']
    img.put(scale, branch(scale, entries['points_source']), '3:2 AF point cells',
            expect=struct.pack('<I', 0x6B170309))                      # subs w9, w24, w23
    # One window over movz (40CF4620) .. movk (40CF4630); the three instructions between stay stock.
    stock = bytes(img.old[POOL_SLOT_LO - 0x40160000:POOL_SLOT_HI + 4 - 0x40160000])
    require(stock[:4] == movz(13, STOCK_SLOT & 0xFFFF, w=True) and stock[16:] == movk_w(13, STOCK_SLOT >> 16, 16),
            'Open-gate fixes: unexpected movie output slot instructions')
    img.put(POOL_SLOT_LO, movz(13, SLOT & 0xFFFF, w=True) + stock[4:16] + movk_w(13, SLOT >> 16, 16),
            'movie output slot 0x18D800', expect=stock)
    detail = dict(code=hex(CAVE), code_bytes=len(code), entries={k: hex(v) for k, v in sorted(entries.items())},
                  movie_output_slot_bytes=SLOT, stock_movie_output_slot_bytes=STOCK_SLOT,
                  af_geometry_sites=[hex(s) for s in (*GEOMETRY_CALLS, FORWARD, INVERSE)],
                  playback_fit=hex(PLAYBACK_FIT), af_points=hex(scale))
    return img, detail
