# Simulate — 미래 리플레이 시뮬레이터 PRD Index

상태: 비전 PRD v0.3 (2026-06-13 — 12-에이전트 워크플로 심화: 지수 차트 완전 명세 + 시뮬 backbone/데이터배선 코드-그라운드 재설계 + 적대검증)
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
- **지수 차트(v0.3)**: 안3(center 탭 주가/지수) + 안4(picker) + CMP. PriceChart `subject` 모드(둘째 차트 0, soft-swap). subject 소유권 = CenterStack-local `$state`(ChartCtl 미상향 — 코드 그라운드 정정). 새 IndexPort(`catalog/search/series`). **★US 지수(SP500/NASDAQ)는 ui 데이터 전무 → KR gov 지수 우선 + US는 운영자 결정(04 §5 OQ12)**. → [06-index-chart.md](06-index-chart.md).
- **통합 시퀀싱**: 지수(1) → 공시 이벤트 레일(2) → 백테스팅 Strategy Tester(3) → 시뮬레이션+Play(4). mainPlan(ui/packages 승격) 이후 착수. 단 지수 차트는 mainPlan 무관 선행 가능. → [07-integration-roadmap.md](07-integration-roadmap.md).
- **착수 전 선결 kill-test**: ★MC 재현성(`_simMonteCarlo.py` 전역 `random.seed` → numpy Generator). Play 결정론·URL 공유·TS 패리티의 척추가 현 코드와 충돌. Phase 0에서 먼저 죽인다.

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
7. [06-index-chart.md](06-index-chart.md) — 지수 차트 v0.3(안3 center 탭 subject-swap + 안4 picker + CMP, IndexPort catalog/search/series, KR gov/indices 105종 OHLCV 완전체, subject 소유권 seam, US 지수 부재 정직 가드).
8. [07-integration-roadmap.md](07-integration-roadmap.md) — 통합 시퀀싱(지수→이벤트레일→백테스팅→시뮬), 공유 DNA, mainPlan 의존, Phase −1~7.

**발간·정합화 (시뮬의 읽기 방식):**
9. [08-valuation-report.md](08-valuation-report.md) — 시뮬레이터=가치평가 엔진 동형, 적정주가(reverseDCF 닻+조건부 범위), 프로급 보고서, 규제선 가드. 발간은 코어 졸업 후.
10. [09-architecture-consolidation.md](09-architecture-consolidation.md) — 시뮬레이터-앵커 부채 원장(DCF 5중·회귀 4중 등 15행)·신용=solvency 뷰·외과 청산 Phase 시퀀스.

**컴포넌트 스펙 (메모리에서 이관):**
11. [10-backtesting-strategy-tester.md](10-backtesting-strategy-tester.md) — 차트 중심 EOD 백테스팅(전 `project_terminal_backtesting_prd`).
12. [11-disclosure-event-rail.md](11-disclosure-event-rail.md) — 공시 위치 찾기 레일(전 `project_terminal_disclosure_event_rail_prd`).

> ⚠ UI 토폴로지: 본 세션 중 터미널이 `landing/src/lib/terminal/` → **`ui/packages/surfaces/src/terminal/`로 이동**. 일부 컴포넌트 스펙(10·11) 본문의 `landing/.../terminal/...` 경로는 stale — 새 SSOT는 `ui/packages/surfaces`. v0.3 워크플로가 토폴로지 코드-그라운드 전수 확정(04 §3). 02 mode enum 본문 통일 완료. 남은 v0.1 잔재: 00(제품명). 상세 = 04 §4.

---

## 정직 척추 (전 문서 관통)

거시·beta·뉴스의 미래는 **예측하지 않고 가정으로 받는다**(scenario ≠ forecast). 회계 항등식(BS 균형·CF 재조정)만 강하게 주장한다. 단일 점추정 금지(fan chart 기본). 결손은 0 대체 금지(missing/blocked/partial 라벨). AI 숫자는 fact 미승격(hypothesis). look-ahead 차단(t종가신호 → t+1시가). 출력에 추천/단정 표현 금지. 본진엔 졸업 게이트 통과 전까지 0줄(시작 = `tests/_attempts/scenarioSimulator/`).
