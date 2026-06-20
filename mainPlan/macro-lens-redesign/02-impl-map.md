# 02. 구현 라인맵 (ground-truth · 3 에이전트 감사 + 운영자 직접검증, 2026-06-20)

> 본 문서는 redesign + superstrengthen 두 PRD를 **현재 소스에 대조한 실측 라인맵**이다. PRD가 "줄번호는 보조, 현 소스가 SSOT"라 했으므로 본 맵이 편집 SSOT. 구현 중 갱신(as-building ledger).

## 0. PRD 대비 9 drift 정정 (편집 전 확정)

| # | PRD 주장 | 실측 | 조치 | 심각도 |
|---|---|---|---|---|
| A1 | CenterStack은 prop 전달뿐·교체대상 아님(§8.5/§8.6) | **CenterStack.svelte:421** `onMacroLens?.('drivers', k.id)` 실 리터럴 존재 | commit2 콜사이트에 **추가**(9번째) | HIGH |
| A2 | LeftRail line 113 | 실제 **L115** | L115 교체 | low |
| A3 | §8.5 표가 MacroLensDialog:21 누락 | `localTab=$state('regime')` L21 | commit1서 'dashboard' | low |
| B1 | `runScript("buildMacroRegime.py",...)` 베어 파일명 | 실제 **전체 repo-상대경로** `".github/scripts/sync/buildMacroRegime.py"` | rc3 전체경로 | med |
| B2 | `_load_regime` = `_analyze_market` 3단 복제 | `_analyze_market` 3단계는 `_fallback()`(합성), missing-payload는 **`_build_transmission`** 패턴 | `_load_regime`는 `_build_transmission` 미싱페이로드 패턴 채택 | med |
| C1 | (forecast.py docstring) probit zone 3단 | 실제 **4단**(low/moderate/elevated/high) — PRD 4단 주장이 맞음, 소스 docstring이 stale | PRD대로 4단 | info |
| C2 | hamilton maxIter | 함수 **default 200**, forecast/sync는 50 명시 | sync서 `maxIter=50` 명시 | info |
| C3 | rates `interpretation` 영어 enum 미확정(HIGH) | **확정: 영어 enum** `steep_normal/normal/flat/inverted`(yieldCurve.py L151-161). desc만 한글 | §4.3 enum→라벨 매핑 유효 | RESOLVED |
| C4 | nowcast confidence = str high/med/low | docstring float 0~1 (nowcast 보류라 무영향) | 표면화 보류 유지 | low |

**추가 확정:** `--panel/--txt/--bd/--dim/--amber/--up/--dn` 모두 terminal.css(L10-27) 실재 → PRD 토큰 그대로 사용. `--dim:#c4ccd8`(보조·밝음)·`--dl-ink-dim:#5b6473`(흐린텍스트) 구분.

## 1. 구현 결정 (locked)

- 모달: `.mlModal` (dialog L928) `min(1040px,96vw)×min(760px,90vh)` → **`min(960px,96vw)×88vh`**. 모바일 override L1427.
- `inspectEvidenceGate`(dialog L185-188): Cockpit 삭제로 dead → **완전 삭제**(`verdictFocusId` L81와 함께). 신규 D블록 GateStrip은 비대화형 `<div>`.
- 콜사이트 9곳(commit2): TerminalSurface 64/241/280, LeftRail 115, ChartMenus 98, ChartRibbon 131, **CenterStack 421**, dialog 21·548(186은 삭제). dialog 24/25/27(tabs)·297·602·799는 §8.1 템플릿 작업서 처리.
- 경로 탭 `<details>` ≤2: `mlEdgeDetails`(기존·L756) 1 + **결합 「심화」 details(scenario+driver-table) 1** = 2.
- `pickFocusCell` tie-break 채널 우선순위 = 명시 배열 `['revenue','margin','valuation','balanceSheet','cashFlow']`(enum 순서 아님 — balanceSheet/valuation 역순).
- `_load_regime`: `_build_transmission` 미싱페이로드 패턴. rc3 전체경로. hamilton maxIter=50 명시.

## 2. macroLens.ts (2809줄) — commit1

