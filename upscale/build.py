#!/usr/bin/env python3
"""Amplia 2x as imagens do SEU Age of Castles e grava public/ageofcastles.swf.

Uso: python build.py [--original] [--threads N] [--low-priority] [arquivo]

- arquivo: o RAW_001.exe (o SWF é extraído dele) ou o ageofcastles.swf.
  Sem argumento, usa o que estiver em put-game-here/.
- --original: só extrai/confere o SWF e o copia para public/, sem ampliar
  (não precisa das ferramentas do setup.py).
- --threads N: núcleos de CPU para a ampliação (padrão 2).
- --low-priority: roda com prioridade mínima, para não atrapalhar a máquina.

Leva cerca de 20 min numa CPU com 2 threads. Se for interrompido, rode de
novo: as imagens já ampliadas são puladas. Funciona em Linux, macOS e
Windows; este script usa só a biblioteca padrão.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GAME_DIR = ROOT / "put-game-here"
T = HERE / ".tools"
WIN = sys.platform == "win32"

# O pipeline depende dos ids e das matrizes deste arquivo exato.
# AOC_SWF_SHA256 existe só para os testes automáticos, que usam um SWF
# sintético no lugar do jogo.
EXPECTED = os.environ.get("AOC_SWF_SHA256",
                          "90eb16c2c9f2922b292c31b7857f20fbd723b2c4717c655c707338c455d4c203")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def step(msg: str) -> None:
    print(f"== {msg}", flush=True)


def run(cmd, **kw) -> None:
    r = subprocess.run([str(c) for c in cmd], **kw)
    if r.returncode != 0:
        sys.exit(f"Falhou ({r.returncode}): {' '.join(map(str, cmd[:4]))} ...")


def low_priority() -> None:
    """Prioridade mínima de CPU (e de disco no Linux); os filhos herdam."""
    if WIN:
        import ctypes
        IDLE_PRIORITY_CLASS = 0x40
        k = ctypes.windll.kernel32
        k.SetPriorityClass(k.GetCurrentProcess(), IDLE_PRIORITY_CLASS)
    else:
        os.nice(19)
        if shutil.which("ionice"):
            subprocess.run(["ionice", "-c", "3", "-p", str(os.getpid())], check=False)


def inputs(arg):
    if arg:
        p = Path(arg).expanduser()
        if not p.is_file():
            sys.exit(f"Arquivo não encontrado: {p}")
        return [p.resolve()]
    found = sorted(p for p in GAME_DIR.glob("*")
                   if p.is_file() and p.suffix.lower() in (".exe", ".swf"))
    if not found:
        sys.exit("Nenhum jogo encontrado em put-game-here/.\n"
                 "Copie para lá o RAW_001.exe ou o ageofcastles.swf, ou passe o caminho do arquivo.")
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("arquivo", nargs="?", help="RAW_001.exe ou ageofcastles.swf (padrão: put-game-here/)")
    ap.add_argument("--original", action="store_true", help="só extrai o SWF, sem ampliar")
    ap.add_argument("--threads", type=int, default=int(os.environ.get("THREADS", "2")))
    ap.add_argument("--low-priority", action="store_true", help="prioridade mínima de CPU")
    ap.add_argument("--out", type=Path, default=ROOT / "public" / "ageofcastles.swf", help=argparse.SUPPRESS)
    ap.add_argument("--work", type=Path, default=HERE / "work", help=argparse.SUPPRESS)
    a = ap.parse_args()
    global W
    W, OUT = a.work.resolve(), a.out.resolve()
    if a.low_priority:
        low_priority()

    W.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    inicio = time.time()

    step("0/6 verificação da entrada")
    entrada = W / "input.swf"
    run([sys.executable, "-I", HERE / "extract_swf.py", entrada, EXPECTED, *inputs(a.arquivo)])
    if sha256(entrada) != EXPECTED:
        sys.exit("SWF extraído com hash inesperado.")
    if a.original:
        shutil.copyfile(entrada, OUT)
        print(f"   {OUT}: SWF original, sem ampliação")
        return

    java = (T / "jre" / "Contents" / "Home" / "bin" / "java" if sys.platform == "darwin"
            else T / "jre" / "bin" / ("java.exe" if WIN else "java"))
    py = T / "venv" / ("Scripts/python.exe" if WIN else "bin/python")
    model = T / "models" / "RealESRGAN_x2plus.pth"
    ffdec_jar = T / "ffdec" / "ffdec.jar"
    if not all(p.is_file() for p in (java, py, model, ffdec_jar)):
        sys.exit("Ferramentas não encontradas. Rode antes: npm run setup")

    env = dict(os.environ, THREADS=str(a.threads))

    def ffdec(*args):
        # O FFDec é verboso: mostra só o fim da saída (ou tudo, se falhar).
        cmd = [str(c) for c in (java, "-Xmx4g", "-Djava.awt.headless=true", "-jar", ffdec_jar, *args)]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, encoding="utf-8", errors="replace")
        linhas = r.stdout.strip().splitlines()
        if r.returncode != 0:
            print(r.stdout)
            sys.exit(f"FFDec falhou ({r.returncode}): {args[0]}")
        for linha in linhas[-2:]:
            print("   " + linha, flush=True)

    images = W / "images"
    marca = W / "images.sha256"
    if images.is_dir() and (not marca.is_file() or marca.read_text().strip() != EXPECTED):
        # Restos de outro SWF (só acontece nos testes): começa do zero.
        for d in ("images", "x2", "stage"):
            shutil.rmtree(W / d, ignore_errors=True)

    step("1/6 exportação das imagens")
    if not images.is_dir():
        tmp = W / "images.tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        ffdec("-export", "image", tmp, entrada)
        tmp.replace(images)
        marca.write_text(EXPECTED + "\n")
    arquivos = sorted(images.iterdir(), key=lambda p: p.stat().st_size)  # menores primeiro
    print(f"   {len(arquivos)} imagens", flush=True)

    step(f"2/6 ampliação (Real-ESRGAN x2, {a.threads} threads, uma linha por imagem)")
    # Em lotes, para não estourar o limite de tamanho da linha de comando no Windows.
    for i in range(0, len(arquivos), 50):
        run([py, "-I", HERE / "upscale.py", model, W / "x2", *arquivos[i:i + 50]], env=env)

    step("3/6 codificação e lista de trocas")
    run([py, "-I", HERE / "prepare_replace.py", images, W / "x2", W / "stage",
         W / "replace_args.txt", W / "replaced_ids.txt"])

    step("4/6 troca das imagens no SWF")
    ffdec("-replace", entrada, W / "x2_replaced.swf", W / "replace_args.txt")

    step("5/6 ajuste das matrizes (via XML)")
    ffdec("-swf2xml", W / "x2_replaced.swf", W / "x2.xml")
    ids = (W / "replaced_ids.txt").read_text().split()
    # Os ids vão por arquivo (@...) pelo mesmo motivo do lote acima.
    run([py, "-I", HERE / "fix_matrices.py", W / "x2.xml", W / "x2_fixed.xml", "2", "@" + str(W / "replaced_ids.txt")])

    step("6/6 remontagem e compactação")
    ffdec("-xml2swf", W / "x2_fixed.xml", W / "x2_png.swf")
    # O FFDec grava as imagens com alfa como PNG sem perda dentro da JPEG3;
    # regrava como JPEG pré-multiplicado + alfa (como o original) e compacta.
    run([py, "-I", HERE / "shrink_jpeg3.py", W / "x2_png.swf", OUT, W / "x2", "90"])
    for f in ("x2.xml", "x2_fixed.xml", "x2_replaced.swf", "x2_png.swf"):
        (W / f).unlink(missing_ok=True)

    print(f"   {OUT}: {OUT.stat().st_size} bytes, sha256 {sha256(OUT)}")
    print(f"== fim em {(time.time() - inicio) / 60:.0f} min ({len(ids)} imagens). "
          f"Pode apagar upscale/work/ se quiser liberar espaço.")


if __name__ == "__main__":
    main()
