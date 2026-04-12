"""FRED 데이터 깊이 파기 — 실제 예측력이 있는 신호 탐색.

검증 방법: 각 신호를 1985~2025 walk-forward로 NASDAQ 6개월 방향 예측
baseline: "항상 up" = ~73%
이걸 이기는 신호만 가치가 있다.
"""

import logging

logging.basicConfig(level=logging.WARNING)
import numpy as np

# ── 헬퍼 ──


def fetch_monthly(g, sid):
    """FRED 시리즈 -> 월간 {month: value} dict."""
    df = g.macro(sid)
    if df is None or len(df) == 0:
        return {}
    dates = df.get_column("date").to_list()
    values = df.get_column("value").to_list()

    monthly = {}
    for d, v in zip(dates, values):
        if v is None:
            continue
        month = str(d)[:7]
        monthly[month] = float(v)  # 같은 달이면 마지막 값
    return monthly


def yoy(d):
    """월간 dict -> YoY 변화율 dict."""
    months = sorted(d.keys())
    result = {}
    for m in months:
        # 12개월 전 찾기
        y, mo = int(m[:4]), int(m[5:7])
        prev = f"{y-1:04d}-{mo:02d}"
        if prev in d and d[prev] != 0:
            result[m] = ((d[m] - d[prev]) / abs(d[prev])) * 100
    return result


def delta(d, months=6):
    """월간 dict -> N개월 변화량 dict."""
    sorted_months = sorted(d.keys())
    idx = {m: i for i, m in enumerate(sorted_months)}
    result = {}
    for m in sorted_months:
        i = idx[m]
        if i >= months:
            prev_m = sorted_months[i - months]
            result[m] = d[m] - d[prev_m]
    return result


def delta_pct(d, months=6):
    """N개월 변화율."""
    sorted_months = sorted(d.keys())
    idx = {m: i for i, m in enumerate(sorted_months)}
    result = {}
    for m in sorted_months:
        i = idx[m]
        if i >= months and abs(d[sorted_months[i - months]]) > 1e-10:
            prev_m = sorted_months[i - months]
            result[m] = ((d[m] - d[prev_m]) / abs(d[prev_m])) * 100
    return result


def ma(d, window=3):
    """이동평균."""
    sorted_months = sorted(d.keys())
    result = {}
    for i in range(window - 1, len(sorted_months)):
        vals = [d[sorted_months[j]] for j in range(i - window + 1, i + 1)]
        result[sorted_months[i]] = np.mean(vals)
    return result


# ── 메인 ──

from dartlab.gather import getDefaultGather

g = getDefaultGather()

# NASDAQ 6개월 forward return
nasdaq = fetch_monthly(g, "NASDAQCOM")
nasdaq_months = sorted(nasdaq.keys())
nasdaq_fwd6 = {}
for i, m in enumerate(nasdaq_months):
    if i + 6 < len(nasdaq_months):
        fm = nasdaq_months[i + 6]
        if nasdaq[m] > 0:
            nasdaq_fwd6[m] = ((nasdaq[fm] - nasdaq[m]) / nasdaq[m]) * 100
nasdaq_dir = {m: ("up" if r > 0 else "down") for m, r in nasdaq_fwd6.items()}

test_months = [m for m in sorted(nasdaq_dir.keys()) if "1985-01" <= m <= "2025-06"]
baseline_up = sum(1 for m in test_months if nasdaq_dir[m] == "up")
baseline_acc = baseline_up / len(test_months) * 100

print(f"테스트: {test_months[0]} ~ {test_months[-1]} ({len(test_months)}건)")
print(f"Baseline (항상 up): {baseline_acc:.1f}%")
print("=" * 70)

# 위기 기간 정의
crisis_months = set()
for y in range(2000, 2004):
    for m in range(1, 13):
        crisis_months.add(f"{y:04d}-{m:02d}")
for y in [2007, 2008, 2009]:
    for m in range(1, 13):
        crisis_months.add(f"{y:04d}-{m:02d}")
