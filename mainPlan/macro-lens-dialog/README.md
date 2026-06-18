# 매크로 렌즈 다이얼로그

상태: 구현 v1.12 (2026-06-19, Phase 1~4 완료 · 대시보드 시각화 방식 v0.6 반영 · `macro.transmission` 터미널 배선 · 회사 macroExposure 품질 UI 소비 · matrix drilldown 패킷 · Release/Source/Evidence Contribution 시각화 · 관측점 기반 co-movement scatter · 모바일 드릴다운 포커스 보강 · Sources 탭 Quality Gate/Model Card 구현 · macroExposure 모델 명세 계약 · Macro Verdict Engine/UI · keyboard/focus shell · Command Bar/Evidence Cockpit · hard-lock verdict guards · Direction Contest/A-B Matrix/Action Queue · direction/evidence score split · driver-local kill-chain · flip test)
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
- 첫 화면은 `판정 보드`도 더 압축한다. 사용자가 바로 보는 것은 `방향 점수(directionScore) / 근거 신뢰(evidenceScore)`, 핵심 경로, driver-local `반증 체인`, `flip test`, 다음 행동뿐이다.
- `driver-local kill-chain`은 `관측값 -> 전파 edge -> 회사 증거 -> 반증 조건 -> 재확인` 5단계다. `macro.transmission.edges[*].falsifiers`를 view-model에서 보존하고, 없으면 회사 증거·동행상관 gate가 결론을 어디서 잠그는지 보여준다.
- `Direction Contest`, `A/B 비교`, `Verdict Engine Rail`, `Evidence Cockpit`, phase/pulse는 첫 화면에서 접힌 `상세 검산`으로 이동했다. 강함은 정보량이 아니라 결론을 공격하는 경로가 먼저 보이는 데서 나온다.
- `Action Queue`는 설명 문장이 아니라 클릭 가능한 작업 목록이다. 첫 화면에서는 kill-chain의 다음 한두 수만 보이고, 나머지 hard lock 복구, 회사 claim 잠금, 전파 경로 검증, 반증 확인은 상세 검산과 해당 탭/driver로 이어진다.
- `buildMacroVerdict()`는 driver를 먼저 자르지 않고 evidence를 붙인 뒤 랭킹한다. template path는 0.42, sectorPrior는 0.68, missing/blocked path는 0.22로 rank cap을 받아 관측 경로를 단순 변화량만으로 이기지 못한다.
- `buildMacroVerdict()`는 호환용 `score`와 별개로 signed `directionScore`(-100~100)와 `evidenceScore`(0~100)를 분리한다. 방향 라벨은 `directionScore`로, claim ceiling은 hard lock/evidence/coverage gate로 제한한다.
- `Flip Test`는 단순 spread 문구가 아니다. hard lock이면 숫자를 만들지 않고, 열려 있을 때만 challenger가 leader를 뒤집는 데 필요한 점수차와 첫 kill switch를 함께 보여준다.
- 시각화는 판정을 만들지 않는다. verdict score와 `LOCK/OPEN/WATCH` 상태는 `macro.transmission`, `macroExposure.exposureQuality`, source lineage, freshness policy, co-movement gate를 `buildMacroVerdict()`가 구조화한 결과다. UI는 이 결과를 표시할 뿐 재계산하거나 추천·목표가로 승격하지 않는다.
- hard-lock 가드는 보수적으로 동작한다. 핵심 primary driver stale, `macro.transmission` 결손/fallback template, 불완전한 `quantCandidate`, 변화 0의 polarity 오독은 정량·회사 claim을 열지 않는다. `locked` verdict는 점수도 잠금 영역으로 제한한다.
- `Release Rail`, 구조화된 `Source Packet`, `Evidence Contribution`, `Co-movement Gate`는 유효한 driver focus 하나에 동기화한다. 외부에서 `KR` 같은 market-level focus가 들어오면 driver로 간주하지 않고 기본 driver로 회수한다. `Evidence Contribution`은 `최근 변화/전파 경로/동행 후보/신선도/회사 품질`의 근거 개방도를 보여주는 분해 렌즈이며 재무 기여도나 합산 점수가 아니다. `Co-movement Gate`는 원시 월별 관측점이 있으면 `macro 월말 1차차분 × 종목 월수익률` 산점도를 그리고, 없을 때만 corr 위치 gate로 fallback한다. 산점도는 beta·회귀선·인과 증명이 아니라 동행 후보의 표본 모양을 보는 반증 도구다.
- `출처·한계` 탭은 출처 문자열 목록이 아니라 `Quality Gate`, `Model Card`, `Missing Ledger`, `Falsifier Strip`, `Release freshness` 순서의 품질 패널이다. `Quality Gate`는 `OPEN/QUAL/LOCK` 상태와 `method/modelVersion/targetMetric/minObs/nObs/R²/window/frequency/lag/coverage/sourceRef`를 한 화면에 묶고, `Model Card`는 `exposureIndicators`를 회사별 macroExposure 지표 후보로만 표시한다. UI는 회귀를 재계산하지 않으며 예측 모델·목표가·추천으로 읽히는 문구를 쓰지 않는다.
- 모바일에서는 matrix의 작은 셀을 주 터치 경로로 쓰지 않는다. `대시보드` 아래 `Mobile Drill Rail` 6개 버튼이 `전파 지도` drilldown과 같은 focus 계약을 사용하며, matrix는 세부 표로 유지한다.
- 엔진 강화는 `tests/_attempts/macroLensEngine/` proof를 거쳐 `macro.transmission` 최소 축까지 `src/dartlab/macro`에 승격했다. 회사별 `analysis.macroExposure`는 `method/modelVersion/targetMetric/minObs/nObs/R²/window/lag/coverage/sourceRef` 품질 계약을 내며, Macro Lens는 이 값을 우선 소비하고 없을 때만 fallback 잠금 상태를 표시한다.
- 매수/매도, 목표주가, 위기 임박, 수혜 확정 표현은 금지한다.
- public/local 공통배선이 기본이다. 로컬 백엔드 없이 퍼블릭 데이터만으로 떠야 한다.
