/**
 * dartlab Pyodide 로더 — 모든 배포 타겟(playground, xlwings lite, JupyterLite)이 공유.
 *
 * 사용법:
 *   import { initDartlab } from "./loader.js";
 *   const { py, run } = await initDartlab({ stockCode: "005930", onLog: console.log });
 *   await run(`print(c.show("IS").shape)`);
 */

const HF_BASE = "https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main";
const WHEEL_BASE = HF_BASE + "/pyodide";
const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js";

const BUILTIN_PACKAGES = [
  "polars", "pyarrow", "micropip", "beautifulsoup4", "lxml",
  "httpx", "pydantic", "rich", "sqlite3", "numpy",
];

const PURE_DEPS = ["diff-match-patch", "openpyxl"];

const DATA_CATEGORIES = [
  { dir: "dart/docs", name: "docs" },
  { dir: "dart/finance", name: "finance" },
  { dir: "dart/report", name: "report" },
];

/**
 * dartlab을 pyodide에서 초기화한다.
 *
 * @param {Object} options
 * @param {string} options.stockCode - 종목코드 (기본 "005930")
 * @param {string} [options.wheelUrl] - wheel URL override (기본: HF)
 * @param {string} [options.version] - dartlab 버전 (기본: "0.9.8")
 * @param {(msg: string) => void} [options.onLog] - 로그 콜백
 * @param {(step: string, progress: number) => void} [options.onProgress] - 진행 콜백
 * @returns {{ py: PyodideInterface, run: (code: string) => Promise<any> }}
 */
export async function initDartlab(options = {}) {
  const {
    stockCode = "005930",
    version = "0.9.8",
    wheelUrl = null,
    onLog = () => {},
    onProgress = () => {},
  } = options;

  // 1. Pyodide 로드
  onProgress("pyodide", 0);
  onLog("[1/5] Pyodide 로드...");

  let loadPyodide;
  if (typeof globalThis.loadPyodide === "function") {
    loadPyodide = globalThis.loadPyodide;
  } else {
    // 동적 import (브라우저에서 CDN script 태그 없이 사용 시)
    const mod = await import(/* webpackIgnore: true */ PYODIDE_CDN);
    loadPyodide = mod.loadPyodide;
  }

  const py = await loadPyodide();
  onLog(`    Pyodide ${py.version}`);

  // 2. 빌트인 패키지
  onProgress("packages", 0.2);
  onLog("[2/5] 빌트인 패키지 로드...");
  await py.loadPackage(BUILTIN_PACKAGES);

  // 3. dartlab wheel 설치
  onProgress("wheel", 0.4);
  onLog("[3/5] dartlab wheel 설치...");

  const whlUrl = wheelUrl || `${WHEEL_BASE}/dartlab-${version}-py3-none-any.whl`;
  const wheelResp = await fetch(whlUrl);
  if (!wheelResp.ok) throw new Error(`wheel fetch 실패: ${wheelResp.status} ${whlUrl}`);
  const wheelBuf = new Uint8Array(await wheelResp.arrayBuffer());
  py.FS.writeFile("/tmp/dartlab.whl", wheelBuf);
  onLog(`    ${(wheelBuf.length / 1024).toFixed(0)} KB`);

  await py.runPythonAsync(`
import micropip
await micropip.install(${JSON.stringify(PURE_DEPS)})
import zipfile, site
whl = zipfile.ZipFile("/tmp/dartlab.whl")
sp = site.getsitepackages()[0] if site.getsitepackages() else "/lib/python3.12/site-packages"
whl.extractall(sp)
whl.close()
  `);

  // 4. HF parquet prefetch
  onProgress("data", 0.6);
  onLog("[4/5] HF 데이터 다운로드...");

  for (const cat of DATA_CATEGORIES) {
    const url = `${HF_BASE}/${cat.dir}/${stockCode}.parquet`;
    const r = await fetch(url);
    if (!r.ok) { onLog(`    ⚠ ${cat.name} 실패 (${r.status})`); continue; }
    const buf = new Uint8Array(await r.arrayBuffer());
    py.FS.mkdirTree(`/data/${cat.dir}`);
    py.FS.writeFile(`/data/${cat.dir}/${stockCode}.parquet`, buf);
    onLog(`    ${cat.name}: ${(buf.length / 1024).toFixed(0)} KB`);
  }

  // 5. import + Company 생성
  onProgress("init", 0.9);
  onLog("[5/5] dartlab 초기화...");

  py.setStdout({ batched: (msg) => onLog("    " + msg) });

  await py.runPythonAsync(`
import dartlab
c = dartlab.Company("${stockCode}")
  `);
  onLog(`    Company(${stockCode}) 준비 완료`);
  onProgress("done", 1.0);

  /** pyodide.runPythonAsync 래퍼 */
  async function run(code) {
    return await py.runPythonAsync(code);
  }

  return { py, run };
}

/**
 * 추가 종목 데이터를 prefetch하고 Company를 생성한다.
 */
export async function loadCompany(py, stockCode, options = {}) {
  const { onLog = () => {} } = options;

  for (const cat of DATA_CATEGORIES) {
    const url = `${HF_BASE}/${cat.dir}/${stockCode}.parquet`;
    const r = await fetch(url);
    if (!r.ok) { onLog(`⚠ ${cat.name} 실패`); continue; }
    const buf = new Uint8Array(await r.arrayBuffer());
    py.FS.mkdirTree(`/data/${cat.dir}`);
    py.FS.writeFile(`/data/${cat.dir}/${stockCode}.parquet`, buf);
  }

  await py.runPythonAsync(`c = dartlab.Company("${stockCode}")`);
  onLog(`Company(${stockCode}) 준비 완료`);
}

/**
 * AI provider API 키를 설정한다.
 */
export async function setApiKey(py, provider, apiKey) {
  const envMap = {
    gemini: ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    openai: ["OPENAI_API_KEY"],
  };
  const keys = envMap[provider];
  if (!keys) throw new Error(`지원하지 않는 provider: ${provider}`);

  for (const k of keys) {
    await py.runPythonAsync(`import os; os.environ["${k}"] = "${apiKey}"`);
  }
}
