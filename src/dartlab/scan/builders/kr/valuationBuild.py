"""KR scan valuation snapshot builder.

Capabilities:
    - Builds raw market valuation snapshots for scan valuation loaders.

Args:
    Public entry points accept logging options.

Returns:
    Generated valuation parquet path or ``None`` when coverage is unsafe.

Example:
    >>> from dartlab.scan.builders.kr.valuationBuild import buildValuation
    >>> p = buildValuation(verbose=True)

Guide:
    Keep this builder raw. PSR and grade derivations belong to the runtime loader.

SeeAlso:
    ``scan.financial.valuation`` and ``scan.io.parquet``.

Requires:
    KRX listing data and Naver finance API access.

AIContext:
    Runtime scan valuation answers should treat ``snapshotAt`` from this output as
    the freshness source of truth.

LLM Specifications:
    AntiPatterns: Do not merge this into ``buildScan``; it has separate rate-limit risk.
    OutputSchema: ``valuation.parquet`` with raw valuation fields.
    Prerequisites: Network-backed valuation fetch succeeds above coverage threshold.
    Freshness: Daily valuation cron output.
    Dataflow: KRX listing -> Naver raw fetch -> coverage gate -> raw parquet.
    TargetMarkets: KR listed companies.
"""

from __future__ import annotations

import time
from pathlib import Path

from dartlab.scan.builders.kr.common import say as _say
from dartlab.scan.builders.kr.common import scanDir as _scanDir


def buildValuation(*, verbose: bool = True) -> Path | None:
    """네이버 API 로 전종목 시세·밸류에이션 raw 수집 → ``valuation.parquet``.

    GH Actions cron (``valuationSnapshot.yml``, 매일 KST 04:00) 에서 호출. 결과 parquet 은
    HuggingFace ``eddmpython/dartlab-data`` 의 ``dart/scan/`` 에 업로드되며, 사용자는
    ``dartlab.scan("valuation")`` 호출 시 자동 다운로드 + 즉시 로드한다 (1초 이내).

    Parameters
    ----------
    verbose : bool, default True
        진행 라인을 ``logger.info`` 로 출력.

    Returns
    -------
    Path | None
        생성된 ``valuation.parquet`` 경로. 수집 실패 또는 rate-limit 으로 0 건이거나
        coverage < 55 % 이면 기존 parquet 덮어쓰지 않고 ``None`` 반환.

    Raises
    ------
    없음 — listing 로드 실패 · 네이버 rate-limit · OSError 는 내부에서 흡수 + None 반환.

    Examples
    --------
    >>> from dartlab.scan.builders.kr.valuationBuild import buildValuation
    >>> p = buildValuation(verbose=True)
    >>> p.name if p else "rate-limited"
    'valuation.parquet'

    Capabilities:
        - 상장사 ~3964 종목의 ``marketCap`` · ``per`` · ``pbr`` · ``dividendYield`` · ``current``
          · ``snapshotAt`` 6 컬럼을 네이버 API 에서 raw 수집. PSR/grade 는 loader 가 매출 parquet
          결합 후 runtime 계산 — 본 빌드는 raw 만 책임.
        - 품질 게이트 — 수집 coverage < 55 % 이면 기존 parquet 보존 (stale data > corrupted).

    AIContext:
        ``dartlab.scan("valuation")`` 호출의 1 차 source. AI 가 밸류에이션 비교 시 (PER/PBR/PSR)
        본 빌드 산출물 + finance 매출 결합한 결과를 사용. snapshotAt 컬럼이 데이터 freshness 의
        ground truth — 24 h 초과 시 사용자에게 stale 경고.

    Guide:
        - cron 외 수동 호출: rate-limit 위험 — 같은 IP 가 짧은 시간에 두 번 돌리면 0 건 응답.
        - 출력 ``valuation.parquet`` 는 ``HF eddmpython/dartlab-data`` 의 ``dart/scan/`` 동기화.
        - listing 미보유 환경에서는 silent skip (None).

    When:
        GH Actions cron 매일 KST 04:00 자동 호출. 로컬 수동 호출은 디버깅/품질 검증 한정.

    How:
        listing (KRX KIND) → 종목코드 리스트 → ``fetchValuationRaw`` (네이버 API 병렬) →
        coverage 게이트 → ``_RAW_SCHEMA`` 컬럼만 selecting → 단일 parquet write. rate-limit
        대응은 ``fetchValuationRaw`` 내부 backoff 가 담당.

    Requires:
        - 네이버 finance API 접근 (rate-limit 의식)
        - ``dartlab.gather.krx.listing.getKindList()`` 가 종목코드 반환
        - ``dartlab.scan.financial.valuation`` 의 ``fetchValuationRaw`` · ``_RAW_SCHEMA``

    SeeAlso:
        - :func:`dartlab.scan.financial.valuation.fetchValuationRaw` — 네이버 raw 수집
        - :func:`dartlab.scan.io.parquet.loadValuationSnapshot` — 빌드 결과 lazy load
        - :func:`dartlab.scan.builders.kr.core.buildScan` — 본 함수에 포함 안 됨 (별도 cron)
    """
    from dartlab.scan.financial.valuation import _RAW_SCHEMA, fetchValuationRaw

    if verbose:
        _say("[valuation] 상장사 목록 로드...")

    try:
        from dartlab.gather.krx.listing import getKindList

        listing = getKindList()
    except (ImportError, OSError, RuntimeError) as e:
        if verbose:
            _say(f"[valuation] listing 로드 실패: {e}")
        return None

    if listing is None or listing.is_empty() or "종목코드" not in listing.columns:
        if verbose:
            _say("[valuation] 상장사 목록 없음")
        return None

    codes = listing["종목코드"].to_list()
    if verbose:
        _say(f"[valuation] {len(codes)}종목 네이버 API 수집 시작")

    t0 = time.perf_counter()
    raw = fetchValuationRaw(codes, verbose=verbose)
    elapsed = time.perf_counter() - t0

    if raw.is_empty():
        if verbose:
            _say(f"[valuation] 수집 0건 (rate-limit 의심, {elapsed:.1f}s) — 기존 parquet 유지")
        return None

    coverage = raw.height / max(len(codes), 1)
    if coverage < 0.55:
        if verbose:
            _say(f"[valuation] 수집 {raw.height}/{len(codes)} ({coverage:.0%}) — 55% 미만, 기존 parquet 유지")
        return None

    outDir = _scanDir()
    outDir.mkdir(parents=True, exist_ok=True)
    outPath = outDir / "valuation.parquet"
    raw.select(list(_RAW_SCHEMA.keys())).write_parquet(str(outPath), compression="zstd")

    if verbose:
        sizeMb = outPath.stat().st_size / 1024 / 1024
        _say(f"[valuation] 완료: {raw.height}종목, {sizeMb:.1f}MB, {elapsed:.1f}s → {outPath}")
    return outPath
