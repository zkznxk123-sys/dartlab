"""Deprecated — use ``dartlab.macro.yieldCurve`` instead.

이 모듈은 ``dartlab.macro.yieldCurve`` 으로 이주됐다 (S4a). 새 코드는 새 경로를 사용. 이
shim 은 다음 메이저에서 제거 예정.
"""

from warnings import warn

from dartlab.macro.yieldCurve import *  # noqa: F401, F403

warn(
    "dartlab.core.finance.yieldCurve → dartlab.macro.yieldCurve (deprecated, removed in next major)",
    DeprecationWarning,
    stacklevel=2,
)
