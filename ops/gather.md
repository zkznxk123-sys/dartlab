# Gather

> 상위 사상: [philosophy.md](philosophy.md) · 자가개선 루프: [coreloop.md](coreloop.md)

**주체**: gather 엔진 (`dartlab.gather(axis, stockCode?)` · `c.gather(axis)`).
**현재**: 주가 · 수급 · 뉴스 · ownership 축 · Naver · Yahoo · FMP fallback · 30 분 TTL 뉴스 · 5 분 TTL 주가 (KR).
**KRX 풀커버**: 전 상장사 일별 OHLCV/시총/발행주식수 1995~ 현재까지 HF dataset (`eddmpython/dartlab-data/krx/prices/`) 으로 사전 빌드. 매 평일 KST 17:00 cron 이 당일 데이터 + 누락 갭 자동 append → 사용자 키 없이 `gather("krx", ...)` 한 줄로 즉시 사용. 수정주가 (split/bonus/rights) 자동 적용.
**방향**: 미국 실시간성 보강 · news sentiment 정교화 · gather → quant 팩터 직결 · KRX events (배당/분할 공시) Stage 2 트랙으로 TR 모드 활성.

외부 시장 데이터 수집. 공시 데이터와 시장 데이터를 연결한다. 각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 1. 호출 — `gather()` 로 가이드, `gather("axis", "code")` 로 수집한다

```python
import dartlab
dartlab.gather()                       # 가이드 — 어떤 축이 있는지
dartlab.gather("price", "005930")      # 주가 시계열
```

### 노트북

[![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/02_gather.py)
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/02_gather.ipynb)

| 항목 | 내용 |
|---|---|
| 레이어 | L1 |
| 진입점 | `dartlab.gather()` · `c.gather()` |
| 소비 | 외부 소스 (Naver 차트 · Naver Global · FMP · FRED · ECOS · Google News) |
| 생산 | analysis · macro 가 gather 데이터를 소비 (주가 · 매크로) |
| 축 | 4 축 — price · flow · macro · news |

`gather/listing.py` (KRX 종목 매퍼) 는 유지되며, 사용자 진입점은 `dartlab.listing()` 단일 facade 로 통일 → `src/dartlab/gather/LISTING.md`.

---

## 2. API 키 미설정 시 — 3 경로로 안내한다

ECOS (한국은행) · FRED (미 연준) 등 외부 API 키를 환경변수에서 자동 read 하는 축은 키 부재 시 다음 경로를 따른다. (KRX OpenAPI 는 자동 read 하지 않는다 — 사용자는 ``gather("krx", ..., apiKey="...")`` 명시 인자만, 운영자 cron 만 환경변수 사용. §9 참조.)

- **대화형 CLI (TTY)** — `promptAndSave` 가 입력을 받아 `.env` 에 저장하고 계속 실행. 사용자가 건너뛰면 `None` 반환.
- **서버·백그라운드 (TTY 없음)** — `core.env.AuthKeyMissing` 예외를 raise. 예외 본문에 서비스명 · 발급 URL · `.env` 설정법 포함.
- **AI tool 경유** — `ai/runtime/toolLoop.py` 가 `AuthKeyMissing` 을 `status="auth_required"` 로 태깅하고 사용자 응답에 안내 그대로 전달.

관련: `core/env.py::AuthKeyMissing` · `gather.__init__._macroKR` · `_macroUS`.

**반복 실패** — 서버·AI 환경에서 키 없으면 조용히 `None` 반환하면 사용자가 원인을 모른다. 예외로 올려서 발급 URL + `.env` 설정법을 그대로 전달.

---

## 3. Company-bound — `c.gather` 로 종목코드 자동 전달한다

```python
c = dartlab.Company("005930")
c.gather("price")                # 주가 OHLCV (종목코드 자동 전달)
c.gather("flow")                 # 외국인·기관 수급
c.gather("news")                 # 뉴스

# EDGAR (미국)
c = dartlab.Company("AAPL")
c.gather("price")                # Naver Global → FMP (market="US" 자동)
c.gather("macro")                # FRED
c.gather("news")                 # Google News RSS
```

