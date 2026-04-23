# Industry

**주체**: industry 엔진 (`dartlab.industry(industry?, stage?)` · `c.industry()`).
**현재**: taxonomy.json 단일 원천 · 2,665사 / 34 산업 분류 · 노드·엣지 JSON (~3,000건) · review `chainPosition` 블록 활성.
**방향**: AI 보조 신규 산업 초안 · 밸류체인 엣지 확장 · 산업별 KPI 자동 연동.

산업 매퍼엔진 — 데이터 주도 산업지도.

전 상장사 2,665사를 34개 산업으로 분류하고, 각 산업 내 공정·역할·공급망 관계를 노드-엣지로 데이터베이스화한다. 분류체계 자체가 데이터(taxonomy.json)이며, 코드는 파이프라인만 고정한다. AI + 사람이 계속 학습하며 유지보수한다.

## 호출 계약

```python
import dartlab

# 기본 조회
dartlab.industry()                              # 가이드 (34개 산업 목록)
dartlab.industry("semiconductor")               # 반도체 산업지도 DataFrame
dartlab.industry("semiconductor", "equipment")  # 장비 공정만

# 집계/추이
dartlab.industry("semiconductor", summary=True)           # 공정별 매출/이익 집계
dartlab.industry("semiconductor", summary=True, year="2023")  # 특정 연도
dartlab.industry("semiconductor", timeline=True)          # 연도별 공정 매출 추이

# 관계 조회
dartlab.industry.edges("semiconductor")                   # 반도체 공급-수요·계열 관계
dartlab.industry.edges(stockCode="005930")                # 삼성전자의 관계

# 분류체계 조회
dartlab.industry.map("semiconductor")                     # IndustryDef 객체 (taxonomy)

# 빌드
dartlab.industry.build()                                  # 4단계 파이프라인 전체
dartlab.industry.build(skipDocs=True)                     # docs 생략 (빠른 테스트)

# 오분류 보정
from dartlab.industry import addOverride
addOverride("semiconductor", "403870", "equipment", note="전공정 장비")
```

### Company-bound 인터페이스

```python
c = dartlab.Company("005930")
c.industry()                                    # 삼성전자의 산업 내 위치 (dict)
```

`c.industry()` 는 내부적으로 `calcChainPosition(company)` 를 호출하여 nodes.json 에서 해당 종목의 산업/공정/역할/peer 를 반환한다.

---

| 항목 | 내용 |
|------|------|
| 레이어 | L2 |
| 진입점 | `dartlab.industry()`, `c.industry()` |
| 소비 | core/(docs parquet), scan/(network, finance), gather/(listing) |
| 생산 | review(chainPosition 블록), ai(산업 분석), 블로그(산업지도 포스트), landing/map |
| 상태 | stable — review 블록 `chainPosition` 활성 (`c.review(only=['chainPosition'])`) |

## 핵심 원칙

1. **분류체계 = 데이터** (taxonomy.json). 코드에 직접 하드코딩하지 않는다 — taxonomy.json 이 SSOT.
2. **노드·엣지 = JSON** (~3,000건). industry 엔진 안에서 자급자족
3. **파이프라인 = 코드** (4단계 빌드). 어떻게 추출/분류하는가만 고정
4. **AI 개입** = AI가 도구로 사용 + 오분류 보정 + 신규 산업 초안 생성

## 데이터 구조

```
src/dartlab/industry/
    taxonomy.json      ← 분류체계 (34개 산업 × stages × keywords)
    nodes.json         ← 전종목 위치 (~2,665건)
    edges.json         ← 공급-수요·계열 관계
    overrides.json     ← AI/사람 검수 확정
```

### taxonomy.json — 분류체계가 데이터다

```json
{
  "industries": {
    "semiconductor": {
      "name": "반도체",
      "ksicCodes": ["반도체 제조업"],
      "stages": {
        "design": {"name": "설계", "role": "제조", "stream": "upstream", "keywords": [...]},
        "fab": {"name": "전공정(FAB)", ...},
        "equipment": {"name": "장비", ...}
      }
    }
  }
}
```

