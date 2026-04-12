"""FRED 데이터 깊이 파기 — 역사적 팩트 기반 인사이트 발견.

방향 예측이 아니라:
1. "이 지표가 이 수준일 때 과거에 무슨 일이 있었나" (조건부 통계)
2. "지금 상태가 과거 언제와 비슷한가" (regime 매칭)
3. "이 조합이 동시에 나타나면 위험 신호인가" (복합 경고)
"""

import logging

logging.basicConfig(level=logging.WARNING)
import numpy as np


def fetch_monthly(g, sid):
    df = g.macro(sid)
    if df is None or len(df) == 0:
        return {}
    dates = df.get_column("date").to_list()
    values = df.get_column("value").to_list()
    monthly = {}
    for d, v in zip(dates, values):
        if v is not None:
            monthly[str(d)[:7]] = float(v)
    return monthly


def yoy(d):
    months = sorted(d.keys())
    result = {}
    for m in months:
        y, mo = int(m[:4]), int(m[5:7])
        prev = f"{y-1:04d}-{mo:02d}"
        if prev in d and abs(d[prev]) > 1e-10:
            result[m] = ((d[m] - d[prev]) / abs(d[prev])) * 100
    return result


def delta(d, months=6):
    sorted_months = sorted(d.keys())
    idx = {m: i for i, m in enumerate(sorted_months)}
    result = {}
    for m in sorted_months:
        i = idx[m]
        if i >= months:
            result[m] = d[m] - d[sorted_months[i - months]]
    return result


def ma(d, window=3):
    sorted_months = sorted(d.keys())
    result = {}
    for i in range(window - 1, len(sorted_months)):
        vals = [d[sorted_months[j]] for j in range(i - window + 1, i + 1)]
        result[sorted_months[i]] = np.mean(vals)
    return result


# NBER 침체 기간 (미국)
RECESSIONS = [
    ("1980-01", "1980-07"),
    ("1981-07", "1982-11"),
    ("1990-07", "1991-03"),
    ("2001-03", "2001-11"),
    ("2007-12", "2009-06"),
    ("2020-02", "2020-04"),
]


def is_recession(month):
    for start, end in RECESSIONS:
        if start <= month <= end:
            return True
    return False


def months_to_recession(month):
    """다음 침체까지 남은 개월 수. 침체 중이면 0."""
    if is_recession(month):
        return 0
    for start, _ in RECESSIONS:
        if month < start:
            y1, m1 = int(month[:4]), int(month[5:7])
            y2, m2 = int(start[:4]), int(start[5:7])
            return (y2 - y1) * 12 + (m2 - m1)
    return 999


# ── 데이터 수집 ──

from dartlab.gather import getDefaultGather

g = getDefaultGather()

print("데이터 수집 중...")
hy_spread = fetch_monthly(g, "BAMLH0A0HYM2")
spread_10y2y = fetch_monthly(g, "T10Y2Y")
spread_10y3m = fetch_monthly(g, "T10Y3M")
unrate = fetch_monthly(g, "UNRATE")
cpi_raw = fetch_monthly(g, "CPIAUCSL")
indpro = fetch_monthly(g, "INDPRO")
vix = fetch_monthly(g, "VIXCLS")
nfci = fetch_monthly(g, "NFCI")
m2 = fetch_monthly(g, "M2SL")
icsa = fetch_monthly(g, "ICSA")
umcsent = fetch_monthly(g, "UMCSENT")
bei = fetch_monthly(g, "T10YIE")
fedfunds = fetch_monthly(g, "FEDFUNDS")
houst = fetch_monthly(g, "HOUST")
real_rate = fetch_monthly(g, "DFII10")
nasdaq = fetch_monthly(g, "NASDAQCOM")

