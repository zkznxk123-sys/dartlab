"""sections 수평화 앵커 (read-side) — scope 파생 + 최신기준 과거 정렬 (요구 #7).

RUNTIME reader 전용 derivation. disclosureKey resolve(채움)는 core.sections.
build(gather) 가 채운 disclosureKey + xbrlClass 를 읽어, 과거 era 의 drift 를
``(disclosureKey, scope)`` 단일 행으로 정렬한다 (read 시점, 저장 14-col 불변).

LLM Specifications:
    AntiPatterns:
        - 사전 계산 컬럼(content_plain/scope) 저장 금지 — read 시점 파생.
        - disclosureKey resolve 를 본 모듈에서 금지 — core.sections.canonical.
    OutputSchema:
        - ``scopeExpr(col) -> pl.Expr`` ("consolidated"/"standalone").
        - ``anchorLatest(df) -> pl.DataFrame`` (scope 부착 + keyed 행 최신 라벨 통일).
    Prerequisites:
        - polars. xbrlClass / disclosureKey / period 컬럼.
    TargetMarkets:
        - KR + US 공통 (disclosureKey 계약 동일).
"""

from __future__ import annotations

import polars as pl


def scopeExpr(col: str = "xbrlClass") -> pl.Expr:
    """xbrlClass → scope ('consolidated' / 'standalone').

    DART ACLASS 명명 규약: 별도(개별) 재무·주석은 ``_S`` 표식 (BS_S / IS_S2 /
    NT_S_D######), 연결은 ``_C`` 또는 옛 무접미사 (BS / IS2 / CF). ``_S`` 가
    없으면 연결로 본다 (옛 무접미사 = 연결).

    Args:
        col: xbrlClass 컬럼명.

    Returns:
        ``scope`` 별칭 Utf8 Expr ("consolidated" / "standalone").

    Examples:
        >>> import polars as pl
        >>> df = pl.DataFrame({"xbrlClass": ["BS_C", "BS_S", "BS", "NT_S_D826385", None]})
        >>> df.select(scopeExpr())["scope"].to_list()
        ['consolidated', 'standalone', 'consolidated', 'standalone', 'consolidated']

    LLM Specifications:
        AntiPatterns:
            - ``_S`` 부분일치를 regex 로 처리 금지 — literal 매칭 (특수문자 0).
            - narrative(xbrlClass null) 에 None scope 부여 금지 — consolidated 기본 (pivot index 안정).
        OutputSchema:
            - ``pl.Expr`` (alias "scope", Utf8).
        Prerequisites:
            - polars. xbrlClass 컬럼.
        TargetMarkets:
            - KR (DART ACLASS _C/_S 규약). EDGAR 는 별도 scope 규칙.
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

    같은 disclosure 가 era 마다 xbrlClass(BS→BS_C)·제목(연결 재무상태표→"")이
    흔들려 pivot 이 era 별로 행을 쪼갬 → ``(disclosureKey, scope)`` 그룹의 **최신
    period 라벨**(chapter/sectionLeaf/blockLeaf)을 전 기간에 덮어써 한 행으로 정렬.
    scope 로 연결/별도 분리 보존 (NT_C vs NT_S 병합 방지). disclosureKey null
    (narrative) 행은 손대지 않음 (텍스트 정렬 유지).

    Args:
        df: sections long DataFrame (disclosureKey/xbrlClass/period/chapter/
            sectionLeaf/blockLeaf 포함).

    Returns:
        ``scope`` 컬럼 추가 + keyed 행의 chapter/sectionLeaf/blockLeaf 가 최신기준
        으로 통일된 DataFrame.

    LLM Specifications:
        AntiPatterns:
            - disclosureKey 단독 group 금지 — (disclosureKey, scope) 페어 (연결/별도 병합 방지).
            - xbrlClass 를 pivot index 에 유지 금지 — era drift 로 행 쪼개짐 (scope 로 대체).
            - 최신 = period 최대 문자열 (YYYYQn 정렬). 결산월 무관 12월결산화된 키라 안전.
        OutputSchema:
            - 입력과 동일 컬럼 + ``scope``, keyed 행 라벨 최신 통일.
        Prerequisites:
            - polars. disclosureKey/period/scope 원천(xbrlClass).
        Dataflow:
            - scope 부착 → keyed 행 (disclosureKey,scope)별 최신 period 라벨 추출 →
              join 후 keyed 행 라벨 덮어쓰기.
        TargetMarkets:
            - KR + US 공통 (disclosureKey 계약 동일).
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
