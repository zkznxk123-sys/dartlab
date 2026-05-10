"""Story Validation — Damodaran *Narrative and Numbers* 검증.

스토리의 타당성은 3단계 테스트를 통과해야 한다:

1. Possible (History)  — 과거 유사 사례가 있는가
2. Plausible (Experience) — 유사 경로에서 실제로 달성된 수치 분포 안에 있는가
3. Probable (Common Sense) — 수학/경제 첫 원칙에 부합하는가

엔진은 dict 만 반환. 해석 문장은 story narrate 층.
새 엔진 만들지 않고 scan/KnowledgeDB/consistency 기존 자산 조합.
"""

from __future__ import annotations

from typing import Any


def calcStoryPrecedents(
    company: Any = None,
    *,
    basePeriod: str | None = None,
    stockCode: str | None = None,
    lifeCyclePhase: str | None = None,
    sectorCode: str | None = None,
    limit: int = 5,
    skipIfScanMissing: bool = True,
) -> dict[str, Any]:
    """Possible Test — 유사 경로 기업 수집 (scan + KnowledgeDB insights).

    Phase 4 G15b: skipIfScanMissing=True 기본 — scan 프리빌드 (271MB) 미다운로드 시
    즉시 skip 반환. AI 대화 첫 호출에서 강제 다운로드로 인한 timeout 방지.

    Returns
    -------
    dict
        precedents : list[dict{stockCode, name, narrative, outcome, similarity}]
        count : int
        confidence : str — "low" | "mid" | "high"
        source : str — 데이터 경로 요약
    """
    # Phase 4 G15b: scan 프리빌드 없으면 강제 다운로드 회피 — AI timeout 방지
    if skipIfScanMissing:
        from pathlib import Path

        scan_path = Path("data/dart/scan/finance.parquet")
        if not scan_path.exists():
            return {
                "precedents": [],
                "count": 0,
                "confidence": "low",
                "source": "scan_not_downloaded",
                "hint": "`dartlab.downloadAll('scan')` 로 271MB 프리빌드 다운로드 후 재시도",
            }

    # company 객체에서 기본값 추출
    if company is not None:
        if stockCode is None:
            stockCode = getattr(company, "stockCode", None)
        if sectorCode is None:
            sec = getattr(company, "sector", None)
            if sec:
                sectorCode = getattr(sec, "code", None) or getattr(sec, "sector", None)
        if lifeCyclePhase is None:
            try:
                from dartlab.analysis.financial.lifeCycle import calcLifeCycle

                lc = calcLifeCycle(company, basePeriod=basePeriod)
                if lc:
                    lifeCyclePhase = lc.get("phase")
            except (ImportError, AttributeError, ValueError, TypeError):
                pass

    precedents: list[dict] = []
    sources: list[str] = []

    # 1. KnowledgeDB insights (블로그/과거 경험 실 추출)
    if sectorCode:
        try:
            from dartlab.ai.persistence.knowledge_db import KnowledgeDB

            db = KnowledgeDB()
            records = db.get_sector_insights(sectorCode, limit=limit)
            for rec in records:
                if rec.stockCode == stockCode:
                    continue  # 자기 자신 제외
                precedents.append(
                    {
                        "stockCode": rec.stockCode,
                        "name": rec.stockCode,
                        "narrative": (rec.narrative or "")[:200],
                        "outcome": None,
                        "similarity": None,
                        "strengths": rec.strengths[:3] if rec.strengths else [],
                        "weaknesses": rec.weaknesses[:3] if rec.weaknesses else [],
                        "source": rec.source,
                        "createdAt": rec.created_at,
                    }
                )
            if records:
                sources.append("knowledge_db")
        except (ImportError, AttributeError, OSError, ValueError):
            pass

    # 2. scan peer — 동일 lifeCyclePhase 기업 (phase 기반 precedent)
    if lifeCyclePhase and stockCode:
        try:
            phase_peers = _findPhaseMatchingPeers(stockCode, lifeCyclePhase, limit=limit)
            for p in phase_peers:
                precedents.append(p)
            if phase_peers:
                sources.append("scan_phase_match")
        except (ImportError, AttributeError, TypeError, ValueError, OSError):
            pass

    count = len(precedents)
    if count >= 5:
        confidence = "high"
    elif count >= 2:
        confidence = "mid"
    else:
        confidence = "low"

    return {
        "precedents": precedents[:limit],
        "count": count,
        "confidence": confidence,
        "source": ",".join(sources) if sources else "none",
    }


