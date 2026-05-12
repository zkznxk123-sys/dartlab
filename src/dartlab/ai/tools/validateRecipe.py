"""ValidateRecipe — recipe 1 건을 testUniverse 종목들에 직렬 실행 후 scorecard 반환.

`feedback_no_graph_regression.md` 준수: stateless tool. BRIEF/WORK/CRITIQUE/COMPOSE/GATE/HARVEST
phase chain 없음. 단순 흐름:

1. getSkillBody(skillId) → frontmatter + body
2. body 의 ``## 공개 호출 방식`` python 블록 추출
3. 각 target 별 placeholder 치환 → runPython 실행
4. validateRefs(refs, requiredEvidence) → present/missing
5. RecipeRunRecord 생성 → appendRun (~/.dartlab/recipeRuns/<skill>.parquet)
6. 모든 target 종료 후 computeScorecard 로 6 신호 산출

자기개선 사다리 회피 — status frontmatter 자동 변경 X. 본 도구는 *append-only* run 기록만.
승격은 운영자 CLI (`scripts/dev/recipe_promote.py promote <id>`).

CLAUDE.md 메모리 규칙: maxTargets=5 강제 (Polars Rust heap, Company 1 개 ≈ 200~500MB, gc 미회수).
"""

from __future__ import annotations

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from dartlab.ai.contracts import Ref
from dartlab.ai.recipes import (
    RecipeRunRecord,
    appendRun,
    computeScorecard,
    validateRefs,
)

from .readSkill import getSkillBody
from .runPython import runPython
from .types import ToolResult

_PUBLIC_CALL_HEADER = "## 공개 호출 방식"
_PYTHON_BLOCK_RE = re.compile(r"```python\n(.*?)```", re.DOTALL)
_HARD_CAP_TARGETS = 5


def _extractPublicCallSection(body: str) -> str:
    idx = body.find(_PUBLIC_CALL_HEADER)
    if idx < 0:
        return ""
    section = body[idx + len(_PUBLIC_CALL_HEADER) :]
    next_h2 = section.find("\n## ")
    return section if next_h2 < 0 else section[:next_h2]


def _firstPythonBlock(body: str) -> str | None:
    section = _extractPublicCallSection(body)
    if not section:
        return None
    matches = _PYTHON_BLOCK_RE.findall(section)
    return matches[0] if matches else None


_DEFAULT_TARGET_PLACEHOLDERS = ('"005930"', "'005930'")


def _substituteTarget(code: str, target: str) -> str:
    """템플릿 placeholder (default 005930) 를 실제 target stockCode 로 치환.

    프로토타입: 첫 wave 에서는 레시피 본문이 ``Company("005930")`` 형태로 작성됐다는 가정.
    target 이 005930 와 다를 때만 단순 문자열 치환. 향후 jinja-like placeholder 도입 가능.
    """
    if not target or target == "005930":
        return code
    out = code
    for placeholder in _DEFAULT_TARGET_PLACEHOLDERS:
        out = out.replace(placeholder, f'"{target}"')
    return out


def _refsToIdList(refs: list[Ref]) -> list[str]:
    out: list[str] = []
    for ref in refs:
        if isinstance(ref, Ref):
            out.append(ref.id)
        elif isinstance(ref, dict):
            refId = ref.get("id")
            if isinstance(refId, str):
                out.append(refId)
    return out


def _evidenceKindsFromRefs(refs: list[Ref]) -> list[str]:
    kinds: set[str] = set()
    for ref in refs:
        if isinstance(ref, Ref) and ref.kind:
            kinds.add(ref.kind)
        elif isinstance(ref, dict):
            kind = ref.get("kind")
            if isinstance(kind, str) and kind:
                kinds.add(kind)
    return sorted(kinds)


