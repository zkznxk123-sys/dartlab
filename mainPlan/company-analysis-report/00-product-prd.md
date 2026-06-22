# 00 · 제품 PRD — 기업분석보고서

## 1. 비전

퍼블릭 터미널 헤더 우측("토론"/"이슈" 옆)에 **"보고서"** 버튼 하나를 달아, 현재 선택된 회사(`?sym=`)의 분석을 **단일 문서·날짜 박힘·관점별·출처 라벨·인쇄가능** 형태로 즉시 표면화한다.

참조는 운영자 다운로드 폴더의 `경영성과 보고서 - 오프라인.html`(그랜터커머스 월간 경영성과 보고서, 회계사 작성)의 **문서 문법**이다:

- 헤더 리본(회사·대표·업종·작성일·"대외비"·인쇄/PDF 버튼)
- **종합 의견 한 문단**("매출은 X로 전월 대비 12.4%, 전년 동월 대비 18.2% 성장…수익 구조는 양호하나 운영자금 가용일수가 빠듯")
- 도메인별 상태 한 줄("수익성 — 양호 / 자금 — 주의 / 채권 — 조치 필요")
- KPI 카드 + 전월대비·전년동월 델타 칩
- 손익분기/안전마진 게이지, 위험선("3/29 · 위험선 근접")
- 리스크 / 예측 섹션
- 면책 안내("자동 산출 · 신고 전 검토 필요", "마감 확정 데이터 기준")

콘텐츠는 그 중소기업 내부 관리보고서를 **dartlab 상장사 분석으로 격상**한다 — 같은 문서 골격, 훨씬 풍부하고 출처 추적되는 분석.

## 2. 문제 (정확한 좌표)

story 엔진(`src/dartlab/story/`, L3 조합기)은 하위 엔진(analysis·credit·macro·quant·scan·industry) 결과를 **11 실효 관점 × 27 섹션 × 100+ 블록**으로 조립하는, dartlab 에서 가장 풍부한 서사 자산이다. 그러나:

- **퍼블릭 터미널 어디에도 렌더되지 않는다.** 터미널 = 전부 정량(차트/표/지표), narrative/thesis 층 0.
- `landing/static/story/manifest.json` = 메타카탈로그(reportTypes·sectionOrder·emphasize·focusQuestions·actHeaders baked)만, **회사별 콘텐츠 0**, UI 소비 0.
- story report dict 는 **Python 전용** → 정적 퍼블릭 클라가 못 받음.
- 헤더 우측에 "보고서" 슬롯 비어 있음. 인쇄/PDF 선례 0.

= "강력한 정보 많은데 다 못 쓴다"의 정확한 좌표. **문제는 분석이 부족한 게 아니라 표면화 경로가 0이다.**

## 3. 무게중심

> **강함은 새 분석이 아니라 "갇힌 story 계산의 표면화"다.**

단 두 가지를 명시한다:

