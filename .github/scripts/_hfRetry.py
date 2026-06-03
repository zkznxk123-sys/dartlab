"""(shim) HF retry helper — 본체는 dartlab.core.hfRetry 로 L0 승격.

본 파일은 ``.github/scripts`` 의 기존 호출부(`from _hfRetry import retryHfCall`) 호환용
re-export 만 남긴다. 신규 코드는 ``dartlab.core.hfRetry`` 를 직접 쓴다.
"""

from __future__ import annotations

from dartlab.core.hfRetry import parseRetryWait, retryHfCall  # noqa: F401

__all__ = ["parseRetryWait", "retryHfCall"]
