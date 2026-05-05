"""축 카탈로그 DataFrame SSOT 빌더.

analysis/scan/macro/credit/quant 5엔진이 무인자 호출 시 반환하는 가이드
DataFrame 생성을 단일 함수로 통합한다. 엔진별 _AXIS_REGISTRY dataclass
차이(group 로직, items 같은 extra 컬럼, description 후처리)는 콜러블
주입으로 흡수하여 각 엔진 _guide() 메서드가 한 블록으로 축소되게 한다.
"""

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
    """엔진 _AXIS_REGISTRY 를 가이드 DataFrame 으로 변환.

    analysis/scan/macro/credit/quant 5엔진이 각자 반복하던 `_guide()`
    구현을 단일 빌더로 통합한다. 엔진별 차이(group 로직, description
    후처리, items 같은 extra 컬럼, apiKey 유무)는 콜러블·옵션 파라미터로
    흡수한다.

    Parameters
    ----------
    registry : Mapping[str, Any]
        `{axisKey: AxisEntry}` 매핑. 각 엔진의 `_AXIS_REGISTRY`. AxisEntry
        는 최소한 `label`, `description`, `example` 속성을 가져야 한다.
    groupExtractor : Callable[[str, Any], str]
        (axisKey, entry) → group 문자열. 엔진별 group 로직 주입.
        예: `lambda k, e: e.section` (analysis), `lambda k, e: f"제{e.act}막"` (macro).
    descriptionExtractor : Callable[[str, Any], str], optional
        (axisKey, entry) → description 문자열. 미지정 시 `entry.description` 사용.
        quant 의 " (종목 불필요)" 같은 후처리 주입용.
    apiKey : str | Callable[[str, Any], str] | None, default "불필요"
        API 키 안내. 상수 문자열이면 모든 row 동일. 콜러블이면 엔트리별.
        None 이면 apiKey 컬럼 자체를 생략 (quant 대응).
    extraColumns : dict[str, Callable[[str, Any], Any]], optional
        `{컬럼명: 값 추출 콜러블}`. analysis 의 `items: len(entry.calcs)`
        같은 엔진 특수 필드 주입용.
    columnOrder : list[str], optional
        출력 컬럼 순서. 미지정 시
        `axis | label | description | example | group | {extra…} | apiKey`
        기본 순서. apiKey=None 이면 apiKey 는 순서에서 제외.

    Returns
    -------
    pl.DataFrame
        axis : str — 정규 축 키
        label : str — 한글 라벨
        description : str — 축 설명
        example : str — 호출 예시
        group : str — 그룹/파트 분류 (엔진별 의미 다름)
        {extra columns} : Any — 엔진별 추가 컬럼 (items 등)
        apiKey : str — 필요한 API 키 안내 (apiKey=None 이면 생략)

    Raises
    ------
    없음 — registry 가 비어있으면 빈 DataFrame 반환.

    Examples
    --------
    >>> from dartlab.guide import buildAxisGuideDataFrame
    >>> df = buildAxisGuideDataFrame(
    ...     _AXIS_REGISTRY,
    ...     groupExtractor=lambda k, e: e.section,
    ...     extraColumns={"items": lambda k, e: len(e.calcs)},
    ... )

    Notes
    -----
    - 엔진별 _AXIS_REGISTRY AxisEntry 는 공통 속성 (label / description /
      example) 만 가정한다. 나머지 특수 필드는 콜러블로 흡수.
    - 반환 DataFrame 의 컬럼 순서·이름은 리팩터 전 각 엔진 구현과 동일
      하도록 `columnOrder` 로 제어 가능. 호출 계약 역호환 보장.

    Guide
    -----
    엔진 _guide() 메서드는 이 함수 호출 한 줄로 축소된다. 엔진별 adapter
    로직(group 분류, description 후처리, items 계산 등)은 콜러블로 전달.

    See Also
    --------
    missingDataHint : 에러 복구 안내 템플릿.
    apiKeyMissingHint : provider 별 API 키 발급 안내 (aiSetup 위임).
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

    # 기본 순서: axis|label|description|example|group|{extra}|apiKey
    defaultOrder: list[str] = list(_DEFAULT_COLUMN_ORDER)
    if extraColumns:
        defaultOrder.extend(extraColumns.keys())
    if apiKey is not None:
        defaultOrder.append("apiKey")
    ordered = [c for c in defaultOrder if c in df.columns]
    return df.select(ordered)
