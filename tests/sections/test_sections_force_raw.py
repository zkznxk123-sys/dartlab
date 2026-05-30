"""sectionsBuilder.forceRaw + periodIter env var DARTLAB_SECTIONS_NO_MIXED 회귀 가드.

plan snazzy-wibbling-origami PR-1c. 옛 docs.parquet 의 stale ``section_content_mixed``
cache 가 sectionsBuilder 의 신 변환 룰 (ALIGN/VALIGN 보존 등) 을 무효화하던 사고 차단.

검증:
    1. ``_forceRawSectionContent`` context 가 env var set + 원상복구
    2. context 안에서만 환경변수 보임
    3. nested context (이미 set 된 상태) 도 원상복구
"""

from __future__ import annotations

import os

import pytest

try:
    from dartlab.providers.dart.docs.sections.sectionsBuilder import _forceRawSectionContent
except ImportError:
    pytest.skip(
        "sections 사전빌드 파이프라인 (parked, plan snazzy-wibbling-origami §3.5 B) — "
        "sectionsBuilder 빌드/변환 함수 미완성. 완성 후 해제.",
        allow_module_level=True,
    )

pytestmark = [pytest.mark.unit]

_KEY = "DARTLAB_SECTIONS_NO_MIXED"


def test_force_raw_sets_env_inside_context():
    # env 미설정 상태로 진입
    os.environ.pop(_KEY, None)
    assert _KEY not in os.environ

    with _forceRawSectionContent():
        assert os.environ.get(_KEY) == "1"

    # context exit 후 원상복구
    assert _KEY not in os.environ


def test_force_raw_restores_prior_env_value():
    # 이미 다른 값으로 set 된 상태 → 원상복구
    os.environ[_KEY] = "0"
    with _forceRawSectionContent():
        assert os.environ.get(_KEY) == "1"
    assert os.environ.get(_KEY) == "0"
    os.environ.pop(_KEY, None)


def test_force_raw_restores_prior_set_value():
    os.environ[_KEY] = "true"
    with _forceRawSectionContent():
        assert os.environ.get(_KEY) == "1"
    assert os.environ.get(_KEY) == "true"
    os.environ.pop(_KEY, None)


def test_periodIter_recognizes_no_mixed_env(monkeypatch):
    """periodIter.iterPeriodSubsets 가 환경변수를 *호출 시점* 마다 read.

    옛 정공법 (모듈 import 시점 1 회 read) 은 sectionsBuilder 의 forceRaw context
    안에서도 옛 값 사용. 매 iterPeriodSubsets 호출시 read 가 정공법.
    """
    import polars as pl

    from dartlab.providers.dart.docs.sections import periodIter

    # mock loadData — section_content + section_content_mixed 둘 다 가진 df
    fakeDf = pl.DataFrame(
        {
            "year": ["2025"],
            "report_type": ["사업보고서"],
            "rcept_date": ["20251231"],
            "section_order": [0],
            "section_title": ["I. 회사의 개요"],
            "section_content": ["<P>raw 본문</P>"],
            "section_content_mixed": ["mixed 본문 (사전계산)"],
            "content": ["raw 본문"],
        }
    )

    monkeypatch.setattr("dartlab.providers.dart.docs.sections.periodIter.loadData", lambda *a, **kw: fakeDf)

    # 1. env 미설정 → mixed 우선
    monkeypatch.delenv(_KEY, raising=False)
    subsets_default = list(periodIter.iterPeriodSubsets("TEST"))
    if subsets_default:
        _, _, ccol_default, _ = subsets_default[0]
        assert ccol_default == "section_content_mixed", f"env 미설정 시 mixed 컬럼 우선 기대, 실제 {ccol_default}"

    # 2. env=1 → raw section_content 사용
    monkeypatch.setenv(_KEY, "1")
    subsets_forced = list(periodIter.iterPeriodSubsets("TEST"))
    if subsets_forced:
        _, _, ccol_forced, _ = subsets_forced[0]
        assert ccol_forced == "section_content", f"env=1 시 raw 컬럼 기대, 실제 {ccol_forced}"
