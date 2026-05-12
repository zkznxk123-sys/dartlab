"""Gather TTL 환경변수 SSOT (G+ P-Q4).

분산된 TTL 상수를 단일 모듈로 통합 + ``DARTLAB_TTL_*`` env 로 override 가능.
테스트 환경에서 ``DARTLAB_TTL_PRICE=0`` 으로 캐시 즉시 expire 검증 가능.

Capabilities:
    - 17 데이터 유형 TTL 단일 SSOT
    - 환경변수 (``DARTLAB_TTL_PRICE`` 등) 로 런타임 override
    - 0/음수 = 캐시 비활성 (즉시 만료)
    - listing.py 의 24h TTL (CACHE_TTL=86400) 도 포함

AIContext:
    - dev/CI 환경에서 fresh fetch 강제 — DARTLAB_TTL_PRICE=0
    - 캐시 hit/miss 디버깅 시 특정 도메인만 짧게 — DARTLAB_TTL_MACRO=60

Guide:
    환경변수 명명 규칙: ``DARTLAB_TTL_<DOMAIN>`` (대문자 + 언더스코어).
    값은 초 단위 정수. 미설정/파싱 실패 시 default 사용.

When:
    cache 호출자 모듈 (infra/cache.py · krx/listing/*.py) 가 import 시.

How:
    ``from dartlab.gather.infra.ttl import TTL_PRICE``
    값을 직접 사용 (재계산 X). 모듈 load 시 1회 env 읽음.

Requires:
    표준 라이브러리 ``os.environ`` 만 — 외부 의존 0.

Raises:
    없음 — int 파싱 실패는 silent default fallback.

Example::

    # 정상 사용
    from dartlab.gather.infra.ttl import TTL_PRICE, TTL_LISTING
    if (time.time() - cache_ts) > TTL_PRICE:
        refresh()

    # 테스트 환경
    # PowerShell: $env:DARTLAB_TTL_PRICE = "0"
    # bash: DARTLAB_TTL_PRICE=0 uv run pytest tests/...

See Also:
    ``infra.cache.GatherCache`` — TTL_PRICE 등 소비.
    ``krx.listing.{registry,dartList,krxList}`` — TTL_LISTING 소비.
"""

from __future__ import annotations

import os


def _envInt(name: str, default: int) -> int:
    """``DARTLAB_TTL_*`` env 가 정수면 사용, 아니면 default. 0/음수 = 캐시 비활성.

    Args:
        name: 환경변수 이름 (예: ``"DARTLAB_TTL_PRICE"``).
        default: env 미설정/파싱 실패 시 fallback 값 (초).

    Returns:
        int — TTL 초. 0/음수면 호출자가 캐시 비활성 의도로 해석.

    Raises:
        없음 — int 파싱 실패 silent fallback.

    Example::

        TTL_PRICE = _envInt("DARTLAB_TTL_PRICE", 300)
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# 17 데이터 유형별 TTL (초) — env 로 override 가능
TTL_PRICE = _envInt("DARTLAB_TTL_PRICE", 300)  # 5분
TTL_FLOW = _envInt("DARTLAB_TTL_FLOW", 3600)  # 1시간
TTL_SECTOR = _envInt("DARTLAB_TTL_SECTOR", 24 * 3600)  # 24시간
TTL_HISTORY = _envInt("DARTLAB_TTL_HISTORY", 6 * 3600)  # 6시간
TTL_SNAPSHOT = _envInt("DARTLAB_TTL_SNAPSHOT", 300)  # 5분 (전체 수집 결과)
TTL_NEWS = _envInt("DARTLAB_TTL_NEWS", 1800)  # 30분
TTL_DIVIDENDS = _envInt("DARTLAB_TTL_DIVIDENDS", 24 * 3600)  # 24시간
TTL_SPLITS = _envInt("DARTLAB_TTL_SPLITS", 24 * 3600)  # 24시간
TTL_MACRO = _envInt("DARTLAB_TTL_MACRO", 6 * 3600)  # 6시간
TTL_SHORT_SELLING = _envInt("DARTLAB_TTL_SHORT_SELLING", 3600)  # 1시간
TTL_INSIDER = _envInt("DARTLAB_TTL_INSIDER", 6 * 3600)  # 6시간
TTL_MAJOR_HOLDER = _envInt("DARTLAB_TTL_MAJOR_HOLDER", 24 * 3600)  # 24시간
TTL_INDEX_MEMBERS = _envInt("DARTLAB_TTL_INDEX_MEMBERS", 24 * 3600)  # 24시간
TTL_MARKET_CAP = _envInt("DARTLAB_TTL_MARKET_CAP", 3600)  # 1시간
TTL_OWNERSHIP = _envInt("DARTLAB_TTL_OWNERSHIP", 6 * 3600)  # 6시간
TTL_DEFAULT = _envInt("DARTLAB_TTL_DEFAULT", 3600)  # 1시간
TTL_LISTING = _envInt("DARTLAB_TTL_LISTING", 86400)  # 24시간 (KIND/KRX/DART listings)
