// Gera dist/age-of-castles.html: o jogo inteiro em um único arquivo HTML,
// que funciona aberto direto do disco (file://), sem servidor.
//
// Rodar depois do `vite build` (npm run build:single). O que vai dentro:
// - CSS e JS do app (dist/assets), inline;
// - os dois núcleos JS do Ruffle, inline ANTES do ruffle.js: são chunks
//   JSONP do webpack, então o Ruffle os encontra já registrados e não os
//   busca por <script src>;
// - ruffle.js, inline;
// - os dois .wasm do Ruffle e o SWF, comprimidos com
//   gzip e guardados em base64 em <script type="application/octet-stream">,
//   que o navegador não executa;
// - um interceptador de fetch, rodado primeiro, que entrega esses arquivos
//   quando o Ruffle os pede pelo nome.
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { gzipSync } from "node:zlib";

const root = resolve(import.meta.dirname, "..");
const dist = join(root, "dist");
const ruffleDir = join(root, "public", "ruffle");
const OUT = join(dist, "age-of-castles.html");

const SWF = "ageofcastles.swf";
const swfPath = join(root, "public", SWF);

let html = readFileSync(join(dist, "index.html"), "utf8");

// Nada de "</script" literal dentro dos scripts inline.
const safeJs = (code) => code.replace(/<\/script/gi, "<\\/script");

// 1) CSS do app
html = html.replace(/<link rel="stylesheet"[^>]*href="\/?(assets\/[^"]+\.css)"[^>]*>/g, (_, href) =>
  `<style>${readFileSync(join(dist, href), "utf8")}</style>`,
);

// 2) JS do app (módulo)
html = html.replace(
  /<script type="module"[^>]*src="\/?(assets\/[^"]+\.js)"[^>]*><\/script>/g,
  (_, src) => `<script type="module">${safeJs(readFileSync(join(dist, src), "utf8"))}</script>`,
);

// 3) Arquivos embutidos: wasm do Ruffle e SWF
const assets = [];
for (const f of readdirSync(ruffleDir).filter((f) => f.endsWith(".wasm"))) {
  assets.push({ name: f, type: "application/wasm", path: join(ruffleDir, f) });
}
assets.push({ name: SWF, type: "application/x-shockwave-flash", path: swfPath });

const blobs = assets
  .map((a, i) => {
    const raw = readFileSync(a.path);
    a.size = raw.length;
    a.gz = gzipSync(raw, { level: 9 });
    return `<script type="application/octet-stream" id="embed-${i}">${a.gz.toString("base64")}</script>`;
  })
  .join("\n");

const manifest = Object.fromEntries(assets.map((a, i) => [a.name, { id: `embed-${i}`, type: a.type }]));

const boot = `<script>
(() => {
  // Entrega os arquivos embutidos quando o Ruffle os pede (wasm, SWF).
  const manifest = ${JSON.stringify(manifest)};
  const absent = ["hyperlinks.txt", "logo.swf"];
  const originalFetch = window.fetch.bind(window);
  const cache = new Map();
  async function load(name) {
    const entry = manifest[name];
    const el = document.getElementById(entry.id);
    const packed = await originalFetch("data:application/octet-stream;base64," + el.textContent.trim());
    const body = packed.body.pipeThrough(new DecompressionStream("gzip"));
    const bytes = await new Response(body).arrayBuffer();
    el.remove(); // libera a memória do texto base64
    return bytes;
  }
  window.fetch = function fetchEmbedded(input, init) {
    const url = input instanceof Request ? input.url : String(input);
    let name = "";
    try { name = new URL(url, document.baseURI).pathname.split("/").pop(); } catch {}
    const entry = manifest[name];
    // Arquivos externos opcionais que o SWF tenta carregar e que não
    // existem: responde 404 em vez de deixar o navegador tentar (em file://
    // isso vira erro no console).
    if (!entry && absent.includes(name)) return Promise.resolve(new Response("", { status: 404 }));
    if (!entry) return originalFetch(input, init);
    if (!cache.has(name)) cache.set(name, load(name));
    return cache.get(name).then((bytes) =>
      new Response(bytes.slice(0), { status: 200, headers: { "Content-Type": entry.type } }));
  };
})();
</script>`;

// 4) Núcleos do Ruffle e ruffle.js, inline, nessa ordem
const cores = readdirSync(ruffleDir)
  .filter((f) => /^core\.ruffle\..*\.js$/.test(f))
  .map((f) => `<script>${safeJs(readFileSync(join(ruffleDir, f), "utf8"))}</script>`)
  .join("\n");
const ruffle = `<script>${safeJs(readFileSync(join(ruffleDir, "ruffle.js"), "utf8"))}</script>`;

const ruffleTag = /<script src="\/?ruffle\/ruffle\.js"><\/script>/;
if (!ruffleTag.test(html)) throw new Error("tag do ruffle.js não encontrada em dist/index.html");
html = html.replace(ruffleTag, () => `${blobs}\n${boot}\n${cores}\n${ruffle}`);

if (/(src|href)="\/?(assets|ruffle)\//.test(html)) {
  throw new Error("ainda há referências a arquivos externos em assets/ ou ruffle/");
}

writeFileSync(OUT, html);
const mb = (n) => (n / 1e6).toFixed(1) + " MB";
for (const a of assets) console.log(`  ${a.name}: ${mb(a.size)} -> gzip ${mb(a.gz.length)}`);
console.log(`dist/age-of-castles.html: ${mb(statSync(OUT).size)} (SWF: ${SWF})`);
console.log("sha256:", createHash("sha256").update(readFileSync(OUT)).digest("hex").slice(0, 16));
