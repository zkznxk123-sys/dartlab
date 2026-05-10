"""AskUserQuestion 4 지선다 안티패턴 차단 — PreToolUse hook validator.

목적: 한 question 의 options 수가 ≥ 3 개면 호출 자체를 거부. 결정 떠넘기기
패턴 (CLAUDE.md "사용자 질문 방식" + MEMORY.md "사용자 지시 수신 시 — 반드시
세 가지 중 하나로 응답") 의 머신 강제 게이트.

사용자 룰 본문:
    - "4 지선다·객관식 선택지 금지 (결정 떠넘김). 자체 판단으로 결론을
      좁힌 뒤, 필요하면 짧은 자유형 질문 1 개."

따라서 옵션 ≤ 2 개 (yes/no 류 양자택일) 만 허용. 정당한 3+ 옵션 케이스는
extremely rare — 발생 시 자체 판단으로 좁히거나 자유형 질문으로 변경.

PreToolUse hook 입력 (stdin JSON)::

    {
      "tool_name": "AskUserQuestion",
      "tool_input": {"questions": [{"question": "...", "options": [...]}]}
    }

종료 코드:
    0 — 통과 (또는 다른 도구 호출 — 무시)
    2 — 옵션 ≥ 3 인 question 발견, AskUserQuestion 차단
"""

from __future__ import annotations

import json
import sys

MAX_OPTIONS = 2


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") != "AskUserQuestion":
        return 0

    questions = (payload.get("tool_input") or {}).get("questions") or []
    bad: list[tuple[str, int]] = []
    for q in questions:
        opts = q.get("options") or []
        if len(opts) > MAX_OPTIONS:
            bad.append((q.get("question", "?"), len(opts)))

    if not bad:
        return 0

    sys.stderr.write("[validate-ask] AskUserQuestion 차단 — 4 지선다/3 지선다 안티패턴.\n")
    for question, n in bad:
        sys.stderr.write(f"  - options {n} 개 (최대 {MAX_OPTIONS}): {question[:120]}\n")
    sys.stderr.write(
        "\nCLAUDE.md '사용자 질문 방식': 4 지선다·객관식 선택지 금지 (결정 떠넘김).\n"
        "자체 판단으로 결론 좁힌 뒤, 필요하면 짧은 자유형 질문 1 개.\n"
        "options ≤ 2 (yes/no) 로 압축하거나, options 없이 자유형 question 으로 변경.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
