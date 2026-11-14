#!/usr/bin/env python3
"""Amplia imagens exportadas do SWF com Real-ESRGAN (CPU).

Uso: upscale.py <modelo.pth> <pasta_saida> <imagem> [<imagem> ...]

- RGB: passa direto pelo modelo.
- RGBA: o RGB e o canal alfa são ampliados separadamente pelo modelo
  (o alfa replicado em 3 canais) e recombinados.
A saída é sempre PNG sem perdas; a compressão final é decidida na
hora de montar o SWF.
"""
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from spandrel import ImageModelDescriptor, ModelLoader

import os

# THREADS limita os núcleos usados (padrão 2, para não ocupar a máquina).
torch.set_num_threads(int(os.environ.get("THREADS", "2")))

model = ModelLoader().load_from_file(sys.argv[1])
assert isinstance(model, ImageModelDescriptor)
model.eval()
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
TILE = 256  # processa em blocos para limitar a memória


def run(rgb: np.ndarray) -> np.ndarray:
    """rgb: HxWx3 uint8 -> (H*s)x(W*s)x3 uint8, em blocos com sobreposição."""
    s = model.scale
    h, w, _ = rgb.shape
    pad = 16
    out = np.zeros((h * s, w * s, 3), dtype=np.float32)
    x = torch.from_numpy(rgb).permute(2, 0, 1).float().div(255).unsqueeze(0)
    with torch.inference_mode():
        for y0 in range(0, h, TILE):
            for x0 in range(0, w, TILE):
                y1, x1 = min(y0 + TILE, h), min(x0 + TILE, w)
                ya, xa = max(y0 - pad, 0), max(x0 - pad, 0)
                yb, xb = min(y1 + pad, h), min(x1 + pad, w)
                tile = model(x[:, :, ya:yb, xa:xb])[0].clamp(0, 1)
                tile = tile.permute(1, 2, 0).numpy()
                oy, ox = (y0 - ya) * s, (x0 - xa) * s
                out[y0 * s:y1 * s, x0 * s:x1 * s] = tile[oy:oy + (y1 - y0) * s,
                                                         ox:ox + (x1 - x0) * s]
    return (out * 255 + 0.5).astype(np.uint8)


def bleed(rgba: np.ndarray) -> np.ndarray:
    """Preenche o RGB dos pixels transparentes com a cor do vizinho opaco
    mais próximo, para o modelo não espalhar lixo pelas bordas."""
    rgb = rgba[:, :, :3].astype(np.float32)
    known = rgba[:, :, 3] > 0
    if known.all() or not known.any():
        return rgba[:, :, :3].copy()
    filled = rgb * known[..., None]
    mask = known.astype(np.float32)
    for _ in range(64):  # dilatação iterativa até cobrir tudo
        if mask.all():
            break
        acc = np.zeros_like(filled)
        cnt = np.zeros_like(mask)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            acc += np.roll(filled, (dy, dx), axis=(0, 1))
            cnt += np.roll(mask, (dy, dx), axis=(0, 1))
        new = (mask == 0) & (cnt > 0)
        filled[new] = acc[new] / cnt[new][:, None]
        mask[new] = 1
    return np.clip(filled + 0.5, 0, 255).astype(np.uint8)


def keep_colors(up: np.ndarray, orig: Image.Image) -> np.ndarray:
    """Mantém a aparência do original e usa do modelo só o detalhe fino:
    cor (Cb/Cr) do original ampliado por bicúbico; brilho = tons gerais do
    original (desfocados) + detalhe de alta frequência do modelo."""
    from PIL import ImageFilter
    size = (up.shape[1], up.shape[0])
    ref_img = orig.convert("RGB").resize(size, Image.BICUBIC).convert("YCbCr")
    up_img = Image.fromarray(up, "RGB").convert("YCbCr")
    blur = ImageFilter.GaussianBlur(radius=2 * model.scale)
    ref = np.asarray(ref_img).astype(np.float32)
    ycc = np.asarray(up_img).astype(np.float32)
    ref_low = np.asarray(ref_img.getchannel("Y").filter(blur)).astype(np.float32)
    up_low = np.asarray(up_img.getchannel("Y").filter(blur)).astype(np.float32)
    out = ref.copy()
    out[:, :, 0] = ref_low + (ycc[:, :, 0] - up_low)
    out = np.clip(out + 0.5, 0, 255).astype(np.uint8)
    return np.asarray(Image.fromarray(out, "YCbCr").convert("RGB"))


for src in sys.argv[3:]:
    t = time.time()
    dst = out_dir / (Path(src).stem + ".png")
    if dst.exists():  # permite retomar uma rodada interrompida
        continue
    im = Image.open(src)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        arr = np.asarray(im)
        base = bleed(arr)
        rgb = keep_colors(run(base), Image.fromarray(base, "RGB"))
        alpha = run(np.repeat(arr[:, :, 3:4], 3, axis=2))[:, :, 0]
        res = Image.fromarray(np.dstack([rgb, alpha]), "RGBA")
    else:
        rgb = np.asarray(im.convert("RGB")).copy()
        res = Image.fromarray(keep_colors(run(rgb), im), "RGB")
    tmp = dst.with_suffix(".tmp.png")
    res.save(tmp, optimize=False)
    tmp.rename(dst)  # só aparece como pronto depois de gravado por inteiro
    print(f"{Path(src).name}: {im.size} -> {res.size} em {time.time() - t:.0f}s", flush=True)
