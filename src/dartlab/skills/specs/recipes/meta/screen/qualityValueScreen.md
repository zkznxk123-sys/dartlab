---
id: recipes.meta.screen.qualityValueScreen
title: Quality × Value 동시 스크린 — Piotroski F≥7 ∧ Value z>1
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 펀더멘털 quality (Piotroski F-score ≥ 7) 와 valuation cheapness (composite Value z > 1) 동시 충족 종목 스크리닝 — "good and cheap" 단순 결합. Piotroski 2000 + Graham value 합성. 트리거 — '퀄리티 밸류', 'quality value', 'good and cheap', '저평가 우량주'.
whenToUse:
  - 퀄리티 밸류
  - quality value
  - good and cheap
  - 저평가 우량주
  - Piotroski 스크린
  - F-score
  - composite value
linkedSkills:
  - engines.scan
  - engines.quant
  - engines.company
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - executionRef
  - sourceRef
visualRefs:
  - engines.viz.tableBackedChart
  - engines.viz.peerMatrix
visualGuidance:
  - "Piotroski F × Value z 2차원 산점도는 engines.viz.peerMatrix — quadrant 4 (high F × high z) 만 강조."
  - "결과 종목 list 는 engines.viz.tableBackedChart — F-score / Value z / sector 컬럼."
gap:
  primary:
    - quant
    - scan
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
    - "035720"
    - "207940"
    - "035420"
  asOfPolicy: latest
falsifier:
  description: KOSPI200 universe 에서 동시 충족 종목 0 건 = 임계 너무 높거나 data 수집 실패 (정상 시장에서 KOSPI200 의 10~20 종목 expectable).
  pythonCheck: |
    assert 5 <= n_qualified <= 100
expectedNovelty:
  - piotroskiF
  - valueZ
  - sector
forbidden:
  - F-score ≥ 7 ≠ 절대 매수 — 본 스크린은 universe 발굴, 개별 회사 판단은 추가 분석 필수.
  - value z 계산 시 산업 중립화 미적용 — 산업 base PER 차이 무시 시 cyclical 만 통과 회귀.
  - 결과 종목 자동 매수 결정 X — `recipes.fundamental.valuation.damodaran.deepDive` 등 후속 deep dive 강행.
failureModes:
  - 신규 상장 종목 (1 년 미만) Piotroski 계산 불가 — universe 제외.
  - 금융주 Piotroski 정의 차이 (Mohanram 2005) — 산업 분리 권장.
  - value composite (PER/PBR/PSR/EV-EBITDA) weighting 차이.
examples:
  - KOSPI200 quality + value 동시 통과 종목 (분기 1 회)
  - 비금융주 한정 F≥7 + Value z > 1.5
lastUpdated: '2026-05-28'
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

# 1. Piotroski F-score (전 종목)
piotroski = dartlab.quant("piotroski", market="KR")
# → DataFrame: stockCode · score (0~9)

# 2. composite Value z (PER/PBR/PSR/earningsYield 합성)
value = dartlab.quant("value", market="KR")
# → DataFrame: stockCode · valueZ · PBR · PER · ...

# 3. 산업 매핑 (산업 중립화용)
industry_map = dartlab.industry()   # 가이드
# → 각 종목의 chainId 매핑은 Company.industry().chainId

# 4. 동시 충족 join + 산업 중립 z
df = (
    piotroski.join(value, on="stockCode", how="inner")
    .filter((pl.col("score") >= 7) & (pl.col("valueZ") > 1.0))
    .sort("score", descending=True)
)

emit_result(
    table=df,
    values={"n_qualified": len(df)},
    date="2026-05-28",
    sources=["dartlab://quant/piotroski", "dartlab://quant/value"],
)
```

## 호출 동작

### 1. 결론 도출

펀더멘털 quality + valuation cheapness 동시 충족 universe — "good and cheap" 발굴.

### 2. 핵심 근거 수집

- `dartlab.quant("piotroski")` — 9 항목 binary score (1 점 × 9)
- `dartlab.quant("value")` — composite Value z (PBR/PER/PSR/earningsYield)
- 산업 매핑 — 산업 중립화 (옵션)

### 3. 메커니즘 분석

```
2 source 동시 충족
   Piotroski F ≥ 7  (수익성/안정성/효율성 9 항목 중 7+ 통과)
   Value z > 1.0    (시장 평균 대비 1σ 저평가)
   ↓
inner join → universe 후보
   ↓
정렬: score desc → value z desc
   ↓
운영자 review → 후속 deep dive 종목 선정
```

### 4. 반례·한계

- 금융주 Piotroski 정의 차이 (Mohanram 2005 G-score 별 트랙) — 산업 분리.
- value composite weighting 차이 (산업 base PBR ↑ 산업이 일괄 통과).
- value trap 가능 (저평가 = 펀더멘털 악화 진행중) — Piotroski 보완 의도지만 lag.
- 신규 상장 1 년 미만 제외.

### 5. 후속 모니터링

- 통과 종목 → `recipes.fundamental.valuation.damodaran.deepDive` 개별 deep dive.
- 산업 중립화 추가 → `recipes.meta.screen.macroRegimeAlignedScreen` 결합.
- 분기 재실행 → universe 변동 trace.

## 대표 반환 형태

`pl.DataFrame` — 컬럼:
- `stockCode : str` · `corpName : str`
- `score : int (0~9)` — Piotroski F
- `valueZ : float`
- `PBR : float` · `PER : float` · `PSR : float`
- `sector : str` (선택)

## 연계 절차

1. 본 recipe → "good and cheap" universe 발굴.
2. 통과 종목 1~5 개 → `recipes.fundamental.valuation.damodaran.fcffDcf` 또는 `recipes.fundamental.valuation.damodaran.deepDive` 개별 deep dive.
3. 산업 중립 변형 → `recipes.meta.screen.macroRegimeAlignedScreen` 결합.
4. 시계열 monitoring → 분기 1 회 본 recipe 재실행 + universe 변동 비교.
