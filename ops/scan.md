# Scan

전 종목 횡단분석. `scan()` 단일 진입점으로 시장 전체를 한 번에. DART + EDGAR 양쪽 지원.

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
| valuation | PER/PBR/PSR + 시가총액 + 등급 (네이버 실시간) |
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

종목별 parquet 2700+개 순차 스캔 → 수분. 프리빌드 합산 parquet → **17초**.

```
data/dart/scan/
├── changes.parquet     # docs 변화 전종목 5Y
├── finance.parquet     # finance 전종목 5Y
└── report/             # apiType별 12개 parquet
```

- 배포자: `dartlab collect --scan` → HF push
- 사용자: `downloadAll("scan")` (271MB) → 즉시 횡단 분석
- scan 파일 없으면 HF 자동 다운로드 시도, 실패 시 종목별 순회 fallback
- **첫 호출 안내**: 로컬 프리빌드가 없으면 `scan:prebuild_missing` (271MB 안내) → 다운로드 → `scan:prebuild_ready`. 실패 시 `scan:prebuild_failed`. guide.emit `_ALWAYS_SHOW` 카테고리라 verbose=False여도 출력 (자세히는 src/dartlab/guide/README.md)

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
