# Scan

> 상위 사상: [philosophy.md](philosophy.md) · 자가개선 루프: [coreloop.md](coreloop.md)

**주체**: scan 엔진 (`dartlab.scan()` 단일 진입점).
**현재**: DART 7 축 정식 · EDGAR 11 축 · 프리빌드 parquet (`edgar/scan/finance.parquet`) · 종목코드 + 종목명 첫 2 컬럼 표준 · `_enrichWithKorean` 한글 매핑 경유.
**방향**: governance·지배구조 축 확대 · scan → story 블록 통합 · realData 스위트 단축.

전 종목 횡단분석. `scan()` 단일 진입점으로 시장 전체를 한 번에. DART + EDGAR 양쪽 지원. 각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 1. 사상 — `account` · `ratio` 가 primitive, 복합 축은 preset

scan 의 핵심 2 축은 `account` (계정 시계열) 와 `ratio` (비율 시계열). 둘 다 prebuild `finance.parquet` 을 lazy scan + pivot 으로 벡터 추출하며, 전 상장사 한 번에 계산된 wide DataFrame 을 반환한다.

| 축 | 함수 | 역할 |
|---|---|---|
| **`account`** | [`scanAccount(snakeId)`](../src/dartlab/providers/dart/finance/scanAccount.py) | 전종목 × 시계열 금액 (매출 · 영업이익 · 자산 · 부채 등) |
| **`ratio`** | [`scanRatio(ratioName)`](../src/dartlab/providers/dart/finance/scanAccount.py) | 전종목 × 시계열 비율 (영업이익률 · ROE · 부채비율 · CCC 등) |

`profitability` · `growth` · `quality` · `liquidity` · `cashflow` · `dividendTrend` 등 복합 축은 자주 쓰는 **preset**. 각 preset 은 `account` + `ratio` 결과를 polars join + `with_columns` 로 조합한 구조이며, 사용자 질문에 맞는 정확한 preset 이 없을 때도 `account` + `ratio` 두 primitive 를 자유 조합해 즉석 스크리닝을 구성한다.

### 데이터 경로 — prebuild 우선, fallback per-file

첫째, prebuild `finance.parquet` 이 있으면 lazy scan + pivot 의 merged 경로로 전 상장사를 한 번에 계산. 둘째, prebuild 파일이 없거나 불완전하면 종목별 parquet 을 순회하는 per-file fallback (`_scanPerFile`) 이 동작. 두 경로 모두 종목별 최신 연도 필터는 [`filterLatestPerStock`](../src/dartlab/scan/_helpers.py) 공용 유틸을 통해 동일하게 처리.

---

## 2. 광역 발굴 SSOT — docstring 이 원천

"투자할만한 회사 / 좋은 회사 / 요즘 투자하기 좋은 / 성장세 좋은 / 배당 좋은 / 저평가 / 턴어라운드" 같은 **광역 발굴 질문** 에 답하는 구체 사용법은 다음 두 독스트링이 단일 원천이다.

- **[`scanRatio` docstring Guide](../src/dartlab/providers/dart/finance/scanAccount.py)** — 7 관점 스크리닝 레시피 (가치 · 성장 · 퀄리티 · 모멘텀 · 배당 · 턴어라운드 · 안정), 질문→primitive 매핑, 5 단계 발굴 워크플로, "투자할만한 회사" 기본 레시피 예제.
- **[`scanAccount` docstring Guide](../src/dartlab/providers/dart/finance/scanAccount.py)** — 계정 원자의 4 사용 패턴과 scanRatio 와의 join 예시.

docstring 은 `inspect.getdoc` 경로로 `ai/tools/__init__.py::_toolDescription` 에 흘러 AI tool schema 의 description 으로 직접 노출된다. 즉 `ops/scan.md` 는 참조 인덱스이고, 레시피 본문·새 관점·새 질문 유형 추가는 **docstring 에 박는다** (프로젝트 최상위 규칙: SSOT · Simple > Complex).

**반복 실패** — 같은 매핑 표·스크리닝 레시피를 ops · 프롬프트 · 독스트링 세 곳에 중복 관리 → 한 곳 수정 시 나머지가 뒤쳐짐. docstring 단일 SSOT, ops 는 포인터만, 프롬프트는 "docstring Guide 참고" 한 줄.