_PHASE_SIGNATURES = {
    "earlyGrowth": {"growthMin": 30, "marginMax": 5},
    "highGrowth": {"growthMin": 15, "growthMax": 35, "marginMin": 0},
    "matureGrowth": {"growthMin": 5, "growthMax": 20, "marginMin": 3},
    "matureStable": {"growthMax": 8, "marginMin": 5},
    "decline": {"growthMax": 0},
    "turnaround": {"growthMin": -5, "growthMax": 15, "marginMin": -5},
}


def _findPhaseMatchingPeers(stockCode: str, phase: str, *, limit: int = 5) -> list[dict]:
    """scan/finance.parquet 에서 같은 lifeCyclePhase signature 를 가진 기업 추출.

    완벽한 phase 계산은 무거우므로 growth/margin signature 로 근사.
    """
    sig = _PHASE_SIGNATURES.get(phase)
    if not sig:
        return []

    try:
        import importlib

        import polars as pl

        _h = importlib.import_module("dartlab.scan._helpers")
        _ensureScanData = _h._ensureScanData
        parseNumStr = _h.parseNumStr
    except ImportError:
        return []

    scan_dir = _ensureScanData()
    path = scan_dir / "finance.parquet"
    if not path.exists():
        return []

    try:
        lf = pl.scan_parquet(str(path))
        needed = [
            "stockCode",
            "bsns_year",
            "sj_div",
            "account_nm",
            "thstrm_amount",
            "frmtrm_amount",
            "fs_nm",
            "reprt_nm",
        ]
        avail = lf.collect_schema().names()
        cols = [c for c in needed if c in avail]
        snap = (
            lf.select(cols)
            .filter(pl.col("fs_nm").str.contains("연결"))
            .filter(pl.col("reprt_nm").str.contains("4분기"))
            .collect()
        )
    except (pl.exceptions.PolarsError, OSError):
        return []
    if snap.is_empty():
        return []

    years = sorted(snap["bsns_year"].unique().to_list(), reverse=True)
    if not years:
        return []
    cur = snap.filter(pl.col("bsns_year") == years[0])

    rev_nms = ["매출액", "수익(매출액)", "영업수익"]
    op_nms = ["영업이익", "영업이익(손실)"]

    matches: list[dict] = []
    for sc in cur["stockCode"].unique().to_list():
        if sc == stockCode:
            continue
        stock = cur.filter(pl.col("stockCode") == sc)
        if stock.is_empty():
            continue
        rev_cur = rev_prev = op_cur = None
        for nm in rev_nms:
            r = stock.filter(pl.col("account_nm") == nm)
            if not r.is_empty():
                rev_cur = parseNumStr(r["thstrm_amount"][0])
                if "frmtrm_amount" in r.columns:
                    rev_prev = parseNumStr(r["frmtrm_amount"][0])
                break
        for nm in op_nms:
            o = stock.filter(pl.col("account_nm") == nm)
            if not o.is_empty():
                op_cur = parseNumStr(o["thstrm_amount"][0])
                break
        if not (rev_cur and rev_prev and rev_prev > 0):
            continue
        yoy = (rev_cur - rev_prev) / rev_prev * 100
        margin = op_cur / rev_cur * 100 if (op_cur is not None and rev_cur > 0) else None

        if "growthMin" in sig and yoy < sig["growthMin"]:
            continue
        if "growthMax" in sig and yoy > sig["growthMax"]:
            continue
        if "marginMin" in sig and (margin is None or margin < sig["marginMin"]):
            continue
        if "marginMax" in sig and (margin is None or margin > sig["marginMax"]):
            continue

        matches.append(
            {
                "stockCode": sc,
                "name": sc,
                "narrative": f"YoY {yoy:.1f}%, 영업마진 {margin:.1f}%" if margin is not None else f"YoY {yoy:.1f}%",
                "outcome": None,
                "similarity": None,
                "source": "scan_phase_match",
            }
        )
        if len(matches) >= limit:
            break
    return matches


