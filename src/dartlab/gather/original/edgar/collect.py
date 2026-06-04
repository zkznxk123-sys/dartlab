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


_DAILY_INDEX_BASE = "https://www.sec.gov/Archives/edgar/daily-index"
_ARCHIVES_ROOT = "https://www.sec.gov/Archives"


def _quarterOf(yyyymmdd: str) -> int:
    """YYYYMMDD → 분기(1~4) — daily-index URL 의 QTR 세그먼트."""
    return (int(yyyymmdd[4:6]) - 1) // 3 + 1


def listRecentFilings(
    dates: list[str] | tuple[str, ...],
    *,
    forms: list[str] | tuple[str, ...] | None = None,
    limit: int | None = None,
) -> list[dict[str, str]]:
    """SEC daily-index(master.idx)로 날짜들의 **전 발행자** 공시를 열거 — panel 증분 발견용.

    Capabilities:
        - 발행자별 submissions 를 8천 번 호출하는 대신, 날짜당 ``master.{YYYYMMDD}.idx``
          1 회로 그날 제출된 *모든* 공시(CIK·form·accession)를 받는다. ``forms`` 로 재무
          폼만 거르면 EDGAR panel 증분의 "무엇이 새로 들어왔나"를 윈도 일수만큼의 요청으로
          확정. 주말/휴장일(404)은 skip.

    Args:
        dates: ``YYYYMMDD`` 일자 list(윈도). 순서 무관.
        forms: form 화이트리스트(예: ``["10-K","10-Q","20-F","40-F"]``). None 이면 전 form.
        limit: 최대 반환 공시 수(None=무제한). 발견 순서대로 cap(샘플링·테스트용).

    Returns:
        list[dict] — 각 dict 키 ``cik``(10-pad) · ``form`` · ``filing_date`` ·
        ``accession_no`` · ``txt_url``. 중복 없음(인덱스가 공시당 1행).

    Raises:
        없음 — 일자별 HTTP 실패는 경고 후 skip(부분 결과 반환).

    Example:
        >>> listRecentFilings(["20260603"], forms=["10-Q"])  # doctest: +SKIP
        [{'cik': '0001000045', 'form': '10-Q', ...}]

    SeeAlso:
        - ``fetchFilings`` — 본 목록 중 신규 accession 의 .txt 수집.
        - ``providers.edgar.panel.build.appendFilingsToPanel`` — 수집분 panel append.

    Requires:
        - 인터넷 + SEC User-Agent.

    When:
        - EDGAR panel 일간 증분: 최근 N일 신규 재무 공시 발견 단계.
    """
    formSet = {f.upper() for f in forms} if forms else None
    rows: list[dict[str, str]] = []
    for day in dates:
        if len(day) != 8 or not day.isdigit():
            continue
        url = f"{_DAILY_INDEX_BASE}/{day[:4]}/QTR{_quarterOf(day)}/master.{day}.idx"
        time.sleep(_REQUEST_INTERVAL)
        try:
            resp = httpx.get(url, headers=_HEADERS, timeout=60, follow_redirects=True)
            if resp.status_code == 404:
                continue  # 주말/휴장 — 인덱스 부재
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            _log.warning("daily-index %s 실패: %s", day, exc)
            continue
        for line in resp.text.splitlines():
            parts = line.split("|")
            # 우측 파싱 — 회사명(2번째 필드)에 '|' 가 있어도 안전(CIK|Company|Form|Date|Filename).
            if len(parts) < 5:
                continue  # 헤더/구분선
            cik, form, filed, filename = parts[0], parts[-3], parts[-2], parts[-1]
            form = form.strip().upper()
            filename = filename.strip()
            if (formSet is not None and form not in formSet) or not filename.endswith(".txt"):
                continue
            if not cik.strip().isdigit():
                continue  # 헤더 라벨 라인("CIK|Company|...") 방어
            rows.append(
                {
                    "cik": cik.strip().zfill(10),
                    "form": form,
                    "filing_date": filed.strip(),
                    "accession_no": filename.rsplit("/", 1)[-1][:-4],
                    "txt_url": f"{_ARCHIVES_ROOT}/{filename}",
                }
            )
            if limit is not None and len(rows) >= limit:
                return rows
    return rows


def fetchFilings(rows: list[dict[str, str]], *, limit: int | None = None) -> dict[str, list]:
    """``listRecentFilings`` 행들의 full submission ``.txt`` 수집 — 기존 skip, CIK 별 그룹.

    Capabilities:
        - 신규 accession 의 ``.txt`` 만 ``data/original/edgar/docs/{cik}/{accession}.txt`` 로
          atomic 저장(이미 있으면 skip). panel append 가 이 경로를 파싱 후 raw 를 폐기한다.

    Args:
        rows: ``listRecentFilings`` 산출(또는 동형). ``cik``·``accession_no``·``txt_url`` 필요.
        limit: 최대 수집 행 수(None=무제한). 앞에서부터 cap.

    Returns:
        dict[str, list[Path]] — ``{cik: [저장된 .txt Path, ...]}`` (skip 포함 = 존재하는 경로).

    Raises:
        없음 — 개별 fetch/write 실패는 해당 행 skip.

    Example:
        >>> fetchFilings([{"cik": "0000320193", "accession_no": "x", "txt_url": "..."}])  # doctest: +SKIP
        {'0000320193': [PosixPath('.../x.txt')]}

    SeeAlso:
        - ``listRecentFilings`` — 입력 행 산출.

    Requires:
        - 인터넷 + SEC User-Agent + 쓰기 가능 ``data/original/edgar/docs/``.

    When:
        - panel 증분에서 발견된 신규 공시 본문을 append 직전 내려받을 때.
    """
    grouped: dict[str, list] = {}
    if limit is not None:
        rows = rows[:limit]
    for row in rows:
        cik = row["cik"]
        outDir = edgarDir(cik)
        outPath = outDir / f"{row['accession_no']}.txt"
        if not outPath.exists():
            content = _fetchTxt(row["txt_url"])
            if content is None:
                continue
            outPath.parent.mkdir(parents=True, exist_ok=True)
            tmp = outPath.with_suffix(f".txt.tmp.{os.getpid()}.{time.monotonic_ns()}")
            try:
                tmp.write_bytes(content)
                os.replace(tmp, outPath)
            except OSError:
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass
                continue
        grouped.setdefault(cik, []).append(outPath)
    return grouped
