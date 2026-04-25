"""auditAnalysis/*.md (사람 수동 작성) 파싱 헬퍼.

Phase P 의 `--include-audit-analysis` 모드에서 참조.
md 파일의 "## 엔진 개선" 섹션 bullet 을 추출해 candidate 후보 풀에 편입한다.
"""

from __future__ import annotations

import re
from pathlib import Path

# "## 엔진 개선" 섹션 헤더 매치 (한/영·level 2/3 수용)
_SECTION_RX = re.compile(
    r"^(#{2,3})\s*(엔진\s*개선|Engine\s*Improve|Improvements?|개선\s*제안)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_BULLET_RX = re.compile(r"^\s*[-*]\s+(.+?)(?:\n|$)", re.MULTILINE)


def parse_engine_improvement_bullets(md_path: Path) -> list[str]:
    """한 md 파일의 '엔진 개선' 섹션 bullet 리스트 반환.

    파일이 없거나 섹션이 없으면 빈 리스트.
    """
    if not md_path.is_file():
        return []
    try:
        text = md_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    match = _SECTION_RX.search(text)
    if not match:
        return []
    header_level = len(match.group(1))
    # 섹션 본문: 다음 같은/상위 레벨 헤더 전까지
    start = match.end()
    tail = text[start:]
    next_header = re.search(rf"^#{{1,{header_level}}}\s+\S", tail, re.MULTILINE)
    body = tail[: next_header.start()] if next_header else tail

    bullets = [m.group(1).strip() for m in _BULLET_RX.finditer(body)]
    return [b for b in bullets if b]


def parse_all(audit_dir: Path) -> dict[str, list[str]]:
    """auditAnalysis 디렉토리 전체 순회 → `{stock_code: [bullet, ...]}`."""
    out: dict[str, list[str]] = {}
    if not audit_dir.is_dir():
        return out
    for md in audit_dir.glob("*.md"):
        stock_code = md.stem
        bullets = parse_engine_improvement_bullets(md)
        if bullets:
            out[stock_code] = bullets
    return out


__all__ = ["parse_engine_improvement_bullets", "parse_all"]
