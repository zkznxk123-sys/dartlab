"""xbrlConcepts.py mirror test."""

import pytest

pytestmark = pytest.mark.unit


def test_imports() -> None:
    """모듈 import smoke."""
    from dartlab.providers.edgar.finance import xbrlConcepts

    assert hasattr(xbrlConcepts, "normalizeConcept")
    assert hasattr(xbrlConcepts, "US_GAAP_CONCEPT_MAP")


def test_normalize_concept_assets() -> None:
    """Assets → total_assets."""
    from dartlab.providers.edgar.finance.xbrlConcepts import normalizeConcept

    assert normalizeConcept("Assets") == "total_assets"


def test_normalize_concept_unknown() -> None:
    """매핑 없으면 None."""
    from dartlab.providers.edgar.finance.xbrlConcepts import normalizeConcept

    assert normalizeConcept("UnknownConcept") is None


def test_list_concepts_has_assets() -> None:
    """listConcepts 가 핵심 concept 포함."""
    from dartlab.providers.edgar.finance.xbrlConcepts import listConcepts

    concepts = listConcepts()
    assert "Assets" in concepts
    assert "NetIncomeLoss" in concepts
    assert "Revenues" in concepts


def test_iter_concepts_basic() -> None:
    """iterConcepts() generator pair."""
    from dartlab.providers.edgar.finance.xbrlConcepts import iterConcepts

    items = list(iterConcepts(limit=3))
    assert len(items) == 3
    assert all(isinstance(c, str) for c in items)
