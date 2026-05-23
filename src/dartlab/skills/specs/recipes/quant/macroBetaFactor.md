---
id: recipes.quant.macroBetaFactor
title: 매크로 beta 팩터 cross-section
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: quant
purpose: KOSPI 200 universe 에서 종목별 매크로 beta (금리·환율·유가 등) 의 cross-section 분포를 측정. quartile 분포 + 자기 종목 위치 표면화. 추론 라벨 없이 ranking 정량만.
whenToUse:
  - 매크로 beta 팩터
  - macroBeta cross-section
  - rate / FX / oil beta
  - factor exposure
linkedSkills:
  - engines.scan
  - recipes.macro.qualityMacroBeta
  - recipes.macro.betaPeerScreen
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
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
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
expectedNovelty:
  - macroBetaRankTable
  - quartileDistribution
falsifier:
  description: "scan('macroBeta') row 수 < 100 이면 quartile 신뢰도 낮음 — 결론 X. 단일 시점 베타를 *시간 안정* 으로 단정하면 실패."
forbidden:
  - macroBeta 단일 측정값을 자산배분 결정으로 단정 금지
  - 한 시점 베타를 다른 시점 베타로 일반화 금지
failureModes:
  - scan row 수 부족 (universe 작음)
  - 시기 따라 beta 부호 자체가 변하는 종목 (regime dependent)
  - rate / FX / oil 베타 가중치 명시 안 한 단일 점수
lastUpdated: '2026-05-23'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"


def floatOr(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


try:
    df = dartlab.scan("macroBeta", market="KR")
    if isinstance(df, pl.DataFrame):
        rows = df.to_dicts()
    else:
        rows = list(df) if hasattr(df, "__iter__") else []
except Exception:
    rows = []

# beta 점수 컬럼 후보 — 환경 따라 column 이름이 다를 수 있어 fallback 다층.
def betaScore(r):
    for k in ("macroBeta", "betaScore", "compositeBeta", "score", "macroExposure"):
        v = r.get(k)
        if v is not None:
            f = floatOr(v)
            if f is not None:
                return f
    return None


scored = []
for r in rows:
    sc = betaScore(r)
    if sc is None:
        continue
    scored.append(
        {
            "stockCode": str(r.get("stockCode") or r.get("code") or r.get("symbol") or ""),
            "score": sc,
        }
    )

scored.sort(key=lambda r: r["score"])
n = len(scored)

if n >= 4:
    q1_cut = scored[n // 4]["score"]
    q3_cut = scored[(3 * n) // 4]["score"]
    median = scored[n // 2]["score"]
else:
    q1_cut = q3_cut = median = None

target_score = next((r["score"] for r in scored if r["stockCode"] == target), None)
target_rank = next((i for i, r in enumerate(scored) if r["stockCode"] == target), None)
target_pct = (target_rank / n) if (target_rank is not None and n > 0) else None

table = pl.DataFrame(
    [
        {
            "universeSize": n,
            "median": median,
            "q1Cut": q1_cut,
            "q3Cut": q3_cut,
            "targetCode": target,
            "targetScore": target_score,
            "targetPercentile": (round(target_pct * 100, 1) if target_pct is not None else None),
        }
    ]
)

emit_result(
    table=table,
    values={
        "universeSize": n,
        "targetScore": target_score,
        "targetPercentile": (round(target_pct * 100, 1) if target_pct is not None else None),
        "median": median,
    },
    date="latest",
    sources=["dartlab://scan/macroBeta"],
)
```

## 호출 동작

`scan('macroBeta')` cross-section row 에서 macroBeta 점수 컬럼 추출 → 정렬 → q1/median/q3 cut 계산 → target 종목 percentile 위치 표면화. 추론 X.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `universeSize` | scan row 수 |
| `median` | 중위 macroBeta |
| `q1Cut` / `q3Cut` | 25 / 75 percentile 컷 |
| `targetScore` | target 종목 macroBeta |
| `targetPercentile` | target percentile (0 ~ 100) |

## 연계 절차

1. recipes.macro.qualityMacroBeta — quality decile × cycle phase 와 결합.
2. recipes.macro.betaPeerScreen — peer 대비 outlier 판정.

## 기본 검증

- universeSize < 100 → quartile 신뢰도 낮음, 한계 표기.
- macroBeta 부호 자체가 시기 따라 변할 수 있음 — 시기 명시 권장.
- target 종목이 universe 에 없으면 (`targetScore=None`) 한계 표기.
