"""providers/dart/docs/sections/loader.py — DartDocsLoader (docs↔sections 합성) 단위.

core/dataLoader 에서 이관된 도메인 read 로더. 실 네트워크 0 — sections 함수 monkeypatch
+ env 게이트로 등록·load·synthesizeToPath·builder-mode·빈 artifact 를 검증.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_registered_under_docs_category() -> None:
    """getLoader("docs") 가 DartDocsLoader 를 반환 (LoaderProvider DIP 등록)."""
    from dartlab.core.loaders import getLoader

    loader = getLoader("docs")
    assert loader is not None
    assert loader.__class__.__name__ == "DartDocsLoader"
    assert loader.category == "docs"
    assert hasattr(loader, "load") and hasattr(loader, "synthesizeToPath")


def test_report_type_expr_mapping() -> None:
    """_docsReportTypeExpr — period 분기 → 옛 docs.parquet report_type 문자열."""
    from dartlab.providers.dart.docs.sections.loader import _docsReportTypeExpr

    df = pl.DataFrame({"period": ["2024Q1", "2024Q2", "2024Q3", "2024Q4"]}).with_columns(_docsReportTypeExpr())
    got = df["report_type"].to_list()
    assert got == [
        "분기보고서 (2024.03)",
        "반기보고서 (2024.06)",
        "분기보고서 (2024.09)",
        "사업보고서 (2024.12)",
    ]


def test_load_empty_artifact_returns_empty(monkeypatch, tmp_path: Path) -> None:
    """artifact 부재 → load() 가 빈 DataFrame (네트워크 0)."""
    import dartlab.providers.dart.docs.sections.loader as mod

    monkeypatch.setattr(mod, "hasSectionsArtifact", lambda code: False)
    monkeypatch.setattr(mod, "_ensureFromHf", lambda code: False)
    monkeypatch.setattr(mod, "sectionsDir", lambda code: tmp_path / "nonexistent")

    out = mod.DartDocsLoader().load("005930")
    assert isinstance(out, pl.DataFrame)
    assert out.is_empty()


def test_synthesize_builder_mode_skips(monkeypatch, tmp_path: Path) -> None:
    """DARTLAB_BUILDER_MODE=1 → synthesizeToPath 재귀 회피 (False, 합성 skip)."""
    from dartlab.providers.dart.docs.sections.loader import DartDocsLoader

    monkeypatch.setenv("DARTLAB_BUILDER_MODE", "1")
    dest = tmp_path / "005930.parquet"
    assert DartDocsLoader().synthesizeToPath("005930", dest) is False
    assert not dest.exists()


def test_synthesize_missing_artifact_returns_false(monkeypatch, tmp_path: Path) -> None:
    """artifact 부재 + HF 미수신 → synthesizeToPath False (다운로드 fallback 은 core 책임)."""
    import dartlab.providers.dart.docs.sections.loader as mod

    monkeypatch.delenv("DARTLAB_BUILDER_MODE", raising=False)
    monkeypatch.setattr(mod, "hasSectionsArtifact", lambda code: False)
    monkeypatch.setattr(mod, "_ensureFromHf", lambda code: False)

    dest = tmp_path / "005930.parquet"
    assert mod.DartDocsLoader().synthesizeToPath("005930", dest) is False
    assert not dest.exists()
