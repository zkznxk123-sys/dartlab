"""DART/EDGAR 공통 타입 + L0 layer-neutral schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple

import polars as pl


class ShowResult(NamedTuple):
    """docs.show() 반환 — text와 table을 분리."""

    text: pl.DataFrame | None
    table: pl.DataFrame | None


# ── L0 강등 — L2 analysis/valuation 의존성 해소 (정공법 A — Hierarchy) ──


@dataclass
class PeerData:
    """피어 기업 멀티플 데이터."""

    ticker: str = ""
    name: str = ""
    per: float | None = None
    pbr: float | None = None
    ev_ebitda: float | None = None
    marketCap: float | None = None

    def __repr__(self) -> str:
        parts = [f"{self.ticker}({self.name})"]
        if self.per is not None:
            parts.append(f"PER={self.per:.1f}")
        if self.pbr is not None:
            parts.append(f"PBR={self.pbr:.2f}")
        if self.ev_ebitda is not None:
            parts.append(f"EV/EBITDA={self.ev_ebitda:.1f}")
        return " ".join(parts)


@dataclass
class MarketSnapshot:
    """Analyst 호환 flat 시장 데이터 — L2 analysis 가 caller 로부터 받아 사용."""

    stockCode: str = ""
    currentPrice: float = 0.0
    multiples: dict[str, float] = field(default_factory=dict)
    peer_multiples: list[PeerData] = field(default_factory=list)
    supply_demand: dict[str, float] = field(default_factory=dict)
    macro: dict[str, float] = field(default_factory=dict)
    price_range_52w: tuple[float, float] | None = None
    collected_at: str = ""
    sourcesAvailable: list[str] = field(default_factory=list)
    sourcesFailed: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        lines = [f"[MarketSnapshot — {self.stockCode}]"]
        if self.currentPrice:
            lines.append(f"  price: {self.currentPrice:,.0f}")
        if self.multiples:
            mm = " ".join(f"{k}={v:.2f}" for k, v in self.multiples.items() if v is not None)
            lines.append(f"  multiples: {mm}")
        if self.peer_multiples:
            lines.append(f"  peers: {len(self.peer_multiples)}")
        return "\n".join(lines)
