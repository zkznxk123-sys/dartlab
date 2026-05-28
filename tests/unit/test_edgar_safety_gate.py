"""EDGAR PR-E7 안전 게이트 인프라 가드 — plan delegated-prancing-tower PR-E7a.

본 PR-E7a 단독 검증:
- ``DATA_RELEASES["edgarDocs"]`` 의 ``deprecated=True`` + ``successor="edgarSections"`` 마킹
- ``tests/audit/sectionsParityEdgar.measureTicker`` 의 status 분기 (missing_old/missing_new)
- baseline ticker 5 종 (AAPL/MSFT/GOOGL/AMZN/NVDA) DEFAULT_TICKERS 상수

PR-E7b (실제 폐기) 는 본 measure 의 ``violations=0`` × 4 주 연속 + 운영자 명시 결정 후만 진행.
"""

from __future__ import annotations

from dartlab.core.dataConfig import DATA_RELEASES


def test_edgar_docs_marked_deprecated() -> None:
    """edgarDocs 카테고리에 deprecated 마킹 + successor 명시."""
    entry = DATA_RELEASES["edgarDocs"]
    assert entry.get("deprecated") is True
    assert entry.get("successor") == "edgarSections"
    # 옛 path 가 dual-write 동안 계속 read 가능해야 — public 유지.
    assert entry.get("public") is True


def test_edgar_sections_not_deprecated() -> None:
    """edgarSections 는 deprecated 마킹 X (successor 본체)."""
    entry = DATA_RELEASES["edgarSections"]
    assert not entry.get("deprecated", False)


def test_parity_module_imports() -> None:
    """sectionsParityEdgar audit 모듈 import 가능 + 진입점 존재."""
    import importlib.util
    from pathlib import Path

    auditPath = Path(__file__).resolve().parents[1] / "audit" / "sectionsParityEdgar.py"
    if not auditPath.exists():
        auditPath = Path("tests/audit/sectionsParityEdgar.py")
    spec = importlib.util.spec_from_file_location("sectionsParityEdgar", auditPath)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.measureTicker)
    assert callable(mod.main)
    assert mod.DEFAULT_TICKERS == ("AAPL", "MSFT", "GOOGL", "AMZN", "NVDA")


def test_measure_ticker_missing_old() -> None:
    """artifact 부재 ticker (옛 docs.parquet 0) → status='missing_old'."""
    import importlib.util
    from pathlib import Path

    auditPath = Path("tests/audit/sectionsParityEdgar.py")
    spec = importlib.util.spec_from_file_location("sectionsParityEdgar", auditPath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    result = mod.measureTicker("ZZZNONEXISTENT")
    assert result["status"] in ("missing_old", "missing_new")
    assert "ticker" in result


def test_measure_ticker_status_schema() -> None:
    """measureTicker 결과 dict 의 키 schema."""
    import importlib.util
    from pathlib import Path

    auditPath = Path("tests/audit/sectionsParityEdgar.py")
    spec = importlib.util.spec_from_file_location("sectionsParityEdgar", auditPath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    result = mod.measureTicker("ZZZ")
    assert result["ticker"] == "ZZZ"
    assert "status" in result
