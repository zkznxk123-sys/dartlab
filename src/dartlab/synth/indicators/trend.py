"""trend indicators 호환 re-export.

새 SSOT 는 ``dartlab.core.indicators.trend`` 다. 기존
``dartlab.synth.indicators.trend`` import 경로 보존용.
"""

from __future__ import annotations

from dartlab.core.indicators.trend import (  # noqa: F401
    vadx,
    vdema,
    vema,
    vhma,
    vmacd,
    vpsar,
    vsma,
    vsupertrend,
    vtema,
    vtrix,
    vvwma,
    vwma,
)
