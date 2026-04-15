/**
 * xlwings_diagnose.py 를 Node pyodide 환경에서 돌려 baseline 확보.
 * node --experimental-wasm-stack-switching test_diagnose.mjs
 */
import { loadPyodide } from "pyodide";
import { readFileSync } from "fs";

async function main() {
  const py = await loadPyodide();
  await py.loadPackage(["polars", "pyarrow", "micropip", "beautifulsoup4", "lxml", "httpx", "pydantic", "rich", "sqlite3", "numpy"]);

  const wheelBuf = readFileSync("dartlab-0.9.13-py3-none-any.whl");
  py.FS.writeFile("/tmp/dartlab.whl", wheelBuf);
  await py.runPythonAsync(`
import micropip
await micropip.install(["diff-match-patch", "openpyxl"])
import zipfile, site
whl = zipfile.ZipFile("/tmp/dartlab.whl")
sp = site.getsitepackages()[0] if site.getsitepackages() else "/lib/python3.12/site-packages"
whl.extractall(sp)
whl.close()
  `);

  const code = readFileSync("xlwings_diagnose.py", "utf-8");
  await py.runPythonAsync(code);
}

main().catch(e => { console.error(e); process.exit(1); });
