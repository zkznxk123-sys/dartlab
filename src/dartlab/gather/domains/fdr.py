"""FinanceDataReader 데이터 도메인 — KR/US 히스토리.

optional dependency: ``pip install finance-datareader``
fallback 체인에서 naver 다음 순서로 사용.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

_CACHE_DIR = Path.home() / ".dartlab" / "cache" / "history"


def _available() -> bool:
    """FinanceDataReader 패키지 설치 여부를 확인.

    Returns
    -------
    bool
        ``True`` — ``finance-datareader`` import 가능.
        ``False`` — 미설치.
    """
    try:
        import FinanceDataReader  # noqa: F401

        return True
    except ImportError:
        return False


async def fetchHistory(
    stockCode: str,
    client=None,
    *,
    start: str = "",
    end: str = "",
    market: str = "KR",
    **kwargs,
) -> list[dict]:
    """OHLCV 히스토리 — FDR 경유.

    Args:
        stock_code: 종목코드 (KR: "005930", US: "AAPL").
        start: 시작일 (YYYY-MM-DD). 빈 문자열이면 최대한 과거.
        end: 종료일. 빈 문자열이면 오늘.

    Returns:
        [{"date": ..., "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...}, ...]
    """
    if not _available():
        log.debug("FDR 미설치 — skip")
        return []

    import FinanceDataReader as fdr

    startDate = start or "1990-01-01"
    endDate = end or (date.today() + timedelta(days=1)).isoformat()

    # Parquet 캐시 확인
    cached = _loadCache(stockCode, market)
    if cached is not None:
        # 캐시 필터링
        filtered = [r for r in cached if (not start or r["date"] >= start) and (not end or r["date"] <= end)]
        if filtered:
            return filtered

    try:
        df = fdr.DataReader(stockCode, startDate, endDate)
    except (ImportError, OSError, ValueError, KeyError, TypeError) as exc:
        log.warning("FDR fetch 실패 (%s): %s", stockCode, exc)
        return []

    if df.empty:
        return []

    rows: list[dict] = []
    for idx, row in df.iterrows():
        dateStr = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
        rows.append(
            {
                "date": dateStr,
                "open": float(row.get("Open", 0)),
                "high": float(row.get("High", 0)),
                "low": float(row.get("Low", 0)),
                "close": float(row.get("Close", 0)),
                "volume": int(row.get("Volume", 0)),
            }
        )

    # Parquet 캐시 저장
    _saveCache(stockCode, market, rows)

    return rows


def _cacheKey(stockCode: str, market: str) -> Path:
    """OHLCV 히스토리 Parquet 캐시 파일 경로를 생성.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: ``"005930"``, ``"AAPL"``).
    market : str
        시장 코드 (예: ``"KR"``, ``"US"``). 소문자로 변환하여 하위 디렉터리 결정.

    Returns
    -------
    Path
        ``~/.dartlab/cache/history/{market}/{stockCode}.parquet`` 경로.
        부모 디렉터리가 없으면 자동 생성.
    """
    subdir = _CACHE_DIR / market.lower()
    subdir.mkdir(parents=True, exist_ok=True)
    return subdir / f"{stockCode}.parquet"


def _saveCache(stockCode: str, market: str, rows: list[dict]) -> None:
    """OHLCV 히스토리를 Parquet 캐시로 저장.

    Parameters
    ----------
    stockCode : str
        종목코드.
    market : str
        시장 코드.
    rows : list[dict]
        OHLCV 행 목록. 빈 리스트면 저장하지 않음.

    Returns
    -------
    None
        파일 저장 완료 후 반환. 저장 실패 시 경고 로그만 남김.
    """
    if not rows:
        return
    try:
        import polars as pl

        df = pl.DataFrame(rows)
        path = _cacheKey(stockCode, market)
        df.write_parquet(path)
        log.debug("FDR 캐시 저장: %s (%d rows)", path, len(rows))
    except (ImportError, OSError, ValueError, KeyError, TypeError) as exc:
        log.warning("FDR 캐시 저장 실패: %s", exc)


def _loadCache(stockCode: str, market: str) -> list[dict] | None:
    """Parquet 캐시에서 OHLCV 히스토리를 로드.

    캐시 파일이 1일 이내 생성된 경우만 사용한다.

    Parameters
    ----------
    stockCode : str
        종목코드.
    market : str
        시장 코드.

    Returns
    -------
    list[dict] | None
        캐시된 OHLCV 행 목록. 각 dict는 date/open/high/low/close/volume 키 포함.
        캐시 없음, 1일 초과, 읽기 실패 시 None.
    """
    path = _cacheKey(stockCode, market)
    if not path.exists():
        return None

    import os
    from datetime import datetime

    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    if (datetime.now() - mtime).days > 1:
        return None

    try:
        import polars as pl

        df = pl.read_parquet(path)
        return df.to_dicts()
    except (ImportError, OSError, ValueError):
        return None
