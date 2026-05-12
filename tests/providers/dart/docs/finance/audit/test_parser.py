"""providers/dart/docs/finance/audit/parser.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.audit.parser  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_classify_block_callable() -> None:
    """classifyBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.audit.parser import classifyBlock

    assert callable(classifyBlock)


def test_dedup_callable() -> None:
    """dedup() callable smoke."""
    from dartlab.providers.dart.docs.finance.audit.parser import dedup

    assert callable(dedup)


def test_extract_table_blocks_callable() -> None:
    """extractTableBlocks() callable smoke."""
    from dartlab.providers.dart.docs.finance.audit.parser import extractTableBlocks

    assert callable(extractTableBlocks)


def test_find_audit_sections_callable() -> None:
    """findAuditSections() callable smoke."""
    from dartlab.providers.dart.docs.finance.audit.parser import findAuditSections

    assert callable(findAuditSections)


def test_fiscal_period_to_year_callable() -> None:
    """fiscalPeriodToYear() callable smoke."""
    from dartlab.providers.dart.docs.finance.audit.parser import fiscalPeriodToYear

    assert callable(fiscalPeriodToYear)


def test_normalize_opinion_callable() -> None:
    """normalizeOpinion() callable smoke."""
    from dartlab.providers.dart.docs.finance.audit.parser import normalizeOpinion

    assert callable(normalizeOpinion)


def test_parse_fee_block_callable() -> None:
    """parseFeeBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.audit.parser import parseFeeBlock

    assert callable(parseFeeBlock)


def test_parse_opinion_block_callable() -> None:
    """parseOpinionBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.audit.parser import parseOpinionBlock

    assert callable(parseOpinionBlock)
