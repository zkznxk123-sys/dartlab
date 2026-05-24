# quant/ — L2 퀀트 factor / alpha

> 퀀트 factor 생성 + alpha 백테스트 + 포트폴리오 매핑. L2 분석 5 엔진 중 하나.
> 21K LOC — providers 다음으로 큰 sub-namespace.

---

## 공개 API

| 모듈 | 역할 |
|------|------|
| `quant/factors.py` | factor 생성 (외인 보유 / 모멘텀 / 가치 / 품질) |
| `quant/foreignFlow.py` | 외인 흐름 factor (foreignFlowFactor / foreignHoldingLevel) |
| `quant/portfolio/` | 포트폴리오 구성 + 매핑 |
| `quant/backtest/` | alpha 백테스트 |
| `quant/scorecards/` | scorecard 6 신호 (recipe lifecycle 정합) |

---

## 진입점

```python
import dartlab
result = dartlab.quant.foreignFlowFactor(universe="kospi200", lookback="60d")
# Polars DataFrame + ref
```

---

## 룰

- **L2 형제 import 0** — analysis / credit / macro / industry import 안 함.
- **L1.5 만 import** — scan / frame / synth / reference.
- **결정론적 seed** — random 호출 시 `core/random.py` 의 SEEDED_RANDOM (T7-3 audit).
- **mutmut 대상** — `quant/factors.py` 포함 (T6-2, 12 모듈 중).

---

## 세계 수준 갭

[memory/quantGap.md](../../../) 참조 — Microsoft qlib + AlphaLens 대비 P0~P3 스프린트 정의.

---

## 관련

- [src/dartlab/skills/specs/engines/quant/SKILL.md](../skills/specs/engines/quant/SKILL.md) — engine spec
- [memory/quantGap.md](../../../) — 세계 수준 갭 분석
- [tests/metamorphic/test_ranking_shift.py](../../../tests/metamorphic/test_ranking_shift.py) — factor ranking 보존 검증 (T6-3)
