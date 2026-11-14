#!/usr/bin/env python3
"""Instala as ferramentas do upscale em upscale/.tools (nada fora do projeto).

- Java 21 (Eclipse Temurin JRE), para o FFDec;
- JPEXS FFDec 26.4.0, que lê e regrava o SWF;
- Python venv com PyTorch (CPU), spandrel, Pillow e NumPy;
- modelo Real-ESRGAN x2plus.

Funciona em Linux, macOS e Windows; usa só a biblioteca padrão. Pode ser
rodado de novo: o que já está instalado é pulado.
Uso: python setup.py   (ou npm run setup, que também faz o build)
"""
import hashlib
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
T = HERE / ".tools"
WIN = sys.platform == "win32"
MAC = sys.platform == "darwin"

FFDEC_VER = "26.4.0"
FFDEC_URL = (f"https://github.com/jindrapetrik/jpexs-decompiler/releases/download/"
             f"version{FFDEC_VER}/ffdec_{FFDEC_VER}.zip")
MODEL_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth"
MODEL_SHA = "49fafd45f8fd7aa8d31ab2a22d14d91b536c34494a5cfe31eb5d89c2fa266abb"
TORCH_INDEX = "https://download.pytorch.org/whl/cpu"


def java_path() -> Path:
    if MAC:
        return T / "jre" / "Contents" / "Home" / "bin" / "java"
    return T / "jre" / "bin" / ("java.exe" if WIN else "java")


def venv_python() -> Path:
    return T / "venv" / ("Scripts/python.exe" if WIN else "bin/python")


def download(url: str, dst: Path) -> None:
    print(f"   baixando {url}", flush=True)
    part = dst.with_name(dst.name + ".part")
    try:
        with urllib.request.urlopen(url) as r, open(part, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 20)
    except OSError as e:
        # Ex.: Python do python.org no macOS sem certificados instalados.
        if not shutil.which("curl"):
            raise
        print(f"   urllib falhou ({e}); tentando com curl", flush=True)
        subprocess.run(["curl", "-fL", "-o", str(part), url], check=True)
    part.replace(dst)


def extract(archive: Path, dst: Path, strip_top: bool) -> None:
    """Extrai zip ou tar.gz; strip_top remove a pasta de nível mais alto."""
    tmp = dst.with_name(dst.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            z.extractall(tmp)
    else:
        with tarfile.open(archive) as t:
            if hasattr(tarfile, "data_filter"):
                t.extractall(tmp, filter="data")
            else:
                t.extractall(tmp)
    src = tmp
    if strip_top:
        (top,) = list(tmp.iterdir())
        src = top
    shutil.rmtree(dst, ignore_errors=True)
    src.replace(dst)
    shutil.rmtree(tmp, ignore_errors=True)


def runs(cmd) -> bool:
    try:
        return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    except OSError:
        return False


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    T.mkdir(parents=True, exist_ok=True)
    maquina = platform.machine().lower()
    arch = {"x86_64": "x64", "amd64": "x64", "aarch64": "aarch64", "arm64": "aarch64"}.get(maquina)
    so = {"win32": "windows", "darwin": "mac"}.get(sys.platform, "linux" if sys.platform.startswith("linux") else None)
    if not arch or not so:
        sys.exit(f"Sistema não suportado: {sys.platform} {maquina}")

    if not runs([str(java_path()), "-version"]):
        print("== Java 21 (Temurin JRE)", flush=True)
        ext = ".zip" if WIN else ".tar.gz"
        arq = T / f"jre{ext}"
        download(f"https://api.adoptium.net/v3/binary/latest/21/ga/{so}/{arch}/jre/hotspot/normal/eclipse", arq)
        extract(arq, T / "jre", strip_top=True)
        arq.unlink()
        if not runs([str(java_path()), "-version"]):
            sys.exit("Java instalado mas não executa: " + str(java_path()))

    if not (T / "ffdec" / "ffdec.jar").is_file():
        print(f"== FFDec {FFDEC_VER}", flush=True)
        arq = T / "ffdec.zip"
        download(FFDEC_URL, arq)
        extract(arq, T / "ffdec", strip_top=False)
        arq.unlink()

    py = venv_python()
    if not py.is_file():
        print("== Python venv", flush=True)
        subprocess.run([sys.executable, "-m", "venv", str(T / "venv")], check=True)
    if not runs([str(py), "-I", "-c", "import torch, torchvision, spandrel, PIL, numpy"]):
        print("== PyTorch (CPU) e dependências (pode demorar)", flush=True)
        pip = [str(py), "-m", "pip", "install", "--disable-pip-version-check", "-q"]
        subprocess.run(pip + ["--upgrade", "pip"], check=True)
        # torch e torchvision juntos do índice CPU, antes do spandrel, para o
        # pip não trocar o torchvision por uma versão com CUDA.
        subprocess.run(pip + ["torch", "torchvision", "--index-url", TORCH_INDEX], check=True)
        subprocess.run(pip + ["spandrel", "pillow", "numpy"], check=True)

    modelo = T / "models" / "RealESRGAN_x2plus.pth"
    if not modelo.is_file():
        print("== modelo Real-ESRGAN x2plus", flush=True)
        modelo.parent.mkdir(exist_ok=True)
        download(MODEL_URL, modelo)
    if sha256(modelo) != MODEL_SHA:
        modelo.unlink()
        sys.exit("O modelo baixado tem hash inesperado; foi apagado. Rode de novo.")

    print(f"Ferramentas prontas em {T}", flush=True)


if __name__ == "__main__":
    main()
