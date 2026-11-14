import { installSaveBridge } from "./save-bridge.js";

const ruffleContainer = document.querySelector("#ruffle-container");

window.RufflePlayer = window.RufflePlayer || {};
window.RufflePlayer.config = {
  autoplay: "on",
  unmuteOverlay: "hidden",
  splashScreen: false,
  scale: "showAll",
  letterbox: "on",
  quality: "high",
  warnOnUnsupportedContent: false,
  // Sem isso o Ruffle descarta os fscommands do SWF, e o save
  // (src/save-bridge.js) nunca é chamado. O SWF é servido pelo próprio site.
  allowScriptAccess: true,
};

const ruffle = window.RufflePlayer?.newest?.();

if (!ruffle) {
  throw new Error("Ruffle não carregou. Verifique public/ruffle/ruffle.js.");
}

const player = ruffle.createPlayer();
ruffleContainer.replaceChildren(player);
installSaveBridge(player);

// __SWF_FILE__ e __SWF_VERSION__ vêm do vite.config.js.
// A versão é o início do SHA-256 do arquivo, para o cache nunca servir
// uma versão antiga do SWF.
const swfUrl = new URL(__SWF_FILE__, document.baseURI).href;
player.ruffle().load(`${swfUrl}?v=${__SWF_VERSION__}`);
