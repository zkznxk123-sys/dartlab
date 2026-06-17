"""산업 양극화 — 마진분산(제출재무) × 밸류분산(시장가치) 교차검증.

산업이 *승자독식으로 갈라지나(polarization) vs 동질 평준화* 를 **독립 두 자료원**으로 교차검증한다.
- 마진 렌즈: 산업내 영업이익률(OPM) 횡단 분산(IQR) 의 다년 방향 — 회사가 *버는 것* 의 갈림.
- 밸류 렌즈: 산업내 P/B 횡단 분산(p90/p10) — 시장이 *값매기는 것* 의 갈림.
두 렌즈가 일치(둘 다 넓음/좁음)하면 강건 — 단일 각도 folk통계 방어. 패널(전수·다년·1차자료)만 답.

졸업 근거: ``tests/_attempts/industryAnalysisLab/`` 전수 발굴 — 9 루트 중 마진분산(루트1, 발산 8:2)·
밸류괴리(루트3, 발산 3.3x) 둘이 robust PASS + 서로 교차검증(제약이 양 렌즈 극단 일치). measure-first.
"""

from __future__ import annotations

from typing import Any

# 관측 기반 임계(tests/_attempts/industryAnalysisLab/ROUTES.md 실측 분포) — 절대 진리 아닌 라벨 경계.
_MARGIN_WIDE = 15.0  # 끝해 OPM IQR(%p) > 15 = 넓음 (반도체 27·제약 78 high vs 철강 4.5·식품 low)
_MARGIN_NARROW = 8.0  # < 8 = 좁음
_VALUE_WIDE = 8.0  # P/B p90/p10 > 8 = 넓음 (제약 22.6·기계 22.3 vs 식품 6.9)
_VALUE_NARROW = 4.0  # < 4 = 좁음

_SURVIVOR_NOTE = "현재 산업 멤버십을 과거 연도에 소급 적용 — 과거 진입·퇴출 기업 미반영(복원 불가)"


