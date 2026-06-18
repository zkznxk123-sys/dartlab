# 01. Product PRD

## 1. 문제 정의

현재 터미널 좌상단의 경제 영역은 `macro.json`의 깊이를 거의 쓰지 못한다. `LeftRail.svelte`는 KR/US phase와 quadrant 설명, 자산 칩, 섹터 순풍/역풍 리본을 텍스트 중심으로 보여준다. 사용자는 "지금 경제가 어디에 있고, 어떤 경로로 어떤 섹터에 닿는지"를 한눈에 보지 못하고 문장을 읽어야 한다.

동시에 공개 화면에는 정직성 버그가 있다. `engine.ts::tailwindOf()`는 `blended < 0.2`를 `역풍`으로 분류하고, `LeftRail.svelte`는 `sectorTailwinds().slice(-3)`를 `HEADWIND/역풍`으로 표시한다. 현재 `landing/static/dashboards/macro.json` v19의 `sectorTailwind.blended`는 12개 섹터 모두 양수다. 따라서 현재 하위 양수 섹터를 역풍으로 부르는 경로가 열려 있다.

Macro Lens 다이얼로그는 이미 강한 분석 요소를 갖고 있지만 회사가 선택되어야 열린다. 이 PRD의 범위는 "회사 선택 전에도 보이는 좌상단 floor"와 "회사 선택 후 깊어지는 기존 Macro Lens transmission 탭"을 같은 데이터 계약으로 연결하는 것이다.

## 2. 한 문장 비전

사용자가 좌상단을 3초 보고 "지금 경제가 어디에 있는지"를 시각적으로 파악하고, 한 번 클릭으로 "그 경제 국면이 어떤 driver와 channel을 통해 어떤 섹터/종목 행동으로 이어지는지"를 증거등급과 함께 확인한다.

## 3. 사용자 시나리오

### S1. Glance

터미널 진입 직후, 회사가 선택되지 않아도 사용자는 2x2 국면 좌표판에서 KR/US가 어느 셀에 있는지 본다. KR은 `stagflation`, US는 `reflation` 셀에 표시된다. 자산 칩은 `equity/bond/commodity/gold/tips/cash`의 overweight/underweight/neutral을 색과 화살로 보여준다. 사용자는 문장을 읽기 전에 위치와 자산 방향을 본다.

### S2. Propagation

좌표판 아래 경로 rail에서 `USDKRW -> revenue -> 반도체`, `BASE_RATE -> balanceSheet -> 전 섹터` 같은 edge를 본다. 섹터 칩 hover는 driver/channel/evidence를 보여주고, 클릭은 기존 좌측 스크리너 필터를 작동시킨다.

### S3. Evidence

상세보기는 기존 Macro Lens 다이얼로그를 연다. transmission 탭 상단에 Macro Path Rail full 버전을 배치하고, 기존 exposure matrix는 그 아래 상세 레이어로 유지한다. `OBS/PRIOR/TPL/LOCK`은 opacity와 line style로 구분한다. `동행≠인과`는 항상 노출한다.

### S4. Honesty

모든 섹터 `blended`가 양수인 날에는 `역풍`이라는 말을 화면에서 제거한다. 하위 섹터는 "상대 약순풍"으로 표시하고 caption에 "전 섹터 약순풍 - 절대 역풍 없음"을 둔다. stale이면 수치를 흐리게 하고 asOf를 함께 보여준다.

## 4. 범위

### In Scope

- 좌상단 `마켓 펄스 · 매크로` 카드의 2x2 `RegimeQuadrant` 승격.
- 기존 `twRibbon`의 정직한 전파/섹터 rail 승격.
- 기존 Macro Lens dialog의 transmission 탭 상단에 `MacroPathRail` full 헤드라인 추가.
- `engine.ts`의 양수 `blended` 역풍 분류 수정.
- 회사 독립 macro floor view builder와 회사 의존 Macro Lens snapshot의 경계 명시.
- 현재 `macro.json` v19 기반 수용 테스트와 Playwright QA.

### Out of Scope

