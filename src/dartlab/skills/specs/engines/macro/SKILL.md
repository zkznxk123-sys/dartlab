---
id: engines.macro
title: Macro
kind: curated
scope: builtin
status: observed
category: engines
purpose: Macro 엔진은 경기, 정책, 유동성, 위기, 자산, 심리, 예측을 6막 구조로 읽는 시장 레벨 분석 스킬이다. 트리거 — '매크로', '거시', '금리', '환율'.
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
  - 미국 유동성 측정
  - dartlab.macro 12 축 가이드
  - 매크로 종합 (한국 / 미국)
  - 기업 매크로 민감도 (c.macro)
procedure:
  - dartlab.macro() 로 12 축 가이드 DataFrame 확인.
  - axis 선택 (cycle · inventory · corporate · trade · rates · liquidity · crisis · assets · sentiment · forecast · scenario · summary).
  - dartlab.macro(axis, market="KR" 또는 "US") 호출.
  - 결과의 indicator · dateRef · valueRef · executionRef 묶음.
  - 시장 레벨 macro 와 기업 내부 재무 해석은 분리 — 회사 단위는 c.macro 또는 engines.analysis.
linkedSkills:
  - engines.macro.cycle
  - engines.macro.summary
  - engines.story
  - engines.gather
  - engines.analysis.macroSensitivity
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
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
company_macro = c.macro("사이클")                    # 시장 매크로 (KR 자동) — c.macro 의 axis 는 macro 엔진 axis
sensitivity = c.analysis("macro", "매크로민감도")   # 기업 단위 매크로 민감도는 analysis 엔진
```

## 강행 호출 룰 (agent 답변 품질 회귀 차단)

12 axis 매크로 질문 (cycle·rates·inflation·corporate·trade 등) 에서 다음 4 룰 강행.

1. **1 차 도구는 EngineCall 강제**. `EngineCall(apiRef="macro", args={"axis": "rates", "market": "KR"})` 양식. RunPython 직접 ECOS/FRED 호출 금지 — 본 엔진이 HF SSOT 캐시 + tableRef 발급 담당.
2. **본문 숫자에 `[valueRef:...]` 또는 `[dateRef:...]` inline 표기 필수**. macro 데이터는 시점 (asOf) 변동 큼 — dateRef 누락 시 stale 데이터 환각.
3. **cycle / inventory 4 phase 판정은 `[conf:30]` 기본** — 회고적 신호임을 명시. NBER vs ECRI vs Cleveland Fed 정의 차이 인지.
4. **단일 지표로 사이클 단정 금지** — CLI·LEI·yield curve 중 최소 2 종 ref 동행. 단일 지표 답변은 한계 명시 필수.

## 호출 동작

무인자 `dartlab.macro()`는 12개 axis 가이드 DataFrame을 반환한다. axis를 지정하면 기본 HF SSOT 또는 직접 API 선택 경로의 ECOS/FRED 데이터를 읽고 축별 dict/table을 만든다.

Company-bound `c.macro()`는 회사의 market을 참조해 기업 단위 민감도나 밴드 확인에 연결한다. 시장 레벨 macro 해석과 기업 내부 재무 해석은 분리한다.

## 전체 축/메서드 목록

| axis | label | group | 대표 호출 | 축-specific 회피 |
| --- | --- | --- | --- | --- |
| cycle | 사이클 | 제1막 | `dartlab.macro("cycle")` | 4 국면 자동식별 결과를 *예측* 으로 단정 X (회고적 신호); 단일 지표 (CLI) 만으로 사이클 단정 X; NBER vs ECRI vs Cleveland Fed 정의 차이 인지 |
| inventory | 재고 | 제1막 | `dartlab.macro("inventory")` | ISM 재고순환 4 phase 명시 없이 단정 X; KR 제조업에 US ISM 직접 적용 X; I/S 산업별 정상수준 차이 무시 X |
| corporate | 기업집계 | 제2막 | `dartlab.macro("corporate")` | 전종목 평균으로 개별 기업 진단 X (analysis 로 분리); Ponzi 비율 한 지표만으로 시장위험 단정 X; 대형주 5 종이 평균 좌우하는 KR 특성 반영 |
| trade | 교역 | 제2막 | `dartlab.macro("trade", market="KR")` | 교역조건 단일 지표로 무역·경상수지 단정 X; KR 수출과 US/CN LEI 시차 (3~6 개월) 명시; 반도체/자동차 수출 비중 변화 반영 |
| rates | 금리 | 제3막: 정책 | `dartlab.macro("rates")` | 정책금리 vs 시장금리 (10Y/3M) 혼동 X; 명목 vs 실질 (CPI 보정) 혼용 X; 10Y-2Y 역전을 즉시 *경기침체* 단정 X; KR-US decoupling 가능성 |
| liquidity | 유동성 | 제4막 | `dartlab.macro("liquidity")` | M2 vs M3/L 혼용 X; 연준 B/S 변동의 QE/QT 단순 인과 단정 X; NFCI 중립값 (0) vs *유동성 부족* 단순 인과 X; 정책→시장 lag |
| crisis | 위기 | 제4막 | `dartlab.macro("crisis")` | Credit-to-GDP gap 한 지표로 위기임박 단정 X (Minsky + GHS 동반); 역사적 위기 (1997/2008) 와 현 환경 제도/정책 차이 무시 X; 위기신호와 실제 발생 12~24m lag |
| assets | 자산 | 제5막 | `dartlab.macro("assets")` | 5 대 자산 (주식·채권·원자재·통화·부동산) 분류 명시; Cu/Au 비율 단일값으로 cycle 단정 X; BEI 4 분면 단순 인과 X |
| sentiment | 심리 | 제5막 | `dartlab.macro("sentiment")` | VIX 단일값으로 *공포* 단정 X (15-/15-25/25+ 구간); 시장 vs 회사별 sentiment 혼동 X; VIX 와 JLN 동치 처리 X |
| forecast | 예측 | 제6막 | `dartlab.macro("forecast")` | 침체확률 한 모델 (Cleveland Fed) 단독 인용 X (Sahm/GaR 교차); LEI/Sahm 미국 지표 KR 직접 적용 X (KR composite leading 분리); GaR 분포 신뢰구간 명시 |
| scenario | 시나리오 | 제6막 | `dartlab.macro("scenario", "2008 금융위기")` | preset (146 종 — 1997 IMF, 2008 GFC, Fed DFAST) 그대로 인용; 임의 가정은 답변 한계로 표기; analysis("macro","매크로민감도") 와 결합해 정량 임팩트 |
| summary | 종합 | 종합 | `dartlab.macro("summary")` | 6 막 점수 + 주요 신호 + 자산배분 힌트 형태; 단일 axis 결과만으로 summary 추정 X |
| marketReview | 시장 회고 | 제5막 | `dartlab.macro("marketReview", market="KR")` | 일별/주별 시장 변동 회고 — *예측* 으로 사용 X. 회고 + 원인 + 한계만 |

**공통 forbidden** (모든 축): 기준일/source 없는 macro 숫자 인용 X · 기업 재무 분석을 macro 로 대체 X · macro 결과를 analysis 내부 계산처럼 섞지 X.

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

## EngineCall (agent 경로) args 매핑

| `dartlab.macro(...)` | `EngineCall(apiRef="macro", args=...)` |
| --- | --- |
| `dartlab.macro()` 가이드 | `{}` (빈 dict) |
| `dartlab.macro("cycle", market="KR")` | `{"axis": "cycle", "market": "KR"}` |
| `dartlab.macro("rates", market="US")` | `{"axis": "rates", "market": "US"}` |
| `dartlab.macro("scenario", "2008 금융위기")` | `{"axis": "scenario", "target": "2008 금융위기"}` |
| `dartlab.macro("summary", market="KR")` | `{"axis": "summary", "market": "KR"}` |
| `Company("005930").macro("사이클")` | `{"stockCode": "005930", "axis": "사이클"}` (apiRef="Company.macro") |

**guard** — axis 와 market 을 점 표기로 합쳐 `apiRef="macro.rates.US"` 호출 금지. args 안에 분리.

## 기업 답변에 macro 변수 결합 시 — 정량 시나리오 권장

P4 류 질문 ("다음 분기 영업이익률 떨어질까? 어떤 조건에서 깨지나") 에서 환율·금리·메모리 가격 같은 macro 변수를 *반증조건* 으로 인용할 때는:

1. **시나리오 호출** — `dartlab.macro("scenario", "USD-KRW 5% 강세")` 또는 사전 정의된 preset (`"2008 금융위기"`, `"COVID 충격"` 등). 임의 가정은 답변 한계로 표기.
2. **민감도 결합** — `c.analysis("macro", "매크로민감도")` 가 기업 단위 매출/영업이익 탄력성 (예: `매출 elasticity vs WonDollar = 0.3`) 반환. 시장 시나리오 × 기업 elasticity = 정량 임팩트.
3. **최소 시나리오 명시 X 답변 금지** — "환율이 우호적이면 마진 방어" 같은 일반론은 evidence 0 으로 GATE 차단 대상. 시나리오 호출 0 회 가능하지만 반증조건은 변수명 + 임계값 + 방향 셋 다 명시.

## 기본 실행 순서

1. 시장을 정한다: `KR`, `US`, 또는 `auto`.
2. 축을 모르면 `dartlab.macro()`로 guide를 확인한다.
3. axis를 실행하고 기준일과 source를 확인한다.
4. 기업 보고서에 넣을 때는 `story`에서 macro 블록으로 조합한다.

## 기본 검증

스킬은 공개 실행 문서다. `dartlab.macro()` guide 축, 공개 호출, 대표 반환 키가 바뀌면 이 파일과 관련 응용 스킬을 같은 변경에서 갱신한다.
