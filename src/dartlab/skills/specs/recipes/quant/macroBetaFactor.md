---
id: recipes.quant.macroBetaFactor
title: 매크로 beta 팩터 cross-section
category: recipes
kind: recipe
scope: builtin
status: curated
graphTier: L1.5
cluster: quant
purpose: KOSPI 200 universe 에서 종목별 매크로 beta (금리·환율·유가 등) 의 cross-section 분포를 측정. quartile 분포 + 자기 종목 위치 표면화. 추론 라벨 없이 ranking 정량만. 트리거 — '매크로 beta 팩터 cross-section', 'macro beta factor', 'macroBetaFactor'.
whenToUse:
  - 매크로 beta 팩터
  - macroBeta cross-section
  - rate / FX / oil beta
  - factor exposure
examples:
  - 005930 금리 beta + 환율 beta cross-section
  - 매크로 beta 가장 높은 종목 — 유가 / 환율 / 금리
  - KOSPI 200 안 매크로 beta 분포
expectedOutputs:
  - 매크로 요인별 beta (금리·환율·유가) 단일값 + quartile 위치
  - universe quartile 경계값 + 자기 종목 percentile
  - 매크로 beta 상위 / 하위 5 종목 list
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
validatedAt: '2026-05-27'
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

### 1. 결론 도출

macroBeta cross-section percentile + quartile 단정. 예: "macroBeta 1.42, universe percentile 0.78 (Q1 = top 25%) — 매크로 충격 민감도 상위 분위 (Beta 큰 종목)."

### 2. 핵심 근거 수집

- scan('macroBeta') cross-section row (KOSPI 200 universe)
- 종목별 macroBeta 점수 (금리·환율·유가 등 매크로 요인 회귀계수)
- universe 분포 q1/median/q3 분위수

### 3. 메커니즘 분석

```
scan('macroBeta') → universe N 종목의 macroBeta 점수
   ↓
정렬 → q1 / median / q3 cut 계산
   ↓
target 종목 위치 percentile = (own > peer 카운트) / universe_size
   ↓
percentile ≥ 0.75  → Q1 (top quartile, 매크로 충격 민감도 큼)
0.25-0.75          → mid
percentile < 0.25  → Q4 (bottom quartile, 매크로 충격 둔감)
```

macroBeta 큰 종목 = 매크로 환경 변화 (금리·환율) 에 가격 변동 큰 회사 (시클리컬). 작은 종목 = defensive (필수소비재·유틸 등).

### 4. 반례·한계

- macroBeta 추정 회귀 기간 (lookback) 따라 값 변동.
- 시장 전체 충격 (COVID 2020) 데이터 포함 시 모든 종목 beta 부풀려짐.
- 신규 상장 (history 부족) macroBeta 산출 불가.
- 단일 macroBeta 값으로 매수/매도 단정 금지 — 시나리오 결합 필요.

### 5. 후속 모니터링

- Q1 macroBeta (top 분위) 종목: `recipes.macro.qualityMacroBeta` 로 macro elasticity 사례별 추적.
- macroBeta 급변 (분기별 ±0.5): 산업 사이클 phase 변화 의심 — `recipes.industry.industryStagePhase` 확인.
- 매크로 충격 시나리오: `recipes.macro.scenarioDiagram` 으로 종목별 영향 정량.

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