for m in range(1, 13):
    crisis_months.add(f"2022-{m:02d}")


def test_signal(name, signal, rule_fn, desc):
    """신호 테스트. rule_fn(value) -> 'up'|'down'|None"""
    hits = total = c_hits = c_total = 0
    for m in test_months:
        if m not in signal:
            continue
        pred = rule_fn(signal[m])
        if pred is None:
            continue
        actual = nasdaq_dir.get(m)
        if actual is None:
            continue
        total += 1
        if pred == actual:
            hits += 1
        if m in crisis_months:
            c_total += 1
            if pred == actual:
                c_hits += 1

    if total < 50:
        return
    acc = hits / total * 100
    c_str = ""
    if c_total > 10:
        c_acc = c_hits / c_total * 100
        c_str = f", 위기 {c_acc:.0f}%"
    marker = "**" if acc > baseline_acc + 2 else ("*" if acc > baseline_acc else " ")
    print(f"{marker} {name}: {acc:.1f}% ({total}건){c_str} -- {desc}")


# ── 금리 ──
print("\n── 금리 ──")

spread_10y2y = fetch_monthly(g, "T10Y2Y")
test_signal("10Y-2Y > 0", spread_10y2y, lambda x: "up" if x > 0 else "down", "YC 양수")
test_signal(
    "10Y-2Y > 0.5 strict",
    spread_10y2y,
    lambda x: "up" if x > 0.5 else ("down" if x < -0.3 else None),
    "확실한 극단만",
)

spread_10y3m = fetch_monthly(g, "T10Y3M")
test_signal("10Y-3M > 0", spread_10y3m, lambda x: "up" if x > 0 else "down", "3M YC")

hy_spread = fetch_monthly(g, "BAMLH0A0HYM2")
test_signal("HY < 5", hy_spread, lambda x: "up" if x < 5 else "down", "HY 수준")
test_signal(
    "HY < 4 strict",
    hy_spread,
    lambda x: "up" if x < 4 else ("down" if x > 6 else None),
    "극단만",
)

# HY 변화 방향
hy_delta3 = delta(hy_spread, 3)
test_signal(
    "HY 3m변화 < 0",
    hy_delta3,
    lambda x: "up" if x < 0 else "down",
    "HY 스프레드 축소 중",
)

real_rate = fetch_monthly(g, "DFII10")
test_signal("실질금리 < 1", real_rate, lambda x: "up" if x < 1 else "down", "실질금리 낮음")

# ── 실물경기 ──
print("\n── 실물경기 ──")

unrate = fetch_monthly(g, "UNRATE")
ur_d6 = delta(unrate, 6)
test_signal("실업률 6m변화 < 0", ur_d6, lambda x: "up" if x < 0 else "down", "실업률 하락")
test_signal(
    "실업률 6m변화 < 0.3",
    ur_d6,
    lambda x: "up" if x < 0.3 else "down",
    "실업률 급등 아님",
)
# 실업률 3개월 MA 방향 (Sahm Rule 변형)
ur_ma3 = ma(unrate, 3)
ur_ma3_d12 = {}
ur_ma3_months = sorted(ur_ma3.keys())
for i, m in enumerate(ur_ma3_months):
    if i >= 12:
        prev = ur_ma3_months[i - 12]
        ur_ma3_d12[m] = ur_ma3[m] - min(ur_ma3[ur_ma3_months[j]] for j in range(i - 12, i + 1))
test_signal("Sahm < 0.3", ur_ma3_d12, lambda x: "up" if x < 0.3 else "down", "Sahm Rule 변형")
test_signal("Sahm < 0.5", ur_ma3_d12, lambda x: "up" if x < 0.5 else "down", "Sahm 0.5")

indpro = fetch_monthly(g, "INDPRO")
ip_yoy = yoy(indpro)
test_signal("산업생산 YoY > 0", ip_yoy, lambda x: "up" if x > 0 else "down", "산업생산 성장")

