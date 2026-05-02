# Story

> 상위 사상: [philosophy.md](philosophy.md) · 자가개선 루프: [coreloop.md](coreloop.md)

**주체**: story 엔진 (`c.story(type?, template?)`).
**현재**: 11 reportType × 7 template 2 축 체계 · 블록 카탈로그 (BlockMap) · NarrativeSection (thesis) · macro/credit/industry 블록 통합.
**방향**: thesis 서사 품질 고도화 · story audit 루프 확대 · dashboard/HTML 출력 옵션.

5 분석 엔진의 calc 결과를 블록 단위로 조합하여 보고서를 만드는 **보고서 빌더**. 각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 1. 사상 — 보고서 빌더로 간다

> 1. **5 엔진** (analysis/scan/macro/credit/quant) 이 데이터를 미리 계산해서 **재료** (calc dict) 를 만든다.
> 2. **story** 가 재료를 블록 단위로 조합하여 **보고서**를 만든다 — 11 가지 보고서 타입 × 7 가지 기업유형 템플릿.
> 3. **AI/사람** 이 보고서를 읽고 **해석하고 판단**한다.
>
> story 는 해석을 제공하지 않는다. **다양한 관점의 근거를 체계적으로 배치**한다. 해석은 AI 또는 사람의 몫이다. 어떤 관점이든 대응할 수 있는 보고서 구조 — 신용, 성장, 위기, 배당, 지배구조, 매크로, 가치평가.
>
> **AI 는 `story()` 를 직접 호출하지 않는다** (83 초 타임아웃). 대신 story 의 보고서 타입을 참고하여 분석 관점을 잡되, 엔진을 직접 호출하여 자기 주관으로 판단한다.

| 항목 | 내용 |
|------|------|
| 레이어 | **L3** (1.0.0 리팩토링 이후) — L2 4 엔진 + L1.5(scan) 소비 |
| 사상 | **이야기꾼** — 엔진이 제공한 숫자를 서사로 조립. 해석 문장 생성 포함 |
| 진입점 | `c.story()`, `c.story(type=...)`, `dartlab.ask()` |
| 소비 | **analysis + credit + quant + macro** (L2) + **scan** (L1.5) |
| 생산 | ai(ask), 사용자(터미널/HTML/마크다운/JSON), 블로그 보고서 |
| 출력 | rich, html, markdown, json |
| 템플릿 | 2 축: reportType (관점) × template (기업유형) |

**반복 실패** — story 가 해석 문장을 주장 ("삼성전자는 강력하다") 으로 전개. story 는 근거 배치, 해석은 AI/사람. narrate 함수는 조건분기 기술로만.

### 방향성 메모 — docstring SSOT 와의 교류 (2026-04-24)

SSOT = [`ops/skills.md`](skills.md) — **skill 은 별도 파일 없이 엔진 docstring 이 담는다**.

story 는 **사람 분석 루트 (L1 → L2 → story → 사람)** 의 종착. AI 는 story 를 우회하고 공개 함수 docstring 을 경험축으로 쓴다 — 루트가 다르다. 교류:

- **docstring → story**: 엔진 docstring Guide 섹션이 audit 로 충분히 검증되면 story 블록 템플릿에 반영 (같은 해석 규칙 · 같은 임계값).
- **story → docstring**: 기존 story 블록 중 재현 가능 · 해석 규칙 명확한 것은 공개 함수로 추출해 엔진 docstring 에 Guide 로 명시. AI · story 공용 호출.

현재 story 블록은 유지, 점진 정합. 상세 사상은 `ops/skills.md`.

---

## 2. 2 축 체계 — reportType × template 로 간다

기존 3 단계 (perspective / preset / template) → **reportType 단일축**으로 통합. 기업유형(template)은 자동 감지 보조로 독립 유지.

### 1 축 — reportType (무엇을 집중적으로 볼 것인가)

11 종. 각 타입 = `{sectionOrder, emphasize, focusQuestions, detail}`.

