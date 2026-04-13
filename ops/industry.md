# Industry

산업 매퍼엔진 — 데이터 주도 산업지도.

전 상장사 2,665사를 34개 산업으로 분류하고, 각 산업 내 공정·역할·공급망 관계를 노드-엣지로 데이터베이스화한다. 분류체계 자체가 데이터(taxonomy.json)이며, 코드는 파이프라인만 고정한다. AI + 사람이 계속 학습하며 유지보수한다.

## 호출 계약

```python
import dartlab

dartlab.industry()                              # 가이드 (34개 산업 목록)
dartlab.industry("semiconductor")               # 반도체 산업지도 DataFrame
dartlab.industry("semiconductor", "equipment")  # 장비 공정만

c = dartlab.Company("005930")
c.industry()                                    # 삼성전자의 산업 내 위치
```

---

| 항목 | 내용 |
|------|------|
| 레이어 | L2 |
| 진입점 | `dartlab.industry()`, `c.industry()` |
| 소비 | core/(docs parquet), scan/(network, finance), gather/(listing) |
| 생산 | review(산업 블록), ai(산업 분석), 블로그(산업지도 포스트) |
| 상태 | beta |

## 핵심 원칙

1. **분류체계 = 데이터** (taxonomy.json). 코드 하드코딩 절대 금지
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
