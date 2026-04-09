# Review

**기업이야기꾼의 대본.** 5 분석 엔진이 만든 재료를 6막 서사로 조립.

## 사상 — 기업이야기꾼

> 1. **5 엔진** (analysis/scan/macro/credit/quant) 이 데이터를 미리 계산해서 **재료** (calc dict) 를 만든다
> 2. **review** 가 재료를 6막 서사로 조립해 **대본** (보고서) 을 만든다
> 3. **AI/사람** 이 대본을 가지고 **언어적 분석·해석**을 한다
>
> review 는 해석하지 않는다. **스토리가 될 수 있는 데이터를 배치**한다.
> 해석은 AI (`c.reviewer()`) 또는 사람의 몫이다.
> 세상에 대해서도 이야기 할 수 있고, 세상이 이래서 기업이 이렇게 간다는 관점도 다룬다.

## 3단계 템플릿 체계

| 레벨 | 이름 | 결정하는 것 | 예시 |
|---|---|---|---|
| **1. 관점 (perspective)** | PERSPECTIVE_TEMPLATES | **섹션 순서** | 바텀업/탑다운/사이클/가치/성장/위기 |
| **2. 기업유형 (template)** | STORY_TEMPLATES | **강조 블록** (★) | 사이클/프랜차이즈/턴어라운드/성장/자본집약/지주/현금부자 |
| **3. 프리셋 (preset)** | PRESETS | **섹션 부분집합** | 경영진/감사/신용/성장/밸류에이션 |

perspective × template × preset 은 **독립 차원**. 동시 사용 가능.

## 호출 계약

```python
import dartlab
c = dartlab.Company("005930")

# 기본 (바텀업 6막)
c.review()
c.review("수익성")                    # 단일 섹션

# 기업유형 템플릿 (강조 블록 ★)
c.review(template="사이클")

# 관점별 순서 (섹션 재배치)
c.review(perspective="topDown")       # 매크로→시장→재무 순서
c.review(perspective="가치")          # 한글도 가능
c.review(perspective="crisis", template="턴어라운드")  # 동시 사용

# AI 종합의견
c.reviewer(guide="...")
```

## 노트북

[![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/08_review.py)
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/08_review.ipynb)

---

| 항목 | 내용 |
|------|------|
| 레이어 | L2 |
| 사상 | **기업이야기꾼의 대본** — 데이터 배치, 해석은 AI/사람 |
| 진입점 | `c.review()`, `c.review(perspective=...)`, `c.reviewer()` |
| 소비 | **analysis + credit + scan + quant + macro** 5엔진 (블록식 조합) |
| 생산 | ai(reviewer), 사용자(터미널/HTML/마크다운/JSON), 블로그 보고서 |
| 출력 | rich, html, markdown, json |
| 템플릿 | 3단계: 관점(순서) × 기업유형(강조) × 프리셋(부분집합) |

## 5엔진 조합 매핑

5 분석 엔진이 각각 독립 calc 모듈로 review 에 도구를 제공한다 (ops/architecture.md "모듈 제공 패턴" 참조).

| 막 | 섹션 | 소비 엔진 | 핵심 calc/블록 |
|---|------|---------|---------|
| 1막 사업이해 | 수익구조, 성장성 | **analysis** | calcSegmentComposition, calcRevenueGrowth, calcConcentration, ... |
| 2막 수익성 | 수익성, 비용구조 | **analysis** | calcMarginTrend, calcReturnTrend, calcCostBreakdown, ... |
| 3막 현금전환 | 현금흐름, 이익품질 | **analysis** | calcCashFlowOverview, calcCashQuality, ... |
| 4막 안정성 | 자금조달, 안정성 | **analysis** | calcLeverage, calcDistress, ... |
| 5막 자본배분 | 자산구조 ~ 신용평가 | **analysis** + **credit** | calcCapitalAllocation, calcCreditScore, calcCreditNarrative, ... |
| 6막-1 가치평가 | 가치평가, 매출전망 | **analysis**(forecast/valuation) | calcValuationSynthesis, calcRevenueDirection, ... |
| 6막-2 비교분석 | 비교분석 | **scan** | calcPeerPosition (교차 조합 관점), calcGovernanceSummary |
| 6막-3 시장분석 | 시장분석 | **quant** | calcTrendNarr, calcRiskNarr, calcSignalNarr, calcStrategyNarr, calcCrosscheckNarr, calcQuantConclusion |
| 6막-4 매크로 | 매크로 | **macro** | macroEnvironment, macroCycle, macroRates, macroLiquidity, macroSentiment, macroForecast, macroCorporate, macroTrade, macroFlags, valuationBand (10블록, `macro("종합")` 1회 호출) |

