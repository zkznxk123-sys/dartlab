import { loadPyodide } from "pyodide";
import { readFileSync } from "fs";

const log = (msg) => console.log(msg);

async function main() {
  const t0 = performance.now();

  log("[1] Pyodide 로드...");
  const py = await loadPyodide();
  log("    " + py.version);

  log("[2] 빌트인 패키지 로드...");
  await py.loadPackage(["polars", "pyarrow", "micropip", "beautifulsoup4", "lxml", "httpx", "pydantic", "rich", "sqlite3"]);

  log("[3] dartlab wheel 설치...");
  const wheelBuf = readFileSync("dartlab-0.9.8-py3-none-any.whl");
  py.FS.writeFile("/tmp/dartlab.whl", wheelBuf);
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

  log("[4] HF parquet pre-fetch → FS...");
  const HF = "https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main";
  for (const cat of ["dart/docs", "dart/finance", "dart/report"]) {
    const url = `${HF}/${cat}/005930.parquet`;
    const resp = await fetch(url);
    if (!resp.ok) { log(`    ⚠ ${cat} 실패`); continue; }
    const buf = new Uint8Array(await resp.arrayBuffer());
    py.FS.mkdirTree(`/data/${cat}`);
    py.FS.writeFile(`/data/${cat}/005930.parquet`, buf);
    log(`    ${cat}: ${(buf.length / 1024).toFixed(0)} KB`);
  }

  log("[5] import dartlab + Company...");
  await py.runPythonAsync(`
import dartlab
print(f"dartlab {dartlab.__version__}")
c = dartlab.Company("005930")
print(f"Company: {c.stockCode}")
  `);

  log("[6] marginTrend 디버그...");
  await py.runPythonAsync(`
import traceback, io
try:
    # select IS 원본 확인
    isResult = c.select("IS", ["매출액", "매출원가", "매출총이익", "판매비와관리비", "영업이익", "당기순이익"])
    print(f"select IS shape: {isResult.df.shape}")
    print(isResult.df.head(6))

    # toDictBySnakeId 결과
    from dartlab.analysis.financial._helpers import toDictBySnakeId
    parsed = toDictBySnakeId(isResult)
    if parsed:
        data, periods = parsed
        print(f"periods: {periods}")
        print(f"keys: {list(data.keys())}")
        for k in list(data.keys())[:3]:
            vals = data[k]
            print(f"  {k}: {dict(list(vals.items())[:3])}")
    else:
        print("toDictBySnakeId = None")

    # calcMarginTrend 직접 호출
    from dartlab.analysis.financial.profitability import calcMarginTrend
    mt = calcMarginTrend(c)
    print(f"calcMarginTrend: {type(mt)}")
    if mt:
        print(f"  keys: {list(mt.keys())}")
except Exception:
    buf = io.StringIO()
    traceback.print_exc(file=buf)
    print(buf.getvalue())
  `);

  log("[7] review...");
  await py.runPythonAsync(`
try:
    r = c.review("수익성")
    md = r.toMarkdown()
    print(f"review: {len(md)}자")
except Exception:
    buf = io.StringIO()
    traceback.print_exc(file=buf)
    print(buf.getvalue())
  `);

  log(`\n완료 (${((performance.now() - t0) / 1000).toFixed(1)}s)`);
}

main().catch(console.error);
