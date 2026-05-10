"""DataLoader 카테고리별 dispatch — Protocol DIP (정공법 B).

core/dataLoader.py 가 providers/edgar 직접 import 하던 분기를 registry 패턴으로
대체. core 는 LoaderProvider Protocol 만 알고, providers 가 module load 시점에
register. dartKey CredentialProvider 와 동일 패턴 (FastAPI startup tasks 와 동등).

작성 순서:
    1. providers/edgar/docs/loader.py 가 EdgarDocsLoader 클래스 + register 호출
    2. providers/edgar/bulk/__init__.py 가 EdgarBulkLoader 클래스 + register 호출
    3. dartlab.providers.edgar import 시 두 모듈 자동 로드 → registry 채워짐
    4. core/dataLoader.py 의 _ensureLocalParquet/loadData 가 dispatchLoader() 사용
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class LoaderProvider(Protocol):
    """카테고리별 parquet 보장 책임.

    구현 위치: providers/edgar/docs/loader.py 의 EdgarDocsLoader 등.
    """

    category: str  # 카테고리 식별자 (예: "edgarDocs", "edgar")

    def ensure(
        self,
        stockCode: str,
        path: Path,
        *,
        sinceYear: int | None = None,
        asOf: str | None = None,
        refresh: str | bool = "auto",
    ) -> None:
        """카테고리에 맞는 데이터 보장 (다운로드 또는 검증)."""
        ...


_LOADERS: dict[str, LoaderProvider] = {}

# Auto-discovery — providers 가 자동 등록될 모듈 path.
# core 는 providers 직접 import 0, plugin 패턴으로 위치만 식별.
_KNOWN_LOADER_MODULES: tuple[str, ...] = (
    "dartlab.providers.edgar.docs.loader",  # EdgarDocsLoader
    "dartlab.providers.edgar.bulk",  # EdgarBulkLoader
)

_DISCOVERED = False


def _discoverLoaders() -> None:
    """알려진 LoaderProvider 모듈을 한 번만 lazy import — register 트리거."""
    global _DISCOVERED
    if _DISCOVERED:
        return
    import importlib

    for modPath in _KNOWN_LOADER_MODULES:
        try:
            importlib.import_module(modPath)
        except ImportError:
            continue
    _DISCOVERED = True


def registerLoader(loader: LoaderProvider) -> None:
    """LoaderProvider 등록 — providers 가 import 시점에 호출."""
    _LOADERS[loader.category] = loader


def getLoader(category: str) -> LoaderProvider | None:
    """카테고리로 LoaderProvider 조회. 미등록이면 None. auto-discovery 트리거."""
    _discoverLoaders()
    return _LOADERS.get(category)


def listLoaders() -> dict[str, LoaderProvider]:
    """등록된 모든 LoaderProvider 반환 (dict 사본). auto-discovery 트리거."""
    _discoverLoaders()
    return dict(_LOADERS)
