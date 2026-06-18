# 매크로 렌즈 다이얼로그

상태: 구현 v1.9 (2026-06-19, Phase 1~4 완료 · 대시보드 시각화 방식 v0.6 반영 · `macro.transmission` 터미널 배선 · 회사 macroExposure 품질 UI 소비 · matrix drilldown 패킷 · Release/Source/Evidence Contribution 시각화 · 관측점 기반 co-movement scatter · 모바일 드릴다운 포커스 보강 · Sources 탭 Quality Gate/Model Card 구현 · macroExposure 모델 명세 계약 · Macro Verdict Engine/UI · keyboard/focus shell)
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
9. [08-dashboard-visual-patterns.md](08-dashboard-visual-patterns.md) — 공식 매크로 대시보드 조사, 시각화 방식 카탈로그, 첫 화면 채택·금지 규칙.

---

## 핵심 결정

- 사용자가 보는 거처는 `ui/packages/surfaces/src/terminal`의 다이얼로그다. 새 라우트·상주 패널·차트 복제는 없다.
- 분석 코어는 `Macro Driver → Transmission Edge → Company Exposure → Financial Checkpoint → Valuation Lever → Falsifier` 사슬이다.
- `macro` 개선은 허용한다. 단, `macro.transmission`은 시장·섹터 레벨 산출물만 만들고 회사/analysis 내부를 import하지 않는다.
- 회사별 민감도는 기존 analysis macro 표면을 확장해 연결한다. public 터미널은 새 per-company artifact 없이 `dashboards/finance.json`의 회사 엔트리에 포함된 `macroExposure.exposureQuality`를 소비한다. `nObs`, `rSquared`, `lag`, `window`, `coverage`, `sourceRef`가 없으면 deep block을 닫는다.
- 첫 화면 구현은 기존 산출물 재사용이다: `dashboards/macro.json`, `macro/{fred,ecos}/observations.parquet`, `MACRO_SERIES`, `co.tailwind`, `eng.sectorTailwinds()`, 차트 co-movement.
- 첫 화면은 `판정` 콘솔이다. `Macro Verdict Hero`가 점수·claim level·핵심 경로·다음 행동을 먼저 보여주고, 바로 아래 `Verdict Engine Rail`이 변화/경로/신선도/섹터/회사/동행 게이트 중 어디가 열리고 막혔는지 보여준다. 기존 phase/pulse/matrix/release rail은 보조 증거로 유지하되, matrix와 release rail은 접힌 상세 영역으로 내린다.
- 시각화는 판정을 만들지 않는다. verdict score와 `LOCK/OPEN/WATCH` 상태는 `macro.transmission`, `macroExposure.exposureQuality`, source lineage, freshness policy, co-movement gate를 `buildMacroVerdict()`가 구조화한 결과다. UI는 이 결과를 표시할 뿐 재계산하거나 추천·목표가로 승격하지 않는다.
- `Release Rail`, 구조화된 `Source Packet`, `Evidence Contribution`, `Co-movement Gate`는 유효한 driver focus 하나에 동기화한다. 외부에서 `KR` 같은 market-level focus가 들어오면 driver로 간주하지 않고 기본 driver로 회수한다. `Evidence Contribution`은 `최근 변화/전파 경로/동행 후보/신선도/회사 품질`의 근거 개방도를 보여주는 분해 렌즈이며 재무 기여도나 합산 점수가 아니다. `Co-movement Gate`는 원시 월별 관측점이 있으면 `macro 월말 1차차분 × 종목 월수익률` 산점도를 그리고, 없을 때만 corr 위치 gate로 fallback한다. 산점도는 beta·회귀선·인과 증명이 아니라 동행 후보의 표본 모양을 보는 반증 도구다.
- `출처·한계` 탭은 출처 문자열 목록이 아니라 `Quality Gate`, `Model Card`, `Missing Ledger`, `Falsifier Strip`, `Release freshness` 순서의 품질 패널이다. `Quality Gate`는 `OPEN/QUAL/LOCK` 상태와 `method/modelVersion/targetMetric/minObs/nObs/R²/window/frequency/lag/coverage/sourceRef`를 한 화면에 묶고, `Model Card`는 `exposureIndicators`를 회사별 macroExposure 지표 후보로만 표시한다. UI는 회귀를 재계산하지 않으며 예측 모델·목표가·추천으로 읽히는 문구를 쓰지 않는다.
- 모바일에서는 matrix의 작은 셀을 주 터치 경로로 쓰지 않는다. `대시보드` 아래 `Mobile Drill Rail` 6개 버튼이 `전파 지도` drilldown과 같은 focus 계약을 사용하며, matrix는 세부 표로 유지한다.
- 엔진 강화는 `tests/_attempts/macroLensEngine/` proof를 거쳐 `macro.transmission` 최소 축까지 `src/dartlab/macro`에 승격했다. 회사별 `analysis.macroExposure`는 `method/modelVersion/targetMetric/minObs/nObs/R²/window/lag/coverage/sourceRef` 품질 계약을 내며, Macro Lens는 이 값을 우선 소비하고 없을 때만 fallback 잠금 상태를 표시한다.
- 매수/매도, 목표주가, 위기 임박, 수혜 확정 표현은 금지한다.
- public/local 공통배선이 기본이다. 로컬 백엔드 없이 퍼블릭 데이터만으로 떠야 한다.