# 산업생산 모멘텀 (가속도)
ip_d3 = delta_pct(indpro, 3)
test_signal("산업생산 3m > 0", ip_d3, lambda x: "up" if x > 0 else "down", "산업생산 3m 모멘텀")

icsa = fetch_monthly(g, "ICSA")
icsa_yoy_d = yoy(icsa)
test_signal(
    "실업수당 YoY < 0", icsa_yoy_d, lambda x: "up" if x < 0 else "down", "실업수당 감소"
)

# 실업수당 4주 MA 방향 (smoothed)
icsa_ma4 = ma(icsa, 4)
icsa_ma4_d = delta(icsa_ma4, 3)
test_signal(
    "실업수당MA 3m방향 < 0",
    icsa_ma4_d,
    lambda x: "up" if x < 0 else "down",
    "실업수당 MA 하락 중",
)

umcsent = fetch_monthly(g, "UMCSENT")
test_signal("소비자심리 > 70", umcsent, lambda x: "up" if x > 70 else "down", "심리 70+")
test_signal("소비자심리 > 80", umcsent, lambda x: "up" if x > 80 else "down", "심리 80+")
sent_d3 = delta(umcsent, 3)
test_signal(
    "소비자심리 3m변화 > 0", sent_d3, lambda x: "up" if x > 0 else "down", "심리 개선 중"
)

# ── 유동성 ──
print("\n── 유동성 ──")

m2 = fetch_monthly(g, "M2SL")
m2_yoy_d = yoy(m2)
test_signal(
    "M2 YoY > 5",
    m2_yoy_d,
    lambda x: "up" if x > 5 else ("down" if x < 2 else None),
    "M2 팽창/수축",
)
test_signal("M2 YoY > 0", m2_yoy_d, lambda x: "up" if x > 0 else "down", "M2 성장")

nfci = fetch_monthly(g, "NFCI")
test_signal("NFCI < 0", nfci, lambda x: "up" if x < 0 else "down", "금융환경 완화")
# NFCI 변화 방향
nfci_d3 = delta(nfci, 3)
test_signal(
    "NFCI 3m변화 < 0", nfci_d3, lambda x: "up" if x < 0 else "down", "금융환경 완화 중"
)

# 연준 총자산
walcl = fetch_monthly(g, "WALCL")
walcl_yoy = yoy(walcl)
test_signal("연준BS YoY > 0", walcl_yoy, lambda x: "up" if x > 0 else "down", "연준 확대")

# ── 인플레이션 ──
print("\n── 인플레이션 ──")

cpi = fetch_monthly(g, "CPIAUCSL")
cpi_yoy_d = yoy(cpi)
test_signal("CPI YoY < 4", cpi_yoy_d, lambda x: "up" if x < 4 else "down", "인플레 4% 미만")
test_signal("CPI YoY < 3", cpi_yoy_d, lambda x: "up" if x < 3 else "down", "인플레 3% 미만")
# CPI 모멘텀 (인플레 둔화/가속)
cpi_d3 = delta(cpi_yoy_d, 3)
test_signal(
    "CPI YoY 3m변화 < 0", cpi_d3, lambda x: "up" if x < 0 else "down", "인플레 둔화 중"
)

bei = fetch_monthly(g, "T10YIE")
test_signal("BEI < 2.5", bei, lambda x: "up" if x < 2.5 else "down", "기대인플레 안정")

# ── VIX ──
print("\n── 변동성 ──")

vix = fetch_monthly(g, "VIXCLS")
test_signal("VIX < 20", vix, lambda x: "up" if x < 20 else "down", "VIX 낮음")
test_signal("VIX < 25", vix, lambda x: "up" if x < 25 else "down", "VIX 25 미만")
# VIX 방향
vix_d3 = delta(vix, 3)
test_signal("VIX 3m변화 < 0", vix_d3, lambda x: "up" if x < 0 else "down", "VIX 하락 중")

