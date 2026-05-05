"""dartlab-skills review — status 승격 후보 표출 + 운영자 confirm + frontmatter 실 갱신.

사용:
    uv run python -X utf8 scripts/dartlab-skills-review.py            # 후보만 표출
    uv run python -X utf8 scripts/dartlab-skills-review.py --apply    # 후보 confirm 받고 frontmatter 갱신

읽기: ~/.dartlab/ai_memory/skill_stats.jsonl + skills/specs/**/*.md frontmatter.
승격 (unverified→observed) 은 운영자 y 입력 시만 frontmatter 갱신.
observed→auditP 는 자동 시그널만 표시 (실제 frontmatter 갱신은 별도 audit 도구 통과 후).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _loadSkillStatuses() -> dict[str, tuple[str, Path]]:
    """SkillSpec frontmatter 에서 id → (status, path) 매핑."""
    skill_root = Path(__file__).resolve().parents[1] / "src" / "dartlab" / "skills" / "specs"
    out: dict[str, tuple[str, Path]] = {}
    if not skill_root.exists():
        return out
    for md in skill_root.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        m_id = re.search(r"^id:\s*(\S+)", text, re.MULTILINE)
        m_status = re.search(r"^status:\s*(\S+)", text, re.MULTILINE)
        if m_id and m_status:
            out[m_id.group(1)] = (m_status.group(1), md)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="confirm 받고 frontmatter 실 갱신")
    args = parser.parse_args(argv)

    from dartlab.ai.memory import updateStatus
    from dartlab.ai.memory.promotion import promotionCandidates

    raw = _loadSkillStatuses()
    statuses = {sid: pair[0] for sid, pair in raw.items()}
    candidates = promotionCandidates(statuses)

    if not candidates:
        print("승격 후보 없음.")
        return 0

    print(f"승격 후보 {len(candidates)}건:\n")
    for cand in candidates:
        gate = "[운영자 confirm 필수]" if cand.requiresConfirm else "[자동 가능]"
        print(f"  {cand.skillId}: {cand.fromStatus} → {cand.toStatus} {gate}")
        print(f"    근거: {cand.reason}")

    if not args.apply:
        print("\n--apply 옵션 없으면 frontmatter 갱신 안 함. 표출만.")
        return 0

    print()
    applied = 0
    for cand in candidates:
        path = raw.get(cand.skillId, (None, None))[1]
        if path is None:
            continue
        prompt = f"  {cand.skillId} {cand.fromStatus}→{cand.toStatus} 적용? (y/N): "
        if cand.requiresConfirm:
            try:
                ans = input(prompt).strip().lower()
            except EOFError:
                ans = "n"
            if ans != "y":
                print(f"    skip ({cand.skillId})")
                continue
        ok = updateStatus(path, cand.toStatus)
        if ok:
            applied += 1
            print(f"    applied: {cand.skillId} → {cand.toStatus}")
        else:
            print(f"    failed: {cand.skillId}")
    print(f"\n총 {applied}건 갱신.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