## 관점별 템플릿 (PERSPECTIVE_TEMPLATES)

기업 유형에 관계없이 **분석 순서**를 바꾼다. 같은 블록들이 다른 순서로 배치된다.

| 관점 | key | 순서 (앞에서부터) | 사용 사례 |
|---|---|---|---|
| **바텀업** | `bottomUp` | 수익구조 → 성장성 → 수익성 → ... → 시장분석 | 기본 (현재 6막) |
| **탑다운** | `topDown` | 시장분석 → 비교분석 → 매출전망 → 가치평가 → ... → 수익구조 | 거시환경 중심 |
| **사이클** | `cycle` | 시장분석 → 매출전망 → 수익구조 → 비용구조 → 현금흐름 → 안정성 | 반도체/화학/조선 |
| **가치** | `value` | 가치평가 → 안정성 → 자금조달 → 현금흐름 → 자본배분 → 수익성 | 가치투자자 |
| **성장** | `growth` | 수익구조 → 성장성 → 매출전망 → 투자효율 → 효율성 → 가치평가 | 성장투자자 |
| **위기** | `crisis` | 안정성 → 자금조달 → 현금흐름 → 이익품질 → 신용평가 → 종합평가 | 위험 진단 |

`perspective` (순서) × `template` (강조) 동시 사용:
- `c.review(perspective="crisis", template="턴어라운드")` → 위기 순서 + 턴어라운드 강조

## 단일 진입점

- **`c.review()` / `c.reviewer()`** 로 접근한다 (Company-bound)
- review 는 **analysis + credit + scan + quant + macro** 5 엔진 결과를 소비하여 보고서로 조립
- 각 엔진은 calc 함수 (독립 모듈) 로 서사·관점·근거를 만들어 review 에 도구로 제공
- **관점 (perspective)** 으로 순서, **기업유형 (template)** 으로 강조, **프리셋 (preset)** 으로 부분집합

## API

```python
c.review()              # 전체 보고서
c.review("수익구조")     # 단일 섹션
c.review(template="auto")  # 스토리 템플릿 자동 판별 + 강조 블록
c.reviewer()            # review + AI 종합의견
c.reviewer(guide="반도체 사이클 관점에서 평가해줘")
```

4개 출력 형식: `rich`(터미널), `html`, `markdown`, `json`

## 아키텍처

```
catalog.py          단일 진실의 원천 (블록 메타 + 섹션 메타 + 순서)
  ├── templates.py  섹션별 설정 (visibleKeys, helper, aiGuide) + 7개 스토리 템플릿
  ├── builders.py   analysis calc* → Block 리스트 변환 (narrate 호출)
  ├── narrate.py    Conditional Narrative Assembly — 임계값 중앙 관리 + 해석 문장
  ├── registry.py   buildBlocks() / buildReview() 조립 + emphasize 반영
  │     └── blockMap.py  BlockMap — 사용자 친화 블록 사전
  ├── publisher.py  블로그 보고서 발간 파이프라인
  ├── renderer.py   Rich 콘솔 렌더링
  ├── formats.py    HTML / Markdown / JSON 렌더링 + 6막 헤더 + 막 결론
  ├── blocks.py     Block 타입 (Heading, Table, Text, Flag, Metric) + emphasized 필드
  └── section.py    Section dataclass
```

