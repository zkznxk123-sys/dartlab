"""`dartlab update` command -- 로컬 데이터를 HuggingFace 최신으로 갱신.

사용 예시::

    dartlab update                   # 로컬 finance+report 파일 갱신 확인 (기본)
    dartlab update --all             # 로컬 finance+report+panel 파일 갱신 확인
    dartlab update -c finance        # finance만
    dartlab update 005930            # 특정 종목만 갱신
    dartlab update 005930 -c panel   # 특정 종목 panel만
"""

from __future__ import annotations


def configureParser(subparsers) -> None:
    """update 서브커맨드 등록."""
    parser = subparsers.add_parser(
        "update",
        help="로컬 데이터를 HuggingFace 최신으로 갱신",
    )
    parser.add_argument(
        "codes",
        nargs="*",
        help="종목코드 (생략 시 전체 갱신)",
    )
    parser.add_argument(
        "--categories",
        "-c",
        type=str,
        default=None,
        help="카테고리 (쉼표 구분: finance,report,panel)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="panel 포함 로컬 파일 갱신 확인 (기본은 finance+report만)",
    )
    parser.set_defaults(handler=run)


def run(args) -> int:
    """로컬 데이터를 HF 최신으로 갱신."""
    from dartlab.cli.services.output import getConsole

    console = getConsole()

    if args.codes:
        return _updateCodes(console, args)
    return _updateAll(console, args)


def _updateCodes(console, args) -> int:
    """특정 종목 데이터를 HF에서 최신으로 갱신."""
    from dartlab.core.dataLoader import loadData

    cats = _parseCategories(args)
    updated = 0

    from dartlab.core.memory import cleanupBetweenCompanies

    for code in args.codes:
        for cat in cats:
            console.print(f"  {code}/{cat}: 확인 중...")
            try:
                loadData(code, cat, refresh="force_check")
                console.print(f"  {code}/{cat}: OK")
                updated += 1
            except (RuntimeError, FileNotFoundError, ValueError) as e:
                console.print(f"  {code}/{cat}: [red]{e}[/]")
        # M8: 회사 사이마다 누적 캐시 회수 — 다중 회사 force_check 시 RSS 누적 차단
        cleanupBetweenCompanies(label=code)

    console.print(f"\n확인 완료: {updated}건")
    return 0


def _updateAll(console, args) -> int:
    """로컬에 존재하는 파일만 HF 최신 여부를 확인하고 갱신."""
    from dartlab.core.dataConfig import resolveDataCategory
    from dartlab.core.dataLoader import _dataDir, loadData

    cats = [resolveDataCategory(cat) for cat in _parseCategories(args)]
    updated = 0

    for cat in cats:
        dataDir = _dataDir(cat)
        files = sorted(path for path in dataDir.glob("*.parquet") if not path.name.startswith("_"))
        if not files:
            console.print(f"[yellow]{cat}: 로컬 파일 없음 — 건너뜀[/]")
            continue

        console.print(f"[bold]{cat}[/] {len(files)}개 로컬 파일 갱신 확인...")
        for path in files:
            code = path.stem
            try:
                loadData(code, cat, refresh="force_check")
                updated += 1
            except (RuntimeError, FileNotFoundError, ValueError) as e:
                console.print(f"  {code}/{cat}: [red]{e}[/]")

    console.print(f"\n확인 완료: {updated}건")

    return 0


def _parseCategories(args) -> list[str]:
    """카테고리 파싱."""
    if args.categories:
        return [c.strip() for c in args.categories.split(",")]
    if getattr(args, "all", False):
        return ["finance", "report", "panel"]
    return ["finance", "report"]
