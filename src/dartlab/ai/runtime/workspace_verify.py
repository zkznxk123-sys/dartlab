"""Verification contract for workspace-native final answers."""

from __future__ import annotations

import re
from typing import Any

from dartlab.ai.runtime.workspace_session import AgentSession
from dartlab.ai.runtime.workspace_visual import hasDegenerateVisual, requiresCsvArtifact, requiresVisualExplanation


def finalizeAnswer(
    session: AgentSession,
    answer: str,
    evidence_refs: list[str],
    artifact_refs: list[str],
    limits: list[str],
) -> dict[str, Any]:
    for limit in limits:
        session.add_limit(str(limit))
    issues = verifyAnswer(session, answer, evidence_refs, artifact_refs)
    session.verificationIssues = issues
    session.verified = not issues
    session.record_trace("verify", {"tool": "finalize_answer", "ok": not issues, "issues": issues})
    if issues:
        return {
            "ok": False,
            "issues": issues,
            "repair": (
                "관찰/계산/검산이 부족합니다. 필요한 경우 inspect_data 또는 run_python을 실행하고 "
                "날짜 표현, 숫자 근거, outlier, chart/artifact를 고쳐 finalize_answer를 다시 호출하세요."
            ),
        }
    session.finalAnswer = answer
    return {
        "ok": True,
        "answer": answer,
        "evidenceRefs": evidence_refs,
        "artifactRefs": artifact_refs,
        "limits": list(session.limits),
    }


def verifyAnswer(session: AgentSession, answer: str, evidence_refs: list[str], artifact_refs: list[str]) -> list[str]:
    issues: list[str] = []
    text = answer or ""
    if not text.strip():
        issues.append("empty_answer")
    if looksLikeDataQuestion(session.question) and not session.observations:
        issues.append("missing_data_inspection")
    if looksLikeComputeQuestion(session.question) and not any(ex.ok for ex in session.executions):
        issues.append("missing_successful_compute")
    if _misstates_today(session, text):
        issues.append("date_context_conflict")
    if _has_recent_index_return_outlier(session, text):
        issues.append("index_return_outlier")
    if hasDegenerateVisual(session):
        issues.append("degenerate_visual")
    if requiresCsvArtifact(session.question) and not _has_csv_artifact(session):
        issues.append("missing_csv_artifact")
    if requiresVisualExplanation(session.question) and not session.visuals:
        issues.append("missing_visual_explanation")
    if session.executions and session.executions[-1].returncode != 0 and not _discloses_failure(text):
        issues.append("execution_failure_hidden")
    if (evidence_refs or artifact_refs) and not _refs_exist(session, evidence_refs, artifact_refs):
        session.add_limit("일부 evidence/artifact 참조명이 맞지 않아 응답의 artifacts 목록을 기준으로 제공했습니다.")
    return list(dict.fromkeys(issues))


def _misstates_today(session: AgentSession, text: str) -> bool:
    current = session.currentDate.replace("-", "")
    for match in re.finditer(
        r"오늘(?:은| 기준| 현재)?[^\n]{0,20}(20\d{2})[-./년\s]*(\d{1,2})[-./월\s]*(\d{1,2})", text
    ):
        found = f"{int(match.group(1)):04d}{int(match.group(2)):02d}{int(match.group(3)):02d}"
        if found != current:
            return True
    return False


def _has_recent_index_return_outlier(session: AgentSession, text: str) -> bool:
    """Block obviously broken short-horizon index return calculations."""
    q = session.question.lower()
    if not any(word in q for word in ("최근", "강세", "상승", "오른", "recent")):
        return False
    if not any(word in q for word in ("지수", "index", "indices", "kospi", "kosdaq")):
        return False
    values: list[float] = []
    for match in re.finditer(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?\s*%", text):
        raw = match.group(0).replace(",", "").replace("%", "").strip()
        try:
            values.append(abs(float(raw)))
        except ValueError:
            continue
    return bool(values and max(values) > 300.0)


def looksLikeDataQuestion(question: str) -> bool:
    return any(word in question.lower() for word in ("최근", "현재", "지수", "주가", "공시", "데이터", "상승", "비교"))


def looksLikeComputeQuestion(question: str) -> bool:
    return any(word in question.lower() for word in ("찾", "계산", "상승", "오른", "강세", "랭킹", "비교", "수익률"))


def _has_csv_artifact(session: AgentSession) -> bool:
    return any(str(item.get("format") or "") == "csv" for item in session.artifacts)


def _discloses_failure(text: str) -> bool:
    return any(word in text for word in ("실패", "오류", "확인 불가", "계산하지 못", "한계"))


def _refs_exist(session: AgentSession, evidence_refs: list[str], artifact_refs: list[str]) -> bool:
    obs_ids = {item.id for item in session.observations} | {str(item.source) for item in session.observations}
    artifact_ids: set[str] = set()
    for item in [*session.artifacts, *session.visuals]:
        artifact_ids.update(str(item.get(key)) for key in ("id", "url", "fileName") if item.get(key))
    return all(str(ref) in obs_ids for ref in evidence_refs) and all(str(ref) in artifact_ids for ref in artifact_refs)
