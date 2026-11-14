# Age of Castles HD

Kit **não oficial** para jogar *Age of Castles* no navegador, com os gráficos
ampliados 2x por IA (Real-ESRGAN) e saves que funcionam.

> **Este repositório não contém o jogo.** Nenhum SWF, imagem, som ou código do
> Age of Castles faz parte dele. Você precisa da sua própria cópia: o
> `RAW_001.exe` da instalação Windows ou o `ageofcastles.swf`. Os scripts
> daqui geram a versão ampliada na sua máquina.
> Projeto sem afiliação com os autores do jogo.

## Como funciona

- **Ruffle** (emulador de Flash em WebAssembly) roda o SWF no navegador.
- **Ponte de save** (`src/save-bridge.js`): o jogo original salvava com
  comandos do Flash Studio e lia `save.xml` do disco. No navegador, a ponte
  recebe esses comandos e guarda o save no `localStorage`, sem alterar o SWF.
- **Upscale** (`upscale/`): exporta as imagens do seu SWF, amplia cada uma
  2x com Real-ESRGAN na CPU, preservando cores e transparência, e remonta o
  SWF com as imagens novas ocupando a mesma área na tela.

## Requisitos

- Linux ou macOS, com `bash`, `curl` e Python 3.10+ (com `venv`).
- Node.js 20+ (para o app web).
- ~3 GB livres (ferramentas + arquivos temporários) e cerca de 20 min de CPU
  para o upscale.
- O jogo, em um destes formatos:
  - `RAW_001.exe`, o executável da instalação Windows. O SWF é extraído
    dele automaticamente; o exe não é executado nem alterado;
  - ou o `ageofcastles.swf` já extraído.

  Só uma versão é suportada: o SWF precisa ter SHA-256
  `90eb16c2c9f2922b292c31b7857f20fbd723b2c4717c655c707338c455d4c203`.
  O script confere isso e recusa outras versões.

## Passo a passo

1. Copie o `RAW_001.exe` (ou o `ageofcastles.swf`) para a pasta
   **`put-game-here/`**. Tudo nela é ignorado pelo git.
2. Rode:

```bash
npm install
npm run setup   # instala as ferramentas e gera o jogo ampliado (~20 min)
npm run dev     # abre o jogo
```

O `npm run setup`:

- instala em `upscale/.tools` o Java 21, o JPEXS FFDec, o PyTorch (CPU) e o
  modelo Real-ESRGAN x2plus (só na primeira vez);
- extrai e confere o SWF do que estiver em `put-game-here/`;
- amplia as imagens e grava o resultado em `public/ageofcastles.swf`, o
  arquivo que o app usa.

Outras formas:

| Comando | O que faz |
| --- | --- |
| `npm run use:original` | Usa o jogo sem ampliar (não instala nada). |
| `npm run upscale` | Só refaz o build, com as ferramentas já instaladas. |
| `npm run upscale -- /caminho/RAW_001.exe` | Usa outro arquivo em vez da pasta (vale para os três comandos). |
| `THREADS=8 npm run setup` | Usa mais núcleos de CPU (padrão: 2). |

O upscale pode ser interrompido e rodado de novo: imagens já ampliadas são
puladas. Para rodar em segundo plano com prioridade baixa:

```bash
mkdir -p upscale/work
nohup nice -n 19 ionice -c 3 upscale/build.sh > upscale/work/build.log 2>&1 &
```

Ao terminar, `upscale/work/` (~130 MB) pode ser apagada.

## Builds

| Comando | Saída |
| --- | --- |
| `npm run build` | `dist/`, para servir em qualquer servidor estático. |
| `npm run build:single` | `dist/age-of-castles.html`: o jogo inteiro em **um único arquivo HTML** (~45 MB), que funciona aberto direto do disco, sem servidor. |

Os arquivos gerados contêm o jogo: são para uso pessoal, não os publique.

## Saves

Ficam no `localStorage` do navegador, na chave `ageofcastles:save.xml`, por
origem: o save do `npm run dev` não é o mesmo do HTML único aberto do disco.
Limpar os dados do site apaga o save.

## Estrutura

```
put-game-here/            onde você coloca o RAW_001.exe ou o SWF (ignorado pelo git)
index.html, src/          app web (Ruffle + ponte de save)
public/ruffle/            Ruffle 0.7.1 self-hosted (MIT/Apache-2.0)
scripts/build-single.mjs  gera o HTML único
upscale/
  setup.sh                instala as ferramentas em upscale/.tools
  build.sh                pipeline completo: exe/SWF -> public/ageofcastles.swf
  extract_swf.py          tira o SWF do RAW_001.exe e confere o hash
  upscale.py              Real-ESRGAN com preservação de cor e alfa
  prepare_replace.py      codifica as imagens (JPEG / JPEG+alfa)
  fix_matrices.py         ajusta as matrizes de bitmap para o tamanho 2x
  shrink_jpeg3.py         regrava imagens com alfa como JPEG3 e compacta
```

## Detalhes do upscale

0. **Entrada**: se for o executável, `extract_swf.py` procura as assinaturas
   de SWF (`FWS`/`CWS`) nos bytes, recorta cada candidato pelo tamanho
   declarado no cabeçalho e fica com o que tem o hash esperado. No
   `RAW_001.exe` o SWF está sem criptografia no recurso `RT_RCDATA/FLASHRES`.
1. **Exportação**: `ffdec -export image`, um arquivo por imagem, nomeado pelo
   id do caractere no SWF.
2. **Ampliação**: Real-ESRGAN x2plus em blocos de 256 px. Nas imagens com
   transparência, o RGB dos pixels transparentes é preenchido com a cor do
   vizinho opaco antes (evita franjas), e o alfa é ampliado à parte. A cor
   (Cb/Cr) e os tons gerais vêm do original ampliado por bicúbico; do modelo
   só se usa o detalhe fino, para não mudar a aparência.
3. **Troca**: imagens opacas viram JPEG q92 (DefineBitsJPEG2); com alfa, PNG
   (DefineBitsJPEG3).
4. **Matrizes**: no XML do `ffdec -swf2xml`, a escala das matrizes de
   preenchimento das imagens trocadas é dividida por 2, para que ocupem a
   mesma área.
5. **Compactação**: as JPEG3 são regravadas como JPEG pré-multiplicado + alfa
   em zlib (como no original) e o SWF é salvo compactado (CWS).

O FPS não foi alterado: as animações do jogo são feitas a 18 fps e só
ficariam aceleradas.

## Licença

O código deste repositório é MIT (ver `LICENSE`). O Ruffle tem licença
própria em `public/ruffle/`. *Age of Castles* pertence aos seus autores e
não é distribuído aqui.
