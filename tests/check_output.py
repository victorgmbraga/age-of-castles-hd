#!/usr/bin/env python3
"""Confere o SWF ampliado gerado a partir do SWF de teste.

Uso: check_output.py <original.swf> <ampliado.swf>

- toda imagem tem o dobro da largura e da altura;
- a imagem com alfa continua como DefineBitsJPEG3 com alfa do tamanho certo;
- as matrizes de preenchimento têm metade da escala (a área na tela é a mesma).
"""
import io
import struct
import sys
import zlib
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from swflib import bitmap_fills, tags  # noqa: E402


def info(path):
    imgs, fills = {}, {}
    for code, body in tags(Path(path).read_bytes()):
        if code == 21:
            imgs[struct.unpack("<H", body[:2])[0]] = (Image.open(io.BytesIO(body[2:])).size, None)
        elif code == 35:
            cid, n = struct.unpack("<HI", body[:6])
            size = Image.open(io.BytesIO(body[6:6 + n])).size
            imgs[cid] = (size, len(zlib.decompress(body[6 + n:])))
        elif code in (2, 22, 32, 83):
            for bid, sx, sy in bitmap_fills(code, body):
                fills[bid] = (sx, sy)
    return imgs, fills


oi, of = info(sys.argv[1])
ni, nf = info(sys.argv[2])
assert set(oi) == set(ni) and oi, (oi, ni)
for cid, ((w, h), _) in oi.items():
    (nw, nh), alfa = ni[cid]
    assert (nw, nh) == (2 * w, 2 * h), f"imagem {cid}: {(w, h)} -> {(nw, nh)}"
    if alfa is not None:
        assert alfa == nw * nh, f"imagem {cid}: alfa com {alfa} bytes"
    print(f"imagem {cid}: {w}x{h} -> {nw}x{nh}" + (" (com alfa)" if alfa else ""))
for bid, (sx, sy) in of.items():
    nx, ny = nf[bid]
    assert abs(nx - sx / 2) < 1e-3 and abs(ny - sy / 2) < 1e-3, f"matriz do bitmap {bid}: {sx} -> {nx}"
    print(f"matriz do bitmap {bid}: escala {sx:g} -> {nx:g}")
print("OK")
