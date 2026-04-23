# Scan

**주체**: scan 엔진 (`dartlab.scan()` 단일 진입점).
**현재**: DART 7축 정식 · EDGAR 11축 · 프리빌드 parquet (`edgar/scan/finance.parquet`) · 종목코드+종목명 첫 2컬럼 표준 · `_enrichWithKorean` 한글 매핑 경유.
**방향**: governance/지배구조 축 확대 · scan→review 블록 통합 · realData 스위트 단축.

전 종목 횡단분석. `scan()` 단일 진입점으로 시장 전체를 한 번에. DART + EDGAR 양쪽 지원.

## 사상 — account / ratio = primitive, 복합 축 = preset

scan 의 핵심 2 축은 `account` (계정 시계열) 와 `ratio` (비율 시계열). 둘 다 prebuild `finance.parquet` 을 lazy scan + pivot 으로 벡터 추출하며, 2664 종목 한 번에 계산된 wide DataFrame 을 반환한다.

| 축 | 함수 | 역할 |
|---|---|---|
| **`account`** | [`scanAccount(snakeId)`](../src/dartlab/providers/dart/finance/scanAccount.py) | 전종목 × 시계열 금액 (매출·영업이익·자산·부채 등) |
| **`ratio`** | [`scanRatio(ratioName)`](../src/dartlab/providers/dart/finance/scanAccount.py) | 전종목 × 시계열 비율 (영업이익률·ROE·부채비율·CCC 등) |

`profitability` · `growth` · `quality` · `liquidity` · `cashflow` · `dividendTrend` 등 복합 축은 자주 쓰는 **preset** 이다. 각 preset 은 `account` + `ratio` 결과를 polars join + with_columns 로 조합한 구조이며, 사용자 질문에 맞는 정확한 preset 이 없을 때도 `account` + `ratio` 두 primitive 를 자유 조합해 즉석 스크리닝을 구성할 수 있다.

scan 의 데이터 경로는 두 단계다. 첫째, prebuild `finance.parquet` 이 있으면 lazy scan + pivot 의 merged 경로로 2664 종목을 한 번에 계산한다. 둘째, prebuild 파일이 없거나 불완전하면 종목별 parquet 을 순회하는 per-file fallback (`_scanPerFile`) 이 동작한다. 두 경로 모두 종목별 최신 연도 필터는 [`filterLatestPerStock`](../src/dartlab/scan/_helpers.py) 공용 유틸을 통해 동일하게 처리된다.

### 질문 유형 → primitive 조합 매핑

| 사용자 질문 | 조합 패턴 |
|---|---|
| "요즘 성장세 좋은 회사" | `scanRatio("salesGrowth")` join `scanRatio("opIncomeGrowth")` — 둘 다 상위 교집합 |
| "돈 잘 버는 회사" | `scanRatio("roe")` + `scanRatio("opMargin")` — 수익성 복합 |
| "저평가인데 재무 탄탄" | `scan("valuation")` join `scanRatio("debtRatio")` + `scanRatio("currentRatio")` |
| "턴어라운드 조짐" | `scanRatio("opMargin", annual=False)` 분기 추이 — 4분기 부호 전환 필터 |
| "업종 평균 뛰어넘는" | scanRatio 결과 + listing 의 섹터 컬럼 join → 섹터별 rank |
| "매출 늘었는데 이익 줄어든" | `scanAccount("sales")` vs `scanAccount("operating_profit")` YoY diff |
| "최근 시장 어때" | `scan("valuation")` 상위 분포 + `scanRatio("salesGrowth")` 중앙값 + macro 사이클 |
| "자산 많은데 수익 못 내는 곳" | `scanAccount("total_assets")` + `scanRatio("roa")` — 자산 상위 & ROA 하위 |
| "배당 꾸준히 늘리는 곳" | `scan("dividendTrend")` 또는 `scanAccount("dividend")` 증가 패턴 |
| "FCF 늘고 있는 곳" | `scanAccount("operating_cashflow")` YoY · `scanAccount("capex")` 변화 |

### 관점별 스크리닝 프레임워크

**1. 가치 (Value)**: `scan("valuation")` 하위 (PBR/PER 낮음) × `scanRatio("roe")` 상위 — "싸면서 수익성 있는" 교집합.

**2. 성장 (Growth)**: `scanRatio("salesGrowth")` + `scanRatio("opIncomeGrowth")` + `scanRatio("netIncomeGrowth")` 모두 상위 — 외형·본업·순이익 동반 성장.

