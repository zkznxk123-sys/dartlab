"""Deprecated — use ``dartlab.analysis.financial.ratios`` instead.

이 모듈은 ``dartlab.analysis.financial.ratios`` 로 이주됐다 (S5a). 새 코드는 새 경로를
사용. 이 shim 은 다음 메이저에서 제거 예정.
"""

from warnings import warn

from dartlab.analysis.financial.ratios import *  # noqa: F401, F403

warn(
    "dartlab.core.finance.ratios → dartlab.analysis.financial.ratios (deprecated, removed in next major)",
    DeprecationWarning,
    stacklevel=2,
)
