"""panel canonical mapper — raw ACLASS → canonical 정렬키 + 행 identity (순수 SSOT).

native ACLASS(정부 발행 Link Role)의 scope marker 만 벗긴 ``canonicalKey``(테이블 0 순수함수)가
회사내·회사간 수평화의 단일 정렬키. ``rowIdentity``(keyed=disclosureKey / narrative=NARR::)는
build·read 가 공유하는 행 식별 SSOT — spine 정렬·diff 의 join 키. 손매핑·학습·bridge lookup 0
([[feedback_xml_native_truth]]).

LLM Specifications:
    AntiPatterns:
        - 직접 hardcoded 의미 매핑 금지 — ACLASS 형식 구조 규칙만(R5).
        - unmapped ACLASS 에 임의 키 부여 금지 — passthrough/None (narrative).
    OutputSchema:
        - ``canonicalKey(xbrlClass) -> str | None`` / ``canonicalKeyExpr(col) -> pl.Expr``.
        - ``rowIdentity(disclosureKey, chapter, sectionLeaf) -> str`` / ``rowIdentityExpr(...) -> pl.Expr``.
        - ``resolveBatch(df, *, marketNs) -> pl.DataFrame`` (disclosureKey=canonicalKey 부착).
    Prerequisites:
        - polars. (데이터 파일 의존 0 — 순수 규칙)
    Freshness:
        - 순수함수 — 입력 외 의존 0.
    Dataflow:
        - xbrlClass → canonicalKey. (disclosureKey, chapter, sectionLeaf) → rowIdentity.
    TargetMarkets:
        - KR (DART ACLASS). US 는 build/usSeed overlay (후속).
"""

from __future__ import annotations

import re

import polars as pl

# canonicalKey scope-strip 형식 규칙 (R5: ACLASS 구조 규칙이지 per-title 의미매핑 아님).
# 정부 표준 ACLASS 위에서 scope marker 만 정규화 (native code 자체가 SSOT).
_XBRL_PREFIX = "{XBRL}"
_NT_RE = re.compile(r"^NT_[CS]_(D\d+)$")  # NT_C_D826380 → D826380
_IS_RE = re.compile(r"^IS(?:_[CS])?(\d)$")  # IS_C2 / IS_S2 / 옛 IS2 → 2
_FS_RE = re.compile(r"^(BS|CF|EF)(?:_[CS])?$")  # BS / BS_C / BS_S → BS


def canonicalKey(xbrlClass: str | None) -> str | None:
    """raw ACLASS(xbrlClass) → scope-정규화 canonical 정렬키 (순수함수, 테이블 0).

    DART XBRL 표준 ACLASS(정부 발행 Link Role)에서 scope marker(_C/_S)만 벗겨 회사내·회사간
    수평화의 단일 정렬키를 만든다 — bridge 매핑 농장 없이 native 코드 자체가 SSOT. era drift
    (옛 ``BS`` ↔ 신 ``BS_C``)는 같은 키로 병합되고, 변종(``IS_C2`` 손익 vs ``IS_C3`` 포괄손익)·
    주석 D-code 는 분리 유지. 연결/별도 분리는 ``anchor.scopeExpr`` 가 raw 의 ``_S`` 에서 독립 산출.

    Args:
        xbrlClass: walker 가 추출한 raw ACLASS (예 "BS_C", "NT_C_D826380"). None/"" 허용.

    Returns:
        canonical 키 (예 "BS", "IS2", "NT_D826380") 또는 None (narrative — xbrlClass 부재).

    Raises:
        없음 — None/빈 입력은 None 반환.

    Example:
        >>> canonicalKey("BS_C"), canonicalKey("BS")
        ('BS', 'BS')
        >>> canonicalKey("IS_C2"), canonicalKey("IS2")
        ('IS2', 'IS2')
        >>> canonicalKey("NT_C_D826380")
        'NT_D826380'
        >>> canonicalKey(None) is None
        True

    SeeAlso:
        - ``canonicalKeyExpr`` — 동일 규칙의 polars Expr (build/read 공통 SSOT).
        - ``anchor.scopeExpr`` — 연결/별도 scope 독립 산출.
        - ``resolveBatch`` — DataFrame 일괄 disclosureKey 부착.

    Requires:
        - 없음 (순수 문자열 함수).

    Capabilities:
        - 회사내·회사간 수평화 정렬키를 native ACLASS 에서 직접 산출 — 손매핑·학습·scatter 0.

    Guide:
        - resolveBatch/canonicalKeyExpr 경유 권장. 직접 호출도 안전(순수).

    AIContext:
        - 정부 표준 코드 위 형식 규칙만 — 의미 추론 0 (mapper farm 회귀 차단).

    When:
        - raw ACLASS 를 era·scope 무관 단일 정렬키로 정규화할 때.

    How:
        - {XBRL} prefix strip → NT_[CS]_D / IS(_[CS])?digit / (BS|CF|EF)(_[CS])? 매칭 → 정규화, else passthrough.

    LLM Specifications:
        AntiPatterns:
            - per-title 의미 regex 추가 금지 — ACLASS 형식 구조 규칙만(R5).
            - 주석 C/S D-code 번호차(826380 vs 826385) 임의 +offset 병합 금지 — 추측.
            - narrative(None) 에 임의 키 부여 금지 — None 유지.
        OutputSchema:
            - ``str | None`` (canonical 키 또는 None).
        Prerequisites:
            - 없음.
        Freshness:
            - 순수함수 — 입력 외 의존 0.
        Dataflow:
            - xbrlClass → prefix strip → 패턴 매칭 → scope-strip canonical.
        TargetMarkets:
            - KR (DART ACLASS). US 는 후속 (us-gaap concept 별도).
    """
    if not xbrlClass:
        return None
    x = xbrlClass.strip()
    if x.startswith(_XBRL_PREFIX):
        x = x[len(_XBRL_PREFIX) :]
    if not x:
        return None
    m = _NT_RE.match(x)
    if m:
        return f"NT_{m.group(1)}"
    m = _IS_RE.match(x)
    if m:
        return f"IS{m.group(1)}"
    m = _FS_RE.match(x)
    if m:
        return m.group(1)
    return x


