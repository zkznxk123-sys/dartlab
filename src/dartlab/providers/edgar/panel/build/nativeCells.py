"""EDGAR native 재무 셀 생성 — fact/context/role 결합 후 panel payload 재료로 반환.

별도 셀 artifact 는 만들지 않는다. builder 가 본 함수의 결과를 같은 ``edgar/panel`` row
``contentRaw`` payload 로 붙이고, read 표면은 그 payload 를 read-time 으로 wide 변환한다.
"""

from __future__ import annotations

from collections import defaultdict

from .mapper import contextToCell, roleToStatement


def buildNativeCells(
    facts: list[dict],
    contexts: dict[str, dict],
    roles: dict[str, list[dict]],
    labels: dict[str, str],
    *,
    meta: dict,
) -> list[dict]:
    """facts × contexts × presentation role → EDGAR native cell row list.

    Args:
        facts: ``instance.extractFacts`` + ``extractInstanceFacts`` 결과.
        contexts: ``instance.extractContexts`` 결과.
        roles: ``linkbase.parsePresentation`` 결과.
        labels: ``linkbase.parseLabels`` 결과.
        meta: ``{"ticker", "accession", "filingPeriod", "fyEndMonth"}``.

    Returns:
        panel payload 로 인코딩할 native cell dict list.

    Raises:
        없음 — 미매칭 fact/context 는 skip 하고 빈 list 도 정상.

    Example:
        >>> buildNativeCells([], {}, {}, {}, meta={"ticker": "AAPL", "accession": "x", "filingPeriod": "2024"})
        []
    """
    factsByConcept: dict[str, list[dict]] = defaultdict(list)
    for fact in facts:
        if fact.get("factType") != "numeric":
            continue
        key = f"{fact['namespace']}:{fact['concept']}" if fact.get("namespace") else fact["concept"]
        factsByConcept[key].append(fact)

    ticker = meta["ticker"]
    accession = meta["accession"]
    filingPeriod = meta["filingPeriod"]
    fyEndMonth = meta.get("fyEndMonth")
    rows: list[dict] = []
    for roleUri, entries in roles.items():
        statement = roleToStatement(roleUri)
        if not statement:
            continue
        for order, entry in enumerate(entries):
            conceptKey = entry["conceptKey"]
            matched = factsByConcept.get(conceptKey)
            if not matched:
                continue
            label = labels.get(conceptKey) or entry["concept"]
            for fact in matched:
                ctx = contexts.get(fact["contextRef"])
                if not ctx:
                    continue
                decoded = contextToCell(ctx, fyEndMonth=fyEndMonth)
                if decoded is None:
                    continue
                ctxYear, ctxFlow, ctxQuarter, ctxMode, axisPath = decoded
                rows.append(
                    {
                        "corp": ticker,
                        "rceptNo": accession,
                        "filingPeriod": filingPeriod,
                        "statement": statement,
                        "scope": "consolidated",
                        "concept": entry["concept"],
                        "label": label,
                        "ctxYear": ctxYear,
                        "ctxFlow": ctxFlow,
                        "ctxQuarter": ctxQuarter,
                        "ctxMode": ctxMode,
                        "axisPath": axisPath,
                        "valueRaw": fact["valueRaw"],
                        "cellOrder": order,
                    }
                )
    return rows
