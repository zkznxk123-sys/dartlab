"""earningsQuality.py 본체 호출 lazy proxies — cycle 회피 SSOT.

`_earningsQualityDeep` facade 가 본 모듈을 re-export. 각 proxy 는 deferred import
로 cycle 방지.
"""

from __future__ import annotations


def _beneishInterpretation(*args, **kwargs):
    """Beneish 해석 — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy)."""
    from dartlab.analysis.financial.earningsQuality import _beneishInterpretation as _f

    return _f(*args, **kwargs)


def calcBeneishMScore(*args, **kwargs):
    """Beneish M-Score 본 점수 — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        earningsQuality.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcBeneishMScore(company)["mScore"]
        -2.1
    """
    from dartlab.analysis.financial.earningsQuality import calcBeneishMScore as _f

    return _f(*args, **kwargs)


def calcSloanAccruals(*args, **kwargs):
    """Sloan accruals — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        earningsQuality.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcSloanAccruals(company)["accruals"]
        0.03
    """
    from dartlab.analysis.financial.earningsQuality import calcSloanAccruals as _f

    return _f(*args, **kwargs)


def calcAccrualAnalysis(*args, **kwargs):
    """발생액 분석 — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        earningsQuality.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcAccrualAnalysis(company)["score"]
        0.5
    """
    from dartlab.analysis.financial.earningsQuality import calcAccrualAnalysis as _f

    return _f(*args, **kwargs)


def calcEarningsPersistence(*args, **kwargs):
    """이익 지속성 — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        earningsQuality.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcEarningsPersistence(company)["score"]
        0.7
    """
    from dartlab.analysis.financial.earningsQuality import calcEarningsPersistence as _f

    return _f(*args, **kwargs)


def _calcEarningsQualityFlagsBase(*args, **kwargs):
    """flags base — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy)."""
    from dartlab.analysis.financial.earningsQuality import _calcEarningsQualityFlagsBase as _f

    return _f(*args, **kwargs)


def detectAuditFlags(*args, **kwargs):
    """감사 flag 검출 — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        earningsQuality.py 본체 import.

    Raises:
        없음.

    Example:
        >>> detectAuditFlags(company)
        ['지정감사인', '한정의견']
    """
    from dartlab.analysis.financial.earningsQuality import detectAuditFlags as _f

    return _f(*args, **kwargs)


def calcEarningsQualityFlags(*args, **kwargs):
    """earnings quality flags — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        earningsQuality.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcEarningsQualityFlags(company)
        [('HIGH_ACCRUAL', '...')]
    """
    from dartlab.analysis.financial.earningsQuality import calcEarningsQualityFlags as _f

    return _f(*args, **kwargs)
