"""DART OpenAPI 키 resolve — gather 자체포함(core/providers 미의존).

「공시 오리지널 수집」 모듈이 ``gather ↛ providers`` 규칙을 지키며 자체포함되도록,
DART 키 해석을 모듈 안에서 직접 한다. 우선순위는 providers 의 ``resolveDartKeys``
(``providers/dart/openapi/dartKey.py``)와 동일 계약:

    인자 → OS env(DART_API_KEYS 쉼표 / DART_API_KEY 단일) → 프로젝트 .env

복수 키(키풀)는 ``OriginalDartClient`` 의 sequential-exhausted 로테이션 입력.
"""

from __future__ import annotations

import os
from pathlib import Path


def _findEnvPath(startPath: Path | None = None) -> Path:
    """프로젝트 루트 ``.env`` 경로 추정 (cwd → 부모).

    Args:
        startPath: 탐색 시작 경로. None 이면 ``Path.cwd()``.

    Returns:
        Path — 발견된 ``.env`` 또는 startPath 기준 ``.env``(미발견 시).

    Raises:
        없음.

    Example:
        >>> _findEnvPath().name
        '.env'
    """
    start = startPath or Path.cwd()
    for current in (start, *start.parents):
        candidate = current / ".env"
        if candidate.exists():
            return candidate
    return start / ".env"


def _loadDotenvKeys(startPath: Path | None = None) -> list[str]:
    """프로젝트 ``.env`` 의 DART_API_KEY(S) 파싱 (복수 우선).

    Args:
        startPath: 탐색 시작 경로.

    Returns:
        list[str] — ``.env`` 의 키 목록. 없으면 빈 list.

    Raises:
        없음 — 파일 read 실패는 빈 list 로 흡수.

    Example:
        >>> isinstance(_loadDotenvKeys(), list)
        True
    """
    envPath = _findEnvPath(startPath)
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
        name, _, value = line.partition("=")
        name = name.strip()
        value = value.strip().strip("'\"")
        if name == "DART_API_KEYS" and value:
            multiKeys = [item.strip() for item in value.split(",") if item.strip()]
        elif name == "DART_API_KEY" and value and not singleKey:
            singleKey = value
    return multiKeys if multiKeys else ([singleKey] if singleKey else [])


def resolveDartKeys(
    apiKey: str | None = None,
    apiKeys: list[str] | None = None,
    *,
    startPath: Path | None = None,
) -> list[str]:
    """DART OpenAPI 키 목록 해석 — 인자 → OS env → 프로젝트 .env.

    Capabilities:
        - 단일/복수 키를 인자·환경변수·.env 3 소스에서 해석 + 가장 많은 키를 가진
          소스 채택(키풀 극대화). providers ``dartKey.resolveDartKeys`` 와 동일 계약을
          모듈 내부에 자체포함.

    Args:
        apiKey: 단일 키 직접 전달(최우선 단일).
        apiKeys: 복수 키 직접 전달(최우선). apiKey 보다 우선.
        startPath: ``.env`` 탐색 시작 경로. None 이면 cwd.

    Returns:
        list[str] — 정규화된 키 목록(공백 제거). 미설정이면 빈 list.

    Raises:
        없음 — 미설정은 빈 list 로 표현(호출자가 안내 분기).

    Example:
        >>> import os
        >>> os.environ["DART_API_KEY"] = "abc"
        >>> resolveDartKeys()
        ['abc']

    Guide:
        - 키 부재(빈 list)면 ``OriginalDartClient`` 가 ValueError 로 안내. 호출 전
          ``if not resolveDartKeys(): ...`` 로 사전 분기 가능.

    SeeAlso:
        - ``OriginalDartClient`` — 본 키 목록을 키풀로 사용.
        - ``providers.dart.openapi.dartKey.resolveDartKeys`` — 동일 계약 원본(import 안 함).

    Requires:
        - 환경변수 ``DART_API_KEYS``/``DART_API_KEY`` 또는 프로젝트 ``.env``.

    When:
        - DART 원본 수집(``archiveDartOriginals``) 시작 시 키풀 구성 입력으로.

    How:
        - 인자/env/.env 중 키가 가장 많은 소스를 골라 ``OriginalDartClient`` 키풀로 전달.

    AIContext:
        내부 키 해석 — AI 가 키 평문을 답변에 노출하지 않는다(개수/소스만 인용).

    LLM Specifications:
        AntiPatterns:
            - 키 평문 로그/답변 노출 X.
            - 단일 키 가정 X — DART_API_KEYS(복수) 가 per-IP 한도 분산의 핵심.
        OutputSchema:
            - list[str](키 0개 이상).
        Prerequisites:
            - env 또는 .env 접근 권한.
        Freshness:
            - 정적(프로세스 env/.env 시점).
        Dataflow:
            - 인자/env/.env → 본 함수 → ``OriginalDartClient`` 키풀.
        TargetMarkets:
            - KR(DART OpenAPI) 인증.
    """
    if apiKeys:
        return [item.strip() for item in apiKeys if item and item.strip()]
    if apiKey and apiKey.strip():
        return [apiKey.strip()]

    envMulti = os.environ.get("DART_API_KEYS", "")
    osMulti = [item.strip() for item in envMulti.split(",") if item.strip()] if envMulti else []

    envSingle = os.environ.get("DART_API_KEY", "")
    osSingle = [envSingle.strip()] if envSingle and envSingle.strip() else []

    dotenvKeys = _loadDotenvKeys(startPath)

    best = max([osMulti, dotenvKeys, osSingle], key=len)
    return best if best else []