| key | 집중 관점 | 대상 | 구조 |
|---|---|---|---|
| `full` | 전체 6 막 인과 | 일반 분석 | 블록 |
| `executive` | 결론/수익/현금/가치 3 분컷 | 의사결정자 | 블록 |
| `credit` | 안정성/현금/자금/7 축등급 | 채권/여신 | 블록 |
| `valuation` | DCF/상대가치/매출전망 | 가치투자 | 블록 |
| `growth` | CAGR/마진확장/투자효율 | 성장투자 | 블록 |
| `crisis` | 부실/레버리지/유동성 | 위험 진단 | 블록 |
| `audit` | 이익품질/재무정합성/공시변화 | 감사/포렌식 | 블록 |
| `dividend` | 배당지속성/FCF커버리지/총환원 | 인컴 투자자 | 블록 |
| `governance` | 임원보수 괴리/외부이사 독립성/지분구조 | 거버넌스 리스크 | 블록 |
| `macro` | 사이클 + 역사적 팩트 (10 macro 블록 + companyCyclePosition) | 탑다운 | 블록 |
| `thesis` | 가설 → 증거 수집 → 판정 | 논제 점검 | **NarrativeSection** (서사 주도) |
| `dashboard` | 한 페이지 스냅샷 | 스냅샷 | 블록 |

### 2 축 — template (이 기업은 어떤 유형인가, 자동 감지)

7 종. reportType 과 **독립 차원**으로 `emphasize` 를 추가 오버레이: 사이클/프랜차이즈/턴어라운드/성장/자본집약/지주/현금부자.

`c.story(type="full", template="사이클")` 동시 사용 가능 — 6 막 순서 + 사이클 강조.

### 블록화 vs 서사화

블록은 **표+숫자+경고 반복의 균질 보고서**에 최적. 10/11 타입은 블록 기반. `thesis` 만 예외 — 가설→증거→판정은 블록으로 쪼개면 서사가 깨져 **NarrativeSection**(Text 중심) 단위로 렌더링.

**반복 실패** — thesis 를 블록으로 쪼개서 서사 끊김. NarrativeSection 단위 유지.

---

## 3. 호출 계약

```python
import dartlab
c = dartlab.Company("005930")

# 기본 (full = 6막 전체)
c.story()
c.story("수익성")                       # 단일 섹션 (기존 유지)

# 보고서 타입 지정
c.story(type="credit")                   # 신용분석
c.story(type="dividend")                 # 배당 지속성 + 총환원
c.story(type="governance")               # 임원보수 괴리 + 외부이사 독립성
c.story(type="macro")                    # 사이클 + 역사적 유사 에포크
c.story(type="thesis", hypothesis="...") # AI 논제 검증 (서사)

# 기업유형 자동 감지 (독립 차원)
c.story(template="auto")
c.story(type="full", template="사이클")

# (deprecated — 다음 릴리즈에 제거)
c.story(perspective="crisis")   # DeprecationWarning → type="crisis"로 매핑
c.story(preset="audit")         # DeprecationWarning → type="audit"로 매핑

# AI 종합의견
c.ask(guide="...")
```

한글 alias: `c.story(type="신용")`, `c.story(type="배당")`, `c.story(type="지배구조")` 등.

### 노트북

[![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/codertest123/blob/master/notebooks/marimo/08_review.py)
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/08_review.ipynb)

---

## 4. 5 엔진 조합 매핑 — 6 막 각 섹션을 엔진 calc 로 채운다

5 분석 엔진이 각각 독립 calc 모듈로 story 에 도구를 제공한다 (`ops/architecture.md` "모듈 제공 패턴" 참조).