`c.gather()` 는 내부적으로 `dartlab.gather(axis, stockCode, market=...)` 를 호출. `EdgarCompany` 는 `market="US"` 자동 전달. `flow` 는 KR 전용 — EDGAR 에서 `None` 반환.

---

## 4. 4 축 — price · flow · macro · news

```python
# DART (한국)
dartlab.gather("price", "005930")              # 주가 OHLCV
dartlab.gather("price", "KOSPI")               # 코스피 지수
dartlab.gather("flow", "005930")               # 외국인·기관 수급
dartlab.gather("macro")                        # 거시지표 (ECOS + FRED)
dartlab.gather("news", "삼성전자")              # 뉴스

# EDGAR (미국) — Company-bound 시 market="US" 자동 전달
c = Company("AAPL")
c.gather("price")                             # Naver Global → FMP
c.gather("macro")                             # FRED
c.gather("news")                              # Google News RSS
```

### 시장 지수 심볼

| 심볼 | 별칭 | 소스 | 시장 |
|---|---|---|---|
| KOSPI | 코스피 | 네이버 차트 API | KR |
| KOSDAQ | 코스닥 | 네이버 차트 API | KR |
| KPI200 | 코스피 200 | 네이버 차트 API | KR |

---

## 5. 데이터 소스 · 캐시

| 축 | KR 소스 | US 소스 | 캐시 |
|---|---|---|---|
| price | Naver 차트 → Naver Global | Naver Global → FMP | 메모리 TTL |
| flow | Naver · KRX | — (KR 전용) | 메모리 TTL |
| macro | ECOS + FRED | FRED | Parquet + 30 분 TTL |
| news | Google News RSS | Google News RSS | GatherCache |

**반복 실패** — `flow` 는 KR 전용. 외국인·기관 수급 데이터는 KRX 에서만 제공되므로 EDGAR ticker 에서 `c.gather("flow")` 는 `None`. 미국 종목에 대한 flow 기대 금지.

---

## 6. 주요 모듈

| 모듈 | 역할 |
|---|---|
| `price.py` | 주가 OHLCV |
| `flow.py` | 수급 시계열 |
| `macro.py` | FRED · ECOS 거시지표, 변화율 계산, 리샘플링 |
| `news.py` | 뉴스 검색 |
| `search.py` | 웹 검색 (Tavily API) |
| `consensus.py` | 컨센서스 |
| `ownership.py` | 주주 정보 |
| `listing.py` | 종목 리스팅 + fuzzy search |
| `resilience.py` | Circuit breaker |

---

## 7. 소비 경로 — macro · analysis 두 엔진이 받아쓴다

gather 매크로 데이터를 두 엔진이 소비한다:

- **macro (L2)** — `dartlab.macro()` — 시장 레벨 매크로 해석 (사이클 · 금리 · 자산 · 심리 · 유동성). Company 불필요. → `src/dartlab/macro/README.md`.
- **analysis (L2)** — `c.analysis("financial", "매크로민감도")` — 기업별 외생변수 회귀. Company-bound.

---

## 8. 외생변수 체계 (analysis 연동)

`core/finance/exogenousAxes.py` — 6 축 28 지표 · 143 업종 매핑.
`gather/macro.py` 로 데이터 수집 → `calcMacroRegression` 에서 소비.

---

## 9. KRX OpenAPI 수집 경로 — 운영자 cron 벌크 + 사용자 API 선택 (EDGAR 와 동일 패턴)

EDGAR 의 벌크/API 분리 (`ops/api-contract.md §12`) 를 KRX 에도 동일하게 적용한다. **엔진 내부는 무조건 HF 데이터셋, 사용자 직접 호출만 자기 KRX_API_KEY**.

### 경로 분리 — 3 모드

