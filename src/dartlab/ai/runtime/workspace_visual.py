"""Visual explanation contract for workspace-native AI responses."""

from __future__ import annotations

from typing import Any

from dartlab.ai.runtime.workspace_session import AgentSession, _json_safe


def requiresCsvArtifact(question: str) -> bool:
    q = question.lower()
    return any(word in q for word in ("찾", "랭킹", "순위", "상승", "오른", "강세")) and any(
        word in q for word in ("주가", "지수", "종목", "수익률", "가격")
    )


def requiresVisualExplanation(question: str) -> bool:
    q = question.lower()
    return any(word in q for word in ("랭킹", "순위", "상승", "오른", "강세", "비교", "추세", "시계열"))


def isMeaningfulVisualSpec(spec: dict[str, Any]) -> bool:
    """Return True only for visuals that explain more than one datapoint."""
    if str(spec.get("vizType") or "chart") == "diagram":
        return bool(str(spec.get("source") or "").strip())
    metric = str(spec.get("metric") or "").lower()
    if _is_placeholder_key(metric):
        return False
    categories = [str(v).strip() for v in spec.get("categories") or [] if str(v).strip()]
    if len(categories) < 2 or len(set(categories)) < 2:
        return False
    series = spec.get("series")
    if not isinstance(series, list):
        return False
    for row in series:
        data = row.get("data") if isinstance(row, dict) else None
        if not isinstance(data, list):
            continue
        numeric = [_number(v) for v in data[: len(categories)]]
        numeric = [v for v in numeric if v is not None]
        if len(numeric) >= 2 and not _looks_like_placeholder_values(row, numeric):
            return True
    return False


def hasDegenerateVisual(session: AgentSession) -> bool:
    return any(not isMeaningfulVisualSpec(item.get("spec") or {}) for item in session.visuals)


def autoVisualFromRows(session: AgentSession, rows: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    if not requiresVisualExplanation(session.question):
        return None
    category_key = _pick_category_key(rows)
    value_key = _pick_numeric_key(rows)
    if not category_key or not value_key:
        return None
    selected: list[tuple[str, float]] = []
    for row in rows[:12]:
        label = str(row.get(category_key) or "").strip()
        value = _number(row.get(value_key))
        if label and value is not None:
            selected.append((label, value))
    if len(selected) < 2:
        return None
    spec = {
        "vizType": "chart",
        "chartType": "bar",
        "purpose": "ranking" if requiresCsvArtifact(session.question) else "comparison",
        "title": name.replace("_", " "),
        "metric": value_key,
        "sourceArtifact": name,
        "categories": [label for label, _value in selected],
        "series": [{"name": value_key, "type": "bar", "data": [value for _label, value in selected]}],
        "unit": "%"
        if any(token in value_key.lower() for token in ("pct", "rate", "return", "수익률", "등락률"))
        else "",
    }
    if not isMeaningfulVisualSpec(spec):
        return None
    item = {"id": session.next_id("viz"), "kind": "visual", "spec": _json_safe(spec), "sourceArtifact": name}
    session.visuals.append(item)
    session.record_trace("compute", {"tool": "create_artifact", "kind": "visual", "id": item["id"], "source": "csv"})
    return item


def _pick_category_key(rows: list[dict[str, Any]]) -> str | None:
    preferred = (
        "IDX_NM",
        "idxName",
        "indexName",
        "index_name",
        "corpName",
        "corp_name",
        "stockCode",
        "stock_code",
        "name",
        "target",
        "지수",
        "종목",
    )
    keys = list(rows[0].keys()) if rows else []
    for key in preferred:
        if key in keys:
            return key
    for key in keys:
        if _is_date_like_key(key):
            continue
        if any(str(row.get(key) or "").strip() for row in rows[:5]) and _number(rows[0].get(key)) is None:
            return key
    return None


def _pick_numeric_key(rows: list[dict[str, Any]]) -> str | None:
    preferred = (
        "bull_score",
        "bullish_score",
        "strength_score",
        "strengthScore",
        "score",
        "강세점수",
        "returnPct",
        "ret20",
        "ret_20",
        "return_20",
        "ret5",
        "ret_5",
        "dailyReturn",
        "changePct",
        "등락률",
        "수익률",
    )
    keys = list(rows[0].keys()) if rows else []
    for key in preferred:
        if key in keys and sum(_number(row.get(key)) is not None for row in rows[:12]) >= 2:
            return key
    for key in keys:
        if _is_placeholder_key(key):
            continue
        lowered = key.lower()
        if any(
            token in lowered
            for token in ("score", "strength", "return", "ret", "pct", "rate", "강세", "수익률", "등락률")
        ):
            if sum(_number(row.get(key)) is not None for row in rows[:12]) >= 2:
                return key
    for key in keys:
        if _is_placeholder_key(key):
            continue
        if sum(_number(row.get(key)) is not None for row in rows[:12]) >= 2:
            return key
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        raw = value.replace(",", "").replace("%", "").strip()
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def _is_date_like_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in {"date", "bas_dd", "asof", "as_of", "observeddate", "observed_date"} or lowered.endswith("date")


def _is_placeholder_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in {"placeholder", "dummy", "sample"} or any(
        token in lowered for token in ("placeholder", "dummy", "sample")
    )


def _looks_like_placeholder_values(row: Any, values: list[float]) -> bool:
    if not isinstance(row, dict):
        return False
    name = str(row.get("name") or row.get("metric") or "").lower()
    return _is_placeholder_key(name) or (len(set(values)) == 1 and set(values) <= {0.0, 1.0})