| 막 | 섹션 | 소비 엔진 | 핵심 calc/블록 |
|---|------|---------|---------|
| 1 막 사업이해 | 수익구조, 성장성 | **analysis** | calcSegmentComposition, calcRevenueGrowth, calcConcentration, ... |
| 2 막 수익성 | 수익성, 비용구조 | **analysis** | calcMarginTrend, calcReturnTrend, calcCostBreakdown, ... |
| 3 막 현금전환 | 현금흐름, 이익품질 | **analysis** | calcCashFlowOverview, calcCashQuality, ... |
| 4 막 안정성 | 자금조달, 안정성 | **analysis** | calcLeverage, calcDistress, ... |
| 5 막 자본배분 | 자산구조 ~ 신용평가 | **analysis** + **credit** | calcCapitalAllocation, calcCreditScore, calcCreditNarrative, ... |
| 6 막-1 가치평가 | 가치평가, 매출전망 | **analysis**(forecast/valuation) | calcValuationSynthesis, calcRevenueDirection, ... |
| 6 막-2 비교분석 | 비교분석 | **scan** | calcPeerPosition (교차 조합 관점), calcGovernanceSummary |
| 6 막-3 시장분석 | 시장분석 | **quant** | calcTrendData, calcRiskData, calcSignalData, calcStrategyData, calcCrosscheckData, calcQuantConclusionData (엔진=숫자만, story 가 narrate 호출) |
| 6 막-4 매크로 | 매크로 | **macro** | macroEnvironment, macroCycle, macroRates, macroLiquidity, macroSentiment, macroForecast, macroCorporate, macroTrade, macroFlags, valuationBand (10 블록, `macro("종합")` 1 회 호출) |

---

## 5. 보고서 타입 상세 — reportTypes.py SSOT 로 관리한다

기존 perspective/preset 을 **reportType 단일축**으로 통합. `c.story(type="credit")`.

| key | label | 집중 관점 | sectionOrder 요약 |
|-----|-------|----------|------------------|
| `full` | 전체 6 막 | 기본 바텀업 인과 서사 | 전체 TEMPLATE_ORDER |
| `executive` | 경영 요약 | 의사결정자 3 분컷 | 종합평가→수익구조→현금흐름→가치평가→SV |
| `credit` | 신용분석 | 채권/여신 심사 | 안정성→현금흐름→자금조달→효율성→신용평가→SV |
| `valuation` | 가치평가 집중 | 가치투자자 | 가치평가→수익성→성장성→매출전망→자본배분→안정성→SV |
| `growth` | 성장 스토리 | 성장투자자 | 수익구조→성장성→매출전망→수익성→투자효율→효율성→자본배분→SV |
| `crisis` | 위기 진단 | 부실/레버리지/유동성 | 매크로→안정성→자금조달→현금흐름→이익품질→신용평가→종합평가→SV |
| `audit` | 감사 관점 | 이익품질/정합성/공시변화 | 이익품질→재무정합성→안정성→지배구조→공시변화→SV |
| `dividend` | 배당·주주환원 | 인컴 투자자 | 수익구조→현금흐름→자본배분→자금조달→안정성→SV |
| `governance` | 경영진·지배구조 | 거버넌스 리스크 | 지배구조→자본배분→공시변화→종합평가→SV |
| `macro` | 매크로 사이클 위치 | 탑다운 투자자 | 매크로→시장분석→매출전망→가치평가→SV |
| `thesis` | AI 논제 검증 | 가설→증거→판정 | thesisReport→SV (NarrativeSection 기반) |
| `dashboard` | **대시보드** | 한 페이지 스냅샷 | 종합평가→수익구조→안정성→가치평가→매크로→SV |

SV = storyValidation 섹션.

### dashboard — 한 페이지 회사 스냅샷 (2026-Q2 추가)

**목적**: 블로그(서사) 와 구분되는 **구조화 스냅샷**. 회사를 6 섹션으로 요약 — 스코어·재무·리스크·가치·매크로·AI 논제.

**emphasize 블록** (기존 calc 재사용):
- `scorecard` — 5 영역 A~F 종합평가.
- `creditScore` — 20 등급 신용평가.
- `valuationSynthesis` — DCF/DDM/상대가치 통합.
- `peerPosition` — 업종 내 백분위.
- `marginTrend`, `leverageTrend`, `distressScore` — 5 년 재무 추이.
- `macroCycle`, `companyCyclePosition` — 매크로 맥락.

**4 채널 렌더링**: 같은 `c.story(type='dashboard')` 결과를 4 채널로 출력.

