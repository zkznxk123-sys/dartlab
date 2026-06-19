# 기업분석보고서 (Company Analysis Report) — PRD

> **한 줄 비전**: 퍼블릭 터미널 헤더의 버튼 하나로, story 엔진이 이미 계산하는 풍부한 회사 분석을 **날짜 박힌·출처 라벨된·관점별·인쇄가능한 단일 문서**로 뽑는다. 참조는 회계사가 만든 *월간 경영성과 보고서*의 문서 문법, 콘텐츠는 dartlab 상장사 분석으로 격상.
>
> **무게중심**: 강함은 새 분석이 아니라 **"갇힌 story 계산의 정직한 표면화"** — 단 정직 토대는 (존재하지 않는) `블록→rcept_no` ref 회로가 아니라 **3중 부분 회로**다: ① `sixActScore.evidence`(축별 evidenceIds) ② 블록별 `sourceEngine` 라벨(어느 dartlab 엔진이 계산했는가) ③ `narrate._classify` 결정론 레이블. 풀 `블록→rcept_no` 회로는 *정직하게 계상한 신규 후속 트랙*이지 P0 필수가 아니다.

---

## 이 PRD 가 푸는 문제

운영자 명령(원문 요지): "다운로드폴더의 경영성과 보고서 html 구조를 *보고서형 종목분석 참고*로, 퍼블릭 터미널에 버튼 달아 기업분석보고서를 뽑고 싶다. 터미널엔 강력한 정보가 많은데 다 못 쓴다. story 엔진의 *관점별 보고서* 개념을 담아라. 목표: 적대적 전문에이전트가 *생성된 보고서*를 90점 이상으로 인정."

진단(코드 실측): story 엔진은 **11 실효 관점(ReportType) × 27 섹션 × 100+ 블록**을 Python 에서 완성했으나 **퍼블릭 터미널 어디에도 렌더되지 않는다**(터미널 = 전부 정량 차트/표/지표, narrative 층 0). `landing/static/story/manifest.json` 은 메타카탈로그(reportTypes·sectionOrder·actHeaders baked)만 있고 **회사별 콘텐츠는 0**, UI 가 가져가지도 않는다. 이것이 "강력한 정보 많은데 다 못 쓴다"의 정확한 좌표다.

해법: 새 분석 엔진을 만들지 않는다. ① story 엔진이 굽는 **회사당 1개의 풍부한 reportPayload JSON** 을 HF 에 발행 → ② 11 관점을 그 payload 위 **정적 config(sectionOrder/emphasize/focusQuestions) 결정론 클라이언트 투영**으로 렌더 → ③ **honest-skip reject-gate** 로 데이터 빈약 회사는 *안 굽는다*(약한 발행 < 정직한 스킵) → ④ **Report Hook Engine 품질게이트**로 "AI 리포트"가 깎이는 지점을 선제 차단.

---

## 작업 산출 (README + 8문서)

| 파일 | 내용 |
|---|---|
| [00-product-prd.md](00-product-prd.md) | 비전·문제·무게중심·차별화·간판기능 요약·NEVER-CLAIM (제품 정본) |
| [01-current-state-audit.md](01-current-state-audit.md) | 가진 것 vs 표면화한 것의 갭 (실측 file:line) + **검증된 사실 정정 4건** |
| [02-killer-features-and-debate.md](02-killer-features-and-debate.md) | 간판 4기능 + 14인 전문가 토론·적대검증 평결 + 심판 7갭→해소 |
| [03-data-bake-and-payload.md](03-data-bake-and-payload.md) | bake 아키텍처 · **payload JSON 스키마 완전 예시** · sourceEngine 태깅 메커니즘 · P0 spike 측정→임계 절차 · buildReportView 의사코드 |
| [04-perspective-matrix-and-honest-conversion.md](04-perspective-matrix-and-honest-conversion.md) | 11 관점→보고서 템플릿 · 참조HTML 골격 매핑 · **C-2 정직변환표(행 단위)** |
| [05-information-architecture-and-ux.md](05-information-architecture-and-ux.md) | 다이얼로그 IA · 버튼 · 관점탭 · **EvidenceStrip(점수 비노출·coverage+evidenceIds만)** · 목업 · 인쇄 |
| [06-quality-rubric-and-acceptance.md](06-quality-rubric-and-acceptance.md) | Report Hook Engine 루브릭 · reject-gate · 7축 · pick 임계 · 적대 분석가 acceptance 페르소나 |
| [07-scope-phasing-guardrails-ledger.md](07-scope-phasing-guardrails-ledger.md) | Phase 0~4 · 형제 PRD 경계 5종 · 롤백 · 이중평가 · 게이트 · 진행 원장 + 재개 NEXT |

