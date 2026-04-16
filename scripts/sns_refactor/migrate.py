"""sns → sns 경로 리팩토링 마이그레이션.

sns/ 디렉토리가 생성된 후(sns → sns rename 완료 후) 실행.
sns/ 및 관련 외부 문서·메모리 파일의 "sns" 문자열 리터럴을 "sns"로 치환한다.

사용:
    python scripts/sns_refactor/migrate.py --scan          # 치환 예정 건수만 리포트
    python scripts/sns_refactor/migrate.py --dry-run       # 각 파일 변경 예정 라인 출력
    python scripts/sns_refactor/migrate.py --apply         # 실제 쓰기 (.bak 백업 생성)
    python scripts/sns_refactor/migrate.py --validate      # py_compile + json.load 검증
    python scripts/sns_refactor/migrate.py --cleanup       # .bak 삭제 (확인 프롬프트)

주의:
- git mv 사용 안 함 (gitignored 파일). 단순 OS mv 전제.
- .bak 파일은 원본 옆에 생성. --cleanup 으로 일괄 삭제.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = "sns"
NEW = "sns"

# 치환 대상 확장자
TEXT_EXTS = {".py", ".md", ".json", ".ts", ".tsx", ".js", ".sh", ".yml", ".yaml", ".txt"}

# 치환 대상 디렉토리 (sns가 이미 rename 됐다는 전제)
TARGET_DIRS = [
    ROOT / "sns",
    ROOT / "blog",  # BLOG.md, TOPIC_ROADMAP.md 등
    ROOT / ".claude",
    ROOT / "scripts",
]
# 루트의 특정 파일
TARGET_ROOT_FILES = [
    ROOT / "CLAUDE.md",
    ROOT / "AGENTS.md",
]
# 메모리 파일 (절대경로)
MEMORY_DIR = Path.home() / ".claude/projects/c--Users-MSI-OneDrive-Desktop-sideProject-dartlab/memory"


def collectFiles() -> list[Path]:
    files: list[Path] = []
    for d in TARGET_DIRS:
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if p.is_file() and p.suffix in TEXT_EXTS:
                # node_modules 등 제외
                if any(part in {"node_modules", "__pycache__", ".svelte-kit", "build", ".git"} for part in p.parts):
                    continue
                files.append(p)
    for f in TARGET_ROOT_FILES:
        if f.exists():
            files.append(f)
    if MEMORY_DIR.exists():
        for p in MEMORY_DIR.rglob("*"):
            if p.is_file() and p.suffix in TEXT_EXTS:
                files.append(p)
    return files


def countMatches(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return 0
    return text.count(OLD)


def replaceFile(path: Path, apply: bool) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return 0
    if OLD not in text:
        return 0
    new = text.replace(OLD, NEW)
    count = text.count(OLD)
    if apply:
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)
        path.write_text(new, encoding="utf-8")
    return count


def diffPreview(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    for i, line in enumerate(text.splitlines(), 1):
        if OLD in line:
            newLine = line.replace(OLD, NEW)
            print(f"  {path.relative_to(ROOT) if ROOT in path.parents else path}:{i}")
            print(f"    - {line}")
            print(f"    + {newLine}")


def scan() -> None:
    files = collectFiles()
    total = 0
    perFile: list[tuple[Path, int]] = []
    for f in files:
        n = countMatches(f)
        if n > 0:
            perFile.append((f, n))
            total += n
    perFile.sort(key=lambda x: -x[1])
    print(f"치환 대상: {len(perFile)}개 파일, {total}건")
    for f, n in perFile[:20]:
        print(f"  {n:4d}  {f}")
    if len(perFile) > 20:
        print(f"  ... +{len(perFile) - 20} more")


def dryRun() -> None:
    files = collectFiles()
    for f in files:
        if countMatches(f) > 0:
            diffPreview(f)


def apply() -> None:
    files = collectFiles()
    changed = 0
    total = 0
    for f in files:
        n = replaceFile(f, apply=True)
        if n > 0:
            changed += 1
            total += n
            print(f"  ✓ {f.relative_to(ROOT) if ROOT in f.parents else f}  ({n})")
    print(f"완료: {changed}개 파일, {total}건 치환, .bak 백업 생성")


def validate() -> None:
    files = collectFiles()
    pyFiles = [f for f in files if f.suffix == ".py"]
    jsonFiles = [f for f in files if f.suffix == ".json"]
    errors = []
    for f in pyFiles:
        result = subprocess.run([sys.executable, "-m", "py_compile", str(f)], capture_output=True)
        if result.returncode != 0:
            errors.append((f, result.stderr.decode()))
    for f in jsonFiles:
        try:
            json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append((f, str(e)))
    if errors:
        print(f"검증 실패: {len(errors)}개")
        for f, err in errors:
            print(f"  ✗ {f}: {err[:200]}")
        sys.exit(1)
    print(f"검증 통과: Python {len(pyFiles)}개, JSON {len(jsonFiles)}개")


def cleanup() -> None:
    bakFiles = []
    for d in TARGET_DIRS + [MEMORY_DIR]:
        if d.exists():
            bakFiles.extend(d.rglob("*.bak"))
    for f in TARGET_ROOT_FILES:
        bak = f.with_suffix(f.suffix + ".bak")
        if bak.exists():
            bakFiles.append(bak)
    if not bakFiles:
        print("삭제할 .bak 없음")
        return
    print(f".bak 파일 {len(bakFiles)}개 발견")
    answer = input("삭제할까요? (y/N): ")
    if answer.lower() == "y":
        for f in bakFiles:
            f.unlink()
        print(f"{len(bakFiles)}개 삭제 완료")
    else:
        print("취소")


def main() -> None:
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--scan", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--validate", action="store_true")
    g.add_argument("--cleanup", action="store_true")
    args = p.parse_args()

    if args.scan:
        scan()
    elif args.dry_run:
        dryRun()
    elif args.apply:
        apply()
    elif args.validate:
        validate()
    elif args.cleanup:
        cleanup()


if __name__ == "__main__":
    main()
