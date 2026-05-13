"""KR scan shares-outstanding helper builder.

Capabilities:
    - Runs the optional shares outstanding scan build without failing the full scan build.

Args:
    Public entry point accepts logging options.

Returns:
    Generated shares parquet path or ``None`` when the optional build fails.

Example:
    >>> from dartlab.scan.builders.kr.shares import buildSharesOutstandingSafe
    >>> p = buildSharesOutstandingSafe(verbose=True)

Guide:
    This module is intentionally small because shares are an optional adjunct to the
    scan prebuild, not a full domain tree.

SeeAlso:
    ``core.buildScan`` and ``providers.dart.docs.finance.shareCapital``.

Requires:
    DART share-capital source data when available.

AIContext:
    Keeps optional share-count failure from corrupting or blocking core scan sources.

LLM Specifications:
    AntiPatterns: Do not place broad finance build logic here.
    OutputSchema: ``sharesOutstanding.parquet`` path when generated.
    Prerequisites: Share-capital builder import succeeds.
    Freshness: Rebuilt with the main scan prebuild.
    Dataflow: provider share-capital builder -> scan output path.
    TargetMarkets: KR DART scan adjunct data.
"""

from __future__ import annotations

from pathlib import Path

from dartlab.scan.builders.kr.common import say as _say
from dartlab.scan.builders.kr.common import scanDir as _scanDir


def buildSharesOutstandingSafe(*, verbose: bool = True) -> Path | None:
    """발행주식수 풀 빌드 — 실패해도 전체 scan 진행.

    Parameters
    ----------
    verbose : bool
        진행 로그 출력 여부.

    Returns
    -------
    Path | None
        생성된 sharesOutstanding.parquet 경로. 실패 시 None.

    Raises
    ------
    없음 — 선택 산출물이므로 내부에서 알려진 실패를 흡수한다.

    Examples
    --------
    >>> buildSharesOutstandingSafe(verbose=False) is None
    True

    Capabilities:
        발행주식수 산출물을 별도 optional step 으로 만들고, 실패 시 전체 scan build 를 계속한다.

    AIContext:
        valuation/share 기반 scan 축에서 보조 데이터로 사용된다. 실패는 핵심 finance/report
        산출물 신뢰도와 분리해서 다룬다.

    Guide:
        이 함수는 보호 wrapper 이다. 실제 수집/계산 책임은 provider shareCapital builder 에 둔다.

    When:
        ``buildScan`` 마지막 단계에서 호출된다.

    How:
        provider builder 를 지연 import 해 실행하고, 알려진 런타임/파일 오류는 None 으로 변환한다.

    Requires:
        ``dartlab.providers.dart.docs.finance.shareCapital.buildSharesOutstandingScan``.

    SeeAlso:
        ``dartlab.scan.builders.kr.core.buildScan``.
    """
    try:
        from dartlab.providers.dart.docs.finance.shareCapital import buildSharesOutstandingScan

        if verbose:
            _say("[shares] 발행주식수 풀 빌드 시작")
        df = buildSharesOutstandingScan()
        if verbose:
            stockCol = "stock_code" if "stock_code" in df.columns else "stockCode"
            _say(f"[shares] 완료: rows={df.height} stocks={df[stockCol].n_unique()}")
        return _scanDir() / "sharesOutstanding.parquet"
    except (FileNotFoundError, RuntimeError, OSError, ValueError) as exc:
        if verbose:
            _say(f"[shares] 실패: {exc}")
        return None
