# 03. 아키텍처와 자산 재사용

상태: 비전 PRD v0.1 (2026-06-13). 코드 경로는 작성 시점 실측(Read/Grep) 기준 — 구현 전 재확인.
목적: 업그레이드를 *쌓기*가 아니라 *기존 격자를 펼치기*로 한다. 무엇을 REUSE/EXTEND/NEW 하고, 어디 사나(browser TS · Python 엔진 · contract), 렌더러는 무엇인가.

---

## 1. 현재 자산 (검증된 거처)

### 터미널 재무 surface (업그레이드 대상) — `ui/packages/surfaces/src/terminal/`
- `lib/finTabs.ts` — `FS_TABS` 5탭(수익성/현금·투자/재무체력/주주환원·소유/인력·보수). `finKey`로 데이터층 카드 + `load()`로 report 교차 카드. `alive` 헬퍼가 전 series null 카드 자동 제거.
- `lib/cardGuide.ts` — `CARD_GUIDE` ~40 카드 {what/good/bad} 큐레이션 해석(환각 0, 데이터 기반 문장생성 금지).
- `charts/MiniFinChart.svelte` — SVG 렌더러: 막대+선·이중축·signed·stacked·refLine·**heatmap(kind='heatmap')·waterfall(kind='waterfall')** 7형 한 컴포넌트. small-multiples 밀도 최적화 + 해석칩(`!` 버튼).
- `panels/FinFullscreen.svelte`·`panels/CenterStack.svelte` — 격자 레이아웃·온디맨드 로드.

### 데이터층 — `ui/packages/runtime/src/adapters/public/sources/financeSource.ts`
- `dart/finance/{code}.parquet`(HF·per-company·~293KB) 를 `../../../data/hfRange.readParquetRows`로 hyparquet 직독(DuckDB 불필요).
- **28 표준계정 `STD`**(`src/dartlab/.../viz/display/finance/accounts.py::_STANDARDS` 포팅): account_id(IFRS) 우선 + account_nm 키워드 fallback + `ex` 제외가드. IS/BS/CF/CIS 레인.
- TTM(직전4분기 standalone 합), 분기규약 자동판정(Σ(Q1..Q3)>annual → YTD 차분), CIS→IS fallback.
- 계약 정본 = `ui/packages/contracts/src/finance.ts`(`FinCard`·`FinSeries`·`TerminalFinanceBundle`·`FinMode`) + `report.ts`(`ReportPort`).

### `engine.ts:valuationOf` (검증)
- `valuationOf(code)`(line ~182): `px.marketCap`(단일 스냅샷 1점) 기준 PER/PBR 계산 + peer median + `fairMid`/`upside`/`perPos`. **즉 PER/PBR은 현재 *단일 시점 스냅샷*이지 시계열이 아니다** — 시계열은 신규 작업(아래 §2).

### DART 엔진 자산 (`src/dartlab/`, 4계층)
- `Company.panel`(IS/BS/CF/CIS/ratios wide 격자) · `compare(codes,topic,period,scope)`(`panel/compare.py`, N사 시점정렬) · reverseDCF/valuation · credit · scan/search · `gather/customs/`(관세청 수출).

---

## 2. 자산 인벤토리 판정 (테마별)

| 업그레이드 테마 | 판정 | 거처 | 근거 |
|---|---|---|---|
| 지수 리베이스(=100) | **EXTEND** `financeSource.ts` | 브라우저 | 시계열 헬퍼 이미 존재. 첫 유효값 정규화 `v/base*100` 1줄. 신규 데이터 0. |
| 전역 기간모드(분기/연간/TTM·역순) | **EXTEND** `FinMode` 토글 | 브라우저 | TTM·annual 이미 계산. 전역 컨트롤 배선만. |
| 업종 인지 카드 필터 | **REUSE** `alive` + 업종 메타 | 브라우저 | 카드 갈아끼우기 아님 — *가시성 토글*(net 제거). 단일 코드패스. |
| 운전자본 회전일수 split | **EXTEND** (기존 CCC 카드) | 브라우저 | DSO/DIO/DPO = panel 계정. 합성 CCC를 3선으로. |
| 동종 백분위 밴딩 | **NEW 배선** (`compare` 호출) | 브라우저 호출 or prebuild | `compare` 완비. 동종 universe 분포를 시점별로. 런타임 Python 불가 → prebuild parquet 또는 경량 분포 사전계산. |
| 가격↔기초체력 지수 오버레이 | **NEW 어댑터** | 브라우저 조인 | `gov/prices/company/{code}.parquet`(OHLCV) × panel 리베이스. 어댑터 1개. |
| PER/PBR **시계열** | **NEW** | 브라우저 조인 | 현재 스냅샷만. 기간별 종가 × 기간별 발행주식수 × 기간별 순익/자본 조인 필요(정합 = [04 §4](04-data-readiness-kill-list.md)). |
| 이익품질 forensic 플래그 | **EXTEND** (결정론 계산) | 브라우저 | CFO/NI·accruals·tie-out = panel 계정 산술. cardGuide.bad 임계를 배지로. |
| reverseDCF 함축 기대 읽기 | **REUSE** 엔진 | Python prebuild | reverseDCF 엔진 존재. asOf 현재가 역산 → prebuild 또는 경량 read. |
| 공시 큐레이션 by type | **REUSE** | 브라우저 | `regularFilingsSource`/`nonRegularFilingsSource` 존재 + scenario-simulator 11 경계 정리. |
| 세그먼트/지역별 | **NEW (Python, 부분차단)** | Python 게이트 | `_noteCellsFromPanel("NT_D871100")` 다축 — 2/10 clean. |
| R&D 추이 | **EXTEND (Python)** | Python 게이트 | 2-tier(IS select → 주석 NT_D834310) 6/10. |
| 수출 오버레이 / 수주잔고 / 컨센서스 | **BLOCKED/EXCLUDED** | — | [04](04-data-readiness-kill-list.md). |

