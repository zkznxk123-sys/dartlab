"""Target / profile / plan / recipe 헬퍼 — 휴리스틱 흐름의 정적 함수 모음.

질문 텍스트에서 종목/티커 추출, profile 빌드, plan/recipe 전개. 외부 LLM 의존 없음.
heuristic.py 와 passes.py 가 본 모듈을 사용.
"""

from __future__ import annotations

from typing import Any

from dartlab.ai.contracts import Ref

from .intent import (
    _ACTION_WORDS,
    _COMPANY_SPLIT_RE,
    _SHOW_TOPIC_ALIASES,
    _STOCK_CODE_RE,
    _TICKER_RE,
)
from .state import WorkbenchState

_EVIDENCE_EXECUTION_NAMES = {
    "execution",
    "executionRef",
    "table",
    "tableRef",
    "value",
    "valueRef",
    "date",
    "dateRef",
    "dataset",
    "datasetRef",
    "datasetAsOf",
    "universe",
    "filter",
    "formula",
}
_NON_EXECUTABLE_API_REFS = {"ask", "Company", "Company.ask", "ChartResult", "SelectResult"}


def _buildQuestionProfile(question: str, *, stockCode: Any = None) -> dict[str, Any]:
    targets = _extractTargets(question, stockCode=stockCode)
    comparison = len(targets) >= 2
    task_type = "companyResearch" if targets else "research"
    return {
        "taskType": task_type,
        "targets": targets,
        "comparison": comparison,
        "showTopic": _inferShowTopic(question),
    }


def _extractTargets(question: str, *, stockCode: Any = None) -> list[str]:
    if stockCode:
        return [str(stockCode)]
    text = str(question or "").strip()
    stock_codes = _STOCK_CODE_RE.findall(text)
    if stock_codes:
        return list(dict.fromkeys(stock_codes))
    ticker_hits = [value for value in _TICKER_RE.findall(text) if value not in {"BS", "IS", "CF", "FCF"}]
    if ticker_hits:
        return list(dict.fromkeys(ticker_hits))
    parts = [part.strip() for part in _COMPANY_SPLIT_RE.split(text) if part.strip()]
    cleaned: list[str] = []
    for part in parts if len(parts) > 1 else [text]:
        value = _cleanTargetPhrase(part)
        if _looksLikeTarget(value) and value not in cleaned:
            cleaned.append(value)
    return cleaned[:3]


def _cleanTargetPhrase(value: str) -> str:
    cleaned = str(value or "")
    for word in _ACTION_WORDS:
        cleaned = cleaned.replace(word, " ")
    return " ".join(cleaned.split()).strip()


def _looksLikeTarget(value: str) -> bool:
    compact = str(value or "").strip()
    if not compact:
        return False
    if _STOCK_CODE_RE.fullmatch(compact) or _TICKER_RE.fullmatch(compact):
        return True
    if " " in compact:
        return False
    if compact in {"회사", "기업", "종목", "기능", "사용법", "질문", "분석", "비교", "확인"}:
        return False
    return 2 <= len(compact) <= 24


def _inferShowTopic(question: str) -> str:
    lowered = str(question or "").lower()
    for topic, aliases in _SHOW_TOPIC_ALIASES:
        if any(alias.lower() in lowered for alias in aliases):
            return topic
    return "BS"


def _planEvidence(state: WorkbenchState) -> list[dict[str, Any]]:
    recipe_plans = _expandRecipe(state)
    if recipe_plans:
        return recipe_plans

    candidates = _candidateApiRefs(state)
    targets = list(state.profile.get("targets") or [])
    plans: list[dict[str, Any]] = []

    scan_ref = _firstScanRef(candidates, state.selectedSkillRefs)
    if scan_ref is not None and not targets:
        plans.append(
            {
                "tool": "engine_call",
                "args": {"plan": {"apiRef": scan_ref, "axis": _scanAxis(scan_ref, state.selectedSkillRefs)}},
            }
        )
        return plans

    if targets:
        company_ref = _firstCompanyRef(candidates)
        if company_ref == "Company.show" or _skillRequiresTable(state.selectedSkillRefs):
            return [
                {
                    "tool": "engine_call",
                    "args": {
                        "plan": {
                            "apiRef": "Company.show",
                            "target": target,
                            "topic": state.profile.get("showTopic") or "BS",
                            "question": state.question,
                        }
                    },
                }
                for target in targets[:2]
            ]
        if company_ref:
            return [
                {
                    "tool": "engine_call",
                    "args": {
                        "plan": _companyPlan(company_ref, target, state.selectedSkillRefs, question=state.question)
                    },
                }
                for target in targets[:2]
            ]

    if _skillRequiresTarget(state.selectedSkillRefs):
        return plans

    capability_ref = _firstCapabilityRef(candidates)
    if capability_ref:
        key = _capabilityKeyFromSkills(state.selectedSkillRefs)
        plans.append({"tool": "engine_call", "args": {"plan": {"apiRef": capability_ref, "path": key}}})
    return plans


