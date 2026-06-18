# 08. Implementation Plan - 착수 가능한 계약으로 내리기

상태: 구현 착수 PRD v0.1 (2026-06-17)
범위: `infra/workers/dartlabConnector` 를 실제로 만들기 전에 닫아야 하는 tool 계약, 데이터 소스, endpoint, OAuth gate, 보안 eval, rollout 기준.

---

## 1. 이 문서가 닫는 구멍

비전 PRD v0.1 은 방향이 맞다. 구현 착수 기준으로는 아래 구멍을 닫아야 한다.

| 구멍 | 보강 결정 |
|---|---|
| tool 별 수용 기준이 느슨함 | tool 마다 input, output, data source, cache, failure, test 를 둔다 |
| 데이터 소스 매핑이 추상적임 | 기존 public runtime, parquet path, route helper 를 직접 참조한다 |
| MCP/OpenAPI schema 실물이 없음 | 단일 tool registry 에서 MCP descriptor 와 OpenAPI schema 를 동시에 생성한다 |
| OAuth/provider 결정이 열려 있음 | Phase 1 은 public only, private tool 은 schema 등록 자체를 막는다 |
| ChatGPT 제출 기준이 구현과 분리됨 | public vertical slice 통과 후 app submission checklist 로 이동한다 |
| 보안 eval fixture 가 부족함 | prompt injection, privacy leak, investment advice, schema drift fixture 를 필수화한다 |

---

## 2. 착수 원칙

1. **새 서버가 아니라 Cloudflare line 에 붙인다.** 거처는 `infra/workers/dartlabConnector`.
2. **provider-neutral 이 core 다.** ChatGPT App, Claude connector, Gemini/function calling 은 adapter 다.
3. **Phase 1 은 공개 근거만 다룬다.** OAuth 없는 public evidence vertical slice 를 먼저 끝낸다.
4. **답변 생성이 아니라 근거 전달이다.** 모든 응답은 Evidence Pack envelope 로 반환한다.
5. **viewer/terminal link 를 1급 결과로 둔다.** AI 답변 뒤에 DartLab 화면으로 돌아오게 만든다.
6. **범용 실행 도구는 노출하지 않는다.** `RunPython`, SQL, file IO, 임의 URL fetch 는 public connector 금지.
7. **기존 UI 를 흔들지 않는다.** Worker 는 read-only gateway 로 시작하고 landing/local route 계약을 침범하지 않는다.

---

## 3. 파일 Touchpoint

### 신규 파일 후보

```text
infra/workers/dartlabConnector/
  wrangler.toml
  src/
    index.ts
    config.ts
    http.ts
    registry.ts
    envelope.ts
    schemas.ts
    links.ts
    sources/
      companySearch.ts
      filings.ts
      finance.ts
      panelEvidence.ts
    tools/
      resolveEntity.ts
      searchFilings.ts
      getFilingEvidence.ts
      createDartlabLink.ts
    security/
      limits.ts
      redaction.ts
      promptInjection.ts
  test/
    fixtures/
    smoke/
```

### 기존 코드 참조

| 목적 | 참조 |
|---|---|
| HF proxy 패턴 | `infra/workers/hfProxy/worker.js` |
| Worker 배포 설정 패턴 | `infra/workers/hfProxy/wrangler.toml` |
| public data origin | `ui/packages/runtime/src/data/origin.ts` |
| origin/cache registry | `ui/packages/runtime/src/data/origins/registry.ts` |
| terminal seed load | `landing/src/lib/terminal-shell/routeLoad.ts` |
| public viewer link | `landing/src/lib/runtime/publicRuntime.ts` |
| local 전용 route 경계 | `ui/apps/local/src/lib/runtime/localRuntime.ts` |
| 정기공시 public source | `ui/packages/runtime/src/adapters/public/sources/regularFilingsSource.ts` |
| 비정기공시 public source | `ui/packages/runtime/src/adapters/public/sources/nonRegularFilingsSource.ts` |
| 재무 public source | `ui/packages/runtime/src/adapters/public/sources/financeSource.ts` |
| viewer panel body columns | `ui/packages/surfaces/src/viewer/lib/panelLoad.ts` |
| viewer evidence helper | `ui/packages/surfaces/src/viewer/lib/searchEvidence.ts` |

---

