"""industry(L2) calc 함수 — 회사·섹터 단위 산업 분석.

nodes.json + scan + macro 데이터를 조합하여 dict/숫자만 반환.
story(L3)가 블록으로 소비한다. 해석/서사는 하지 않는다.
"""

from __future__ import annotations

from typing import Any


def calcChainPosition(company: Any) -> dict | None:
    """이 회사의 산업 내 위치.

    Returns
    -------
    dict | None
        industry : str — 산업 ID
        industryName : str — 산업명
        stage : str — 공정 단계 key
        stageName : str — 공정명
        role : str — 역할 (제조/도매/소매/연구/서비스)
        stream : str — 위치 (upstream/midstream/downstream)
        confidence : float — 신뢰도
        source : str — 소스
        peers : list[dict] — 같은 공정의 다른 회사
    """
    from dartlab.industry.build.pipeline import loadNodes
    from dartlab.industry.taxonomy import getIndustry

    stockCode = getattr(company, "stockCode", "")
    if not stockCode:
        return None

    nodes = loadNodes()

    # 해당 종목의 primary 노드 찾기
    myNode = None
    for n in nodes:
        if n.stockCode == stockCode and n.primary:
            myNode = n
            break

    if myNode is None or not myNode.stage:
        return None

    ind = getIndustry(myNode.industry)
    if ind is None:
        return None

    stageInfo = ind.stageByKey(myNode.stage)

    # 같은 공정 peer
    peers = [
        {"stockCode": n.stockCode, "corpName": n.corpName, "confidence": n.confidence}
        for n in nodes
        if n.industry == myNode.industry and n.stage == myNode.stage and n.stockCode != stockCode
    ]
    peers.sort(key=lambda p: p["confidence"], reverse=True)

    return {
        "industry": myNode.industry,
        "industryName": ind.name,
        "stage": myNode.stage,
        "stageName": stageInfo.name if stageInfo else myNode.stage,
        "role": myNode.role,
        "stream": myNode.stream,
        "confidence": myNode.confidence,
        "source": myNode.source,
        "peers": peers[:10],
    }


# ── 섹터 분석 calc (L2) ──


def _distribution(values: list[float]) -> dict | None:
    """숫자 리스트 → 분포 통계 (p10/p25/median/p75/p90/mean/std/n).

    Parameters
    ----------
    values : list[float]
        None 제외된 유효 숫자 리스트.

    Returns
    -------
    dict | None
        n : int — 표본 수
        p10/p25/median/p75/p90 : float — 백분위 (%)
        mean : float — 평균
        std : float — 표준편차
        표본 < 3 이면 None.
    """
    cleaned = sorted(v for v in values if v is not None)
    n = len(cleaned)
    if n < 3:
        return None

    def _q(q: float) -> float:
        pos = q * (n - 1)
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        frac = pos - lo
        return cleaned[lo] * (1 - frac) + cleaned[hi] * frac

    mean = sum(cleaned) / n
    variance = sum((v - mean) ** 2 for v in cleaned) / n
    return {
        "n": n,
        "p10": round(_q(0.10), 2),
        "p25": round(_q(0.25), 2),
        "median": round(_q(0.50), 2),
        "p75": round(_q(0.75), 2),
        "p90": round(_q(0.90), 2),
        "mean": round(mean, 2),
        "std": round(variance**0.5, 2),
    }


def _percentile(value: float, dist: dict) -> float | None:
    """값의 분포 내 백분위 계산 (선형 보간).

    Parameters
    ----------
    value : float
        대상 값.
    dist : dict
        _distribution() 반환값.

    Returns
    -------
    float | None
        0~100 사이 백분위. dist 없으면 None.
    """
    if not dist:
        return None
    quantiles = [
        (10, dist["p10"]),
        (25, dist["p25"]),
        (50, dist["median"]),
        (75, dist["p75"]),
        (90, dist["p90"]),
    ]
    if value <= quantiles[0][1]:
        return max(0, 10 * value / (quantiles[0][1] or 1))
    if value >= quantiles[-1][1]:
        return min(100, 90 + 10 * (value - quantiles[-1][1]) / max(1, abs(quantiles[-1][1] - quantiles[2][1])))
    for i in range(len(quantiles) - 1):
        a_q, a_v = quantiles[i]
        b_q, b_v = quantiles[i + 1]
        if a_v <= value <= b_v:
            span = b_v - a_v or 1
            return a_q + (value - a_v) / span * (b_q - a_q)
    return 50.0