| 경로 | 트리거 | 키 | 소스 | 출력 |
|---|---|---|---|---|
| **A. 운영자 cron (벌크)** | `.github/workflows/buildKrxData.yml` cron (KST 17:00 평일) | 환경변수 `KRX_API_KEY` (GitHub secret, 운영자 빌드 스크립트만 read) | KRX OpenAPI 직접 | HF dataset `eddmpython/dartlab-data` 의 `krx/prices/` 빌드 (long parquet) |
| **B. 사용자 + apiKey 명시** | `gather("krx", target, ..., apiKey="...")` | 인자 명시 (env 자동 read 없음) | KRX OpenAPI 직접 | **wide pivot** (행 = stockCode + corpName, 열 = 일자, value = target) |
| **C. 사용자 + apiKey 미명시 (기본)** | `gather("krx", target, ...)` | 키 불필요 | HF dataset 자동 | **wide pivot** (B 와 동일, 모든 사용자 동일 SSOT) |

### 저장 vs view — long 저장, wide 보여주기

- **저장 (HF parquet)**: long format (KRX 응답 그대로 + adjustment factor). SSOT, schema 안정,
  events join 친화, 신규 상장 시 row 추가만.
- **사용자 view (`gather("krx", target, ...)`)**: wide pivot — **행 = `stockCode` + `corpName`,
  열 = 일자 (YYYYMMDD)**. scan 의 횡단면 표준과 동일 컬럼 → scan 결과와 join 가능.
  한 row = 한 회사 → ranking/sort/screening 직관 (예: ``df.sort("20250630", descending=True).head(10)``
  한 줄로 그날 종가순 상위 10). 시계열 transform 시 `df.transpose(...)` 한 줄로 row=date 변환.
- **컬럼명 정합** — wide 모드는 quant 표준 (소문자 close/open/high/low/volume + stockCode/corpName/...),
  raw 모드 (`target="raw"`) 만 KRX 원본 그대로 (BAS_DD/ISU_CD/TDD_*/ACC_*).
- **엔진 internal**: long 형태가 group_by 친화 → `_hfBulk.loadFiltered` 직접 호출 (gatherKrx 거치지 않음).
- **escape hatch**: long 이 필요하면 `gather("krx", "raw", ...)` — events join 등 자유 가공.

### target 디스패치 (positional 첫 인자)

`gather("krx", <target>, ...)` 의 ``target`` 하나로 raw OHLCV / 시총 / 발행주식수 / 30+ 보조지표
모두 동일 진입점. 기본값 ``"close"``.

#### A. raw OHLCV/시총/발행주식수 (KRX 응답 → quant 표준 컬럼명)

| target | KRX raw 컬럼 | wide value 단위 |
|---|---|---|
| `close` (기본) | TDD_CLSPRC | 원 (Int64) |
| `open` | TDD_OPNPRC | 원 |
| `high` | TDD_HGPRC | 원 |
| `low` | TDD_LWPRC | 원 |
| `volume` | ACC_TRDVOL | 주 |
| `amount` | ACC_TRDVAL | 원 |
| `marketCap` (alias `mktcap`) | MKTCAP | 원 |
| `listShares` (alias `shares`) | LIST_SHRS | 주 |
| `fluctuationRate` (alias `fluc`) | FLUC_RT | % (Float64) |
| `priceChange` (alias `change`) | CMPPREVDD_PRC | 원 |
| `raw` | (KRX 원본 long DataFrame 그대로) | — |

#### B. 보조지표 (`gather/indicators.py` SSOT, 종목별 group 동시 계산)