**3. 퀄리티 (Quality)**: `scanRatio("roe") > 15` · `scanRatio("accrualRatio") 낮음` · `scanRatio("cfNi") > 1` · `scanRatio("debtRatio") < 100` — 높은 이익률 + 현금창출 + 보수적 재무.

**4. 모멘텀 (Momentum)**: `scanAccount("operating_profit", annual=False)` 분기 개선 추세 — 최근 4분기 QoQ 양수.

**5. 배당 (Income)**: `scan("dividendTrend")` 연속 증가 + `scanRatio("opCfMargin")` 안정 — 현금 배당 지속 가능성.

**6. 턴어라운드 (Recovery)**: `scanRatio("opMargin")` 가 전전기 음수 → 최근 양수 반전 + `scanAccount("sales")` 동반 증가.

**7. 안정 (Defensive)**: `scanRatio("debtRatio") < 50` · `scanRatio("currentRatio") > 150` · `scanRatio("interestCoverage") > 5` — 위기 버티기.

### 기업 발굴 5 단계 워크플로

dartlab scan 이 상정하는 기업 발굴 흐름은 매크로 맥락 → 관점 선택 → primitive 조합 스크린 → 섹터/규모 보정 → 상위 N 종목 심층의 5 단계다.

1. **매크로 맥락**: `macro("사이클")` + `macro("자산배분")` 결과가 현재 어떤 관점을 유리하게 만드는지 제공한다. 회복 국면에서는 성장·모멘텀, 스태그플레이션 국면에서는 안정·배당 관점이 자산배분 시그널과 맞물린다.
2. **관점별 preset 스크린**: 위 7 관점 중 매크로 판단에 맞는 것을 1~2 개 선택한다. primitive 조합으로 후보 50~100 종목이 추려진다.
3. **섹터 / 규모 보정**: `listing()` 과 join 하면 섹터별 · 시총별 편중이 드러난다. 한 업종에 몰리는 경우 그 업종 특이 요인인지 전반 시장 패턴인지 구분된다.
4. **상위 N 심층**: 후보 상위 5~10 종목에 대해 `Company(stockCode).analysis("종합평가")` · `credit` · `show` 가 개별 검증 경로다. scan 은 필터 축, Company 엔진은 개별 종목 판단 축이다.
5. **과거 서사 확인**: `pastInsight(stockCode)` 는 과거 판단 컨텍스트를 제공한다. 이전 블로그 · analysis 가 남아있으면 현재 판단의 기준점이 된다.

---

## 호출 계약

```python
import dartlab
dartlab.scan()                    # 가이드 — 20축 + 사용 예시
dartlab.scan("profitability")     # 전종목 수익성 비교
```

## 노트북

[![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/03_scan.py)
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/03_scan.ipynb)

---

| 항목 | 내용 |
|------|------|
| 레이어 | L1 |
| 진입점 | `dartlab.scan()`, `c.governance()` 등 |
| 소비 | providers/(dart, edgar), core/finance, 프리빌드 parquet |
| 생산 | ai가 시장 비교에 사용, analysis와 독립 |
| 축 | DART 20축, EDGAR 11축 |

## 단일 진입점

- **`dartlab.scan()`** 하나로 모든 축에 접근한다
- `c.governance()` 등은 scan 내부 view — 별도 전역 함수가 아니다
- 새 축은 `scan/` 아래 모듈로 추가한다

## 20축 전체 목록

### 비재무 축 (company-bound + market-level)

| 축 | 타입 | 소스 | 설명 |
|------|------|------|------|
| governance | company-bound | majorHolder, outsideDirector, executivePay, auditOpinion, minorityHolder | 지배구조 5축 100점 → A~E 등급 |
| workforce | company-bound | employee, executivePayIndividual, finance IS | 인력/급여, 인건비율, 1인당부가가치, 급여매출괴리 |
| capital | company-bound | dividend, treasuryStock, capitalChange | 주주환원 분류 (환원형/중립/희석형) |
| debt | company-bound | corporateBond, finance BS/IS | 부채 구조, ICR, 위험등급 |
| network | market-level | docs sections | 관계 네트워크 (dict 반환) |
| disclosureRisk | market-level | changes.parquet | 공시 변화 선행 리스크 (우발부채, 키워드, 감사변경, 계열변화, 사업전환) |
| insider | market-level | majorHolder | 최대주주 지분변동, 자기주식 현황, 경영권 안정성 |
| audit | market-level | auditOpinion | 감사의견, 감사인변경, 특기사항, 감사독립성비율 |

### 재무 8축 (financial 그룹)

2-level 호출 지원: `scan("financial")` → 8축 가이드, `scan("financial", "수익성")` → 수익성 실행.

