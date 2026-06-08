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
    인자도 같은 이름·같은 어휘를 쓴다. US 는 현재 row(주석·서술) 비교만 열려 있고 재무 셀
    비교(``topic`` 이 ``bs/is/cf/cis/sce``)는 EDGAR native adapter 확정 전까지 차단된다.

    Args:
        codes: US ticker 하나 또는 ticker 목록 (2~6개).
        topic: None이면 전체 격자. row 비교는 disclosureKey/sectionLeaf 부분일치.
        period: None, ``"2025Q4"``, ``"2025"``, 또는 리스트.
        scope: None, ``"consolidated"``, ``"separate"``.
        freq: ``"quarter"``/``"year"``/``"ytd"`` (DART 와 동일 어휘). 재무 셀모드 입도라
            row-only 인 US 경로에서는 실질 영향이 없다 — 계약 대칭을 위해 받기만 한다.

    Returns:
        ticker 간 비교 wide DataFrame.

    Raises:
        ValueError: 하위 DART compare 계약에서 입력/데이터가 유효하지 않을 때
            (대상 수, code/period/scope/freq 오타, 시장 혼합, US finance compare 시도).

    Example:
        >>> compare(["AAPL", "MSFT"], topic="revenue")  # doctest: +SKIP
    """
    return _compare(codes, topic=topic, period=period, scope=scope, freq=freq)


__all__ = ["compare"]