| target 패턴 | 함수 | 기본 period | 입력 컬럼 |
|---|---|---|---|
| `ma{N}` · `sma{N}` | vsma | 20 | close |
| `ema{N}` | vema | 20 | close |
| `wma{N}` | vwma | 20 | close |
| `dema{N}` · `tema{N}` · `hma{N}` | vdema/vtema/vhma | 20 | close |
| `macd` | vmacd | (12/26/9) | close |
| `rsi{N}` | vrsi | 14 | close |
| `roc{N}` | vroc | 12 | close |
| `momentum{N}` | vmomentum | 10 | close |
| `cmo{N}` | vcmo | 14 | close |
| `atr{N}` | vatr | 14 | high·low·close |
| `adx{N}` | vadx | 14 | high·low·close |
| `cci{N}` | vcci | 20 | high·low·close |
| `williamsR{N}` | vwilliamsR | 14 | high·low·close |
| `ulcer{N}` | vulcer | 14 | close |
| `obv` | vobv | — | close·volume |
| `adl` | vadl | — | high·low·close·volume |
| `vwap` | vvwap | — | high·low·close·volume |
| `mfi{N}` | vmfi | 14 | high·low·close·volume |
| `forceIndex{N}` | vforceIndex | 13 | close·volume |
| `nvi` · `pvi` · `pvt` | vnvi/vpvi/vpvt | — | close·volume |
| `trix{N}` | vtrix | 15 | close |
| `dpo{N}` | vdpo | 20 | close |

이름은 lowercase 정규화 (camelCase 도 자동 — `williamsR14` ≡ `williamsr14`).

#### C. 보조지표 = 전종목 동시 계산 매커니즘

Polars `group_by(stockCode)` 안에서 각 그룹의 close/high/low/volume 을 NumPy 벡터 함수에
넘김 (gather/indicators.py 의 vsma/vrsi/...). 1년치 (~700K rows × 30 지표) ≈ 5~10초 (CPU).
GPU 옵션 (Polars `engine="gpu"`) 후속.

**환경변수 자동 read 는 Mode A 의 빌드 스크립트만**. 라이브러리 (`gather/krxApi.py`) 는
환경변수 자동 read 하지 않는다 — 사용자가 의식적으로 키를 명시 전달해야만 KRX OpenAPI 호출.

### KRX OpenAPI 키 발급 + 전달 방법 (Mode B)

1. https://openapi.krx.co.kr → 회원가입 (무료)
2. 로그인 → "API 인증키 신청" → 즉시 발급
3. 발급키 전달 3 가지:
   - 직접: ``gather("krx", date="2024-04-15", apiKey="발급키")``
   - .env: ``KRX_API_KEY=발급키`` 저장 → ``gather("krx", ..., apiKey=os.environ["KRX_API_KEY"])``
   - 셸: ``export KRX_API_KEY=발급키`` → 위 .env 와 동일

### 데이터 모델 (HF dataset — `core/dataConfig.DATA_RELEASES["krxPrices"]` SSOT)

```
huggingface.co/datasets/eddmpython/dartlab-data
└── krx/                                  # KRX 카테고리 (DATA_RELEASES["krxPrices"].dir)
    └── prices/
        ├── raw-{YYYY}.parquet            # 연도별 (각 ~30-50MB), row group pruning
        └── ...
```

events parquet (배당/분할/증자) 는 별도 트랙으로 추후 `krx/events/` 추가 예정 — `_adjustPrice` 가
이미 events 부재 시 raw + warning fallback 작동 (자동 활성화 준비됨).

yearly 파티션 = 너무 잘게 쪼개면 metadata overhead, 너무 크면 부분 fetch 비효율의 sweet spot. 한국 거래일 ~250일 × ~2800종목 ≈ 70만 행/년 → 압축 30~50MB → 단일 종목 fetch 시 ~1MB.

### 엔진 내부 액세스 (`gather/_hfBulk.py`)

```python
def loadFiltered(stockCode=None, year=None, start=None, end=None) -> pl.DataFrame:
    # 1. 필요 연도 결정 (year/start-end → [2024, 2025])
    # 2. ~/.cache/dartlab/krx-prices/raw-{year}.parquet 캐시 ETag 체크
    #    - 없거나 변경 → hf_hub_download 로 그 파일만 다운
    # 3. polars scan_parquet + filter (stockCode/date) → collect (row group pruning)
```

`quant/_helpers.py::fetch_ohlcv` 가 이걸 호출. 사용자 KRX_API_KEY 환경변수는 **엔진에서 절대 안 본다**.

