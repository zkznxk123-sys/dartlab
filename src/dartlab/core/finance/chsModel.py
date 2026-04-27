"""Deprecated — use ``dartlab.credit.chsModel`` instead.

이 모듈은 ``dartlab.credit.chsModel`` 으로 이주됐다 (S6). 새 코드는 새 경로를 사용. 이
shim 은 다음 메이저에서 제거 예정.
"""

from warnings import warn

from dartlab.credit.chsModel import *  # noqa: F401, F403

warn(
    "dartlab.core.finance.chsModel → dartlab.credit.chsModel (deprecated, removed in next major)",
    DeprecationWarning,
    stacklevel=2,
)
