"""Generated-spec validated DartLab engine call tool."""

from __future__ import annotations

import logging
import os
import re
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any

import polars as pl

from dartlab.ai.contracts import Ref

from .formatting import formatMoney, formatPercent
from .types import ToolResult

_AUTO_GATHER_ENABLED = os.environ.get("DARTLAB_AUTO_GATHER", "1") not in {"0", "false", "False"}

_PERIOD_RE = re.compile(r"^\d{4}(?:Q[1-4])?$")
_STMT_LABELS = {"BS": "재무상태표", "IS": "손익계산서", "CF": "현금흐름표"}
# 컬럼 alias SSOT 는 dartlab.ai.tools.columnAlias 에 있다. 여기서는 priority list 만
# 호환 dict 로 변환해 사용 — IS/CF/BS 5+ 표준 컬럼 + 한국어 label.
from .columnAlias import topicAccountPriority as _topicAccountPriority

_ACCOUNT_PRIORITY = {
    "BS": _topicAccountPriority("BS"),
    "IS": _topicAccountPriority("IS"),
    "CF": _topicAccountPriority("CF"),
}


def engineCall(plan: dict[str, Any] | None = None, **kwargs: Any) -> ToolResult:
    """Validate and execute a public DartLab API call plan."""

    call_plan = dict(plan or kwargs or {})
    apiRef = _apiRef(call_plan)
    if not apiRef:
        return ToolResult(False, "apiRef를 확인하지 못했습니다.", error="missing_api_ref")
    if apiRef.startswith("_") or "._" in apiRef or "internal" in apiRef.lower():
        return ToolResult(False, f"private/internal API는 차단됩니다: {apiRef}", error="private_api_blocked")
    if not _capabilityExists(apiRef):
        return ToolResult(False, f"generated spec에 없는 API입니다: {apiRef}", error="unknown_api_ref")

    if apiRef == "Company.show":
        return _companyShow(call_plan)
    if apiRef in {"dartlab.scan", "scan"} or apiRef.startswith("scan."):
        if apiRef.startswith("scan.") and not call_plan.get("axis"):
            call_plan["axis"] = apiRef.split(".", 1)[1]
        return _scan(call_plan)
    if apiRef in {"dartlab.capabilities", "capabilities"}:
        return _capabilities(call_plan)
    return _genericPublicCall(apiRef, call_plan)


def _apiRef(plan: dict[str, Any]) -> str:
    if plan.get("apiRef"):
        return str(plan["apiRef"])
    engine = str(plan.get("engine") or "").strip()
    method = str(plan.get("method") or "").strip()
    if engine.lower() == "company" and method:
        return f"Company.{method}"
    if engine.lower() == "dartlab" and method:
        return f"dartlab.{method}"
    return ""


def _capabilityExists(apiRef: str) -> bool:
    from dartlab.core.capability._generated import CAPABILITIES

    return apiRef in CAPABILITIES