- `MacroLensTab` **L6**: 5값 → `'dashboard' | 'transmission' | 'sources'`.
- 삭제 verdict 타입 **L235-380**(연속 블록 통째). `MacroLensSnapshot.verdict` **L418**.
- 삭제 verdict 함수: `signWeight`930-934 · `verdictDirectionLabel`936-946(이미 dead) · `impactDirectionLabel`948-958 · `verdictComponent`960-975 · `contestSideLabel`977-982 · `verdictGateStatus`984-986 · `buildDriverGates`988-1085 · `buildDriverKillChain`1087-1177 · `buildMacroVerdict`1179-1633. **추가 dead:** `sectorEvidenceScore`921-928 · `roundScore`917-919(검증 후).
- **삭제 금지(공유)**: `confidenceScore`859·`freshnessScore`866·`exposureQualityScore`895·`changeIntensity`901·`componentStatus`855·`clamp01`913·`hasCompanyExposureEvidence`870 — 전부 `buildContributionStacks`/`quantEvidenceOpen`(KEEP) 사용. `buildVerdictActions`는 **부재**(buildMacroVerdict 인라인).
- 신규 함수(이관·export): `buildExposureMatrixRows`(현 dialog `buildExposureRows` 134-146 이관·`filledCount` 추가·**cap 6**·filledCount 내림차순 안정정렬) + `pickFocusCell`(observed>sectorPrior>template · tie-break confidence→채널우선순위배열→driverId · 결정성 · 셀0 null).
- 스냅샷 생산자: `buildMacroLensSnapshot` **2595-2689**(verdict const 2627-2639·assign L2684) · `buildMarketMacroLensSnapshot` **2720-2805**(verdict const 2747-2759·assign L2800). verdict const+필드만 삭제, evidenceGates 유지.
- `buildEdges`2167(fallback filter L2172-2173·slice(0,8) L2174) · `buildEdgesFromTransmission`2091(slice(0,12) L2098) · `buildEvidenceGates`2369-2452(5게이트·path status edgeSourceRef기반·**무변경**, quant 제외는 소비단). 전부 KEEP.
- `transitionLabel` 함수 **1754-1763**(`${tr.progress}%` L1757·`transitionLabel:tr.label` L1791 buildRegimeMarket). RegimeMarketView.transitionLabel L453·hasTransitionProgress L454. (superstrengthen서 신규 `transitionFraction`로 대체·재사용 금지.)
- `MacroChannel` L8·`CHANNEL_LABELS` 775-781.

## 3. MacroLensDialog.svelte (1475줄) — commit1

구조: script 1-259 · 템플릿 261-925 · style 927-1475.
- localTab L21·tabs 23-29·렌더루프 280-290.
- 탭 블록: regime **297-601** · drivers **602-637** · transmission **638-798** · scenario **799-820** · sources(bare `{:else}`) **821-922** · `{/if}` 922.
- **CRITICAL nesting**: regime 안 2 sibling `<details>`:
  - `mlVerdictAuditFold` **392-538**: Contest394-412·Compare414-444·Mechanism446-466·Decision468-484·Cockpit486-504·VerdictDrivers506-519 **+ KEEP Phase 521-525 + Pulse 526-537**(여기 들어있음!).
  - `mlEvidenceFold` **539-601**: Matrix541-563(→mlMap)·MobileDrillRail564-572(삭제)·GateStrip573-581·ReleaseRail582-594·Legend595-600(삭제).
- 삭제(regime 위): Hero 298-371·KillChain 373-390. drivers 탭: pressureGrid 609-617(삭제)·mlDriverTable 618-636(→경로 심화 fold).
- mlMatrix: head 542-545·body 546-562·mlMatrixDriver `goto('drivers')` **L548**→transmission·`cellClass` **L154**=edge.confidence→evidenceLevel·`cellLabel` L155.
- script 삭제: verdict $derived 60-64·verdictFocusId 81·topVerdictRelease 82·modelClaimRows 108-127; fn showVerdictOnChart 174-178·inspectVerdictPath 179-181·inspectVerdictSources 182-184·runVerdictAction 189-191·signedScore 160·killStatus 161·inspectEvidenceGate 185-188.
- buildExposureRows 134-146(used L91)→macroLens.ts 이관 호출.
- KEEP 주의: `exposureQualityClass` L93(sources 838 사용)·`pressureText` L52(driver-table)·삭제후보 `compareComponentIds` L56(Compare 전용).
- style 삭제: verdict 949-1144(외과적)·mlXCell.high/medium/low/blocked bg **1182-1185**·mlMobileDrillRail base 1189·legend+pressure 1263-1275·공유규칙 L1157(.mlLegend 토큰만 제거)·미디어 1428/1431-1459/1462-1468(interleaved).
- KEEP base: .mlModal928·.mlBody943(gap 10→12)·.mlMatrix*1169-1188(→mlMap 재설계 base).
- 토큰 미사용→사용: 파일 현재 `--dl-ink/--dl-ink-dim/--dl-line/--amber/--dl-bg-raised` 사용. PRD `--panel/--txt/--bd/--dim` 추가 사용(terminal.css 실재).
- 미디어쿼리 현재 760px만. **560px 신규 추가**(Map 카드 전환).

