"""DART 시장 설정 — marketNs, HF repo, data/dart/* 레이아웃 SSOT.

LLM Specifications:
    AntiPatterns:
        - 경로 문자열 하드코딩 분산 금지 — 본 모듈 단일 SSOT.
    OutputSchema:
        - 경로 헬퍼 (financePath/reportPath/sectionsDir/hfUrl).
    Prerequisites:
        - dartlab.config(dataDir).
    TargetMarkets:
        - KR (DART).
"""

from __future__ import annotations

from pathlib import Path

import dartlab.config as _cfg

MARKET_NS = "kr"
HF_REPO = "eddmpython/dartlab-data"
HF_BASE_URL = "https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main"
_BASE = "dart"  # data/dart/*


def _root() -> Path:
    return Path(_cfg.dataDir) / _BASE


def financePath(code: str) -> Path:
    """data/dart/finance/{code}.parquet (DART OpenAPI XBRL 원본)."""
    return _root() / "finance" / f"{code}.parquet"


def reportPath(code: str) -> Path:
    """data/dart/report/{code}.parquet (DART OpenAPI 정기보고서)."""
    return _root() / "report" / f"{code}.parquet"


def sectionsDir(code: str) -> Path:
    """data/dart/sections/{code}/ (period-sharded sections artifact)."""
    return _root() / "sections" / code


def hfUrl(category: str, code: str) -> str:
    """HF single-file resolve URL — category ∈ {finance, report}."""
    return f"{HF_BASE_URL}/{_BASE}/{category}/{code}.parquet"