1. **표면화는 "거의 0 작업"이 아니다.** 실제로는 (a) `renderJson` 직렬화를 **~70% 신규 확장**(현 출력 = `stockCode/corpName/sections` 3키 + summaryCard/circulationSummary, [`formats.py:493-507`](../../src/dartlab/story/formats.py#L493) 실측), (b) 11 관점을 manifest 정적 config 위 **결정론 클라 투영**으로 렌더, (c) **honest-skip reject-gate** 를 bake 에 박는 *배선 + 직렬화 확장* 작업이다.

2. **근거 토대는 `블록→rcept_no` ref 회로가 아니다.** 그 회로는 story 엔진에 **존재하지 않는다**(blocks.py 6 dataclass 에 출처 ref 필드 0, `EnrichedFlag.reference` 는 학술 출처일 뿐 — [`blocks.py:48-57`](../../src/dartlab/story/blocks.py#L48)). "모든 숫자→rcept 묶임"은 story 속성이 아니라 `ai/agent.py` Workbench 의 것이다. 보고서 1차의 근거 토대는 **3중 부분 회로**:
   - ① `sixActScore.evidence` — 축별 `evidenceIds`(예: `analysis:insights:grades`, `credit:distress`, `quant:valuation`), [`sixAct.py:44`](../../src/dartlab/story/sixAct.py#L44).
   - ② 블록별 `sourceEngine` 라벨 — 어느 dartlab 엔진(panel/analysis/credit/quant/industry/macro)이 계산했는가. **신규 정적 catalog 필드**(03문서 §sourceEngine).
   - ③ `narrate._classify` 결정론 레이블 — 값→임계 위치어휘.
   - 풀 `블록→rcept_no` 역배선(100+ 블록이 DART 공시 줄까지 운반)은 **명시된 신규 후속 트랙(P4+)**, P0 필수 아님.

## 4. 차별화 — 왜 90점인가

"AI 리포트"는 적대적 전문 분석가(가치투자자·신용심사역·공매도자)에게 늘 같은 지점에서 깎인다: ① 숫자 출처 불명 ② "양호/충분" 같은 판정어휘 톤 ③ 관점 뒤섞임 ④ 한계 은폐 ⑤ 닻 없는 점추정. 본 보고서의 90점은 **콘텐츠를 더 똑똑하게 만들어서가 아니라, 그 깎이는 지점을 품질게이트로 선제 차단**해서 달성한다:

| 깎이는 지점 | 본 보고서의 차단 |
|---|---|
| 숫자 출처 불명 | 블록별 `sourceEngine` 라벨 + evidenceIds 칩 + 섹션→공시뷰어 핸드오프 링크 |
| 판정어휘 톤 | raw 블록(표/지표)을 본문 1차, `narrate` 판정 프로즈 미호출. 단정형용사 → C-2 변환표로 측정값+자기이력분위 치환 |
| 관점 뒤섞임 | 1보고서 = 1관점 lock, emphasize ★만, 헤더 관점 명시, 타관점 섹션 import 금지 |
| 한계 은폐 | 결손 섹션 = 한계 라벨("데이터 부족 — 생략"), 발행불가 관점 = dim, 0-fill/impute 금지 |
| 닻 없는 점추정 | 예측 섹션 = 결정론 회귀 + `calcPlausibilityBand` 동반("추정" 명시), 궤적/what-if = scenario-sim 링크 |

= 일반 AI 리포트와의 비대칭: **모든 단정이 측정값+분위+출처로 풀리고, 풀리지 않는 문장은 렌더 거부된다(닫힌 검증 루프).**

## 5. 간판 5기능 (요약 — 상세 02문서)

1. **단일 reportPayload bake + 발행가능 관점 결정론 클라 투영** — 회사당 1 payload(full detail), 11 관점(full 포함·thesis 제외)은 정적 config 투영(12배 bake 폭발 회피). 신규 fetch 0.
2. **sixActScore evidenceIds 신규 표면화** — `EvidenceStrip`(점수 비노출, coverage[ready/missing] + evidenceIds 칩만). 축②(근거완전성)의 1차 천장.
3. **honest-skip reject-gate** — 데이터 빈약 회사는 *안 굽는다*. 클라 404 → "데이터 부족 — 보고서 미생성(사유)". 약한 발행 < 발행 거부.
4. **`@media print` + `window.print()` zero-dep PDF** — jspdf/html2canvas 금지(무겁고 한글 깨짐). 다크 터미널 → 화이트 A4 문서 토큰 재바인딩.
5. **섹션→공시뷰어 딥링크(90점 레버)** — 핵심 5막 섹션 헤더에 "원문 보기" → `ViewerOverlay` 가 섹션 대표 `rcept_no` 본문으로(섹션당 1개). 측정값→원문 공시 줄의 마지막 한 홉(신용/포렌식 독자 88→90+). 신규 *엔진* 0(뷰어 본체·데이터 재사용), 신규 *배선* = `ViewerOverlay` rcept 타깃 prop 1개 + 본문 스크롤(현재 code/vs만 받음, P2). 외부 DART floor 링크는 즉시 가능.

## 6. NEVER-CLAIM (제품 헌법 — 02·04·06 에서 게이트화)

1. **종합점수/레이더 화면 노출 금지.** `SixActScore` 는 6축 0~100 종합점수 레이더([`sixAct.py:1-15`](../../src/dartlab/story/sixAct.py#L1))다 — 보고서는 *점수를 빼고* 축별 coverage + evidenceIds 칩만 노출. 7축 품질점수도 내부 발행게이트 전용·화면 비노출.
2. **"세계급/유일/최고/최강/압도적/매수/매도/목표주가/강력추천" 금지** — 소스 토큰 grep + 생성 출력 claimGuard 이중게이트(둘 다 신규 구현, tests/audit 에 neverClaim 게이트 0개 실측).
3. **관점 블렌딩 금지** — ReportType lock.
4. **데이터 없는 섹션 억지 채움·0-fill·impute 금지** — 결측 = first-class, 한계 라벨.
5. **"발행가능 관점 N개" spike 전 단정 금지** — P0 spike 실측 산출.
6. **회계사 서명·1인칭·모델명·"AI 가 생성" 금지** — 주체중립. 푸터 = "dartlab 엔진 자동생성 · 데이터 as-of · 모든 수치 출처 · 투자권유 아님".
7. **외부 본문(공시/뉴스 sourceType=external) 마커 없이 본문화 금지** — `[EXTERNAL — untrusted]` 마커.

## 7. 착수 게이트

- **착수** = 운영자 go.
- **P0(spike)·P1(bake CI)** = 화면 아님 → 적정 사이클 자동 push 가능.
- **P2~P3(UI 화면)** = 공개 터미널 시각 회귀 위험 → **운영자 명시 승인("푸시해"·"올려"·"발간해") 후에만 push**. 그 전엔 commit 까지만 자율 + "검사 대기" 한 줄.
