# 03. Source Ledger and Next Research

Date: 2026-06-17 KST
Mode: 조사 전용. 구현 없음.
Source policy: 공식 문서, 프로젝트 문서, primary repository 위주로만 기술 판단에 사용한다.

## 1. 외부 공식 자료 확인 기록

| 주제 | 확인한 사실 | Source |
| --- | --- | --- |
| Polars GPU | Python Lazy API용 NVIDIA GPU/RAPIDS cuDF engine. Open Beta이며 빠르게 개발 중. 기본 엔진으로 단정하면 안 됨 | https://docs.pola.rs/user-guide/gpu-support/ |
| DuckDB Parquet | DuckDB는 Parquet read/write와 filter/projection pushdown을 지원 | https://duckdb.org/docs/current/data/parquet/overview |
| DuckDB HTTP Parquet | `httpfs` 설치/로드 후 HTTP(S) Parquet를 `read_parquet(...)`로 읽을 수 있음 | https://duckdb.org/docs/current/guides/network_cloud_storage/http_import |
| DuckDB S3/httpfs | S3 API object storage read/write/glob 지원. public reads는 HTTP Range requests가 핵심 | https://duckdb.org/docs/lts/core_extensions/httpfs/s3api |
| DuckDB-WASM | DuckDB가 WebAssembly로 브라우저에서 실행 가능. 최신 stable wasm client version은 문서 기준 1.5.3 | https://duckdb.org/docs/current/clients/wasm/overview |
| hyparquet | JS/browser에서 Parquet를 HTTP로 효율적으로 읽기 위한 parser | https://github.com/hyparam/hyparquet |
| MCP | LLM application과 외부 data/tools 통합을 위한 open protocol. 2025-06-18 spec 확인 | https://modelcontextprotocol.io/specification/2025-06-18 |
| AG-UI | user-facing application과 agent backend 사이의 lightweight event protocol | https://docs.ag-ui.com/introduction |
| AG-UI events | lifecycle, text, tool call, state, activity, special, reasoning event category 확인 | https://docs.ag-ui.com/concepts/events |
| OpenTelemetry GenAI | GenAI attributes는 input/output messages, token usage, provider/model 등 민감정보 주의가 필요한 trace 항목을 정의 | https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/ |
| OpenAI Structured Outputs | `response_format: {"type":"json_schema", ... "strict": true}` 및 strict function schema 사용 가능. unsupported schema keyword는 에러 | https://developers.openai.com/api/docs/guides/structured-outputs |
| GitHub Artifact Attestations | Actions에서 build provenance attestation 생성 가능. 권한과 attest action 필요 | https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations |
| Playwright visual comparison | `expect(page).toHaveScreenshot()`로 screenshot baseline 생성/비교 가능 | https://playwright.dev/docs/test-snapshots |
| Astral uv | Rust로 작성된 빠른 Python package/project manager | https://docs.astral.sh/uv/ |
| Astral ty | Rust로 작성된 Python type checker/language server. beta 성격 | https://docs.astral.sh/ty/ |
| Vite Rolldown | Rust-powered bundler integration. Vite는 Rolldown 통합을 계획하며 `rolldown-vite`는 pin 권장 | https://v7.vite.dev/guide/rolldown |
| TanStack Virtual | Svelte 포함 여러 UI runtime에서 long list virtualization을 headless로 제공 | https://tanstack.com/virtual/latest/docs/introduction |
| TanStack Svelte Virtual | `@tanstack/svelte-virtual` adapter가 core virtual logic wrapper 제공 | https://tanstack.com/virtual/v3/docs/framework/svelte/svelte-virtual |
| OpenLineage | job/run/dataset/facet 중심의 lineage metadata open standard | https://openlineage.io/docs/ |

## 2. DartLab 내부 근거

| 관찰 | 파일 |
| --- | --- |
| DuckDB fallback은 Polars collect 후 DuckDB 등록이므로 source-native OOC가 아님 | `src/dartlab/scan/io/cross.py` |
| AI tool registry는 EngineCall/RunPython/ReadSkill/ReadCapability 경계를 이미 갖고 있음 | `src/dartlab/ai/tools/registry.py` |
| MCP advertised tools는 registry canonical list를 따른다 | `src/dartlab/mcp/protocol.py` |
| UI data call은 `createDataCore`와 origin registry가 SSOT | `ui/packages/runtime/src/data/fetch/request.ts`, `ui/packages/runtime/src/data/origins/registry.ts` |
| local AI stream은 SSE를 AiStreamEvent로 변환하고 AG-UI식 이벤트를 전달 | `ui/packages/runtime/src/adapters/local/api/stream.ts` |
| search API는 facet planner, answerability, entity graph, evidence card, query log candidate를 연결 | `src/dartlab/providers/dart/search/api.py` |
| evidence card는 sourceRef/source/report/section/date/snippet을 JSON fieldCards로 구성 | `src/dartlab/providers/dart/search/evidencePack.py` |
| query-log gold는 candidate/reviewer/release gate를 분리 | `src/dartlab/providers/dart/search/goldLog.py` |
| CI gate SSOT는 `tests/run.py`이며 workflow는 matrix dispatch | `tests/run.py`, `.github/workflows/ci-fast.yml` |

