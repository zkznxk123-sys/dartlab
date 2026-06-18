# 06. Progress Ledger

상태: 구현 v1.5

## 2026-06-19

### v1.5 — Command Bar / Evidence Cockpit / hard-lock guards

배경:

- 판정-first UI는 구조를 만들었지만, 사용자가 첫 화면에서 바로 검증 행동을 실행하는 조작성이 부족했다.
- 엔진 red-team에서 stale 핵심 driver, missing transmission, invalid quantCandidate, zero-change polarity가 claim 과장 위험으로 확인됐다.

완료:

- `MacroLensDialog` 판정 화면에 `Command Bar`를 추가했다. 핵심 지표 차트 오버레이, 전파 경로 탭, 출처/반증 탭으로 즉시 이동한다.
- `Evidence Cockpit`을 첫 화면에 추가해 시계열/경로/동행/회사노출/민감도 5개 gate와 핵심 release freshness를 항상 보이게 했다.
- 모바일 mechanism rail을 3x2 압축 그리드로 바꾸고, cockpit/mobile overflow를 검증했다.
- `buildMacroVerdict()`와 evidence gate를 보강했다. stale primary driver, missing/fallback transmission, unusable edge는 hard lock으로 처리한다.
- `quantCandidate`는 `coverage=company`, `nObs>=minObs`, `R²`, `window`, `frequency`가 있어야만 `companyCandidate`로 승격한다.
- 변화가 0인 negative/positive edge는 pressure/supportive로 라벨링하지 않는다. mixed edge는 계속 mixed로 유지한다.
- locked verdict score는 `<=44`로 제한해 잠김 상태가 강한 신호처럼 보이지 않게 했다.

검증:

- `npx vitest run ui/packages/surfaces/src/terminal/lib/macroMappings.test.ts ui/packages/surfaces/src/terminal/lib/macroLens.test.ts` 통과. 12개 테스트.
- `npm run check -w @dartlab/ui-surfaces` 통과. 기존 warning 45개, error 0.
- `npm run check --prefix landing` 통과. 기존 warning 56개, error 0.
- Playwright smoke: command button 3개, cockpit 1개, gate 5개, 경로/출처 탭 이동, desktop/mobile overflow 0, page/console error 0.
- QA screenshots: `output/playwright/macro-verdict-command-cockpit-desktop.png`, `output/playwright/macro-verdict-command-cockpit-mobile.png`.

NEXT:

1. 실제 release calendar/vintage 데이터가 열리면 release reaction gate를 추가한다.
2. 탭 본문 컴포넌트 분리는 별도 유지보수 리팩터로만 처리한다.

---

### v1.4 — Dialog keyboard/focus shell

배경:

- v1.3의 판정-first UI는 분석 구조를 개선했지만, 탭과 포커스 조작은 아직 심층 콘솔 수준으로 고정되어 있지 않았다.

완료:

- `MacroLensDialog` 탭을 `tablist/tab/tabpanel` ARIA 계약으로 바꿨다.
- `ArrowLeft/ArrowRight/Home/End` 탭 전환, `Tab/Shift+Tab` modal focus trap, `Escape` 닫힘을 고정했다.

검증:

- `npm run check -w @dartlab/ui-surfaces` 통과.
- Playwright keyboard smoke: 방향키 탭 전환, End 키, 40회 Tab 후 modal 내부 focus 유지, Escape 닫힘, desktop/mobile overflow 0 확인.

NEXT:

1. 탭별 본문 컴포넌트 분리는 유지보수성 리팩터로 별도 처리한다.

### v1.3 — Macro Verdict Engine / 판정-first 다이얼로그

배경:

- v1.2 구현은 macro path와 transmission rail을 터미널에 연결했지만, 다이얼로그 첫 화면은 여전히 matrix와 pulse 중심이라 사용자가 즉시 볼 핵심 판단 구조가 약했다.
- 판정은 사람이 임의로 내리는 값이 아니라, 공개 산출물의 증거 gate를 통해 산출되어야 한다.

완료:

