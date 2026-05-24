# frame/ — L1.5 raw 결합

> provider raw → 분석 ready frame 변환. L1.5 가공 4 형제 중 하나.

| 모듈 | 역할 |
|------|------|
| `frame/finance.py` | XBRL finance frame (account × period) |
| `frame/disclosure.py` | 공시 본문 frame (topic × period) |
| `frame/market.py` | 가격 / 수급 frame |

## 룰

- L1.5 형제 cross import 금지 (scan / synth / reference 와 분리)
- L1 provider raw 만 dependent
- Polars lazy 우선 (T3-5)

## 관련

- [src/dartlab/skills/specs/runtime/providerProtocol.md](../skills/specs/runtime/providerProtocol.md)
- [tests/architecture/test_l15_no_cross_import.py](../../../tests/architecture/test_l15_no_cross_import.py)