## catalog.py — 단일 진실의 원천

- `_BLOCKS` 리스트 = 블록 정의 + 렌더링 순서
- `SECTIONS` 리스트 = 섹션 정의 + 렌더링 순서
- **key는 불변** — 한번 등록된 key는 영구 유지
- **label은 자유** — 사용자 표시명은 언제든 변경 가능
- **리스트 정의 순서 = 렌더링 순서** (list로 순서 보장)
- catalog label 하나 바꾸면 전체 렌더링이 따라간다
- builders.py에 하드코딩된 HeadingBlock title은 **0개**

## BlockMap — 사용자 친화 블록 사전

```python
b = c.blocks()
b["매출 성장률"]      # 한글 label
b["growth"]          # 영문 key
b.growth             # attribute (tab-complete)
b                    # 섹션별 카탈로그 테이블
```

오타 시 `KeyError: 'grwth' — 혹시: growth?`

## 블록 추가 절차

1. `catalog.py`: `_BLOCKS`에 BlockMeta 추가
2. `builders.py`: builder 함수 작성, `_meta(key).label`로 title
3. `registry.py`: `buildBlocks()` 안에 추가
4. `templates.py`: 섹션의 `visibleKeys`에 key 추가

**라벨 변경**: catalog.py label만 변경. 끝. 전부 자동 반영.
**순서 변경**: catalog.py _BLOCKS 위치만 이동. 끝.

## DART/EDGAR 통합 동작

review는 Company-bound — DART/EDGAR 자동 분기.

### 통화 포맷
- `company.currency` → `_REVIEW_CURRENCY` contextvars 자동 설정
- KRW: 조/억 포맷 (예: "매출 39.2조원")
- USD: $B/$M 포맷 (예: "Revenue $394.3B")
- `review/registry.py::buildBlocks()`에서 자동 적용

### EDGAR review 동작

```python
c = Company("AAPL")
c.review()               # 전체 6막 보고서 (USD 포맷)
c.review("수익구조")      # 단일 섹션
c.reviewer()             # review + AI 종합의견
```

6막 서사 구조, 블록 카탈로그, 4개 출력 형식 전부 EDGAR에서 동일 동작.

## 스토리 템플릿 체계

기업 특성에 따라 보고서의 강조점을 자동 조정한다.

### 7개 템플릿

| 템플릿 | 판별 조건 | 강조 블록 |
|--------|----------|----------|
| 사이클 | 영업이익률 CV > 0.4 | 부문매출, 마진, CAPEX, 운전자본, ROIC Tree |
| 프랜차이즈 | CV < 0.15, 마진 > 10% | 마진, 현금품질, 배당, 스코어카드 |
| 턴어라운드 | 최근 3년 내 적자→흑자 | 마진, 레버리지, 부실판별, CF |
| 성장 | CAGR > 15% | 성장추이, CAGR, ROIC, 매출전망 |
| 자본집약 | PPE/자산 > 40% | CAPEX, OCF분해, 자산구조, Penman |
| 지주 | 지분법/영업 > 30% | 영업외분해, 지분추이, 배당, 자산 |
| 현금부자 | 순현금 + 현금/자산 > 20% | 자금원천, Penman, 배당, FCF사용처 |

### 템플릿 구조

각 템플릿은 `templates.py`의 `STORY_TEMPLATES` dict에 정의:

```python
"사이클": {
    "description": "...",
    "emphasize": {...},       # 강조 블록 set → ★ 마크
    "keyQuestions": [...],    # 핵심 질문 4개
    "actFocus": {...},        # 막별 관전 포인트
    "industryContext": "...", # 업종 맥락 (AI 참조)
    "peerAxes": [...],        # 비교 축
}
```

- `detectTemplate(company)` — 재무 데이터로 자동 판별
- `detectTemplates(company)` — 복수 매칭 (예: 사이클 + 자본집약)
- 새 템플릿 추가: dict 하나 추가 + detectTemplate에 판별 조건 추가

