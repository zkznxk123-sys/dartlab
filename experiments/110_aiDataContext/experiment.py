"""실험 110: AI용 데이터 맥락 보강 (AI Data Context Enrichment)

가설: analysis calc 결과에 "비교 맥락"(업종 중앙값, 5년 평균, YoY, 등급)을
     함께 제공하면 AI의 해석 품질이 구조적으로 올라간다.

방법:
  A. 현재 방식 — raw dict를 TOON으로 인코딩해서 AI에 전달
  B. 보강 방식 — raw dict + 맥락(업종 비교, 추세 판단, 핵심 요약)을 함께 전달

비교: 같은 질문을 A/B로 물어서 AI 해석의 정확성/깊이를 비교

설계 방향 — 공통 변환 레이어:
  1. 각 엔진이 반환하는 dict/DataFrame은 변경하지 않는다 (기존 API 유지)
  2. AI 경로에서만 작동하는 "enrichment 레이어"를 하나 만든다
  3. api-contract 원칙: 새 프로퍼티 금지 → 같은 진입점에 파라미터 토글
     → ContextBuilder가 calc 결과를 AI용으로 변환하는 단계 추가
"""

from __future__ import annotations

import sys
sys.path.insert(0, "src")


# ── 1단계: 현재 raw 데이터 확인 ────────────────────────────

def get_raw_data(stock: str = "005930"):
    """analysis 수익성의 raw dict 구조."""
    import dartlab
    c = dartlab.Company(stock)
    r = c.analysis("financial", "수익성")
    return c, r


def show_raw(r: dict):
    """AI가 현재 받는 형태 — history 배열."""
    hist = r["marginTrend"]["history"]
    print("=== AI가 현재 보는 데이터 (raw) ===")
    for h in hist[:5]:
        print(f"  {h['period']:>6}  매출={h['revenue']/1e8:,.0f}억  "
              f"영업이익률={h['operatingMargin']:.1f}%  "
              f"순이익률={h['netMargin']:.1f}%")


# ── 2단계: 맥락 보강 프로토타입 ────────────────────────────

def enrich_for_ai(c, r: dict) -> dict:
    """raw analysis dict → AI가 이해하기 좋은 enriched dict.

    추가하는 맥락:
    1. 5년 평균 대비 현재 위치
    2. YoY 변화 방향 + 크기 판단 (대폭/소폭)
    3. 핵심 1줄 요약 (자연어)
    4. 업종 백분위 (scan 데이터 활용)
    """
    enriched = {}

    # ── marginTrend 보강 ──
    hist = r.get("marginTrend", {}).get("history", [])
    if len(hist) >= 2:
        latest = hist[0]
        prev = hist[1]
        period = latest["period"]

        # 5년 평균
        margins = [h["operatingMargin"] for h in hist[:5] if h.get("operatingMargin") is not None]
        avg_5y = sum(margins) / len(margins) if margins else None

        # YoY 변화
        opm_now = latest.get("operatingMargin")
        opm_prev = prev.get("operatingMargin")
        opm_delta = (opm_now - opm_prev) if opm_now is not None and opm_prev is not None else None

        # 변화 크기 판단
        def judge_delta(delta, metric_name=""):
            if delta is None:
                return "데이터 없음"
            if abs(delta) < 1:
                return "보합"
            elif abs(delta) < 3:
                return "소폭 개선" if delta > 0 else "소폭 하락"
            elif abs(delta) < 7:
                return "개선" if delta > 0 else "하락"
            else:
                return "대폭 개선" if delta > 0 else "대폭 하락"

        opm_judgment = judge_delta(opm_delta)

        # 핵심 요약 1줄
        summary_parts = []
        if opm_now is not None:
            summary_parts.append(f"영업이익률 {opm_now:.1f}%")
        if opm_delta is not None:
            summary_parts.append(f"전기 대비 {opm_delta:+.1f}pp ({opm_judgment})")
        if avg_5y is not None:
            diff_from_avg = opm_now - avg_5y if opm_now is not None else None
            if diff_from_avg is not None:
                pos = "위" if diff_from_avg > 0 else "아래"
                summary_parts.append(f"5년 평균({avg_5y:.1f}%) {pos} {abs(diff_from_avg):.1f}pp")

        enriched["marginTrend"] = {
            "summary": " · ".join(summary_parts),
            "current": {
                "period": period,
                "operatingMargin": opm_now,
                "netMargin": latest.get("netMargin"),
                "grossMargin": latest.get("grossMargin"),
            },
            "context": {
                "avg5y_operatingMargin": round(avg_5y, 2) if avg_5y else None,
                "yoy_delta_pp": round(opm_delta, 2) if opm_delta is not None else None,
                "yoy_judgment": opm_judgment,
                "trend_direction": "개선" if opm_delta and opm_delta > 0 else "악화" if opm_delta and opm_delta < 0 else "보합",
            },
            "history": hist[:5],  # 원본 유지
        }

    # ── returnTrend 보강 ──
    ret_hist = r.get("returnTrend", {}).get("history", [])
    if len(ret_hist) >= 2:
        latest_r = ret_hist[0]
        prev_r = ret_hist[1]
        roe_now = latest_r.get("roe")
        roe_prev = prev_r.get("roe")
        roe_delta = (roe_now - roe_prev) if roe_now is not None and roe_prev is not None else None

        roes = [h["roe"] for h in ret_hist[:5] if h.get("roe") is not None]
        avg_roe = sum(roes) / len(roes) if roes else None

        ret_summary_parts = []
        if roe_now is not None:
            ret_summary_parts.append(f"ROE {roe_now:.1f}%")
        if roe_delta is not None:
            ret_summary_parts.append(f"전기 대비 {roe_delta:+.1f}pp ({judge_delta(roe_delta)})")
        if avg_roe is not None and roe_now is not None:
            diff = roe_now - avg_roe
            pos = "위" if diff > 0 else "아래"
            ret_summary_parts.append(f"5년 평균({avg_roe:.1f}%) {pos} {abs(diff):.1f}pp")

        enriched["returnTrend"] = {
            "summary": " · ".join(ret_summary_parts),
            "history": ret_hist[:5],
        }

    # ── 업종 백분위 (scan 활용) ──
    try:
        import dartlab
        scan_df = dartlab.scan("profitability")
        stock_code = getattr(c, "stockCode", None)
        if scan_df is not None and stock_code:
            import polars as pl
            row = scan_df.filter(pl.col("종목코드") == stock_code)
            if row.shape[0] > 0:
                roe_col = "ROE"
                opm_col = "영업이익률"
                total = scan_df.shape[0]
                if opm_col in scan_df.columns:
                    rank = scan_df.filter(
                        pl.col(opm_col) > row[opm_col][0]
                    ).shape[0]
                    pct = round((1 - rank / total) * 100, 1)
                    enriched["peerPosition"] = {
                        "operatingMargin_percentile": pct,
                        "operatingMargin_rank": f"{rank+1}/{total}",
                        "summary": f"영업이익률 상위 {pct}% (전체 {total}개사 중 {rank+1}위)"
                    }
    except Exception:
        pass  # scan 실패해도 진행

    # ── profitabilityFlags 유지 ──
    flags = r.get("profitabilityFlags", [])
    if flags:
        enriched["warnings"] = [str(f) for f in flags[:5]]

    return enriched