| 축 | 설명 |
|------|------|
| profitability | 영업이익률/순이익률/ROE/ROA + 등급 |
| growth | 매출/영업이익/순이익 CAGR + 성장 패턴 분류 (6종) |
| efficiency | 자산/재고/매출채권 회전율 + CCC(현금전환주기) + 등급 |
| quality | Accrual Ratio + CF/NI 비율 — 이익이 현금 뒷받침되는지 |
| liquidity | 유동비율 + 당좌비율 — 단기 지급능력 |
| valuation | PER/PBR/PSR + 시가총액 + 등급. 일일 prebuild snapshot (HF `dart/scan/valuation.parquet`, GH Actions cron KST 04:00). 1초 이내 로드. 장중 급변 시 `refresh=True` 로 네이버 재수집 (~50초). |
| cashflow | OCF/ICF/FCF + 현금흐름 패턴 분류 (8종) |
| dividendTrend | DPS 3개년 시계열 + 패턴 분류 (연속증가/안정/감소/시작/중단) |

### 데이터 축 (target 필수)

| 축 | 설명 |
|------|------|
| account | 전종목 단일 계정 시계열 (매출액, 영업이익 등). `scan("account", "매출액")` |
| ratio | 전종목 단일 재무비율 시계열 (ROE, 부채비율 등). `scan("ratio", "roe")` |

### 분석 축

| 축 | 설명 |
|------|------|
| macroBeta | 전종목 GDP/금리/환율 베타 횡단면 (OLS 회귀) |
| screen | 멀티팩터 스크리닝 (value/dividend/growth/risk/quality 프리셋) |

## Company-bound 인터페이스

```python
c = dartlab.Company("005930")

c.governance()          # 이 회사 1행
c.governance("all")     # 전체 상장사
c.governance("market")  # 유가/코스닥 요약
c.workforce()           # 직원수, 평균급여, 인건비율
c.capital()             # 배당, 자사주, 환원 분류
c.debt()                # 사채만기, 부채비율, ICR
c.network()             # 출자/지분/계열 관계
```

governance/workforce/capital/debt/network 5축이 Company-bound.
나머지 축은 `dartlab.scan("축이름")` market-level API로만 접근.

## scan 프리빌드 가속

종목별 parquet 순차 스캔 → 수분. 프리빌드 합산 parquet → **17초**.

```
data/dart/scan/
├── changes.parquet           # docs 변화 전종목 5Y (~51MB)
├── finance.parquet           # finance 전종목 5Y (~307MB)
├── finance-lite.parquet      # 브라우저 pyodide 용 경량본 (~18MB, 30계정 × 2022~분기)
├── sharesOutstanding.parquet # 상장주식수 (~1MB)
└── report/                   # apiType별 12개 parquet
```

- 배포자: `dartlab collect --scan` → HF push (자동 파이프라인 `dataPrebuild.yml` 12h 주기)
- 사용자: `downloadAll("scan")` (약 360MB) → 즉시 횡단 분석
- scan 파일 없으면 HF 자동 다운로드 시도, 실패 시 종목별 순회 fallback
- **첫 호출 안내**: 로컬 프리빌드가 없으면 `scan:prebuild_missing` → 다운로드 → `scan:prebuild_ready`. 실패 시 `scan:prebuild_failed`, 불완전 다운로드면 `scan:prebuild_incomplete`. `_ALWAYS_SHOW` 카테고리라 verbose=False 여도 출력

### finance-lite (pyodide/브라우저 전용)

- **목적**: `finance.parquet`(307MB) 은 브라우저 fetch 비용 + polars WASM `scan_parquet` 미지원 때문에 쓸 수 없음. 주요 30 계정 × 2022~ 분기만 추린 **18MB** 경량본이 pyodide 전용 대체본
- **SSOT**: 계정 리스트 `src/dartlab/scan/_helpers.py::LITE_ACCOUNTS` (IS 10 + BS 12 + CF 8 = 30)
- **빌드**: `dartlab collect --scan finance-lite` 또는 `buildScan()` 이 자동 포함. 기존 `finance.parquet` 에서 필터만 하므로 <1초
- **로딩 경로**:
  - 일반 환경: `scanAccount` 가 `finance.parquet` 우선 사용 (finance-lite 는 무시)
  - Pyodide: `scanAccount` 가 `finance-lite.parquet` 로 분기 → `pyarrow.parquet.read_table` + `pl.from_arrow` 경유 (WASM polars `scan_parquet` 미지원 우회)
- **경량본에 없는 계정을 pyodide 에서 조회하면** `_scanAccountFromMerged` 가 빈 DataFrame 반환 → 기존 fallback (`data/dart/finance/*.parquet`) 시도. 브라우저엔 종목별 파일도 없어 최종 빈 결과 (경고 emit)

