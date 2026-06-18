# 03. Expert Debate

## 1. Roles

- Product/UX information designer
- Buy-side macro analyst
- Terminal UI engineer
- Data contract architect
- Skeptical implementation red team

## 2. Debate Summary

This file reflects three implementation-facing expert reviews plus the main code/data audit. The review agents did not change code; their findings are folded into the v1.1 PRD as acceptance contracts.

### A. Product/UX

Decision: The floor should answer only two questions:

1. Where is the economy?
2. What path does that open toward sectors?

Rejected:

- Long explanatory prose in the floor.
- A new floor panel.
- Hero-like or decorative visualization.
- A general dashboard page separate from terminal.

Accepted:

- 2x2 ordinal quadrant because it is a compact visual grammar.
- Asset implication chips because they preserve the existing `assetImplication` contract.
- Path rail because it connects macro state to existing screener action.
- Company-unselected mode must still open the macro drill. Otherwise the main S1 scenario fails before implementation starts.
- The floor must be validated at the actual left-rail widths: 300px, 284px, and 270px.

### B. Macro Analyst

Decision: The UI must separate model lenses instead of forcing one verdict.

Current data has `kr.phase=recovery` and `kr.quadrant=stagflation`. That is not a UI bug; it means the cycle phase model and growth/inflation quadrant lens are different. The correct product move is to show both.

Rejected:

- "KR is stagflation" as a single final verdict.
- Progress arrow for KR transition when `transition=null`.
- `growthSignal` and `inflationSignal` as physical coordinates because units/scales are not normalized.

Accepted:

- `국면 모델: 회복 · 격자: 스태그플레이션`.
- Transition line with missing state.
- Confidence/freshness as visual strength, not conclusion strength.
- `transition=null` means no arrow, no progress, and no next-phase CTA.
- `sectorTailwind.blended` is consumed as a relative sector score unless it is actually negative.

### C. Terminal UI Engineer

Decision: The existing `LeftRail` and `MacroLensDialog` are the right homes.

Rejected:

- New route.
- New modal tab.
- Full Sankey.
- New global CSS surface.

Accepted:

- `RegimeQuadrant.svelte` component scoped to terminal panel.
- `MacroPathRail.svelte` shared between compact floor and full dialog mode.
- Existing `toggleSector` and `onMacroLens` routes reused.
- `sectorFilter` and `bottomTab` move to `TerminalSurface` so modal chips can switch the screener tab and apply the same filter state.
- The transmission tab first viewport is limited to `PathRail + legend + selected edge drill`; the old edge grid is detail, not another competing headline.

### D. Data Contract Architect

Decision: Add view builders, not fetchers.

Rejected:

- Any extra network call for the macro floor.
- Any public API change.
- Directly using runtime local API for public terminal macro data.

Accepted:

- `buildRegimeQuadrant(macro)` as a pure UI view-model builder.
- `buildMacroPath(transmission, sectorTailwinds, opts)` as a pure UI view-model builder.
- `MacroSide` type widening to match actual data shape.
- Mapper test against `landing/static/dashboards/macro.json`.
- Two view contracts: company-independent `MacroGlanceView` and company-dependent `CompanyMacroLensSnapshot`.
- A single shared edge-sector mapper. Duplicate constants in `engine.ts` and `macroLens.ts` are rejected.
- `logistics` and `utility` stay `tailwind 미산출` until data explicitly supports them.

### E. Red Team

Risk findings:

1. `HEADWIND` bug spans both `LeftRail` and top KPI strip, not just `tailwindOf`.
2. The original PRD's sector key table was larger than current v19; tests must distinguish current required keys from future graceful handling.
3. `ui/packages/surfaces` has no `test` script; a PRD saying "vitest" without command is weak.
4. Feature flags must not become a permanent product switch. They are rollback constants only.
5. Playwright "pass" can miss design flaws. The PRD must require screenshot eye review before push.
6. Feature rollback must include `types.ts`, `macroLens.ts`, `engine.ts`, `LeftRail.svelte`, `MacroLensDialog.svelte`, `TerminalSurface.svelte`, tests, and component flags. "Delete two files" is not a sufficient rollback plan.
7. `macroLensSnapshot` currently blocks the modal when `co` is absent. This is a product bug for the new macro floor, not an implementation detail.

## 3. Final Synthesis

The strongest version is not "more macro panels." It is a two-layer lens:

- Floor: ordinal state and path candidates, visible before the user decides what to inspect.
- Dialog: evidence and limits, tied to the selected company/sector.

The moat is not the 2x2 chart itself. The moat is the chain:

```text
macro.json quadrant
  -> asset implication
  -> transmission driver/channel/sector edge
  -> evidence level and falsifier
  -> existing screener filter
  -> existing company Macro Lens details
```

The final PRD therefore prioritizes:

1. Fix the public honesty bug first.
2. Replace text-heavy macro card with a compact visual state machine.
3. Add path rail without claiming magnitude.
4. Keep unknown and stale states physically visible.
5. Verify with current data, fake negative fixture, Svelte check, UI data wiring guard, and Playwright screenshots.

## 4. Expert Review Closure

The three explicit review tracks changed the PRD in these concrete ways:

| Review track | PRD change |
|---|---|
| Product/UX | Added company-unselected `MacroGlanceView`, actual rail width budget, first-viewport cap for the dialog. |
| Macro/data contract | Split `phase` vs `quadrant`, split file freshness vs driver freshness, made `transition=null` a hard no-arrow rule. |
| Implementation/red team | Added `TerminalSurface` KPI to P0, single mapper ownership, runnable test command rules, feature-flag rollback acceptance. |

No review finding remains open in the planning layer. Open work starts at P0 implementation.