### emphasize 동작

`registry.py::buildReview(template="auto")`에서:
1. `detectTemplate()` 호출 → 템플릿 판별
2. `STORY_TEMPLATES[template]["emphasize"]` 로드
3. 블록 조립 시 해당 key의 블록에 `Block.emphasized = True`
4. `formats.py`에서 `★` 마크 표시

## Conditional Narrative Assembly (narrate.py)

AP통신/Arria NLG 패턴. 데이터 값의 변화율/수준/추세에 따라 해석 문장을 조건 분기.
AI 없이 100% 결정론적, 환각 0%.

### 임계값 중앙 관리

```python
# narrate.py
_THRESHOLDS = {
    "margin_delta": [(5, "대폭 확대"), (1, "개선"), (-1, "보합"), (-5, "하락"), (None, "급락")],
    "debt_ratio": [(50, "매우 안정적"), (100, "안정적"), ...],
    ...
}
```

기준을 바꾸면 모든 해석 문장이 자동 반영.

### narrate 함수 9개

| 함수 | 적용 블록 | 해석 내용 |
|------|----------|----------|
| narrateGrowth | growth | YoY + CAGR 방향성 |
| narrateMargin | marginTrend | 마진 변화 + 수준 + 추세 |
| narrateCashFlow | cashFlowOverview | CF 패턴 + FCF 방향 |
| narrateCashQuality | cashQuality | OCF/NI 현금 전환 판정 |
| narrateLeverage | leverageTrend | 부채비율 수준 + 추세 |
| narrateDistress | distressScore | Z-Score 구간 판정 |
| narrateROIC | roicTimeline | ROIC vs WACC 가치 창출/파괴 |
| narrateValuation | valuationSynthesis | 저/적정/고평가 + 안전마진 |
| narrateConcentration | concentration | HHI 집중도 판정 |

### 막 결론 (buildActSummary)

각 막이 끝날 때 1-2문장 결론 자동 생성. 사용한 thread는 재사용하지 않아 6막 전부 고유.

## 보고서 발간 (publisher.py)

review 보고서를 블로그 포스트로 자동 발간.

### API

```python
from dartlab.review.publisher import publishReport, publishBatch

publishReport("005930")               # 단일 기업
publishReport("005930", template="사이클")  # 템플릿 수동 지정
publishBatch(["005930", "000660"])     # 배치 (순차, 메모리 안전)
```

### 발간 경로

```
blog/05-company-reports/{순번}-{종목코드}-{기업명}/index.md
```

### frontmatter 구조

```yaml
---
title: "삼성전자 — 사이클의 파도 위에서"
date: 2026-04-04
category: company-reports
series: company-reports
stockCode: "005930"
corpName: "삼성전자"
storyTemplate: "사이클"
grade: "dCR-AA+"
---
```

### 보고서 구성

```
frontmatter
보고서 헤더 (템플릿명, 섹터, 데이터 기준)
요약 카드 (결론 + 강점 + 경고)
스토리 템플릿 핵심 질문
재무 순환 서사

# 제1막: 이 회사는 뭘 하는가
  > 핵심 질문 + 관전 포인트
  ★ 강조 블록 + 해석 문장 + 테이블
  **1막 결론**

> 1→2 전환 문장

# 제2막 ~ 제6막 (동일 패턴)

credit 보고서 링크 (있으면)
면책
```

### 정기 발간 체계

| 유형 | 주기 | 트리거 | 대상 |
|------|------|--------|------|
| 정기 보고서 | 분기 | 사업보고서 공시 후 2주 | KOSPI 시총 상위 30 |
| 이벤트 보고서 | 수시 | 실적 서프라이즈, 등급 변동 | 해당 종목 |
| 신규 커버리지 | 수시 | 사용자 요청 또는 신규 상장 | 개별 |

### credit 통합 (단일 보고서 단일화)

