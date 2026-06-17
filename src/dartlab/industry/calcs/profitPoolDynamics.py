"""산업 이익 풀 동학 — 집중형 vs 이동형 (시간축 argmax 리더 교체).

스냅샷 profit-pool 이 아니라 *시간에 따라 어느 공정이 이익을 가져가나* 를 본다. McKinsey
profit-pool migration 의 진짜 통찰. 패널(전수·다년·1차자료)만 답하는 질문.
"""

from __future__ import annotations

from typing import Any


def calcProfitPoolDynamics(industryId: str, *, years: list[str] | None = None) -> dict:
    """산업 stage별 영업이익의 다년 동학 — 리더 교체(이동형) vs 고착(집중형) 판정.

    Capabilities:
        ``buildTimelineSummary`` (stage×연도 영업이익(조)) 위에 **argmax 리더 교체**라는 결정론
        판정 한 줄을 얹는다. 첫해 1위 공정과 끝해 1위 공정이 다르면 "이동형", 같으면 "집중형".
        share(%) 미사용 — levels(조)만 (총합 zero-crossing 시 점유율 폭발 차단). 적자전환 stage 를
        이동의 1차자료 증거로 플래그. 생존편향은 복원 불가라 정직 표기.

    Parameters
    ----------
    industryId : str
        산업 ID (taxonomy key).
    years : list[str] | None
        대상 연도. None 이면 ``buildTimelineSummary`` 기본(2021~2025). finance.parquet 깊이가
        얕아 결손 연도는 자동 제외(Σ영업이익>0 연도만 유효).

    Returns
    -------
    dict
        판정 : str | None — "집중형" | "이동형" (유효 연도 < 2 면 None)
        리더_첫해 : tuple — (stage, 공정명) 첫 유효연도 영업이익 1위
        리더_끝해 : tuple — (stage, 공정명) 끝 유효연도 영업이익 1위
        적자전환 : list[str] — 첫해>0 & 끝해<0 인 공정명 (이동 증거)
        윈도 : str — "2021~2024" 형태 (유효 연도 범위)
        stage시계열 : list[dict] — 공정별 `{공정, 공정명, 첫해(조), 끝해(조), 변화(조), 연도별}`
        기업수추이 : list[tuple] — (연도, 기업수) — 멤버십 소급의 가시 신호
        생존편향주의 : str — 현재 멤버십 과거 소급 한계 고정 경고

    Raises
    ------
    없음 — 데이터 없으면 판정 None + 빈 시계열.

    Example
    -------
    >>> from dartlab.industry.calcs.profitPoolDynamics import calcProfitPoolDynamics
    >>> r = calcProfitPoolDynamics("battery")  # 셀이 줄곧 1위 → 집중형, 양극재는 적자전환
    >>> r["판정"], r["리더_끝해"][1], r["적자전환"]
    ('집중형', '셀', ['양극재'])

    Guide
    -----
    levels(조)만 정직 — 음수 stage 는 그대로 표기, share 폐기. 모든 stage 음수인 해는 리더 산출
    제외. 생존편향(현 멤버십 과거 소급)은 복원 불가 — ``생존편향주의`` + ``기업수추이`` 를 답변에
    동반 인용. 4년 윈도라 "추세" 아닌 "방향 신호".

    SeeAlso
    -------
    - ``dartlab.industry.build.financials.buildTimelineSummary`` : 입력 stage×연도 산출
    - ``dartlab.industry.calcs.lifecycle.classifyLifecycle`` : 동일 timeline 위 phase 분류 형제

    Requires
    --------
    - L1.5 scan: finance.parquet (years 각각)
    - taxonomy + nodes.json

    AIContext
    ---------
    "이 산업은 어느 공정이 이익을 가져가나 / 이익 풀이 이동했나" 답변. 이동형이면 적자전환 stage 와
    끝해 리더를 함께 인용. **생존편향·levels(추정 아님) 단서 명시** — 점유율% 인용 금지.

    When:
        산업 동학(통합/범용화/이익 이동) 질문. 단일 연도는 ``Industry()(id, summary=True)``.

    How:
        ``buildTimelineSummary`` long-format → 유효 연도(Σ영업이익>0) 필터 → 첫/끝해 argmax 리더 →
        교체 여부 판정 + 적자전환 플래그 + 생존편향 표기.

    See Also:
        - ``dartlab.industry.build.financials.buildTimelineSummary`` : 입력 산출
        - ``dartlab.industry.calcs.lifecycle.classifyLifecycle`` : 형제 (phase 분류)
    """
    from dartlab.industry.build.financials import buildTimelineSummary
    from dartlab.industry.build.pipeline import loadNodes

    survivorNote = "현재 산업 멤버십을 과거 연도에 소급 적용 — 과거 진입·퇴출 기업 미반영(복원 불가)"
    empty = {
        "판정": None,
        "리더_첫해": None,
        "리더_끝해": None,
        "적자전환": [],
        "윈도": "",
        "stage시계열": [],
        "기업수추이": [],
        "생존편향주의": survivorNote,
    }

    df = buildTimelineSummary(loadNodes(), industryId, years=years)
    if df.is_empty():
        return empty

    rows = df.iter_rows(named=True)
    # stage → {year: opIncome}, stage → 공정명, year → 기업수합
    byStage: dict[str, dict[str, float]] = {}
    stageLabel: dict[str, str] = {}
    yearCount: dict[str, int] = {}
    for r in rows:
        st = r["stage"]
        y = r["연도"]
        op = r["영업이익(조)"]
        stageLabel[st] = r.get("공정명") or st
        byStage.setdefault(st, {})[y] = op
        yearCount[y] = yearCount.get(y, 0) + (r.get("기업수") or 0)

    # 유효 연도 = Σ영업이익(조) > 0 (zero-crossing/전적자 해 제외 — 끝해 가드)
    allYears = sorted(yearCount.keys())
    validYears = [y for y in allYears if sum(v.get(y) for v in byStage.values() if v.get(y) is not None) > 0]
    if len(validYears) < 2:
        return {**empty, "기업수추이": [(y, yearCount[y]) for y in allYears]}

    firstY, lastY = validYears[0], validYears[-1]

    def leaderAt(y: str) -> tuple[str, str] | None:
        """해당 연도 영업이익 1위 공정 (stage, 공정명) — 데이터 없으면 None."""
        cand = [(st, v[y]) for st, v in byStage.items() if v.get(y) is not None]
        if not cand:
            return None
        st = max(cand, key=lambda x: x[1])[0]
        return (st, stageLabel.get(st, st))

    firstLeader = leaderAt(firstY)
    lastLeader = leaderAt(lastY)
    verdict = "이동형" if (firstLeader and lastLeader and firstLeader[0] != lastLeader[0]) else "집중형"

    # 적자전환: 첫해>0 & 끝해<0 (이동의 1차자료 증거)
    flipped = []
    stageSeries = []
    for st, v in byStage.items():
        f = v.get(firstY)
        ll = v.get(lastY)
        if f is not None and ll is not None and f > 0 and ll < 0:
            flipped.append(stageLabel.get(st, st))
        stageSeries.append(
            {
                "공정": st,
                "공정명": stageLabel.get(st, st),
                "첫해(조)": v.get(firstY),
                "끝해(조)": v.get(lastY),
                "변화(조)": (round(ll - f, 1) if (f is not None and ll is not None) else None),
                "연도별": {y: v.get(y) for y in validYears},
            }
        )
    # 끝해 영업이익 내림차순(리더 먼저)
    stageSeries.sort(key=lambda s: (s["끝해(조)"] is None, -(s["끝해(조)"] or -1e9)))

    return {
        "판정": verdict,
        "리더_첫해": firstLeader,
        "리더_끝해": lastLeader,
        "적자전환": flipped,
        "윈도": f"{firstY}~{lastY}",
        "stage시계열": stageSeries,
        "기업수추이": [(y, yearCount[y]) for y in validYears],
        "생존편향주의": survivorNote,
    }


