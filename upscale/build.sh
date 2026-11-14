#!/usr/bin/env bash
# Amplia 2x as imagens do SEU ageofcastles.swf e grava o resultado em
# public/ageofcastles.swf, que é o arquivo usado pelo app web.
#
# Uso:  upscale/build.sh /caminho/para/ageofcastles.swf
#   ou: upscale/build.sh /caminho/para/RAW_001.exe   (o SWF é extraído dele)
#
# Antes, rode upscale/setup.sh uma vez. Leva cerca de 20 min numa CPU com
# 2 threads; THREADS=n usa mais núcleos. Para rodar em segundo plano sem
# atrapalhar a máquina:
#   nohup nice -n 19 ionice -c 3 upscale/build.sh jogo.swf > upscale/work/build.log 2>&1 &
# Se for interrompido, rode de novo: as imagens já ampliadas são puladas.
set -euo pipefail

# Com --original, só extrai/confere o SWF e o copia para public/, sem
# ampliar (não precisa do setup.sh).
ORIGINAL=0
if [ "${1:-}" = "--original" ]; then ORIGINAL=1; shift; fi
if [ $# -ne 1 ] || [ ! -f "$1" ]; then
  echo "Uso: $0 [--original] /caminho/para/ageofcastles.swf  (ou RAW_001.exe)" >&2
  exit 2
fi
SWF_IN="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
cd "$(dirname "$0")"

# O pipeline depende dos ids e das matrizes deste arquivo exato.
EXPECTED=90eb16c2c9f2922b292c31b7857f20fbd723b2c4717c655c707338c455d4c203
sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }

W=work
OUT=../public/ageofcastles.swf
mkdir -p "$W"

echo "== 0/6 verificação da entrada"
# Aceita o SWF ou o executável do jogo; sai com erro se não houver a versão
# suportada. Só o Python da máquina é usado aqui (biblioteca padrão).
python3 -I extract_swf.py "$SWF_IN" "$W/input.swf" "$EXPECTED"
SWF_IN="$PWD/$W/input.swf"
[ "$(sha256 "$SWF_IN")" = "$EXPECTED" ]
if [ "$ORIGINAL" = 1 ]; then
  cp "$SWF_IN" "$OUT"
  echo "   $OUT: SWF original, sem ampliação"
  exit 0
fi

T="$PWD/.tools"
JAVA="$T/jre/bin/java"; [ -x "$JAVA" ] || JAVA="$T/jre/Contents/Home/bin/java"
PY="$T/venv/bin/python"
MODEL="$T/models/RealESRGAN_x2plus.pth"
if [ ! -x "$JAVA" ] || [ ! -x "$PY" ] || [ ! -f "$MODEL" ] || [ ! -f "$T/ffdec/ffdec.jar" ]; then
  echo "Ferramentas não encontradas. Rode antes: upscale/setup.sh" >&2
  exit 1
fi
export THREADS="${THREADS:-2}"
ffdec() { "$JAVA" -Xmx4g -Djava.awt.headless=true -jar "$T/ffdec/ffdec.jar" "$@"; }

echo "== $(date '+%F %T') início (THREADS=$THREADS)"

echo "== 1/6 exportação das imagens"
if [ ! -d "$W/images" ]; then
  ffdec -export image "$W/images.tmp" "$SWF_IN" | tail -1
  mv "$W/images.tmp" "$W/images"
fi
echo "   $(ls "$W/images" | wc -l | tr -d ' ') imagens"

echo "== 2/6 ampliação (Real-ESRGAN x2, uma linha por imagem)"
FILES=()
while IFS= read -r f; do FILES+=("$W/images/$f"); done < <(ls -S -r "$W/images")
"$PY" -I upscale.py "$MODEL" "$W/x2" "${FILES[@]}"

echo "== 3/6 codificação e lista de trocas"
"$PY" -I prepare_replace.py "$W/images" "$W/x2" "$W/stage" "$W/replace_args.txt" "$W/replaced_ids.txt"

echo "== 4/6 troca das imagens no SWF"
ffdec -replace "$SWF_IN" "$W/x2_replaced.swf" "$W/replace_args.txt" | tail -3

echo "== 5/6 ajuste das matrizes (via XML)"
ffdec -swf2xml "$W/x2_replaced.swf" "$W/x2.xml" | tail -3
"$PY" -I fix_matrices.py "$W/x2.xml" "$W/x2_fixed.xml" 2 $(cat "$W/replaced_ids.txt")

echo "== 6/6 remontagem e compactação"
ffdec -xml2swf "$W/x2_fixed.xml" "$W/x2_png.swf" | tail -3
# O FFDec grava as imagens com alfa como PNG sem perda dentro da JPEG3;
# regrava como JPEG pré-multiplicado + alfa (como o original) e compacta.
"$PY" -I shrink_jpeg3.py "$W/x2_png.swf" "$OUT" "$W/x2" 90
rm -f "$W/x2.xml" "$W/x2_fixed.xml" "$W/x2_replaced.swf" "$W/x2_png.swf"

echo "   $OUT: $(wc -c < "$OUT" | tr -d ' ') bytes, sha256 $(sha256 "$OUT")"
echo "== $(date '+%F %T') fim. Pode apagar upscale/work/ se quiser liberar espaço."
