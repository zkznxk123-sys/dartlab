"""전종목 단일 계정/비율 연간 시계열 배치 추출.

finance parquet 2,744개를 병렬 읽기하여
특정 snakeId 하나의 전종목 × 연도 시계열 DataFrame을 생성한다.

Q4 사업보고서 thstrm_amount = 연간 누적값이므로 standalone 변환 불필요.

설계: ThreadPool I/O + 파일별 즉시 필터(CFS+account 매칭)
      → concat 대상 ~25K행 → 메모리 +135MB, 속도 ~3초
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from dartlab.core.memory import withMemoryBudget
from dartlab.providers.dart.finance.mapper import (
    ACCOUNT_NAME_SYNONYMS,
    ID_SYNONYMS,
    AccountMapper,
)

_log = logging.getLogger(__name__)


_REPRT_TO_Q = {"1분기": "Q1", "2분기": "Q2", "3분기": "Q3", "4분기": "Q4"}


def _resolveSjDiv(snakeId: str) -> str:
    """sortOrder.json에서 snakeId → sjDiv 자동 결정."""
    from dartlab.core.utils.ordering import _ensureLoaded

    data = _ensureLoaded()
    for sjDiv in ("IS", "BS", "CF"):
        if snakeId in data.get(sjDiv, {}):
            return sjDiv
    msg = f"snakeId '{snakeId}'를 sortOrder.json에서 찾을 수 없습니다"
    raise ValueError(msg)


def _parseAmount(val: str | None) -> float | None:
    """문자열 금액 → float. 쉼표 제거, 빈값 → None."""
    if val is None:
        return None
    cleaned = str(val).replace(",", "").strip()
    if not cleaned or cleaned == "-":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _buildFastKeys(snakeId: str) -> set[str]:
    """snakeId에 매핑되는 모든 원본 키를 사전 수집 (O(1) set lookup)."""
    mapper = AccountMapper.get()
    mappings = mapper._mappings or {}

    directKeys: set[str] = set()
    for key, sid in mappings.items():
        if sid == snakeId:
            directKeys.add(key)

    allKeys = set(directKeys)
    for synonym, canonical in ACCOUNT_NAME_SYNONYMS.items():
        if canonical in directKeys:
            allKeys.add(synonym)

    for synonym, canonical in ID_SYNONYMS.items():
        if canonical in directKeys:
            allKeys.add(synonym)
            for prefix in ("ifrs-full_", "ifrs_", "dart_", "ifrs-smes_"):
                allKeys.add(prefix + synonym)

    for key in list(directKeys):
        for prefix in ("ifrs-full_", "ifrs_", "dart_", "ifrs-smes_"):
            allKeys.add(prefix + key)

    return allKeys


def _parseAmountCol(col: str) -> pl.Expr:
    """금액 문자열 컬럼 → Float64."""
    return (
        pl.col(col)
        .cast(pl.Utf8)
        .str.replace_all(",", "")
        .str.strip_chars()
        .pipe(lambda s: pl.when(s == "").then(None).when(s == "-").then(None).otherwise(s))
        .cast(pl.Float64, strict=False)
    )


def _resolveSnakeId(nameOrId: str) -> str:
    """한글 항목/영문 snakeId → 정규 snakeId 변환."""
    # 이미 snakeId면 그대로
    if nameOrId.isascii() and "_" in nameOrId:
        return nameOrId

    # mapper로 한글 → snakeId 변환
    mapper = AccountMapper.get()
    # 한글명 우선
    normalizedNm = ACCOUNT_NAME_SYNONYMS.get(nameOrId, nameOrId)
    if normalizedNm in (mapper._mappings or {}):
        return mapper._mappings[normalizedNm]
    # 공백 제거 후 재시도
    noSpace = normalizedNm.replace(" ", "")
    if noSpace in (mapper._mappings or {}):
        return mapper._mappings[noSpace]
    # 영문 ID로도 시도
    stripped = nameOrId.lower().replace("-", "").replace(" ", "")
    normalizedId = ID_SYNONYMS.get(stripped, stripped)
    if normalizedId in (mapper._mappings or {}):
        return mapper._mappings[normalizedId]

    # 변환 실패 시 원본 반환 (이후 _resolveSjDiv에서 에러)
    return nameOrId


def _scanAccountFromMerged(
    scanPath: Path | None,
    snakeId: str,
    sjDiv: str,
    filterDivs: list[str],
    fsPref: str,
    fastKeys: set[str],
    *,
    freq: str = "Q",
    lazyFrame: pl.LazyFrame | None = None,
) -> pl.DataFrame | None:
    """단일 계정 시계열 추출 — 합본 또는 raw glob LazyFrame 모두 처리.

    scanPath 경로 (프리빌드 ``finance.parquet`` 또는 ``finance-lite.parquet``) 가
    있으면 그것을, 없으면 ``lazyFrame`` 주입 인자 (raw glob DuckDB 결과) 를 받아
    동일 후처리 (CFS/OFS · 분기 standalone · 종목 wide pivot) 적용.

    Pyodide(브라우저 WASM) 에서는 polars `scan_parquet` 이 미지원이라 pyarrow 로
    전체 로드 → `pl.from_arrow` 로 DataFrame 전환 후 동일 필터 연산. 원본 파일은
    `finance-lite.parquet`(18MB) 이므로 메모리 부담 없음.
    """
    from dartlab.core.dataLoader import _IS_PYODIDE

    try:
        if lazyFrame is not None:
            # raw glob fallback path (DuckDB 가 sj_div 필터까지만 push-down)
            # account 매칭은 polars 단에서 (fastKeys 에 `'` 등 SQL 특수문자 포함 안전)
            scCol = "stockCode"
            fastKeysList = list(fastKeys)
            lz = lazyFrame.filter(pl.col("account_nm").is_in(fastKeysList) | pl.col("account_id").is_in(fastKeysList))
            if freq == "Y":
                lz = lz.filter(pl.col("reprt_nm") == "4분기")
            df = lz.collect(engine="streaming")
        elif _IS_PYODIDE:
            import pyarrow.parquet as pq

            fastKeysList = list(fastKeys)
            # finance-lite 스키마 고정: stockCode, bsns_year, reprt_nm, sj_div, fs_nm,
            # account_id, account_nm, thstrm_amount, thstrm_add_amount
            tbl = pq.read_table(str(scanPath))
            scCol = "stockCode" if "stockCode" in tbl.column_names else "stock_code"
            df = pl.from_arrow(tbl).filter(
                pl.col("sj_div").is_in(filterDivs)
                & (pl.col("account_nm").is_in(fastKeysList) | pl.col("account_id").is_in(fastKeysList))
            )
            if freq == "Y":
                df = df.filter(pl.col("reprt_nm") == "4분기")
        else:
            schema = pl.scan_parquet(str(scanPath)).collect_schema()
            scCol = "stockCode" if "stockCode" in schema.names() else "stock_code"

            lz = pl.scan_parquet(str(scanPath)).filter(
                pl.col("sj_div").is_in(filterDivs)
                & (pl.col("account_nm").is_in(list(fastKeys)) | pl.col("account_id").is_in(list(fastKeys)))
            )

            if freq == "Y":
                lz = lz.filter(pl.col("reprt_nm") == "4분기")

            df = lz.collect(engine="streaming")
    except (pl.exceptions.PolarsError, OSError, FileNotFoundError):
        return None

    if df.is_empty():
        return None

    # CFS/OFS 우선: 종목별로 연결재무제표가 있으면 연결만
    cfsLabel = "연결" if fsPref == "CFS" else "재무제표"
    hasCfs = df.filter(pl.col("fs_nm").str.contains(cfsLabel)).select(scCol).unique().to_series().to_list()
    hasCfsSet = set(hasCfs)

    # 연결 있는 종목은 연결만, 없는 종목은 전체
    if hasCfsSet:
        cfsPart = df.filter(pl.col(scCol).is_in(list(hasCfsSet)) & pl.col("fs_nm").str.contains(cfsLabel))
        ofsPart = df.filter(~pl.col(scCol).is_in(list(hasCfsSet)))
        df = pl.concat([cfsPart, ofsPart]) if not ofsPart.is_empty() else cfsPart

    if df.is_empty():
        return None

    # 금액 파싱
    df = df.with_columns(_parseAmountCol("thstrm_amount").alias("amount"))

    if freq == "Y":
        # 연간: thstrm_amount (4분기 사업보고서) 그대로
        parsed = df.filter(pl.col("amount").is_not_null())
        if parsed.is_empty():
            return None
        result = (
            parsed.select(
                pl.col(scCol).alias("stockCode"),
                pl.col("bsns_year").cast(pl.Utf8).alias("period"),
                pl.col("amount"),
            )
            .group_by(["stockCode", "period"])
            .agg(pl.col("amount").first())
        )
    else:
        # 분기별 standalone 계산 — Polars 벡터 연산
        df = df.with_columns(_parseAmountCol("thstrm_add_amount").alias("_addAmount"))
        df = df.filter(pl.col("amount").is_not_null())
        if df.is_empty():
            return None

        isBs = sjDiv == "BS"

        # period 컬럼 생성
        qMap = pl.DataFrame({"reprt_nm": list(_REPRT_TO_Q.keys()), "_qLabel": list(_REPRT_TO_Q.values())})
        df = df.join(qMap, on="reprt_nm", how="inner")
        df = df.with_columns((pl.col("bsns_year").cast(pl.Utf8) + pl.col("_qLabel")).alias("period"))

        if isBs:
            # BS: 잔액 그대로
            result = df.select(
                pl.col(scCol).alias("stockCode"),
                pl.col("period"),
                pl.col("amount"),
            )
        else:
            # IS/CF: 1~3분기 thstrm = standalone, 4분기 = thstrm - Q3 addAmount
            notQ4 = df.filter(pl.col("reprt_nm") != "4분기").select(
                pl.col(scCol).alias("stockCode"),
                pl.col("period"),
                pl.col("amount"),
            )

            q4 = df.filter(pl.col("reprt_nm") == "4분기")
            q3Add = df.filter(pl.col("reprt_nm") == "3분기").select(
                pl.col(scCol).alias("_sc"),
                pl.col("bsns_year").alias("_by"),
                pl.col("_addAmount").alias("_q3add"),
            )
            q4j = q4.join(q3Add, left_on=[scCol, "bsns_year"], right_on=["_sc", "_by"], how="left")
            q4j = q4j.with_columns(
                pl.when(pl.col("_q3add").is_not_null())
                .then(pl.col("amount") - pl.col("_q3add"))
                .otherwise(pl.col("amount"))
                .alias("amount")
            ).select(
                pl.col(scCol).alias("stockCode"),
                pl.col("period"),
                pl.col("amount"),
            )
            result = pl.concat([notQ4, q4j])

    return result


@withMemoryBudget(limitMb=500)
def scanAccount(
    snakeId: str,
    *,
    sjDiv: str | None = None,
    fsPref: str = "CFS",
    freq: str = "Q",
) -> pl.DataFrame:
    """전종목 단일 계정 시계열 — dartlab scan 의 **원자 primitive**.

    scan 의 모든 복합 축 (profitability · growth · quality · liquidity 등) 은 이 함수의
    반환값을 **polars join + with_columns** 로 조합해 만들 수 있다. prebuild 된
    ``finance.parquet`` 한 파일을 lazy scan + push-down filter 로 한 번에 추출하므로
    2664 종목 전체가 수 초에 나온다. Python for 문 없음, iter_rows 없음.

    **사상**: 개별 계정 (원자) + ``scanRatio`` (비율) 조합이 **무궁무진**. AI 는 질문에
    맞춰 이 두 축을 자유롭게 엮어라. 복합 축 (scan("profitability") 등) 은 그저
    **자주 쓰는 프리셋** 일 뿐이다.

    Parameters
    ----------
    snakeId : str
        계정 식별자. 영문 snake_case (``"sales"``, ``"operating_profit"``,
        ``"net_income"``) 또는 한글 (``"매출액"``, ``"영업이익"``, ``"당기순이익"``)
        모두 가능. 지원 목록은 ``scanAccountList()``.
    sjDiv : str | None, optional
        재무제표 구분 (``"IS"`` · ``"CIS"`` · ``"BS"`` · ``"CF"``). None 이면 snakeId
        로부터 자동 판정 (sortOrder.json).
    fsPref : {"CFS", "OFS"}, default "CFS"
        연결(CFS) 우선 · 별도(OFS) 우선. 연결 없으면 별도 fallback.
    freq : {"Q", "Y"}, default "Q"
        ``"Q"`` = 분기 데이터 (``2025Q4`` · ``2025Q3`` 컬럼 — 가장 최신 마일스톤 포함).
        ``"Y"`` = 연간 (``2025`` · ``2024`` 컬럼). Company 엔진의 `freq` 와 일치.

    Returns
    -------
    df : pl.DataFrame
        2664 종목 행. 컬럼:

        - ``stockCode`` : str — 종목코드
        - 기간 컬럼들 : float — 금액 (원)
          * freq="Q": ``"2025Q4"`` · ``"2025Q3"`` · ``"2025Q2"`` · ``"2024Q4"`` · ...
          * freq="Y": ``"2025"`` · ``"2024"`` · ``"2023"`` · ...

        종목별 자기 최신 기간이 있는 컬럼에만 값, 없으면 null. sort / head /
        with_columns 로 바로 조작 가능한 wide 테이블.

    Examples
    --------
    **단순 랭킹** — "영업이익 큰 회사 10":

    >>> scanAccount("operating_profit", freq="Y").sort("2025", descending=True).head(10)

    **YoY 성장률 상위**:

    >>> df = scanAccount("sales", freq="Y")
    >>> df.with_columns(((pl.col("2025") - pl.col("2024")) / pl.col("2024") * 100).alias("yoy")).sort("yoy", descending=True).head(20)

    **다계정 조합** — "매출 > 1조인데 영업이익 역성장":

    >>> rev = scanAccount("sales", freq="Y").select(["stockCode", "2025"]).rename({"2025": "rev25"})
    >>> op  = scanAccount("operating_profit", freq="Y").select(["stockCode", "2024", "2025"]).rename({"2024": "op24", "2025": "op25"})
    >>> rev.join(op, on="stockCode").filter((pl.col("rev25") > 1e12) & (pl.col("op25") < pl.col("op24")))

    **분기 모멘텀** — "최근 분기 대비 전분기 증가":

    >>> df = scanAccount("operating_profit", freq="Q")  # 분기
    >>> df.with_columns(((pl.col("2025Q4") - pl.col("2025Q3")) / pl.col("2025Q3")).alias("qoq"))

    Notes
    -----
    - ``finance.parquet`` prebuild 사용 (첫 호출 자동 다운로드). Python loop 없음.
    - 종목별 최신 기간 자동 정렬 — **latestYear 글로벌 필터 버그 없음**.
    - pyodide 환경은 경량본 ``finance-lite.parquet`` (~18MB) 자동 사용.

    Guide
    -----
    **⛔ 광역 발굴 질문 ("투자할만한 회사" / "좋은 회사" / "요즘 투자하기 좋은") 에
    scanAccount 하나만 쓰고 끝내지 말 것.** 계정 하나는 원자이고, 발굴은 최소 3~4
    축 조합이다. 자세한 레시피 · 7 관점 스크리닝 · 5 단계 워크플로는
    :func:`scanRatio` 의 Guide 섹션이 SSOT — 그쪽을 먼저 읽고 본 함수를 원자로 끼워
    넣는 구조로 조합한다.

    **이 함수의 4 가지 사용 패턴**:

    1. **단일 축 랭킹** — ``scanAccount("X", freq="Y").sort("YYYY", desc).head(N)``
    2. **시계열 변화** — 두 기간 컬럼으로 YoY/QoQ/CAGR 계산 (``with_columns``)
    3. **크로스 계정** — 매출 · 영업이익 · 순이익 · 자산 · 부채를 join 해 독자 비율 산출
       예) "매출 1조+ 인데 영업이익 역성장" = sales 상위 ∩ operating_profit YoY 음수
    4. **프리셋 대체** — ``scanRatio`` 와 join 해 primitive 조합으로 복합 스크린 구성

    **계정 1 개로 무엇을 판단하는가** — primitive 단독 호출 패턴 ::

        ┌──────────────────────────────────────┬───────────────────────────────────────────────────────┐
        │ 단독 호출                            │ 판단 (AI 가 이걸로 알 수 있는 것)                     │
        ├──────────────────────────────────────┼───────────────────────────────────────────────────────┤
        │ scanAccount("매출액", freq="Y")      │ 매출 규모 랭킹 — 1 조 클럽 · 1000 억 클럽 분류         │
        │ scanAccount("매출액", freq="Q")      │ 분기 매출 모멘텀 — 최근 QoQ 가속/감속 · 계절성        │
        │ scanAccount("영업이익", freq="Y")    │ 본업 수익 절대값 + 적자 종목 (음수) 분류              │
        │ scanAccount("연구개발비", freq="Y")  │ R&D 절대 규모 — 산업 강도 + 미래 투자 비교            │
        │ scanAccount("재고자산", freq="Q")    │ 재고 절대 규모 — 사이클 산업 (반도체·화학) 재고 사이클 │
        │ scanAccount("총자산", freq="Y")      │ 자산 거인 — 자본 집약도 + 산업 평균 대비 위치          │
        │ scanAccount("현금성자산", freq="Y")  │ 현금 보유 거인 — 자본환원 여력 (배당·자사주) 후보      │
        │ scanAccount("영업현금흐름", freq="Y")│ OCF 절대 규모 — 본업 현금 창출력 직접 비교             │
        │ scanAccount("이익잉여금", freq="Y")  │ 누적 이익 — 장기 흑자 누적 종목 분류                  │
        └──────────────────────────────────────┴───────────────────────────────────────────────────────┘

    **계정 2 개 join = 무한 조합** — ratio 가 미구현인 지표를 primitive 로 직접 만든다 ::

        ┌──────────────────────────────────────────┬──────────────────────────────────────────────────┐
        │ 두 계정 조합                             │ 새로 판단 가능한 것 (= 미구현 ratio 대체)          │
        ├──────────────────────────────────────────┼──────────────────────────────────────────────────┤
        │ 매출액 YoY + 영업이익 YoY                │ 마진 변화 — 매출 늘어도 이익 줄면 비용 압박       │
        │ 연구개발비 ÷ 매출액                      │ R&D 집약도 (R&D / Sales) — 경쟁력·미래 투자 강도  │
        │ 재고자산 YoY + 매출액 YoY                │ 재고 누적 vs 매출 정체 → 사이클 하강·불황 신호    │
        │ 현금성자산 + 단기차입금                  │ 단기 유동성 cushion — 부채비율보다 직접 측정       │
        │ 영업현금흐름 + 유형자산취득(CAPEX)       │ Free Cash Flow 추정 (FCF = OCF − CAPEX)            │
        │ 매출원가 ÷ 매출액                        │ 매출원가율 (= 1 − 매출총이익률) 추이              │
        │ 영업이익 ÷ 이자비용                      │ 이자보상배율 (interest coverage)                  │
        │ 매출액 ÷ 무형자산                        │ 무형자산 활용 효율 — 브랜드·IP 회사 영업 레버리지  │
        │ 자기자본 + 시가총액 (gather)             │ PBR 직접 계산 — 시가총액 ÷ 자기자본               │
        └──────────────────────────────────────────┴──────────────────────────────────────────────────┘

    **조합 예시 (scanRatio 와 엮는다)**:

    ========================================  ======================================================
    질문                                      scanAccount ⨝ scanRatio
    ========================================  ======================================================
    "자산 많은데 수익 못 내는"                total_assets 상위 ∩ scanRatio("roa") 하위
    "매출 큰데 영업이익 역성장"                sales 상위 ∩ operating_profit YoY 음수
    "현금 많이 쌓고 있는 회사"                 cash_and_cash_equivalents 상위 + YoY 양수 + debtRatio 낮음
    "R&D 비중 높은데 성장 느림"                 research_expenses / sales 상위 ∩ scanRatio("revenueGrowth") 하위
    ========================================  ======================================================

    Verified
    --------
    아래는 2026-04-27 시점 실데이터로 검증한 account ⨝ ratio 조합 한 예 ::

        # "자산 많은데 수익 못 내는" — total_assets 상위 200 ∩ ROA < 1% (2024)
        #    → 후보 77 종목. 상위 (roa asc):
        #      034220 LG디스플레이   (총자산 32.9 조 / ROA -7.3 %)
        #      011790 SKC            (총자산  6.7 조 / ROA -6.7 %)
        #      035760 CJ ENM         (총자산  9.3 조 / ROA -6.2 %)
        #      361610 SK아이이테크놀로지 (총자산 4.2 조 / ROA -5.9 %)
        #      011170 롯데케미칼    (총자산 34.5 조 / ROA -5.3 %)
        #    → 화학·디스플레이 시클리컬 적자 사이클 (단순 음수 ROA 가 아닌 자산 거인의
        #       구조적 비효율 vs 사이클 일시 적자 구분은 macro · scan("debt") 와 엮어 판단)

    See Also
    --------
    scanRatio : 비율 시계열 (primitive 2/2) — 발굴 레시피·7 관점 SSOT
    scanAccountList : 지원 계정 목록
    scan("profitability") · scan("growth") 등 : 자주 쓰는 프리셋 (이 함수 + scanRatio 조합 결과)

    Raises
    ------
    없음 (지원되지 않는 snakeId 또는 데이터 부재 시 빈 DataFrame).

    Args:
        snakeId: <TODO: param desc> (str)
        sjDiv: <TODO: param desc> (str | None)
        fsPref: <TODO: param desc> (str)
        freq: <TODO: param desc> (str)

    Returns:
        <TODO: return desc> (pl.DataFrame)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - concurrent
        - dartlab
        - logging
        - polars

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>
    """
    from dartlab.core.dataLoader import _dataDir

    snakeId = _resolveSnakeId(snakeId)

    if sjDiv is None:
        sjDiv = _resolveSjDiv(snakeId)

    filterDivs = ["IS", "CIS"] if sjDiv in ("IS", "CIS") else [sjDiv]
    fastKeys = _buildFastKeys(snakeId)

    # ── scan/finance(-lite).parquet 가속 경로 ──
    # Pyodide(브라우저) 에서는 경량본 `finance-lite.parquet`(~18MB) 을 우선 사용한다.
    # 일반 환경은 전량 `finance.parquet`(~307MB) 사용.
    import importlib

    from dartlab.core.dataLoader import _IS_PYODIDE

    _ensureScanData = importlib.import_module("dartlab.scan.io.parquet")._ensureScanData

    scanDir = _ensureScanData()
    scanFileName = "finance-lite.parquet" if _IS_PYODIDE else "finance.parquet"
    scanPath = scanDir / scanFileName
    allDf = None

    if scanPath.exists():
        allDf = _scanAccountFromMerged(
            scanPath,
            snakeId,
            sjDiv,
            filterDivs,
            fsPref,
            fastKeys,
            freq=freq,
        )
        if allDf is not None:
            _log.info("scanAccount('%s'): %s 가속 경로 사용", snakeId, scanFileName)

    # ── fallback: raw glob → DuckDB streaming SQL ──
    if allDf is None:
        financeDir = Path(_dataDir("finance"))
        parquetFiles = sorted(financeDir.glob("*.parquet"))

        if not parquetFiles:
            from dartlab.core.messaging import emit

            emit("hint:market_data_needed", category="finance", fn="scanAccount")
            return pl.DataFrame({"stockCode": []})

        _log.info(
            "scanAccount('%s', freq=%s): DuckDB raw glob fallback (%d 종목)",
            snakeId,
            freq,
            len(parquetFiles),
        )

        from dartlab.scan.io.parquet import _loadRawFinanceViaDuckDb

        # sinceYear=2021 — prebuild 합본과 동일 cutoff (buildFinance default)
        # account 매칭은 SQL push-down (raw 3M row → 매칭 row 만 polars 통과)
        lz = _loadRawFinanceViaDuckDb(
            financeDir,
            sjDivs=filterDivs,
            sinceYear=2021,
            accountIds=set(fastKeys),
            accountNms=set(fastKeys),
        )
        if lz is None:
            return pl.DataFrame({"stockCode": []})

        allDf = _scanAccountFromMerged(
            None,
            snakeId,
            sjDiv,
            filterDivs,
            fsPref,
            fastKeys,
            freq=freq,
            lazyFrame=lz,
        )

        if allDf is None or allDf.is_empty():
            return pl.DataFrame({"stockCode": []})

    # 기간당 첫 값 + pivot
    allDf = allDf.group_by(["stockCode", "period"]).agg(pl.col("amount").first())

    result = allDf.pivot(on="period", index="stockCode", values="amount")  # polars-streaming-unsupported: pivot
    periodCols = sorted(c for c in result.columns if c != "stockCode")

    # 분기: 첫 연도에 Q4만 존재하면 제거 (불완전 분기)
    if freq != "Y" and periodCols:
        firstYear = periodCols[0][:4]
        firstYearQs = [c for c in periodCols if c.startswith(firstYear)]
        if len(firstYearQs) == 1 and firstYearQs[0].endswith("Q4"):
            periodCols = periodCols[1:]

    # 최신 먼저 역순 정렬
    periodCols = list(reversed(periodCols))
    result = result.select(["stockCode"] + periodCols)

    _log.info(
        "scanAccount('%s'): %d종목 × %d기간",
        snakeId,
        result.height,
        len(periodCols),
    )

    return result


# ── scanRatio ──────────────────────────────────────────────────


_RATIO_DEFS: dict[str, dict] = {
    # 수익성
    "roe": {"numer": "net_income", "denom": "total_stockholders_equity", "pct": True, "label": "ROE"},
    "roa": {"numer": "net_income", "denom": "total_assets", "pct": True, "label": "ROA"},
    "operatingMargin": {
        "numer": "operating_profit",
        "denom": "sales",
        "pct": True,
        "label": "영업이익률",
    },
    "netMargin": {"numer": "net_income", "denom": "sales", "pct": True, "label": "순이익률"},
    "grossMargin": {"numer": "gross_profit", "denom": "sales", "pct": True, "label": "매출총이익률"},
    # 안정성
    "debtRatio": {
        "numer": "total_liabilities",
        "denom": "total_stockholders_equity",
        "pct": True,
        "label": "부채비율",
    },
    "currentRatio": {
        "numer": "current_assets",
        "denom": "current_liabilities",
        "pct": True,
        "label": "유동비율",
    },
    "equityRatio": {
        "numer": "total_stockholders_equity",
        "denom": "total_assets",
        "pct": True,
        "label": "자기자본비율",
    },
    # 성장성 (YoY)
    "revenueGrowth": {"base": "sales", "yoy": True, "pct": True, "label": "매출성장률"},
    "operatingProfitGrowth": {
        "base": "operating_profit",
        "yoy": True,
        "pct": True,
        "label": "영업이익성장률",
    },
    "netProfitGrowth": {
        "base": "net_income",
        "yoy": True,
        "pct": True,
        "label": "순이익성장률",
    },
    # 효율성
    "totalAssetTurnover": {
        "numer": "sales",
        "denom": "total_assets",
        "pct": False,
        "label": "총자산회전율",
    },
    # 현금흐름
    "operatingCfMargin": {
        "numer": "operating_cashflow",
        "denom": "sales",
        "pct": True,
        "label": "영업CF마진",
    },
}


def scanRatio(
    ratioName: str,
    *,
    fsPref: str = "CFS",
    freq: str = "Q",
) -> pl.DataFrame:
    """전종목 단일 재무비율 시계열 — dartlab scan 의 **원자 primitive 2**.

    ``scanAccount`` 와 짝. 비율 (영업이익률·ROE·ROA·부채비율·CCC 등) 을 전종목 ×
    시계열 형태로 추출. 모든 복합 축 프리셋 (profitability · quality · liquidity) 이
    이 함수의 결과를 **polars join + with_columns** 로 조합한 것에 지나지 않는다.

    **사상**: "수익성 좋은 회사 찾아줘" 같은 질문에 scan 복합 축만 쓰지 말고, 이 함수
    + ``scanAccount`` 를 자유 조합해 **질문 맥락에 딱 맞는 스크리닝** 을 즉석에서 구성.
    prebuild ``finance.parquet`` 을 lazy scan + pivot 으로 **한 번에 벡터 계산**.

    Parameters
    ----------
    ratioName : str
        비율 식별자. **정확한 지원 목록은 항상 ``scanRatioList()`` 로 확인**.
        현재 제공 13 종 (finance.parquet 로만 계산 가능한 범위):

        - 수익성: ``"roe"`` · ``"roa"`` · ``"operatingMargin"`` · ``"netMargin"`` · ``"grossMargin"``
        - 안정성: ``"debtRatio"`` · ``"currentRatio"`` · ``"equityRatio"``
        - 성장 (YoY): ``"revenueGrowth"`` · ``"operatingProfitGrowth"`` · ``"netProfitGrowth"``
        - 효율성: ``"totalAssetTurnover"``
        - 현금흐름: ``"operatingCfMargin"``

        ⛔ **호출 금지** — ``"pbr"`` · ``"per"`` · ``"psr"`` · ``"dividendYield"`` ·
        ``"evEbitda"`` 등 시가총액·배당 기반 밸류에이션 비율은 finance.parquet 으로
        계산 불가 → ``ValueError`` 즉시 raise. **반드시 ``scan("valuation")``** 사용
        (네이버 시총 snapshot 경로). 이자보상배율 · CCC · accrual ratio 등 미구현
        지표는 ``pythonExec`` 에서 primitive (``scanAccount``) 조합으로 직접 계산.
    fsPref : {"CFS", "OFS"}, default "CFS"
        연결(CFS) 우선 · 별도(OFS) 우선.
    freq : {"Q", "Y"}, default "Q"
        ``"Q"`` 분기 · ``"Y"`` 연간. Company 엔진의 `freq` 와 일치.

    Returns
    -------
    df : pl.DataFrame
        2664 종목 행 × 기간 컬럼들.

        - ``stockCode`` : str
        - 기간 컬럼들 : float — 비율 값 (%·배·일). 단위는 ``_RATIO_DEFS[ratioName]["label"]`` 참조.

    Examples
    --------
    **단일 비율 랭킹** — "ROE 최상위 30":

    >>> scanRatio("roe", freq="Y").sort("2025", descending=True).head(30)

    **"요즘 수익성 좋은 회사"** — 영업이익률 · ROE 둘 다 높은 교집합:

    >>> opm = scanRatio("operatingMargin", freq="Y").select(["stockCode", "2025"]).rename({"2025": "opm"})
    >>> roe = scanRatio("roe",             freq="Y").select(["stockCode", "2025"]).rename({"2025": "roe"})
    >>> opm.join(roe, on="stockCode").filter((pl.col("opm") >= 10) & (pl.col("roe") >= 15)).sort("roe", descending=True)

    **안정성 필터** — "부채비율 < 100% · 유동비율 > 150% · 영업이익률 > 15%":

    >>> dr  = scanRatio("debtRatio",       freq="Y").select(["stockCode", "2025"]).rename({"2025": "debt"})
    >>> cr  = scanRatio("currentRatio",    freq="Y").select(["stockCode", "2025"]).rename({"2025": "curr"})
    >>> opm = scanRatio("operatingMargin", freq="Y").select(["stockCode", "2025"]).rename({"2025": "opm"})
    >>> dr.join(cr, on="stockCode").join(opm, on="stockCode") \
    ...   .filter((pl.col("debt") < 100) & (pl.col("curr") > 150) & (pl.col("opm") > 15))

    **관점별 스크리닝** — "성장주"·"가치주":

    >>> # 성장주: 매출·영업이익·순이익 YoY 셋 다 상위
    >>> revG = scanRatio("revenueGrowth",        freq="Y")
    >>> opG  = scanRatio("operatingProfitGrowth", freq="Y")
    >>> netG = scanRatio("netProfitGrowth",       freq="Y")
    >>> # 가치주: scan("valuation") (PBR/PER) 하위 + ROE 상위 교집합

    **추이 반전** — "최근 4분기 영업이익률 턴어라운드":

    >>> df = scanRatio("operatingMargin", freq="Q")
    >>> df.filter(
    ...     (pl.col("2024Q4") < 0) & (pl.col("2025Q1") < 0)
    ...     & (pl.col("2025Q3") > 0) & (pl.col("2025Q4") > 0)
    ... )

    Notes
    -----
    - prebuild finance.parquet 기반. Python loop 없음. 2664 종목 한 번에 계산.
    - 부호 전환 (흑자 ↔ 적자) YoY 는 None 반환 (``yoy_pct`` 정책).
    - 섹터 평균 대비는 이 함수 + listing 의 섹터 컬럼 join 으로.
    - **지주사 · 금융업 · 라이센싱사 비정상치** — 지분법이익이 매출보다 큰 구조 (지주사) ·
      보험료/이자수익이 별도 영업수익으로 분류 (금융업) · 로열티가 영업이익으로만
      잡히는 구조 (라이센싱) 등은 ``operatingMargin`` · ``netMargin`` 이 100 % 초과
      비정상치로 raw 반환된다. **후보 표에 그대로 인용 금지** — ``listing()`` 의
      시장구분·업종으로 1차 필터, 또는 의심 종목은 ``c.show("IS")`` 로 매출·영업
      이익 구조 직접 확인. 실측 예 (2024 raw): 한솔케미칼 233.8 % · 파마리서치 379.0 % ·
      LG 161.3 % · 대성홀딩스 69.1 % — 모두 지주사·라이센싱 구조라 비교 무의미.

    Guide
    -----
    **⛔ 한 축만 돌리고 끝내지 말 것.** "투자할만한 회사 / 좋은 회사 / 요즘 투자하기
    좋은 / 성장세 좋은 / 배당 좋은" 같은 광역 발굴 질문은 단일 지표 (ROE 하나, 영업
    이익률 하나) 로 답할 수 없다. 아래 표에서 관점을 고르고, 해당 관점의 **모든 축**
    을 polars join 으로 교집합 해 후보를 좁힌 뒤 표로 출력하고 **종료** 한다. 사용자가
    특정 종목을 지목하지 않는 한 Company 엔진으로 넘어가지 않는다.

    **7 관점 스크리닝 레시피** — 질문에 맞는 관점을 1~2 개 선택해 모든 축 교집합.
    사용할 ratioName 은 현재 지원 13 종 (Parameters 참조) 범위 안에서만. 그 범위 밖
    신호 (CCC · interest coverage · accrual) 가 필요하면 ``pythonExec`` 에서 scanAccount
    조합으로 직접 계산 ::

        ┌─────────────────┬───────────────────────────────────────────────────────────────────────────────┐
        │ 관점            │ 축 조합 (모두 적용)                                                           │
        ├─────────────────┼───────────────────────────────────────────────────────────────────────────────┤
        │ 가치 (Value)    │ scan("valuation") 하위 (PBR/PER 낮음) + scanRatio("roe") 상위                │
        │ 성장 (Growth)   │ revenueGrowth & operatingProfitGrowth & netProfitGrowth 모두 상위             │
        │ 퀄리티(Quality) │ roe > 15 & operatingMargin > 10 & debtRatio < 100                             │
        │ 모멘텀          │ scanAccount("operating_profit", freq="Q") 최근 4Q QoQ 양수                │
        │ 배당 (Income)   │ scan("dividendTrend") 연속증가 + operatingCfMargin 안정                        │
        │ 턴어라운드      │ scanRatio("operatingMargin", freq="Q") 전전기 음수 → 최근 양수            │
        │ 안정(Defensive) │ debtRatio < 50 & currentRatio > 150 & equityRatio > 50                        │
        └─────────────────┴───────────────────────────────────────────────────────────────────────────────┘

    **"투자할만한 회사" 기본 레시피** (관점 지정 없을 때 = 퀄리티 + 안정 융합) ::

        opm = scanRatio("operatingMargin", freq="Y").select(["stockCode", "2025"]).rename({"2025": "opm"})
        roe = scanRatio("roe",             freq="Y").select(["stockCode", "2025"]).rename({"2025": "roe"})
        dbt = scanRatio("debtRatio",       freq="Y").select(["stockCode", "2025"]).rename({"2025": "dbt"})
        grw = scanRatio("revenueGrowth",   freq="Y").select(["stockCode", "2025"]).rename({"2025": "grw"})
        candidates = (
            opm.join(roe, on="stockCode")
               .join(dbt, on="stockCode")
               .join(grw, on="stockCode")
               .filter(
                   (pl.col("opm") >= 10) & (pl.col("roe") >= 12) &
                   (pl.col("dbt") <  100) & (pl.col("grw") >   0)
               )
               .sort("roe", descending=True)
               .head(20)
        )
        # → 20 개 후보 테이블 출력, 응답 종료. Company 호출 금지.

    **5 단계 발굴 워크플로** — AI 는 이 순서를 지킨다 ::

        1. macro("사이클") · macro("자산배분")  # 관점 선택의 근거 (회복 → 성장·모멘텀 / 스태그 → 안정·배당)
        2. 관점별 primitive 조합 스크린          # 위 표의 축을 모두 join · filter
        3. listing() join + 섹터·규모 편중 확인   # 한 업종 몰림은 업종 요인인지 시장 패턴인지 구분
        4. 후보 표 출력 → 응답 종료              # Company 호출 금지
        5. 사용자가 특정 종목 지목 → 그때만 Company(stockCode) 로 넘어감

    **질문 → primitive 매핑** ::

        =====================================  ====================================================================================
        사용자 질문                             scan 호출 조합
        =====================================  ====================================================================================
        "요즘 성장세 좋은 회사"                 revenueGrowth ∩ operatingProfitGrowth ∩ netProfitGrowth 상위
        "돈 잘 버는 회사"                       roe ∩ operatingMargin ∩ netMargin 상위 + debtRatio < 100
        "저평가인데 수익성 좋은 회사"           scan("valuation") 하위 (PBR/PER) ∩ scanRatio("roe") 상위
        "부채 적고 현금 많은 회사"              debtRatio < 50 ∩ currentRatio > 150 ∩ scanAccount("cash_and_cash_equivalents") 상위
        "턴어라운드 조짐"                       scanRatio("operatingMargin", freq="Q") 부호 반전 필터
        "업종 평균 뛰어넘는 곳"                 scanRatio 결과 + listing().select(sector) join → 섹터내 랭킹
        "최근 매출 늘었는데 이익 줄어든"        revenueGrowth > 0 ∩ operatingProfitGrowth < 0
        "자산 많은데 수익 못 내는"              scanAccount("total_assets") 상위 ∩ scanRatio("roa") 하위
        =====================================  ====================================================================================

    **복합 축 프리셋**: ``scan("profitability")`` 같은 프리셋은 이 함수 + ``scanAccount``
    의 자주 쓰는 조합. primitive 조합으로 직접 만들면 필터 자유도가 훨씬 높다.

    Verified
    --------
    아래는 2026-04-27 시점 ``finance.parquet`` 프리빌드로 직접 실행한 결과. ratioName
    조합 → 실제로 잡히는 종목 패턴 감각용 ::

        # 1. "투자할만한 회사" 기본 레시피 (퀄리티 + 안정 융합, 2024 baseline)
        #    operatingMargin >= 10 & roe >= 12 & debtRatio < 100 & revenueGrowth > 0
        #    → 후보 103 종목, 상위 5 (roe desc):
        #      257720 실리콘투 (opm 19.9 / roe 46.2 / dbt 75.0 / grw 101.7)
        #      018290 브이티   (opm 25.7 / roe 43.2 / dbt 49.4 / grw 46.1)
        #      326030 에스케이바이오팜 (opm 17.6 / roe 39.5 / dbt 80.6 / grw 94.0)
        #      123330 제닉     (opm 12.1 / roe 34.1 / dbt 72.2 / grw 77.8)
        #      278470 에이피알 (opm 17.0 / roe 33.3 / dbt 74.7 / grw 38.0)
        #    → 화장품·바이오·소비재 비중 높음 (섹터 편중 점검 필수, 5 단계 3 번)

        # 2. 분기 턴어라운드 (operatingMargin Q 부호 반전)
        #    2024Q3 < 0 & 2024Q4 < 0 & 2025Q2 > 0 & 2025Q3 > 0
        #    → 후보 79 종목, 상위 5 (2025Q3 desc):
        #      102940 코오롱생명과학 (24Q3 -37372 → 25Q3 +3989, 일회성 변동성 큼)
        #      006380 카프로         (24Q4 -889   → 25Q3 +85)
        #      052710 아모텍         (24Q4 -1637  → 25Q3 +81)
        #      127710 아시아경제     (24Q4 -97    → 25Q3 +45)
        #      230980 비유테크놀러지 (24Q3 -81    → 25Q3 +38)
        #    → opm 절대값 큰 종목은 매출 급변/일회성 의심, account 으로 검증

    한 분기 후 (사업보고서 추가 입수) 같은 레시피 재실행 시 후보가 바뀌는 정도로 본
    레시피의 시점 민감도를 가늠한다.

    See Also
    --------
    scanAccount : 단일 계정 시계열 (primitive 1/2)
    scanRatioList : 지원 비율 목록
    scan("profitability") · scan("quality") 등 : 프리셋 조합

    Raises
    ------
    ValueError
        지원하지 않는 ``ratioName`` 일 때 (사용 가능 목록 + hint 포함).

    Args:
        ratioName: <TODO: param desc> (str)
        fsPref: <TODO: param desc> (str)
        freq: <TODO: param desc> (str)

    Returns:
        <TODO: return desc> (pl.DataFrame)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - concurrent
        - dartlab
        - logging
        - polars

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>
    """
    if ratioName not in _RATIO_DEFS:
        available = ", ".join(sorted(_RATIO_DEFS))
        lower = ratioName.lower()
        hint = ""
        if lower in {"pbr", "per", "psr", "ev", "evEbitda".lower(), "ev_ebitda", "dividendyield", "dividend_yield"}:
            hint = (
                " — 시가총액 기반 밸류에이션 비율은 scanRatio 범위 밖이다. "
                "dartlab.scan('valuation') 을 사용하라 (네이버 시총 snapshot 경로)."
            )
        msg = f"지원하지 않는 비율: '{ratioName}'.{hint} 사용 가능: {available}"
        raise ValueError(msg)

    defn = _RATIO_DEFS[ratioName]

    if defn.get("yoy"):
        return _calcYoyRatio(defn, fsPref, freq=freq)
    return _calcSimpleRatio(defn, fsPref, freq=freq)


def scanRatioList() -> list[dict[str, str]]:
    """사용 가능한 scanRatio 비율 목록을 반환한다.

    Summary
    -------
    `scan("ratio")` 와 `scan("fields")` 가 공유하는 비율 카탈로그.

    Description
    -----------
    `_RATIO_DEFS` 를 단일 원천으로 사용해 비율 키, 표시명, 단위를 반환한다.
    새 비율을 추가할 때는 `_RATIO_DEFS` 에만 정의하면 목록·필드 카탈로그·AI
    tool description 이 같은 원천을 소비한다.

    Parameters
    ----------
    없음.

    Returns
    -------
    list[dict[str, str]]
        name : str — `scanRatio(ratioName=...)` 에 넣는 정규 비율 키 (단위 없음).
        label : str — 사용자 표시명 (단위 없음).
        unit : str — 비율 단위. `%` 또는 `배`.

    Raises
    ------
    없음.

    Examples
    --------
    >>> dartlab.scan("ratio")
    >>> dartlab.scan("fields", "roe")

    Notes
    -----
    PER/PBR/PSR 같은 시가총액 기반 밸류에이션은 이 목록이 아니라
    `scan("valuation")` 및 `scan("fields", source="valuation")` 에 있다.

    Guide
    -----
    When: AI 또는 사용자가 먼저 가용 비율을 확인할 때.
    How: `name` 을 `scan("ratio", name)` 또는 `finance.ratio.{name}` 필드로 사용한다.
    Verified: `scan("fields")` 의 finance ratio 행이 이 목록에서 생성된다.

    See Also
    --------
    scanRatio : 전종목 비율 시계열.
    scanFields : 조건형 스크리닝 필드 카탈로그.

    Returns:
        <TODO: return desc> (list[dict[str, str]])

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>
    """
    return [{"name": k, "label": v["label"], "unit": "%" if v.get("pct") else "배"} for k, v in _RATIO_DEFS.items()]


def scanAccountList() -> list[dict[str, str]]:
    """사용 가능한 scanAccount 계정 목록을 반환한다.

    Summary
    -------
    `sortOrder.json` 기준 재무제표 계정 카탈로그.

    Description
    -----------
    재무제표 계정의 단일 원천은 `sortOrder.json` 과 `AccountMapper` 이다.
    이 함수는 IS/BS/CF 계정 키와 한글 라벨을 반환하며, `scan("account")` 와
    `scan("fields")` 가 같은 목록을 소비한다.

    Parameters
    ----------
    없음.

    Returns
    -------
    list[dict[str, str]]
        name : str — `scanAccount(snakeId=...)` 에 넣는 정규 계정 키 (단위 없음).
        label : str — 한글 계정명 또는 snakeId fallback (단위 없음).
        statement : str — 재무제표 구분. `IS`, `BS`, `CF` 중 하나.

    Raises
    ------
    없음.

    Examples
    --------
    >>> dartlab.scan("account")
    >>> dartlab.scan("fields", "매출")

    Notes
    -----
    금액 단위는 원이다. 기간별 값은 `scanAccount` 가 wide DataFrame 으로 반환하고,
    조건형 screen 은 종목별 최신 기간 값을 비교한다.

    Guide
    -----
    When: 매출액·영업이익·자산·현금흐름 같은 원자 계정으로 후보를 찾을 때.
    How: `name` 을 `scan("account", name)` 또는 `finance.account.{name}` 필드로 사용한다.
    Verified: `scan("fields")` 의 finance account 행이 이 목록에서 생성된다.

    See Also
    --------
    scanAccount : 전종목 계정 시계열.
    scanFields : 조건형 스크리닝 필드 카탈로그.

    Returns:
        <TODO: return desc> (list[dict[str, str]])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - concurrent
        - dartlab
        - logging
        - polars

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>
    """
    from dartlab.core.utils.ordering import _ensureLoaded

    data = _ensureLoaded()

    # 한글명 역매핑: snakeId → 한글 항목
    mapper = AccountMapper.get()
    idToKr: dict[str, str] = {}
    if mapper._mappings:
        for krName, snakeId in mapper._mappings.items():
            if not krName.isascii() and snakeId not in idToKr:
                idToKr[snakeId] = krName

    result = []
    for sjDiv in ("IS", "BS", "CF"):
        for snakeId in data.get(sjDiv, {}):
            label = idToKr.get(snakeId, snakeId)
            result.append({"name": snakeId, "label": label, "statement": sjDiv})
    return result


def _calcSimpleRatio(defn: dict, fsPref: str, *, freq: str = "Q") -> pl.DataFrame:
    """분자/분모 비율 계산."""
    numer = scanAccount(defn["numer"], fsPref=fsPref, freq=freq)
    denom = scanAccount(defn["denom"], fsPref=fsPref, freq=freq)

    # 기간 컬럼만 추출
    numerYears = [c for c in numer.columns if c != "stockCode"]
    denomYears = [c for c in denom.columns if c != "stockCode"]
    commonYears = sorted(set(numerYears) & set(denomYears), reverse=True)

    if not commonYears:
        return pl.DataFrame({"stockCode": []})

    joined = numer.select(["stockCode"] + commonYears).join(
        denom.select(["stockCode"] + commonYears),
        on="stockCode",
        suffix="_d",
    )

    isPct = defn.get("pct", False)
    multiplier = 100.0 if isPct else 1.0

    resultExprs = [pl.col("stockCode")]
    for y in commonYears:
        expr = (
            pl.when((pl.col(f"{y}_d") != 0) & pl.col(f"{y}_d").is_not_null() & pl.col(y).is_not_null())
            .then((pl.col(y) / pl.col(f"{y}_d") * multiplier).round(2))
            .otherwise(pl.lit(None, dtype=pl.Float64))
            .alias(y)
        )
        resultExprs.append(expr)

    return joined.select(resultExprs)


def _calcYoyRatio(defn: dict, fsPref: str, *, freq: str = "Q") -> pl.DataFrame:
    """YoY 성장률 계산."""
    base = scanAccount(defn["base"], fsPref=fsPref, freq=freq)
    # base는 이미 최신 먼저 — YoY 계산은 오름차순 필요
    yearCols = sorted(c for c in base.columns if c != "stockCode")

    if len(yearCols) < 2:
        return pl.DataFrame({"stockCode": []})

    resultExprs = [pl.col("stockCode")]
    for i in range(1, len(yearCols)):
        cur = yearCols[i]
        prev = yearCols[i - 1]
        expr = (
            pl.when(
                (pl.col(prev) != 0) & pl.col(prev).is_not_null() & pl.col(cur).is_not_null() & (pl.col(prev).abs() > 0)
            )
            .then(((pl.col(cur) - pl.col(prev)) / pl.col(prev).abs() * 100).round(2))
            .otherwise(pl.lit(None, dtype=pl.Float64))
            .alias(cur)
        )
        resultExprs.append(expr)

    # 최신 먼저 역순으로 컬럼 재배치
    yoyCols = [yearCols[i] for i in range(1, len(yearCols))]
    return base.select(resultExprs).select(["stockCode"] + list(reversed(yoyCols)))