- `MacroLensSnapshot.verdict`를 추가했다. `score/direction/claimLevel/title/summary/primaryChain/nextAction/falsifier/blockers/sourceRefs/drivers`를 구조화한다.
- `buildMacroVerdict()`는 driver별 변화, 전파 경로, 신선도, 섹터 tailwind, 회사 macroExposure 품질, co-movement를 component score로 만든다.
- mixed edge는 방향 기여를 0으로 두고, 회사 evidence가 잠긴 경우 정량 claim을 잠근다. market-only snapshot은 `marketMap` claim level로 제한한다.
- `MacroLensDialog` 첫 탭을 `판정`으로 바꾸고 `Macro Verdict Hero -> Verdict Engine Rail -> 반증/잠금/근거 수준 -> Top 3 drivers` 순서로 재구성했다.
- 기존 matrix/release rail/legend는 접힌 상세 증거 영역으로 내렸다.
- 모바일 탭 줄바꿈과 핵심 경로 truncation을 수정했다.

검증:

- `npx vitest run ui/packages/surfaces/src/terminal/lib/macroMappings.test.ts ui/packages/surfaces/src/terminal/lib/macroLens.test.ts` 통과.
- `npm run check -w @dartlab/ui-surfaces` 통과. 기존 warning은 남아 있으나 error는 0.
- Playwright desktop/mobile smoke: verdict hero, engine rail, top driver 3개, component step 6개, evidence fold 기본 닫힘, 수평 overflow 0 확인.
- QA screenshots: `output/playwright/macro-verdict-v2-desktop-modal.png`, `output/playwright/macro-verdict-v4-mobile-modal.png`.

NEXT:

1. 실제 발표 캘린더/빈티지 데이터가 열리면 release reaction gate를 verdict component에 추가한다.
2. public/local UI 변경이므로 push 전에는 운영자 눈검수 스크린샷 확인을 유지한다.

### v1.0 — Current-code grounded PRD 승격

배경:

- 원문 `C:\Users\MSI\.claude\plans\graceful-yawning-valley.md`는 방향과 화면 자산은 강했지만, 일부 계약이 현재 코드/데이터보다 넓고 테스트 명령이 불명확했다.
- 사용자는 전문 관점 토론을 거쳐 PRD를 완성하라고 지시했다.

완료:

- PRD를 `mainPlan/macro-lens/` SSOT로 승격했다.
- 현재 코드 근거를 `LeftRail.svelte`, `TerminalSurface.svelte`, `engine.ts`, `macroLens.ts`, `types.ts`, `landing/static/dashboards/macro.json` 기준으로 검증했다.
- 현행 v19 `macro.json`의 실제 sector key set, all-sector edge, phase/quadrant/transition, all-positive blended 상태를 문서에 고정했다.
- `HEADWIND/역풍` 정직 버그가 `engine.ts`, `LeftRail.svelte`, `TerminalSurface.svelte` 세 표면에 걸쳐 있음을 반영했다.
- `ui/packages/surfaces`에 test script가 없다는 점을 반영해 Vitest 실행 방식을 명시했다.
- 전문 관점 토론 결과를 제품/UX, 매크로, UI, 데이터계약, 구현 레드팀으로 분해했다.

검증:

- 문서 작업 단계에서는 코드 실행 변경 없음.
- Current state audit은 로컬 파일 읽기와 `node` JSON inspection으로 수행했다.

NEXT:

1. 완료: v1.1에서 에이전트 3인의 검토 결과를 통합했다.
2. 구현 착수 시 P0 `positive blended -> no headwind` 버그 수정부터 독립 commit으로 진행한다.

### v1.1 — Expert review integration and visual research

배경:

- Product/UX, macro/data, implementation red-team 리뷰가 모두 같은 약점을 지적했다: 회사 미선택 뷰, 실제 v19 sector key 계약, P0 영향 표면, 테스트 명령, 롤백 범위가 더 명확해야 했다.
- 사용자는 매크로 분석 대시보드 시각화 방식을 조사하라고 요구했다.

완료:

- `MacroGlanceView`와 `CompanyMacroLensSnapshot`을 분리했다. 회사 미선택 상태에서도 macro drill이 열리는 계약을 추가했다.
- 실제 LeftRail 폭 300/284/270px와 `RegimeQuadrant` 높이 138px 예산을 수용 기준으로 추가했다.
- `sectorFilter`와 `bottomTab`의 단일 owner를 `TerminalSurface`로 고정했다.
- `EDGE_TO_TAILWIND` 중복 금지와 공유 mapper 원칙을 추가했다.
- `logistics`, `utility`는 임의로 `it_software`/`energy`에 붙이지 않고 `tailwind 미산출`로 렌더하도록 수정했다.
- freshness와 evidence 시각 채널을 분리했다.
- P0 범위에 `engine.ts`, `LeftRail.svelte`, `TerminalSurface.svelte`를 모두 명시했다.
- 테스트 명령에 `uv run python -X utf8 tests/audit/dartlabGuard.py quick`와 Vitest 실행 조건을 추가했다.
- 공식 매크로 대시보드 조사 결과를 `07-visual-research.md`로 추가했다.

