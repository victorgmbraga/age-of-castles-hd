#!/usr/bin/env python3
"""Gera um SWF sintético (sem nada do jogo) para testar o pipeline.

Uso: make_test_swf.py <saida.swf> [<falso.exe>]

O SWF tem uma imagem opaca (DefineBitsJPEG2) e uma com transparência
(DefineBitsJPEG3), cada uma num shape com preenchimento de bitmap em escala
20 (1 pixel = 20 twips). Com <falso.exe>, também grava um "executável" com
o SWF embutido no meio de bytes aleatórios e de assinaturas falsas.
"""
import io
import os
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from swflib import BitWriter, matrix, rect, tag  # noqa: E402

rng = np.random.default_rng(1)


def jpeg(arr):
    b = io.BytesIO()
    Image.fromarray(arr, "RGB").save(b, "JPEG", quality=90)
    return b.getvalue()


# Imagem opaca 40x30: degradê com ruído.
y, x = np.mgrid[0:30, 0:40]
opaca = np.dstack([x * 6, y * 8, (x + y) * 3]).astype(np.uint8)
opaca = np.clip(opaca + rng.integers(0, 30, opaca.shape), 0, 255).astype(np.uint8)

# Imagem com alfa 32x32: círculo vermelho com borda suave.
y, x = np.mgrid[0:32, 0:32]
dist = np.hypot(x - 15.5, y - 15.5)
alfa = np.clip((14 - dist) * 80, 0, 255).astype(np.uint8)
cor = np.zeros((32, 32, 3), np.uint8); cor[..., 0] = 200; cor[..., 1] = 40
pre = (cor.astype(np.float32) * alfa[..., None] / 255).astype(np.uint8)

out = [tag(9, bytes([30, 60, 90]))]
out.append(tag(21, struct.pack("<H", 1) + jpeg(opaca), long=True))
j = jpeg(pre)
out.append(tag(35, struct.pack("<HI", 2, len(j)) + j + zlib.compress(alfa.tobytes()), long=True))


def shape(sid, bid, w, h):
    W, H = w * 20, h * 20
    b = BitWriter()
    rect(b, 0, W, 0, H)
    head = b.bytes()
    b = BitWriter()
    matrix(b, scale=20.0)
    fills = bytes([1, 0x41]) + struct.pack("<H", bid) + b.bytes() + bytes([0])
    b = BitWriter()
    b.u(1, 4); b.u(0, 4)  # NumFillBits=1, NumLineBits=0
    b.u(0, 1); b.u(0b00101, 5)  # StyleChange: FillStyle0 + MoveTo
    b.u(1, 5); b.s(0, 1); b.s(0, 1)
    b.u(1, 1)  # FillStyle0 = 1
    n = max(W, H).bit_length() + 1
    for dx, dy in ((W, 0), (0, H), (-W, 0), (0, -H)):
        b.u(1, 1); b.u(1, 1); b.u(n - 2, 4); b.u(0, 1)
        if dx:
            b.u(0, 1); b.s(dx, n)
        else:
            b.u(1, 1); b.s(dy, n)
    b.u(0, 6)  # EndShape
    return tag(2, struct.pack("<H", sid) + head + fills + b.bytes())


out += [shape(3, 1, 40, 30), shape(4, 2, 32, 32)]
for depth, cid, tx in ((1, 3, 400), (2, 4, 2000)):
    b = BitWriter(); matrix(b, tx=tx, ty=400)
    out.append(tag(26, bytes([0x06]) + struct.pack("<HH", depth, cid) + b.bytes()))
out += [tag(1, b""), tag(0, b"")]

b = BitWriter(); rect(b, 0, 16000, 0, 12000)
corpo = b.bytes() + struct.pack("<HH", 18 << 8, 1) + b"".join(out)
swf = b"FWS\x06" + struct.pack("<I", 8 + len(corpo)) + corpo
Path(sys.argv[1]).write_bytes(swf)
print(f"{sys.argv[1]}: {len(swf)} bytes")

if len(sys.argv) > 2:
    lixo = lambda n: os.urandom(n).replace(b"FWS", b"xxx").replace(b"CWS", b"xxx")  # noqa: E731
    falso = b"FWS\x06" + struct.pack("<I", 30) + os.urandom(22)
    exe = b"MZ" + lixo(4000) + b"FWS\x06\xff\xff\xff\xff" + lixo(100) + falso + lixo(3000) + swf + lixo(5000)
    Path(sys.argv[2]).write_bytes(exe)
    print(f"{sys.argv[2]}: {len(exe)} bytes")
