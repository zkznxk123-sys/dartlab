"""recipePromote — recipe lifecycle 운영자 CLI (status frontmatter 단독 권한).

`feedback_no_graph_regression.md` 준수: 자기개선 사다리 회피. 어떤 자동 도구도 status
frontmatter 를 수정하지 않는다 — 본 CLI 가 단독 권한.

서브커맨드:
- ``list [--status=<s>]`` — recipe 목록 + 현재 status + 누적 run 수 / pass rate.
- ``inspect <id>`` — 단일 recipe 의 6 신호 scorecard + drift 진단 + 최근 N run.
- ``promote <id>`` — tested → verified. scorecard 미달이면 거부. ``--force`` 우회 (운영자 책임).
- ``deprecate <id> --reason="..."`` — drift / 중복 / 폐기 사유 기록.
- ``promote-to-storyboard <id>`` — verified → storyboard 이식 가이드 (수동).

실행:
    uv run python -X utf8 src/dartlab/skills/recipePromote.py list
    uv run python -X utf8 src/dartlab/skills/recipePromote.py inspect recipes.credit.distressDual
    uv run python -X utf8 src/dartlab/skills/recipePromote.py promote recipes.credit.distressDual
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RECIPE_DIR = REPO_ROOT / "src" / "dartlab" / "skills" / "specs" / "recipes"

# 프로젝트 모듈 import 를 위해 src 를 path 추가.
sys.path.insert(0, str(REPO_ROOT / "src"))

# ── frontmatter 조작 (recipe_schema_migrate.py 와 같은 surgical line-level) ──
# `dartlab.ai.recipes` import 는 양방향 cycle (ai <-> skills) 회피를 위해
# 각 command 함수 본문 안에서 lazy import 한다.


_FRONTMATTER_DELIM = "---"


def _readSpec(path: Path) -> tuple[str, dict[str, object], str]:
    """recipe spec 을 (raw_text, frontmatter_dict, body) 로 파싱."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith(_FRONTMATTER_DELIM):
        raise ValueError(f"frontmatter 누락: {path.name}")
    parts = text.split(_FRONTMATTER_DELIM, 2)
    if len(parts) < 3:
        raise ValueError(f"frontmatter 닫힘 X: {path.name}")
    front_text = parts[1]
    body = parts[2]
    front: dict[str, object] = {}
    for line in front_text.splitlines():
        if ":" not in line or line.startswith(" "):
            continue
        key, _, value = line.partition(":")
        front[key.strip()] = value.strip().strip("'\"")
    return text, front, body


