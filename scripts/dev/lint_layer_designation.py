"""계층 명명 lint — alias 금지 강제.

룰 (operation.philosophy §5 + operation.architecture):
- L0: core
- L1: company (provider facade), gather
- L1.5: scan (종목 횡단), search (문서 횡단)
- L2 분석엔진 (5): analysis, credit, macro, quant, industry
- L3 조합기: story (분석엔진 X — 순환참조 방지)
- L4: 소비자

검사 항목:
1. SKILL.md 가 자칭 "L2 엔진" 인 곳은 정확히 5 개여야 함 (L2 5 분석엔진).
2. scan SKILL.md 가 "L1.5" 자칭.
3. industry SKILL.md 가 "L2 분석엔진" 자칭 (자칭 "매퍼 엔진" 단독 금지).
4. story SKILL.md 가 "L3 조합기" 자칭 (자칭 "분석엔진" 또는 "L2" 평탄화 금지).
5. "6 분석 엔진" 표현 0 hit (전 repo).
6. operation/architecture.md 의 import 방향이 "L0 ← L1 ← L1.5 ← L2 ← L3" 형식.

Usage:
    uv run python -X utf8 scripts/dev/lint_layer_designation.py
    uv run python -X utf8 scripts/dev/lint_layer_designation.py --strict   # exit 1 if violations
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "src" / "dartlab" / "skills" / "specs" / "engines"

L2_ENGINES = ("analysis", "credit", "macro", "quant", "industry")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _check_l2_self_label(violations: list[str]) -> None:
    """L2 5 엔진 SKILL.md 가 자칭 'L2 엔진' / 'L2 분석엔진' 을 포함해야 함."""
    for engine in L2_ENGINES:
        skill = SPECS / engine / "SKILL.md"
        if not skill.exists():
            violations.append(f"{skill.relative_to(ROOT)} — SKILL.md 없음.")
            continue
        text = _read(skill)
        if "L2 엔진" not in text and "L2 분석엔진" not in text:
            violations.append(
                f"{skill.relative_to(ROOT)} — '{engine}' 가 L2 분석엔진 자칭 없음. "
                "본문 '엔진 역할' 단락에 'L2 분석엔진' 또는 'L2 엔진' 명시 필요."
            )


def _check_scan_l15(violations: list[str]) -> None:
    """scan SKILL.md 가 L1.5 자칭이어야 하고 'L2 엔진' 자칭 금지."""
    skill = SPECS / "scan" / "SKILL.md"
    text = _read(skill)
    if not text:
        violations.append(f"{skill.relative_to(ROOT)} — 읽기 실패.")
        return
    if "L1.5" not in text:
        violations.append(f"{skill.relative_to(ROOT)} — scan 이 L1.5 자칭 없음.")
    # scan 이 자기 자신을 'L2 엔진' 라고 부르는 패턴 ("scan ... L2 엔진")
    body_lines = text.splitlines()
    for line_no, line in enumerate(body_lines, start=1):
        if "scan" in line and "L2 엔진" in line and "L1.5" not in line:
            # "L2 엔진 ... 가 아니" 같은 부정형은 통과
            if "아니" in line or "X" in line:
                continue
            violations.append(f"{skill.relative_to(ROOT)}:{line_no} — scan 이 'L2 엔진' 평탄화. L1.5 명시 필요.")


def _check_industry_l2(violations: list[str]) -> None:
    """industry SKILL.md 가 'L2 분석엔진' 자칭이어야 하고 '매퍼 엔진' 단독 금지."""
    skill = SPECS / "industry" / "SKILL.md"
    text = _read(skill)
    if not text:
        violations.append(f"{skill.relative_to(ROOT)} — 읽기 실패.")
        return
    if "L2 분석엔진" not in text:
        violations.append(f"{skill.relative_to(ROOT)} — industry 가 'L2 분석엔진' 자칭 없음.")
    # '매퍼 엔진' 단독 표현 (괄호 보조 어휘 X) 검사
    for line_no, line in enumerate(text.splitlines(), start=1):
        if "매퍼 엔진" in line and "L2" not in line:
            violations.append(
                f"{skill.relative_to(ROOT)}:{line_no} — '매퍼 엔진' 단독 표현. "
                "'L2 분석엔진 (산업 매퍼)' 형식으로 보조 어휘 처리."
            )


def _check_story_l3(violations: list[str]) -> None:
    """story SKILL.md 가 'L3 조합기' 자칭이어야 하고 '분석엔진' 평탄화 금지."""
    skill = SPECS / "story" / "SKILL.md"
    text = _read(skill)
    if not text:
        violations.append(f"{skill.relative_to(ROOT)} — 읽기 실패.")
        return
    if "L3 조합기" not in text:
        violations.append(f"{skill.relative_to(ROOT)} — story 가 'L3 조합기' 자칭 없음.")
    # story 가 자기 자신을 '분석엔진' / 'L2 엔진' 라고 *서술하는* 패턴
    # 식별 어휘: "story 는 L2", "story 가 L2", "story 는 ... 분석엔진", "story 가 ... 분석엔진".
    # 외부 참조 (story 가 다루는 대상) 와 ecosystem 서술은 통과.
    skip_substr = ("5 분석엔진", "조합", "추가", "수정", "등록", "블록", "결합", "참조", "직조", "묶")
    for line_no, line in enumerate(text.splitlines(), start=1):
        lower = line.lower()
        if "story" not in lower or "L2 엔진" not in line:
            continue
        if any(s in line for s in skip_substr):
            continue
        # 자기 서술 패턴 식별
        is_self_desc = any(tok in line for tok in ("story 는 L2", "story 가 L2", "`story` 는 L2", "`story` 가 L2"))
        if not is_self_desc:
            continue
        violations.append(f"{skill.relative_to(ROOT)}:{line_no} — story 가 'L2 엔진' 평탄화. L3 조합기 분리 필요.")


def _check_six_engine_phrase(violations: list[str]) -> None:
    """'6 분석 엔진' / '분석엔진 6' / '6 엔진 동일' alias 금지 — 전 repo."""
    forbidden_phrases = ("6 분석 엔진", "6분석엔진", "분석엔진 6", "6 엔진 동일")
    scan_dirs = [
        ROOT / "src" / "dartlab",
        ROOT / "README.md",
        ROOT / "blog",
        ROOT / ".github",
    ]
    targets: list[Path] = []
    for entry in scan_dirs:
        if entry.is_file():
            targets.append(entry)
        elif entry.is_dir():
            targets.extend(entry.rglob("*.md"))
            targets.extend(entry.rglob("*.py"))
    skip_substr = ("skills/index.json", "_generated", "lint_layer_designation")
    # 금지 어휘를 *prohibition* 으로 인용한 라인은 통과 (룰 본문)
    prohibition_markers = ("표현 금지", "alias 금지", "사용 금지", "쓰지 않", "안 쓴", "X —", "금지된")
    for path in targets:
        rel_str = str(path.relative_to(ROOT)).replace("\\", "/")
        if any(s in rel_str for s in skip_substr):
            continue
        text = _read(path)
        if not text:
            continue
        for phrase in forbidden_phrases:
            if phrase not in text:
                continue
            # 라인 단위로 prohibition marker 확인
            offending_lines = [
                (i, ln)
                for i, ln in enumerate(text.splitlines(), start=1)
                if phrase in ln and not any(m in ln for m in prohibition_markers)
            ]
            if not offending_lines:
                continue
            line_no = offending_lines[0][0]
            violations.append(
                f"{path.relative_to(ROOT)}:{line_no} — alias '{phrase}' 발견. "
                "'5 L2 분석엔진 + L3 조합기 (story)' 분리 명시 필요."
            )
            break


def _check_architecture_import_arrow(violations: list[str]) -> None:
    """operation/architecture.md 의 import 방향 표기에 L1.5 가 빠지면 안 됨."""
    arch = ROOT / "src" / "dartlab" / "skills" / "specs" / "operation" / "architecture.md"
    text = _read(arch)
    if not text:
        violations.append(f"{arch.relative_to(ROOT)} — 읽기 실패.")
        return
    # "L0 ← L1 ← L2 ← L3" — L1.5 빠진 옛 형식
    if "L0 ← L1 ← L2" in text and "L0 ← L1 ← L1.5" not in text:
        violations.append(
            f"{arch.relative_to(ROOT)} — import 방향 표기 'L0 ← L1 ← L2' (L1.5 누락). "
            "'L0 ← L1 ← L1.5 ← L2 ← L3' 형식 필요."
        )


def main() -> int:
    violations: list[str] = []
    _check_l2_self_label(violations)
    _check_scan_l15(violations)
    _check_industry_l2(violations)
    _check_story_l3(violations)
    _check_six_engine_phrase(violations)
    _check_architecture_import_arrow(violations)

    strict = "--strict" in sys.argv

    if not violations:
        print("[layer-designation] OK — 6 단 계층 명명 정합.")
        return 0

    print(f"[layer-designation] 위반 {len(violations)} 건:\n")
    for v in violations:
        print(f"  - {v}")
    print("\n룰 본문: src/dartlab/skills/specs/operation/architecture.md '6 단 계층 SSOT'")
    return 1 if strict else 0


if __name__ == "__main__":
    sys.exit(main())
