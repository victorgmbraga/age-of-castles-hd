#!/usr/bin/env python3
"""Prepara as imagens ampliadas para o `ffdec -replace`.

Uso: prepare_replace.py <imagens_originais> <ampliadas> <pasta_stage> <argsfile> <idsfile>

- Imagem sem transparência: JPEG qualidade 92, sem subamostragem de cor,
  trocada como `jpeg2`.
- Imagem com transparência: PNG RGBA, trocada como `jpeg3` (JPEG + alfa).
Grava o argsfile do FFDec (id, arquivo, formato, um por linha) e a lista
de ids trocados, usada depois para ajustar as matrizes.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

orig_dir, up_dir, stage, argsfile, idsfile = map(Path, sys.argv[1:6])
stage.mkdir(parents=True, exist_ok=True)

linhas, ids, faltando = [], [], []
for orig in sorted(orig_dir.iterdir(), key=lambda p: int(p.stem)):
    up = up_dir / f"{orig.stem}.png"
    if not up.exists():
        faltando.append(orig.name)
        continue
    im = Image.open(up)
    tem_alfa = im.mode == "RGBA" and np.asarray(im)[:, :, 3].min() < 255
    if tem_alfa:
        arquivo, formato = up, "jpeg3"
    else:
        arquivo, formato = stage / f"{orig.stem}.jpg", "jpeg2"
        if not arquivo.exists():
            im.convert("RGB").save(arquivo, quality=92, subsampling=0, optimize=True)
    linhas += [orig.stem, str(arquivo.resolve()), formato]
    ids.append(orig.stem)

if faltando:
    raise SystemExit(f"{len(faltando)} imagens ainda não ampliadas, ex.: {faltando[:5]}")
argsfile.write_text("\n".join(linhas) + "\n", encoding="utf-8")
idsfile.write_text(" ".join(ids) + "\n", encoding="utf-8")
print(f"{len(ids)} imagens: {sum(1 for i in range(2, len(linhas), 3) if linhas[i] == 'jpeg3')} com alfa (jpeg3), "
      f"{sum(1 for i in range(2, len(linhas), 3) if linhas[i] == 'jpeg2')} opacas (jpeg2)")