## 4. 콜사이트 (commit2) — 9곳
TerminalSurface L64`$state('regime')`·L241`openMacroLens(tab='regime')`·L280`openMacroLens('regime','')` → dashboard. LeftRail L115`('regime','KR')`→dashboard. ChartMenus L98`('drivers')`·ChartRibbon L131`('drivers')`·**CenterStack L421`('drivers',k.id)`**→dashboard. (macroLens.ts 1128/1522/1536 verdict 내부 리터럴은 자동소멸.)

## 5. superstrengthen backend (Phase B)
- `macro.py` runMacro: rc1=buildMacroData·rc2=buildMacroCycle(if rc1==0 else 1). runScript=**전체경로**. 실패msg `macro rc=data:{rc1}/cycle:{rc2}`. → rc3=buildMacroRegime(if rc1==0 else 1·rc2무관)·msg `.../regime:{rc3}`. 실제 코드는 `if rc1!=0 or rc2!=0` 형 → `or rc3!=0` 확장.
- `buildMacroCycle.py` 템플릿: `_analyzeMarket`30·`buildCycle`41(for market in (KR,US)·per-market try/except continue)·`deploy`67(`api.upload_file(path_in_repo=f"macro/cycle/{market}.json")`)·`main`90(argparse --out/--repo-id eddmpython/dartlab-data/--push). **신규는 per-axis try/except**(per-market continue 아님).
- `buildMacroJson.py`: `enforceOffline()` **L189**. `_analyze_market`113(step3=_fallback). `_build_transmission`148(미싱페이로드 163-181·**_load_regime 템플릿**). output 219-226(version **"v19"** L220+docstring L3/L10). transmission `_build_transmission()` L217(동결통과). _load_regime 호출 L217~219 사이. version v20.
- `test_prebuild_offline.py`: `_FORBIDDEN_IMPORTS` **L34-40**(5: providers.{dart,edgar,edinet}.openapi + macro.cycles.cycle + macro.seriesFetch). +forecast.forecast·rates.rates → 7. matcher L116(startswith). docstring L11-13 갱신(cosmetic).
- `macroData.yml`: 실재·`dartlab.pipeline macro` 호출 L63·timeout 120 → yml 무수정.

## 6. engine 함수 (Phase B sync 입력 ground-truth)
- `forecast.py::analyzeForecast` L115. recessionProb 227-240(US·KR None 293)·sahmRule None가드 **L342**(>=15)·lei components **246-278(10키 확정)**·availableComponents L287/totalComponents L288·hamiltonRegime 352-375(gdp_id L354·가드 L356 >=20·contractionProb L365=smoothedProbs[-1,1]·**smoothedProbs 드롭 확정**)·nowcast 377-394. import L15 `from dartlab.macro.cycles.regimeSwitching import clevelandProbit, conferenceBoardLEI, hamiltonRegime, sahmRule`.
- `cycles/_regimeSwitchingLei.py`: clevelandProbit 47-123·conferenceBoardLEI 145-262·_LEI_WEIGHTS 131-142·sahmRule 281-352. probit zone **4단**.
- `cycles/_regimeSwitchingHamilton.py`: hamiltonRegime **L139**(maxIter default **200**)·HamiltonResult(mu_expansion/mu_contraction/sigma_expansion/sigma_contraction/phi/p_stay_*/smoothedProbs/converged/iterations·params 351-359)·mu-swap 246-248+330-336(col1=contraction 보장).
- `cycles/regimeSwitching.py`: 4함수 re-export 확정.
- `rates/rates.py::analyzeRates` L104·yieldCurve 234-256·interpretation **L254**(=ns.interpretation 영어enum)·**spread 필드 없음** → spread=forecast.probit.spread.
- `rates/yieldCurve.py::nelsonSiegel`: interp **L151-161** `steep_normal/normal/flat/inverted`(영어enum 확정)·L171 interpretation=interp.
- `crisis/growthAtRisk.py::growthAtRisk` **L65-71**(fciValues,gdpGrowthValues,*,horizon=4,quantiles)·키 currentGaR5/25/median/75/95/currentFCI/tailRisk/tailRiskLabel/skewness/horizon/observations/description·None가드 L138/L149/L160·observations=len(X_raw)=len(fci)-horizon.
- `summary.py::_addGrowthAtRisk` **263-294**·fci.history 271-272·GDP fetch 275·NFCI fallback **284-287**(>=20)·call `_gar(fci,gdp,horizon=4)` L290.
