// Persistência de saves para o SWF original.
//
// Na versão Windows, o jogo rodava dentro do Flash Studio e salvava assim:
//   fscommand("flashstudio.saveutf8_filename", "\"save.xml\"");
//   fscommand("flashstudio.saveutf8", <xml do save>);
// e carregava com XML.load("./save.xml"), lendo o arquivo do disco.
//
// No navegador, esses fscommands não fazem nada e o "./save.xml" viraria uma
// requisição ao servidor. Esta ponte grava o XML no localStorage e responde
// as requisições de save.xml com o conteúdo gravado, sem alterar o SWF.

const STORAGE_PREFIX = "ageofcastles:";
const DEFAULT_FILENAME = "save.xml";

const memoryFallback = new Map();

function storageKey(filename) {
  return STORAGE_PREFIX + filename;
}

// A cópia em memória é sempre a mais recente da sessão, mesmo que o
// localStorage tenha recusado a última gravação.
function readSave(filename) {
  if (memoryFallback.has(filename)) return memoryFallback.get(filename);
  try {
    return window.localStorage.getItem(storageKey(filename));
  } catch {
    // localStorage indisponível (modo privado, bloqueado etc.).
    return null;
  }
}

function writeSave(filename, contents) {
  memoryFallback.set(filename, contents);
  try {
    window.localStorage.setItem(storageKey(filename), contents);
  } catch (error) {
    console.warn("Não foi possível gravar o save no localStorage:", error);
  }
}

// Os argumentos chegam como no ActionScript: "\"save.xml\"".
function parseFilename(args) {
  const name = String(args ?? "")
    .trim()
    .replace(/^"(.*)"$/s, "$1")
    .split(/[\\/]/)
    .pop();
  return name || DEFAULT_FILENAME;
}

function saveFilenameFromUrl(rawUrl) {
  let url;
  try {
    url = new URL(rawUrl, document.baseURI);
  } catch {
    return null;
  }
  if (url.origin !== window.location.origin) return null;
  const name = url.pathname.split("/").pop();
  return name && name.toLowerCase().endsWith(".xml") && name.startsWith("save")
    ? name
    : null;
}

function installFetchInterceptor() {
  const originalFetch = window.fetch.bind(window);

  window.fetch = function fetchWithSaves(input, init) {
    const rawUrl = input instanceof Request ? input.url : String(input);
    const filename = saveFilenameFromUrl(rawUrl);

    if (filename) {
      const contents = readSave(filename);
      if (contents === null) {
        return Promise.resolve(
          new Response("", { status: 404, statusText: "Not Found" }),
        );
      }
      return Promise.resolve(
        new Response(contents, {
          status: 200,
          headers: { "Content-Type": "text/xml; charset=utf-8" },
        }),
      );
    }

    return originalFetch(input, init);
  };
}

function installFSCommandHandler(player) {
  let pendingFilename = DEFAULT_FILENAME;

  player.ruffle().addFSCommandHandler((command, args) => {
    switch (command) {
      case "flashstudio.saveutf8_filename":
        pendingFilename = parseFilename(args);
        break;
      case "flashstudio.saveutf8":
        writeSave(pendingFilename, String(args ?? ""));
        pendingFilename = DEFAULT_FILENAME;
        break;
      default:
        // quit, flashstudio.exit, flashstudio.setdxres, prompt_adv:
        // sem equivalente no navegador.
        break;
    }
  });
}

// Deve rodar antes de o SWF ser carregado.
export function installSaveBridge(player) {
  installFetchInterceptor();
  installFSCommandHandler(player);
}