### 사용자 직접 호출 (`gather/krxApi.py`)

**시그니처 통일 (2026-04-24)**: `date` 인자 폐기 → `start` 단독 = "그 날부터 오늘까지", `start+end` = 명시 기간, 단일일자 = `start=end` 명시.
SSOT — 모든 호출이 같은 정신모델 (기간 기반). `precision` 인자 = 보조지표 round 자릿수 (디폴트 2, finance 표준).

```python
import dartlab

# raw OHLCV — 단일일자 (start 만, end 자동 = start)
df = dartlab.gather("krx", "close", start="2025-06-30")                      # 종가 wide
df = dartlab.gather("krx", "marketCap", start="2025-06-30")                  # 시총
df = dartlab.gather("krx", "raw", start="2025-06-30")                        # long 원본 escape

# 기간 (start + end)
df = dartlab.gather("krx", "close", start="2020-01-01", end="2025-06-30")    # 기간 종가 wide
df = dartlab.gather("krx", "volume", start="2025-06-01", end="2025-06-30")   # 거래량 매트릭스

# 보조지표 — 전종목 동시 계산
rsi = dartlab.gather("krx", "rsi14", start="2025-01-01", end="2025-06-30")
ma = dartlab.gather("krx", "ma20", start="2025-01-01", end="2025-06-30")
macd = dartlab.gather("krx", "macd", start="2025-01-01", end="2025-06-30")

# 종목/시장 필터
df = dartlab.gather("krx", "close", start="2025-06-30", stockCodes=["005930","000660"])
df = dartlab.gather("krx", "close", start="2025-06-30", market="KOSDAQ")

# 본인 키로 직접 (장 마감 직후 즉시)
df = dartlab.gather("krx", "close", start="2025-06-30", apiKey=os.environ["KRX_API_KEY"])
```

`date=` 는 entry.py 가 legacy alias (start 로 매핑) — 호환 유지하되 새 코드는 `start` 사용 권장.

### gather("price", code) 의 indicators 옵션 — 단일종목/지수 OHLCV + 보조지표

```python
df = dartlab.gather("price", "005930")                              # 기본 = OHLCV + basic 9 지표 (sma5/20/60, ema12/26, rsi14, macd, atr14, obv)
df = dartlab.gather("price", "KOSPI")                               # 시장지수도 동일 동작
df = dartlab.gather("price", "005930", indicators=False)            # raw OHLCV 만
df = dartlab.gather("price", "005930", indicators=True)             # OHLCV + 30 지표 모두
df = dartlab.gather("price", "005930", indicators=["ma20","rsi14"]) # 일부만
```

**default = `"basic"`** — 종목/지수 호출 한 번에 즉시 분석 가능. 사용자 편의 원칙 (단일 import / 단일 호출 / 핵심 지표 자동 포함). raw OHLCV 만 원하면 `indicators=False` 명시.

`KRX_API_KEY` 미설정 시 `core.env.AuthKeyMissing` (CLI 는 `promptAndSave`, 서버는 발급 URL + .env 안내 — §2 참조).

### gather("krxindex", ...) — KRX 시장군별 전체 지수 일별 매매현황

```python
df = dartlab.gather("krxindex", "close", market="KOSPI", apiKey=os.environ["KRX_API_KEY"])
# → KOSPI 시장 모든 지수 (KOSPI 종합/200/100/섹터/스타일/사이즈) 일별 종가 wide

df = dartlab.gather("krxindex", "close", market="KOSDAQ",
                    indexFilter=["KOSDAQ150"], apiKey=...)
# → 단일 지수 + basic 9 보조지표 자동 (rsi14/sma20/macd/...)

df = dartlab.gather("krxindex", "raw", market="KRX", apiKey=...)
# → KRX 통합 지수 (KRX300, ESG, ...) long DataFrame (원본 컬럼)
```

