"""panel canonical resolver (L0) — raw ACLASS / us-gaap concept → disclosureKey.

(rawId, marketNs) + bridge SSOT → disclosureKey(snakeId). gather build(disclosureKey
채움) · providers reader(fallback) 공통 계약. 회사간·세계마켓간 정규화의 lookup 엔진.

LLM Specifications:
    AntiPatterns:
        - 직접 hardcoded 매핑 금지 — bridge parquet 만 활용.
        - 매번 bridge read 금지 — lru_cache dict.
        - unmapped rawId 에 임의 disclosureKey 부여 금지 — None 반환 (narrative fallback).
    OutputSchema:
        - ``resolveDisclosureKey(rawId, marketNs) -> str | None``.
        - ``resolveBatch(df, *, marketNs) -> pl.DataFrame`` (disclosureKey 컬럼 부착).
    Prerequisites:
        - polars. data/bridge/panelBridge.parquet (seedBridgeTier1 후 존재).
    Freshness:
        - bridge parquet 변경 시 invalidateCache.
    Dataflow:
        - rawId + marketNs → bridge lookup dict → disclosureKey.
    TargetMarkets:
        - KR + US 통합.
"""

from __future__ import annotations

import re
from functools import lru_cache

import polars as pl

from .bridge import loadBridge

# canonicalKey scope-strip 형식 규칙 (R5: ACLASS 구조 규칙이지 per-title 의미매핑 아님).
# 정부 표준 ACLASS 카탈로그(bridge._tier1Seed rawId) 위에서 scope marker 만 정규화.
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


@lru_cache(maxsize=1)
def _lookupDict() -> dict[tuple[str, str], str]:
    """bridge parquet → ``(rawId, marketNs) -> disclosureKey`` dict (tier 우선).

    Args:
        없음.

    Returns:
        ``(rawId, marketNs) -> disclosureKey`` dict. 동일 키 다중 tier 시 tier1 우선.

    Raises:
        없음.

    Example:
        >>> d = _lookupDict()  # doctest: +SKIP
        >>> isinstance(d, dict)  # doctest: +SKIP
        True

    SeeAlso:
        - ``bridge.loadBridge`` — 원천 parquet.
        - ``invalidateCache`` — bridge 변경 후 무효화.

    Requires:
        - polars.

    Capabilities:
        - rawId lookup 의 메모리 dict (tier1 우선 — manual seed > corpus-learned).

    Guide:
        - 내부 helper — resolve* 경유.

    AIContext:
        - lru_cache — invalidateCache 로만 갱신.

    LLM Specifications:
        AntiPatterns:
            - tier 무시 금지 — tier 오름차순 정렬 후 첫 매핑 채택(tier1 우선).
        OutputSchema:
            - ``dict[tuple[str, str], str]``.
        Prerequisites:
            - bridge parquet (없으면 빈 dict).
        Freshness:
            - invalidateCache 시 재계산.
        Dataflow:
            - loadBridge → tier sort → dict.
        TargetMarkets:
            - KR + US 통합.
    """
    bridge = loadBridge()
    if bridge.is_empty():
        return {}
    sortedDf = bridge.sort("tier")
    out: dict[tuple[str, str], str] = {}
    for row in sortedDf.iter_rows(named=True):
        k = (row["rawId"], row["marketNs"])
        if k not in out:
            out[k] = row["disclosureKey"]
    return out


def resolveDisclosureKey(rawId: str | None, marketNs: str) -> str | None:
    """단일 rawId → disclosureKey (또는 None).

    Args:
        rawId: Layer 1 rawId (DART "NT_C_D826380" / US "us-gaap:...TextBlock").
        marketNs: 시장 namespace ("kr" / "us").

    Returns:
        disclosureKey 또는 None (unmapped → narrative fallback).

    Raises:
        없음.

    Example:
        >>> resolveDisclosureKey("BS_C", "kr")  # doctest: +SKIP
        'consolidatedBalanceSheet'
        >>> resolveDisclosureKey(None, "kr")

    SeeAlso:
        - ``resolveBatch`` — DataFrame 일괄 부착.
        - ``bridge`` — disclosureKey 어휘 SSOT.

    Requires:
        - polars (lookup dict).

    Capabilities:
        - 회사간·세계마켓간 정렬 키 단건 조회.

    Guide:
        - build 단계 disclosureKey 부착에 사용. None 은 정상(narrative).

    AIContext:
        - 순수 lookup — 부작용 0.

    LLM Specifications:
        AntiPatterns:
            - unmapped 에 임의 키 부여 금지 — None.
        OutputSchema:
            - ``str | None``.
        Prerequisites:
            - bridge parquet.
        Freshness:
            - invalidateCache 후 반영.
        Dataflow:
            - (rawId, marketNs) → _lookupDict → disclosureKey.
        TargetMarkets:
            - KR + US 통합.
    """
    if not rawId:
        return None
    return _lookupDict().get((rawId, marketNs))


