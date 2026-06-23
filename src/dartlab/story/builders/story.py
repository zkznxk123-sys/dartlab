"""story 블록 빌더 — story 도메인 (debt-honesty P3-3 god-split). 공유 imports·상수·헬퍼는 _shared."""

from __future__ import annotations

from dartlab.story.builders._shared import (
    _STREAM_LABEL,
    FlagBlock,
    HeadingBlock,
    MetricBlock,
    TableBlock,
    TextBlock,
    _enrichedFlagsBlock,
    _flagsBlock,
    _meta,
    narrateStoryPrecedents,
    pl,
)


def criticalAssumptionsBlock(data: dict | None) -> list:
    """calcScenarioSensitivity 결과 → 핵심 가정 목록."""
    if not data:
        return []
    assumptions = data.get("criticalAssumptions", [])
    if not assumptions:
        return []

    return [
        HeadingBlock(
            _meta("criticalAssumptions").label,
            level=2,
            helper="이 보고서의 결론을 지탱하는 가정. 하나라도 무너지면 재평가 필요.",
        ),
        TextBlock("\n".join(f"- {a}" for a in assumptions)),
    ]


def stabilityFlagsBlock(data) -> list:
    """calcStabilityFlags 결과 → FlagBlock."""
    if isinstance(data, dict):
        return _enrichedFlagsBlock(data.get("flags", []), data.get("enrichedFlags"))
    flags = data if isinstance(data, list) else []
    return _flagsBlock(flags)


def sectorKpiBlock(data: dict | None) -> list:
    """sectorKpi 결과 → 업종별 KPI 블록. 업종에 따라 다른 내용."""
    if not data:
        return []
    sector = data.get("sector", "")
    kpis = data.get("kpis", {})
    if not kpis:
        return []

    sector_labels = {"construction": "건설", "semiconductor": "반도체", "gaming": "게임·엔터", "pharma": "제약·바이오"}

    blocks: list = [
        HeadingBlock(
            f"업종 특수 KPI ({sector_labels.get(sector, sector)})",
            level=2,
            helper="범용 14축에 없는 이 업종만의 핵심 지표",
        ),
    ]

    from dartlab.story.narrate import narrateSectorContext

    context = narrateSectorContext(sector, kpis)
    if context:
        blocks.append(TextBlock(context))

    for key, val in kpis.items():
        if not val or not isinstance(val, dict):
            continue

        # 공통 패턴: history가 있으면 표, 아니면 metric
        history = val.get("history", [])
        if history and isinstance(history, list) and len(history) > 0 and isinstance(history[0], dict):
            cols_dict: dict[str, list] = {}
            for h in history:
                for k, v in h.items():
                    if k == "period":
                        continue
                    if k not in cols_dict:
                        cols_dict[k] = []
                    cols_dict[k].append(str(v) if v is not None else "-")
            if cols_dict:
                periods_list = [str(h.get("period", "")) for h in history]
                rows = [{"": k, **dict(zip(periods_list, vals))} for k, vals in cols_dict.items()]
                if rows:
                    blocks.append(TableBlock(key, pl.DataFrame(rows)))

        # simple metrics
        metrics = []
        for k, v in val.items():
            if k in ("history", "note", "products"):
                continue
            if isinstance(v, (int, float)):
                metrics.append((k, f"{v:.1f}" if isinstance(v, float) else str(v)))
            elif isinstance(v, str) and v:
                metrics.append((k, v))
        if metrics:
            blocks.append(MetricBlock(metrics[:8]))

        # note
        note = val.get("note")
        if note:
            blocks.append(TextBlock(f"_{note}_"))

    return blocks


# ── 개선 시나리오 (How축) ──