| 채널 | API | 용도 |
|------|-----|------|
| 웹 | `/dashboard/{stockCode}` (GitHub Pages) | `landing/static/dashboards/{code}.json` 사전빌드 |
| Jupyter | `c.story(type='dashboard')` → 변수 자동 렌더 | `VizSpec._repr_html_` |
| Marimo | 동일 | `VizSpec._repr_mimebundle_` |
| CLI | `renderAscii(story)` | `dartlab.story.formats.renderAscii` (터미널 ANSI) |

**사전빌드**: `scripts/build/buildDashboards.py` (mapBuild workflow 에 연동).

---

## 6. 아키텍처 — catalog.py SSOT + builders/registry/narrate

```
catalog.py          단일 진실의 원천 (164 블록 메타 + 25 섹션 메타 + 순서)
  ├── templates.py  섹션별 설정 (visibleKeys, helper, aiGuide) + 7개 스토리 템플릿 + 6개 생애주기
  ├── reportTypes.py 11 ReportType 정의 (full/executive/credit/valuation/growth/crisis/audit/dividend/governance/macro/thesis)
  ├── builders.py   analysis calc* → Block 리스트 변환 (narrate 호출)
  ├── narrate.py    Conditional Narrative Assembly — 임계값 중앙 관리 + 해석 문장
  ├── registry.py   buildBlocks() / buildStory() 조립 + emphasize 반영
  │     └── blockMap.py  BlockMap — 사용자 친화 블록 사전
  ├── publisher.py  블로그 보고서 발간 파이프라인
  ├── renderer.py   Rich 콘솔 렌더링
  ├── formats.py    HTML / Markdown / JSON 렌더링 + 6막 헤더 + 막 결론
  ├── blocks.py     Block 타입 (Heading, Table, Text, Flag, Metric) + emphasized 필드
  └── section.py    Section dataclass
```

### catalog.py SSOT

- `_BLOCKS` 리스트 = **164 개** 블록 정의 + 렌더링 순서.
- `SECTIONS` 리스트 = **25 개** 섹션 (6 막 22 개 + 메타 3 개) + 렌더링 순서.
- **key 는 불변** — 한 번 등록된 key 는 영구 유지.
- **label 은 자유** — 사용자 표시명은 언제든 변경 가능.
- **리스트 정의 순서 = 렌더링 순서** (list 로 순서 보장).
- catalog label 하나 바꾸면 전체 렌더링이 따라간다.
- builders.py 에 하드코딩된 `HeadingBlock` title 은 **0 개**.

### 섹션 목록 (25 개, 6 막 + 메타)

| 막 | 섹션 key | title |
|----|---------|-------|
| 1 막 | 수익구조, 성장성 | 사업 이해 |
| 2 막 | 수익성, 비용구조 | 수익성 + 원천 |
| 3 막 | 현금흐름, 이익품질 | 현금 전환 |
| 4 막 | 자금조달, 안정성 | 안정성 |
| 5 막 | 자산구조, 효율성, 투자효율, 자본배분, 재무정합성, 종합평가, 신용평가 | 자본배분 |
| 6 막 | 가치평가, 지배구조, 공시변화, 비교분석, 매출전망, 시장분석, 매크로 | 전망 + 가치 |
| 메타 | improvementPlan, storyValidation, thesisReport | 개선/검증/논제 |

**반복 실패** — builders.py 에 `HeadingBlock("섹션명")` 하드코딩 → label 변경 시 누락. catalog.py `_meta(key).label` 경유 유지.

---

## 7. BlockMap — 사용자 친화 블록 사전으로 접근한다

```python
b = c.blocks()
b["매출 성장률"]      # 한글 label
b["growth"]          # 영문 key
b.growth             # attribute (tab-complete)
b                    # 섹션별 카탈로그 테이블
```

오타 시 `KeyError: 'grwth' — 혹시: growth?`.

### 블록 추가 절차

1. `catalog.py`: `_BLOCKS` 에 BlockMeta 추가.
2. `builders.py`: builder 함수 작성, `_meta(key).label` 로 title.
3. `registry.py`: `buildBlocks()` 안에 추가.
4. `templates.py`: 섹션의 `visibleKeys` 에 key 추가.

