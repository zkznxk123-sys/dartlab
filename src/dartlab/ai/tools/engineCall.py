"""Generated-spec validated DartLab engine call tool."""

from __future__ import annotations

import logging
import re
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any

import polars as pl

from dartlab.ai.contracts import Ref

from .formatting import format_money, format_percent
from .types import ToolResult

_PERIOD_RE = re.compile(r"^\d{4}(?:Q[1-4])?$")
_STMT_LABELS = {"BS": "재무상태표", "IS": "손익계산서", "CF": "현금흐름표"}
_ACCOUNT_PRIORITY = {
    "BS": (
        ("cash_and_cash_equivalents", "현금및현금성자산"),
        ("shortterm_financial_instruments", "단기금융상품"),
        ("accounts_receivable", "매출채권"),
        ("inventories", "재고자산"),
        ("current_assets", "유동자산"),
        ("total_assets", "자산총계"),
        ("current_liabilities", "유동부채"),
        ("total_liabilities", "부채총계"),
        ("owners_of_parent_equity", "지배주주지분"),
        ("total_stockholders_equity", "자본총계"),
        ("total_equity", "자본총계"),
    ),
    "IS": (
        ("sales", "매출액"),
        ("revenue", "매출액"),
        ("gross_profit", "매출총이익"),
        ("operating_profit", "영업이익"),
        ("operating_income", "영업이익"),
        ("profit_before_tax", "법인세차감전순이익"),
        ("net_profit", "당기순이익"),
        ("net_income", "당기순이익"),
    ),
    "CF": (
        ("operating_cashflow", "영업활동현금흐름"),
        ("cash_flows_from_operating_activities", "영업활동현금흐름"),
        ("investing_cashflow", "투자활동현금흐름"),
        ("cash_flows_from_investing_activities", "투자활동현금흐름"),
        ("financing_cashflow", "재무활동현금흐름"),
        ("cash_flows_from_financing_activities", "재무활동현금흐름"),
        ("purchase_of_property_plant_and_equipment", "유형자산의취득"),
        ("capital_expenditures", "유형자산의취득"),
        ("dividends_paid", "배당금지급"),
    ),
}


def engineCall(plan: dict[str, Any] | None = None, **kwargs: Any) -> ToolResult:
    """Validate and execute a public DartLab API call plan."""

    call_plan = dict(plan or kwargs or {})
    api_ref = _api_ref(call_plan)
    if not api_ref:
        return ToolResult(False, "apiRef를 확인하지 못했습니다.", error="missing_api_ref")
    if api_ref.startswith("_") or "._" in api_ref or "internal" in api_ref.lower():
        return ToolResult(False, f"private/internal API는 차단됩니다: {api_ref}", error="private_api_blocked")
    if not _capability_exists(api_ref):
        return ToolResult(False, f"generated spec에 없는 API입니다: {api_ref}", error="unknown_api_ref")

    if api_ref == "Company.show":
        return _company_show(call_plan)
    if api_ref in {"dartlab.scan", "scan"} or api_ref.startswith("scan."):
        if api_ref.startswith("scan.") and not call_plan.get("axis"):
            call_plan["axis"] = api_ref.split(".", 1)[1]
        return _scan(call_plan)
    if api_ref in {"dartlab.capabilities", "capabilities"}:
        return _capabilities(call_plan)
    return _generic_public_call(api_ref, call_plan)


def _api_ref(plan: dict[str, Any]) -> str:
    if plan.get("apiRef"):
        return str(plan["apiRef"])
    engine = str(plan.get("engine") or "").strip()
    method = str(plan.get("method") or "").strip()
    if engine.lower() == "company" and method:
        return f"Company.{method}"
    if engine.lower() == "dartlab" and method:
        return f"dartlab.{method}"
    return ""


def _capability_exists(api_ref: str) -> bool:
    from dartlab.core._generated import CAPABILITIES

    return api_ref in CAPABILITIES


