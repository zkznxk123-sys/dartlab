"""M2: src/dartlab 의 ``.collect()`` 호출 중 streaming engine 명시 비율 강제.

Polars LazyFrame.collect() 호출 시 ``engine="streaming"`` 명시 비율이 baseline
이상이어야 한다. M2-1~M2-6 도입 후 ~100 곳 streaming 명시 — 회귀 차단.

미지원 22~27 호출부 (pivot/over/asof) 는 inline 주석 마커로 분리.

비율 = streaming_count / (total_collect_count - gc.collect - unsupported)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parent.parent.parent
_SCAN_ROOTS = ("src/dartlab",)

_RE_STREAMING_COLLECT = re.compile(r'\.collect\(\s*engine\s*=\s*["\']streaming["\']')
# .collect() 단독 (engine 인자 없음). gc.collect() 는 word-boundary 로 분리.
_RE_BARE_COLLECT = re.compile(r"(?<![A-Za-z_])(?<!gc)\.collect\(\s*\)")
_RE_UNSUPPORTED_MARKER = re.compile(r"polars-streaming-unsupported")

# M2-6 baseline (2026-05-12): streaming 86 + bare 0 + unsupported 27 = 86/86 = 100%
_MIN_STREAMING_RATIO = 0.80


def _scanCounts() -> tuple[int, int, int]:
    """src/dartlab 전수 streaming/bare/unsupported 카운트 반환."""
    streaming = 0
    bare = 0
    unsupported = 0
    for root in _SCAN_ROOTS:
        for p in (_REPO / root).rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for line in text.splitlines():
                if _RE_UNSUPPORTED_MARKER.search(line):
                    unsupported += 1
                    continue
                streaming += len(_RE_STREAMING_COLLECT.findall(line))
                bare += len(_RE_BARE_COLLECT.findall(line))
    return streaming, bare, unsupported


def test_streaming_ratio_above_baseline():
    """``.collect(engine="streaming")`` 비율 ≥ 80% — M2 일괄 도입 회귀 가드."""
    streaming, bare, unsupported = _scanCounts()
    polarsCalls = streaming + bare  # gc.collect, ZipDocsCollector.collect 제외
    assert polarsCalls > 0, "polars collect 호출 0 — scan 로직 부재 의심"
    ratio = streaming / polarsCalls
    assert ratio >= _MIN_STREAMING_RATIO, (
        f"streaming engine 명시 비율 {ratio:.1%} < {_MIN_STREAMING_RATIO:.0%}. "
        f"streaming={streaming} bare={bare} unsupported={unsupported}. "
        f"신규 `.collect()` 는 `.collect(engine='streaming')` 명시 (M2)."
    )


def test_streaming_count_above_baseline():
    """streaming 명시 절대 카운트 ≥ 60 — 회귀 시 알람."""
    streaming, bare, unsupported = _scanCounts()
    assert streaming >= 60, (
        f"streaming 명시 {streaming} 곳 < 60 baseline. M2 회귀 의심. bare={bare} unsupported={unsupported}."
    )
