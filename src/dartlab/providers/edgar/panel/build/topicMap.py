"""EDGAR panel topic 파싱 — sections ``topic`` → (form, itemId, sectionPath) (순수 규칙, 테이블 0).

DART ``panel.mapper.canonicalKey`` 의 EDGAR analog. gather 가 이미 itemize 한 sections ``topic``
(``"10-K::item1Business"`` 형식 = ``{form}::{itemId}``)에서 수평화 행 키(itemId)·문서종류(form)·
계층 truth(sectionPath)를 형식 규칙만으로 뽑는다 — 의미 추론·학습·매핑 농장 0. itemId 가
``panel`` 의 ``sectionLeaf`` (기간 가로질러 안정한 rowIdentity 키), form 이 ``chapter``.

scalar(``parseTopic``)과 Expr(``itemIdExpr``)이 **같은 규칙**(첫 ``::`` 기준 분리) — build 가
Expr(컬럼 일괄), 테스트가 scalar 로 동치 검증(DART canonicalKey/canonicalKeyExpr 쌍과 같은 SSOT 패턴).

LLM Specifications:
    AntiPatterns:
        - itemId 에 의미 매핑/별칭 부여 금지 — topic 형식 그대로(gather 가 이미 canonical).
        - ``::`` 부재 topic 에 임의 분해 금지 — (topic, topic, topic) honest passthrough.
        - scalar/Expr 규칙 분기 금지 — 첫 ``::`` 기준 동일(테스트 동치 강제).
    OutputSchema:
        - ``parseTopic(topic) -> tuple[str, str, str]`` (form, itemId, sectionPath).
        - ``itemIdExpr(col) -> pl.Expr`` (alias "sectionLeaf").
    Prerequisites:
        - polars (Expr).
    Freshness:
        - 순수함수 — 입력 외 의존 0.
    Dataflow:
        - topic → 첫 ``::`` 분리 → (앞=form, 뒤=itemId), 전체=sectionPath.
    TargetMarkets:
        - US (EDGAR sections topic).
"""

from __future__ import annotations

import polars as pl

_TOPIC_SEP = "::"


def parseTopic(topic: str | None) -> tuple[str, str, str]:
    """EDGAR sections ``topic`` → (form, itemId, sectionPath) — 첫 ``::`` 기준 분리 (순수).

    ``"10-K::item1Business"`` → ``("10-K", "item1Business", "10-K::item1Business")``. itemId 는
    panel ``sectionLeaf`` (기간 안정 수평화 키), sectionPath 는 계층 truth(topic 전체 보존).
    ``::`` 없으면 honest passthrough — (topic, topic, topic) (분해 추측 0).

    Args:
        topic: sections ``topic`` 문자열 (None/"" 허용).

    Returns:
        ``(form, itemId, sectionPath)`` 튜플. None/"" 입력은 ("", "", "").

    Raises:
        없음 — None 은 "" 로 흡수.

    Example:
        >>> parseTopic("10-K::item1Business")
        ('10-K', 'item1Business', '10-K::item1Business')
        >>> parseTopic("10-Q::partIItem2Mdna")
        ('10-Q', 'partIItem2Mdna', '10-Q::partIItem2Mdna')
        >>> parseTopic("noseparator")
        ('noseparator', 'noseparator', 'noseparator')
        >>> parseTopic(None)
        ('', '', '')

    SeeAlso:
        - ``itemIdExpr`` — 동일 규칙 polars Expr (build 일괄).
        - ``providers.dart.panel.mapper.canonicalKey`` — DART analog (ACLASS scope-strip).

    Requires:
        - 없음 (순수 문자열 함수).

    Capabilities:
        - sections topic 에서 수평화 행 키(itemId)·문서종류(form)·계층 truth 를 형식 규칙만으로 산출.

    Guide:
        - build(itemIdExpr 일괄)·테스트(scalar 동치). 직접 호출 안전(순수).

    AIContext:
        - gather sections topic 위 형식 규칙만 — 의미 추론 0.

    When:
        - sections topic 을 panel chapter/sectionLeaf/sectionPath 로 가를 때.

    How:
        - 첫 ``::`` partition → (form, itemId), sectionPath = topic 전체.

    LLM Specifications:
        AntiPatterns:
            - 두 번째 ``::`` 에서 분리 금지 — 첫 ``::`` partition(itemId 가 나머지 전체).
        OutputSchema:
            - ``tuple[str, str, str]``.
        Prerequisites:
            - 없음.
        Freshness:
            - 순수함수.
        Dataflow:
            - topic → partition("::") → (form, itemId, topic).
        TargetMarkets:
            - US (EDGAR).
    """
    t = topic or ""
    if _TOPIC_SEP in t:
        form, _sep, item = t.partition(_TOPIC_SEP)
        return (form, item, t)
    return (t, t, t)


def itemIdExpr(col: str = "topic") -> pl.Expr:
    """``parseTopic`` 의 itemId 를 산출하는 polars Expr — build 컬럼 일괄 (scalar 와 동치).

    첫 ``::`` 뒤 전체를 itemId 로 (``parseTopic[1]`` 동일). ``::`` 부재면 topic 그대로. build 가
    ``sectionLeaf`` 컬럼 산출에 사용 — map_elements 회피(SIMD columnar).

    Args:
        col: topic 컬럼명 (기본 "topic").

    Returns:
        ``sectionLeaf`` 별칭 Utf8 Expr.

    Raises:
        없음.

    Example:
        >>> import polars as pl
        >>> df = pl.DataFrame({"topic": ["10-K::item1Business", "10-Q::partIItem1ARiskFactors", "bare"]})
        >>> df.select(itemIdExpr())["sectionLeaf"].to_list()
        ['item1Business', 'partIItem1ARiskFactors', 'bare']

    SeeAlso:
        - ``parseTopic`` — scalar 동치 (테스트로 강제).

    Requires:
        - polars.

    Capabilities:
        - topic 컬럼을 itemId(sectionLeaf)로 일괄 — 기간 안정 수평화 키.

    Guide:
        - ``builder.sectionsToPanel`` 내부 사용. 직접 호출 가능.

    AIContext:
        - split("::").list.slice(1).join — 첫 구분자 뒤 전체(partition 동치), 부재면 원본.

    When:
        - sections topic 컬럼을 panel sectionLeaf 로 일괄 변환할 때.

    How:
        - split("::") → 길이>1 이면 slice(1) join("::"), else 원본.

    LLM Specifications:
        AntiPatterns:
            - list.last() 금지 — 다중 ``::`` 에서 partition 과 어긋남(slice(1).join 가 정답).
        OutputSchema:
            - ``pl.Expr`` (alias "sectionLeaf", Utf8).
        Prerequisites:
            - polars. topic 컬럼.
        Freshness:
            - 순수 Expr.
        Dataflow:
            - topic → split("::") → slice(1).join 또는 원본.
        TargetMarkets:
            - US (EDGAR).
    """
    c = pl.col(col).cast(pl.Utf8).fill_null("")
    parts = c.str.split(_TOPIC_SEP)
    rest = parts.list.slice(1).list.join(_TOPIC_SEP)
    return pl.when(parts.list.len() > 1).then(rest).otherwise(c).alias("sectionLeaf")
