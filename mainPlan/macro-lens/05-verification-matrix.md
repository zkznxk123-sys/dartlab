# 05. Verification Matrix

## 1. Acceptance Criteria

| Requirement | Evidence |
|---|---|
| 회사 미선택에서도 macro drill이 열린다 | Playwright: no selected company state에서 detail button opens market-only Macro Lens view. |
| 좌표판만 보고 경제 위치를 알 수 있다 | Screenshot review: KR/US chips visible in 2x2 cells; phase/quadrant labels visible but not dominant. |
| KR/US cell is correct for v19 | Unit test: KR=`stagflation`, US=`reflation` from `landing/static/dashboards/macro.json`. |
| Asset chips match v19 `assetImplication` | Unit test maps all six keys; screenshot confirms chips render. |
| KR transition missing is honest | Unit test: `kr.transition=null` means no progress/arrow DOM. |
| phase and quadrant are not blended into one verdict | DOM/snapshot contains separate `국면 모델` and `격자` labels when values differ. |
| No positive blended headwind | Unit test + DOM assertion: current v19 all-positive data has no `역풍`/`HEADWIND` in macro floor/KPI. |
| Negative fixture returns headwind | Unit test with one negative `blended` shows headwind bucket. |
| All 7 v19 transmission edges render | Unit test counts rendered link view models. |
| All v19 sector keys covered | Unit test extracts distinct sectorKeys from `macro.json` and compares mapper keys plus `all`. |
| Weak semantic joins are not invented | Unit test: `logistics` and `utility` produce `tailwind=null`/`tailwind 미산출`, not `it_software` or `energy`. |
| `['all']` edge is one pill | Unit test: all-sector links count 2; fan-out count 0. |
| Evidence strength is opacity/style | DOM/CSS test or screenshot review: observed/sectorPrior/template classes differ by opacity/style, not width. |
| Freshness is separate from evidence | Unit/DOM test: file stale state uses asOf chip/tone; driver stale state uses driver lineage tone; evidence opacity does not drop body text below 0.68. |
| Sector click filters screener | Playwright: click sector chip, `.filtChip` appears and rank list is filtered; click again clears. |
| Sector click changes tab owner state | Playwright: from non-screener bottom tab, sector chip click switches to screener and applies the same `sectorFilter` shown in LeftRail. |
| Existing 5 modal tabs preserved | Playwright/DOM: `.mlTabs button` count remains 5. |
| No new fetch/origin | `node tests/audit/checkUiDataWiring.mjs` passes with no baseline increase. |
| Svelte type safety | `npm run check -w @dartlab/ui-surfaces` passes with 0 errors. |
| Landing route still works | `npm run check --prefix landing` and Playwright `/terminal` smoke pass. |
| Mobile layout does not overflow | Playwright checks `document.documentElement.scrollWidth <= innerWidth + 1` and modal scrollWidth <= clientWidth + 1. |

## 2. Regression Tests To Add

Recommended files:

- `ui/packages/surfaces/src/terminal/lib/engine.test.ts`
- `ui/packages/surfaces/src/terminal/lib/macroLens.test.ts`

Test cases:

1. `classifyTailwindsAllPositive`
2. `classifyTailwindsWithNegative`
3. `buildRegimeQuadrantFromMacroV19`
4. `buildRegimeQuadrantDoesNotUseRawSignalsForCoordinates`
5. `buildRegimeQuadrantNullTransitionHasNoArrow`
6. `buildMacroPathCoversCurrentTransmissionKeys`
7. `buildMacroPathAllSectorPill`
8. `buildMacroPathEvidenceClasses`
9. `buildMacroPathUnknownSectorKeyBlocked`
10. `buildMacroPathLogisticsUtilityTailwindMissing`
11. `buildMacroGlanceViewWithoutCompany`

## 3. Playwright Assertions

Desktop:

- viewport `1440x1000`
- open `/terminal`
- wait for `마켓 펄스 · 매크로`
- assert no company selection is required to open macro detail
- assert quadrant component visible
- assert `역풍` absent when current all-positive data is used
- click first macro path sector chip
- assert screener filter chip visible
- open Macro Lens detail
- switch transmission tab
- assert Macro Path Rail full visible
- assert 5 tabs
- assert no page/modal overflow
- repeat left rail width snapshots at 300px, 284px, and 270px if the route/harness supports container sizing

Mobile:

- viewport `390x844`
- same assertions for visibility and overflow
- compact rail must wrap or scroll internally without page horizontal overflow

## 4. Completion Audit Checklist

Before marking implementation complete:

- [ ] Every changed file is part of the PRD write set.
- [ ] No new public API.
- [ ] No new fetch origin.
- [ ] No new route.
- [ ] No new modal tab.
- [ ] No Sankey/magnitude ribbon.
- [ ] P0 positive-headwind bug fixed in `engine.ts`, `LeftRail.svelte`, and `TerminalSurface.svelte`.
- [ ] Type widening matches actual `macro.json`.
- [ ] Tests cover current v19 and at least one fake negative fixture.
- [ ] Svelte check passed.
- [ ] UI data wiring guard passed.
- [ ] Playwright desktop/mobile passed.
- [ ] Screenshots reviewed before push.
- [ ] Dev server/processes stopped before final response.
