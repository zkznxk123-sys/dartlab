# 03. 목표 아키텍처

상태: 설계 v0.2
범위: 다이얼로그 거처, 데이터 흐름, 엔진 경계.

---

## 1. 거처

Macro Lens의 사용 표면은 터미널 다이얼로그다. 분석 본체는 `macro.transmission`과 기존 analysis macro 표면의 공개 산출물을 합친 view-model이다.

권장 파일:

```text
ui/packages/surfaces/src/terminal/panels/MacroLensDialog.svelte
ui/packages/surfaces/src/terminal/lib/macroLens.ts
```

진입 배선 후보:

```text
ui/packages/surfaces/src/terminal/panels/LeftRail.svelte
ui/packages/surfaces/src/terminal/panels/CenterStack.svelte
ui/packages/surfaces/src/terminal/charts/ChartMenus.svelte
ui/packages/surfaces/src/terminal/charts/ChartRibbon.svelte
ui/packages/surfaces/src/terminal/TerminalSurface.svelte
```

CSS는 기존 `terminal.css`의 다이얼로그/패널 톤을 재사용한다. 새 상주 column, 새 route, 새 chart instance는 만들지 않는다.

---

## 2. 표면 배치 원칙

| 영역 | 남길 것 | 다이얼로그로 보낼 것 |
|---|---|---|
| 좌측 마켓 펄스 | KR/US 국면, 순풍/역풍 섹터, 섹터 필터 | 왜 그런 국면인지, 해당 섹터 영향 근거 |
| 상단 KPI ticker | 최신값·스파크라인·클릭 입구 | 지표 그룹 표, 기준일, 출처 |
| 중앙 PriceChart | ECON 오버레이, 최대 3개, co-movement 표시 | 오버레이 해석, 반증 조건 |
| 우측 Stack | 공시·뉴스·재무표·리스크 근거 | 매크로 장문 리포트 금지 |

다이얼로그는 기존 화면을 대체하지 않고, "왜"와 "어디까지 믿을 수 있는가"를 설명하는 분석 조종석이다.

---

## 3. 데이터 흐름

```text
HF macro artifacts
  ├─ dashboards/macro.json
  └─ macro/{fred,ecos}/observations.parquet
        ↓
ui runtime DataCore request()
        ↓
MacroPort + routeLoad raw macro
        ↓
terminal Engine + Company + ChartCtl
        ↓
macroLens.ts view-model
        ↓
MacroLensDialog.svelte
```

규칙:

- 모든 데이터 호출은 `ui/packages/runtime/src/data/fetch` 진입점을 통과한다.
- 새 source에서 raw `fetch`, 직접 HF URL, 자체 `Map` 캐시를 만들지 않는다.
- local runtime도 기본은 `createHfMacroPort(dataCore)`를 재사용한다.
- 로컬 `:8400` 백엔드 없이 다이얼로그 기본 기능이 떠야 한다.

---

## 4. 엔진 경계

### Phase A — UI view-model

- Python 엔진을 새로 부르지 않는다.
- `src/dartlab/macro` 내부 함수 import 없음.
- `src/dartlab/analysis` 내부 함수 import 없음.
- 터미널이 이미 가진 JSON/parquet/runtime 산출물로 view-model을 만든다.

### Phase B — `macro.transmission`

매크로 엔진 개선이 필요하면 새 독립 엔진을 만들지 않고 기존 `src/dartlab/macro`의 공개 축으로 추가한다.

허용:

- `driver registry`: canonical id, source series, 방향성 의미, default lag.
- `transmission edge`: driver → market/sector/industry → financial line → valuation lever.
- `regime evidence`: 국면 판단 근거와 기준일.
- `source/date/value` lineage.

금지:

- 회사 객체 import.
- `src/dartlab/analysis` 내부 함수 호출.
- 종목별 추천/수혜/피해 산출.
- per-company artifact 생성.

### Phase C — analysis macro exposure quality

회사별 연결은 기존 `Company.analysis("macro", "매크로민감도")` 계열의 analysis 공개 surface가 맡는다. `analysis.macroExposure`는 내부 산출명 또는 alias 후보일 뿐 새 사용자 호출로 바로 노출하지 않는다.

- 회사별 `calcMacroSensitivity`/`calcMacroRegression`을 제품화하려면 공개 surface를 경유해야 한다.
- 필수 품질 라벨은 `nObs`, `rSquared`, `window`, `frequency`, `lag`, `coverage`, `sourceRef`다.
- 품질이 낮으면 정량 beta를 닫고 qualitative path만 표시한다.

### Phase D — 선택적 L2.5 조합기

- L2끼리 직접 import하지 않는다.
- 결합이 필요하면 다음 중 하나를 택한다.
  1. UI view-model 조합: 브라우저에서 이미 로드한 데이터 조합.
  2. L3 story/recipe: 엔진 결과를 블록으로 배치.
  3. L2.5 조합기: 수학 0, 내부 import 0, 공개 L2 API 호출만.

전역 금지:

- `macro`가 `analysis` 내부 함수 호출.
- `analysis`가 `macro` 내부 구현을 직접 import.
- UI가 Python 내부 helper 이름에 의존.
- `src/dartlab/ai/lenses/macro.py`의 L4 prompt 자산을 UI 데이터 계약으로 재사용.

---

## 5. 다이얼로그 상태

권장 상태:

```typescript
type MacroLensTab = 'regime' | 'drivers' | 'transmission' | 'scenario' | 'sources';

interface MacroLensOpenState {
  open: boolean;
  tab: MacroLensTab;
  focusId?: string;
}
```

진입별 focus:

- `focusId = 'KR' | 'US'` — 국면 탭.
- `focusId = MACRO_SERIES.id` — driver/지표 탭.
- `focusId = sector id` — 전파 지도 탭.
- `focusId = coMovement id` — co-movement row.

---

## 6. UI 상한

다음은 기획상 금지한다.

- 새 좌측 패널 추가.
- 새 우측 매크로 패널 추가.
- 차트 안 장문 tooltip.
- 지표별 카드 40개.
- 다이얼로그 내부 차트 복제.
- 새 리본 행.
- 매크로 종합 점수/등급을 선택 종목 판정처럼 표시.

상한은 **한 다이얼로그, 다섯 탭, 기존 진입점 재사용**이다.
