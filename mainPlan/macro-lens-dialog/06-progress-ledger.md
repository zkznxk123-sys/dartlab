# 06. 진행 원장

상태: v0.7

---

## 2026-06-18

### v0.7 — `macro.transmission` 터미널 배선 + macroExposure 품질 계약

배경:

- `macro.transmission`은 src에 승격됐지만 터미널 Macro Lens는 아직 UI 템플릿 edge를 우선 사용했다.
- 운영자가 "판정형? 누가 판정하는데?"를 지적했으므로 UI는 결론자가 아니라 엔진 산출물·근거 gate 소비자가 되어야 한다.

완료:

- `dashboards/macro.json` prebuild 산출물에 `transmission` payload를 싣는 경로를 추가했다.
- `MacroPort.getTransmission()` 계약을 추가하고 public runtime이 `dashboards/macro.json#transmission`을 market/sector 기준으로 필터링한다.
- fake runtime도 동일한 `drivers/edges/sourceRefs/missing` shape를 반환해 터미널 테스트 셸이 같은 계약을 쓴다.
- `TerminalSurface.svelte`가 선택 종목 업종 기준으로 `runtime.macro.getTransmission({ market: "KR", sectorKey, includeCrossMarket: true })`를 호출한다.
- `MacroLensSnapshot` edge 생성은 `macro.transmission` 산출물을 우선 소비하고, 없을 때만 UI fallback template을 쓴다.
- driver lineage는 `sourceLineage(date/value/unit/artifactPath/status)`가 있으면 pulse/edge에 반영한다.
- `analysis.financial.macroExposure.calcMacroSensitivity`는 지표별 `nObs`, `window`, `frequency`, `lagMonths`, `coverage`, `sourceRef`, `sourceRefs`와 top-level `exposureQuality`를 낸다.
- `tests/analysis/test_macro_exposure_quality.py`로 정량 후보와 macro observation 결손 시 blocked 품질 상태를 고정했다.

검증:

- `python -X utf8 -m pytest tests\analysis\test_macro_exposure_quality.py -q` 통과.
- `python -X utf8 -m pytest tests\macro\test_transmission.py tests\analysis\test_macro_exposure_quality.py -q` 통과.
- `python -X utf8 -m pytest tests\architecture\test_prebuild_offline.py -q` 통과.
- `npm run check -w @dartlab/ui-contracts` 통과.
- `npm run check -w @dartlab/ui-runtime` 통과.
- `npm run check -w @dartlab/ui-surfaces` 통과(기존 Svelte warning만 남음).

NEXT:

1. `MacroLensSnapshot.exposureQuality`가 하드코딩된 잠금 상태가 아니라 `Company.analysis("macro", "매크로민감도")` 또는 public-safe 분석 산출물을 직접 소비하게 바꾼다.
2. 셀 클릭 상세 탭에 `contribution -> co-movement -> falsifier -> source packet` 순서를 실제 interaction으로 연결한다.
3. public macro artifact 갱신 후 `dashboards/macro.json#transmission`이 실제 배포 파일에도 들어갔는지 visual/runtime QA로 확인한다.

### v0.6 — `macro.transmission` src 최소 승격

배경:

- Macro Lens의 첫 화면 gate와 matrix는 UI view-model로 정리됐지만, `OBS/PRIOR/TPL` edge의 원천이 아직 UI 임시 번역에 가까웠다.
- 강한 분석의 본체는 UI가 아니라 `macro.transmission`과 analysis macro exposure 품질 산출물이어야 한다.

완료:

- `src/dartlab/macro/transmission/transmission.py`를 추가했다.
- 공개 축 `dartlab.macro("transmission", market="KR", sectorKey="semiconductor")`를 `_AXIS_REGISTRY`에 등록했다.
- 산출물은 회사 객체 없이 `drivers`, `edges`, `regimeEvidence`, `sourceRefs`, `missing`만 반환한다.
- 각 driver는 canonical id, sourceSeriesId, sourceLineage(`date/value/unit/artifactPath/status`)를 가진다.
- 각 edge는 `driver -> sector -> financialLine -> valuationLever`와 `evidenceLabel(OBS/PRIOR/TPL)`, requiredCompanyEvidence, falsifier를 가진다.
- `macro` 엔진은 `analysis`, `Company`, terminal UI state를 import하지 않는다.
- `engines.macro` Skill OS 원문을 14축 공개 계약으로 갱신했다.

