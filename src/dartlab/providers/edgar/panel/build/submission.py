"""SEC full-submission ``.txt`` SGML 파서 — header + `<DOCUMENT>` 분해 (자급, 네트워크 0).

호출자가 SEC 에서 fetch 한 full-submission text 를 파싱한다. 구조:
``<SEC-HEADER>`` (form·cik·accession·CONFORMED PERIOD OF REPORT·FISCAL YEAR END·name) + 다수
``<DOCUMENT>`` 블록(`<TYPE>`/`<SEQUENCE>`/`<FILENAME>`/`<TEXT>…</TEXT>`). primary(``<TYPE>{form}``,
최소 SEQUENCE)=iXBRL HTML(본문+inline facts+`<xbrli:context>`), 별도 블록 ``EX-101.PRE/LAB`` = XBRL
링크베이스. **모든 XBRL 재료가 한 파일 안에 자급** — DART 가 zip 을 자급 파싱하는 것의 EDGAR 미러.

기존 viewer HTML 재-fetch 경로가 아니라 full-submission text 자체를 한 번 파싱한다.

LLM Specifications:
    AntiPatterns:
        - viewer HTML 재-fetch 금지 — full-submission text 자급 파싱.
        - exhibit(EX-*)/GRAPHIC 를 primary 로 오인 금지 — `<TYPE>==form` & 최소 SEQUENCE.
    OutputSchema:
        - ``parseSubmission(txt) -> dict`` (form/cik/accession/periodOfReport/fiscalYearEnd/name/primaryHtml/ex101).
    Prerequisites:
        - 없음 (순수 문자열 파싱).
    Freshness:
        - 순수 — 입력 ``.txt`` 외 의존 0.
    Dataflow:
        - txt → SGML header regex + `<DOCUMENT>` split → primary HTML + EX-101.PRE/LAB.
    TargetMarkets:
        - US (SEC EDGAR full-submission).
"""

from __future__ import annotations

import re
from datetime import date

_HEADER_END_RE = re.compile(r"</SEC-HEADER>", re.IGNORECASE)
_FIELD_RES = {
    "form": re.compile(r"CONFORMED SUBMISSION TYPE:\s*(\S+)", re.IGNORECASE),
    "accession": re.compile(r"ACCESSION NUMBER:\s*(\S+)", re.IGNORECASE),
    "cik": re.compile(r"CENTRAL INDEX KEY:\s*(\d+)", re.IGNORECASE),
    "periodOfReport": re.compile(r"CONFORMED PERIOD OF REPORT:\s*(\d{8})", re.IGNORECASE),
    "fiscalYearEnd": re.compile(r"FISCAL YEAR END:\s*(\d{4})", re.IGNORECASE),
    "name": re.compile(r"COMPANY CONFORMED NAME:\s*(.+)", re.IGNORECASE),
}
_DOC_SPLIT_RE = re.compile(r"<DOCUMENT>", re.IGNORECASE)
_TYPE_RE = re.compile(r"<TYPE>([^\r\n<]+)", re.IGNORECASE)
_SEQ_RE = re.compile(r"<SEQUENCE>([^\r\n<]+)", re.IGNORECASE)
_FILENAME_RE = re.compile(r"<FILENAME>([^\r\n<]+)", re.IGNORECASE)
_TEXT_RE = re.compile(r"<TEXT>(.*?)</TEXT>", re.IGNORECASE | re.DOTALL)
# iXBRL/PDF wrapper (TEXT 안 본문 감쌈) strip.
_WRAPPER_OPEN_RE = re.compile(r"^\s*<(XBRL|PDF)>", re.IGNORECASE)
_WRAPPER_CLOSE_RE = re.compile(r"</(XBRL|PDF)>\s*$", re.IGNORECASE)


def _parsePeriodDate(yyyymmdd: str | None) -> date | None:
    """``YYYYMMDD`` → date (실패 None)."""
    if not yyyymmdd or len(yyyymmdd) != 8 or not yyyymmdd.isdigit():
        return None
    try:
        return date(int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:8]))
    except ValueError:
        return None


def _docText(docSeg: str) -> str:
    """`<DOCUMENT>` segment 의 `<TEXT>` 본문 추출 + `<XBRL>`/`<PDF>` wrapper strip."""
    m = _TEXT_RE.search(docSeg)
    if not m:
        return ""
    body = m.group(1)
    body = _WRAPPER_OPEN_RE.sub("", body, count=1)
    body = _WRAPPER_CLOSE_RE.sub("", body, count=1)
    return body.strip()