def calcPlausibilityBand(
    company: Any = None,
    *,
    basePeriod: str | None = None,
    stockCode: str | None = None,
    forecastAssumptions: dict[str, Any] | None = None,
    sectorCode: str | None = None,
) -> dict[str, Any]:
    """Plausible Test — 현재 forecast 가정이 섹터 피어 분포 어디에 위치하는지.

    Returns
    -------
    dict
        growthPercentile : float | None — 0.0~100.0
        marginPercentile : float | None
        band : str — "within" (p25~p75) | "stretch" (p75~p95) | "unrealistic" (>p95)
        peerStats : dict — {growthMedian, growthP75, growthP95, marginMedian, ...}
        source : str
    """
    if company is not None and stockCode is None:
        stockCode = getattr(company, "stockCode", None)
    if company is not None and sectorCode is None:
        sec = getattr(company, "sector", None)
        if sec:
            sectorCode = getattr(sec, "code", None) or getattr(sec, "sector", None)
    if forecastAssumptions is None:
        # company 에서 추론 시도 — growthTrend 최근 CAGR + 최근 마진
        forecastAssumptions = {}
        if company is not None:
            try:
                from dartlab.analysis.financial.growthAnalysis import calcGrowthTrend
                from dartlab.analysis.financial.profitability import calcMarginTrend

                g = calcGrowthTrend(company, basePeriod=basePeriod)
                m = calcMarginTrend(company, basePeriod=basePeriod)
                if g:
                    forecastAssumptions["growthRate"] = (g.get("cagr") or {}).get("revenue")
                if m and m.get("history"):
                    forecastAssumptions["operatingMargin"] = m["history"][0].get("operatingMargin")
            except (ImportError, AttributeError, ValueError, TypeError):
                pass

    growth = forecastAssumptions.get("growthRate") or forecastAssumptions.get("revenueGrowth")
    op_margin = forecastAssumptions.get("operatingMargin") or forecastAssumptions.get("opm")

    peer_growth: list[float] = []
    peer_margin: list[float] = []

    # scan/finance.parquet 직접 쿼리 → 전종목 매출 YoY + 영업마진 분포
    try:
        import importlib

        import polars as pl

        _h = importlib.import_module("dartlab.scan._helpers")
        _ensureScanData = _h._ensureScanData
        parseNumStr = _h.parseNumStr

        scan_dir = _ensureScanData()
        path = scan_dir / "finance.parquet"
        if path.exists():
            lf = pl.scan_parquet(str(path))
            needed = [
                "stockCode",
                "bsns_year",
                "sj_div",
                "account_nm",
                "thstrm_amount",
                "frmtrm_amount",
                "fs_nm",
                "reprt_nm",
            ]
            avail = lf.collect_schema().names()
            cols = [c for c in needed if c in avail]
            snap = (
                lf.select(cols)
                .filter(pl.col("fs_nm").str.contains("연결"))
                .filter(pl.col("reprt_nm").str.contains("4분기"))
                .collect()
            )
            if not snap.is_empty():
                years = sorted(snap["bsns_year"].unique().to_list(), reverse=True)
                if years:
                    cur = snap.filter(pl.col("bsns_year") == years[0])
                    rev_nms = ["매출액", "수익(매출액)", "영업수익"]
                    op_nms = ["영업이익", "영업이익(손실)"]
                    stockcodes = [s for s in cur["stockCode"].unique().to_list() if s is not None]
                    for sc in stockcodes[:500]:  # 샘플 500 (메모리 + 속도)
                        stock = cur.filter(pl.col("stockCode") == sc)
                        if stock.is_empty():
                            continue
                        # 매출 + 영업이익 현재기/전기 추출
                        rev_cur = rev_prev = op_cur = None
                        for nm in rev_nms:
                            r = stock.filter(pl.col("account_nm") == nm)
                            if not r.is_empty():
                                rev_cur = parseNumStr(r["thstrm_amount"][0])
                                if "frmtrm_amount" in r.columns:
                                    rev_prev = parseNumStr(r["frmtrm_amount"][0])
                                break
                        for nm in op_nms:
                            o = stock.filter(pl.col("account_nm") == nm)
                            if not o.is_empty():
                                op_cur = parseNumStr(o["thstrm_amount"][0])
                                break
                        # YoY
                        if rev_cur and rev_prev and rev_prev > 0:
                            yoy = (rev_cur - rev_prev) / rev_prev * 100
                            if -80 < yoy < 300:
                                peer_growth.append(float(yoy))
                        # Margin
                        if rev_cur and op_cur is not None and rev_cur > 0:
                            margin = op_cur / rev_cur * 100
                            if -100 < margin < 80:
                                peer_margin.append(float(margin))
    except (ImportError, AttributeError, TypeError, ValueError, OSError):
        pass

    def _percentile(series: list[float], value: float | None) -> float | None:
        """시리즈 내 값의 백분위 위치 산출 (0~100)."""
        if value is None or not series:
            return None
        below = sum(1 for x in series if x < value)
        return round(below / len(series) * 100, 1)

    def _quantile(series: list[float], q: float) -> float | None:
        """시리즈에서 q 분위수 값 추출."""
        if not series:
            return None
        sorted_s = sorted(series)
        idx = int(q * (len(sorted_s) - 1))
        return round(sorted_s[idx], 2)

    growth_pctile = _percentile(peer_growth, growth)
    margin_pctile = _percentile(peer_margin, op_margin)

    band = "within"
    if growth_pctile is not None:
        if growth_pctile > 95:
            band = "unrealistic"
        elif growth_pctile > 75:
            band = "stretch"

    return {
        "growthPercentile": growth_pctile,
        "marginPercentile": margin_pctile,
        "band": band,
        "peerStats": {
            "growthMedian": _quantile(peer_growth, 0.5),
            "growthP75": _quantile(peer_growth, 0.75),
            "growthP95": _quantile(peer_growth, 0.95),
            "marginMedian": _quantile(peer_margin, 0.5),
            "marginP75": _quantile(peer_margin, 0.75),
            "count": len(peer_growth),
        },
        "source": "scan_peer" if peer_growth else "none",
    }


