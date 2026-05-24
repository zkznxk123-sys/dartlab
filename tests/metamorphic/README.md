# Metamorphic Tests — 변환 후 보존 속성 검증 (T6-3)

> oracle (정답 데이터) 부재 시 *변환에도 불변* 인 속성으로 회귀 차단.
> 금융 계산의 신뢰도 보강 — *결과의 절대값 검증* 보다 *관계 보존 검증* 이 강력.

## 5 패턴

| # | 패턴 | 의미 | 대상 함수 예시 |
|---|------|------|---------------|
| 1 | **scale invariance** | 단위 환산 (KRW↔USD) 후 % 비율 보존 | `Company.ratios()` 의 PBR/PER |
| 2 | **ranking shift 보존** | 같은 데이터 같은 호출 → 같은 순서 | `scan.foreignBuyMomentum` Top 10 |
| 3 | **idempotency** | 같은 args 2회 호출 → 같은 ref | `EngineCall(apiRef, args)` |
| 4 | **monotonicity** | 단조 입력 변화 → 단조 출력 변화 | `analysis.creditScore` (매출 ↑ → 점수 ↑) |
| 5 | **commutativity** | 인자 순서 무관 결과 동일 | `synth.scenarioMatch(A, B) == (B, A)` |

## 실행

```bash
bash tests/test-lock.sh tests/metamorphic/ -m "metamorphic" -v
```

## 결과 (현재)

| 패턴 | 파일 | 상태 |
|------|------|------|
| scale invariance | test_scale_invariance.py | ✓ 구조 작성 (T6-3 첫 commit) |
| ranking shift | test_ranking_shift.py | ✓ |
| idempotency | test_idempotency.py | ✓ |
| monotonicity | test_monotonicity.py | ✓ |
| commutativity | test_commutativity.py | ✓ |

각 패턴은 *최소 1 case + 100 random input* 으로 확장. 실제 dartlab 함수 호출은
fixture (Company/scan/credit) 가 메모리 안전 룰 (T3-3 serial marker) 정합 후 활성화.

## 관련

- [TODO.md](../../TODO.md) T6-3 트랙
- [CLAUDE.md](../../CLAUDE.md) 메모리 안전 룰 (Polars 힙 + fixture scope=module)
- 참고: Microsoft qlib metamorphic suite + polars hypothesis suite
