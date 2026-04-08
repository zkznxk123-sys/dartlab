"""Rule — boolean entry/exit + sizing/stop 명시 주입.

dartlab Strategy DSL 의 핵심 객체. 가중치 필드 없음 — 사용자가 boolean 으로 직접
컴포즈. sizing/stop 은 명시 안 하면 equal 1.0 / no stop.

사용 예:
    >>> from dartlab.quant.strategy import Rule
    >>> rule = (
    ...     Rule.entry(rsi_oversold & regime_bull)
    ...         .exit(rsi_overbought)
    ...         .with_sizing("kelly", k=0.25)
    ...         .with_stop("atr", k=3.0)
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Rule:
    """boolean entry/exit + sizing/stop 핸들 보관 (가중치 없음).

    Attributes:
        entry_expr: boolean numpy array (True = 진입 시그널)
        exit_expr: boolean numpy array (True = 청산 시그널)
        sizing: dict {method: str, kwargs: dict} — None 이면 equal 1.0
        stop: dict {method: str, kwargs: dict} — None 이면 no stop
        meta: 식별자/주석 (백테스트 결과에 포함)
    """

    entry_expr: np.ndarray
    exit_expr: np.ndarray
    sizing: dict[str, Any] | None = None
    stop: dict[str, Any] | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        ent = np.asarray(self.entry_expr)
        ex = np.asarray(self.exit_expr)
        if ent.dtype != np.bool_:
            ent = ent.astype(np.bool_)
        if ex.dtype != np.bool_:
            ex = ex.astype(np.bool_)
        if len(ent) != len(ex):
            raise ValueError(f"entry/exit length mismatch: {len(ent)} vs {len(ex)}")
        self.entry_expr = ent
        self.exit_expr = ex

    @classmethod
    def entry(cls, expr) -> "_RuleBuilder":
        """체이닝 빌더 시작점."""
        return _RuleBuilder(entry=expr)

    def with_sizing(self, method: str, **kwargs) -> "Rule":
        """포지션 사이징 명시 — kelly / vol_target / risk_budget / equal.

        명시 안 하면 equal 1.0 (전 자본 진입).
        """
        return Rule(
            entry_expr=self.entry_expr,
            exit_expr=self.exit_expr,
            sizing={"method": method, "kwargs": kwargs},
            stop=self.stop,
            meta=self.meta,
        )

    def with_stop(self, method: str, **kwargs) -> "Rule":
        """손절 명시 — atr / fixed_pct / chandelier.

        명시 안 하면 no stop (entry/exit 시그널만 사용, 홀드).
        """
        return Rule(
            entry_expr=self.entry_expr,
            exit_expr=self.exit_expr,
            sizing=self.sizing,
            stop={"method": method, "kwargs": kwargs},
            meta=self.meta,
        )

    def with_meta(self, **kw) -> "Rule":
        merged = {**self.meta, **kw}
        return Rule(
            entry_expr=self.entry_expr,
            exit_expr=self.exit_expr,
            sizing=self.sizing,
            stop=self.stop,
            meta=merged,
        )

    def __len__(self) -> int:
        return len(self.entry_expr)

    def __repr__(self) -> str:
        n = len(self.entry_expr)
        n_entry = int(np.sum(self.entry_expr))
        n_exit = int(np.sum(self.exit_expr))
        sz = self.sizing["method"] if self.sizing else "equal"
        st = self.stop["method"] if self.stop else "none"
        return f"Rule(len={n}, entries={n_entry}, exits={n_exit}, sizing={sz}, stop={st})"


@dataclass
class _RuleBuilder:
    """Rule 체이닝 빌더 — Rule.entry(...).exit(...) 패턴 sugar."""

    entry: Any

    def exit(self, expr) -> Rule:
        return Rule(entry_expr=self.entry, exit_expr=expr)