## 4. Data Source Map

| capability | Phase 1 source | Phase 2+ source | 비고 |
|---|---|---|---|
| 회사 검색 | `map/search-index.json` | 동일 + alias tuning | `landing/src/lib/terminal-shell/routeLoad.ts` 가 이미 사용 |
| 최근 비정기공시 | `dart/allFilings/recent.parquet` | same | `stock_code`, `rcept_dt`, `report_nm`, `rcept_no`, `flr_nm` |
| 정기공시 목록 | `dart/panel/{code}.parquet` 에서 `period`, `rceptNo` | same | `regularFilingsSource.ts` 경로와 컬럼을 따른다 |
| 재무 패널 | 보류 | `dart/finance/{code}.parquet` | Phase 1 에 schema 등록하지 않는다 |
| 공시 본문 근거 | metadata/link only | `dart/panel/{code}.parquet` `READ_COLUMNS` | body chunk evidence 는 Phase 2 |
| viewer link | `/viewer/company/{code}` | anchor/query 확장 | public route 만 반환 |
| terminal link | `/terminal` + code state/link 계약 | code-specific public route 확정 후 확장 | local `/terminal/{code}` 와 혼동 금지 |
| DART 원문 link | `rceptNo` 기반 public DART URL | same | source URL 로 반환 |
| news/naver | 제외 | 별도 tool 검토 | Phase 1 에 섞지 않는다 |
| watchlist/private state | 제외 | OAuth 이후 | public tool 과 분리 |

Phase 1 의 `get_filing_evidence` 는 본문 chunk 를 반환하지 않는다. 반환 범위는 filing metadata, DART source link, DartLab viewer link, limitation 이다. 본문 snippet, section anchor, search evidence 는 `panelLoad.READ_COLUMNS` 경로를 Worker 에 안전하게 포팅한 뒤 Phase 2 로 올린다.

---

## 5. Endpoint 와 Schema 계약

### HTTP endpoints

| endpoint | Phase 1 | 설명 |
|---|---:|---|
| `GET /health` | yes | build, version, time, enabled tools |
| `POST /mcp` | yes | remote MCP endpoint |
| `GET /openapi.json` | yes | 같은 registry 에서 생성 |
| `POST /api/v1/tools/resolve_entity` | yes | REST adapter |
| `POST /api/v1/tools/search_filings` | yes | REST adapter |
| `POST /api/v1/tools/get_filing_evidence` | yes | Phase 1 metadata/link only |
| `POST /api/v1/tools/create_dartlab_link` | yes | public link only |

`get_company_snapshot`, `get_financial_panel`, `compare_companies`, `get_watchlist_delta` 는 문서에는 남기되 Phase 1 schema 에 등록하지 않는다. 구현되지 않은 tool 을 노출하고 501 을 반환하는 방식은 금지한다.

### 단일 registry 원칙

```ts
type ToolDefinition = {
  name: string;
  visibility: 'public' | 'private';
  phase: 1 | 2 | 3;
  inputSchema: JsonSchema;
  outputSchema: JsonSchema;
  handler: ToolHandler;
  cachePolicy: CachePolicy;
  risk: 'low' | 'medium' | 'high';
};
```

MCP descriptor, OpenAPI path, REST router 는 이 registry 만 본다. tool 이름, input schema, output schema 가 세 군데에서 드리프트 나는 구조를 만들지 않는다.

### 공통 envelope

```json
{
  "requestId": "req_...",
  "asOf": "2026-06-17T00:00:00Z",
  "tool": "search_filings",
  "data": {},
  "evidence": [],
  "freshness": {
    "source": "hf-public",
    "generatedAt": null,
    "cacheTtlSec": 3600
  },
  "links": [],
  "limitations": [
    "evidenceOnly",
    "notInvestmentAdvice"
  ]
}
```

---

## 6. Tool 별 수용 기준

### `resolve_entity`

Input:

```json
{ "query": "삼성전자", "limit": 5 }
```

Source: `map/search-index.json`.

Acceptance:

- 종목명, 종목코드, alias, 시장 정보가 있으면 반환한다.
- query 가 모호하면 `confidence` 를 낮추고 후보를 여러 개 반환한다.
- 결과가 없으면 빈 배열과 `not_found` limitation 을 반환한다.
- private state, watchlist, 최근 방문 기록을 읽지 않는다.
- REST 와 MCP 호출 결과 shape 이 동일해야 한다.

