# PRD — US(EDGAR) 종목 터미널 도달 (배선 재정렬)

> **단일 권위 문서.** 옛 `mainPlan/edgar-parity-wiring/`(00–09)는 per-pillar 데이터 swap 가정으로 바닥(터미널
> 엔진=7 baked KR aggregate, KRW 결합)을 놓쳐 어긋났다 — 폐기/아카이브하고 본 PRD로 시작한다.
> 원칙: **덕지덕지 금지** — 통화/시장 분기는 데이터 소스 2곳에 모으고 표시점에 흩지 않는다.

작성 시점 검증 기준: 커밋 `52935bcf8`(바닥 SSOT)·`eaf3d97dc`(통화 기초)·`d3d4992f0`(CenterStack 부분).

---

## 1. 목표

AAPL 같은 US(EDGAR) 종목이 터미널에서 **검색→열림→주가→재무**까지 KR과 동일 배선으로 동작한다.
이후 panel/filings·scan·map 까지 패리티. "확실하게 터미널 도달" = dev 에서 US 종목이 실제 떠야 완료.

## 2. 현 상황 (실측)

### 2.1 이미 된 것
- **EDGAR finance 데이터·HF 발행**: `edgar/financeStmt/{ticker}.parquet` 6,437개(파사드 표준화 bake, USD).
  `edgar/panel/{ticker}`·`edgar/tickers/tickers.parquet` 도 HF 200. (커밋 ~`19852541b`)
- **financeSource US 분기**: `financeSource.ts` 가 `resolveMarket` 으로 KR=dart/finance·US=edgar/financeStmt 직독.
- **통화 인식 기초**: `Company.currency` + `fmtMoney`/`fmtMoneyTril`(engine.ts). KR 무회귀.

### 2.2 바닥 배선 (왜 아직 도달 못 하나) — SSOT
- 터미널 엔진 `createEngine(raw)` 는 **7 baked JSON**(`landing/.../routeLoad.ts`)에서 회사 모델을 만든다:
  `search-index`(검색)·`finance.json`(엔진재무)·`prices-snapshot`(주가요약)·`ecosystem`·meta·quarters·industryStats.
  전부 **KR scan 생태계** 집계.
- **결정적 게이트**: `engine.buildCompanyImpl` 은 `raw.finance.companies[code]` **AND** `raw.prices.data[code]`
  둘 다 없으면 `null`. → US 가 검색·열림 되려면 search-index+finance+prices-snapshot 3 집계에 있어야 한다.
- **★ 주가 스냅샷 ≠ 주가 그래프 — 출처가 다르다 (놓치기 쉬운 구멍).**
  - **스냅샷**(현재가·시총·수익률·52주): `prices-snapshot.json` 1파일 → buildCompany 게이트. 종가 요약이면 충분.
  - **그래프**(`PriceChart`/klinecharts): 7 baked JSON 이 아니라 **런타임 `rt.price` 포트**가 회사별 **일별 OHLCV
    전체이력(~10년)** 을 lazy 백필(`priceSource`=`gov/prices/date/{year}.parquet` range-read·`govPriceSource`=
    `gov/prices/company/{code}.parquet` 통파일). 수정주가·캔들·거래량 페인·turnover·백테스트가 이 OHLCV 를 먹는다.
    **`rt.price` 포트(`candles/older/loaded/govCandles`)는 전부 KRX 스키마(ISU_CD 'A'+코드·gov 경로) KR 전용** — US 브랜치 0.
    → 스냅샷만 채우면 US 가 "열리지만 그래프는 빈 화면". **종가-only spark 로는 그래프 불가.**
- 엔진/표시 전체가 **KRW 조원에 결합**(`조`/`억` 리터럴이 수십 파일 분산). 통화 개념은 방금 기초만 깔림.
- 검증된 US 데이터 소스: 검색=`edgar/tickers`(ticker·title·exchange), 재무=`buildAnnual(cik)`(AAPL FY2024
  $391.04B=실측 일치, DART canonical snakeId 동일 vocabulary), **그래프 OHLCV**=`gather` US history
  (`yahooChart.fetchHistory`, Yahoo v8 `period1/period2·interval=1d·adjclose`, 일별 o/h/l/c/v ~10년 실측).

