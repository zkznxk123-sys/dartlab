---
id: engines.company.finance
title: finance — 회사 재무 엔진 (XBRL + 주석 sub-domain)
kind: curated
scope: builtin
status: observed
category: engines
purpose: company.finance 는 한국 DART 사업보고서·재무제표·주석에서 재무 시계열 + 6 sub-domain 운영 데이터 (요약재무·관계기업·부문·주주·원재료·비용성격별) 를 추출하는 sub-engine 이다. XBRL 표준 계정 매핑 (engines.mappers) 위에서 ratios/extract/pivot 으로 분기별·연도별·누적 시계열 조립. 트리거 — '재무 시계열', 'ROE/ROA', 'fsSummary', 'majorHolder', 'segment', 'affiliate'.
whenToUse:
  - 회사 재무 시계열 빌드
  - 재무비율 (ROE · ROA · 부채비율 · FCF)
  - 최대주주 · 5% 이상 주주 · 의결권 분석
  - 사업부문 · 지역 · 제품별 매출 분해
  - 관계기업 · 공동기업 투자 분석
  - 비용의 성격별 분류 시계열
  - 원재료 · 생산설비 · 시설투자 추출
inputs:
  - 종목코드 (예 — 005930)
  - period (q/y/cum), fsDivPref (CFS/OFS)
  - 분석 대상 사업연도 범위
outputs:
  - 시계열 dict (snakeId × period)
  - RatioResult (ROE / ROA / margins / debt)
  - MajorHolderResult · HolderOverview
  - SegmentsResult · AffiliatesResult
  - CostByNatureResult · RawMaterialResult
  - AnalysisResult (fsSummary 매칭 결과)
capabilityRefs: []
toolRefs:
  - RunPython
knowledgeRefs:
  - engines.company
  - engines.mappers
  - engines.data.foundation
sourceRefs:
  - dartlab://skills/engines.company.finance
requiredEvidence:
  - stockCode
  - fsDivPref
  - period
  - snakeId
expectedOutputs:
  - 시계열 행/열 수치 (원본 단위 명시)
  - 비율 (% / 배 / 절대값)
  - 매칭 신뢰도 (fsSummary allRate)
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: limited
failureModes:
  - fsDivPref 미지정 — CFS 우선, 없으면 OFS fallback. 양쪽 다 없으면 빈 dict.
  - 단위 혼재 (USD/천USD/백만원 자회사별 테이블)
  - 2015년 이전 보고서 — 테이블 구조 차이로 지분율 오류 가능
  - 분기/반기 보고서에 비용성격 미공시 (연간만 공시 다수)
  - 금융업/리츠/지주회사 — 비용성격 / 생산설비 미공시
forbidden:
  - snakeId 추측 (engines.mappers 의 normalizeColumn 경유 의무)
  - allRate 낮을 때 매칭 결과 그대로 인용
examples:
  - Company('005930').ratios → ROE 8.29% (CFS, 2024)
  - majorHolder('005930') → 최대주주 + 시계열
  - segments('005930') → 사업부문 + 제품 + 지역 분해
  - fsSummary('005930') → 158 기업 구간 내 97.7% 매칭
procedure:
  - dartlab.Company(code) 컨텍스트 — RSS 회수 의무.
  - c.timeseries / c.annual / c.cumulative — 분기 · 연도 · 누적 시계열.
  - c.ratios — 재무비율 (CFS 기본, OFS getRatios("OFS")).
  - 6 sub-domain 진입: from dartlab.finance.{affiliate, segment, summary, majorHolder, costByNature, rawMaterial}.
  - 매핑 SSOT — engines.mappers ↔ reference/data/accountMappings.json (34,171 entries).
linkedSkills:
  - engines.company
  - engines.mappers
  - engines.company.sections
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-12'
---

## 엔진 역할

`company.finance` 는 사용자 capability 가 아니라 *Company 엔진 내부 sub-module* 이다. XBRL 표준 계정 매핑 + 주석 영역 6 sub-domain 파서를 묶어 단일 회사의 재무 시계열을 빌드한다. dartlab 공개 호출은 Company facade 경유.