- `regimeToAllocation %` 같은 정량 비중 산출.
- Sankey, river, ribbon width 기반 flow magnitude.
- 회사별 전파 크기, beta, elasticity, 목표가, 추천.
- `kr.transition=null` 자체를 엔진에서 고치는 작업.
- `phase`와 `quadrant`의 근본 합의 모델 수정.
- 새 API, 새 fetch origin, 새 route, 새 terminal tab.

## 5. 정보 구조

```text
GLANCE: LeftRail floor, company-independent MacroGlanceView
  RegimeQuadrant
    KR/US 2x2 ordinal cell
    asset implication chips
    phase vs quadrant dual label
    transition honesty line
  MacroPathRail compact
    top sector path chips
    evidence opacity/style
    sector click -> screener filter

DRILL: MacroLensDialog existing modal
  Transmission tab
    MacroPathRail full headline
    existing exposure matrix below
    company-selected sector path highlight if company exists
    company checkpoint disabled state if company is absent

ACTION: LeftRail screener
  sectorFilter and bottomTab owned by TerminalSurface
  sector chip click -> screener tab + industry filter
```

View ownership:

- `MacroGlanceView`: company-independent. Inputs are only `eng.raw.macro`, `eng.raw.macro.transmission`, and `eng.sectorTailwinds()`. It must render before any company is selected.
- `CompanyMacroLensSnapshot`: company-dependent. It may use `co`, `co.industry`, and runtime sector-filtered transmission. It must never be required for opening the macro drill view.
- `sectorFilter` and `bottomTab` move to `TerminalSurface` as the single owner. `LeftRail` receives `{ sectorFilter, onSectorFilter }`; `MacroPathRail` calls the same handler.

## 6. Asset 1: RegimeQuadrant

### Contract

Input: `MacroFile | null`

Output: `RegimeQuadrantView`

Required fields:

- `macro.asOf`
- `macro.kr.phase`, `macro.kr.phaseLabel`, `macro.kr.quadrant`
- `macro.us.phase`, `macro.us.phaseLabel`, `macro.us.quadrant`
- `quadrant.quadrant`, `quadrant.quadrantLabel`
- `quadrant.growth`, `quadrant.inflation`
- `quadrant.assetImplication`
- `quadrant.confidence` if present
- `side.transition` if present
- `side.confidence` if present
- `side.signals` if present. Runtime allows string or string array.

Rendering rules:

- Four cells are fixed ordinal buckets: `stagflation`, `reflation`, `deflation`, `goldilocks`.
- `growthSignal` and `inflationSignal` must not determine x/y coordinate or transform.
- If `phase` and `quadrant` disagree, render both as separate lenses: `국면 모델: 회복 · 격자: 스태그플레이션`.
- If `transition` is null, render `전이신호 미산출`; do not show progress bar or arrow.
- If `quadrant` is absent, render `국면 상세 데이터 없음`.
- `assetImplication` maps to `ow/uw/nu` chips. Missing value maps to neutral, not zero.

Layout budget:

- Validate the left rail at 300px, 284px, and 270px widths, matching the current terminal grid.
- `RegimeQuadrant` floor height target is 138px or less.
- Cell text is limited to KR/US chip and quadrant name. `description` is detail/tooltip only.
- If the budget is exceeded, remove explanatory text before reducing the 2x2 cell structure.

## 7. Asset 2: MacroPathRail

### Contract

Input:

- `MacroTransmissionPayload | null`
- `sectorTailwinds: { id; kr; en; blended }[]`
- `opts.activeIndustryId?: string`
- `opts.mode: 'compact' | 'full'`

Output: `MacroPathView`

Required fields:

- `driverNodes[]`
- `channelNodes[]`
- `sectorNodes[]`
- `links[]`
- `allSectorLinks[]`
- `missing[]`
- `asOf`

Rendering rules:

- `edge.evidenceLevel` maps to opacity/style:
  - `observed`: solid, opacity 1.0
  - `sectorPrior`: solid/dim, opacity 0.65
  - `template`: dashed, opacity 0.45
