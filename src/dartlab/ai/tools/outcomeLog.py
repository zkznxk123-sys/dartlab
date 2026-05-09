"""OutcomeLog — pending decision 기록 도구 (memory.outcome_log SSOT 경유).

dartlab 의 *진화 루프* 는 분석 결과를 시간 stamp 와 함께 기록 → N 일 뒤 시장 가격으로 reflection.
지금까지 이 흐름은 workbench HARVEST 패스 안에 갇혀 있어 외부 클라이언트 또는 chat-native
agent 가 자율적으로 호출 못 했음. 이 도구가 registry SSOT 로 표면화하여 둘 다 사용 가능.

idempotent=False — 같은 (date, stockCode) 호출은 store_decision 이 skip 하지만 도구 자체
시그니처상 write 인식. annotations: readOnly=False, idempotent=False.
"""

from __future__ import annotations

from dartlab.ai.contracts import Ref

from .types import ToolResult


def outcomeLog(
    *,
    stockCode: str,
    market: str = "KR",
    date: str,
    decision: str,
    theme: str = "Verdict",
) -> ToolResult:
    """pending entry 를 ~/.dartlab/decisions/{market}/{stockCode}.md 에 추가.

    Args:
        stockCode: KR 6 자리 / US ticker / generic safe 식별자. safe_stockcode 가드 필수.
        market: "KR" 또는 "US" — 그 외는 KR 로 정규화.
        date: YYYY-MM-DD 형식.
        decision: 의사결정 본문 — Buy / Hold / Sell + 근거.
        theme: 라벨 (default "Verdict").
    """
    from dartlab.ai.memory.outcome_log import store_decision

    try:
        wrote = store_decision(
            stockCode=stockCode,
            market=market,
            date=date,
            theme=theme,
            decision_text=decision,
        )
    except ValueError as exc:
        return ToolResult(
            ok=False,
            summary=f"OutcomeLog 거부 — stockCode/date 형식: {exc}",
            error="outcome_log_invalid_input",
        )

    summary = "outcome_log pending 기록" if wrote else "outcome_log 동일 entry 이미 있음 — skip"
    return ToolResult(
        ok=True,
        summary=summary,
        refs=[
            Ref(
                id=f"decision:{market}:{stockCode}:{date}",
                kind="decisionRef",
                title=f"{stockCode} {date} {theme}",
                source="dartlab.ai.memory.outcome_log",
                payload={
                    "stockCode": stockCode,
                    "market": market,
                    "date": date,
                    "theme": theme,
                    "wrote": wrote,
                },
            )
        ],
        data={"wrote": wrote, "stockCode": stockCode, "market": market, "date": date},
    )