def canonicalKeyExpr(col: str = "xbrlClass") -> pl.Expr:
    """``canonicalKey`` 의 polars Expr — build/read 동일 규칙 단일 SSOT.

    scalar ``canonicalKey`` 와 바이트 동치(동일 scope-strip 규칙). build(disclosureKey 부착)·
    read(fallback) 양쪽이 본 Expr 하나만 의존 → 규칙 분기 0.

    Args:
        col: xbrlClass 컬럼명 (기본 "xbrlClass").

    Returns:
        ``canonicalKey`` 별칭 Utf8 Expr (xbrlClass null/미매칭은 §규칙대로 null/passthrough).

    Raises:
        없음.

    Example:
        >>> import polars as pl
        >>> df = pl.DataFrame({"xbrlClass": ["BS_C", "NT_C_D826380", "IS_S2", None]})
        >>> df.select(canonicalKeyExpr())["canonicalKey"].to_list()
        ['BS', 'NT_D826380', 'IS2', None]

    SeeAlso:
        - ``canonicalKey`` — scalar 동치.
        - ``resolveBatch`` — 본 Expr 로 disclosureKey 컬럼 채움.

    Requires:
        - polars.

    Capabilities:
        - 일괄 canonical 키 산출 — map_elements 회피, SIMD columnar.

    Guide:
        - resolveBatch 내부 또는 reader fallback 에서 사용. 직접 호출 가능.

    AIContext:
        - regex extract + when/then — scalar 규칙과 1:1.

    When:
        - DataFrame 의 xbrlClass 컬럼을 canonical 키로 일괄 변환할 때.

    How:
        - {XBRL} strip → str.extract(NT/IS/FS regex) → when/then 우선순위 → canonical.

    LLM Specifications:
        AntiPatterns:
            - scalar ``canonicalKey`` 와 규칙 분기 금지 — 동일 패턴(테스트로 동치 강제).
            - map_elements 금지 — str.extract Expr.
        OutputSchema:
            - ``pl.Expr`` (alias "canonicalKey", Utf8).
        Prerequisites:
            - polars. xbrlClass 컬럼.
        Freshness:
            - read/build 파생.
        Dataflow:
            - col → {XBRL} strip → NT/IS/FS extract → when/then canonical.
        TargetMarkets:
            - KR (DART ACLASS). US 후속.
    """
    base = pl.col(col).str.strip_chars().str.replace(r"^\{XBRL\}", "")
    base = pl.when(base.str.len_chars() == 0).then(None).otherwise(base)
    nt = base.str.extract(r"^NT_[CS]_(D\d+)$", 1)
    isn = base.str.extract(r"^IS(?:_[CS])?(\d)$", 1)
    fs = base.str.extract(r"^(BS|CF|EF)(?:_[CS])?$", 1)
    return (
        pl.when(base.is_null())
        .then(None)
        .when(nt.is_not_null())
        .then(pl.lit("NT_") + nt)
        .when(isn.is_not_null())
        .then(pl.lit("IS") + isn)
        .when(fs.is_not_null())
        .then(fs)
        .otherwise(base)
        .alias("canonicalKey")
    )


