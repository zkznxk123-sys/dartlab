"""review 엔진 실제 데이터 스모크 — 보고서 조립."""

from __future__ import annotations

import pytest


@pytest.mark.realData
@pytest.mark.integration
class TestReviewEngine:
    def test_blocks_builds(self, samsungRealData):
        """review.blocks(c) 가 실제 Company 로 블록 리스트 생성."""
        import dartlab

        blocks = dartlab.review.blocks(samsungRealData)
        assert blocks is not None

    def test_buildReview_assembles(self, samsungRealData):
        """review.buildReview(c) 가 Review 객체 조립."""
        import dartlab

        review = dartlab.review.buildReview(samsungRealData)
        assert review is not None