본 sub-spec 은 운영 SSOT — 파일 구조 · 6 sub-domain 책임 · 검증 결과 · 매핑 사이클을 한 곳에서 관리.

## 공개 호출 방식

```python
import dartlab

with dartlab.Company("005930") as c:
    # 시계열 (분기 / 연도 / 누적)
    q = c.timeseries
    y = c.annual
    cum = c.cumulative

    # 재무비율
    r = c.ratios               # CFS 기본
    rOfs = c.getRatios("OFS")  # 별도

    # 커스텀 시계열
    sQ_OFS = c.getTimeseries(period="q", fsDivPref="OFS")

# 6 sub-domain — 주석 영역 파서
from dartlab.finance.summary import fsSummary
from dartlab.finance.majorHolder import majorHolder, holderOverview
from dartlab.finance.segment import segments
from dartlab.finance.affiliate import affiliates
from dartlab.finance.costByNature import costByNature
from dartlab.finance.rawMaterial import rawMaterial

result = fsSummary("005930")        # 요약재무 브릿지 매칭
mh = majorHolder("005930")          # 최대주주 + 시계열
seg = segments("005930")            # 사업부문 / 제품 / 지역
aff = affiliates("005930")          # 관계기업 / 공동기업
cbn = costByNature("005930", "y")   # 비용 성격별
raw = rawMaterial("005930")         # 원재료 / 생산설비 / 시설투자
```

## 호출 동작

- `Company.timeseries` / `annual` / `cumulative` — `buildTimeseries(stockCode, fsDivPref)` 위임. CFS 우선, 없으면 OFS fallback. snakeId × period 의 nested dict 반환.
- `Company.ratios` — `calcRatios(series, marketCap=None)` 위임. ROE · ROA · 마진 · 부채비율 · FCF 등.
- `Company.getTimeseries(period, fsDivPref)` — 4 조합 (q/y/cum × CFS/OFS) 명시 조회.
- `fsSummary(source, ifrsOnly=True)` — 4 단계 브릿지 매칭. 2 년 미만 → None.
- `majorHolder(stockCode)` — 사업보고서 "VII. 주주에 관한 사항" 파싱.
- `segments(stockCode)` / `affiliates(stockCode)` — 주석 표 추출 (일반 + 횡전개).
- `costByNature(stockCode, period)` — 3 가지 테이블 유형 (inline / split / multiCol) 자동 감지.
- `rawMaterial(stockCode)` — 원재료 + 유형자산 변동 + 시설투자 3 영역 동시 추출.

미매핑 계정 발견 시 `engines.mappers` 학습 후보 데이터로 흐른다 (사람 검토 후 `AccountMapper.release()`).

## 대표 반환 형태

```text
Company.ratios
→ RatioResult
   roe : float          # 자기자본이익률 (%)
   roa : float          # 총자산이익률 (%)
   operatingMargin : float
   debtRatio : float
   currentRatio : float
   fcf : float          # Free Cash Flow

fsSummary(source)
→ AnalysisResult | None
   corpName : str | None
   nYears : int
   allRate : float | None        # 전체 매칭률
   contRate : float | None       # 연속 매칭률
   segments : list[Segment]      # 구간 통계
   breakpoints : list[BridgeResult]
   yearAccounts : dict[str, YearAccounts]

majorHolder(stockCode)
→ MajorHolderResult | None
   majorHolder : str | None      # 최대주주명
   majorRatio : float | None
   totalRatio : float | None
   holders : list[Holder]
   timeSeries : pl.DataFrame
```

## 코어 finance 엔진

`src/dartlab/providers/dart/finance/` — 분기별 · 연도별 · 누적 시계열 + 재무비율.

| 파일 | 역할 |
|------|------|
| `__init__.py` | public API export |
| `mapper.py` | XBRL account_id + 한글명 → snakeId 매핑 (engines.mappers 위임) |
| `sceMapper.py` | 자본변동표 (SCE) 별도 매퍼 |
| `pivot.py` | parquet → 시계열 dict 피벗 + 동의어 병합 + 연도별/누적 집계 |
| `scanAccount.py` | 미매핑 계정 스캔 (학습 후속 데이터) |
| `spec.py` | 엔진 명세 (`summary.mappedAccounts` 등) |

