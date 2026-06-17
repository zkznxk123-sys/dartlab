# 매크로 렌즈 다이얼로그

상태: 비전 PRD v0.1 (2026-06-17, 전문 관점 토론 반영)
범위: 퍼블릭 터미널에 이미 있는 매크로 엔진 산출물을 심층 분석 다이얼로그로 녹인다. 새 L2 엔진이 아니라 `dartlab.macro` + 회사 분석 + 터미널 차트 자산을 하나의 전파 사슬로 묶는 제품 기획이다.

---

## 한 줄 결론

**`경제지표분석`을 지표 목록에서 `Macro Lens`로 승격한다.** 사용자가 보는 질문은 "금리·환율·물가가 얼마인가"가 아니라 **"지금 매크로 국면이 이 종목의 섹터, 손익, 현금흐름, 밸류에이션에 어떤 경로로 닿을 수 있는가"** 다. 따라서 상주 패널을 늘리지 않고, 좌측 마켓 펄스·상단 KPI 티커·차트 ECON 오버레이를 입구로 쓰는 **하나의 심층 다이얼로그**를 만든다.

---

## 문서 지도

1. [00-current-state-and-roi.md](00-current-state-and-roi.md) — 현 자산, 빈틈, ROI, 전문 관점 토론 결론.
2. [01-product-prd.md](01-product-prd.md) — 제품 비전, 사용자 질문, 다이얼로그 정보 구조.
3. [02-data-contract.md](02-data-contract.md) — 재사용 데이터, `MacroLensSnapshot` 계약, 결손·출처 규칙.
4. [03-target-architecture.md](03-target-architecture.md) — 터미널 배치, 런타임 공통배선, 엔진 경계.
5. [04-scope-phasing-guardrails.md](04-scope-phasing-guardrails.md) — Phase, MUST/SHOULD/WON'T, 정직 가드.
6. [05-validation-and-risk.md](05-validation-and-risk.md) — 검증, 테스트, 롤백, 리스크.
7. [06-progress-ledger.md](06-progress-ledger.md) — 결정 기록과 NEXT.

---

## 핵심 결정

- 거처는 `ui/packages/surfaces/src/terminal`의 다이얼로그다. 새 라우트·상주 패널·차트 복제는 없다.
- 첫 구현은 기존 산출물 재사용이다: `dashboards/macro.json`, `macro/{fred,ecos}/observations.parquet`, `MACRO_SERIES`, `co.tailwind`, `eng.sectorTailwinds()`, 차트 co-movement.
- 강한 분석의 중심은 `Macro → Sector → Company → Financial → Valuation` 전파 사슬이다.
- `analysis.macroSensitivity`와 `calcMacroRegression`은 심층화 후보지만, 퍼블릭 floor에서는 결손·신뢰도 라벨 없이 단정하지 않는다.
- 매수/매도, 목표주가, 위기 임박, 수혜 확정 표현은 금지한다.
- public/local 공통배선이 기본이다. 로컬 백엔드 없이 퍼블릭 데이터만으로 떠야 한다.

