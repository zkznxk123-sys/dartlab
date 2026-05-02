# Pyodide

**주체**: Pyodide 배포 (브라우저 · Excel Python · pyodide node 테스트).
**현재**: 번들 json 30 개 + `accountMappings` 검증 · `test_node.mjs` 13/13 · `dartlab.prefetch()` 경로 확립.
**방향**: 번들 크기 축소 · Excel 시나리오 템플릿 · 브라우저용 lazy-load 경로.

dartlab 을 브라우저·Excel 에서 실행. 설치 없이 재무분석. 각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 1. 호출 — `prefetch` 후 Company 로 간다

```python
import dartlab
await dartlab.prefetch("005930")
c = dartlab.Company("005930")
c.show("IS")
c.analysis("financial", "수익성")
c.story("수익성").toMarkdown()
```

| 항목 | 내용 |
|---|---|
| 상태 | alpha |
| 진입점 | `import dartlab` + `await dartlab.prefetch(code)` |
| 런타임 | Pyodide 0.27.2+ (WASM Python 3.12) |
| 데이터 | HuggingFace CDN (CORS OK) |
| 배포 | PyPI (`micropip.install("dartlab")`) + HF wheel |

---

## 2. 아키텍처 — 설치·데이터·실행 3 층으로 간다

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

---

## 3. polars WASM 제약 — pyarrow 경유로 우회한다

polars WASM wheel 은 parquet I/O 가 비활성 (GitHub `pola-rs/polars#20876`).

| 함수 | 상태 | 우회 |
|---|---|---|
| `pl.read_parquet()` | ❌ | `readParquetSafe()` (pyarrow 경유) |
| `pl.write_parquet()` | ❌ | 사용하지 않음 |
| `pl.scan_parquet()` | ❌ | 사용하지 않음 |
| `pl.from_arrow()` | ✓ | pyarrow 먼저 로드 필요 |
| DataFrame 연산 전부 | ✓ | |

`readParquetSafe(path)` — `core/dataLoader.py` 의 공통 유틸. 일반 환경에서는 `pl.read_parquet`, pyodide 에서는 pyarrow 경유.

**반복 실패** — `pl.read_parquet` 직접 호출 → pyodide 에서 에러. 항상 `readParquetSafe` 사용.

---

## 4. pyodide 분기 패턴 — `sys.platform == "emscripten"` 로 체크한다

```python
import sys
if sys.platform == "emscripten":
    # pyodide 전용 경로
```

### 수정된 파일

| 파일 | 변경 |
|---|---|
| `pyproject.toml` | 이중 환경 마커 + `artifacts` 에 `*.json` · `*.parquet` |
| `core/dataLoader.py` | `_IS_PYODIDE` · `_loadDataPyodide` · `readParquetSafe` · `_pyodideFetchToFS` |
| `core/finance/labels.py` | `Path.resolve()` → `Path.parent.parent` (pyodide FS 호환) |
| `__init__.py` | `prefetch()` async 함수 + server · cli import guard |
| `core/__init__.py` | `gather.listing` import guard |
| `providers/dart/_utils.py` | `_ensureAllData` 바이패스 + threading 순차 |
| `providers/dart/company.py` | `codeToName` 바이패스 |
| `gather/listing.py` | `getKindList` 빈 DataFrame + cache 스킵 |
| `story/registry.py` | `Section` import 순환 참조 수정 |
| `providers/dart/docs/sections/artifacts.py` | `readParquetSafe` 사용 |
| `core/finance/exogenousAxes.py` | `readParquetSafe` 사용 |

---

## 5. pyodide 불가·제한 기능

| 기능 | 상태 |
|---|---|
| `dartlab.scan("account"/"ratio")` | ✓ 지원 — `finance-lite.parquet` (~18MB) 경량본. 30 주요 계정 × 5 년 분기만 |
| `dartlab.scan("governance"/"audit"/…)` | ❌ `report/*.parquet` 미전송 (필요 시 추가 경량본 설계 필요) |
| `dartlab.gather()` | ❌ 외부 API CORS 차단 |
| `dartlab.collect()` | ❌ DART OpenAPI CORS 차단 |
| `dartlab.ask()` (OAuth profile) | ❌ 외부 인증 도메인 CORS 차단 |
| `dartlab.ask()` (API key profile) | ✓ API 키 방식으로 가능 (CORS OK) |
| KRX 상장법인 목록 | ❌ KRX API CORS 차단 → 빈 DataFrame |
| threading | ❌ WASM 단일 스레드 |

### Skill runtimeCompatibility

`src/dartlab/skills` 의 SkillSpec 은 Pyodide 실행 가능성을 `runtimeCompatibility.pyodide` 로 표시한다.

| status | 의미 |
|---|---|
| `supported` | HF parquet/prefetch 만으로 브라우저에서 절차 수행 가능 |
| `limited` | 일부 근거만 가능. live API, OAuth, 전체 prebuild 부재 등 한계를 답변에 명시 |
| `unsupported` | 브라우저에서 실행하지 말고 서버/MCP 경로 사용 |
| `unknown` | generated capability view 등 환경 검증 전 |