def _companyShow(plan: dict[str, Any]) -> ToolResult:
    target = str(plan.get("target") or plan.get("stockCode") or "").strip()
    args = list(plan.get("args") or [])
    kwargs = dict(plan.get("kwargs") or {})
    topic = str(plan.get("topic") or (args[0] if args else "") or kwargs.get("topic") or "").strip() or "BS"
    topic = _normalizeStatement(topic)
    if topic not in _STMT_LABELS:
        return _genericCompanyMethod("show", target, [topic], {})
    company = _resolveCompany(target or str(plan.get("question") or ""))
    if company is None:
        return ToolResult(
            False,
            "종목을 먼저 특정해야 재무제표를 확인할 수 있습니다. 예: `삼성전자 재무상태표 확인`",
            error="company_not_resolved",
        )
    companyName = str(getattr(company, "corpName", None) or getattr(company, "name", None) or "")
    stockCode = str(getattr(company, "stockCode", None) or target or "")
    with _quietExecutionNoise():
        table = company.show(topic)
    auto_gather_used = False
    if (not isinstance(table, pl.DataFrame) or table.height == 0) and _AUTO_GATHER_ENABLED:
        if _tryAutoUpdate(company, "finance"):
            auto_gather_used = True
            with _quietExecutionNoise():
                table = company.show(topic)
    if not isinstance(table, pl.DataFrame) or table.height == 0:
        msg = f"{companyName or stockCode} {topic} 데이터를 찾지 못했습니다."
        if auto_gather_used:
            msg += " (자동 update 후에도 빈 결과 — 미공시 분기 또는 폐상장 가능성)."
        return ToolResult(False, msg, error="empty_result")
    summary = _summarizeStatement(topic, table)
    if not summary:
        return ToolResult(
            False, f"{companyName or stockCode} {topic} 표를 요약하지 못했습니다.", error="unreadable_table"
        )
    table_ref = Ref(
        id=f"table:{stockCode}:{topic}:{summary['latestPeriod']}",
        kind="tableRef",
        title=f"{companyName or stockCode} {_STMT_LABELS[topic]} {summary['latestPeriod']}",
        source=f"Company({stockCode}).show('{topic}')",
        payload=summary,
    )
    refs = [table_ref]
    refs.extend(
        Ref(
            id=f"value:{stockCode}:{topic}:{summary['latestPeriod']}:{row['snakeId']}",
            kind="valueRef",
            title=f"{row['item']} {summary['latestPeriod']}",
            source=table_ref.id,
            payload=row,
        )
        for row in summary["rows"]
    )
    refs.append(
        Ref(
            id=f"date:{stockCode}:{topic}:{summary['latestPeriod']}",
            kind="dateRef",
            title=f"{_STMT_LABELS[topic]} 기준시점",
            source=table_ref.id,
            payload={"period": summary["latestPeriod"]},
        )
    )
    summary_msg = f"{companyName or stockCode} {_STMT_LABELS[topic]} {summary['latestPeriod']} 확인"
    if auto_gather_used:
        summary_msg += " (자동 update 후 재조회 성공)"
    return ToolResult(
        True,
        summary_msg,
        refs=refs,
        data={
            "companyName": companyName,
            "stockCode": stockCode,
            "statement": topic,
            "label": _STMT_LABELS[topic],
            "summary": summary,
            "markdown": _statementMarkdown(companyName, stockCode, topic, summary),
            "autoGatherUsed": auto_gather_used,
        },
    )


def _tryAutoUpdate(company: Any, category: str) -> bool:
    """company.update(categories=[category]) 자동 호출. 예외/지연 발생 시 False.

    실패 정책: 어떤 예외든 잡아서 False 반환 (호출자가 기존 empty_result 처리).
    DART API 호출이라 5~30s 소요 가능 — 환경에 따라 timeout 보호 필요 시 별도 thread/signal.
    """
    if not hasattr(company, "update"):
        return False
    try:
        with _quietExecutionNoise():
            result = company.update(categories=[category])
        if isinstance(result, dict):
            return any(v > 0 for v in result.values() if isinstance(v, int))
    except Exception as exc:
        logging.getLogger(__name__).debug("auto_gather update failed: %s", exc)
        return False
    return False


def _scan(plan: dict[str, Any]) -> ToolResult:
    axis = str(plan.get("axis") or plan.get("target") or (plan.get("args") or [""])[0] or "").strip() or "growth"
    import dartlab

    with _quietExecutionNoise():
        result = dartlab.scan(axis)
    if not isinstance(result, pl.DataFrame) or result.height == 0:
        return ToolResult(False, f"dartlab.scan('{axis}') 결과가 비어 있습니다.", error="empty_scan")
    if axis.lower() == "growth" or "성장" in axis:
        rows = _rankGrowthRows(result)
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
                "markdown": _growthMarkdown(result.height, rows),
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
    markdown = _capabilitiesMarkdown(data, path=path)
    ref = Ref(
        id=f"api:dartlab.capabilities:{path or 'root'}",
        kind="apiRef",
        title="dartlab.capabilities",
        source="dartlab.capabilities",
        payload={"path": path, "preview": str(data)[:4000]},
    )
    return ToolResult(True, "capabilities 조회 완료", refs=[ref], data={"result": str(data), "markdown": markdown})


def _capabilitiesMarkdown(data: Any, *, path: str = "") -> str:
    title = f"DartLab {path} 기능을 확인했습니다." if path else "DartLab이 할 수 있는 일을 확인했습니다."
    lines = [title, ""]
    if isinstance(data, dict):
        items = _capabilityItems(data, path=path)
        for key, value in items:
            if isinstance(value, dict):
                summary = value.get("summary") or value.get("guide") or ""
            else:
                summary = str(value)
            lines.append(f"- {key}: {_publicCapabilitySummary(summary)}")
    elif isinstance(data, list):
        for item in [item for item in data if _publicCapabilityKey(str(item))][:12]:
            lines.append(f"- {item}")
    else:
        lines.append(str(data)[:800])
    lines.append("")
    lines.append("이 결과는 generated capability/docstring 카탈로그를 근거로 한 기능 안내입니다.")
    return "\n".join(lines)