## EDGAR scan (11축)

EDGAR scan은 XBRL companyfacts 기반. DART scan과 동일 인터페이스.

```python
from dartlab.scan._edgar_scan import edgarScan
df = edgarScan("profitability")   # 전종목 수익성
df = edgarScan("valuation")       # 밸류에이션
```

### EDGAR scan 축

| 축 | 지표 | 종목 수 | 상태 |
|---|------|--------|------|
| profitability | opMargin, netMargin, ROE, ROA | ~6,600 | ✅ |
| growth | revenueYoY, opYoY, niYoY | ~5,600 | ✅ |
| quality | cfToNi, accrualRatio | ~8,300 | ✅ |
| liquidity | currentRatio, quickRatio | ~4,800 | ✅ |
| efficiency | assetTurnover, CCC | ~6,100 | ✅ |
| cashflow | OCF/ICF/FCF, 패턴 분류 | ~5,700 | ✅ |
| dividendTrend | payoutRatio, 패턴 | ~4,000 | ✅ |
| capital | 배당+자사주, 분류 | ~4,800 | ✅ |
| debt | debtRatio, ICR, 위험등급 | ~7,300 | ✅ |
| valuation | EBITDA, equityMultiplier, ROE | ~16,500 | ✅ |
| audit | AuditFees, NonAuditFees | 가변 | ✅ |

### EDGAR scan 프리빌드

```
data/edgar/scan/
└── finance.parquet    # 전종목 연간 BS/IS/CF 주요 22계정
```

- 빌드: `dartlab collect --tier sp500 --scan` 또는 `buildEdgarScan(sinceYear=2021)`
- 배치 200개 단위 + 중간 파일 병합 (메모리 안전)
- DART scan 프리빌드와 동일 패턴

### DART vs EDGAR scan 갭

| 축 | DART | EDGAR | 사유 |
|---|------|-------|------|
| governance | ✅ 5축 100점 | — | DEF 14A proxy 파싱 필요 |
| workforce | ✅ | — | SEC 구조화 데이터 없음 (10-K 텍스트 제한적) |
| network | ✅ | — | SEC에 출자/계열 관계 구조화 데이터 없음 |
| signal | ✅ | — | DART 공시 키워드 트렌드 전용 |
| disclosureRisk | ✅ | — | DART changes.parquet 전용 |

## scan → review 모듈 매핑

scan 은 review 6-4 "비교분석" 섹션에 독립 calc 모듈로 **교차 조합 관점**을 제공한다.
전종목 횡단 데이터를 2~3축 교차하면 단일 종목에서 안 보이는 뷰가 나온다:

- 수익성 × 성장성 → "성숙기 캐시카우" / "고성장 고마진"
- 부채 × 자본환원 → "레버리지 주주환원" / "무차입 보수"
- 매출 순위 × 영업이익 순위 → "마진 프리미엄" / "규모만 큰 저마진"

| calc 함수 (`scan/extended.py`) | review 블록 | 서사 내용 |
|---|---|---|
| `calcPeerPosition` | peerPosition | 수익성/성장/품질/부채 백분위 + 교차 관점 |
| `calcGovernanceSummary` | governanceSummary | 지배구조 5축 점수/등급 |

scan/finance.parquet 프리빌드 사용 → 단일 종목 filter 빠름.

## 설계 원칙

- scanner는 Company를 import하지 않는다 (역의존 방지)
- Company에서 scan 데이터는 `_ensure*()` 경유로 접근
- scan → review calc 함수 (`scan/extended.py`) 는 review 가 호출하는 wrapper
- 스코어링/분류 로직 변경은 실험 검증 후 반영

## 관련 코드

| 경로 | 역할 |
|------|------|
| `src/dartlab/scan/` | DART 축 모듈 |
| `src/dartlab/scan/_edgar_scan.py` | EDGAR 11축 scan 디스패치 |
| `src/dartlab/scan/_edgar_helpers.py` | EDGAR scan 공용 헬퍼 |
| `src/dartlab/scan/edgarBuilder.py` | EDGAR scan 프리빌드 |
| `src/dartlab/scan/network/` | 관계 네트워크 (DART 전용) |
| `src/dartlab/scan/disclosureRisk/` | 공시 변화 리스크 (DART 전용) |
| `src/dartlab/core/finance/scanAccount.py` | 범용 계정/비율 전종목 조회 |
| `src/dartlab/providers/edgar/finance/scanAccount.py` | EDGAR 계정 스캔 |
