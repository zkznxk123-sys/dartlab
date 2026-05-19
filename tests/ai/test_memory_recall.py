"""recall 점수화 — target / skill category / metric 가중치."""

from __future__ import annotations

from pathlib import Path

import pytest

from dartlab.ai.memory.decisions import recall, remember, setDecisionsPathForTesting


@pytest.fixture
def isolated_decisions(tmp_path: Path) -> Path:
    """각 테스트마다 별도 decisions.jsonl 로 격리."""
    p = tmp_path / "decisions.jsonl"
    setDecisionsPathForTesting(p)
    yield p


@pytest.mark.unit
def test_recall_boosts_target_match(isolated_decisions: Path) -> None:
    """query 안 stockCode 가 record.tags 의 target:CODE 와 일치하면 +0.3 가중."""
    remember("삼성전자 자산총계 분석 결과", tags=["target:005930", "skill:engines.company"])
    remember("현대차 자산총계 분석 결과", tags=["target:005380", "skill:engines.company"])

    results = recall("삼성전자 005930 자산총계", k=5)
    # 005930 일치 record 가 첫 번째
    assert results[0]["text"] == "삼성전자 자산총계 분석 결과"


@pytest.mark.unit
def test_recall_boosts_recipe_skill(isolated_decisions: Path) -> None:
    """skill:recipes.* 태그 record 가 +0.2 가중."""
    remember("일반 분석 결과", tags=["skill:engines.company"])
    remember("종합 recipe 분석 결과", tags=["skill:recipes.meta.report.companyDeepAnalysis"])

    results = recall("종합 분석 recipe", k=5)
    # recipe 태그가 첫 번째
    assert results[0]["text"] == "종합 recipe 분석 결과"


@pytest.mark.unit
def test_recall_boosts_metric_match(isolated_decisions: Path) -> None:
    """metric:NAME 태그가 query 토큰에 포함되면 +0.2 가중."""
    # 두 record 모두 base overlap 동일 (분석 토큰 일치) → metric 가중이 결정
    remember("일반 분석", tags=["skill:engines.company"])
    remember("자산총계 분석 결과", tags=["metric:total_assets"])

    results = recall("total_assets 분석", k=5)
    assert results[0]["text"] == "자산총계 분석 결과"


@pytest.mark.unit
def test_recall_returns_empty_for_no_overlap(isolated_decisions: Path) -> None:
    """토큰 overlap 0 인 record 는 score=0 → 결과에서 제외."""
    remember("삼성전자 자산총계", tags=["target:005930"])
    results = recall("애플 매출", k=5)
    assert results == []


@pytest.mark.unit
def test_recall_preserves_base_score_without_tags(isolated_decisions: Path) -> None:
    """tag 가 없어도 토큰 overlap 만으로 score > 0 이면 결과에 포함."""
    remember("삼성전자 분석 결과")
    results = recall("삼성전자 종합 분석", k=5)
    assert len(results) == 1
    assert results[0]["text"] == "삼성전자 분석 결과"
