# Simulate — 미래 리플레이 시뮬레이터 PRD Index

상태: 비전 PRD v0.4 (스위트 버전 — 2026-06-14 구현 정합 정정: simulate/ 결정론 코어 졸업[4노드 DAG·random.Random·proforma-FCFF·공개 verb] 반영 + 문서↔코드 발산 정합)
범위: 과거 근거 → 미래 시뮬레이션. 거시·지수·뉴스·공시·재무를 미래로 투영하고, if(가정)를 켜고/끄며, **재생버튼으로 미래가 시간순으로 펼쳐지는 퍼포먼스**를 결과물로 내는 DartLab의 정점 기능.

---

## 한 줄 결정

이 기능은 "주가 예측기"가 아니다. `asOf` 시점에 알려진 근거와 명시 가정을 고정한 뒤, **재생버튼을 누르면 그 가정 하에서 미래가 시간순으로 펼쳐지는(주가·사건·지표·재무) 결정론적 리플레이 퍼포먼스**다. 핵심 명제: *미래를 맞히려는 게 아니라, 명시된 가정 하에서 무슨 일이 벌어질 수 있는지를 확률 분포로 정직하게 보여준다.* scenario ≠ forecast.

---

## 핵심 결정 요약 (v0.2)

- **엔진**: 새 **L2.5 독립 묶음** `simulate/`(드라이버 DAG + 엣지 transfer 소유, leaf 계산은 L2 SSOT 호출). story 동급 L3 기각(story=순수 렌더러 "자체 계산 0"인데 simulate는 transfer 계산 소유) + 신규 L2 기각(L2↔L2 cross-import 금지) → `L2_PEERS` 미소속이라 analysis+macro+quant 동시 결합 합법. 톱레벨 verb = `dartlab.simulate(...)`, 단일 종목 = `Company.simulate(...)`, `mode=whatif|replay|walkforward` 흡수. 상세 = [01-engine-architecture.md](01-engine-architecture.md).
- **중심 산출물**: ★Play 미래 리플레이 — 기존 터미널 replay 상태기계(과거 되감기)의 미래 방향 대칭 확장. 새 재생 엔진 0. 미래 캔버스는 사전 계산된 결정론 path를 *드러내는 것*(매 프레임 재계산 아님). → [05-play-future-replay.md](05-play-future-replay.md).
- **데이터 모델**: AssumptionLedger(if 토글 SSOT) + ScenarioTree(분기) + EvidenceGraph(근거-드라이버, 인과 단정 금지). 분기 생성 싸게·가지치기는 결정론 엔진(회계 항등식·과거 베타). Morphological Field/CIB는 다축 확장(Phase 5+)으로 deferred.
- **AI 의견**: 결정론 엔진 = SSOT, AI = `ai/tools/` lens 도구가 내는 ref 첨부 의견 카드. 채택 판정 = 결정론 gate(순수 함수). graph/node/pass 0 추가(no-graph-regression). → [03-validation-ai-review.md](03-validation-ai-review.md).
- **지수 차트(v0.4)**: 안3(center 탭 주가/지수) + 안4(picker) + CMP. PriceChart `subject` 모드(둘째 차트 0, soft-swap). subject 소유권 = CenterStack-local `$state`(ChartCtl 미상향). IndexPort(`catalog/search/series`). **KR gov 지수=OHLCV 캔들 + US FRED 지수=종가 라인(SP500·NASDAQ·다우·VIX) 평행 통합**(운영자 결정 '미국 지수는 FRED 고려' — FRED 데이터 라이브 실측, 새 차트·포트 0·`candleStyle='area'` degenerate candle, 종가전용 지표 3분기 매트릭스). → [06-index-chart.md](06-index-chart.md).
- **통합 시퀀싱**: 지수(1) → 공시 이벤트 레일(2) → 백테스팅 Strategy Tester(3) → 시뮬레이션+Play(4). mainPlan(ui/packages 승격) 이후 착수. 단 지수 차트는 mainPlan 무관 선행 가능. → [07-integration-roadmap.md](07-integration-roadmap.md).
- **착수 전 선결 kill-test — ✅ 완료(2026-06-14)**: ★MC 재현성(`_simMonteCarlo.py:145`·`pricetarget.py:278` 전역 `random.seed` → 로컬 `random.Random(seed)`, **stdlib·pyodide 안전 — numpy PCG64 아님**) + `:205` 덮어쓰기 버그 → 연도별 cumprod(`test_horizon_widens_cone` kill-test로 옛 버그 증명 후 전환). 단 이 수정은 *레거시 MC 경로*(`analysis/forecast/_simMonteCarlo`) 한정 — **신생 `simulate/` 결정론 코어에는 MC 노드가 아직 없다**(mc.distribution 후속 단계, 01 §5b). Play 결정론·URL 공유·TS 패리티의 척추. 09 P1.

---

## 문서 지도

**코어 (시뮬레이터 엔진·방법·검증):**
1. [00-product-prd.md](00-product-prd.md) — 제품 비전, 사용자 문제, 핵심 화면, 범위, scenario ≠ forecast 정직 척추.
2. [01-engine-architecture.md](01-engine-architecture.md) — 엔진 거처 L2.5 `simulate/`·verb·AI 보완/경합·성능·횡단면·계층 계약.
3. [02-assumption-and-simulation-method.md](02-assumption-and-simulation-method.md) — 가정 장부·vintage·bridge·절차 + §2B DriverRegistry 수렴/확장.
4. [03-validation-ai-review.md](03-validation-ai-review.md) — look-ahead 차단·walk-forward·품질 게이트·AI 패널·반증·출시 기준.
5. [04-progress-ledger.md](04-progress-ledger.md) — 현재 결정·문서 상태·워크스페이스 변동·NEXT 닫기 체크리스트.

