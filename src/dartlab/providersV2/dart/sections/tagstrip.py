"""contentRaw (raw XML) → plain text — 호출 시점 변환 (사전 파생 0).

요구 #4: contentRaw 단일 무손실 컬럼. plain text 는 디스크에 사전 계산하지 않고
show/agent 호출 시점에 polars expr 로 변환 (content_plain 컬럼 신설 금지).

LLM Specifications:
    AntiPatterns:
        - content_plain 컬럼 사전 계산/저장 금지 — 호출 시점 strip only.
        - lxml parse 로 strip 금지 (느림) — polars regex SIMD.
    OutputSchema:
        - ``stripExpr(col) -> pl.Expr`` / ``stripValue(str) -> str``.
    Prerequisites:
        - polars.
    Dataflow:
        - contentRaw → tag 제거 + 공백 정리 → plain text.
    TargetMarkets:
        - KR + US 공통 (XML/HTML 태그 공통 양식).
"""

from __future__ import annotations

import re

import polars as pl

_TAG_RE = r"<[^>]+>"
_PY_TAG_RE = re.compile(_TAG_RE)
_PY_WS_RE = re.compile(r"[ \t]*\n[ \t\n]*")
_PY_SPACE_RE = re.compile(r"[ \t]{2,}")


def stripExpr(col: str = "contentRaw") -> pl.Expr:
    """raw XML 컬럼 → plain text polars expr (태그 제거 + 다중공백 정리).

    Examples:
        >>> import polars as pl
        >>> df = pl.DataFrame({"contentRaw": ["<P>안녕<SPAN>하세요</SPAN></P>"]})
        >>> df.select(stripExpr())["contentRaw"][0]
        '안녕하세요'
    """
    return pl.col(col).str.replace_all(_TAG_RE, "").str.replace_all(r"[ \t]{2,}", " ").str.strip_chars().alias(col)


def stripValue(raw: str | None) -> str:
    """단일 raw XML str → plain text.

    Args:
        raw: raw XML/HTML 문자열.

    Returns:
        태그 제거 + 공백 정리 plain text. None → "".
    """
    if not raw:
        return ""
    s = _PY_TAG_RE.sub("", raw)
    s = _PY_WS_RE.sub("\n", s)
    s = _PY_SPACE_RE.sub(" ", s)
    return s.strip()
