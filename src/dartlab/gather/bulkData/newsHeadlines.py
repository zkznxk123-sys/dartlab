"""news headlines archive 부분 액세스 — 엔진 내부용 (Mode 2).

Phase A (news archive forward-only) 의 read-side. `data/news/headlines/{market}/`
일별 parquet 을 기간으로 합쳐 단일 DataFrame 반환. PIT (asof) 옵션 동행 —
Sprint 4 bitemporal 패턴 따라 `business_time=date`/`knowledge_time=captured_at`.

데이터 흐름 (dartlab 표준):
    1. 로컬 `data/news/headlines/{market}/{YYYY}-{MM}-{DD}.parquet` 확인
    2. 없으면 HF (`eddmpython/dartlab-data` / `news/headlines/{market}/...`) lazy 다운로드
    3. LRU 캐시 (32 일분) — 같은 세션 재호출 메모리 hit
    4. 결과 concat + asof 필터 + 시간 정렬

본 모듈은 read-only — write 는 `.github/scripts/sync/syncNewsHeadlines.py` 가 SSOT.
"""

from __future__ import annotations

import logging
from datetime import date as _date
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import polars as pl

from ..transforms.pit import applyAsOf

log = logging.getLogger(__name__)

_CATEGORY = "newsHeadlines"
_REPO_ROOT = Path(__file__).resolve().parents[4]
_LOCAL_ROOT = _REPO_ROOT / "data" / "news" / "headlines"

_EMPTY_SCHEMA = {
    "date": pl.Date,
    "title": pl.Utf8,
    "source": pl.Utf8,
    "url": pl.Utf8,
    "market": pl.Utf8,
    "query": pl.Utf8,
    "captured_at": pl.Datetime("us", time_zone="UTC"),
}


def _toDate(d: str | _date) -> _date:
    """YYYY-MM-DD / YYYYMMDD / date → date."""
    if isinstance(d, _date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    s = str(d).replace("-", "").strip()
    if len(s) >= 8:
        return _date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    return _date.today()


def _dayRange(start: _date, end: _date) -> list[_date]:
    """[start..end] inclusive 일자 리스트."""
    if start > end:
        start, end = end, start
    span = (end - start).days
    return [start + timedelta(days=i) for i in range(span + 1)]


@lru_cache(maxsize=128)
def _loadDay(market: str, dayIso: str) -> pl.DataFrame | None:
    """단일 일자 parquet 로드 — 로컬 우선, 없으면 HF lazy 다운로드.

    Sig: ``_loadDay(market: str, dayIso: str) -> pl.DataFrame | None``

    Capabilities: 일별 1 파일 로드 + LRU 캐시 (128 일).
    AIContext: loadNewsArchive 가 일자 루프로 호출. 미존재 시 None silent.
    Guide: 로컬 우선, 없으면 dataLoader 통해 HF download.
    When: 일자별 archive parquet 1 회 로드 필요 시.
    How: 로컬 path 확인 → pl.read_parquet → 미존재 시 dataLoader.loadData.

    Args:
        market: "KR" | "US" (대문자 정규화).
        dayIso: "YYYY-MM-DD".

    Returns:
        pl.DataFrame | None — 해당 일자 archive. 미존재 시 None.

    Raises:
        없음 — 모든 IO 에러 silent debug log.

    Example::

        df = _loadDay("KR", "2026-05-28")

    Requires:
        로컬 parquet 또는 HF 네트워크.

    See Also:
        ``loadNewsArchive``: 본 함수의 일자 루프 caller.
    """
    marketU = market.upper()
    local = _LOCAL_ROOT / marketU / f"{dayIso}.parquet"
    if local.exists():
        try:
            return pl.read_parquet(local)
        except (OSError, pl.exceptions.ComputeError) as exc:
            log.debug("newsHeadlines local read 실패 %s: %s", local, exc)
            return None

    # HF lazy fetch
    try:
        from dartlab.core.dataLoader import loadData

        stockCode = f"{marketU}/{dayIso}"
        return loadData(stockCode, category=_CATEGORY)
    except Exception as exc:
        log.debug("newsHeadlines/%s/%s.parquet 미가용: %s", marketU, dayIso, type(exc).__name__)
        return None


def loadNewsArchive(
    start: str | _date,
    end: str | _date,
    market: str = "KR",
    *,
    asof: str | _date | None = None,
) -> pl.DataFrame:
    """news headlines archive 기간 로드 + 옵션 PIT 필터.

    Capabilities:
        - 기간 [start..end] 일별 parquet concat
        - asof 지정 시 PIT 필터 (date ≤ asof AND captured_at ≤ asof)
        - 빈 결과는 동일 schema 빈 DataFrame
        - LRU 캐시 (`_loadDay` 128 일) — 반복 호출 메모리 hit

    AIContext:
        Phase B `narrativePulse.buildNarrativePulse` + Phase C `analyzeNarrative`
        의 입력 SSOT. 모든 narrative downstream 이 본 함수 경유.

    Guide:
        forward-only archive — 시작 시점 (T0) 이전 일자는 비어 있음.
        backtest 시 asof= 사용으로 look-ahead bias 차단.

    When:
        - dartlab.macro("내러티브") 진입점
        - 시나리오 엔진 narrative_signal 계산
        - 사용자 직접: `loadNewsArchive("2026-04-01","2026-05-01","KR")`

    How:
        start..end 일자 루프 → `_loadDay(market, day)` → pl.concat → asof 필터.

    Args:
        start: 시작일 (포함). YYYY-MM-DD 또는 date.
        end: 종료일 (포함). YYYY-MM-DD 또는 date.
        market: "KR" | "US". 기본 "KR".
        asof: PIT 시점 (포함). None 이면 필터 0 — 모든 archive 반환.

    Returns:
        pl.DataFrame — (date, title, source, url, market, query, captured_at)
        date desc + url 정렬. 빈 결과도 동일 schema.

    Raises:
        없음 — 미존재 일자는 silent skip.

    Example::

        df = loadNewsArchive("2026-05-01", "2026-05-28", "KR")
        dfPit = loadNewsArchive("2026-05-01", "2026-05-28", "KR", asof="2026-05-15")

    Requires:
        Phase A archive cron (syncNewsHeadlines.py) 가 1 회 이상 실행되어
        `data/news/headlines/{market}/*.parquet` 가 존재 또는 HF 보유.

    See Also:
        ``_loadDay``: 단일 일자 로더.
        ``gather.transforms.pit.applyAsOf``: PIT 필터 SSOT.
        ``.github/scripts/sync/syncNewsHeadlines.py``: archive write-side.
    """
    s = _toDate(start)
    e = _toDate(end)
    marketU = market.upper()

    frames: list[pl.DataFrame] = []
    for day in _dayRange(s, e):
        df = _loadDay(marketU, day.isoformat())
        if df is not None and df.height > 0:
            frames.append(df)

    if not frames:
        return pl.DataFrame(schema=_EMPTY_SCHEMA)

    out = pl.concat(frames, how="diagonal_relaxed")
    if asof is not None:
        asofIso = _toDate(asof).isoformat()
        out = applyAsOf(
            out,
            asofIso,
            businessCol="date",
            knowledgeCol="captured_at",
            fallbackCol="date",
        )
    out = out.unique(subset=["url"], keep="first")
    out = out.sort(["date", "url"], descending=[True, False])
    return out
