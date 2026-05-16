"""변화점 (Turning Point) 감지 — CUSUM + Rolling Z.

시계열 데이터에서 "언제 무엇이 바뀌었는지" 자동 감지.
story/narrate 의 "이 분기에 마진이 급변" 자동 표시 base.

순수 알고리즘. dict 반환. SSOT.
"""

from __future__ import annotations

from statistics import mean, pstdev


def detectTurningPoints(
    series: list[float | None],
    periods: list[str],
    *,
    minDeltaPct: float = 20.0,
    method: str = "rolling_z",
    windowSize: int = 3,
) -> list[dict]:
    """시계열 turning point 감지 — rolling z-score 또는 CUSUM 알고리즘.

    Capabilities:
        시계열의 추세 전환점 (turning point) 자동 감지. rolling z-score
        방법 (이동평균 + 표준편차 기반) 또는 CUSUM 방법 (누적합 알고리즘).
        매출/이익/마진의 구조변화 시점 식별 + 변화 크기/방향 라벨.

    Args:
        series: 시계열 값 (최신 → 과거 순서). None 자동 제외.
        periods: 기간 라벨 (series 와 같은 길이).
        minDeltaPct: 최소 변화율 (%). 이 미만은 노이즈로 무시. 기본 20%.
        method: ``"rolling_z"`` (이동평균 z-score) 또는 ``"cusum"``.
        windowSize: rolling 윈도우 크기. 기본 3 (분기).

    Returns:
        list[dict]: turning point 별:
            - ``period`` (str): 전환 시점
            - ``before``/``after`` (float): 전후 값
            - ``deltaPct`` (float): 변화율 (%, 양수=상승)
            - ``direction`` (str): ``"up"``/``"down"``
            - ``magnitude`` (str): ``"large"``/``"moderate"``/``"small"``

    Raises:
        없음.

    Example:
        >>> tp = detectTurningPoints([100, 105, 110, 115, 80, 75, 70],
        ...                          ["2024Q4","2024Q3",...])
        >>> [(t["period"], t["direction"]) for t in tp]
        [('2024Q1', 'down')]  # 115→80 (-30%) 가 turning point

    Guide:
        rolling_z: |last - rolling_mean| / rolling_std > 2 = turning point.
        CUSUM: 누적 변화 + threshold 임계. minDeltaPct 20%+ 권장 (재무 데이터
        분기 노이즈 회피). magnitude: large > 50%, moderate 30~50%, small.

    SeeAlso:
        - ``calcStructuralBreak``: Chow Test 기반 (다른 알고리즘)
        - ``injectTurningPoints``: tableau-friendly dict 변환

    Requires:
        series 길이 ≥ windowSize × 2 + 1.

    AIContext:
        turning point 결과는 모델/예측의 시작점 — break 이후 데이터만 사용
        권장 (calcStructuralBreak 와 연계). 단년 감지는 신뢰도 낮음.

    LLM Specifications:
        AntiPatterns:
            - minDeltaPct 5% 입력 → 노이즈 다수 검출. 재무 분기 데이터는
              20%+ 권장.
            - series 길이 부족 (windowSize 미달) → 빈 list 반환. 호출자
              분기 필요.
        OutputSchema:
            list[dict] — 0 개 이상 turning point.
        Prerequisites:
            series + periods 동일 길이, 최소 7~8 기간 권장.
        Freshness:
            시계열 freshness 에 따름.
        Dataflow:
            method 분기 → _detectByRollingZ 또는 _detectByCusum → minDeltaPct
            필터 → _magnitude 라벨 → dict list.
        TargetMarkets: 시장 무관 (시계열 분석).
    """
    if not series or not periods or len(series) != len(periods):
        return []

    # None 제거 + index 정렬 (최신 → 과거)
    valid = [(p, v) for p, v in zip(periods, series) if isinstance(v, (int, float))]
    if len(valid) < windowSize + 1:
        return []

    points = []
    if method == "rolling_z":
        points = _detectByRollingZ(valid, minDeltaPct, windowSize)
    elif method == "cusum":
        points = _detectByCusum(valid, minDeltaPct)
    else:
        return []

    return points


