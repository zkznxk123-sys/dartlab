# 매크로 렌즈 다이얼로그

상태: 구현 v0.3 (2026-06-18, Phase 1~4 완료 · src 승격 대기)
범위: 퍼블릭 터미널의 `경제지표분석`을 Macro Lens 분석 코어로 승격한다. 화면은 다이얼로그지만, 핵심은 `dartlab.macro`의 시장·섹터 전파 산출물과 `analysis`의 회사 노출 품질을 하나의 검증 가능한 전파 사슬로 묶는 것이다.

---

## 한 줄 결론

**`경제지표분석`을 지표 목록에서 `Macro Lens` 분석 조종석으로 승격한다.** 사용자가 보는 질문은 "금리·환율·물가가 얼마인가"가 아니라 **"지금 매크로 국면이 어떤 driver를 통해 섹터, 회사 손익, 현금흐름, 밸류에이션에 닿고, 그 연결을 무엇으로 반증할 수 있는가"** 다. 따라서 상주 패널을 늘리지 않고, 좌측 마켓 펄스·상단 KPI 티커·차트 ECON 오버레이를 입구로 쓰는 **하나의 심층 다이얼로그**를 만든다. 단, 강한 분석의 본체는 UI가 아니라 `macro.transmission`과 기존 analysis macro 표면의 회사 노출·품질 산출물이다.

---

## 문서 지도

1. [00-current-state-and-roi.md](00-current-state-and-roi.md) — 현 자산, 빈틈, ROI, 전문 관점 토론 결론.
2. [01-product-prd.md](01-product-prd.md) — 제품 비전, 사용자 질문, 다이얼로그 정보 구조.
3. [02-data-contract.md](02-data-contract.md) — 재사용 데이터, `MacroLensSnapshot` 계약, 결손·출처 규칙.
4. [03-target-architecture.md](03-target-architecture.md) — 터미널 배치, 런타임 공통배선, 엔진 경계.
5. [04-scope-phasing-guardrails.md](04-scope-phasing-guardrails.md) — Phase, MUST/SHOULD/WON'T, 정직 가드.
6. [05-validation-and-risk.md](05-validation-and-risk.md) — 검증, 테스트, 롤백, 리스크.
7. [06-progress-ledger.md](06-progress-ledger.md) — 결정 기록과 NEXT.
8. [07-macro-engine-upgrade.md](07-macro-engine-upgrade.md) — 매크로 엔진 강화 트랙, 산출물, graduation gate.

---

## 핵심 결정

- 사용자가 보는 거처는 `ui/packages/surfaces/src/terminal`의 다이얼로그다. 새 라우트·상주 패널·차트 복제는 없다.
- 분석 코어는 `Macro Driver → Transmission Edge → Company Exposure → Financial Checkpoint → Valuation Lever → Falsifier` 사슬이다.
- `macro` 개선은 허용한다. 단, `macro.transmission`은 시장·섹터 레벨 산출물만 만들고 회사/analysis 내부를 import하지 않는다.
- 회사별 민감도는 기존 `Company.analysis("macro", "매크로민감도")` 계열을 확장해 연결한다. 내부 산출명은 `analysis.macroExposure` 후보로 둘 수 있지만, `nObs`, `rSquared`, `lag`, `window`, `coverage`, `sourceRef`가 없으면 deep block을 닫는다.
- 첫 화면 구현은 기존 산출물 재사용이다: `dashboards/macro.json`, `macro/{fred,ecos}/observations.parquet`, `MACRO_SERIES`, `co.tailwind`, `eng.sectorTailwinds()`, 차트 co-movement.
- 엔진 강화는 `tests/_attempts/macroLensEngine/` proof까지 완료했다. `src/dartlab` 승격은 별도 단계로 진행한다.
- 매수/매도, 목표주가, 위기 임박, 수혜 확정 표현은 금지한다.
- public/local 공통배선이 기본이다. 로컬 백엔드 없이 퍼블릭 데이터만으로 떠야 한다.
