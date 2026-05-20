"""buildToneBlock 회귀 가드 — 합성 view 가 system prompt 에 흘러가는지."""

from __future__ import annotations

import time
from pathlib import Path

import pytest


def _writeFeedback(path: Path, *, name: str, description: str, body: str) -> None:
    fm = f"---\nname: {name}\ndescription: {description}\nmetadata:\n  type: feedback\n---\n\n{body}\n"
    path.write_text(fm, encoding="utf-8")


@pytest.fixture
def fake_memory(tmp_path, monkeypatch):
    mem = tmp_path / "memory"
    mem.mkdir()
    _writeFeedback(
        mem / "feedback_alpha.md",
        name="alpha",
        description="자동 sweep 금지 — 운영자 명시 트리거",
        body="자동 도구 회귀 차단. 관련: [[feedback_beta]]",
    )
    _writeFeedback(
        mem / "feedback_beta.md",
        name="beta",
        description="docstring 자동 격상 금지",
        body="회귀 가드 lint 동행. 관련: [[feedback_alpha]]",
    )
    cache = tmp_path / "tone.cache.md"
    monkeypatch.setenv("DARTLAB_MEMORY_DIR", str(mem))
    monkeypatch.setenv("DARTLAB_TONE_CACHE_PATH", str(cache))
    return {"mem": mem, "cache": cache}


@pytest.mark.unit
def test_tone_block_non_empty_when_memory_has_feedback(fake_memory):
    from dartlab.ai.memory.synthesizer import buildToneBlock

    block = buildToneBlock()
    assert block, "feedback 메모리 있을 때 빈 블록 반환"
    assert "운영자 톤" in block
    assert "근본 톤 키워드" in block


@pytest.mark.unit
def test_tone_block_empty_when_memory_missing(tmp_path, monkeypatch):
    from dartlab.ai.memory.synthesizer import buildToneBlock

    monkeypatch.setenv("DARTLAB_MEMORY_DIR", str(tmp_path / "nonexistent"))
    monkeypatch.setenv("DARTLAB_TONE_CACHE_PATH", str(tmp_path / "cache.md"))
    assert buildToneBlock() == ""


@pytest.mark.unit
def test_tone_block_cache_hit_skips_resynth(fake_memory, monkeypatch):
    from dartlab.ai.memory.synthesizer import buildToneBlock, promptInjector

    block_first = buildToneBlock()
    assert fake_memory["cache"].exists()

    # 다음 호출이 synthFeedbackStats 를 *호출 안 하는지* 검증 — monkeypatch
    called = {"count": 0}

    def _spy(*args, **kwargs):
        called["count"] += 1
        raise RuntimeError("synth should not be called when cache valid")

    monkeypatch.setattr(promptInjector, "synthFeedbackStats", _spy)
    block_second = buildToneBlock()
    assert called["count"] == 0
    assert block_second == block_first


@pytest.mark.unit
def test_tone_block_cache_invalidated_when_memory_modified(fake_memory):
    from dartlab.ai.memory.synthesizer import buildToneBlock

    buildToneBlock()
    cache = fake_memory["cache"]
    assert cache.exists()
    cache_mtime_first = cache.stat().st_mtime

    # 1.5 초 대기 후 feedback 추가 — memory mtime > cache mtime → invalidate
    time.sleep(1.5)
    _writeFeedback(
        fake_memory["mem"] / "feedback_gamma.md",
        name="gamma",
        description="새 룰 — 측정 후 박기",
        body="회귀 가드 N 회",
    )
    block_after = buildToneBlock()
    assert cache.stat().st_mtime > cache_mtime_first
    assert "측정" in block_after or "회귀" in block_after


@pytest.mark.unit
def test_tone_block_force_refresh_skips_cache(fake_memory, monkeypatch):
    from dartlab.ai.memory.synthesizer import buildToneBlock, promptInjector

    buildToneBlock()  # 캐시 박음
    called = {"count": 0}
    orig = promptInjector.synthFeedbackStats

    def _spy(*args, **kwargs):
        called["count"] += 1
        return orig(*args, **kwargs)

    monkeypatch.setattr(promptInjector, "synthFeedbackStats", _spy)
    buildToneBlock(forceRefresh=True)
    assert called["count"] == 1, "forceRefresh=True 인데 재합성 안 됨"