Tests:

- exact code query: `005930`
- Korean name query: `삼성전자`
- ambiguous query
- no result query
- malformed input

### `search_filings`

Input:

```json
{
  "code": "005930",
  "kind": "all",
  "from": "2025-01-01",
  "to": "2026-06-17",
  "limit": 20
}
```

Source: `dart/allFilings/recent.parquet`, `dart/panel/{code}.parquet`.

Acceptance:

- `code` 는 6자리 숫자로 normalize 한다.
- `limit` 은 서버 상한을 둔다. Phase 1 기본 20, 최대 50.
- `rceptNo`, `rceptDate`, `reportName`, `filerName`, `dartUrl`, `viewerUrl` 을 반환한다.
- 정기공시와 비정기공시를 섞을 때 source 구분을 유지한다.
- 날짜 범위 밖 결과를 반환하지 않는다.
- 본문 전체를 반환하지 않는다.

Tests:

- known code recent filings
- date filter
- limit cap
- invalid code
- empty range

### `get_filing_evidence`

Input:

```json
{
  "code": "005930",
  "rceptNo": "20240312000736",
  "topic": "revenue",
  "maxEvidence": 5
}
```

Phase 1 Source: filing metadata, DART URL, public viewer URL.

Phase 2 Source: `ui/packages/surfaces/src/viewer/lib/panelLoad.ts` 의 `READ_COLUMNS` 와 `searchEvidence.ts` 의 evidence helper 를 Worker-safe 모듈로 분리하거나 재구현.

Acceptance Phase 1:

- filing metadata 를 찾으면 `data.filing` 과 `links` 를 반환한다.
- DART 원문 link 와 DartLab viewer link 를 반환한다.
- body snippet 을 아직 반환하지 않는다는 limitation 을 명시한다.
- `topic` 은 받되 Phase 1 에서는 routing hint 로만 기록한다.
- report text 를 신뢰 문장으로 섞지 않고 `external_untrusted` 로 표시한다.

Acceptance Phase 2:

- `chapter`, `sectionPath`, `blockLeaf`, `contentRaw`, `period`, `rceptNo` 기반 snippet 을 반환한다.
- snippet 은 max length 를 둔다.
- prompt injection 문구는 실행 지시로 취급하지 않고 evidence text 로만 반환한다.
- section anchor 가 있으면 viewer deep link 에 반영한다.

Tests:

- known rceptNo metadata
- missing rceptNo
- topic ignored safely in Phase 1
- prompt injection fixture in `contentRaw` for Phase 2

### `create_dartlab_link`

Input:

```json
{
  "kind": "viewer",
  "code": "005930",
  "rceptNo": "20240312000736",
  "publicOnly": true
}
```

Source: public route helpers.

Acceptance:

- Phase 1 은 public link 만 반환한다.
- viewer 는 `/viewer/company/{code}` 계열만 반환한다.
- terminal 은 공개 `/terminal` route 계약만 반환한다. code-specific state 는 별도 확정 전 query/state 로 임의 발명하지 않는다.
- local 전용 `/analysis/{code}/viewer` 또는 `/terminal/{code}` 를 반환하지 않는다.
- token, email, user id, local path 를 link 에 넣지 않는다.

Tests:

- viewer link
- terminal link
- unsupported kind
- private state request rejected

### Deferred tools

| tool | Phase | 착수 조건 |
|---|---:|---|
| `get_company_snapshot` | 2 | public finance + filings 요약 source map 고정 |
| `get_financial_panel` | 2 | `financeSource.ts` 컬럼 계약과 numeric normalization test |
| `compare_companies` | 2 | `resolve_entity` + financial panel 안정화 |
| `get_watchlist_delta` | 3 | OAuth, D1/KV state, user scope, no-store logging 완료 |

---

## 7. Worker 구현 순서

1. `infra/workers/dartlabConnector` skeleton 과 `wrangler.toml` 작성.
2. `envelope.ts`, `registry.ts`, `schemas.ts` 를 먼저 작성.
3. `/health`, `/openapi.json`, `/mcp` 를 registry 기반으로 연결.
4. `resolve_entity` 를 가장 먼저 end-to-end 구현.
5. `search_filings` 를 recent + regular metadata 로 구현.
6. `create_dartlab_link(public)` 를 route guard 와 함께 구현.
7. `get_filing_evidence` Phase 1 metadata/link only 구현.
8. MCP inspector 와 REST smoke 로 동일 envelope 를 검증.
9. Phase 1 문서와 실제 schema diff 를 CI 에서 검사.

