"""`dartlab sections` command."""

from __future__ import annotations

import polars as pl

from dartlab.cli.services.errors import CLIError
from dartlab.cli.services.runtime import configureDartlab


def configureParser(subparsers) -> None:
    """sections 서브커맨드 등록 — pure docs 수평화 sections 출력."""
    parser = subparsers.add_parser("sections", help="pure docs 수평화 sections 출력")
    parser.add_argument("company", help="종목코드 (005930) 또는 회사명 (삼성전자)")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="태그 보존 (viewer 양식, HTML <table rowspan colspan>). 기본은 태그 제거 plain text.",
    )
    parser.set_defaults(handler=run)


def run(args) -> int:
    """docs.sections DataFrame을 콘솔에 출력한다."""
    from dartlab.cli.services.output import getConsole, printDataframe

    dartlab = configureDartlab()
    console = getConsole()

    try:
        company = dartlab.Company(args.company)
    except (ValueError, FileNotFoundError, OSError, RuntimeError) as exc:
        from dartlab.cli.services.errors import wrapError

        raise CLIError(wrapError(exc, stockCode=args.company)) from exc

    console.print(f"\n  [bold]{company.corpName}[/] ({company.stockCode})\n")

    # CLI 기본 — stripTags=True (콘솔 plain text). --raw 시 mixed (태그 보존).
    sections = company.sectionsAs(stripTags=not args.raw)
    if sections is None:
        console.print(f"[dim]{company.corpName} sections 데이터가 없습니다.[/]")
        return 0
    if not isinstance(sections, pl.DataFrame):
        console.print("[bold red]오류:[/] sections 데이터 형식이 올바르지 않습니다.")
        return 1
    printDataframe(sections, title="Sections")
    return 0