# 행 identity 구분자 (narrative 행 식별 prefix + chapter/section 구분 U+241F SYMBOL FOR UNIT SEP).
_NARR_PREFIX = "NARR::"
_NARR_SEP = "␟"


def rowIdentity(disclosureKey: str | None, chapter: str | None, sectionLeaf: str | None) -> str:
    """panel 한 행의 안정 identity — keyed=disclosureKey / narrative=NARR::chapter␟section.

    spine 정렬·diff 의 join 키. 재무·주석 행은 era-stable ``disclosureKey``(=canonicalKey) 자체가
    identity. 서술(disclosureKey 부재) 행은 ``chapter``/``sectionLeaf`` 로 식별 (정부 양식 표준
    제목이라 회사·기간 가로질러 안정). build·read 가 동일 규칙 1개 공유 → identity 분기 0.

    Args:
        disclosureKey: canonicalKey (예 "NT_D826380", "BS"). narrative 행은 None/"".
        chapter: SECTION-1 대분류 (예 "I. 회사의 개요").
        sectionLeaf: 절 제목 (예 "1. 회사의 개요").

    Returns:
        identity str — keyed 행은 disclosureKey, narrative 행은 ``NARR::{chapter}␟{sectionLeaf}``.

    Raises:
        없음.

    Example:
        >>> rowIdentity("NT_D826380", "III. 재무에 관한 사항", "3. 연결재무제표 주석")
        'NT_D826380'
        >>> rowIdentity(None, "I. 회사의 개요", "1. 회사의 개요")
        'NARR::I. 회사의 개요␟1. 회사의 개요'

    SeeAlso:
        - ``rowIdentityExpr`` — 동일 규칙 polars Expr (read pivot 후 일괄).
        - ``canonicalKey`` — keyed identity 의 원천.

    Requires:
        - 없음 (순수 문자열 함수).

    Capabilities:
        - spine 전역 뼈대·diff 의 행 join 키를 keyed/narrative 통합 산출 — 회사·기간 안정.

    Guide:
        - build(spine 생성)·read(spine 정렬)가 공유. 직접 호출 안전(순수).

    AIContext:
        - 정부 코드/제목 위 형식 규칙만 — 의미 추론 0.

    When:
        - 한 행을 회사·기간 가로질러 식별할 때 (spine join, diff).

    How:
        - disclosureKey 있으면 그대로, 없으면 NARR:: + chapter + ␟ + sectionLeaf.

    LLM Specifications:
        AntiPatterns:
            - narrative 에 blockOrder/period 포함 금지 — 기간 가로질러 불안정.
            - keyed 행에 chapter 혼합 금지 — disclosureKey 단독(era-stable).
        OutputSchema:
            - ``str`` (keyed=disclosureKey / narrative=NARR::chapter␟section).
        Prerequisites:
            - 없음.
        Freshness:
            - 순수함수.
        Dataflow:
            - (disclosureKey | chapter, sectionLeaf) → identity str.
        TargetMarkets:
            - KR + US 공통.
    """
    if disclosureKey:
        return disclosureKey
    return f"{_NARR_PREFIX}{chapter or ''}{_NARR_SEP}{sectionLeaf or ''}"


