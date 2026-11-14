import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { defineConfig } from "vite";

const SWF = "ageofcastles.swf";
const swfPath = new URL(`public/${SWF}`, import.meta.url);

// O SWF não faz parte do repositório: cada pessoa gera o seu a partir da
// própria cópia do jogo (ver README).
if (!existsSync(swfPath)) {
  throw new Error(
    `public/${SWF} não encontrado. Gere com "upscale/build.sh /caminho/do/RAW_001.exe" ` +
      `ou "upscale/build.sh --original ..." para usar o original (ver README).`,
  );
}

// A versão na URL (?v=) é o início do SHA-256 do SWF: muda sozinha quando
// o arquivo muda, e o navegador nunca reaproveita um SWF antigo do cache.
const version = createHash("sha256").update(readFileSync(swfPath)).digest("hex").slice(0, 16);

export default defineConfig({
  define: {
    __SWF_FILE__: JSON.stringify(SWF),
    __SWF_VERSION__: JSON.stringify(version),
  },
});
