"""Deprecated — use ``dartlab.credit.sectorThresholds`` instead.

이 모듈은 ``dartlab.credit.sectorThresholds`` 으로 이주됐다 (S6). 새 코드는 새 경로를 사용. 이
shim 은 다음 메이저에서 제거 예정.
"""

from warnings import warn

from dartlab.credit.sectorThresholds import *  # noqa: F401, F403

warn(
    "dartlab.core.finance.sectorThresholds → dartlab.credit.sectorThresholds (deprecated, removed in next major)",
    DeprecationWarning,
    stacklevel=2,
)
