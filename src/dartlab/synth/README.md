# synth/ — L1.5 분석 후처리 / 매칭 / 시나리오

> L2 분석 결과를 *매칭 / 시나리오 / 합성* 하는 후처리. L1.5 가공 4 형제 중 하나.

| 모듈 | 역할 |
|------|------|
| `synth/scenarioMatch.py` | scenario 매칭 (사용자 시나리오 ↔ historical peer) |
| `synth/peer.py` | peer 합성 |
| `synth/scenario.py` | scenario 시뮬레이션 |

## 룰

- L1.5 형제 cross import 금지
- L2 분석 결과는 ref 형태로 받음 (직접 호출 안 함 — synth 가 L2 import 시 cycle)

## 관련

- [src/dartlab/skills/specs/operation/compareTargets.md](../skills/specs/operation/compareTargets.md)
- [tests/metamorphic/test_commutativity.py](../../../tests/metamorphic/test_commutativity.py) — scenarioMatch A↔B 대칭 (T6-3)