검증:

- 문서 보강 단계에서는 코드 실행 변경 없음.
- 전문가 리뷰 3건의 모든 구현 차단 지적을 PRD/계획/검증 매트릭스 중 하나에 반영했다.

NEXT:

1. 외부 원문 PRD `C:\Users\MSI\.claude\plans\graceful-yawning-valley.md`에 SSOT 승격 상태를 표시한다.
2. 문서 링크/미해결 토큰 검사를 통과시킨 뒤 explicit-path commit을 만든다.

### v1.2 — Terminal implementation

배경:

- 사용자는 기획에서 멈추지 말고 실제 public terminal의 경제지표분석 핵심 기능으로 구현하라고 지시했다.
- 구현 중 전문가 리뷰는 `HEADWIND` 정직 버그, 회사 미선택 macro drill 차단, `sectorFilter`/`bottomTab` 소유권 분산, 현행 v19 sector key 계약을 우선순위로 지적했다.

완료:

- `macroMappings.ts`를 추가해 `INDUSTRY_TAILWIND_MAP`, `EDGE_SECTOR_TO_TAILWIND`, `classifyTailwind()`를 공유 SSOT로 만들었다.
- `engine.ts`의 `tailwindOf()`와 `sectorTailwinds()`가 공유 분류 함수를 사용하도록 바꿔 양수 `blended`가 `역풍`이 되는 경로를 제거했다.
- `TerminalSurface.svelte`의 상단 macro KPI도 음수 `blended`가 있을 때만 `역풍/headwind`를 표시하도록 고쳤다.
- `buildRegimeQuadrant()`, `buildMacroPath()`, `buildMacroGlanceView()`, `buildMarketMacroLensSnapshot()`을 추가해 회사 선택 전에도 macro drill을 열 수 있게 했다.
- `RegimeQuadrant.svelte`와 `MacroPathRail.svelte`를 추가하고, `LeftRail.svelte`의 기존 macro floor를 2x2 국면 + 전이 경로 rail로 교체했다.
- `MacroLensDialog.svelte`의 기존 5개 탭을 유지하면서 transmission 탭 상단에 full `MacroPathRail`을 배치했다.
- `sectorFilter`와 `bottomTab` 소유권을 `TerminalSurface`로 이동해 macro path sector chip 클릭이 screener 필터와 같은 상태를 쓰도록 만들었다.
- `logistics`는 terminal filter id를 유지하되 sector-tailwind는 `tailwind 미산출`로 표시하고, `utility`는 industry/tailwind 모두 unmapped로 유지했다.
- public loader가 HF-first macro 신선도를 유지하되 HF 산출물에 `transmission`이 없는 경우 local v19 `transmission`만 보강하도록 `loadMacroWithTransmission()`을 추가했다.
- `macroMappings.test.ts`와 `macroLens.test.ts`를 추가해 current v19 sector key coverage, all-sector fanout 금지, 2x2 국면, 회사 미선택 glance, positive blended no-headwind 회귀를 고정했다.

검증:

- `npx vitest run ui/packages/surfaces/src/terminal/lib/macroMappings.test.ts ui/packages/surfaces/src/terminal/lib/macroLens.test.ts` 통과.
- `npm run check -w @dartlab/ui-surfaces` 통과. 기존 a11y/state warning은 남아 있으나 error는 0.
- `npm run check --prefix landing` 통과. 기존 warning은 남아 있으나 error는 0.
- `node tests/audit/checkUiDataWiring.mjs` 통과. 신규 위반 0.
- `uv run python -X utf8 tests/audit/dartlabGuard.py quick` 통과.
- `python -X utf8 tests/audit/lint_camelcase_ast.py --changed --strict` 통과.
- Playwright smoke 통과: desktop `1440x1000`, mobile `390x844`. macro floor, positive no-headwind, sector filter, 5 modal tabs, full transmission rail, horizontal overflow를 확인했다.
- QA screenshots: `output/playwright/macro-lens-desktop.png`, `output/playwright/macro-lens-mobile.png`.

NEXT:

1. dev server와 브라우저 세션을 정리하고 explicit-path commit을 만든다.
