"""실험 110-2: 자동 감지 기반 AI 맥락 보강 — 엔진별 수작업 0

핵심 아이디어:
  모든 엔진의 반환값은 3가지 패턴 중 하나:
  1. dict with history[] → period + 숫자 필드 (analysis 전축)
  2. DataFrame → 컬럼명 + 타입 + 통계
  3. flat dict → key: value (credit 등급, quant 종합)

  이 3가지 패턴을 자동 감지해서 맥락을 보강하면,
  엔진이 새 축을 추가해도 enrichment가 자동 적용된다.
"""

from __future__ import annotations
import sys
sys.path.insert(0, "src")


def auto_enrich(data, *, company=None, label: str = "") -> dict:
    """엔진 반환값을 자동 감지해서 AI용 맥락 보강.

    엔진별 수작업 0. 구조만 보고 판단.
    - dict with history[] → _enrich_timeseries
    - DataFrame → _enrich_dataframe
    - flat dict (숫자 키) → _enrich_flat
    """
    import polars as pl

    if isinstance(data, pl.DataFrame):
        return _enrich_dataframe(data, label=label)

    if isinstance(data, dict):
        # history를 가진 서브키가 있으면 시계열
        ts_keys = [k for k, v in data.items()
                   if isinstance(v, dict) and "history" in v
                   and isinstance(v["history"], list) and v["history"]]
        if ts_keys:
            return _enrich_dict_with_history(data, ts_keys, company=company, label=label)

        # flat dict (숫자가 있는)
        numeric_keys = [k for k, v in data.items() if isinstance(v, (int, float))]
        if numeric_keys:
            return _enrich_flat(data, label=label)

    # 변환 불가 → 원본 반환
    return {"_raw": data, "_enriched": False}


# ── 패턴 1: dict with history[] ──────────────────────────

def _enrich_dict_with_history(data: dict, ts_keys: list[str], *, company=None, label: str = "") -> dict:
    """history[] 시계열을 자동 보강. 엔진/축 무관."""
    enriched = {"_label": label, "_enriched": True, "summaries": [], "keys": {}}

    for ts_key in ts_keys:
        hist = data[ts_key]["history"]
        if not hist:
            continue

        latest = hist[0]
        period = latest.get("period", "?")

        # 모든 숫자 필드를 자동 감지
        numeric_fields = [k for k, v in latest.items()
                         if isinstance(v, (int, float)) and k != "period"]

        field_summaries = []
        for field in numeric_fields:
            values = [h.get(field) for h in hist[:5] if h.get(field) is not None]
            if not values:
                continue

            current = values[0]
            avg = sum(values) / len(values)
            is_ratio = _is_ratio_field(field, current)

            # YoY — 비율은 차이(pp), 금액은 변화율(%)
            yoy = None
            yoy_unit = "pp" if is_ratio else "%"
            if len(values) >= 2 and values[1] is not None:
                if is_ratio:
                    yoy = current - values[1]  # pp 차이
                elif values[1] != 0:
                    yoy = (current - values[1]) / abs(values[1]) * 100  # 변화율 %

            # 5년 평균 대비도 같은 로직
            if is_ratio:
                vs_avg = current - avg if avg is not None else None
            else:
                vs_avg = ((current - avg) / abs(avg) * 100) if avg and avg != 0 else None

            judgment = _judge_change(yoy, is_ratio)

            # 5년 평균 대비
            vs_avg = current - avg if avg != 0 else None
            avg_pos = "위" if vs_avg and vs_avg > 0 else "아래" if vs_avg and vs_avg < 0 else "동일"

            field_summaries.append({
                "field": field,
                "current": current,
                "period": period,
                "avg5": round(avg, 2),
                "vs_avg": round(vs_avg, 2) if vs_avg is not None else None,
                "avg_position": avg_pos,
                "yoy_delta": round(yoy, 2) if yoy is not None else None,
                "yoy_judgment": judgment,
            })

        # 핵심 필드만 요약 문장 생성 (상위 3개 — 변화가 큰 순)
        sorted_fields = sorted(field_summaries,
                              key=lambda x: abs(x["yoy_delta"]) if x["yoy_delta"] is not None else 0,
                              reverse=True)

        # 핵심 필드 우선 정렬: 비율 필드를 금액 필드보다 앞에
        ratio_fields = [fs for fs in sorted_fields if _is_ratio_field(fs["field"], fs["current"])]
        amount_fields = [fs for fs in sorted_fields if not _is_ratio_field(fs["field"], fs["current"])]
        prioritized = ratio_fields[:3] or amount_fields[:3]  # 비율 우선, 없으면 금액

        top_summaries = []
        for fs in prioritized:
            is_ratio = _is_ratio_field(fs["field"], fs["current"])
            unit = "pp" if is_ratio else "%"
            parts = [f"{_korean_name(fs['field'])} {_format_number(fs['current'], fs['field'])}"]
            if fs["yoy_delta"] is not None:
                parts.append(f"전기비 {fs['yoy_delta']:+.1f}{unit}({fs['yoy_judgment']})")
            if fs["vs_avg"] is not None:
                avg_unit = "pp" if is_ratio else "%"
                parts.append(f"5년평균 {fs['avg_position']} {abs(fs['vs_avg']):.1f}{avg_unit}")
            top_summaries.append(" · ".join(parts))

        enriched["keys"][ts_key] = {
            "summary": " | ".join(top_summaries),
            "fields": {fs["field"]: fs for fs in field_summaries},
            "history_periods": [h.get("period") for h in hist[:5]],
        }
        enriched["summaries"].append(f"[{ts_key}] {' | '.join(top_summaries)}")

    # 업종 백분위 (company가 있으면)
    if company:
        peer = _get_peer_position(company)
        if peer:
            enriched["peerPosition"] = peer
            enriched["summaries"].append(f"[업종위치] {peer['summary']}")

    # 전체 1줄 요약
    enriched["oneLiner"] = " / ".join(enriched["summaries"][:3])

    # 원본 history 유지
    enriched["_raw"] = data

    return enriched


