---
id: recipes.meta.screen.distressEarlyWarning
title: Distress Early Warning — Altman Z″<1.8 ∧ Beneish M>-1.78
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 부실 가능성 조기 경보 스크린 — Altman Z″ (manufacturing free) < 1.8 (distress zone) 동시 Beneish M-score > -1.78 (manipulation 의심) 두 강건 신호 동시 충족 종목. Altman 1968 + Beneish 1999 정통 결합. 트리거 — '부실 경보', 'distress', 'Altman Beneish', '회계 조작 의심', '신용 위험 스크린'.
whenToUse:
  - 부실 경보
  - distress early warning
  - Altman Beneish
  - 회계 조작 의심
  - 신용 위험 스크린
  - manipulation 의심
  - Z-score
  - M-score
linkedSkills:
  - engines.scan
  - engines.quant
  - engines.credit
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
  - "Altman Z × Beneish M 2 차원 산점도 — engines.viz.peerMatrix, quadrant 3 (low Z × high M) red zone."
gap:
  primary:
    - quant
    - credit
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
  description: KOSPI200 universe 에서 동시 충족 0 건 = 본 강건 신호의 baseline rate (~5-15%) 과 모순 — 데이터 수집 실패 의심.
  pythonCheck: |
    assert n_distress >= 3
expectedNovelty:
  - altmanZ
  - beneishM
  - distressZone
forbidden:
  - distress zone 진입 = 부도 예측 X (Altman 정확도 ~80% 1 년 전, 95% 2 년 전). 결과는 priority 정렬용 universe.
  - Beneish M > -1.78 = 회계 조작 *의심* 이지 확정 X — 추가 forensics 분석 강행.
  - 금융주 Altman 정의 차이 — 산업 분리 (Altman Z″ 가 manufacturing free, 그래도 금융주는 별 모델 필요).
failureModes:
  - 신규 상장 종목 (3 년 미만) Beneish lookback 부족.
  - 한국 산업 base rate 보정 미적용 (US 기반 모델 그대로 사용 시 industry false-positive).
  - 분기 보고서 reporting lag (Q4 결산 발표 ~3 월) 동안 stale.
examples:
  - KOSPI200 distress 의심 universe (분기 1 회)
  - Altman Z″ < 1.8 + Beneish M > -1.78 + Piotroski F ≤ 3 triple 강화
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

# 1. Altman Z″ (전 종목)
altman = dartlab.quant("altman", market="KR")
# → DataFrame: stockCode · zScore · zone (distress/grey/safe)

# 2. Beneish M-score
beneish = dartlab.quant("beneish", market="KR")
# → DataFrame: stockCode · mScore · manipulator (likely/unlikely)

# 3. 동시 충족 join
df = (
    altman.join(beneish, on="stockCode", how="inner")
    .filter((pl.col("zScore") < 1.8) & (pl.col("mScore") > -1.78))
    .sort("zScore")
)

emit_result(
    table=df,
    values={"n_distress": len(df)},
    date="2026-05-28",
    sources=["dartlab://quant/altman", "dartlab://quant/beneish"],
)
```

## 호출 동작

### 1. 결론 도출

부실 + 회계 조작 의심 동시 충족 universe — 위험 신호 priority 정렬용. 부도 예측 아닌 *주의 priority*.

### 2. 핵심 근거 수집

- `dartlab.quant("altman")` — 5 비율 가중 Z″ (manufacturing free 변형)
- `dartlab.quant("beneish")` — 8 비율 가중 M-score (1999 정통)

### 3. 메커니즘 분석

```
2 강건 신호 동시 충족
   Altman Z″ < 1.8  (distress zone, 1~2 년 부도 ~80% precision)
   Beneish M > -1.78 (manipulator 의심, 0.6~0.8 precision)
   ↓
inner join → red zone universe
   ↓
zScore 오름차순 정렬 (가장 위험 먼저)
   ↓
운영자 review → forensics deep dive 종목 선정
```

### 4. 반례·한계

- Altman zone 진입 ≠ 부도 확정 (정확도 80% 1 년 전).
- Beneish 는 manipulation *의심* 이지 확정 X — manipulator-likely 가 실제 manipulator 비율 ~60-80%.
- 산업 base 차이 (heavy capex 산업 Z 낮음, asset-light 산업 Z 높음).
- 금융주 별 모델 필요 (CAMELS 또는 Mohanram G-score).

### 5. 후속 모니터링

- distress universe → `recipes.fundamental.quality.forensics.deepDive` forensics 27 종 deep dive.
- accruals 추가 → `recipes.fundamental.quality.forensics.accountingPolicyChange` 결합.
- credit 측 검증 → `engines.credit` dCR rating + `recipes.fundamental.credit.distressCandidateScreen` triple.

## 대표 반환 형태

`pl.DataFrame` — 컬럼:
- `stockCode : str` · `corpName : str`
- `zScore : float` — Altman Z″
- `zone : str` — distress / grey / safe
- `mScore : float` — Beneish M
- `manipulator : str` — likely / unlikely
- `sector : str` (선택)

## 연계 절차

1. 본 recipe → distress + manipulation 의심 universe.
2. 통과 종목 → `recipes.fundamental.quality.forensics.deepDive` 또는 `recipes.fundamental.credit.distressCandidateScreen` triple.
3. 회계 forensics 추가 → `recipes.fundamental.quality.forensics.accountingPolicyChange` / `bigBathDetection` / `revenueToCashBridge`.
4. credit 측 dCR rating 결합 → `recipes.fundamental.credit.creditQuantConsensus` 4-source 합의.
5. 분기 재실행 → universe 변동 trace (악화 진행 종목 priority 상향).
