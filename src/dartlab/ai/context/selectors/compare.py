"""Compare selector: scan 횡단분석 결과 주입."""

from __future__ import annotations

from typing import Any

from dartlab.ai.context.bundle import ContextPart, PartPriority
from dartlab.ai.context.encoder import encodeAuto, estimateTokens


def selectCompare(company: Any) -> list[ContextPart]:
    """scan profitability 결과에서 해당 종목 위치 + 상하위 5개 주입."""
    if company is None:
        return []
    stockCode = getattr(company, "stockCode", None) or getattr(company, "ticker", None)
    if not stockCode:
        return []
    try:
        import dartlab

        df = dartlab.scan("profitability")
    except (ImportError, FileNotFoundError, OSError, RuntimeError):
        return []
    if df is None or len(df) == 0:
        return []

    # 해당 종목 행 찾기
    try:
        code_col = "종목코드" if "종목코드" in df.columns else "stockCode"
        if code_col not in df.columns:
            return []
        my_row = df.filter(df[code_col] == stockCode)
        if len(my_row) == 0:
            return []
        # 상하위 5개 + 내 위치
        rank_col = "영업이익률_rank" if "영업이익률_rank" in df.columns else None
        if rank_col:
            my_rank = my_row[rank_col][0]
            nearby = df.sort(rank_col).slice(max(0, int(my_rank) - 3), 7)
            data = nearby.to_dicts()
        else:
            data = my_row.to_dicts()
    except (KeyError, IndexError, TypeError, ValueError):
        return []

    if not data:
        return []
    text_body = encodeAuto(data)
    text = f'<context source="scan:profitability">\n## 동종업계 수익성 비교 ({stockCode})\n{text_body}\n</context>'
    return [
        ContextPart(
            key="compare.profitability",
            text=text,
            priority=PartPriority.HIGH,
            estimatedTokens=estimateTokens(text),
            source="scan:profitability",
        )
    ]