- `edge.sign` maps only to color, not width.
- `edge.confidence === 'blocked'` forces dotted gray tone and opacity 0.30.
- `edge.sectorKeys === ['all']` renders one `전 섹터` pill. Do not fan out to every sector.
- Compact mode shows ranked sector chips and hover detail.
- Full mode shows driver -> channel -> sector columns as the first viewport of the existing transmission tab.
- The previous edge grid becomes an expandable detail layer or one-row summary under the rail. The first viewport may contain only `PathRail + legend + selected edge drill`.
- Sector chip click calls `onSectorFilter(industryId)` owned by `TerminalSurface`, switches the bottom tab to screener, and applies the same filter state visible in `LeftRail`.
- Company selected sector only highlights matching links. It does not hide other links.
- Freshness is separate from evidence: file freshness comes from `macro.asOf`; driver freshness comes from `driver.sourceLineage.date + staleAfterDays`. Do not lower body text opacity below 0.68 for freshness.

Mapper ownership:

- Keep one shared terminal mapper, not one copy in `engine.ts` and another copy in `macroLens.ts`.
- The mapper must cover every current v19 `transmission.edges[].sectorKeys`.
- Unknown future key renders as `tailwind 미산출` and fails a current-fixture coverage test until explicitly classified.

### Current v19 Sector Key Mapping

The mapper must cover every distinct `macro.json#transmission.edges[].sectorKeys` observed in v19:

| transmission sectorKey | terminal industry id | sectorTailwind key |
|---|---|---|
| `semiconductor` | `semiconductor` | `semiconductor` |
| `auto` | `auto` | `automotive` |
| `shipbuilding` | `shipbuilding` | `shipbuilding` |
| `chemical` | `chemical` | `chemicals` |
| `battery` | `battery` | `chemicals` |
| `logistics` | none | none; render `tailwind 미산출` |
| `finance` | `finance` | `finance` |
| `bank` | `finance` | `finance` |
| `food` | `food` | `retail` |
| `energy` | `energy` | `energy` |
| `utility` | none | none; render `tailwind 미산출` |
| `retail` | `retail` | `retail` |
| `all` | none | special all-sector pill |

Future key handling:

- Unknown key must render as blocked/unknown, not crash.
- Test must fail if current `macro.json` introduces a new key without mapper coverage, except `all`.
- Do not invent weak semantic joins. `logistics` and `utility` stay unmapped until data or product explicitly adds sector-tailwind coverage.

## 8. P0 Bug: Positive Blended Must Not Become Headwind

Current bad rule:

- `tailwindOf()` uses `b >= 0.4 ? 순풍 : b >= 0.2 ? 중립 : 역풍`.
- `LeftRail` labels bottom slice as `HEADWIND/역풍` regardless of sign.

Required rule:

- If `min(sectorTailwinds.blended) > 0`, do not produce `역풍/HEADWIND` labels in floor or ticker.
- Use `상대 약순풍` / `relative weak tailwind` for bottom ranked positive sectors.
- Only show `역풍/HEADWIND` when at least one `blended < 0` exists.
- If negative sectors exist in a fixture, the headwind bucket must return.

Surfaces:

- `engine.ts::tailwindOf()` classification.
- `LeftRail.svelte` bottom sector bucket title.
- `TerminalSurface.svelte` top macro KPI/ticker.

## 9. Never-Claim Rules

1. Do not use raw `growthSignal` or `inflationSignal` as pixel coordinates.
2. Do not show KR transition progress/arrow when `transition === null`.
3. Do not call positive `blended` values headwind.
4. Do not encode transmission magnitude with link width.
5. Do not imply co-movement is causation.
6. Do not collapse `phase` and `quadrant` into one verdict when they disagree.
7. Do not show stale data as fresh.
8. Do not show company-level beta/elasticity unless analysis quality contract provides it.

## 10. Visualization Research Anchors

The product pattern is grounded in existing macro dashboard idioms, but narrowed to DartLab's terminal workflow:

- At-a-glance panels: FRED/Economy at a Glance uses a small set of key charts as a fast economy snapshot. DartLab adopts the snapshot role, not a multi-chart wall.
- Nowcast panels: Atlanta Fed GDPNow separates model estimate and update date. DartLab adopts explicit asOf/freshness, not forecast authority.
- High-frequency activity index: NY Fed WEI compresses multiple real-activity series into one timely signal. DartLab adopts "compressed signal with source lineage", not a single black-box score.
- Business cycle clock: Eurostat/KOSIS use four-quadrant cycle location. DartLab adopts ordinal quadrant location, not continuous point geometry from raw signals.

Research links are captured in `07-visual-research.md`.