- **endpoint**: `data-dbg.krx.co.kr/svc/apis/idx/{krx,kospi,kosdaq}_dd_trd` POST + JSON `{"basDd": "YYYYMMDD"}` + `AUTH_KEY` 헤더
- **카테고리 권한 별도** — sto (종목) 키와 분리. `https://openapi.krx.co.kr` 마이페이지에서 idx 카테고리 별도 신청 필수
- **한 호출 = 시장군 내 수십 개 지수** (종합/사이즈/섹터/스타일/ESG/테마)
- **활용**: 섹터 로테이션 alpha, 스타일 팩터 ground truth, 다중 benchmark, macro regime, ESG/테마
- 키 권한 부재 시 friendly error (HTTP 401 → "idx 카테고리 권한 없음, 마이페이지에서 별도 신청 필요")

### 장 마감 확정 가드 + 자동 갭 메움 (T-0 당일 포함)

- KRX OpenAPI 데이터는 KST 15:30 장 마감 후 정산까지 약 1시간 내 확정.
- 운영자 cron: KST 17:00 평일 — **당일 (T-0) 포함**. 17:00 시점이면 정산 완료라 그날 데이터 즉시 push.
- `buildIncremental` 은 1일 fixed 가 아니라 **"마지막 저장일 + 1 ~ today" 가변 윈도** fetch — cron 누락 / 캐시 miss / 정산 지연 등으로 갭이 생겨도 다음 cron 이 자동 메움.
- 마지막 저장일 조회: 로컬 parquet 우선 → HF 현재 연도 fallback (캐시 miss 대비).
- 사용자 호출도 동일 가드 — 오늘 날짜 호출 시 `"today not finalized — KRX confirms after 17:00 KST"` 경고 + None.

### 수정주가 — raw 저장 + 시점 계산 (CRSP 표준)

KRX OpenAPI 가 raw 만 제공. 수정주가는 dartlab 이 자체 계산:

- HF `krx/events/` 의 dividends + splits + capital 이벤트 → adjustment factor 시계열
- `gather/_adjustPrice.py::applyAdjustment(raw, events, mode="split"|"tr"|"raw")` 가 사용 시점에 계산
- 새 이벤트 발견 시 factor 만 재계산 → 전 역사 자동 소급 보정 (raw 영원히 불변)
- 알고리즘: backward chaining + ex-day boundary (smoke test 통과, ops/gather.md §9 참조)

### 수정주가 적용 PLAN (1년치 backfill 완료 후 진행)

**Step 1 — DART 공시 이벤트 원천**:
| 공시 유형 | DART rcept 보고서명 | 핵심 필드 | 영향 |
|---|---|---|---|
| 현금배당결정 | "현금ㆍ현물배당결정" | 배당기준일 (≈ 배당락일 D-1), 1주당 배당금 | divFactor (TR 모드만) |
| 주식분할결정 | "주식분할결정" | 분할 기일, 분할 비율 (newShares/oldShares) | splitFactor |
| 무상증자결정 | "무상증자결정" | 권리락일, 신주배정비율 | splitFactor (분할과 등가) |
| 유상증자결정 | "유상증자결정" | 권리락일, 신주가/시가 비율 | splitFactor (이론권리락 조정) |

**Step 2 — 수집 모듈 신설**:
- `src/dartlab/gather/dividend.py` — DART 배당결정 공시 파싱 → `data/dart/krx/events/dividends.parquet`
  - schema: BAS_DD (배당락일), ISU_CD, type="dividend", divPerShare, ratio=null
- `src/dartlab/gather/capitalEvent.py` — 분할/무상증자/유상증자 → `splits.parquet`, `capital.parquet`
  - schema: BAS_DD (권리락일/분할기일), ISU_CD, type ∈ {split, bonus, rights}, ratio, divPerShare=null
- `providers/dart` 의 기존 공시 파싱 인프라 재활용 (rcept_no → ZipDocsCollector → 본문 정규식 추출)