**라벨 변경**: catalog.py label 만 변경. 끝. 전부 자동 반영.
**순서 변경**: catalog.py `_BLOCKS` 위치만 이동. 끝.

---

## 8. DART/EDGAR 통합 — Company-bound 로 자동 분기한다

story 는 Company-bound — DART/EDGAR 자동 분기.

### 통화 포맷
- `company.currency` → `_STORY_CURRENCY` contextvars 자동 설정.
- KRW: 조/억 포맷 (예: "매출 39.2 조원").
- USD: $B/$M 포맷 (예: "Revenue $394.3B").
- `story/registry.py::buildBlocks()` 에서 자동 적용.

### EDGAR story 동작

```python
c = Company("AAPL")
c.story()               # 전체 6막 보고서 (USD 포맷)
c.story("수익구조")      # 단일 섹션
dartlab.ask()             # story + AI 종합의견
```

6 막 서사 구조, 블록 카탈로그, 4 개 출력 형식 전부 EDGAR 에서 동일 동작.

---

## 9. 스토리 템플릿 — 7 종 + 생애주기 6 단계

기업 특성에 따라 보고서의 강조점을 자동 조정한다.

### 7 개 템플릿

| 템플릿 | 판별 조건 | 강조 블록 |
|--------|----------|----------|
| 사이클 | 영업이익률 CV > 0.4 | 부문매출, 마진, CAPEX, 운전자본, ROIC Tree |
| 프랜차이즈 | CV < 0.15, 마진 > 10% | 마진, 현금품질, 배당, 스코어카드 |
| 턴어라운드 | 최근 3 년 내 적자→흑자 | 마진, 레버리지, 부실판별, CF |
| 성장 | CAGR > 15% | 성장추이, CAGR, ROIC, 매출전망 |
| 자본집약 | PPE/자산 > 40% | CAPEX, OCF 분해, 자산구조, Penman |
| 지주 | 지분법/영업 > 30% | 영업외분해, 지분추이, 배당, 자산 |
| 현금부자 | 순현금 + 현금/자산 > 20% | 자금원천, Penman, 배당, FCF 사용처 |

### 생애주기 단계 (LIFECYCLE_PHASES × template 직교)

`templates.py` 의 `LIFECYCLE_PHASES` — template(사업 특성) 과 독립된 시간적 위치 축.

| phase | label | 핵심 | 밸류에이션 힌트 |
|-------|-------|------|----------------|
| `earlyGrowth` | 초기성장 | 매출 폭발, 마진·FCF 음수 | Revenue multiple + Survival probability |
| `highGrowth` | 고성장 | 빠른 확대 + 마진 전환 | 2-stage DCF |
| `matureGrowth` | 성숙성장 | 중속 성장 + FCF 양전환 | FCFF DCF + 상대가치 |
| `matureStable` | 성숙안정 | 저성장 + 고배당 | FCFF DCF + DDM + 상대가치 |
| `decline` | 쇠퇴 | 매출·마진 축소, ROIC < WACC | Liquidation value |
| `turnaround` | 턴어라운드 | 적자→흑자 초기 | 시나리오 DCF |

`detectTemplate()` = 사업 특성, `calcLifeCycle()` = 시간 위치. 보고서 헤더에 `{template} × 생애주기 {label}` 표시.

### 템플릿 구조

각 템플릿은 `templates.py` 의 `STORY_TEMPLATES` dict 에 정의:

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

- `detectTemplate(company)` — 재무 데이터로 자동 판별.
- `detectTemplates(company)` — 복수 매칭 (예: 사이클 + 자본집약).
- 새 템플릿 추가: dict 하나 추가 + detectTemplate 에 판별 조건 추가.

### emphasize 동작

`registry.py::buildStory(template="auto")` 에서:
1. `detectTemplate()` 호출 → 템플릿 판별.
2. `STORY_TEMPLATES[template]["emphasize"]` 로드.
3. 블록 조립 시 해당 key 의 블록에 `Block.emphasized = True`.
4. `formats.py` 에서 `★` 마크 표시.

