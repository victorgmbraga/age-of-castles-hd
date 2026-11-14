#!/usr/bin/env python3
"""Divide a escala das matrizes de preenchimento das imagens ampliadas.

Uso: fix_matrices.py <entrada.xml> <saida.xml> <fator> <id> [<id> ...]
     (ou @arquivo com os ids separados por espaço)

Trabalha no XML gerado por `ffdec -swf2xml`. Para cada FILLSTYLE de bitmap
(tipos 64-67) cujo bitmapId esteja na lista, divide scaleX, scaleY,
rotateSkew0 e rotateSkew1 da bitmapMatrix pelo fator. A translação fica
igual: o canto da imagem continua no mesmo lugar e ela ocupa a mesma área.
"""
import re
import sys

src, dst, fator = sys.argv[1], sys.argv[2], float(sys.argv[3])
ids = set()
for arg in sys.argv[4:]:
    ids.update(open(arg[1:], encoding="utf-8").read().split() if arg.startswith("@") else [arg])

item_re = re.compile(r'<item type="FILLSTYLE" bitmapId="(\d+)" fillStyleType="(6[4-7])">\s*<bitmapMatrix ([^>]*)/>')
attr_re = re.compile(r'(scaleX|scaleY|rotateSkew0|rotateSkew1)="(-?[0-9.Ee+-]+)"')

contagem = {}


def fix(m):
    if m.group(1) not in ids:
        return m.group(0)
    contagem[m.group(1)] = contagem.get(m.group(1), 0) + 1
    attrs = attr_re.sub(lambda a: f'{a.group(1)}="{float(a.group(2)) / fator!r}"', m.group(3))
    return m.group(0).replace(m.group(3), attrs)


texto = open(src, encoding="utf-8").read()
novo = item_re.sub(fix, texto)
open(dst, "w", encoding="utf-8").write(novo)

faltando = ids - set(contagem)
print("matrizes ajustadas:", dict(sorted(contagem.items(), key=lambda kv: int(kv[0]))))
if faltando:
    print("AVISO: ids sem nenhuma forma:", sorted(faltando, key=int))