# 파생
cpi_yoy = yoy(cpi_raw)
ip_yoy = yoy(indpro)
m2_yoy = yoy(m2)
icsa_yoy = yoy(icsa)
houst_yoy = yoy(houst)
hy_d3 = delta(hy_spread, 3)
hy_d6 = delta(hy_spread, 6)
ur_d6 = delta(unrate, 6)
vix_d3 = delta(vix, 3)
nfci_d3 = delta(nfci, 3)
cpi_accel = delta(cpi_yoy, 3)  # CPI 가속도
ff_d6 = delta(fedfunds, 6)  # 금리 변화 방향

print("데이터 수집 완료")
print()

# ══════════════════════════════════════════════════════════
# 인사이트 1: HY 스프레드 급등 → 침체까지 몇 개월?
# ══════════════════════════════════════════════════════════
print("=" * 70)
print("인사이트 1: HY 스프레드 급등 후 침체까지")
print("=" * 70)

# HY가 3개월간 +100bp 이상 급등한 시점
hy_spikes = []
for m in sorted(hy_d3.keys()):
    if hy_d3[m] > 1.0:  # +100bp
        mtr = months_to_recession(m)
        hy_spikes.append((m, hy_d3[m], mtr, is_recession(m)))

print(f"HY 스프레드 3개월 +100bp 이상 급등: {len(hy_spikes)}회")
print(f"{'날짜':>8} {'변화(bp)':>8} {'침체까지':>8} {'침체중':>6}")
for m, chg, mtr, in_rec in hy_spikes:
    rec_str = "침체중" if in_rec else (f"{mtr}개월" if mtr < 100 else "-")
    print(f"{m:>8} {chg*100:>+8.0f}bp {rec_str:>8}")

# 통계
non_rec_spikes = [s for s in hy_spikes if not s[3] and s[2] < 100]
if non_rec_spikes:
    avg_lead = np.mean([s[2] for s in non_rec_spikes])
    within_12 = sum(1 for s in non_rec_spikes if s[2] <= 12)
    print(f"\n침체 전 급등 → 평균 {avg_lead:.0f}개월 후 침체")
    print(f"12개월 내 침체 비율: {within_12}/{len(non_rec_spikes)} = {within_12/len(non_rec_spikes)*100:.0f}%")

# ══════════════════════════════════════════════════════════
# 인사이트 2: Yield Curve 역전 → 침체까지
# ══════════════════════════════════════════════════════════
print()
print("=" * 70)
print("인사이트 2: Yield Curve 역전 → 침체까지 (10Y-3M)")
print("=" * 70)

# 역전 시작점 찾기 (양→음 전환)
inversions = []
prev_positive = True
inversion_start = None
for m in sorted(spread_10y3m.keys()):
    val = spread_10y3m[m]
    if val < 0 and prev_positive:
        inversion_start = m
        mtr = months_to_recession(m)
        inversions.append((m, val, mtr))
    prev_positive = val >= 0

print(f"{'역전시작':>10} {'스프레드':>8} {'침체까지':>8}")
for m, val, mtr in inversions:
    rec_str = f"{mtr}개월" if mtr < 100 else "-"
    print(f"{m:>10} {val:>+8.2f}% {rec_str:>8}")

if inversions:
    valid = [i for i in inversions if i[2] < 100]
    if valid:
        leads = [i[2] for i in valid]
        print(f"\n역전 → 침체: 평균 {np.mean(leads):.0f}개월, 중위 {np.median(leads):.0f}개월")
        print(f"범위: {min(leads)}~{max(leads)}개월")

# ══════════════════════════════════════════════════════════
# 인사이트 3: 실업률 반등 시작 → 침체까지
# ══════════════════════════════════════════════════════════
print()
print("=" * 70)
print("인사이트 3: 실업률 저점에서 반등 시작 → 침체까지")
print("=" * 70)

