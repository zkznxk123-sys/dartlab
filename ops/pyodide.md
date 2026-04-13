# Pyodide

dartlab을 브라우저/Excel에서 실행. 설치 없이 재무분석.

## 호출 계약

```python
import dartlab
await dartlab.prefetch("005930")
c = dartlab.Company("005930")
c.show("IS")
c.analysis("financial", "수익성")
c.review("수익성").toMarkdown()
```

---

| 항목 | 내용 |
|------|------|
| 상태 | alpha |
| 진입점 | `import dartlab` + `await dartlab.prefetch(code)` |
| 런타임 | Pyodide 0.27.2+ (WASM Python 3.12) |
| 데이터 | HuggingFace CDN (CORS OK) |
| 배포 | PyPI (`micropip.install("dartlab")`) + HF wheel |

## 아키텍처

```
[설치] micropip.install("dartlab")
         ↓ pyproject.toml 이중 마커
         lxml/polars/numpy/pyarrow/httpx → pyodide 빌트인 로드
         beautifulsoup4/openpyxl/diff-match-patch → PyPI pure Python

[데이터] await dartlab.prefetch("005930")
         ↓ pyodide.http.pyfetch (async)
         HF CDN → docs/finance/report parquet
         ↓ pyodide FS
         /data/dart/{cat}/{code}.parquet

[실행] c = dartlab.Company("005930")
         ↓ loadData → _loadDataPyodide
         pyodide FS → pyarrow.parquet.read_table → pl.from_arrow
```

## polars WASM 제약

polars WASM wheel은 parquet I/O가 비활성 (GitHub pola-rs/polars#20876).

| 함수 | 상태 | 우회 |
|------|------|------|
| `pl.read_parquet()` | ❌ | `readParquetSafe()` (pyarrow 경유) |
| `pl.write_parquet()` | ❌ | 사용하지 않음 |
| `pl.scan_parquet()` | ❌ | 사용하지 않음 |
| `pl.from_arrow()` | ✅ | pyarrow 먼저 로드 필요 |
| DataFrame 연산 전부 | ✅ | |

`readParquetSafe(path)` — `core/dataLoader.py`의 공통 유틸. 일반 환경에서는 `pl.read_parquet`, pyodide에서는 pyarrow 경유.

## pyodide 분기 패턴

모든 pyodide 분기는 `sys.platform == "emscripten"` 체크.

```python
import sys
if sys.platform == "emscripten":
    # pyodide 전용 경로
```

## 수정된 파일

| 파일 | 변경 |
|------|------|
| `pyproject.toml` | 이중 환경 마커 + artifacts에 `*.json/*.parquet` |
| `core/dataLoader.py` | `_IS_PYODIDE`, `_loadDataPyodide`, `readParquetSafe`, `_pyodideFetchToFS` |
| `core/finance/labels.py` | `Path.resolve()` → `Path.parent.parent` (pyodide FS 호환) |
| `__init__.py` | `prefetch()` async 함수 + server/cli import guard |
| `core/__init__.py` | `gather.listing` import guard |
| `providers/dart/_utils.py` | `_ensureAllData` 바이패스 + threading 순차 |
| `providers/dart/company.py` | `codeToName` 바이패스 |
| `gather/listing.py` | `getKindList` 빈 DataFrame + cache 스킵 |
| `review/registry.py` | `Section` import 순환 참조 수정 |
| `providers/dart/docs/sections/artifacts.py` | `readParquetSafe` 사용 |
| `core/finance/exogenousAxes.py` | `readParquetSafe` 사용 |

## pyodide 불가 기능

| 기능 | 사유 |
|------|------|
| `dartlab.scan()` | scan 프리빌드 271MB |
| `dartlab.gather()` | 외부 API CORS 차단 |
| `dartlab.collect()` | DART OpenAPI CORS 차단 |
| `dartlab.ask()` (oauth-codex) | chatgpt.com CORS 차단 |
| `dartlab.ask()` (gemini/openai) | API 키 방식으로 가능 (CORS OK) |
| KRX 상장법인 목록 | KRX API CORS 차단 → 빈 DataFrame |
| threading | WASM 단일 스레드 |

## 배포 타겟

| 타겟 | 설치 방법 |
|------|----------|
| xlwings lite | requirements에 `dartlab` 추가 |
| JupyterLite | `micropip.install("dartlab")` |
| 브라우저 (playground) | `pyodide/loader.js` 사용 |

## prefetch

`dartlab.prefetch()` — pyodide 전용 async 함수. Company 생성 전에 호출.

```python
await dartlab.prefetch("005930")           # 단일
await dartlab.prefetch("005930", "000660")  # 복수
```

내부 동작:
1. `pyodide_js.loadPackage(["pyarrow", "lxml", "polars", "numpy", "pydantic"])` — C 확장 빌트인 로드
2. `pyodide.http.pyfetch(HF_URL)` — docs/finance/report parquet 다운로드
3. pyodide FS `/data/dart/{cat}/{code}.parquet`에 저장

일반 환경에서는 no-op.

## 빌드/배포

```bash
# wheel 빌드 (pyodide deps 제거 버전)
python pyodide/build.py

# wheel 빌드 + HF 업로드
python pyodide/build.py --upload

# Node.js 테스트
cd pyodide && node test_node.mjs
```

`build.py`는 원본 wheel에서 pyodide 미지원 deps를 제거하고 pyodide 빌트인 deps의 버전 제약을 완화한 전용 wheel을 생성한다.

PyPI wheel은 이중 마커로 pyodide 호환:
```toml
"lxml>=6.0.2,<7; sys_platform != 'emscripten'",
"lxml; sys_platform == 'emscripten'",
```

## 검증 결과 (2026-04-13)

Node.js pyodide 0.27.2, 삼성전자 005930:

| 테스트 | 결과 |
|--------|------|
| import + Company | ✅ |
| show IS | ✅ 33x42 분기 |
| show BS | ✅ 59x42 |
| show CF | ✅ 63x42 |
| show CIS | ✅ 16x42 |
| analysis 수익성 | ✅ 6키 |
| analysis 성장성 | ✅ 5키 |
| analysis 안정성 | ✅ 6키 |
| select | ✅ 2x42 |
| review 수익성 | ✅ 2771자 |
| c.index | ✅ 63 topics |
| **총** | **13/13** |

## 관련 코드

| 경로 | 역할 |
|------|------|
| `pyodide/` | 빌드 스크립트 + 테스트 + 문서 |
| `pyodide/loader.js` | JS 초기화 헬퍼 (playground/xlwings 공용) |
| `pyodide/build.py` | wheel 빌드 + HF 업로드 |
| `pyodide/test_node.mjs` | Node.js 종합 테스트 (13개) |
| `src/dartlab/core/dataLoader.py` | `readParquetSafe`, `_loadDataPyodide` |
| `experiments/120_pyodidePoc/` | 초기 POC (아카이브) |
