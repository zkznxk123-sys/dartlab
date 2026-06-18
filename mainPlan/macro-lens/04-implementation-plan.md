# 04. Implementation Plan

## Phase P0: Headwind Honesty Fix

Goal: Do not label positive `sectorTailwind.blended` as headwind.

Files:

- `ui/packages/surfaces/src/terminal/lib/engine.ts`
- `ui/packages/surfaces/src/terminal/panels/LeftRail.svelte`
- `ui/packages/surfaces/src/terminal/TerminalSurface.svelte`
- tests added under `ui/packages/surfaces/src/terminal/lib/`

Changes:

- Add a helper such as `classifyTailwind(blended, allPositive)` or equivalent.
- `tailwindOf()` returns `상대 약순풍`/neutral-ish tone for positive low blended when all sectors are positive.
- `LeftRail` bottom bucket label becomes `상대 약순풍` when all `blended > 0`.
- `TerminalSurface` macro KPI must not emit label `headwind/역풍` when all `blended > 0`.
- Fake fixture with one negative blended verifies that `역풍/HEADWIND` returns.
- Do not wait for the visual redesign. This bug fix is the first independent implementation commit.

Acceptance:

- Current v19 all-positive data renders no `역풍/HEADWIND` in the macro floor or macro KPI.
- Negative fixture renders one headwind bucket.

Rollback:

- Revert this phase independently. It is bug fix only and should not depend on visual components.

## Phase P1: RegimeQuadrant Builder and Component

Goal: Replace text-only quadrant cards with an ordinal 2x2 visual state.

Files:

- `ui/packages/surfaces/src/terminal/lib/types.ts`
- `ui/packages/surfaces/src/terminal/lib/macroLens.ts` or new terminal-local view model file if cleaner
- `ui/packages/surfaces/src/terminal/panels/RegimeQuadrant.svelte`
- `ui/packages/surfaces/src/terminal/panels/LeftRail.svelte`

Changes:

- Widen `MacroQuadrant` and `MacroSide` types to include actual optional fields:
  - `growthSignal?: number`
  - `inflationSignal?: number`
  - `confidence?: string`
  - `signals?: string | string[] | Record<string, unknown> | null`
  - `transition?: { from?: string; to?: string; progress?: number; triggered?: string[]; pending?: string[] } | null`
- Add `RegimeQuadrantView` with `cells`, `markets`, `assetRows`, `freshness`, `lensConflict`.
- Render 2x2 fixed cell grid.
- Render KR/US chips by `quadrant.quadrant`, not by raw signals.
- Render phase/quadrant dual label when they differ.
- Render transition missing/available line.
- Add `MacroGlanceView` builder path that does not require `co`.

Acceptance:

- KR chip in `stagflation`, US chip in `reflation` with v19.
- No style transform or coordinate computed from `growthSignal`/`inflationSignal`.
- `kr.transition=null` produces no arrow/progress.
- Missing quadrant path renders `국면 상세 데이터 없음`.

Rollback:

- Feature flag constant `FLAG_REGIME_PLANE = false` restores previous `quadWrap` block.
- With the flag off, `npm run check -w @dartlab/ui-surfaces` must still pass.

## Phase P2: MacroPath Builder and Full Rail

Goal: Build sector-level path rail from `macro.transmission` without company dependence.

Files:

- `ui/packages/surfaces/src/terminal/lib/macroLens.ts`
- `ui/packages/surfaces/src/terminal/panels/MacroPathRail.svelte`
- `ui/packages/surfaces/src/terminal/panels/MacroLensDialog.svelte`

Changes:

- Add or extract one shared `EDGE_SECTOR_TO_TAILWIND` mapper for current v19 sector keys. Do not duplicate it across `engine.ts` and `macroLens.ts`.
- Add `buildMacroPath(transmission, sectorTailwinds, opts)` using `eng.raw.macro?.transmission` for market-only mode.
- Render full rail at the top of the existing `transmission` tab.
- Keep existing exposure matrix below.
- For `sectorKeys=['all']`, render one `전 섹터` pill.
- Evidence level controls opacity/style, not width.
- Sign controls color only.
- Company sector highlight is additive, not filtering.
- `logistics` and `utility` render with `tailwind 미산출`, not guessed substitutes.
- Evidence strength and freshness use separate visual channels.