---

## 3. 필드 탐색형 스크리닝 — fields → screen spec → 심층 검증

조건형 종목 발굴은 `scan("fields")` 와 `scan("screen", spec=...)` 두 단계로 간다.

```python
dartlab.scan("fields", "roe")
dartlab.scan("screen", spec={
    "where": [
        {"field": "finance.ratio.roe", "op": ">", "value": 10},
        {"field": "finance.ratio.debtRatio", "op": "between", "value": [0, 100]},
    ],
    "select": ["krx.marketCap", "krx.rsi14"],
    "sort": {"field": "finance.ratio.roe", "desc": True},
    "limit": 30,
})
```

필드 카탈로그는 하나의 SSOT (`scan/fields.py`) 로 관리한다. 반환 컬럼은
`field`, `label`, `source`, `kind`, `unit`, `operatorSet`, `coverage`, `example`,
`notes` 로 고정한다. 원천은 다음처럼 의미를 나눈다.

| source | 실행 의미 |
|---|---|
| finance | `scanAccountList()` + `scanRatioList()` 기반 수치 필터 |
| valuation | 일일 prebuild 밸류에이션 snapshot 최신값 필터 |
| report | 구조화 공시 API type/컬럼 필터. prebuild 없으면 fallback 가능하나 느릴 수 있음 |
| docs | 검색 인덱스 hit 기반 후보 생성. 완전한 원문 boolean scan 으로 표현하지 않음 |
| krx | KRX 가격·거래·시총·기술지표 최신값 필터. 기본 window 는 최근 252 거래일 |
| krxIndex | 시장 지수 컨텍스트 컬럼. 종목별 필터 조건으로 쓰지 않음 |

`screen` spec 계약은 v1 에서 좁게 유지한다.

| 키 | 의미 |
|---|---|
| `where` | AND 조건 리스트 |
| `any` | OR 조건 리스트 |
| `select` | 결과에 붙일 field 리스트 |
| `sort` | `{"field": "...", "desc": true}` |
| `limit` | 반환 행 수. 기본 50 |

**반복 실패** — `finance/report/docs/krx/krxIndex` 를 하나의 거대 DataFrame 으로 합치려는 설계. 원천별 비용·의미가 다르므로 카탈로그로 발견하고 실행기는 필요한 필드만 로드한다.

**반복 실패** — 단일 지표 하나로 “좋은 종목”을 확정. 후보 발굴은 최소 3관점 교차 검증 후 Company/analysis 로 원문·재무제표를 다시 확인한다.

---

## 5. 호출 계약

```python
import dartlab
dartlab.scan()                    # 가이드 — 20축 + 사용 예시
dartlab.scan("profitability")     # 전종목 수익성 비교
dartlab.scan("fields", "매출")     # 조건형 스크리닝 필드 검색
dartlab.scan("screen", spec={...}) # 조건 조합 후보 추출
```

### 노트북

[![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/03_scan.py)
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/03_scan.ipynb)

`03_scan` 노트북은 마지막 코드 셀에서 `scan("fields", "roe")` 로 필드 키를
확인한 뒤 `scan("screen", spec=...)` 으로 ROE·부채비율 조건 후보를 좁히는
예시를 제공한다. 설명은 마크다운 셀이 아니라 코드 주석으로 둔다.

| 항목 | 내용 |
|---|---|
| 레이어 | L1 |
| 진입점 | `dartlab.scan()` · `c.governance()` 등 |
| 소비 | `providers/` (dart · edgar) · `core/finance` · 프리빌드 parquet |
| 생산 | AI 가 시장 비교에 사용, analysis 와 독립 |
| 축 | DART 20 축, EDGAR 11 축 |

---

## 6. 단일 진입점 — `dartlab.scan()` 하나로 모든 축에 접근한다

- `dartlab.scan()` 하나로 모든 축에 접근.
- `c.governance()` 등은 scan 내부 view — 별도 전역 함수가 아니다.
- 새 축은 `scan/` 아래 모듈로 추가한다.

**반복 실패** — 축별 전역 함수 (`dartlab.profitability()` 등) 를 추가 → 진입점 분열. 항상 `scan("축")` 단일 진입점 유지.

---

## 7. 20 축 — 비재무 8 + 재무 8 + 데이터 2 + 분석 2

