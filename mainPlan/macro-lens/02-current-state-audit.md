# 02. Current State Audit

검증일: 2026-06-19

## 1. 읽은 운영 규칙

- `AGENTS.md`
- `CLAUDE.md`
- `C:\Users\MSI\.claude\projects\c--Users-MSI-OneDrive-Desktop-sideProject-dartlab\memory\MEMORY.md`
- `src/dartlab/skills/specs/start/dartlabSkillOs.md`
- `src/dartlab/skills/specs/operation/testing.md`
- `src/dartlab/skills/specs/operation/code.md`
- `src/dartlab/skills/specs/operation/architecture.md`
- `src/dartlab/skills/specs/operation/ui.md`
- `src/dartlab/skills/specs/operation/apiContract.md`
- `src/dartlab/skills/specs/engines/macro/SKILL.md`

## 2. Current Code Evidence

| Claim | Current source | Evidence |
|---|---|---|
| Macro floor lives in LeftRail | `ui/packages/surfaces/src/terminal/panels/LeftRail.svelte` | `macro = eng.raw.macro`, `assetChips`, `quadWrap`, `twRibbon` are rendered in the top `Panel`. |
| Macro Lens modal is company-gated | `ui/packages/surfaces/src/terminal/TerminalSurface.svelte` | `macroLensSnapshot = co ? buildMacroLensSnapshot(...) : null`; dialog renders only `{#if macroLensOpen && macroLensSnapshot}`. |
| Transmission is fetched by current company sector | `TerminalSurface.svelte` | `runtime.macro.getTransmission({ market: 'KR', sectorKey, includeCrossMarket: true })`. |
| Existing snapshot edges are company-filtered | `ui/packages/surfaces/src/terminal/lib/macroLens.ts` | `buildEdgesFromTransmission(co, drivers, payload)` filters edges by `transmissionEdgeMatches(e, co.industry)`. |
| Bottom sector tailwinds are called headwind | `LeftRail.svelte` | `twBot = tailwinds.slice(-3).reverse()` then label `HEADWIND/역풍`. |
| Positive small blended is classified as headwind | `ui/packages/surfaces/src/terminal/lib/engine.ts` | `tailwindOf()` maps `b < 0.2` to `label: '역풍', tone: 'down'`. |
| `MacroSide` lacks transition/confidence typing | `ui/packages/surfaces/src/terminal/lib/types.ts` | `MacroSide` has only `phase`, `phaseLabel`, optional `quadrant`. Runtime data has `transition`; type should be widened. |
| ui-surfaces has check script only | `ui/packages/surfaces/package.json` | script only includes `"check": "svelte-check --tsconfig ./tsconfig.json"`. Vitest files exist but no package script. |

## 3. Current Data Evidence

Command used:

```bash
node -e "const fs=require('fs');const m=JSON.parse(fs.readFileSync('landing/static/dashboards/macro.json','utf8')); /* inspect fields */"
```

Observed:

- `version`: `v19`
- `asOf`: `2026-06-18`
- `kr.phase`: `recovery`
- `kr.phaseLabel`: `회복`
- `kr.quadrant.quadrant`: `stagflation`
- `kr.quadrant.growth`: `falling`
- `kr.quadrant.inflation`: `rising`
- `kr.transition`: `null`
- `us.phase`: `slowdown`
- `us.quadrant.quadrant`: `reflation`
- `us.transition`: `{ from: "slowdown", to: "contraction", progress: 33, triggered: ["gold_surging"], pending: ["vix_spiking", "term_spread_inverted"] }`
- `sectorTailwind` count: 12
- `sectorTailwind` negative count: 0
- min blended: `biotech = 0.08`
- max blended: `it_software = 0.28`
- below `0.2`: `construction`, `shipbuilding`, `automotive`, `steel`, `chemicals`, `display`, `retail`, `biotech`
- transmission drivers: 6
- transmission edges: 7
- observed edge sector keys: `semiconductor`, `auto`, `shipbuilding`, `chemical`, `battery`, `logistics`, `all`, `finance`, `bank`, `food`, `energy`, `utility`, `retail`
- `all` edges: `rate-debt-interest`, `hy-risk-premium`

## 4. PRD Corrections From Audit

1. The original mapping table listed future/non-v19 keys such as `electronics`, `steel`, `cosmetics`. The implementation acceptance test must use the current v19 key set and handle future keys explicitly.
2. The original PRD called unit tests `vitest` but did not identify a runnable package command. The plan must specify either a one-off `npx vitest run ...` command from the package context or a package script addition in the implementation phase.
3. `MacroSide` type widening is required before using `transition/confidence/signals` in typed builders.
4. `TerminalSurface` top KPI also has a `headwind/역풍` macro KPI for the bottom tailwind. P0 must fix both `LeftRail` and this top KPI.
5. Screenshot artifacts should not be committed. Use temp or ignored evidence paths during QA and record only command results in `06-progress-ledger.md`.

## 5. Non-Negotiable Repo Constraints

- Work on `master`; do not create branch/worktree.
- No `git add -A` or `git add .`; commit only explicit paths.
- UI push requires operator approval.
- No new root `scripts/` folder.
- No new public API unless `operation.apiContract` passes.
- No new source raw fetch outside `operation.ui` data workspace.
- Full `pytest tests/ -v` is forbidden; use targeted tests and Guard Index when needed.

