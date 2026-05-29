"""HF download 공통 메커니즘 — market 이 repo/path 주입 (filings 자체 loader).

옛 `core.dataLoader` (깨진 docs path) 우회. 로컬 parquet 이 있으면 그대로 사용,
없을 때만 HF 에서 단건 다운로드. filings 독립성 유지 (providers/dataLoader 의존 0).

LLM Specifications:
    AntiPatterns:
        - dartlab.core.dataLoader import 금지 — filings 독립.
        - 매 호출 네트워크 접근 금지 — 로컬 존재 시 즉시 반환.
    OutputSchema:
        - ``downloadIfMissing(localPath, url) -> Path``.
    Prerequisites:
        - urllib (stdlib). market 가 HF URL 구성.
    TargetMarkets:
        - 공통 (URL 은 market config 가 제공).
"""

from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request
from pathlib import Path

_log = logging.getLogger(__name__)


def downloadIfMissing(
    localPath: str | Path,
    url: str,
    *,
    refresh: bool = False,
    retries: int = 3,
    timeout: int = 60,
) -> Path | None:
    """로컬 parquet 없으면 HF URL 에서 다운로드 (있으면 즉시 반환).

    Args:
        localPath: 로컬 저장 경로.
        url: HF resolve URL.
        refresh: True 면 존재해도 재다운로드.
        retries: 재시도 횟수 (지수 백오프).
        timeout: 소켓 타임아웃(초).

    Returns:
        로컬 Path (성공) 또는 None (다운로드 실패).
    """
    p = Path(localPath)
    if p.exists() and not refresh:
        return p
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    for attempt in range(retries):
        try:
            urllib.request.urlretrieve(url, str(tmp))  # noqa: S310 — HF https only
            tmp.replace(p)
            return p
        except (OSError, urllib.error.URLError) as exc:
            _log.warning("download 실패 (%d/%d) %s: %s", attempt + 1, retries, url, exc)
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            if attempt < retries - 1:
                time.sleep(2**attempt)
    return None
