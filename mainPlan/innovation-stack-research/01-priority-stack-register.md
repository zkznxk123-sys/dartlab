# 01. Priority Stack Register

Date: 2026-06-17 KST
Mode: 조사 전용. 구현 없음.

## Priority 0 — 바로 다음 실측 후보

| 후보 | DartLab에 주는 혁신 | 현재 anchor | 흡수 방식 | 첫 검증 |
| --- | --- | --- | --- | --- |
| DuckDB source-native OOC Parquet SQL | cross-company scan의 메모리 병목 제거 | `scan/io/cross.py`, `pipeline`, source manifest | `LazyFrame` collect 후 등록이 아니라 Parquet path/source manifest를 DuckDB가 직접 scan | `tests/_attempts/crossScanOoc/`에서 동일 query를 Polars streaming vs DuckDB read_parquet로 RSS/time 비교 |
| Lineage-as-Guard | raw source → parquet → search/evidence/AI answer의 trace를 gate로 고정 | `operation.dataLineage`, `pipeline`, `providers/dart/search/sourceManifest.py` | OpenLineage식 job/run/dataset/facet JSON subset을 내부 ledger로 채택. Marquez 서버는 보류 | search index build와 `dartlab.search(...)` result에 lineage id를 붙이고 audit |
| AG-UI/MCP contract hardening | local UI, external AI connector, MCP tool surface의 이벤트/도구 계약 통일 | `mcp/protocol.py`, `ui/.../api/stream.ts`, `ai/tools/registry.py` | 기존 이벤트 allowlist를 AG-UI event taxonomy와 매핑. MCP는 current canonical tools만 advertise | stream event fixture에서 unknown event/type mismatch 차단 |
| CI Evidence Bus | CI 통과를 artifact proof bundle로 전환 | `tests/run.py`, `.github/workflows/ci-fast.yml`, search proof docs | gate별 JSON evidence를 `ci-evidence-manifest.json`에 등록 | smoke/search/ui/security artifact를 모아 readiness summary 생성 |
| Browser Parquet Workbench | public/local UI에서 sourceRef와 parquet row 직접 검사 | UI `data/fetch`, `hfRange`, `duckdbOpfs.ts`, `hyparquet` | data SSOT 밑에 browser inspect arm 추가. raw fetch 금지 | 10MB/100MB parquet에서 column projection, filter, first rows latency 측정 |

## Priority 1 — shadow 또는 opt-in 흡수

| 후보 | DartLab 적용 판단 | 흡수 방식 | 첫 검증 |
| --- | --- | --- | --- |
| Polars GPU engine | compute-bound Lazy query에는 가능성. OOC/streaming 문제의 기본 해법은 아님 | `mainPlan/polars-gpu-backend`의 opt-in backend로 유지 | RAPIDS/cuDF 설치 환경에서 `collect(engine="gpu")` smoke. 기본 의존성 추가 금지 |
| Structured Outputs / strict JSON schema | AI tool plan, evidence verdict, answerability output의 drift 감소 | tool schema와 judge/eval output에만 적용. provider lock-in 피하려면 schema subset 분리 | `GroundingCheck` 또는 `EvidenceGate` output schema를 strict subset으로 고정 |
| GenAI/agent trace attributes | AI 실행 비용, latency, tool call, retrieval context를 관측 가능하게 함 | OpenTelemetry GenAI 속성 이름을 참고하되 민감정보 저장 금지 | one run trace JSON fixture와 PII redaction audit |
| uv-first CI + ty shadow + Ruff ratchet | 설치/검사 속도와 타입 회귀 가시성 향상 | `tests/run.py` non-blocking gate로 먼저 | `ty check src/dartlab` shadow report artifact. pyright 대체 금지 |
| Playwright visual/aria regression | public/local UI 공유 wiring 회귀 탐지 | UI smoke gate에 screenshot/aria snapshot을 추가 | local build 2 viewport screenshot baseline 생성 |
| Vite Rolldown | UI build 속도 개선 가능. 아직 실험/마이그레이션 성격 | 별도 branch/attempt에서 vite alias 실측 | `landing`, `ui/apps/local` build time/memory 비교 |
| TanStack Virtual Svelte | evidence table, search result, logs 대량 렌더링 개선 | UI component 내부 implementation detail로 사용 | 10k evidence rows scroll FPS/paint 비교 |

## Priority 2 — 장기 관찰

| 후보 | 장기 판단 | 보류 이유 |
| --- | --- | --- |
| WebLLM/local browser LLM | offline explanation/demo에는 흥미롭지만 DartLab의 근거 분석 핵심은 아님 | 모델 품질/브라우저 자원/보안 대비 ROI 낮음 |
| Pyodide-heavy workbench | DartLab이 pyodide 호환을 고려하지만 전체 분석을 브라우저로 옮기기에는 무거움 | public UI는 inspect 중심, heavy analysis는 local/server가 맞음 |
| OpenLineage full backend/Marquez | lineage model 참고 가치는 큼 | 현재는 server 운영 비용이 큼. 내부 JSON subset으로 충분 |
| Iceberg/lakeFS | 데이터 버전 관리에는 강력 | 현재 dataset 규모와 HF manifest 운영에는 과함. source manifest로 먼저 해결 |

## Candidate Details

### A. DuckDB source-native OOC scan

문제:

- 현재 `DuckDbCrossScan`은 Polars LazyFrame을 먼저 collect한다.
- 이 때문에 DuckDB의 Parquet pushdown, HTTPFS range/S3 scan, spill 이점이 제한된다.

흡수 설계:

1. `CrossScanEngine` surface는 유지한다.
2. LazyFrame만 받는 현재 surface 옆에 source manifest/path plan을 받는 내부 arm을 둔다.
3. DuckDB arm은 `read_parquet(paths)`를 직접 수행하고 filter/projection SQL을 생성한다.
4. 결과 schema는 기존 Polars DataFrame으로 되돌린다.
5. 기능 졸업 전에는 public API에 노출하지 않는다.

첫 실측:

- 동일 source parquet 3개 이상.
- row count 100k/1M/10M.
- query: projection only, filter+projection, group by, join.
- metric: peak RSS, elapsed, result equality, first-row latency.

기각 조건:

- path/source manifest를 잃어버려 sourceRef/evidence lineage가 약해진다.
- query builder가 public SQL injection surface가 된다.
- Polars streaming보다 memory/time 모두 악화한다.

### B. Lineage-as-Guard

문제:

- Search/source manifest는 강하지만, 모든 pipeline/AI/UI 산출물이 같은 lineage event 모델을 공유하지는 않는다.

흡수 설계:

- 내부 lineage event JSON:
  - `job`: 예 `searchIndexMain`, `Company.panel`, `AI.EngineCall`.
  - `run`: run id, startedAt, finishedAt, status.
  - `inputs`: dataset id, sourceRef, manifest hash.
  - `outputs`: parquet path, tableRef, evidenceRef, answerRef.
  - `facets`: schema hash, row count, dataAsOf, provider.
- OpenLineage의 job/run/dataset/facet 개념을 참고하되 서버 운영은 하지 않는다.
- `tests/audit`에서 "sourceRef 없는 evidence card", "lineage 없는 AI final ref"를 차단한다.

첫 실측:

- `dartlab.search("유상증자", limit=5)` 결과 5개 row에 lineage id와 source manifest hash를 붙인 fixture.
- AI `EngineCall` 결과 tableRef가 source lineage를 보존하는지 검사.

### C. AG-UI/MCP contract hardening

문제:

- UI 이벤트는 AG-UI와 형태가 비슷하지만, 공식 protocol과의 차이를 문서/테스트로 고정하지 않으면 drift가 발생한다.
- MCP external plane은 `ai-workbench-connector`와 연결되지만 local UI stream과 완전히 같은 contract로 설명되지는 않는다.

흡수 설계:

- `AiStreamEvent` allowlist를 AG-UI categories와 매핑:
  - lifecycle: `RUN_STARTED`, `RUN_FINISHED`, `RUN_ERROR`
  - text: `TEXT_MESSAGE_CONTENT`
  - tool: `TOOL_CALL_START`, `TOOL_CALL_RESULT`
  - state/custom: 필요 시 내부 event로만 제한
- MCP advertised tools는 `mcpAdvertisedToolNames()`와 registry `CANONICAL_V2` 불일치를 audit한다.
- public/local UI가 raw trace를 바로 노출하지 않고 evidence-safe view를 쓴다.

첫 실측:

- one AI stream fixture를 JSONL로 고정.
- parser가 unknown event를 거부하거나 `RUN_ERROR`로 강등하는지 확인.

### D. CI Evidence Bus

문제:

- 게이트는 많지만 release/readiness 판단은 여러 artifact와 로그를 사람이 연결해야 한다.

흡수 설계:

- 각 gate가 optional evidence JSON을 남긴다.
- `tests/run.py` 또는 `tests/audit`에 manifest aggregator를 둔다.
- manifest fields:
  - gate name, tier, command hash.
  - artifact path, sha256, summary.
  - blocker count, warning count.
  - data mode, fixture/realdata flag.
  - source manifest hash if data related.
- `publish.yml`의 provenance/SBOM과 연결한다.

첫 실측:

- `smoke`, `search productization status`, `ui data wiring`, `security` artifact 4개를 묶은 manifest fixture.

### E. Browser Parquet Workbench

문제:

- public/local UI는 데이터 호출 SSOT가 있지만, 사용자가 sourceRef의 parquet row를 브라우저에서 즉시 검증하는 흐름은 더 강화할 수 있다.

흡수 설계:

- 소형/중형 parquet inspect:
  - `hyparquet`: 빠른 browser parse와 HTTP range 중심.
  - `DuckDB-WASM`: SQL inspection, local file/import, OPFS cache 가능성.
- UI `data/fetch`와 `origins` 아래로만 연결한다.
- raw fetch 또는 component-local cache Map 금지.

첫 실측:

- HF range parquet 10MB/100MB.
- columns 5개 projection.
- simple filter.
- sourceRef deep link에서 row preview까지 latency 측정.

## Decision Matrix

| 후보 | Impact | Fit | Risk | 상태 |
| --- | ---: | ---: | ---: | --- |
| DuckDB source-native OOC | 5 | 5 | 3 | P0 실측 |
| Lineage-as-Guard | 5 | 5 | 2 | P0 설계 |
| AG-UI/MCP hardening | 4 | 5 | 2 | P0 구현 후보 |
| CI Evidence Bus | 4 | 5 | 2 | P0 설계 |
| Browser Parquet Workbench | 4 | 4 | 3 | P0 실측 |
| Polars GPU | 3 | 4 | 4 | P1 opt-in |
| Structured Outputs/trace | 4 | 4 | 3 | P1 scoped |
| uv/ty/Ruff ratchet | 3 | 4 | 2 | P1 shadow |
| Playwright visual/aria | 3 | 4 | 2 | P1 scoped |
| Rolldown | 2 | 3 | 3 | P1 benchmark only |
| TanStack Virtual | 3 | 4 | 2 | P1 UI detail |
| WebLLM/Pyodide-heavy | 2 | 2 | 4 | P2 watch |
