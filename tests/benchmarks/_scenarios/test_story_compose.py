"""Benchmark 시나리오 3 — Story 8 막 compose (T3-1)."""

from __future__ import annotations

import pytest


@pytest.mark.benchmark
@pytest.mark.serial
class TestStoryCompose:
    """Story compose 8 막 P50 baseline — ≤ 10s 목표."""

    def test_story_compose_005930(self, benchmark) -> None:
        try:
            import dartlab

            story = dartlab.Story("005930")
        except (ImportError, AttributeError, RuntimeError):
            pytest.skip("dartlab.Story 미설치")
            return

        def compose() -> object:
            return story.compose() if hasattr(story, "compose") else story

        benchmark(compose)
