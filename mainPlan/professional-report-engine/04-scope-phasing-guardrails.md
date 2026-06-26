# 04 · Phase 분해 · 졸업 게이트 · 가드레일 · 결정사항

> operator 확정 순서: **능력 먼저(P1) → 리포트 엔진(P2) → 랜딩 동일소비(P3)**. 각 phase·sub-phase 는 독립 출하·롤백 가능. 각 능력은 졸업 게이트 통과 후 다음.

## P0 · 현상태 publish (선행)

라이브러리 안정화 단계 → 현 안정본 publish 후 착수. 능력 격상은 publish 뒤.

## P1 · 능력 엔진 격상 (SSOT de-gate + 검증)

밸류에이션이 의존 허브이므로 **02a 먼저**. 이후 병렬 가능하나 게이트 순서 유지.

| sub | 엔진 | 산출 | 졸업 게이트 (통과 전 리포트 미탑재) | 롤백 |
|---|---|---|---|---|
| P1a | 밸류에이션 (02a) | de-gate calcDFV·bottom-up WACC 배선·재투자성장·fade·reverse-DCF·가중삼각·`_dFVDrivers.py` | G1 단위항등 + G2 백테스트(20사 t+12M, 방향>55%·중앙오차 무회귀) + G3 민감도 + G5 consistency≥70 | de-gate edit revert(엔진 기존경로 보존) |
| P1b | 전망 (02b) | driver 계단·fade·영업레버리지 마진·`_revenueBacktest.py` | G1 MAPE≤8/15% + G2 방향≥70/60% + G3 밴드커버 + G4 skill>0 | forecast 기존 경로 유지(추가형) |
| P1c | 세그먼트 (02c) | 부문 마진 도출(배분+peer reconcile)·`calcOperatingSegmentSotp` | 공시사 백테스트 MAE≤5%p·커버≥80%·ρ≥0.6 (미통과 시 방향/믹스만) | `marginSource=derived` 플래그 off |
| P1d | 정량 moat (02d) | `analysis/financial/moat.py` 5성분 등급 + `unmeasured[]` | cohort 평균회귀 백테스트(wide vs none, T+3 fade 저항) | 신규 모듈이라 미배선 = 무영향 |
| P1e | 신용 라이브 + 매크로 (02e) | credit→finance.json publish · forward PD lookup · 매크로 분기/다변량/sector 폴백 | credit panel parity(byte동일)+79사 보존 · 매크로 β-stability(sign-flip<20%) | publish 필드 제거(엔진 0-변경) |

**P1a 가 P1d(moat fade)·P1e(Kd)·P1b(ROIC성장)의 선행** — 의존그래프(02 §2).

## P2 · 리포트 엔진 갈아엎기

1. **삭제 ~2,834 LOC**: `story/macro/`(1823)·`publisher.py`(327)·`sixAct.py`(268)·`dashboard.py`(121)·`sections/`(1). (reportTypes/templates 는 死코드 아님 — emitter 가 대체하며 은퇴.)
2. **emitter 신설**: `story/report.py::buildReportModel(company, perspective) -> ReportModel`(TypedDict), L3, self-calc 0, 기존 `builders/` + 격상 능력(02) 조립. `ai/agent.py` 본체 아님.
3. **계약 SSOT**: `ui/packages/contracts/src/reportModel.ts`(기존 `report.ts`/`ReportPort` 충돌 회피한 파일명) — ReportModel + 18블록 + Thesis/ValuationView/ScenarioSet/ForwardView. EvidenceRef·FinCard 재사용.
4. **소비자 마이그레이션**: `Company.report()`·`dartlab report` 추가(기존 `story()` 유지), 테스트 ~277 대부분 무변.

## P3 · 랜딩 동일 소비

1. landing `build.ts` → 같은 `ReportModel` emit(라이브, 브라우저, 베이크 0). 단일 fetch SSOT(`dataCore.requestParquetRows`) 유지.
2. `model.ts` = `reportModel.ts` re-export shim(기존 import 무회귀, 추가형).
3. **drift parity**: 6 상수만 박제(verdict 임계·window guard·peer cut·valuation model-selection·thesis 규율·arc 순서), N=5 회사 ~20 셀 golden-parity, `tests/run.py` 배선. 전체 스냅샷 parity 금지(유지비 폭탄).
4. **UI 게이트**: 푸시 전 스크린샷 전수 눈검수 + 운영자 명시 승인("푸시해"). 5관점·모바일·인쇄·라이트/다크 전수.

## 강행 가드레일

- ⛔ 런타임-SSOT: 베이크 금지. P3 브라우저 직독·parity, 굽지 않음.
- ⛔ no-graph-regression: emitter 는 평범한 함수(`*Loop`/5패스 노드 0), companyStory MCP 부활 금지. `checkAgentBoundary.py`.
- ⛔ find-SSOT-improve: P1 전부 정본 모듈 in-place(병렬빌드 0).
- ⛔ 날조 금지: 모든 추정 = 방법·가정 노출 + 게이트 검증. 미검증 확신 금지.
- ⛔ OOM 가드: 백테스트 module-scope fixture·직렬 load. ⛔ master only·변경단위 commit·UTF-8.
- ⛔ _attempts 졸업: moat(02d)는 `tests/_attempts/quantMoat/` 개념확립 후 `analysis/financial/moat.py` 본진.

## ⚠ 운영자 승인 필요 — 결정사항

1. **신용 prebuild-publish (02e P1)**: dCR 를 `finance.json` 에 임베드하는 경로. 에이전트 논거 = "`macroExposure` 가 *이미* finance.json 에 임베드돼 있다(`buildFinanceJson.py:324`) → 이건 *런타임-SSOT 출력 직렬화*이지 금지된 베이크가 아니다. dCR 은 브라우저에서 산출 불가(Company 객체·BS/IS/CF·sectorThresholds·CHS 필요)." **그러나 런타임-SSOT 강행규칙상 베이크성 작업은 사전 토론·명시 승인 필요** — `macroExposure` 선례가 이미 블레스됐다면 일관, 아니라면 TS 재구현+golden-parity 대안. **운영자 판단 요청.**
2. **순서 확정**: P1(능력)→P2(엔진)→P3(랜딩) — operator 이미 확정. P1 내 02a 선행도 확정.

## 리스크 요약

| 리스크 | 완화 |
|---|---|
| 백테스트 OOM | module-scope fixture·직렬·BoundedCache |
| 격상이 기존 답변 회귀 | de-gate 는 추가형, 기존 경로 G4 무회귀 게이트 |
| credit publish 가 베이크 규칙 위반 | §결정1 운영자 승인 게이트 |
| 두 빌더 drift | 6상수 parity(전체 아님) |
| UI 시각 회귀 | 스크린샷 눈검수 + 운영자 승인 push |