def _candidateApiRefs(state: WorkbenchState) -> list[str]:
    refs: list[str] = []
    for ref in state.selectedSkillRefs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        refs.extend(str(item) for item in payload.get("capabilityRefs") or [])
    for ref in state.apiRefs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        api_ref = payload.get("apiRef") or ref.id.removeprefix("api:")
        if api_ref:
            refs.append(str(api_ref))
    return [ref for ref in dict.fromkeys(refs) if _isExecutableApiRef(ref)]


def _isExecutableApiRef(api_ref: str) -> bool:
    if not api_ref or api_ref in _NON_EXECUTABLE_API_REFS:
        return False
    if api_ref.startswith("aiContract."):
        return False
    return True


def _firstScanRef(candidates: list[str], skill_refs: list[Ref]) -> str | None:
    skill_ids = [_skillId(ref) for ref in skill_refs]
    if not any(skill_id.startswith("engines.scan") for skill_id in skill_ids):
        return None
    for api_ref in candidates:
        if api_ref.startswith("scan."):
            return api_ref
    if "scan" in candidates:
        return "scan"
    return None


def _scanAxis(api_ref: str, skill_refs: list[Ref]) -> str:
    if api_ref.startswith("scan."):
        return api_ref.split(".", 1)[1]
    for ref in skill_refs:
        skill_id = _skillId(ref)
        if skill_id.startswith("engines.scan."):
            return skill_id.rsplit(".", 1)[1]
    return "screen"


def _firstCompanyRef(candidates: list[str]) -> str | None:
    if "Company.show" in candidates:
        return "Company.show"
    for api_ref in candidates:
        if api_ref.startswith("Company.") and api_ref not in {"Company", "Company.ask"}:
            return api_ref
    return None


def _firstCapabilityRef(candidates: list[str]) -> str | None:
    for api_ref in candidates:
        if api_ref in {"capabilities", "dartlab.capabilities"}:
            return api_ref
    return None


def _skillRequiresTable(skill_refs: list[Ref]) -> bool:
    for ref in skill_refs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        required = {str(item) for item in payload.get("requiredEvidence") or []}
        if required & {"table", "tableRef", "valueRef", "dateRef"}:
            return True
    return False


def _skillRequiresTarget(skill_refs: list[Ref]) -> bool:
    for ref in skill_refs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        required = {str(item) for item in payload.get("requiredEvidence") or []}
        inputs = {str(item).lower() for item in payload.get("inputs") or []}
        if "target" in required or "target" in inputs or "기업명 또는 종목코드" in payload.get("inputs", []):
            return True
    return False


def _companyPlan(api_ref: str, target: str, skill_refs: list[Ref], *, question: str) -> dict[str, Any]:
    if api_ref == "Company.analysis":
        subaxis = _analysisSubaxis(skill_refs)
        args = ["financial", subaxis] if subaxis else []
        return {"apiRef": api_ref, "target": target, "args": args, "question": question}
    return {"apiRef": api_ref, "target": target, "question": question}


def _analysisSubaxis(skill_refs: list[Ref]) -> str:
    for ref in skill_refs:
        skill_id = _skillId(ref)
        if not skill_id.startswith("engines.analysis."):
            continue
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        title = str(payload.get("title") or ref.title or "")
        cleaned = title.replace("Analysis -", "").replace("분석", "").strip(" -")
        if cleaned:
            return cleaned
    return ""


def _capabilityKeyFromSkills(skill_refs: list[Ref]) -> str:
    for ref in skill_refs:
        skill_id = _skillId(ref)
        parts = skill_id.split(".")
        if len(parts) >= 2 and parts[0] == "engines":
            return parts[1]
    return ""


def _skillId(ref: Ref) -> str:
    if isinstance(ref.payload, dict) and ref.payload.get("id"):
        return str(ref.payload["id"])
    return ref.id.removeprefix("skill:")


def _requiredEvidence(state: WorkbenchState) -> list[str]:
    required: list[str] = []
    for ref in state.selectedSkillRefs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        required.extend(str(item) for item in payload.get("requiredEvidence") or [])
    return list(dict.fromkeys(required or ["skillRef", "apiRef"]))


def _requiresExecution(state: WorkbenchState) -> bool:
    required = set(_requiredEvidence(state))
    if required & _EVIDENCE_EXECUTION_NAMES:
        return True
    skill_ids = [_skillId(ref) for ref in state.selectedSkillRefs]
    return any(skill_id.startswith("engines.") for skill_id in skill_ids)


def _hasRecipe(state: WorkbenchState) -> bool:
    """state.selectedSkillRefs 안에 kind=='recipe' 또는 recipeSteps 가 있는지."""
    for ref in state.selectedSkillRefs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        if payload.get("kind") == "recipe":
            return True
        if payload.get("recipeSteps"):
            return True
    return False


def _recipeRefForState(state: WorkbenchState) -> Ref | None:
    """state.selectedSkillRefs 중 첫 recipe ref 반환."""
    for ref in state.selectedSkillRefs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        if payload.get("kind") == "recipe" or payload.get("recipeSteps"):
            return ref
    return None


