"""SecretStore — 자격증명 저장 추상화 (T2-3).

dartlab 의 외부 자격증명 (DART API key / OpenAI / Anthropic / FRED 등) 을 표준
인터페이스로 저장/조회. 3 backend 지원 (env / keyring / file). 운영자가 환경에
맞춰 선택.

본 v1 은 **Protocol + EnvSecretStore 1 backend** 만 구현. keyring / file backend
는 후속 (T2-3 분기 작업).

Protocol 등록 패턴:
    >>> from dartlab.core.secrets import EnvSecretStore, registerSecretStore
    >>> registerSecretStore(EnvSecretStore())
    >>> from dartlab.core.secrets import getSecret
    >>> getSecret("DART_API_KEY")

CLAUDE.md `feedback_no_extras_install` 정합:
    base 의존성만 사용 (keyring backend 는 optional import — base 부담 없음).

후속 트랙 (T2-3):
    - KeyringSecretStore: `keyring` 라이브러리 wrapper (Windows credential manager)
    - FileSecretStore: encrypted JSON (`cryptography` 라이브러리, optional)
"""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable


@runtime_checkable
class SecretStore(Protocol):
    """자격증명 저장소 인터페이스 — DI Protocol (CLAUDE.md core/di 패턴).

    구현체:
        - EnvSecretStore: os.environ (기본)
        - KeyringSecretStore: keyring 라이브러리 (후속, optional)
        - FileSecretStore: encrypted JSON (후속, optional)
    """

    def get(self, key: str) -> str | None:
        """key 의 secret 값 — 없으면 None."""
        ...

    def set(self, key: str, value: str) -> None:
        """key = value 저장."""
        ...

    def delete(self, key: str) -> None:
        """key 삭제 — 없으면 idempotent."""
        ...

    def listKeys(self) -> list[str]:
        """저장된 key 목록."""
        ...


class EnvSecretStore:
    """os.environ 기반 SecretStore — 기본 backend.

    Example:
        >>> store = EnvSecretStore()
        >>> os.environ["TEST_KEY"] = "value"
        >>> store.get("TEST_KEY")
        'value'
        >>> store.get("MISSING_KEY") is None
        True
    """

    def get(self, key: str) -> str | None:
        """os.environ 에서 key 조회 — 없으면 None."""
        return os.environ.get(key)

    def set(self, key: str, value: str) -> None:
        """os.environ[key] = value (프로세스 한정, persistent 아님).

        영구 저장은 별도 backend (Keyring / File) 필요.
        """
        os.environ[key] = value

    def delete(self, key: str) -> None:
        """os.environ 에서 key 제거 — 없으면 idempotent."""
        os.environ.pop(key, None)

    def listKeys(self) -> list[str]:
        """현재 환경변수 key 목록 (전체)."""
        return list(os.environ.keys())


# ── 등록 패턴 ──


_currentStore: SecretStore = EnvSecretStore()


def registerSecretStore(store: SecretStore) -> None:
    """전역 SecretStore 교체 — DI 진입점 (T10-4).

    Capabilities:
        프로세스 한정 전역 SecretStore 인스턴스를 사용자 지정으로 교체. 테스트
        에서는 InMemoryStore, 프로덕션에서는 KeyringSecretStore 등으로 교체.

    Args:
        store: SecretStore Protocol 구현체.

    Returns:
        None.

    Example:
        >>> from dartlab.core.secrets import EnvSecretStore, registerSecretStore
        >>> registerSecretStore(EnvSecretStore())

    Guide:
        전역 상태 변경이라 테스트 시 fixture (scope=function) + 원복 강행.

    SeeAlso:
        getStore / getSecret / setSecret.

    Requires:
        store 가 SecretStore Protocol (get/set/delete/listKeys) 충족.

    AIContext:
        T2-3 보안 트랙. 프로덕션 OAuth 갱신 (T2-4) 의 backing store 교체.

    Raises:
        없음.
    """
    global _currentStore
    _currentStore = store


def getStore() -> SecretStore:
    """현재 등록된 SecretStore 반환 (T10-4).

    Returns:
        현재 활성 SecretStore (기본: EnvSecretStore).

    Example:
        >>> from dartlab.core.secrets import getStore
        >>> store = getStore()
        >>> store.get("DART_API_KEY")
    """
    return _currentStore


def getSecret(key: str) -> str | None:
    """등록된 store 에서 key 의 secret 값 조회 (T10-4).

    Args:
        key: 자격증명 식별자 (예: "DART_API_KEY", "OPENAI_API_KEY").

    Returns:
        secret 값 또는 None (없을 시).

    Example:
        >>> from dartlab.core.secrets import getSecret
        >>> apikey = getSecret("DART_API_KEY")
    """
    return _currentStore.get(key)


def setSecret(key: str, value: str) -> None:
    """등록된 store 에 key=value 저장 (T10-4).

    Args:
        key: 자격증명 식별자.
        value: secret 값.

    Guide:
        EnvSecretStore 사용 시 os.environ 변경 — 프로세스 한정. 영구 저장은
        KeyringSecretStore (후속) 또는 .env 파일 직접 수정.

    AIContext:
        T2-3 보안 트랙. setSecret 후 recordIssuance (T2-4) 호출 권장.
    """
    _currentStore.set(key, value)


__all__ = [
    "SecretStore",
    "EnvSecretStore",
    "registerSecretStore",
    "getStore",
    "getSecret",
    "setSecret",
]
