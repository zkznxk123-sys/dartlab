"""수급 분석 — 기관/외국인 매매 분석 (KR전용).

gather("flow") 데이터를 퀀트 신호로 변환.
"""

from __future__ import annotations

import logging

import numpy as np

from dartlab.quant._helpers import resolve_market

log = logging.getLogger(__name__)


def analyze_flow(stockCode: str, *, market: str = "auto", series: bool = False, **kwargs) -> dict:
    """기관/외국인 수급 분석.

    Args:
        stockCode: 종목코드 (KR 전용).
        market: "KR" | "US" | "auto".
        series: True 면 dict 에 `_series` 키 추가 — Strategy DSL 입력용 누적 시계열.

    Returns:
        dict with foreignNetBuy, instNetBuy, flowMomentum, streak.
        series=True (KR only) 시: _series = {foreign_cum5, foreign_cum20, inst_cum5, inst_cum20}.
        US 면 _series = None.
    """
    market = resolve_market(stockCode, market)

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
    flow_data = _fetch_flow(stockCode)
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
            foreign_col = _find_col(cols, ["외국인", "foreign", "foreignNet"])
            if foreign_col:
                foreign = flow_data.get_column(foreign_col).to_numpy().astype(np.float64)
                foreign = np.nan_to_num(foreign, nan=0.0)
                result["foreignNetBuy"] = _analyze_investor(foreign, "외국인")

            # 기관 순매수
            inst_col = _find_col(cols, ["기관", "institution", "instNet", "기관계"])
            if inst_col:
                inst = flow_data.get_column(inst_col).to_numpy().astype(np.float64)
                inst = np.nan_to_num(inst, nan=0.0)
                result["instNetBuy"] = _analyze_investor(inst, "기관")

            # 개인 순매수
            retail_col = _find_col(cols, ["개인", "retail", "retailNet"])
            if retail_col:
                retail = flow_data.get_column(retail_col).to_numpy().astype(np.float64)
                retail = np.nan_to_num(retail, nan=0.0)
                result["retailNetBuy"] = _analyze_investor(retail, "개인")

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
                date_col = _find_col(cols, ["date", "Date", "rcept_dt"])
                if date_col:
                    series_data["date"] = flow_data.get_column(date_col).to_list()
                result["_series"] = series_data

    except (ImportError, ValueError, TypeError) as e:
        log.warning("수급 분석 실패: %s — %s", stockCode, e)
        result["error"] = str(e)

    return result


def _analyze_investor(data: np.ndarray, name: str) -> dict:
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


def _fetch_flow(stockCode: str):
    """gather("flow") 호출."""
    try:
        from dartlab.gather.entry import GatherEntry

        g = GatherEntry()
        return g("flow", stockCode)
    except (ImportError, ValueError, TypeError, RuntimeError):
        return None


def _find_col(columns: list[str], candidates: list[str]) -> str | None:
    """컬럼 이름 매칭."""
    for c in candidates:
        for col in columns:
            if c in col:
                return col
    return None