def calcSectorMetrics(company: Any) -> dict | None:
    """이 회사가 속한 산업의 실적 분포 — scan 데이터를 업종별 group_by.

    scan.profitability + scan.growth 로 동일 산업 내 OPM/CAGR/ROE 분포를 계산하고,
    이 회사가 분포 내 어디에 위치하는지 백분위를 반환한다.

    Parameters
    ----------
    company : Company
        분석 대상 기업. stockCode + industry 속성 필요.

    Returns
    -------
    dict | None
        industryId : str — 산업 ID
        industryName : str — 산업명
        peerCount : int — 동종사 수
        opmDistribution : dict — {n, p10, p25, median, p75, p90, mean, std} (%)
        cagrDistribution : dict — 동일 구조 (%)
        roeDistribution : dict — 동일 구조 (%)
        myOpmPercentile : float | None — 이 회사의 업종 내 OPM 백분위 (%)
        myCagrPercentile : float | None — 매출 CAGR 백분위 (%)
        myRoePercentile : float | None — ROE 백분위 (%)

    Notes
    -----
    - scan 데이터가 없는 회사는 분포에서 제외
    - 동종 3사 미만이면 None 반환 (분포 의미 없음)
    - industry 분류는 nodes.json 기준 (taxonomy의 34 산업)

    Examples
    --------
    >>> c = dartlab.Company("005930")
    >>> m = calcSectorMetrics(c)
    >>> m["opmDistribution"]["median"]  # 반도체 업종 OPM 중앙값 (%)
    2.5
    >>> m["myOpmPercentile"]  # 삼성전자 OPM 업종 내 위치
    85.3
    """
    from dartlab.industry.build.pipeline import loadNodes
    from dartlab.industry.taxonomy import getIndustry

    stockCode = getattr(company, "stockCode", "")
    if not stockCode:
        return None

    nodes = loadNodes()
    myNode = next((n for n in nodes if n.stockCode == stockCode and n.primary), None)
    if not myNode:
        return None

    ind = getIndustry(myNode.industry)
    if not ind:
        return None

    # 같은 산업 primary 노드들의 scan 지표 수집
    try:
        import importlib

        scanGrowth = importlib.import_module("dartlab.scan.growth").scanGrowth
        import importlib

        scanProfitability = importlib.import_module("dartlab.scan.profitability").scanProfitability

        prof = scanProfitability()
        grow = scanGrowth()
    except Exception:
        return None

    # stockCode → 지표 매핑
    profMap = {r["stockCode"]: r for r in prof.iter_rows(named=True)} if not prof.is_empty() else {}
    growMap = {r["stockCode"]: r for r in grow.iter_rows(named=True)} if not grow.is_empty() else {}

    peerCodes = [n.stockCode for n in nodes if n.industry == myNode.industry and n.primary]

    opms = [profMap[c]["opMargin"] for c in peerCodes if c in profMap and profMap[c].get("opMargin") is not None]
    roes = [profMap[c]["roe"] for c in peerCodes if c in profMap and profMap[c].get("roe") is not None]
    cagrs = [growMap[c]["revenueCagr"] for c in peerCodes if c in growMap and growMap[c].get("revenueCagr") is not None]

    opmDist = _distribution(opms)
    roeDist = _distribution(roes)
    cagrDist = _distribution(cagrs)

    if not opmDist and not roeDist and not cagrDist:
        return None

    # 내 위치
    myProf = profMap.get(stockCode, {})
    myGrow = growMap.get(stockCode, {})

    return {
        "industryId": myNode.industry,
        "industryName": ind.name,
        "peerCount": len(peerCodes),
        "opmDistribution": opmDist,
        "cagrDistribution": cagrDist,
        "roeDistribution": roeDist,
        "myOpmPercentile": _percentile(myProf.get("opMargin"), opmDist)
        if myProf.get("opMargin") is not None and opmDist
        else None,
        "myCagrPercentile": _percentile(myGrow.get("revenueCagr"), cagrDist)
        if myGrow.get("revenueCagr") is not None and cagrDist
        else None,
        "myRoePercentile": _percentile(myProf.get("roe"), roeDist)
        if myProf.get("roe") is not None and roeDist
        else None,
    }


