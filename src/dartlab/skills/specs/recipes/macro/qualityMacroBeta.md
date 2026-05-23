---
id: recipes.macro.qualityMacroBeta
title: 퀄리티 (QMJ) × 매크로 사이클 — phase 의존 우량주
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: quality 팩터 (QMJ — Asness/Frazzini/Pedersen) 점수가 매크로 사이클 phase (early-recovery / mid-expansion / late-cycle / contraction) 별로 다르게 작동한다는 검증된 패턴을 단일 회사에 적용. quant ↔ macro 격리 메우는 조합. 트리거 — '퀄리티 사이클', 'QMJ 매크로', 'quality phase'.
whenToUse:
  - 퀄리티 사이클
  - QMJ 매크로
  - quality phase
  - 후행 우량주
linkedSkills:
  - engines.company
  - engines.quant
  - engines.scan
  - engines.macro
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
  - "engines.viz.scenarioVisuals"
  - "engines.viz.tableBackedChart"
  - "engines.viz.mermaidDiagram"
visualGuidance:
  - "stress·민감도·충격 전파는 engines.viz.scenarioVisuals를 사용하고 assumption grid 또는 수치 임계가 없으면 scenario table로 낮춘다."
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
  - "메커니즘 diagram은 engines.viz.mermaidDiagram으로 8노드 이하만 만들고 모든 edge에 문장·수치·sourceRef 근거를 둔다."

gap:
  primary:
    - quant
    - macro
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
  description: quality decile 1 (낮은 퀄리티) 가 early-recovery 에서 decile 10 (높은 퀄리티) 보다 outperform 하면 factor inversion
  pythonCheck: |
    assert decile10_return_in_early_recovery > decile1_return_in_early_recovery
expectedNovelty:
  - cyclePhase
  - expectedReturn
  - phaseAlignment
forbidden:
  - 단일 phase 결과만으로 일반화 금지 — 4 phase 모두 검토.
  - QMJ 점수 ≥ 80 ≠ 절대 매수 신호 — phase context 필수.
failureModes:
  - 사이클 phase 분류가 60-month rolling 등 lookback window 의존.
  - quality 측정 → ROE / 부채비율 / 매출 안정성 weighting 차이.
examples:
  - 삼성전자 QMJ + 사이클 phase
  - 현대차 quality late-cycle 적합도
lastUpdated: '2026-05-13'
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

c = dartlab.Company("005930")

# 1. QMJ quality score
qmj = c.quant("qmj")
quality_score = qmj["score"] if isinstance(qmj, dict) else 0
quality_decile = qmj.get("decile", 5) if isinstance(qmj, dict) else 5

# 2. macro cycle phase (early-recovery / mid-expansion / late-cycle / contraction)
cycle = dartlab.macro("cycle", market="KR")
phase = cycle.get("phase", "unknown") if isinstance(cycle, dict) else "unknown"

# 3. macro beta — 회사 sensitivity 60M rolling
beta = c.scan("macroBeta") if hasattr(c, "scan") else None
rate_beta = beta.get("rateBeta") if isinstance(beta, dict) else 0
fx_beta = beta.get("fxBeta") if isinstance(beta, dict) else 0

# 4. phase-quality alignment 매핑 (학술적 sweep — Frazzini-Pedersen 2014)
PHASE_QUALITY_FIT = {
    "early-recovery": "low",      # low quality outperform
    "mid-expansion": "balanced",
    "late-cycle": "high",         # quality outperform
    "contraction": "high",        # flight to quality
}
expected_winner = PHASE_QUALITY_FIT.get(phase, "balanced")
high_quality = quality_decile >= 8
phase_alignment = (
    (high_quality and expected_winner == "high")
    or (not high_quality and expected_winner == "low")
)

emit_result(
    table=[{
        "stockCode": "005930",
        "qualityScore": round(quality_score, 2),
        "qualityDecile": quality_decile,
        "cyclePhase": phase,
        "rateBeta": round(rate_beta, 3),
        "fxBeta": round(fx_beta, 3),
        "expectedWinner": expected_winner,
        "phaseAlignment": phase_alignment,
    }],
    values={"qualityDecile": quality_decile, "cyclePhase": phase, "phaseAlignment": phase_alignment},
    date="2024-12-31",
    sources=["dartlab://company/scan/quality", "dartlab://company/scan/macroBeta", "dartlab://macro/cycle"],
)
```

## 호출 동작

1. `c.quant("qmj")` — QMJ 종합 점수 + decile.
2. `dartlab.macro("cycle", market="KR")` — 현재 사이클 phase 분류.
3. `c.scan("macroBeta")` — 60M rolling rate / FX beta.
4. phase ↔ quality 적합도 매핑 (Frazzini-Pedersen 2014 학술 결과).
5. phaseAlignment True → 기대 outperform.

## 대표 반환 형태

`pl.DataFrame` — 컬럼:
- `qualityScore : float` · `qualityDecile : int (1~10)`
- `cyclePhase : str` — early-recovery / mid-expansion / late-cycle / contraction
- `rateBeta : float` · `fxBeta : float`
- `expectedWinner : str` — high / low / balanced
- `phaseAlignment : bool`

## 연계 절차

1. 본 recipe → 회사 quality + 사이클 phase 정합성.
2. phaseAlignment = True → `recipes.meta.screen.industryStageScreen` 으로 같은 산업 stage 후행기 종목 추가 발굴.
3. phaseAlignment = False → 다음 phase 전환까지 대기 (timing 신호).
4. universe 검증은 `recipes.macro.quantScenarioBacktest` 로 backtest.
