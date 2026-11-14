#!/usr/bin/env python3
"""Regrava como JPEG3 de verdade as imagens com alfa que o FFDec guardou em PNG.

Uso: shrink_jpeg3.py <entrada.swf> <saida.swf> <pasta_x2> [qualidade]

O `ffdec -replace ... jpeg3` com um PNG grava o PNG inteiro (sem perda)
dentro da DefineBitsJPEG3. Este script troca cada uma dessas tags por:
  JPEG (qualidade 90) da cor PRÉ-MULTIPLICADA pelo alfa + alfa em zlib,
que é como o SWF original guarda as suas (pixels com alfa 0 têm cor 0).
A fonte é o PNG ampliado em <pasta_x2>/<id>.png, com alfa normal.
Grava o resultado compactado (CWS, suportado desde o Flash 6).
"""
import io
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

src, dst, x2 = sys.argv[1], sys.argv[2], Path(sys.argv[3])
qualidade = int(sys.argv[4]) if len(sys.argv) > 4 else 90

data = open(src, "rb").read()
if data[:3] == b"CWS":
    data = data[:8] + zlib.decompress(data[8:])
assert data[:3] == b"FWS"

nbits = data[8] >> 3
inicio = 8 + (5 + 4 * nbits + 7) // 8 + 4  # depois de RECT, frame rate e frame count
saida = [data[8:inicio]]
p = inicio
trocadas, antes, depois = 0, 0, 0


def tag(codigo, corpo):
    if len(corpo) < 63:
        return struct.pack("<H", (codigo << 6) | len(corpo)) + corpo
    return struct.pack("<HI", (codigo << 6) | 63, len(corpo)) + corpo


while p < len(data):
    h = struct.unpack("<H", data[p:p + 2])[0]
    q = p + 2
    codigo, tam = h >> 6, h & 63
    if tam == 63:
        tam = struct.unpack("<I", data[q:q + 4])[0]
        q += 4
    corpo = data[q:q + tam]
    if codigo == 35 and corpo[6:10] == b"\x89PNG":
        cid = struct.unpack("<H", corpo[:2])[0]
        rgba = np.asarray(Image.open(x2 / f"{cid}.png").convert("RGBA")).astype(np.float32)
        alfa = rgba[:, :, 3:4]
        pre = np.clip(rgba[:, :, :3] * alfa / 255 + 0.5, 0, 255).astype(np.uint8)
        buf = io.BytesIO()
        Image.fromarray(pre, "RGB").save(buf, "JPEG", quality=qualidade, optimize=True)
        jpg = buf.getvalue()
        alfa_z = zlib.compress(rgba[:, :, 3].astype(np.uint8).tobytes(), 9)
        novo = struct.pack("<HI", cid, len(jpg)) + jpg + alfa_z
        saida.append(tag(35, novo))
        trocadas += 1
        antes += len(corpo)
        depois += len(novo)
    else:
        saida.append(data[p:q + tam])
    p = q + tam
    if codigo == 0:
        break

corpo_swf = b"".join(saida)
total = 8 + len(corpo_swf)
cabecalho = b"CWS" + bytes([data[3]]) + struct.pack("<I", total)
open(dst, "wb").write(cabecalho + zlib.compress(corpo_swf, 9))
print(f"{trocadas} tags JPEG3 regravadas: {antes / 1e6:.1f} MB -> {depois / 1e6:.1f} MB; "
      f"SWF final {Path(dst).stat().st_size / 1e6:.1f} MB (descompactado {total / 1e6:.1f} MB)")