def _company_show(plan: dict[str, Any]) -> ToolResult:
    target = str(plan.get("target") or plan.get("stockCode") or "").strip()
    args = list(plan.get("args") or [])
    kwargs = dict(plan.get("kwargs") or {})
    topic = str(plan.get("topic") or (args[0] if args else "") or kwargs.get("topic") or "").strip() or "BS"
    topic = _normalize_statement(topic)
    if topic not in _STMT_LABELS:
        return _generic_company_method("show", target, [topic], {})
    company = _resolve_company(target or str(plan.get("question") or ""))
    if company is None:
        return ToolResult(
            False,
            "종목을 먼저 특정해야 재무제표를 확인할 수 있습니다. 예: `삼성전자 재무상태표 확인`",
            error="company_not_resolved",
        )
    company_name = str(getattr(company, "corpName", None) or getattr(company, "name", None) or "")
    stock_code = str(getattr(company, "stockCode", None) or target or "")
    with _quiet_execution_noise():
        table = company.show(topic)
    if not isinstance(table, pl.DataFrame) or table.height == 0:
        return ToolResult(
            False, f"{company_name or stock_code} {topic} 데이터를 찾지 못했습니다.", error="empty_result"
        )
    summary = _summarize_statement(topic, table)
    if not summary:
        return ToolResult(
            False, f"{company_name or stock_code} {topic} 표를 요약하지 못했습니다.", error="unreadable_table"
        )
    table_ref = Ref(
        id=f"table:{stock_code}:{topic}:{summary['latestPeriod']}",
        kind="tableRef",
        title=f"{company_name or stock_code} {_STMT_LABELS[topic]} {summary['latestPeriod']}",
        source=f"Company({stock_code}).show('{topic}')",
        payload=summary,
    )
    refs = [table_ref]
    refs.extend(
        Ref(
            id=f"value:{stock_code}:{topic}:{summary['latestPeriod']}:{row['snakeId']}",
            kind="valueRef",
            title=f"{row['item']} {summary['latestPeriod']}",
            source=table_ref.id,
            payload=row,
        )
        for row in summary["rows"]
    )
    refs.append(
        Ref(
            id=f"date:{stock_code}:{topic}:{summary['latestPeriod']}",
            kind="dateRef",
            title=f"{_STMT_LABELS[topic]} 기준시점",
            source=table_ref.id,
            payload={"period": summary["latestPeriod"]},
        )
    )
    return ToolResult(
        True,
        f"{company_name or stock_code} {_STMT_LABELS[topic]} {summary['latestPeriod']} 확인",
        refs=refs,
        data={
            "companyName": company_name,
            "stockCode": stock_code,
            "statement": topic,
            "label": _STMT_LABELS[topic],
            "summary": summary,
            "markdown": _statement_markdown(company_name, stock_code, topic, summary),
        },
    )


def _scan(plan: dict[str, Any]) -> ToolResult:
    axis = str(plan.get("axis") or plan.get("target") or (plan.get("args") or [""])[0] or "").strip() or "growth"
    import dartlab

    with _quiet_execution_noise():
        result = dartlab.scan(axis)
    if not isinstance(result, pl.DataFrame) or result.height == 0:
        return ToolResult(False, f"dartlab.scan('{axis}') 결과가 비어 있습니다.", error="empty_scan")
    if axis.lower() == "growth" or "성장" in axis:
        rows = _rank_growth_rows(result)
        if not rows:
            return ToolResult(
                False,
                "growth scan은 실행됐지만 순위를 만들 핵심 지표가 부족합니다.",
                error="scan_growth_no_rankable_rows",
            )
        dataset_ref = Ref(
            id="dataset:scan:growth",
            kind="datasetRef",
            title="scan growth universe",
            source='dartlab.scan("growth")',
            payload={"rowCount": result.height, "columns": list(result.columns)},
        )
        table_ref = Ref(
            id="table:scan:growth:top",
            kind="tableRef",
            title="성장성 상위 후보",
            source=dataset_ref.id,
            payload={"axis": "growth", "rows": rows, "filter": "매출/영업이익/순이익 CAGR + 매출 규모 + 기간"},
        )
        refs = [dataset_ref, table_ref]
        refs.extend(
            Ref(
                id=f"value:scan:growth:{row['stockCode']}:score",
                kind="valueRef",
                title=f"{row['name']} growth score",
                source=table_ref.id,
                payload=row,
            )
            for row in rows
        )
        return ToolResult(
            True,
            f"growth scan 후보 {len(rows)}개",
            refs=refs,
            data={
                "axis": "growth",
                "rowCount": result.height,
                "rows": rows,
                "markdown": _growth_markdown(result.height, rows),
            },
        )
    table_ref = Ref(
        id=f"table:scan:{axis}:preview",
        kind="tableRef",
        title=f"scan {axis} preview",
        source=f"dartlab.scan('{axis}')",
        payload={"rowCount": result.height, "columns": list(result.columns), "rows": result.head(10).to_dicts()},
    )
    return ToolResult(
        True,
        f"scan {axis} 실행 완료",
        refs=[table_ref],
        data={"rowCount": result.height, "columns": list(result.columns)},
    )