def _capabilityItems(data: dict[str, Any], *, path: str = "") -> list[tuple[str, Any]]:
    if path:
        return [(key, value) for key, value in data.items() if _publicCapabilityKey(str(key))][:12]
    preferred = ["Company", "scan", "analysis", "macro", "gather", "quant", "credit", "story"]
    picked = [(key, data[key]) for key in preferred if key in data and _publicCapabilityKey(key)]
    if len(picked) >= 6:
        return picked
    for key, value in data.items():
        if len(picked) >= 12:
            break
        if key in {item[0] for item in picked} or not _publicCapabilityKey(str(key)):
            continue
        picked.append((key, value))
    return picked


def _publicCapabilityKey(key: str) -> bool:
    lowered = key.lower()
    if lowered in {"ask", "company.ask", "chartresult"}:
        return False
    if lowered.startswith("aicontract.") or "._" in lowered or lowered.startswith("_"):
        return False
    return True


def _publicCapabilitySummary(value: Any) -> str:
    text = str(value or "").splitlines()[0]
    text = text.replace(" — 내부 구현", "").replace("(내부 구현)", "").replace("**", "")
    return text[:180]


def _genericPublicCall(apiRef: str, plan: dict[str, Any]) -> ToolResult:
    if apiRef.startswith("Company."):
        return _genericCompanyMethod(
            apiRef.split(".", 1)[1],
            str(plan.get("target") or plan.get("stockCode") or ""),
            list(plan.get("args") or []),
            dict(plan.get("kwargs") or {}),
        )
    if apiRef.startswith("dartlab.") or "." not in apiRef:
        import dartlab

        method = apiRef.split(".", 1)[1] if apiRef.startswith("dartlab.") else apiRef
        if method.startswith("_") or not hasattr(dartlab, method):
            return ToolResult(False, f"공개 dartlab API를 찾지 못했습니다: {apiRef}", error="unknown_api_ref")
        func = getattr(dartlab, method)
        if not callable(func):
            return ToolResult(False, f"호출 가능한 API가 아닙니다: {apiRef}", error="not_callable")
        result = func(*list(plan.get("args") or []), **dict(plan.get("kwargs") or {}))
        return _resultToRefs(apiRef, result)
    return ToolResult(False, f"지원하지 않는 apiRef입니다: {apiRef}", error="unsupported_api_ref")


def _genericCompanyMethod(method: str, target: str, args: list[Any], kwargs: dict[str, Any]) -> ToolResult:
    company = _resolveCompany(target)
    if company is None:
        return ToolResult(False, "종목을 먼저 특정해야 Company API를 호출할 수 있습니다.", error="company_not_resolved")
    if method.startswith("_") or not hasattr(company, method):
        return ToolResult(False, f"공개 Company API를 찾지 못했습니다: Company.{method}", error="unknown_api_ref")
    func = getattr(company, method)
    if not callable(func):
        return ToolResult(False, f"호출 가능한 API가 아닙니다: Company.{method}", error="not_callable")
    with _quietExecutionNoise():
        result = func(*args, **kwargs)
    return _resultToRefs(f"Company.{method}", result, target=str(getattr(company, "stockCode", None) or target))


def _resultToRefs(apiRef: str, result: Any, *, target: str = "") -> ToolResult:
    if isinstance(result, pl.DataFrame):
        table_ref = Ref(
            id=f"table:{apiRef}:{target or 'result'}",
            kind="tableRef",
            title=f"{apiRef} result",
            source=apiRef,
            payload={"rowCount": result.height, "columns": list(result.columns), "rows": result.head(20).to_dicts()},
        )
        return ToolResult(
            True,
            f"{apiRef} 실행 완료",
            refs=[table_ref],
            data={"rowCount": result.height, "columns": list(result.columns)},
        )
    ref = Ref(
        id=f"execution:{apiRef}:{target or 'result'}",
        kind="executionRef",
        title=f"{apiRef} result",
        source=apiRef,
        payload={"preview": str(result)[:4000]},
    )
    return ToolResult(True, f"{apiRef} 실행 완료", refs=[ref], data={"result": str(result)})


def _resolveCompany(target: str):
    target = str(target or "").strip()
    if target:
        import dartlab

        try:
            with _quietExecutionNoise():
                return dartlab.Company(target)
        except (OSError, RuntimeError, TypeError, ValueError):
            pass
        from dartlab.company import resolveFromText

        try:
            with _quietExecutionNoise():
                company, _ = resolveFromText(target)
                return company
        except (OSError, RuntimeError, TypeError, ValueError):
            return None
    return None


