"""Deprecated — use ``dartlab.core.utils.labels`` instead.

이 모듈은 ``dartlab.core.utils.labels`` 으로 이주됐다. 새 코드는 새 경로를 사용. 이 shim
은 다음 메이저에서 제거 예정.
"""

from warnings import warn

from dartlab.core.utils.labels import *  # noqa: F401, F403

warn(
    "dartlab.core.finance.labels → dartlab.core.utils.labels (deprecated, removed in next major)",
    DeprecationWarning,
    stacklevel=2,
)