def resolveBatch(df: pl.DataFrame, *, marketNs: str, useCanonical: bool = False) -> pl.DataFrame:
    """panel artifact DataFrame → disclosureKey 컬럼 부착 (canonicalKey 또는 bridge).

    KR within-market 정렬키는 ``useCanonical=True`` 시 ``canonicalKeyExpr``(native ACLASS
    scope-strip, 테이블 0, 커버 ~100%)로 채운다. 옛 bridge 경로(``useCanonical=False``, 손수
    seed lookup)는 US cross-market overlay·하위호환용으로 유지.

    Args:
        df: panel artifact (xbrlClass 컬럼 보유).
        marketNs: 빌드 시장 ("kr" / "us"). bridge 경로에서만 lookup 키로 사용.
        useCanonical: True 면 canonicalKey 순수함수, False(기본) 면 bridge lookup.

    Returns:
        ``disclosureKey`` 컬럼이 채워진 DataFrame (원본 비면 그대로).

    Raises:
        없음.

    Example:
        >>> import polars as pl
        >>> df = pl.DataFrame({"xbrlClass": ["NT_C_D826380", "UNKNOWN"]})
        >>> resolveBatch(df, marketNs="kr", useCanonical=True)["disclosureKey"].to_list()
        ['NT_D826380', 'UNKNOWN']

    SeeAlso:
        - ``canonicalKeyExpr`` — useCanonical 경로의 native 정렬키.
        - ``resolveDisclosureKey`` — bridge 단건 조회.
        - gather ``builder`` — BUILD 단계 본 함수로 disclosureKey 채움(KR=useCanonical).

    Requires:
        - polars. (useCanonical=False 시 bridge parquet)

    Capabilities:
        - BUILD 단계 일괄 disclosureKey 부착 → runtime resolve 회피(경량).

    Guide:
        - build write 시점 호출. KR=useCanonical=True, US=False(bridge). reader 는 채워진 컬럼 사용.

    AIContext:
        - useCanonical=canonicalKeyExpr(SIMD). bridge=map_elements lookup.

    When:
        - build write 시점 artifact 에 disclosureKey 를 부착할 때.

    How:
        - useCanonical: xbrlClass → canonicalKeyExpr. else: xbrlClass → _lookupDict.

    LLM Specifications:
        AntiPatterns:
            - runtime 매 read resolve 금지 — build 에서 1회 부착.
            - KR 에 bridge(useCanonical=False) 고정 금지 — 손 seed scatter 회귀(P5 후 canonical 기본).
        OutputSchema:
            - ``pl.DataFrame`` (+ disclosureKey Utf8).
        Prerequisites:
            - xbrlClass 컬럼. (bridge 경로 시 bridge parquet)
        Freshness:
            - bridge 변경 시 재빌드 또는 invalidateCache. canonical 은 코드 규칙(재빌드만).
        Dataflow:
            - useCanonical: xbrlClass → canonicalKeyExpr → disclosureKey. else: _lookupDict.
        TargetMarkets:
            - KR (canonical) + US (bridge overlay).
    """
    if df.is_empty() or "xbrlClass" not in df.columns:
        return df
    if useCanonical:
        return df.with_columns(canonicalKeyExpr("xbrlClass").alias("disclosureKey"))
    lookup = _lookupDict()
    keys = df["xbrlClass"].map_elements(
        lambda x: lookup.get((x, marketNs)) if x else None,
        return_dtype=pl.Utf8,
    )
    return df.with_columns(keys.alias("disclosureKey"))


def invalidateCache() -> None:
    """bridge parquet 변경 후 lookup·bridge 캐시 초기화.

    Args:
        없음.

    Returns:
        None.

    Raises:
        없음.

    Example:
        >>> invalidateCache()

    SeeAlso:
        - ``bridge.loadBridge`` — 무효화 대상 캐시.
        - ``_lookupDict`` — 무효화 대상 캐시.

    Requires:
        - 없음.

    Capabilities:
        - learn(tier2/3) 또는 seed 갱신 후 동일 프로세스 내 즉시 반영.

    Guide:
        - bridge parquet write 직후 호출.

    AIContext:
        - 캐시 clear 부작용만.

    LLM Specifications:
        AntiPatterns:
            - bridge 갱신 후 미호출 시 stale lookup.
        OutputSchema:
            - ``None``.
        Prerequisites:
            - 없음.
        Freshness:
            - 호출 즉시 다음 resolve 가 재로드.
        Dataflow:
            - cache_clear (_lookupDict + loadBridge).
        TargetMarkets:
            - KR + US 공통.
    """
    _lookupDict.cache_clear()
    loadBridge.cache_clear()
