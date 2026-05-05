---
id: engines.analysis
title: Analysis
kind: curated
scope: builtin
status: observed
category: engines
purpose: Analysis 엔진은 단일 기업의 재무제표, 가치평가, 지배구조, 전망, 기업 단위 매크로 민감도를 22개 분석 축으로 읽는 실행 스킬이다.
whenToUse:
  - Analysis
  - analysis
  - 기업 재무제표 분석
  - 수익구조
  - 자금조달
  - 자산구조
  - 현금흐름
  - 수익성
  - 성장성
  - 안정성
  - 효율성
  - 종합평가
  - 이익품질
  - 비용구조
  - 자본배분
  - 투자효율
  - 재무정합성
  - 가치평가
  - 지배구조
  - 공시변화
  - 비교분석
  - 매출전망
  - 예측신호
  - 매크로민감도
  - 밸류에이션밴드
inputs:
  - Company 객체 또는 종목코드
  - group 또는 axis
  - 세부 분석 축
  - 기준 기간
  - 비교/가정/오버라이드
outputs:
  - 분석 축 가이드 DataFrame
  - 계산 항목 가이드 DataFrame
  - 축별 분석 dict
  - tableRef/valueRef/dateRef/executionRef
  - story/report handoff
capabilityRefs:
  - analysis
  - Company.analysis
  - Company.show
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.company
  - engines.data.foundation
  - engines.story
sourceRefs:
  - dartlab://skills/engines.analysis
requiredEvidence:
  - target
  - period
  - metric
  - tableRef
  - valueRef
  - dateRef
  - executionRef
expectedOutputs:
  - 선택한 분석 축
  - 실제 공개 호출
  - 대표 반환 형태
  - 검증한 근거와 제한
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
    notes:
      - 실제 실행 가능 여부는 연결된 Company 데이터 snapshot과 capability 지원 범위를 따른다.
failureModes:
  - axis 가이드를 확인하지 않고 과거 스킬명이나 삭제된 문서 경로로 이동함
  - 결손값을 0으로 대체해 수익성/현금흐름/안정성 판단을 왜곡함
  - analysis 안에서 credit/macro 같은 L2 엔진 결과를 직접 import해 결합함
  - 스킬의 공개 호출 방식과 실제 공개 API가 어긋난 상태로 방치함
forbidden:
  - 근거 없는 숫자를 만들지 않는다.
  - 결손값을 0으로 대체하지 않는다.
  - analysis 엔진에서 credit, macro, scan, story 같은 L2 엔진을 직접 import하지 않는다.
  - 시장 레벨 매크로 해석을 analysis가 담당한다고 설명하지 않는다.
  - 공개 API 호출법, 반환 형태, 오류/제한 동작이 바뀌었는데 이 skill을 갱신하지 않은 상태로 완료 처리하지 않는다.
examples:
  - 삼성전자 수익성 분석
  - 기업 현금흐름과 이익품질 점검
  - 가치평가 축으로 적정가 범위 확인
  - 매출전망과 예측신호 확인
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-04'
---

## 엔진 역할

`analysis`는 단일 기업을 재무제표의 인과 구조로 읽는 L2 엔진이다. 이 엔진은 매출과 비용, 자산과 부채, 현금흐름, 수익성, 성장성, 안정성, 효율성, 가치평가, 지배구조, 전망 신호를 축별로 계산하고 해석한다.

담당하는 질문은 "이 회사는 무엇으로 돈을 벌고, 그 돈은 진짜 현금으로 남고, 그 성장은 지속 가능하며, 지금 가격은 어느 정도인가"이다. 시장 전체 매크로 전망은 `engines.macro`, 신용등급/부도위험 중심 평가는 `engines.credit`, 여러 종목을 찾는 작업은 `engines.scan`, 최종 보고서 조합은 `engines.story`가 담당한다.

## 공개 호출 방식

기본 호출은 `Company.analysis()`이다. 축을 모르면 먼저 가이드를 보고, 축을 알면 group과 axis를 지정한다.

```python
import dartlab

c = dartlab.Company("005930")

# 1. 전체 분석 축 가이드
guide = c.analysis()

# 2. 그룹 가이드 또는 그룹 내 계산 항목 확인
financial = c.analysis("financial")

# 3. 특정 분석 축 실행
profitability = c.analysis("financial", "수익성")
cashflow = c.analysis("financial", "현금흐름")
valuation = c.analysis("valuation", "가치평가")
forecast = c.analysis("forecast", "매출전망")

# 4. 축 이름만으로 실행 가능한 경우
profitability = c.analysis("수익성")

# 5. 모듈 함수형 호출
profitability = dartlab.analysis("financial", "수익성", c)
valuation = dartlab.analysis("valuation", "가치평가", c)
```

