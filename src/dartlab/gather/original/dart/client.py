"""DART OpenAPI HTTP client — gather 자체포함 (키풀 sequential-exhausted).

「공시 오리지널 수집」 모듈이 ``gather ↛ providers`` 규칙을 지키며 자체포함되도록,
DART 인증 client 를 모듈 안에서 직접 구현한다. providers ``DartClient``
(``providers/dart/openapi/client.py``)와 **동일한 sequential-exhausted 키 로테이션**을
재현해 DART per-IP anti-abuse 차단(operation.docsBuilderRefactor §15)을 회귀시키지
않는다.

self-contained 의도(복제) — providers client 를 import 하지 않는다. 본 client 는
원본 수집에 필요한 2 endpoint 만 노출: ``list.json``(공시 목록) · ``document.xml``
(원본 zip bytes).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx

from .keys import resolveDartKeys

_BASE_URL = "https://opendart.fss.or.kr/api"
_COOLDOWN_SEC = 60.0  # status 020(한도 초과) 시 키 cooldown — 분당 회복 대기
_DEFAULT_RPM = 580  # DART 키당 분당 한도


@dataclass
class _KeySlot:
    """단일 API 키 + per-key throttle 상태 (스레드별 slot 예약으로 간섭 차단)."""

    key: str
    nextAvailable: float = 0.0  # monotonic — 다음 요청 가능 시각(예약 포함)
    coolDownUntil: float = 0.0  # 020 발생 시 회복 시각
    inFlight: int = 0


class OriginalDartClientError(Exception):
    """OpenDART 원본 수집 client 에러 (한도 소진 / API 키 오류 등)."""


class OriginalDartClient:
    """DART OpenAPI 인증 client — 키풀 sequential-exhausted (원본 수집 전용).

    Capabilities:
        - 멀티 키 sequential-exhausted 로테이션(키 1개 580rpm 소진 후 다음 키 — 매
          요청 rotation 이 아님 → DART per-IP 차단 회피, §15).
        - ``list.json`` 공시 목록(페이지 단위) + ``document.xml`` 원본 zip bytes.
        - status 020(한도) 자동 cooldown 후 다음 키 전환, 전 키 cooldown 시 대기.
        - 스레드 안전(``_poolLock``) — ``archiveDartOriginals`` 의 ThreadPool 공유.

    Args:
        apiKey: 단일 키(테스트/단일키 환경).
        apiKeys: 복수 키(키풀). apiKey 보다 우선.
        requestsPerMinute: 키당 분당 한도(기본 580).

    Returns:
        OriginalDartClient 인스턴스.

    Raises:
        OriginalDartClientError: 사용 가능한 DART 키가 0개.

    Example:
        >>> client = OriginalDartClient(apiKey="...")  # doctest: +SKIP
        >>> raw = client.getBytes("document.xml", {"rcept_no": "20240101000001"})  # doctest: +SKIP

    Guide:
        - 키는 ``DART_API_KEYS``(쉼표) 다중 권장 — per-IP 한도 분산.
        - 본 client 는 원본 수집 전용 저수준 — 사용자 facade 아님.

    SeeAlso:
        - ``gather.original.dart.collect.archiveDartOriginals`` — 본 client 소비자.
        - ``providers.dart.openapi.client.DartClient`` — 동일 패턴 원본(import 안 함).

    Requires:
        - 인터넷 + ``DART_API_KEY``/``DART_API_KEYS`` + httpx.

    AIContext:
        내부 HTTP client — AI 직접 호출 X. 키 평문 노출 X.

    LLM Specifications:
        AntiPatterns:
            - 매 요청 키 rotation X — sequential exhausted(§15 per-IP 차단 회피 핵심).
            - 단일 키로 대량 수집 X — DART_API_KEYS 다중 키.
            - status 020 미처리 X — 본 client 가 자동 cooldown.
        OutputSchema:
            - getBytes → bytes(zip 또는 status XML), getFilingsPage → dict(raw JSON).
        Prerequisites:
            - DART_API_KEY(S) + 네트워크.
        Freshness:
            - DART OpenAPI 실시간(분 단위).
        Dataflow:
            - 키풀 → httpx GET → DART API → bytes/JSON.
        TargetMarkets:
            - KR(DART OpenAPI).
    """

    def __init__(
        self,
        apiKey: str | None = None,
        apiKeys: list[str] | None = None,
        requestsPerMinute: int = _DEFAULT_RPM,
    ) -> None:
        keys = resolveDartKeys(apiKey=apiKey, apiKeys=apiKeys)
        if not keys:
            raise OriginalDartClientError(
                "DART API 키가 필요합니다. 환경변수 DART_API_KEYS(쉼표) 또는 DART_API_KEY, "
                "또는 프로젝트 .env 에 설정하세요. 발급: https://opendart.fss.or.kr"
            )
        self._slots: list[_KeySlot] = [_KeySlot(key=k) for k in keys]
        self._minInterval = 60.0 / requestsPerMinute
        self._poolLock = threading.Lock()
        self._session = httpx.Client(follow_redirects=True)

    @property
    def keyCount(self) -> int:
        """키풀 크기(설정된 DART 키 개수).

        Returns:
            int — 키 개수.

        Requires:
            - 초기화 시 resolve 된 키풀(``_slots``).

        Raises:
            없음.

        Example:
            >>> OriginalDartClient(apiKey="x").keyCount
            1
        """
        return len(self._slots)

    def _acquireSlot(self) -> tuple[_KeySlot, float]:
        """순차 키 소진 slot 예약 — 매 요청 동일 키(§15 per-IP 차단 회피).

        Args:
            없음.

        Returns:
            tuple[_KeySlot, float] — (예약된 slot, 호출자가 sleep 할 초).

        Raises:
            없음.

        Example:
            >>> slot, wait = OriginalDartClient(apiKey="x")._acquireSlot()  # doctest: +SKIP
        """
        now = time.monotonic()
        with self._poolLock:
            for s in self._slots:
                if s.coolDownUntil <= now:
                    startAt = max(now, s.nextAvailable)
                    s.nextAvailable = startAt + self._minInterval
                    s.inFlight += 1
                    return s, max(0.0, startAt - now)
            best = min(self._slots, key=lambda s: s.coolDownUntil)
            startAt = best.coolDownUntil
            best.nextAvailable = startAt + self._minInterval
            best.inFlight += 1
            return best, max(0.0, startAt - now)

    def _releaseSlot(self, slot: _KeySlot) -> None:
        """slot inFlight 카운트 감소.

        Args:
            slot: 반납할 slot.

        Returns:
            None.

        Raises:
            없음.

        Example:
            >>> c = OriginalDartClient(apiKey="x"); s, _ = c._acquireSlot(); c._releaseSlot(s)  # doctest: +SKIP
        """
        with self._poolLock:
            slot.inFlight = max(0, slot.inFlight - 1)

    def _markCoolDown(self, slot: _KeySlot) -> None:
        """status 020 발생 slot 을 60초 cooldown — 자동 다음 키 전환 유도.

        Args:
            slot: cooldown 처리할 slot.

        Returns:
            None.

        Raises:
            없음.

        Example:
            >>> c = OriginalDartClient(apiKey="x"); s, _ = c._acquireSlot(); c._markCoolDown(s)  # doctest: +SKIP
        """
        with self._poolLock:
            slot.coolDownUntil = time.monotonic() + _COOLDOWN_SEC

    def _allCoolingDown(self) -> bool:
        """모든 slot 이 cooldown 중인지.

        Returns:
            bool — 전 키 cooldown 여부.

        Raises:
            없음.

        Example:
            >>> OriginalDartClient(apiKey="x")._allCoolingDown()
            False
        """
        now = time.monotonic()
        with self._poolLock:
            return all(s.coolDownUntil > now for s in self._slots)

    def getBytes(self, endpoint: str, params: dict[str, Any] | None = None) -> bytes:
        """바이너리 endpoint 호출 — ``document.xml`` 원본 zip bytes.

        Capabilities:
            - 키풀 sequential-exhausted 로 binary endpoint 호출. status 020(JSON 에러
              응답) 감지 시 자동 cooldown 후 다음 키 재시도. 정상 응답은 bytes 그대로.

        Args:
            endpoint: DART endpoint(예: ``"document.xml"``).
            params: 요청 파라미터(예: ``{"rcept_no": "..."}``). crtfc_key 는 자동 주입.

        Returns:
            bytes — 정상 시 zip(``PK\\x03\\x04`` prefix) 또는 status XML(본문 부재 통지).
            zip 유효성/본문 부재 판정은 호출자(collect) 책임.

        Raises:
            OriginalDartClientError: 전 키 cooldown 소진(한도 초과).
            httpx.HTTPError: 네트워크/HTTP 오류.

        Example:
            >>> raw = OriginalDartClient(apiKey="x").getBytes("document.xml", {"rcept_no": "20240101000001"})  # doctest: +SKIP

        Guide:
            - 응답 첫 4바이트 ``PK\\x03\\x04`` 이면 zip, 아니면 status XML(013/014 등).

        SeeAlso:
            - ``archiveDartOriginals`` — 본 메서드로 zip 수집.

        Requires:
            - DART_API_KEY(S) + 네트워크.

        When:
            - 신규 rcept 의 원본 zip(document.xml 단건)이 필요할 때.

        How:
            - 키풀 slot 획득 → httpx GET document.xml → bytes 반환(호출자가 zip 판정).

        AIContext:
            내부 binary fetch — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - 응답을 무조건 zip 으로 가정 X — status XML(본문 부재) 분기 필수.
                - status 020 미처리 X — 본 메서드가 자동 cooldown.
            OutputSchema:
                - bytes.
            Prerequisites:
                - DART_API_KEY(S) + rcept_no.
            Freshness:
                - DART 실시간.
            Dataflow:
                - 키풀 → httpx GET document.xml → bytes.
            TargetMarkets:
                - KR(DART).
        """
        url = f"{_BASE_URL}/{endpoint}"
        attempts = 0
        maxAttempts = max(2 * len(self._slots), 4)
        while attempts < maxAttempts:
            slot, sleepFor = self._acquireSlot()
            if sleepFor > 0:
                time.sleep(sleepFor)
            try:
                merged = {"crtfc_key": slot.key}
                if params:
                    merged.update(params)
                resp = self._session.get(url, params=merged, timeout=60)
                resp.raise_for_status()
                contentType = resp.headers.get("Content-Type", "")
                if "json" in contentType:
                    data = resp.json()
                    status = data.get("status", "000")
                    if status == "020":
                        self._markCoolDown(slot)
                        attempts += 1
                        if self._allCoolingDown():
                            time.sleep(1.0)
                        continue
                return resp.content
            finally:
                self._releaseSlot(slot)
        raise OriginalDartClientError("요청 제한 초과 (모든 키 cooldown)")

    def getFilingsPage(
        self,
        *,
        bgnDe: str,
        endDe: str,
        pageNo: int = 1,
        pageCount: int = 100,
        corpCls: str | None = None,
    ) -> dict[str, Any]:
        """``list.json`` 공시 목록 한 페이지 호출 (날짜 범위).

        Capabilities:
            - 날짜 범위 전체 공시 목록을 페이지 단위 조회. corp 미지정 → 전 종목.
              status 020 자동 cooldown + 다음 키. status 013(결과 없음)은 빈 list.

        Args:
            bgnDe: 시작일 ``YYYYMMDD``.
            endDe: 종료일 ``YYYYMMDD``.
            pageNo: 페이지 번호(1-base).
            pageCount: 페이지당 행수(최대 100).
            corpCls: 법인구분 필터(``Y``/``K``/``N``/``E``). None 이면 전체.

        Returns:
            dict[str, Any] — raw JSON. 키: ``status`` · ``list``(행 list) · ``total_page`` ·
            ``page_no`` 등. 각 행: ``corp_cls`` · ``corp_name`` · ``corp_code`` ·
            ``stock_code`` · ``report_nm`` · ``rcept_no`` · ``rcept_dt`` · ``flr_nm``.

        Raises:
            OriginalDartClientError: 전 키 cooldown 소진 또는 API 키 오류(010/011 등).
            httpx.HTTPError: 네트워크/HTTP 오류.

        Example:
            >>> j = OriginalDartClient(apiKey="x").getFilingsPage(bgnDe="20260601", endDe="20260601")  # doctest: +SKIP
            >>> j["status"]  # doctest: +SKIP
            '000'

        Guide:
            - ``total_page`` 까지 ``pageNo`` 증가시켜 전수 수집. status 013 → 빈 list.

        SeeAlso:
            - ``archiveDartOriginals`` — 본 목록을 rcept 단위로 순회.

        Requires:
            - DART_API_KEY(S) + 네트워크.

        When:
            - 날짜 범위 공시 목록을 페이지 단위로 열거할 때.

        How:
            - 키풀 slot 획득 → httpx GET list.json → raw JSON(list/total_page) 반환.

        AIContext:
            내부 목록 조회 — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - 큰 날짜 범위 단일 호출 X — total_page 폭증. 일 단위 분할 권장.
                - status 013 을 에러로 처리 X — 휴일/결과 없음.
            OutputSchema:
                - dict(raw DART JSON).
            Prerequisites:
                - DART_API_KEY(S) + 날짜.
            Freshness:
                - DART 실시간(정정공시 반영).
            Dataflow:
                - 키풀 → httpx GET list.json → dict.
            TargetMarkets:
                - KR(DART).
        """
        params: dict[str, str] = {
            "bgn_de": bgnDe,
            "end_de": endDe,
            "page_no": str(pageNo),
            "page_count": str(pageCount),
        }
        if corpCls:
            params["corp_cls"] = corpCls

        url = f"{_BASE_URL}/list.json"
        attempts = 0
        maxAttempts = max(2 * len(self._slots), 4)
        while attempts < maxAttempts:
            slot, sleepFor = self._acquireSlot()
            if sleepFor > 0:
                time.sleep(sleepFor)
            try:
                merged = {"crtfc_key": slot.key}
                merged.update(params)
                resp = self._session.get(url, params=merged, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status", "000")
                if status in ("000", "013"):
                    return data
                if status == "020":
                    self._markCoolDown(slot)
                    attempts += 1
                    if self._allCoolingDown():
                        time.sleep(1.0)
                    continue
                raise OriginalDartClientError(f"[{status}] {data.get('message', 'DART list.json 오류')}")
            finally:
                self._releaseSlot(slot)
        raise OriginalDartClientError("요청 제한 초과 (모든 키 cooldown)")

    def close(self) -> None:
        """httpx 세션 종료(connection pool 정리).

        Returns:
            None.

        Raises:
            없음.

        Example:
            >>> OriginalDartClient(apiKey="x").close()
        """
        self._session.close()
