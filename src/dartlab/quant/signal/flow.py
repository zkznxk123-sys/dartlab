"""수급 분석 — 기관/외국인 매매 분석 (KR전용).

gather("flow") 데이터를 퀀트 신호로 변환.
"""

from __future__ import annotations

import logging

import numpy as np

from dartlab.core.market import resolveMarket

log = logging.getLogger(__name__)


def calcFlow(stockCode: str, *, market: str = "auto", series: bool = False, **kwargs) -> dict:
    """기관/외국인 수급 분석 — KR 전용 (KRX 투자자별 거래).

    Capabilities:
        외국인/기관/개인 일별 순매수 + 5d/20d 누적 + flowMomentum (최근 5d /
        20d 비율) + streak (연속 매수/매도 일수) 산출. KRX 가 공시하는
        투자자별 거래대금 기반. US 는 별도 데이터 (13F 분기) 라 본 함수 미지원.

    Args:
        stockCode: 종목코드 (KR 6 자리 전용).
        market: "KR" 만 정상 처리, 그 외는 error.
        series: True 면 ``_series`` 추가 (foreign_cum5, foreign_cum20,
            inst_cum5, inst_cum20).

    Returns:
        dict:
            - ``foreignNetBuy``/``instNetBuy``/``individualNetBuy`` (dict):
              일별/5d/20d/streak.
            - ``flowMomentum`` (float): 최근 5d vs 20d 비율.
            - 또는 ``error`` (str): KR 외 또는 수급 데이터 부재.

    Raises:
        없음 (error 키).

    Example:
        >>> r = calcFlow("005930")
        >>> r["foreignNetBuy"]["streak"]
        5  # 외국인 5 일 연속 순매수

    Guide:
        - 외국인 + 기관 동시 순매수 + streak ≥ 3 = 강한 매수 시그널.
        - 외국인↑ vs 기관↓ 분기 = 의견 분기 (단기 변동성 큼).
        - 누적 20d 절대값 + 시가총액 대비 비율 함께 인용 (절대값만 보면
          대형주 편향).

    SeeAlso:
        - ``calcVolume``: 거래량 (수급 = 거래 주체별 분해)
        - ``calcMomentum``: 가격 모멘텀
        - ``calcEventSignal``: 공시 이벤트와 결합

    Requires:
        gather("flow") 데이터 — KR 만 가능.

    AIContext:
        외국인 / 기관 분리 인용. 단일 day 액수 단독 인용 금지 — 5d/20d 누적
        + streak 함께. US 종목에 본 함수 호출 시 error 즉시 반환.

    LLM Specifications:
        AntiPatterns:
            - US 종목에 본 함수 호출 — error.
            - 1 일 순매수만 인용 — 5d/20d 누적 + streak 함께 필수.
        OutputSchema:
            ``{foreignNetBuy: dict, instNetBuy: dict, individualNetBuy: dict,
              flowMomentum: float}`` 또는 ``{..., error: str}``.
        Prerequisites:
            gather("flow") 데이터 (KR 전용).
        Freshness:
            일별 (KRX 마감 후).
        Dataflow:
            gather flow → 일별 순매수 → 5d/20d 누적 → flowMomentum → streak.
        TargetMarkets: KR (KRX), US 미지원.
    """
    market = resolveMarket(stockCode, market)

    if market != "KR":
        result_us: dict = {
            "stockCode": stockCode,
            "market": market,
            "error": "수급 데이터는 KR(한국) 시장만 지원합니다.",
        }
        if series:
            result_us["_series"] = None
        return result_us

    # gather("flow") 로드
    flow_data = _fetchFlow(stockCode)
    if flow_data is None:
        return {"stockCode": stockCode, "market": market, "error": "수급 데이터 없음"}

    result: dict = {
        "stockCode": stockCode,
        "market": market,
    }

    try:
        import polars as pl

        if isinstance(flow_data, pl.DataFrame) and not flow_data.is_empty():
            cols = flow_data.columns
            n = len(flow_data)
            result["dataPoints"] = n

            # 외국인 순매수
            foreign_col = _findCol(cols, ["외국인", "foreign", "foreignNet"])
            if foreign_col:
                foreign = flow_data.get_column(foreign_col).to_numpy().astype(np.float64)
                foreign = np.nan_to_num(foreign, nan=0.0)
                result["foreignNetBuy"] = _analyzeInvestor(foreign, "외국인")

            # 기관 순매수
            inst_col = _findCol(cols, ["기관", "institution", "instNet", "기관계"])
            if inst_col:
                inst = flow_data.get_column(inst_col).to_numpy().astype(np.float64)
                inst = np.nan_to_num(inst, nan=0.0)
                result["instNetBuy"] = _analyzeInvestor(inst, "기관")

            # 개인 순매수
            retail_col = _findCol(cols, ["개인", "retail", "retailNet"])
            if retail_col:
                retail = flow_data.get_column(retail_col).to_numpy().astype(np.float64)
                retail = np.nan_to_num(retail, nan=0.0)
                result["retailNetBuy"] = _analyzeInvestor(retail, "개인")

            # 종합 수급 판단
            bull_signals = 0
            bear_signals = 0
            for key in ("foreignNetBuy", "instNetBuy"):
                inv = result.get(key, {})
                if isinstance(inv, dict):
                    if inv.get("trend") == "매수 우위":
                        bull_signals += 1
                    elif inv.get("trend") == "매도 우위":
                        bear_signals += 1

            if bull_signals > bear_signals:
                result["flowVerdict"] = "bullish"
            elif bear_signals > bull_signals:
                result["flowVerdict"] = "bearish"
            else:
                result["flowVerdict"] = "neutral"

            if series:
                # Strategy DSL 입력: 5/20일 누적 시계열
                def _cum(arr: np.ndarray, win: int) -> np.ndarray:
                    out = np.full(len(arr), np.nan, dtype=np.float64)
                    for i in range(win, len(arr)):
                        out[i] = float(np.sum(arr[i - win + 1 : i + 1]))
                    return out

                series_data: dict = {}
                if foreign_col:
                    series_data["foreign_cum5"] = _cum(foreign, 5)
                    series_data["foreign_cum20"] = _cum(foreign, 20)
                if inst_col:
                    series_data["inst_cum5"] = _cum(inst, 5)
                    series_data["inst_cum20"] = _cum(inst, 20)
                # date 컬럼 함께 노출 (OHLCV 매칭용)
                date_col = _findCol(cols, ["date", "Date", "rcept_dt"])
                if date_col:
                    series_data["date"] = flow_data.get_column(date_col).to_list()
                result["_series"] = series_data

    except (ImportError, ValueError, TypeError) as e:
        log.warning("수급 분석 실패: %s — %s", stockCode, e)
        result["error"] = str(e)

    return result


