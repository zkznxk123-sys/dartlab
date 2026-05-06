---
id: engines.company.sections
title: sections — 회사 전체 지도
kind: curated
scope: builtin
status: observed
category: engines
purpose: sections 는 한 회사의 모든 기간 공시를 topic × period 매트릭스로 가로화한 단일 진입 DataFrame 이다. 개별 보고서를 하나씩 열지 않고 전 기간을 한 화면에서 비교한다.
whenToUse:
  - 회사 전체 공시를 한 번에 훑기
  - topic × period 매트릭스 직접 다루기
  - show / trace 의 원천 자료 이해
  - 공시 기간 커버리지 확인
  - 한국 DART 와 미국 EDGAR 같은 구조 이해
inputs:
  - 종목코드 또는 ticker
  - 선택적 topic 또는 period 필터
outputs:
  - topic × period Polars DataFrame
  - chapter / blockType / textNodeType / textLevel / textPath 메타
  - 기간별 원문 payload (text 또는 markdown table)
capabilityRefs:
  - Company.sections
  - Company.show
  - Company.trace
  - Company.select
  - Company.diff
toolRefs: []
knowledgeRefs:
  - engines.company
  - engines.data.foundation
  - engines.story
sourceRefs:
  - dartlab://skills/engines.company.sections
requiredEvidence:
  - target
  - period
  - topic
  - tableRef
  - executionRef
expectedOutputs:
  - 선택한 topic 의 chapter / blockType / textNodeType
  - 기간별 payload 비교 결과
  - source priority 적용 결과 (finance > report > docs)
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
procedure:
  - dartlab.Company(code) 로 회사를 만든다.
  - c.sections 로 전체 매트릭스 DataFrame 을 받는다.
  - chapter · topic · blockType 으로 Polars filter 한다.
  - c.show(topic) 으로 source priority (finance > report > docs) 적용된 단일 topic 을 본다.
  - c.trace(topic) 으로 어떤 source 가 선택됐는지 확인한다.
failureModes:
  - 결손값 (null) 을 0 으로 대체해 추세 왜곡
  - source priority 무시하고 docs 의 숫자를 finance 결과로 단정
  - 같은 topic 의 text 와 table 블록을 한 셀로 합쳐 처리
forbidden:
  - 기간 컬럼의 null 을 0 으로 대체하지 않는다.
  - source priority 가 적용되지 않은 raw 값을 분석 결론으로 단정하지 않는다.
examples:
  - 삼성전자 sections 보기
  - 사업개요 기간별 변화 추적
  - DART · EDGAR 같은 구조로 미국 종목 가로화
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-06"
---

## 엔진 역할

`sections` 는 한 회사의 전체 지도다. 각 보고기간 공시 문서를 topic 별로 쪼개고 시간축으로 옆으로 늘어놓아 가로화 보드 하나로 만든다. 개별 사업보고서를 하나씩 열지 않고 모든 공시 섹션을 시계열로 한 번에 비교한다.

한국 DART 사업보고서는 수십 개 섹션을 갖는다 — 제 I 장 (회사 개황) ~ 제 XII 장 (상세표). 각 보고서가 분기/연도별로 별도 파일이라서 같은 topic ("사업의 개요") 이 여러 기간에 흩어진다. `sections` 는 이 흩어진 원문을 **topic × 기간 매트릭스**로 재구성한다.

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")
c.sections                       # 전체 topic × 기간 DataFrame
c.show("BS")                     # 단일 topic + source priority
c.trace("BS")                    # 어떤 source 가 선택됐나
c.show("companyOverview", 0)     # 특정 블록의 실제 데이터
```

미국 종목도 같은 API:

```python
us = dartlab.Company("AAPL")
us.sections
us.show("10-K::item1Business")
us.show("BS")
```

Polars DataFrame 이므로 자유 필터:

```python
import polars as pl