def improvementLeversBlock(data: dict | None) -> list:
    """calcImprovementLevers 결과 → 개선 레버 순위 + narrate."""
    if not data:
        return []
    levers = data.get("levers", [])
    if not levers:
        return []

    from dartlab.story.narrate import narrateImprovementLevers

    blocks: list = [
        HeadingBlock(_meta("improvementLevers").label, level=2, helper="영향도 순 개선 경로 — 가장 효과 큰 것부터")
    ]

    narration = narrateImprovementLevers(data)
    if narration:
        blocks.append(TextBlock(narration))

    rows = []
    for lv in levers[:5]:
        row: dict = {"레버": lv["name"], "난이도": lv.get("difficulty", ""), "기간": lv.get("timeframe", "")}
        impact = lv.get("impact", {})
        if impact.get("opm") is not None:
            row["OPM"] = f"{impact['opm']:.1f}%"
        if impact.get("roe") is not None:
            row["ROE"] = f"{impact['roe']:.1f}%"
        if impact.get("fcf_change_pct") is not None:
            row["FCF 변화"] = f"{impact['fcf_change_pct']:+.0f}%"
        if impact.get("interestCoverage") is not None:
            row["이자보상"] = f"{impact['interestCoverage']:.1f}x"
        rows.append(row)

    if rows:
        blocks.append(TableBlock("개선 레버 영향도", pl.DataFrame(rows)))
    return blocks


def gradeUpgradePathBlock(data: dict | None) -> list:
    """calcGradeImprovement 결과 → 신용등급 상향 경로."""
    if not data:
        return []

    from dartlab.story.narrate import narrateGradeUpgrade

    blocks: list = [
        HeadingBlock(_meta("gradeUpgradePath").label, level=2, helper="dCR 한 노치 상향에 필요한 구체적 변화")
    ]

    narration = narrateGradeUpgrade(data)
    if narration:
        blocks.append(TextBlock(narration))

    metrics = [("현재 등급", data.get("currentGrade", "")), ("목표 등급", data.get("targetGrade", ""))]
    if data.get("weakestAxis"):
        metrics.append(("가장 약한 축", data["weakestAxis"]))
    blocks.append(MetricBlock(metrics))

    improvements = data.get("improvements", [])
    if improvements:
        rows = [
            {
                "축": imp["axis"],
                "지표": imp["metric"],
                "현재": f"{imp['current']:.1f}",
                "목표": f"{imp['target']:.1f}",
                "변화": imp["change"],
            }
            for imp in improvements
        ]
        blocks.append(TableBlock("등급 상향 경로", pl.DataFrame(rows)))
    return blocks


def cyclicalActionPlanBlock(data: dict | None) -> list:
    """calcCyclicalAction 결과 → 사이클 대응 행동 계획."""
    if not data:
        return []

    from dartlab.story.narrate import narrateCyclicalAction

    blocks: list = [
        HeadingBlock(_meta("cyclicalActionPlan").label, level=2, helper="사이클 위치에 따른 지금 해야 할 것")
    ]

    narration = narrateCyclicalAction(data)
    if narration:
        blocks.append(TextBlock(narration))

    blocks.append(MetricBlock([("사이클 국면", data.get("phaseLabel", ""))]))

    actions = data.get("actions", [])
    if actions:
        rows = [
            {"우선순위": a["priority"], "행동": a["action"], "이유": a["reason"], "긴급도": a.get("urgency", "")}
            for a in actions
        ]
        blocks.append(TableBlock("행동 계획", pl.DataFrame(rows)))

    precedent = data.get("historicalPrecedent")
    if precedent:
        blocks.append(TextBlock(f"**역사적 선례**: {precedent}"))
    return blocks


def damodaran3testBlock(company) -> list:
    """Damodaran 3-test 결과 → 스토리 검증 블록."""
    try:
        from dartlab.story.validators.validators import damodaranTest

        result = damodaranTest(company)
    except (ImportError, AttributeError, ValueError):
        return []

    blocks: list = [
        HeadingBlock(
            _meta("damodaran3test").label,
            level=2,
            helper="Damodaran: 모든 스토리는 History/Experience/Common Sense 3시험을 통과해야 한다",
        ),
    ]

    for test in [result.historyTest, result.experienceTest, result.commonSenseTest]:
        if test is None:
            continue
        icon = "✓" if test.passed else "✗"
        blocks.append(TextBlock(f"**{icon} {test.name}**: {test.detail}"))

    blocks.append(MetricBlock([("통과", f"{result.passCount}/{result.totalCount}")]))
    if result.passCount < 3:
        blocks.append(FlagBlock("warning", "3-test 일부 미통과 — 스토리 재검토 권고"))

    return blocks


