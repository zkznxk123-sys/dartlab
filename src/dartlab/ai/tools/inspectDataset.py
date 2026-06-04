"""inspect_dataset — dataset schema/latest/metric 후보를 빠르게 확인.

WORK 패스에서 LLM 이 run_python 으로 코드를 짜기 전에 dataset 의 컬럼·타입·최신
관측·행 수를 알 수 있게 해 emit_result 실패 사이클 (schema 추측 실패) 을 줄인다.

지원 target:
- "Company.panel:<stockCode>:<topic>" — 예: "Company.panel:005930:BS" (옛 "Company.show:" 도 허용)
- "scan:<axis>" — 예: "scan:profitability"
- "macro" — dartlab.macro() 종합
- "gather:<axis>:<target>" — dartlab.gather() 결과
"""

from __future__ import annotations

from typing import Any

from dartlab.ai.contracts import Ref

from .types import ToolResult


def inspectDataset(target: str, *, sampleRows: int = 5) -> ToolResult:
    """dataset target 을 inspect 한다."""
    target = (target or "").strip()
    if not target:
        return ToolResult(False, "target 미지정", error="missing_target")

    try:
        df, source_label = _resolveDataset(target)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            False,
            f"inspect_dataset 실패: {exc}",
            error=type(exc).__name__,
        )

    if df is None:
        return ToolResult(False, f"dataset 없음: {target}", error="dataset_not_found")

    schema = _schema(df)
    latest = _latest(df)
    sample = _sample(df, n=max(1, int(sampleRows or 5)))
    rows = _rowCount(df)

    payload = {
        "target": target,
        "source": source_label,
        "schema": schema,
        "rowCount": rows,
        "latest": latest,
        "sample": sample,
    }

    refs = [
        Ref(
            id=f"dataset:{target}",
            kind="datasetRef",
            title=source_label,
            source="inspect_dataset",
            payload=payload,
        )
    ]
    return ToolResult(
        True,
        f"inspect_dataset 완료: {source_label} (rows={rows}, cols={len(schema)})",
        refs=refs,
        data=payload,
    )


def _resolveDataset(target: str) -> tuple[Any, str]:
    if target.startswith(("Company.panel:", "Company.show:")):  # show: 옛 호출 back-compat
        _, code, topic = target.split(":", 2) if target.count(":") >= 2 else (None, None, None)
        if not code:
            raise ValueError("Company.panel target 은 'Company.panel:<stockCode>:<topic>' 형식")
        from dartlab.company import Company

        c = Company(code)
        df = c.panel(topic or "BS")
        return df, f"Company({code}).panel({topic or 'BS'})"
    if target.startswith("scan:"):
        axis = target.split(":", 1)[1]
        from dartlab.scan import Scan

        df = Scan()(axis)
        return df, f"scan({axis})"
    if target == "macro":
        from dartlab.macro import Macro

        df = Macro()()
        return df, "macro()"
    if target.startswith("gather:"):
        parts = target.split(":", 2)
        axis = parts[1] if len(parts) > 1 else None
        sub = parts[2] if len(parts) > 2 else None
        from dartlab.gather.entry import GatherEntry

        g = GatherEntry()
        df = g(axis, sub) if (axis and sub) else g(axis) if axis else g()
        return df, f"gather({axis}{', ' + sub if sub else ''})"
    raise ValueError(f"알 수 없는 target 형식: {target}")


def _schema(df: Any) -> list[dict[str, str]]:
    if hasattr(df, "schema"):
        try:
            return [{"name": str(name), "dtype": str(dtype)} for name, dtype in df.schema.items()]
        except Exception:  # noqa: BLE001
            pass
    if hasattr(df, "columns"):
        return [{"name": str(name), "dtype": "?"} for name in df.columns]
    return []


def _rowCount(df: Any) -> int:
    if hasattr(df, "height"):
        try:
            return int(df.height)
        except Exception:  # noqa: BLE001
            return 0
    if hasattr(df, "__len__"):
        try:
            return len(df)
        except Exception:  # noqa: BLE001
            return 0
    return 0


def _latest(df: Any) -> dict[str, Any]:
    if not hasattr(df, "columns"):
        return {}
    cols = [str(c) for c in df.columns]
    date_cols = [c for c in cols if any(k in c.lower() for k in ("date", "asof", "as_of", "기준일", "year", "분기"))]
    if not date_cols:
        return {}
    col = date_cols[0]
    try:
        max_val = df[col].max()
        return {"column": col, "value": str(max_val) if max_val is not None else None}
    except Exception:  # noqa: BLE001
        return {"column": col, "value": None}


def _sample(df: Any, *, n: int = 5) -> list[dict]:
    if not hasattr(df, "head"):
        return []
    try:
        head = df.head(n)
        if hasattr(head, "to_dicts"):
            return list(head.to_dicts())
        if hasattr(head, "to_dict"):
            return list(head.toDict("records"))
    except Exception:  # noqa: BLE001
        pass
    return []