# 실업률 12개월 최저에서 +0.3%p 이상 반등
ur_months = sorted(unrate.keys())
ur_bounces = []
for i, m in enumerate(ur_months):
    if i < 12:
        continue
    window = [unrate[ur_months[j]] for j in range(i - 12, i + 1)]
    low = min(window)
    if unrate[m] - low >= 0.3 and unrate[ur_months[i - 1]] - low < 0.3:
        # 이번 달에 처음 0.3%p 돌파
        mtr = months_to_recession(m)
        ur_bounces.append((m, unrate[m], low, unrate[m] - low, mtr))

print(f"{'날짜':>8} {'실업률':>6} {'12m저점':>7} {'반등폭':>6} {'침체까지':>8}")
for m, ur, low, bounce, mtr in ur_bounces:
    rec_str = "침체중" if mtr == 0 else (f"{mtr}개월" if mtr < 100 else "-")
    print(f"{m:>8} {ur:>6.1f}% {low:>7.1f}% {bounce:>+5.1f}pp {rec_str:>8}")

# ══════════════════════════════════════════════════════════
# 인사이트 4: CPI 가속도 — 인플레이션이 빠르게 올라갈 때
# ══════════════════════════════════════════════════════════
print()
print("=" * 70)
print("인사이트 4: CPI 가속 구간 (3개월간 YoY +1%p 이상 상승)")
print("=" * 70)

cpi_accel_events = []
for m in sorted(cpi_accel.keys()):
    if cpi_accel[m] > 1.0:  # 3개월간 CPI YoY가 1%p 이상 상승
        cpi_val = cpi_yoy.get(m)
        ff_val = fedfunds.get(m)
        cpi_accel_events.append((m, cpi_accel[m], cpi_val, ff_val))

print(f"CPI 가속 이벤트: {len(cpi_accel_events)}회")
print(f"{'날짜':>8} {'가속도':>8} {'CPI YoY':>8} {'기준금리':>8}")
for m, acc, cpi, ff in cpi_accel_events[:20]:
    cpi_s = f"{cpi:.1f}%" if cpi else "-"
    ff_s = f"{ff:.2f}%" if ff else "-"
    print(f"{m:>8} {acc:>+7.1f}pp {cpi_s:>8} {ff_s:>8}")

# ══════════════════════════════════════════════════════════
# 인사이트 5: 동시 악화 — 3개 이상 경고등이 동시에 켜질 때
# ══════════════════════════════════════════════════════════
print()
print("=" * 70)
print("인사이트 5: 동시 경고등 (3개 이상 동시 점등)")
print("=" * 70)

warnings_by_month = {}
all_months = sorted(
    set(hy_spread.keys())
    & set(spread_10y2y.keys())
    & set(unrate.keys())
    & set(cpi_yoy.keys())
)

for m in all_months:
    flags = []
    if m in hy_spread and hy_spread[m] > 5:
        flags.append("HY>5%")
    if m in hy_d3 and hy_d3[m] > 0.5:
        flags.append("HY급등")
    if m in spread_10y2y and spread_10y2y[m] < 0:
        flags.append("YC역전")
    if m in ur_d6 and ur_d6[m] > 0.3:
        flags.append("실업↑")
    if m in vix and vix[m] > 25:
        flags.append("VIX>25")
    if m in nfci and nfci[m] > 0:
        flags.append("NFCI긴축")
    if m in ip_yoy and ip_yoy[m] < 0:
        flags.append("산업생산↓")
    if m in cpi_yoy and cpi_yoy[m] > 5:
        flags.append("CPI>5%")

    if len(flags) >= 3:
        mtr = months_to_recession(m)
        warnings_by_month[m] = (flags, mtr, is_recession(m))

# 최근부터 역순으로 표시
sorted_warnings = sorted(warnings_by_month.items(), reverse=True)
print(f"3개+ 동시 경고: {len(sorted_warnings)}회")
print(f"{'날짜':>8} {'경고수':>4} {'침체':>8} 내용")
for m, (flags, mtr, in_rec) in sorted_warnings[:30]:
    rec_str = "침체중" if in_rec else (f"{mtr}m전" if mtr < 24 else "-")
    print(f"{m:>8} {len(flags):>4}개 {rec_str:>8} {', '.join(flags)}")

