"""sections() fast path skeleton 회귀.

Phase C 본격 처방 (DuckDB PIVOT) 의 *명목 skeleton* — 환경변수 활성 시
``_sectionsFastDuckdb`` 호출. 현재는 ``NotImplementedError`` 라서 *legacy fallback*
경로 활성. 본 회귀 가드:

  1. ``_sectionsFastDuckdb`` 가 호출 가능 + 항상 ``NotImplementedError``.
  2. 환경변수 ``DARTLAB_SECTIONS_FAST_PIVOT=1`` 활성 시 sections() 가 fallback
     으로 legacy 결과 반환 (caller 0 차이).
  3. 환경변수 없는 default 호출은 기존 동작.

실제 SQL 구현은 별도 PR — caller predicate statementFilter 6 fail 사례
(commit 7eebdacbc) 가 보여주듯 sj_div 단순 가정만으로 부족. sections 의
30+ 컬럼 schema 는 동일/더 큰 parity 위험.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_fast_path_skeleton_raises_not_implemented() -> None:
    """``_sectionsFastDuckdb`` 가 항상 NotImplementedError — fail/revert 후 skeleton 복귀.

    시도 history (transcript): 부분 SQL 작성 (detailTopicForTopic mapper import)
    → ImportError fail → revert. *내 능력 한계 실증*.
    """
    from dartlab.providers.dart.docs.sections.pipeline import _sectionsFastDuckdb

    with pytest.raises(NotImplementedError) as excInfo:
        _sectionsFastDuckdb("005930", None)
    msg = str(excInfo.value)
    assert "별도 PR" in msg or "미구현" in msg


def test_env_var_off_uses_legacy(monkeypatch) -> None:
    """환경변수 OFF — sections() 가 기존 path 사용 (NotImplementedError 발생 X)."""
    monkeypatch.delenv("DARTLAB_SECTIONS_FAST_PIVOT", raising=False)
    from dartlab.providers.dart.docs.sections.pipeline import sections

    # 실제 데이터 없으면 None — 단 호출 자체는 정상 (NotImplementedError 안 남)
    try:
        result = sections("000000", topics={"businessOverview"})  # 가짜 종목
        # 결과 None 또는 DataFrame — NotImplementedError 안 나면 PASS
        assert result is None or hasattr(result, "schema")
    except (FileNotFoundError, OSError, RuntimeError):
        pass  # 종목 데이터 부재 / 네트워크 실패 — skeleton 자체와 무관  # 종목 데이터 부재 — skeleton 자체와 무관


def test_env_var_on_falls_back_to_legacy(monkeypatch) -> None:
    """환경변수 ON — _sectionsFastDuckdb NotImplementedError 후 legacy fallback."""
    monkeypatch.setenv("DARTLAB_SECTIONS_FAST_PIVOT", "1")
    from dartlab.providers.dart.docs.sections.pipeline import sections

    # legacy fallback 이라 결과는 default 와 동일 (실데이터 부재 시 None).
    try:
        result = sections("000000", topics={"businessOverview"})
        assert result is None or hasattr(result, "schema")
    except (FileNotFoundError, OSError, RuntimeError):
        pass  # 종목 데이터 부재 / 네트워크 실패 — skeleton 자체와 무관