---

## 10. Conditional Narrative Assembly (narrate.py) — 해석 문장을 조건분기로 자동 생성한다

AP 통신/Arria NLG 패턴. 데이터 값의 변화율/수준/추세에 따라 해석 문장을 조건 분기. AI 없이 100% 결정론적, 환각 0%.

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

### narrate 함수 9 개

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

각 막이 끝날 때 1-2 문장 결론 자동 생성. 사용한 thread 는 재사용하지 않아 6 막 전부 고유.

---

## 11. 6 막 렌더링 (formats.py)

### 6 막 헤더

각 막의 첫 섹션 앞에 자동 삽입:

```markdown
# 제1막: 이 회사는 뭘 하는가
> **핵심 질문**: 매출의 원천은 무엇이고 얼마나 빨리 성장하는가?
> **이 기업의 관전 포인트**: 부문별 매출 변동 진폭 + 재고 사이클
```

### 6 막 전환 문장

데이터 기반 인과 연결 (`narrative.py::buildActTransitions`):

```
1→2: "매출 333.6조에서 영업이익률 13.1% — 이 마진의 원천은?"
2→3: "순이익 45.2조 → 영업CF 85.3조 (189%) — 이익이 현금으로 뒷받침되는가?"
```

---

## 12. 보고서 발간 (publisher.py) — 블로그 포스트로 자동 발간한다

story 보고서를 블로그 포스트로 자동 발간.

### API

```python
from dartlab.story.publisher import publishReport, publishBatch

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
| 정기 보고서 | 분기 | 사업보고서 공시 후 2 주 | KOSPI 시총 상위 30 |
| 이벤트 보고서 | 수시 | 실적 서프라이즈, 등급 변동 | 해당 종목 |
| 신규 커버리지 | 수시 | 사용자 요청 또는 신규 상장 | 개별 |

### credit 통합 (단일 보고서 단일화)

story 5-7 신용평가 섹션이 credit 의 모든 정보를 흡수한다:
- creditMetrics, creditScore, creditHistory, cashFlowGrade, creditPeerPosition, creditFlags (수치).
- **creditNarrative** — 7 축 서사 (severity 별 strong/adequate/weak/critical) ← 신규.
- **creditAudit** — 외부 신평사(KIS/KR/NICE) 등급 + notch 차이 + 동의/비동의 ← 신규.

**credit 자체 publisher 는 deprecated.** story.publisher 가 단일 진입점. 기존 16 개 credit 보고서는 `blog/04-credit-reports/` 에 아카이브로 보존.

### _registry.json

발간된 보고서 목록. publisher 가 자동 관리.

```json
[{"stockCode": "005930", "corpName": "삼성전자", "order": 4, "template": "사이클", ...}]
```

---

## 13. Story Audit — story 보면서 근본 1 곳을 고친다

> story 를 실제로 돌려보면서 사람(또는 AI 대리)이 읽고 → 데이터 이상 / 엔진 부족 / 템플릿 부족 발견 → 코드 수정 → 다시 돌려보기. 이게 유일한 진짜 audit. 개별 엔진 단위 audit 는 파편화 — story audit 1 개로 통합.

### Fix 원칙

**근본 원인 1 곳을 고친다.** 우회로·private 헬퍼 신설은 지양.
- 포맷팅 단에서 "만원이면 조로 변환" 같은 패치 대신, 파서가 단위를 올바르게 뽑도록 근본 수정.
- 같은 버그가 2 종목 이상에서 나오면 종목별 분기 대신 공통 경로에서 해결.
- 고치기 어려우면 `None` 반환이 패치보다 낫다.

### 파이프라인

```
1단계: story 실행
   c.story(type="full", template="auto")

2단계: 사람/AI 읽고 발견
   데이터 이상 / 엔진 오류 / 서사 부재 / 관점 부적절 / 축 추가 필요 / AI 해석 오류

3단계: 기록
   data/dart/auditStory/{종목코드}.md (story 전문 + 발견 + 조치)