### 2.3 막힌 것 (블로커) — 해소됨(§6)
- **프로덕션 주가 라이브 불가**: Yahoo v8 chart 가 **429(per-IP rate limit)·CORS** 라 런타임/브라우저 직호출 불가
  (KR 도 동일 이유로 라이브 안 하고 HF 에 굽는다). → **bake-to-HF 로 해소**(§6). 스냅샷·그래프 둘 다 같은 OHLCV 에서.

## 3. 덕지덕지 위험 → 깨끗한 원칙

| 위험(하던 방식) | 깨끗한 대체 |
|---|---|
| 통화를 표시점마다 if 패치(수십 파일) | **데이터 소스 2곳**(`buildCompany`·`buildBundle`)에서 통화 처리 → 표시는 data-driven(분기 0) |
| US 를 별도 `-us.json` ad-hoc 병합 | US 도 KR과 **동형 엔트리**(currency 태그) — 빌더가 생산, 병합은 1곳 |
| 코드 곳곳 `market==='US'` if | `resolveMarket` SSOT 1곳 판정, 결과를 데이터에 태깅해 전파 |
| eco/credit/percentile 까지 US 즉시 | **도달 우선** — rich 기능은 P3(없어도 buildCompany 동작, eco=`{}` 폴백) |

핵심: **통화는 값과 함께 흐른다.** 엔진 co·재무 번들이 `currency` + 통화 단위로 산출 → 표시 컴포넌트는 통화를 모른다.

## 4. 아키텍처

### 4.1 데이터 흐름 (도달 = 3 baked 집계 + 1 런타임 포트)
```
edgar/tickers ──────────────► search-index(+currency,market=US)  → raw.index    → suggest/buildCompany
EDGAR companyfacts(buildAnnual)► finance-us(+currency=USD)         → raw.finance  → buildCompany(게이트)
[A] gather US OHLCV bake ──────► prices-snapshot-us(+currency=USD)  → raw.prices   → buildCompany(게이트)
routeLoad: KR aggregate + US 동형 엔트리 병합(1곳) → raw → createEngine     ┐ 검색→열림
                                                                            ┘
[A] 같은 OHLCV ──► edgar/prices/company/{ticker}.parquet ─(HF read-only)─► rt.price US 브랜치 → PriceChart 그래프
```
**[A] 단일 OHLCV 소스가 둘을 동시 생산**: gather US history(Yahoo v8) → 회사별 OHLCV parquet(그래프) + 그 마지막
행들에서 스냅샷(현재가·수익률·52주·변동성) 파생. KR 의 `gov/prices/company`(그래프)+`prices-snapshot`(요약) 쌍과 동형.
**그래프 도달의 핵심 = `rt.price` 포트에 resolveMarket SSOT US 브랜치 1곳** (govPriceSource 미러). PriceChart 무변경.

### 4.2 통화 처리 = 소스 2곳 (덕지덕지 차단점)
1. **`engine.buildCompany`**: `co.currency = fin.currency ?? 'KRW'`. co 의 금액(price.mktcap·income/balance/cashflow
   값)을 `fmtMoney`/`fmtMoneyTril(v, co.currency)` 로 산출하거나 통화를 동반. (기초·시총 적용 완료, 재무시리즈 잔여.)
2. **`financeSource.buildBundle`**: `bundle.currency = resolveMarket(code).market==='US'?'USD':'KRW'`.
   16카드 `unit`·값을 통화 인식으로 빌드 → FinFullscreen·MiniFinChart 는 unit 을 그대로 렌더(per-card 분기 0).

→ 이 2곳만 통화 인식이면 CenterStack·FinFullscreen·MiniFinChart·표·기타 패널이 자동 따라온다.

## 5. 단계 (도달 우선)

