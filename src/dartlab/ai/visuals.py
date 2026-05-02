"""Visual evidence compiler for Ask Workbench."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .contracts import Ref, new_id


@dataclass(frozen=True)
class VisualSpec:
    id: str
    viz_type: str
    chart_type: str
    purpose: str
    title: str
    source_ref: str
    metric: str
    categories: list[str]
    series: list[dict[str, Any]]
    as_of: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["vizType"] = data.pop("viz_type")
        data["chartType"] = data.pop("chart_type")
        data["sourceRef"] = data.pop("source_ref")
        data["asOf"] = data.pop("as_of")
        return data


def compile_visual(
    *,
    source_ref: str,
    rows: list[dict[str, Any]],
    category: str,
    metric: str,
    purpose: str = "ranking",
    title: str | None = None,
    as_of: str | None = None,
) -> VisualSpec:
    """Visual 컴파일 — table/execution 근거에서만 차트 spec 생성.

    Description
    -----------
    LLM 이 임의로 차트를 꾸미지 못하게 하고, 이미 계산된 table rows 에서만
    visual spec 을 만든다. 단일 값/단일 category visual 은 거부한다.

    Parameters
    ----------
    source_ref : str
        visual 의 근거가 되는 table 또는 execution ref id.
    rows : list[dict]
        차트로 변환할 표 행.
    category : str
        x축/category 컬럼명.
    metric : str
        y축 numeric metric 컬럼명.
    purpose : str, optional
        visual 목적. 예: ranking, comparison, change.
    title : str, optional
        차트 제목.
    as_of : str, optional
        데이터 기준일.

    Returns
    -------
    VisualSpec
        id : str — visual ref id
        viz_type : str — `"chart"`
        chart_type : str — `"bar"`
        purpose : str — visual 설명 목적
        source_ref : str — 근거 ref id
        metric : str — 표시 지표
        categories : list[str] — category 값
        series : list[dict] — numeric series
        as_of : str | None — 데이터 기준일

    Raises
    ------
    ValueError
        source ref 가 없거나 2개 미만 category/value 로 visual 을 만들 때.

    Examples
    --------
    >>> compile_visual(source_ref="table:1", rows=[{"name":"A","v":1},{"name":"B","v":2}], category="name", metric="v")
    VisualSpec(...)

    Notes
    -----
    Visual 은 장식이 아니라 근거 연결 산출물이다.

    Guide
    -----
    LLM 은 먼저 `run_python` 또는 `inspect_dataset` 결과로 table ref 를 만든 뒤
    이 함수를 호출한다.

    See Also
    --------
    visual_to_ref : VisualSpec 을 ref 로 변환.
    """

    if not source_ref:
        raise ValueError("visual requires a source table or execution ref")
    categories: list[str] = []
    values: list[float] = []
    for row in rows:
        if category not in row or metric not in row:
            continue
        try:
            value = float(str(row[metric]).replace(",", ""))
        except (TypeError, ValueError):
            continue
        categories.append(str(row[category]))
        values.append(value)
    if len(categories) < 2 or len(values) < 2:
        raise ValueError("visual requires at least two categories and two numeric values")
    return VisualSpec(
        id=new_id("visual"),
        viz_type="chart",
        chart_type="bar",
        purpose=purpose,
        title=title or metric,
        source_ref=source_ref,
        metric=metric,
        categories=categories,
        series=[{"name": metric, "data": values}],
        as_of=as_of,
    )


def visual_to_ref(spec: VisualSpec) -> Ref:
    return Ref(id=spec.id, kind="visual", source="compile_visual", payload=spec.to_dict())


compileVisual = compile_visual