4단계: 수정 + 재검증 (발견 0건까지)

5단계: 크로스 종목 (3~5종목 공통 패턴 → 엔진 레벨 수정)
```

### 오류 발견 → 학습 매커니즘 반영 경로

story audit 에서 발견한 오류는 **3 가지 학습 매커니즘** 중 하나로 이어질 수 있다:

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
story audit 에서 세그먼트/재무 데이터 이상 발견
→ 원본 docs parquet 의 해당 topic 확인 (c.show("productService"))
→ 테이블 레이아웃 변경 여부 판단
→ revenue.py / bridge.py 파싱 룰 수정
→ 실험 검증 → 프로덕션 반영
```

### 실행 주기

| 주기 | 대상 | 목적 |
|---|---|---|
| 신규 엔진/축 추가 시 | 1 종목 | 새 블록 story 정상 등장 |
| 릴리즈 전 | KOSPI top 5 | 전체 회귀 |
| 분기 1 회 | KOSPI top 10 + 업종 대표 5 | 데이터 드리프트 + 학습 필요 판단 |

### 핵심 원칙

- **story 를 보면서 한다** — calc 단위 테스트로는 대본 품질 알 수 없음.
- **story audit 로 통합** — analysis/quant 단위 audit 는 별도로 운영하지 않는다.
- **발견 → 기록 → 수정 → 재검증** 폐쇄 루프.
- **학습은 실험 기반** — accountMappings 수정은 실험 검증을 거친 뒤 반영한다.

**반복 실패** — 개별 엔진 단위 audit 파편화 / 포맷팅 단 패치로 근본 원인 회피 / 종목별 분기로 2 종목 이상 버그 흡수. 셋 모두 "근본 1 곳" 원칙 위반.

---

## 14. 품질 검증

- 빈 섹션, 중복 표시, 극단값 비율(수만%), 맥락 없는 경고 체크.
- 공개 샘플: `docs/samples/{종목코드}.md` (10 개).
- `grep -n 'HeadingBlock("' src/dartlab/story/builders.py` → 0 건이어야 함.
- 해석 문장 30 개+ 확인 (narrate 함수 9 개 × 커버리지).
- 막 결론 6 개 전부 고유 확인.
- Polars 박스 아트 0 개, 과학 표기법 0 개.

버그픽스 점검 진행사항은 KnowledgeDB `executions` + `insights` 테이블에 저장 (파일 기반 audit 폐기).

---

## 15. 개선 파이프라인 — story 변경 시 반드시 거친다

> story 변경 없이 AI 프롬프트/규칙만 건드리는 것 = 덕지덕지. **근본은 story.**

```
story 관점 추가/개선
  ↓
재료 엔진 calc 확인 (있으면 연결, 없으면 추가)
  ↓
story 블록 조립 (builders.py)
  ↓
AI Self-Description 자동 반영 (tool schema 자동)
  ↓
AI audit 질문 검증 (ASK_WORKBENCH_KERNEL.md)
  ↓
사람이 직접 읽고 품질 판단
```

### 절차

1. **관점 정의** — 어떤 분석 관점을 추가/개선하는가.
2. **재료 확인** — 필요한 calc 가 있는가 (analysis/scan/credit/quant/macro/industry).
3. **재료 없으면** — 해당 엔진에 calc 추가 (`ops/{엔진}.md` 규칙 준수, docstring 9 섹션 필수).
4. **블록 조립** — `story/builders.py` 에 블록 추가.
5. **AI audit** — `scripts/audit/aiAudit.py` 10 개 질문 실행 + **사람 직접 읽고 판단**.
6. **품질 미달 시** — 3 번으로 돌아가 재료 보강.

### 관점 현황 (2026-04-18 기준)