def show_enriched(enriched: dict):
    """AI에게 전달할 보강된 데이터."""
    print("\n=== AI가 받을 보강 데이터 ===")
    mt = enriched.get("marginTrend", {})
    print(f"[수익성 요약] {mt.get('summary', '-')}")
    ctx = mt.get("context", {})
    print(f"  5년 평균 영업이익률: {ctx.get('avg5y_operatingMargin')}%")
    print(f"  YoY 변화: {ctx.get('yoy_delta_pp')}pp ({ctx.get('yoy_judgment')})")
    print(f"  추세: {ctx.get('trend_direction')}")

    rt = enriched.get("returnTrend", {})
    print(f"[수익률 요약] {rt.get('summary', '-')}")

    peer = enriched.get("peerPosition", {})
    if peer:
        print(f"[업종 위치] {peer.get('summary', '-')}")

    print(f"[경고] {enriched.get('warnings', '없음')}")


# ── 3단계: A/B 비교 — 같은 질문, 다른 컨텍스트 ─────────────

def ab_test():
    """A: raw TOON vs B: enriched TOON → AI 해석 품질 비교."""
    from dartlab.ai.context.encoder import encodeAuto

    c, r = get_raw_data("005930")
    show_raw(r)

    enriched = enrich_for_ai(c, r)
    show_enriched(enriched)

    # TOON 인코딩 비교
    raw_toon = encodeAuto(r["marginTrend"]["history"][:5])
    enriched_toon = encodeAuto(enriched)

    print(f"\n=== 토큰 비교 ===")
    print(f"Raw TOON:      {len(raw_toon):>6}자 (~{len(raw_toon)//3}토큰)")
    print(f"Enriched TOON: {len(enriched_toon):>6}자 (~{len(enriched_toon)//3}토큰)")
    print(f"추가 비용:     +{len(enriched_toon) - len(raw_toon)}자")

    print("\n=== Raw TOON (AI가 현재 보는 것) ===")
    print(raw_toon[:500])

    print("\n=== Enriched TOON (제안하는 것) ===")
    print(enriched_toon[:800])

    return enriched


# ── 4단계: 실제 AI 호출 A/B ─────────────────────────────

def ai_ab_test():
    """실제 AI에게 두 버전을 주고 해석 품질 비교."""
    from dartlab.ai.runtime.core import analyze
    from dartlab.ai.context.encoder import encodeAuto

    c, r = get_raw_data("005930")
    enriched = enrich_for_ai(c, r)

    question = "삼성전자 수익성이 지금 어떤 상태야? 좋은 거야 나쁜 거야?"

    # A: 현재 방식 — analyze 직접 호출
    print("=" * 60)
    print("A: 현재 방식 (raw)")
    print("=" * 60)
    chunks_a = []
    for ev in analyze(None, question):
        if ev.kind == "chunk":
            chunks_a.append(ev.data.get("text", ""))
    answer_a = "".join(chunks_a)
    print(answer_a[:2000])
    print(f"\n[A 응답 길이: {len(answer_a)}자]")

    # B: 보강 방식 — enriched 데이터를 컨텍스트에 추가 주입
    print("\n" + "=" * 60)
    print("B: 보강 방식 (enriched context)")
    print("=" * 60)
    enriched_text = encodeAuto(enriched)
    enriched_question = (
        f"{question}\n\n"
        f"<context source='experiment.enriched_profitability'>\n"
        f"{enriched_text}\n"
        f"</context>"
    )
    chunks_b = []
    for ev in analyze(None, enriched_question):
        if ev.kind == "chunk":
            chunks_b.append(ev.data.get("text", ""))
    answer_b = "".join(chunks_b)
    print(answer_b[:2000])
    print(f"\n[B 응답 길이: {len(answer_b)}자]")

    return answer_a, answer_b


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "ai":
        ai_ab_test()
    else:
        ab_test()