- **P0 통화 소스화** (표시 무패치): buildCompany 재무시리즈 + buildBundle currency. KR 무회귀 가드. → US 값이 $ 로.
- **P1 프로덕션 데이터** (빌더는 도메인 위임 `별도빌드 금지`·offline 가드):
  ① finance-us(buildAnnual 6437, 오프라인) ② search-us(tickers)
  ③ **주가 OHLCV bake**(§6) — gather US history → `edgar/prices/company/{ticker}.parquet`(그래프) +
     마지막행 파생 `prices-snapshot-us`(게이트). **한 빌더가 둘 생산.** 429 페이싱·증분(recent tail + 1회 전이력).
  ④ **런타임 `rt.price` US 브랜치** — `priceSource`/`govPriceSource` 미러로 `edgar/prices/company` 읽는 US 소스 신설,
     `createPublicRuntime` price 포트(`candles/older/loaded`)를 resolveMarket SSOT 로 분기. PriceChart·엔진 무변경.
- **P2 병합·발행·검증**: routeLoad 병합 + HF/CI 발행. **dev 5173 AAPL 검색→열림→USD 재무 + 주가그래프 렌더** 눈검수(시각).
- **P3 확장**: panel/filings(edgar/panel 있음)·scan(edgar/scan)·map·eco US.

## 6. 주가 소스 — 확정: 회사별 OHLCV bake (그래프+스냅샷 단일 파이프라인)

US 정부 오픈 주가 데이터는 **없다**(EDGAR=공시만, 주가=거래소 상업데이터·Stooq bulk=401/PoW·FMP free=250/day).
그래프는 **회사별 일별 OHLCV 전체이력**이 필수(§2.2 ★) — 종가-only spark 로는 그래프를 못 그린다.

**확정 소스 = gather US history**(`yahooChart.fetchHistory`, Yahoo v8 `period1/period2·interval=1d·adjclose`):
- date·open·high·low·close·volume 일봉 **~10년**(KR `gov/prices/company` 와 동형 schema). 무인증 실측 확인.
- **429·CORS 라 런타임 라이브 불가** → KR 과 동일하게 **HF 에 bake**, 런타임은 read-only 로 읽는다.

**단일 파이프라인이 그래프 + 스냅샷 둘 다 생산** (덕지덕지 차단 — 소스 1개):
- 회사별 `edgar/prices/company/{ticker}.parquet`(전체 OHLCV) = **그래프**(`rt.price` US 브랜치가 읽음).
- 각 파일 마지막 행들에서 파생 → `prices-snapshot-us`(현재가·return1m/3m/1y·volatility1y·52w hi/lo·**marketCap=
  currentPrice × shares**[EDGAR dei `EntityCommonStockSharesOutstanding`]) = **스냅샷**(buildCompany 게이트).
- 빌더 = 신규 gather/prebuild 스텝(도메인 위임). 페이싱+백오프, 증분(recent tail 일배치 + 전이력 1회 백필).
- 규모: 6437 회사별 history 호출 = KR `gov/prices/company`(~2555) 과 동급의 주기 cron. 라이브 아님(read-only HF).
- **spark 는 불필요**: 종가-only 라 그래프 불가. (스냅샷 부트스트랩 가속이 굳이 필요하면 멀티심볼 spark 를 *선택적*
  초기 채움으로 쓸 수 있으나 설계 본류 아님 — OHLCV bake 가 스냅샷도 자급.)

→ **블로커 해소** (라이브→bake 로). P1③④ 진행 가능.

## 7. 검증 게이트
- vitest `engineUsReach`(도달 계약, 통과중) 유지.
- KR 무회귀: `fmtKRW`=`fmtMoney('KRW')` 동치·기존 스냅샷 불변.
- P2 **시각 눈검수 필수**(정량 PASS 가 통화/레이아웃 디테일 못 봄).

## 8. 비범위 (이번 PRD)
- AI/ask 의 US (별도), EDINET(일본), eco/credit rich 패리티의 완전성(P3 이후 점진).
