"""_valuationDeep 의 16 lazy proxies + __getattr__ — valuation.py 본체 위임."""

from __future__ import annotations


def __getattr__(name: str):
    from dartlab.analysis.financial import valuation as _v

    if hasattr(_v, name):
        return getattr(_v, name)
    raise AttributeError(f"module 'dartlab.analysis.financial._valuationDeep' has no attribute {name!r}")


def computePriceTarget(*args, **kwargs):
    """price target — valuation.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        valuation.py 본체 import 가능.

    Raises:
        없음 — 본체 위임.

    Example:
        >>> computePriceTarget(company)
        {...}
    """
    from dartlab.analysis.financial.valuation import computePriceTarget as _f

    return _f(*args, **kwargs)


def calcValuationConsistency(*args, **kwargs):
    """valuation 일관성 — valuation.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        valuation.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcValuationConsistency(company)["score"]
        0.7
    """
    from dartlab.analysis.financial.valuation import calcValuationConsistency as _f

    return _f(*args, **kwargs)


def calcMonteCarloValuation(*args, **kwargs):
    """Monte Carlo valuation — valuation.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        valuation.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcMonteCarloValuation(company)["mean"]
        78000
    """
    from dartlab.analysis.financial.valuation import calcMonteCarloValuation as _f

    return _f(*args, **kwargs)


def calcCrossSectionRegression(*args, **kwargs):
    """횡단면 회귀 — valuation.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        valuation.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcCrossSectionRegression(company)["impliedValue"]
        80000
    """
    from dartlab.analysis.financial.valuation import calcCrossSectionRegression as _f

    return _f(*args, **kwargs)


def _rimCalc(*args, **kwargs):
    """RIM calc — residualIncome.calcResidualIncome 위임 (cycle 회피 lazy proxy).

    d77f9abf8 facade 리팩토링이 valuation.py 의 `_rimCalc` re-export 를 누락 →
    ImportError 로 calcValuationSynthesis 의 RIM/relative 합성이 깨짐. 원 정의
    (analysis.valuation.residualIncome.calcResidualIncome) 로 직접 위임해 복구.
    """
    from dartlab.analysis.valuation.residualIncome import calcResidualIncome as _f

    return _f(*args, **kwargs)


def _inRange(*args, **kwargs):
    """범위 체크 — valuation.py 본체 위임 (cycle 회피 lazy proxy)."""
    from dartlab.analysis.financial.valuation import _inRange as _f

    return _f(*args, **kwargs)


def _resolveSectorKey(*args, **kwargs):
    """sector key 해석 — valuation.py 본체 위임 (cycle 회피 lazy proxy)."""
    from dartlab.analysis.financial.valuation import _resolveSectorKey as _f

    return _f(*args, **kwargs)


def _fetchPriceContext(*args, **kwargs):
    """price context fetch — valuation.py 본체 위임 (cycle 회피 lazy proxy)."""
    from dartlab.analysis.financial.valuation import _fetchPriceContext as _f

    return _f(*args, **kwargs)


def _getSeriesAndShares(*args, **kwargs):
    """series + shares getter — valuation.py 본체 위임 (cycle 회피 lazy proxy)."""
    from dartlab.analysis.financial.valuation import _getSeriesAndShares as _f

    return _f(*args, **kwargs)


def _getSectorParams(*args, **kwargs):
    """sector params getter — valuation.py 본체 위임 (cycle 회피 lazy proxy)."""
    from dartlab.analysis.financial.valuation import _getSectorParams as _f

    return _f(*args, **kwargs)


def calcDcf(*args, **kwargs):
    """DCF 계산 — valuation.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        valuation.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcDcf(company)["intrinsicValue"]
        82000
    """
    from dartlab.analysis.financial.valuation import calcDcf as _f

    return _f(*args, **kwargs)


def calcDdm(*args, **kwargs):
    """DDM 계산 — valuation.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        valuation.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcDdm(company)["intrinsicValue"]
        72000
    """
    from dartlab.analysis.financial.valuation import calcDdm as _f

    return _f(*args, **kwargs)


def calcRelativeValuation(*args, **kwargs):
    """상대 valuation — valuation.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        valuation.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcRelativeValuation(company)["impliedPER"]
        12
    """
    from dartlab.analysis.financial.valuation import calcRelativeValuation as _f

    return _f(*args, **kwargs)


def calcResidualIncome(*args, **kwargs):
    """residual income — valuation.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        valuation.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcResidualIncome(company)["intrinsicValue"]
        75000
    """
    from dartlab.analysis.financial.valuation import calcResidualIncome as _f

    return _f(*args, **kwargs)


def calcNavValuation(*args, **kwargs):
    """NAV valuation — valuation.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        valuation.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcNavValuation(company)["nav"]
        90000
    """
    from dartlab.analysis.financial.valuation import calcNavValuation as _f

    return _f(*args, **kwargs)


def calcReverseImplied(*args, **kwargs):
    """reverse implied — valuation.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        valuation.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcReverseImplied(company)["impliedGrowth"]
        0.08
    """
    from dartlab.analysis.financial.valuation import calcReverseImplied as _f

    return _f(*args, **kwargs)


def calcSensitivity(*args, **kwargs):
    """sensitivity — valuation.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        valuation.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcSensitivity(company)["range"]
        (60000, 90000)
    """
    from dartlab.analysis.financial.valuation import calcSensitivity as _f

    return _f(*args, **kwargs)
