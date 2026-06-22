# 02 · 검증 · 롤백 · 부채 · 원장

## 테스트 매트릭스

| # | 테스트 | 잡는 함정 |
|---|---|---|
| a | 회사 로드 → MAX 기간/좌측 팬 백필로 `getDataList().length > candles.length` 유발 → 내보낸 행 수 == `getDataList().length` == 보이는 봉 수 | 함정 1 (백필 body 절단) |
| b | 파일명 마지막 날짜 == body 마지막 행 날짜 == `getDataList` 마지막 봉 | 함정 2 (filename 절단) |
| c | `subject==='index'` + 비어 있지 않은 `rt.index.series` → 버튼 *미렌더* | 함정 3 (index 오라벨) |
| d | HA 모드(`ctl.candleStyle==='ha'`) → 버튼 비활성 | 함정 4a (합성봉) |
| e | 리플레이 ON(`ctl.replay.on`) → 버튼 비활성 | 함정 4b (리플레이 절단) |
| f | turnover 컬럼 미출력(OHLCV-only) | 함정 5 (1e8 단위 거짓) |
| g | CSV 왕복: BOM + 콤마 이스케이프(`csvExport escapeCell`)로 pandas 등가 리더가 깨끗이 파싱, null 거래량 셀=빈칸(0 아님) | 결손 빈셀 |
| h | 클릭 시점 `chart` non-null 가드 (getDataList 최초 사용·0 prior call) | 런타임 안전 |

> 핵심: 테스트 a 는 **백필 divergence** 를 반드시 유발해야 한다. "17개사 LRU eviction" 만으로는 재진입 시 prop/getDataList 가 재-seed 로 수렴해 버그 직렬화기에도 PASS 하므로 함정 1 을 못 잡는다.

## 롤백

순수 가산 — 공유 계약 변경 0. 버튼 + 직렬화기 제거 = `PriceChart.svelte`/`ChartMenus`/`ChartRibbon` diff 의 단순 revert, 데이터/파이프라인/cron 마이그레이션 없음. 완전 가역.

## Phasing

단일 페이즈(산출물이 작음):
1. `getDataList()` 위 직렬화기 — `timestamp→YYYYMMDD` 재정형 + `csvExport.ts toCsv/downloadCsv` 재사용.
2. 게이트된 버튼을 `ChartMenus` + `ChartRibbon` 에 `onSnapshot` 식 prop 로 배선.
3. 테스트 a–h.

파이프라인/빌드/cron 변경 0. **공개 surface → 커밋 자율, push 는 운영자 명시 승인("푸시해"·"올려") + 스크린샷 눈검수 후에만.**

## 부채 티켓 (범위 밖 · 원장 등록)

- **TKT-EXP-1**: `ui/packages/surfaces/src/viewer/lib/panelLoad.ts:4` 가 `readParquetRows` 를 `@dartlab/ui-runtime/data/parquet/hfRange` 에서 직접 import + `:19 bundleCache = new Map()` — 코어+오리진 SSOT 우회(검증된 실제 우회). 본 PRD 범위 밖.
- **TKT-EXP-2**: `tests/audit/checkUiDataWiring.mjs` 가 `ui/packages/runtime/src/adapters/**/sources/*.ts` 만 글롭 → `surfaces/` 에 *맹점*. 글롭을 surfaces/ data-egress 까지 넓혀야 한다(ViewerStudio parquet passthrough 도 가시화). **선결 NOTE**: 본 가격 CSV 는 메모리 차트 객체를 직렬화하고 origin URL 을 안 만들어 *영향 없음* — 가드 통과를 soundness 근거로 삼지 않음(글롭 밖).
- **TKT-EXP-3**: CSV 작성기 5종 분산 — `scan/csvExport.ts:27 toCsv(columns, records)` vs `viewer/lib/dataExport.ts:11 toCsv(string[][])`(시그니처 비호환) + `panelToCsv` + `financeToExcel` + BOM 없는 `BacktestReport` 인라인 — 단일 SSOT 로 수렴. 범위 밖; 본 PRD 는 `csvExport.ts` 재사용·신규 0.

## OPEN QUESTION

- **macro/screener 행-egress**: 그 surface 들이 klinecharts v9 인스턴스(`getDataList` 핸들)를 들고 있는지 *미확인*. `getDataList` 는 오늘 ui/ 전체에서 0 hits, 그 surface 들의 동기 render 핸들도 미확인 → **단정 제외 아니라 OPEN QUESTION 유지**. 포함 여부 결정 전 v9 인스턴스 보유 확인 선행. **범위 재팽창 금지.**

> HA/리플레이 fork 는 v7 에서 DISABLE 로 *확정·박제*(→ [01](01-architecture-traps-format.md) 함정 4) — 더 이상 open 아님.

## 결정 로그 · 토론 이력

- **토론 1차(5라운드, 다기 전문 에이전트 + 적대 반증 + 심사단)**: "데이터 모두 다운로드"의 거대 프레이밍을 코드 재검증으로 점진 해부. 라운드별 95→96→96→98→95. 결론이 *역전* — 대부분이 이미 ViewerStudio 로 ship 됨을 발견, 순-신규를 가격 텍스트 1포맷으로 좁힘. 단 라운드 5 자체에 메커니즘 오류(displaySeries=render 진실, PNG=export, index 이유 역전) 잔존.
- **토론 2차(보정, 2라운드, 심사단 100/100)**: 라운드 5 적대 반증의 8개 검증된 수정 흡수 — getDataList(render 진실)·PNG≠export(범주 교정)·index 명시 게이트·CSV `#` 주석 부패 회피·SSOT 우회 비-모범화. 새 함정 2종 발견(파일명 절단·거래대금 1e8). 점수 100.
- **최종 레드팀 정정(3 major, 본 문서 흡수)**: ① 함정 1 *메커니즘* 교정 — 절단 동인은 LRU eviction 이 아니라 *백필 append-beyond-prop*(`loadOlderYear:127-138` 가 prop 갱신 안 함); 테스트도 백필 divergence 유발로 교정. ② HA/리플레이 fork 자기모순 해소 — DISABLE 로 확정(미결 출하 금지). ③ 파일 경로 정정 — `priceSource.ts` = `ui/packages/runtime/src/adapters/public/sources/`, `panelLoad.ts` = `ui/packages/surfaces/src/viewer/lib/`, `CenterStack.svelte` = `ui/packages/surfaces/src/terminal/panels/`.

## NEXT (세션 재개용)

- 착수 = 운영자 go. 본 문서 + [00](00-product-and-scope.md) + [01](01-architecture-traps-format.md) 만으로 재조사 없이 구현 가능.
- 구현 순서: 직렬화기 → 버튼 배선(ChartMenus/ChartRibbon) → 테스트 a–h → 스크린샷 눈검수 → 커밋(자율) → push(운영자 승인 대기).
- 착수 전 단 하나 확인: macro/screener OPEN QUESTION 은 *범위 재팽창 신호* — 손대지 말 것.