def _capabilities(plan: dict[str, Any]) -> ToolResult:
    import dartlab

    args = list(plan.get("args") or [])
    path = str(plan.get("path") or (args[0] if args else "") or "").strip()
    data = dartlab.capabilities(path) if path else dartlab.capabilities()
    markdown = _capabilities_markdown(data, path=path)
    ref = Ref(
        id=f"api:dartlab.capabilities:{path or 'root'}",
        kind="apiRef",
        title="dartlab.capabilities",
        source="dartlab.capabilities",
        payload={"path": path, "preview": str(data)[:4000]},
    )
    return ToolResult(True, "capabilities 조회 완료", refs=[ref], data={"result": str(data), "markdown": markdown})


def _capabilities_markdown(data: Any, *, path: str = "") -> str:
    title = f"DartLab {path} 기능을 확인했습니다." if path else "DartLab이 할 수 있는 일을 확인했습니다."
    lines = [title, ""]
    if isinstance(data, dict):
        items = _capability_items(data, path=path)
        for key, value in items:
            if isinstance(value, dict):
                summary = value.get("summary") or value.get("guide") or ""
            else:
                summary = str(value)
            lines.append(f"- {key}: {_public_capability_summary(summary)}")
    elif isinstance(data, list):
        for item in [item for item in data if _public_capability_key(str(item))][:12]:
            lines.append(f"- {item}")
    else:
        lines.append(str(data)[:800])
    lines.append("")
    lines.append("이 결과는 generated capability/docstring 카탈로그를 근거로 한 기능 안내입니다.")
    return "\n".join(lines)


def _capability_items(data: dict[str, Any], *, path: str = "") -> list[tuple[str, Any]]:
    if path:
        return [(key, value) for key, value in data.items() if _public_capability_key(str(key))][:12]
    preferred = ["Company", "scan", "analysis", "macro", "gather", "quant", "credit", "story"]
    picked = [(key, data[key]) for key in preferred if key in data and _public_capability_key(key)]
    if len(picked) >= 6:
        return picked
    for key, value in data.items():
        if len(picked) >= 12:
            break
        if key in {item[0] for item in picked} or not _public_capability_key(str(key)):
            continue
        picked.append((key, value))
    return picked


def _public_capability_key(key: str) -> bool:
    lowered = key.lower()
    if lowered in {"ask", "company.ask", "chartresult"}:
        return False
    if lowered.startswith("aicontract.") or "._" in lowered or lowered.startswith("_"):
        return False
    return True


def _public_capability_summary(value: Any) -> str:
    text = str(value or "").splitlines()[0]
    text = text.replace(" — 내부 구현", "").replace("(내부 구현)", "").replace("**", "")
    return text[:180]


def _generic_public_call(api_ref: str, plan: dict[str, Any]) -> ToolResult:
    if api_ref.startswith("Company."):
        return _generic_company_method(
            api_ref.split(".", 1)[1],
            str(plan.get("target") or plan.get("stockCode") or ""),
            list(plan.get("args") or []),
            dict(plan.get("kwargs") or {}),
        )
    if api_ref.startswith("dartlab.") or "." not in api_ref:
        import dartlab

        method = api_ref.split(".", 1)[1] if api_ref.startswith("dartlab.") else api_ref
        if method.startswith("_") or not hasattr(dartlab, method):
            return ToolResult(False, f"공개 dartlab API를 찾지 못했습니다: {api_ref}", error="unknown_api_ref")
        func = getattr(dartlab, method)
        if not callable(func):
            return ToolResult(False, f"호출 가능한 API가 아닙니다: {api_ref}", error="not_callable")
        result = func(*list(plan.get("args") or []), **dict(plan.get("kwargs") or {}))
        return _result_to_refs(api_ref, result)
    return ToolResult(False, f"지원하지 않는 apiRef입니다: {api_ref}", error="unsupported_api_ref")


