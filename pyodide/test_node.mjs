/**
 * dartlab pyodide 종합 테스트 — 핵심 기능 전부 확인.
 * cd pyodide && node test_node.mjs
 */
import { loadPyodide } from "pyodide";
import { readFileSync } from "fs";

const STOCK = "005930";
const HF = "https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main";
const log = (msg) => console.log(msg);

async function main() {
  const t0 = performance.now();
  const results = [];
  function check(name, ok) {
    results.push({ name, ok });
    log(`  ${ok ? "✅" : "❌"} ${name}`);
  }

  log("[1] Pyodide + 패키지...");
  const py = await loadPyodide();
  await py.loadPackage(["polars", "pyarrow", "micropip", "beautifulsoup4", "lxml", "httpx", "pydantic", "rich", "sqlite3", "numpy"]);

  log("[2] dartlab wheel 설치...");
  const wheelBuf = readFileSync("dartlab-0.9.10-py3-none-any.whl");
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

  log("[3] HF parquet prefetch...");
  for (const cat of ["dart/docs", "dart/finance", "dart/report"]) {
    const r = await fetch(`${HF}/${cat}/${STOCK}.parquet`);
    const buf = new Uint8Array(await r.arrayBuffer());
    py.FS.mkdirTree(`/data/${cat}`);
    py.FS.writeFile(`/data/${cat}/${STOCK}.parquet`, buf);
  }

  log("[4] 핵심 기능 테스트...\n");

  // import + Company
  const importOk = await py.runPythonAsync(`
import dartlab
v = dartlab.__version__
c = dartlab.Company("${STOCK}")
v
  `);
  check("import dartlab + Company", !!importOk);

  // show IS
  const isShape = await py.runPythonAsync(`
df = c.show("IS")
f"{df.shape[0]}x{df.shape[1]}" if df is not None else "None"
  `);
  check(`show IS = ${isShape} (33x42 기대)`, isShape === "33x42");

  // show IS 컬럼 (분기)
  const isCol = await py.runPythonAsync(`c.show("IS").columns[2] if c.show("IS") is not None else "None"`);
  check(`IS 컬럼 분기 = ${isCol}`, isCol && isCol.includes("Q"));

  // show IS 매출액 존재
  const hasSales = await py.runPythonAsync(`
"매출액" in c.show("IS")["항목"].to_list() if c.show("IS") is not None else False
  `);
  check("IS 매출액 포함", hasSales === true);

  // show BS
  const bsShape = await py.runPythonAsync(`
df = c.show("BS")
f"{df.shape[0]}x{df.shape[1]}" if df is not None else "None"
  `);
  check(`show BS = ${bsShape}`, bsShape !== "None" && bsShape !== null);

  // show CF
  const cfShape = await py.runPythonAsync(`
df = c.show("CF")
f"{df.shape[0]}x{df.shape[1]}" if df is not None else "None"
  `);
  check(`show CF = ${cfShape}`, cfShape !== "None" && cfShape !== null);

  // show CIS
  const cisShape = await py.runPythonAsync(`
df = c.show("CIS")
f"{df.shape[0]}x{df.shape[1]}" if df is not None else "None"
  `);
  check(`show CIS = ${cisShape}`, cisShape !== "None" && cisShape !== null);

  // analysis 수익성
  const profKeys = await py.runPythonAsync(`
r = c.analysis("financial", "수익성")
",".join(k for k,v in r.items() if v is not None) if r else "None"
  `);
  check(`analysis 수익성 non-None = ${profKeys}`, profKeys && profKeys.includes("marginTrend"));

  // analysis 성장성
  const growKeys = await py.runPythonAsync(`
r = c.analysis("financial", "성장성")
",".join(k for k,v in r.items() if v is not None) if r else "None"
  `);
  check(`analysis 성장성 non-None = ${growKeys}`, growKeys !== "None" && growKeys !== null);

  // analysis 안정성
  const stabKeys = await py.runPythonAsync(`
r = c.analysis("financial", "안정성")
",".join(k for k,v in r.items() if v is not None) if r else "None"
  `);
  check(`analysis 안정성 non-None = ${stabKeys}`, stabKeys !== "None" && stabKeys !== null);

  // select
  const selectShape = await py.runPythonAsync(`
s = c.select("IS", ["매출액", "영업이익"])
f"{s.df.shape[0]}x{s.df.shape[1]}" if s is not None and hasattr(s, 'df') else "None"
  `);
  check(`select IS 매출액/영업이익 = ${selectShape}`, selectShape !== "None");

  // review 수익성
  const reviewLen = await py.runPythonAsync(`
import traceback, io
_review_len = 0
try:
    md = c.review("수익성").toMarkdown()
    _review_len = len(md)
except Exception as e:
    buf = io.StringIO(); traceback.print_exc(file=buf); print(buf.getvalue())
    _review_len = -1
_review_len
  `);
  check(`review 수익성 = ${reviewLen}자`, reviewLen > 500);

  // c.index
  const indexLen = await py.runPythonAsync(`
_idx_len = 0
try:
    idx = c.index
    _idx_len = len(idx) if idx is not None else 0
except Exception as e:
    buf = io.StringIO(); traceback.print_exc(file=buf); print(buf.getvalue())
    _idx_len = -1
_idx_len
  `);
  check(`c.index = ${indexLen} topics`, indexLen > 0);

  // 결과 요약
  const total = results.length;
  const passed = results.filter(r => r.ok).length;
  const failed = results.filter(r => !r.ok);
  log(`\n${"=".repeat(50)}`);
  log(`결과: ${passed}/${total} 통과 (${((performance.now() - t0) / 1000).toFixed(1)}s)`);
  if (failed.length) {
    log(`실패:`);
    failed.forEach(f => log(`  ❌ ${f.name}`));
  }
  process.exit(failed.length > 0 ? 1 : 0);
}

main().catch(e => { console.error(e); process.exit(1); });