검증:

- `python -X utf8 -m pytest tests\macro\test_transmission.py -q` 통과.
- `python -X utf8 -m pytest tests\_attempts\macroLensEngine\test_macroLensEngine.py -q` 통과.

NEXT:

1. `analysis.macroExposure`가 `nObs/R²/window/lag/coverage/sourceRef`를 안정적으로 내도록 회사 단위 품질 산출물을 보강한다.
2. UI `MacroLensSnapshot`의 edge 생성은 다음 단계에서 `dartlab.macro("transmission")` 산출물을 우선 입력으로 받게 바꾼다.

### v0.5 — 매크로 대시보드 시각화 방식 조사

배경:

- 운영자가 "매크로 분석에 쓰이는 대시보드 시각화를 조사해라"라고 요청했다.
- 결론: Macro Lens는 화려한 chart gallery가 아니라 `지표 상태`, `전파 경로`, `증거 잠금`, `source/date/value lineage`를 한 화면에서 읽는 계기판이어야 한다.

조사 대상:

- FRED Dashboard: graph, table, single value, data list, note, map widget 조합.
- OECD Short-Term Indicators Dashboard: G20/지역 aggregate의 short-term macro chart/table, 월 2회 업데이트, codebook/frequency/unit/coverage 제공.
- Atlanta Fed GDPNow: running estimate, official forecast 아님, subcomponent contribution과 update history.
- NY Fed GSCPI: supply chain pressure composite index와 방법론/한계.
- World Bank DataBank/BIS Data Portal: query, chart/table/map, metadata, topic dashboard, data story.
- IMF DataMapper/ECB Data Portal: 국가·지역 비교 chart/map와 hover data point.

제품 결정:

- P0 첫 화면: phase strip, driver pulse strip, exposure matrix, evidence gate rail, source stamp.
- P1 상세 탭: contribution waterfall, update path chart, co-movement scatter, falsifier rail, data packet drawer.
- P2 후순위: country map, peer comparator, scenario fan chart, data story canvas.
- 첫 화면 금지: gauge, donut, 단일 macro score, 뉴스 카드 wall. 원인·경로·결손을 숨기기 때문이다.
- 조사 방식은 차트 종류가 아니라 질문 처리 방식으로 재분류했다. 첫 화면은 `상태 위젯형`, `시계열형`, `매트릭스형`, `반증형`, `원천 패킷형`만 채택한다.
- `기여도 분해`, `업데이트 경로`, `비교`, `불확실성 band/fan`은 셀 클릭 후 상세 탭으로 둔다.

문서 반영:

- [08-dashboard-visual-patterns.md](08-dashboard-visual-patterns.md)를 v0.3으로 확장했다.

NEXT:

1. P1 상세 탭을 만들 때 `contribution -> co-movement -> falsifier -> source packet` 순서를 유지한다.
2. 첫 화면에는 map/fan/story canvas를 넣지 않는다. 회사별 매크로 노출을 읽는 속도가 떨어진다.
3. 엔진 승격 시 `evidenceGates`와 `exposureQuality`가 P0/P1 시각화의 직접 입력이 되게 한다.

### v0.4 — 대시보드형 증거 상태판 전환

배경:

- 운영자가 "판정형? 누가 판정하는데?"라고 지적했다.
- 결론: 제품은 투자판단자가 아니다. Macro Lens는 `노출 후보`, `전파 경로`, `커버리지`, `신선도`, `동행상관 상태`, `정량 claim 잠금 사유`를 보여주는 증거 상태판이어야 한다.

완료:

