"""quant 엔진 공용 헬퍼 — OHLCV fetch, market 감지, scan parquet 로드."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np
    import polars as pl

log = logging.getLogger(__name__)


from dartlab.core.polarsUtil import isEmptyDf

# ── 종목코드 컬럼 후보 SSOT ──────────────────────────────
# scan/quant 의 DataFrame universe 식별 컬럼 우선순위. 여러 모듈에서 같은 후보를
# 반복 정의하던 것 (scanBacktest._STOCK_CODE_CANDIDATES, _helpers.load_changes_for_stock 등)
# 의 단일 출처. 새 코드는 이걸 import.
STOCK_CODE_COLUMNS: tuple[str, ...] = ("stockCode", "종목코드", "stock_code", "corp_code")


# ── OHLCV fetch ──────────────────────────────────────────


def fetchOhlcv(stockCode: str, **kwargs: Any) -> "pl.DataFrame | None":
    """gather("price")로 OHLCV 수집 — 실패 시 None.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: "005930", "AAPL").
    **kwargs
        GatherEntry 전달 인자 (start, market 등).

    Returns
    -------
    pl.DataFrame | None
        date : date — 거래일
        open : float — 시가 (원)
        high : float — 고가 (원)
        low : float — 저가 (원)
        close : float — 종가 (원)
        volume : int — 거래량 (주)
        수집 실패 시 None.

    Requires:
        L1 gather provider (KR KRX 또는 US Yahoo Finance) 활성.

    Raises:
        없음 — 모든 실패는 None 반환 + warning 로그.
    """
    try:
        from dartlab.gather.entry import GatherEntry

        g = GatherEntry()
        return g("price", stockCode, **kwargs)
    except (ImportError, ValueError, TypeError, RuntimeError):
        log.warning("OHLCV fetch 실패: %s", stockCode)
        return None


def fetchBenchmark(market: str = "KR", **kwargs: Any) -> "pl.DataFrame | None":
    """벤치마크 OHLCV 수집 — KR=KRX 지수, US=S&P500.

    Parameters
    ----------
    market : str
        "KR" / "KOSPI" / "KOSDAQ" 또는 "US".
    **kwargs
        ``stockCode``, ``benchmark``, ``start``, ``end`` 등.

    Returns
    -------
    pl.DataFrame | None
        date : date — 거래일
        open : float — 시가
        high : float — 고가
        low : float — 저가
        close : float — 종가
        volume : int — 거래량
        수집 실패 시 None.

    Example:
        >>> df = fetchBenchmark("KR")
        >>> df.columns
        ['date', 'open', 'high', 'low', 'close', 'volume']

    Requires:
        gather provider 활성 + 벤치마크 시리즈 등록.

    Raises:
        없음 — 실패는 None.
    """
    try:
        from dartlab.quant.benchmark.data import fetchBenchmarkOhlcv

        stockCode = kwargs.pop("stockCode", None)
        benchmark = kwargs.pop("benchmark", None)
        benchmarkMode = kwargs.pop("benchmarkMode", "market")
        return fetchBenchmarkOhlcv(
            stockCode,
            market=market,
            benchmark=benchmark,
            benchmarkMode=benchmarkMode,
            **kwargs,
        )
    except (ImportError, ValueError, TypeError, RuntimeError):
        log.warning("벤치마크 fetch 실패: %s", market)
        return None


# ── scan parquet 로드 (메모리 안전) ──────────────────────


def _scanDataRoot() -> Path:
    """data/ 루트 경로."""
    from dartlab.core.dataLoader import _getDataRoot

    return Path(_getDataRoot())


def loadScanParquet(name: str, market: str = "KR") -> "pl.LazyFrame | None":
    """scan 프리빌드 parquet lazy scan 로드.

    Capabilities:
        - dart/scan 또는 edgar/scan 하위 parquet 을 polars LazyFrame 으로 로드
        - report/ 하위 fallback 자동 시도 (finance/changes 외 보조 파일)

    Args:
        name: ``"finance"``, ``"changes"`` 또는 report/ 하위 이름.
        market: ``"KR"`` | ``"US"``.

    Returns:
        pl.LazyFrame | None — 파일 미존재 시 None.

    Guide:
        Quant screen·signal 모듈의 표준 데이터 진입점. lazy scan 으로 메모리 절약 (Polars
        OOM 방지). collect 는 호출자 책임.

    When:
        Quant 횡단면 스크리닝 + 시계열 분석 진입.

    How:
        ``_scanDataRoot`` → market 별 base 경로 → ``name.parquet`` 또는 ``report/name.parquet``.

    Requires:
        ``data/{dart|edgar}/scan/`` 디렉토리 + 대상 parquet 존재.

    Raises:
        없음 — 파일 부재 시 warning 로그 + None.

    Example:
        >>> lf = loadScanParquet("finance", market="KR")
        >>> lf.collect_schema().names()[:3]
        ['stockCode', 'fy', 'sales']

    See Also:
        - loadSharesOutstanding : 발행주식수 LazyFrame
        - loadAllfilingsForStock : 종목별 allFilings
        - fetchOhlcv : OHLCV 시계열

    AIContext:
        Quant cross-sectional 답변 시 finance/changes parquet 로드 → percentile/factor 계산.
    """
    import polars as pl

    root = _scanDataRoot()
    if market == "KR":
        base = root / "dart" / "scan"
    else:
        base = root / "edgar" / "scan"

    # finance.parquet 또는 report/ 하위
    path = base / f"{name}.parquet"
    if not path.exists():
        path = base / "report" / f"{name}.parquet"
    if not path.exists():
        log.warning("scan parquet 없음: %s", path)
        return None

    return pl.scan_parquet(path)


def loadSharesOutstanding(market: str = "KR") -> "pl.DataFrame | None":
    """발행주식수 프리빌드 LazyFrame 로드.

    Capabilities:
        - KR: ``data/dart/scan/sharesOutstanding.parquet`` (보통주/우선주 분리)
        - US: ``data/edgar/scan/sharesOutstanding.parquet`` (XBRL dei)
        - scan 카테고리이므로 ``_ensureScanData()`` 가 자동으로 HF 에서 받아온다

    Args:
        market: ``"KR"`` 또는 ``"US"``.

    Returns:
        pl.LazyFrame | None — 파일 부재 시 None.

    Guide:
        Quant valuation factor (PER/PBR) 의 시가총액 계산 필수 입력. finance.parquet 과
        ``stockCode + period_end`` 키로 join.

    When:
        Market cap 기반 factor 계산 + AI 시총 인용 답변.

    How:
        KR: ``_ensureScanData`` → ``sharesOutstanding.parquet``. US: ``_scanDataRoot`` 직접.

    Requires:
        scan parquet 디렉토리 존재 + HF 데이터셋 다운로드 완료.

    Raises:
        없음 — 파일 부재 시 warning + None.

    Example:
        >>> lf = loadSharesOutstanding("KR")
        >>> lf.collect_schema().names()
        ['stockCode', 'period_end', 'common', 'preferred']

    See Also:
        - loadScanParquet : 일반 scan parquet
        - dartlab.scan.io.parquet : HF 동기화

    AIContext:
        시총·PER/PBR 답변 시 발행주식수 × 종가 인용.
    """
    import polars as pl

    if market == "KR":
        import importlib

        _ensureScanData = importlib.import_module("dartlab.scan.io.parquet")._ensureScanData

        scanDir = _ensureScanData()
        path = scanDir / "sharesOutstanding.parquet"
    else:
        root = _scanDataRoot()
        path = root / "edgar" / "scan" / "sharesOutstanding.parquet"

    if not path.exists():
        log.warning("sharesOutstanding parquet 없음: %s", path)
        return None
    return pl.scan_parquet(path)


def loadDocsForStock(stockCode: str) -> "pl.DataFrame | None":
    """단일 종목 docs parquet 로드.

    Capabilities:
        - ``data/dart/docs/{stockCode}.parquet`` eager read
        - 종목별 사업보고서 본문 텍스트 (텍스트 alpha 입력)

    Args:
        stockCode: 6 자리 종목코드.

    Returns:
        pl.DataFrame | None — 파일 부재 시 None.

    Guide:
        Quant text alpha (sentiment/toneChange/riskText/governance) 의 본문 입력. 종목별
        한 파일.

    When:
        Text factor 계산 + AI 공시 본문 기반 답변.

    How:
        ``_scanDataRoot`` → ``dart/docs/{stockCode}.parquet`` → ``pl.read_parquet``.

    Requires:
        ``data/dart/docs/{stockCode}.parquet`` 존재.

    Raises:
        없음 — 부재 시 warning + None.

    Example:
        >>> df = loadDocsForStock("005930")
        >>> df["section"].unique().to_list()[:3]
        ['business', 'risk', 'mdAndA']

    See Also:
        - loadChangesForStock : 변경사항 시계열
        - calcSentiment : 본문 sentiment 추출

    AIContext:
        본문 인용 답변 시 section 별 텍스트 → sentiment/risk 점수 인용.
    """
    import polars as pl

    root = _scanDataRoot()
    path = root / "dart" / "docs" / f"{stockCode}.parquet"
    if not path.exists():
        log.warning("docs parquet 없음: %s", path)
        return None

    return pl.read_parquet(path)


def loadChangesForStock(stockCode: str) -> "pl.DataFrame | None":
    """changes.parquet에서 단일 종목 필터링.

    Capabilities:
        - ``dart/scan/changes.parquet`` 에서 stockCode 컬럼 자동 탐색 → 단일 종목 추출
        - STOCK_CODE_COLUMNS SSOT 후보 순회

    Args:
        stockCode: 6 자리 종목코드.

    Returns:
        pl.DataFrame | None — 컬럼 모두 매칭 실패 시 None.

    Guide:
        changes.parquet 의 컬럼명 변동성 (snake_case ↔ camelCase ↔ 한글) 대응.
        streaming engine 으로 메모리 안전.

    When:
        종목별 시계열 변동 분석 + AI quarterly change 답변.

    How:
        STOCK_CODE_COLUMNS 후보 순회 → 첫 매칭 컬럼에 ``filter`` → ``collect(streaming)``.

    Requires:
        ``data/dart/scan/changes.parquet`` 존재 + STOCK_CODE_COLUMNS 중 하나 컬럼 존재.

    Raises:
        없음 — 매칭 실패 시 None.

    Example:
        >>> df = loadChangesForStock("005930")
        >>> df.shape[0]
        24

    See Also:
        - loadScanParquet : 일반 scan 진입
        - STOCK_CODE_COLUMNS : 컬럼 후보 SSOT

    AIContext:
        분기 변화 답변 시 columnPos 별 ``change_pct`` 인용.
    """
    import polars as pl

    root = _scanDataRoot()
    path = root / "dart" / "scan" / "changes.parquet"
    if not path.exists():
        return None

    lf = pl.scan_parquet(path)
    for col in STOCK_CODE_COLUMNS:
        try:
            return lf.filter(pl.col(col) == stockCode).collect(engine="streaming")
        except pl.exceptions.ColumnNotFoundError:
            continue
    return None


# ── scan parquet에서 종목 백분위 계산 ────────────────────


def stockPercentile(lf, stockCode: str, col: str, stockCol: str = "stockCode", reverse: bool = False) -> float | None:
    """scan lazy frame에서 특정 종목의 컬럼 백분위를 계산.

    Args:
        lf: pl.LazyFrame (scan parquet)
        stockCode: 종목코드
        col: 백분위를 구할 컬럼명
        stockCol: 종목코드 컬럼명
        reverse: True이면 높은 값 = 낮은 백분위 (PBR 등)

    Returns:
        (value, percentile) 또는 (None, None)

    Example:
        >>> stockPercentile(lf, "005930", "roe")
        (0.18, 0.85)

    Requires:
        lf 가 polars LazyFrame + col 존재.

    Raises:
        없음 — 컬럼 누락 시 (None, None).
    """
    import polars as pl

    try:
        # 종목코드 컬럼 자동 탐색
        schema_names = lf.collect_schema().names()
        actual_stock_col = None
        for c in (stockCol, "종목코드", "stockCode", "corp_code"):
            if c in schema_names:
                actual_stock_col = c
                break
        if actual_stock_col is None or col not in schema_names:
            return None, None

        # 이 종목의 값
        row = lf.filter(pl.col(actual_stock_col) == stockCode).select(col).collect(engine="streaming")
        if len(row) == 0 or row.item() is None:
            return None, None

        val = float(row.item())

        # 전체 분포에서 백분위
        all_vals = lf.select(col).drop_nulls().collect(engine="streaming").to_series()
        if len(all_vals) == 0:
            return val, None

        if reverse:
            pct = float((all_vals > val).sum() / len(all_vals))
        else:
            pct = float((all_vals < val).sum() / len(all_vals))

        return val, round(pct, 4)
    except (KeyError, ValueError, TypeError):
        return None, None


def loadAllfilingsForStock(stockCode: str, *, lookback: int | None = None) -> "pl.DataFrame | None":
    """allFilings parquet 에서 단일 종목 데이터 로드.

    `data/dart/allFilings/*.parquet` 일자별 전종목 파일에서 stock_code 로 필터.
    polars lazy scan + filter pushdown 으로 메모리 안전 (전체 스캔 가능).

    [Phase 4 R3 fix]
    - 이전: `parquets[-60:]` 슬라이싱으로 60일 한정 → eventDriven 5년 백테스트 막힘
    - 정정: 전체 일자 lazy scan, 컬럼 매칭 `stock_code` (snake_case) 우선
    - lookback_days 명시 시만 최근 N일로 제한 (호출자 책임)

    Capabilities:
        - 일자별 allFilings parquet 전체 lazy scan + stock_code 매칭 컬럼 자동 탐색
        - lookback 명시 시 최근 N 일 슬라이싱, ``diagonal_relaxed`` concat 으로 스키마 변동 흡수

    Args:
        stockCode: 6 자리 종목코드 (예: ``"005930"``).
        lookback: ``None`` = 전체, 숫자 = 최근 N 일.

    Returns:
        pl.DataFrame | None — 매칭 0 건 시 None.

    Guide:
        eventDriven 백테스트의 표준 입력. ``lookback`` 미지정 = 전체 5+ 년 스캔 가능
        (streaming engine 이라 메모리 안전).

    When:
        Event study + AI 공시 시계열 답변.

    How:
        ``allFilings/*.parquet`` glob → ``_meta`` 제외 → lookback 슬라이싱 → 컬럼 매칭 후
        per-file filter + concat.

    Requires:
        ``data/dart/allFilings/`` 존재 + parquet 파일 ≥ 1 개.

    Raises:
        없음 — OSError/ComputeError 는 per-file skip.

    Example:
        >>> df = loadAllfilingsForStock("005930", lookback=252)
        >>> df.shape[0]
        18

    See Also:
        - loadChangesForStock : changes.parquet 단일 종목
        - calcCAR : event study CAR

    AIContext:
        공시 이력 시계열 답변 시 ``filing_date + filing_type`` 인용.
    """
    import polars as pl

    root = _scanDataRoot()
    adir = root / "dart" / "allFilings"
    if not adir.exists():
        return None

    parquets = sorted(adir.glob("*.parquet"))
    parquets = [p for p in parquets if "_meta" not in p.name]
    if not parquets:
        return None

    if lookback is not None and lookback > 0:
        parquets = parquets[-lookback:]

    # 컬럼명 우선순위: STOCK_CODE_COLUMNS SSOT (snake_case 우선이라 별도 순서 — 그러나
    # SSOT 의 후보 셋과 동일). allFilings parquet 은 stock_code 가 일반적이라 첫 시도.
    candidate_cols = ("stock_code", *(c for c in STOCK_CODE_COLUMNS if c != "stock_code"))

    frames: list = []
    for p in parquets:
        try:
            lf = pl.scan_parquet(p)
            schema = lf.collect_schema().names()
            matched_col = next((c for c in candidate_cols if c in schema), None)
            if matched_col is None:
                continue
            filtered = lf.filter(pl.col(matched_col) == stockCode).collect(engine="streaming")
            if len(filtered) > 0:
                frames.append(filtered)
        except (OSError, pl.exceptions.ComputeError):
            continue

    if not frames:
        return None
    return pl.concat(frames, how="diagonal_relaxed")


# ── OHLCV → numpy 변환 ──────────────────────────────────


# ── 강건한 계정 추출 (DART finance.parquet) ──────────────


# 표준 키 → DART account_nm 정규식 패턴 (우선순위 순서, 첫 매치 사용)
_ACCOUNT_PATTERNS: dict[str, list[str]] = {
    "sales": [
        r"^매출액$",
        r"^수익\(매출액\)$",
        r"^수익$",
        r"^영업수익$",
        r"^매출$",
        r"매출액",
    ],
    "operating_profit": [
        r"^영업이익$",
        r"^영업이익\(손실\)$",
        r"^영업손익$",
        r"영업이익",
    ],
    "net_income": [
        r"^당기순이익$",
        r"^당기순이익\(손실\)$",
        r"^당기순손익$",
        r"^연결당기순이익$",
        r"^지배기업소유주지분순이익$",
        r"^지배기업의?\s*소유주에?\s*귀속되는?\s*당기순이익$",
        r"당기순이익",
    ],
    "total_assets": [r"^자산총계$"],
    "total_liabilities": [r"^부채총계$"],
    "total_equity": [
        r"^자본총계$",
        r"^지배기업소유주지분$",
    ],
    "operating_cf": [
        r"^영업활동현금흐름$",
        r"^영업활동으로?\s*인한?\s*현금흐름$",
        r"영업활동.*현금흐름",
    ],
    "investing_cf": [
        r"^투자활동현금흐름$",
        r"투자활동.*현금흐름",
    ],
    "financing_cf": [
        r"^재무활동현금흐름$",
        r"재무활동.*현금흐름",
    ],
    "current_assets": [r"^유동자산$", r"유동자산"],
    "current_liabilities": [r"^유동부채$", r"유동부채"],
    "retained_earnings": [
        r"^이익잉여금$",
        r"^이익잉여금\(결손금\)$",
        r"이익잉여금",
    ],
    "gross_profit": [r"^매출총이익$", r"^매출총손익$", r"매출총이익"],
    "cost_of_sales": [r"^매출원가$", r"매출원가"],
    "inventory": [r"^재고자산$", r"재고자산"],
    "accounts_receivable": [
        r"^매출채권$",
        r"^매출채권\s*및?\s*기타채권$",
        r"매출채권",
    ],
    "depreciation": [
        r"^감가상각비$",
        r"감가상각비",
        r"^감가상각및?\s*무형자산상각비$",
    ],
    "selling_admin": [
        r"^판매비와?\s*관리비$",
        r"^판매관리비$",
        r"판매비.*관리비",
    ],
}

# 표준 키 → 후보 sj_div 리스트
# IS = 별개 손익계산서, CIS = 포괄손익계산서 단일 양식. 일부 기업(SK하이닉스 등)은 CIS만 사용.
_ACCOUNT_SJ: dict[str, list[str]] = {
    "sales": ["IS", "CIS"],
    "operating_profit": ["IS", "CIS"],
    "net_income": ["IS", "CIS"],
    "total_assets": ["BS"],
    "total_liabilities": ["BS"],
    "total_equity": ["BS"],
    "operating_cf": ["CF"],
    "investing_cf": ["CF"],
    "financing_cf": ["CF"],
    "current_assets": ["BS"],
    "current_liabilities": ["BS"],
    "retained_earnings": ["BS"],
    "gross_profit": ["IS", "CIS"],
    "cost_of_sales": ["IS", "CIS"],
    "inventory": ["BS"],
    "accounts_receivable": ["BS"],
    "depreciation": ["IS", "CIS", "CF"],
    "selling_admin": ["IS", "CIS"],
}


def extractAccount(df, key: str) -> float | None:
    """단일 종목/단일 기간 DataFrame에서 표준 계정 추출 — DART/EDGAR 자동 분기.

    Capabilities:
        - DART finance.parquet: ``_ACCOUNT_PATTERNS`` 정규식 + ``_ACCOUNT_SJ`` sj_div 순회 매칭
        - EDGAR: ``ACCOUNT_MAP`` 직접 컬럼 + net_profit/total_stockholders_equity 별칭 처리
        - ``parseNumStr`` 로 thstrm_amount 문자열 → float 안전 변환

    Args:
        df: pl.DataFrame — DART (sj_div/account_nm/thstrm_amount) 또는 EDGAR (직접 컬럼).
        key: 표준 키 (``"sales"``, ``"operating_profit"``, ``"net_income"``, ``"total_assets"`` ...).

    Returns:
        float | None — DART 는 패턴 매칭, EDGAR 는 직접 컬럼. 매칭 실패 시 None.

    Guide:
        Quant factor (PER/ROE) 의 계정 정규화 SSOT. 새 계정 추가 시 ``_ACCOUNT_PATTERNS`` +
        ``_ACCOUNT_SJ`` 에 함께 등록.

    When:
        Cross-sectional factor 계산 + AI 회계 항목 답변.

    How:
        EDGAR 분기: fy 컬럼 존재 + sj_div 부재 판정 → ACCOUNT_MAP. DART 분기: sj_div × 패턴
        순회 → 첫 매칭.

    Requires:
        DART: sj_div/account_nm/thstrm_amount 컬럼. EDGAR: ``synth.scanBridge.ACCOUNT_MAP``.

    Raises:
        없음 — ComputeError/ValueError/TypeError 는 skip + None.

    Example:
        >>> extractAccount(df, "sales")
        279600000000.0

    See Also:
        - extractAccounts : 여러 키 일괄
        - _ACCOUNT_PATTERNS : 정규식 SSOT
        - synth.scanBridge.ACCOUNT_MAP : EDGAR 매핑

    AIContext:
        AI 가 "매출/영업이익" 류 질문 답변 시 본 함수로 단일 값 추출 → factor 계산 전 정규화.
    """
    import polars as pl

    if isEmptyDf(df):
        return None

    # EDGAR 스키마 — fy 컬럼 + sj_div 없음 → 직접 컬럼 read
    if "fy" in df.columns and "sj_div" not in df.columns:
        from dartlab.synth.scanBridge import ACCOUNT_MAP

        # key 가 EDGAR snake_case 면 그대로, 한글이면 매핑
        col = ACCOUNT_MAP.get(key, key)
        # net_income 별칭 처리 (EDGAR 컬럼명은 net_profit)
        if col == "net_income" and "net_profit" in df.columns:
            col = "net_profit"
        if col == "total_equity" and "total_stockholders_equity" in df.columns:
            col = "total_stockholders_equity"
        if col not in df.columns:
            return None
        try:
            v = df[col][0]
            return float(v) if v is not None else None
        except (ValueError, TypeError, IndexError):
            return None

    patterns = _ACCOUNT_PATTERNS.get(key)
    sj_list = _ACCOUNT_SJ.get(key)
    if patterns is None or sj_list is None:
        return None

    for sj in sj_list:
        base = df.filter(pl.col("sj_div") == sj)
        if base.is_empty():
            continue
        for pat in patterns:
            try:
                rows = base.filter(pl.col("account_nm").str.contains(pat))
            except (pl.exceptions.ComputeError, AttributeError):
                continue
            if len(rows) == 0:
                continue
            amounts = rows.get_column("thstrm_amount").to_list()
            from dartlab.core.utils.helpers import parseNumStr

            for amt in amounts:
                v = parseNumStr(amt) if not isinstance(amt, (int, float)) else float(amt)
                if v is not None:
                    return v
    return None


def extractAccounts(df, keys: list[str]) -> dict[str, float | None]:
    """여러 표준 계정 일괄 추출 — DART finance.parquet 용.

    Parameters
    ----------
    df : pl.DataFrame
        DART finance.parquet 의 단일 종목/단일 기간 DataFrame.
        sj_div, account_nm, thstrm_amount 컬럼 보유.
    keys : list[str]
        표준 계정 키 리스트
        ("sales", "operating_profit", "net_income", "total_assets",
         "total_liabilities", "total_equity", "operating_cf",
         "investing_cf", "financing_cf").

    Returns
    -------
    dict[str, float | None]
        키별 금액 (원). 매칭 실패 시 해당 키 = None.

    Examples
    --------
    >>> extractAccounts(df, ["sales", "net_income"])

    Requires:
        df 의 sj_div / account_nm / thstrm_amount 컬럼 존재.

    Raises:
        없음 — 매칭 실패는 None 값.
    """
    return {k: extractAccount(df, k) for k in keys}


def ohlcvToArrays(df) -> dict:
    """Polars OHLCV DataFrame → numpy 배열 dict.

    Capabilities:
        - open/high/low/close/volume 컬럼을 float64 numpy 변환
        - date 컬럼은 list 로 보존 (날짜 객체 형식 유지)

    Args:
        df: pl.DataFrame — OHLCV (date/open/high/low/close/volume).

    Returns:
        dict — keys ``open/high/low/close/volume/date``. 빈 df 시 ``{}``.

    Guide:
        Quant signal/regime 모듈 (technical indicators, chartPatterns) 의 표준 입력 변환.

    When:
        Numpy 기반 indicator 계산 + AI technical 답변.

    How:
        ``isEmptyDf`` skip → 각 컬럼 ``to_numpy().astype(np.float64)``.

    Requires:
        df 가 polars DataFrame.

    Raises:
        없음 — 누락 컬럼 자동 skip.

    Example:
        >>> arr = ohlcvToArrays(df)
        >>> arr["close"].shape
        (252,)

    See Also:
        - fetchOhlcv : 원본 DataFrame 소스
        - detectChartPatterns : numpy 소비자

    AIContext:
        Technical signal 계산 직전 변환. AI quant axis 답변 체인의 표준 단계.
    """
    import numpy as np

    if isEmptyDf(df):
        return {}

    result = {}
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            result[col] = df.get_column(col).to_numpy().astype(np.float64)

    if "date" in df.columns:
        result["date"] = df.get_column("date").to_list()

    return result


# ── Strategy DSL 공용 헬퍼 (Phase B) ──────────────────────────────────────────


def tomMask(dates) -> "Any":
    """Turn-of-the-Month boolean mask — KR 캘린더 시즌신호.

    KOSDAQ 에서 학술 검증된 월말 3거래일 + 월초 3거래일 효과를 boolean 시계열로 반환.
    학술 근거: Lakonishok-Smidt 1988, Korean Journal of Finance (KOSDAQ TOM, 2018+).

    seasonalKR 스타일 외에 다른 곳에서 만들지 말 것 (SSOT).

    Capabilities:
        - 일자 시퀀스 → ``day ≤ 3 or day ≥ 25`` boolean ndarray
        - TOM 효과 (월말·월초 abnormal return) 진입 마스크

    Args:
        dates: ``list[date]`` 또는 polars Date Series — OHLCV 의 date 컬럼.

    Returns:
        numpy.ndarray[bool] — 길이 N. 월말 3 일 / 월초 3 일 True.

    Guide:
        seasonalKR 스타일의 진입 게이트. 다른 위치에서 재구현 금지 (SSOT).

    When:
        시즌 alpha + AI calendar effect 답변.

    How:
        list comprehension ``d.day ≤ 3 or d.day ≥ 25`` → np.bool_ array.

    Requires:
        dates 의 각 원소가 ``.day`` 속성 보유 (date/datetime).

    Raises:
        없음 — 빈 입력 시 빈 array.

    Example:
        >>> from datetime import date
        >>> tomMask([date(2026, 1, 1), date(2026, 1, 15), date(2026, 1, 28)])
        array([ True, False,  True])

    See Also:
        - strategy.styles.seasonalKR : 본 mask 의 유일 호출자
        - extractSignalSeries : 호환 signal wrapper

    AIContext:
        시즌 alpha 답변 시 TOM 효과 활성 일자 인용.
    """
    import numpy as np

    days = [d.day for d in dates]
    return np.array([(d <= 3 or d >= 25) for d in days], dtype=np.bool_)


def extractSignalSeries(arr: dict, fn, *, key: str | None = None, **kwargs) -> "np.ndarray | None":
    """벡터 신호 함수를 OHLCV 배열에 적용해 시계열 반환 (SSOT).

    Strategy DSL 이 dict-only analyze_xxx 함수의 시계열 분기 안에서 호출하는 단일
    공용 헬퍼. 다른 위치에 비슷한 wrapper 만들지 말 것.

    Capabilities:
        - inspect 로 ``fn`` 의 시그니처 자동 분석 + arr/kwargs 에서 대응 입력 매칭
        - 결과를 ``{key or fn.__name__: NDArray}`` 단일 컬럼 dict 로 정규화

    Args:
        arr: ``ohlcvToArrays`` 결과 dict (close/high/low/volume/date).
        fn: ``signals.py`` / ``indicators.py`` 의 v* 함수 (시그니처 자동 감지).
        key: 결과 컬럼 명. None 이면 ``fn.__name__``.
        **kwargs: fn 에 전달할 추가 인자.

    Returns:
        dict ``{key: NDArray}`` — 길이 보존.

    Guide:
        Strategy DSL 의 v*-함수 시계열 분기 단일 SSOT. 다른 위치에 비슷한 wrapper 금지.

    When:
        Strategy DSL 의 시계열 신호 합성 + AI 백테스트 답변.

    How:
        ``inspect.signature(fn).parameters`` 순회 → arr[param] 또는 kwargs[param] 매칭
        → 나머지 kwargs 전달.

    Requires:
        arr 에 close 컬럼 + fn 이 callable + 시그니처 readable.

    Raises:
        없음 — close 부재 또는 빈 arr 시 ``{}``.

    Example:
        >>> def vsma(close, n=20): ...
        >>> out = extractSignalSeries(arr, vsma, n=50)
        >>> out["vsma"].shape
        (252,)

    See Also:
        - strategy.signal : 신호 함수 모음
        - ohlcvToArrays : arr 생성

    AIContext:
        DSL 답변 시 v*-함수 결과 시계열 인용 → 백테스트 시뮬레이션 체인.
    """
    import inspect

    if not arr or "close" not in arr:
        return {}
    sig_params = list(inspect.signature(fn).parameters.keys())
    inputs = []
    for p in sig_params:
        if p in arr:
            inputs.append(arr[p])
        elif p in kwargs:
            inputs.append(kwargs.pop(p))
        else:
            break  # 나머지는 kwargs 로 전달
    out = fn(*inputs, **kwargs)
    return {key or fn.__name__: out}


# ── Deprecated snake_case aliases ────────────────────────
# canonical 은 camelCase. snake_case 호출자는 0.10 이후 제거 예정 (operation.code.md
# "snake_case shim 유지" 룰). DeprecationWarning 발생.

# 0.10 BC 깸 — 옛 snake_case alias (fetch_ohlcv 등 12 개) 삭제.
# 새 이름 (fetchOhlcv · loadScanParquet · ohlcvToArrays 등) 만 SSOT.
