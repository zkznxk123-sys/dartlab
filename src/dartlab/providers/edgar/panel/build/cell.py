"""EDGAR 셀 분해 — facts × contexts × presentation role → EDGAR_CELL_SCHEMA (DART cell 미러).

DART ``cellsFromContent``(재무표 ``<TE ACODE ACONTEXT>`` → 셀)의 EDGAR 미러. 단 EDGAR 는 fact·context·
구조가 분리돼 있어 **3원 결합**한다: ① presentation role(``linkbase``)이 statement(BS/IS/CF) + concept
표시순을 주고, ② inline fact(``instance``)가 concept→값, ③ context(``instance``)가 기간·차원. 각 statement
role 의 concept 마다 그 concept 의 fact 들을 context 해소(``mapper.contextToCell``)해 셀 행 생성.
build-time 해소(contextRef 가 문서-전역 간접참조라 read-time 불가) → cell artifact.

LLM Specifications:
    AntiPatterns:
        - abstract(header) concept 에 셀 생성 금지 — fact 없으면 자동 skip.
        - 비-statement role(Disclosure) fact 를 셀로 금지 — roleToStatement None 은 board narrative.
        - 동일 concept 다중 statement role 출현 시 누락 금지 — role 별 emit(Cash=BS+CF 정상).
    OutputSchema:
        - ``buildCells(facts, contexts, roles, labels, *, meta) -> list[dict]`` (EDGAR_CELL_SCHEMA).
    Prerequisites:
        - mapper (roleToStatement / contextToCell).
    Freshness:
        - 순수 — 입력 외 의존 0.
    Dataflow:
        - role(statement+concept순서) × fact(concept→값) × context(기간) → 셀.
    TargetMarkets:
        - US.
"""

from __future__ import annotations

from collections import defaultdict

from .mapper import contextToCell, roleToStatement


def buildCells(
    facts: list[dict],
    contexts: dict[str, dict],
    roles: dict[str, list[dict]],
    labels: dict[str, str],
    *,
    meta: dict,
) -> list[dict]:
    """facts × contexts × presentation role → EDGAR_CELL_SCHEMA 행 list (build-time 해소).

    각 재무제표 role(``roleToStatement`` 매치)의 concept 순서를 따라, 그 concept 의 numeric fact 들을
    context 해소해 셀 행 생성. statement=role, concept=us-gaap local-name, period/축=context, value=
    해소 numeric, cellOrder=role 내 표시순. abstract(fact 0) concept 은 자동 제외.

    Args:
        facts: ``instance.extractFacts`` 결과.
        contexts: ``instance.extractContexts`` 결과 (ref→해소).
        roles: ``linkbase.parsePresentation`` 결과 (roleURI→concept 순서).
        labels: ``linkbase.parseLabels`` 결과 (conceptKey→라벨).
        meta: ``{"ticker", "accession", "filingPeriod"}``.

    Returns:
        list[dict] — EDGAR_CELL_SCHEMA 14-col 행. 재무제표 fact 0 이면 빈 list.

    Raises:
        없음.

    Example:
        >>> rows = buildCells(facts, ctxs, roles, labels, meta={"ticker":"AAR","accession":"...","filingPeriod":"2025Q2"})  # doctest: +SKIP

    SeeAlso:
        - ``providers.dart.panel.build.cell.cellsFromContent`` — DART analog.
        - ``providers.edgar.panel.cellRead.readStatement`` — 본 셀 → acode×period wide.

    Requires:
        - mapper.

    Capabilities:
        - 재무제표를 계정×기간 셀로 — DART ACONTEXT 셀 분해의 EDGAR 3원결합 미러.

    Guide:
        - builder 가 호출. 순수.

    AIContext:
        - role 이 statement+표시순 truth, fact 가 값, context 가 기간/축. 셋 결합.

    When:
        - 필링 재무제표를 셀 artifact 로 분해할 때.

    How:
        - factsByConcept index → role 별 concept 순회 → fact×context → 셀.

    LLM Specifications:
        AntiPatterns:
            - text fact 를 셀로 금지 — numeric 만(재무 수치).
        OutputSchema:
            - ``list[dict]``.
        Prerequisites:
            - mapper.
        Freshness:
            - 순수.
        Dataflow:
            - role×fact×context → 셀.
        TargetMarkets:
            - US.
    """
    factsByConcept: dict[str, list[dict]] = defaultdict(list)
    for f in facts:
        if f.get("factType") != "numeric":
            continue
        key = f"{f['namespace']}:{f['concept']}" if f.get("namespace") else f["concept"]
        factsByConcept[key].append(f)

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
                continue  # abstract / 미출현 concept
            label = labels.get(conceptKey) or entry["concept"]
            for f in matched:
                ctx = contexts.get(f["contextRef"])
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
                        "valueRaw": f["valueRaw"],
                        "cellOrder": order,
                    }
                )
    return rows