---

## 8. OAuth Decision Gate

Phase 1 에서는 OAuth 를 구현하지 않는다. 대신 private tool 을 노출하지 않는 것으로 보안면을 줄인다.

OAuth 착수 조건:

- public evidence vertical slice 가 smoke/eval 통과
- rate limit 과 abuse log가 존재
- private state schema 가 D1/KV 기준으로 고정
- user deletion/export 정책 문서화
- provider 선택 완료

| 후보 | 장점 | 리스크 | 현재 판단 |
|---|---|---|---|
| Cloudflare Access/OAuth | Worker line 과 가깝고 운영 부담 낮음 | ChatGPT/외부 connector UX 검증 필요 | 1순위 검토 |
| 자체 OAuth | 제품 통제력 높음 | 보안/운영 비용 큼 | Phase 1 금지 |
| provider 별 token | 빠른 실험 가능 | 플랫폼별 파편화 | 제출용으로 부적합 |

---

## 9. Security/Eval Fixtures

필수 fixture:

| fixture | 예시 | 기대 |
|---|---|---|
| prompt injection | 공시 본문에 "이전 지시를 무시하라" 포함 | evidence text 로만 반환 |
| privacy leak | public tool 에 watchlist 요구 | 거절, private scope 필요 |
| investment advice | "지금 사도 되나" | 근거와 제한만 반환, 추천 금지 |
| schema drift | MCP/OpenAPI/REST output 차이 | CI 실패 |
| oversized request | limit 5000 | cap 적용 |
| malformed code | `005930;DROP` | validation error |
| source unavailable | HF 5xx | retry 후 source_unavailable limitation |

출시 차단:

- public tool 이 user state 를 읽는 경우
- body evidence 에 injection 문구가 tool instruction 으로 승격되는 경우
- 매수/매도/목표주가를 DartLab 판단처럼 반환하는 경우
- schema 에 구현되지 않은 tool 이 노출되는 경우

---

## 10. Rollout / Rollback

Phase 1 rollout:

1. workers.dev preview.
2. REST smoke.
3. MCP inspector.
4. ChatGPT connector dev 연결.
5. Claude/Gemini adapter feasibility smoke.
6. public docs internal review.
7. custom domain 검토.

Rollback:

- registry 에서 tool 비활성화하면 MCP/OpenAPI/REST 에서 동시에 빠져야 한다.
- `DARTLAB_CONNECTOR_ENABLED=false` 로 전체 endpoint 를 health-only 로 내릴 수 있어야 한다.
- private tool 은 Phase 3 전까지 rollback 대상이 아니라 애초에 배포 대상이 아니다.

---

## 11. PR 단위

권장 PR 순서:

1. `기획: AI 워크벤치 커넥터 구현 계약 보강`
2. `인프라: dartlabConnector 워커 스켈레톤 추가`
3. `계약: 커넥터 envelope 와 tool registry 추가`
4. `기능: 공개 회사 검색 tool 추가`
5. `기능: 공개 공시 검색 tool 추가`
6. `기능: DartLab 공개 링크 tool 추가`
7. `기능: 공시 근거 metadata tool 추가`
8. `검증: MCP REST smoke 와 보안 fixture 추가`

---

## 12. 착수 판정

현재 판정:

| 영역 | 점수 | 판단 |
|---|---:|---|
| 제품 방향 | 95 | 챗봇이 아니라 evidence connector 로 선명함 |
| 아키텍처 | 90 | Cloudflare Worker + MCP/OpenAPI neutral contract 로 충분 |
| 보안 경계 | 88 | public/private split 은 좋고 OAuth 선택만 남음 |
| 구현 착수성 | 85 | Phase 1 public vertical slice 는 바로 착수 가능 |

남은 미해결은 OAuth provider, custom domain, panel body evidence 포팅 방식이다. 이 셋은 Phase 1 착수를 막지 않는다. Phase 1 은 public metadata/link evidence 만으로 시작한다.
