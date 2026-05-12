"""장애 방어 — Circuit Breaker + Source Health Tracker."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

# ══════════════════════════════════════
# Circuit Breaker
# ══════════════════════════════════════


class _State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class _CircuitState:
    state: _State = _State.CLOSED
    failure_count: int = 0
    opened_at: float = 0.0


class CircuitBreaker:
    """소스별 circuit breaker.

    - closed → open: 연속 ``failure_threshold`` 회 실패
    - open → half_open: ``recovery_timeout`` 초 경과 후 1회 시도
    - half_open → closed: 성공 시 / open: 실패 시
    """

    __slots__ = ("_failure_threshold", "_recovery_timeout", "_circuits", "_lock")

    def __init__(
        self,
        failureThreshold: int = 5,
        recoveryTimeout: float = 300.0,
    ) -> None:
        """CircuitBreaker 초기화.

        Parameters
        ----------
        failure_threshold : int
            서킷을 open으로 전환하는 연속 실패 횟수. 기본 5.
        recovery_timeout : float
            open 상태에서 half_open 시도까지 대기 시간 (초). 기본 300.0.
        """
        self._failure_threshold = failureThreshold
        self._recovery_timeout = recoveryTimeout
        self._circuits: dict[str, _CircuitState] = {}
        self._lock = threading.Lock()

    def _get(self, source: str) -> _CircuitState:
        """소스별 서킷 상태 반환 (없으면 CLOSED로 생성).

        Parameters
        ----------
        source : str
            데이터 소스 이름.

        Returns
        -------
        _CircuitState
            state : _State — 현재 서킷 상태
            failure_count : int — 연속 실패 횟수 (회)
            opened_at : float — OPEN 전환 시각 (monotonic, 초)
        """
        if source not in self._circuits:
            self._circuits[source] = _CircuitState()
        return self._circuits[source]

    def isOpen(self, source: str) -> bool:
        """소스가 차단 상태인지 확인. half_open 전환도 처리.

        Capabilities: thread-safe state machine — CLOSED/OPEN/HALF_OPEN 분기.
        AIContext: 외부 source 의 cascading failure 차단 — fallback chain 진입 직전.
        Guide: half_open 은 1 회만 허용. recovery_timeout 경과 시 half_open 시도.
        When: 매 fetch 시도 직전 source 차단 여부 검증.
        How: lock → state 분기 (CLOSED → False / HALF_OPEN → OPEN 1회 / OPEN → timeout 비교).

        half_open은 1회만 허용 — 첫 호출이 허용되면 즉시 OPEN으로 되돌려
        다른 스레드의 동시 통과를 방지한다. record_success()에서 CLOSED로 전환.

        Parameters
        ----------
        source : str
            데이터 소스 이름 (예: "naver", "fmp").

        Returns
        -------
        bool
            True면 차단 상태 (요청 불가), False면 통과 허용.

        Raises
        ------
        없음.

        Requires
        --------
        ``self._lock`` + ``self._circuits`` dict.

        Example
        -------
        >>> if not cb.isOpen("naver"):
        ...     fetch_naver()

        See Also
        --------
        recordSuccess · recordFailure : state 전환 trigger.
        state : 디버깅 문자열.
        """
        with self._lock:
            cs = self._get(source)
            if cs.state == _State.CLOSED:
                return False
            if cs.state == _State.HALF_OPEN:
                # 1회 시도 허용 후 즉시 OPEN 복귀 (동시 통과 방지)
                cs.state = _State.OPEN
                cs.opened_at = time.monotonic()
                return False
            # OPEN — recovery timeout 경과 시 1회 시도 허용
            if time.monotonic() - cs.opened_at >= self._recovery_timeout:
                # 타이머 리셋 후 이번 1회만 허용 (다음 호출은 다시 차단)
                cs.opened_at = time.monotonic()
                return False
            return True

    def recordSuccess(self, source: str) -> None:
        """소스 성공 기록 및 서킷 닫기.

        Capabilities: state = CLOSED + failure_count 리셋.
        AIContext: fetch 성공 후 회복 신호 — half_open → CLOSED 복귀.
        Guide: 성공 1 회로 즉시 회복 (관대 정책).
        When: fetch 성공 직후.
        How: lock → state = CLOSED + failure_count = 0.

        Parameters
        ----------
        source : str
            데이터 소스 이름.

        Returns
        -------
        None

        Raises
        ------
        없음.

        Requires
        --------
        ``self._lock`` + ``self._circuits``.

        Example
        -------
        >>> cb.recordSuccess("naver")

        See Also
        --------
        recordFailure : 짝 — 실패 시 OPEN 전환.
        """
        with self._lock:
            cs = self._get(source)
            cs.state = _State.CLOSED
            cs.failure_count = 0

    def recordFailure(self, source: str) -> None:
        """소스 실패 기록 및 임계치 초과 시 서킷 열기.

        Capabilities: failure_count 증가 + HALF_OPEN 시 OPEN 복귀 + 임계치 초과 시 OPEN 전환.
        AIContext: cascading failure 차단 — N 회 연속 실패 시 source 차단.
        Guide: failure_threshold (기본 5) 도달 시 OPEN.
        When: fetch 실패 직후.
        How: lock → failure_count += 1 → state 분기 (HALF_OPEN → OPEN / 임계 초과 → OPEN).

        Parameters
        ----------
        source : str
            데이터 소스 이름.

        Returns
        -------
        None

        Raises
        ------
        없음.

        Requires
        --------
        ``self._lock`` + ``self._circuits``.

        Example
        -------
        >>> cb.recordFailure("naver")

        See Also
        --------
        recordSuccess : 짝.
        isOpen : 본 메서드 결과의 후속 조회.
        """
        with self._lock:
            cs = self._get(source)
            cs.failure_count += 1
            if cs.state == _State.HALF_OPEN:
                # half_open에서 실패 → 다시 open
                cs.state = _State.OPEN
                cs.opened_at = time.monotonic()
            elif cs.failure_count >= self._failure_threshold:
                cs.state = _State.OPEN
                cs.opened_at = time.monotonic()

    def state(self, source: str) -> str:
        """현재 상태 문자열 반환 (디버깅용).

        Capabilities: ``_State.value`` 추출 — 사용자 표시용 문자열.
        AIContext: 디버깅 / 모니터링 / dashboard 표시 진입.
        Guide: "closed"/"open"/"half_open" — _State enum 값.
        When: source 차단 상태 진단 시.
        How: ``self._get(source).state.value``.

        Parameters
        ----------
        source : str
            데이터 소스 이름.

        Returns
        -------
        str
            "closed", "open", "half_open" 중 하나.

        Raises
        ------
        없음.

        Requires
        --------
        ``self._lock`` + ``self._circuits``.

        Example
        -------
        >>> cb.state("naver")

        See Also
        --------
        isOpen : boolean 변형.
        """
        with self._lock:
            return self._get(source).state.value


# ══════════════════════════════════════
# Source Health Tracker
# ══════════════════════════════════════


@dataclass
class _HealthRecord:
    timestamp: float
    success: bool
    latency: float = 0.0


@dataclass
class _SourceHealth:
    records: deque[_HealthRecord] = field(default_factory=lambda: deque(maxlen=100))

    @property
    def score(self) -> float:
        """health_score = success_rate × 0.7 + latency_score × 0.3.

        Capabilities: sliding window 100 건 → success rate + latency 가중 점수.
        AIContext: SourceHealthTracker.reorder 의 정렬 키.
        Guide: 기록 0 → 0.5 중립. latency 1s = 1.0 / 10s = 0.0.
        When: SourceHealthTracker.score / reorder 가 본 property 조회 시.
        How: success_rate*0.7 + latency_score*0.3.

        Returns
        -------
        float
            건강도 점수 (0.0~1.0, 점). 기록 없으면 0.5 (중립).

        Raises
        ------
        없음.

        Requires
        --------
        ``self.records`` deque.

        Example
        -------
        >>> h.score

        See Also
        --------
        SourceHealthTracker.score · reorder : 본 property caller.
        """
        if not self.records:
            return 0.5  # 데이터 없으면 중립
        successes = sum(1 for r in self.records if r.success)
        success_rate = successes / len(self.records)
        # latency_score: 평균 응답시간 기반 (1초 이하 = 1.0, 10초 = 0.0)
        latencies = [r.latency for r in self.records if r.success and r.latency > 0]
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            latency_score = max(0.0, 1.0 - avg_latency / 10.0)
        else:
            latency_score = 0.5
        return success_rate * 0.7 + latency_score * 0.3


class SourceHealthTracker:
    """소스별 건강도 추적 — sliding window 100건."""

    __slots__ = ("_sources", "_lock")

    def __init__(self) -> None:
        self._sources: dict[str, _SourceHealth] = {}
        self._lock = threading.Lock()

    def record(self, source: str, *, success: bool, latency: float = 0.0) -> None:
        """소스 요청 결과(성공/실패, 지연시간) 기록.

        Capabilities: thread-safe sliding window deque (maxlen=100) push.
        AIContext: 매 fetch 결과 health log — reorder 기반.
        Guide: latency 0 = unknown (성공 latency 만 score 에 반영).
        When: gather domains/* 의 fetch 직후.
        How: lock → _HealthRecord(timestamp, success, latency) deque.append.

        Parameters
        ----------
        source : str
            데이터 소스 이름.
        success : bool
            요청 성공 여부.
        latency : float
            응답 지연시간 (초). 기본 0.0.

        Returns
        -------
        None

        Raises
        ------
        없음.

        Requires
        --------
        ``self._lock`` + ``self._sources`` dict.

        Example
        -------
        >>> tracker.record("naver", success=True, latency=0.4)

        See Also
        --------
        score · reorder : 본 메서드 결과의 후속 조회/정렬.
        """
        with self._lock:
            if source not in self._sources:
                self._sources[source] = _SourceHealth()
            self._sources[source].records.append(
                _HealthRecord(
                    timestamp=time.monotonic(),
                    success=success,
                    latency=latency,
                )
            )

    def score(self, source: str) -> float:
        """소스의 현재 건강도 점수 반환.

        Capabilities: ``_SourceHealth.score`` property 조회 (thread-safe).
        AIContext: source 신뢰도 진단 — reorder / dashboard 진입.
        Guide: 0.5 = 중립 (데이터 없음).
        When: reorder 가 호출 / 사용자 모니터링 시.
        How: lock → ``self._sources[source].score`` direct.

        Parameters
        ----------
        source : str
            데이터 소스 이름.

        Returns
        -------
        float
            건강도 점수 (0.0~1.0, 점). 데이터 없으면 0.5 (중립).

        Raises
        ------
        없음.

        Requires
        --------
        ``self._lock`` + ``self._sources``.

        Example
        -------
        >>> s = tracker.score("naver")

        See Also
        --------
        reorder : 본 메서드 결과로 chain 정렬.
        _SourceHealth.score : 위임 property.
        """
        with self._lock:
            if source not in self._sources:
                return 0.5
            return self._sources[source].score

    def reorder(self, chain: tuple[str, ...] | list[str]) -> list[str]:
        """fallback 체인을 health score 높은 순으로 재정렬.

        Capabilities: chain 각 source 의 score 계산 → sort desc → 0.2 미만 차이 시 원본 유지.
        AIContext: 동적 fallback chain 최적화 — sources/price.fetch 의 chain 정렬.
        Guide: 안정성 — 0.2 미만 차이는 노이즈 취급 (원본 순서 유지).
        When: gather sources/* 의 fetch chain 진입 직전.
        How: scored sort desc → diff < 0.2 시 chain 원본 / 아니면 재정렬.

        원본 순서를 존중하되 health 차이가 유의미하면(0.2+) 재정렬.

        Parameters
        ----------
        chain : tuple[str, ...] | list[str]
            원본 fallback 소스 순서.

        Returns
        -------
        list[str]
            health score 기준 재정렬된 소스 이름 리스트.
            1위와 최하위 차이가 0.2 미만이면 원본 순서 유지.

        Raises
        ------
        없음.

        Requires
        --------
        ``self._sources`` + ``score`` 가용.

        Example
        -------
        >>> reordered = tracker.reorder(("naver", "fmp", "yahoo"))

        See Also
        --------
        score : 본 메서드의 source 신호.
        sources/price.fetch : 본 메서드의 caller.
        """
        scored = [(name, self.score(name)) for name in chain]
        # 안정적 정렬: score 같으면 원래 순서 유지
        scored.sort(key=lambda x: -x[1])
        # 1위와 나머지 차이가 0.2 미만이면 원래 순서 유지
        if len(scored) > 1 and scored[0][1] - scored[-1][1] < 0.2:
            return list(chain)
        return [name for name, _ in scored]


# ── 모듈 레벨 싱글턴 ──

circuitBreaker = CircuitBreaker()
healthTracker = SourceHealthTracker()
