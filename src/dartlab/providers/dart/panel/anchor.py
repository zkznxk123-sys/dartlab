"""panel 최신앵커 (L1 read) — scope 파생 + 과거 기간 최신기준 정렬 (요구 #7).

RUNTIME reader 전용 derivation. build 가 채운 disclosureKey + xbrlClass 를 읽어, 과거
era 의 drift(BS→BS_C, 제목 변동)를 ``(disclosureKey, scope)`` 단일 행으로 정렬한다 —
회사내 수평화의 핵심(과거 기간이 최신기준 한 행에 모임). 저장 14-col 불변(scope 는 read 파생).

LLM Specifications:
    AntiPatterns:
        - 사전 계산 컬럼(scope) 저장 금지 — read 시점 파생.
        - disclosureKey resolve 를 본 모듈에서 금지 — core.panel.canonical 책임.
        - lxml/network import 금지 — read 층(R2).
    OutputSchema:
        - ``scopeExpr(col) -> pl.Expr`` ("consolidated"/"standalone").
        - ``anchorLatest(df) -> pl.DataFrame`` (scope 부착 + keyed 행 최신 라벨 통일).
    Prerequisites:
        - polars. xbrlClass / disclosureKey / period 컬럼.
    Freshness:
        - read 시점 파생 — artifact 변경과 무관.
    Dataflow:
        - scope 부착 → keyed 행 (disclosureKey,scope)별 최신 period 라벨 → join 덮어쓰기.
    TargetMarkets:
        - KR + US 공통 (disclosureKey 계약 동일).
"""

from __future__ import annotations

import polars as pl


def scopeExpr(col: str = "xbrlClass") -> pl.Expr:
    """xbrlClass → scope ('consolidated' / 'standalone') 파생 Expr.

    DART ACLASS 규약: 별도(개별) 재무·주석은 ``_S`` 표식(BS_S/IS_S2/NT_S_D######),
    연결은 ``_C`` 또는 옛 무접미사(BS/IS2/CF). ``_S`` 없으면 연결.

    Args:
        col: xbrlClass 컬럼명 (기본 "xbrlClass").

    Returns:
        ``scope`` 별칭 Utf8 Expr ("consolidated"/"standalone").

    Raises:
        없음.

    Example:
        >>> import polars as pl
        >>> df = pl.DataFrame({"xbrlClass": ["BS_C", "BS_S", "BS", "NT_S_D826385", None]})
        >>> df.select(scopeExpr())["scope"].to_list()
        ['consolidated', 'standalone', 'consolidated', 'standalone', 'consolidated']

    SeeAlso:
        - ``anchorLatest`` — scope 로 연결/별도 병합 방지.
        - ``core.panel.PIVOT_INDEX`` — scope 가 pivot index 의 일부.

    Requires:
        - polars.

    Capabilities:
        - 연결/별도 분리 보존 — BS_C↔BS_S 병합 차단(같은 disclosureKey 라도 scope 다름).

    Guide:
        - anchorLatest / pivot 내부에서 사용 — 직접 호출 가능(파생 Expr).

    AIContext:
        - 순수 Expr — literal 매칭(특수문자 0).

    LLM Specifications:
        AntiPatterns:
            - ``_S`` regex 부분매칭 금지 — literal 매칭.
            - narrative(null) 에 None scope 금지 — consolidated 기본(pivot index 안정).
        OutputSchema:
            - ``pl.Expr`` (alias "scope", Utf8).
        Prerequisites:
            - polars. xbrlClass 컬럼.
        Freshness:
            - read 파생.
        Dataflow:
            - xbrlClass → null/_S/else → scope.
        TargetMarkets:
            - KR (DART _C/_S 규약). EDGAR 는 별도 scope 규칙.
    """
    c = pl.col(col)
    return (
        pl.when(c.is_null())
        .then(pl.lit("consolidated"))
        .when(c.str.contains("_S", literal=True))
        .then(pl.lit("standalone"))
        .otherwise(pl.lit("consolidated"))
        .alias("scope")
    )


