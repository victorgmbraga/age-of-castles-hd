#!/usr/bin/env bash
# Instala as ferramentas do upscale em upscale/.tools (nada fora do projeto):
# - Java 21 (Eclipse Temurin JRE), para o FFDec;
# - JPEXS FFDec 26.4.0, que lê e regrava o SWF;
# - Python venv com PyTorch (CPU), spandrel, Pillow e NumPy;
# - modelo Real-ESRGAN x2plus.
# Pode ser rodado de novo: o que já está instalado é pulado.
set -euo pipefail
cd "$(dirname "$0")"
T="$PWD/.tools"
mkdir -p "$T"

FFDEC_VER=26.4.0
MODEL_URL=https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth
MODEL_SHA=49fafd45f8fd7aa8d31ab2a22d14d91b536c34494a5cfe31eb5d89c2fa266abb

case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) JRE_OS=linux; JRE_ARCH=x64 ;;
  Linux-aarch64) JRE_OS=linux; JRE_ARCH=aarch64 ;;
  Darwin-x86_64) JRE_OS=mac; JRE_ARCH=x64 ;;
  Darwin-arm64) JRE_OS=mac; JRE_ARCH=aarch64 ;;
  *) echo "Sistema não suportado: $(uname -s) $(uname -m)" >&2; exit 1 ;;
esac

if ! "$T/jre/bin/java" -version >/dev/null 2>&1 && ! "$T/jre/Contents/Home/bin/java" -version >/dev/null 2>&1; then
  echo "== Java 21 (Temurin JRE)"
  rm -rf "$T/jre" "$T/jre.tar.gz"
  curl -fL -o "$T/jre.tar.gz" \
    "https://api.adoptium.net/v3/binary/latest/21/ga/$JRE_OS/$JRE_ARCH/jre/hotspot/normal/eclipse"
  mkdir -p "$T/jre"
  tar -xzf "$T/jre.tar.gz" -C "$T/jre" --strip-components=1
  rm "$T/jre.tar.gz"
fi

if [ ! -f "$T/ffdec/ffdec.jar" ]; then
  echo "== FFDec $FFDEC_VER"
  rm -rf "$T/ffdec" "$T/ffdec.zip"
  curl -fL -o "$T/ffdec.zip" \
    "https://github.com/jindrapetrik/jpexs-decompiler/releases/download/version$FFDEC_VER/ffdec_$FFDEC_VER.zip"
  mkdir -p "$T/ffdec"
  python3 -I -m zipfile -e "$T/ffdec.zip" "$T/ffdec"
  rm "$T/ffdec.zip"
fi

if [ ! -x "$T/venv/bin/python" ]; then
  echo "== Python venv"
  python3 -m venv "$T/venv"
fi
if ! "$T/venv/bin/python" -I -c "import torch, torchvision, spandrel, PIL, numpy" 2>/dev/null; then
  echo "== PyTorch (CPU) e dependências"
  "$T/venv/bin/pip" install -q --upgrade pip
  # torch e torchvision juntos do índice CPU, antes do spandrel, para o pip
  # não trocar o torchvision por uma versão com CUDA.
  "$T/venv/bin/pip" install -q torch torchvision --index-url https://download.pytorch.org/whl/cpu
  "$T/venv/bin/pip" install -q spandrel pillow numpy
fi

M="$T/models/RealESRGAN_x2plus.pth"
if [ ! -f "$M" ]; then
  echo "== modelo Real-ESRGAN x2plus"
  mkdir -p "$T/models"
  curl -fL -o "$M.part" "$MODEL_URL"
  mv "$M.part" "$M"
fi
sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d" " -f1; }
[ "$(sha256 "$M")" = "$MODEL_SHA" ] || { echo "modelo com hash inesperado" >&2; exit 1; }

echo "Ferramentas prontas em $T"
