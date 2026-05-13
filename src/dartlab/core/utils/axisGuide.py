"""엔진 axis registry 를 가이드 DataFrame 으로 바꾸는 L0 helper."""

from __future__ import annotations

from typing import Any, Callable, Mapping

import polars as pl

_DEFAULT_COLUMN_ORDER: tuple[str, ...] = ("axis", "label", "description", "example", "group")


def buildAxisGuideDataFrame(
    registry: Mapping[str, Any],
    *,
    groupExtractor: Callable[[str, Any], str],
    descriptionExtractor: Callable[[str, Any], str] | None = None,
    apiKey: str | Callable[[str, Any], str] | None = "불필요",
    extraColumns: dict[str, Callable[[str, Any], Any]] | None = None,
    columnOrder: list[str] | None = None,
) -> pl.DataFrame:
    """axis registry 를 사용자 가이드 DataFrame 으로 변환한다.

    Capabilities:
        L2/L1.5 엔진별 axis registry 를 동일한 사용자 안내 DataFrame 형태로 변환한다.
    AIContext:
        AI와 UI가 엔진별 축 목록을 같은 컬럼 구조로 설명할 수 있게 하는 L0 helper.
    Guide:
        엔진별 group/description/extra 컬럼 차이는 콜러블로 주입하고, 여기에는 엔진 import를 두지 않는다.
    When:
        ``analysis()``, ``scan()``, ``macro()`` 같은 엔진이 무인자 가이드 화면을 만들 때.
    How:
        registry item을 순회하며 공통 컬럼을 만들고, optional extractor 결과를 추가한 뒤 컬럼 순서를 정렬한다.
    Args:
        registry: ``{axisKey: entry}`` mapping.
        groupExtractor: ``(axisKey, entry) -> group`` callable.
        descriptionExtractor: optional description override callable.
        apiKey: apiKey 컬럼 값, callable, 또는 컬럼 생략용 ``None``.
        extraColumns: 추가 컬럼명과 extractor mapping.
        columnOrder: 출력 컬럼 순서.
    Returns:
        Axis guide ``polars.DataFrame``. 빈 registry면 빈 DataFrame.
    Requires:
        Entry objects expose ``label``, ``description``, and ``example`` attributes when available.
    Raises:
        Extractor callable 예외와 Polars DataFrame 생성 예외를 전파한다.
    Example:
        >>> buildAxisGuideDataFrame({"a": type("E", (), {"label": "A", "description": "d", "example": "e"})()}, groupExtractor=lambda k, e: "g").columns
        ['axis', 'label', 'description', 'example', 'group', 'apiKey']
    SeeAlso:
        ``dartlab.synth.axisGuide`` compatibility re-export.
    """
    if not registry:
        return pl.DataFrame()

    rows: list[dict[str, Any]] = []
    for key, entry in registry.items():
        description = (
            descriptionExtractor(key, entry) if descriptionExtractor is not None else getattr(entry, "description", "")
        )
        row: dict[str, Any] = {
            "axis": key,
            "label": getattr(entry, "label", key),
            "description": description,
            "example": getattr(entry, "example", ""),
            "group": groupExtractor(key, entry),
        }
        if extraColumns:
            for colName, extractor in extraColumns.items():
                row[colName] = extractor(key, entry)
        if apiKey is not None:
            row["apiKey"] = apiKey(key, entry) if callable(apiKey) else apiKey
        rows.append(row)

    df = pl.DataFrame(rows)

    if columnOrder is not None:
        ordered = [c for c in columnOrder if c in df.columns]
        return df.select(ordered)

    defaultOrder: list[str] = list(_DEFAULT_COLUMN_ORDER)
    if extraColumns:
        defaultOrder.extend(extraColumns.keys())
    if apiKey is not None:
        defaultOrder.append("apiKey")
    ordered = [c for c in defaultOrder if c in df.columns]
    return df.select(ordered)