- industries 키 = 산업 ID
- stages 키 = 공정 ID
- keywords = 빌드 파이프라인이 매칭에 사용
- **AI/사람이 JSON을 직접 편집하여 산업 추가, 키워드 갱신, 공정 재정의**
- 코드 수정 없이 분류체계를 진화시킨다

### nodes.json — 전종목 위치

```json
[
  {"stockCode": "005930", "corpName": "삼성전자", "industry": "semiconductor",
   "stage": "fab", "role": "제조", "stream": "midstream",
   "confidence": 0.9, "source": "docs", "primary": true}
]
```

- 하나의 회사가 여러 행 가능 (multi-mapping: 삼성전자 = 반도체 + 디스플레이)
- `primary=true` 하나만 (매출 집계 중복 방지)
- source: kindlist / product / docs / ai / manual

### edges.json — 공급-수요·계열 관계

```json
[
  {"fromCode": "240810", "fromName": "원익IPS", "toCode": "005930", "toName": "삼성전자",
   "type": "supplier", "industry": "semiconductor",
   "confidence": 0.6, "source": "docs", "evidence": "원재료 섹션에서 '삼성전자' 언급"}
]
```

- type: supplier / customer / affiliate / investor
- source: network / docs / ai / manual

### overrides.json — AI/사람 검수

```json
{
  "semiconductor": [
    {"stockCode": "403870", "corpName": "HPSP", "stage": "equipment", "note": "전공정 장비"}
  ]
}
```

- AI가 `addOverride()`로 즉시 수정
- 사람이 JSON 직접 편집
- 다음 빌드 시 4단계에서 자동 반영

## 4단계 빌드 파이프라인

```python
from dartlab.industry.build.pipeline import buildIndustryMap
buildIndustryMap()                  # 전체 빌드
buildIndustryMap(skipDocs=True)     # docs 생략 (빠른 테스트)
```

### 1단계: KindList 업종 → 대분류 (`stage1_ksic.py`)

KindList의 업종(KSIC) 컬럼을 taxonomy의 ksicCodes와 매칭.
"반도체 제조업" → semiconductor. confidence=0.7.

### 2단계: 주요제품 → 중분류 (`stage2_product.py`)

KindList의 주요제품 텍스트를 쉼표 토큰화 → taxonomy keywords 매칭.
"DRAM,NAND" → semiconductor.fab. confidence 0.6~0.9.

### 3단계: docs → 소분류 (`stage3_docs.py`)

docs parquet의 businessOverview/productService/rawMaterial 텍스트 스캔.
taxonomy keywords 매칭으로 stage 보강/신뢰도 갱신.
Company 객체 미로드 — Polars lazy frame 직접 스캔 (메모리 안전).

### 4단계: override 적용 (`stage4_review.py`)

overrides.json의 확정 매핑을 반영. confidence=1.0, source="manual".

### 엣지 빌드 (`edges.py`)

| 소스 | 추출 방법 | edge type |
|------|----------|-----------|
| scan/network investedCompany | 투자관계 (지분율, 목적) | affiliate / investor |
| docs rawMaterial 섹션 | 텍스트에서 상장사명 매칭 | supplier |
| docs 매출처 섹션 | 텍스트에서 상장사명 매칭 | customer |

## AI 개입 체계

### AI가 산업지도를 사용

```python
dartlab.ask("삼성전자는 반도체 밸류체인 어디에 있어?")
# → AI가 c.industry() 호출 → nodes.json 조회 → 분석
```

### AI가 산업지도를 보정

```python
# AI가 분석 중 오분류 발견 시:
from dartlab.industry import addOverride
addOverride("semiconductor", "403870", "equipment", note="전공정 장비")
# → overrides.json 즉시 갱신 → 다음 빌드에 반영
```