def _generic_company_method(method: str, target: str, args: list[Any], kwargs: dict[str, Any]) -> ToolResult:
    company = _resolve_company(target)
    if company is None:
        return ToolResult(False, "종목을 먼저 특정해야 Company API를 호출할 수 있습니다.", error="company_not_resolved")
    if method.startswith("_") or not hasattr(company, method):
        return ToolResult(False, f"공개 Company API를 찾지 못했습니다: Company.{method}", error="unknown_api_ref")
    func = getattr(company, method)
    if not callable(func):
        return ToolResult(False, f"호출 가능한 API가 아닙니다: Company.{method}", error="not_callable")
    with _quiet_execution_noise():
        result = func(*args, **kwargs)
    return _result_to_refs(f"Company.{method}", result, target=str(getattr(company, "stockCode", None) or target))


def _result_to_refs(api_ref: str, result: Any, *, target: str = "") -> ToolResult:
    if isinstance(result, pl.DataFrame):
        table_ref = Ref(
            id=f"table:{api_ref}:{target or 'result'}",
            kind="tableRef",
            title=f"{api_ref} result",
            source=api_ref,
            payload={"rowCount": result.height, "columns": list(result.columns), "rows": result.head(20).to_dicts()},
        )
        return ToolResult(
            True,
            f"{api_ref} 실행 완료",
            refs=[table_ref],
            data={"rowCount": result.height, "columns": list(result.columns)},
        )
    ref = Ref(
        id=f"execution:{api_ref}:{target or 'result'}",
        kind="executionRef",
        title=f"{api_ref} result",
        source=api_ref,
        payload={"preview": str(result)[:4000]},
    )
    return ToolResult(True, f"{api_ref} 실행 완료", refs=[ref], data={"result": str(result)})


def _resolve_company(target: str):
    target = str(target or "").strip()
    if target:
        import dartlab

        try:
            with _quiet_execution_noise():
                return dartlab.Company(target)
        except (OSError, RuntimeError, TypeError, ValueError):
            pass
        from dartlab.core.resolve import resolve_from_text

        try:
            with _quiet_execution_noise():
                company, _ = resolve_from_text(target)
                return company
        except (OSError, RuntimeError, TypeError, ValueError):
            return None
    return None


def _normalize_statement(value: str) -> str:
    q = str(value or "").strip().lower()
    if q in {"bs", "balance sheet", "재무상태표", "자산", "부채", "자본"}:
        return "BS"
    if q in {"is", "income statement", "손익계산서", "손익", "이익"}:
        return "IS"
    if q in {"cf", "cash flow", "현금흐름표", "현금흐름"}:
        return "CF"
    return str(value or "").strip()


def _summarize_statement(statement: str, table: pl.DataFrame) -> dict[str, Any] | None:
    periods = [col for col in table.columns if _PERIOD_RE.match(str(col))]
    if not periods:
        return None
    latest = periods[0]
    rows = _select_rows(statement, table, latest)
    if not rows:
        return None
    return {
        "statement": statement,
        "label": _STMT_LABELS[statement],
        "latestPeriod": latest,
        "rowCount": table.height,
        "columnCount": len(table.columns),
        "rows": rows,
    }


def _select_rows(statement: str, table: pl.DataFrame, period: str) -> list[dict[str, Any]]:
    if "snakeId" not in table.columns or period not in table.columns:
        return []
    label_col = "항목" if "항목" in table.columns else table.columns[0]
    table_rows = table.select(["snakeId", label_col, period]).to_dicts()
    available = {str(row["snakeId"]): row for row in table_rows}
    rows: list[dict[str, Any]] = []
    used: set[str] = set()
    for snake_id, label in _ACCOUNT_PRIORITY[statement]:
        row = available.get(snake_id) or _find_row_by_label(table_rows, label, used, label_col=label_col)
        if row is None:
            continue
        resolved_snake = str(row.get("snakeId") or snake_id)
        if resolved_snake in used:
            continue
        value = row.get(period)
        if value is None:
            continue
        used.add(resolved_snake)
        rows.append(
            {
                "snakeId": resolved_snake,
                "item": str(row.get(label_col) or snake_id),
                "period": period,
                "value": value,
                "formatted": format_money(value),
            }
        )
        if len(rows) >= (10 if statement == "BS" else 8):
            break
    return rows