# ── 주택 ──
print("\n── 주택 ──")

houst = fetch_monthly(g, "HOUST")
houst_yoy_d = yoy(houst)
test_signal("주택착공 YoY > 0", houst_yoy_d, lambda x: "up" if x > 0 else "down", "주택착공 증가")

# ── 복합 신호 ──
print("\n── 복합 신호 ──")


def combo_test(name, pred_fn, desc):
    hits = total = c_hits = c_total = 0
    for m in test_months:
        pred = pred_fn(m)
        if pred is None:
            continue
        actual = nasdaq_dir.get(m)
        if actual is None:
            continue
        total += 1
        if pred == actual:
            hits += 1
        if m in crisis_months:
            c_total += 1
            if pred == actual:
                c_hits += 1
    if total < 50:
        return
    acc = hits / total * 100
    c_str = ""
    if c_total > 10:
        c_str = f", 위기 {c_hits / c_total * 100:.0f}%"
    marker = "**" if acc > baseline_acc + 2 else ("*" if acc > baseline_acc else " ")
    print(f"{marker} {name}: {acc:.1f}% ({total}건){c_str} -- {desc}")


# YC + HY
combo_test(
    "YC>0 + HY<5",
    lambda m: (
        "up"
        if spread_10y2y.get(m, 0) > 0 and hy_spread.get(m, 10) < 5
        else (
            "down"
            if spread_10y2y.get(m, 0) < -0.3 and hy_spread.get(m, 0) > 6
            else None
        )
    ),
    "금리+신용",
)

# 실업률 + 산업생산
combo_test(
    "실업률하락 + IP성장",
    lambda m: (
        "up"
        if ur_d6.get(m, 1) < 0 and ip_yoy.get(m, -1) > 0
        else ("down" if ur_d6.get(m, 0) > 0.5 and ip_yoy.get(m, 1) < 0 else None)
    ),
    "고용+생산 동시",
)

# NFCI + CPI
combo_test(
    "NFCI완화 + CPI<4",
    lambda m: (
        "up"
        if nfci.get(m, 1) < 0 and cpi_yoy_d.get(m, 5) < 4
        else ("down" if nfci.get(m, -1) > 0 and cpi_yoy_d.get(m, 0) > 4 else None)
    ),
    "유동성+인플레",
)

# Sahm + HY
combo_test(
    "Sahm<0.3 + HY<5",
    lambda m: (
        "up"
        if ur_ma3_d12.get(m, 1) < 0.3 and hy_spread.get(m, 10) < 5
        else (
            "down"
            if ur_ma3_d12.get(m, 0) > 0.5 and hy_spread.get(m, 0) > 6
            else None
        )
    ),
    "Sahm+신용",
)

# 3-factor: 실업률변화 + HY + VIX
combo_test(
    "실업률OK + HY<5 + VIX<25",
    lambda m: (
        "up"
        if ur_d6.get(m, 1) < 0.3 and hy_spread.get(m, 10) < 5 and vix.get(m, 30) < 25
        else (
            "down"
            if ur_d6.get(m, 0) > 0.5 and (hy_spread.get(m, 0) > 6 or vix.get(m, 0) > 30)
            else None
        )
    ),
    "고용+신용+변동성",
)

# 전부 OK면 up
combo_test(
    "4-factor ALL OK",
    lambda m: (
        "up"
        if (
            ur_d6.get(m, 1) < 0.3
            and hy_spread.get(m, 10) < 5
            and cpi_yoy_d.get(m, 5) < 4
            and spread_10y2y.get(m, -1) > 0
        )
        else (
            "down"
            if (
                ur_d6.get(m, 0) > 0.5
                and hy_spread.get(m, 0) > 6
            )
            else None
        )
    ),
    "고용+신용+인플레+YC",
)

print()
print(f"** = baseline+2%p 초과, * = baseline 초과")
print(f"Baseline: {baseline_acc:.1f}%")
