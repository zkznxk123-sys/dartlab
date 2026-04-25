# 120 — Pyodide POC

**상태: Phase 1~3 전부 성공 (2026-04-13)**

## 결과

| 단계 | 결과 | 비고 |
|---|---|---|
| Pyodide 로드 | ✅ 0.27.2 | |
| polars/pyarrow 빌트인 | ✅ | polars 1.18.0 WASM |
| dartlab wheel 설치 | ✅ 15MB | zip 직접 해제 (micropip deps 우회) |
| HF parquet fetch | ✅ docs 16.6MB + finance 287KB + report 220KB | CORS OK |
| `import dartlab` | ✅ 0.9.8 | |
| `Company("005930")` | ✅ | corpName은 docs parquet에서 추출 |
| `c.show("IS")` | ✅ 21행 12컬럼 | |
| `c.analysis("수익성")` | ✅ dict | marginTrend=None (데이터 정합성, pyodide 무관) |
| `c.story("수익성")` | ✅ 729자 마크다운 | |
| httpx transport | ✅ JavascriptFetchTransport | 브라우저 자동 |
| Gemini API | ✅ HTTP 403 (키만 넣으면 동작) | CORS OK |
| OpenAI API | ✅ HTTP 401 (키만 넣으면 동작) | CORS OK |
| oauth-codex | ❌ chatgpt.com CORS 차단 | 브라우저 불가 |
| 총 시간 | **11~17초** | |

## 확정된 아키텍처

```
[JS] fetch(HF URL) → pyodide.FS.writeFile("/data/dart/{cat}/{code}.parquet")
[Python] Path("/data/...").read_bytes() → pyarrow.parquet.read_table → pl.from_arrow()
[AI] httpx JavascriptFetchTransport → Gemini/OpenAI API (CORS OK)
```

## AI provider (pyodide)

| Provider | 브라우저 | 사유 |
|---|---|---|
| gemini | ✅ | CORS OK |
| openai | ✅ | CORS OK |
| oauth-codex | ❌ | chatgpt.com/backend-api CORS 차단 |
| ollama | ❌ | localhost 서버 필요 |

## polars WASM 제약

- `read_parquet`, `write_parquet`, `scan_parquet` 전부 비활성 (GitHub #20876)
- pyarrow 경유 필수

## 수정된 dartlab 코드 (8파일)

| 파일 | 변경 |
|---|---|
| `core/dataLoader.py` | `_IS_PYODIDE` + `_loadDataPyodide` (FS→pyarrow→polars) |
| `__init__.py` | server/cli/gather import 차단 |
| `core/__init__.py` | gather.listing import 차단 |
| `providers/dart/_utils.py` | `_ensureAllData` 바이패스 + threading 순차 |
| `providers/dart/company.py` | `codeToName` 바이패스 |
| `gather/listing.py` | cache read/write 스킵 |
| `review/registry.py` | `Section` import 순환 참조 수정 |
| `pyproject.toml` | `[project.optional-dependencies].pyodide` 추가 |

## 배포 타겟

| 타겟 | AI provider | 경로 |
|---|---|---|
| landing playground | gemini | `landing/src/routes/playground/` |
| xlwings lite | gemini/openai | Excel Add-in |
| JupyterLite | gemini/openai | JupyterLite |

## 알려진 제한

- `marginTrend=None`: select IS에서 "매출액" 미매칭 — 연간 합성/계정명 정합성 (pyodide 무관)
- KRX KIND 목록: pyodide에서 httpx.post 불가 → getKindList 0건 반환
- threading 불가 → concurrent.futures 순차
- oauth-codex: CORS 차단 → gemini/openai 사용

## 다음 단계

- [ ] landing playground 통합
- [ ] xlwings lite 연동
- [ ] marginTrend 데이터 정합성 수정
- [ ] Gemini API 키 입력 UI + 실제 `dartlab.ask()` E2E
