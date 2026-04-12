/**
 * dartlab pyodide Node.js 검증 — HF에서 wheel 다운로드하여 테스트.
 * 사용법: cd pyodide && npm install pyodide@0.27.2 && node test_node.mjs
 */
import { loadPyodide } from "pyodide";

const HF = "https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main";
const WHEEL_URL = `${HF}/pyodide/dartlab-0.9.8-py3-none-any.whl`;
const STOCK = "005930";

const log = (msg) => console.log(msg);

async function main() {
  const t0 = performance.now();

  log("[1] Pyodide 로드...");
  const py = await loadPyodide();
  log("    " + py.version);

  log("[2] 빌트인 패키지 로드...");
  await py.loadPackage(["polars", "pyarrow", "micropip", "beautifulsoup4", "lxml", "httpx", "pydantic", "rich", "sqlite3", "numpy"]);

  log("[3] dartlab wheel 설치 (HF에서 다운로드)...");
  const wheelResp = await fetch(WHEEL_URL);
  if (!wheelResp.ok) throw new Error(`wheel fetch 실패: ${wheelResp.status}`);
  const wheelBuf = new Uint8Array(await wheelResp.arrayBuffer());
  py.FS.writeFile("/tmp/dartlab.whl", wheelBuf);
  log(`    ${(wheelBuf.length / 1024).toFixed(0)} KB`);

  await py.runPythonAsync(`
import micropip
await micropip.install(["diff-match-patch", "openpyxl"])
import zipfile, site
whl = zipfile.ZipFile("/tmp/dartlab.whl")
sp = site.getsitepackages()[0] if site.getsitepackages() else "/lib/python3.12/site-packages"
whl.extractall(sp)
whl.close()
print("dartlab 설치 완료")
  `);

  log("[4] HF parquet prefetch...");
  for (const cat of ["dart/docs", "dart/finance", "dart/report"]) {
    const url = `${HF}/${cat}/${STOCK}.parquet`;
    const r = await fetch(url);
    if (!r.ok) { log(`    ⚠ ${cat} 실패`); continue; }
    const buf = new Uint8Array(await r.arrayBuffer());
    py.FS.mkdirTree(`/data/${cat}`);
    py.FS.writeFile(`/data/${cat}/${STOCK}.parquet`, buf);
    log(`    ${cat}: ${(buf.length / 1024).toFixed(0)} KB`);
  }

  log("[5] import dartlab + Company...");
  await py.runPythonAsync(`
import dartlab
print(f"dartlab {dartlab.__version__}")
c = dartlab.Company("${STOCK}")
print(f"Company: {c.stockCode}")
  `);

  log("[6] show + analysis + review...");
  await py.runPythonAsync(`
print(f"IS: {c.show('IS').shape}")

result = c.analysis("financial", "수익성")
print(f"analysis: {list(result.keys())[:5] if result else None}")

import traceback, io
try:
    md = c.review("수익성").toMarkdown()
    print(f"review: {len(md)}자")
except Exception:
    buf = io.StringIO(); traceback.print_exc(file=buf); print(buf.getvalue())
  `);

  log(`\n✅ 완료 (${((performance.now() - t0) / 1000).toFixed(1)}s)`);
}

main().catch(console.error);
