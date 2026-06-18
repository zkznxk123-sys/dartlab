# 01 — 현 상태 정밀 인벤토리 (가진 것 vs 표면화한 것)

> 모든 줄번호는 2026-06-19 실측. 적대검증 5인이 in-code 확인. 핵심 4개는 이번 세션 재확인 완료.

## 1. 데이터 수집 vs 표면화 갭 (요약)

| 영역 | 수집(parquet/contract) | 현재 표면화 | 갭(버려지는 것) |
|---|---|---|---|
| 인력·생산성 | `report.workforce()` → 전 연도 `WorkforceYear[]` (총/남/여/정규/계약/평균급여/근속) | `RightStack` 인라인 `wfLast`(최신 1년) 6개 평면 팩트. FinFullscreen PEOPLE 탭에 풍부 차트(묻힘) | 전 연도 시계열·정규vs계약 추세·급여vs생산성 갭. **인력 패널만 `상세보기` 없음** |
| 주주환원 | `report.shareholderReturn()` → 전 연도 `ShareholderReturnYear[]` (배당·소각`buybackCancel`·취득·처분·payout·yield) | `RightStack` 인라인 `srLast`(최신 1년). 취득/처분 raw 주식수만 | **`buybackCancel`(소각) fetch 후 버림** — 진짜vs화장 환원의 단 하나 필드. 전 연도 흐름·배당 streak |
| 타법인출자·소유 | `report.investments()` + `report.shareholderPeriods()` → 전 기간. `holdings.ts buildHoldingsModel` 이 lossPct·contribShare·pctOfParentCap·control 계산 | `RightStack` 5컬럼 인라인 표 + `HoldingsDialog`(Sankey 관계망, 세계급) | lossPct·control-shift·pctOfParentCap 이 **다이얼로그 안에 갇힘**. `shPeriods` 전 기간 fetch 되나 최신 1개만 사용 |
| 생산·설비·가동률 | NARRATIVE only (`sectionMappings.json rawMaterial`) — 구조화 컬럼 0, scan parquet 없음 | 없음 | 구조화 불가. honest = 원문 발췌만 |
| R&D 집약도 | `calcRndExpense`(costStructure.py) = **이미 완성 엔진**. 59.7% 커버(센서스 측정) | 없음(터미널 grep 0 hits) | scan parquet 부재 → 공개 HF read 경로 없음(CI bake 필요) |
| 세그먼트 | `_noteCellsFromPanel('NT_D871100')` — axis-tagged clean 4.6%(67/1465) | 없음 | 95% unusable → 범용 카드 불가(blocked) |

## 2. P0 스파인의 토대 — `rcept_no` 가 버려진다 (실측)

**`landing/src/lib/browser/companyLive.ts`**
- `L266` `loadLiveCompanyReportFacts(stockCode)` — 6개 report parquet 을 평면 팩트로.
- SELECT 6개: `L281`(dividend, `year, stlm_dt, se, thstrm, frmtrm, lwfr`) · `L288`(treasury) · `L295`(executive) · `L303`(auditOpinion) · `L310`(majorHolder) · `L317`(corporateBond).
- **결정적**: 6개 SELECT 어디에도 `rcept_no` 없음. `stlm_dt` 는 dividend(L281)만 가져오고 `L1126` 에서 `[year, stlm_dt].join(' · ')` 디테일 문자열로만 매장. → **팩트가 원문 공시로 클릭 이동 불가, as-of 가 헤더에 안 뜸.**
- `rcept_no` 는 모든 report parquet **행에 존재**(엔진측 `reportSource.ts` 가 dedupe·`fy=rcept_no.slice(0,4)-1` 에 사용). 즉 **SELECT 6곳에 컬럼 추가 = 줄단위 저비용 언락**.

## 3. ↗원문 배선 — 정정 사실 (실측)

- 정확한 딥링크: `ui/packages/surfaces/src/viewer/lib/dartUrl.ts:14` `viewerUrl(market, rceptNo)` → `https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rceptNo}`. `marketForCode` 동일 모듈.
- **함정**: 토론 초안이 인용한 `rt.viewer.urlForCompany` 는 **public 에서 설계상 `null`** 반환(`createPublicRuntime.ts:47` 주석 "urlForCompany → null"). 로컬 임베드 iframe 전용(`ViewerOverlay.svelte:30`).
- → ↗원문 은 `viewerUrl(marketForCode(code), rceptNo)` + `ViewerPort.openFiling({url})` 로 배선(공개+로컬 동일). 로컬은 추가로 임베드 오버레이 가능하나 floor 는 외부 DART 링크.