---

## 한눈 결정 (TL;DR)

- **무게중심**: "갇힌 story 계산의 정직한 표면화". 신규 *분석 엔진* 0. 정직하게는 (a) renderJson 직렬화 **~70% 신규 확장** (b) 11 관점 **정적 클라 투영** (c) **honest-skip reject-gate bake** = *배선 + 직렬화 확장* 작업.
- **간판 5기능**: ① 단일 reportPayload bake + 발행가능 관점 결정론 투영 ② sixActScore evidenceIds **신규 표면화**(coverage+ids, 점수 비노출) ③ honest-skip reject-gate ④ `@media print` + `window.print()` zero-dep PDF ⑤ **섹션→공시뷰어 딥링크**(핵심 5막·섹션당 대표 rcept_no = 측정값→원문 마지막 한 홉, 보고서 90점 레버. 신규 엔진 0, 신규 배선 = ViewerOverlay rcept 타깃 prop 1개 + 본문 스크롤).
- **정직 토대 = 3중 부분 회로**: sixActScore.evidence(evidenceIds) + 블록 sourceEngine 라벨 + narrate._classify. 풀 `블록→rcept_no` 는 신규 후속 트랙(P4+).
- **★검증된 사실 정정**(코드 실측, 2라운드, 01문서 + 02 §6): (i) 런타임 `Section` 엔 act 없으나 `SectionMeta`(catalog) **`act` 실재 + manifest 이미 baked** → catalog act 사용(`partId.split` 버그 폐기) / (ii) `sixActScore()` registry **미호출** → bake 직접호출 + `score`→`_internalScore` 분리 / (iii) 터미널 `EvidencePanel` 컴포넌트 **부재** → EvidenceStrip 신규 구축 / (iv) `SixActScore` = 6축 0~100 **레이더** → NEVER-CLAIM 준수 위해 보고서엔 *점수 빼고* coverage+evidenceIds만.
- **NEVER-CLAIM**: 종합점수/레이더/세계급/매수·매도·목표주가 화면 금지. 7축 품질점수는 **내부 발행게이트 전용·화면 비노출**(정직 라벨만). 모든 단정 = 측정값 + 자기이력분위 + sourceEngine 3튜플.
- **발행가능 관점 수는 박지 않는다** — P0 spike(30~50사 bake)가 관점별 nonEmpty emphasize-block 충족률을 실측해 확정. "관점 N개 발행가능" spike 전 단정 금지.
- **착수** = 운영자 go. **UI push = 운영자 명시 승인**(공개 터미널 화면 작업, CLAUDE.md ⛔). P0~P1(엔진/bake, 화면 아님)은 자동 push 가능.

---

## 출처

전문에이전트 14인 워크플로(설계 5 lens + 적대 비평 5 + 종합 리드 + 적대 PRD 심판 2라운드, `wf_5da6bc28-697`, 2026-06-19, 88/83) + **1차 코드 실측 검증**(심판 4 FATAL 을 grep/read 확인·정정) + **2차 적대검증**(작성된 8문서 대상 3인 독립 심판: PRD 엄정성 84·보고서 품질 88·코드사실 9/10 → 7건 추가 정정, 02 §6 H1~H7). 참조 문서 문법은 `Downloads/경영성과 보고서 - 오프라인.html`(그랜터커머스 월간 경영성과 보고서). 토론·심판 평결 정본은 본 문서들에 박제.
