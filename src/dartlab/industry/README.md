# industry/ — L2 섹터 / peer 매트릭스

> 섹터 분류 + peer 매트릭스 + sectorMomentumLeadership + 산업 맵.

---

## 공개 API

```python
import dartlab
result = dartlab.industry.sectorMomentumLeadership(sector="반도체", peers=8)
# Leader / Laggard label + 20d return 분포
```

| 모듈 | 역할 |
|------|------|
| `industry/sectorMomentum.py` | 섹터 모멘텀 ranking |
| `industry/peerMatrix.py` | peer 회사 매트릭스 |
| `industry/map.py` | 산업 맵 / 카테고리 |
| `industry/concentration.py` | 산업 집중도 (HHI) |

---

## 룰

- L2 형제 import 0
- 산업 맵 정적 JSON 은 L1.5 reference 에 owner
- mutmut 대상은 후속 (현재 12 / 30 모듈)

---

## 관련

- [src/dartlab/skills/specs/engines/industry/SKILL.md](../skills/specs/engines/industry/SKILL.md)
- [src/dartlab/reference/data/](../reference/data/) — 산업 맵 / 카테고리 정적 데이터