- 첫 탭을 `국면`에서 `대시보드`로 전환했다.
- 첫 화면을 `Macro Phase Strip`, `Driver Pulse Strip`, `Exposure Matrix`, `Evidence Gate`, `Legend`로 재구성했다.
- `판정`, `목표주가`, `매수/매도`, `수혜 확정/피해 확정`처럼 추천 또는 단정으로 읽힐 수 있는 UI 문구를 제거했다.
- matrix 셀은 `OBS/PRIOR/TPL/LOCK/·`처럼 증거 단계만 표시한다.
- `MacroLensSnapshot.evidenceGates`를 추가해 첫 화면 gate를 UI 추론이 아니라 view-model 계약으로 고정했다.
- `exposureQuality`에 `blockedReason`, `missingEvidence`, `frequency`, `sourceRef`를 추가했고, co-movement에는 `window`를 붙였다.
- `missing`은 문자열 배열에서 `{status, reason, sourceRef}` 구조로 전환했다.
- 공식 매크로 대시보드 조사 결과를 [08-dashboard-visual-patterns.md](08-dashboard-visual-patterns.md)에 추가했다.

검증:

- `npm run check -w @dartlab/ui-surfaces` 통과(기존 Svelte warning만 남음).
- `python -X utf8 tests\audit\dartlabGuard.py quick` 통과.
- Playwright 브라우저 확인: `대시보드` 탭에서 phase 3개, pulse 6개, matrix 6행/30셀, gate 5개, legend 4개 렌더링 확인.

NEXT:

1. `macro.transmission` src 승격 시 `OBS/PRIOR/TPL/LOCK` 라벨을 UI 임시 번역이 아니라 엔진 lineage 산출물로 제공한다.
2. `analysis.macroExposure`가 `nObs/R²/window/lag/coverage/sourceRef`를 내기 전까지 민감도/beta는 계속 잠근다.
3. co-movement 숫자 노출은 `corr + n + window`가 모두 있을 때만 허용한다.

### v0.3 — Phase 1~4 구현 완료

완료:

- 터미널 Macro Lens 다이얼로그가 `국면`, `지표·Driver`, `전파 지도`, `시나리오`, `출처·한계` 5탭으로 구현됐다.
- 기존 마켓 펄스, KPI ticker, 차트 ECON 메뉴/리본 입구를 재사용한다.
- `MacroLensSnapshot` view-model이 driver, transmission edge, company checkpoint, falsifier, scenario, source/limit를 만든다.
- UI의 단일 숫자 pressure score 노출을 제거했다. 대신 `우선 경로`, `품질`, `company evidence`, `readiness`를 표시한다.
- 모바일/좁은 폭에서도 driver row의 ECON 토글 액션이 사라지지 않게 했다.
- `tests/_attempts/macroLensEngine/`가 샘플 계약 저장소에서 순수 실행 proof로 강화됐다.
  - `macroLensEngine.py`: driver registry + transmission edge + lagged co-movement + exposure quality + scenario readiness 조립.
  - `test_macroLensEngine.py`: 최소 driver/sector, lag/R² 후보, partial evidence, look-ahead, stale, source/date/value lineage, snapshot shape 검증.
  - `validateSamples.py`: JSON 필드 검증 + 실제 attempt snapshot 생성 검증.
  - sample JSON v2: `confidence`, `rSquared`, `sourceSeriesId`, `sourceRefs`, alias registry를 production 후보 이름으로 고정.

검증:

- `python -X utf8 tests/_attempts/macroLensEngine/validateSamples.py` 통과.
- `python -X utf8 -m pytest tests/_attempts/macroLensEngine/test_macroLensEngine.py -q` 통과.
- `npm run check -w @dartlab/ui-surfaces` 통과(기존 Svelte warning만 남음).

판정:

- Phase 1~3 터미널 제품 단위와 Phase 4 attempts proof는 완료.
- `macro.transmission`과 `analysis.macroExposure`의 `src/dartlab` 승격은 아직 하지 않는다. 승격 전에는 attempts 계약을 production API로 옮기고 architecture guard를 통과해야 한다.

NEXT:

