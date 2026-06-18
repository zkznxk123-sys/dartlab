# 07. Progress Ledger

상태: v0.2 작성 완료 (`08-implementation-plan` 보강)
범위: 토론 수렴 기록, 결정 원장, NEXT.

---

## 1. 토론 렌즈

2026-06-17 기준 네 렌즈로 수렴했다.

| 렌즈 | 핵심 결론 |
|---|---|
| 제품 전략 | DartLab 챗봇이 아니라 AI 가 호출하는 공시·재무 evidence workbench connector |
| Cloudflare/MCP 아키텍처 | `dartlabConnector` Worker, MCP-first + OpenAPI-compatible, Canonical Tool Contract |
| 보안/프라이버시 | Public Evidence Plane 과 User Context Plane 완전 분리, OAuth scope, untrusted content |
| AI 생태계 상호운용성 | ChatGPT 는 1차 배포 채널, core 는 provider-neutral MCP/OpenAPI contract |

---

## 2. 결정 원장

### D1. 이름

결정: `AI Workbench Connector`

거처:

```text
mainPlan/ai-workbench-connector
infra/workers/dartlabConnector
```

기각:

```text
dartlabGpt
dartlabChatbot
dartlabMcpOnly
```

이유: MCP 는 표준 노출 방식이고, ChatGPT 는 배포 채널이다. 제품 본체는 neutral connector 다.

### D2. Tool surface

결정: 8개 canonical tools.

```text
resolve_entity
get_company_snapshot
search_filings
get_filing_evidence
get_financial_panel
compare_companies
get_watchlist_delta
create_dartlab_link
```

이유: tool 수가 많아지면 모델 선택 비용이 커지고 보안 경계가 흐려진다.

### D3. 외부 AI 에 범용 실행 금지

결정: public connector 에 `RunPython`, SQL, file IO 노출 금지.

이유: 기존 local/workbench MCP 와 public connector 는 보안 요구가 다르다.

### D4. Deep link 는 필수

결정: 모든 핵심 tool 은 가능한 경우 viewer/terminal link 를 반환한다.

이유: DartLab 의 독립 가치는 AI 답변이 아니라 검증 가능한 근거 화면이다.

### D5. Public/private split

결정: 공개 evidence 와 개인 context 를 tool/권한/캐시 레벨에서 분리한다.

이유: 공개 공시 도구가 사용자 워치리스트를 읽는 순간 제품이 보안적으로 성립하지 않는다.

### D6. 구현 착수 SSOT

결정: 구현 착수 기준은 `08-implementation-plan.md` 를 우선한다.

이유: 앞 문서들은 제품 방향과 아키텍처 원칙을 설명한다. 실제 코딩은 tool 별 AC, data source map, endpoint/schema, eval fixture, phase gate 가 더 중요하다.

---

## 3. 외부 근거

확인한 공식 문서:

- MCP intro: https://modelcontextprotocol.io/docs/getting-started/intro
- OpenAI Apps SDK: https://developers.openai.com/apps-sdk/
- OpenAI Connect from ChatGPT: https://developers.openai.com/apps-sdk/deploy/connect-chatgpt
- OpenAI app submission: https://developers.openai.com/apps-sdk/deploy/submission
- OpenAI MCP and Connectors API: https://developers.openai.com/api/docs/guides/tools-connectors-mcp
- Claude MCP connector: https://platform.claude.com/docs/en/agents-and-tools/mcp-connector
- Gemini function calling: https://ai.google.dev/gemini-api/docs/function-calling
- Cloudflare remote MCP server: https://developers.cloudflare.com/agents/model-context-protocol/guides/remote-mcp-server/

---

## 4. NEXT

운영자 go 이후 착수 순서:

1. `infra/workers/dartlabConnector` skeleton 작성.
2. canonical envelope/types 를 먼저 작성.
3. public tools 4개만 vertical slice:
   - `resolve_entity`
   - `search_filings`
   - `get_filing_evidence` Phase 1 metadata/link only
   - `create_dartlab_link(public)`
4. `/mcp` + `/openapi.json` 둘 다 같은 tool registry 를 보게 한다.
5. MCP inspector + REST smoke 로 같은 결과 검증.
6. body chunk evidence 는 `panelLoad.READ_COLUMNS` 경로를 Worker-safe 로 포팅한 뒤 Phase 2 로 착수.
7. OAuth/private plane 은 public evidence vertical slice 이후 착수.

---

## 5. 미해결 질문

코딩 전 결정 필요:

| 질문 | 현재 판단 |
|---|---|
| domain | 초기에는 `*.workers.dev`, 제출 전 custom domain 검토 |
| OAuth provider | Cloudflare Access 또는 DartLab 자체 OAuth 중 선택 필요 |
| public state TTL | 7~30일 범위, evidence link 사용성 보고 결정 |
| HF public/private 경계 | public data 는 hfProxy, private data 는 secret + 최소 endpoint |
| App submission timing | Phase 1~3 보안 게이트 후 |
