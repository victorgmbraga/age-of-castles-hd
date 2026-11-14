# Coloque o jogo aqui

Copie para esta pasta **um** destes arquivos da sua cópia do Age of Castles:

- `RAW_001.exe`, o executável da instalação Windows (o SWF é extraído dele);
- ou `ageofcastles.swf`.

Depois, na raiz do projeto:

```bash
npm install
npm run setup     # instala as ferramentas e gera o jogo ampliado 2x
npm run dev
```

Tudo nesta pasta, exceto este README, é ignorado pelo git: o jogo nunca vai
para o repositório.