df = c.sections.filter(pl.col("topic") == "companyOverview")
df_text = c.sections.filter(pl.col("blockType") == "text")
df_table = c.sections.filter(pl.col("blockType") == "table")
```

편의 메서드:

```python
c.sections.periods()    # 기간 리스트
c.sections.ordered()    # 최신순 정렬
c.sections.coverage()   # topic 별 기간 커버리지 요약
```

## 호출 동작

`c.sections` 는 사용자 진입점. 각 행이 한 topic 블록, 각 열이 한 기간. 텍스트와 표는 원본 그대로 보존, 시간축에만 정렬한다.

`c.show(topic)` 는 `sections` 위에서 동작하고 source priority 를 적용한다:

1. **finance** (BS, IS, CF, CIS, SCE) — 숫자는 권위 있으므로 docs 본문보다 우선.
2. **report** — DART 정형 공시 데이터.
3. **docs** — 원본 산문 텍스트와 표.

`c.trace(topic)` 는 어떤 source 가 실제 선택됐는지 확인:
- 선택된 source (docs / finance / report).
- 기간별 데이터 커버리지.
- chapter, label 같은 메타.

기간 컬럼의 `null` 은 그 기간 데이터 없음. 0 으로 대체하지 않는다.

## 대표 반환 형태

`c.sections` DataFrame 구조:

```
chapter │ topic            │ blockType │ textNodeType │ 2025Q4 │ 2024Q4 │ 2024Q3 │ …
I       │ companyOverview  │ text      │ heading      │ "…"    │ "…"    │ "…"    │
I       │ companyOverview  │ text      │ body         │ "…"    │ "…"    │ "…"    │
I       │ companyOverview  │ table     │ null         │ "…"    │ "…"    │ null   │
II      │ businessOverview │ text      │ heading      │ "…"    │ "…"    │ "…"    │
```

### 구조 컬럼

| 컬럼 | 설명 |
|---|---|
| `chapter` | 최상위 장 번호 (I ~ XII). |
| `topic` | snakeCase 표준 식별자 (`companyOverview`, `businessOverview`, `BS`, `IS`, `CF`). |
| `blockType` | `"text"` 또는 `"table"`. |
| `blockOrder` | topic 내 블록 순서 (원문 순서 보존). |
| `textNodeType` | text 블록 sub-type — `"heading"` 또는 `"body"`. table 은 null. |
| `textLevel` | heading 깊이 (1, 2, 3, ...). body / table 은 null. |
| `textPath` | heading 의 구조 경로. |

### 기간 컬럼

`2025Q4`, `2024Q4`, `2024Q3`, ... 최신순. 사업보고서는 Q4. 각 셀 = 그 기간의 원본 payload (text 블록은 산문, table 블록은 markdown table). null = 데이터 없음.

EDGAR 도 같은 구조. topic 이름만 SEC form 규약 (`10-K::item1Business`, `10-K::item7MDA`). 재무 topic (BS, IS, CF) 은 DART 와 같은 이름.

## evidence 기준

- target (종목코드 / ticker).
- period (어느 분기/연도).
- topic (어떤 섹션).
- tableRef / valueRef / dateRef / executionRef.

## 기본 실행 순서

1. `dartlab.Company(code)` 로 회사 객체 생성.
2. `c.sections` 또는 `c.topics` 로 사용 가능한 topic 확인.
3. 분석할 topic 선택 → `c.show(topic)` 으로 본문 확인.
4. 기간 비교가 필요하면 `c.diff()` · `c.diff(topic)`.
5. source 가 의심되면 `c.trace(topic)` 으로 검증.

## 기본 검증

- 결과 DataFrame 의 행 수와 기간 컬럼 수 확인.
- null 비율이 비정상이면 `coverage()` 또는 `trace()` 로 source 점검.
- 숫자 답변은 `tableRef` / `valueRef` / `dateRef` / `executionRef` 묶어서 답변.

## 다음 단계

- [engines.company](/skills/engines.company) — Company facade 전체 메서드 카탈로그.
- [engines.company.disclosureEvent](/skills/engines.company.disclosureEvent) — 공시 이벤트 추적.
- [engines.company.usEdgarReview](/skills/engines.company.usEdgarReview) — 미국 종목 EDGAR 리뷰.
- [start.quickStart](/skills/start.quickStart) — 8 단계 walkthrough.
