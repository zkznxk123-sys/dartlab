# 04. State 와 Deep Link

상태: 비전 PRD v0.1
범위: AI 답변에서 DartLab viewer/terminal 로 돌아오는 링크와 상태 저장 계약.

---

## 1. 핵심 결정

DartLab Connector 의 차별점은 답변이 아니라 **근거 화면으로 돌아오는 능력**이다.

```text
AI 답변
  -> evidence summary
  -> viewer link
  -> terminal link
  -> 사용자가 원문/표/차트에서 확인
```

AI 가 답변하고 끝나면 DartLab 은 단순 요약 API 가 된다. Deep link 가 있어야 workbench 가 된다.

---

## 2. Link 종류

| Link | 목적 | 예 |
|---|---|---|
| viewer link | 공시 원문/섹션/표 위치로 이동 | 사업보고서 공급망 섹션 |
| terminal link | 회사 terminal 의 탭/패널/비교 상태로 이동 | 재무 탭, 공급망 패널 |
| source link | 원천 DART/EDGAR 문서 | DART receipt |
| state link | 복합 상태 재현 | 회사 + 공시 + 섹션 + peer 비교 |

---

## 3. State 원칙

state 는 화면 전체를 저장하지 않는다. 재현 가능한 포인터만 저장한다.

```ts
type DartLabState = {
  version: 1
  visibility: "public" | "private"
  market: "KR" | "US"
  code: string
  view: "viewer" | "terminal"
  rceptNo?: string
  accessionNo?: string
  section?: string
  tab?: string
  period?: string
  compareCodes?: string[]
  sourceVersion?: string
  createdAt: string
  expiresAt: string
}
```

금지:

- 개인 메모 원문을 public state 에 저장.
- 워치리스트 전체를 public state 에 저장.
- OAuth token/session id 를 state 에 저장.
- AI 프롬프트 전문을 state 에 저장.
- 화면 DOM snapshot 저장.

---

## 4. Public State

public state 는 링크를 가진 누구나 열 수 있어도 되는 정보만 담는다.

허용:

```text
market
code
rceptNo
section
tab
period
compareCodes
sourceVersion
```

저장:

```text
KV: DARTLAB_PUBLIC_STATE
TTL: 7~30일
```

사용 예:

```text
"DartLab terminal 에서 삼성전자 공급망 패널 열기"
"DartLab viewer 에서 이 공시의 주주환원 섹션 열기"
```

---

## 5. Private State

private state 는 OAuth 사용자만 열 수 있다.

허용:

```text
내 워치리스트 id
마지막 방문 시각
개인 terminal layout pointer
사용자별 saved state metadata
```

저장:

```text
D1: DARTLAB_USER_CONTEXT
ACL: userId + stateId
Cache-Control: no-store
```

private link 는 다른 사용자가 열면 403 이 나야 한다. public fallback 으로 조용히 열면 안 된다.

---

## 6. `create_dartlab_link` 계약

입력:

```ts
{
  target: "viewer" | "terminal"
  market?: "KR" | "US"
  code: string
  rceptNo?: string
  section?: string
  tab?: string
  period?: string
  compareCodes?: string[]
  stateVisibility?: "public" | "private"
}
```

출력:

```ts
{
  data: {
    target: "viewer" | "terminal"
    url: string
    stateId?: string
    expiresAt?: string
    visibility: "public" | "private"
  },
  links: {
    viewer?: string
    terminal?: string
    filingSource?: string
  }
}
```

수용 기준:

- `viewer` target 은 가능한 경우 section anchor 를 포함한다.
- `terminal` target 은 tab/section 을 복원한다.
- private state 는 OAuth 없으면 생성 불가.
- public state 에 개인 데이터 0.
- link 생성 실패 시 raw state 를 응답하지 않는다.

---

## 7. 모바일 경로

모바일에서 터미널 전체 화면은 밀도가 높다. 따라서 AI 답변의 deep link 는 모바일 친화 view 우선순위를 가져야 한다.

```text
viewer link 우선:
  공시 근거 확인에 적합

terminal link:
  차트/재무/공시/AI 탭 중 한 화면으로 바로 진입

desktop terminal link:
  3열 dense terminal 복원
```

terminal-improvement PRD 의 모바일 최적화와 충돌하면, AI connector 는 모바일에서 viewer/evidence-first 를 우선한다.

---

## 8. 실패 모드

- AI 가 링크 없이 요약만 반환.
- viewer link 가 공시 첫 화면만 열고 section 으로 가지 못함.
- private state 가 public 으로 열림.
- state 에 사용자 개인정보가 포함됨.
- 링크가 "최신 데이터"라고 말하지만 sourceVersion/asOf 가 없음.
- 모바일에서 링크가 dense terminal 최상단만 열어 사용자가 다시 스크롤해야 함.

