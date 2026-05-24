# macro/ — L2 거시 사이클 + 섹터 로테이션

> FRED / ECOS / KRX 거시지표 기반 사이클 + 섹터 로테이션 + scenario.

---

## 공개 API

```python
import dartlab
cycle = dartlab.macro.cycle("us-pmi")
print(cycle.currentRegime)   # 'contraction' / 'trough' / 'expansion' / 'peak'

rotation = dartlab.macro.sectorRotation(cycle="us-pmi", market="kospi")
print(rotation.recommend(asOf="latest"))
```

| 모듈 | 역할 |
|------|------|
| `macro/cycle.py` | 사이클 regime 분류 (PMI / 금리 / 유동성) |
| `macro/sectorRotation.py` | regime 전환 시 섹터별 historical hit rate |
| `macro/scenario.py` | macro scenario 시뮬레이션 |
| `macro/forecast/` | 거시 forecast 모듈 |

---

## 룰

- L2 형제 import 0
- 외부 데이터 (FRED / ECOS) 는 *sync* 단계에서만 (prebuild offline 정합, T7-2 lineage)
- mutmut 대상 — `macro/cycle.py` (T6-2)

---

## 관련

- [docs/CASE_STUDIES.md](../../../docs/CASE_STUDIES.md) — 사례 3 매크로 + 섹터 로테이션
- [src/dartlab/skills/specs/engines/macro/SKILL.md](../skills/specs/engines/macro/SKILL.md)
- [src/dartlab/core/dataAudit.py](../core/dataAudit.py) (T7-2) — sync lineage
