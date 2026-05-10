"""`dartlab story` — 기업 분석 스토리 (rich 렌더링).

사용 예시::

    dartlab story 005930               # 전체 보고서
    dartlab story 005930 수익구조       # 특정 섹션

AI 종합의견이 필요하면 `dartlab ask "005930 종합 분석 해줘"` 사용.
"""

from __future__ import annotations

from dartlab.cli.services.errors import CLIError
from dartlab.cli.services.runtime import configureDartlab


def configureParser(subparsers) -> None:
    """story 서브커맨드 등록 — 기업 분석 스토리."""
    parser = subparsers.add_parser("story", help="기업 분석 스토리 (사람이 읽는 보고서)")
    parser.add_argument("company", help="종목코드 (005930) 또는 회사명 (삼성전자)")
    parser.add_argument("section", nargs="?", default=None, help="분석 섹션 (수익구조 등). 기본: 전체")
    parser.set_defaults(handler=_runStory)


def _runStory(args) -> int:
    """기업 분석 스토리."""
    dartlab = configureDartlab()

    try:
        company = dartlab.Company(args.company)
    except (ValueError, FileNotFoundError, OSError, RuntimeError) as exc:
        from dartlab.cli.services.errors import wrapError

        raise CLIError(wrapError(exc, stockCode=args.company)) from exc

    from dartlab.story.registry import buildStory

    report = buildStory(company, section=args.section)
    return _printReport(report, args)


def _printReport(report, args) -> int:
    """보고서 렌더링."""
    from dartlab.cli.services.output import getConsole
    from dartlab.story.renderer import renderStory

    if not report.sections:
        console = getConsole()
        name = getattr(report, "corpName", args.company) or args.company
        if args.section:
            console.print(f"  [yellow]'{args.section}' 섹션에 대한 분석 결과가 없습니다.[/]")
        else:
            console.print(f"  [yellow]{name} — 분석 결과가 없습니다.[/]")
        return 0

    console = getConsole()
    renderStory(console, report)
    return 0
