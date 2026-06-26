"""제목 → 종목코드 해소 — 명시 6자리 코드 우선 + corpCode 상장사명 fallback.

1차: 제목 내 '(005930/매수)' 같은 명시 6자리 코드 정규식 추출 (의존성 0·오탐 0).
2차: corpCode 상장사명 최장 매칭 (DART_API_KEY 필요 — 실패 시 graceful skip).
산업·시황 리포트는 회사 없어 None — 0-fill 금지, None first-class.
"""

from __future__ import annotations

import re
from functools import lru_cache

_CODE_RE = re.compile(r"\((\d{6})[/)\s]")


@lru_cache(maxsize=1)
def _listedPairs() -> tuple[tuple[str, str], ...]:
    """상장사 (회사명, 종목코드) 튜플 — 이름 길이 내림차순. corpCode 실패 시 빈 튜플(graceful).

    Returns:
        tuple — (corp_name, stock_code) 들, 이름 길이 desc. corpCode 로드 실패 시 ().

    Example::

        _listedPairs()[:1]   # 최장 회사명부터
    """
    try:
        import polars as pl

        from dartlab.gather.dart import corpCode

        client = corpCode.DartClient()
        df = corpCode.loadCorpCodes(client)
        listed = df.filter(pl.col("stock_code").str.strip_chars().str.len_chars() == 6)
        pairs = [
            (r["corp_name"].strip(), r["stock_code"].strip()) for r in listed.iter_rows(named=True) if r["corp_name"]
        ]
        pairs.sort(key=lambda x: len(x[0]), reverse=True)
        return tuple(pairs)
    except Exception:  # noqa: BLE001 — 키/네트워크 없으면 명시코드 경로만 사용
        return ()


def _resolveTicker(title: str, *, minLen: int = 3, useNameMatch: bool = True) -> str | None:
    """제목 → 종목코드. 명시 6자리 코드 우선, 없으면 최장 상장사명 매칭(graceful).

    Args:
        title: 리포트 제목.
        minLen: 이름 매칭 최소 회사명 길이 (오탐 억제, 기본 3).
        useNameMatch: False 면 명시 코드만 사용 (corpCode 로드 회피).

    Returns:
        str | None — 6자리 종목코드. 회사 없으면/외국주식이면 None.

    Example::

        _resolveTicker("삼성전자 (005930/매수) ...")   # '005930'
        _resolveTicker("◆ Daily 시황 ◆")               # None
    """
    if not title:
        return None
    m = _CODE_RE.search(title)
    if m:
        return m.group(1)
    if not useNameMatch:
        return None
    for name, code in _listedPairs():
        if len(name) >= minLen and name in title:
            return code
    return None