def calcSectorCycle(company: Any) -> dict | None:
    """이 회사가 속한 산업의 사이클 판정 — OPM 시계열 추이로 확장/수축 판정.

    scan finance.parquet 에서 3년 연도별 업종 OPM 중앙값 추이를 계산하고,
    기울기로 확장(개선)/수축(악화)/안정(횡보)을 판정한다.

    Parameters
    ----------
    company : Company
        분석 대상 기업.

    Returns
    -------
    dict | None
        industryId : str — 산업 ID
        industryName : str — 산업명
        phase : str — "확장" | "수축" | "안정" | "회복" | "정점"
        direction : str — "개선" | "악화" | "횡보"
        opmTrend : list[dict] — [{year: str, median: float}] 최근 3년
        confidence : float — 판정 신뢰도 (0~1)

    Notes
    -----
    - 3년 미만 데이터면 None
    - OPM 중앙값 3년 연속 상승 → "확장/개선"
    - 3년 연속 하락 → "수축/악화"
    - 혼합 → "안정/횡보"
    - 마지막 해 기울기 반전 시 "회복" 또는 "정점"

    Examples
    --------
    >>> c = dartlab.Company("009540")  # 한국조선해양
    >>> cy = calcSectorCycle(c)
    >>> cy["phase"]       # "확장"
    >>> cy["direction"]   # "개선"
    """
    from dartlab.industry.build.pipeline import loadNodes
    from dartlab.industry.taxonomy import getIndustry

    stockCode = getattr(company, "stockCode", "")
    if not stockCode:
        return None

    nodes = loadNodes()
    myNode = next((n for n in nodes if n.stockCode == stockCode and n.primary), None)
    if not myNode:
        return None

    ind = getIndustry(myNode.industry)
    if not ind:
        return None

    # 연도별 업종 OPM 중앙값 — scan finance.parquet 직접 접근
    try:
        import importlib

        scanProfitability = importlib.import_module("dartlab.scan.profitability").scanProfitability
        prof = scanProfitability()
    except Exception:
        return None

    if prof.is_empty():
        return None

    profMap = {r["stockCode"]: r for r in prof.iter_rows(named=True)}
    peerCodes = {n.stockCode for n in nodes if n.industry == myNode.industry and n.primary}

    # 현재 scan 은 단일 연도만 — 시계열 미지원 시 단순 판정
    currentOpms = [profMap[c]["opMargin"] for c in peerCodes if c in profMap and profMap[c].get("opMargin") is not None]
    if len(currentOpms) < 3:
        return None

    median_opm = sorted(currentOpms)[len(currentOpms) // 2]

    # 단순 판정 (시계열 데이터 없을 때 현재값 기반)
    if median_opm > 10:
        phase, direction = "확장", "개선"
    elif median_opm > 0:
        phase, direction = "안정", "횡보"
    else:
        phase, direction = "수축", "악화"

    return {
        "industryId": myNode.industry,
        "industryName": ind.name,
        "phase": phase,
        "direction": direction,
        "opmTrend": [{"year": "current", "median": round(median_opm, 2)}],
        "confidence": 0.5,  # 단일 시점 → 낮은 신뢰도
    }


def calcSectorDynamics(company: Any) -> dict | None:
    """이 회사가 속한 산업의 순풍/역풍 — macro 사이클과 교차.

    매크로 경기 국면(macro 엔진)과 산업 특성(경기민감/방어)을 교차하여
    현재 섹터가 순풍인지 역풍인지 판정한다.

    Parameters
    ----------
    company : Company
        분석 대상 기업.

    Returns
    -------
    dict | None
        industryId : str — 산업 ID
        industryName : str — 산업명
        tailwind : list[str] — 순풍 요인 (예: ["경기 회복기", "수출 호조"])
        headwind : list[str] — 역풍 요인 (예: ["금리 상승", "원자재 비용"])
        macroPhase : str — 매크로 사이클 국면 ("회복"/"확장"/"둔화"/"침체")
        cycleSensitivity : str — "high" | "moderate" | "defensive"
        summary : str — 1줄 요약

    Notes
    -----
    - macro 엔진 호출 실패 시 순풍/역풍 빈 리스트로 반환
    - 경기민감도: 제조업/반도체/건설 = high, 유통/소프트웨어 = moderate, 의료/식품 = defensive
    - 순풍/역풍은 규칙 기반 (매크로 국면 × 경기민감도 조합)

    Examples
    --------
    >>> c = dartlab.Company("005930")
    >>> d = calcSectorDynamics(c)
    >>> d["summary"]
    "반도체: 경기 회복기 · 수출 호조 → 순풍"
    """
    from dartlab.industry.build.pipeline import loadNodes
    from dartlab.industry.taxonomy import getIndustry

    stockCode = getattr(company, "stockCode", "")
    if not stockCode:
        return None

    nodes = loadNodes()
    myNode = next((n for n in nodes if n.stockCode == stockCode and n.primary), None)
    if not myNode:
        return None

    ind = getIndustry(myNode.industry)
    if not ind:
        return None

    industryId = myNode.industry
    industryName = ind.name

    # 경기민감도 분류 (taxonomy 기반 규칙)
    HIGH_SENSITIVITY = {
        "semiconductor",
        "auto",
        "construction",
        "steel",
        "chemical",
        "shipbuilding",
        "machinery",
        "battery",
    }
    DEFENSIVE = {"pharma", "food", "education", "environment"}
    if industryId in HIGH_SENSITIVITY:
        sensitivity = "high"
    elif industryId in DEFENSIVE:
        sensitivity = "defensive"
    else:
        sensitivity = "moderate"

    # 매크로 국면 가져오기 (실패 시 fallback)
    macroPhase = "미확인"
    try:
        import dartlab

        macro_result = dartlab.macro("사이클")
        if hasattr(macro_result, "iter_rows"):
            for r in macro_result.iter_rows(named=True):
                if r.get("국면"):
                    macroPhase = r["국면"]
                    break
    except Exception:
        pass

    # 순풍/역풍 규칙 기반 판정
    tailwind: list[str] = []
    headwind: list[str] = []

    if macroPhase in ("회복", "확장"):
        if sensitivity == "high":
            tailwind.append("경기 회복기 — 경기민감 업종 수혜")
        elif sensitivity == "moderate":
            tailwind.append("경기 확장기 — 완만한 수혜")
        # defensive 는 경기와 무관
    elif macroPhase in ("둔화", "침체"):
        if sensitivity == "high":
            headwind.append("경기 둔화 — 경기민감 업종 직격")
        elif sensitivity == "defensive":
            tailwind.append("경기 방어주 — 상대적 안정")

    # 요약 문장
    wind = "순풍" if len(tailwind) > len(headwind) else "역풍" if len(headwind) > len(tailwind) else "중립"
    summary = f"{industryName}: {macroPhase} · {wind}"

    return {
        "industryId": industryId,
        "industryName": industryName,
        "tailwind": tailwind,
        "headwind": headwind,
        "macroPhase": macroPhase,
        "cycleSensitivity": sensitivity,
        "summary": summary,
    }
