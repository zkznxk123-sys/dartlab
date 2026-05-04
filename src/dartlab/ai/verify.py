"""Deterministic verification for Ask Workbench answer release.

Hardcoding rule: verifier code must not contain question-, company-, market-,
dataset-, engine-, or skill-specific gates.  It may only check general release
contracts such as supported numbers, dates, tables, visuals, execution success,
and disclosed limits.
"""

from __future__ import annotations

import re
from typing import Any

from .contracts import AnswerDraft, Ref, VerificationResult, WorkbenchTask

_DATE_LIKE = re.compile(r"\b20\d{2}[-./]?\d{2}[-./]?\d{2}\b|\b20\d{6}\b")
_NUMBER_LIKE = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:,\d{3})*(?:\.\d+)?%?")
_PERCENT_LIKE = re.compile(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?%")
_EXECUTION_SUCCESS_LIKE = re.compile(
    r"(실행|계산|조회|분석|수집).{0,12}(성공|완료|했다|했습니다)|successfully|succeeded", re.IGNORECASE
)
_MARKDOWN_TABLE_LIKE = re.compile(r"(?m)^\s*\|.+\|\s*$\n^\s*\|(?:\s*:?-{3,}:?\s*\|)+\s*$")
_RANKING_RESULT_MARKERS = (
    "상위",
    "후보",
    "랭킹",
    "ranking",
    "ranked",
    "candidate",
    "candidates",
    "top ",
)
_SCREENING_ENTITY_MARKERS = (
    "회사",
    "기업",
    "종목",
    "티커",
    "ticker",
    "company",
    "corp",
    "stock",
)
_SCREENING_METRIC_MARKERS = (
    "성장률",
    "수익률",
    "증가율",
    "등락률",
    "매출",
    "이익",
    "metric",
    "rate",
    "growth",
    "return",
    "%",
)


def verify_answer(task: WorkbenchTask, refs: list[Ref], draft: AnswerDraft) -> VerificationResult:
    """최종 답변 검산 — 질문 유형이 아니라 답변 claim 과 ref 만 대조.

    Description
    -----------
    Ask Workbench Kernel 의 release gate 다. 이 함수는 질문을 분류하지 않는다.
    최종 답변이 실제로 말한 숫자·날짜·시각화·실행 성공 주장이 세션 ref 로
    뒷받침되는지만 검사한다.

    Parameters
    ----------
    task : WorkbenchTask
        호환용 세션 task. 질문 텍스트는 검증 판단에 사용하지 않는다.
    refs : list[Ref]
        세션 중 생성된 근거 ref 목록.
    draft : AnswerDraft
        LLM 이 제출한 최종 답변 초안.

    Returns
    -------
    VerificationResult
        ok : bool — release 가능 여부
        issues : list[dict] — 위반 목록
        passed_checks : list[str] — 통과한 검산 항목

    Raises
    ------
    없음
        검증 실패는 예외가 아니라 issues 로 반환한다.

    Examples
    --------
    >>> verify_answer(task, refs, draft).ok
    True

    Notes
    -----
    질문 단어 기반 실행 요구는 금지한다. 숫자를 말하면 숫자 근거를,
    날짜를 말하면 날짜 근거를 요구한다. 검증기는 질문 intent 를 맞히거나
    특정 엔진/시장/종목을 판별하지 않는다. 공통 release 계약만 검사한다.

    Guide
    -----
    새 검증 규칙은 답변 claim 에서 시작해야 한다. 질문 intent 를 맞히는
    planner 로 확장하지 않는다.

    See Also
    --------
    runAsk : provider loop 와 release 를 수행하는 kernel 진입점.
    """

    issues: list[dict[str, Any]] = []
    passed: list[str] = []
    kinds = {ref.kind for ref in refs}
    executions = [ref for ref in refs if ref.kind == "execution"]
    failed_executions = [ref for ref in executions if not ref.payload.get("ok")]
    successful_executions = [ref for ref in executions if ref.payload.get("ok")]

    if task.release_policy.get("skillRefsRequired") and _non_trivial_answer(draft.answer) and "skill" not in kinds:
        issues.append(
            {
                "code": "missing_skill_ref",
                "message": "non-trivial Ask Workbench answers must cite at least one selected DartLab skill ref",
            }
        )
    else:
        passed.append("skill_ref_present_or_not_required")

    if _looks_like_tool_transcript(draft.answer):
        issues.append(
            {"code": "tool_transcript_released", "message": "tool call transcript is not a user-facing answer"}
        )
    else:
        passed.append("no_tool_transcript_leak")

    if _claims_execution_success(draft.answer):
        if not successful_executions:
            issues.append(
                {
                    "code": "unsupported_execution_success",
                    "message": "execution success claim needs a successful execution ref",
                }
            )
        else:
            passed.append("execution_success_supported")
    else:
        passed.append("no_execution_success_claim")

    if failed_executions and not successful_executions and _hides_failed_execution(draft.answer, draft.limits):
        issues.append(
            {
                "code": "failed_execution_hidden",
                "message": "failed execution exists but answer does not disclose the limitation",
            }
        )
    elif failed_executions and successful_executions and _releases_superseded_failed_attempt(draft.answer):
        issues.append(
            {
                "code": "superseded_failed_attempt_released",
                "message": "superseded failed tool attempts belong in evidence, not the final answer",
            }
        )
    else:
        passed.append("failed_execution_not_hidden")

    if _claims_dataset_unavailable(draft.answer) and _has_available_dataset_ref(refs):
        issues.append(
            {
                "code": "dataset_availability_conflict",
                "message": "answer claims datasets are unavailable while dataset refs exist",
            }
        )
    else:
        passed.append("dataset_availability_consistent")

    if _has_visual_language(draft.answer) or draft.visual_refs:
        visuals = [ref for ref in refs if ref.kind == "visual"]
        if not visuals:
            issues.append({"code": "missing_visual", "message": "visual claim needs visual evidence"})
        elif any(_is_single_value_visual(ref) for ref in visuals):
            issues.append({"code": "single_value_visual", "message": "single-value chart is not valid visual evidence"})
        elif any(_unsupported_visual(ref, refs) for ref in visuals):
            issues.append(
                {"code": "unsupported_visual", "message": "visual must be linked to a table or execution ref"}
            )
        else:
            passed.append("visual_valid")

    table_issue = _invalid_table_issue(refs, draft)
    if table_issue:
        issues.append(table_issue)
    else:
        passed.append("table_values_valid")

    date_consistency_issue = _date_consistency_issue(refs, draft)
    if date_consistency_issue:
        issues.append(date_consistency_issue)
    else:
        passed.append("table_dates_consistent")

    unsupported_numbers = _unsupported_numeric_claims(refs, draft) if _has_material_numbers(draft.answer) else []
    if unsupported_numbers:
        issues.append(
            {
                "code": "unsupported_numeric_claim",
                "message": "numeric prose needs matching value/table evidence",
                "values": unsupported_numbers[:8],
            }
        )
    else:
        passed.append("numeric_claims_supported")

    outlier = _implausible_percentage_claim(draft.answer, draft.limits)
    if outlier:
        issues.append(
            {
                "code": "implausible_percentage_claim",
                "message": f"percentage claim is implausibly large without outlier disclosure: {outlier}",
            }
        )
    else:
        passed.append("percentage_outliers_checked")

    if _DATE_LIKE.search(draft.answer) and not ({"date", "dataset"} & kinds):
        issues.append({"code": "unsupported_date_claim", "message": "date claim needs a date ref"})
    else:
        passed.append("date_claims_supported")

    screening_issues = _screening_contract_issues(refs, draft)
    if screening_issues:
        issues.extend(screening_issues)
    else:
        passed.append("screening_output_contract_checked")

    return VerificationResult(ok=not issues, issues=issues, passed_checks=passed)


def _non_trivial_answer(answer: str) -> bool:
    text = answer.strip()
    if not text:
        return False
    if len(text) >= 80:
        return True
    markers = ("분석", "계산", "검산", "규칙", "사용", "데이터", "엔진", "skill", "스킬")
    return any(marker in text.lower() for marker in markers)


def _screening_contract_issues(refs: list[Ref], draft: AnswerDraft) -> list[dict[str, Any]]:
    if not _claims_ranked_candidate_result(draft.answer):
        return []
    scoped_refs = _linked_refs(refs, _evidence_scope(refs, draft))
    if not scoped_refs:
        scoped_refs = refs
    kinds = {ref.kind for ref in scoped_refs}
    issues: list[dict[str, Any]] = []
    if "execution" not in kinds or not any(ref.kind == "execution" and ref.payload.get("ok") for ref in scoped_refs):
        issues.append(
            {
                "code": "missing_screening_execution_ref",
                "message": "ranked candidate answers need a successful execution ref",
            }
        )
    if "table" not in kinds:
        issues.append({"code": "missing_screening_table_ref", "message": "ranked candidate answers need a table ref"})
    if not ({"dataset", "date"} & kinds):
        issues.append(
            {
                "code": "missing_screening_basis_ref",
                "message": "ranked candidate answers need a dataset or date ref for universe/as-of basis",
            }
        )
    if not _has_markdown_table(draft.answer):
        issues.append(
            {
                "code": "missing_answer_evidence_table",
                "message": "ranked candidate answers must include a markdown evidence table in the final answer",
            }
        )
    elif not _answer_table_has_screening_columns(draft.answer):
        issues.append(
            {
                "code": "incomplete_answer_evidence_table",
                "message": "answer evidence table needs entity, period/basis, and metric columns",
            }
        )
    if not _has_screening_contract_text(draft.answer):
        issues.append(
            {
                "code": "incomplete_answer_contract",
                "message": "ranked candidate answers must disclose input/universe, filters, formula/metric, and output",
            }
        )
    return issues


def _claims_ranked_candidate_result(answer: str) -> bool:
    lowered = answer.lower()
    if not any(marker in lowered for marker in _RANKING_RESULT_MARKERS):
        return False
    if not any(marker in lowered for marker in _SCREENING_METRIC_MARKERS):
        return False
    return _has_material_numbers(answer) or bool(_MARKDOWN_TABLE_LIKE.search(answer))


def _has_markdown_table(answer: str) -> bool:
    return bool(_MARKDOWN_TABLE_LIKE.search(answer))


def _answer_table_has_screening_columns(answer: str) -> bool:
    lines = answer.splitlines()
    for idx, line in enumerate(lines[:-1]):
        if not line.strip().startswith("|"):
            continue
        if not re.match(r"^\s*\|(?:\s*:?-{3,}:?\s*\|)+\s*$", lines[idx + 1]):
            continue
        header = line.lower()
        has_entity = any(marker in header for marker in _SCREENING_ENTITY_MARKERS)
        has_metric = any(marker in header for marker in _SCREENING_METRIC_MARKERS)
        has_basis = any(
            marker in header
            for marker in (
                "기준",
                "기간",
                "시작",
                "종료",
                "연도",
                "base",
                "current",
                "period",
                "asof",
                "as_of",
                "fy",
                "year",
                "20",
            )
        )
        if has_entity and has_metric and has_basis:
            return True
    return False


def _has_screening_contract_text(answer: str) -> bool:
    lowered = answer.lower()
    groups = (
        ("입력", "input", "유니버스", "universe", "대상"),
        ("필터", "filter", "조건", "제외"),
        ("계산식", "formula", "metric", "지표", "산식"),
        ("결과", "output", "출력", "산출물"),
    )
    return all(any(marker in lowered for marker in group) for group in groups)


def verification_to_ref(result: VerificationResult) -> Ref:
    from .contracts import Ref, new_id

    return Ref(id=new_id("verify"), kind="verify", source="verify_answer", payload=result.to_dict())


def _has_material_numbers(answer: str) -> bool:
    without_dates = _DATE_LIKE.sub("", _strip_non_claim_numbers(answer))
    tokens = [m.group(0) for m in _NUMBER_LIKE.finditer(without_dates)]
    return any(len(token.strip("%").replace(",", "").replace(".", "")) >= 2 for token in tokens)


def _implausible_percentage_claim(answer: str, limits: list[str]) -> str | None:
    for match in _PERCENT_LIKE.finditer(answer):
        raw = match.group(0).strip("%").replace(",", "")
        try:
            value = abs(float(raw))
        except ValueError:
            continue
        if value > 1000:
            return match.group(0)
    return None


def _looks_like_tool_transcript(answer: str) -> bool:
    text = answer.strip().lower()
    markers = (
        "[tool_calls]",
        "tool_calls",
        "args={",
        "call_id=",
        '"code":',
        "'code':",
    )
    return any(marker in text for marker in markers)


def _releases_superseded_failed_attempt(answer: str) -> bool:
    text = answer.lower()
    failure_markers = ("실패", "오류", "에러", "failed", "error")
    tool_markers = ("c.show(", "run_python", "traceback", "exception", "도구", "tool")
    return any(marker in text for marker in failure_markers) and any(marker in text for marker in tool_markers)


def _numeric_claims_supported(refs: list[Ref], draft: AnswerDraft) -> bool:
    return not _unsupported_numeric_claims(refs, draft)


def _unsupported_numeric_claims(refs: list[Ref], draft: AnswerDraft) -> list[float]:
    evidence_scope = _evidence_scope(refs, draft)
    numeric_values = _numeric_values_from_refs(evidence_scope)
    for limit in draft.limits:
        _append_payload_numbers(numeric_values, limit)
    answer_numbers = _numbers_from_answer(draft.answer)
    if not numeric_values and answer_numbers:
        numeric_values = _numeric_values_from_refs(_fallback_numeric_refs(refs, draft))
        for limit in draft.limits:
            _append_payload_numbers(numeric_values, limit)
    if not numeric_values:
        return answer_numbers
    unsupported = [number for number in answer_numbers if not _number_in_values(number, numeric_values)]
    if unsupported:
        fallback_values = _numeric_values_from_refs(_fallback_numeric_refs(refs, draft))
        for limit in draft.limits:
            _append_payload_numbers(fallback_values, limit)
        unsupported = [number for number in answer_numbers if not _number_in_values(number, fallback_values)]
        if unsupported:
            return unsupported
    for claim in draft.material_claims:
        value = claim.get("value")
        if value is None:
            continue
        try:
            numeric = float(str(value).replace(",", "").strip("%"))
        except ValueError:
            continue
        claim_refs = claim.get("refIds") or claim.get("refs") or claim.get("evidenceRefs") or []
        scoped = [ref for ref in refs if ref.id in set(claim_refs)] if claim_refs else evidence_scope
        scoped_values = _numeric_values_from_refs(scoped)
        if not _number_in_values(numeric, scoped_values) and not _number_in_values(
            numeric, _numeric_values_from_refs(_fallback_numeric_refs(refs, draft))
        ):
            return [numeric]
    return []


def _evidence_scope(refs: list[Ref], draft: AnswerDraft) -> list[Ref]:
    ref_ids = set(draft.evidence_refs or [])
    if not ref_ids:
        return refs
    scoped = [ref for ref in refs if ref.id in ref_ids]
    return scoped or refs


def _numbers_from_answer(answer: str) -> list[float]:
    without_dates = _DATE_LIKE.sub("", _strip_non_claim_numbers(answer))
    out: list[float] = []
    for match in _NUMBER_LIKE.finditer(without_dates):
        raw = match.group(0).strip("%").replace(",", "")
        if len(raw.replace(".", "").replace("-", "").replace("+", "")) < 2:
            continue
        try:
            numeric = float(raw)
        except ValueError:
            continue
        out.append(_scale_number_by_korean_unit(numeric, without_dates[match.end() : match.end() + 3]))
    return out


def _strip_non_claim_numbers(answer: str) -> str:
    text = re.sub(r"```.*?```", " codeblock ", answer, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]+`", " inlinecode ", text)
    text = _DATE_LIKE.sub(" date ", text)
    text = re.sub(r"(?m)^\s*\d+[\.)]\s+", " item ", text)
    text = re.sub(r"(?im)^(\|\s*)\d+(\s*\|)", r"\1rank\2", text)
    text = re.sub(r"(?m)(\|\s*)\d{5,6}(\s*\|)", r"\1identifier\2", text)
    text = re.sub(r"(?i)\btop\s*\d+\b", "top count", text)
    text = re.sub(r"(상위|하위).{0,8}?\d+\s*(?:개|곳|종목|회사|기업|위)?", r"\1 count", text)
    text = re.sub(r"(상위|하위)\s*\d+\s*(?:개|곳|종목|회사|위)?", r"\1 count", text)
    text = re.sub(r"\d+\s*(?:개|곳)\s*(?:후보|종목|회사)", "count candidate", text)
    text = re.sub(r"\b20\d{2}\s*(?:년|연도|fy)?\s*(?:[→~\-/]\s*20\d{2}\s*(?:년|연도|fy)?)?", "period", text)
    text = re.sub(r"\d+\s*(?:분기|개월|월|일|년|개년)", "period", text)
    text = re.sub(r"(?i)\b(?:q[1-4]|[1-4]q)\b", "period", text)
    text = re.sub(r"\d+(?:,\d{3})*(?:\.\d+)?\s*(?:조원|억원|만원|원)\s*(?:이상|초과|미만|이하)\w*", "filter", text)
    text = re.sub(r"(?i)([×x*]\s*)100\b", r"\1formula", text)
    text = re.sub(r"(?i)\b[a-z_][a-z0-9_]*[a-z_][a-z0-9_]*\b", "identifier", text)
    return text


def _numeric_values_from_refs(refs: list[Ref]) -> list[float]:
    values: list[float] = []
    for ref in refs:
        payload = ref.payload
        if ref.kind == "value":
            _append_numeric(values, payload.get("value"))
        elif ref.kind == "table":
            rows = payload.get("rows")
            if isinstance(rows, list):
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    for value in row.values():
                        _append_numeric(values, value)
        elif ref.kind == "execution":
            _append_execution_payload_numbers(values, payload)
        elif ref.kind in {"doc", "tool", "capability", "skill", "knowledge", "dataset", "visual"}:
            _append_payload_numbers(values, payload)
    return values


def _fallback_numeric_refs(refs: list[Ref], draft: AnswerDraft) -> list[Ref]:
    cited = set(draft.evidence_refs or []) | set(draft.visual_refs or [])
    if cited:
        cited_refs = [ref for ref in refs if ref.id in cited]
        linked = _linked_refs(refs, cited_refs)
        if any(ref.kind in {"table", "value", "execution", "visual"} for ref in linked):
            return linked
    return [ref for ref in refs if ref.kind in {"table", "value", "date", "dataset", "execution", "visual"}]


def _linked_refs(refs: list[Ref], seed_refs: list[Ref]) -> list[Ref]:
    by_id = {ref.id: ref for ref in refs}
    selected: dict[str, Ref] = {ref.id: ref for ref in seed_refs}
    changed = True
    while changed:
        changed = False
        for ref in list(selected.values()):
            for key in ("executionRef", "sourceRef", "source_ref"):
                linked_id = ref.payload.get(key)
                if isinstance(linked_id, str) and linked_id in by_id and linked_id not in selected:
                    selected[linked_id] = by_id[linked_id]
                    changed = True
            if ref.kind == "execution":
                for candidate in refs:
                    if candidate.id in selected:
                        continue
                    if candidate.payload.get("executionRef") == ref.id:
                        selected[candidate.id] = candidate
                        changed = True
    return list(selected.values())


def _append_execution_payload_numbers(values: list[float], payload: dict[str, Any]) -> None:
    stdout = payload.get("stdout")
    if not isinstance(stdout, str):
        return
    marker = "DARTLAB_RESULT_JSON="
    for line in stdout.splitlines():
        if marker not in line:
            continue
        raw = line.split(marker, 1)[1].strip()
        try:
            import json

            parsed = json.loads(raw)
        except Exception:
            continue
        _append_payload_numbers(values, parsed)


def _append_payload_numbers(values: list[float], payload: Any) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in {"path", "resourceUri"}:
                continue
            _append_payload_numbers(values, value)
        return
    if isinstance(payload, list):
        for item in payload:
            _append_payload_numbers(values, item)
        return
    if isinstance(payload, str):
        text = _DATE_LIKE.sub("", payload)
        for match in _NUMBER_LIKE.finditer(text):
            raw = match.group(0).strip("%").replace(",", "")
            if len(raw.replace(".", "").replace("-", "").replace("+", "")) < 2:
                continue
            try:
                numeric = float(raw)
            except ValueError:
                continue
            values.append(_scale_number_by_korean_unit(numeric, text[match.end() : match.end() + 3]))
        return
    _append_numeric(values, payload)


def _append_numeric(values: list[float], raw: Any) -> None:
    if isinstance(raw, bool):
        return
    try:
        values.append(float(str(raw).replace(",", "").strip("%")))
    except (TypeError, ValueError):
        return


def _scale_number_by_korean_unit(number: float, suffix: str) -> float:
    compact = suffix.strip()
    if compact.startswith("조"):
        return number * 1_000_000_000_000
    if compact.startswith("억"):
        return number * 100_000_000
    if compact.startswith("만"):
        return number * 10_000
    return number


def _number_in_values(number: float, values: list[float]) -> bool:
    for value in values:
        tolerance = max(0.1, abs(value) * 0.005)
        if abs(number - value) <= tolerance:
            return True
    return False


def _has_visual_language(answer: str) -> bool:
    text = answer.lower()
    if any(
        marker in text
        for marker in ("차트는 아직", "차트 없음", "차트를 생성하지", "visual not", "no visual", "no chart")
    ):
        return False
    capability_markers = (
        "차트도 만들 수",
        "차트를 만들 수",
        "차트 제공 가능",
        "시각화 가능",
        "시각화도 가능",
        "visualization available",
        "can create charts",
        "can provide charts",
    )
    if any(marker in text for marker in capability_markers):
        return False
    claim_markers = (
        "아래 차트",
        "다음 차트",
        "생성한 차트",
        "차트를 생성",
        "차트입니다",
        "그래프입니다",
        "visual:",
        "chart:",
    )
    return any(marker in text for marker in claim_markers)


def _claims_execution_success(answer: str) -> bool:
    return bool(_EXECUTION_SUCCESS_LIKE.search(answer))


def _hides_failed_execution(answer: str, limits: list[str]) -> bool:
    lowered = (answer + "\n" + "\n".join(limits)).lower()
    disclosure_markers = ("실패", "오류", "에러", "제한", "확인하지 못", "failed", "error", "limit")
    return not any(marker in lowered for marker in disclosure_markers)


def _claims_dataset_unavailable(answer: str) -> bool:
    lowered = answer.lower()
    markers = (
        "데이터 디렉터리에서 parquet/csv를 찾지 못",
        "데이터 파일(parquet/csv)을 확인하지 못",
        "parquet/csv를 찾지 못",
        "dataset path not found",
        "no parquet/csv",
    )
    return any(marker in lowered for marker in markers)


def _has_available_dataset_ref(refs: list[Ref]) -> bool:
    for ref in refs:
        payload = ref.payload
        if ref.kind == "dataset" and (payload.get("ok") is True or payload.get("path") or payload.get("latest")):
            return True
        if ref.kind == "doc" and str(payload.get("resourceUri") or "").startswith("dartlab://datasets"):
            return True
    return False


def _is_single_value_visual(ref: Ref) -> bool:
    payload = ref.payload
    categories = payload.get("categories")
    series = payload.get("series")
    value_count = 0
    if isinstance(series, list):
        for item in series:
            if isinstance(item, dict) and isinstance(item.get("data"), list):
                value_count += len(item["data"])
    return not isinstance(categories, list) or len(categories) < 2 or value_count < 2


def _unsupported_visual(ref: Ref, refs: list[Ref]) -> bool:
    source_ref = ref.payload.get("sourceRef") or ref.payload.get("source_ref")
    if not source_ref:
        return True
    ref_ids = {item.id for item in refs}
    if source_ref in ref_ids:
        return False
    return not any(source_ref.startswith(prefix) for prefix in ("table:", "execution:"))


def _invalid_table_issue(refs: list[Ref], draft: AnswerDraft) -> dict[str, Any] | None:
    table_refs = [ref for ref in _evidence_scope(refs, draft) if ref.kind == "table"]
    if not table_refs and draft.evidence_refs:
        table_refs = [ref for ref in _fallback_numeric_refs(refs, draft) if ref.kind == "table"]
    if not table_refs:
        table_refs = [ref for ref in refs if ref.kind == "table"]
    for ref in table_refs:
        if ref.kind != "table":
            continue
        rows = ref.payload.get("rows")
        metric = ref.payload.get("metric")
        if not isinstance(rows, list) or not rows:
            return {"code": "empty_table_ref", "message": "table ref has no rows"}
        if not metric:
            continue
        for row in rows:
            if not isinstance(row, dict):
                return {"code": "invalid_table_row", "message": "table ref contains non-object row"}
            value = row.get(metric)
            if value is None:
                return {"code": "invalid_table_value", "message": f"table metric {metric} contains null"}
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return {"code": "invalid_table_value", "message": f"table metric {metric} is not numeric"}
            if _metric_is_ratio_like(str(metric)) and abs(numeric) > 1000:
                return {"code": "implausible_table_value", "message": f"table metric {metric} is implausibly large"}
    return None


def _date_consistency_issue(refs: list[Ref], draft: AnswerDraft) -> dict[str, Any] | None:
    anchor_dates = _anchor_dates_from_answer(draft.answer)
    if not anchor_dates:
        return None
    table_refs = [ref for ref in _evidence_scope(refs, draft) if ref.kind == "table"]
    if not table_refs and draft.evidence_refs:
        table_refs = [ref for ref in _fallback_numeric_refs(refs, draft) if ref.kind == "table"]
    for ref in table_refs:
        rows = ref.payload.get("rows")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            for key, value in row.items():
                if not _is_end_date_key(str(key)):
                    continue
                normalized = _normalize_date_value(value)
                if normalized and normalized not in anchor_dates:
                    return {
                        "code": "answer_table_date_conflict",
                        "message": f"answer anchor date conflicts with table {key}: {normalized}",
                    }
    return None


def _anchor_dates_from_answer(answer: str) -> set[str]:
    anchors: set[str] = set()
    for match in _DATE_LIKE.finditer(answer):
        window = answer[max(0, match.start() - 24) : min(len(answer), match.end() + 24)].lower()
        if any(marker in window for marker in ("기준일", "최신", "as-of", "asof", "관측일", "종료일", "기준 관측")):
            anchors.add(_normalize_date_text(match.group(0)))
    return {date for date in anchors if date}


def _is_end_date_key(key: str) -> bool:
    lowered = key.lower()
    if any(token in lowered for token in ("start", "begin", "시작")):
        return False
    return any(
        token in lowered for token in ("end", "asof", "as_of", "latest", "observed", "종료", "기준일", "관측일", "최신")
    )


def _normalize_date_value(value: Any) -> str | None:
    if value is None:
        return None
    return _normalize_date_text(str(value))


def _normalize_date_text(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 8 and digits.startswith("20"):
        return digits
    return ""


def _metric_is_ratio_like(metric: str) -> bool:
    lowered = metric.lower()
    return any(
        token in lowered
        for token in ("%", "rate", "ratio", "return", "ret", "fluc", "change", "pct", "수익률", "등락률", "비율")
    )