노트북이나 MCP에서 사람이 따라 할 때도 같은 순서로 쓴다. 먼저 `c.analysis()`로 가능한 축을 확인하고, 그 다음 실제 축을 호출한다.

## 호출 동작

`axis`가 없으면 실행 가능한 분석 축 가이드 DataFrame을 반환한다. 이 가이드는 사람이 어떤 축을 골라야 하는지 보여주는 공개 메뉴다.

`group`만 주면 해당 그룹의 축 또는 계산 항목 가이드를 반환한다. 회사 객체가 없는 함수형 호출에서는 계산 목록을 탐색하는 용도로 쓰이고, 회사 객체가 있는 호출에서는 해당 회사 기준으로 축 실행을 준비한다.

`group`과 `axis`가 함께 있거나 축 이름만 들어오면 해당 축을 실행한다. 엔진은 `Company`가 가진 재무제표, 시계열, 공시/시장 데이터 snapshot, 내부 계산 registry를 읽고 축별 계산을 수행한다.

데이터가 충분하면 축별 분석 dict를 반환한다. 데이터가 부족하면 결손을 0으로 채우지 않고, `flags`, `assumptions`, `dataAsOf`, 빈 history, null 값, 제한 메시지 등으로 표현한다. 호출한 group 또는 axis가 없으면 사용 가능한 group/axis를 확인할 수 있는 오류를 낸다.

`analysis`는 같은 L2 엔진인 `credit`, `macro`, `scan`, `story`를 내부에서 import해 조합하지 않는다. 필요한 원천 데이터는 `Company`/core 계층에서 직접 읽고, 최종 조합은 `story`가 한다.

## 분석 축 전체

| group | axis | 담당 질문 | 대표 호출 | items |
| --- | --- | --- | --- | --- |
| financial | 수익구조 | 이 회사는 무엇으로 돈을 버는가 | `c.analysis("financial", "수익구조")` | 8 |
| financial | 자금조달 | 돈을 어디서 조달하는가 | `c.analysis("financial", "자금조달")` | 9 |
| financial | 자산구조 | 조달한 돈으로 뭘 준비했는가 | `c.analysis("financial", "자산구조")` | 4 |
| financial | 현금흐름 | 실제로 현금은 어떻게 흘렀는가 | `c.analysis("financial", "현금흐름")` | 4 |
| financial | 수익성 | 이 회사는 얼마나 잘 벌고 있는가 | `c.analysis("financial", "수익성")` | 6 |
| financial | 성장성 | 이 회사는 얼마나 빨리 성장하는가 | `c.analysis("financial", "성장성")` | 5 |
| financial | 안정성 | 이 회사는 망하지 않는가 | `c.analysis("financial", "안정성")` | 6 |
| financial | 효율성 | 이 회사는 자산을 잘 굴리는가 | `c.analysis("financial", "효율성")` | 2 |
| financial | 종합평가 | 재무 상태를 한마디로 본다 | `c.analysis("financial", "종합평가")` | 3 |
| financial | 이익품질 | 이익이 진짜인가 | `c.analysis("financial", "이익품질")` | 7 |
| financial | 비용구조 | 비용이 어떻게 움직이는가 | `c.analysis("financial", "비용구조")` | 5 |
| financial | 자본배분 | 번 돈을 어디에 쓰는가 | `c.analysis("financial", "자본배분")` | 7 |
| financial | 투자효율 | 투자가 가치를 만드는가 | `c.analysis("financial", "투자효율")` | 5 |
| financial | 재무정합성 | 재무제표가 서로 맞는가 | `c.analysis("financial", "재무정합성")` | 6 |
| valuation | 가치평가 | 이 회사의 적정 가치는 얼마인가 | `c.analysis("valuation", "가치평가")` | 14 |
| governance | 지배구조 | 이 회사의 주인은 누구이며 감시는 작동하는가 | `c.analysis("governance", "지배구조")` | 8 |
| governance | 공시변화 | 이 회사의 공시가 뭐가 달라졌는가 | `c.analysis("governance", "공시변화")` | 4 |
| governance | 비교분석 | 이 회사는 시장에서 어디에 서 있는가 | `c.analysis("governance", "비교분석")` | 3 |
| forecast | 매출전망 | 이 회사의 매출은 어디로 가며 재무는 어떻게 변하는가 | `c.analysis("forecast", "매출전망")` | 8 |
| forecast | 예측신호 | 이 회사의 실적은 어디로 향하는가 | `c.analysis("forecast", "예측신호")` | 15 |
| macro | 매크로민감도 | 이 회사의 매출은 어떤 매크로 변수에 민감한가 | `c.analysis("macro", "매크로민감도")` | 1 |
| macro | 밸류에이션밴드 | PER/PBR이 과거 대비 어디에 있는가 | `c.analysis("macro", "밸류에이션밴드")` | 1 |

