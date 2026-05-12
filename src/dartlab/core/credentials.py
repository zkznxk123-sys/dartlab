"""환경/토큰/키 통합 조회 — CredentialManager.

Protocol + Registry 패턴 (정공법 B — DIP). core 는 ai/providers 직접 import 0:
- CredentialProvider Protocol 정의
- registerCredentialProvider() / listCredentialProviders() registry
- providers/dart, ai/providers 등 외부 모듈이 import 시점에 register
- CredentialManager 는 registry 만 iterate
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class CredentialStatus:
    """단일 자격 증명 상태."""

    name: str
    configured: bool
    source: str
    maskedValue: str | None = None


@dataclass(frozen=True)
class EnvironmentSnapshot:
    """전체 환경 스냅샷."""

    dataDir: str
    verbose: bool
    dartKey: CredentialStatus
    aiProviders: dict[str, CredentialStatus]
    aiDefaultProvider: str | None
    version: str


# ── Protocol DIP ──────────────────────────────────────────


@runtime_checkable
class CredentialProvider(Protocol):
    """단일 자격 증명 제공자 — Protocol DIP.

    구현 위치: providers/dart/openapi/dartKey.py 의 DartKeyProvider 등.
    각 provider 는 import 시점에 registerCredentialProvider() 로 등록.
    """

    name: str  # 자격 증명 식별자 (예: "dart_api_key")

    def check(self) -> CredentialStatus:
        """현재 자격 증명 상태 조회."""
        ...

    def save(self, value: str) -> None:
        """자격 증명 저장."""
        ...


_PROVIDERS: dict[str, CredentialProvider] = {}

# Auto-discovery — alpha 모듈 path list. CredentialManager 첫 사용 시 lazy load.
# core 가 providers 직접 import 하지 않고 plugin 패턴으로 위치를 식별만.
# 새 provider 추가 시 path 만 add (FastAPI startup tasks 와 동등 패턴).
_KNOWN_PROVIDER_MODULES: tuple[str, ...] = (
    "dartlab.providers.dart.openapi.dartKey",  # DartKeyProvider
)

_DISCOVERED = False


def _discoverProviders() -> None:
    """알려진 CredentialProvider 모듈을 한 번만 lazy import — register 트리거.

    PEP 562 lazy attribute 환경에서 dartlab 자체 import 가 providers 로드 안 함.
    이 함수가 첫 CredentialManager 사용 시 호출돼 plugin 모듈을 명시 로드.
    """
    global _DISCOVERED
    if _DISCOVERED:
        return
    import importlib

    for modPath in _KNOWN_PROVIDER_MODULES:
        try:
            importlib.import_module(modPath)
        except ImportError:
            continue  # optional dep 미설치 graceful
    _DISCOVERED = True


def registerCredentialProvider(provider: CredentialProvider) -> None:
    """CredentialProvider 등록 — providers 가 import 시점에 호출.

    같은 이름 재등록 시 덮어쓰기 (테스트 용이).
    """
    _PROVIDERS[provider.name] = provider


def listCredentialProviders() -> dict[str, CredentialProvider]:
    """등록된 모든 CredentialProvider 반환 (dict 사본). auto-discovery 트리거."""
    _discoverProviders()
    return dict(_PROVIDERS)


def getCredentialProvider(name: str) -> CredentialProvider | None:
    """이름으로 단일 provider 조회. 미등록이면 None. auto-discovery 트리거."""
    _discoverProviders()
    return _PROVIDERS.get(name)


# ── Manager ───────────────────────────────────────────────


class CredentialManager:
    """환경/토큰/키 통합 관리자 — Protocol Registry 기반.

    core 는 providers 직접 import 0. providers 가 module load 시점에
    registerCredentialProvider() 호출.
    """

    def snapshot(self) -> EnvironmentSnapshot:
        """현재 전체 환경 상태를 스냅샷으로 반환."""
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as _pkgVersion

        from dartlab import config

        try:
            __version__ = _pkgVersion("dartlab")
        except PackageNotFoundError:
            __version__ = "unknown"

        dartStatus = self.getCredential("dart_api_key")
        aiStatuses = self._checkAiProviders()
        defaultProvider = self._getDefaultProvider()

        return EnvironmentSnapshot(
            dataDir=config.dataDir,
            verbose=config.verbose,
            dartKey=dartStatus,
            aiProviders=aiStatuses,
            aiDefaultProvider=defaultProvider,
            version=__version__,
        )

    def getCredential(self, name: str) -> CredentialStatus:
        """특정 자격 증명 상태 조회 — registry 우선, fallback ai providers."""
        provider = getCredentialProvider(name)
        if provider is not None:
            return provider.check()
        # AI provider 는 별도 로직 (auth_kind=api_key|oauth) 유지
        if name.endswith("_api_key") or name.endswith("_oauth"):
            aiStatuses = self._checkAiProviders()
            return aiStatuses.get(name, CredentialStatus(name=name, configured=False, source="none"))
        return CredentialStatus(name=name, configured=False, source="none")

    def saveKey(self, name: str, value: str) -> None:
        """키 저장 — registry 우선, AI provider 는 SecretStore 직접."""
        provider = getCredentialProvider(name)
        if provider is not None:
            provider.save(value)
            return
        from dartlab.reference.providers import apiKeySecretName, getSecretStore, normalizeProvider

        rawProvider = name.replace("_api_key", "")
        normalized = normalizeProvider(rawProvider) or rawProvider
        getSecretStore().set(apiKeySecretName(normalized), value)

    def _checkAiProviders(self) -> dict[str, CredentialStatus]:
        """AI provider 자격 (api_key + oauth) 일괄 검사 — core/providers registry."""
        results: dict[str, CredentialStatus] = {}
        try:
            import os

            from dartlab.reference.providers import (
                _PROVIDERS as _AI_PROVIDERS,
            )
            from dartlab.reference.providers import (
                apiKeySecretName,
                getSecretStore,
                oauthSecretName,
            )

            store = getSecretStore()
            for pid, spec in _AI_PROVIDERS.items():
                if spec.auth_kind == "api_key" and spec.env_key:
                    envVal = os.environ.get(spec.env_key)
                    secretVal = store.get(apiKeySecretName(pid))
                    configured = bool(envVal or secretVal)
                    source = "env" if envVal else ("secret_store" if secretVal else "none")
                    val = envVal or secretVal
                    masked = (val[:4] + "..." + val[-4:]) if val and len(val) > 8 else None
                    results[pid] = CredentialStatus(
                        name=f"{pid}_api_key",
                        configured=configured,
                        source=source,
                        maskedValue=masked if configured else None,
                    )
                elif spec.auth_kind == "oauth":
                    configured = store.has(oauthSecretName(pid))
                    results[pid] = CredentialStatus(
                        name=f"{pid}_oauth",
                        configured=configured,
                        source="oauth" if configured else "none",
                    )
        except ImportError:
            pass
        return results

    def _getDefaultProvider(self) -> str | None:
        """ai_profile.json 의 defaultProvider 만 직접 조회 (core/providers thin 헬퍼)."""
        try:
            from dartlab.reference.providers import getDefaultProvider

            return getDefaultProvider()
        except ImportError:
            return None
