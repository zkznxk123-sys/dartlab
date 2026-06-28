# 06 · 진행 원장

> 표기: ☐ 대기 · ◐ 진행 · ✅ 완료 · ⚠ 차단(결정 대기). 완료 시 게이트 결과 한 줄 동행.

## 기획 (조사·플랜)

- ✅ 현상태 매핑 (두 시스템·story 군더더기·소비 그래프) — `01`
- ✅ 전문 리포트 PRD (인과 아크·thesis 규율·밸류·신용·서사 문법) — `00`
- ✅ 능력 엔진 6 SSOT 조사 (de-gate 발견) — `02a~02e`
- ✅ 리포트 엔진 아키텍처 (계약 SSOT·delete ~2,834·emitter) — `03`
- ✅ Phase 분해·게이트·가드 — `04`
- ✅ 운영자 결정: 신용 prebuild-publish **조건부 승인** (§04 결정1) — 코드검증(브라우저 산출불가·TS재구현=관리불능) + 5가드(단일경로·단일소스·정의스키마·빌드비용·offline)

## P0 · publish
- ☐ 현 안정본 publish

## P1 · 능력 격상 (순서: 02a 선행)
- ◐ P1a 밸류에이션 de-gate + WACC/성장/fade/reverse — 게이트 G1·G2(백테스트)·G3·G5
  - ✅ **G1·G3·G5 offline 통과** (`tests/quant/test_valuationUplift.py` **9개**, test-lock): G1 reinvest round-trip·fade 단조수렴·terminal 무료성장 차단·reverse-DCF 항등(오차 0%) · G3 WACC×g 민감도 단조성(WACC↑→가치↓·g↑→가치↑)+TVshare 폭주 차단 · G5 Growth Equation 정합성(g=reinvest×ROIC critical 0, 위반 입력 감점).
  - ✅ **본진 디게이트 완료**: `_estimateWacc` bottom-up β + Damodaran 국가테이블(005930 실측 8.72) · `_calcTwoStageDcf` 펀더멘털 성장(g=reinvest×ROIC fade, naive 매출CAGR 대체) · 신규 `_dFVDrivers.py`(buildReinvestmentPath·buildDriverScenarios·reverseDcfExhibit) · `dFV` ±0.12→드라이버 시나리오 + reverseDcf·reinvestmentCheck 출력(guarded).
  - ✅ **DCF de-gate 실데이터 검증**(005930 offline 결정론): fundG 8.91%(reinvest 0.9×ROIC 9.9) < naive · new DCF < old(과대 해소) · **TVshare 0.78→0.67**(터미널 의존 감소). camelCase·docstring·ruff·import 전부 clean.
  - 🔧 **정공법 결정 2건**: ① `multiStageDcf` 재투자 FCFF *미적용* — `baseFcf` 가 이미 FCF(OCF−capex)라 거기서 또 빼면 이중계산. 성장 path 로 교정(02a §4.2 보다 정확). ② credit→Kd 스프레드(02a §4.4) = P1e 신용배선으로 이관(Fernandez 이중계산 회피 + 신용 SSOT 동시).
  - ✅ **calcDFV 통합 검증**(close→no-op monkeypatch 우회 스모크 `tests/_attempts/valuationUplift/smoke_calcdfv.py`): 크래시 0 · reinvestmentCheck 정상 배선(005930 fundG=8.91·reinvest 0.9·wacc 8.72, offline 검증과 일치) · driverScenarios 활성(NAVER dcf2stage bull558k/base392k/bear295k) · 시장가 결측 시 liquidation graceful 폴백. **배선·무크래시·재투자 로직 실데이터 확정.** 통합 게이트 `tests/quant/test_valuationUpliftIntegration.py`(requires_data) 박제 — CI 영속컨텍스트 실행.
  - ✅ **push 완료** (`518b4e370`, master). 로컬 전 게이트 통과 — ruff·camelCase·docstring·import 신규위반 0(census baseline-diff, 위반은 전부 기존 quant→gather 부채)·offline 9 테스트·통합 무크래시. CI-fast(offline) green.
  - ☐ **남은 = *올바른* 시장데이터 환경 후속(데이터 벽, 실측 확인)**: 샌드박스 가격이 부재가 아니라 **오염**(30일 stale + 틀림 — 삼성 339,500/실제~75k, 하이닉스 2,673,000/실제~200k) → G2/범위가드를 여기서 돌리면 거짓 결과. 따라서 ① **G2 백테스트(20사 t+12M, 02a §5)** ② **`test_damodaranPhase4.py` 범위가드 데이터잡 무회귀/재baseline** = CI 데이터잡(신선 HF)·production 필요. G4 calcValuationSynthesis = 내 변경 무영향(독자 WACC 경로).
  - 🔎 **stress-test 발견(P1b 전 처리 권장)**: 고-ROIC 사이클 peak 종목에서 펀더멘털 성장 과공격적 — 하이닉스 ROIC 31%(HBM boom) → fundG 28% → dcf2stage 897k 과대. 처방 = **through-cycle ROIC 정규화**(현 `_tsdMaybeNormalizeFcf` 의 FCF 정규화와 정합 — 현재 base FCF 는 정규화하나 성장 anchor ROIC 는 latest peak 사용 = 불일치). ⚠ 올바른 데이터 없이 정규화 변경 = 미검증 회귀라 보류, G2(신선데이터)로 측정 후 적용. buildReinvestmentPath roicAnchor: latest → median(through-cycle) 후보.
- ☐ P1b 전망 driver + `_revenueBacktest.py` — 게이트 MAPE·방향·밴드·skill
- ☐ P1c 세그먼트 마진 도출 + SOTP — 게이트 MAE≤5%p·커버·ρ
- ☐ P1d 정량 moat(`_attempts/quantMoat` → `moat.py`) — 게이트 cohort 평균회귀
- ☐ P1e 신용 라이브배선 + 매크로 강화 — 게이트 parity·79사·β-stability (결정1 ✅ 조건부, 5가드 준수)

## P2 · 리포트 엔진
- ☐ 삭제 ~2,834 LOC (`story/macro`·publisher·sixAct·dashboard·sections)
- ☐ `reportModel.ts` 계약 + 18블록
- ☐ `story/report.py::buildReportModel` emitter
- ☐ 소비자 마이그레이션 (CLI·테스트·storyTemplate)

## P3 · 랜딩 동일소비
- ☐ `build.ts` → ReportModel emit (베이크 0)
- ☐ `model.ts` re-export shim
- ☐ 6상수 golden-parity (N=5, ~20셀)
- ☐ UI 스크린샷 눈검수 + 운영자 승인 push

## 결정·이벤트 로그
- 2026-06-26 착수. operator 사상 확정: 정직-스킵=무능, 능력부족은 SSOT 찾아 개선, 날조만 금지. 순서 = 능력 먼저. 기획 7+5문서 박제.
- 2026-06-26 신용 publish 조건부 승인 ("반드시 필요하면 허용, 단 덕지덕지·관리불능 금지"). 코드검증 후 5가드 박제 → 착수 unblocked.
