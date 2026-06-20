"""Damodaran 국가 ERP(equity risk premium) 외부 fetch — pages.stern.nyu.edu/~adamodar.

``ctryprem.html``(국가별 Moody's rating + adj default spread + total ERP) 다운로드·파싱 →
구조화 dict. 외부 fetch = gather(Extract) SSOT 라 본 모듈에 둔다 — ISO2 매핑 + reference/data/
damodaranDefaults.json 병합·쓰기(sink)는 호출자(.github/scripts/sync/updateDamodaranERP)
책임. Damodaran 연 2회(1·7월) 갱신.
"""

from __future__ import annotations

import logging
import re
import urllib.request

log = logging.getLogger(__name__)

DAMODARAN_ERP_URL = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html"


def _fetchHtml(timeout: float = 30.0) -> str | None:
    """Damodaran ctryprem.html 원문 다운로드 (인코딩 자동 감지). 실패 시 None."""
    try:
        req = urllib.request.Request(DAMODARAN_ERP_URL, headers={"User-Agent": "dartlab/1.0 (research)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — 고정 https 도메인
            raw = resp.read()
            for enc in ("utf-8", "windows-1252", "latin-1"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="replace")
    except (OSError, ValueError) as exc:
        log.warning("Damodaran ERP fetch 실패: %s", exc)
        return None


def _extractMatureMarketERP(html: str) -> float | None:
    """Mature market equity risk premium (US base) 추출 — 'mature market ... N.NN%' 패턴."""
    m = re.search(r"mature\s+market[^.]*?(\d+\.\d+)\s*%", html, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _extractCountries(html: str) -> dict[str, dict]:
    """국가 테이블 파싱 (관대한 tr/td regex — 표 형태 변화 대응).

    표준 컬럼: Country | Rating | Adj Default Spread | Total ERP | Country Risk Premium.
    각 행은 ``{name: {"rawNumbers": [float, ...]}}`` — 컬럼 순서 해석은 호출자(sink).
    """
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE)
    out: dict[str, dict] = {}
    for row in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL | re.IGNORECASE)
        if len(cells) < 4:
            continue
        clean = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        name = clean[0]
        if not name or len(name) > 50:
            continue
        nums: list[float] = []
        for c in clean[1:]:
            m = re.search(r"(\d+\.\d+)\s*%?", c)
            if m:
                try:
                    nums.append(float(m.group(1)))
                except ValueError:
                    pass
        if len(nums) < 2:
            continue
        out[name] = {"rawNumbers": nums}
    return out


def fetchDamodaranCountryErp(*, timeout: float = 30.0) -> dict | None:
    """Damodaran ctryprem.html → 구조화 ERP dict. 외부 fetch=gather SSOT.

    Args:
        timeout: HTTP 타임아웃(초).

    Returns:
        ``{"matureMarketERP": float | None, "countries": {name: {"rawNumbers": [float]}}}`` —
        fetch/디코드 실패 시 None. matureMarketERP 미발견 시 None(호출자가 fallback).

    Raises:
        없음 — 네트워크/디코드 실패는 None 으로 흡수.

    Example:
        >>> out = fetchDamodaranCountryErp()  # doctest: +SKIP
        >>> set(out) >= {"matureMarketERP", "countries"}  # doctest: +SKIP
        True
    """
    html = _fetchHtml(timeout=timeout)
    if not html:
        return None
    return {
        "matureMarketERP": _extractMatureMarketERP(html),
        "countries": _extractCountries(html),
    }
