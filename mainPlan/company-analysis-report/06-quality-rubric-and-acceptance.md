# 06 · Report Hook Engine — 품질 루브릭 + Acceptance Test

> 운영자 목표 = **적대적 전문 분석가가 생성 보고서를 90점 이상 인정.** 그 보장의 정체 = "최고 보고서 강제"가 아니라 **"약한 보고서 발행 거부"**(editorial Hook Engine 공유). 점수는 **내부 발행게이트 전용 · 화면 비노출**(behavior 자기평가 노출금지).

## 1. 구조 — generate(bake) → reject-gate → 7축 점수 → pick

품질 점수 = **발행 게이트**(장식 아님). bake 가 굽고 게이트가 발행/스킵을 결정한다. 화면엔 **정직 라벨만**(점수 숫자 비노출).

## 2. Reject-Gate (하드 차단 — 통과 못하면 점수 계산 전 발행 거부)

| 게이트 | 차단 | 성격 |
|---|---|---|
| **G1 근거-고아** | 핵심 claim 이 evidenceIds + sourceEngine 라벨 **둘 다 0**(근거 토대 없는 단정). ★풀 rcept 회로 미구현이므로 1차 검사 대상 = sixAct evidenceIds + sourceEngine 누락. "evidence 토대 0인 핵심 claim 주입 → G1 reject" **red 테스트로 죽은게이트 방지** | 정직성·우회불가 |
| **G2 NEVER-CLAIM** | "세계급/유일/최고/최강/압도적/종합점수/레이더/총점/매수/매도/목표주가/강력추천" — 소스 토큰 grep + **생성 출력문자열 claimGuard** 이중게이트(둘 다 신규, tests/audit 에 0개 실측) | 정직성·우회불가 |
| **G3 untrusted 누출** | 외부 본문(sourceType=external)이 마커 없이 본문화 | 보안·우회불가 |
| **G4 관점 블렌딩** | sectionOrder/emphasize 가 선언 관점과 drift, 타관점 섹션 침입 | 강도 |
| **G5 stale** | as-of 없거나 basePeriod 가 N분기 초과 노후 | 강도 |
| **G6 날조 URL** | dartlab.io/.com 등 환각 도메인 | 정직성·우회불가 |
| **G7 판정어휘** | C-2 변환표에 없는 판정형용사("양호/주의" raw)가 conclusion·본문에 등장 | 정직성·우회불가 |

## 3. 7축 점수 (가중합 0~100 — 내부)

| 축 | 가중 | 측정 |
|---|---|---|
| ① 증거밀도 | 18 | claim 당 동반 표/지표 충실도 |
| ② **근거완전성** | 22 | ★1차 천장 = 0 이 아니라 **sixAct evidenceIds 표면화율 + 블록 sourceEngine 라벨 도달율**. `블록→rcept_no` 역배선 구축 전 22점 만점 불가는 **명시**하되, 부분 실재회로 위에서 *표면화율에 비례*해 채점(고정 12-14 아님) |
| ③ 관점일관성 | 14 | sectionOrder/emphasize/focusQuestions 가 선언 관점과 0 drift |
| ④ 정직한계명시 | 16 | 결손 = 명시 정직라벨, publishablePerspectives 미충족 관점 dim, 은폐 0 |
| ⑤ 서사명료 | 12 | conclusion 1줄(C-2 통과) + severity 색분류 + 위치어휘, 판정 프로즈 미호출 |
| ⑥ 무과대주장 | 10 | reject-gate 후 잔여 과장부사 밀도 |
| ⑦ 실행가능성 | 8 | 각 섹션이 공시뷰어/JUDGE(fin-stmt-lab)/시뮬 핸드오프 링크 보유. ★핵심 5막의 **섹션→공시뷰어 딥링크(간판5)** = 측정값→원문 마지막 한 홉의 닻(신용/포렌식 90점 레버) |

★축②가 무게중심(22)인데 1차 천장을 부분 실재회로(evidenceIds + sourceEngine) 위에서 정직 비례로 올린다 — 사상("갇힌 계산의 표면화")과 정합. 풀 회로(rcept)는 후속 트랙으로 천장을 올린다.

## 4. Pick 임계 + 화면 표시

| 점수(내부) | 발행 | 화면 라벨(점수 비노출) |
|---|---|---|
| ≥ 90 | verified 발행 | "검증됨" 또는 라벨 없음 |
| 75–89 | 조건부 발행 | "조건부: N섹션 생략 · M축 근거 미도달" 배너 강제 |
| < 75 | **발행 거부** | "데이터 부족 — 보고서 미생성(사유)" (약한 발행 < 정직 스킵) |

★**점수 자체는 화면에 노출하지 않는다.** 하단 quality 섹션 = 정직 라벨(생략 섹션·미도달 축)만. acceptance 의 "점수 공개" 항목은 삭제(behavior 자기평가 노출금지 준수).

## 5. Acceptance Test — 적대 분석가 페르소나 (90점 검증)

90점 인정의 정체 = **적대 분석가가 깎는 지점을 설계가 선제 차단**. 페르소나별 통과 기준:

| 페르소나 | 시나리오 | 통과 기준 |
|---|---|---|
| **신용심사역** | 삼성 credit 관점 | ≥90 + "부채/현금 숫자가 `sourceEngine:credit/panel` 라벨로 근거 도달" + 차환 4질문(focusQuestions)에 섹션이 답함 + **섹션→공시뷰어 딥링크로 원문 한 클릭 도달**(간판5, 측정값→원문 마지막 한 홉) |
| **가치투자자** | 가치평가 관점 | DCF/안전마진 = JUDGE(fin-stmt-lab) 링크(자체 재계산 0), 예측 = plausibilityBand 닻 동반("추정" 명시), 닻 없는 점추정 0. ★fin-stmt-lab **미착수 시** → 죽은 링크 금지 → "가치평가 닻 보류(JUDGE 미배포)" honest-skip 라벨. 현재값(PER 등)은 인라인 |
| **공매도자** | 소형주/적자사 | <75 → **발행 거부** 검증(억지 보고서 0). 발행되는 경우 모든 단정이 측정값+분위+출처로 풀림, "어느 엔진" 즉답 |
| **관점 차별** | executive vs credit vs valuation | 실제 **다른 sectionOrder · 다른 1줄 결론** 차별 매트릭스 PASS(같은 보고서 재탕 0) |
| **인쇄** | PDF 단일문서 | ★정량 PASS 아님 → 푸시 전 스크린샷/인쇄 미리보기 **눈검수 수동 게이트** |

## 6. 구현 (P0 ③)

- `tests/_attempts/reportQuality/` → 졸업 후 본진 `story/reportQuality.py`(`scoreReport` + reject-gate). claimGuard = `tests/audit` 신규 게이트(G2/G7 grep + 생성 출력 검사). G1 = sixAct evidenceIds 누락 검사로 **red 테스트 고정**(죽은게이트 방지).
- acceptance 페르소나 하니스 = spike 표본 회사로 4 페르소나 자동 채점 + 차별 매트릭스.
- A/B 진화(경량): 발행 후 사용 신호 → 월 1회 사람이 **7축 가중치만 ±10% 캡** 보정(`rubric_v` 태그). ML·자동분기 금지. `OutcomeLog` 재사용.
