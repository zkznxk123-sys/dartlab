# 00. 제품 비전 — 챗봇이 아니라 AI 가 읽는 DartLab 워크벤치

상태: 비전 PRD v0.1
범위: 사용자 의도, 제품 정의, 차별화, 성공/실패 기준, 왜 "우리 서비스 안 챗봇"이 아니라 "외부 AI 가 호출하는 근거 커넥터"인가.

---

## 1. 사용자가 원하는 것

사용자가 원하는 것은 DartLab 안에 또 하나의 AI 채팅창을 붙이는 게 아니다.

원하는 구조는 이거다.

```text
DartLab = 공시 · 재무 · 워치리스트 · viewer/terminal 상태 제공자
사용자 AI = 해석자
사용자 = 자기 AI 결제로 질문
```

사용자는 모바일에서 밀도 높은 터미널을 직접 다 파고들기 어렵다. 그래서 이미 쓰는 AI 에 이렇게 묻고 싶다.

```text
"내 워치리스트에서 오늘 볼 공시 뭐야?"
"삼성전자 최근 사업보고서에서 공급망 관련 바뀐 부분 보여줘."
"이 회사 실적이 좋아진 이유를 재무제표와 공시 근거로 설명해줘."
"답변 근거를 DartLab viewer 에서 열어줘."
```

이때 DartLab 은 답변을 생성하는 모델이 아니라 **AI 가 호출하는 공시·재무 근거 서버**가 되어야 한다.

---

## 2. 제품 정의

**DartLab AI Workbench Connector 는 외부 AI 가 DartLab 의 공시·재무·워치리스트·viewer/terminal 상태를 안전하게 조회하고, 사용자가 답변의 근거를 DartLab 화면에서 즉시 검증할 수 있게 하는 AI-native evidence workbench layer 다.**

제품은 세 평면으로 나뉜다.

| Plane | 역할 | 인증 | 캐시 |
|---|---|---|---|
| Public Evidence Plane | 회사 검색, 공개 공시, 공개 재무 패널, viewer link | 익명 가능 | 강한 캐시 가능 |
| User Context Plane | 내 워치리스트, 마지막 방문 이후 델타, 개인 terminal state | OAuth 필수 | no-store 또는 사용자별 짧은 TTL |
| Link-State Plane | viewer/terminal deep link, 재현 가능한 stateId | public/private 상태에 따라 분기 | public TTL, private ACL |

제품의 최종 그림은 이렇다.

```text
AI 답변
  -> 근거 요약
  -> Evidence Pack
  -> DartLab viewer link
  -> DartLab terminal link
  -> 사용자가 원문/표/차트에서 검증
```

---

## 3. 핵심 사용자

### 3.1 B2C 개인 투자자

모바일 터미널을 직접 스크롤하기보다 자기 AI 에 먼저 묻는다. 관심사는 "종목 추천"보다 "내가 보던 회사에 무슨 변화가 생겼는가"다.

필요한 기능:

- 내 워치리스트 공시 델타
- 최근 공시 변화 요약
- 재무 핵심 수치와 출처
- viewer/terminal 링크

### 3.2 B2B 리서치 · IR · 회계 · 투자 실무자

답변보다 중요한 것은 근거다. 어느 공시, 어느 섹션, 어느 표에서 나온 숫자인지 추적 가능해야 한다.

필요한 기능:

- 공시 원문 section anchor
- 재무 패널 기준일/기간/계정명
- 동종 비교 근거
- 팀 공유 가능한 링크

### 3.3 AI 워크플로 사용자

ChatGPT 하나가 아니라 Claude, Gemini, agent framework, 사내 AI 에서 DartLab 데이터를 호출하고 싶다.

필요한 기능:

- MCP endpoint
- OpenAPI/function schema
- 일관된 JSON envelope
- OAuth scope 와 read-only 정책

---

## 4. 차별화

DartLab 의 차별점은 모델이 아니다.

```text
공시 원문 근거
재무 패널
워치리스트 변화
viewer section anchor
terminal state deep link
```

일반 AI 는 그럴듯한 해석은 하지만 DartLab viewer 의 특정 위치, DART receipt, 재무 패널의 as-of, 사용자의 watchlist delta 를 모른다. DartLab Connector 는 AI 가 모르는 **현장 데이터와 검증 가능한 화면**을 제공한다.

따라서 차별 포지션은:

```text
"AI 답변에서 끝나는 서비스"가 아니라
"AI 답변 -> DartLab 근거 화면 -> 터미널 분석"으로 돌아오는 서비스
```

---

## 5. 성공 기준

성공은 AI 가 문장을 잘 쓰는지가 아니다. 성공은 DartLab 이 근거 서버로 쓰이는지다.

| 기준 | 의미 |
|---|---|
| AI 답변에서 viewer 로 돌아오는 비율 | 답변이 검증 행동으로 이어지는가 |
| 워치리스트 델타 반복 사용률 | 재방문 이유가 생겼는가 |
| 회사 검색 → 공시 근거 조회 → viewer 열기 전환율 | AI 가 DartLab 을 discovery 가 아니라 workbench 로 쓰는가 |
| 출처 클릭률 | 근거가 실제로 신뢰 행동을 만든다 |
| 환각·잘못된 근거율 | evidence pack 품질 |
| B2B 팀 공유/재조회 빈도 | 링크와 state 가 협업 자산이 되는가 |

가장 중요한 기준은 하나다.

```text
사용자가 AI 답변을 믿기 전에 DartLab 근거를 열어본다.
```

---

## 6. 실패 기준

다음으로 흐르면 실패다.

- 종목 추천 챗봇이 됨.
- 공시 원문 링크 없는 요약봇이 됨.
- ChatGPT 전용 기능으로 닫힘.
- 모델에 DartLab 데이터를 통째로 던짐.
- 모바일 터미널 개선을 AI 로 대체하려 함.
- 퍼블릭에서 개인화/실시간성/완결성을 과장함.
- 매수·매도·목표주가 같은 투자 조언으로 포지셔닝함.

---

## 7. 제품 원칙

1. **Evidence first.** 모든 tool response 는 근거를 먼저 가진다.
2. **Provider neutral.** 특정 AI 제품의 SDK 를 core logic 에 섞지 않는다.
3. **Public/private split.** 공개 공시 데이터와 개인 워치리스트를 같은 tool 에 섞지 않는다.
4. **Deep link required.** 근거를 열 수 없는 답변은 DartLab 답변이 아니다.
5. **Read-only first.** 초기 connector 는 조회·링크 생성만. 쓰기 기능은 state 저장까지 제한.
6. **No trading action.** 거래 실행, 투자 성향 기반 추천, 목표주가 단정은 범위 밖.
7. **No universal runtime.** 외부 AI 에 범용 Python/SQL/tool runner 를 주지 않는다.

