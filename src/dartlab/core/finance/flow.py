"""Deprecated — use ``dartlab.core.utils.flow`` instead.

이 모듈은 ``dartlab.core.utils.flow`` 으로 이주됐다. 새 코드는 새 경로를 사용. 이 shim
은 다음 메이저에서 제거 예정.
"""

from warnings import warn

from dartlab.core.utils.flow import *  # noqa: F401, F403

warn(
    "dartlab.core.finance.flow → dartlab.core.utils.flow (deprecated, removed in next major)",
    DeprecationWarning,
    stacklevel=2,
)
