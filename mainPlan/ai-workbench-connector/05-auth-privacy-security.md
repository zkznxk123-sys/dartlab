# 05. Auth · Privacy · Security

상태: 비전 PRD v0.1
범위: OAuth, public/private 분리, secret 관리, prompt injection, rate limit, logging, 투자 조언 리스크.

---

## 1. 핵심 보안선

DartLab Connector 는 처음부터 두 평면을 분리해야 한다.

```text
Public Evidence Plane
  - 공시 원문/근거
  - 회사 검색
  - 공개 재무 패널
  - viewer/terminal public deep link
  - 익명 호출 가능, 캐시 가능, 재현 가능

User Context Plane
  - 내 워치리스트
  - 마지막 방문 이후 델타
  - 개인 terminal state
  - 저장한 분석/메모/히스토리
  - OAuth 필수, 사용자별 권한 필수, 전역 캐시 금지
```

공개 tool 이 개인 상태를 읽으면 PRD 위반이다. 예를 들어 `get_company_snapshot` 은 공개 tool 이고, `get_watchlist_delta` 는 개인 tool 이다.

---

## 2. OAuth Scope

초기 scope 는 작게 쪼갠다.

```text
public:read
filing:read
finance:read
watchlist:read
terminal_state:read
terminal_state:write
viewer_link:create
```

기본 연결은 `public:read` 만으로도 동작해야 한다. 개인 기능은 사용자가 명시 승인한 scope 만 허용한다.

권한 규칙:

| Scope | 허용 |
|---|---|
| `public:read` | 회사 검색, 공개 snapshot |
| `filing:read` | 공개 공시 목록/근거 |
| `finance:read` | 공개 재무 패널 |
| `watchlist:read` | 내 워치리스트 델타 |
| `terminal_state:read` | 내 private state 조회 |
| `terminal_state:write` | 내 private state 저장 |
| `viewer_link:create` | public/private link 생성 |

Worker 는 매 요청에서 token 의 issuer, audience, expiry, scope 를 검증한다.

---

## 3. Secret 관리

repo 에 secret 을 두지 않는다.

Cloudflare Secrets:

```text
OAUTH_CLIENT_SECRET
SESSION_SIGNING_KEY
HF_PRIVATE_TOKEN
RATE_LIMIT_SALT
WEBHOOK_VERIFY_SECRET
```

repo 에 둬도 되는 것:

```text
wrangler.toml binding 이름
.dev.vars.example
tool schema
public endpoint 계약
mock 응답
README
```

명확히 구분한다.

```text
런타임 secret = Cloudflare Secret
배포자 credential = 개발자 로컬 .env
AI/사용자 호출 경로 = 온라인 Cloudflare Worker URL
```

`.env` 는 온라인 ChatGPT/Claude/Gemini 가 쓰는 값이 아니다.

---

## 4. Prompt Injection / Untrusted Content

DartLab 의 공시 원문, 사업보고서, 뉴스, 외부 텍스트는 모두 untrusted content 다.

tool 응답은 반드시 데이터로 감싼다.

```text
[EXTERNAL CONTENT START - untrusted]
공시 본문 excerpt
[EXTERNAL CONTENT END]
```

또는 structured field 로 분리한다.

```ts
{
  excerpt: "...",
  contentTrust: "external_untrusted"
}
```

금지:

- 외부 원문을 system/developer prompt 에 넣기.
- 공시 원문 안 문장을 tool 선택 지시로 취급.
- 외부 원문이 private tool 호출을 유도하게 두기.
- 근거 chunk 와 해석 지시를 한 필드에 섞기.
- "이전 지시 무시" 같은 문구를 모델 지시로 전달.

---

## 5. Rate Limit / Abuse Defense

남용 방어는 세 축으로 한다.

```text
IP 기준:
  익명 public API 남용 차단

userId 기준:
  OAuth 사용자별 quota
  private tool 호출 제한

client/app 기준:
  AI 플랫폼별 client_id 또는 audience 기준 제한
```

비용 등급:

| 등급 | Tool | 정책 |
|---|---|---|
| 저렴 | `resolve_entity`, `search_filings`, `create_dartlab_link(public)` | 캐시 강함 |
| 중간 | `get_company_snapshot`, `get_filing_evidence` | sourceVersion 기준 캐시 |
| 비쌈 | `get_financial_panel`, `compare_companies` | quota 관리 |
| private | `get_watchlist_delta`, `create_dartlab_link(private)` | OAuth + no-store |

response 에 운영 추적 필드를 둔다.

```text
requestId
userScope
cacheStatus
asOf
dataFreshness
```

raw IP, 이메일, OAuth token 은 로그에 남기지 않는다. 필요하면 salted hash 또는 집계 counter 만 남긴다.

---

## 6. Investment Advice Risk

DartLab Connector 는 투자 조언자가 아니다. 근거 워크벤치다.

허용:

```text
공시 변화 요약
재무 수치 근거 제시
동종 비교 데이터 제공
리스크 항목 정리
viewer 근거 링크 제공
```

금지:

```text
매수/매도/보유 지시
목표주가 단정
수익률 보장
개인 투자성향 기반 추천
"오늘 사야 한다" 같은 실행 권고
```

모든 tool response 의 `safety` 에 다음이 포함된다.

```ts
{
  evidenceOnly: true,
  notInvestmentAdvice: true
}
```

`limitations` 에는 필요한 경우 다음을 포함한다.

```text
공개 공시/재무 데이터 기준
EOD 또는 배치 데이터 기준
실시간 체결/호가 아님
애널리스트 목표주가/컨센서스 아님
투자 조언 아님
```

---

## 7. 보안 출시 게이트

출시 전 차단 조건:

```text
1. public/private tool 완전 분리
2. OAuth scope별 접근 테스트
3. private 응답 Cache-Control: no-store 검증
4. secret repo 유입 0
5. prompt injection fixture 테스트
6. rate limit 우회 테스트
7. 투자 조언 금지 문구와 tool 정책 고정
8. viewer/terminal link 에 권한 없는 state 노출 0
9. external_untrusted marking 누락 0
10. raw token/email/IP log 0
```

