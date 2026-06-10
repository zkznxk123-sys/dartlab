"""gather 데이터 공급자 자격증명 진입점 — env·토큰 관리·안내 단일 facade.

SSOT 본체는 `core/providers/dataCredentials.py` (L0, cross-cutting). 본 모듈은
gather 사용자가 한 곳에서 키를 해석·설정·점검하도록 thin re-export + doctor CLI.

세팅 (둘 중 하나):
    1. .env 에 `DATA_GO_KR_KEY=...` (템플릿: `dartlab.gather.writeEnvExample()`).
    2. `dartlab.gather.setCredential("dataGoKr", "<키>")` — 암호화 저장, .env 불필요.

점검:
    >>> from dartlab import gather
    >>> print(gather.formatStatus())          # 사람용 상태표
    >>> gather.credentialStatus()             # 구조화 상태 리스트

소스 구현 측:
    >>> from dartlab.gather.credentials import resolveKey
    >>> key = resolveKey("dataGoKr", apiKey)  # 명시 → env → SecretStore → 안내에러
"""

from __future__ import annotations

from pathlib import Path

from dartlab.core.providers.dataCredentials import (
    CredentialError,
    CredentialStatus,
    DataProviderSpec,
    allSpecs,
    credentialStatus,
    envTemplate,
    formatStatus,
    getKey,
    getSpec,
    isConfigured,
    missingKeyMessage,
    resolveKey,
    setCredential,
)


def writeEnvExample(path: str | Path = ".env.example") -> Path:
    """레지스트리 기반 `.env.example` 파일 생성/갱신.

    Args:
        path: 출력 경로. 기본 repo 루트 ``.env.example``.

    Returns:
        Path — 작성된 파일 경로.

    Raises:
        OSError: 파일 쓰기 실패.

    Example:
        >>> writeEnvExample("/tmp/.env.example")  # doctest: +SKIP
    """
    out = Path(path)
    out.write_text(envTemplate(), encoding="utf-8")
    return out


def _main() -> int:
    """`python -m dartlab.gather.credentials` — 자격증명 상태 doctor."""
    print(formatStatus())
    return 0


__all__ = [
    "CredentialError",
    "CredentialStatus",
    "DataProviderSpec",
    "allSpecs",
    "credentialStatus",
    "envTemplate",
    "formatStatus",
    "getKey",
    "getSpec",
    "isConfigured",
    "missingKeyMessage",
    "resolveKey",
    "setCredential",
    "writeEnvExample",
]


if __name__ == "__main__":
    raise SystemExit(_main())