def _headlineFromEmitted(emitted: dict[str, Any]) -> tuple[str, str]:
    """emit_result payload 에서 headline metric 이름 + 값 추출.

    우선순위: ``emitted["headline"]`` (명시) > ``values`` 의 첫 항목 > ``table`` 첫 row 의 첫 컬럼.
    """
    if not isinstance(emitted, dict):
        return "", ""
    if isinstance(emitted.get("headline"), dict):
        head = emitted["headline"]
        name = str(head.get("metric") or "headline")
        value = head.get("value")
        return name, "" if value is None else str(value)
    values = emitted.get("values")
    if isinstance(values, dict) and values:
        key = next(iter(values))
        return str(key), str(values[key])
    table = emitted.get("table")
    if isinstance(table, list) and table:
        first = table[0]
        if isinstance(first, dict) and first:
            key = next(iter(first))
            return str(key), str(first[key])
    return "", ""


def _resolveTargets(spec: dict[str, Any], explicit: list[str] | None) -> list[str]:
    if explicit:
        return list(explicit)[:_HARD_CAP_TARGETS]
    test_universe = spec.get("testUniverse") or {}
    if isinstance(test_universe, dict):
        codes = test_universe.get("stockCodes")
        if isinstance(codes, list) and codes:
            return [str(c) for c in codes][:_HARD_CAP_TARGETS]
    return ["005930"]