review 5-7 신용평가 섹션이 credit의 모든 정보를 흡수한다:
- creditMetrics, creditScore, creditHistory, cashFlowGrade, creditPeerPosition, creditFlags (수치)
- **creditNarrative** — 7축 서사 (severity별 strong/adequate/weak/critical) ← 신규
- **creditAudit** — 외부 신평사(KIS/KR/NICE) 등급 + notch 차이 + 동의/비동의 ← 신규

**credit 자체 publisher는 deprecated.** review.publisher가 단일 진입점.
기존 16개 credit 보고서는 `blog/04-credit-reports/`에 아카이브로 보존.

### _registry.json

발간된 보고서 목록. publisher가 자동 관리.

```json
[{"stockCode": "005930", "corpName": "삼성전자", "order": 4, "template": "사이클", ...}]
```

## 6막 렌더링 (formats.py)

### 6막 헤더

각 막의 첫 섹션 앞에 자동 삽입:

```markdown
# 제1막: 이 회사는 뭘 하는가
> **핵심 질문**: 매출의 원천은 무엇이고 얼마나 빨리 성장하는가?
> **이 기업의 관전 포인트**: 부문별 매출 변동 진폭 + 재고 사이클
```

### 6막 전환 문장

데이터 기반 인과 연결 (narrative.py::buildActTransitions):

```
1→2: "매출 333.6조에서 영업이익률 13.1% — 이 마진의 원천은?"
2→3: "순이익 45.2조 → 영업CF 85.3조 (189%) — 이익이 현금으로 뒷받침되는가?"
```

## Review Audit 체계

> review 를 실제로 돌려보면서 사람(또는 AI 대리) 이 읽고 → 데이터 이상 / 엔진 부족 / 템플릿 부족 발견 → 코드 수정 → 다시 돌려보기.
> 이게 유일한 진짜 audit. 개별 엔진 단위 audit 는 파편화 — review audit 1개로 통합.

### Fix 원칙

**근본 원인 1곳만 고친다.** 우회로/덕지덕지/private 함수 신설 금지.
- 포맷팅 단에서 "만원이면 조로 변환" 같은 패치 금지 → 파서가 단위를 올바르게 뽑도록 근본 수정
- 같은 버그가 2종목 이상에서 나오면 종목별 분기 금지 → 공통 경로에서 해결
- 고치기 어려우면 None 반환이 패치보다 낫다

### 파이프라인

```
1단계: review 실행
   c.review(perspective="bottomUp", template="auto")

2단계: 사람/AI 읽고 발견
   데이터 이상 / 엔진 오류 / 서사 부재 / 관점 부적절 / 축 추가 필요 / AI 해석 오류

3단계: 기록
   data/dart/auditReview/{종목코드}.md (review 전문 + 발견 + 조치)

4단계: 수정 + 재검증 (발견 0건까지)

5단계: 크로스 종목 (3~5종목 공통 패턴 → 엔진 레벨 수정)
```

### 오류 발견 → 학습 매커니즘 반영 경로

review audit 에서 발견한 오류는 **3가지 학습 매커니즘** 중 하나로 이어질 수 있다:

| 원인 | 학습 대상 | 파일 (SSOT) | 절차 |
|---|---|---|---|
| **계정명 미매핑** | accountMappings.json | `core/data/accountMappings.json` (34,171 매핑) | `_reference/LEARNING_WORKFLOW.md` 6단계: 측정→수집→분석→학습→병합→검증. 매핑률 목표 ≥95% |
| **Topic 인식 실패** | sections 매퍼 | `core/docs/topicGraph.py::TOPIC_KEYWORDS` (33 topic) | 한글 키워드 추가 → 실험(`experiments/XXX.py`) 검증 → STATUS.md 갱신 |
| **snakeId 불일치** | DART↔EDGAR alias | `core/finance/labels.py::SNAKEID_ALIASES` (70 alias) | 하드코딩 수동 편집 → mergeAliasRows 양방향 검증 |
| **파싱 규칙 변경** (DART 공시 구조 변경) | 분석 calc 함수 | `analysis/financial/*.py` | 실험 기반 검증 후 반영. accountMappings 무분별한 수작업 PR 거절 |

