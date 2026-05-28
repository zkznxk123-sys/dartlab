"""도메인별 일일 quota tracker — 80% 도달 시 차단 + UTC midnight 자동 reset.

기존 ``http.py`` 의 429 핸들링은 *분당* rate limit 만 추적 (sliding window).
무료 데이터 vendor (FMP 250/day, Yahoo 비공식 2000/day) 는 *일일* cap 도 존재 —
도달 시 분당 limit 안에서도 429 폭주. 본 모듈이 일일 카운터를 박아서 80%
도달 시 사전 차단 → 다른 fallback 소스로 자동 라우팅.

`SourceHealthTracker` (resilience.py) + `circuitBreaker` 와 직교 (alive/accuracy/cap
3 축 분리).
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

log = logging.getLogger(__name__)

# 도메인별 일일 request 상한 — http.py DOMAIN_POLICY key 와 동일 hostname.
# 미등록 도메인은 무제한 (checkDaily 항상 True).
DAILY_LIMITS: dict[str, int] = {
    "query2.finance.yahoo.com": 2000,  # Yahoo v8 Chart 비공식 일일 한도
    "financialmodelingprep.com": 250,  # FMP free tier
}

# 차단 시작 임계 — 상한의 몇 % 도달부터 거절할지.
# 80% 면 fallback chain 의 다른 소스에 여유 두고 전환.
BLOCK_THRESHOLD_RATIO = 0.8


class _DailyQuotaTracker:
    """thread-safe 도메인별 일일 request counter.

    Attributes:
        _counts: 도메인 → 누적 count (당일 UTC).
        _lastResetUtcDate: 마지막 reset 된 UTC date (YYYY-MM-DD).
        _lock: thread-safe 가드.
    """

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._lastResetUtcDate: str = self._todayUtcDate()
        self._lock = threading.Lock()

    @staticmethod
    def _todayUtcDate() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _resetIfNewDay(self) -> None:
        """UTC midnight 지났으면 카운터 초기화. caller 는 lock 보유 상태."""
        today = self._todayUtcDate()
        if today != self._lastResetUtcDate:
            self._counts.clear()
            self._lastResetUtcDate = today

    def record(self, domain: str) -> None:
        """매 HTTP 호출 직후 counter +1.

        Sig: ``record(domain) -> None``

        Capabilities: thread-safe counter +1 + UTC midnight 자동 reset.
        AIContext: ``infra.http.GatherHttpClient.get/post`` 의 응답 직후 hook.
        Guide: 등록 안 된 domain 도 카운트 (관찰성). DAILY_LIMITS 만 차단 영향.
        When: HTTP 요청 1 회 발사 직후 (성공/실패 무관).
        How: lock → ``_resetIfNewDay`` → counter +1.

        Args:
            domain: hostname (예: ``"financialmodelingprep.com"``).

        Returns:
            None.

        Raises:
            없음.

        Example:
            >>> quotaTracker.record("financialmodelingprep.com")

        See Also:
            ``checkDaily`` — 본 카운터의 조회자.
        """
        with self._lock:
            self._resetIfNewDay()
            self._counts[domain] = self._counts.get(domain, 0) + 1

    def checkDaily(self, domain: str) -> bool:
        """일일 한도의 ``BLOCK_THRESHOLD_RATIO`` 미만이면 True (호출 허용).

        Sig: ``checkDaily(domain) -> bool``

        Capabilities: 일일 한도 80% 도달 사전 차단 신호.
        AIContext: ``infra.http.GatherHttpClient`` 의 GET/POST 직전 hook.
        Guide: 미등록 도메인 항상 True (no-op). 80% 임계로 fallback 여유 확보.
        When: HTTP 요청 발사 직전.
        How: lock → ``_resetIfNewDay`` → ``count < limit * 0.8`` 비교.

        Args:
            domain: hostname.

        Returns:
            True 면 호출 허용. False 면 일일 80% 초과 → 차단.

        Raises:
            없음.

        Example:
            >>> if not quotaTracker.checkDaily("financialmodelingprep.com"):
            ...     raise RateLimitExceededError("daily cap")

        See Also:
            ``record`` — count 증분.
            ``snapshot`` — 모든 도메인 현재 사용량 조회.
        """
        limit = DAILY_LIMITS.get(domain)
        if limit is None:
            return True  # 미등록 = 무제한
        with self._lock:
            self._resetIfNewDay()
            count = self._counts.get(domain, 0)
            return count < int(limit * BLOCK_THRESHOLD_RATIO)

    def snapshot(self) -> dict[str, int]:
        """모든 도메인 현재 누적 count (관찰성).

        Sig: ``snapshot() -> dict[str, int]``

        Capabilities: 도메인 → 당일 count dict 사본 반환.
        AIContext: 대시보드/디버그 — 일일 quota 소비량 확인.
        Guide: dict 사본 반환 (외부 수정 차단).
        When: 사용자/AI 가 quota 현황 조회 시.
        How: lock → ``_resetIfNewDay`` → dict copy.

        Returns:
            ``{domain: count}`` dict (당일 UTC 기준).

        Raises:
            없음.

        Example:
            >>> quotaTracker.snapshot()
            {'financialmodelingprep.com': 42}

        See Also:
            ``record`` · ``checkDaily``.
        """
        with self._lock:
            self._resetIfNewDay()
            return dict(self._counts)

    def reset(self) -> None:
        """수동 reset — 테스트 또는 운영 비상 조치 전용.

        Sig: ``reset() -> None``

        Capabilities: 모든 카운터 즉시 0 으로 + lastReset 갱신.
        AIContext: 테스트 fixture / 운영 비상 — 일반 호출 금지.
        Guide: production 코드에서 직접 호출 금지 (UTC midnight 자동 reset 사용).
        When: 테스트 setup / 운영 incident 후 강제 재시작.
        How: lock → counts.clear → lastResetUtcDate 오늘.

        Returns:
            None.

        Raises:
            없음.

        Example:
            >>> quotaTracker.reset()  # 테스트에서만

        See Also:
            ``_resetIfNewDay`` — 자동 일일 reset.
        """
        with self._lock:
            self._counts.clear()
            self._lastResetUtcDate = self._todayUtcDate()


# ── 모듈 레벨 싱글턴 ──

quotaTracker = _DailyQuotaTracker()


def record(domain: str) -> None:
    """모듈 레벨 shortcut — ``quotaTracker.record`` 위임."""
    quotaTracker.record(domain)


def checkDaily(domain: str) -> bool:
    """모듈 레벨 shortcut — ``quotaTracker.checkDaily`` 위임."""
    return quotaTracker.checkDaily(domain)