# ── 패턴 2: DataFrame ────────────────────────────────────

def _enrich_dataframe(df, *, label: str = "") -> dict:
    """DataFrame 자동 보강 — 스키마 + 통계 + 요약."""
    import polars as pl

    enriched = {
        "_label": label,
        "_enriched": True,
        "schema": {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)},
        "shape": {"rows": df.shape[0], "cols": df.shape[1]},
        "columns": df.columns,
    }

    # 숫자 컬럼 통계
    numeric_cols = [col for col, dtype in zip(df.columns, df.dtypes)
                   if dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32)]
    if numeric_cols:
        stats = {}
        for col in numeric_cols[:5]:  # 상위 5개만
            series = df[col].drop_nulls()
            if len(series) > 0:
                stats[col] = {
                    "min": round(float(series.min()), 2),
                    "max": round(float(series.max()), 2),
                    "mean": round(float(series.mean()), 2),
                    "median": round(float(series.median()), 2),
                }
        enriched["stats"] = stats

    # 샘플 3행
    enriched["sample"] = df.head(3).to_dicts()

    enriched["oneLiner"] = f"{label}: {df.shape[0]}행 × {df.shape[1]}열, 컬럼=[{', '.join(df.columns[:6])}{'...' if len(df.columns) > 6 else ''}]"

    return enriched


# ── 패턴 3: flat dict ────────────────────────────────────

def _enrich_flat(data: dict, *, label: str = "") -> dict:
    """flat dict 보강 — 숫자 필드에 의미 부여."""
    enriched = {
        "_label": label,
        "_enriched": True,
        "fields": {},
    }

    summaries = []
    for k, v in data.items():
        if isinstance(v, (int, float)):
            enriched["fields"][k] = {
                "value": v,
                "display": _format_number(v, k),
            }
            summaries.append(f"{_korean_name(k)}={_format_number(v, k)}")
        elif isinstance(v, str) and len(v) < 50:
            enriched["fields"][k] = {"value": v}
            summaries.append(f"{_korean_name(k)}={v}")

    enriched["oneLiner"] = " · ".join(summaries[:5])
    enriched["_raw"] = data
    return enriched


# ── 유틸 ─────────────────────────────────────────────────

def _is_ratio_field(field: str, value) -> bool:
    """비율 필드인지 판단 (이름 + 값 범위)."""
    ratio_keywords = {"margin", "ratio", "rate", "roe", "roa", "roic", "turnover",
                      "pct", "yield", "percent", "coverage", "leverage"}
    if any(kw in field.lower() for kw in ratio_keywords):
        return True
    # 값이 -100~200 범위면 비율일 가능성 높음
    if isinstance(value, (int, float)) and -100 <= value <= 200:
        return True
    return False


def _judge_change(delta, is_ratio: bool) -> str:
    """변화 크기 판단."""
    if delta is None:
        return "데이터 없음"
    threshold = 1 if is_ratio else 5
    if abs(delta) < threshold * 0.5:
        return "보합"
    elif abs(delta) < threshold * 2:
        return "소폭 개선" if delta > 0 else "소폭 악화"
    elif abs(delta) < threshold * 5:
        return "개선" if delta > 0 else "악화"
    else:
        return "대폭 개선" if delta > 0 else "대폭 악화"


