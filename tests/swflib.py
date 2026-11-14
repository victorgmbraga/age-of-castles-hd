"""Leitura e escrita mínimas de SWF, para os testes automáticos."""
import struct
import zlib


class BitWriter:
    def __init__(self):
        self.bits = []

    def u(self, v, n):
        self.bits += [(v >> (n - 1 - i)) & 1 for i in range(n)]

    def s(self, v, n):
        self.u(v & ((1 << n) - 1), n)

    def bytes(self):
        b = self.bits + [0] * (-len(self.bits) % 8)
        return bytes(int("".join(map(str, b[i:i + 8])), 2) for i in range(0, len(b), 8))


class BitReader:
    def __init__(self, data, pos=0):
        self.data, self.bit = data, pos * 8

    def u(self, n):
        v = 0
        for _ in range(n):
            v = (v << 1) | ((self.data[self.bit // 8] >> (7 - self.bit % 8)) & 1)
            self.bit += 1
        return v

    def s(self, n):
        v = self.u(n)
        return v - (1 << n) if n and v >> (n - 1) else v

    def align(self):
        self.bit = -(-self.bit // 8) * 8
        return self.bit // 8


def nbits(*vals):
    return max(max(abs(v).bit_length() for v in vals) + 1, 1)


def rect(w, x0, x1, y0, y1):
    n = nbits(x0, x1, y0, y1)
    w.u(n, 5)
    for v in (x0, x1, y0, y1):
        w.s(v, n)


def matrix(w, scale=None, tx=0, ty=0):
    if scale is None:
        w.u(0, 1)
    else:
        f = round(scale * 65536)
        n = nbits(f)
        w.u(1, 1); w.u(n, 5); w.s(f, n); w.s(f, n)
    w.u(0, 1)  # sem rotação
    n = nbits(tx, ty) if (tx or ty) else 0
    w.u(n, 5)
    if n:
        w.s(tx, n); w.s(ty, n)


def read_matrix(r):
    sx = sy = 1.0
    if r.u(1):
        n = r.u(5); sx = r.s(n) / 65536; sy = r.s(n) / 65536
    if r.u(1):
        n = r.u(5); r.s(n); r.s(n)
    n = r.u(5); r.s(n); r.s(n)
    return sx, sy


def tag(code, body, long=False):
    if len(body) < 63 and not long:
        return struct.pack("<H", (code << 6) | len(body)) + body
    return struct.pack("<HI", (code << 6) | 63, len(body)) + body


def tags(swf):
    """Itera (código, corpo) de um SWF FWS ou CWS."""
    if swf[:3] == b"CWS":
        swf = b"FWS" + swf[3:8] + zlib.decompress(swf[8:])
    assert swf[:3] == b"FWS", swf[:3]
    p = 8 + (5 + 4 * (swf[8] >> 3) + 7) // 8 + 4
    while p < len(swf):
        h = struct.unpack("<H", swf[p:p + 2])[0]
        p += 2
        code, n = h >> 6, h & 63
        if n == 63:
            n = struct.unpack("<I", swf[p:p + 4])[0]
            p += 4
        yield code, swf[p:p + n]
        p += n
        if code == 0:
            return


def bitmap_fills(code, body):
    """(bitmapId, scaleX, scaleY) dos preenchimentos de bitmap de uma DefineShape."""
    r = BitReader(body, 2)
    r.u(r.u(5) * 4)
    pos = r.align()
    if code == 83:  # DefineShape4: EdgeBounds + flags
        r = BitReader(body, pos)
        r.u(r.u(5) * 4)
        pos = r.align() + 1
    count = body[pos]; pos += 1
    if count == 0xFF and code != 2:
        count = struct.unpack("<H", body[pos:pos + 2])[0]; pos += 2
    out = []
    for _ in range(count):
        t = body[pos]; pos += 1
        if not 0x40 <= t <= 0x43:
            raise ValueError(f"teste só gera preenchimentos de bitmap, achou {t:#x}")
        bid = struct.unpack("<H", body[pos:pos + 2])[0]
        r = BitReader(body, pos + 2)
        sx, sy = read_matrix(r)
        pos = r.align()
        out.append((bid, sx, sy))
    return out