def _find_row_by_label(
    rows: list[dict[str, Any]], label: str, used: set[str], *, label_col: str
) -> dict[str, Any] | None:
    compact_label = _compact(label)
    for row in rows:
        snake_id = str(row.get("snakeId") or "")
        if snake_id in used:
            continue
        item = _compact(str(row.get(label_col) or ""))
        if compact_label and compact_label in item:
            return row
    return None


def _compact(text: str) -> str:
    return re.sub(r"[\s,()\-_/·]", "", text)


def _statement_markdown(company_name: str, stock_code: str, statement: str, summary: dict[str, Any]) -> str:
    display = f"{company_name}({stock_code})" if company_name and stock_code else company_name or stock_code
    lines = [
        f"{display} {_STMT_LABELS[statement]}를 확인했습니다.",
        "",
        f"## {_STMT_LABELS[statement]} ({summary['latestPeriod']})",
        "| 항목 | 값 |",
        "|---|---:|",
    ]
    for row in summary["rows"]:
        lines.append(f"| {row['item']} | {row['formatted']} |")
    lines.append("")
    lines.append("근거는 tableRef, valueRef, dateRef로 남겼습니다.")
    return "\n".join(lines)


def _rank_growth_rows(df: pl.DataFrame) -> list[dict[str, Any]]:
    required = {"종목코드", "종목명", "매출CAGR", "영업이익CAGR", "순이익CAGR", "등급", "패턴"}
    if not required <= set(df.columns):
        return []
    scored: list[dict[str, Any]] = []
    for row in df.to_dicts():
        values = [_to_float(row.get(col)) for col in ("매출CAGR", "영업이익CAGR", "순이익CAGR")]
        valid = [value for value in values if value is not None]
        revenue = _to_float(row.get("revenue"))
        years = _to_float(row.get("years"))
        if len(valid) < 3 or any(value <= 10 for value in valid):
            continue
        if revenue is None or revenue < 100_000_000_000:
            continue
        if years is not None and years < 3:
            continue
        score = sum(valid) / len(valid)
        scored.append(
            {
                "stockCode": str(row.get("종목코드") or ""),
                "name": str(row.get("종목명") or ""),
                "revenue": format_money(row.get("revenue")),
                "salesCagr": values[0],
                "operatingProfitCagr": values[1],
                "netProfitCagr": values[2],
                "years": row.get("years"),
                "grade": str(row.get("등급") or ""),
                "pattern": str(row.get("패턴") or ""),
                "score": round(score, 2),
            }
        )
    scored.sort(key=lambda item: (item["score"], item["salesCagr"] or -9999), reverse=True)
    return scored[:5]


def _growth_markdown(row_count: int, rows: list[dict[str, Any]]) -> str:
    lines = [f'`dartlab.scan("growth")`로 {row_count:,}개 기업의 성장성 스캔을 확인했습니다.', ""]
    lines.append("| 순위 | 기업 | 매출CAGR | 영업이익CAGR | 순이익CAGR | 등급 | 패턴 |")
    lines.append("|---:|---|---:|---:|---:|---|---|")
    for idx, row in enumerate(rows, start=1):
        lines.append(
            f"| {idx} | {row['name']}({row['stockCode']}) | {format_percent(row['salesCagr'])} | {format_percent(row['operatingProfitCagr'])} | {format_percent(row['netProfitCagr'])} | {row['grade']} | {row['pattern']} |"
        )
    lines.append("")
    lines.append(
        "이 표는 후보 발굴 단계입니다. 투자 판단으로 확정하려면 각 후보를 Company/analysis/quant로 다시 검증해야 합니다."
    )
    lines.append("근거는 scan growth datasetRef, tableRef, valueRef로 남겼습니다.")
    return "\n".join(lines)


def _to_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


@contextmanager
def _quiet_execution_noise():
    noisy_loggers = [logging.getLogger("dartlab.providers.dart.finance.pivot")]
    previous = [(logger, logger.disabled, logger.level) for logger in noisy_loggers]
    try:
        for logger in noisy_loggers:
            logger.disabled = True
            logger.setLevel(logging.CRITICAL + 1)
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            yield
    finally:
        for logger, disabled, level in previous:
            logger.disabled = disabled
            logger.setLevel(level)