def thesisReportBlocks(company, hypothesis: str | None) -> list:
    """AI 주도 논제 검증 — 가설→증거→판정 서사.

    블록을 기계적으로 쪼개지 않고 AI 응답 텍스트를 서사 단위로 3~4 블록에 배치.
    review의 '균질 블록' 원칙의 예외 — thesis는 서사 주도.
    """
    if not hypothesis:
        return [
            HeadingBlock(_meta("thesisStatement").label, level=2),
            FlagBlock(
                "warning",
                "hypothesis 파라미터가 필요합니다. 예: c.story(type='thesis', hypothesis='...')",
            ),
        ]

    blocks: list = [
        HeadingBlock(_meta("thesisStatement").label, level=2, helper="사용자 가설"),
        TextBlock(f"**가설**: {hypothesis}"),
    ]

    # AI 호출 (선택적 — 실패 시 스켈레톤만 반환)
    try:
        ask = getattr(company, "ask", None)
        if ask is None:
            blocks.append(FlagBlock("warning", "AI 엔진이 이 Company에 연결되지 않았습니다."))
            return blocks

        prompt = (
            f"다음 가설을 이 기업의 재무/공시 데이터로 검증하라:\n\n"
            f"가설: {hypothesis}\n\n"
            f"응답 형식:\n"
            f"## 지지 증거\n- 수치/팩트 (출처 명시)\n\n"
            f"## 반박 증거\n- 수치/팩트 (출처 명시)\n\n"
            f"## 판정\n지지/반박/미결 중 하나 + 신뢰도 (low/medium/high)"
        )
        response = ask(prompt)
        text = str(response) if response is not None else ""

        if text:
            blocks.append(HeadingBlock(_meta("evidenceFor").label, level=2))
            blocks.append(TextBlock(text))
    except (AttributeError, ValueError, RuntimeError) as e:
        blocks.append(FlagBlock("warning", f"AI 검증 실패: {e}"))

    return blocks


def storyPrecedentsBlock(data: dict) -> list:
    """calcStoryPrecedents → HeadingBlock + TextBlock + TableBlock.

    유사 경로 기업 선례 (Possible Test).
    """
    if not data:
        return []

    narration = narrateStoryPrecedents(data)
    precedents = data.get("precedents") or []

    blocks = [
        HeadingBlock(
            _meta("storyPrecedents").label,
            level=2,
            helper="Damodaran Possible Test — 같은 phase 기업 + 블로그 경험",
        ),
    ]
    if narration:
        blocks.append(TextBlock(narration, indent="h2"))

    if precedents:
        rows = []
        for p in precedents[:5]:
            rows.append(
                {
                    "종목": p.get("name") or p.get("stockCode") or "-",
                    "서사": (p.get("narrative") or "")[:80],
                    "출처": p.get("source") or "-",
                }
            )
        if rows:
            blocks.append(TableBlock("", pl.DataFrame(rows)))

    return blocks


def chainPositionBlock(data: dict | None) -> list:
    """calcChainPosition 결과 → 밸류체인 내 위치 블록.

    Parameters
    ----------
    data : dict | None
        calcChainPosition 반환값. industry/industryName/stage/stageName/
        role/stream/confidence/source/peers 포함.

    Returns
    -------
    list
        HeadingBlock + 서술 TextBlock + peer TableBlock.
        data 가 None/비어있으면 빈 리스트.
    """
    if not data:
        return []

    industryName = data.get("industryName") or data.get("industry") or "-"
    stageName = data.get("stageName") or data.get("stage") or "-"
    role = data.get("role") or ""
    stream = data.get("stream") or ""
    confidence = data.get("confidence")
    source = data.get("source") or ""
    peers = data.get("peers") or []

    blocks: list = [
        HeadingBlock(
            _meta("chainPosition").label,
            level=2,
            helper="전 상장사 2,665사 중 이 회사의 산업·공정·역할·스트림",
        ),
    ]

    streamLabel = _STREAM_LABEL.get(stream, stream)
    parts = [f"**{industryName}** 산업의 **{stageName}** 단계"]
    if role:
        parts.append(f"{role} 역할")
    if streamLabel:
        parts.append(streamLabel)
    narration = "에 위치한다. ".join([" · ".join(parts)]) + "."

    if confidence is not None:
        if confidence >= 0.9:
            narration += f" 매핑 신뢰도 {confidence:.2f} ({source or '자동'})."
        elif confidence >= 0.6:
            narration += f" 신뢰도 {confidence:.2f} — 자동 분류 추정."
        else:
            narration += f" 신뢰도 {confidence:.2f} — 저신뢰, 재검수 필요."
    blocks.append(TextBlock(narration))

    if peers:
        rows = [
            {
                "종목코드": p.get("stockCode", "-"),
                "회사명": p.get("corpName", "-"),
                "신뢰도": f"{p.get('confidence', 0):.2f}" if p.get("confidence") is not None else "-",
            }
            for p in peers[:10]
        ]
        blocks.append(TableBlock(f"같은 공정 피어 ({len(peers)}사 중 상위 {len(rows)})", pl.DataFrame(rows)))

    return blocks


