"""메모리 합성기 — 누적된 feedback_*.md 의 read-only 통계 view 산출.

회귀 가드: 원본 `feedback_*.md` 절대 자동 수정 없음. 합성기는 *측정 + 분류* 만,
의미 합성은 운영자가 main agent 에 요청해 cherry-pick.

산출: 입력 디렉토리 안 `_synth/feedbackStats.md` (markdown 리포트).
"""

from __future__ import annotations

from .feedbackStats import FeedbackStats, synthFeedbackStats

__all__ = ["FeedbackStats", "synthFeedbackStats"]
