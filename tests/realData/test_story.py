"""story 엔진 실제 데이터 스모크 — 보고서 조립."""

from __future__ import annotations

import pytest


@pytest.mark.realData
@pytest.mark.integration
class TestReviewEngine:
    def test_blocks_builds(self, samsungRealData):
        """story.blocks(c) 가 실제 Company 로 블록 리스트 생성."""
        import dartlab

        blocks = dartlab.story.blocks(samsungRealData)
        assert blocks is not None

    def test_buildReview_assembles(self, samsungRealData):
        """story.buildStory(c) 가 Story 객체 조립."""
        import dartlab

        story = dartlab.story.buildStory(samsungRealData)
        assert story is not None
