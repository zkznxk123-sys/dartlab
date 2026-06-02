"""EDGAR full submission 원본 수집 → ``data/original/edgar/{cik}/{accession}.txt``.

발행자(ticker/CIK)의 **전 form** 공시를 열거하고, 각 accession 의 full submission
``.txt`` (전 문서 + SGML 헤더, **가공 0**)를 디스크에 보관한다. 이미 있는 파일은
skip(idempotent). atomic write. SEC keyless — User-Agent(연락처)만 사용.
"""

from __future__ import annotations

import os
import time

import httpx

from dartlab.core.logger import getLogger

from ..paths import edgarDir
from .submissions import listAllFilings

_log = getLogger(__name__)

_HEADERS = {"User-Agent": "DartLab eddmpython@gmail.com"}
_REQUEST_INTERVAL = 0.2  # SEC 10 req/s 한도 — 5 req/s 보수적
_MIN_VALID_BYTES = 64


def _fetchTxt(url: str) -> bytes | None:
    """full submission .txt fetch(User-Agent + interval). 실패 시 None.

    Args:
        url: submission .txt URL.

    Returns:
        bytes | None — 본문 bytes 또는 실패 시 None.

    Raises:
        없음 — HTTP/네트워크 실패는 None 으로 흡수.

    Example:
        >>> _fetchTxt("https://www.sec.gov/Archives/edgar/data/.../x.txt")  # doctest: +SKIP
    """
    time.sleep(_REQUEST_INTERVAL)
    try:
        resp = httpx.get(url, headers=_HEADERS, timeout=60, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError:
        return None
    content = resp.content
    if not content or len(content) < _MIN_VALID_BYTES:
        return None
    return content


def archiveEdgarOriginals(
    tickersOrCiks: list[str] | tuple[str, ...],
    *,
    forms: list[str] | tuple[str, ...] | None = None,
    sinceYear: int = 2009,
    showProgress: bool = True,
) -> dict[str, int]:
    """EDGAR full submission 원본 ``.txt`` 를 ``data/original/edgar/`` 에 수집(가공 0).

    Capabilities:
        - 발행자별 **전 form** 공시를 열거(정기+비정기) → 각 full submission ``.txt``
          (전 문서·SGML 헤더 보존)를 디스크 보관. 기존 파일 skip, atomic write.
          SEC keyless(User-Agent) + 0.2s interval 로 SEC 정책 준수.

    Args:
        tickersOrCiks: ticker/CIK list(예: ``["AAPL", "MSFT"]``).
        forms: form 화이트리스트(예: ``["8-K", "10-K"]``). None 이면 **전 form**.
        sinceYear: 시작 연도(기본 2009 — XBRL 의무화).
        showProgress: 진행 로그 출력.

    Returns:
        dict[str, int] — ``{"ok", "skipped", "error", "issuers"}`` 집계.

    Raises:
        없음 — 개별 발행자/공시 실패는 집계로 흡수(전체 중단 X).

    Example:
        >>> archiveEdgarOriginals(["AAPL"], forms=["8-K"], sinceYear=2024)  # doctest: +SKIP
        {'ok': 41, 'skipped': 0, 'error': 0, 'issuers': 1}

    Guide:
        - 전 form 은 종목당 수백~수천 — ``forms``/``sinceYear`` 로 범위 조절.
        - 재실행은 기존 ``.txt`` skip 으로 자동 이어감.

    SeeAlso:
        - ``gather.original.dart.collect.archiveDartOriginals`` — DART 짝.
        - ``listAllFilings`` — 본 함수의 열거 backend.

    Requires:
        - 인터넷 + SEC User-Agent + 쓰기 가능 ``data/original/edgar/``.

    When:
        - 운영자가 US 발행자들의 전 form 원본 .txt 를 수집/백필할 때.

    How:
        - 발행자별 listAllFilings(전 form) → 각 txt_url fetch → data/original/edgar/{cik}/{accession}.txt.

    AIContext:
        원본 백업 배치 — 운영자/CLI. 수집한 본문은 untrusted(해석 별도 엔진).

    LLM Specifications:
        AntiPatterns:
            - 분석 파이프라인에서 호출 X — 배치 전용(무겁다).
            - User-Agent 미설정 X — SEC 403.
            - 무필터 전 form 대량 호출 시 종목당 수천 — forms/sinceYear 권장.
        OutputSchema:
            - dict[str, int] 집계.
        Prerequisites:
            - 인터넷 + ticker/CIK list.
        Freshness:
            - 매 실행 submissions 재열거 + 기존 .txt skip.
        Dataflow:
            - ticker → listAllFilings(전 form) → .txt fetch →
              data/original/edgar/{cik}/{accession}.txt.
        TargetMarkets:
            - US(SEC EDGAR) 전 form.
    """
    stats = {"ok": 0, "skipped": 0, "error": 0, "issuers": 0}

    for raw in tickersOrCiks:
        try:
            filings = listAllFilings(raw, sinceYear=sinceYear, forms=forms)
        except (ValueError, httpx.HTTPError) as exc:
            _log.warning("[%s] 열거 실패: %s", raw, exc)
            stats["error"] += 1
            continue
        if not filings:
            if showProgress:
                _log.info("[%s] 공시 0", raw)
            continue
        stats["issuers"] += 1
        outDir = edgarDir(filings[0]["cik"])

        for row in filings:
            accession = row["accession_no"]
            outPath = outDir / f"{accession}.txt"
            if outPath.exists():
                stats["skipped"] += 1
                continue
            content = _fetchTxt(row["txt_url"])
            if content is None:
                stats["error"] += 1
                continue
            outPath.parent.mkdir(parents=True, exist_ok=True)
            tmp = outPath.with_suffix(f".txt.tmp.{os.getpid()}.{time.monotonic_ns()}")
            try:
                tmp.write_bytes(content)
                os.replace(tmp, outPath)
                stats["ok"] += 1
            except OSError as exc:
                _log.warning("[%s] write 실패 %s: %s", raw, accession, exc)
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass
                stats["error"] += 1

        if showProgress:
            _log.info("[%s] ok=%d skip=%d error=%d", raw, stats["ok"], stats["skipped"], stats["error"])

    if showProgress:
        _log.info("EDGAR 원본 수집 완료: %s", stats)
    return stats
