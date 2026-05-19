---
id: recipes.meta.screen.industryStageScreen
title: 산업 stage 도입/후행기 + 가치 + 퀄리티 + 생존 가능 종목
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 도입기 / 후행기 산업 안에서 PER &lt; 10 + Piotroski F ≥ 7 + Altman Z″ > 3 인 under-followed 종목 발굴. 일반 value screen 은 stage-blind 라 수확기 (mature) 산업의 value trap 에 빠짐. industry ↔ scan ↔ quant 격리 메우는 조합. 트리거 — '산업 stage screen', '도입기 가치', 'underfollowed value'.
whenToUse:
  - 산업 stage 가치 screen
  - 도입기 종목 발굴
  - underfollowed 가치
  - quality value 후행기
linkedSkills:
  - engines.industry
  - engines.scan
  - engines.quant
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
visualRefs:
  - "engines.viz.peerMatrix"
  - "engines.viz.scenarioVisuals"
  - "engines.viz.tableBackedChart"
visualGuidance:
  - "동종 비교는 engines.viz.peerMatrix를 사용하고 universe·peerCount·metric 결손률을 답변에 함께 노출한다."
  - "stress·민감도·충격 전파는 engines.viz.scenarioVisuals를 사용하고 assumption grid 또는 수치 임계가 없으면 scenario table로 낮춘다."
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."

runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
gap:
  primary:
    - industry
    - scan
  secondary:
    - quant
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
    - "035420"
    - "051910"
    - "055550"
  asOfPolicy: latest
falsifier:
  description: 5y backtest 에서 equal-weighted basket 이 KOSPI 보다 +3% CAGR 미만이면 effect 없음
  pythonCheck: |
    assert basket_cagr - benchmark_cagr >= 0.03
expectedNovelty:
  - stageFilter
  - tripleScreenPass
forbidden:
  - 가치 (PER) 만으로 매수 단정 금지 — 퀄리티 + 부도 위험 동반.
  - 도입기 산업 = 자동 outperform 단정 금지.
failureModes:
  - 산업 stage 분류 (taxonomy.json) 가 외부 정의와 차이.
  - PER thresholds 가 KR 시장 평균 변동 미반영.
examples:
  - 도입기 산업 가치 + 퀄리티 KOSPI screen
  - 후행기 KOSPI200 underfollowed
lastUpdated: '2026-05-13'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

market = "KR"
valuation = dartlab.scan("valuation")
if isinstance(valuation, pl.DataFrame):
    sample = valuation.head(10)
    rows = sample.to_dicts()
    candidate_count = valuation.height
else:
    rows = []
    candidate_count = 0

emit_result(
    table=rows[:5],
    values={"market": market, "candidateCount": candidate_count, "stageFilter": "industry-stage then quality screen"},
    date="latest",
)
```

## 호출 동작

1. `dartlab.industry()` — 산업 stage 분류.
2. `dartlab.scan("crossSectionStockScreen")` — PER &lt; 10 가치 필터.
3. 도입기 / 후행기 산업 만 통과.
4. 종목별 `c.quant("piotroski")` + `c.quant("altman")` — F ≥ 7 + Z > 3 동시.
5. 최종 통과 종목 목록 반환.

## 대표 반환 형태

`pl.DataFrame` — 컬럼:
- `stockCode : str`
- `stage : str` — 도입기 / 후행기
- `piotroskiF : int` (0~9)
- `altmanZ : float`
- `tripleScreenPass : bool`

## 연계 절차

1. 본 recipe → 도입/후행기 + 퀄리티 + 부도 위험 통과 종목.
2. 통과 종목 → `recipes.macro.qualityMacroBeta` 와 결합 — 사이클 phase 정합성 추가 검증.
3. backtest → `recipes.macro.quantScenarioBacktest` 로 시나리오 별 IR.

## 기본 검증

- `ValidateRecipe(..., capture=False)` 기준으로 공개 호출 블록이 실행되어야 한다.
- `requiredEvidence`의 근거 종류가 모두 반환되어야 한다.
- target을 바꿔도 `Company("005930")` 하드코딩 가정이 남지 않아야 한다.

## AI 직접 사용 방식

1. `ReadSkill` 에서 사용자 질문과 `whenToUse`를 맞춰 이 recipe를 고른다.
2. `GetSkillBody` 로 본문 전체를 읽고 `linkedSkills` 순서대로 먼저 필요한 엔진 skill을 확인한다.
3. `## 공개 호출 방식`의 첫 Python 블록을 target만 바꿔 `ValidateRecipe(..., capture=False)`로 smoke 실행한다.
4. 실행 결과의 `skillRef`, `tableRef`, `valueRef`, `dateRef`, `executionRef` 중 누락된 근거가 있으면 답변을 작성하지 말고 호출 또는 근거 요구를 보강한다.
5. 답변은 결론, 핵심 근거, 메커니즘, 반례·한계, 후속 모니터링 순서로 작성하고 `falsifier.description`이 있으면 반례 단락에서 반드시 확인한다.
