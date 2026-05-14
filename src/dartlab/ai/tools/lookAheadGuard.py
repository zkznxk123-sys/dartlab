"""LookAheadGuard — 시점 안전한 Company.show 호출 도구 (asOf 강제).

dartlab 분석 루프에서 *과거 시점 진단* (back-test, decision reflection) 시 미래 데이터
누설 (look-ahead bias) 차단. Company.show 의 asOf= 파라미터를 *반드시* 명시하도록
강제하는 tool. 같은 동작을 RunPython 안에서 호출 가능하지만 LLM 이 asOf 를 잊을 위험을
표면화 강제로 방어.

annotations: readOnly=True (분석 read), idempotent=True (같은 입력 동일 결과),
openWorld=False, destructive=False.
"""

from __future__ import annotations

from dartlab.ai.contracts import Ref

from .types import ToolResult


def lookAheadGuard(
    *,
    stockCode: str,
    asOf: str,
    topic: str = "BS",
    market: str = "KR",
    block: int | None = None,
    period: str | list[str] | None = None,
    freq: str = "Q",
    scope: str = "consolidated",
) -> ToolResult:
    """Company(stockCode).show(topic, asOf=asOf, ...) 호출 + asOf 메타데이터 보고.

    Args:
        stockCode: KR 6 자리 / US ticker.
        asOf: YYYY-MM-DD 또는 YYYYQn (예: "2024Q2"). *필수* — 누락 거부.
        topic: BS/IS/CF/CIS/SCE/ratios/dividend/companyOverview 등.
        market: "KR" (DART) 또는 "US" (EDGAR).
        block / period / freq / scope: Company.show 의 동일 인자.

    Returns:
        ToolResult — refs 안에 tableRef + asOf 메타. 본 도구는 LLM 이 *시점 누설 없는*
        분석을 강제하기 위함.
    """
    if not asOf or not str(asOf).strip():
        return ToolResult(
            ok=False,
            summary="LookAheadGuard 거부 — asOf 가 비어 있다. 시점 명시 필수.",
            error="lookahead_guard_missing_asof",
        )
    if not stockCode or not str(stockCode).strip():
        return ToolResult(
            ok=False,
            summary="LookAheadGuard 거부 — stockCode 가 비어 있다.",
            error="lookahead_guard_missing_stockcode",
        )

    try:
        from dartlab.company import Company

        kwargs = {"asOf": asOf, "freq": freq, "scope": scope}
        if block is not None:
            kwargs["block"] = block
        if period is not None:
            kwargs["period"] = period

        # market 은 stockCode 형식 (KR 6 자리 vs US ticker) 으로 auto-detect.
        # tool 의 market arg 는 advisory — provider 가 자체 분기.
        company = Company(stockCode)
        df = company.show(topic, **kwargs)
    except Exception as exc:  # noqa: BLE001 — 외부 provider 모든 예외 포착
        return ToolResult(
            ok=False,
            summary=f"LookAheadGuard 호출 실패 — {type(exc).__name__}: {str(exc)[:200]}",
            error="lookahead_guard_call_failed",
        )

    # 결과 직렬화 — DataFrame 이면 dicts, dict/list 면 그대로.
    rows: list[dict] = []
    columns: list[str] = []
    try:
        import polars as pl

        if isinstance(df, pl.DataFrame):
            rows = df.to_dicts()
            columns = df.columns
        elif isinstance(df, list):
            rows = [r if isinstance(r, dict) else {"value": r} for r in df]
            columns = list(rows[0].keys()) if rows else []
        elif isinstance(df, dict):
            rows = [df]
            columns = list(df.keys())
    except ImportError:
        rows = [{"raw": str(df)}] if df is not None else []

    refs: list[Ref] = []
    if rows:
        refs.append(
            Ref(
                id=f"table:lookahead:{stockCode}:{topic}:{asOf}",
                kind="tableRef",
                title=f"{stockCode} {topic} (asOf={asOf})",
                source="dartlab.providers.Company.show",
                payload={"rows": rows, "asOf": asOf, "topic": topic, "columns": columns},
            )
        )

    return ToolResult(
        ok=True,
        summary=f"asOf={asOf} 기준 {topic} {len(rows)} 행 (시점 이후 데이터 strip)",
        refs=refs,
        data={
            "stockCode": stockCode,
            "market": market,
            "topic": topic,
            "asOf": asOf,
            "rowCount": len(rows),
            "columns": columns,
        },
    )