**Step 3 — HF events 카테고리 등록**:
- `core/dataConfig.DATA_RELEASES["krxEvents"]` — `dir = "krx/events"`, public=True
- `ops/data.md` DATA_RELEASES 표 + 워크플로우 표 갱신

**Step 4 — 운영 자동화**:
- `buildKrxData.yml` 의 incremental step 에 `gather/dividend` + `gather/capitalEvent` 추가 (어제 공시 1일치 증분)
- 또는 별도 `buildKrxEvents.yml` (DART rate limit 분리, dataSync 와 직렬화)

**Step 5 — _adjustPrice 자동 활성**:
- `_hfBulk.py::_loadEvents(stockCode)` placeholder 를 실제 HF fetch 로 교체:
  ```python
  def _loadEvents(stockCode):
      return loadHF("krx/events/dividends.parquet").filter(...).vstack(splits).vstack(capital)
  ```
- 한 번에 활성 — 기존 `_adjustPrice.applyAdjustment(raw, events, mode="split")` 는 events 도착 시 즉시 작동

**Step 6 — 검증 (sanity check)**:
- 005930 (삼성전자) 2018-05-04 50:1 액면분할:
  - raw 2018-05-03 종가 ≈ 2,650,000원
  - split-adjusted 2018-05-03 ≈ 53,000원
  - dartlab `gather("krx", stockCodes=["005930"], start="2018-04-01", end="2018-06-01")` 결과 검증
- 비교 대상: 네이버 fchart 의 수정주가 (split-only) 와 일치해야 함
- TR 모드 검증: 005930 의 10년 TR vs split-only 차이 = 누적 배당 (~연 2~3% × 10년 ≈ 25%)

**Step 7 — 사용자 호출 풀셋 완성**:
- `gather("krx", ..., adjustment="split")` 또는 `"tr"` 옵션 추가 (현재 wide 만, adjustment 디폴트 "split")
- 노트북 셀 + ops/gather.md 사용 예시 보강
- `_helpers.fetch_ohlcv` 를 `_hfBulk.loadFiltered` 로 교체 → quant 엔진 자동 연동

### 검증

```bash
# 엔진이 사용자 키 환경변수 안 보는지 (HF 만 써야 함)
grep -rn "KRX_API_KEY" src/dartlab/quant/ src/dartlab/scan/ src/dartlab/analysis/  # 0 건
# CI 워크플로우와 사용자 직접 호출 모듈만 KRX OpenAPI 직접 호출
grep -rn "openapi.krx.co.kr" src/dartlab/ .github/workflows/
```

**반복 실패** — 엔진 (quant · scan · analysis) 이 사용자 키 환경변수를 직접 보면 키 없는 사용자가 엔진 못 씀 + 결과 재현성 깨짐. 엔진은 무조건 HF, 사용자 직접 호출은 `gather("krx", ...)` 명시 경로에서만.

---

## 관련 코드

- `src/dartlab/gather/` — 19 모듈.
- `src/dartlab/gather/ecos/` — 한국은행 ECOS.
- `src/dartlab/gather/fred/` — FRED.

---

## 요약 — 명제 7 줄

1. `dartlab.gather()` 가이드, `gather("axis", "code")` 수집, `c.gather("axis")` 종목코드 자동.
2. 4 축 — price (OHLCV) · flow (KR 전용 수급) · macro (ECOS+FRED) · news (Google RSS).
3. API 키 부재 시 CLI 는 `promptAndSave`, 서버는 `AuthKeyMissing` 예외로 발급 URL 안내.
4. 시장 지수 심볼 — KOSPI · KOSDAQ · KPI200 네이버 차트 API.
5. 캐시 전략 — price 메모리 TTL · flow 메모리 TTL · macro Parquet + 30 분 TTL · news GatherCache.
6. macro 는 `dartlab.macro()` (시장 레벨) + `c.analysis("매크로민감도")` (기업 회귀) 두 엔진이 소비.
7. 외생변수 `exogenousAxes.py` 6 축 28 지표 143 업종 매핑이 `calcMacroRegression` 재료.
