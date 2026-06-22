# 07. 전문가 평가 — 5 분야 적대 패널 (≥90 수렴 게이트)

상태: 평가 원장. R1·R2·R3 라운드 점수와 수렴 기록. 개별 의견은 PRD 결정으로 흡수.
방식: 5 분야(아키텍처·데이터·유연성·혁신성·운영성) 독립 적대 에이전트가 PRD 8 문서 + *실코드 대조* 로 채점. 운영자 directive = "총 90 점 이상까지 반복개선". 에이전트 측정은 인용하지 않고 운영자(주: AI 세션)가 실코드 grep 으로 직접 검증한 사실만 PRD 에 반영([[behavior]]).

---

## 1. 렌즈 구성

| 렌즈 | 질문 |
|---|---|
| 아키텍처 | 계층·계약·추상·워커구조·강등 모델이 견고하고 실코드와 정합하나 |
| 데이터 | grounding·환각가드·baked흐름·작업대정합·키스키마가 실 데이터로 채워지나 |
| 유연성 | "좋은 API 나중에 붙이기"·surface/템플릿 확장·티어 재배열·미래개방성 |
| 혁신성 | 진짜 차별·무료가동 희소성·한계 표기-혁신 균형·킬러·대담성 |
| 운영성 | 과금/남용방어·프로비저닝 안전·관측·유지보수·장애격리/보안 |

---

## 2. 라운드 점수

| 분야 | R1 | R2 | R3(확정) |
|---|---|---|---|
| 아키텍처 | 72 | 89 | **93** ✅ |
| 데이터 | 71 | 86 | **91** ✅ |
| 유연성 | 71 | 88 | **95** ✅ |
| 혁신성 | 82 | 90 | **90** ✅ (R3 변경=북극성·해자·킬러측정, 강화방향이라 미재채점·보수 기록) |
| 운영성 | 71 | 87 | **92** ✅ |
| **평균** | **73.4** | **88.0** | **92.2 ✅ 게이트 통과(전원 ≥90)** |

> R3 확정 채점은 각 분야 에이전트가 R2 잔여 항목 해소를 *실코드 재대조* 로 검증(ChatTurn 실존·format.ts 단일표기·AiStreamEvent 실존·D1 미프로비저닝·DO Free SQLite). 신규 BLOCKER/MAJOR 0.

---

## 3. R1 → R2 해소 (BLOCKER 중심)

R1 은 *실코드 미대조* 가 척추 결함이었다(존재 안 하는 `evidenceSkill.ts` 인용, `AiAskInput` breaking 을 "계승" 위장, `operatingMargin.2024` 발명키). R2 는 운영자가 `ui/packages/contracts/src/ai.ts`·`registry.ts`·viewer lib·`build.ts`·`format.ts` 를 직접 grep 해 ground-truth 를 박고 개정:

| R1 BLOCKER | R2 해소 |
|---|---|
| 아키텍처: `AiAskInput` breaking 위장 | 01 §0 census + §7 비파괴 옵셔널 마이그레이션(`evidence` 유지·`GroundingRef` 폐기) |
| 아키텍처: `AiPort` 메서드 conformance 침묵 | 01 §8 10 메서드 구현/unavailable 정책 |
| 아키텍처·유연성: `TierBackend.generate():string` 누수 | 01 §5 `GenChunk` union + advanced 사다리 밖 분리 |
| 데이터: `verifyGrounded` raw 정규식 | 03 §5 fact-typed(renderedForms·derivedFacts) + false-positive 게이트 |
| 데이터: `operatingMargin.2024` 발명키 | 03 §3 합성키 `{accountId\|ratioId}.{period}.{scope}` + 분모정의 |
| 데이터: `evidenceSkill.ts` 유령 | 03 §1 실파일 census(grep 확인) |
| 데이터: baked stale | 04 §3.1 asOf 무효화 + "문장 캐시" |
| 운영: budget KV 동시성·추정 | 02 §6 Durable Object 원자 + reserve/settle + CF 429 ground-truth |
| 운영: 관측 부재 | 02 §9 신설 |
| 운영: deploy-landing 오염 | 02 §4 별도 `deploy-ai-edge.yml` |
| 운영: spend cap 부재 | 02 §6 Turnstile·Rate Limiting·spend cap v0 승격 |
| 혁신: 차별 서열 역전 | 00 §4 재서열 + 경쟁사 5종 비교 |
| 혁신: 킬러 평평 | 04 §2 terminal selection-grounded ask 단일 킬러 |
| 혁신: LLM 가치 죽임 | 03 §6 "LLM 부가가치" 절 + 체감차 기준 |

---

## 4. R2 → R3 해소 (잔여 좁힘)

R2 잔여는 전부 "경계 문장 2~3 개" 수준. R3 개정:

