/**
 * _pyodideFetchToFS 의 3가지 방법이 실제로 동작하는지 검증.
 * prefetch 없이 Company() 호출 → auto-fetch 경로 확인.
 *
 * cd pyodide && node test_autofetch.mjs
 */
import { loadPyodide } from "pyodide";
import { readFileSync } from "fs";

const STOCK = "005930";
const HF = "https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main";

async function main() {
  console.log("[1] Pyodide + 패키지...");
  const py = await loadPyodide();
  await py.loadPackage(["polars", "pyarrow", "micropip", "beautifulsoup4", "lxml", "httpx", "pydantic", "rich", "sqlite3", "numpy"]);

  console.log("[2] dartlab wheel 설치...");
  const wheelBuf = readFileSync("dartlab-0.9.12-py3-none-any.whl");
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

  console.log("[3] 4가지 fetch 방법 개별 테스트 (prefetch 없음)...\n");

  // 방법 0: JSPI run_sync + pyfetch
  console.log("--- 방법 0: JSPI (pyodide.ffi.run_sync + pyfetch) ---");
  const m0 = await py.runPythonAsync(`
try:
    from pyodide.ffi import run_sync
    from pyodide.http import pyfetch
    r = run_sync(pyfetch("${HF}/dart/finance/${STOCK}.parquet"))
    if r.status == 200:
        buf = bytes(run_sync(r.bytes()))
        result = f"OK: status=200 bytes={len(buf)} magic={buf[:4].hex()}"
    else:
        result = f"FAIL: status={r.status}"
except Exception as e:
    result = f"FAIL: {type(e).__name__}: {e}"
result
  `);
  console.log(`  ${m0}\n`);


  // 방법 1: pyfetch + run_until_complete
  console.log("--- 방법 1: pyodide.http.pyfetch (async → run_until_complete) ---");
  const m1 = await py.runPythonAsync(`
import sys, traceback
try:
    import asyncio
    from pyodide.http import pyfetch
    async def _f():
        r = await pyfetch("${HF}/dart/finance/${STOCK}.parquet")
        return (r.status, len(await r.bytes()))
    loop = asyncio.get_event_loop()
    if loop.is_running():
        result = f"SKIP: loop.is_running()=True"
    else:
        status, size = loop.run_until_complete(_f())
        result = f"OK: status={status} bytes={size}"
except Exception as e:
    result = f"FAIL: {type(e).__name__}: {e}"
result
  `);
  console.log(`  ${m1}\n`);

  // 방법 2: sync XMLHttpRequest
  console.log("--- 방법 2: XMLHttpRequest sync (xhr.open(url, False)) ---");
  const m2 = await py.runPythonAsync(`
import traceback
try:
    from js import XMLHttpRequest
    xhr = XMLHttpRequest.new()
    xhr.open("GET", "${HF}/dart/finance/${STOCK}.parquet", False)
    xhr.overrideMimeType("text/plain; charset=x-user-defined")
    xhr.send()
    if xhr.status == 200:
        raw = xhr.responseText
        buf = bytes(ord(c) & 0xFF for c in raw)
        result = f"OK: status=200 bytes={len(buf)} magic={buf[:4].hex()}"
    else:
        result = f"FAIL: status={xhr.status}"
except Exception as e:
    result = f"FAIL: {type(e).__name__}: {e}"
result
  `);
  console.log(`  ${m2}\n`);

  // 방법 3: open_url
  console.log("--- 방법 3: pyodide.http.open_url ---");
  const m3 = await py.runPythonAsync(`
try:
    from pyodide.http import open_url
    resp = open_url("${HF}/dart/finance/${STOCK}.parquet")
    raw = resp.read()
    buf = raw.encode("latin-1") if isinstance(raw, str) else raw
    result = f"OK: bytes={len(buf)} magic={buf[:4].hex()}"
except Exception as e:
    result = f"FAIL: {type(e).__name__}: {e}"
result
  `);
  console.log(`  ${m3}\n`);

  // 최종: 셋 다 없이 Company() 호출
  console.log("--- 최종: prefetch 없이 Company() + c.show(\"IS\") ---");
  const full = await py.runPythonAsync(`
import traceback, io
try:
    import dartlab
    c = dartlab.Company("${STOCK}")
    df = c.show("IS")
    result = f"OK: shape={df.shape if df is not None else None}"
except Exception as e:
    buf = io.StringIO(); traceback.print_exc(file=buf)
    result = f"FAIL: {type(e).__name__}: {e}\\n{buf.getvalue()[-800:]}"
result
  `);
  console.log(`  ${full}\n`);
}

main().catch(e => { console.error(e); process.exit(1); });
