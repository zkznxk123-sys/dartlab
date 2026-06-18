# 06. 진행 원장

상태: v1.4

---

## 2026-06-18

### v1.4 — 모바일 드릴다운 포커스 보강

배경:

- 브라우저 QA에서 좌측 매크로 카드의 `상세보기`가 `focusId='KR'`로 다이얼로그를 열면, `전파 지도`의 기본 drilldown이 유효 driver가 아닌 market-level focus에 묶이는 문제가 확인됐다.
- 모바일에서는 matrix가 가로 스크롤 표로 유지되기 때문에, 작은 셀 클릭을 주 진입로로 삼으면 drilldown 발견성과 조작성이 약했다.

완료:

- `MacroLensDialog`가 `focusableIds`를 만들고, 외부 `focusId`가 실제 driver/series 계약에 맞을 때만 `activeFocusId`로 채택하게 했다.
- 기본 focus는 유효한 `topPressures` driver, 관측점 보유 `coMoveGates`, relevant driver 순서로 회수한다.
- `focusIndicator`는 더 이상 `sourceRef.includes()`로 느슨하게 맞추지 않고 `seriesId/sourceRefs`의 정확한 id만 사용한다.
- 모바일 대시보드에 `Mobile Drill Rail`을 추가했다. 6개 큰 터치 타깃이 `전파 지도`로 이동하며 기존 matrix, release rail, source packet, contribution, co-movement gate와 같은 focus를 공유한다.
- 데스크톱에서는 모바일 레일을 숨기고 기존 matrix를 유지한다.

검증:

- `npm run check -w @dartlab/ui-surfaces` 통과(기존 Svelte warning 46개 유지).
- Playwright desktop: 좌측 `상세보기`로 열린 `KR` focus 경로에서 `전파 지도` 클릭 시 `Co-movement Gate`, 산점도 72점, latest 1점, `인과 아님`, formula 표시, 수평 overflow 없음 확인.
- Playwright mobile: `Mobile Drill Rail` display `grid`, 버튼 6개, 첫 버튼 클릭 시 `전파 지도`와 산점도 72점, latest 1점, `인과 아님`, formula 표시, 수평 overflow 없음 확인.

NEXT:

1. 실제 발표 캘린더/빈티지 데이터가 생기면 산점도와 별도로 release reaction view를 검토한다. 현재 scatter는 발표일 반응 분석이 아니다.
2. `analysis.macroExposure`의 표본 길이가 늘어나도 `OPEN/정량 민감도`는 품질 gate 뒤에 둔다.

### v1.3 — 관측점 기반 Co-movement Scatter 구현

배경:

- v1.2의 `Co-movement Gate`는 corr 위치 막대만 있어서 “표본이 실제로 어떻게 생겼는지”를 볼 수 없었다.
- 전문 UI/매크로 비평 결과, 새 탭이나 첫 화면 노출은 금지하고 기존 `전파 지도` drilldown 안에서 반증 도구로만 쓰는 방향이 맞았다.

완료:

- `rankCoMovers()`가 corr/n만 반환하지 않고 월별 `ym`, `stockReturn`, `macroDiff` 관측점 배열을 함께 반환한다.
- `MacroCoMoveGateView`가 산점도용 `points`, `displayedPoints`, `lagLabel`, `formula`, `limitations`, `x/y zero axis`, `x/y range`를 가진다.
- `MacroLensDialog`의 `Co-movement Gate`는 점 배열이 있으면 실제 산점도를 그리고, 없으면 기존 corr 위치 gate를 fallback으로 유지한다.
- UI는 `corr n`과 `shown`을 분리 표기한다. corr 계산 표본과 화면 표시점 수가 다를 때도 오해하지 않게 하기 위함이다.
- 산점도 옆에 `lag 0M`, `x=거시 월말값 1차차분 · y=종목 월수익률`, `월말 겹침 표본`, `발표일·revision 미반영`, `outlier·우연상관 민감`을 고정 표시한다.
- 회귀선, beta, 설명력, 수혜/피해 색상은 추가하지 않았다. 산점도는 전파 증명이 아니라 동행 후보와 반증 조건 확인용이다.

검증:

- `npm run check -w @dartlab/ui-surfaces` 통과(기존 Svelte warning 46개 유지).

NEXT:

1. Playwright로 desktop/mobile에서 점이 보이고 텍스트가 겹치지 않는지 확인한다.
2. `analysis.macroExposure`의 품질 계약이 더 길어진 표본을 공급하기 전까지 `OPEN/정량 민감도`는 계속 품질 gate 뒤에 둔다.
3. 발표일·빈티지 데이터가 생기면 산점도와 별도로 release reaction view를 검토한다. 현재 scatter는 발표일 반응 분석이 아니다.

### v1.2 — Release/Source/Contribution 시각화 구현

배경:

- 운영자가 "구현할만하나" 이후 실제 구현을 요청했다.
- 전문 UI 리뷰 결과, 새 탭을 늘리지 말고 기존 matrix와 drilldown에 `Release Rail`, `Source Packet`, `Contribution Mini Drilldown`, `Co-movement Gate`를 붙이는 방향이 맞았다.

완료:

- `MacroLensSnapshot`에 `releaseRail`, `sourcePackets`, `contributionStacks`, `coMoveGates`를 추가했다.
- `releaseRail`은 driver별 마지막 관측일, freshness 상태, 다음 확인 시점, stale policy를 구조화한다. 실제 발표 캘린더를 꾸미지 않고 현재 관측 artifact 기준의 freshness policy로만 표시한다.
- `sourcePackets`는 `seriesId/source/unit/frequency/asOf/latest/change/transform/artifactPath/lineage/status`를 구조화해 UI 문자열 파싱을 없앴다.
- `contributionStacks`는 driver가 화면에 올라온 이유를 `최근 변화`, `전파 경로`, `동행 후보`, `신선도`, `회사 품질`로 분해한다. 방향성 점수나 투자 결론이 아니다.
- `coMoveGates`는 원시 관측점 배열이 없으므로 가짜 산점도를 만들지 않고 corr 위치 gate로 표시한다.
- 첫 화면 `Evidence Gate` 아래에 `Release Rail`을 붙였다.
- `전파 지도` 상단 drilldown을 `전파 chain / 품질 gate / contribution / source packet` 4칸으로 재구성했다.
- matrix cell, pulse, release rail, source packet 선택이 `localFocus` 하나로 같은 driver를 가리키게 했다.
- [02-data-contract.md](02-data-contract.md)와 [README.md](README.md)를 새 구현 계약에 맞췄다.

검증:

- `npm run check -w @dartlab/ui-contracts` 통과.
- `npm run check -w @dartlab/ui-surfaces` 통과(기존 Svelte warning 46개 유지).

NEXT:

1. 원시 co-movement 관측점 배열이 공개 계약으로 올라오면 corr 위치 gate를 실제 산점도로 승격한다.
2. 실제 발표 캘린더/빈티지 데이터가 들어오기 전까지 Release Rail은 freshness policy로만 표시한다.
3. visual QA로 desktop/mobile에서 release rail과 drilldown 4칸이 겹치지 않는지 확인한다.

### v1.1 — 매크로 대시보드 시각화 방식 재조사 보강

배경:

- 운영자가 "매크로 분석에 쓰이는 대시보드 시각화를 조사해라. 방식들"을 다시 요청했다.
- 이전 문서는 방향은 맞았지만, "판정형"으로 오해될 수 있는 지점과 실제 화면 문법의 실패 신호가 부족했다.

완료:

- [08-dashboard-visual-patterns.md](08-dashboard-visual-patterns.md)를 v0.5로 갱신했다.
- FRED, OECD, ECB, IMF, Atlanta Fed GDPNow, Chicago Fed NFCI, NY Fed GSCPI, OFR FSVM, BIS Credit-to-GDP gaps, World Bank DataBank 사례를 다시 확인했다.
- 공식 사례에서 반복되는 규칙을 별도 표로 뽑았다.
  - 최신값은 단독으로 두지 않는다.
  - 국면 음영에는 기준 주체가 필요하다.
  - 복합지수는 구성요소 기여도 없이 headline으로 쓰지 않는다.
  - heatmap은 결론이 아니라 추가 조사 신호다.
  - metadata/source/frequency/coverage는 차트와 같은 레벨이다.