---

## 3. 데이터 가용성 경계 (대부분 아이디어가 죽는 곳)

- **브라우저 TS로 즉시 가능**(`dart/finance/{code}.parquet` 안에 이미 있음): 지수 리베이스, 기간모드, 업종 필터, 운전자본 split, 이익품질 플래그, 손익/현금/자본 브리지 변형 — 전부 `financeSource.ts`로 in-browser. **신규 데이터 0.**
- **기존 어댑터 조합**(데이터 있음, 배선만): 가격↔기초체력(`gov/prices` × panel), PER/PBR 시계열(가격 × 발행주식수 × 순익/자본). 발행주식수는 `reportSource`의 ownership(stockTotal)에 있음.
- **Python 엔진 필수**(`src/dartlab`, 졸업 게이트 후 prebuild parquet → hyparquet 직독): 세그먼트(다축 XBRL), R&D(주석 2-tier), reverseDCF 함축기대(엔진 계산), 동종 백분위(분포 사전계산이 경량). **런타임 Python 호출 불가** — `dart/scan/report/` 패턴처럼 prebuild 산출 parquet로 떨군다.
- **차단**: 수주잔고(표면 부재)·컨센서스(소스 부재)·수출 회사매핑(집계 데이터).

---

## 4. 렌더러 결정 — `MiniFinChart` EXTEND, `ChartRenderer` 도입 금지

`MiniFinChart.svelte`를 EXTEND한다. 이유:
- 이미 bar+line·이중축·signed·stacked·refLine·heatmap·waterfall 7형을 한 컴포넌트로 + small-multiples 밀도(컴팩트 SVG, barW 상한) + 해석칩까지. 백분위 밴드는 새 `kind`가 아니라 **series 뒤 분포 음영 + 배지**(spec 필드 추가). 지수 리베이스도 새 kind 아니라 **데이터 변환**(렌더러 0줄).
- `ui/shared/chart/ChartRenderer.svelte`(landing/notebook RechartsSpec 디스패처, `min-height:200px`, lazy import 13종)는 **풀사이즈 단일차트**용. 터미널 16카드 격자에 끌어오면 lazy import 폭발 + 밀도 붕괴. "손수 차트 금지" 룰의 정신 = *렌더러 재발명 금지*인데, **터미널에선 MiniFinChart가 이미 그 SSOT 렌더러다.** (메모리 `reference_financial_graph_ssot` = ui/web·landing 디스패처 정본이지 터미널 격자 정본이 아님 — 터미널은 별 렌더 경로.)

계약 확장(최소): `FinCard`에 ① `band?: { p25:Num[]; p50:Num[]; p75:Num[]; pctileBadge?: string }`(동종 분포) ② `rebase?: boolean`(지수 모드는 데이터변환이라 spec 불필요할 수도 — 토글이 데이터를 바꿈) ③ `flags?: { at:number; kind:'warn'|'info'; label:string }[]`(결정론 플래그). 전부 옵셔널 — 기존 카드 무변경.

---

## 5. 덕지덕지 함정과 규율 구조

구체적 위험: ① iTooza 37차트 통째 덤프 → `FS_TABS` 탭 10개 누적. ② 업종마다 `if(업종==='bank')` 특수 카드 분기. ③ 기능마다 새 패널(`SegmentPanel`·`ExportPanel`·`ValuationPanel`…). **전부 `feedback_always_check_clutter` 위반.**

규율 구조:
- 현 5탭이 이미 iTooza 6분류 압축본. **탭을 늘리지 말고** 기존 탭에 카드를 `alive` null-filter로 추가(업종 무관 단일 코드패스). 밸류에이션은 신탭 1개까지 허용(현재 통째 없음) — 그 이상 탭 증식 금지.
- 지수 리베이스·기간모드는 신규 카드가 아니라 **기존 카드의 토글**.
- 백분위 밴드는 신규 카드가 아니라 **기존 카드 위 레이어**.
- 세그먼트/R&D는 졸업 후 **해당 탭에 1카드씩** 삽입.
- 업종 분기는 코드 분기(`if bank`)가 아니라 **카드 메타의 가시성 필터**(데이터 driven, 단일 경로).

---

## 6. 4계층 import 준수

- 브라우저층(ui/packages)은 `src/dartlab` 직접 import 안 함 — prebuild parquet(HF) 경유. 신규 데이터는 `.github/scripts/prebuild/`(offline only, HF 다운로드) 또는 `sync/`(online) 산출.
- Python 신규 능력은 `tests/_attempts/financialStatementLab/` 졸업 후 `src/dartlab/analysis/`(L2) 또는 기존 엔진 확장. L2↔L2 cross-import 금지 — 백분위(compare)·reverseDCF·forensic 결합은 *소비측*(L3 story 또는 prebuild 스크립트)에서 조립, L2끼리 직접 호출 금지.
- 공개 계약only: 노출은 공개 verb(`Company.panel`·`compare`)지 내부 계층 아님.
