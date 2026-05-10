"""Console output helpers for CLI commands — Rich 기반."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from dartlab.core.formatting import formatComma

if TYPE_CHECKING:
    import polars as pl

_console = Console()
_err_console = Console(stderr=True)


def getConsole() -> Console:
    """공용 Rich Console 반환."""
    return _console


def printError(message: str) -> None:
    """오류 메시지를 stderr에 출력."""
    from rich.markup import escape

    _err_console.print(f"[bold red]오류:[/] {escape(message)}")


def printInfo(message: str = "") -> None:
    """일반 정보 메시지 출력."""
    _console.print(message)


def printWarning(message: str) -> None:
    """경고 메시지를 stderr에 출력."""
    _err_console.print(f"[bold yellow]경고:[/] {message}")


def _isNumericCol(dtypeStr: str) -> bool:
    """Polars dtype 문자열이 숫자형인지 판별."""
    return bool(re.search(r"(Int|UInt|Float|Decimal)", dtypeStr))


def _formatNumber(val) -> str:
    """숫자 포맷: 천단위 쉼표, 소수점 유지 (None/NaN → 빈 문자열)."""
    return formatComma(val, decimals=2, nullStr="")


def printDataframe(
    df: "pl.DataFrame",
    *,
    title: str | None = None,
    maxRows: int = 50,
) -> None:
    """Polars DataFrame을 Rich Table로 렌더링.

    - 숫자 우정렬, 천단위 쉼표
    - 양수/음수 색상 구분
    - 최대 max_rows행 표시
    """
    if df.is_empty():
        _console.print("[dim]데이터가 없습니다.[/]")
        return

    table = Table(title=title, show_lines=False, padding=(0, 1))
    schema = df.schema

    for col_name in df.columns:
        dtypeStr = str(schema[col_name])
        justify = "right" if _isNumericCol(dtypeStr) else "left"
        table.add_column(col_name, justify=justify, no_wrap=True)

    display_df = df.head(maxRows)
    for row in display_df.iter_rows(named=True):
        cells = []
        for col_name in df.columns:
            val = row[col_name]
            dtypeStr = str(schema[col_name])
            if _isNumericCol(dtypeStr):
                formatted = _formatNumber(val)
                if isinstance(val, (int, float)) and val is not None:
                    if isinstance(val, float) and val != val:
                        cells.append("")
                    elif val < 0:
                        cells.append(f"[red]{formatted}[/]")
                    else:
                        cells.append(formatted)
                else:
                    cells.append(formatted)
            elif val is None:
                cells.append("")
            else:
                cells.append(str(val))
        table.add_row(*cells)

    _console.print(table)
    if len(df) > maxRows:
        _console.print(f"[dim]... {len(df) - maxRows}행 추가 (총 {len(df)}행)[/]")


def printSearchResults(results: "pl.DataFrame") -> None:
    """dartlab.search() 결과를 Rich Table로 표시."""
    printDataframe(results, title="검색 결과")
