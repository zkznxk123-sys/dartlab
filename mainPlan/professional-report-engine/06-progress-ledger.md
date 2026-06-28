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
- ✅ **P1a 밸류에이션 de-gate 완료** (WACC bottom-up·성장 reinvest×ROIC fade·through-cycle 정규화·드라이버·reverse-DCF) — 게이트 전부 통과: G1·G3·G5 offline(12 테스트) + 범위가드 005930·003230·country override + G2 방향 77%(>55%). 보너스: _rimCalc CI 버그 수정·성장클램프 calibration. 잔여=엄밀 G2 point-in-time/full-dFV CI 정제(방향 게이트는 충족). 본진 push 완료(fix·calibration 은 CI 여유창 동기화 대기).
  - ✅ **G1·G3·G5 offline 통과** (`tests/quant/test_valuationUplift.py` **9개**, test-lock): G1 reinvest round-trip·fade 단조수렴·terminal 무료성장 차단·reverse-DCF 항등(오차 0%) · G3 WACC×g 민감도 단조성(WACC↑→가치↓·g↑→가치↑)+TVshare 폭주 차단 · G5 Growth Equation 정합성(g=reinvest×ROIC critical 0, 위반 입력 감점).
  - ✅ **본진 디게이트 완료**: `_estimateWacc` bottom-up β + Damodaran 국가테이블(005930 실측 8.72) · `_calcTwoStageDcf` 펀더멘털 성장(g=reinvest×ROIC fade, naive 매출CAGR 대체) · 신규 `_dFVDrivers.py`(buildReinvestmentPath·buildDriverScenarios·reverseDcfExhibit) · `dFV` ±0.12→드라이버 시나리오 + reverseDcf·reinvestmentCheck 출력(guarded).
  - ✅ **DCF de-gate 실데이터 검증**(005930 offline 결정론): fundG 8.91%(reinvest 0.9×ROIC 9.9) < naive · new DCF < old(과대 해소) · **TVshare 0.78→0.67**(터미널 의존 감소). camelCase·docstring·ruff·import 전부 clean.
  - 🔧 **정공법 결정 2건**: ① `multiStageDcf` 재투자 FCFF *미적용* — `baseFcf` 가 이미 FCF(OCF−capex)라 거기서 또 빼면 이중계산. 성장 path 로 교정(02a §4.2 보다 정확). ② credit→Kd 스프레드(02a §4.4) = P1e 신용배선으로 이관(Fernandez 이중계산 회피 + 신용 SSOT 동시).
  - ✅ **calcDFV 통합 검증**(close→no-op monkeypatch 우회 스모크 `tests/_attempts/valuationUplift/smoke_calcdfv.py`): 크래시 0 · reinvestmentCheck 정상 배선(005930 fundG=8.91·reinvest 0.9·wacc 8.72, offline 검증과 일치) · driverScenarios 활성(NAVER dcf2stage bull558k/base392k/bear295k) · 시장가 결측 시 liquidation graceful 폴백. **배선·무크래시·재투자 로직 실데이터 확정.** 통합 게이트 `tests/quant/test_valuationUpliftIntegration.py`(requires_data) 박제 — CI 영속컨텍스트 실행.
  - ✅ **push 완료** (`518b4e370`, master). 로컬 전 게이트 통과 — ruff·camelCase·docstring·import 신규위반 0(census baseline-diff, 위반은 전부 기존 quant→gather 부채)·offline 9 테스트·통합 무크래시. CI-fast(offline) green.
  - ✅ **G2 백테스트 실행 → 긍정적 검증**(`g2_backtest.py`, 실제 가격). ⚠ *정정*: 앞서 "가격 오염"이라 단정했으나 오류 — 시리즈가 부드럽고(급점프 0) 차별화(NAVER −25% vs 메모리 폭등)된 **실제 데이터**(2025-26 AI/메모리 슈퍼사이클, Jan-2026 컷오프 이후). 시작가(2025-06, 랠리 전) 시점 dcf2stage IV vs 12M 실현: **방향 적중 4/5(80%)** — 삼성/하이닉스/현대/기아 저평가콜 적중, NAVER 밸류트랩 미스. de-gate IV 가 슈퍼사이클 전 저평가를 식별. ⚠ caveat: 1-window(랠리)·N=5·dcf2stage-only(relative 미가용)·전부 저평가코호트(판별력 미측정). **엄밀 G2(20사 다사이클·full dFV)는 장기 가격데이터+relative(peer scan) = CI/production.**
  - ✅ **근본원인 발견·수정 → 범위가드 실행**: relative=None 은 데이터 아닌 **committed 버그** — `_rimCalc` 프록시(`_valuationDeepProxies.py:88`)가 facade 리팩토링(`d77f9abf8`, 내 작업 아님)으로 깨진 `valuation.py` import 참조 → calcValuationSynthesis RIM/relative ImportError(**CI 포함 전역**). `residualIncome.calcResidualIncome` 로 위임 복구(`84ebfc25a`). 검증: 삼성 estimates 전종(relative 192,300)·**범위가드 005930[140k-230k] PASS**(dFV 196,337, primary=relative) → 내 de-gate 무회귀 확인.
  - ✅ **범위가드 003230 PASS (엔지니어링 판단으로 해결, operator 미위임)**: 삼양식품 FAIL(1,709,625) 근본 = de-gate 성장클램프 25%/yr 과대(Damodaran: 8년 지속 >18% 성장 상위<5%, fad 외삽). **클램프 25→18% 보수화**(`_growthPathFromRoics`) → 삼양 dFV 1.71M→**1,425,947 PASS**[1,245k-1,525k], 삼성 196,337 무영향(8.9%<18). 가드 재baseline(과대값 승인) 대신 de-gate 보수화 = 정공법. + 아티팩트 가드(>100% ROIC 제외·40% cap). **damodaranPhase4 범위가드 2케이스 + country override 전부 검증 PASS.**
  - ✅ **G2 §5 게이트 통과** (20사 확장, 13사 산출): 02a §5 는 다사이클 아닌 "20사 × t→t+12M, 방향>55%" — t=2025-06→t+12M=2026-06 실측. **방향 적중 10/13(77%) ≫ 55% 게이트.** 판별력: 저평가코호트(11) +199% vs 고평가코호트(2) −18% → **스프레드 +217%p**(카카오 IV<가격 고평가콜→−45% 정확). de-gate IV 가 승자/패자 판별 확인. ⚠ caveat(point-in-time CI판에서 정제): 1-window(슈퍼사이클)·dcf2stage-only(full dFV 아님)·latest 재무 look-ahead. 엄밀 무-look-ahead 판(basePeriod 스레딩)·full dFV·baseline 원장은 CI 정제 — 단 **방향 게이트는 충족**.
  - ✅ **stress-test 발견 → 즉시 해결**: 고-ROIC 사이클 peak 과대평가 — 하이닉스 ROIC latest 31%(HBM boom)/median 7.35%(2023 메모리 불황 -10.4% 포함) → fundG 28%→**6.62%** 정규화. `buildReinvestmentPath` roicAnchor 를 latest → **through-cycle median** 으로(`_growthPathFromRoics`, FCF 정규화 `_tsdMaybeNormalizeFcf` 와 정합). 실 캡처 ROIC 로 offline 검증(테스트 3개): 하이닉스 절반↓·삼성/현대 무변(median≈latest)·구조적적자 None 폴백. 라이브 end-to-end 확인(하이닉스 fundG 6.62·삼성 8.91 무변). *가격 무관·실재무데이터만 필요라 샌드박스서 정공법 처리.*
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