데이터 SSOT — `reference/data/accountMappings.json` (`learnedSynonyms: 31,489` / `standardAccounts: 3,402` / `merged: 34,171`). 학습 사이클은 `engines.mappers` 참조.

### 시계열 API

| 함수 | 반환 | 설명 |
|------|------|------|
| `buildTimeseries(stockCode, fsDivPref="CFS")` | `(series, periods)` | 분기별 standalone |
| `buildAnnual(stockCode, fsDivPref="CFS")` | `(series, years)` | 연도별 |
| `buildCumulative(stockCode, fsDivPref="CFS")` | `(series, periods)` | 분기별 누적 |

### 값 추출

| 함수 | 설명 |
|------|------|
| `getTTM(series, sjDiv, snakeId)` | 최근 4 분기 합 (IS/CF) |
| `getLatest(series, sjDiv, snakeId)` | 최신 non-null 값 (BS) |
| `getAnnualValues(series, sjDiv, snakeId)` | 전체 시계열 리스트 |
| `getRevenueGrowth3Y(series)` | 매출 3 년 CAGR (%) |

### 비율 계산

`calcRatios(series, marketCap=None)` → `RatioResult` (ROE · ROA · 마진 · 부채 · FCF 등).

### Company 통합

| 접근자 | 설명 |
|--------|------|
| `c.timeseries` | 분기별 standalone (CFS) |
| `c.annual` | 연도별 (CFS) |
| `c.cumulative` | 분기별 누적 (CFS) |
| `c.ratios` | 재무비율 (CFS) |
| `c.getTimeseries(period, fsDivPref)` | 커스텀 조회 (q/y/cum × CFS/OFS) |
| `c.getRatios(fsDivPref)` | 커스텀 비율 (CFS/OFS) |

### fsDivPref 파라미터

- `"CFS"` — 연결재무제표 (기본값). 없으면 OFS fallback.
- `"OFS"` — 별도재무제표. 없으면 CFS fallback.

### 검증 결과 (삼성전자 005930, 2024)

| 지표 | CFS | OFS |
|------|-----|-----|
| Revenue | 300.9T | 209.1T |
| ROE | 8.29% | 5.19% |
| Debt Ratio | 27.40% | 20.67% |

## 6 sub-domain (주석 영역 파서)

`src/dartlab/providers/dart/docs/finance/{name}/` + `disclosure/rawMaterial/` 의 6 영역.

### 1. summary — 요약재무 브릿지 매칭

`dartlab.finance.summary.fsSummary(source, ifrsOnly=True)` → `AnalysisResult | None`.

DART 공시 요약재무정보에서 숫자 브릿지 매칭으로 계정명을 연도간 매핑하여 시계열 생성.

| 파일 | 설명 |
|------|------|
| `constants.py` | 매칭 임계값, 핵심 계정 목록 |
| `types.py` | `AnalysisResult` · `Segment` · `BridgeResult` · `YearAccounts` |
| `contentExtractor.py` | 요약재무 영역 추출 (연결 우선) |
| `bridgeMatcher.py` | 4 단계 숫자 브릿지 매칭 알고리즘 |
| `segmentation.py` | 전환점 탐지, 구간 분리 |
| `pipeline.py` | `fsSummary()` · `loadYearData()` 오케스트레이터 |

**매칭 알고리즘 (4 단계)**:
1. **정확 매칭** — N년 전기 금액 == N-1년 당기 금액 (차이 < 0.5)
2. **재작성 보정** — 이름 유사도 0.8+ 금액 차이 5% 이내
3. **명칭변경 보정** — 이름 유사도 0.6+ 금액 차이 5% 이내
4. **특수항목** — EPS · 회사수 등 이름 강제 매칭

**검증** — 158 개 기업 구간 내 97.7%, 오매칭 0.07%. 임계 `BREAKPOINT_THRESHOLD = 0.85`. 핵심 계정 10 개.