## 3. 다음 실측 질문

### Q1. DuckDB source-native scan은 실제 RSS를 낮추는가?

Experiment:

- `tests/_attempts/crossScanOoc/`
- 동일 parquet set을 Polars streaming, current DuckDbCrossScan, source-native DuckDB read_parquet 세 방식으로 실행.
- query: projection, filter, group by, join.

Pass:

- source-native DuckDB가 current DuckDbCrossScan보다 peak RSS를 의미 있게 낮춤.
- result equality 통과.
- source manifest/sourceRef 보존.

Fail:

- SQL planner가 복잡해져 public API나 security risk가 커짐.
- Polars streaming보다 이점 없음.

### Q2. Lineage event subset은 search와 AI를 같이 묶을 수 있는가?

Experiment:

- `search(...)` result row에 `lineageRunId` 또는 `sourceManifestHash`를 내부 metadata로 붙인 fixture.
- `EngineCall` 결과 tableRef가 lineage id를 carry하는지 검사.

Pass:

- search result, evidence card, AI final answer가 같은 sourceRef lineage를 추적 가능.
- tests/audit에서 누락 감지 가능.

Fail:

- lineage가 문자열 로그에만 남음.
- UI/AI에서 소비 불가.

### Q3. AG-UI event mapping은 현 AiStreamEvent와 충돌하지 않는가?

Experiment:

- one run JSONL fixture.
- event types를 AG-UI category에 매핑.
- unknown event와 missing required field를 gate에서 차단.

Pass:

- 현 local UI stream과 external connector plane 모두 같은 allowlist를 사용.
- raw trace와 user evidence view가 분리.

Fail:

- event naming 변경이 public/local UI를 동시에 깨뜨림.

### Q4. CI Evidence Bus가 gate drift를 줄이는가?

Experiment:

- smoke/search/ui/security artifact summary 4개를 `ci-evidence-manifest.json`으로 합침.
- manifest schema를 test로 고정.

Pass:

- releaseReady 판정이 raw log 없이 JSON evidence만으로 가능.
- fixture/realdata/provenance 구분이 보존.

Fail:

- artifact path만 모으고 의미 있는 summary가 없음.

### Q5. Browser Parquet Workbench는 public UI에서 충분히 빠른가?

Experiment:

- `hyparquet`와 DuckDB-WASM을 같은 HF range parquet로 비교.
- sourceRef deep link → row preview까지 latency 측정.

Pass:

- 10MB dataset에서 interactive.
- 100MB dataset에서 projection/filter가 timeout 없이 동작.
- `data/fetch`와 `origins` 우회 없음.

Fail:

- bundle size, startup time, memory가 public UI에 과함.

### Q6. ty shadow gate가 의미 있는 신호를 주는가?

Experiment:

- `tests/run.py`에 non-blocking dry-run candidate로 ty command를 기록하기 전, local report를 `tests/_attempts/typecheckTy/`에서 산출.

Pass:

- pyright와 다른 actionable issue를 낮은 noise로 발견.
- elapsed가 fast tier에 맞음.

Fail:

- beta false positive가 많아 운영 비용이 큼.

### Q7. Playwright visual/aria snapshot이 UI 회귀를 잘 잡는가?

Experiment:

- public landing, local terminal shell, evidence table 후보 화면 2 viewport.
- screenshot + aria snapshot.

Pass:

- layout overlap, missing text, empty panel을 잡음.
- baseline update 절차가 명확.

Fail:

- flaky diff가 많아 개발 흐름을 방해.

## 4. 다음 문서화 작업

1. `polars-gpu-backend`에 DuckDB source-native OOC와 GPU opt-in의 경계를 더 명시한다.
2. `ai-workbench-connector`에 AG-UI event mapping과 MCP tool contract audit를 연결한다.
3. `search-productization`에 lineage event subset과 CI Evidence Bus 소비 지점을 연결한다.
4. UI workbench PRD가 생기면 Browser Parquet Workbench를 `data/fetch` 하위 실험으로 편입한다.

## 5. 조사 보류 항목

- WebLLM/local LLM: 제품 가치보다 자원/품질/보안 리스크가 크므로 watch.
- full OpenLineage backend: 내부 JSON subset 검증 전 보류.
- Vite Rolldown: Vite version/lockfile 상태를 먼저 확인해야 하므로 benchmark only.
- Rust/PyO3: 병목 실측 전 보류.
