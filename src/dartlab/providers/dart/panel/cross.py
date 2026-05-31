"""panel 회사간·세계마켓간 수평화 (L1 read) — disclosureKey 로 다회사·다시장 정렬.

같은 disclosureKey 를 여러 회사(회사간)·여러 시장(세계마켓간)에서 읽어 가로 정렬한다.
disclosureKey 가 cross-company/market canonical 이라 같은 의미 disclosure 가 한 보드에 모임.

⚠️ P5 구현 = per-company read (정확). slim ``_index.parquet`` 가속(G6, 100+ 회사 풀로드
회피)은 P4 에서 index 빌드 후 본 모듈이 활용 — 그 전엔 정확하되 대량은 느림(정직).

LLM Specifications:
    AntiPatterns:
        - 전 회사 contentRaw 풀로드 후 필터 금지(대량 OOM) — P4 index 로 locator 선별 예정.
        - disclosureKey 없는 회사 silent drop 금지 — 결과에서 누락 명시(없으면 행 0).
        - network/lxml import 금지(R2).
    OutputSchema:
        - ``crossCompany(codes, disclosureKey, ...) -> pl.DataFrame | None`` (corp × period).
        - ``crossMarket(codesByMarket, disclosureKey, ...) -> pl.DataFrame | None``.
    Prerequisites:
        - polars. 각 회사 panel artifact.
    Freshness:
        - 매 호출 read.
    Dataflow:
        - codes → 각 readPanelWide(filter disclosureKey) → corp 부착 → diagonal concat.
    TargetMarkets:
        - KR (DART) + US (EDGAR, marketNs="us").
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

from .pivot import readPanelWide
from .reader import resolveKeyArg

_log = logging.getLogger(__name__)

# codes=None 자동발견 상한 — 초과 시 OOM 가드로 raise (전 회사 wide 풀로드 방지).
_MAX_AUTO_CODES = 100


def _indexCodesFor(keys: list[str], marketNs: str) -> list[str] | None:
    """slim _index.parquet 로 canonicalKey(들) 보유 종목 발견 (G6 가속).

    Args:
        keys: canonicalKey 후보 list (resolveKeyArg 산출 — exact + 라벨 매칭).
        marketNs: 시장 namespace ("kr"/"us").

    Returns:
        해당 disclosure 를 가진 corp list (정렬). index 없으면 None.

    Raises:
        없음 — index 부재/실패 시 None (caller fallback).

    Example:
        >>> _indexCodesFor(["NT_D826380"], "kr")  # doctest: +SKIP

    SeeAlso:
        - ``gather.dart.panel.buildIndex`` — _index.parquet 생산.
        - ``crossCompany`` — 본 helper 로 codes=None 처리.

    Requires:
        - polars. data/{dart|edgar}/panel/_index.parquet.

    Capabilities:
        - 전종목 풀스캔 없이 disclosure 보유 종목만 식별 (G6 — 본문 미read).

    Guide:
        - crossCompany(codes=None) 내부에서 사용.

    AIContext:
        - scan_parquet + filter(is_in) — locator 컬럼만(contentRaw 없음).

    LLM Specifications:
        AntiPatterns:
            - gather.index import 금지 — 경로 config 직접(providers↛gather, R1).
            - 본문 read 금지 — corp 컬럼만.
        OutputSchema:
            - ``list[str] | None``.
        Prerequisites:
            - _index.parquet (P4 buildIndex).
        Freshness:
            - index 갱신 시.
        Dataflow:
            - _index scan → filter(disclosureKey is_in keys) → corp unique.
        TargetMarkets:
            - KR + US.
    """
    base = "dart" if marketNs == "kr" else "edgar"
    p = Path(_cfg.dataDir) / base / "panel" / "_index.parquet"
    if not p.exists():
        return None
    try:
        corps = (
            pl.scan_parquet(str(p))
            .filter(pl.col("disclosureKey").is_in(keys))
            .select("corp")
            .unique()
            .collect()["corp"]
            .to_list()
        )
    except (pl.exceptions.PolarsError, OSError):
        return None
    return sorted(c for c in corps if c)


def crossCompany(
    codes: list[str] | None = None,
    disclosureKey: str = "",
    *,
    marketNs: str = "kr",
    periods: list[str] | None = None,
    byLabel: bool = True,
) -> pl.DataFrame | None:
    """여러 회사의 동일 disclosure 를 가로 정렬 (회사간 수평화).

    Args:
        codes: 종목코드 list. None 이면 ``_index.parquet`` 로 disclosure 보유 종목 자동 발견(G6).
        disclosureKey: canonicalKey("NT_D826380") 또는 한글 라벨 substring("재고", byLabel 시).
        marketNs: 시장 namespace (기본 "kr").
        periods: 특정 period 만. None = 전체.
        byLabel: True(기본) 면 한글 라벨 substring 도 매칭.

    Returns:
        rows = (corp, scope, …), columns = period 인 DataFrame. 해당 disclosure 가
        한 회사도 없으면 None.

    Raises:
        ValueError: codes=None 자동발견이 ``_MAX_AUTO_CODES``(100) 초과 시 — 전 회사 wide
            풀로드 OOM 가드. 명시 codes 를 전달하면 우회. 회사별 read 실패는 skip(로그).

    Example:
        >>> crossCompany(["005930", "000660"], "inventoryDisclosure")  # doctest: +SKIP

    SeeAlso:
        - ``pivot.readPanelWide`` — 회사내 수평화.
        - ``crossMarket`` — 다시장 확장.

    Requires:
        - polars. 각 회사 panel artifact.

    Capabilities:
        - 같은 disclosure 를 N개 회사 가로 비교 (회사간 정규화, G3 데이터 위에서 동작).

    Guide:
        - board 에서 disclosureKey 확인 후 codes 지정. 대량은 P4 index 후.

    AIContext:
        - per-company read + diagonal concat — corp 컬럼으로 출처 보존.

    When:
        - 같은 disclosure 를 여러 회사에 걸쳐 가로 비교할 때.

    How:
        - codes(또는 _index 자동발견) → readPanelWide filter → diagonal concat.

    LLM Specifications:
        AntiPatterns:
            - 회사 누락 silent 금지 — 없으면 행 0(명시).
        OutputSchema:
            - ``pl.DataFrame | None`` (corp + scope + period 열).
        Prerequisites:
            - 각 회사 panel artifact + disclosureKey 매핑.
        Freshness:
            - 매 호출.
        Dataflow:
            - codes → readPanelWide filter(disclosureKey) → corp 부착 → diagonal concat.
        TargetMarkets:
            - KR + US.
    """
    if not disclosureKey:
        return None
    keys = resolveKeyArg(disclosureKey, marketNs=marketNs, byLabel=byLabel)
    if codes is None:
        codes = _indexCodesFor(keys, marketNs)
        if not codes:
            return None
        if len(codes) > _MAX_AUTO_CODES:
            raise ValueError(
                f"crossCompany(codes=None, '{disclosureKey}') 자동발견 {len(codes)} 종목 — "
                f"전 회사 wide 풀로드는 OOM 위험({_MAX_AUTO_CODES} 초과, Polars 네이티브 힙). "
                "명시 codes 를 전달하시오 (locator 기반 lazy cell pull 최적화는 후속)."
            )
    frames: list[pl.DataFrame] = []
    for code in codes:
        wide = readPanelWide(code, marketNs=marketNs, periods=periods)
        if wide is None or "disclosureKey" not in wide.columns:
            continue
        sub = wide.filter(pl.col("disclosureKey").is_in(keys))
        if sub.is_empty():
            continue
        sub = sub.with_columns(pl.lit(code).alias("corp"), pl.lit(marketNs).alias("marketNs"))
        frames.append(sub)
    if not frames:
        return None
    return pl.concat(frames, how="diagonal")


def crossMarket(
    codesByMarket: dict[str, list[str]],
    disclosureKey: str,
    *,
    periods: list[str] | None = None,
) -> pl.DataFrame | None:
    """여러 시장의 동일 disclosure 를 가로 정렬 (세계마켓간 수평화).

    Args:
        codesByMarket: ``{marketNs: [codes]}`` (예: ``{"kr": ["005930"], "us": ["AAPL"]}``).
        disclosureKey: universal disclosureKey.
        periods: 특정 period 만. None = 전체.

    Returns:
        시장 무관 한 보드 (corp/marketNs × period). 없으면 None.

    Raises:
        없음.

    Example:
        >>> crossMarket({"kr": ["005930"], "us": ["AAPL"]}, "inventoryDisclosure")  # doctest: +SKIP

    SeeAlso:
        - ``crossCompany`` — 단일 시장.
        - ``core.panel.bridge`` — KR ACLASS / US us-gaap 동일 disclosureKey.

    Requires:
        - polars. 각 시장 panel artifact.

    Capabilities:
        - DART↔EDGAR 동일 disclosure 한 보드 정렬 — schema/disclosureKey market-neutral(G7).

    Guide:
        - US panel(EDGAR) 빌드는 후속. 현재는 KR 위주, 구조는 다시장 ready.

    AIContext:
        - crossCompany 를 시장별 호출 후 diagonal concat.

    When:
        - DART↔EDGAR 동일 disclosure 를 한 보드로 정렬할 때.

    How:
        - market 별 crossCompany → diagonal concat.

    LLM Specifications:
        AntiPatterns:
            - 시장별 schema 분기 금지 — 14-col 동결(값으로 시장차이).
        OutputSchema:
            - ``pl.DataFrame | None`` (corp/marketNs + period).
        Prerequisites:
            - 각 시장 panel artifact + bridge 동일 disclosureKey.
        Freshness:
            - 매 호출.
        Dataflow:
            - market 별 crossCompany → diagonal concat.
        TargetMarkets:
            - KR + US (JP 후속).
    """
    frames: list[pl.DataFrame] = []
    for marketNs, codes in codesByMarket.items():
        cc = crossCompany(codes, disclosureKey, marketNs=marketNs, periods=periods)
        if cc is not None:
            frames.append(cc)
    if not frames:
        return None
    return pl.concat(frames, how="diagonal")
