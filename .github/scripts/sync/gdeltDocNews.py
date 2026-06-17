"""GDELT DOC 2.0 API 종목 뉴스 fetcher — 과거 트랙(무료·합법, 제목+링크, 스니펫 없음).

GKG 벌크 수집(`gather/sources/gdelt.py`, 시간슬롯·제목 없음·회사키 없음)과 **다른 엔드포인트**다.
DOC 2.0 API 는 *질의 기반*이라 회사명으로 직접 검색 → 제목·URL·날짜를 돌려준다(네이버 fanout 동형).
2017년경까지 과거 커버. 무료·키 불필요. ToS 가 학술/상업 사용 허용(GKG 와 동일 GDELT 정책).

한계(정직): 한국 매체 커버리지 부분적(영문매체 위주), 스니펫 없음(제목+링크만), maxrecords 250/질의.

본 fetcher 는 .github/scripts/sync 의 online 수집 글루다(src/dartlab 신규 능력 아님 — 기존 news 소스
패턴의 sync-layer 확장). buildNaverCompanyNews 가 호출해 gdelt 트랙 archive 를 채운다.
"""

from __future__ import annotations

import logging
import time
from datetime import date as _date
from datetime import datetime, timezone
from urllib.parse import urlparse

import polars as pl

_log = logging.getLogger("gdeltDocNews")

_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_MAX_RECORDS = 250  # DOC API 상한
_GDELT_FLOOR_YEAR = 2017  # DOC 인덱스 시작 연도


def _yearWindow(year: int) -> tuple[str, str]:
    """연도 → (startdatetime, enddatetime) GDELT 형식 (YYYYMMDDHHMMSS)."""
    return f"{year}0101000000", f"{year}1231235959"


def _domain(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").replace("www.", "")
    except Exception:  # noqa: BLE001
        return ""


def _fetchOne(client, name: str, year: int) -> list[dict]:
    """회사명×연도 1 질의 → article dict 리스트 (실패·빈 결과는 [])."""
    params = {
        "query": f'"{name}" sourcecountry:southkorea',
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(_MAX_RECORDS),
        "sort": "datedesc",
        "startdatetime": _yearWindow(year)[0],
        "enddatetime": _yearWindow(year)[1],
    }
    try:
        resp = client.get(_DOC_URL, params=params)
        if resp.status_code != 200:
            return []
        # DOC API 는 결과 0 일 때 빈 본문/비-JSON 을 주기도 함 → 방어적 파싱
        try:
            payload = resp.json()
        except Exception:  # noqa: BLE001
            return []
    except Exception as exc:  # noqa: BLE001 — 네트워크/타임아웃은 그 질의만 skip
        _log.debug("GDELT DOC 질의 실패 %s/%d: %s", name, year, exc)
        return []
    return payload.get("articles") or []


def fetchGdeltDoc(
    nameToCode: dict[str, str],
    *,
    years: int = 1,
    perQuery: float = 0.25,
    timeout: float = 30.0,
    budgetSec: float | None = None,
) -> pl.DataFrame:
    """회사명→코드 매핑의 각 회사를 GDELT DOC API 로 질의 → 뉴스 archive df (gdelt 트랙).

    Sig: ``fetchGdeltDoc(nameToCode, *, years=1, perQuery=0.25, timeout=30.0, budgetSec=None) -> pl.DataFrame``

    최근 ``years`` 개 연도를 회사별로 질의(daily=1=올해, backfill=5=2021~). 반환 컬럼은 naver archive 와
    호환(date/title/source/url/query/description/market/captured_at) — description 은 항상 빈 문자열.
    전 종목(~2800)은 한 job 에 다 못 도므로 ``budgetSec`` 시간예산 초과 시 중단(누적이라 다음 run 이 이어감).

    Args:
        nameToCode: 회사명 → 종목코드. query=회사명, 결과행에 stockCode 동봉(__code).
        years: 최근 몇 개 연도를 질의할지 (1=올해만 증분, ≥2=과거 backfill).
        perQuery: 질의 간 sleep(초) — DOC API rate 보호.
        timeout: httpx 타임아웃.
        budgetSec: 전체 fetch 시간예산(초). 초과 시 그때까지 모은 것 반환(부분). None=무제한.

    Returns:
        pl.DataFrame — gdelt 트랙 뉴스(빈 결과면 빈 df, 동일 스키마). __code 컬럼 포함.
    """
    if not nameToCode:
        return pl.DataFrame()
    import httpx

    nowYear = datetime.now(tz=timezone.utc).year
    yearList = [y for y in range(nowYear, nowYear - max(1, years), -1) if y >= _GDELT_FLOOR_YEAR]
    capturedAt = datetime.now(tz=timezone.utc)
    started = time.monotonic()
    rows: list[dict] = []
    done = 0
    with httpx.Client(follow_redirects=True, timeout=timeout, headers={"User-Agent": "dartlab/news"}) as client:
        for name, code in nameToCode.items():
            if budgetSec is not None and time.monotonic() - started > budgetSec:
                _log.info("GDELT DOC 시간예산 %ss 초과 — %d/%d 종목에서 중단(누적)", budgetSec, done, len(nameToCode))
                break
            done += 1
            for year in yearList:
                for art in _fetchOne(client, name, year):
                    url = art.get("url") or ""
                    title = (art.get("title") or "").strip()
                    seen = art.get("seendate") or ""
                    if not url or not title or len(seen) < 8:
                        continue
                    try:
                        d = _date(int(seen[:4]), int(seen[4:6]), int(seen[6:8]))
                    except ValueError:
                        continue
                    rows.append(
                        {
                            "date": d,
                            "title": title,
                            "source": art.get("domain") or _domain(url),
                            "url": url,
                            "query": name,
                            "description": "",
                            "market": "KR",
                            "captured_at": capturedAt,
                            "__code": str(code).strip(),
                        }
                    )
                time.sleep(perQuery)
    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows).unique(subset=["url"], keep="first")
