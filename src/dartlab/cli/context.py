"""Shared CLI constants and metadata."""

from __future__ import annotations

from dataclasses import dataclass

from dartlab.ai.settings import cliProviderChoices, providerChoices

PROVIDERS = providerChoices()
CLI_PROVIDERS = cliProviderChoices()

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_RUNTIME = 1
EXIT_INTERRUPTED = 130
DEPRECATED_ALIASES: dict[str, str] = {}


@dataclass(frozen=True)
class CommandSpec:
    """CLI 서브커맨드 메타데이터."""

    name: str
    import_path: str
    description: str = ""