# ── Industry (L2) — 섹터 실적 분포 + 전망 ──


def sectorMetricsBlock(data: dict | None) -> list:
    """calcSectorMetrics 결과 → 업종 실적 분포 블록.

    Parameters
    ----------
    data : dict | None
        calcSectorMetrics 반환값.

    Returns
    -------
    list
        HeadingBlock + TextBlock(분포 요약) + MetricBlock(내 위치).
        data 가 None 이면 빈 리스트.
    """
    if not data:
        return []

    industryName = data.get("industryName") or "-"
    peerCount = data.get("peerCount") or 0

    blocks: list = [
        HeadingBlock(
            _meta("sectorMetrics").label,
            level=2,
            helper=f"{industryName} {peerCount}사 대비 실적 분포",
        ),
    ]

    parts = []
    opm = data.get("opmDistribution")
    if opm:
        parts.append(f"영업이익률 중앙값 {opm['median']}% (P25 {opm['p25']}% ~ P75 {opm['p75']}%)")
    roe = data.get("roeDistribution")
    if roe:
        parts.append(f"ROE 중앙값 {roe['median']}% (P25 {roe['p25']}% ~ P75 {roe['p75']}%)")
    cagr = data.get("cagrDistribution")
    if cagr:
        parts.append(f"매출 CAGR 중앙값 {cagr['median']}%")

    if parts:
        blocks.append(TextBlock(f"**{industryName}** {peerCount}사 분포: " + " · ".join(parts)))

    metrics = []
    myOpm = data.get("myOpmPercentile")
    if myOpm is not None:
        metrics.append(("영업이익률 위치", f"상위 {100 - myOpm:.0f}%"))
    myRoe = data.get("myRoePercentile")
    if myRoe is not None:
        metrics.append(("ROE 위치", f"상위 {100 - myRoe:.0f}%"))
    myCagr = data.get("myCagrPercentile")
    if myCagr is not None:
        metrics.append(("매출 CAGR 위치", f"상위 {100 - myCagr:.0f}%"))
    if metrics:
        blocks.append(MetricBlock(metrics))

    return blocks


def sectorOutlookBlock(cycle: dict | None, dynamics: dict | None) -> list:
    """calcSectorCycle + calcSectorDynamics 결과 → 섹터 전망 블록.

    Parameters
    ----------
    cycle : dict | None
        calcSectorCycle 반환값.
    dynamics : dict | None
        calcSectorDynamics 반환값.

    Returns
    -------
    list
        HeadingBlock + TextBlock(사이클) + TextBlock(순풍/역풍).
    """
    if not cycle and not dynamics:
        return []

    industryName = (cycle or dynamics or {}).get("industryName") or "-"
    blocks: list = [
        HeadingBlock(
            _meta("sectorOutlook").label,
            level=2,
            helper=f"{industryName} 사이클 + 매크로 교차",
        ),
    ]

    if cycle:
        phase = cycle.get("phase") or "미확인"
        direction = cycle.get("direction") or ""
        conf = cycle.get("confidence") or 0
        trend = cycle.get("opmTrend") or []
        narration = f"**{industryName}** 사이클: **{phase}** ({direction})"
        if conf < 0.6:
            narration += " — 데이터 제한으로 신뢰도 낮음"
        blocks.append(TextBlock(narration))
        if trend:
            rows = [{"기간": t.get("year", ""), "OPM 중앙값(%)": str(t.get("median", ""))} for t in trend]
            if rows:
                blocks.append(TableBlock("OPM 추이", pl.DataFrame(rows)))

    if dynamics:
        summary = dynamics.get("summary") or ""
        if summary:
            blocks.append(TextBlock(summary))
        tailwind = dynamics.get("tailwind") or []
        headwind = dynamics.get("headwind") or []
        if tailwind:
            blocks.append(TextBlock("순풍: " + " · ".join(tailwind)))
        if headwind:
            blocks.append(TextBlock("역풍: " + " · ".join(headwind)))

    return blocks