def calcPolarization(industryId: str, *, years: list[str] | None = None) -> dict:
    """산업 양극화 — 마진분산(재무)·밸류분산(시장) 두 렌즈 교차검증으로 승자독식 vs 평준화 판정.

    Capabilities:
        한 산업의 횡단 분산을 **독립 두 자료원**으로 측정해 교차검증한다. ① 마진 렌즈 = 멤버
        영업이익률(OPM) 의 연도별 IQR(p75−p25) 첫해→끝해 방향(확대/축소) + 끝해 레벨. ② 밸류
        렌즈 = 멤버 P/B(시총/자본) 의 p90/p10 분산(스냅샷). 둘 다 "넓음"이면 *승자독식 심화*,
        둘 다 "좁음"이면 *동질 평준화*, 갈리면 *혼재(교차검증 불일치)*. 음수자본·n<3 정직 제외.

    Parameters
    ----------
    industryId : str
        산업 ID (taxonomy key).
    years : list[str] | None
        마진 렌즈 대상 연도. None 이면 finance.parquet 실효 윈도(2021+) 자동. 결손 연도는
        ``_distribution`` n<3 가드로 제외.

    Returns
    -------
    dict
        산업 : str — industryId
        판정 : str — "승자독식 심화" | "동질 평준화" | "혼재" | "데이터부족"
        교차검증 : str — "일치" | "불일치(렌즈 갈림)" | "불가(한 렌즈 결손)"
        마진 : dict — {첫해IQR(%p), 끝해IQR(%p), 방향, 레벨, n, 윈도}  (밸류는 levels·스냅샷)
        밸류 : dict — {p90p10, 중앙PB, 레벨, n, 음수자본제외}
        생존편향주의 : str — 현 멤버십 과거 소급 한계 고정 경고

    Raises
    ------
    없음 — 데이터 없으면 판정 "데이터부족" + 빈 렌즈.

    Example
    -------
    >>> from dartlab.industry.calcs.polarization import calcPolarization
    >>> r = calcPolarization("pharma")  # 제약 = 마진 IQR 33→78 확대 + P/B p90/p10 22.6 넓음
    >>> r["판정"], r["교차검증"]
    ('승자독식 심화', '일치')

    Guide
    -----
    두 렌즈가 *서로 다른 자료원*(제출재무 ↔ 시장가치)인 게 핵심 — 일치하면 한 자료원 인공물이
    아니라는 강건 신호. 불일치면 "재무는 갈리는데 시장은 균등 평가" 식의 *불일치 자체가 통찰*.
    5점 윈도라 마진 방향은 "추세" 아닌 *방향 신호*. 밸류는 단일 스냅샷(시점 1).

    SeeAlso
    -------
    - ``dartlab.industry.calcs.concentration.calcIndustryConcentration`` : 시장구조 집중도(HHI) 형제
    - ``dartlab.industry.calcs.companyCalcs._distribution`` : 본 모듈이 재사용하는 분포 헬퍼

    Requires
    --------
    - L1.5 scan: finance.parquet (operatingMargin·total_stockholders_equity)
    - L1 gather: gov prices (MKTCAP, 최신 연도 스냅샷)
    - taxonomy + nodes.json

    AIContext
    ---------
    "이 산업은 승자독식으로 갈라지나 / 회사 간 격차가 벌어지나" 답변. **교차검증 결과(일치/불일치)를
    반드시 인용** — 일치면 강건, 불일치면 재무·시장 괴리를 단서로. 음수자본 제외수·생존편향·5점
    윈도(방향신호)·밸류 스냅샷(시점 1)을 evidence 로 동반. 점유율·인과 주장 금지.

    When:
        산업 양극화/격차/승자독식 질문. 단일 회사 위치는 ``Company().industry()``, 집중도는
        ``Industry()(id, concentration=True)``.

    How:
        멤버 OPM 연도루프 ``_distribution`` → IQR 첫/끝해 + 방향 → 멤버 P/B ``_distribution`` →
        p90/p10 → 두 렌즈 레벨 교차 판정. 임계는 _attempts 실측 분포 기반 라벨 경계.

    See Also:
        - ``dartlab.industry.calcs.concentration.calcIndustryConcentration`` : 형제(집중도)
        - ``dartlab.industry.calcs.profitPoolDynamics.calcProfitPoolDynamics`` : 형제(이익 동학)
    """
    import polars as pl

    from dartlab.gather.bulkData.hfBulk import loadFiltered
    from dartlab.industry.build.pipeline import loadNodes
    from dartlab.industry.calcs.companyCalcs import _distribution
    from dartlab.providers.dart.finance.scanAccount import scanAccount
    from dartlab.providers.dart.finance.scanRatio import scanRatio

    empty: dict = {
        "산업": industryId,
        "판정": "데이터부족",
        "교차검증": "불가(한 렌즈 결손)",
        "마진": {},
        "밸류": {},
        "생존편향주의": _SURVIVOR_NOTE,
    }

    nodes = loadNodes()
    codes = {n.stockCode for n in nodes if n.primary and n.industry == industryId}
    if not codes:
        return empty

    # ── 마진 렌즈: OPM 연도별 IQR(p75−p25) 첫해→끝해 방향 ──
    opm = scanRatio("operatingMargin", freq="Y")
    yearCols = [c for c in sorted(opm.columns) if c.isdigit() and c >= "2021"]
    if years:
        yearCols = [y for y in yearCols if y in years]
    opmMap = {r["stockCode"]: r for r in opm.iter_rows(named=True)}

    marginLens: dict = {}
    iqrByYear: list[tuple[str, float, int]] = []  # (연도, IQR, n)
    for y in yearCols:
        vals = [opmMap[c][y] for c in codes if c in opmMap and opmMap[c].get(y) is not None]
        dist = _distribution(vals)
        if dist:
            iqrByYear.append((y, round(dist["p75"] - dist["p25"], 2), dist["n"]))
    if len(iqrByYear) >= 2:
        firstY, firstIqr, _ = iqrByYear[0]
        lastY, lastIqr, lastN = iqrByYear[-1]
        direction = "확대" if lastIqr > firstIqr else "축소"
        level = "넓음" if lastIqr > _MARGIN_WIDE else ("좁음" if lastIqr < _MARGIN_NARROW else "보통")
        marginLens = {
            "첫해IQR(%p)": firstIqr,
            "끝해IQR(%p)": lastIqr,
            "방향": direction,
            "레벨": level,
            "n": lastN,
            "윈도": f"{firstY}~{lastY}",
        }

    # ── 밸류 렌즈: 최신 시총 ⨝ 최신 자본 → P/B 분포 p90/p10 (스냅샷) ──
    priceYear = int(iqrByYear[-1][0]) if iqrByYear else 2025
    valueLens: dict = {}
    try:
        px = loadFiltered(year=priceYear, adjustment="raw")
        if not px.is_empty():
            latest = (
                px.filter(pl.col("MKTCAP").is_not_null() & (pl.col("MKTCAP") > 0))
                .sort("BAS_DD")
                .group_by("ISU_CD")
                .last()
                .select(["ISU_CD", "MKTCAP"])
            )
            mcap = {r["ISU_CD"]: r["MKTCAP"] for r in latest.iter_rows(named=True)}

            eq = scanAccount("total_stockholders_equity", freq="Y")
            eqYears = [c for c in sorted(eq.columns) if c.isdigit() and c >= "2021"]
            eqMap: dict[str, float] = {}
            for r in eq.iter_rows(named=True):
                for y in reversed(eqYears):  # 최신 자본 우선
                    if r.get(y) is not None:
                        eqMap[r["stockCode"]] = r[y]
                        break

            pb, negEq = [], 0
            for c in codes:
                m, e = mcap.get(c), eqMap.get(c)
                if m is None or e is None:
                    continue
                if e <= 0:  # 음수자본 제외 + 제외수 인용
                    negEq += 1
                    continue
                pb.append(m / e)
            dist = _distribution(pb)
            if dist and dist["p10"] > 0:
                spread = round(dist["p90"] / dist["p10"], 1)
                vlevel = "넓음" if spread > _VALUE_WIDE else ("좁음" if spread < _VALUE_NARROW else "보통")
                valueLens = {
                    "p90p10": spread,
                    "중앙PB": dist["median"],
                    "레벨": vlevel,
                    "n": dist["n"],
                    "음수자본제외": negEq,
                }
    except Exception:  # noqa: BLE001 — 가격 데이터 결손은 밸류 렌즈만 비우고 진행(마진 렌즈 보존)
        valueLens = {}

    # ── 교차검증 판정 ──
    verdict, crossCheck = _crossVerdict(marginLens, valueLens)
    return {
        "산업": industryId,
        "판정": verdict,
        "교차검증": crossCheck,
        "마진": marginLens,
        "밸류": valueLens,
        "생존편향주의": _SURVIVOR_NOTE,
    }