def _normalizeStatement(value: str) -> str:
    q = str(value or "").strip().lower()
    if q in {"bs", "balance sheet", "재무상태표", "자산", "부채", "자본"}:
        return "BS"
    if q in {"is", "income statement", "손익계산서", "손익", "이익"}:
        return "IS"
    if q in {"cf", "cash flow", "현금흐름표", "현금흐름"}:
        return "CF"
    return str(value or "").strip()


def _summarizeStatement(statement: str, table: pl.DataFrame) -> dict[str, Any] | None:
    periods = [col for col in table.columns if _PERIOD_RE.match(str(col))]
    if not periods:
        return None
    latest = periods[0]
    rows = _selectRows(statement, table, latest)
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


def _selectRows(statement: str, table: pl.DataFrame, period: str) -> list[dict[str, Any]]:
    if "snakeId" not in table.columns or period not in table.columns:
        return []
    labelCol = "항목" if "항목" in table.columns else table.columns[0]
    table_rows = table.select(["snakeId", labelCol, period]).to_dicts()
    available = {str(row["snakeId"]): row for row in table_rows}
    rows: list[dict[str, Any]] = []
    used: set[str] = set()
    for snakeId, label in _ACCOUNT_PRIORITY[statement]:
        row = available.get(snakeId) or _findRowByLabel(table_rows, label, used, labelCol=labelCol)
        if row is None:
            continue
        resolved_snake = str(row.get("snakeId") or snakeId)
        if resolved_snake in used:
            continue
        value = row.get(period)
        if value is None:
            continue
        used.add(resolved_snake)
        rows.append(
            {
                "snakeId": resolved_snake,
                "item": str(row.get(labelCol) or snakeId),
                "period": period,
                "value": value,
                "formatted": formatMoney(value),
            }
        )
        if len(rows) >= (10 if statement == "BS" else 8):
            break
    return rows


def _findRowByLabel(rows: list[dict[str, Any]], label: str, used: set[str], *, labelCol: str) -> dict[str, Any] | None:
    compact_label = _compact(label)
    for row in rows:
        snakeId = str(row.get("snakeId") or "")
        if snakeId in used:
            continue
        item = _compact(str(row.get(labelCol) or ""))
        if compact_label and compact_label in item:
            return row
    return None


def _compact(text: str) -> str:
    return re.sub(r"[\s,()\-_/·]", "", text)


def _statementMarkdown(companyName: str, stockCode: str, statement: str, summary: dict[str, Any]) -> str:
    display = f"{companyName}({stockCode})" if companyName and stockCode else companyName or stockCode
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


def _rankGrowthRows(df: pl.DataFrame) -> list[dict[str, Any]]:
    required = {"종목코드", "종목명", "매출CAGR", "영업이익CAGR", "순이익CAGR", "등급", "패턴"}
    if not required <= set(df.columns):
        return []
    scored: list[dict[str, Any]] = []
    for row in df.to_dicts():
        values = [_toFloat(row.get(col)) for col in ("매출CAGR", "영업이익CAGR", "순이익CAGR")]
        valid = [value for value in values if value is not None]
        revenue = _toFloat(row.get("revenue"))
        years = _toFloat(row.get("years"))
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
                "revenue": formatMoney(row.get("revenue")),
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


def _growthMarkdown(rowCount: int, rows: list[dict[str, Any]]) -> str:
    lines = [f'`dartlab.scan("growth")`로 {rowCount:,}개 기업의 성장성 스캔을 확인했습니다.', ""]
    lines.append("| 순위 | 기업 | 매출CAGR | 영업이익CAGR | 순이익CAGR | 등급 | 패턴 |")
    lines.append("|---:|---|---:|---:|---:|---|---|")
    for idx, row in enumerate(rows, start=1):
        lines.append(
            f"| {idx} | {row['name']}({row['stockCode']}) | {formatPercent(row['salesCagr'])} | {formatPercent(row['operatingProfitCagr'])} | {formatPercent(row['netProfitCagr'])} | {row['grade']} | {row['pattern']} |"
        )
    lines.append("")
    lines.append(
        "이 표는 후보 발굴 단계입니다. 투자 판단으로 확정하려면 각 후보를 Company/analysis/quant로 다시 검증해야 합니다."
    )
    lines.append("근거는 scan growth datasetRef, tableRef, valueRef로 남겼습니다.")
    return "\n".join(lines)


def _toFloat(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


@contextmanager
def _quietExecutionNoise():
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
