# 052 factorEvaluation (Grinold IC/IR)

- 실험일: 2026-04-15
- 판정: **통과 (6/6)**

## 핵심 수치

| 케이스 | Pearson | Spearman | 기대 |
|---|---|---|---|
| factor==return | 1.000 | 1.000 | 1.0 |
| factor==-return | -1.000 | -1.000 | -1.0 |
| random N=10000 | -0.008 | -0.006 | \|IC\|<0.05 |
| Fund.Law IC=0.05, br=400 | IR=1.000 | — | 1.0 |
| calcIR 공식 | IR=0.5145 | — | mean/std |
| partial ρ=0.3 | 0.318 | 0.278 | ≈0.3 |

## 결론

- numpy 순수 구현으로 교과서 수식 전부 재현 (scipy 0)
- L0 SSOT `core/quant/factorEval.py` 에 박을 수식 확정
- 후속 B1 단계로 진행

## 흡수 함수 목록 (L0 SSOT)

- `pearsonCorr(x, y) -> float`
- `spearmanCorr(x, y) -> float`  (동률 평균 rank)
- `calcIR(alphaSeries) -> float`
- `fundamentalLawIR(ic, breadth) -> float`
- `rollingTimeSeriesZscore(series, window) -> np.ndarray`  (B1 단계 추가)
