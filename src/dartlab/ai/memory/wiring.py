"""Memory wiring 공통 helper — chat-native + workbench HARVEST 가 공유.

세션 종료 시 호출:
- recordSkillUsage(skillId, ok, valueRefs) — 사용 빈도 통계
- remember(question + answer 요약, tags=[...]) — 다음 세션 recall 컨텍스트

P-revised: chat-native runAgent 도 본 helper 호출 → SSOT.md Principle 6
"session trace → HARVEST → decisions.jsonl" 의 정합 (이전엔 workbench 만 작성).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from dartlab.ai.contracts import Ref
from dartlab.ai.memory import recordSkillUsage, remember

_DECISION_DIGEST_CAP = 280
_QUESTION_CAP = 200


def wireSessionMemory(
    *,
    question: str,
    answerText: str,
    refs: Iterable[Ref],
    selectedSkillRefs: Iterable[Ref] = (),
    ok: bool = True,
    runId: str = "",
    extraTags: Iterable[str] = (),
) -> None:
    """세션 종료 시 memory 작성. 실패해도 조용히 (사용자 흐름 보호).

    Args:
        question: 사용자 원 질문 (앞 200 char 사용)
        answerText: 답변 본문 (앞 280 char digest)
        refs: 누적 ref 목록 — valueRef 카운트 → skill_stats avgValueRefs
        selectedSkillRefs: 사용된 skill ref (없으면 chat-native default 'chatNative')
        ok: GATE 통과 / failure 없음 여부
        runId: trace runId (tag 에 포함)
        extraTags: 추가 tag (예: 'target:005930', 'market:KR')
    """
    refs_list = list(refs)
    selected_list = list(selectedSkillRefs)
    value_refs = sum(1 for r in refs_list if r.kind == "valueRef")

    skill_ids = _extractSkillIds(selected_list)
    if not skill_ids:
        skill_ids = ["chatNative"]

    for skill_id in skill_ids:
        try:
            recordSkillUsage(skill_id, ok=ok, valueRefs=value_refs)
        except Exception:  # noqa: BLE001
            pass

    if not answerText:
        return
    digest = answerText[:_DECISION_DIGEST_CAP].replace("\n", " ").strip()
    if not digest:
        return

    tags: list[str] = ["pass:harvest"]
    if runId:
        tags.append(f"runId:{runId}")
    tags.append(f"status:{'ok' if ok else 'failed'}")
    for skill_id in skill_ids[:3]:
        tags.append(f"skill:{skill_id}")
    for tag in extraTags:
        tag_str = str(tag or "").strip()
        if tag_str and tag_str not in tags:
            tags.append(tag_str)

    try:
        remember(f"Q: {question[:_QUESTION_CAP]}\nA: {digest}", tags=tags)
    except Exception:  # noqa: BLE001
        pass


def _extractSkillIds(refs: list[Ref]) -> list[str]:
    out: list[str] = []
    for ref in refs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        skill_id = payload.get("id") or ref.id.removeprefix("skill:")
        skill_id_str = str(skill_id or "").strip()
        if skill_id_str and skill_id_str not in out:
            out.append(skill_id_str)
    return out


def inferStockCodeContext(
    refs: Iterable[Ref], *, kwargs: dict[str, Any] | None = None
) -> tuple[str | None, str | None]:
    """누적 refs / kernel kwargs 에서 stockCode + market 추출 시도.

    chat-native HARVEST bridge 가 outcome_log.store_decision 호출 시 사용 (다음 commit).
    """
    if kwargs:
        sc = kwargs.get("stockCode")
        mkt = kwargs.get("market")
        if sc:
            return str(sc), (str(mkt) if mkt else None)
    for ref in refs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        sc = payload.get("stockCode") or payload.get("ticker")
        mkt = payload.get("market")
        if sc:
            return str(sc), (str(mkt) if mkt else None)
    return None, None


__all__ = ["inferStockCodeContext", "wireSessionMemory"]
