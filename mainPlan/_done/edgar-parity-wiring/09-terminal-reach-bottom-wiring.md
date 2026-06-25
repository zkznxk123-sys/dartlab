# 09 — 터미널 도달 바닥 배선 (실측 SSOT)

> 운영자 지시 "디테일하게 바닥배선부터 제대로 파악" 의 산출물. 터미널에서 US(EDGAR) 종목이 검색→열림→
> 데이터까지 가는 **실제 배선**을 코드:라인 근거로 박제. 추측 아님 — 전부 읽고 vitest 로 증명.

## 1. 터미널 회사 모델의 바닥 = 7 baked JSON

`landing/src/lib/terminal-shell/routeLoad.ts:loadTerminalRaw` 가 7 JSON 을 병렬 로드해 `RawData(raw)` 조립 →
`ui/.../terminal/lib/engine.ts:createEngine(raw)` 가 그 위에서 **모든 회사 기능**을 만든다.

| raw 필드 | JSON | 빌더 | 원천·단위 |
|---|---|---|---|
| `raw.index` (검색) | `map/search-index.json` | buildIndustryMap | dart scan — `IndexRow{stockCode,corpName,industry,revenue}` |
| `raw.finance.companies` | `dashboards/finance.json` | buildFinanceJson | `dart/scan/finance.parquet`·`account_id_std`·**조원** |
| `raw.prices.data` | `map/prices-snapshot.json` | buildPricesSnapshot | `gov/prices`(KRX)·**KRW** |
| `raw.eco.nodes` | `map/ecosystem.json` | buildIndustryMap | scan 등급·업종(KR) |
| meta·quarters·industryStats | dashboards·map | — | KR |

## 2. 결정적 게이트 — buildCompany 는 finance+prices 둘 다 필수

`engine.ts:buildCompanyImpl`:
```
const fin = raw.finance.companies[code]; const px = raw.prices.data[code];
if (!fin || !px) return null;   // ← 둘 중 하나라도 없으면 co 없음 = 못 연다
```
→ AAPL 을 **열기만 해도** `search-index`+`finance`+`prices` 3 집계에 있어야 한다. `eco` 는 `|| {}` 라 optional.

## 3. 검증된 데이터 소스 (전부 실측)

- 검색: `data/edgar/tickers.parquet`(10,436행 — ticker·title·exchange·cik). ✓ 있음.
- 재무: `providers.edgar.finance.pivot.buildAnnual(cik)` → DART canonical snakeId 시계열. AAPL FY2024 sales=$391.04B(실제 일치). `finance.json` 의 `account_id_std`(sales·operating_profit·total_assets…)와 **동일 vocabulary**. ✓
- 주가: `getDefaultGather().price("AAPL", market="US")` → 1Y OHLCV(close $293.08). ✓ 단 **Yahoo per-ticker 429** — bulk 아님.
- 시총: `getSharesOutstanding(cik)`(EDGAR dei) × price. ✓

## 4. 도달 배선 — 완료 + 증명

- `routeLoad.ts`: US 번들(`finance-us.json`·`prices-snapshot-us.json`·`search-index-us.json`)을 로드해 `raw.finance.companies`·`raw.prices.data`·`raw.index` 에 **추가 병합**(KR 무영향). [구현됨]
- `engineUsReach.test.ts`: 병합 raw 로 `suggest('AAPL'/'Apple')` 발견 + `buildCompany('AAPL')` non-null(price·매출 흐름) + 데이터 없는 종목 null 게이트. **vitest 4/4 PASS** = US 가 엔진에 도달함 증명.

## 5. 남은 2대 과제 (둘 다 큼 — "간단치 않다")

### ① 통화 표시 sweep
엔진/표시가 **KRW 조원에 결합**. `fmtKRW`·`조`/`억` 리터럴이 **수십 파일에 분산**(CenterStack·FinFullscreen·
HoldingsDialog·IndustryDialog·LeftRail·MarketFeed·charts…). `EcoNode.market`(KR 세그먼트)은 있어도 통화 개념 없음.
→ `co.currency`(finance 엔트리 `currency='USD'` 태그에서) + **중앙 통화 포맷터**로 sweep 필요.

### ② 프로덕션 데이터 (6437)
- 재무 `finance-us.json`: buildAnnual 전수(오프라인) — tractable.
- 검색 `search-index-us.json`: edgar/tickers — trivial.
- **주가 `prices-snapshot-us.json`: 블로커.** Yahoo per-ticker=429·FMP free=250/day·FDR=per-ticker. dartlab 에
  **bulk US 주가 소스 없음**. 정답 = **Stooq bulk CSV**(무료·전 US 일별 1파일) 신규 gather 도메인, 또는 FMP/EOD 유료.
- eco/scan/credit/percentile US: 엔진 rich 기능 전부 KR scan 결합 — 별도 US scan 생태계 필요(후순위, 도달엔 불요).

## 6. 빌드 순서 (도달 우선)
1. 통화 중앙 포맷터 + `co.currency` (KR 무회귀 가드).
2. 오프라인 전수 빌드: finance-us(buildAnnual)·search-us(tickers).
3. 주가 bulk 소스(Stooq 도메인) → prices-us 전수.
4. routeLoad 병합 HF 발행 + CI 파이프라인.
5. dev 5173 AAPL 검색→열림→USD 정상표시 눈검수.
6. (후순위) panel/filings·scan·map·eco US.