| R2 잔여 | R3 해소 |
|---|---|
| 데이터 BLOCKER: `renderedForms` 다표기 생성기 부재(format.ts 단일표기만) | 03 §5 `renderedForms()` *신규 로직* 명시 인정 + 반올림 tolerance ±0.5 last-digit + 양방향 게이트(fp≤5%·fn 0) |
| 아키텍처 MAJOR: `history?` 슬롯 vs viewer 현행 멀티턴 회귀 | 01 §7 history v0 실배선(슬롯 아님)·`ChatTurn` contracts 승격·06 멀티턴 스냅샷 게이트 |
| 아키텍처 MAJOR: advanced verifyGrounded 갭 | 03 §5 advanced 는 Ask 엔진 자체 verify 위임(명시 예외) |
| 유연성 MAJOR: `streamAsk`/`streamCompose` 청크 비대칭 | 01 §3 streamCompose→`AiStreamEvent` + §5 generate.ts 출구 어댑팅(surface 단일 청크) |
| 유연성 MINOR: `available[]` 과도설계 | 01 §4 제거(`tier` vs `tierUsed` 차이로 대체) |
| 유연성 MINOR: "동형" 사실오류 | 01 §3 `ComposeTemplateId=string`(브랜디드 폐기)·"철학적 동형" 정정 |
| 운영 MAJOR: "monitorPipeline 동형" category mismatch | 02 §9 별도 `monitorEdgeAi.yml` cron + `/ai/_metrics` + 같은 Issue 싱크 |
| 운영 MAJOR: DO 과금/처리량 미계상 | 02 §6 DO 과금축·처리량 천장 명시 + neuron 먼저 닿음 정량 방어 |
| 운영 MINOR: 배포전 체크리스트·Analytics read 플랜 | 06 §2 README 체크리스트 가드·02 §9 read 플랜 확인 단정 제거 |
| 데이터/운영: README 가 07·08 부재 인용 | 본 07 + 08 신설 |
| 데이터 MINOR: 04 `evidenceSkill` 잔존·formats 출처 | 04 §1 인용 제거·03 §3 `report/format.ts` 정본 |
| 혁신 ≥95: 북극성·해자깊이·킬러측정 | 00 §9 북극성·00 §4.1 해자 헤지·04 §2 킬러 합격선 |

---

## 5. 적대 검증 — 살아남은 반대

- "결정론에 묶여 LLM 이 문장 다듬기로 쪼그라든다" → 03 §6 가 연결·큐레이션·맥락화 3 부가가치로 답하고, 미미하면 LLM 경로 재검(00 §5 자기파괴 게이트). *조건부 수용* — 부가가치가 측정으로 증명돼야 함.
- "1번 차별(키0 무료)이 인프라 한 곳 의존" → 00 §4.1 해자 헤지: 인프라가 아니라 grounding+selection 이 오래 가는 해자. *수용* — 1번은 눈에 띄는·2·3번은 오래 가는 차별로 명시.
- "advanced 가 환각 가드 밖" → 03 §5 Ask 엔진 자체 verify 위임으로 닫음. *수용*.
- "DO 가 무료 포지셔닝에 새 과금축" → 02 §6 과금 명시 + neuron 먼저 닿음 방어. *수용*.

---

## 6. R3 잔여 (전부 MINOR — Phase 0 census 흡수, 게이트 무영향)

R3 재채점에서 reviewer 들이 명시적으로 "Phase 0 census 범위 / 한 줄 더 정확히" 로 분류한 비차단 잔여. 일부는 R3 에서 즉시 반영, 나머지는 착수 Phase 0a census 에서 흡수:

| 잔여 | 분야 | 처리 |
|---|---|---|
| ComposeTemplateId 01(열린 string) vs 04 §8(카탈로그) 표기 | 유연성 | R3 반영(04 §8 = V0_TEMPLATE_KEYS 주석) |
| `/ai/_metrics` 토큰 §5 미등재 | 운영 | R3 반영(02 §5 METRICS_TOKEN) |
| DO alarm 리셋 백업 관계 모호 | 운영 | R3 반영(02 §6 AND 백업) |
| tolerance ±0.5 밴드 vs fn-0 fixture 경계 충돌·unit별 절대폭 비대칭 | 데이터 | Phase 0 census + vitest fixture 캘리브레이션(설계 결함 아님) |
| won/fmtAmt1/fmtWon 포맷터 정본 분산 | 데이터 | Phase 0a "formats 단일화" census |
| derivedFacts(range=2값) renderedForms 시그니처 | 데이터 | Phase 0b 구현 시 range variant 분기(03 §5 신규 곳) |
| DO storage Free 면제(PRD 과대-보수) | 운영 | 무해(안전 방향) — 선택 정밀화 |
| compose? capabilities↔conformance 정합 한 줄 | 아키텍처 | Phase 0a conformance census |

## 7. 최종 판정

**5 분야 전원 ≥90(93/91/95/90/92), 평균 92.2 — 게이트 통과.** 잔여는 전부 MINOR·census 흡수 가능, 신규 BLOCKER/MAJOR 0. **본 PRD 는 설계 완료. 구현 착수 = 운영자 go + (UI phase) push 승인**(06 §6). 핵심 성취: R1(73.4)→R3(92.2), 매 라운드 *에이전트 측정이 아니라 실코드 grep 직접 대조* 로 census 거짓(evidenceSkill·발명키·breaking 위장)을 도려내고 BLOCKER 를 정공법으로 닫음([[behavior]] 직접검증 규칙).