def _setStatus(path: Path, newStatus: str, *, validatedAt: str | None = None) -> None:
    """recipe spec 의 frontmatter 에서 ``status:`` 줄 교체. 다른 라인 보존.

    validatedAt 이 주어지면 ``validatedAt:`` 라인을 함께 갱신/추가.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith(_FRONTMATTER_DELIM):
        raise ValueError(f"frontmatter 누락: {path.name}")
    parts = text.split(_FRONTMATTER_DELIM, 2)
    if len(parts) < 3:
        raise ValueError(f"frontmatter 닫힘 X: {path.name}")
    front_text = parts[1]
    body = parts[2]

    # status 라인 교체.
    status_re = re.compile(r"^status\s*:.*$", re.MULTILINE)
    if status_re.search(front_text):
        front_text = status_re.sub(f"status: {newStatus}", front_text, count=1)
    else:
        front_text = front_text.rstrip("\n") + f"\nstatus: {newStatus}\n"

    if validatedAt is not None:
        validated_re = re.compile(r"^validatedAt\s*:.*$", re.MULTILINE)
        if validated_re.search(front_text):
            front_text = validated_re.sub(f"validatedAt: '{validatedAt}'", front_text, count=1)
        else:
            front_text = front_text.rstrip("\n") + f"\nvalidatedAt: '{validatedAt}'\n"

    new_text = _FRONTMATTER_DELIM + front_text + _FRONTMATTER_DELIM + body
    path.write_text(new_text, encoding="utf-8")


def _setDeprecated(path: Path, reason: str) -> None:
    text = path.read_text(encoding="utf-8")
    parts = text.split(_FRONTMATTER_DELIM, 2)
    front_text = parts[1]
    body = parts[2]

    status_re = re.compile(r"^status\s*:.*$", re.MULTILINE)
    front_text = status_re.sub("status: deprecated", front_text, count=1)
    deprecated_at = datetime.now(timezone.utc).date().isoformat()
    front_text = front_text.rstrip("\n") + (f"\ndeprecatedAt: '{deprecated_at}'\ndeprecatedReason: \"{reason}\"\n")
    new_text = _FRONTMATTER_DELIM + front_text + _FRONTMATTER_DELIM + body
    path.write_text(new_text, encoding="utf-8")


# ── recipe 메타데이터 fetch (frontmatter dict + 추가 필드) ──


def _recipeMeta(skillId: str) -> dict[str, object]:
    """recipe spec frontmatter 에서 requiredEvidence / expectedNovelty / falsifier 등 fetch."""
    try:
        from dartlab.skills import getSkill
    except ImportError:
        return {}
    try:
        spec = getSkill(skillId)
    except KeyError:
        return {}
    return {
        "requiredEvidence": list(getattr(spec, "requiredEvidence", []) or []),
        "expectedNovelty": list(getattr(spec, "expectedNovelty", []) or []),
        "falsifierPresent": bool(
            isinstance(getattr(spec, "falsifier", None), dict) and getattr(spec, "falsifier", {}).get("description")
        ),
        "status": getattr(spec, "status", "unknown"),
        "title": getattr(spec, "title", ""),
        "kind": getattr(spec, "kind", ""),
    }


def _pathFor(skillId: str) -> Path:
    parts = skillId.split(".")
    if len(parts) >= 3 and parts[0] == "recipes":
        return RECIPE_DIR.joinpath(*parts[1:-1]) / f"{parts[-1]}.md"
    slug = parts[-1] or skillId
    return RECIPE_DIR / f"{slug}.md"


def _skillIdForPath(path: Path) -> str:
    rel = path.relative_to(RECIPE_DIR)
    stem_parts = list(rel.with_suffix("").parts)
    return "recipes." + ".".join(stem_parts)


# ── 서브커맨드 ──


def cmdList(args: argparse.Namespace) -> int:
    """recipe 목록과 status·run·passRate 표 출력."""
    from dartlab.ai.recipes import loadRuns

    if not RECIPE_DIR.is_dir():
        print(f"recipe 디렉터리 없음: {RECIPE_DIR}", file=sys.stderr)
        return 1
    rows: list[tuple[str, str, int, float]] = []
    for path in sorted(RECIPE_DIR.rglob("*.md")):
        skill_id = _skillIdForPath(path)
        try:
            _, front, _ = _readSpec(path)
        except ValueError:
            continue
        status = str(front.get("status", "unknown"))
        if args.status and status != args.status:
            continue
        runs = loadRuns(skill_id)
        run_count = runs.height if runs is not None else 0
        if run_count and "ok" in runs.columns:
            pass_rate = float(runs.filter(runs["ok"]).height) / run_count
        else:
            pass_rate = 0.0
        rows.append((skill_id, status, run_count, pass_rate))

    if not rows:
        print(f"매칭 recipe 없음 (status filter: {args.status or '없음'})")
        return 0
    print(f"{'skillId':<55} {'status':<12} {'runs':>5} {'passRate':>10}")
    print("-" * 90)
    for sid, status, count, rate in rows:
        print(f"{sid:<55} {status:<12} {count:>5} {rate:>10.0%}")
    return 0


def cmdInspect(args: argparse.Namespace) -> int:
    """단일 recipe 의 scorecard·drift·최근 run 표시."""
    from dartlab.ai.recipes import computeScorecard, detectDrift, loadRuns

    skill_id = args.skillId
    path = _pathFor(skill_id)
    if not path.exists():
        print(f"recipe spec 파일 없음: {path}", file=sys.stderr)
        return 1
    meta = _recipeMeta(skill_id)
    runs = loadRuns(skill_id)

    print(f"=== {skill_id} ===")
    print(f"status: {meta.get('status', 'unknown')}")
    print(f"title: {meta.get('title', '')}")
    print(f"runs: {runs.height}")

    sc = computeScorecard(
        skill_id,
        runs,
        requiredEvidence=meta.get("requiredEvidence") or [],
        expectedNovelty=meta.get("expectedNovelty") or [],
        falsifierPresent=bool(meta.get("falsifierPresent")),
    )
    print()
    print("--- 6 신호 scorecard ---")
    print(f"executionPassRate:    {sc.executionPassRate:.2%}")
    print(f"evidenceCompleteness: {sc.evidenceCompleteness:.2%}")
    print(f"crossTargetStability: {sc.crossTargetStability:.4f}")
    print(f"novelty:              {sc.novelty}")
    print(f"falsifierEvaluated:   {sc.falsifierEvaluated}")
    print(f"meetsThresholds:      {sc.meetsThresholds}")
    if sc.notes:
        print("notes:")
        for note in sc.notes:
            print(f"  - {note}")

    if runs.height >= 10:
        drift = detectDrift(skill_id, runs)
        print()
        print("--- drift 진단 ---")
        print(f"schemaDriftRate:    {drift.schemaDriftRate:.0%}")
        print(f"insightDriftSigma:  {drift.insightDriftSigma}")
        print(f"suggestDeprecate:   {drift.suggestDeprecate}")
        if drift.notes:
            for note in drift.notes:
                print(f"  - {note}")

    if args.recent and runs.height:
        print()
        print(f"--- 최근 {args.recent} run ---")
        recent = runs.tail(args.recent)
        for row in recent.iter_rows(named=True):
            mark = "✓" if row.get("ok") else "✗"
            print(
                f"  {mark} {row.get('runId', '')[:10]} {row.get('target', ''):<10} "
                f"{row.get('headlineMetric', ''):<20} {row.get('headlineValue', '')}"
            )
    return 0


def cmdPromote(args: argparse.Namespace) -> int:
    """status 전이 — tested→verified 는 scorecard 게이트, 그 외는 --force."""
    from dartlab.ai.recipes import computeScorecard, loadRuns

    skill_id = args.skillId
    path = _pathFor(skill_id)
    if not path.exists():
        print(f"recipe spec 파일 없음: {path}", file=sys.stderr)
        return 1
    meta = _recipeMeta(skill_id)
    cur_status = str(meta.get("status", "unknown"))
    target_status = args.toStatus

    if cur_status == target_status:
        print(f"이미 {target_status} 상태 — no-op")
        return 0

    # tested → verified 만 scorecard 게이트. 나머지는 명시적 force 필요.
    if cur_status in ("unverified", "tested") and target_status == "verified":
        runs = loadRuns(skill_id)
        sc = computeScorecard(
            skill_id,
            runs,
            requiredEvidence=meta.get("requiredEvidence") or [],
            expectedNovelty=meta.get("expectedNovelty") or [],
            falsifierPresent=bool(meta.get("falsifierPresent")),
        )
        if not sc.meetsThresholds and not args.force:
            print("scorecard 미달 — verified 거부:", file=sys.stderr)
            print(f"  runs={sc.runCount}", file=sys.stderr)
            print(f"  executionPassRate={sc.executionPassRate:.2%}", file=sys.stderr)
            print(f"  evidenceCompleteness={sc.evidenceCompleteness:.2%}", file=sys.stderr)
            print(f"  crossTargetStability={sc.crossTargetStability:.4f}", file=sys.stderr)
            print(f"  novelty={sc.novelty}", file=sys.stderr)
            print(f"  falsifierEvaluated={sc.falsifierEvaluated}", file=sys.stderr)
            for note in sc.notes:
                print(f"  - {note}", file=sys.stderr)
            print("  (--force 로 운영자 책임 우회 가능)", file=sys.stderr)
            return 1
        validated_at = datetime.now(timezone.utc).date().isoformat()
        _setStatus(path, "verified", validatedAt=validated_at)
        print(f"{skill_id}: {cur_status} → verified (validatedAt={validated_at})")
        return 0

    # 그 외 전이 (drafted → unverified, verified → curated 등) — --force 필요.
    if not args.force:
        print(
            f"{cur_status} → {target_status} 전이는 일반 게이트 없음. --force 로 운영자 명시.",
            file=sys.stderr,
        )
        return 1
    _setStatus(path, target_status)
    print(f"{skill_id}: {cur_status} → {target_status} (force)")
    return 0


def cmdDeprecate(args: argparse.Namespace) -> int:
    """recipe 폐기 — drift/중복 사유 필수 기록."""
    skill_id = args.skillId
    path = _pathFor(skill_id)
    if not path.exists():
        print(f"recipe spec 파일 없음: {path}", file=sys.stderr)
        return 1
    if not args.reason:
        print("--reason 필요", file=sys.stderr)
        return 1
    _setDeprecated(path, args.reason)
    print(f"{skill_id}: deprecated (reason={args.reason})")
    return 0


def cmdPromoteToStoryboard(args: argparse.Namespace) -> int:
    """verified/curated recipe 의 storyboard 이식 수동 가이드 출력."""
    skill_id = args.skillId
    meta = _recipeMeta(skill_id)
    cur_status = str(meta.get("status", "unknown"))
    if cur_status not in ("verified", "curated"):
        print(
            f"verified / curated 상태에서만 storyboard 이식 가능 (현재 {cur_status})",
            file=sys.stderr,
        )
        return 1

    print(f"=== {skill_id} → storyboard 이식 가이드 ===")
    print()
    print("수동 단계:")
    print("1. src/dartlab/story/reportTypes.py 의 REPORT_TYPES dict 에 신규 ReportType 등록.")
    print(f"   - key: 적절한 단어 (예: '{skill_id.split('.')[-1]}')")
    print("   - sectionOrder: story/catalog.py 의 SECTIONS 에서 선택")
    print("   - emphasize: 강조 block key (선택)")
    print()
    print("2. recipe spec frontmatter 에 storyboardKey 추가:")
    print("   storyboardKey: '<선택한 키>'")
    print()
    print("3. 검증:")
    print(
        '   uv run python -X utf8 -c "import dartlab; '
        "c = dartlab.Company('005930'); "
        "s = c.story(reportType='<선택한 키>'); print(s.summaryCard)\""
    )
    print()
    print("4. tests/ai/test_ai_skill_catalog_audit.py 에 cross-link 검증 추가 후 commit.")
    return 0


# ── argparse 진입 ──


def main(argv: list[str] | None = None) -> int:
    """argparse subparser 진입점 — list/inspect/promote/deprecate/promote-to-storyboard 디스패치."""
    parser = argparse.ArgumentParser(description="recipe lifecycle 운영자 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="recipe 목록 + status + run 통계")
    p_list.add_argument("--status", help="특정 status 만 필터 (drafted/unverified/tested/verified/curated/deprecated)")
    p_list.set_defaults(func=cmdList)

    p_inspect = sub.add_parser("inspect", help="단일 recipe 의 scorecard + drift")
    p_inspect.add_argument("skillId")
    p_inspect.add_argument("--recent", type=int, default=10, help="최근 N run 표시 (기본 10)")
    p_inspect.set_defaults(func=cmdInspect)

    p_promote = sub.add_parser("promote", help="status 전이 (tested → verified 등)")
    p_promote.add_argument("skillId")
    p_promote.add_argument(
        "--to",
        dest="toStatus",
        default="verified",
        choices=["unverified", "tested", "verified", "curated"],
    )
    p_promote.add_argument("--force", action="store_true", help="scorecard 게이트 우회 (운영자 책임)")
    p_promote.set_defaults(func=cmdPromote)

    p_deprecate = sub.add_parser("deprecate", help="recipe 폐기 (drift/중복)")
    p_deprecate.add_argument("skillId")
    p_deprecate.add_argument("--reason", required=True)
    p_deprecate.set_defaults(func=cmdDeprecate)

    p_storyboard = sub.add_parser(
        "promote-to-storyboard",
        help="verified recipe → story.reportType 이식 가이드 (수동)",
    )
    p_storyboard.add_argument("skillId")
    p_storyboard.set_defaults(func=cmdPromoteToStoryboard)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
