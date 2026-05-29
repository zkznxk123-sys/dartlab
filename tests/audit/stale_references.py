"""Stale reference lint — 폐기된 API/이름이 코드에 잔존하는지 검증.

대규모 rename / API 폐기 후 일부 위치에서 옛 이름이 남는 패턴을 자동 차단.
"95% 완료 패턴" (오늘 fix 한 review→story, c.docs/c.finance 폐기 등) 재발 방지.

탐지 방식: 파일 단위 정규식 매칭 + 화이트리스트 (경로 + 라인 마커).

설정 SSOT: ``tests/audit/stalePatterns.yaml``
    - patterns: 카테고리별 정규식 + 심각도 (error/warn) + 메시지
    - whitelist: 경로 패턴 (의도된 잔존 — deprecation note, history 등)

사용법::

    uv run python -X utf8 tests/audit/stale_references.py
    uv run python -X utf8 tests/audit/stale_references.py --warn-only
    uv run python -X utf8 tests/audit/stale_references.py --pattern review_to_story

종료 코드:
    0  깨끗 (또는 --warn-only)
    1  error 심각도 위반 발견
    2  설정 파일 오류
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Windows cp949 콘솔에서 한글·em-dash 출력 시 UnicodeEncodeError. CI (Linux) 와 동일
# 동작 보장 위해 stdout/stderr 를 utf-8 로 재설정. PYTHONIOENCODING 환경변수로도 가능
# 하지만 사용자가 직접 실행할 때 잊는 사고 방지 — 스크립트 자체 방어.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML 필요 — pip install pyyaml", file=sys.stderr)
    sys.exit(2)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PATTERNS_FILE = _REPO_ROOT / "tests" / "audit" / "stalePatterns.yaml"

# 검사 대상 디렉토리 — planRealdata.py 의 INFRA_PREFIXES 와 일관
_SCAN_ROOTS: tuple[str, ...] = (
    "src/dartlab",
    "tests",
    "ops",
    "scripts",
    ".github",
    "landing/src",
    "README.md",
    "README_EN.md",
)

# 라인 단위 예외 마커 — 라인 끝에 이 주석이 있으면 해당 라인 검사 제외
_LINE_NOQA_MARKERS: tuple[str, ...] = (
    "# noqa: stale-ref",
    "# stale-ref-allow",
)


@dataclass(frozen=True)
class _Pattern:
    name: str
    regex: re.Pattern[str]
    severity: str  # "error" or "warn"
    message: str
    whitelist_paths: tuple[str, ...]  # glob 또는 substring


@dataclass(frozen=True)
class _Violation:
    path: Path
    line_no: int
    line: str
    pattern: _Pattern


def _load_patterns(path: Path) -> list[_Pattern]:
    """YAML 패턴 설정 로드. ``default_whitelist`` 가 모든 패턴에 자동 적용됨."""
    if not path.exists():
        print(f"ERROR: 패턴 설정 없음 — {path}", file=sys.stderr)
        sys.exit(2)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        print(f"ERROR: YAML 파싱 실패 — {e}", file=sys.stderr)
        sys.exit(2)

    default_whitelist = tuple(data.get("default_whitelist", []))

    patterns: list[_Pattern] = []
    for entry in data.get("patterns", []):
        try:
            per_pattern = tuple(entry.get("whitelist_paths", []))
            patterns.append(
                _Pattern(
                    name=entry["name"],
                    regex=re.compile(entry["regex"]),
                    severity=entry.get("severity", "error"),
                    message=entry.get("message", ""),
                    whitelist_paths=default_whitelist + per_pattern,
                )
            )
        except (KeyError, re.error) as e:
            print(f"ERROR: 패턴 '{entry.get('name', '?')}' 설정 오류 — {e}", file=sys.stderr)
            sys.exit(2)
    return patterns


def _is_whitelisted(path: Path, pattern: _Pattern) -> bool:
    """파일 경로가 해당 패턴의 whitelist 에 포함되는지."""
    rel = path.relative_to(_REPO_ROOT).as_posix()
    for pat in pattern.whitelist_paths:
        if pat in rel:
            return True
    return False


def _has_line_noqa(line: str) -> bool:
    """라인에 noqa 마커가 있는지."""
    return any(marker in line for marker in _LINE_NOQA_MARKERS)


def _iter_target_files(roots: tuple[str, ...]) -> list[Path]:
    """검사 대상 파일 목록. .py / .md / .yml / .yaml / .ts / .svelte / .json."""
    extensions = {".py", ".md", ".yml", ".yaml", ".ts", ".tsx", ".svelte", ".json"}
    excluded_dirs = {"__pycache__", "node_modules", ".git", "dist", "build", "_backup"}
    excluded_names = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock"}
    max_scan_bytes = 1_000_000

    try:
        result = subprocess.run(
            ["git", "ls-files", "--", *roots],
            cwd=_REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        candidates = [_REPO_ROOT / line for line in result.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.CalledProcessError):
        candidates = []
        for root_str in roots:
            root = _REPO_ROOT / root_str
            if root.is_file():
                candidates.append(root)
                continue
            if root.is_dir():
                candidates.extend(root.rglob("*"))

    files: list[Path] = []
    for path in candidates:
        if not path.is_file():
            continue
        if path.name in excluded_names:
            continue
        if path.suffix not in extensions:
            continue
        if any(part in excluded_dirs for part in path.parts):
            continue
        try:
            if path.stat().st_size > max_scan_bytes:
                continue
        except OSError:
            continue
        files.append(path)
    return files


def _scan_file(path: Path, patterns: list[_Pattern]) -> list[_Violation]:
    """한 파일을 라인 단위로 검사."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return []

    active_patterns = [pattern for pattern in patterns if not _is_whitelisted(path, pattern)]
    if not active_patterns:
        return []

    violations: list[_Violation] = []
    for line_no, line in enumerate(content.split("\n"), 1):
        if len(line) > 20_000:
            continue
        if _has_line_noqa(line):
            continue
        for pattern in active_patterns:
            if pattern.regex.search(line):
                violations.append(_Violation(path, line_no, line.rstrip(), pattern))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warn-only", action="store_true", help="error 심각도 위반도 exit 0")
    parser.add_argument("--pattern", help="특정 패턴 이름만 검사")
    parser.add_argument("--patterns-file", default=str(_PATTERNS_FILE), help="YAML 설정 경로")
    args = parser.parse_args()

    patterns = _load_patterns(Path(args.patterns_file))
    if args.pattern:
        patterns = [p for p in patterns if p.name == args.pattern]
        if not patterns:
            print(f"ERROR: 패턴 '{args.pattern}' 없음", file=sys.stderr)
            return 2

    files = _iter_target_files(_SCAN_ROOTS)
    print(f"검사: {len(files)} 파일, {len(patterns)} 패턴")

    all_violations: list[_Violation] = []
    for path in files:
        all_violations.extend(_scan_file(path, patterns))

    if not all_violations:
        print("✓ 깨끗 — 잔존 0건")
        return 0

    # 카테고리별 그룹
    by_pattern: dict[str, list[_Violation]] = {}
    for v in all_violations:
        by_pattern.setdefault(v.pattern.name, []).append(v)

    error_count = 0
    warn_count = 0
    for name, group in sorted(by_pattern.items()):
        sev = group[0].pattern.severity
        msg = group[0].pattern.message
        marker = "ERROR" if sev == "error" else "WARN"
        print(f"\n[{marker}] {name} — {msg} ({len(group)} 건)")
        for v in group:
            rel = v.path.relative_to(_REPO_ROOT).as_posix()
            print(f"  {rel}:{v.line_no}: {v.line.strip()}")
        if sev == "error":
            error_count += len(group)
        else:
            warn_count += len(group)

    print(f"\n총 {error_count} 에러 / {warn_count} 경고")

    if error_count > 0 and not args.warn_only:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
