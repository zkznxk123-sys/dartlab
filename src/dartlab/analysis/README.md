# analysis/ — L2 재무 분석 엔진

> 단일 종목 또는 peer 의 *재무 분석* — cashflow / ratios / margin / growth / forensics.
> L2 분석 5 엔진 중 하나. 상호 import 0 (L2 형제 격리).

---

## 공개 API

| 모듈 | 역할 |
|------|------|
| `analysis/ratios.py` | 재무비율 — PBR / PER / ROA / ROE / DSCR / 이자보상배율 |
| `analysis/cashflow.py` | 현금흐름 분석 — FCF / OCF / 운전자본 |
| `analysis/margin.py` | 수익성 — 매출총이익률 / 영업이익률 / 순이익률 |
| `analysis/growth.py` | 성장성 — YoY / QoQ / CAGR |
| `analysis/forensics/` | 회계 forensics — Beneish / Big bath / 회계 추정 변경 |

---

## 진입점

```python
import dartlab
c = dartlab.Company("005930")
c.show("ratios")     # 재무비율
c.show("cashflow")   # 현금흐름
```

---

## 룰

- **L2 분석 5 엔진 상호 import 0** — analysis / credit / macro / quant / industry 간 import 금지 (importlinter contract).
- **L1.5 만 import** — frame / synth / reference 만 dependent (L1 직접 import 는 예외 시에만).
- **Decimal 정합** — 회계 비교는 `core/decimal.isClose` 사용 (T7-4 트랙).
- **Polars lazy 우선** — 대용량 frame 처리 시 `scan_parquet` + `lazy()` (T3-5 audit).

---

## metamorphic 보증

`analysis.ratios.*` 함수는 `tests/metamorphic/` (T6-3) 의 다음 패턴 보증:
- scale invariance: KRW ↔ USD 환산 후 비율 동일
- monotonicity: 매출 ↑ → 이익률 ↑ (다른 변수 고정)
- safeDivide: 0 분모 안전 처리

---

## 관련

- [src/dartlab/skills/specs/engines/analysis/SKILL.md](../skills/specs/engines/analysis/SKILL.md) — engine spec
- [tests/metamorphic/](../../../tests/metamorphic/) — 변환 보존 검증 (T6-3)
- [src/dartlab/core/decimal.py](../core/decimal.py) — 회계 Decimal 헬퍼 (T7-4)