- industry(L2)에서 AI(L4)를 import하지 않음 (레이어 규칙)
- AI(L4)가 코드 실행 루프에서 industry 함수를 호출

### AI가 새 산업을 제안

1. AI가 KindList 필터 + docs 스캔으로 초안 생성
2. taxonomy.json에는 **사람만** 추가 (AI 직접 수정 금지)
3. overrides.json은 AI가 직접 수정 가능

### AI context 주입 (Phase 2)

ContextBuilder에 industry selector 추가:
- ACT1(사업이해) intent에서 chainPosition 자동 주입
- 같은 공정 peer 목록 포함

## 지속 학습 매커니즘

### 선순환 루프

```
빌드(자동) → 데이터에서 노드·엣지 추출
    ↓
AI(L4) → 분석 중 오분류 발견 → addOverride()
    ↓
overrides.json → 다음 빌드에 반영
    ↓
블로그 07-industry-map/ → 산업 인사이트 기록
    ↓
taxonomy.json → 사람이 키워드 추가, 공정 재정의
    ↓
빌드(자동) → 정밀도 향상
```

### 학습 트리거

| 트리거 | 동작 |
|--------|------|
| 분기보고서 공시 | docs parquet 갱신 → 재빌드 → 변경 감지 |
| 신규 상장 | KindList 변경 → 자동 분류 → AI 검수 |
| 회사 분할/합병 | AI가 override 이전 → 사람 확인 |
| AI audit | 오분류 발견 → addOverride() → 재빌드 |
| 사람 편집 | taxonomy.json/overrides.json 수정 → 재빌드 |

### 정밀도 향상 경로

```
1단계 KSIC만:       confidence 0.7, stage 없음
2단계 +주요제품:    confidence 0.6~0.9, stage 일부
3단계 +docs:        confidence 0.5~1.0, stage 대부분
4단계 +override:    confidence 1.0, 사람 확정
```

시간이 지날수록 override가 쌓이고, taxonomy 키워드가 보강되어 자동 분류 정밀도가 올라간다.

### 블로그 연동

`blog/07-industry-map/` 카테고리에 산업지도 포스트를 발간한다.
frontmatter에 구조화된 산업 데이터를 포함하여 코드가 읽을 수 있다.

## 34개 산업 (전 상장사 커버)

| 산업 | 공정수 | 예시 |
|------|--------|------|
| semiconductor | 6 | 설계/FAB/패키징/테스트/장비/소재 |
| electronics | 4 | 부품/모듈/디스플레이/완제품 |
| telecom | 3 | 인프라/단말/서비스 |
| software | 4 | 플랫폼/솔루션/게임/AI |
| pharma | 5 | 연구/원료의약/완제의약/의료기기/유통 |
| auto | 5 | 완성차/파워트레인/차체/샤시/전장 |
| battery | 6 | 양극재/음극재/분리막/전해질/셀/팩 |
| chemical | 3 | 기초화학/정밀화학/고분자 |
| steel | 3 | 원료/철강제품/가공 |
| machinery | 3 | 범용/전용/정밀기기 |
| construction | 3 | 종합건설/건자재/엔지니어링 |
| finance | 4 | 은행/증권/보험/핀테크 |
| ... | | 총 34개 |

## calcs.py — review 블록용 calc 함수

| calc 함수 | review 블록 | 반환 | 설명 |
|---|---|---|---|
| `calcChainPosition(company)` | chainPosition | dict | 이 회사의 산업 내 위치 + peers |
| `calcSectorMetrics(company)` | sectorMetrics | dict | 업종 내 OPM/CAGR/ROE 분포 + 백분위 |
| `calcSectorCycle(company)` | sectorCycle | dict | 업종 OPM 추이로 확장/수축/안정 판정 |
| `calcSectorDynamics(company)` | sectorDynamics | dict | macro 사이클 × 경기민감도 → 순풍/역풍 |

## sector.py — 섹터 분류/파라미터 공개 API

