"""Deprecated — use ``dartlab.core.cross.corporateAggregate`` instead.

이 모듈은 ``dartlab.core.cross.corporateAggregate`` 으로 이주됐다 (S8). 새 코드는 새 경로를 사용. 이
shim 은 다음 메이저에서 제거 예정 — 그때 core/finance/ 폴더 자체도 삭제.
"""

from warnings import warn

from dartlab.core.cross.corporateAggregate import *  # noqa: F401, F403

warn(
    "dartlab.core.finance.corporateAggregate → dartlab.core.cross.corporateAggregate (deprecated, removed in next major)",
    DeprecationWarning,
    stacklevel=2,
)