**제품 경험 (UI 단면):**
6. [05-play-future-replay.md](05-play-future-replay.md) — ★중심 산출물. Play 미래 리플레이·미래 캔버스·다중분기·if 토글 실시간·근거 인벤토리·graceful degradation.
7. [06-index-chart.md](06-index-chart.md) — 지수 차트 v0.4(안3 center 탭 subject-swap + 안4 picker + CMP, IndexPort catalog/search/series, **KR gov OHLCV 캔들 + US FRED 종가 라인 평행 subject**, candleStyle='area' degenerate·종가전용 지표 3분기, subject 소유권 seam, FRED 데이터 라이브 실측).
8. [07-integration-roadmap.md](07-integration-roadmap.md) — 통합 시퀀싱(지수→이벤트레일→백테스팅→시뮬), 공유 DNA, mainPlan 의존, Phase −1~7.

**발간·정합화 (시뮬의 읽기 방식):**
9. [08-valuation-report.md](08-valuation-report.md) — 시뮬레이터=가치평가 엔진 동형, 적정주가(reverseDCF 닻+조건부 범위), 프로급 보고서, 규제선 가드. 발간은 코어 졸업 후.
10. [09-architecture-consolidation.md](09-architecture-consolidation.md) — 시뮬레이터-앵커 부채 원장(DCF 5중·회귀 4중 등 16행)·신용=solvency 뷰·외과 청산 Phase 시퀀스. **앵커 양방향**: 역=leaf 수학 금지(`test_simulate_leaf_ssot`), 순=leaf 계약 drift CI red(`test_simulate_leaf_binding`, P16).

**컴포넌트 스펙 (메모리에서 이관):**
11. [10-backtesting-strategy-tester.md](10-backtesting-strategy-tester.md) — 차트 중심 EOD 백테스팅(전 `project_terminal_backtesting_prd`).
12. [11-disclosure-event-rail.md](11-disclosure-event-rail.md) — 공시 위치 찾기 레일(전 `project_terminal_disclosure_event_rail_prd`).

> ⚠ UI 토폴로지: 본 세션 중 터미널이 `landing/src/lib/terminal/` → **`ui/packages/surfaces/src/terminal/`로 이동**. 일부 컴포넌트 스펙(10·11) 본문의 `landing/.../terminal/...` 경로는 stale — 새 SSOT는 `ui/packages/surfaces`. v0.3 워크플로가 토폴로지 코드-그라운드 전수 확정(04 §3). 02 mode enum 본문 통일 완료. 남은 v0.1 잔재: 00(제품명). 상세 = 04 §4.

---

## 버전 정책 + 스위트 버전

문서별 버전이 어긋나 혼란을 막기 위한 단일 규칙:

- **스위트 버전 = `v0.4`**(2026-06-14). 개별 문서 헤더는 그 문서가 마지막으로 *내용 개정*된 시점의 minor를 단다(README/01/02/04/06/08 = v0.4 수준, 03/05/09 = v0.3, 00 = v0.1 본문 + v0.2/v0.4 정정 헤더). 스위트 버전이 정본 — 개별 헤더는 *그 문서가 어디까지 따라왔나*의 표식이다.
- **minor 범프(0.x→0.x+1)** = 코드-그라운드 사실 정정 또는 새 결정이 한 문서 이상에 반영될 때. **patch(문구·오타)** = 헤더 갱신 없이 본문만 수정. **major(1.0)** = 본진 `simulate/` 졸업 + 발간 게이트가 *기계 강제*로 검증된 뒤(현 미충족 → 09 §10 fatal①~④: 발간표면 투자권유 lint[★T1 빌드·배선 완료]·forward-test write 끝단·gate/ledger/admission/lens·US 해금) **+ ⑤ simulate↔leaf 계약 drift 자동인식(`test_simulate_leaf_binding`, 앵커 순방향, 09 §6·P16)** — 엔진 변환 시 simulate silent 깨짐 0 의 5번째 conformance 표면.
- **2층 헤더(v0.1 본문 + v0.2 정정)** = 정정 헤더가 본문보다 우선(00·03). 정정 헤더가 정본, 본문은 미개정 잔재로 읽는다.
- **구현 정합 = 코드가 정본.** 문서 주장이 `src/dartlab/simulate/` 구현과 어긋나면 코드를 정본으로 문서를 고친다(반대 아님). "구현 완료"는 헤더 오버레이가 아니라 본문 텍스트까지 코드와 일치할 때만 ✅.

---

## 정직 척추 (전 문서 관통)

거시·beta·뉴스의 미래는 **예측하지 않고 가정으로 받는다**(scenario ≠ forecast). 회계 항등식(BS 균형·CF 재조정)만 강하게 주장한다. 단일 점추정 금지(fan chart 기본). 결손은 0 대체 금지(missing/blocked/partial 라벨). AI 숫자는 fact 미승격(hypothesis). look-ahead 차단(t종가신호 → t+1시가). 출력에 추천/단정 표현 금지. 본진엔 졸업 게이트 통과 전까지 0줄(시작 = `tests/_attempts/scenarioSimulator/`).
