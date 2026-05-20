"""feedback_*.md 합성 결과를 system prompt 용 짧은 블록으로 변환 + 캐시.

`feedbackStats.synthFeedbackStats` 의 결과를 *답변마다* 다시 계산하면 느리고
토큰 비용. 캐시 파일 (`~/.dartlab/ai_memory/feedbackTone.cache.md`) 에 7 일 TTL
또는 memory 디렉토리 mtime 변경 시 stale 로 자동 재계산.

블록 형태 (system prompt 끝에 부착):

    ## 운영자 톤 (메모리 합성 — 답변 작성 시 참조)
    근본 톤: 자동 X · 운영자 명시 트리거 · 회귀 가드 lint 동행 · 측정 후 박기
    톱 키워드: 금지(N) · 자동(N) · ...

빈 문자열 반환 시 호출자가 헤더 자체 부재화 (환각 가드).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .feedbackStats import FeedbackStats, synthFeedbackStats

_CACHE_DEFAULT = Path.home() / ".dartlab" / "ai_memory" / "feedbackTone.cache.md"
_CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 일


def _cachePath() -> Path:
    env = os.environ.get("DARTLAB_TONE_CACHE_PATH")
    return Path(env) if env else _CACHE_DEFAULT


def _memoryDir() -> Path | None:
    """운영자 memory 디렉토리 위치 — env override 우선, 없으면 표준 경로 추정.

    sweep 휴리스틱: 여러 프로젝트 memory 가 있을 때 *가장 많은 feedback_*.md* 가진
    디렉토리 선택. dartlab 메모리 38 개 vs 다른 프로젝트 1~2 개 같은 분포라면
    dartlab 이 정확히 매칭됨.
    """
    env = os.environ.get("DARTLAB_MEMORY_DIR")
    if env:
        candidate = Path(env)
        return candidate if candidate.is_dir() else None

    base = Path.home() / ".claude" / "projects"
    if not base.exists():
        return None

    best: Path | None = None
    best_count = 0
    for proj in base.iterdir():
        if not proj.is_dir():
            continue
        mem = proj / "memory"
        if not mem.is_dir():
            continue
        count = sum(1 for _ in mem.glob("feedback_*.md"))
        if count > best_count:
            best = mem
            best_count = count
    return best


def _maxMtime(memoryDir: Path) -> float:
    """feedback_*.md 중 가장 최근 mtime — 캐시 staleness 판정."""
    latest = 0.0
    for path in memoryDir.glob("feedback_*.md"):
        try:
            mt = path.stat().st_mtime
            if mt > latest:
                latest = mt
        except OSError:
            continue
    return latest


def _isCacheValid(cachePath: Path, memoryDir: Path) -> bool:
    """캐시가 7 일 TTL + memory mtime 모두 만족하면 valid."""
    if not cachePath.exists():
        return False
    try:
        cache_mtime = cachePath.stat().st_mtime
    except OSError:
        return False
    import time

    if time.time() - cache_mtime > _CACHE_TTL_SECONDS:
        return False
    if _maxMtime(memoryDir) > cache_mtime:
        return False
    return True


def _formatBlock(stats: FeedbackStats, *, topTokens: int = 6, topLinks: int = 4) -> str:
    """FeedbackStats → system prompt 부착용 짧은 markdown 블록."""
    if stats.file_count == 0:
        return ""
    lines: list[str] = ["## 운영자 톤 (메모리 합성 — 답변 작성 시 참조)"]
    ko_top = [tok for tok, _ in stats.ko_top_tokens[:topTokens]]
    if ko_top:
        lines.append(f"근본 톤 키워드: {' · '.join(ko_top)}")
    link_top = [f"[[{name}]]" for name, _ in stats.link_in_degree[:topLinks]]
    if link_top:
        lines.append(f"자주 참조되는 룰: {' · '.join(link_top)}")
    lines.append(f"누적 메모리: {stats.file_count} 파일.")
    lines.append(
        "답변 톤은 본 키워드·룰과 충돌하지 않게 — 자동 sweep / 측정 없는 단정 / 운영자 명시 없는 트랙 진행 회피."
    )
    return "\n".join(lines) + "\n"


def buildToneBlock(*, memoryDir: Path | None = None, forceRefresh: bool = False) -> str:
    """system prompt 부착용 운영자 톤 블록 반환.

    Args:
        memoryDir: feedback_*.md 위치. None 이면 표준 경로 자동 탐색.
        forceRefresh: True 면 캐시 무시하고 즉시 재합성.

    Returns:
        markdown 블록 문자열. memory 없거나 합성 실패 시 빈 문자열 (호출자 graceful skip).
    """
    mem = memoryDir or _memoryDir()
    if mem is None or not mem.is_dir():
        return ""

    cache = _cachePath()
    if not forceRefresh and _isCacheValid(cache, mem):
        try:
            return cache.read_text(encoding="utf-8")
        except OSError:
            pass  # cache 읽기 실패 → 재합성

    try:
        stats = synthFeedbackStats(mem, writeReport=False)
    except Exception:  # noqa: BLE001
        return ""

    block = _formatBlock(stats)
    if not block:
        return ""

    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(block, encoding="utf-8")
    except OSError:
        pass  # cache 쓰기 실패해도 블록 반환은 OK

    return block


__all__ = ["buildToneBlock"]
