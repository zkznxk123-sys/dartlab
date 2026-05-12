---
id: recipes.screen.industryStageScreen
title: 산업 stage 도입/후행기 + 가치 + 퀄리티 + 생존 가능 종목
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 도입기 / 후행기 산업 안에서 PER < 10 + Piotroski F ≥ 7 + Altman Z″ > 3 인 under-followed 종목 발굴. 일반 value screen 은 stage-blind 라 수확기 (mature) 산업의 value trap 에 빠짐. industry ↔ scan ↔ quant 격리 메우는 조합. 트리거 — '산업 stage screen', '도입기 가치', 'underfollowed value'.
whenToUse:
  - 산업 stage 가치 screen
  - 도입기 종목 발굴
  - underfollowed 가치
  - quality value 후행기
linkedSkills:
  - engines.industry
  - engines.scan.crossSectionStockScreen
  - engines.quant.piotroski
  - engines.quant.altman
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
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
lastUpdated: '2026-05-10'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

# 1. 산업 stage 분류 (taxonomy)
taxonomy = dartlab.industry().get("taxonomy") if hasattr(dartlab, "industry") else {}
target_stages = ["도입기", "후행기"]

# 2. KOSPI universe + crossSectionStockScreen — 가치 1 차 필터 (PER < 10)
universe = dartlab.scan("crossSectionStockScreen", market="KR", filters={"per_lt": 10})
if isinstance(universe, pl.DataFrame):
    candidates = universe
elif isinstance(universe, list):
    candidates = pl.DataFrame(universe)
else:
    candidates = pl.DataFrame()

# 3. 산업 stage 매핑 후 도입/후행기 만 통과
def stage_of(stock_code):
    return taxonomy.get(stock_code, {}).get("stage", "unknown")

if "stockCode" in candidates.columns:
    candidates = candidates.with_columns(
        pl.col("stockCode").map_elements(stage_of, return_dtype=pl.Utf8).alias("stage")
    ).filter(pl.col("stage").is_in(target_stages))

# 4. Piotroski F ≥ 7 + Altman Z″ > 3 — 종목별 수치 fetch
final_rows = []
for stock_code in candidates["stockCode"].to_list()[:30] if "stockCode" in candidates.columns else []:
    try:
        co = dartlab.Company(stock_code)
        piotroski = co.quant("piotroski")
        altman = co.quant("altman")
        f_score = piotroski.get("score", 0) if isinstance(piotroski, dict) else 0
        z_score = altman.get("zScore", 0) if isinstance(altman, dict) else 0
        if f_score >= 7 and z_score > 3:
            final_rows.append({
                "stockCode": stock_code,
                "stage": stage_of(stock_code),
                "piotroskiF": f_score,
                "altmanZ": round(z_score, 2),
                "tripleScreenPass": True,
            })
    except Exception:
        continue

emit_result(
    table=final_rows,
    values={"passCount": len(final_rows)},
    date="2024-12-31",
)
```

## 호출 동작

1. `dartlab.industry()` — 산업 stage 분류.
2. `dartlab.scan("crossSectionStockScreen")` — PER < 10 가치 필터.
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
3. backtest → `recipes.macro.macroQuantScenarioBacktest` 로 시나리오 별 IR.
