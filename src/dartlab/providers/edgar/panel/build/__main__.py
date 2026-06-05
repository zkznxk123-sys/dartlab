"""EDGAR panel build CLI — local full-submission text → panel 단일 artifact.

provider package 내부 CLI 는 fetch/orchestration 을 하지 않는다. SEC discovery/fetch 는
``.github/scripts/sync/buildEdgarPanel.py`` 또는 pipeline stage 가 맡고, 이 엔트리는 이미
받아둔 full-submission ``.txt`` 를 panel builder 에 넘기는 transform-only 도구다.

사용::

    python -X utf8 -m dartlab.providers.edgar.panel.build --ticker AAPL filing1.txt filing2.txt
    python -X utf8 -m dartlab.providers.edgar.panel.build --ticker AAPL --no-overwrite filing1.txt
"""

from __future__ import annotations

import argparse
from pathlib import Path


def _recordsFromFiles(paths: list[str]) -> list[dict[str, str]]:
    """local full-submission 파일들 → builder record list."""
    records: list[dict[str, str]] = []
    for raw in paths:
        path = Path(raw)
        text = path.read_bytes().decode("utf-8", errors="replace")
        records.append({"text": text, "accession_no": path.stem})
    return records


def _main() -> None:
    """argparse → local file read + buildEdgarPanel 위임 + 결과 요약 출력."""
    parser = argparse.ArgumentParser(prog="dartlab.providers.edgar.panel.build")
    parser.add_argument("--ticker", required=True, help="US ticker (예: AAPL)")
    parser.add_argument("filings", nargs="+", help="SEC full-submission .txt 파일 경로")
    parser.add_argument("--no-overwrite", action="store_true", help="기존 보드 artifact skip(증분)")
    parser.add_argument("--quiet", action="store_true", help="per-ticker 로그 억제")
    args = parser.parse_args()

    from .builder import buildEdgarPanel

    ticker = args.ticker.strip().upper()
    result = buildEdgarPanel(
        ticker, _recordsFromFiles(args.filings), overwrite=not args.no_overwrite, verbose=not args.quiet
    )
    print(  # noqa: T201
        f"edgar panel build: {ticker} rows={result['rows']:,} periods={result['periods']} filings={result['filings']}"
    )


if __name__ == "__main__":
    _main()