| 관점 | 재료 엔진 | 상태 |
|---|---|---|
| 유형별 관점 자동 설정 | analysis/lifeCycle | ✅ lifeCycle → emphasize 자동 연결 |
| 시나리오 분석 (base/bull/bear) | analysis/forecast + overrides | ✅ valuationSynthesisBlock scenarios |
| pro forma 전망 재무제표 | core/finance/proforma | ✅ proFormaHighlightsBlock |
| 경쟁사 비교 서사 | scan + industry | ✅ peerPositionBlock / peerRankingBlock |
| 산업 밸류체인 맥락 | industry | ✅ chainPositionBlock |
| 매크로 민감도 정량화 | analysis/macroExposure | ✅ macroSensitivityBlock |
| 신용등급 시나리오 | credit + overrides | ✅ creditScenarioBlock |
| thesis 보고서 | storyValidation | ✅ thesisReportBlocks |
| quant 서사 연결 | quant narrate | ✅ quantModuleBlock |

### 다음 개선 후보

- 배당 지속성 시나리오 (금리 변동 시 배당 커버리지 변화).
- ESG/탄소 리스크 관점 (재료 엔진 미구현).
- 경영진 교체 리스크 (재료: governance + 공시 diff).
- AI 논제 검증 고도화 (thesis — 가설→증거 자동 수집 강화).

---

## 16. 관련 코드

| 파일 | 역할 |
|------|------|
| `src/dartlab/story/catalog.py` | 블록/섹션 메타, 순서 (단일 진실의 원천, 164 블록/25 섹션) |
| `src/dartlab/story/templates.py` | 섹션 설정 + 7 개 스토리 템플릿 + 6 개 생애주기 + (deprecated) PERSPECTIVE_TEMPLATES |
| `src/dartlab/story/reportTypes.py` | 11 ReportType 정의 (perspective+preset 통합) |
| `src/dartlab/story/narrate.py` | 해석 문장 생성 (임계값 중앙 관리) |
| `src/dartlab/story/builders.py` | calc* → Block 변환 + narrate 호출 |
| `src/dartlab/story/registry.py` | buildBlocks/buildStory 조립 + emphasize |
| `src/dartlab/story/publisher.py` | 블로그 보고서 발간 |
| `src/dartlab/story/formats.py` | 6 막 헤더 + 막 결론 + 마크다운/HTML/JSON |
| `src/dartlab/story/narrative.py` | 7 개 인과 패턴 감지 + 6 막 전환 문장 |
| `src/dartlab/story/blocks.py` | Block 타입 (emphasized 필드 포함) |
| `src/dartlab/story/summary.py` | 요약 카드 + 섹션 요약 |
| `src/dartlab/story/presets.py` | 관점별 프리셋 (deprecated → reportTypes.py) |

---

## 요약 — 명제 11 줄

1. story 는 보고서 빌더. 5 엔진 calc 를 재료로 블록 조립. 해석은 AI/사람.
2. 축은 reportType (11 종 관점) × template (7 종 기업유형) 2 축. thesis 만 NarrativeSection.
3. catalog.py 가 SSOT — 164 블록 + 25 섹션 메타 + 순서. builders.py HeadingBlock 하드코딩 0.
4. 6 막 구조 (사업→수익→현금→안정→배분→전망), 각 섹션을 엔진 calc 로 채움.
5. 통화 자동 분기 (`company.currency` → contextvars), EDGAR 도 동일 동작.
6. narrate.py 9 함수 + 임계값 중앙 관리 = 결정론적 해석 문장 (환각 0).
7. publisher 는 `blog/05-company-reports/` 로 자동 발간, credit 통합 (단일 진입점).
8. dashboard type 은 한 페이지 스냅샷 (웹/Jupyter/Marimo/CLI 4 채널).
9. story audit 는 story 보면서 근본 1 곳 수정. 학습은 accountMappings/topicGraph/labels 경로.
10. AI 는 story 직접 호출 안 함 (83 초), 엔진을 직접 호출. story 는 사람용 + 블로그 파이프.
11. `dartlab.skills` 는 story 가 공유할 수 있는 분석 절차 reference 다. story 는 skill 을 runner 로 쓰지 않고 reportType/엔진 승격 후보 판단에 참고한다.
12. 개선 파이프라인 — 관점 → 재료 → 블록 → AI audit → 사람 판단. 프롬프트만 고치기는 덕지덕지.