def anchorLatest(df: pl.DataFrame) -> pl.DataFrame:
    """과거 기간을 최신기준으로 수평화 — disclosureKey 단일 앵커 정렬 (요구 #7).

    같은 disclosure 가 era 마다 xbrlClass(BS→BS_C)·제목이 흔들려 pivot 이 era 별로 행을
    쪼갬 → ``(disclosureKey, scope)`` 그룹의 **최신 period 라벨**(chapter/sectionLeaf/
    blockLeaf)을 전 기간에 덮어써 한 행으로 정렬. scope 로 연결/별도 분리 보존. disclosureKey
    null(narrative) 행은 손대지 않음(텍스트 정렬 유지).

    Args:
        df: panel long DataFrame (disclosureKey/xbrlClass/period/chapter/sectionLeaf/
            blockLeaf 포함).

    Returns:
        ``scope`` 컬럼 추가 + keyed 행의 chapter/sectionLeaf/blockLeaf 최신기준 통일 DataFrame.
        빈/필수컬럼 부재 시 원본 그대로.

    Raises:
        없음.

    Example:
        >>> out = anchorLatest(longDf)  # doctest: +SKIP
        >>> "scope" in out.columns  # doctest: +SKIP
        True

    SeeAlso:
        - ``scopeExpr`` — scope 파생.
        - ``pivot.readPanelWide`` — anchorLatest 후 period 축 pivot.

    Requires:
        - polars.

    Capabilities:
        - 회사내 수평화의 era drift 흡수 — 과거 기간이 최신기준 한 행에 정렬.

    Guide:
        - pivot/reader 가 wide 변환 전 호출 — 직접 호출 가능.

    AIContext:
        - keyed 행만 라벨 통일, narrative 는 보존 — 무손실.

    When:
        - pivot 이 회사내 wide 변환 전 era drift 를 흡수할 때.

    How:
        - scope 부착 → (disclosureKey, scope) 최신 period 라벨 → join 덮어쓰기.

    LLM Specifications:
        AntiPatterns:
            - disclosureKey 단독 group 금지 — (disclosureKey, scope) 페어(연결/별도 병합 방지).
            - xbrlClass 를 pivot index 유지 금지 — era drift 로 행 쪼개짐(scope 대체).
            - 최신 = period 최대 문자열(YYYYQn 정렬, 12월결산화라 안전).
        OutputSchema:
            - 입력 + ``scope``, keyed 행 라벨 최신 통일.
        Prerequisites:
            - disclosureKey/period/xbrlClass 컬럼.
        Freshness:
            - read 파생.
        Dataflow:
            - scope 부착 → keyed (disclosureKey,scope) 최신 period 라벨 → join 덮어쓰기.
        TargetMarkets:
            - KR + US 공통.
    """
    if df.is_empty() or "disclosureKey" not in df.columns or "period" not in df.columns:
        return df
    df = df.with_columns(scopeExpr())
    keyed = df.filter(pl.col("disclosureKey").is_not_null())
    if keyed.is_empty():
        return df
    latest = (
        keyed.sort("period")
        .group_by(["disclosureKey", "scope"], maintain_order=True)
        .agg(
            pl.col("chapter").last().alias("_chapterL"),
            pl.col("sectionLeaf").last().alias("_sectionLeafL"),
            pl.col("blockLeaf").last().alias("_blockLeafL"),
        )
    )
    df = df.join(latest, on=["disclosureKey", "scope"], how="left")
    return df.with_columns(
        pl.when(pl.col("_chapterL").is_not_null())
        .then(pl.col("_chapterL"))
        .otherwise(pl.col("chapter"))
        .alias("chapter"),
        pl.when(pl.col("_sectionLeafL").is_not_null())
        .then(pl.col("_sectionLeafL"))
        .otherwise(pl.col("sectionLeaf"))
        .alias("sectionLeaf"),
        pl.when(pl.col("_blockLeafL").is_not_null())
        .then(pl.col("_blockLeafL"))
        .otherwise(pl.col("blockLeaf"))
        .alias("blockLeaf"),
    ).drop(["_chapterL", "_sectionLeafL", "_blockLeafL"])