def _crossVerdict(marginLens: dict, valueLens: dict) -> tuple[str, str]:
    """두 렌즈 레벨을 교차해 양극화 판정·교차검증 라벨 산출 (둘 다 있어야 일치/불일치 판정)."""
    mLevel = marginLens.get("레벨")
    vLevel = valueLens.get("레벨")
    if mLevel is None or vLevel is None:
        present = marginLens or valueLens
        if not present:
            return "데이터부족", "불가(한 렌즈 결손)"
        # 한 렌즈만 — 그 렌즈 단독 판정(교차검증은 불가 명시)
        solo = mLevel or vLevel
        single = "승자독식 심화" if solo == "넓음" else ("동질 평준화" if solo == "좁음" else "혼재")
        return single, "불가(한 렌즈 결손)"
    if mLevel == "넓음" and vLevel == "넓음":
        return "승자독식 심화", "일치"
    if mLevel == "좁음" and vLevel == "좁음":
        return "동질 평준화", "일치"
    if {mLevel, vLevel} == {"넓음", "좁음"}:
        return "혼재", "불일치(렌즈 갈림)"
    return "혼재", "일치"  # 한쪽 보통 — 약한 동조


def _polarizationDataFrame(industryId: str, *, years: list[str] | None = None) -> Any:
    """``calcPolarization`` (dict) → 표면 계약(DataFrame). 2행 two-lens 표(마진·밸류 나란히)로 교차검증 가시화."""
    import polars as pl

    r = calcPolarization(industryId, years=years)
    schema = {
        "렌즈": pl.Utf8,
        "분산지표": pl.Utf8,
        "첫해값": pl.Float64,
        "끝해값": pl.Float64,
        "방향레벨": pl.Utf8,
        "n": pl.Int64,
        "음수자본제외": pl.Int64,
        "양극화판정": pl.Utf8,
        "교차검증": pl.Utf8,
        "윈도": pl.Utf8,
        "생존편향주의": pl.Utf8,
    }
    m, v = r.get("마진") or {}, r.get("밸류") or {}
    if not m and not v:
        return pl.DataFrame(schema=schema)

    rows = []
    if m:
        rows.append(
            {
                "렌즈": "마진(제출재무)",
                "분산지표": "OPM IQR(%p)",
                "첫해값": m.get("첫해IQR(%p)"),
                "끝해값": m.get("끝해IQR(%p)"),
                "방향레벨": f"{m.get('방향')}/{m.get('레벨')}",
                "n": m.get("n"),
                "음수자본제외": None,
                "양극화판정": r["판정"],
                "교차검증": r["교차검증"],
                "윈도": m.get("윈도"),
                "생존편향주의": r["생존편향주의"],
            }
        )
    if v:
        rows.append(
            {
                "렌즈": "밸류(시장가치)",
                "분산지표": "P/B p90/p10",
                "첫해값": None,  # 스냅샷(시점 1) — 첫해 없음
                "끝해값": v.get("p90p10"),
                "방향레벨": v.get("레벨"),
                "n": v.get("n"),
                "음수자본제외": v.get("음수자본제외"),
                "양극화판정": r["판정"],
                "교차검증": r["교차검증"],
                "윈도": m.get("윈도") or "스냅샷",
                "생존편향주의": r["생존편향주의"],
            }
        )
    return pl.DataFrame(rows, schema=schema)