- `OBS/PRIOR/TPL/LOCK/OPEN/QUAL/STALE/MISSING` 상태가 누가 만드는지 명시했다. 사람, AI, UI 문구가 아니라 `macro.transmission`, `macroExposure.exposureQuality`, source lineage, freshness policy가 만든다.
- `대시보드 문법`을 추가해 Phase Strip, Driver Pulse, Exposure Matrix, Evidence Gate, Release Rail, Drilldown Packet, Contribution/Scatter의 읽을 것과 실패 신호를 정리했다.
- [README.md](README.md)에 "시각화는 판정을 만들지 않는다"는 상위 결정으로 반영했다.

검증:

- 문서 변경만 수행했다. 코드·데이터 산출물 변경 없음.

NEXT:

1. UI에서 `Release Rail`과 `Contribution/Scatter`가 아직 P1이므로, 구현 시 첫 화면이 아니라 matrix 셀 클릭 상세 아래에만 붙인다.
2. heatmap, map, fan chart는 데이터 계약이 열릴 때까지 계속 P2/금지로 둔다.

### v1.0 — Matrix drilldown evidence packet

배경:

- 첫 화면 matrix는 강해졌지만 셀 클릭 후 `contribution -> co-movement -> falsifier -> source packet` 흐름이 아직 약했다.
- 사용자에게 더 많은 문단을 주는 대신, 선택 driver의 전파 chain과 품질 gate를 한 화면에서 묶어야 했다.

완료:

- `MacroLensSnapshot.exposureIndicators`를 추가해 `finance.json#macroExposure.selected`의 지표별 `seriesId/R²/nObs/window/sourceRef/sourceRefs`를 UI 패킷으로 전달한다.
- Macro Lens 다이얼로그 내부 focus state를 추가했다. matrix driver/cell 클릭 시 선택 driver를 유지한 채 `drivers` 또는 `transmission` 탭으로 이동한다.
- `전파 지도` 탭 상단에 drilldown 패킷을 추가했다.
  - `전파 chain`: driver → sector → financial line → valuation lever.
  - `품질 gate`: `OPEN/QUAL/LOCK`, `R²`, `nObs`, `window`.
  - `필요 증거`: edge의 company evidence 또는 quality missing evidence.
  - `source packet`: selected macro exposure sourceRef, driver lineage, falsifier.
- UI가 새 계산을 만들지 않고 snapshot에 들어온 공개 산출물만 표시하게 유지했다.

검증:

- `npm run check -w @dartlab/ui-contracts` 통과.
- `npm run check -w @dartlab/ui-surfaces` 통과(기존 Svelte warning 46개 유지).

NEXT:

1. 실제 브라우저 visual QA로 matrix 셀 클릭 → drilldown 패킷 전환이 모바일/데스크톱에서 읽히는지 확인한다.
2. P1 상세 탭에 waterfall/scatter 차트가 필요하면 이 drilldown 패킷 아래에만 붙인다. 첫 화면에는 추가하지 않는다.

### v0.9 — 회사 macroExposure 품질의 public terminal 소비

배경:

- `analysis.macroExposure`는 `nObs/R²/window/lag/coverage/sourceRef` 품질 계약을 냈지만, Macro Lens UI는 아직 `analysis.macroExposure pending` 하드코딩 상태를 표시했다.
- 새 per-company artifact는 금지되어 있으므로 기존 public terminal data path 안에서 해결해야 했다.

완료:

- `macroExposure.calcMacroExposureFromAnnualRevenue()`를 추가해 회사 객체 없이 연매출 배열과 macro observation 연평균으로 `exposureQuality`를 계산하게 했다.
- `buildFinanceJson.py`가 `data/macro/{ecos,fred}/observations.parquet`, `data/kindList/corpList.parquet`, `data/dart/scan/productIndex.parquet`를 로컬/offline으로 읽고 기존 `dashboards/finance.json#companies[*].macroExposure`에 품질 패킷을 포함한다.
- `FinanceCompany`와 terminal `Company` 타입에 `macroExposure`를 추가했다.
- `buildCompany()`가 raw finance의 `macroExposure`를 `Company`로 전달한다.
- `MacroLensSnapshot.exposureQuality`가 `co.macroExposure.exposureQuality`를 우선 소비하고, 없을 때만 fallback pending lock을 만든다.
- Evidence Gate의 `회사노출`과 `민감도`는 `quantCandidate/qualitativeOnly/blocked` 상태에 따라 `OBS/PRIOR/LOCK`, `OPEN/LOCK`으로 표시된다.
- 출처·한계 탭은 실제 `nObs/R²/window/frequency/lag/sourceRef`를 표시하고, 결손 증거가 있을 때만 `필요 증거` 줄을 노출한다.
- `landing/static/dashboards/finance.json`을 재생성했다. 예: `005930`은 `analysis.macroExposure:005930:USDKRW`, `nObs=3`, `R²=0.991`, `window=2023-2025 annual`, `qualitativeOnly`로 잠긴다.

