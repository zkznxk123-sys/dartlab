"""Memory wiring 공통 helper — chat-native + workbench HARVEST 가 공유.

세션 종료 시 호출:
- recordSkillUsage(skillId, ok, valueRefs) — 사용 빈도 통계
- remember(question + answer 요약, tags=[...]) — 다음 세션 recall 컨텍스트
- outcome_log.store_decision(stockCode, market, ...) — stockCode 인식 시 pending entry 작성
- tryResolvePending(stockCode, market, pricer=...) — 같은 종목 다음 호출 진입부에서 pending → resolved 자동 변환

P-revised: chat-native runAgent 도 본 helper 호출 → SSOT.md Principle 6
"session trace → HARVEST → decisions.jsonl + outcome_log" 정합 (이전엔 workbench 만 작성).

ai/ 정적 import 가드 (SSOT §1) — providers 호출이 필요한 default lookup 은 함수
local lazy import. caller 는 더 정교한 pricer 를 주입할 수 있다.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date
from typing import Any

from dartlab.ai.contracts import Ref
from dartlab.ai.memory.decisions import recall, remember
from dartlab.ai.memory.outcome_log import (
    get_past_context,
    safe_stockcode,
    store_decision,
)
from dartlab.ai.memory.promotion import recordSkillUsage

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
    stockCode: str | None = None,
    market: str | None = None,
    decisionTheme: str | None = None,
) -> None:
    """세션 종료 시 memory 작성. 실패해도 조용히 (사용자 흐름 보호).

    Args:
        question: 사용자 원 질문 (앞 200 char 사용)
        answerText: 답변 본문 (앞 280 char digest)
        refs: 누적 ref 목록 — valueRef 카운트 → skill_stats avgValueRefs
        selectedSkillRefs: 사용된 skill ref
        ok: GATE 통과 / failure 없음 여부
        runId: trace runId (tag 에 포함)
        extraTags: 추가 tag (예: 'target:005930', 'market:KR')
        stockCode / market: 명시 시 outcome_log 에 pending entry 작성 (다음 같은 종목 호출 시 resolve)
        decisionTheme: outcome_log entry tag 의 theme 컬럼 (예: "Buy", "Hold", "Concern"). 미지정 시 "Verdict".
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

    # outcome_log 에 pending entry — stockCode 명시 + ok 시만.
    if stockCode and ok:
        try:
            safe_code = safe_stockcode(stockCode)
            store_decision(
                stockCode=safe_code,
                market=market or "KR",
                date=date.today().isoformat(),
                theme=(decisionTheme or "Verdict").strip()[:32],
                decision_text=digest,
            )
        except Exception:  # noqa: BLE001
            pass


def fetchPastContext(stockCode: str | None, market: str | None = None, *, n_same: int = 5, n_cross: int = 3) -> str:
    """BRIEF / agent.runAgent 진입부에서 호출 — outcome_log past_context 조회.

    빈 문자열 반환 시 호출자가 prompt 의 placeholder 섹션 자체를 부재화 (환각 가드).
    stockCode 미지정 또는 가드 거부 시 빈 문자열.
    """
    if not stockCode:
        return ""
    try:
        safe_code = safe_stockcode(stockCode)
        return get_past_context(safe_code, market=market or "KR", n_same=n_same, n_cross=n_cross)
    except Exception:  # noqa: BLE001
        return ""


def fetchRecallContext(question: str, *, k: int = 5) -> list[dict[str, Any]]:
    """BM25 recall — 다음 세션 컨텍스트 주입용. 실패 시 빈 list."""
    try:
        return recall(question, k=k) or []
    except Exception:  # noqa: BLE001
        return []


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


def defaultPriceLookup(symbol: str, asOf: str, *, market: str = "KR") -> float | None:
    """KR 종목용 default pricer — Company.gather("price") + asOf 필터.

    SSOT §6 의 `Company.price(asOf=...)` 명시는 본 helper 가 effective 의미를 충족.
    US 는 EDGAR 측 미구현 (None 반환). 빈 데이터 / 예외 / asOf 이전 가격 0 건 → None
    (resolver 가 pending 유지).

    네트워크 호출 비용 큼. 운영 cron sweep 에서 사용 시 caller 가 캐시 wrap 권장.
    """
    if market != "KR":
        return None
    try:
        import polars as pl  # noqa: PLC0415  (lazy: ai/ 정적 import 가드)

        from dartlab.providers.dart.company import Company  # noqa: PLC0415

        c = Company(symbol)
        df = c.gather("price")
        if df is None or df.is_empty():
            return None
        target = pl.lit(asOf).cast(pl.Date, strict=False)
        filtered = df.filter(pl.col("date") <= target)
        if filtered.is_empty():
            return None
        return float(filtered.sort("date").tail(1)["close"][0])
    except Exception:  # noqa: BLE001
        return None


def tryResolvePending(
    stockCode: str | None,
    market: str | None = None,
    *,
    pricer: Callable[[str, str], float | None] | None = None,
    benchmarkPricer: Callable[[str, str], float | None] | None = None,
    benchmarkSymbol: str | None = None,
    today: str | None = None,
    minHoldingDays: int = 30,
) -> int:
    """outcome_resolver 호출 wrapper — 진입부 1 줄 호출용.

    pricer 미주입 시 noop (0). 실패 / 가드 거부 / 예외 시 안전 0.
    caller 는 default 로 `defaultPriceLookup` 사용 가능 (KR 만 지원).

    Returns:
        resolved 갱신된 entry 수.
    """
    if not stockCode:
        return 0
    if pricer is None:
        return 0
    try:
        from dartlab.ai.memory.outcome_resolver import resolvePending  # noqa: PLC0415

        safe_code = safe_stockcode(stockCode)
        report = resolvePending(
            safe_code,
            market=market or "KR",
            pricer=pricer,
            benchmarkPricer=benchmarkPricer,
            benchmarkSymbol=benchmarkSymbol,
            today=today,
            minHoldingDays=minHoldingDays,
        )
        return report.resolvedCount
    except Exception:  # noqa: BLE001
        return 0


__all__ = [
    "defaultPriceLookup",
    "fetchPastContext",
    "fetchRecallContext",
    "inferStockCodeContext",
    "tryResolvePending",
    "wireSessionMemory",
]
