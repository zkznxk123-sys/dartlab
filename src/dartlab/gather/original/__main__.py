"""CLI 진입 — ``python -m dartlab.gather.original dart ...``.

공시 오리지널 수집 모듈의 배치 실행 진입점. 패키지 안에 entry 를 두어 자체포함을
유지한다(별도 sync 스크립트 불요).

사용법::

    python -m dartlab.gather.original dart --start 20260601 --end 20260603 --scope nonperiodic
"""

from __future__ import annotations

import argparse
import sys

from .dart import archiveDartOriginals


def _buildParser() -> argparse.ArgumentParser:
    """CLI 인자 파서 구성(DART 원본 zip 수집).

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
        description="공시 오리지널 수집 — DART(정기+비정기) document.xml zip 원본 백업",
    )
    sub = parser.add_subparsers(dest="provider", required=True)

    dart = sub.add_parser("dart", help="DART document.xml 원본 zip 수집")
    dart.add_argument("--start", required=True, help="시작일 YYYYMMDD")
    dart.add_argument("--end", required=True, help="종료일 YYYYMMDD")
    dart.add_argument("--scope", default="all", choices=["all", "periodic", "nonperiodic"])
    dart.add_argument("--workers", type=int, default=4, help="document.xml 병렬 워커")
    dart.add_argument("--no-progress", dest="noProgress", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 본체 — DART 원본 zip 수집을 실행하고 집계를 출력.

    Capabilities:
        - ``dart``: ``archiveDartOriginals(start, end, scope, workers)`` 위임.
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
        - DART 는 ``DART_API_KEY(S)`` 필요.

    SeeAlso:
        - ``archiveDartOriginals`` — 실제 수집 본체.

    Requires:
        - ``DART_API_KEY(S)``.

    When:
        - 운영자가 셸에서 ``python -m dartlab.gather.original dart ...`` 로 백업을 돌릴 때.

    How:
        - argparse 로 provider 서브커맨드 분기 → archiveDart 위임 → 집계 출력.

    AIContext:
        운영자/배치 CLI — AI 분석 흐름 아님.

    LLM Specifications:
        AntiPatterns:
            - 분석 도중 호출 X — 배치 수집 전용.
        OutputSchema:
            - int(exit code) + stdout 집계 dict.
        Prerequisites:
            - dart 서브커맨드 + 필수 인자.
        Freshness:
            - 매 실행 재열거 + 기존 파일 skip.
        Dataflow:
            - argv → archive* 위임 → stdout 집계.
        TargetMarkets:
            - KR(DART).
    """
    parser = _buildParser()
    args = parser.parse_args(argv)
    showProgress = not args.noProgress

    stats = archiveDartOriginals(
        args.start,
        args.end,
        scope=args.scope,
        workers=args.workers,
        showProgress=showProgress,
    )

    print(stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
