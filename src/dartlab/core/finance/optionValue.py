"""Black-Scholes 옵션 가격 (scipy 무의존).

math.erf 기반 표준정규 CDF/PDF — merton.py 선례 재사용.
Real Options 용 범용 가격 SSOT.

근거:
- Hull, *Options, Futures, and Other Derivatives* Ch.15
- Damodaran, *Investment Valuation* Ch.28 (Real Options in Valuation)
"""

from __future__ import annotations

import math


def _normCdf(x: float) -> float:
    """표준정규 누적분포 — math.erf 기반."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _normPdf(x: float) -> float:
    """표준정규 확률밀도."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def blackScholesCall(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
) -> dict:
    """Black-Scholes European Call.

    Parameters
    ----------
    S : 기초자산 현재 가격
    K : 행사가
    T : 만기 (년)
    r : 무위험수익률 (소수, 예: 0.03)
    sigma : 변동성 (연환산, 예: 0.30)
    q : 연속 배당수익률 (기본 0)

    Returns
    -------
    dict
        call : float — 콜 가격
        put : float — 풋 가격 (put-call parity)
        d1, d2, Nd1, Nd2 : Black-Scholes 구성 요소
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        intrinsic = max(0.0, S - K)
        return {
            "call": intrinsic,
            "put": max(0.0, K - S),
            "d1": None,
            "d2": None,
            "Nd1": None,
            "Nd2": None,
        }

    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    nd1 = _normCdf(d1)
    nd2 = _normCdf(d2)

    call = S * math.exp(-q * T) * nd1 - K * math.exp(-r * T) * nd2
    put = K * math.exp(-r * T) * _normCdf(-d2) - S * math.exp(-q * T) * _normCdf(-d1)

    return {
        "call": call,
        "put": put,
        "d1": d1,
        "d2": d2,
        "Nd1": nd1,
        "Nd2": nd2,
    }


def binomialOption(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    steps: int = 50,
    kind: str = "call",
    american: bool = True,
) -> dict:
    """Cox-Ross-Rubinstein Binomial Tree — 미국식 옵션 가능.

    Parameters
    ----------
    steps : 시간 분할 수 (50 권장)
    kind : "call" 또는 "put"
    american : True 면 조기행사 허용

    Returns
    -------
    dict
        value : float — 옵션 가격
        steps : int
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0 or steps < 1:
        return {"value": 0.0, "steps": 0}

    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    p = (math.exp(r * dt) - d) / (u - d)
    if not (0 < p < 1):
        # 파라미터 수치적 문제 → Black-Scholes 폴백
        bs = blackScholesCall(S, K, T, r, sigma)
        return {"value": bs["call"] if kind == "call" else bs["put"], "steps": steps}

    disc = math.exp(-r * dt)

    # 만기 payoff
    prices = [S * (u ** (steps - i)) * (d ** i) for i in range(steps + 1)]
    values = [
        max(0.0, px - K) if kind == "call" else max(0.0, K - px)
        for px in prices
    ]

    # 뒤로 할인
    for step in range(steps - 1, -1, -1):
        new_values = []
        for i in range(step + 1):
            v = disc * (p * values[i] + (1 - p) * values[i + 1])
            if american:
                px = S * (u ** (step - i)) * (d ** i)
                intrinsic = max(0.0, px - K) if kind == "call" else max(0.0, K - px)
                v = max(v, intrinsic)
            new_values.append(v)
        values = new_values

    return {"value": values[0], "steps": steps}
