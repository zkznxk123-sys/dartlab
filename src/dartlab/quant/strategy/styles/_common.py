"""스타일 빌드 공통 헬퍼 — OHLCV 페치 + 시장 분기 + length 정렬.

각 스타일 build 함수가 import 해서 보일러플레이트 없이 시작할 수 있게 하는
얇은 공용 모듈. 헬퍼 난립 금지 — 이 파일 외에 styles/ 안에 별도 utility 만들지 말 것.
"""

from __future__ import annotations

import numpy as np

from dartlab.quant._helpers import fetch_ohlcv, ohlcv_to_arrays, resolve_market


def get_arrays(company) -> dict:
    """Company 객체에서 OHLCV → numpy dict 변환.

    Returns:
        dict {open, high, low, close, volume, date} 또는 빈 dict
    """
    code = getattr(company, "stockCode", None) or getattr(company, "stock_code", None)
    if not code:
        return {}
    df = fetch_ohlcv(code)
    if df is None or df.is_empty():
        return {}
    return ohlcv_to_arrays(df)


def is_kr(company) -> bool:
    """KR 시장 여부."""
    code = getattr(company, "stockCode", None) or getattr(company, "stock_code", "")
    return resolve_market(code, "auto") == "KR"


def stock_code(company) -> str:
    return getattr(company, "stockCode", None) or getattr(company, "stock_code", "")


def safe_quantile(arr: np.ndarray, q: float) -> float:
    """NaN-safe quantile."""
    a = arr[~np.isnan(arr)]
    if len(a) < 10:
        return float("nan")
    return float(np.quantile(a, q))