### 비재무 축 (company-bound + market-level)

| 축 | 타입 | 소스 | 설명 |
|---|---|---|---|
| governance | company-bound | majorHolder · outsideDirector · executivePay · auditOpinion · minorityHolder | 지배구조 5 축 100 점 → A~E 등급 |
| workforce | company-bound | employee · executivePayIndividual · finance IS | 인력·급여 · 인건비율 · 1 인당부가가치 · 급여매출괴리 |
| capital | company-bound | dividend · treasuryStock · capitalChange | 주주환원 분류 (환원형·중립·희석형) |
| debt | company-bound | corporateBond · finance BS · IS | 부채 구조 · ICR · 위험등급 |
| network | market-level | docs sections | 관계 네트워크 (dict 반환) |
| disclosureRisk | market-level | `changes.parquet` | 공시 변화 선행 리스크 (우발부채 · 키워드 · 감사변경 · 계열변화 · 사업전환) |
| insider | market-level | majorHolder | 최대주주 지분변동 · 자기주식 현황 · 경영권 안정성 |
| audit | market-level | auditOpinion | 감사의견 · 감사인변경 · 특기사항 · 감사독립성비율 |

### 재무 8 축 (financial 그룹)

2-level 호출 지원 — `scan("financial")` → 8 축 가이드, `scan("financial", "수익성")` → 수익성 실행.

| 축 | 설명 |
|---|---|
| profitability | 영업이익률·순이익률·ROE·ROA + 등급 |
| growth | 매출·영업이익·순이익 CAGR + 성장 패턴 분류 (6 종) |
| efficiency | 자산·재고·매출채권 회전율 + CCC (현금전환주기) + 등급 |
| quality | Accrual Ratio + CF/NI 비율 — 이익이 현금 뒷받침되는지 |
| liquidity | 유동비율 + 당좌비율 — 단기 지급능력 |
| valuation | PER·PBR·PSR + 시가총액 + 등급. 일일 prebuild snapshot (HF `dart/scan/valuation.parquet`, GH Actions cron KST 04:00). 1 초 이내 로드. 장중 급변 시 `refresh=True` 로 네이버 재수집 (~50 초). |
| cashflow | OCF·ICF·FCF + 현금흐름 패턴 분류 (8 종) |
| dividendTrend | DPS 3 개년 시계열 + 패턴 분류 (연속증가·안정·감소·시작·중단) |

### 데이터 축 (target 필수)

| 축 | 설명 |
|---|---|
| account | 전종목 단일 계정 시계열 (매출액 · 영업이익 등). `scan("account", "매출액")` |
| ratio | 전종목 단일 재무비율 시계열 (ROE · 부채비율 등). `scan("ratio", "roe")` |

### 분석 축

| 축 | 설명 |
|---|---|
| macroBeta | 전종목 GDP·금리·환율 베타 횡단면 (OLS 회귀) |
| fields | 조건형 스크리닝 필드 카탈로그 |
| screen | 멀티팩터 스크리닝 (value · dividend · growth · risk · quality 프리셋 + spec 조건) |

---

## 8. Company-bound — 5 축이 Company 진입

```python
c = dartlab.Company("005930")

c.governance()          # 이 회사 1행
c.governance("all")     # 전체 상장사
c.governance("market")  # 유가·코스닥 요약
c.workforce()           # 직원수, 평균급여, 인건비율
c.capital()             # 배당, 자사주, 환원 분류
c.debt()                # 사채만기, 부채비율, ICR
c.network()             # 출자/지분/계열 관계
```

`governance` · `workforce` · `capital` · `debt` · `network` 5 축이 Company-bound. 나머지 축은 `dartlab.scan("축이름")` market-level API 로만 접근.

---

## 9. 프리빌드 — finance.parquet 으로 17 초에 전종목 스캔

종목별 parquet 순차 스캔은 수분, 프리빌드 합산 parquet 은 17 초.

```
data/dart/scan/
├── changes.parquet           # docs 변화 전종목 5Y (~51MB)
├── finance.parquet           # finance 전종목 5Y (~307MB)
├── finance-lite.parquet      # 브라우저 pyodide 용 경량본 (~18MB, 30계정 × 2022~분기)
├── sharesOutstanding.parquet # 상장주식수 (~1MB)
└── report/                   # apiType별 12개 parquet
```

