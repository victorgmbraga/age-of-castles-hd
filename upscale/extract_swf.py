#!/usr/bin/env python3
"""Obtém o ageofcastles.swf a partir do arquivo fornecido pelo usuário.

Uso: extract_swf.py <entrada> <saida.swf> <sha256_esperado>

A entrada pode ser:
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

src, dst, esperado = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3].lower()
data = src.read_bytes()


def candidato(p):
    """Bytes do SWF que começa em p, ou None se não for um SWF válido."""
    assinatura, versao = data[p:p + 3], data[p + 3]
    if not 1 <= versao <= 50 or p + 8 > len(data):
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


def achar():
    if hashlib.sha256(data).hexdigest() == esperado:
        return data
    vistos = 0
    for assinatura in (b"FWS", b"CWS"):
        p = data.find(assinatura)
        while p != -1:
            swf = candidato(p)
            if swf is not None:
                vistos += 1
                if hashlib.sha256(swf).hexdigest() == esperado:
                    print(f"SWF encontrado no offset {p:#x} ({len(swf)} bytes)")
                    return swf
            p = data.find(assinatura, p + 1)
    raise SystemExit(
        f"Nenhum SWF da versão suportada em {src.name} "
        f"({vistos} candidato(s) com outro conteúdo).\n"
        f"Forneça o ageofcastles.swf ou o RAW_001.exe da instalação Windows.")


dst.write_bytes(achar())
