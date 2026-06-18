# 03. Cloudflare Worker Architecture

상태: 비전 PRD v0.1
범위: 기존 Cloudflare Worker 라인 위에 provider-neutral DartLab Connector Gateway 를 배치하는 구조.

---

## 1. 결정

새 호스팅 후보를 찾지 않는다. DartLab 은 이미 Cloudflare Worker 운영 흔적이 있다.

현재 관련 자산:

```text
infra/workers/hfProxy
infra/workers/questionCollector
infra/workers/siteSignals
```

따라서 신규 거처는:

```text
infra/workers/dartlabConnector
```

`dartlabMcp` 라고 부르지 않는다. MCP 는 노출 표준 중 하나이고, 제품은 connector/gateway 다.

---

## 2. 논리 아키텍처

```text
AI clients
  -> /mcp
  -> /openapi.json
  -> /api/v1/tools/*
  -> /oauth/*

Cloudflare Worker: dartlabConnector
  -> adapter layer
  -> auth/scope/rate limit
  -> canonical tools
  -> evidence pack builder
  -> data access ports
  -> link/state service

Data sources
  -> HF parquet / static JSON
  -> existing hfProxy
  -> D1/KV/R2
  -> public DartLab viewer/terminal routes
```

---

## 3. Endpoint Layout

```text
/health
/mcp
/openapi.json
/.well-known/oauth-protected-resource
/.well-known/oauth-authorization-server

/api/v1/tools/resolve-entity
/api/v1/tools/company-snapshot
/api/v1/tools/search-filings
/api/v1/tools/filing-evidence
/api/v1/tools/financial-panel
/api/v1/tools/compare-companies
/api/v1/tools/watchlist-delta
/api/v1/tools/create-dartlab-link

/api/v1/state
/api/v1/link/viewer
/api/v1/link/terminal
/oauth/authorize
/oauth/token
/oauth/callback
```

OpenAPI 와 MCP 는 같은 canonical tool 을 감싼다. REST endpoint 와 MCP tool 이 서로 다른 로직을 가지면 안 된다.

---

## 4. 내부 모듈 분리

초기에는 Worker 하나로 시작한다. 내부 모듈만 분리한다.

```text
infra/workers/dartlabConnector/
  worker.js or src/index.ts
  wrangler.toml
  README.md
  .dev.vars.example

  src/adapters/mcp.ts
  src/adapters/openApi.ts
  src/adapters/chatGptUi.ts

  src/tools/resolveEntity.ts
  src/tools/companySnapshot.ts
  src/tools/searchFilings.ts
  src/tools/filingEvidence.ts
  src/tools/financialPanel.ts
  src/tools/compareCompanies.ts
  src/tools/watchlistDelta.ts
  src/tools/createDartlabLink.ts

  src/evidence/envelope.ts
  src/evidence/refs.ts
  src/auth/oauth.ts
  src/auth/scopes.ts
  src/security/rateLimit.ts
  src/security/untrusted.ts
  src/state/publicState.ts
  src/state/privateState.ts
  src/data/hfPublic.ts
  src/data/userContext.ts
```

규모가 커지면 다음처럼 분리할 수 있다.

```text
dartlabConnector-publicEvidence
dartlabConnector-userContext
dartlabConnector-stateLink
dartlabConnector-oauth
```

하지만 v0 에서 Worker 를 여러 개로 쪼개면 배포/인증/observability 비용만 늘어난다.

---

## 5. Storage Binding

| Binding | 용도 | Plane |
|---|---|---|
| KV `DARTLAB_PUBLIC_STATE` | public stateId, short metadata, cache pointer | Link-State |
| D1 `DARTLAB_USER_CONTEXT` | user watchlist, lastSeen, private state metadata | User Context |
| R2 `DARTLAB_EVIDENCE_CACHE` | 선택적 evidence pack cache, large JSON | Public Evidence |
| Secret `HF_PRIVATE_TOKEN` | private dataset read when needed | server only |
| Existing hfProxy | HF parquet/range/news proxy 재사용 | Public Evidence |

초기 public evidence 는 가능하면 기존 static/HF/hfProxy 를 읽는다. D1 은 사용자 상태가 필요할 때만 사용한다.

---

## 6. Public Evidence Plane

특징:

- 익명 호출 가능.
- 캐시 가능.
- source freshness 명시.
- 개인 정보 없음.
- 공개 공시/재무/회사 검색만.

도구:

```text
resolve_entity
get_company_snapshot
search_filings
get_filing_evidence
get_financial_panel
compare_companies
create_dartlab_link(stateVisibility=public)
```

캐시 정책:

```text
company/search metadata: edge cache 가능
filing evidence: rceptNo/topic 기준 cache 가능
financial panel: data version/asOf 기준 cache 가능
```

---

## 7. User Context Plane

특징:

- OAuth 필수.
- 사용자별 ACL.
- no-store 기본.
- 최소 데이터 반환.
- 전역 캐시 금지.

도구:

```text
get_watchlist_delta
create_dartlab_link(stateVisibility=private)
```

개인 데이터는 AI 에 통째로 넘기지 않는다. 질문에 필요한 최소 조각만 반환한다.

---

## 8. Link-State Plane

state 는 화면 전체 snapshot 이 아니라 **재현 가능한 포인터**다.

```text
company code
market
rceptNo
section
tab
period
compareCodes
sourceVersion
```

public state 는 누구나 열 수 있어도 되는 정보만 저장한다. private state 는 OAuth 사용자만 열 수 있다.

---

## 9. Deployment 원칙

repo 에 둘 수 있는 것:

```text
worker code
tool schema
OpenAPI schema
wrangler.toml binding 이름
.dev.vars.example
mock response
README
```

repo 에 두면 안 되는 것:

```text
OAUTH_CLIENT_SECRET
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID 값
HF_PRIVATE_TOKEN
SESSION_SIGNING_KEY
RATE_LIMIT_SALT
WEBHOOK_VERIFY_SECRET
```

운영 secret 은 Cloudflare Secrets 에 둔다. `.env` 는 개발자가 deploy 할 때 쓰는 자격증명일 뿐, 온라인 ChatGPT/Claude/Gemini 호출 경로에는 관여하지 않는다.