1. `macro.transmission` 축 후보를 `src/dartlab/macro`에 추가한다. 반환은 `drivers`, `edges`, `regimeEvidence`, `sourceRefs`, `missing`으로 제한하고 회사 import 0을 지킨다.
2. 기존 `Company.analysis("macro", "매크로민감도")` 표면을 유지한 채 `analysis.macroExposure` 품질 라벨(`nObs/rSquared/window/frequency/lag/coverage/status/blockedReason/missingEvidence/sourceRef`)을 보강한다. 후보 문구였던 `company.analysis("macroExposure")`는 현재 registry와 맞지 않으므로 바로 쓰지 않는다.
3. source/date/value lineage는 실제 observation artifact 경로, 원본 series id, 기준일, 값, 단위, asOf policy까지 검증한다.
4. src 승격 시 targeted test + `dartlabGuard.py quick` + architecture/cycle guard를 통과시킨다.

---

## 2026-06-17

### v0.2 — 엔진 강화 반영

배경:

- 운영자가 "분석에 핵이 될 수 있게, 필요하면 매크로 엔진도 개선"을 요청했다.
- v0.1은 다이얼로그와 재사용 자산 중심이라 첫 화면 구현에는 안전하지만, 분석 코어로는 약했다.

추가 결정:

- Macro Lens는 UI 기능이 아니라 `Macro Driver → Transmission Edge → Company Exposure → Financial Checkpoint → Valuation Lever → Falsifier` 사슬이다.
- `macro` 개선은 허용한다. 단, 새 독립 L2 엔진이 아니라 기존 macro의 시장·섹터 전파 축(`macro.transmission`) 후보로 둔다.
- `macro.transmission`은 회사/analysis 내부를 import하지 않는다.
- 회사별 민감도와 회귀 품질은 기존 analysis macro 표면 확장 후보로 둔다.
- 엔진 강화는 `tests/_attempts/macroLensEngine/` proof를 먼저 만든 뒤 src 승격을 결정한다.
- canonical id는 `MACRO_SERIES.id`를 기준으로 한다. 레거시 id는 alias registry 없이는 edge에 쓰지 않는다.

NEXT:

1. 구현 go가 있으면 Phase 1~3 다이얼로그 제품 단위를 먼저 만든다.
2. 엔진 go가 있으면 `tests/_attempts/macroLensEngine/`에 driver registry/edge/quality 샘플과 실패 케이스를 만든다.
3. attempts proof 후 `macro.transmission`과 `analysis.macroExposure` 승격 범위를 결정한다.

착수 상태:

- 코드 작업 전.
- 문서만 v0.2로 보강.

---

### v0.1 — 최초 기획

결정:

- `경제지표분석` 강화는 `Macro Lens` 다이얼로그로 기획한다.
- 당시에는 새 L2 엔진이 아니라 기존 `dartlab.macro`, `MacroPort`, `macro.json`, `sectorTailwind`, 차트 co-movement를 묶는 UI 제품으로 시작한다고 정했다.
- 강한 분석의 중심은 `Macro → Sector → Company → Financial → Valuation` 전파 사슬이다.
- 상주 패널 추가는 금지한다. 기존 좌측 마켓 펄스, KPI ticker, 차트 ECON을 진입점으로 재사용한다.
- 첫 구현은 5탭 이하: `국면`, `지표·Driver`, `전파 지도`, `시나리오`, `출처·한계`.
- 회사별 회귀/민감도 심층화는 품질 라벨 계약 전까지 Phase 5로 둔다.

전문 관점 토론:

- 금융/매크로 렌즈: 전파 경로, 민감도 품질, co-movement 반증, 현금흐름 흡수력, 밸류에이션 전파가 핵심.
- 터미널 UX/PM 렌즈: 한 다이얼로그 5탭, 기존 진입점 재사용, 차트 복제 금지, 30초 4문장 성공 기준.
- 아키텍처/데이터 렌즈: public/local 공통배선, UI view-model first, 새 artifact는 시장 단위만, L2 내부 import 금지.

NEXT:

1. 운영자 go가 있으면 구현 전 현재 `ui/packages/surfaces/src/terminal`와 runtime audit 명령을 재확인한다.
2. Phase 1 다이얼로그 shell부터 구현한다.
3. 구현 후 public/local visual QA와 data wiring audit를 통과시킨다.

착수 상태:

- 코드 작업 전.
- 문서만 작성.
