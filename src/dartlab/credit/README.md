# credit/ — L2 신용 분석

> Altman Z-score / Beneish M-score / KIS-score 등 *신용 위험 점수* + 등급 평가 + zone 분류.

---

## 공개 API

```python
import dartlab
c = dartlab.Company("005380")
credit = c.credit.altmanZScore()
print(credit.score, credit.zone)   # 1.65, distress
```

| 모듈 | 역할 |
|------|------|
| `credit/altman.py` | Altman Z-score (K-IFRS 정합) |
| `credit/beneish.py` | Beneish M-score (earnings manipulation) |
| `credit/kisScore.py` | KIS 신용등급 매핑 |
| `credit/zone.py` | safe / gray / distress zone 분류 |

---

## 룰

- L2 형제 import 0
- L1.5 만 import
- Z-score zone 임계 (1.81 / 2.99) 는 `core/decimal.isClose` 정합 (T7-4)
- mutmut 대상 — `credit/altman.py` (T6-2, 12 모듈 중)

---

## 관련

- [docs/CASE_STUDIES.md](../../../docs/CASE_STUDIES.md) — 사례 2 신용 점수 모니터링
- [src/dartlab/skills/specs/engines/credit/SKILL.md](../skills/specs/engines/credit/SKILL.md) — engine spec