## 대표 반환 형태

전체 가이드 호출은 DataFrame을 반환한다.

```text
c.analysis()
-> DataFrame
   axis, description, example, group, items, apiKey
```

특정 축 실행은 dict를 반환한다. 공통적으로 다음 계열을 확인한다.

```text
c.analysis("financial", "수익성")
-> dict
   items: 축별 계산 항목과 결과
   history: 기간별 핵심 값
   displayHints: 표/차트 표시 힌트
   turningPoints: 변곡점 또는 변화 감지 결과
   dataAsOf: 데이터 기준일과 snapshot 정보
   assumptions: 계산 가정과 제한
   flags: 결손, 이상치, 비교 불가, 제한 상태
   _summary: 사람이 읽을 요약
   tableRef/valueRef/dateRef/executionRef: 근거 연결용 참조
```

축별 dict에는 공통 키 외에 전용 블록이 붙을 수 있다. 예를 들어 수익성은 매출총이익률, 영업이익률, 순이익률, ROE/ROA 흐름을 포함하고, 현금흐름은 영업/투자/재무 현금흐름과 잉여현금흐름을 포함한다. 안정성은 부채비율, 유동성, 이자보상 성격의 지표를 포함한다.

가치평가 축은 `valuationSummary`, `targetPrice`, `relativeValue`, `dcf`, `ddm`, `rim`, `sensitivity`, `valuationFlags` 같은 블록을 반환할 수 있다. 매출전망/예측신호 축은 `forecastRevenue`, `scenario`, `signal`, `forecastFlags` 같은 전망 관련 블록을 반환할 수 있다.

단위는 원천 데이터와 계산 항목의 성격을 따른다. 금액은 원천 table의 통화/단위를 보존하고, 비율은 percent 또는 ratio 여부를 명확히 표시해야 한다. 스킬에 적힌 대표 키와 실제 공개 API가 충돌하면 스킬이 오래된 것이므로 같은 변경에서 갱신한다.

## 축 선택 규칙

수익구조, 비용구조, 이익품질, 현금흐름처럼 재무제표 안에서 인과를 읽는 질문은 `financial` 그룹을 쓴다.

적정가, 멀티플, DCF/DDM/RIM, 목표가 범위는 `valuation` 그룹을 쓴다. 단, 가치평가 결과를 말할 때는 수익성, 성장성, 현금흐름, 자본배분의 근거를 같이 확인한다.

주주, 이사회, 공시 변화, 동종 비교는 `governance` 그룹을 쓴다. 업종 전체 구조 분석은 `engines.industry`, 보고서 문장 조합은 `engines.story`로 넘긴다.

매출 전망과 실적 방향은 `forecast` 그룹을 쓴다. 시장 전체 금리/환율/물가 전망은 `engines.macro`가 담당하고, analysis의 `macro` 그룹은 기업 단위 민감도와 밴드 확인에 한정한다.

여러 종목을 조건으로 찾는 일은 `analysis`가 아니라 `engines.scan`이 담당한다. scan으로 후보를 찾고, 각 후보를 `analysis`로 깊게 읽는다.

## 기본 실행 순서

1. 대상 기업을 확정한다: `c = dartlab.Company("005930")`.
2. 축이 불명확하면 `c.analysis()`로 전체 가이드를 확인한다.
3. 질문 성격에 맞는 group/axis를 고른다.
4. 실제 축을 호출한다: `c.analysis("financial", "수익성")`.
5. `history`, `items`, `flags`, `assumptions`, `dataAsOf`를 먼저 확인한다.
6. 숫자를 말할 때 `tableRef`, `valueRef`, `dateRef`, `executionRef`를 연결한다.
7. 여러 축을 보고서로 엮을 때는 `story`가 조합한다.

## 기본 검증

분석 결과는 최소한 대상, 기간, 지표명, 값, 단위, 기준일을 함께 확인한다. 기간 비교가 필요한 축은 전년동기, 전기, 최근 3년/5년 흐름 중 어떤 기준을 썼는지 밝혀야 한다.

결손값, 음수 전환, 회계 기준 변경, 사업 분할/합병, 상장 기간 부족, 데이터 snapshot 제한은 정상 값처럼 포장하지 않는다. 계산이 제한되면 `flags`와 `assumptions`를 결과의 일부로 취급한다.

스킬은 공개 실행 문서다. `Company.analysis()` 또는 `dartlab.analysis()`의 호출 방식, 대표 반환 키, 오류/제한 동작이 바뀌면 이 파일과 관련 응용 스킬을 같은 변경에서 갱신해야 한다.
