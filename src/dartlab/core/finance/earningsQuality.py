"""Deprecated — use ``dartlab.analysis.financial.earningsQuality`` instead.

이 모듈의 base 계산 함수들 (``calcBeneishMScore``, ``calcSloanAccruals``,
``detectAuditFlags``, ``_calcEarningsQualityFlagsBase``) 은
``dartlab.analysis.financial.earningsQuality`` 로 흡수됐다 (S5b — 동명 wrapper 와 머지).
새 코드는 새 경로를 사용. 이 shim 은 다음 메이저에서 제거 예정.

주의: ``calcEarningsQualityFlags`` 는 머지 시 동명 충돌로 ``_calcEarningsQualityFlagsBase``
로 rename 됐다. 외부 사용자가 옛 이름으로 import 하면 깨질 수 있어 별칭도 export.
"""

from warnings import warn

from dartlab.analysis.financial.earningsQuality import (
    _calcEarningsQualityFlagsBase as calcEarningsQualityFlags,  # noqa: F401
)
from dartlab.analysis.financial.earningsQuality import (
    calcBeneishMScore,  # noqa: F401
    calcSloanAccruals,  # noqa: F401
    detectAuditFlags,  # noqa: F401
)

warn(
    "dartlab.core.finance.earningsQuality → dartlab.analysis.financial.earningsQuality "
    "(deprecated, removed in next major)",
    DeprecationWarning,
    stacklevel=2,
)