_KOREAN_NAMES = {
    "operatingMargin": "영업이익률", "netMargin": "순이익률", "grossMargin": "매출총이익률",
    "roe": "ROE", "roa": "ROA", "roic": "ROIC",
    "revenue": "매출", "operatingIncome": "영업이익", "netIncome": "순이익",
    "debtRatio": "부채비율", "equityRatio": "자기자본비율",
    "ocf": "영업CF", "fcf": "FCF", "capex": "CAPEX",
    "ccc": "CCC", "dso": "매출채권회수일", "dio": "재고회전일",
    "totalAssetTurnover": "총자산회전율",
    "revenueYoy": "매출YoY", "operatingIncomeYoy": "영업이익YoY",
    "healthScore": "건전도", "score": "점수", "grade": "등급",
    "verdict": "종합판단", "rsi": "RSI", "adx": "ADX",
}

def _korean_name(field: str) -> str:
    return _KOREAN_NAMES.get(field, field)


def _format_number(value, field: str = "") -> str:
    """숫자를 사람이 읽기 좋은 형태로."""
    if value is None:
        return "-"
    if _is_ratio_field(field, value):
        return f"{value:.1f}%"
    if isinstance(value, float) and abs(value) > 1e12:
        return f"{value/1e12:.1f}조"
    if isinstance(value, float) and abs(value) > 1e8:
        return f"{value/1e8:,.0f}억"
    if isinstance(value, float):
        return f"{value:,.1f}"
    return str(value)


def _get_peer_position(company) -> dict | None:
    """scan에서 업종 백분위 조회."""
    try:
        import dartlab
        import polars as pl
        scan_df = dartlab.scan("profitability")
        stock_code = getattr(company, "stockCode", None)
        if scan_df is None or not stock_code:
            return None
        row = scan_df.filter(pl.col("종목코드") == stock_code)
        if row.shape[0] == 0:
            return None
        total = scan_df.shape[0]
        opm = row["영업이익률"][0] if "영업이익률" in row.columns else None
        if opm is None:
            return None
        rank = scan_df.filter(pl.col("영업이익률") > opm).shape[0] + 1
        pct = round((1 - rank / total) * 100, 1)
        return {
            "percentile": pct,
            "rank": f"{rank}/{total}",
            "summary": f"영업이익률 상위 {pct}% ({total}개사 중 {rank}위)",
        }
    except Exception:
        return None


# ── 테스트 ────────────────────────────────────────────────

def test_all_engines():
    """모든 엔진에 auto_enrich 적용 — 수작업 0 확인."""
    import dartlab
    c = dartlab.Company("005930")

    print("=" * 60)
    print("모든 엔진 auto_enrich 테스트 — 엔진별 수작업 0")
    print("=" * 60)

    # analysis 전축
    for axis in ["수익성", "성장성", "안정성", "현금흐름", "비용구조", "효율성"]:
        r = c.analysis("financial", axis)
        enriched = auto_enrich(r, company=c, label=f"analysis/{axis}")
        print(f"\n[analysis/{axis}]")
        print(f"  {enriched.get('oneLiner', '-')}")

    # credit
    cr = c.credit("등급")
    enriched = auto_enrich(cr, label="credit/등급")
    print(f"\n[credit/등급]")
    print(f"  {enriched.get('oneLiner', '-')}")

    # quant
    qt = c.quant("종합")
    enriched = auto_enrich(qt, label="quant/종합")
    print(f"\n[quant/종합]")
    print(f"  {enriched.get('oneLiner', '-')}")

    # scan
    df = dartlab.scan("profitability")
    enriched = auto_enrich(df, label="scan/profitability")
    print(f"\n[scan/profitability]")
    print(f"  {enriched.get('oneLiner', '-')}")

    # show
    df2 = c.show("IS")
    enriched = auto_enrich(df2, label="show/IS")
    print(f"\n[show/IS]")
    print(f"  {enriched.get('oneLiner', '-')}")

    # macro
    try:
        m = dartlab.macro("사이클")
        enriched = auto_enrich(m, label="macro/사이클")
        print(f"\n[macro/사이클]")
        print(f"  {enriched.get('oneLiner', '-')}")
    except Exception as e:
        print(f"\n[macro/사이클] SKIP: {e}")


if __name__ == "__main__":
    test_all_engines()
