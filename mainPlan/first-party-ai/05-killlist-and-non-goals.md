# 05. Kill List & Non-Goals

상태: 경계 PRD v0.1
범위: 안 하는 것. 정체성 미끄러짐·과장·아키텍처 손상·회귀를 미리 차단한다.

---

## 1. KILL — 절대 안 함

### K1. surface 별 분산 AI 구현
viewer 처럼 surface 안에서 webllm/ollama/fetch 를 직접 부르는 구조를 *늘리지* 않는다. 전부 `runtime.ai` 포트. 이게 본 PRD 의 존재 이유. (현재 viewer 직접 import 는 03 §7 로 *회수* 한다.)

### K2. 숫자 생성을 모델에 맡김
모델은 Grounding facts 의 숫자를 *인용* 만 한다. 모델이 만든 수치는 사후검증(03 §5)에서 stray 로 잡혀 채택 거부 또는 절단. "AI 가 계산했다" 는 결정론 SSOT 가 한다.

### K3. 퍼블릭 브라우저/워커에 무거운 에이전트 재현
5패스 노드 그래프·`BRIEF/WORK/CRITIQUE/...` 고정 노드·multi-turn tool-calling agent 를 edge/onDevice 에 만들지 않는다. 그건 `advanced`(로컬 ask 엔진) 전용. edge/onDevice 는 *단발 근거-서술* 생성기. [[feedback_no_graph_regression]] 직접 적용 — `checkAgentBoundary.py` 가드 범위.

### K4. "무제한 무료 AI" 과장
Cloudflare 무료티어 = 10k neurons/day. 예산 서킷브레이커로 보호하고, 마케팅·UI·문서 어디서도 "무제한/영구 무료" 로 쓰지 않는다(`ai-workbench-connector` 정직 척추 §7 계승). "퍼블릭 무료 가동, 한도 도달 시 온디바이스로" 가 정직 표현.

### K5. 투자 조언
매수/매도/보유, 목표주가 단정, 수익률 보장, 개인 성향 추천 = 범위 밖. 허용 = 공시 변화·재무 수치 근거·동종 비교·리스크 항목·추세 *서술*. 프롬프트 가드 + 출력 필터.

### K6. 커넥터와 혼입
외부 AI 노출(`/mcp`·`/openapi.json`·OAuth·watchlist delta)은 `ai-workbench-connector` 의 일. 본 PRD 워커(`aiEdge`)에 그 엔드포인트·D1 사용자 상태·OAuth 를 *넣지 않는다*. 공유는 Grounding 근거 빌더 한 곳만(00 §7).

### K7. surface 안 티어/env 분기 코드
`if (runtime.env.kind==='public')`·`if (tier==='edge')` 같은 분기를 surface 에 두지 않는다(02-runtime-ai-services §1·§10 계승). 티어는 `capabilities()` 표시(배지·CTA)로만 노출. 분기는 어댑터 polymorphism.

### K8. 온디바이스 장문 생성
web-llm 4096 컨텍스트 하드캡([[project_viewer_cag_infeasible]]). onDevice 는 짧은 답·짧은 카피만. 장문(블로그 본문)은 baked(CI, 큰 모델/실 API 가능) 또는 결정론 구조. onDevice 로 장문 시도 금지.

### K9. 정적 카피의 런타임 생성
캐러셀 카드·블로그 문단·랜딩 블러브처럼 *사용자 입력에 안 의존* 하는 카피를 런타임에 LLM 으로 만들지 않는다. baked(CI)가 정답 — 비용 0·검수 가능·일관. live 는 사용자 질문/선택이 입력일 때만(terminal ask, report "더 풀어줘").

---

## 2. DEFER — 지금 안 하지만 자리 비워둠

| 항목 | 왜 미룸 | 언제 |
|---|---|---|
| 실 API 티어(Claude/GPT) | 무료 경로 먼저 안정화 | `TierBackend` 1개 추가로 (01 §5) 언제든 |
| landing 기능 카피(featureBlurb) | 손작성이 대개 적절 | 운영자 발의 시 |
| edge 다턴 대화 | 단발로 충분, budget 보호 | 수요·예산 확인 후 |
| 인과·정성 환각 가드 | 숫자 가드부터 | 방법론 성숙 후([[project_search_strengthening_loop]] 자산 재사용) |

> **R1 운영 승격 — DEFER 에서 v0 필수로 끌어올림**: Turnstile(봇 차단) + CF native Rate Limiting + **CF Workers Paid spend cap(과금 상한)** 은 미루지 않는다. origin 헤더는 위조 가능(보안 아님)·per-IP 는 IP 로테이션에 무력 → edge 가 metered 인 이상 이 3겹이 *없으면* 과금 공격에 노출. 02 §6 의 4겹 방어로 v0 에 포함.

---

## 3. NON-GOAL — 애초에 목표 아님

- 자체 모델 학습/파인튜닝(GPU0 사상, [[project_finance_slm]] 별개 트랙).
- viewer 의 ask 를 *교체* (정리·끌어올림이지 재작성 아님).
- 결정론 계기판을 AI 로 대체(AI 는 *위에 얹는* 레인, 결정론이 척추).
- 임베딩/RAG 신설(검색은 기존 BM25·search 포트 재사용, [[project_disclosure_search_serverless]]).
- 데이터 작업대 fetch 재설계(Grounding 은 포트 *소비자*, 03 §6).

---

## 4. 정직 TTL·캐시 정책

- edge `/ai/*` 응답: **캐시 안 함**(scope:'none') — 같은 질문도 컨텍스트(asOf·선택)가 다름. 단 baked compose 산출물은 데이터라 HF origin 캐시 정상.
- `/ai/health`·budget: 짧은 TTL(예 60s) — 예산은 실시간성 생명.
- baked 리드/카피: 데이터 버전·asOf 기준 캐시 가능(작업대 정직 TTL 계승).

---

## 5. 한 줄 경계 요약

```text
이 PRD = DartLab 1인칭, 근거에 묶인, 끊기지 않는, 정직한 티어 사다리.
아닌 것 = 외부 AI 게이트웨이 · 무제한 무료 챗봇 · 숫자 만드는 모델 · 투자 조언 · surface 분산 구현.
```
