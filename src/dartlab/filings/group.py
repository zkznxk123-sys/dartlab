"""다회사 facade — companies([...]) 회사 간 수평화 (같은 canonical 키 정렬).

LLM Specifications:
    AntiPatterns:
        - 전 회사 contentRaw eager 적재 금지 — 회사별 show per-query 후 stack.
        - 회사별 메모리 미회수 금지 — 대량 시 Company with-block 권장.
    OutputSchema:
        - ``companies(codes) -> Group`` (.show(key) / .sections).
    Prerequisites:
        - 각 회사 sections/finance/report 데이터.
    TargetMarkets:
        - 단일 marketNs 내 회사 간 (cross-market 비교는 별도).
"""

from __future__ import annotations

import polars as pl

from dartlab.filings.company import Company


class Group:
    """여러 회사 묶음 — show/sections 를 corp 라벨로 stack (회사 간 비교)."""

    def __init__(self, codes, marketNs: str = "kr"):
        self.marketNs = marketNs
        self.members = [Company(c, marketNs) for c in codes]

    def show(self, key: str, **kw) -> pl.DataFrame | None:
        """각 회사 show(key) 를 corp 컬럼 달아 stack — 같은 canonical 키 회사 간 정렬."""
        frames = []
        for c in self.members:
            df = c.show(key, **kw)
            if df is not None and not df.is_empty():
                frames.append(df.with_columns(pl.lit(c.code).alias("corp")))
        if not frames:
            return None
        return pl.concat(frames, how="diagonal_relaxed")

    @property
    def sections(self) -> pl.DataFrame | None:
        """각 회사 sections 구조 board 를 corp 컬럼 달아 stack."""
        frames = []
        for c in self.members:
            m = c.sections
            if m is not None and not m.is_empty():
                frames.append(m.with_columns(pl.lit(c.code).alias("corp")))
        if not frames:
            return None
        return pl.concat(frames, how="diagonal_relaxed")

    def __repr__(self) -> str:
        return f"Group({[c.code for c in self.members]!r}, marketNs={self.marketNs!r})"


def companies(codes, marketNs: str = "kr") -> Group:
    """다회사 Group 생성.

    Args:
        codes: 종목코드 iterable.
        marketNs: 시장 namespace.

    Returns:
        Group.
    """
    return Group(codes, marketNs)
