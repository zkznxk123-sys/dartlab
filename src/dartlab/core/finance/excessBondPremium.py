"""Deprecated — use ``dartlab.credit.excessBondPremium`` instead.

이 모듈은 ``dartlab.credit.excessBondPremium`` 으로 이주됐다 (S6). 새 코드는 새 경로를 사용. 이
shim 은 다음 메이저에서 제거 예정.
"""

from warnings import warn

from dartlab.credit.excessBondPremium import *  # noqa: F401, F403

warn(
    "dartlab.core.finance.excessBondPremium → dartlab.credit.excessBondPremium (deprecated, removed in next major)",
    DeprecationWarning,
    stacklevel=2,
)
