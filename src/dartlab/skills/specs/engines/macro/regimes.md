---
id: engines.macro.regimes
title: Macro — Regime 분류 (regimes)
category: engines
kind: curated
scope: builtin
status: observed
purpose: 매크로 regime 분류 SSOT — 시장 상태를 4~5 regime (확장·둔화·수축·회복 + 위기) 으로 자동 라벨링. Hamilton 1989 HMM 패러다임 + dartlab 자체 cycle · liquidity · crisis axis 결합 결과의 단일 어휘 정의.
whenToUse:
  - regime
  - 시장 국면
  - 매크로 regime
  - HMM regime
  - 확장·둔화·수축·회복
  - 위기 regime
  - regime 전환
  - 시장 상태 분류
sourceRefs:
  - dartlab://skills/engines.macro.regimes
capabilityRefs:
  - macro
knowledgeRefs:
  - engines.macro
  - engines.quant
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
  - engines.macro.cycles
  - engines.quant
---

## 엔진 역할

`macro` 엔진의 *regime 분류* 어휘 SSOT. base SKILL `engines.macro` 의 12 axis 중 `cycle` + `liquidity` + `crisis` 결합 결과를 5 regime enum 으로 단일화. quant 엔진의 regime-aware factor / scenario backtest 와 *같은 어휘* 인용.

Hamilton 1989 (Markov-switching) 패러다임 + dartlab 자체 KR/US 시장 cycle axis 의 라벨링 SSOT.

## 공개 호출 방식

```python
import dartlab

# 1. 현재 시장 regime (KR)
cycle = dartlab.macro("cycle", market="KR")
# → regime 라벨 + indicator + dateRef

# 2. regime 시계열 (cycle axis 반환의 시계열 컬럼)
# → cycle axis 결과의 phase / regime 컬럼 참조

# 3. quant 엔진 regime-aware 호출
# (quant 측 regime 인자가 본 enum 따름)
```

## 호출 동작

본 spec 은 *어휘 정의* — 실제 분류는 `dartlab.macro("cycle"|"liquidity"|"crisis")` 의 반환 dict 안 phase/regime 컬럼이 본 5 enum 으로 라벨링되어 있다.

1. `cycle` axis → 경기 사이클 phase (회복/확장/후퇴/수축) — 본 spec 의 expansion/slowdown/contraction/recovery 매핑.
2. `crisis` axis → 위기 regime 진입 여부 (binary) — 본 spec 의 `crisis` regime.
3. `liquidity` axis → 유동성 quartile — regime 분류 보조 신호 (regime 단독 결정 X).
4. 종합 regime = 위 3 axis 결합 정성 판단 (HMM 자동 분류 + 운영자 검토).

## 5 regime enum 정의

| regime | 한글 | cycle phase | liquidity | crisis | 자산 추세 (참고) |
|---|---|---|---|---|---|
| **expansion** | 확장 | 확장 | 상위 | False | 위험자산 ↑ / 금리 ↑ |
| **slowdown** | 둔화 | 후퇴 (초기) | 중하위 | False | 위험자산 ↘ / 금리 ↘ |
| **contraction** | 수축 | 수축 | 하위 | False | 위험자산 ↓ / 금리 ↓ |
| **recovery** | 회복 | 회복 | 중상위 (확대) | False | 위험자산 ↑ / 금리 → |
| **crisis** | 위기 | 어느 phase 든 | 급락 | True | 모든 위험자산 ↓ |

`crisis` 는 cycle phase 와 직교 — 평상시 4 regime 중 하나에 위기 trigger 시 crisis 로 override.

## 대표 반환 형태

```text
dartlab.macro("cycle", market="KR")
→ dict
   axis : str               # "cycle"
   market : str             # "KR" / "US"
   regime : str             # 5 enum 중 하나 (expansion/slowdown/contraction/recovery/crisis)
   regimeLabel : str        # 한글
   phase : str              # cycle 4 phase (회복/확장/후퇴/수축)
   indicators : dict        # 분류 근거 지표 (CPI/PMI/금리/...)
   dateRef : str            # YYYY-MM
   confidence : float       # 0.0 ~ 1.0
   ...
```

## 기본 실행 순서

1. **현재 regime** — `dartlab.macro("cycle", market=...)` 결과의 `regime` 필드 인용.
2. **regime 시계열** — `cycle` axis 의 시계열 컬럼 (월/분기 단위).
3. **regime × 자산배분** — `dartlab.macro("assets", market=..., scenario=...)` 가 본 regime enum 으로 분기.
4. **quant 결합** — `recipes.macro.qualityMacroBeta` 등 recipe 에서 regime 인자로 본 enum 사용.

## 기본 검증

- 반환 `regime` 값이 5 enum 안.
- `crisis=True` 면 `regime="crisis"` (override).
- 같은 market·dateRef 재호출 시 regime 동일.
- `confidence` 0~1 범위.

본 spec 은 공개 실행 문서다. 5 regime enum 또는 분류 임계가 변경되면 본 파일을 같은 변경에서 갱신한다.

## 관련

- [engines.macro](/skills/engines.macro) — base SKILL (12 axis)
- [engines.macro.cycles](/skills/engines.macro.cycles) — 사이클 phase 시계열
- [engines.quant](/skills/engines.quant) — regime-aware factor / scenario backtest
- [recipes.macro.qualityMacroBeta](/skills/recipes.macro.qualityMacroBeta) — QMJ × regime 결합 recipe
