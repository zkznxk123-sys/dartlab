"""ExitPlanMode plan 본문 형식 게이트 — PreToolUse hook validator.

목적: plan mode 종료 시 plan 본문이 "끝까지 미는 plan" 의 최소 형식 요건을
충족하는지 강행한다. 미달이면 exit 2 로 ExitPlanMode 호출 자체를 차단해
모델이 plan 을 보강한 뒤 재호출하게 만든다.

본 게이트는 *형식* 만 검증한다. plan 의 *깊이/품질* 은 못 잡는다.
prose 룰 (`memory/plan_deep_gate.md`) + 절차서 (`.claude/skills/plan-deep/SKILL.md`)
와 결합돼야 의미가 있다.

필수 섹션 (4 개, 한국어 또는 영문):
    1. 영향 파일       — 어떤 파일이 변경되거나 영향을 받는지 path 목록
    2. 영향 함수/심볼  — 어떤 함수·메서드·심볼이 새/변경되는지
    3. 테스트          — 영향받는 테스트 또는 신규 테스트 매핑
    4. 롤백            — 실패 시 되돌릴 절차/커밋 단위

추가 정량 게이트:
    - plan 본문 안에 명시된 path 토큰 (예: ``src/foo/bar.py``) 이 ≥ 2 개.
      placeholder ("TBD", "TODO" 단독) 회피 차단.
    - 각 필수 섹션 헤더 다음에 비어있지 않은 본문 1 줄 이상 존재.

PreToolUse hook 입력 (stdin JSON)::

    {
      "session_id": "...",
      "tool_name": "ExitPlanMode",
      "tool_input": {"plan": "..."}
    }

종료 코드:
    0 — 통과 (또는 ExitPlanMode 가 아닌 다른 도구 호출 — 무시)
    2 — 형식 게이트 미달, ExitPlanMode 차단

bypass: 하나의 plan 안에 ``<!-- plan-gate: bypass -->`` 주석이 있으면 형식
검증을 스킵 (긴급 핫픽스 등). 남용 방지로 stderr 에 경고 한 줄 띄운다.
"""

from __future__ import annotations

import json
import re
import sys

REQUIRED_SECTIONS: tuple[tuple[str, str], ...] = (
    ("영향 파일", r"##+\s*(?:영향\s*파일|Files\b|Affected\s+Files)"),
    ("영향 함수/심볼", r"##+\s*(?:영향\s*함수|영향\s*심볼|Functions?\b|Symbols?\b)"),
    ("테스트", r"##+\s*(?:테스트|Test\s*plan|Tests?\b)"),
    ("롤백", r"##+\s*(?:롤백|Rollback\b|Revert\b)"),
)

PATH_TOKEN_RE = re.compile(r"[\w./-]+/[\w./-]+\.[a-zA-Z0-9]+")
PLACEHOLDER_RE = re.compile(r"^\s*(?:TBD|TODO|XXX|\?+|N/?A|미정)\s*$", re.IGNORECASE)
BYPASS_RE = re.compile(r"<!--\s*plan-gate:\s*bypass\s*-->", re.IGNORECASE)
MIN_PATH_TOKENS = 2


def _section_body(plan: str, header_re: str) -> str | None:
    m = re.search(header_re, plan, re.IGNORECASE)
    if not m:
        return None
    after = plan[m.end() :]
    next_header = re.search(r"\n##+\s", after)
    body = after[: next_header.start()] if next_header else after
    return body.strip()


def _validate(plan: str) -> list[str]:
    errors: list[str] = []

    missing: list[str] = []
    empty: list[str] = []
    for label, header_re in REQUIRED_SECTIONS:
        body = _section_body(plan, header_re)
        if body is None:
            missing.append(label)
            continue
        non_placeholder_lines = [ln for ln in body.splitlines() if ln.strip() and not PLACEHOLDER_RE.match(ln)]
        if not non_placeholder_lines:
            empty.append(label)

    if missing:
        errors.append("누락 섹션 (`## 영향 파일` / `## 영향 함수` / `## 테스트` / `## 롤백`):")
        for label in missing:
            errors.append(f"    - {label}")

    if empty:
        errors.append("placeholder 만 있는 섹션 (TBD/TODO/미정 단독 금지):")
        for label in empty:
            errors.append(f"    - {label}")

    path_tokens = PATH_TOKEN_RE.findall(plan)
    unique_paths = sorted(set(path_tokens))
    if len(unique_paths) < MIN_PATH_TOKENS:
        errors.append(
            f"영향 파일 path 토큰 {len(unique_paths)} 개 (최소 {MIN_PATH_TOKENS}). "
            "구체 path (예: `src/dartlab/foo/bar.py`) 를 본문에 명시하라."
        )

    return errors


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") != "ExitPlanMode":
        return 0

    plan = (payload.get("tool_input") or {}).get("plan") or ""
    if not plan.strip():
        sys.stderr.write("[validate-plan] plan 본문 비어있음 — ExitPlanMode 차단.\n")
        return 2

    if BYPASS_RE.search(plan):
        sys.stderr.write("[validate-plan] WARN — bypass 마커 감지. 형식 게이트 스킵 (긴급 핫픽스 가정).\n")
        return 0

    errors = _validate(plan)
    if not errors:
        return 0

    sys.stderr.write("[validate-plan] ExitPlanMode 차단 — plan 형식 게이트 미달:\n")
    for line in errors:
        sys.stderr.write(f"  {line}\n")
    sys.stderr.write(
        "\n절차 SSOT: `.claude/skills/plan-deep/SKILL.md` · prose 룰: "
        "`memory/plan_deep_gate.md`. 4 섹션 채우고 영향 path ≥ 2 개 명시 후 재호출.\n"
        "정말 형식 미달 그대로 진행해야 하면 plan 본문에 "
        "`<!-- plan-gate: bypass -->` 추가.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
