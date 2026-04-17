"""호환 shim — 새 코드는 dartlab.core.messaging을 사용하세요."""

from dartlab.core.messaging import (  # noqa: F401
    _SIMPLE,
    _STRUCTURED,
    _ctx,
    _StructuredMsg,
    emit,
    format,
    progress,
    suggest,
)
