"""EDGAR panel compare facade — DART compare surface for US tickers."""

from __future__ import annotations

import polars as pl

from dartlab.providers.dart.panel.compare import compare as _compare


def compare(
    codes: list[str] | str,
    *,
    topic: str | None = None,
    period: list[str] | str | None = None,
    scope: str | None = None,
    freq: str = "quarter",
) -> pl.DataFrame:
    """N개 EDGAR ticker panel 을 DART compare 계약으로 비교한다.

    호출계약은 ``dartlab.compare`` (DART) 와 동일하다 — 단어 1 개 톱레벨 verb, keyword-only
    인자도 같은 이름·같은 어휘를 쓴다. row(주석·서술) 비교와 재무 셀 비교(``topic`` 이
    ``bs/is/cf/cis/sce``) 둘 다 열려 있다 — 재무 셀은 EDGAR native account(snakeId) 정렬,
    USD 실값(``valueUnit="USD"``). EDGAR native 는 연결(consolidated)만 존재해 ``scope="separate"``
    는 빈 결과(honest-gap)다.

    Args:
        codes: US ticker 하나 또는 ticker 목록 (2~6개).
        topic: None이면 전체 격자. 재무 키(bs/is/cf/cis/sce)는 native account 단위 비교,
            그 외는 disclosureKey/sectionLeaf 부분일치 row 비교.
        period: None, ``"2025Q4"``, ``"2025"``, 또는 리스트.
        scope: None, ``"consolidated"``, ``"separate"``.
        freq: ``"quarter"``/``"year"``/``"ytd"`` (DART 와 동일 어휘). 재무 셀모드 입도를 정한다.

    Returns:
        ticker 간 비교 wide DataFrame.

    Raises:
        ValueError: 하위 DART compare 계약에서 입력/데이터가 유효하지 않을 때
            (대상 수, code/period/scope/freq 오타, 시장 혼합).

    Example:
        >>> compare(["AAPL", "MSFT"], topic="revenue")  # doctest: +SKIP
    """
    return _compare(codes, topic=topic, period=period, scope=scope, freq=freq)


__all__ = ["compare"]
