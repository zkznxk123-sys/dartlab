"""Stop hook trigger phrase 가드 — 컷오프/4지선다 안티패턴 차단.

목적: assistant 의 마지막 응답 텍스트에 다음 안티패턴이 있으면 stop 차단,
모델을 다시 turn 으로 돌려서 끝까지 진행하거나 자유형 질문 1 개로 좁히게
강제한다.

차단 대상:
    1. "다음 세션에서 이어한다" 류 컷오프 — auto-compact 가 컨텍스트를
       자동 압축하므로 세션 한계 가정 자체가 오류.
    2. "(A) ... (B) ... (C) ..." 본문 4지선다 — AskUserQuestion 도구를
       안 쓰고 답변 본문에 직접 객관식 박는 안티패턴 (validate_ask.py 가
       못 잡는 케이스).
    3. "다음 중 선택", "결정 부탁", "어느 옵션" 류 결정 떠넘기기 phrase.

사용자 룰:
    - MEMORY.md "사용자 지시 수신 시 — 반드시 세 가지 중 하나로 응답"
    - feedback_finish_to_end_no_midstop.md "끝까지 자동 실행"
    - CLAUDE.md "사용자 질문 방식 — 4 지선다·객관식 선택지 금지"

Stop hook 입력 (stdin JSON)::

    {
      "session_id": "...",
      "transcript_path": "...",
      "stop_hook_active": false,
      ...
    }

종료 코드:
    0 — 통과 (trigger phrase 없음, 또는 stop_hook_active 재진입 차단)
    2 — trigger phrase 감지, stop 차단 + 모델 재투입
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# 컷오프 패턴 — 동사가 동반된 *행위* 만 매치 (단순 명사구 false positive 회피).
CUTOFF_PATTERNS: tuple[str, ...] = (
    r"다음\s*세션(?:에서|에)?\s*(?:이어|진행|계속|마저|이를|넘기|하겠|할\s*수)",
    r"(?:이번\s*)?세션\s*(?:한계|컷오프)",
    r"한\s*세션\s*(?:안에|에)?\s*(?:못\s*끝|어렵|한계)",
    r"여기까지(?:가)?\s*(?:한계|이번\s*세션)",
    r"이번\s*세션은\s*여기서\s*(?:마무리|중단|종료|끝)",
)

# 본문 4지선다 — assistant 가 답변 텍스트에 직접 (A)/(B)/(C)/(D) 박는 케이스.
# AskUserQuestion 도구를 우회한 결정 떠넘김.
MULTICHOICE_PATTERNS: tuple[str, ...] = (
    r"\(A\)[\s\S]{1,800}?\(B\)[\s\S]{1,800}?\(C\)",
    r"^\s*A[.)][\s\S]{1,800}?^\s*B[.)][\s\S]{1,800}?^\s*C[.)]",
    r"다음\s*중\s*(?:선택|골라|고르|하나)",
    r"(?:결정|선택)\s*부탁",
    r"어느\s*(?:옵션|쪽|것|안)(?:으로|이|을|로)?",
)

ALL_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = tuple(
    [("cutoff", p, re.compile(p, re.IGNORECASE | re.MULTILINE)) for p in CUTOFF_PATTERNS]
    + [("multichoice", p, re.compile(p, re.IGNORECASE | re.MULTILINE)) for p in MULTICHOICE_PATTERNS]
)

BYPASS_RE = re.compile(r"<!--\s*stop-guard:\s*bypass\s*-->", re.IGNORECASE)


def _last_assistant_text(transcript_path: Path) -> str:
    try:
        lines = transcript_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""

    for line in reversed(lines[-100:]):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        msg = entry.get("message") or {}
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        text_parts: list[str] = []
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(str(block.get("text") or ""))
        elif isinstance(content, str):
            text_parts.append(content)
        if text_parts:
            return "\n".join(text_parts)
    return ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("stop_hook_active"):
        return 0

    transcript_path = payload.get("transcript_path")
    if not transcript_path:
        return 0
    p = Path(transcript_path)
    if not p.exists():
        return 0

    text = _last_assistant_text(p)
    if not text:
        return 0

    if BYPASS_RE.search(text):
        return 0

    matches: list[tuple[str, str, str]] = []
    for kind, pattern, compiled in ALL_PATTERNS:
        m = compiled.search(text)
        if m:
            snippet = m.group(0).replace("\n", " ")[:100]
            matches.append((kind, pattern, snippet))

    if not matches:
        return 0

    sys.stderr.write("[validate-stop-phrase] Stop 차단 — 컷오프/4지선다 안티패턴 감지.\n")
    for kind, pattern, snippet in matches:
        sys.stderr.write(f"  - [{kind}] '{snippet}'\n")
    sys.stderr.write(
        "\nauto-compact 가 컨텍스트 자동 압축한다 — '다음 세션' 컷오프 자체가 가정 오류.\n"
        "MEMORY.md '사용자 지시 수신 시 — 세 가지 중 하나로 응답' + "
        "feedback_finish_to_end_no_midstop.md '끝까지 자동 실행' + "
        "CLAUDE.md '4 지선다 금지'.\n"
        "끝까지 진행하거나, 자체 판단으로 결론 좁힌 뒤 짧은 자유형 질문 1 개.\n"
        "정말 컷오프가 필요한 비가역 결정점이면 응답 안에 "
        "`<!-- stop-guard: bypass -->` 추가.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
