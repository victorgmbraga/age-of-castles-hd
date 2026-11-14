// Roda um script Python com o interpretador do sistema, em Linux, macOS e
// Windows. Uso (pelos scripts do package.json): node scripts/py.mjs <script.py> [args...]
//
// Procura, nesta ordem: python3, python, py -3 (lançador do Windows). Pula
// interpretadores com versão menor que 3.10 e o atalho da Microsoft Store,
// que existe como "python.exe" mas só abre a loja.
import { spawnSync } from "node:child_process";

const MIN = [3, 10];
const candidates = [["python3"], ["python"], ["py", "-3"]];

function works([cmd, ...pre]) {
  const r = spawnSync(cmd, [...pre, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"], {
    encoding: "utf8",
  });
  if (r.status !== 0 || !r.stdout) return false;
  const [maj, min] = r.stdout.trim().split(".").map(Number);
  return maj > MIN[0] || (maj === MIN[0] && min >= MIN[1]);
}

const python = candidates.find(works);
if (!python) {
  console.error(
    `Python ${MIN.join(".")}+ não encontrado.\n` +
      "  Windows: instale pelo https://www.python.org (marque \"Add python.exe to PATH\")\n" +
      "           ou rode: winget install Python.Python.3.12\n" +
      "  Linux:   instale python3 e python3-venv pelo gerenciador de pacotes\n" +
      "  macOS:   brew install python",
  );
  process.exit(1);
}

const [cmd, ...pre] = python;
// -X utf8: no Windows, sem isso a saída redirecionada sai em cp1252 e os
// acentos se corrompem (o build.py repassa a opção para os scripts que chama).
const r = spawnSync(cmd, [...pre, "-I", "-X", "utf8", ...process.argv.slice(2)], { stdio: "inherit" });
process.exit(r.status ?? 1);
