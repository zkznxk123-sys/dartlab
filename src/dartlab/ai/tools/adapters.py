"""Tool handler 어댑터 — dartlab 공개 API 를 tool 로 래핑.

LLM 이 호출한 tool → 여기서 실제 dartlab 함수를 직접 호출 (subprocess 없음).
반환값은 DataFrame 또는 dict. serializeForLlm/Ui 가 LLM/UI 용으로 변환.
"""

from __future__ import annotations

from typing import Any


# ── Company bound helpers ──────────────────────────────────


def _makeCompany(stockCode: str) -> Any:
    """canHandle 라우팅으로 DART/EDGAR Company 자동 생성."""
    import dartlab

    return dartlab.Company(stockCode)


# ── Tool handlers ──────────────────────────────────────────


def handleShow(stockCode: str, topic: str, period: str | None = None, freq: str | None = None) -> Any:
    c = _makeCompany(stockCode)
    kwargs: dict[str, Any] = {}
    if period is not None:
        kwargs["period"] = period
    if freq is not None:
        kwargs["freq"] = freq
    return c.show(topic, **kwargs)


def handleSelect(
    stockCode: str,
    topic: str,
    fields: list[str],
    period: str | None = None,
    freq: str | None = None,
) -> Any:
    c = _makeCompany(stockCode)
    kwargs: dict[str, Any] = {}
    if period is not None:
        kwargs["period"] = period
    if freq is not None:
        kwargs["freq"] = freq
    # select 는 indList 로 행 필터. Company.select(topic, fields, ...) 시그니처 사용.
    return c.select(topic, fields, **kwargs)


def handleAnalysis(stockCode: str, axis: str, overrides: dict | None = None) -> Any:
    c = _makeCompany(stockCode)
    if overrides:
        return c.analysis(axis, overrides=overrides)
    return c.analysis(axis)


def handleScan(
    axis: str,
    stockCode: str | None = None,
    sortBy: str | None = None,
    descending: bool = True,
    limit: int | None = 20,
) -> Any:
    import dartlab

    df = dartlab.scan(axis)
    if df is None:
        return None

    # 종목 필터
    if stockCode:
        try:
            if "종목코드" in df.columns:
                df = df.filter(df["종목코드"] == stockCode)
            elif "stockCode" in df.columns:
                df = df.filter(df["stockCode"] == stockCode)
        except (AttributeError, KeyError):
            pass

    # 정렬
    if sortBy:
        try:
            df = df.sort(sortBy, descending=descending, nulls_last=True)
        except (AttributeError, KeyError, ValueError):
            pass

    # limit
    if limit and limit > 0:
        try:
            df = df.head(limit)
        except (AttributeError,):
            pass

    return df


def handleMacro(axis: str) -> Any:
    import dartlab

    return dartlab.macro(axis)


def handleCredit(stockCode: str, axis: str | None = None) -> Any:
    c = _makeCompany(stockCode)
    if axis:
        return c.credit(axis)
    return c.credit()


def handleGather(stockCode: str, axis: str) -> Any:
    c = _makeCompany(stockCode)
    return c.gather(axis)


def handleSearch(
    query: str,
    scope: str = "title",
    corp: str | None = None,
    start: str | None = None,
    end: str | None = None,
    limit: int = 10,
) -> Any:
    import dartlab

    return dartlab.search(query, corp=corp, start=start, end=end, topK=limit, scope=scope)


def handleReview(
    stockCode: str,
    type: str | None = None,  # noqa: A002 — tool schema 상 'type' 유지
    section: str | None = None,
    template: str | None = None,
) -> Any:
    c = _makeCompany(stockCode)
    kwargs: dict[str, Any] = {}
    if type is not None:
        kwargs["type"] = type
    if section is not None:
        kwargs["section"] = section
    if template is not None:
        kwargs["template"] = template
    return c.review(**kwargs)


def handlePythonExec(code: str, stockCode: str | None = None) -> str:
    from dartlab.ai.tools.coding import DartlabCodeExecutor

    executor = DartlabCodeExecutor()
    return executor.execute(code, stockCode=stockCode, timeout=60)


# ── 핸들러 테이블 ───────────────────────────────────────────


HANDLERS: dict[str, Any] = {
    "show": handleShow,
    "select": handleSelect,
    "analysis": handleAnalysis,
    "scan": handleScan,
    "macro": handleMacro,
    "credit": handleCredit,
    "gather": handleGather,
    "search": handleSearch,
    "review": handleReview,
    "pythonExec": handlePythonExec,
}