def validateRecipe(
    skillId: str,
    targets: list[str] | None = None,
    *,
    asOf: str | None = None,
    maxTargets: int = _HARD_CAP_TARGETS,
    capture: bool = True,
) -> ToolResult:
    """recipe 1 건의 testUniverse target 들에 직렬 실행 + scorecard.

    Parameters
    ----------
    skillId : str
        ``recipes.<category>.<slug>``.
    targets : list[str], optional
        실행 대상 stockCode 목록. 미지정시 spec 의 ``testUniverse.stockCodes`` 또는 005930 fallback.
    asOf : str, optional
        실행 시점 (ISO yyyy-mm-dd). 본 도구가 LookAheadGuard 를 직접 강제하진 않음 — recipe
        본문이 자체적으로 freq/asOf 처리 (1 차 wave). 추후 LookAheadGuard 통합.
    maxTargets : int
        target 상한 (CLAUDE.md 메모리 규칙: ≤ 5 강제). 5 초과 입력은 절단.
    capture : bool
        ``True`` 면 ``~/.dartlab/recipeRuns/`` 에 run 기록 append.

    Returns
    -------
    ToolResult
        ok=True 면 ``data``: ``{scorecard, runs: [...], runIds, missingEvidence}``.

    Notes
    -----
    chat-native — graph node X. AI 가 자율 호출하거나 운영자 CLI 가 호출.
    """
    skill_id = (skillId or "").strip()
    if not skill_id:
        return ToolResult(False, "skillId 가 비어있다", error="missing_skill_id")

    body_result = getSkillBody(skill_id)
    if not body_result.ok:
        return ToolResult(
            False,
            f"skill 본문 조회 실패: {body_result.summary}",
            error="skill_not_found",
        )
    spec = body_result.data or {}
    body = str(spec.get("body") or "")
    if not body:
        return ToolResult(
            False,
            f"recipe {skill_id} body 가 비어있다",
            error="empty_body",
        )

    code = _firstPythonBlock(body)
    if not code:
        return ToolResult(
            False,
            f"recipe {skill_id} '## 공개 호출 방식' 안에 python 블록 없음",
            error="missing_python_block",
        )

    required_evidence = list(spec.get("requiredEvidence") or [])
    expected_novelty = list(spec.get("expectedNovelty") or [])
    falsifier_present = bool(isinstance(spec.get("falsifier"), dict) and spec.get("falsifier", {}).get("description"))

    cap = max(1, min(maxTargets, _HARD_CAP_TARGETS))
    target_list = _resolveTargets(spec, targets)[:cap]
    market = "KR"  # 첫 wave default. testUniverse.market 추후 인식.

    runs_summary: list[dict[str, Any]] = []
    run_ids: list[str] = []
    missing_evidence_overall: set[str] = set()

    for target in target_list:
        runId = uuid.uuid4().hex[:12]
        run_ids.append(runId)
        substituted = _substituteTarget(code, target)
        start = time.monotonic()
        rp_result = runPython(substituted, runId=runId)
        duration_ms = int((time.monotonic() - start) * 1000)

        emitted = (rp_result.data or {}).get("result") or {}
        evidence_kinds = _evidenceKindsFromRefs(rp_result.refs or [])
        ref_ids = _refsToIdList(rp_result.refs or [])

        validation = validateRefs(rp_result.refs or [], required_evidence)
        missing_evidence_overall.update(validation.missing)

        ok = bool(rp_result.ok and validation.ok)
        error_class = None
        if not rp_result.ok:
            error_class = (rp_result.data or {}).get("errorClass") or "execution_failed"
        elif not validation.ok:
            error_class = f"missing_evidence:{','.join(validation.missing)}"

        headline_metric, headline_value = _headlineFromEmitted(emitted)

        record = RecipeRunRecord(
            runId=runId,
            skillId=skill_id,
            target=str(target),
            market=market,
            ok=ok,
            evidenceKinds=evidence_kinds,
            headlineMetric=headline_metric,
            headlineValue=headline_value,
            durationMs=duration_ms,
            refs=ref_ids,
            errorClass=error_class,
            asOf=asOf,
            capturedAt=datetime.now(timezone.utc).isoformat(),
        )
        if capture:
            appendRun(record)

        runs_summary.append(
            {
                "runId": runId,
                "target": str(target),
                "ok": ok,
                "evidenceKinds": evidence_kinds,
                "missing": validation.missing,
                "headlineMetric": headline_metric,
                "headlineValue": headline_value,
                "durationMs": duration_ms,
                "errorClass": error_class,
            }
        )

    # scorecard — 누적 run (capture=True 면 디스크에서 다시 읽기 = 정합) / 단일 호출 inline 도 OK.
    if capture:
        from dartlab.ai.recipes import loadRuns

        sc = computeScorecard(
            skill_id,
            loadRuns(skill_id),
            requiredEvidence=required_evidence,
            expectedNovelty=expected_novelty,
            falsifierPresent=falsifier_present,
        )
    else:
        # capture=False — 디스크 기록 없이 inline DataFrame 으로 scorecard 산출.
        import polars as pl

        from dartlab.ai.recipes.runs import _SCHEMA  # 내부 schema 참조 (single source).

        records = [
            {
                "runId": s["runId"],
                "skillId": skill_id,
                "asOf": asOf or "",
                "target": s["target"],
                "market": market,
                "ok": s["ok"],
                "evidenceKinds": s["evidenceKinds"],
                "headlineMetric": s["headlineMetric"],
                "headlineValue": s["headlineValue"],
                "durationMs": s["durationMs"],
                "refs": [],
                "errorClass": s["errorClass"] or "",
                "capturedAt": datetime.now(timezone.utc).isoformat(),
            }
            for s in runs_summary
        ]
        df = pl.DataFrame(records, schema=_SCHEMA) if records else pl.DataFrame(schema=_SCHEMA)
        sc = computeScorecard(
            skill_id,
            df,
            requiredEvidence=required_evidence,
            expectedNovelty=expected_novelty,
            falsifierPresent=falsifier_present,
        )

    summary_text = (
        f"validateRecipe {skill_id}: {len(target_list)} target × passRate "
        f"{sc.executionPassRate:.0%} · scorecard.meets={sc.meetsThresholds}"
    )

    return ToolResult(
        True,
        summary_text,
        refs=[],
        data={
            "skillId": skill_id,
            "scorecard": sc.toDict(),
            "runs": runs_summary,
            "runIds": run_ids,
            "missingEvidence": sorted(missing_evidence_overall),
            "targetCount": len(target_list),
            "capture": capture,
        },
    )


__all__ = ["validateRecipe"]