def calcValuationSins(
    company: Any = None,
    *,
    basePeriod: str | None = None,
    valuation: dict[str, Any] | None = None,
    peerStats: dict[str, Any] | None = None,
    roicPct: float | None = None,
    waccPct: float | None = None,
    operatingMarginPct: float | None = None,
    country: str | None = None,
    currency: str | None = None,
) -> dict[str, Any]:
    """Probable Test — 경제·수학 첫 원칙 위반 규칙 순회.

    `consistency.calcCashFlowConsistency` 와 구별: consistency 는 **가정 간 매칭**,
    이쪽은 **경쟁 수렴 / 마진 상한 / 서사-숫자 갭 등 정성적 판단 규칙** 까지 포함.

    Returns
    -------
    dict
        flags : list[dict{key, severity, reason, suggestedRetry}]
        severity : str — 전체 최고 (info/warn/critical)
        count : int
    """
    from dartlab.analysis.valuation.consistency import calcCashFlowConsistency

    # company 에서 자동 추출
    if company is not None:
        if currency is None:
            currency = getattr(company, "currency", None)
        if valuation is None:
            try:
                from dartlab.analysis.valuation.dFV import calcDFV

                valuation = calcDFV(company, basePeriod=basePeriod)
            except (ImportError, AttributeError, ValueError, TypeError):
                pass
        if roicPct is None or operatingMarginPct is None:
            try:
                from dartlab.analysis.financial.investmentAnalysis import calcRoicTimeline
                from dartlab.analysis.financial.profitability import calcMarginTrend

                r = calcRoicTimeline(company, basePeriod=basePeriod)
                if r and r.get("history"):
                    roicPct = roicPct if roicPct is not None else r["history"][0].get("roic")
                    if waccPct is None:
                        waccPct = r["history"][0].get("waccEstimate")
                m = calcMarginTrend(company, basePeriod=basePeriod)
                if m and m.get("history"):
                    operatingMarginPct = (
                        operatingMarginPct if operatingMarginPct is not None else m["history"][0].get("operatingMargin")
                    )
            except (ImportError, AttributeError, ValueError, TypeError):
                pass

    # consistency 호출 (수학적 정합성은 거기서)
    consistency = calcCashFlowConsistency(
        valuation=valuation,
        roicPct=roicPct,
        waccPct=waccPct,
        country=country,
        currency=currency,
    )

    flags: list[dict] = []

    # consistency 결과를 flags 에 흡수
    for f in consistency.get("flags", []):
        flags.append(
            {
                "key": f.get("rule"),
                "severity": f.get("severity"),
                "reason": f.get("message"),
                "suggestedRetry": None,
            }
        )

    # 추가 규칙 — 경쟁 수렴 (ROIC > WACC × 3 지속 가정)
    if roicPct is not None and waccPct is not None and waccPct > 0:
        ratio = roicPct / waccPct
        if ratio > 3.0:
            flags.append(
                {
                    "key": "roic_wacc_persist",
                    "severity": "warn",
                    "reason": f"ROIC {roicPct:.1f}% / WACC {waccPct:.1f}% = {ratio:.1f}x — 장기 경쟁 수렴 가정 위반",
                    "suggestedRetry": {"terminalGrowth": 2.0},
                }
            )

    # 마진 상한 (peer p95 × 1.5 초과)
    if peerStats and operatingMarginPct is not None:
        p95 = peerStats.get("marginP75") or peerStats.get("marginMedian")
        if isinstance(p95, (int, float)) and p95 > 0 and operatingMarginPct > p95 * 1.5:
            flags.append(
                {
                    "key": "margin_ceiling",
                    "severity": "warn",
                    "reason": f"영업마진 {operatingMarginPct:.1f}% 가 업종 상위 기준치 {p95:.1f}% 의 1.5배 초과",
                    "suggestedRetry": None,
                }
            )

    # 스토리 ↔ 숫자 갭 (storyTemplate 없이 valuation 실행)
    if valuation and not valuation.get("companyType"):
        flags.append(
            {
                "key": "story_numbers_gap",
                "severity": "info",
                "reason": "기업유형 미판정 — 서사 없는 숫자, Damodaran 원칙 위반",
                "suggestedRetry": None,
            }
        )

    # Control + Synergy 이중계산 — Damodaran Dark Side Ch.17
    if valuation:
        cp = valuation.get("controlPremium") or (valuation.get("control") or {}).get("controlPremium")
        syn = valuation.get("synergy") or (valuation.get("synergy") or {}).get("synergy")
        sq = valuation.get("dFV") or valuation.get("statusQuoValue")
        if isinstance(cp, (int, float)) and isinstance(syn, (int, float)) and isinstance(sq, (int, float)) and sq > 0:
            if (cp + syn) > sq * 0.5:
                flags.append(
                    {
                        "key": "control_synergy_overlap",
                        "severity": "critical",
                        "reason": (
                            f"Control premium {cp:,.0f} + Synergy {syn:,.0f} = {cp + syn:,.0f}"
                            f" 이 standalone {sq:,.0f} × 50% 초과 — 이중계산 위험"
                        ),
                        "suggestedRetry": None,
                    }
                )

    severity = "info"
    order = {"info": 0, "warn": 1, "critical": 2}
    for f in flags:
        if order.get(f.get("severity", "info"), 0) > order.get(severity, 0):
            severity = f["severity"]

    return {
        "flags": flags,
        "severity": severity,
        "count": len(flags),
    }
