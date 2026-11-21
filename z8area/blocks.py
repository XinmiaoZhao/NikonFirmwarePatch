import struct

ROM, DOFF, DVA = 0x40160000, 0x4B13000, 0xA02808000
def off(va): return va - DVA + DOFF if va >= DVA else va - ROM
def words(stock, va, n): return list(struct.unpack_from('<%dI' % n, stock, off(va)))
def ptrs(stock, va): return list(struct.unpack_from('<9Q', stock, off(va)))
T = dict(k0=0xA02A960A0, k1=0xA02A96160, s0=0xA02A961B0, s1=0xA02A96270)
P = lambda lo, hi: (lo & 0xffff) | (hi & 0xffff) << 16
f16 = lambda v: v // 16 * 16
f8 = lambda v: v // 8 * 8

# geometry per area: kind 0 = JPEG L size, crop edge, origin in the 8280x5520 frame; kind 1 = live-view crop in 2756x1836
STILL = {0: dict(W=8256, H=5504, cx=12, cy=8, x0=0, y0=0), 1: dict(W=5392, H=3592, cx=8, cy=8, x0=1436, y0=956),
         4: dict(W=8256, H=4640, cx=12, cy=8, x0=0, y0=432), 8: dict(W=5504, H=5504, cx=8, cy=8, x0=1380, y0=0)}
LIVE = {0: dict(W=2748, H=1832, ox=4, oy=2), 1: dict(W=1796, H=1196, ox=480, oy=320), 4: dict(W=2752, H=1544, ox=2, oy=146),
        5: dict(W=1796, H=1008, ox=480, oy=414), 8: dict(W=1832, H=1832, ox=462, oy=2)}
DX_READOUT = {1, 5}


def pow2_for(v):
    n = 1
    while v * n < 4096: n *= 2
    return n


def grid(Wh, Hh, nx, ny, bw, bh):
    """Statistics grid: nx*ny cells of bw x bh, centred in the half-size image; second grid uses square bw cells."""
    xs1, ys1 = (Wh - nx * bw) // 2, (Hh - ny * bh) // 2
    xs2, ys2 = xs1 - 4, ((Hh - ny * bw) // 2) // 8 * 8
    return xs1, ys1, xs2, ys2


def record(src_w, src_h, out_w, out_h):
    """Scaler record (0x14 bytes): origin 0, ratio floor(64*src/out) per axis, output size."""
    return [0, 0, P(64 * src_w // out_w, 64 * src_h // out_h), 0, P(out_w, out_h)]


def block178(kind, g, cells, rec0, rec2, donor, scale):
    """Rebuild a 0x178 block; `scale` = processing divisor (2 for FX-readout still/live, 1 for DX live)."""
    w = list(donor)
    W, H = g['W'], g['H']
    if kind == 0:
        w[0], w[1] = P(W, g['x0'] + g['cx']), P(H, g['y0'] + g['cy'])
    else:
        w[0], w[1] = P(W, g['ox']), P(H, g['oy'])
    Wh, Hh = W // scale, H // scale
    nx, ny, bw, bh = cells
    xs1, ys1, xs2, ys2 = grid(Wh, Hh, nx, ny, bw, bh)
    cnt, cnt2 = nx | ny << 8, (2 * nx) | (2 * ny) << 8
    w[0x10 // 4] = P(0xa7, xs1); w[0x14 // 4] = P(ys1, bw); w[0x18 // 4] = P(bh, bw); w[0x1c // 4] = P(bh, cnt)
    w[0x7c // 4] = P(xs2, ys2); w[0x80 // 4] = P(bw, bw); w[0x84 // 4] = P(cnt, xs2); w[0x88 // 4] = P(ys2, bw // 2)
    w[0x8c // 4] = P(bw // 2, cnt2); w[0x90 // 4] = w[0x7c // 4]; w[0x94 // 4] = P(bw // 2, bw // 2)
    w[0x98 // 4] = P(cnt2, xs2); w[0x9c // 4] = w[0x88 // 4]; w[0xa0 // 4] = w[0x8c // 4]
    cx = g.get('cx', g.get('ox_edge', 0))
    sw, sh = f16(W - cx) if kind == 0 else f16(W - g.get('edge', 0)), f16(H)
    w[0xfc // 4:0x110 // 4] = record(sw, sh, *rec0)
    w[0x124 // 4:0x138 // 4] = record(sw, sh, *rec2)
    w[0x14c // 4:0x160 // 4] = record(sw, sh, *rec2)
    if kind == 0:
        Wp, Hp = Wh - 8, f8(Hh)
        nxp, nyp = pow2_for(Wp), pow2_for(Hp)
        w[0x160 // 4] = Wp << 16; w[0x164 // 4] = Hp << 16
        w[0x168 // 4] = ((1 << 20) // (Wp * nxp)) << 16; w[0x16c // 4] = nxp
        w[0x170 // 4] = (1 << 20) // (Hp * nyp); w[0x174 // 4] = nyp.bit_length()
    return w