웹 AI 는 이 필드를 보고 브라우저에서 가능한 skill 을 우선 고르고, `limited` 는 한계를 먼저 표시한다. 예: `krxIndexStrengthReview` 는 HF `krx/indices` parquet 를 Pyodide FS 에 내려받으면 계산 가능하지만, KRX API 실시간 호출은 하지 않는다.

### scan 지원 경로

- 프리빌드 — `dart/scan/finance-lite.parquet` (~18MB, 30 계정, 2022 년 ~ 분기).
- 다운로드 — `loader.js::loadScanLite(py)` 또는 파이썬 측 `dartlab.scan(...)` 첫 호출 시 자동.
- 내부 구현 — `scanAccount._scanAccountFromMerged` 가 `_IS_PYODIDE` 분기에서 `pyarrow.parquet.read_table` + `pl.from_arrow` 로 전환 (polars `scan_parquet` 미지원 우회).
- SSOT 계정 리스트 — `src/dartlab/scan/_helpers.py::LITE_ACCOUNTS`.

**반복 실패** — 외부 API 필요한 기능 (gather · collect · OAuth profile · KRX) 은 CORS 차단으로 불가. pyodide 대상 기능 설계 시 이 제약 먼저 확인.

---

## 6. 배포 타겟

| 타겟 | 설치 방법 |
|---|---|
| xlwings lite | `requirements` 에 `dartlab` 추가 |
| JupyterLite | `micropip.install("dartlab")` |
| 브라우저 (playground) | `pyodide/loader.js` 사용 |

---

## 7. prefetch — 일반 환경에서는 no-op, pyodide 에서는 parquet 다운로드

`dartlab.prefetch()` — pyodide 전용 async 함수. Company 생성 전에 호출.

```python
await dartlab.prefetch("005930")           # 단일
await dartlab.prefetch("005930", "000660")  # 복수
```

**내부 동작**:
1. `pyodide_js.loadPackage(["pyarrow", "lxml", "polars", "numpy", "pydantic"])` — C 확장 빌트인 로드.
2. `pyodide.http.pyfetch(HF_URL)` — docs · finance · report parquet 다운로드.
3. pyodide FS `/data/dart/{cat}/{code}.parquet` 에 저장.

일반 환경에서는 no-op.

---

## 8. 빌드·배포

```bash
# wheel 빌드 (pyodide deps 제거 버전)
python pyodide/build.py

# wheel 빌드 + HF 업로드
python pyodide/build.py --upload

# Node.js 테스트
cd pyodide && node test_node.mjs
```

`build.py` 는 원본 wheel 에서 pyodide 미지원 deps 를 제거하고 pyodide 빌트인 deps 의 버전 제약을 완화한 전용 wheel 을 생성한다.

PyPI wheel 은 이중 마커로 pyodide 호환:

```toml
"lxml>=6.0.2,<7; sys_platform != 'emscripten'",
"lxml; sys_platform == 'emscripten'",
```

---

## 9. 검증 결과 (2026-04-13)

Node.js pyodide 0.27.2, 삼성전자 005930:

| 테스트 | 결과 |
|---|---|
| import + Company | ✓ |
| show IS | ✓ 33x42 분기 |
| show BS | ✓ 59x42 |
| show CF | ✓ 63x42 |
| show CIS | ✓ 16x42 |
| analysis 수익성 | ✓ 6 키 |
| analysis 성장성 | ✓ 5 키 |
| analysis 안정성 | ✓ 6 키 |
| select | ✓ 2x42 |
| story 수익성 | ✓ 2,771 자 |
| `c.index` | ✓ 63 topics |
| **총** | **13/13** |

---

## 관련 코드

| 경로 | 역할 |
|---|---|
| `pyodide/` | 빌드 스크립트 + 테스트 + 문서 |
| `pyodide/loader.js` | JS 초기화 헬퍼 (playground · xlwings 공용) |
| `pyodide/build.py` | wheel 빌드 + HF 업로드 |
| `pyodide/test_node.mjs` | Node.js 종합 테스트 (13 개) |
| `src/dartlab/core/dataLoader.py` | `readParquetSafe` · `_loadDataPyodide` |
| `experiments/120_pyodidePoc/` | 초기 POC (아카이브) |

---

## 요약 — 명제 7 줄

1. pyodide 에서는 `await dartlab.prefetch(code)` 후 `Company(code)` 로 시작한다.
2. 설치는 `micropip.install("dartlab")`, 이중 환경 마커로 pyodide 빌트인·PyPI 분기.
3. polars parquet I/O 는 WASM 에서 비활성 → `readParquetSafe()` 로 pyarrow 경유 우회.
4. pyodide 분기는 `sys.platform == "emscripten"` 체크, 10 여 파일에 `_IS_PYODIDE` 가드.
5. CORS 로 외부 API (gather · collect · OAuth profile · KRX) 는 불가, API 키 방식 ask 만 가능.
6. scan 은 `finance-lite.parquet` (18MB 30 계정 5 년) 로 지원, report 기반 축은 미지원.
7. 빌드는 `pyodide/build.py` (pyodide deps 제거 + HF 업로드), Node.js 테스트 13/13 통과가 게이트.