**AnalysisResult 필드** — corpName / nYears / nPairs / nBreakpoints / nSegments / allRate / contRate / segments / breakpoints / pairResults / yearAccounts.

**BridgeResult** — `pairs: {당해년도 계정명: 전년도 계정명}` · `yearGap` (보통 1, 갭 있으면 2+).

**입력 데이터** — polars DataFrame 또는 parquet. 필수: `year` / `report_type` / `rcept_date` / `section_title` / `section_content`. 선택: `corp_name`.

### 2. majorHolder — 주주 현황

`dartlab.finance.majorHolder.majorHolder(stockCode)` → `MajorHolderResult | None`.
`dartlab.finance.majorHolder.holderOverview(stockCode)` → `HolderOverview | None`.

**MajorHolderResult** — corpName / majorHolder (최대주주명) / majorRatio / totalRatio (특수관계인 포함) / holders / timeSeries.

**HolderOverview** — bigHolders (5% 이상) · minority (소액주주) · voting (의결권).

**파싱 성공률 (267 종목)** — 최대주주 100% (227/0/40) · 5% 이상 주주 100% (217/0/50) · 소액주주 100% (214/0/53) · 의결권 100% (223/0/44).

**파싱 전략**:
- majorHolder — "VII. 주주에 관한 사항" → "성 명 | 관 계" 헤더 + 8-cell 데이터행, "본인"/"최대주주" 관계 식별
- 5% 이상 주주 — `| 5% 이상 주주 | 주주명 | 소유주식수 | 지분율 | 비고 |` 구조
- 소액주주 — 단일행 `| 주주수 | 전체주주수 | 비율 | 소액주식수 | 총발행 | 비율 |`
- 의결권 — A(발행총수) ~ F(행사가능) 보통주/우선주 분리

**주의** — 2015 년 이전 보고서 테이블 구조 차이로 지분율 오류 가능. 스팩/비상장사 5% 이상 주주/소액주주 부재.

### 3. segment — 사업부문 보고

`dartlab.finance.segment.segments(stockCode)` → `SegmentsResult` (사업부문 · 제품 · 지역 테이블).

| 파일 | 설명 |
|------|------|
| `types.py` | `SegmentsResult` · `SegmentTable` |
| `extractor.py` | `core.notesExtractor` re-export |
| `parser.py` | 부문 테이블 파싱 (일반 + 횡전개) |
| `pipeline.py` | `segments()` 오케스트레이터 |

### 4. affiliate — 관계기업 / 공동기업

`dartlab.finance.affiliate.affiliates(stockCode)` → `AffiliatesResult` (지분 현황 + 변동).

| 파일 | 설명 |
|------|------|
| `types.py` | `AffiliatesResult` · `AffiliateProfile` · `AffiliateMovement` |
| `extractor.py` | 마크다운 테이블 행 추출 (`parseTableRows`) |
| `parser.py` | 프로필 / 변동 파싱 (일반 + 횡전개) |
| `pipeline.py` | `affiliates()` 오케스트레이터 |

### 5. costByNature — 비용의 성격별 분류

`dartlab.finance.costByNature.costByNature(stockCode, period)` → `CostByNatureResult`.

**파일 구성** — `types.py` (`CostByNatureResult`) · `parser.py` (inline/split/multiCol 3 방식) · `pipeline.py`.

**성능** — 171 / 171 (100%) 파싱 성공 · 시계열 173 종목 · 교차검증 일치율 87.8% · null 17.5%.

**파서 구조**:
- 3 가지 테이블 유형 자동 감지 (inline / split / multiCol)
- 30 개 정규화 매핑 (487 원본 → 표준)
- 22 가지 합계행 패턴 자동 제거

**period** — `"y"` 사업보고서 (연간) · `"q"` Q1/반기/Q3/사업보고서 (분기) · `"h"` 반기.

**ratios** — 각 비용 항목의 양수 합계 대비 비율 (%) DataFrame (year · account · amount · ratio).

**제한** — 금융업/리츠/지주회사 58 / 267 미공시. 교차검증 불일치 12.2% 는 소급 재작성 (파서 오류 아님).

