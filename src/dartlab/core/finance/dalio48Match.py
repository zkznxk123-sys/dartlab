"""Deprecated — use ``dartlab.core.cross.dalio48Match`` instead.

이 모듈은 ``dartlab.core.cross.dalio48Match`` 으로 이주됐다 (S8). 새 코드는 새 경로를 사용. 이
shim 은 다음 메이저에서 제거 예정 — 그때 core/finance/ 폴더 자체도 삭제.
"""

from warnings import warn

from dartlab.core.cross.dalio48Match import *  # noqa: F401, F403

warn(
    "dartlab.core.finance.dalio48Match → dartlab.core.cross.dalio48Match (deprecated, removed in next major)",
    DeprecationWarning,
    stacklevel=2,
)
