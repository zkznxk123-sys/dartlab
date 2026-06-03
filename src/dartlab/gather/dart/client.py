"""OpenDART HTTP 클라이언트.

- 멀티 키 로테이션 (키 여러 개 → rate limit 분산)
- rate limit 자동 조절 + 초과 시 다음 키로 전환 재시도
- 응답 → Polars DataFrame 변환
- 에러 코드 구조화 처리 (013 = 빈 DataFrame 옵션)
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import polars as pl

from dartlab.core.dartClient import DartApiError, registerDartFetchProvider
from dartlab.gather.dart.keys import resolveDartKeys

BASE_URL = "https://opendart.fss.or.kr/api"

# 키 020 (rate limit) 시 cooldown — DART 분당 580 rpm 회복 대기.
_COOLDOWN_SEC = 60.0


@dataclass
class _KeySlot:
    """단일 API 키 + per-key throttle 상태. 스레드별 slot 예약으로 간섭 차단."""

    key: str
    nextAvailable: float = 0.0  # epoch — 다음 요청 가능 시각 (예약 포함)
    coolDownUntil: float = 0.0  # 020 발생 시 회복 시각
    failures: int = 0  # 누적 실패 (디버그)
    inFlight: int = 0  # 현재 진행 중 요청 수


_ERROR_MESSAGES: dict[str, str] = {
    "000": "정상",
    "010": "등록되지 않은 API 키",
    "011": "사용할 수 없는 API 키",
    "013": "조회된 데이터가 없음",
    "020": "요청 제한 초과",
    "100": "필드 오류",
    "800": "시스템 점검 중",
    "900": "정의되지 않은 오류",
}


class DartClient:
    """OpenDART API 클라이언트 — 멀티 키 로테이션 지원.

    Parameters
    ----------
    apiKey : str | None
        단일 API 키.
    apiKeys : list[str] | None
        복수 API 키 (로테이션). apiKey보다 우선.
    requestsPerMinute : int
        키당 분당 최대 요청 수 (기본 580).

    키 탐색 순서:
    1. apiKeys 파라미터
    2. apiKey 파라미터
    3. 환경변수 DART_API_KEYS (쉼표 구분)
    4. 환경변수 DART_API_KEY (단일)
    """

    def __init__(
        self,
        apiKey: str | None = None,
        apiKeys: list[str] | None = None,
        requestsPerMinute: int = 580,
    ):
        self._keys = self._resolveKeys(apiKey, apiKeys)
        if not self._keys:
            raise ValueError(
                "DART API 키가 필요합니다.\n"
                "  설정 방법 (우선순위 순):\n"
                "  1. DartClient(apiKey='...')  직접 전달\n"
                "  2. 환경변수 DART_API_KEY 또는 DART_API_KEYS(쉼표 구분) 설정\n"
                "  3. 프로젝트 루트 .env 파일에 DART_API_KEY=... 작성\n"
                "  발급: https://opendart.fss.or.kr → 인증키 신청"
            )
        self._minInterval = 60.0 / requestsPerMinute
        self._slots: list[_KeySlot] = [_KeySlot(key=k) for k in self._keys]
        self._poolLock = threading.Lock()
        # httpx.Client 는 thread-safe (per docs) — 단일 인스턴스 공유 OK.
        self._session = httpx.Client(follow_redirects=True)

    @staticmethod
    def _resolveKeys(apiKey: str | None, apiKeys: list[str] | None) -> list[str]:
        """키 탐색 우선순위: 파라미터 → 환경변수 → .env 파일."""
        return resolveDartKeys(apiKey=apiKey, apiKeys=apiKeys)

    @property
    def currentKey(self) -> str:
        """현재 사용 중인 DART API 키를 반환한다.

        Args:
            (인자 자동 생성).

        Raises:
            없음.

        Example:
            >>> currentKey(...)

        Returns:
            str — 현재 활성 키.

        LLM Specifications:
            AntiPatterns:
                - DartApiError (status="013" 등) 미처리 → 예외 propagate. caller try/except 의무.
                - 단일 키로 분당 580 req 초과 → rate limit. 멀티 키 (DART_API_KEYS) 사용.
            OutputSchema:
                - pl.DataFrame / dict / bytes — endpoint 별.
            Prerequisites:
                - 인터넷 + DART_API_KEY 또는 DART_API_KEYS.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → httpx → DART API → 응답 정규화 → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        return self._slots[0].key

    def _acquireSlot(self) -> tuple[_KeySlot, float]:
        """순차 키 소진 패턴 — `.github/scripts/sync/syncRecent.py` 와 동일.

        DART per-IP anti-abuse 는 매 요청 다른 키 rotation 을 abuse 로 분류.
        finance/syncRecent 가 차단 0 으로 동작했던 이유 = 키 1개로 580 rpm 소진
        후 다음 키. 본 method 도 같은 패턴:
        1. 첫 가용 slot (cooldown 안 걸린 것) 반환 — 매 요청 동일 키
        2. 같은 slot 의 throttle (slot.nextAvailable) 만 caller 가 sleep
        3. 020 발생 → _markCoolDown 으로 60s 잠금 → 자동 다음 slot
        4. 모든 slot cooldown → 가장 빨리 풀리는 slot 의 cooldown 시각까지 대기

        스레드 안전: _poolLock 안에서 slot 선택 + nextAvailable 예약.
        """
        now = time.monotonic()
        with self._poolLock:
            # 1. cooldown 안 걸린 첫 slot 사용 (sequential exhausted)
            for s in self._slots:
                if s.coolDownUntil <= now:
                    startAt = max(now, s.nextAvailable)
                    s.nextAvailable = startAt + self._minInterval
                    s.inFlight += 1
                    return s, max(0.0, startAt - now)
            # 2. 전부 cooldown — 가장 빨리 풀리는 slot 대기
            best = min(self._slots, key=lambda s: s.coolDownUntil)
            startAt = best.coolDownUntil
            best.nextAvailable = startAt + self._minInterval
            best.inFlight += 1
            return best, max(0.0, startAt - now)

    def _releaseSlot(self, slot: _KeySlot) -> None:
        with self._poolLock:
            slot.inFlight = max(0, slot.inFlight - 1)

    def _markCoolDown(self, slot: _KeySlot) -> None:
        with self._poolLock:
            slot.coolDownUntil = time.monotonic() + _COOLDOWN_SEC
            slot.failures += 1

    def _allSlotsCoolingDown(self) -> bool:
        now = time.monotonic()
        with self._poolLock:
            return all(s.coolDownUntil > now for s in self._slots)

    def getJson(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        emptyOn013: bool = False,
    ) -> dict[str, Any]:
        """JSON 엔드포인트 호출.

        Parameters
        ----------
        emptyOn013 : bool
            True면 '013' (데이터 없음) 시 에러 대신 빈 dict 반환.

        Raises:
            없음.

        Example:
            >>> getJson(...)

        Args:
            endpoint: DART API endpoint (예 "company.json").
            params: 요청 파라미터 dict. None 이면 빈 dict.
            emptyOn013: True 면 DART status="013" (조회 결과 없음) 을 빈 결과로 변환.

        Returns:
            dict[str, Any] — DART OpenAPI JSON 응답.

        SeeAlso:
            - ``resolveDartKeys`` — 멀티 키 resolve.
            - ``Dart`` facade — 본 client wrapper.

        Requires:
            - dartlab
            - httpx
            - polars
            - time

        Capabilities:
            - DART OpenAPI HTTP 호출 + 멀티 키 로테이션 + rate limit 분산 + DataFrame 변환.
              에러 코드 013 (empty result) 옵션 처리.

        Guide:
            - 사용자 facade 는 ``Dart()`` — 본 클래스 직접 사용 X.

        AIContext:
            internal HTTP client — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - DartApiError (status="013" 등) 미처리 → 예외 propagate. caller try/except 의무.
                - 단일 키로 분당 580 req 초과 → rate limit. 멀티 키 (DART_API_KEYS) 사용.
            OutputSchema:
                - pl.DataFrame / dict / bytes — endpoint 별.
            Prerequisites:
                - 인터넷 + DART_API_KEY 또는 DART_API_KEYS.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → httpx → DART API → 응답 정규화 → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        url = f"{BASE_URL}/{endpoint}"
        cooldownAttempts = 0
        maxCooldownAttempts = max(2 * len(self._slots), 4)
        while cooldownAttempts < maxCooldownAttempts:
            slot, sleepFor = self._acquireSlot()
            if sleepFor > 0:
                time.sleep(sleepFor)
            try:
                merged = {"crtfc_key": slot.key}
                if params:
                    merged.update(params)
                resp = self._session.get(url, params=merged, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status", "000")
                if status == "000":
                    return data
                if status == "013" and emptyOn013:
                    return {}
                if status == "020":
                    self._markCoolDown(slot)
                    cooldownAttempts += 1
                    if self._allSlotsCoolingDown():
                        time.sleep(1.0)
                    continue
                msg = data.get("message", _ERROR_MESSAGES.get(status, "알 수 없는 오류"))
                raise DartApiError(status, msg)
            finally:
                self._releaseSlot(slot)

        msg = _ERROR_MESSAGES.get("020", "요청 제한 초과")
        raise DartApiError("020", f"{msg} (모든 키 cooldown)")

    def getBytes(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> bytes:
        """바이너리 엔드포인트 호출 (ZIP, XML 다운로드 등).

        JSON 에러 응답도 감지하고, rate limit 시 키 로테이션.

        Args:
            endpoint: 인자.
            params: 인자.

        Raises:
            없음.

        Example:
            >>> getBytes(...)

        Returns:
            bytes — DART OpenAPI binary 응답.

        SeeAlso:
            - ``resolveDartKeys`` — 멀티 키 resolve.
            - ``Dart`` facade — 본 client wrapper.

        Requires:
            - dartlab
            - httpx
            - polars
            - time

        Capabilities:
            - DART OpenAPI HTTP 호출 + 멀티 키 로테이션 + rate limit 분산 + DataFrame 변환.
              에러 코드 013 (empty result) 옵션 처리.

        Guide:
            - 사용자 facade 는 ``Dart()`` — 본 클래스 직접 사용 X.

        AIContext:
            internal HTTP client — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - DartApiError (status="013" 등) 미처리 → 예외 propagate. caller try/except 의무.
                - 단일 키로 분당 580 req 초과 → rate limit. 멀티 키 (DART_API_KEYS) 사용.
            OutputSchema:
                - pl.DataFrame / dict / bytes — endpoint 별.
            Prerequisites:
                - 인터넷 + DART_API_KEY 또는 DART_API_KEYS.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → httpx → DART API → 응답 정규화 → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        url = f"{BASE_URL}/{endpoint}"
        cooldownAttempts = 0
        maxCooldownAttempts = max(2 * len(self._slots), 4)
        while cooldownAttempts < maxCooldownAttempts:
            slot, sleepFor = self._acquireSlot()
            if sleepFor > 0:
                time.sleep(sleepFor)
            try:
                merged = {"crtfc_key": slot.key}
                if params:
                    merged.update(params)
                resp = self._session.get(url, params=merged, timeout=60)
                resp.raise_for_status()
                # OpenDART 는 바이너리 에러 시에도 JSON 반환 가능.
                contentType = resp.headers.get("Content-Type", "")
                if "application/json" in contentType or "text/json" in contentType:
                    data = resp.json()
                    status = data.get("status", "000")
                    if status == "020":
                        self._markCoolDown(slot)
                        cooldownAttempts += 1
                        if self._allSlotsCoolingDown():
                            time.sleep(1.0)
                        continue
                    if status != "000":
                        msg = data.get("message", _ERROR_MESSAGES.get(status, "알 수 없는 오류"))
                        raise DartApiError(status, msg)
                return resp.content
            finally:
                self._releaseSlot(slot)

        raise DartApiError("020", "요청 제한 초과 (모든 키 cooldown)")

    def getDf(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        listKey: str = "list",
    ) -> pl.DataFrame:
        """JSON → Polars DataFrame. 데이터 없으면 빈 DataFrame.

        Args:
            endpoint: 인자.
            params: 인자.
            listKey: 인자.

        Raises:
            없음.

        Example:
            >>> getDf(...)

        Returns:
            pl.DataFrame — DART OpenAPI 응답 정규화 결과.

        SeeAlso:
            - ``resolveDartKeys`` — 멀티 키 resolve.
            - ``Dart`` facade — 본 client wrapper.

        Requires:
            - dartlab
            - httpx
            - polars
            - time

        Capabilities:
            - DART OpenAPI HTTP 호출 + 멀티 키 로테이션 + rate limit 분산 + DataFrame 변환.
              에러 코드 013 (empty result) 옵션 처리.

        Guide:
            - 사용자 facade 는 ``Dart()`` — 본 클래스 직접 사용 X.

        AIContext:
            internal HTTP client — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - DartApiError (status="013" 등) 미처리 → 예외 propagate. caller try/except 의무.
                - 단일 키로 분당 580 req 초과 → rate limit. 멀티 키 (DART_API_KEYS) 사용.
            OutputSchema:
                - pl.DataFrame / dict / bytes — endpoint 별.
            Prerequisites:
                - 인터넷 + DART_API_KEY 또는 DART_API_KEYS.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → httpx → DART API → 응답 정규화 → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        data = self.getJson(endpoint, params, emptyOn013=True)
        rows = data.get(listKey, [])
        if not rows:
            return pl.DataFrame()
        return pl.DataFrame(rows)

    def getDfAll(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        listKey: str = "list",
        pageSize: int = 100,
    ) -> pl.DataFrame:
        """자동 페이지네이션 → 전체 결과 Polars DataFrame.

        Args:
            endpoint: 인자.
            params: 인자.
            listKey: 인자.
            pageSize: 인자.

        Raises:
            없음.

        Example:
            >>> getDfAll(...)

        Returns:
            pl.DataFrame — DART OpenAPI 응답 정규화 결과.

        SeeAlso:
            - ``resolveDartKeys`` — 멀티 키 resolve.
            - ``Dart`` facade — 본 client wrapper.

        Requires:
            - dartlab
            - httpx
            - polars
            - time

        Capabilities:
            - DART OpenAPI HTTP 호출 + 멀티 키 로테이션 + rate limit 분산 + DataFrame 변환.
              에러 코드 013 (empty result) 옵션 처리.

        Guide:
            - 사용자 facade 는 ``Dart()`` — 본 클래스 직접 사용 X.

        AIContext:
            internal HTTP client — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - DartApiError (status="013" 등) 미처리 → 예외 propagate. caller try/except 의무.
                - 단일 키로 분당 580 req 초과 → rate limit. 멀티 키 (DART_API_KEYS) 사용.
            OutputSchema:
                - pl.DataFrame / dict / bytes — endpoint 별.
            Prerequisites:
                - 인터넷 + DART_API_KEY 또는 DART_API_KEYS.
            Freshness:
                - DART OpenAPI 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → httpx → DART API → 응답 정규화 → 본 함수.
            TargetMarkets:
                - KR (DART) 한정.
        """
        merged = dict(params) if params else {}
        merged["page_count"] = str(pageSize)

        allRows: list[dict] = []
        page = 1

        while True:
            merged["page_no"] = str(page)
            data = self.getJson(endpoint, merged, emptyOn013=True)
            rows = data.get(listKey, [])
            if not rows:
                break
            allRows.extend(rows)

            totalPage = int(data.get("total_page", 1))
            if page >= totalPage:
                break
            page += 1

        if not allRows:
            return pl.DataFrame()
        return pl.DataFrame(allRows)


# ── DartFetchProvider 구현 + register (정공법 B — DIP) ─────────────
# providers build/read 가 core.dartClient seam 으로 client·키를 얻는다 (providers↛gather).


class _DartFetchProvider:
    """core.dartClient.DartFetchProvider 구현 — gather 가 DART fetch 전담."""

    def makeClient(self, apiKey=None, apiKeys=None, requestsPerMinute=580):
        """멀티 키 DartClient 인스턴스 생성."""
        return DartClient(apiKey=apiKey, apiKeys=apiKeys, requestsPerMinute=requestsPerMinute)

    def resolveKeys(self, apiKey=None, apiKeys=None):
        """DART API 키 list resolve."""
        return resolveDartKeys(apiKey=apiKey, apiKeys=apiKeys)

    def hasKey(self):
        """DART API 키 설정 여부."""
        from dartlab.gather.dart.keys import hasDartApiKey

        return hasDartApiKey()


registerDartFetchProvider(_DartFetchProvider())