def _dynamicsDataFrame(industryId: str, *, years: list[str] | None = None) -> Any:
    """``calcProfitPoolDynamics`` (dict) → 표면 계약(DataFrame). 공정별 첫/끝해 levels + 판정 첨부."""
    import polars as pl

    r = calcProfitPoolDynamics(industryId, years=years)
    schema = {
        "공정명": pl.Utf8,
        "첫해(조)": pl.Float64,
        "끝해(조)": pl.Float64,
        "변화(조)": pl.Float64,
        "적자전환": pl.Boolean,
        "끝해리더": pl.Boolean,
        "판정": pl.Utf8,
        "리더이동": pl.Utf8,
        "윈도": pl.Utf8,
        "생존편향주의": pl.Utf8,
    }
    series = r.get("stage시계열") or []
    if not series:
        return pl.DataFrame(schema=schema)

    flipped = set(r.get("적자전환") or [])
    lastLeader = (r.get("리더_끝해") or (None, None))[1]
    firstLeader = (r.get("리더_첫해") or (None, None))[1]
    move = f"{firstLeader} → {lastLeader}" if r.get("판정") == "이동형" else f"{lastLeader} 고착"
    out = [
        {
            "공정명": s["공정명"],
            "첫해(조)": s["첫해(조)"],
            "끝해(조)": s["끝해(조)"],
            "변화(조)": s["변화(조)"],
            "적자전환": s["공정명"] in flipped,
            "끝해리더": s["공정명"] == lastLeader,
            "판정": r["판정"],
            "리더이동": move,
            "윈도": r["윈도"],
            "생존편향주의": r["생존편향주의"],
        }
        for s in series
    ]
    return pl.DataFrame(out, schema=schema)
