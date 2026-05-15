"""predictionSignals OLS·상관 수치 헬퍼 — calcMacroRegression 의 하위 도구.

analysis/financial/predictionSignals.py 가 2594 줄 god module 이라 수치 헬퍼 분리.
identity 보존을 위해 predictionSignals.py 가 본 모듈에서 re-export 한다.

순수 Python 수치 (numpy 의존 없음 — 호출 빈도 낮은 회귀 1 회용):
- _quickCorr — 빠른 피어슨 상관 (페어 ≥5 요구)
- _fitOLS — 절편 포함 OLS β + R²
- _invertMatrix — 가우스-조르단 역행렬 (정사각, 작은 차원 1~5)
- _calcLagCorrelation — lag 0/1/2 상관 dict
- _pearsonCorrelation — lag 적용 피어슨 상관
"""

from __future__ import annotations

import math


def _quickCorr(y: list[float | None], x: list[float | None]) -> float | None:
    """빠른 피어슨 상관계수."""
    pairs = [(a, b) for a, b in zip(y, x) if a is not None and b is not None]
    if len(pairs) < 5:
        return None
    ys = [p[0] for p in pairs]
    xs = [p[1] for p in pairs]
    ym = sum(ys) / len(ys)
    xm = sum(xs) / len(xs)
    cov = sum((a - ym) * (b - xm) for a, b in pairs) / len(pairs)
    ystd = math.sqrt(sum((a - ym) ** 2 for a in ys) / len(ys))
    xstd = math.sqrt(sum((b - xm) ** 2 for b in xs) / len(xs))
    if ystd < 1e-12 or xstd < 1e-12:
        return None
    return cov / (ystd * xstd)


def _fitOLS(
    y: list[float | None], macroData: dict[str, list[float | None]], cols: list[str]
) -> tuple[dict[str, float] | None, float | None, int]:
    """OLS 회귀 — y ~ 거시변화율 + 산업지표변화율 (가변 변수).

    macroData의 키가 회귀 변수명이 된다.
    외부 의존성 없이 순수 Python으로 구현.

    Returns:
        (betas, r_squared, n_obs) 또는 (None, None, 0).
    """
    varNames = [k for k in macroData.keys() if k != "_usedIndicators" and isinstance(macroData[k], list)]
    if not varNames:
        return None, None, 0

    n = min(len(y), *(len(macroData[v]) for v in varNames))

    validY: list[float] = []
    validX: list[list[float]] = []
    activeVars: list[str] = []

    for v in varNames:
        if any(x is not None for x in macroData[v][:n]):
            activeVars.append(v)

    for i in range(n):
        yVal = y[i]
        if yVal is None:
            continue
        xVals = []
        skip = False
        for v in activeVars:
            val = macroData[v][i] if i < len(macroData[v]) else None
            if val is None:
                skip = True
                break
            xVals.append(val)
        if not skip:
            validY.append(yVal)
            validX.append(xVals)

    if len(validY) < 3 or not activeVars:
        return None, None, 0

    nObs = len(validY)
    k = 1 + len(activeVars)

    X = [[1.0] + row for row in validX]

    XtX = [[sum(X[r][i] * X[r][j] for r in range(nObs)) for j in range(k)] for i in range(k)]
    Xty = [sum(X[r][i] * validY[r] for r in range(nObs)) for i in range(k)]

    inv = _invertMatrix(XtX)
    if inv is None:
        return None, None, 0

    beta = [sum(inv[i][j] * Xty[j] for j in range(k)) for i in range(k)]

    yMean = sum(validY) / nObs
    ssTot = sum((y_ - yMean) ** 2 for y_ in validY)
    yPred = [sum(X[r][j] * beta[j] for j in range(k)) for r in range(nObs)]
    ssRes = sum((validY[r] - yPred[r]) ** 2 for r in range(nObs))
    rSquared = 1 - ssRes / ssTot if ssTot > 0 else 0.0

    betas = {activeVars[i]: round(beta[i + 1], 4) for i in range(len(activeVars))}

    return betas, rSquared, nObs


def _invertMatrix(m: list[list[float]]) -> list[list[float]] | None:
    """4x4 행렬 가우스-조르단 역행렬."""
    n = len(m)
    aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(m)]

    for col in range(n):
        maxRow = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[maxRow][col]) < 1e-12:
            return None
        aug[col], aug[maxRow] = aug[maxRow], aug[col]

        pivot = aug[col][col]
        aug[col] = [x / pivot for x in aug[col]]

        for row in range(n):
            if row != col:
                factor = aug[row][col]
                aug[row] = [aug[row][j] - factor * aug[col][j] for j in range(2 * n)]

    return [row[n:] for row in aug]


def _calcLagCorrelation(
    y: list[float | None], macroData: dict[str, list[float | None]], cols: list[str]
) -> dict[str, dict[str, float | None]]:
    """시간차(lag) 상관도 — lag 0, 1, 2."""
    result: dict[str, dict[str, float | None]] = {}

    for key in [k for k in macroData if k != "_usedIndicators" and isinstance(macroData[k], list)]:
        vals = macroData[key]
        lagCorrs: dict[str, float | None] = {}
        changes = []
        for i in range(len(vals) - 1):
            cur, prev = vals[i], vals[i + 1]
            if cur is not None and prev is not None and prev != 0:
                if key == "rate":
                    changes.append(cur - prev)
                else:
                    changes.append((cur - prev) / abs(prev) * 100)
            else:
                changes.append(None)

        for lag in range(3):
            corr = _pearsonCorrelation(y, changes, lag=lag)
            lagCorrs[f"lag{lag}"] = round(corr, 4) if corr is not None else None

        result[key] = lagCorrs

    return result


def _pearsonCorrelation(y: list[float | None], x: list[float | None], *, lag: int = 0) -> float | None:
    """피어슨 상관계수 (lag 적용)."""
    pairs: list[tuple[float, float]] = []
    for i in range(len(y)):
        xi = i + lag
        if xi < len(x):
            yVal, xVal = y[i], x[xi]
            if yVal is not None and xVal is not None:
                pairs.append((yVal, xVal))

    if len(pairs) < 3:
        return None

    yVals = [p[0] for p in pairs]
    xVals = [p[1] for p in pairs]
    yMean = sum(yVals) / len(yVals)
    xMean = sum(xVals) / len(xVals)

    cov = sum((y_ - yMean) * (x_ - xMean) for y_, x_ in pairs) / len(pairs)
    yStd = math.sqrt(sum((y_ - yMean) ** 2 for y_ in yVals) / len(yVals))
    xStd = math.sqrt(sum((x_ - xMean) ** 2 for x_ in xVals) / len(xVals))

    if yStd < 1e-12 or xStd < 1e-12:
        return None

    return cov / (yStd * xStd)


__all__ = [
    "_calcLagCorrelation",
    "_fitOLS",
    "_invertMatrix",
    "_pearsonCorrelation",
    "_quickCorr",
]