### 6. rawMaterial — 원재료 · 생산설비 · 시설투자

`dartlab.finance.rawMaterial.rawMaterial(stockCode)` → `RawMaterialResult | None`.

**RawMaterialResult** — corpName / year / materials / equipment / capexItems.

- **RawMaterial** — segment · item · usage · amount · ratio · supplier
- **Equipment** — land · buildings · structures · machinery · construction · vehicles · fixtures · rou · undelivered · other · total · depreciation · capex
- **CapexItem** — segment · amount

**파싱 성공률 (267 종목)** — 원재료 93.0% · 생산설비 33.8% · 시설투자 16.2%. 125 종목 None (해당사항 없음 또는 매입 테이블 부재).

**품질 검증** — ratio 이상 (>100%) 2 / DL이앤씨 1, 그 외 0 건 (amt-None / 숫자 item / total 음수 / 1조 초과 / 런타임 에러).

**검증 완료 종목 스팟체크** — 삼성전자 (14 건 매입 · 2,059,452 설비) · 현대차 (17 건 · 44,533,941) · SK하이닉스 (5 건 · 60,157,474) · LG화학 (5 건 · 54,570,446) · LG · SK · F&F.

**파싱 전략 (원재료 12 단계)**:
1. 헤더 직접 감지 — `(매입액|투입액)` + `(품목|원재료|부문)` 조합
2. `_findHeaderIndices()` 동적 매핑
3. shifted 행 감지 (segment 생략 시 왼쪽 밀림)
4. 합쳐진 "매입액 (비율)" 셀 분리 — `1,483,067 (43.8%)` 패턴
5. 연도별 헤더 (`제N기`, `20XX년`) 지원
6. 분할 헤더 (row1 + row2 병합)
7. 비율 > 100 shifted 감지
8. 연도 컬럼 ratio 제외
9. 생산 테이블 필터 (생산능력/수량 키워드)
10. 숫자 item 필터 (shift 데이터 판단)
11. 각주 참조 필터 (`(주N)`)
12. amount 없는 헤더 진입 차단

**제한** — DL이앤씨 헤더 shifted 2 건 · 단위 혼재 (USD/천USD/백만원) 미지원 · 생산설비 33.8% (테이블 형식 다양).

## 의존 (sub-domain 공통)

- `dartlab.frame.dataLoader` — `loadData` · `extractCorpName` · `PERIOD_KINDS`
- `dartlab.providers.notesExtractor` — `extractNotesContent` · `findNumberedSection`
- `dartlab.providers.reportSelector` — 보고서 선택
- `dartlab.providers.tableParser` — 마크다운 테이블 파싱, 금액/단위 처리
- `engines.mappers` — 계정명 → snakeId 정규화

## evidence 기준

- finance 시계열 인용 시 `stockCode` · `fsDivPref` · `period` · `snakeId` · `source` (DART).
- 6 sub-domain 인용 시 `parsing_success_rate` 명시 (예 — 원재료 93.0%, 생산설비 33.8%).
- 미매핑 계정 발견 시 `engines.mappers` 후속 학습 후보로 로그.

## 기본 검증

```python
import dartlab
with dartlab.Company("005930") as c:
    print(c.ratios.roe)             # 8.29 (CFS)
    print(c.getRatios("OFS").roe)   # 5.19 (OFS)

from dartlab.finance.summary import fsSummary
result = fsSummary("data/docsData/005930.parquet")
print(f"{result.corpName}: {result.allRate:.1%}")  # 매칭률
```

## 변경 이력

- 2026-03-06 — 6 sub-domain 패키지 초기 구축 (affiliate / segment / summary / majorHolder / costByNature / rawMaterial)
- 2026-03-06 — `stockCode` 시그니처 전환, `extractor` 중복 제거 → `core` re-export
- 2026-03-07 — rawMaterial 실무 투입
- 2026-03-09 — XBRL 계정 표준화 + Company `docs/finance` 통합
- 2026-05-12 — STATUS.md 7 곳 → 본 sub-spec 통합 (Skill OS 운영 SSOT 승격)
