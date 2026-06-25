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
  `search-index`(검색)·`finance.json`(엔진재무)·`prices-snapshot`(주가)·`ecosystem`·meta·quarters·industryStats.
  전부 **KR scan 생태계** 집계.
- **결정적 게이트**: `engine.buildCompanyImpl` 은 `raw.finance.companies[code]` **AND** `raw.prices.data[code]`
  둘 다 없으면 `null`. → US 가 검색·열림 되려면 search-index+finance+prices 3 집계에 있어야 한다.
- 엔진/표시 전체가 **KRW 조원에 결합**(`조`/`억` 리터럴이 수십 파일 분산). 통화 개념은 방금 기초만 깔림.
- 검증된 US 데이터 소스: 검색=`edgar/tickers`(ticker·title·exchange), 재무=`buildAnnual(cik)`(AAPL FY2024
  $391.04B=실측 일치, DART canonical snakeId 동일 vocabulary), 주가=`gather.price(t,market="US")`(yahoo, $293 실측).

### 2.3 막힌 것 (블로커)
- **프로덕션 주가 bulk 소스 없음**: 헤드리스 무료 전부 막힘 — Yahoo 429·Stooq JS PoW·FMP free 250/day·FDR=Yahoo래퍼.
  → **결정 필요**(§6).

## 3. 덕지덕지 위험 → 깨끗한 원칙

| 위험(하던 방식) | 깨끗한 대체 |
|---|---|
| 통화를 표시점마다 if 패치(수십 파일) | **데이터 소스 2곳**(`buildCompany`·`buildBundle`)에서 통화 처리 → 표시는 data-driven(분기 0) |
| US 를 별도 `-us.json` ad-hoc 병합 | US 도 KR과 **동형 엔트리**(currency 태그) — 빌더가 생산, 병합은 1곳 |
| 코드 곳곳 `market==='US'` if | `resolveMarket` SSOT 1곳 판정, 결과를 데이터에 태깅해 전파 |
| eco/credit/percentile 까지 US 즉시 | **도달 우선** — rich 기능은 P3(없어도 buildCompany 동작, eco=`{}` 폴백) |

핵심: **통화는 값과 함께 흐른다.** 엔진 co·재무 번들이 `currency` + 통화 단위로 산출 → 표시 컴포넌트는 통화를 모른다.

## 4. 아키텍처

### 4.1 데이터 흐름 (도달 3집계)
```
edgar/tickers ──────────────► search-index(+currency,market=US)  → raw.index   → suggest/buildCompany
EDGAR companyfacts(buildAnnual)► finance-us(+currency=USD)         → raw.finance → buildCompany(필수)
gather/소스(§6) ───────────────► prices-us(+currency=USD)           → raw.prices  → buildCompany(필수)
routeLoad: KR aggregate + US 동형 엔트리 병합(1곳) → raw → createEngine
```

### 4.2 통화 처리 = 소스 2곳 (덕지덕지 차단점)
1. **`engine.buildCompany`**: `co.currency = fin.currency ?? 'KRW'`. co 의 금액(price.mktcap·income/balance/cashflow
   값)을 `fmtMoney`/`fmtMoneyTril(v, co.currency)` 로 산출하거나 통화를 동반. (기초·시총 적용 완료, 재무시리즈 잔여.)
2. **`financeSource.buildBundle`**: `bundle.currency = resolveMarket(code).market==='US'?'USD':'KRW'`.
   16카드 `unit`·값을 통화 인식으로 빌드 → FinFullscreen·MiniFinChart 는 unit 을 그대로 렌더(per-card 분기 0).

→ 이 2곳만 통화 인식이면 CenterStack·FinFullscreen·MiniFinChart·표·기타 패널이 자동 따라온다.

## 5. 단계 (도달 우선)

- **P0 통화 소스화** (표시 무패치): buildCompany 재무시리즈 + buildBundle currency. KR 무회귀 가드. → US 값이 $ 로.
- **P1 프로덕션 데이터**: ① finance-us(buildAnnual 6437, 오프라인) ② search-us(tickers) ③ prices-us(§6 결정 후).
  빌더는 도메인 위임(`별도빌드 금지`)·offline 가드.
- **P2 병합·발행·검증**: routeLoad 병합 + HF/CI 발행. **dev 5173 AAPL 검색→열림→USD 정상** 눈검수(시각).
- **P3 확장**: panel/filings(edgar/panel 있음)·scan(edgar/scan)·map·eco US.

## 6. 미결정 (운영자 판단 필요)

**주가 bulk 소스** — 헤드리스 무료 없음:
- (A) Yahoo 일배치 cron(gather 기존, 페이싱+백오프) — 무료·느림(6437≈수시간, GHA 6h 한계 내).
- (B) 유료 API(EOD Historical/Polygon/FMP paid) — 빠름·키+비용.
- (C) 범위 축소(S&P500 등 우선) + 점진 확대.

권장: 우선 (A) 무료로 도달 증명 → 필요 시 (B). **단 운영자 비용 결정이라 확정 전 P1③ 보류.**

## 7. 검증 게이트
- vitest `engineUsReach`(도달 계약, 통과중) 유지.
- KR 무회귀: `fmtKRW`=`fmtMoney('KRW')` 동치·기존 스냅샷 불변.
- P2 **시각 눈검수 필수**(정량 PASS 가 통화/레이아웃 디테일 못 봄).

## 8. 비범위 (이번 PRD)
- AI/ask 의 US (별도), EDINET(일본), eco/credit rich 패리티의 완전성(P3 이후 점진).
