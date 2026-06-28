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
  - ☐ **push 게이트(네트워크/CI 환경 필요)**: 샌드박스 calcDFV end-to-end 불가(credit/CHS·consensus fetch httpx 클라이언트-closed). 푸시 전 영속루프 환경에서: ① calcDFV 실행해 신규 dFV 값 확인 ② **`tests/quant/test_damodaranPhase4.py` requires_data 범위 가드(삼성 140k–230k 등) 무회귀 확인/필요시 정정**(de-gate 가 의도적으로 값 이동) ③ G2 백테스트(20사 t+12M) ④ G4 calcValuationSynthesis sanity(내 변경 무영향 — 독자 computeCompanyWacc 경로, 확인용). G4 sanity 는 영향 없음(calcValuationSynthesis ⊥ 내 calcDFV 경로). 커밋은 완료(로컬 게이트 7+import+ruff+camelCase+docstring clean), **push 보류**.
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
