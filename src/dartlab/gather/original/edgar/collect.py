"""EDGAR 제출 목록화 + full-submission text fetch helper.

EDGAR panel 은 full-submission ``.txt`` 를 로컬 원본으로 저장하지 않는다. SEC daily-index
또는 submissions 목록에서 ``txt_url`` 을 얻고, 필요한 본문은 메모리 record 로 받아 즉시
``edgar/panel/{ticker}.parquet`` 빌드/append 에 넘긴다.
"""

from __future__ import annotations

import time

import httpx

from dartlab.core.logger import getLogger

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
        - ``fetchFilingTexts`` — 본 목록 중 신규 accession 의 text fetch.
        - ``providers.edgar.panel.build.appendFilingTextsToPanel`` — fetch 결과 panel append.

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


def fetchFilingTexts(rows: list[dict[str, str]], *, limit: int | None = None) -> dict[str, list[dict[str, str]]]:
    """``listRecentFilings``/``listAllFilings`` 행들의 full-submission text 를 메모리로 fetch.

    EDGAR panel 은 raw ``.txt`` 를 저장하지 않고 fetch 결과를 즉시 build/append 한다. 이 함수는
    ``data/original/edgar/docs`` 에 쓰지 않고 ``{"text", "accession_no", ...}`` records 만 반환한다.

    Args:
        rows: ``cik`` · ``accession_no`` · ``txt_url`` 필요.
        limit: 최대 fetch 행 수(None=무제한).

    Returns:
        dict[str, list[dict[str, str]]] — ``{cik: [record, ...]}``.

    Raises:
        없음 — 개별 fetch 실패는 해당 행 skip.

    Example:
        >>> rows = [{"cik": "320193", "accession_no": "x", "txt_url": "https://..."}]
        >>> fetchFilingTexts(rows, limit=1)  # doctest: +SKIP

    SeeAlso:
        - ``listRecentFilings`` — 증분 discovery.
        - ``providers.edgar.panel.build.appendFilingTextsToPanel`` — fetch 결과 append.

    Requires:
        - SEC full-submission text URL.

    Capabilities:
        - EDGAR 원문을 로컬 artifact 로 남기지 않고 panel builder 입력으로만 전달.

    Guide:
        - 호출자는 반환 record 수가 입력보다 적으면 해당 ticker build/append 를 skip 한다.

    When:
        - EDGAR panel 신규/전체 build 전에 full-submission text 가 필요할 때.

    How:
        - filing discovery row 를 받아 SEC URL 을 fetch 하고 CIK 별 record 로 묶어 반환한다.

    AIContext:
        - 원문 저장 없이 메모리 fetch 만 수행하므로 데이터 계보는 panel artifact 에서 닫힌다.

    LLM Specifications:
        AntiPatterns: fetch 실패를 부분 panel 로 저장하지 않는다.
        OutputSchema: ``dict[str, list[dict[str, str]]]``.
    """
    grouped: dict[str, list[dict[str, str]]] = {}
    if limit is not None:
        rows = rows[:limit]
    for row in rows:
        content = _fetchTxt(row["txt_url"])
        if content is None:
            continue
        cik = str(row["cik"]).zfill(10)
        rec = dict(row)
        rec["cik"] = cik
        rec["text"] = content.decode("utf-8", errors="replace")
        grouped.setdefault(cik, []).append(rec)
    return grouped