### 학습 절차 상세

**1. 계정 매핑 학습** (`_reference/LEARNING_WORKFLOW.md`):
```
측정 (현재 매핑률) → 수집 (미매핑 계정 리스트)
→ 분석 (snakeId 판단, SequenceMatcher ≥0.95 자동/0.6~0.95 수동)
→ 학습 (learnedSynonyms.json 수정)
→ 병합 (accountMappings.json 재생성)
→ 검증 (BS 항등식 ±1%, 매핑률 재측정)
```

**2. Sections 학습** (`core/docs/topicGraph.py`):
```
DART 공시 HTML 구조 변경 감지 → topicGraph.py TOPIC_KEYWORDS 확인
→ 키워드 추가/수정 → 실험 파일 작성 (experiments/XXX.py)
→ 종목별 매칭률 ≥95% 확인 → STATUS.md 갱신 → 사용자 승인
```

**3. DART 공시 구조 변경 대응** (매 분기 잠재):
```
review audit 에서 세그먼트/재무 데이터 이상 발견
→ 원본 docs parquet 의 해당 topic 확인 (c.show("productService"))
→ 테이블 레이아웃 변경 여부 판단
→ revenue.py / bridge.py 파싱 룰 수정
→ 실험 검증 → 프로덕션 반영
```

### 실행 주기

| 주기 | 대상 | 목적 |
|---|---|---|
| 신규 엔진/축 추가 시 | 1종목 | 새 블록 review 정상 등장 |
| 릴리즈 전 | KOSPI top 5 | 전체 회귀 |
| 분기 1회 | KOSPI top 10 + 업종 대표 5 | 데이터 드리프트 + 학습 필요 판단 |

### 핵심 원칙

- **review 를 보면서 한다** — calc 단위 테스트로는 대본 품질 알 수 없음
- **파편 audit 금지** — analysis/quant/AI audit 따로 X. review audit 1개로 통합
- **발견 → 기록 → 수정 → 재검증** 폐쇄 루프
- **학습은 실험 기반** — accountMappings 무분별한 수작업 금지, 실험 검증 후 반영

## 품질 검증

- 빈 섹션, 중복 표시, 극단값 비율(수만%), 맥락 없는 경고 체크
- 공개 샘플: `docs/samples/{종목코드}.md` (10개)
- `grep -n 'HeadingBlock("' src/dartlab/review/builders.py` → 0건이어야 함
- 해석 문장 30개+ 확인 (narrate 함수 9개 × 커버리지)
- 막 결론 6개 전부 고유 확인
- Polars 박스 아트 0개, 과학 표기법 0개

## 버그픽스 점검 진행사항

→ KnowledgeDB `executions` + `insights` 테이블에 저장 (파일 기반 audit 폐기)

## 관련 코드

| 파일 | 역할 |
|------|------|
| `src/dartlab/review/catalog.py` | 블록/섹션 메타, 순서 (단일 진실의 원천) |
| `src/dartlab/review/templates.py` | 섹션 설정 + 7개 스토리 템플릿 |
| `src/dartlab/review/narrate.py` | 해석 문장 생성 (임계값 중앙 관리) |
| `src/dartlab/review/builders.py` | calc* → Block 변환 + narrate 호출 |
| `src/dartlab/review/registry.py` | buildBlocks/buildReview 조립 + emphasize |
| `src/dartlab/review/publisher.py` | 블로그 보고서 발간 |
| `src/dartlab/review/formats.py` | 6막 헤더 + 막 결론 + 마크다운/HTML/JSON |
| `src/dartlab/review/narrative.py` | 7개 인과 패턴 감지 + 6막 전환 문장 |
| `src/dartlab/review/blocks.py` | Block 타입 (emphasized 필드 포함) |
| `src/dartlab/review/summary.py` | 요약 카드 + 섹션 요약 |
| `src/dartlab/review/presets.py` | 관점별 프리셋 5개 |
