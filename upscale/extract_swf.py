#!/usr/bin/env python3
"""Obtém o ageofcastles.swf a partir do arquivo fornecido pelo usuário.

Uso: extract_swf.py <saida.swf> <sha256_esperado> <entrada> [<entrada> ...]

Usa a primeira entrada que contiver a versão suportada. Cada uma pode ser:
- o próprio SWF;
- o executável Windows do jogo (RAW_001.exe), que guarda o SWF sem
  criptografia como recurso (RT_RCDATA "FLASHRES"). O executável não é
  executado nem alterado: o script procura assinaturas de SWF (FWS/CWS)
  nos bytes, recorta cada candidato pelo tamanho do cabeçalho e fica com
  o que tem o hash esperado.
"""
import hashlib
import struct
import sys
import zlib
from pathlib import Path

dst, esperado = Path(sys.argv[1]), sys.argv[2].lower()


def candidato(data, p):
    """Bytes do SWF que começa em p, ou None se não for um SWF válido."""
    if p + 8 > len(data):
        return None
    assinatura, versao = data[p:p + 3], data[p + 3]
    if not 1 <= versao <= 50:
        return None
    tamanho = struct.unpack("<I", data[p + 4:p + 8])[0]
    if assinatura == b"FWS":
        if tamanho < 21 or p + tamanho > len(data):
            return None
        return data[p:p + tamanho]
    # CWS: o tamanho é o descompactado; o fim é onde o zlib termina.
    d = zlib.decompressobj()
    try:
        corpo = d.decompress(data[p + 8:], tamanho)
    except zlib.error:
        return None
    if len(corpo) + 8 != tamanho:
        return None
    try:
        d.flush()
    except zlib.error:
        return None
    consumido = len(data) - p - 8 - len(d.unused_data)
    return data[p:p + 8 + consumido]


def achar(data):
    """Bytes do SWF suportado dentro de data, ou o número de candidatos."""
    if hashlib.sha256(data).hexdigest() == esperado:
        return data
    vistos = 0
    for assinatura in (b"FWS", b"CWS"):
        p = data.find(assinatura)
        while p != -1:
            swf = candidato(data, p)
            if swf is not None:
                vistos += 1
                if hashlib.sha256(swf).hexdigest() == esperado:
                    print(f"SWF encontrado no offset {p:#x} ({len(swf)} bytes)")
                    return swf
            p = data.find(assinatura, p + 1)
    return vistos


for src in map(Path, sys.argv[3:]):
    achado = achar(src.read_bytes())
    if isinstance(achado, bytes):
        print(f"Usando {src.name}")
        dst.write_bytes(achado)
        break
    print(f"{src.name}: nenhum SWF da versão suportada ({achado} candidato(s) com outro conteúdo)")
else:
    raise SystemExit("Forneça o RAW_001.exe da instalação Windows ou o ageofcastles.swf.")