Acceptance:

- All 7 v19 edges render.
- All observed sector keys are either mapped or special-cased as `all`.
- `all` edges do not fan out.
- Existing 5 tabs remain unchanged.
- Company absence does not block the drill modal from opening in market-only mode.

Rollback:

- `FLAG_MACRO_PATH = false` removes the rail and leaves existing matrix.
- With the flag off, the existing transmission tab renders and `npm run check -w @dartlab/ui-surfaces` passes.

## Phase P3: Compact Floor Rail and Screener Action

Goal: Make the floor path rail actionable.

Files:

- `LeftRail.svelte`
- `TerminalSurface.svelte`
- `MacroPathRail.svelte`

Changes:

- Replace `twRibbon` with compact `MacroPathRail`.
- Move `sectorFilter` and `bottomTab` ownership to `TerminalSurface`.
- `LeftRail` receives `{ sectorFilter, onSectorFilter }`.
- Chip click calls `onSectorFilter(id)`, switches bottom tab to screener, and applies the same filter state.
- Hover/keyboard focus shows driver/channel/evidence hint.
- Enter/Space activates sector chip.
- If `sectorTailwind` is missing for a key, render blocked/unknown chip rather than dropping it silently.

Acceptance:

- Clicking `반도체` filters the existing screener to semiconductor companies.
- The bottom area switches to screener if it was previously on another tab.
- Clicking same chip again clears filter.
- Keyboard Enter/Space parity.

Rollback:

- `FLAG_MACRO_PATH = false` restores old `twRibbon`, with P0 honesty fix still applied.

## Phase P4: Responsive Polish and Evidence QA

Goal: Make it shippable on public terminal.

Files:

- Same UI files as P1-P3.
- `mainPlan/macro-lens/06-progress-ledger.md`

Checks:

- desktop 1440x1000
- left rail widths 300px, 284px, 270px
- modal 1040px
- mobile 390x844

Acceptance:

- No page horizontal overflow.
- No modal horizontal overflow.
- No console/page errors.
- Text does not overlap or escape chips.
- Weak evidence is visibly weaker in grayscale/opacity, not only color.
- Screenshots reviewed by a human before push.

## Test Commands

Targeted commands:

```powershell
npm run check -w @dartlab/ui-surfaces
npm run check --prefix landing
node tests/audit/checkUiDataWiring.mjs
uv run python -X utf8 tests/audit/dartlabGuard.py quick
python -X utf8 tests/audit/lint_camelcase_ast.py --changed --strict
```

If Vitest tests are added, the implementation must either add a runnable surfaces test script/config in the same PR or document an executable root command. Transitional root command:

```powershell
npx vitest run ui/packages/surfaces/src/terminal/lib/macroLens.test.ts ui/packages/surfaces/src/terminal/lib/engine.test.ts
```

If implementation adds a package script, prefer:

```powershell
npm run test -w @dartlab/ui-surfaces -- --run src/terminal/lib/macroLens.test.ts src/terminal/lib/engine.test.ts
```

Browser QA:

```powershell
cd landing
npm run dev
```

Then use Playwright against `http://127.0.0.1:5173/terminal`. Terminate the dev server before final response.

Do not commit screenshots unless explicitly requested. Record screenshot paths and assertions in `06-progress-ledger.md`.

## Commit Plan

- Before implementation, record current dirty state with `git status --short` and touch only the PRD write set for the phase.
- Commit P0 alone: `수정: 매크로 순풍 역풍 라벨 정직화`
- Commit P1-P2 together only if the builder/component boundary is cohesive.
- Commit P3-P4 as UI polish/action commit.
- Use explicit path commits only.
- Do not push until operator says `푸시해`, `올려`, or equivalent.