- 배포자 — `dartlab collect --scan` → HF push (자동 파이프라인 `dataPrebuild.yml` 12h 주기).
- 사용자 — `downloadAll("scan")` (약 360MB) → 즉시 횡단 분석.
- scan 파일 없으면 HF 자동 다운로드 시도, 실패 시 종목별 순회 fallback.
- **첫 호출 안내** — 로컬 프리빌드가 없으면 `scan:prebuild_missing` → 다운로드 → `scan:prebuild_ready`. 실패 시 `scan:prebuild_failed`, 불완전 다운로드면 `scan:prebuild_incomplete`. `_ALWAYS_SHOW` 카테고리라 `verbose=False` 여도 출력.

### finance-lite (pyodide · 브라우저 전용)

- **목적** — `finance.parquet` (307MB) 은 브라우저 fetch 비용 + polars WASM `scan_parquet` 미지원 때문에 사용 불가. 주요 30 계정 × 2022~ 분기만 추린 **18MB** 경량본이 pyodide 전용 대체본.
- **SSOT** — 계정 리스트 `src/dartlab/scan/_helpers.py::LITE_ACCOUNTS` (IS 10 + BS 12 + CF 8 = 30).
- **빌드** — `dartlab collect --scan finance-lite` 또는 `buildScan()` 이 자동 포함. 기존 `finance.parquet` 에서 필터만 하므로 <1 초.
- **로딩 경로**
  - 일반 환경 — `scanAccount` 가 `finance.parquet` 우선 사용 (finance-lite 는 무시).
  - Pyodide — `scanAccount` 가 `finance-lite.parquet` 로 분기 → `pyarrow.parquet.read_table` + `pl.from_arrow` 경유 (WASM polars `scan_parquet` 미지원 우회).
- **경량본에 없는 계정을 pyodide 에서 조회하면** `_scanAccountFromMerged` 가 빈 DataFrame 반환 → 기존 fallback (`data/dart/finance/*.parquet`) 시도. 브라우저엔 종목별 파일도 없어 최종 빈 결과 (경고 emit).

**반복 실패** — 프리빌드 없는 상태로 scan 호출 → per-file fallback 으로 수분 걸림. `downloadAll("scan")` 또는 `dataPrebuild.yml` 자동 파이프라인 활용.

---

## 10. EDGAR scan — 11 축, XBRL companyfacts 기반

EDGAR scan 은 XBRL companyfacts 기반. DART scan 과 동일 인터페이스.

```python
from dartlab.scan._edgar_scan import edgarScan
df = edgarScan("profitability")   # 전종목 수익성
df = edgarScan("valuation")       # 밸류에이션
```

### EDGAR scan 축

| 축 | 지표 | 종목 수 | 상태 |
|---|---|---|---|
| profitability | opMargin · netMargin · ROE · ROA | ~6,600 | ✓ |
| growth | revenueYoY · opYoY · niYoY | ~5,600 | ✓ |
| quality | cfToNi · accrualRatio | ~8,300 | ✓ |
| liquidity | currentRatio · quickRatio | ~4,800 | ✓ |
| efficiency | assetTurnover · CCC | ~6,100 | ✓ |
| cashflow | OCF · ICF · FCF + 패턴 분류 | ~5,700 | ✓ |
| dividendTrend | payoutRatio + 패턴 | ~4,000 | ✓ |
| capital | 배당 + 자사주, 분류 | ~4,800 | ✓ |
| debt | debtRatio · ICR · 위험등급 | ~7,300 | ✓ |
| valuation | EBITDA · equityMultiplier · ROE | ~16,500 | ✓ |
| audit | AuditFees · NonAuditFees | 가변 | ✓ |

### EDGAR scan 프리빌드

```
data/edgar/scan/
└── finance.parquet    # 전종목 연간 BS/IS/CF 주요 22계정
```

- 빌드 — `dartlab collect --tier sp500 --scan` 또는 `buildEdgarScan(sinceYear=2021)`.
- 배치 200 개 단위 + 중간 파일 병합 (메모리 안전).
- DART scan 프리빌드와 동일 패턴.

### DART vs EDGAR scan 갭

