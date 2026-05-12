---
id: recipes.macro.sixActs
title: 경제분석 6막 진입 절차
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 종목 없이 경제분석을 시작할 때 macro 12축을 6막 인과 순서로 호출해 현재 경기 위치, 정책, 금융시스템, 시장 반응, 향후 시나리오를 한 번에 정리하는 절차. 트리거 — '경제분석 시작', '거시 전체', '매크로 6막', '경제 상황 요약'.
whenToUse:
  - 경제분석 시작
  - 매크로 전체
  - 거시 6막
  - 경기 정책 유동성 시장 종합
  - economic six acts
linkedSkills:
  - engines.macro
  - engines.macro.cycle
  - engines.macro.rates
  - engines.macro.liquidity
  - engines.macro.crisis
  - engines.macro.assets
  - engines.macro.sentiment
  - engines.macro.forecast
  - engines.macro.scenario
  - engines.macro.summary
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
  - valueRef
  - executionRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
gap:
  primary:
    - macro
    - story
testUniverse:
  market: KR
  asOfPolicy: latest
falsifier:
  description: "summary 결과가 cycle/rates/liquidity/crisis 중 2축 이상을 포함하지 못하면 6막 진입 recipe로 부적합하다."
expectedNovelty:
  - actOrder
  - macroDashboard
  - causalSummary
forbidden:
  - 모든 경제 질문에 6막을 강제하지 않는다. 사용자가 단일 축을 원하면 해당 macro 축만 호출한다.
  - 기준일 없는 수치 판단 금지.
  - summary 점수만 보고 결론 금지 — cycle/rates/liquidity/crisis의 근거를 함께 확인한다.
failureModes:
  - KR/US 시장을 섞어 기준일과 지표 단위가 어긋남.
  - 6막 순서가 아닌 단편 축 나열로 끝남.
  - scenario를 현재 상태처럼 오해함.
examples:
  - 한국 경제 지금 어디에 있나
  - 미국 매크로 전체 상황 6막으로 정리
  - 경기와 금리와 위기 신호를 한 번에 봐줘
lastUpdated: '2026-05-12'
---

## 공개 호출 방식

```python
import dartlab

market = "KR"
guide = dartlab.macro()
try:
    summary = dartlab.macro("summary", market=market)
except Exception as exc:
    summary = {"error": str(exc)}
cycle = dartlab.macro("cycle", market=market)
rates = dartlab.macro("rates", market=market)
liquidity = dartlab.macro("liquidity", market=market)
crisis = dartlab.macro("crisis", market=market)
assets = dartlab.macro("assets", market=market)
sentiment = dartlab.macro("sentiment", market=market)
forecast = dartlab.macro("forecast", market=market)

emit_result(
    table=[
        {"act": 1, "axis": "cycle", "result": cycle},
        {"act": 3, "axis": "rates", "result": rates},
        {"act": 4, "axis": "liquidity", "result": liquidity},
        {"act": 4, "axis": "crisis", "result": crisis},
        {"act": 5, "axis": "assets", "result": assets},
        {"act": 5, "axis": "sentiment", "result": sentiment},
        {"act": 6, "axis": "forecast", "result": forecast},
    ],
    values={
        "market": market,
        "overall": summary.get("overall") if isinstance(summary, dict) else None,
        "score": summary.get("score") if isinstance(summary, dict) else None,
    },
    date=summary.get("latestAsOf") if isinstance(summary, dict) else None,
)
```

## 호출 동작 — 5 단 분석 구조

본 recipe 의 답변은 시스템 프롬프트의 분석 5 단 (결론 / 근거 / 메커니즘 / 반례·한계 / 후속 모니터링) 과 매핑된다. 6 막은 *근거·메커니즘 단의 내부 구조* — 답안은 여전히 5 단으로 정리하고, 6 막은 그 안에서 macro 12 축을 *어떤 순서로* 묶을지 가이드한다.

### 1. 결론 도출

`market` 의 *현재 매크로 국면* + *정책 방향* + *시장 반응* 을 한 문장 정량 결론으로.

좋은 결론 예시:
- "KR 매크로는 후반 확장 (cycle phase=expansion / score 60), 정책금리 +25bp 인상 후 보유 (rates outlook=tight), 가계신용 138%·기업부채 KOSDAQ 평균 부채비율 95% (crisis flag=elevated), 자산가격 KOSPI PER 11.2 ×·KRX 채권 변동성 +18% (assets repricing=moderate), 향후 분기 forecast PMI 47 → 49 회복 (forecast=bottoming)."
- "US 매크로는 침체 직전 (cycle phase=late expansion / score -10), Fed 동결 + dot plot 2 회 인하 시사 (rates outlook=pivoting), ISM 47 / 신용스프레드 BBB 165bp (crisis flag=watch), assets S&P PER 22 ×·VIX 18 (assets=stretched), forecast cycle bottom T+2Q."

금지 — `summary.overall`/`summary.score` 단독 결론. 반드시 *각 막의 근거 지표 2 개 이상* 결합.

### 2. 핵심 근거 수집

`requiredEvidence: skillRef + tableRef + dateRef + valueRef + executionRef` 5 종 모두 답변에 명시.

