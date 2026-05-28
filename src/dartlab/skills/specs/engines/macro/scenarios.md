---
id: engines.macro.scenarios
title: Macro — 시나리오 카탈로그 (scenarios)
category: engines
kind: curated
scope: builtin
status: observed
purpose: 매크로 시나리오 카탈로그 SSOT — 역사 시나리오 (1997 외환위기 · 2008 금융위기 · 2020 팬데믹) + 가설 시나리오 (금리 +200bp / USD/KRW +10% / 유가 +50%) 단일 enum + scenario axis 의 override 인자 표준 schema. recipes.macro.* 가 본 enum 인용.
whenToUse:
  - 시나리오
  - scenario
  - 매크로 시나리오
  - 1997 외환위기
  - 2008 금융위기
  - 2020 팬데믹
  - stress test
  - 금리 +200bp
  - 시나리오 backtest
sourceRefs:
  - dartlab://skills/engines.macro.scenarios
capabilityRefs:
  - macro
knowledgeRefs:
  - engines.macro
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
linkedSkills:
  - engines.macro
  - engines.macro.regimes
  - engines.quant
---

## 엔진 역할

`macro` 엔진의 *시나리오 카탈로그* SSOT sub-spec. base SKILL `engines.macro` 의 12 axis 중 `scenario` axis 의 override 인자 표준 schema + 역사·가설 시나리오 enum 단일 정의. recipes.macro.quantScenarioBacktest / companyMacroPathProjection / credit covenantStressTest 등이 본 enum 그대로 인용.

## 공개 호출 방식

```python
import dartlab

# 1. 역사 시나리오
result = dartlab.macro("scenario", scenario="crisis_2008")
# → 2008 시나리오 적용 결과 (자산·금리·환율 path)

# 2. 가설 시나리오 (override)
result = dartlab.macro("scenario", overrides={
    "rates_us10y": "+200bp",
    "usdkrw": "+10%",
    "oil_wti": "+50%"
})

# 3. 시나리오 가이드
dartlab.macro("scenario")
# → 등록된 시나리오 enum + 정의 표
```

## 호출 동작

`dartlab.macro("scenario", scenario=<id>)` — 역사 시나리오 enum hit 시 해당 사건의 자산·금리·환율 path 적용. `overrides=` 명시 시 가설 시나리오 — 본 sub-spec 의 schema 따름.

scenario + overrides 동시 사용 가능 — override 가 scenario 의 일부 path 만 교체.

## 역사 시나리오 enum

| id | 사건 | 기간 | 핵심 path |
|---|---|---|---|
| **crisis_1997** | 한국 외환위기 (IMF) | 1997-11 ~ 1998-12 | KRW -50% · 금리 +1500bp · KOSPI -65% |
| **crisis_2000** | 닷컴 버블 붕괴 | 2000-03 ~ 2002-10 | 나스닥 -78% · KOSPI -50% |
| **crisis_2008** | 글로벌 금융위기 | 2008-09 ~ 2009-03 | S&P -55% · KOSPI -52% · 신용스프레드 +600bp |
| **shock_2011** | 유럽 재정위기 | 2011-08 ~ 2011-10 | KOSPI -25% · 신용스프레드 +200bp |
| **crash_2018** | 미중 무역분쟁 | 2018-10 ~ 2018-12 | KOSPI -18% · 신흥국 통화 -10% |
| **pandemic_2020** | COVID-19 충격 | 2020-02 ~ 2020-03 | KOSPI -34% · VKOSPI +50% · 유가 -65% |
| **inflation_2022** | 글로벌 인플레이션 | 2022-01 ~ 2022-12 | 금리 +425bp · 채권 -15% · 주식 -25% |

각 시나리오는 monthly path (자산·금리·환율 시계열) 으로 저장. dartlab.macro("scenario", scenario=...) 가 해당 path 직접 노출.

## 가설 시나리오 schema (overrides)

```python
overrides = {
    # 금리 (절대 변동, bp)
    "rates_us10y": "+200bp",          # 미 10년물 +200bp
    "rates_kgb10y": "+100bp",         # 한국 국고 10년물 +100bp
    "rates_kr_base": "+75bp",         # 한국 기준금리

    # 환율 (상대 변동, %)
    "usdkrw": "+10%",                 # 원/달러 절하
    "usdjpy": "-5%",                  # 엔/달러 절상

    # 원자재 (상대 변동, %)
    "oil_wti": "+50%",                # WTI
    "copper": "-20%",                 # 구리

    # 주가지수 (상대 변동, %)
    "kospi": "-15%",
    "sp500": "-10%",

    # 신용스프레드 (절대 변동, bp)
    "spread_corp_aaa": "+50bp",
    "spread_corp_bbb": "+150bp",
}
```

- 절대 변동 = `+/-Nbp` (금리·스프레드)
- 상대 변동 = `+/-N%` (환율·원자재·주가)
- 단위 명시 strict — 단위 누락 시 ValueError.

## 대표 반환 형태

```text
dartlab.macro("scenario", scenario="crisis_2008")
→ dict
   scenarioId : str           # "crisis_2008"
   scenarioName : str         # "글로벌 금융위기"
   period : tuple[str, str]   # ("2008-09", "2009-03")
   paths : dict[str, list]    # {"kospi": [-15%, -28%, ...], "rates_us10y": [...], ...}
   regime : str               # "crisis" (engines.macro.regimes SSOT)
   dateRef : str
```

```text
dartlab.macro("scenario", overrides={...})
→ dict
   scenarioId : str           # "custom_<hash>"
   overrides : dict           # 입력 그대로
   paths : dict               # 적용 결과
   regime : str               # 추정 regime
```

## 기본 실행 순서

1. **역사 시나리오 비교** — enum id 명시 호출.
2. **가설 시나리오 stress test** — overrides schema 따라 절대/상대 변동 명시.
3. **결합 시나리오** — scenario + overrides 동시 (override 가 scenario path 일부 교체).
4. **recipe 인용** — `recipes.macro.quantScenarioBacktest` 등이 본 enum 그대로 사용.

## 기본 검증

- scenario enum 값이 7 종 안.
- overrides 모든 key 가 schema 표 안.
- 절대 변동 (bp) / 상대 변동 (%) 단위 명시.
- 결과 paths 의 시계열 길이 ≥ 1.
- regime 분류가 `engines.macro.regimes` 5 enum 안.

본 spec 은 공개 실행 문서다. scenario enum 또는 overrides schema 가 변경되면 본 파일을 같은 변경에서 갱신한다.

## 관련

- [engines.macro](/skills/engines.macro) — base SKILL
- [engines.macro.regimes](/skills/engines.macro.regimes) — scenario 결과의 regime 분류 SSOT
- [recipes.macro.quantScenarioBacktest](/skills/recipes.macro.quantScenarioBacktest) — scenario × quant walk-forward
- [recipes.macro.companyMacroPathProjection](/skills/recipes.macro.companyMacroPathProjection) — 146 시나리오 × elasticity
