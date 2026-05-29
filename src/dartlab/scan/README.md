# scan/ — L1.5 횡단면 스크리닝

> 전종목 / peer 그룹 / 시장 전체 *횡단면 분석* 진입점. `dartlab.scan("recipeName", **params)` 표면.
> L1.5 가공 4 형제 중 하나. cross import 금지 (frame / synth / reference 와 분리).

---

## 진입점

```python
import dartlab
result = dartlab.scan("foreignBuyMomentum", universe="kospi200", window="20d")
# ScanResult { table: DataFrame, refs: [Ref, ...] }
```

---

## recipe 분류

| 분류 | 예시 |
|------|------|
| **flow** | foreignBuyMomentum / foreignHoldingLevel / foreignFlowFactor |
| **profitability** | scanRatio / earningsRevision |
| **technical** | priceVolumeZScore / sectorMomentumLeadership |
| **valuation** | (TODO) |
| **risk** | workingCapitalPressureMap |
| **disclosure** | disclosureLatencyAudit |

전체 recipe lifecycle: [src/dartlab/skills/specs/operation/recipePromote.md](../skills/specs/operation/recipePromote.md)
(drafted → unverified → tested → verified → curated → deprecated)

---

## 룰

- **L1.5 형제 cross import 금지** — frame / synth / reference import 안 함 (강제: `tests/architecture/test_l15_no_cross_import.py`).
- **eager scan** — 횡단면이라 전종목 로드 필요. fixture scope = module / serial marker 강행.
- **memory budget** — Polars 힙 누수 회피. `withMemoryBudget(limitMb=...)` decorator 활용.
- **recipe 자동 승급** — coverage ≥ 90% + mutation ≥ 80% 시 drafted → tested (T5-3 트랙).

---

## 관련

- [src/dartlab/skills/specs/operation/recipePromote.md](../skills/specs/operation/recipePromote.md) — recipe lifecycle
- [src/dartlab/skills/recipePromote.py](../skills/recipePromote.py) — 승급 CLI (status frontmatter 단독 권한)
- [tests/audit/moduleSizeAudit.py](../../../tests/audit/moduleSizeAudit.py) (T9-4) — sub-namespace 크기 측정