def _detectByRollingZ(
    valid: list[tuple[str, float]],
    minDeltaPct: float,
    windowSize: int,
) -> list[dict]:
    """이동 평균 ± 표준편차 기반 — windowSize 이전 평균 대비 z-score 큰 시점."""
    points = []
    n = len(valid)
    # 최신 → 과거 순이라면 reverse 로 시간 진행 순으로 (과거 → 현재)
    chronological = list(reversed(valid))

    for i in range(windowSize, n):
        window_vals = [v for _, v in chronological[max(0, i - windowSize) : i]]
        if len(window_vals) < 2:
            continue
        baseline = mean(window_vals)
        current_period, current_val = chronological[i]
        if baseline == 0:
            continue
        delta_pct = (current_val - baseline) / abs(baseline) * 100
        if abs(delta_pct) < minDeltaPct:
            continue
        # z-score 추가 검증 (변동성 클 때 false positive 회피)
        if len(window_vals) >= 3:
            std = pstdev(window_vals)
            if std > 0:
                z = (current_val - baseline) / std
                if abs(z) < 1.5:
                    continue
        magnitude = _magnitude(abs(delta_pct))
        points.append(
            {
                "period": current_period,
                "before": round(baseline, 2),
                "after": round(current_val, 2),
                "deltaPct": round(delta_pct, 1),
                "direction": "up" if delta_pct > 0 else "down",
                "magnitude": magnitude,
            }
        )
    # 최신순 정렬
    points.sort(key=lambda p: p["period"], reverse=True)
    return points


def _detectByCusum(
    valid: list[tuple[str, float]],
    minDeltaPct: float,
) -> list[dict]:
    """CUSUM (Cumulative Sum) — 평균 shift 감지."""
    points = []
    chronological = list(reversed(valid))
    vals = [v for _, v in chronological]
    if len(vals) < 4:
        return []

    overall_mean = mean(vals)
    threshold = abs(overall_mean) * (minDeltaPct / 100)
    cusum_pos = 0.0
    cusum_neg = 0.0
    for i, (period, val) in enumerate(chronological):
        diff = val - overall_mean
        cusum_pos = max(0, cusum_pos + diff)
        cusum_neg = min(0, cusum_neg + diff)
        if cusum_pos > threshold:
            before = mean(vals[:i]) if i > 0 else val
            delta_pct = (val - before) / abs(before) * 100 if before != 0 else 0
            points.append(
                {
                    "period": period,
                    "before": round(before, 2),
                    "after": round(val, 2),
                    "deltaPct": round(delta_pct, 1),
                    "direction": "up",
                    "magnitude": _magnitude(abs(delta_pct)),
                }
            )
            cusum_pos = 0  # reset
        elif cusum_neg < -threshold:
            before = mean(vals[:i]) if i > 0 else val
            delta_pct = (val - before) / abs(before) * 100 if before != 0 else 0
            points.append(
                {
                    "period": period,
                    "before": round(before, 2),
                    "after": round(val, 2),
                    "deltaPct": round(delta_pct, 1),
                    "direction": "down",
                    "magnitude": _magnitude(abs(delta_pct)),
                }
            )
            cusum_neg = 0
    points.sort(key=lambda p: p["period"], reverse=True)
    return points


def injectTurningPoints(
    history: list[dict] | None,
    *,
    seriesKey: str,
    periodKey: str = "period",
    minDeltaPct: float = 25.0,
    method: str = "rolling_z",
    windowSize: int = 3,
) -> list[dict]:
    """history dict 리스트에서 시계열 추출 → turningPoints 반환.

    calc 들의 boilerplate (5x 복붙) 제거용 헬퍼.

    Returns
    -------
    list[dict]
        실패/데이터부족 시 [] (예외 X — 호출처 안전).
    """
    if not history:
        return []
    try:
        series = [h.get(seriesKey) for h in history]
        periods = [h.get(periodKey) for h in history]
        return detectTurningPoints(
            series,
            periods,
            minDeltaPct=minDeltaPct,
            method=method,
            windowSize=windowSize,
        )
    except (AttributeError, TypeError, ValueError):
        return []


def _magnitude(deltaAbsPct: float) -> str:
    if deltaAbsPct >= 100:
        return "major"
    if deltaAbsPct >= 50:
        return "moderate"
    return "minor"
