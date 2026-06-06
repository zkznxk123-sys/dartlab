"""`dartlab sections` compatibility command backed by panel."""

from __future__ import annotations

import polars as pl

from dartlab.cli.services.errors import CLIError
from dartlab.cli.services.runtime import configureDartlab


def configureParser(subparsers) -> None:
    """sections 서브커맨드 등록 — panel 공시 격자 출력."""
    parser = subparsers.add_parser("sections", help="panel 공시 격자 출력")
    parser.add_argument("company", help="종목코드 (005930) 또는 회사명 (삼성전자)")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="태그 보존 (viewer 양식, HTML <table rowspan colspan>). 기본은 태그 제거 plain text.",
    )
    parser.set_defaults(handler=run)


def run(args) -> int:
    """panel 공시 수평화 보드를 콘솔에 출력한다 (docs 농장 은퇴 → c.panel)."""
    from dartlab.cli.services.output import getConsole, printDataframe

    dartlab = configureDartlab()
    console = getConsole()

    try:
        company = dartlab.Company(args.company)
    except (ValueError, FileNotFoundError, OSError, RuntimeError) as exc:
        from dartlab.cli.services.errors import wrapError

        raise CLIError(wrapError(exc, stockCode=args.company)) from exc

    console.print(f"\n  [bold]{company.corpName}[/] ({company.stockCode})\n")

    # CLI 기본 — plain text(tag=False). --raw 시 원본 XML 태그 보존(tag=True).
    panel = company.panel(tag=args.raw)
    if panel is None:
        console.print(f"[dim]{company.corpName} panel 데이터가 없습니다.[/]")
        return 0
    if not isinstance(panel, pl.DataFrame):
        console.print("[bold red]오류:[/] panel 데이터 형식이 올바르지 않습니다.")
        return 1
    printDataframe(panel, title="Panel")
    return 0
