"""환경/토큰/키 통합 조회 — CredentialManager."""

from __future__ import annotations

from dataclasses import dataclass


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


class CredentialManager:
    """환경/토큰/키 통합 관리자.

    기존 모듈을 래핑하여 단일 진입점 제공.
    쓰기 작업은 기존 모듈에 위임.
    """

    def snapshot(self) -> EnvironmentSnapshot:
        """현재 전체 환경 상태를 스냅샷으로 반환."""
        from dartlab import config

        try:
            from dartlab import __version__
        except ImportError:
            __version__ = "unknown"

        dartStatus = self._checkDartKey()
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
        """특정 자격 증명 상태 조회."""
        if name == "dart_api_key":
            return self._checkDartKey()
        aiStatuses = self._checkAiProviders()
        return aiStatuses.get(name, CredentialStatus(name=name, configured=False, source="none"))

    def saveKey(self, name: str, value: str) -> None:
        """키 저장 — dart key 는 .env, AI provider 는 SecretStore 직접 저장.

        이전: AiProfileManager.save_api_key 호출 (revision++ 부수효과 포함).
        현재: SecretStore 직접 — core 가 ai 의존 안 함 (단방향 import 정책).
        provider 카탈로그 변경은 별도 호출자가 ai/settings 통해 처리.
        """
        if name == "dart_api_key":
            from dartlab.providers.dart.openapi.dartKey import saveDartKeyToDotenv

            saveDartKeyToDotenv(value)
            return
        from dartlab.core.providers import apiKeySecretName, getSecretStore, normalizeProvider

        provider = name.replace("_api_key", "")
        normalized = normalizeProvider(provider) or provider
        getSecretStore().set(apiKeySecretName(normalized), value)

    def _checkDartKey(self) -> CredentialStatus:
        try:
            from dartlab.providers.dart.openapi.dartKey import getDartKeyStatus

            status = getDartKeyStatus()
            masked = None
            if status.configured:
                try:
                    from dartlab.providers.dart.openapi.dartKey import resolveDartKeys

                    keys = resolveDartKeys()
                    if keys:
                        k = keys[0]
                        masked = k[:4] + "..." + k[-4:] if len(k) > 8 else "***"
                except (ImportError, TypeError):
                    pass
            return CredentialStatus(
                name="dart_api_key",
                configured=status.configured,
                source=status.source,
                maskedValue=masked,
            )
        except ImportError:
            return CredentialStatus(name="dart_api_key", configured=False, source="none")

    def _checkAiProviders(self) -> dict[str, CredentialStatus]:
        results: dict[str, CredentialStatus] = {}
        try:
            import os

            from dartlab.core.providers import (
                _PROVIDERS,
                apiKeySecretName,
                getSecretStore,
                oauthSecretName,
            )

            store = getSecretStore()
            for pid, spec in _PROVIDERS.items():
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
            from dartlab.core.providers import getDefaultProvider

            return getDefaultProvider()
        except ImportError:
            return None