def _analyzeInvestor(data: np.ndarray, name: str) -> dict:
    """투자자별 수급 분석."""
    n = len(data)
    if n == 0:
        return {"name": name, "error": "데이터 없음"}

    result = {"name": name}

    # 최근 합계
    result["total5d"] = float(np.sum(data[-5:])) if n >= 5 else float(np.sum(data))
    result["total20d"] = float(np.sum(data[-20:])) if n >= 20 else float(np.sum(data))

    # 순매수 연속 일수 (streak)
    streak = 0
    if data[-1] > 0:
        for i in range(n - 1, -1, -1):
            if data[i] > 0:
                streak += 1
            else:
                break
    elif data[-1] < 0:
        for i in range(n - 1, -1, -1):
            if data[i] < 0:
                streak -= 1
            else:
                break
    result["streak"] = streak
    result["streakDirection"] = "매수" if streak > 0 else "매도" if streak < 0 else "전환"

    # 수급 모멘텀 (5일 vs 20일)
    if n >= 20:
        avg_5 = float(np.mean(data[-5:]))
        avg_20 = float(np.mean(data[-20:]))
        result["momentum"] = (
            "가속" if abs(avg_5) > abs(avg_20) * 1.3 else "감속" if abs(avg_5) < abs(avg_20) * 0.7 else "유지"
        )

    # 추세
    total = result.get("total20d", 0)
    if total > 0:
        result["trend"] = "매수 우위"
    elif total < 0:
        result["trend"] = "매도 우위"
    else:
        result["trend"] = "중립"

    return result


def _fetchFlow(stockCode: str):
    """gather("flow") 호출."""
    try:
        from dartlab.gather.entry import GatherEntry

        g = GatherEntry()
        return g("flow", stockCode)
    except (ImportError, ValueError, TypeError, RuntimeError):
        return None


def _findCol(columns: list[str], candidates: list[str]) -> str | None:
    """컬럼 이름 매칭."""
    for c in candidates:
        for col in columns:
            if c in col:
                return col
    return None