def rowIdentityExpr(
    keyCol: str = "disclosureKey", chapterCol: str = "chapter", sectionCol: str = "sectionLeaf"
) -> pl.Expr:
    """``rowIdentity`` 의 polars Expr — read pivot 후 wide 행 identity 일괄 산출.

    scalar ``rowIdentity`` 와 동일 규칙 (keyed=disclosureKey / narrative=NARR::chapter␟section).

    Args:
        keyCol: disclosureKey 컬럼명.
        chapterCol: chapter 컬럼명.
        sectionCol: sectionLeaf 컬럼명.

    Returns:
        ``_rowIdentity`` 별칭 Utf8 Expr.

    Raises:
        없음.

    Example:
        >>> import polars as pl
        >>> df = pl.DataFrame({"disclosureKey": ["BS", None], "chapter": ["c", "I"], "sectionLeaf": ["s", "1"]})
        >>> df.select(rowIdentityExpr())["_rowIdentity"].to_list()
        ['BS', 'NARR::I␟1']

    SeeAlso:
        - ``rowIdentity`` — scalar 동치.
        - ``read.readWide`` — 본 Expr 로 spine join 키 생성.

    Requires:
        - polars.

    Capabilities:
        - wide 행 identity 일괄 산출 — spine join 키, map_elements 회피.

    Guide:
        - readWide pivot 후 사용. 직접 호출 가능.

    AIContext:
        - when/then — scalar 규칙과 1:1.

    When:
        - read 가 wide 각 행을 spine 에 매핑할 때.

    How:
        - disclosureKey null/"" → NARR:: + chapter + ␟ + section, else disclosureKey.

    LLM Specifications:
        AntiPatterns:
            - scalar ``rowIdentity`` 와 규칙 분기 금지 — 동일(테스트 동치 강제).
        OutputSchema:
            - ``pl.Expr`` (alias "_rowIdentity", Utf8).
        Prerequisites:
            - polars. disclosureKey/chapter/sectionLeaf 컬럼.
        Freshness:
            - read 파생.
        Dataflow:
            - (key|chapter,section) → identity.
        TargetMarkets:
            - KR + US 공통.
    """
    # cast(Utf8) — all-null 컬럼이 Null dtype 으로 추론돼도 문자열 연산 안전.
    key = pl.col(keyCol).cast(pl.Utf8)
    chap = pl.col(chapterCol).cast(pl.Utf8).fill_null("")
    sect = pl.col(sectionCol).cast(pl.Utf8).fill_null("")
    narr = pl.lit(_NARR_PREFIX) + chap + pl.lit(_NARR_SEP) + sect
    return pl.when(key.is_not_null() & (key.str.len_chars() > 0)).then(key).otherwise(narr).alias("_rowIdentity")


def resolveBatch(df: pl.DataFrame, *, marketNs: str = "kr") -> pl.DataFrame:
    """panel artifact DataFrame → disclosureKey 컬럼 부착 (native canonicalKey).

    ``canonicalKeyExpr``(native ACLASS scope-strip, 테이블 0, 커버 ~100%)로 ``disclosureKey`` 를
    채운다. bridge lookup 농장 없이 정부 코드 자체가 SSOT — KR within-market 정렬키.

    Args:
        df: panel artifact (xbrlClass 컬럼 보유).
        marketNs: 빌드 시장 ("kr" 기본). 현재 canonicalKey 는 시장 무관(인자 보존, US 후속).

    Returns:
        ``disclosureKey`` 컬럼이 채워진 DataFrame (xbrlClass 부재/빈 입력은 그대로).

    Raises:
        없음.

    Example:
        >>> import polars as pl
        >>> df = pl.DataFrame({"xbrlClass": ["NT_C_D826380", "UNKNOWN"]})
        >>> resolveBatch(df)["disclosureKey"].to_list()
        ['NT_D826380', 'UNKNOWN']

    SeeAlso:
        - ``canonicalKeyExpr`` — native 정렬키 Expr.
        - ``build.builder`` — BUILD 단계 본 함수로 disclosureKey 채움.

    Requires:
        - polars.

    Capabilities:
        - BUILD 단계 일괄 disclosureKey 부착 → runtime resolve 회피(경량).

    Guide:
        - build write 시점 호출. reader 는 채워진 컬럼 사용 (전부 null 옛 artifact 만 fallback).

    AIContext:
        - canonicalKeyExpr SIMD columnar — map_elements 0.

    When:
        - build write 시점 artifact 에 disclosureKey 를 부착할 때.

    How:
        - xbrlClass → canonicalKeyExpr → disclosureKey.

    LLM Specifications:
        AntiPatterns:
            - runtime 매 read resolve 금지 — build 에서 1회 부착.
            - bridge lookup 농장 부활 금지 — native canonicalKey SSOT.
        OutputSchema:
            - ``pl.DataFrame`` (+ disclosureKey Utf8).
        Prerequisites:
            - xbrlClass 컬럼.
        Freshness:
            - 코드 규칙 — 재빌드만.
        Dataflow:
            - xbrlClass → canonicalKeyExpr → disclosureKey.
        TargetMarkets:
            - KR (canonical). US 후속 (build/usSeed overlay).
    """
    if df.is_empty() or "xbrlClass" not in df.columns:
        return df
    return df.with_columns(canonicalKeyExpr("xbrlClass").alias("disclosureKey"))