| 함수/클래스 | 설명 |
|---|---|
| `classify(companyName, kindIndustry, mainProducts)` | WICS 섹터 분류 → SectorInfo |
| `getParams(sectorInfo)` | 섹터별 밸류에이션 파라미터 → SectorParams |
| `getThresholds(sector, industryGroup)` | 섹터별 신용등급 기준표 → dict |
| `getMarketParams(currency)` | 통화별 시장 파라미터 → MarketParams (riskFreeRate, ERP 등) |
| `Sector` | WICS 대분류 Enum (에너지/소재/산업재/금융/IT 등 12개) |
| `IndustryGroup` | WICS 중분류 Enum (반도체와반도체장비/은행/자동차와부품 등 35개) |
| `SectorInfo` | 분류 결과 dataclass (sector, industryGroup, confidence, source) |
| `SectorParams` | 밸류에이션 파라미터 dataclass (discountRate, perMultiple, beta 등) |
| `MarketParams` | 국가별 시장 파라미터 dataclass (riskFreeRate, ERP, CRP, taxRate, gdpGrowth) |
| `MARKET_KR` / `MARKET_US` | 한국/미국 MarketParams 인스턴스 |
| `MARKET_PARAMS` | `{"KRW": MARKET_KR, "USD": MARKET_US}` dict |

## 관련 코드

| 경로 | 역할 |
|------|------|
| `src/dartlab/industry/__init__.py` | Industry 진입점 + addOverride |
| `src/dartlab/industry/taxonomy.json` | 분류체계 데이터 |
| `src/dartlab/industry/nodes.json` | 전종목 위치 |
| `src/dartlab/industry/edges.json` | 공급-수요·계열 관계 |
| `src/dartlab/industry/overrides.json` | AI/사람 검수 |
| `src/dartlab/industry/types.py` | IndustryNode, IndustryEdge 타입 |
| `src/dartlab/industry/taxonomy.py` | taxonomy 로드/조회/캐시 |
| `src/dartlab/industry/build/pipeline.py` | 4단계 오케스트레이터 |
| `src/dartlab/industry/build/stage1_ksic.py` | KindList → 대분류 |
| `src/dartlab/industry/build/stage2_product.py` | 주요제품 → 중분류 |
| `src/dartlab/industry/build/stage3_docs.py` | docs → 소분류 |
| `src/dartlab/industry/build/stage4_review.py` | override 적용 |
| `src/dartlab/industry/build/edges.py` | 엣지 빌더 (network + docs) |
| `src/dartlab/industry/calcs.py` | review 블록용 calc |
| `src/dartlab/industry/build/enrichCompany.py` | 회사별 egograph + 5Y 재무 + AI + 블로그 + 공급망 enrich |
| `src/dartlab/industry/build/hop2.py` | 2홉 공급망 사전 계산 |
| `src/dartlab/industry/build/delta.py` | YoY 재무 변화 계산 |
| `scripts/build/buildIndustryMap.py` | **산업지도 JSON 전체 빌드** (아래 상세) |
| `.github/workflows/mapBuild.yml` | **자동화 — Data Prebuild 후 맵 재빌드** |

## 산업지도 빌드 파이프라인 (`buildIndustryMap.py`)

