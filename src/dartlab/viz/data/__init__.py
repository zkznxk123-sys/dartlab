"""viz/data — raw 가공 헬퍼 진입점 (catalog/builder 가 lookup).

기존 `display/finance/{normalize, periods, statements, ratios, accounts, _cache}.py`
의 통합 진입점. 물리 이동 없이 re-export — `display/finance/views.py` 의 기존
호출자도 그대로 작동.

builder.py 가 `from dartlab.viz.data import statements, ratios, _cache, normalize`
한 줄로 모든 헬퍼 접근.
"""

from __future__ import annotations

from dartlab.viz.display.finance import (
    _cache,
    accounts,
    normalize,
    periods,
    ratios,
    statements,
)
from dartlab.viz.display.finance.normalize import normalize as normalizeRaw

__all__ = [
    "_cache",
    "accounts",
    "normalize",
    "normalizeRaw",
    "periods",
    "ratios",
    "statements",
]