## 4. 우측 레일 패널 지형 (실측, RightStack.svelte)

| 줄 | 패널 | `상세보기` | 비고 |
|---|---|---|---|
| L520 | `DART 정기보고서 팩트` (평면) | 없음 | dividend/treasury 를 주주환원 패널과 **중복** 표면화 → 리본으로 흡수(−1) |
| **L541** | `인력 · 생산성` | **없음(유일)** | report 패널 중 `상세보기` 없는 단 하나 → 추가 → FinFullscreen PEOPLE |
| L555 | `주주환원` | 없음 | `srLast` 평면 → 환원흐름 문장 + `상세보기` → FinFullscreen RETURN(SHAREHOLDER) 탭 |
| L569/570 | `타법인 출자` | 있음(→`holdingsOpen` `HoldingsDialog`) | 헤더에 lossPct + control-shift 한 줄(표 5컬럼 불변) |
| L437/438 | `업종 내 백분위` | 있음(→`pctCrossOpen` `PercentileCrossDialog`) | 인적자본 축 1개 추가 지점 |
| L745 | `거버넌스 · 현금흐름` | — | 소유 섹션 연계 |

## 5. 갇힌 계산들 (이미 코드에 있고, 표면화만 안 됨)

- **인적자본 효율 엔진 (Phase 2)**: `src/dartlab/scan/workforce/scanner.py` + `growth.py` — `scanValueAdded()`=(영업이익+급여)/직원수, `scanLaborRatio()`, `computeSalaryVsRevenue()`=급여매출괴리, `scanTopPay()`. 전부 유니버스-wide·가드 클램프(근속>60y·급여>50억→null·±500% clamp). **단 `scanRevenuePerEmployee()` 만 baked**(`snapshot.py L161`); 나머지는 Python 안에서 dead-end, UI 배선 0.
- **R&D 엔진 (Phase 2)**: `src/dartlab/analysis/financial/costStructure.py` `calcRndExpense` — **이미 graduated 완성 엔진**(9섹션 docstring·`@memoizedCalc`·2-tier IS라인→`NT_D834310/834315` 주석 fallback·`_inferNoteUnitScale` 단위추론·available-flag 정직). *재graduate 할 것 없음.* 센서스: `tests/_attempts/segmentRndExtraction/outputs/census_shard0.json` R&D any 874/1465=59.7%, 세그먼트 axis-tagged 67/1465=4.6%.
- **타법인출자 모델 (P0/P1, 새 fetch 0)**: `ui/.../terminal/lib/holdings.ts buildHoldingsModel()` — `pctOfParentCap`/`sumEquityEarn`/`contribShare`(L113-116), lossPct=lossBook/bookTotal(`HoldingsDialog` L120-121), `mutualCodes`, `invTrend`. **함정**: `contribShare` 의 분모 `parentNet=mktcap/PER`(L27-28, 다이얼로그가 이미 '참고·미산출' 로 hedge L207) — 상시 헤드라인 승격 시 추정을 prime fact 로 둔갑 → 보고 `fin.is.net`(engine.ts L594/L707) 재배선 또는 라인 삭제.
- **control-shift (P1, 새 helper)**: `reportSource buildShareholderPeriods()`(L363-383)가 전 기간 `named[]` 반환하나 `shareholders()` 는 `.at(-1)` 최신 1개만. → `controlShiftSummary(periods)` 순수 helper 로 기간 간 `named[]` diff(법인·기관만, 개인은 익명 집계 Δ). 새 fetch 0.

## 6. 백분위 머신 (재사용 자산)

`engine.ts` `mk()`(L479)+`pctRank`(L181)+`buildFundMetrics`(L461) + `DistCurve.svelte`(`neutral` 그레이핀 모드 있음) + `PercentileCrossDialog.svelte`(`rowDefs`·`MIN_N` n<10 가드·`—`/분포없음 상태·정직 푸터). 현재 12+축 전부 재무지표 — **인적자본 축 0**. cross-universe-percentile(`_done`) 가 배선 패턴 정본.

## 7. 결론

가진 것: 풍부하고 구조화된 비재무 사업보고서 데이터 + 이미 만들어 묻어둔 엔진(관계망·인적자본·R&D·백분위). 못 쓰는 것: 표면화의 얕음·출처 부재·의미층 부재. **해법은 새 분석이 아니라 표면화·스파인·의미층** → 02 의 7개 기능으로 구체화.