검증:

- `python -X utf8 -m pytest tests\analysis\test_macro_exposure_quality.py -q` 통과.
- `uv run ruff check src\dartlab\analysis\financial\macroExposure.py .github\scripts\prebuild\buildFinanceJson.py tests\analysis\test_macro_exposure_quality.py` 통과.
- `python -X utf8 .github\scripts\prebuild\buildFinanceJson.py` 통과, `finance.json` 2802사 생성.
- `python -X utf8 -m pytest tests\macro\test_transmission.py tests\analysis\test_macro_exposure_quality.py tests\architecture\test_prebuild_offline.py tests\architecture\test_l2_no_cross_import.py -q` 통과.
- `npm run check -w @dartlab/ui-contracts` 통과.
- `npm run check -w @dartlab/ui-runtime` 통과.
- `npm run check -w @dartlab/ui-surfaces` 통과(기존 Svelte warning 46개 유지).
- `python -X utf8 tests\audit\dartlabGuard.py quick` 통과.

NEXT:

1. `finance.parquet`가 현재 2021~2025만 포함해 대부분 종목은 `nObs<5`로 `qualitativeOnly`가 된다. 정량 gate를 더 자주 열려면 prebuild 입력에 더 긴 연간 매출 이력을 공급해야 한다.
2. 셀 클릭 상세 탭에 `Contribution Waterfall`, `Co-movement Scatter`, `Model Card Drawer`, `Source Packet` 상호작용을 붙인다.
3. visual/runtime QA로 `회사노출` gate가 실제 품질 상태를 표시하는지 확인한다.

### v0.8 — 매크로 대시보드 시각화 방식 재조사

배경:

- 운영자가 "매크로 분석에 쓰이는 대시보드 시각화를 조사해라. 방식들"이라고 요청했다.
- 이전 조사 문서는 방향은 맞았지만, `판정형`으로 오해될 여지가 남아 있었다.

완료:

- [08-dashboard-visual-patterns.md](08-dashboard-visual-patterns.md)를 v0.4로 다시 정리했다.
- FRED, OECD, ECB, IMF, Atlanta Fed GDPNow, Chicago Fed NFCI, NY Fed GSCPI, OFR Vulnerabilities Monitor, BIS Credit-to-GDP gaps, World Bank DataBank 사례를 시각화 방식 기준으로 재분류했다.
- `상태 압축형`, `전파 경로형`, `분해·기여도형`, `업데이트·빈티지형`, `품질·반증형`, `비교·분포형`, `원천 패킷형`으로 카탈로그를 나눴다.
- "누가 판정하나"에 대한 제품 답을 명확히 했다. AI나 UI가 판정하지 않고, `macro.transmission`, `analysis.macroExposure`, 공개 데이터의 `asOf/source/frequency/coverage`가 gate 상태를 만든다.
- 첫 화면 구조를 `Phase Strip -> Driver Pulse -> Exposure Matrix -> Evidence Gate/Release Rail -> Source Drawer`로 고정했다.
- 금지 시각화를 `gauge`, `donut`, 단일 macro score, 뉴스 카드 wall, 첫 화면 지도, 출처 없는 heatmap, 모델 분포 없는 fan chart로 명확히 했다.

NEXT:

1. P0 화면은 `Driver Pulse Strip`, `Exposure Matrix`, `Evidence Gate Rail`, `Source Stamp`, `Release Rail`, `Falsifier Rail`만 남긴다.
2. P1 상세는 `Contribution Waterfall`, `Update/Vintage Path`, `Co-movement Scatter`, `Model Card Drawer` 순서로 설계한다.
3. UI 문구에서 `판정`, `수혜 확정`, `피해 확정`, `좋음/나쁨`을 계속 금지하고 `OBS/PRIOR/TPL/LOCK/STALE/MISSING` 상태만 사용한다.

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