| 축 | DART | EDGAR | 사유 |
|---|---|---|---|
| governance | ✓ 5 축 100 점 | — | DEF 14A proxy 파싱 필요 |
| workforce | ✓ | — | SEC 구조화 데이터 없음 (10-K 텍스트 제한적) |
| network | ✓ | — | SEC 에 출자·계열 관계 구조화 데이터 없음 |
| signal | ✓ | — | DART 공시 키워드 트렌드 전용 |
| disclosureRisk | ✓ | — | DART `changes.parquet` 전용 |

---

## 11. scan → story 모듈 매핑

scan 은 story 6-4 "비교분석" 섹션에 독립 calc 모듈로 **교차 조합 관점** 을 제공. 전종목 횡단 데이터를 2~3 축 교차하면 단일 종목에서 안 보이는 뷰가 나온다:

- 수익성 × 성장성 → "성숙기 캐시카우" · "고성장 고마진".
- 부채 × 자본환원 → "레버리지 주주환원" · "무차입 보수".
- 매출 순위 × 영업이익 순위 → "마진 프리미엄" · "규모만 큰 저마진".

| calc 함수 (`scan/extended.py`) | story 블록 | 서사 내용 |
|---|---|---|
| `calcPeerPosition` | peerPosition | 수익성·성장·품질·부채 백분위 + 교차 관점 |
| `calcGovernanceSummary` | governanceSummary | 지배구조 5 축 점수·등급 |

`scan/finance.parquet` 프리빌드 사용 → 단일 종목 filter 빠름.

---

## 12. 설계 원칙

- scanner 는 Company 를 import 하지 않는다 (역의존 방지).
- Company 에서 scan 데이터는 `_ensure*()` 경유로 접근.
- scan → story calc 함수 (`scan/extended.py`) 는 story 가 호출하는 wrapper.
- 스코어링·분류 로직 변경은 실험 검증 후 반영.

**반복 실패** — scanner 가 Company 를 import 하면 역의존 발생. Company 쪽에서만 `_ensure*()` 로 scan 데이터 당겨 쓴다.

---

## 관련 코드

| 경로 | 역할 |
|---|---|
| `src/dartlab/scan/` | DART 축 모듈 |
| `src/dartlab/scan/_edgar_scan.py` | EDGAR 11 축 scan 디스패치 |
| `src/dartlab/scan/_edgar_helpers.py` | EDGAR scan 공용 헬퍼 |
| `src/dartlab/scan/edgarBuilder.py` | EDGAR scan 프리빌드 |
| `src/dartlab/scan/network/` | 관계 네트워크 (DART 전용) |
| `src/dartlab/scan/disclosureRisk/` | 공시 변화 리스크 (DART 전용) |
| `src/dartlab/core/finance/scanAccount.py` | 범용 계정·비율 전종목 조회 |
| `src/dartlab/providers/edgar/finance/scanAccount.py` | EDGAR 계정 스캔 |

---

## 요약 — 명제 10 줄

1. scan 은 `dartlab.scan()` 단일 진입점으로 전종목 횡단분석, DART 20 축 + EDGAR 11 축.
2. `account` · `ratio` 가 primitive, 복합 축 (profitability · growth · quality · …) 은 preset.
3. 데이터 경로는 prebuild `finance.parquet` 우선, 없으면 per-file fallback, `filterLatestPerStock` 공용 유틸.
4. 7 관점 스크리닝 (Value · Growth · Quality · Momentum · Income · Recovery · Defensive) 과 fields→screen spec 으로 primitive 조합.
5. 기업 발굴 5 단계 — 매크로 맥락 → 관점 preset → 섹터·규모 보정 → 상위 N 심층 → 과거 서사.
6. Company-bound 5 축 (governance · workforce · capital · debt · network), 나머지는 market-level API.
7. 프리빌드로 17 초 전종목 스캔, `dataPrebuild.yml` 12h 주기 자동, `downloadAll("scan")` 로 클라이언트 수령.
8. `finance-lite.parquet` (18MB 30 계정) 은 pyodide 전용, `LITE_ACCOUNTS` SSOT.
9. EDGAR scan 11 축은 XBRL companyfacts 기반, DART 동일 인터페이스, governance·workforce 등 5 축은 SEC 구조 한계로 갭.
10. scanner 는 Company import 없음 (역의존 방지), scan → story 는 `scan/extended.py` wrapper 경유.