industry 엔진의 노드·엣지·분류 데이터를 **landing/static/map/** 의 정적 JSON으로 변환하는 빌드 스크립트. GitHub Pages 배포 시 포함.

### 산출물

| 파일 | 내용 | 크기 |
|------|------|------|
| `ecosystem.json` | 전 상장사 노드 + 공급망 엣지 + 산업 메타 | ~4MB |
| `atlas.json` | 산업 노드 + 산업간 공급 플로우 Top 50 | ~50KB |
| `industries/{id}.json` | 산업별 공정 노드 + 내부 엣지 | 산업별 |
| `companies/{code}.json` | 회사별 egograph + enriched 데이터 | 상장사별 |
| `industryStats.json` | 산업별 ROE/OPM/CAGR 분포(p10~p90) + Top 기업 | ~200KB |
| `movers.json` | 변화 감지 6카테고리 (수익성/매출/부채) | ~30KB |
| `search-index.json` | 전 종목 검색 인덱스 | ~300KB |
| `insights.json` | 인사이트 랭킹 | ~10KB |
| `meta.json` | 빌드 ID + 데이터 기준일 | ~1KB |
| `feed/movers.xml` | RSS 피드 | ~20KB |
| `feed/industry/*.xml` | 산업별 RSS 피드 | 34파일 |
| `feed/calendar.ics` | iCal 피드 | ~5KB |

### 노드 필드 (ecosystem.json)

```
기본:      id, label, industry, industryName, stage, stageName, role, stream, revenue, size, color
scan 4축:  roe, opMargin, debtRatio, revCagr
scan 7축:  profGrade, debtGrade, growthGrade, govGrade, cfPattern, auditRisk, qualGrade, liqGrade, capClass
순위:      industryRank, industryPeerCount, marketShare
YoY:       roeDelta, opMarginDelta, debtRatioDelta, revenueYoyPct, deltaYear
insider:   holderPct, holderChange, stability
기타:      confidence, source, empCount
```

### enrich 데이터 (companies/{code}.json)

| 필드 | 소스 | 내용 |
|------|------|------|
| `financials5y` | scan/finance.parquet | 5년 매출/영업이익/순이익/총자산 |
| `aiInsight` | KnowledgeDB | AI 분석 narrative + strengths/weaknesses |
| `blogPosts` | blog/05-company-reports/ | 블로그 포스트 메타 (verdict/direction/archetype) |
| `supplyInsights` | edges 기반 계산 | HHI + 의존도 + 공급사/고객 수 |
| `suppliers/customers` | edges Top 10 | 거래처 목록 (금액/비율) |
| `peers` | nodes 동종사 | 같은 업종 Top 5 |
| `hop2` | computeHop2() | 2홉 공급망 (허브 1.5홉 제한) |
| `creditMetrics` | credit 엔진 | 신용등급 + 5축 점수 |

### 실행

```bash
# 전 종목 빌드 (기본)
uv run python -X utf8 scripts/build/buildIndustryMap.py

# 개발용 빠른 빌드 (상위 500사만 enrich)
uv run python -X utf8 scripts/build/buildIndustryMap.py --companies 500
```

## 자동화 파이프라인

### 전체 흐름

```
Data Sync (매일 03:00 KST)
  DART 공시 수집 → finance/report/docs parquet
    ↓
Data Prebuild (자동 트리거)
  scan 프리빌드 → HuggingFace 업로드
    ↓
Map Build (자동 트리거)  ← .github/workflows/mapBuild.yml
  buildIndustryMap.py --companies 0
  → landing/static/map/ 전체 재생성
  → 변경 있으면 자동 커밋 [skip ci]
    ↓
GitHub Pages 배포 (자동)
  landing/ 정적 사이트 빌드 → /map 페이지 갱신
```

### 워크플로우 설정

| 파일 | 트리거 | 역할 |
|------|--------|------|
| `dataSync.yml` | cron 매일 | DART 공시 수집 |
| `dataPrebuild.yml` | dataSync 완료 후 | scan 프리빌드 → HF |
| **`mapBuild.yml`** | dataPrebuild 완료 후 | **산업지도 JSON 전체 빌드** |
| `docs.yml` | push 시 | GitHub Pages 배포 |

### 사용자 데이터 갱신

라이브러리 사용자(`pip install dartlab`)는 별도 조치 없이 최신 데이터 사용:
- **TTL = 12시간**: 12시간마다 HF와 ETag 비교 → 변경 시 자동 다운로드
- **강제 갱신**: `refresh="force_check"` 옵션
- 웹 사용자(landing /map): GitHub Pages 배포와 동시에 최신 JSON 반영
