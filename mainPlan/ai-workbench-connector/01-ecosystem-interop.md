# 01. AI 생태계 상호운용성 — MCP-first, OpenAPI-compatible

상태: 비전 PRD v0.1
범위: ChatGPT 만이 아니라 Claude, Gemini, API agent, LangChain/LlamaIndex 류 클라이언트까지 붙일 수 있는 provider-neutral 설계.

---

## 1. 핵심 결정

**DartLab 의 내부 표준은 특정 AI 제품이 아니라 `Canonical Tool Contract` 다.**

```text
DartLab Canonical Tool Contract
  -> MCP adapter
  -> REST/OpenAPI adapter
  -> ChatGPT App UI adapter
  -> Claude remote MCP adapter
  -> Gemini function-calling adapter
  -> LangChain / LlamaIndex / custom agent adapter
```

MCP 는 1차 표준이다. 하지만 MCP 만 만들면 안 된다. Gemini 류 function calling, 자체 agent client, 일반 개발자 통합은 OpenAPI/JSON Schema 를 더 자연스럽게 소비한다. 따라서 **MCP-first, OpenAPI-compatible** 이 정답이다.

---

## 2. 공식 근거

- MCP 는 여러 AI assistant 와 개발 도구가 지원하는 open protocol 이며, 서버가 data/tools 를 노출하는 구조다. 공식 intro 는 Claude, ChatGPT, VS Code, Cursor 등 broad ecosystem support 를 전제로 설명한다.  
  Source: https://modelcontextprotocol.io/docs/getting-started/intro
- OpenAI Apps SDK 는 ChatGPT 안에서 MCP server 와 web component UI 로 앱을 만드는 구조다. ChatGPT connector 생성은 HTTPS 로 접근 가능한 MCP server URL 을 요구하며, 모바일 앱에서도 연결된 connector 를 사용할 수 있다고 설명한다.  
  Sources: https://developers.openai.com/apps-sdk/ , https://developers.openai.com/apps-sdk/deploy/connect-chatgpt
- OpenAI 앱 제출은 실제 접속 가능한 MCP server URL, OAuth credentials, app 설명, tool 정보, screenshots, test prompts 등을 요구한다. placeholder URL 로 제출하면 안 된다.  
  Source: https://developers.openai.com/apps-sdk/deploy/submission
- OpenAI API 의 Responses API 는 `type: "mcp"` tool 로 MCP server URL 또는 connector id 를 붙이는 방식을 지원한다.  
  Source: https://developers.openai.com/api/docs/guides/tools-connectors-mcp
- Claude API 는 remote MCP server 를 Messages API 에 직접 연결하는 MCP connector 를 제공하고, HTTPS URL, tool allowlist/denylist, OAuth bearer token 을 다룬다. 단 현재는 MCP tools 중심이며 resources/prompts 지원 범위는 제한될 수 있다.  
  Source: https://platform.claude.com/docs/en/agents-and-tools/mcp-connector
- Gemini API 는 function calling 으로 외부 API/도구를 호출할 수 있고, function declaration 은 JSON schema 식 정의를 사용한다.  
  Source: https://ai.google.dev/gemini-api/docs/function-calling
- Cloudflare 는 Workers/Agents 위에 remote MCP server 를 배포하는 guide 를 제공하고, Streamable HTTP, authless 시작, OAuth 추가, Claude Desktop 등 다른 MCP client 연결 흐름을 설명한다.  
  Source: https://developers.cloudflare.com/agents/model-context-protocol/guides/remote-mcp-server/

---

## 3. 클라이언트별 설계

| Client | 1차 경로 | 보조 경로 | DartLab 원칙 |
|---|---|---|---|
| ChatGPT | Apps SDK + MCP `/mcp` | Responses API MCP tool | UI 는 선택. core 는 tool contract. |
| Claude | Remote MCP connector | API client-side tools | HTTPS MCP, OAuth bearer, allowlist 대응. |
| Gemini | OpenAPI/function schema | MCP bridge 가능 시 후속 | 얕은 schema, enum 명확, nested 최소화. |
| Custom agent | REST/OpenAPI | MCP client | HTTP JSON 으로 동일 envelope 반환. |
| LangChain/LlamaIndex 류 | MCP 또는 OpenAPI tool import | direct REST | structuredContent 중심. |
| 모바일 ChatGPT | 연결된 connector 사용 | deep link open | 화면 UI 는 모바일 테스트 필수. |

---

## 4. Adapter 원칙

Provider 별 차이를 tool logic 에 섞지 않는다.

```text
잘못된 구조:
  searchCompanyForChatGPT()
  searchCompanyForClaude()
  searchCompanyForGemini()

정답 구조:
  resolveEntity()
    -> mcpAdapter exposes resolve_entity
    -> openApiAdapter exposes resolve_entity
    -> chatGptUiAdapter renders result
```

Adapter 는 다음만 책임진다.

- tool schema 변환
- transport 차이 흡수
- auth token 전달 방식 차이 흡수
- UI component 가능 여부 분기
- response content type 제한 대응

비즈니스 로직, 데이터 조회, evidence pack 조립, 권한 검사는 adapter 바깥 `Canonical Tool Contract` 계층이 맡는다.

---

## 5. MCP primitives 사용 범위

초기에는 tools 중심으로 간다. 단 PRD 레벨에서는 resources/prompts 도 설계해 둔다.

### Tools

AI 가 직접 호출하는 기능. 예: `get_filing_evidence`, `get_financial_panel`.

### Resources

AI 또는 MCP client 가 특정 주소로 읽을 수 있는 구조화된 context.

```text
dartlab://company/KR/005930
dartlab://filing/{rceptNo}
dartlab://watchlist/{watchlistId}/delta
dartlab://terminal/state/{stateId}
```

### Prompts

반복 워크플로용 prompt template.

```text
analyze_recent_filing_change
daily_watchlist_brief
compare_financial_health
open_evidence_in_viewer
```

초기 ChatGPT/Claude 환경에서 resources/prompts 노출이 제한되면 tools 안에서 링크/상태 조회로 대체한다. 하지만 core contract 에서는 future-proof 로 유지한다.

---

## 6. 제품 포지셔닝

ChatGPT App 으로 시작할 수는 있다. 그러나 문서와 코드 명명은 ChatGPT 에 갇히면 안 된다.

권장 이름:

```text
mainPlan/ai-workbench-connector
infra/workers/dartlabConnector
```

피해야 할 이름:

```text
dartlabGpt
dartlabChatbot
dartlabMcpOnly
```

`MCP` 는 중요한 노출 표준이지만 제품 정체성은 `Workbench Connector` 다.

