/**
 * Company() → c.show("IS") 호출 시 어느 카테고리가 fetch 되는지 추적.
 * node --experimental-wasm-stack-switching test_fetchOrder.mjs
 */
import { loadPyodide } from "pyodide";
import { readFileSync } from "fs";

const STOCK = "005930";
const fetchLog = [];

// 원본 fetch 가로채서 HF URL 만 기록
const origFetch = globalThis.fetch;
globalThis.fetch = async (url, opts) => {
  const s = String(url);
  if (s.includes("huggingface.co")) {
    const cat = s.match(/\/(dart\/[^/]+)\//)?.[1] || s;
    fetchLog.push(cat);
    console.log(`  [fetch] ${cat}`);
  }
  return origFetch(url, opts);
};

async function main() {
  console.log("[1] Pyodide 로드...");
  const py = await loadPyodide();
  await py.loadPackage(["polars", "pyarrow", "micropip", "beautifulsoup4", "lxml", "httpx", "pydantic", "rich", "sqlite3", "numpy"]);

  console.log("[2] dartlab 0.9.13 wheel 설치...");
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

  console.log("\n[3] dartlab.Company() — fetch 추적:");
  fetchLog.length = 0;
  await py.runPythonAsync(`
import dartlab
c = dartlab.Company("${STOCK}")
print(f"corpName = {c.corpName!r}")
  `);
  console.log(`  Company() 결과: ${fetchLog.length}개 fetch → [${fetchLog.join(", ")}]`);

  console.log("\n[4] c.show(\"IS\") — fetch 추적:");
  fetchLog.length = 0;
  const shape = await py.runPythonAsync(`
df = c.show("IS")
f"{df.shape}"
  `);
  console.log(`  show("IS") 결과: ${fetchLog.length}개 fetch → [${fetchLog.join(", ")}] shape=${shape}`);

  console.log("\n[5] c.show(\"BS\") — 재fetch 있나?:");
  fetchLog.length = 0;
  await py.runPythonAsync(`c.show("BS")`);
  console.log(`  show("BS") 결과: ${fetchLog.length}개 fetch → [${fetchLog.join(", ")}]`);
}

main().catch(e => { console.error(e); process.exit(1); });