def _expandRecipe(state: WorkbenchState) -> list[dict[str, Any]]:
    """recipe ref 의 step list 를 plan list 로 전개.

    각 step 의 skillId 에 대해 Skill OS 에서 spec 을 찾고, 그 capabilityRefs 로
    engine_call plan 을 생성한다. 한 번만 전개 (BRIEF retry 시 재전개 방지) —
    명시적 `state.recipeExpanded` boolean.

    회귀 보호: targets >= 2 인 두 회사 비교는 휴리스틱의 _composeStatementComparison
    분기가 더 정확한 답을 만들므로 recipe 발동을 양보 (빈 list 반환).
    """
    if state.recipeExpanded:
        return []
    recipe_ref = _recipeRefForState(state)
    if recipe_ref is None:
        return []
    targets = list(state.profile.get("targets") or [])
    if len(targets) >= 2:
        # 두 회사 비교는 휴리스틱 분기 우선 — recipe 양보.
        return []
    state.recipeExpanded = True

    payload = recipe_ref.payload if isinstance(recipe_ref.payload, dict) else {}
    steps = payload.get("recipeSteps") or []
    if not steps:
        # body 에서 직접 추출 fallback
        from dartlab.skills.registry import _steps_from_recipe_body

        steps = _steps_from_recipe_body(str(payload.get("body") or ""))
    if not steps:
        # linkedSkills 만 있고 body step 없으면 단순 전개
        steps = [{"skillId": sid, "note": ""} for sid in payload.get("linkedSkills") or []]
    if not steps:
        return []

    targets = list(state.profile.get("targets") or [])
    plans: list[dict[str, Any]] = []
    try:
        from dartlab.skills.registry import getSkill
    except Exception:  # noqa: BLE001
        return []

    last_scan_index: int | None = None
    for step in steps[:8]:  # max 8 step (token cost guard)
        skill_id = str(step.get("skillId") or "")
        if not skill_id:
            continue
        try:
            spec = getSkill(skill_id, includeUser=False)
        except Exception:  # noqa: BLE001
            continue
        executable_refs = [ref for ref in (spec.capabilityRefs or []) if _isExecutableApiRef(str(ref))]
        # Company.show / Company.analysis 같은 method-form 우선, 단순 'Company' 클래스명 후순위.
        method_refs = [ref for ref in executable_refs if "." in str(ref)]
        capability_refs = method_refs or executable_refs
        if not capability_refs:
            continue
        api_ref = capability_refs[0]
        is_scan_step = api_ref.startswith("scan.") or api_ref in {"scan", "dartlab.scan"}
        is_company_step = api_ref.startswith("Company.")

        for target in targets[:2] if targets else [None]:
            plan = {
                "tool": "engine_call",
                "args": {
                    "plan": {
                        "apiRef": api_ref,
                        "target": target,
                        "question": state.question,
                        "_recipeStep": skill_id,
                    }
                },
            }
            # scan→company step dependency: 다음 Company step 이 prev scan 결과
            # stockCodes 를 target 으로 받게 메타 추가 (실제 inject 는 _injectStepDependency).
            if is_company_step and last_scan_index is not None and not target:
                plan["args"]["plan"]["_inheritTargetsFrom"] = last_scan_index
            if not target:
                plan["args"]["plan"].pop("target", None)
            plans.append(plan)
        if is_scan_step:
            last_scan_index = len(plans) - 1
    return plans


def _injectStepDependency(plan: dict[str, Any], prev_results: list[dict[str, Any]]) -> dict[str, Any]:
    """plan 의 _inheritTargetsFrom 메타가 가리키는 prev step 결과 ref 에서 stockCode 추출 후 target 으로 inject.

    매칭 안 되면 원본 그대로 반환 (회귀 보호).
    """
    args = plan.get("args") or {}
    inner = args.get("plan") or {}
    src_idx = inner.get("_inheritTargetsFrom")
    if src_idx is None or not isinstance(src_idx, int):
        return plan
    if src_idx < 0 or src_idx >= len(prev_results):
        return plan
    prev = prev_results[src_idx]
    prev_refs = (prev.get("result") or {}).refs if hasattr(prev.get("result") or {}, "refs") else []
    # ref payload 안 stockCode 후보 추출
    candidates: list[str] = []
    for ref in prev_refs or []:
        payload = getattr(ref, "payload", None) or {}
        if not isinstance(payload, dict):
            continue
        # scan rows 형태 — payload.rows[*].stockCode 또는 payload.stockCode
        rows = payload.get("rows")
        if isinstance(rows, list):
            for row in rows[:5]:
                if isinstance(row, dict):
                    code = str(row.get("stockCode") or row.get("종목코드") or "").strip()
                    if code and code not in candidates:
                        candidates.append(code)
        code = str(payload.get("stockCode") or "").strip()
        if code and code not in candidates:
            candidates.append(code)
    if not candidates:
        return plan
    inner["target"] = candidates[0]  # 첫 후보만 — peer 일괄은 별도 향후 확장
    return plan