def parseSubmission(txt: str) -> dict:
    """SEC full-submission ``.txt`` → header meta + primary HTML + EX-101.PRE/LAB (자급).

    ``<SEC-HEADER>`` regex 로 form/cik/accession/period/fiscalYearEnd/name 추출. ``<DOCUMENT>`` 분해 후
    primary(``<TYPE>==form``, 최소 SEQUENCE)=iXBRL HTML, ``EX-101.PRE``/``EX-101.LAB`` 링크베이스 추출.

    Args:
        txt: SEC full-submission 원문.

    Returns:
        dict — ``{form, cik, accession, periodOfReport(date|None), fiscalYearEnd(str|None),
        name, primaryHtml(str), ex101Pre(str), ex101Lab(str)}``. primaryHtml 부재 시 "".

    Raises:
        없음 — 결손 필드는 None/"".

    Example:
        >>> sub = parseSubmission(open("0001410578-25-001475.txt").read())  # doctest: +SKIP
        >>> sub["form"], sub["periodOfReport"]
        ('10-K', datetime.date(2025, 5, 31))

    SeeAlso:
        - ``instance.extractFacts`` / ``extractContexts`` — primaryHtml 소비.
        - ``linkbase.parsePresentation`` / ``parseLabels`` — ex101Pre/Lab 소비.

    Requires:
        - 없음 (순수 문자열).

    Capabilities:
        - full-submission text 1개에서 XBRL 전 재료(본문 HTML + 링크베이스) 자급 추출.

    Guide:
        - ``builder.filingTextToBoard`` 가 호출. 순수라 직접/테스트 호출 안전.

    AIContext:
        - SGML 형식 규칙만 — 의미 추론 0. 거대 파일(16MB+)은 한 번 read 후 regex.

    When:
        - SEC fetch text 를 panel 보드로 파싱하기 직전.

    How:
        - `</SEC-HEADER>` 기준 header 분리 → 필드 regex → `<DOCUMENT>` split → TYPE/SEQ/TEXT.

    LLM Specifications:
        AntiPatterns:
            - 첫 `<DOCUMENT>` 를 무조건 primary 로 가정 금지 — `<TYPE>==form` 우선(없으면 첫 .htm).
            - `<TEXT>` 의 `<XBRL>` wrapper 미strip 금지 — 본문만.
        OutputSchema:
            - ``dict`` (header + primaryHtml + ex101Pre + ex101Lab).
        Prerequisites:
            - 없음.
        Freshness:
            - 순수.
        Dataflow:
            - txt → header regex + DOCUMENT split → 본문/링크베이스.
        TargetMarkets:
            - US.
    """
    headerEnd = _HEADER_END_RE.search(txt)
    header = txt[: headerEnd.end()] if headerEnd else txt[:5000]
    meta: dict = {}
    for key, rx in _FIELD_RES.items():
        m = rx.search(header)
        meta[key] = m.group(1).strip() if m else None
    form = (meta.get("form") or "").strip()
    out: dict = {
        "form": form,
        "cik": (meta.get("cik") or "").zfill(10) if meta.get("cik") else None,
        "accession": meta.get("accession"),
        "periodOfReport": _parsePeriodDate(meta.get("periodOfReport")),
        "fiscalYearEnd": meta.get("fiscalYearEnd"),
        "name": meta.get("name"),
        "primaryHtml": "",
        "ex101Pre": "",
        "ex101Lab": "",
        "ex101Ins": "",
    }

    # <DOCUMENT> 분해 — 각 segment 에서 TYPE/SEQUENCE/TEXT.
    segs = _DOC_SPLIT_RE.split(txt)[1:]  # [0] = header 앞부분
    primaryCandidates: list[tuple[int, str]] = []  # (sequence, html)
    htmFallback: list[tuple[int, str]] = []
    for seg in segs:
        tm = _TYPE_RE.search(seg)
        docType = tm.group(1).strip() if tm else ""
        sm = _SEQ_RE.search(seg)
        try:
            seq = int(sm.group(1).strip()) if sm else 9999
        except ValueError:
            seq = 9999
        fm = _FILENAME_RE.search(seg)
        filename = fm.group(1).strip().lower() if fm else ""
        upType = docType.upper()
        if upType == "EX-101.PRE" and not out["ex101Pre"]:
            out["ex101Pre"] = _docText(seg)
            continue
        if upType == "EX-101.LAB" and not out["ex101Lab"]:
            out["ex101Lab"] = _docText(seg)
            continue
        if upType == "EX-101.INS" and not out["ex101Ins"]:
            out["ex101Ins"] = _docText(seg)
            continue
        # primary = form 과 동일 TYPE (예 10-K). exhibit/graphic/taxonomy 제외.
        if form and upType == form.upper():
            primaryCandidates.append((seq, _docText(seg)))
        elif filename.endswith((".htm", ".html")) and not upType.startswith(("EX-", "GRAPHIC")):
            htmFallback.append((seq, _docText(seg)))

    if primaryCandidates:
        primaryCandidates.sort(key=lambda x: x[0])
        out["primaryHtml"] = primaryCandidates[0][1]
    elif htmFallback:
        htmFallback.sort(key=lambda x: x[0])
        out["primaryHtml"] = htmFallback[0][1]
    return out