# 동시 경고 → 침체 통계
multi_warn_pre = [
    (m, data)
    for m, data in sorted_warnings
    if not data[2] and data[1] < 100  # 침체 중 아니고 침체 전
]
if multi_warn_pre:
    leads = [d[1] for _, d in multi_warn_pre]
    within_18 = sum(1 for l in leads if l <= 18)
    print(
        f"\n침체 전 동시경고 → 18개월 내 침체: {within_18}/{len(multi_warn_pre)} = {within_18/len(multi_warn_pre)*100:.0f}%"
    )

# ══════════════════════════════════════════════════════════
# 인사이트 6: 현재 상태 진단
# ══════════════════════════════════════════════════════════
print()
print("=" * 70)
print("인사이트 6: 현재 상태 진단 (최신 데이터)")
print("=" * 70)

latest_month = max(
    set(hy_spread.keys())
    & set(spread_10y2y.keys())
    & set(unrate.keys())
)

indicators = {
    "HY 스프레드": hy_spread.get(latest_month),
    "10Y-2Y": spread_10y2y.get(latest_month),
    "10Y-3M": spread_10y3m.get(latest_month),
    "실업률": unrate.get(latest_month),
    "실업률 6m변화": ur_d6.get(latest_month),
    "CPI YoY": cpi_yoy.get(latest_month),
    "CPI 가속도": cpi_accel.get(latest_month),
    "산업생산 YoY": ip_yoy.get(latest_month),
    "VIX": vix.get(latest_month),
    "NFCI": nfci.get(latest_month),
    "M2 YoY": m2_yoy.get(latest_month),
    "소비자심리": umcsent.get(latest_month),
    "BEI 10Y": bei.get(latest_month),
    "기준금리": fedfunds.get(latest_month),
    "실질금리": real_rate.get(latest_month),
}

print(f"기준: {latest_month}")
print()
for name, val in indicators.items():
    if val is not None:
        print(f"  {name:>14}: {val:>8.2f}")

# 현재 경고등
current_flags = []
if hy_spread.get(latest_month, 0) > 5:
    current_flags.append("HY>5%")
if hy_d3.get(latest_month, 0) > 0.5:
    current_flags.append("HY급등")
if spread_10y2y.get(latest_month, 1) < 0:
    current_flags.append("YC역전")
if ur_d6.get(latest_month, 0) > 0.3:
    current_flags.append("실업↑")
if vix.get(latest_month, 0) > 25:
    current_flags.append("VIX>25")
if nfci.get(latest_month, -1) > 0:
    current_flags.append("NFCI긴축")
if ip_yoy.get(latest_month, 1) < 0:
    current_flags.append("산업생산↓")
if cpi_yoy.get(latest_month, 0) > 5:
    current_flags.append("CPI>5%")

print(f"\n현재 경고등: {len(current_flags)}개")
if current_flags:
    print(f"  → {', '.join(current_flags)}")
else:
    print("  → 없음 (양호)")

# 과거 유사 시기 (같은 경고등 조합)
if current_flags:
    similar_periods = []
    for m, (flags, mtr, in_rec) in sorted_warnings:
        overlap = set(flags) & set(current_flags)
        if len(overlap) >= 2:
            similar_periods.append((m, flags, mtr, in_rec, overlap))

    if similar_periods:
        print(f"\n과거 유사 시기 (경고등 2개+ 일치):")
        for m, flags, mtr, in_rec, overlap in similar_periods[:5]:
            rec_str = "침체중" if in_rec else (f"{mtr}m후 침체" if mtr < 24 else "침체 없음")
            print(f"  {m}: {', '.join(flags)} → {rec_str}")
