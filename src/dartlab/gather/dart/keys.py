"""DART OpenAPI 키 상태/저장/검증 공용 헬퍼."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DartKeyStatus:
    """DART API 키 설정 상태를 담는 불변 데이터 클래스."""

    configured: bool
    source: str
    keyCount: int
    envPath: str
    writable: bool

    def toDict(self) -> dict[str, Any]:
        """키 상태를 딕셔너리로 변환한다.

        Args:
            (인자 자동 생성).

        Raises:
            없음.

        Example:
            >>> toDict(...)

        Returns:
            dict[str, Any] — 상태 dict.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 평문 노출 X — 환경변수 또는 .env 파일 사용.
                - 키 여러 개 (로테이션) 시 keyCount > 1 — 단일 키 가정 X.
            OutputSchema:
                - dict / str / Path / bool / DartKeyStatus — 함수별.
            Prerequisites:
                - DART_API_KEY 환경변수 또는 .env 파일.
            Freshness:
                - 키 설정 시점 (정적).
            Dataflow:
                - env / .env → 본 헬퍼 → DartClient.
            TargetMarkets:
                - KR (DART) — API 키 관리.
        """
        return {
            "configured": self.configured,
            "source": self.source,
            "keyCount": self.keyCount,
            "envPath": self.envPath,
            "writable": self.writable,
        }


def findProjectEnvPath(startPath: Path | None = None) -> Path:
    """프로젝트 루트 .env 경로를 추정한다.

    Args:
        startPath: 인자.

    Raises:
        없음.

    Example:
        >>> findProjectEnvPath(...)

    Returns:
        Path — .env 파일 경로.

    SeeAlso:
        - ``DartKeyStatus`` / ``DartClient`` — 본 키 사용 처.

    Requires:
        - datetime

    Capabilities:
        - DART_API_KEY 환경 탐지 + 상태 dataclass 또는 키 list 반환. .env 또는 환경변수 우선순위.

    Guide:
        - "DART 키 상태 확인" → 본 모듈 함수.

    AIContext:
        internal key helper — AI 가 직접 호출 X. 운영자 setup.

    LLM Specifications:
        AntiPatterns:
            - DART_API_KEY 평문 노출 X.
            - 단일 키 가정 X — DART_API_KEYS (복수) 도 지원.
        OutputSchema:
            - list[str] / Path / bool / DartKeyStatus — 함수별.
        Prerequisites:
            - DART_API_KEY 또는 DART_API_KEYS 환경변수, 또는 .env 파일.
        Freshness:
            - 키 설정 시점 (정적).
        Dataflow:
            - env / .env → 본 헬퍼 → DartClient.
        TargetMarkets:
            - KR (DART) — API 키 관리.
    """
    start = startPath or Path.cwd()
    for current in (start, *start.parents):
        candidate = current / ".env"
        if candidate.exists():
            return candidate
    return start / ".env"


def loadDotenvDartKeys(startPath: Path | None = None) -> list[str]:
    """프로젝트 .env의 DART_API_KEY(S)를 읽는다.

    Args:
        startPath: 인자.

    Raises:
        없음.

    Example:
        >>> loadDotenvDartKeys(...)

    Returns:
        list[str] — DART API 키 목록.

    SeeAlso:
        - ``DartKeyStatus`` / ``DartClient`` — 본 키 사용 처.

    Requires:
        - datetime

    Capabilities:
        - DART_API_KEY 환경 탐지 + 상태 dataclass 또는 키 list 반환. .env 또는 환경변수 우선순위.

    Guide:
        - "DART 키 상태 확인" → 본 모듈 함수.

    AIContext:
        internal key helper — AI 가 직접 호출 X. 운영자 setup.

    LLM Specifications:
        AntiPatterns:
            - DART_API_KEY 평문 노출 X.
            - 단일 키 가정 X — DART_API_KEYS (복수) 도 지원.
        OutputSchema:
            - list[str] / Path / bool / DartKeyStatus — 함수별.
        Prerequisites:
            - DART_API_KEY 또는 DART_API_KEYS 환경변수, 또는 .env 파일.
        Freshness:
            - 키 설정 시점 (정적).
        Dataflow:
            - env / .env → 본 헬퍼 → DartClient.
        TargetMarkets:
            - KR (DART) — API 키 관리.
    """
    envPath = findProjectEnvPath(startPath)
    if not envPath.exists():
        return []

    try:
        text = envPath.read_text(encoding="utf-8")
    except OSError:
        return []

    multiKeys: list[str] = []
    singleKey = ""
    for rawLine in text.splitlines():
        line = rawLine.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        normalizedKey = key.strip()
        normalizedValue = value.strip().strip("'\"")
        if normalizedKey == "DART_API_KEYS" and normalizedValue:
            multiKeys = [item.strip() for item in normalizedValue.split(",") if item.strip()]
        elif normalizedKey == "DART_API_KEY" and normalizedValue and not singleKey:
            singleKey = normalizedValue
    # 복수키 우선
    return multiKeys if multiKeys else ([singleKey] if singleKey else [])


def resolveDartKeys(
    apiKey: str | None = None,
    apiKeys: list[str] | None = None,
    *,
    startPath: Path | None = None,
) -> list[str]:
    """DART 키 우선순위: 인자 -> OS env -> 프로젝트 .env.

    Args:
        apiKey: 인자.
        apiKeys: 인자.
        startPath: 인자.

    Raises:
        없음.

    Example:
        >>> resolveDartKeys(...)

    Returns:
        list[str] — DART API 키 목록.

    SeeAlso:
        - ``DartKeyStatus`` / ``DartClient`` — 본 키 사용 처.

    Requires:
        - datetime

    Capabilities:
        - DART_API_KEY 환경 탐지 + 상태 dataclass 또는 키 list 반환. .env 또는 환경변수 우선순위.

    Guide:
        - "DART 키 상태 확인" → 본 모듈 함수.

    AIContext:
        internal key helper — AI 가 직접 호출 X. 운영자 setup.

    LLM Specifications:
        AntiPatterns:
            - DART_API_KEY 평문 노출 X.
            - 단일 키 가정 X — DART_API_KEYS (복수) 도 지원.
        OutputSchema:
            - list[str] / Path / bool / DartKeyStatus — 함수별.
        Prerequisites:
            - DART_API_KEY 또는 DART_API_KEYS 환경변수, 또는 .env 파일.
        Freshness:
            - 키 설정 시점 (정적).
        Dataflow:
            - env / .env → 본 헬퍼 → DartClient.
        TargetMarkets:
            - KR (DART) — API 키 관리.
    """
    if apiKeys:
        return [item.strip() for item in apiKeys if item and item.strip()]
    if apiKey and apiKey.strip():
        return [apiKey.strip()]

    # OS env + .env 모두 확인해서 키가 더 많은 쪽 채택
    envKeys = os.environ.get("DART_API_KEYS", "")
    osKeysList = [item.strip() for item in envKeys.split(",") if item.strip()] if envKeys else []

    envKey = os.environ.get("DART_API_KEY", "")
    osSingleKey = [envKey.strip()] if envKey and envKey.strip() else []

    dotenvKeys = loadDotenvDartKeys(startPath)

    # 가장 많은 키를 가진 소스 반환
    candidates = [osKeysList, dotenvKeys, osSingleKey]
    best = max(candidates, key=len)
    return best if best else []


def hasDartApiKey(startPath: Path | None = None) -> bool:
    """DART API 키가 하나라도 설정되어 있는지 확인한다.

    Args:
        startPath: 인자.

    Raises:
        없음.

    Example:
        >>> hasDartApiKey(...)

    Returns:
        bool — 성공 여부.

    LLM Specifications:
        AntiPatterns:
            - DART_API_KEY 평문 노출 X.
            - 키 검증 실패 시 None 반환 — caller 분기.
        OutputSchema:
            - bool / list[str] / DartKeyStatus — 함수별.
        Prerequisites:
            - env / .env 파일 접근.
        Freshness:
            - 키 설정 시점 (정적).
        Dataflow:
            - env / .env → 본 헬퍼 → 사용자/DartClient.
        TargetMarkets:
            - KR (DART) — API 키 setup.
    """
    return bool(resolveDartKeys(startPath=startPath))


def getDartKeyStatus(startPath: Path | None = None) -> DartKeyStatus:
    """현재 DART API 키 설정 상태를 조회한다.

    Args:
        startPath: 인자.

    Raises:
        없음.

    Example:
        >>> getDartKeyStatus(...)

    Returns:
        DartKeyStatus — 키 상태 dataclass.

    SeeAlso:
        - ``DartKeyStatus`` / ``DartClient`` — 본 키 사용 처.

    Requires:
        - datetime

    Capabilities:
        - DART_API_KEY 환경 탐지 + 상태 dataclass 또는 키 list 반환. .env 또는 환경변수 우선순위.

    Guide:
        - "DART 키 상태 확인" → 본 모듈 함수.

    AIContext:
        internal key helper — AI 가 직접 호출 X. 운영자 setup.

    LLM Specifications:
        AntiPatterns:
            - DART_API_KEY 평문 노출 X.
            - 단일 키 가정 X — DART_API_KEYS (복수) 도 지원.
        OutputSchema:
            - list[str] / Path / bool / DartKeyStatus — 함수별.
        Prerequisites:
            - DART_API_KEY 또는 DART_API_KEYS 환경변수, 또는 .env 파일.
        Freshness:
            - 키 설정 시점 (정적).
        Dataflow:
            - env / .env → 본 헬퍼 → DartClient.
        TargetMarkets:
            - KR (DART) — API 키 관리.
    """
    envPath = findProjectEnvPath(startPath)
    envKeys = os.environ.get("DART_API_KEYS", "")
    envKey = os.environ.get("DART_API_KEY", "")
    dotenvKeys = loadDotenvDartKeys(startPath)

    if envKeys:
        keyCount = len([item for item in envKeys.split(",") if item.strip()])
        source = "env"
    elif envKey:
        keyCount = 1
        source = "env"
    elif dotenvKeys:
        keyCount = len(dotenvKeys)
        source = "dotenv"
    else:
        keyCount = 0
        source = "none"

    writableTarget = envPath if envPath.exists() else envPath.parent
    return DartKeyStatus(
        configured=keyCount > 0,
        source=source,
        keyCount=keyCount,
        envPath=str(envPath),
        writable=os.access(writableTarget, os.W_OK),
    )


def saveDartKeyToDotenv(key: str, startPath: Path | None = None) -> Path:
    """프로젝트 .env의 DART_API_KEY를 추가 또는 갱신한다.

    Args:
        key: 인자.
        startPath: 인자.

    Raises:
        없음.

    Example:
        >>> saveDartKeyToDotenv(...)

    Returns:
        Path — .env 파일 경로.

    SeeAlso:
        - ``DartKeyStatus`` / ``DartClient`` — 본 키 사용 처.

    Requires:
        - datetime

    Capabilities:
        - DART_API_KEY 환경 탐지 + 상태 dataclass 또는 키 list 반환. .env 또는 환경변수 우선순위.

    Guide:
        - "DART 키 상태 확인" → 본 모듈 함수.

    AIContext:
        internal key helper — AI 가 직접 호출 X. 운영자 setup.

    LLM Specifications:
        AntiPatterns:
            - DART_API_KEY 평문 노출 X.
            - 단일 키 가정 X — DART_API_KEYS (복수) 도 지원.
        OutputSchema:
            - list[str] / Path / bool / DartKeyStatus — 함수별.
        Prerequisites:
            - DART_API_KEY 또는 DART_API_KEYS 환경변수, 또는 .env 파일.
        Freshness:
            - 키 설정 시점 (정적).
        Dataflow:
            - env / .env → 본 헬퍼 → DartClient.
        TargetMarkets:
            - KR (DART) — API 키 관리.
    """
    envPath = findProjectEnvPath(startPath)
    lines: list[str] = []
    replaced = False

    if envPath.exists():
        text = envPath.read_text(encoding="utf-8")
        for rawLine in text.splitlines():
            stripped = rawLine.strip()
            if stripped.startswith("DART_API_KEY=") or stripped.startswith("DART_API_KEYS="):
                if not replaced:
                    lines.append(f"DART_API_KEY={key}")
                    replaced = True
                continue
            lines.append(rawLine)

    if not replaced:
        lines.append(f"DART_API_KEY={key}")

    envPath.parent.mkdir(parents=True, exist_ok=True)
    envPath.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return envPath


def clearDartKeyFromDotenv(startPath: Path | None = None) -> Path:
    """프로젝트 .env에서 DART_API_KEY(S)를 제거한다.

    Args:
        startPath: 인자.

    Raises:
        없음.

    Example:
        >>> clearDartKeyFromDotenv(...)

    Returns:
        Path — .env 파일 경로.

    SeeAlso:
        - ``DartKeyStatus`` / ``DartClient`` — 본 키 사용 처.

    Requires:
        - datetime

    Capabilities:
        - DART_API_KEY 환경 탐지 + 상태 dataclass 또는 키 list 반환. .env 또는 환경변수 우선순위.

    Guide:
        - "DART 키 상태 확인" → 본 모듈 함수.

    AIContext:
        internal key helper — AI 가 직접 호출 X. 운영자 setup.

    LLM Specifications:
        AntiPatterns:
            - DART_API_KEY 평문 노출 X.
            - 단일 키 가정 X — DART_API_KEYS (복수) 도 지원.
        OutputSchema:
            - list[str] / Path / bool / DartKeyStatus — 함수별.
        Prerequisites:
            - DART_API_KEY 또는 DART_API_KEYS 환경변수, 또는 .env 파일.
        Freshness:
            - 키 설정 시점 (정적).
        Dataflow:
            - env / .env → 본 헬퍼 → DartClient.
        TargetMarkets:
            - KR (DART) — API 키 관리.
    """
    envPath = findProjectEnvPath(startPath)
    if not envPath.exists():
        return envPath

    text = envPath.read_text(encoding="utf-8")
    keptLines = [
        rawLine
        for rawLine in text.splitlines()
        if not rawLine.strip().startswith("DART_API_KEY=") and not rawLine.strip().startswith("DART_API_KEYS=")
    ]
    newText = "\n".join(keptLines).rstrip()
    envPath.write_text((newText + "\n") if newText else "", encoding="utf-8")
    return envPath


def validateDartApiKey(key: str) -> dict[str, Any]:
    """키 유효성만 빠르게 점검한다.

    Args:
        key: 인자.

    Raises:
        없음.

    Example:
        >>> validateDartApiKey(...)

    Returns:
        dict[str, Any] — 상태 dict.

    SeeAlso:
        - ``DartKeyStatus`` / ``DartClient`` — 본 키 사용 처.

    Requires:
        - datetime

    Capabilities:
        - DART_API_KEY 환경 탐지 + 상태 dataclass 또는 키 list 반환. .env 또는 환경변수 우선순위.

    Guide:
        - "DART 키 상태 확인" → 본 모듈 함수.

    AIContext:
        internal key helper — AI 가 직접 호출 X. 운영자 setup.

    LLM Specifications:
        AntiPatterns:
            - DART_API_KEY 평문 노출 X.
            - 단일 키 가정 X — DART_API_KEYS (복수) 도 지원.
        OutputSchema:
            - list[str] / Path / bool / DartKeyStatus — 함수별.
        Prerequisites:
            - DART_API_KEY 또는 DART_API_KEYS 환경변수, 또는 .env 파일.
        Freshness:
            - 키 설정 시점 (정적).
        Dataflow:
            - env / .env → 본 헬퍼 → DartClient.
        TargetMarkets:
            - KR (DART) — API 키 관리.
    """
    from dartlab.gather.dart.client import DartClient

    today = datetime.now().strftime("%Y%m%d")
    client = DartClient(apiKey=key)
    client.getJson(
        "list.json",
        {
            "bgn_de": today,
            "end_de": today,
            "page_no": "1",
            "page_count": "1",
        },
        emptyOn013=True,
    )
    return {"ok": True}


# ── CredentialProvider 구현 + register (정공법 B — DIP) ─────────────


class DartKeyProvider:
    """DART API key 의 CredentialProvider 구현 — core 가 직접 import 안 하고 registry 로 접근.

    module load 시점에 registerCredentialProvider() 호출됨 (파일 끝).
    core/credentials.py 의 CredentialManager 가 registry iterate 로 사용.
    """

    name = "dart_api_key"

    def check(self):
        """DART API 키 상태 → CredentialStatus.

        Raises:
            없음.

        Example:
            >>> check(...)

        SeeAlso:
            - ``DartKeyStatus`` / ``DartClient`` — 본 키 사용 처.

        Requires:
            - datetime

        Capabilities:
            - DART 키 setup/검증/저장 헬퍼. 운영자 도구.

        Guide:
            - "DART 키 등록 / 검증" → 본 메서드.

        AIContext:
            internal key helper — AI 직접 호출 X.
        """
        from dartlab.core.credentials import CredentialStatus

        try:
            status = getDartKeyStatus()
        except (OSError, ValueError, KeyError):
            # 환경변수/파일 읽기 실패 또는 형식 오류 — 미설정으로 응답.
            return CredentialStatus(name=self.name, configured=False, source="none")

        masked: str | None = None
        if status.configured:
            try:
                keys = resolveDartKeys()
                if keys:
                    k = keys[0]
                    masked = k[:4] + "..." + k[-4:] if len(k) > 8 else "***"
            except (TypeError, ValueError):
                pass

        return CredentialStatus(
            name=self.name,
            configured=status.configured,
            source=status.source,
            maskedValue=masked,
        )

    def save(self, value: str) -> None:
        """프로젝트 .env 에 DART_API_KEY 저장.

        Args:
            value: 인자.

        Raises:
            없음.

        Example:
            >>> save(...)

        SeeAlso:
            - ``DartKeyStatus`` / ``DartClient`` — 본 키 사용 처.

        Requires:
            - datetime

        Capabilities:
            - DART 키 setup/검증/저장 헬퍼. 운영자 도구.

        Guide:
            - "DART 키 등록 / 검증" → 본 메서드.

        AIContext:
            internal key helper — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 평문 노출 X — 환경변수 또는 .env 파일 사용.
                - 키 여러 개 (로테이션) 시 keyCount > 1 — 단일 키 가정 X.
            OutputSchema:
                - dict / str / Path / bool / DartKeyStatus — 함수별.
            Prerequisites:
                - DART_API_KEY 환경변수 또는 .env 파일.
            Freshness:
                - 키 설정 시점 (정적).
            Dataflow:
                - env / .env → 본 헬퍼 → DartClient.
            TargetMarkets:
                - KR (DART) — API 키 관리.
        """
        saveDartKeyToDotenv(value)


def _registerDartKeyProvider() -> None:
    """import 시점 등록 — circular import 회피 위해 함수 내부 lazy import."""
    from dartlab.core.credentials import registerCredentialProvider

    registerCredentialProvider(DartKeyProvider())


_registerDartKeyProvider()