- **skillRef**: `engines.macro.summary` (1 막 진입) + `engines.macro.{cycle,rates,liquidity,crisis,assets,sentiment,forecast}` 7 축 각각. 답변에 "skill: engines.macro.cycle 의 phase" 식 인용.
- **sourceRef**: 각 axis 의 reference 원자료 (예: 한국은행 ECOS / 국가통계청 / Fed FRED). axis result 의 `sourceUrl`·`provider` 명시.
- **tableRef**: 6 막별 (act / axis / 핵심값 / 방향) 4 컬럼 표 한 개. 답변 본체 시각화.
- **dateRef**: 각 axis 의 `asOf` (최신 관측일) — quarterly 기준 정합 권장.
- **valueRef**: `overall` · `score` + 각 axis 의 핵심 수치 (cycle.score / rates.policyRate / crisis.flag 등).
- **executionRef**: RunPython 실행 결과 id — 답변에 "ref:N" 으로 직접 인용.

도구: `EngineCall` (개별 axis 단발 호출) 또는 `RunPython` (8 축 batch + 정렬).

### 3. 메커니즘 분석 — 6 막 인과 순서

답변의 *메커니즘* 단은 다음 6 막 순서로 작성. 각 막은 *이전 막의 결과가 다음 막의 입력* 인 인과 관계.

| 막 | macro 축 | 답변 단락 내용 |
|---|---|---|
| 1. **현재 위치** | `cycle` | phase (확장/둔화/침체) + score + 최근 추세 |
| 2. **정책 환경** | `rates` (+ `summary`) | 정책금리 outlook + 시장금리 곡선 + 정책 lag |
| 3. **금융 시스템** | `liquidity` + `crisis` | M2·신용 스프레드·외환보유고 + 위기 flag |
| 4. **자산 가격** | `assets` (+ `sentiment`) | 주식·채권·외환 valuation + 심리 지표 |
| 5. **선행 시그널** | `forecast` | 향후 1~4 분기 cycle trajectory |
| 6. **시나리오** | `scenario` (선택) | tail risk 후보 — *답변 결론에는 단정 X, 조건부 만* |

mermaid graph LR 권장:
```
cycle --> rates --> liquidity --> crisis --> assets --> forecast
```

각 막 단락은 *최소 1 개 정량 인용* + *기준일 (asOf)* 필수.

### 4. 반례·한계

- **Falsifier**: `summary` 가 `cycle/rates/liquidity/crisis` 중 2 축 이상을 포함 못 하면 6 막 진입에 부적합 — 단일 axis 답변으로 fallback 하고 한계 명시.
- **시장 혼합 금지**: KR 분석 중 US 지표 (예: Fed funds rate) 단독 인용 금지. KR↔US 비교가 필요하면 *별도 컬럼* 으로 표기.
- **summary score 한계**: `overall`/`score` 가 0~100 단일 수치라 위기 신호 조기 감지에 lag. crisis flag 와 병기.
- **forecast 단정 금지**: forecast 는 *현 추세 연장* 이지 *예측* 아님. "다음 분기 X 가 일어난다" 단정 표현 X.
- **scenario 오해**: scenario 결과는 *조건부 경로*. "지금 KR 이 2008 위기다" 식 단정 금지.
- **failureModes** — KR/US 섞임 / 6 막 순서 무시 / scenario 를 현재 상태로 오해 — 답변 작성 시 self-check.

### 5. 후속 모니터링

답변 끝에 6 막별 **다음 review 시점** 표 추가:

| 막 | 축 | 다음 review | 임계값 (전환 시그널) |
|---|---|---|---|
| 1 | cycle | 분기 | phase 전환 (확장→둔화) |
| 2 | rates | 월간 (FOMC/금통위) | 정책금리 ±25bp |
| 3 | liquidity·crisis | 주간 | 신용 스프레드 +100bp |
| 4 | assets | 일간 | PER 15× / VIX 25 |
| 5 | forecast | 분기 | PMI 50 하향/상향 돌파 |

연계 절차:
- 현재 위치가 불명확하면 → `recipes.macro.historicalPositioning` (과거 위기 대비 위치)
- 신용 취약성이 핵심이면 → `recipes.credit.cycleStressMap`
- 꼬리위험 질문이면 → `recipes.macro.tailRiskScenarioScan`
- 회사 단위로 내려가면 → `recipes.macro.companyMacroPathProjection` 또는 `recipes.macro.toCompany`

재호출 트리거: "한국 경제 지금 어디 있나", "미국 매크로 전체 6 막", "경기·금리·위기 신호 한 번에".

## 대표 반환 형태

- `tableRef` — 6 막 × (axis / 핵심값 / 방향 / asOf) 표. 답변 본문 인라인.
- `valueRef` — `{market, overall, score, cyclePhase, ratesOutlook, crisisFlag, ...}`.
- `dateRef` — 각 axis asOf + summary latestAsOf (최신 관측 기준).
- `executionRef` — RunPython 실행 id (답변 인용 키).

## 연계 절차

1. 현재 위치가 불명확하면 `recipes.macro.historicalPositioning` 으로 과거 위기 대비 위치를 비교한다.
2. 신용 취약성이 핵심이면 `recipes.credit.cycleStressMap` 으로 이동한다.
3. 꼬리위험 질문이면 `recipes.macro.tailRiskScenarioScan` 으로 이동한다.
4. 회사 단위로 내려가면 `recipes.macro.companyMacroPathProjection` 또는 `recipes.macro.toCompany`.

## 기본 검증

- `summary` 와 개별 axis 의 방향이 충돌하면 충돌을 숨기지 않고 병기한다.
- KR 분석은 `market="KR"`, US 분석은 `market="US"` 를 명시한다.
- 기준일 (asOf) 이 없는 값은 판단 근거가 아니라 *보조 힌트* 로만 쓴다.
- 6 막을 *항상* 강제하지 않는다 — 사용자가 단일 축을 원하면 그 axis 만 호출.
