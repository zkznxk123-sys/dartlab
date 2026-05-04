---
id: engines.macro
title: Macro
kind: curated
scope: builtin
status: observed
category: engines
purpose: Macro 엔진은 경기, 정책, 유동성, 위기, 자산, 심리, 예측을 6막 구조로 읽는 시장 레벨 분석 스킬이다.
whenToUse:
  - Macro
  - macro
  - 경기 사이클
  - 금리
  - 유동성
  - 위기
  - 자산배분
  - 매크로 시나리오
  - 경기 예측
inputs:
  - axis
  - market
  - scenario
  - overrides
outputs:
  - guide DataFrame
  - macro axis dict
  - scenario/stress result
  - story handoff
capabilityRefs:
  - macro
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.story
  - engines.gather
sourceRefs:
  - dartlab://skills/engines.macro
requiredEvidence:
  - market
  - indicator
  - dateRef
  - valueRef
  - executionRef
expectedOutputs:
  - 선택한 macro axis
  - 공개 호출
  - 핵심 지표와 기준일
  - 제한/가정
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
  - 기업 단일 재무제표 질문을 macro로 처리함
  - 최신성/시장 구분 없이 금리·환율·경기 판단을 말함
  - macro 결과를 analysis 내부 값처럼 섞음
forbidden:
  - macro에서 analysis/credit을 직접 import해 결합하지 않는다.
  - 기준일 없는 매크로 숫자를 말하지 않는다.
  - 공개 API 호출법, guide 축, 반환 형태가 바뀌었는데 이 skill을 갱신하지 않은 상태로 완료 처리하지 않는다.
examples:
  - 한국 금리 환경 점검
  - 경기 사이클과 자산배분 확인
  - 2008 금융위기 시나리오 비교
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-04'
---

## 엔진 역할

`macro`는 회사가 아니라 시장/경제 환경을 읽는 L2 엔진이다. 경제 사이클, 재고, 기업집계, 교역, 금리, 유동성, 위기, 자산, 심리, 예측, 시나리오, 종합을 6막 인과 구조로 해석한다.

단일 기업 수익성/현금흐름/가치평가는 `analysis`가 담당한다. macro는 그 기업이 놓인 외부 환경을 제공하고, 보고서 조합은 `story`가 담당한다.

## 공개 호출 방식

```python
import dartlab

guide = dartlab.macro()
cycle = dartlab.macro("cycle", market="KR")
rates = dartlab.macro("금리", market="US")
scenario = dartlab.macro("시나리오", "2008 금융위기")
summary = dartlab.macro("종합", market="KR")

c = dartlab.Company("005930")
company_macro = c.macro("매크로민감도")
```

## 호출 동작

무인자 `dartlab.macro()`는 12개 axis 가이드 DataFrame을 반환한다. axis를 지정하면 기본 HF SSOT 또는 직접 API 선택 경로의 ECOS/FRED 데이터를 읽고 축별 dict/table을 만든다.

Company-bound `c.macro()`는 회사의 market을 참조해 기업 단위 민감도나 밴드 확인에 연결한다. 시장 레벨 macro 해석과 기업 내부 재무 해석은 분리한다.

## 전체 축/메서드 목록

| axis | label | group | 대표 호출 |
| --- | --- | --- | --- |
| cycle | 사이클 | 제1막: 경제는 어디에 있나 | `dartlab.macro("cycle")` |
| inventory | 재고 | 제1막: 경제는 어디에 있나 | `dartlab.macro("inventory")` |
| corporate | 기업집계 | 제2막: 왜 여기에 있나 | `dartlab.macro("corporate")` |
| trade | 교역 | 제2막: 왜 여기에 있나 | `dartlab.macro("trade", market="KR")` |
| rates | 금리 | 제3막: 정책은 뭘 하고 있나 | `dartlab.macro("rates")` |
| liquidity | 유동성 | 제4막: 금융 시스템은 괜찮나 | `dartlab.macro("liquidity")` |
| crisis | 위기 | 제4막: 금융 시스템은 괜찮나 | `dartlab.macro("crisis")` |
| assets | 자산 | 제5막: 시장은 어떻게 반응하나 | `dartlab.macro("assets")` |
| sentiment | 심리 | 제5막: 시장은 어떻게 반응하나 | `dartlab.macro("sentiment")` |
| forecast | 예측 | 제6막: 앞으로 어떻게 되나 | `dartlab.macro("forecast")` |
| scenario | 시나리오 | 제6막: 앞으로 어떻게 되나 | `dartlab.macro("scenario", "2008 금융위기")` |
| summary | 종합 | 종합 | `dartlab.macro("summary")` |

## 대표 반환 형태

```text
dartlab.macro()
-> DataFrame
   axis, label, description, example, group, apiKey
```

축 실행은 dict 또는 DataFrame 성격의 결과를 반환한다.

```text
market, latestAsOf/date, indicator, value, unit,
signal/regime, score, basis/source, assumptions, flags
```

`scenario`는 충격 이름, 역사적 비교 기간, 스트레스 변수, 예상 반응을 포함할 수 있다. `summary`는 6막 전체 점수, 주요 신호, 자산배분/전략 힌트를 포함할 수 있다.

## evidence 기준

매크로 판단에는 시장, 지표명, 값, 단위, 기준일, 출처, 실행 ref가 필요하다. 최신 데이터가 아니면 stale 가능성을 같이 말한다.

## 기본 실행 순서

1. 시장을 정한다: `KR`, `US`, 또는 `auto`.
2. 축을 모르면 `dartlab.macro()`로 guide를 확인한다.
3. axis를 실행하고 기준일과 source를 확인한다.
4. 기업 보고서에 넣을 때는 `story`에서 macro 블록으로 조합한다.

## 기본 검증

스킬은 공개 실행 문서다. `dartlab.macro()` guide 축, 공개 호출, 대표 반환 키가 바뀌면 이 파일과 관련 응용 스킬을 같은 변경에서 갱신한다.
