"""CLI 진입 — ``python -m dartlab.gather.original dart|edgar ...``.

공시 오리지널 수집 모듈의 배치 실행 진입점. 패키지 안에 entry 를 두어 자체포함을
유지한다(별도 sync 스크립트 불요).

사용법::

    python -m dartlab.gather.original dart  --start 20260601 --end 20260603 --scope nonperiodic
    python -m dartlab.gather.original edgar --tickers AAPL,MSFT --forms 8-K --since-year 2024
"""

from __future__ import annotations

import argparse
import sys

from .dart import archiveDartOriginals
from .edgar import archiveEdgarOriginals


def _buildParser() -> argparse.ArgumentParser:
    """CLI 인자 파서 구성(dart/edgar 서브커맨드).

    Returns:
        argparse.ArgumentParser — 구성된 파서.

    Raises:
        없음.

    Example:
        >>> _buildParser().prog.endswith("original")  # doctest: +SKIP
        True
    """
    parser = argparse.ArgumentParser(
        prog="python -m dartlab.gather.original",
        description="공시 오리지널 수집 — DART(정기+비정기) + EDGAR(전 form) 가공 0 원본 백업",
    )
    sub = parser.add_subparsers(dest="provider", required=True)

    dart = sub.add_parser("dart", help="DART document.xml 원본 zip 수집")
    dart.add_argument("--start", required=True, help="시작일 YYYYMMDD")
    dart.add_argument("--end", required=True, help="종료일 YYYYMMDD")
    dart.add_argument("--scope", default="all", choices=["all", "periodic", "nonperiodic"])
    dart.add_argument("--workers", type=int, default=4, help="document.xml 병렬 워커")
    dart.add_argument("--no-progress", dest="noProgress", action="store_true")

    edgar = sub.add_parser("edgar", help="EDGAR full submission .txt 원본 수집")
    edgar.add_argument("--tickers", required=True, help="ticker/CIK 쉼표 구분 (예: AAPL,MSFT)")
    edgar.add_argument("--forms", default=None, help="form 화이트리스트 쉼표 구분 (예: 8-K,10-K). 미지정=전 form")
    edgar.add_argument("--since-year", dest="sinceYear", type=int, default=2009, help="시작 연도")
    edgar.add_argument("--no-progress", dest="noProgress", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 본체 — dart/edgar 수집을 실행하고 집계를 출력.

    Capabilities:
        - ``dart``: ``archiveDartOriginals(start, end, scope, workers)`` 위임.
        - ``edgar``: ``archiveEdgarOriginals(tickers, forms, sinceYear)`` 위임.
          집계 dict 를 stdout 출력하고 exit code 반환.

    Args:
        argv: 인자 list(테스트용). None 이면 ``sys.argv[1:]``.

    Returns:
        int — 0(성공) / 2(인자 오류는 argparse 가 SystemExit).

    Raises:
        SystemExit: argparse 인자 오류/도움말.

    Example:
        >>> main(["dart", "--start", "20260601", "--end", "20260601", "--scope", "nonperiodic"])  # doctest: +SKIP
        0

    Guide:
        - DART 는 ``DART_API_KEY(S)`` 필요. EDGAR 는 keyless(User-Agent).

    SeeAlso:
        - ``archiveDartOriginals`` · ``archiveEdgarOriginals`` — 실제 수집 본체.

    Requires:
        - DART: ``DART_API_KEY(S)``. EDGAR: 인터넷 + SEC User-Agent.

    When:
        - 운영자가 셸에서 ``python -m dartlab.gather.original ...`` 로 백업을 돌릴 때.

    How:
        - argparse 로 provider 서브커맨드 분기 → archiveDart/Edgar 위임 → 집계 출력.

    AIContext:
        운영자/배치 CLI — AI 분석 흐름 아님.

    LLM Specifications:
        AntiPatterns:
            - 분석 도중 호출 X — 배치 수집 전용.
        OutputSchema:
            - int(exit code) + stdout 집계 dict.
        Prerequisites:
            - provider 서브커맨드 + 필수 인자.
        Freshness:
            - 매 실행 재열거 + 기존 파일 skip.
        Dataflow:
            - argv → archive* 위임 → stdout 집계.
        TargetMarkets:
            - KR(DART) · US(EDGAR).
    """
    parser = _buildParser()
    args = parser.parse_args(argv)
    showProgress = not args.noProgress

    if args.provider == "dart":
        stats = archiveDartOriginals(
            args.start,
            args.end,
            scope=args.scope,
            workers=args.workers,
            showProgress=showProgress,
        )
    else:
        forms = [f.strip() for f in args.forms.split(",") if f.strip()] if args.forms else None
        tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
        stats = archiveEdgarOriginals(
            tickers,
            forms=forms,
            sinceYear=args.sinceYear,
            showProgress=showProgress,
        )

    print(stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
