"""providers/dart/search/derived.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.search.derived  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_company_profile_callable() -> None:
    """buildCompanyProfile() callable smoke."""
    from dartlab.providers.dart.search.derived import buildCompanyProfile

    assert callable(buildCompanyProfile)


def test_build_dna_callable() -> None:
    """buildDna() callable smoke."""
    from dartlab.providers.dart.search.derived import buildDna

    assert callable(buildDna)


def test_build_event_timeline_callable() -> None:
    """buildEventTimeline() callable smoke."""
    from dartlab.providers.dart.search.derived import buildEventTimeline

    assert callable(buildEventTimeline)


def test_dna_callable() -> None:
    """dna() callable smoke."""
    from dartlab.providers.dart.search.derived import dna

    assert callable(dna)


def test_load_profile_callable() -> None:
    """loadProfile() callable smoke."""
    from dartlab.providers.dart.search.derived import loadProfile

    assert callable(loadProfile)


def test_load_timeline_callable() -> None:
    """loadTimeline() callable smoke."""
    from dartlab.providers.dart.search.derived import loadTimeline

    assert callable(loadTimeline)


def test_pulse_callable() -> None:
    """pulse() callable smoke."""
    from dartlab.providers.dart.search.derived import pulse

    assert callable(pulse)


def test_similar_companies_callable() -> None:
    """similarCompanies() callable smoke."""
    from dartlab.providers.dart.search.derived import similarCompanies

    assert callable(similarCompanies)
