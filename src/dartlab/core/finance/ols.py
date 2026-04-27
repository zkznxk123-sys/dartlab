"""Deprecated — use ``dartlab.core.utils.ols`` instead.

이 모듈은 ``dartlab.core.utils.ols`` 로 이주됐다. 새 코드는 새 경로를 사용. 이 shim
은 다음 메이저에서 제거 예정.
"""

from warnings import warn

from dartlab.core.utils.ols import *  # noqa: F401, F403

warn(
    "dartlab.core.finance.ols → dartlab.core.utils.ols (deprecated, removed in next major)",
    DeprecationWarning,
    stacklevel=2,
)
