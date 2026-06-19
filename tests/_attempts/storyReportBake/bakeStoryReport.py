"""기업분석보고서 payload bake (PRD P0 ② — _attempts, 본진 아님).

PRD `mainPlan/company-analysis-report/` 03문서의 reportPayload 직렬화기 1차 구현.
story 엔진의 renderJson 출력을 ~확장 — 섹션에 act/actHeader/sourceEngine 부착,
sixActScore 의 evidenceFrame(점수는 _internalScore 로 분리, NEVER-CLAIM 레이더 비노출),
honest-skip reject-gate(데이터 빈약 회사는 안 굽고 _skipped 기록).

dev 격리: 산출 JSON 은 landing/static/story/report-{code}.json 로 써서
dev 라우트(/lab/report)가 fetch. 본진(src/dartlab) 미변경.

Sig:
    bakeStoryReport(code, bakedAt) -> dict | None  (None = honest-skip)

Example::
    uv run python -X utf8 tests/_attempts/storyReportBake/bakeStoryReport.py 005930 000660

Returns:
    payload dict (자격 통과) 또는 None(skip). 파일도 함께 기록.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# 섹션 → 지배(계산 주도) 엔진. sourceEngine = "어느 dartlab 엔진이 계산했는가"
# (DART 공시 줄이 아님 — rcept 풀회로는 PRD P4 후속 트랙). 멀티소스는 primary.
SECTION_SOURCE_ENGINE: dict[str, str] = {
    "수익구조": "analysis",
    "성장성": "analysis",
    "수익성": "analysis",
    "비용구조": "analysis",
    "이익품질": "analysis",
    "현금흐름": "analysis",
    "자금조달": "analysis",
    "안정성": "analysis",
    "자산구조": "analysis",
    "효율성": "analysis",
    "투자효율": "analysis",
    "자본배분": "analysis",
    "재무정합성": "analysis",
    "종합평가": "analysis",
    "가치평가": "analysis",
    "매출전망": "analysis",
    "지배구조": "analysis",
    "공시변화": "analysis",
    "신용평가": "credit",
    "시장분석": "quant",
    "매크로": "macro",
    "비교분석": "industry",
    "storyValidation": "story",
    "improvementPlan": "story",
    "thesisReport": "story",
}

# honest-skip reject-gate 임계 (PRD: spike 로 확정 — 여기선 dev 1차값, 분포 실측 후 갱신)
MIN_NONEMPTY_SECTIONS = 6
CORE_ACTS_REQUIRED = 3  # 핵심막 중 최소 블록 보유 막 수
CORE_SECTIONS = {"수익구조", "수익성", "현금흐름", "안정성", "가치평가"}


def _splitEvidenceFrame(saDict: dict) -> dict:
    """sixActScore.asDict() → evidenceFrame. score 는 _internalScore 로 분리(화면 비노출).

    정직: sixActScore 는 fresh Company 경로에서 대부분 축 missing(c.insights 미수집·
    credit DataFrame). ready 축만 axes 에 넣어 *빈 레이더 비노출*. 전부 missing 이면 axes={}.
    """
    score = saDict.get("score", {})
    evidence = saDict.get("evidence", {})
    coverage = saDict.get("coverage", {})
    notes = saDict.get("notes", {})
    axes = {}
    for axis in ("macro", "sector", "firm", "financial", "value", "risk"):
        cov = coverage.get(axis, "missing")
        if cov == "ready":
            axes[axis] = {
                "coverage": cov,
                "evidenceIds": list(evidence.get(axis, [])),
                "note": notes.get(axis, ""),
            }
    return {"axes": axes, "_internalScore": {k: v for k, v in score.items() if v is not None}}


# sourceEngine 라벨(어느 엔진이 계산했는가) — 사람 표시명.
_ENGINE_LABEL: dict[str, str] = {
    "analysis": "재무분석",
    "credit": "신용평가",
    "quant": "시장·기술",
    "industry": "산업비교",
    "macro": "거시",
    "story": "종합서사",
}


def _provenanceFrame(sections: list[dict]) -> dict:
    """이 보고서를 *실제로* 만든 엔진 provenance — sourceEngine 집계(신뢰 가능한 정직 토대).

    sixActScore 레이더가 비어도 이건 항상 채워진다(블록의 실제 출처 엔진).
    PRD 정직 토대 3중 회로 중 pillar ②(블록 sourceEngine)를 보고서 단위로 요약.
    """
    engines: dict[str, dict] = {}
    for s in sections:
        if not s.get("blocks"):
            continue
        eng = s.get("sourceEngine", "analysis")
        e = engines.setdefault(
            eng, {"label": _ENGINE_LABEL.get(eng, eng), "sections": 0, "blocks": 0, "sectionKeys": []}
        )
        e["sections"] += 1
        e["blocks"] += len(s["blocks"])
        e["sectionKeys"].append(s.get("key", ""))
    return {
        "engines": engines,
        "note": "sourceEngine = 어느 dartlab 엔진이 계산했는가 (원천 DART 공시 줄 아님 — rcept 딥링크는 별도)",
    }


_JUDGMENT_RE = re.compile(
    r"(매우 |다소 |비교적 )?(양호한?|안정적인?|우수한?|건전한?|견고한?|탄탄한?|취약한?|부진한?)"
    r"\s*(마진 수준|자본 구조|수익 구조|재무 구조)?(이다|이며|하다|함)?\.?"
)
_BAD_NUM_RE = re.compile(r"\d{6,}\.?\d*조")  # 백만원 raw 에 조 오접미


def _rescaleManwon(val: str) -> str:
    """'187967346.0조' (백만원 raw + 조 오접미) → '188.0조'. 그 외 원본 유지."""
    if isinstance(val, str) and val.endswith("조"):
        num = val[:-1].replace(",", "")
        try:
            f = float(num)
        except ValueError:
            return val
        if abs(f) >= 10000:  # 백만원 단위가 조 라벨로 잘못 붙음
            scaled = f / 1_000_000.0
            return f"{scaled:,.1f}조"
    return val


def _fixTableUnits(data: list[dict]) -> list[dict]:
    return [{k: _rescaleManwon(v) for k, v in row.items()} for row in data]


def _dropEmptyRows(data: list[dict]) -> list[dict]:
    """전 연도 결측/0 인 행 제거 — 결측을 0 으로 둔갑한 행을 표에서 숨김."""
    if not data:
        return data
    cols = list(data[0].keys())
    yearCols = cols[1:]
    if not yearCols:
        return data
    empty = {"", "-", "0", "0.0", "0%", "0.0%", "N/A", "None", "nan"}
    return [row for row in data if not all(str(row.get(c, "")).strip() in empty for c in yearCols)]


# CF 비율행에서 "0%"/"0.0%" = 분자(영업CF) 결측 둔갑 → "-" (부분결측 가드)
_CF_RATIO_HINT = ("CF", "현금", "전환", "FCF")
_ZERO_PCT = {"0%", "0.0%", "0.00%", "0.0", "0"}


def _guardMissingRatios(data: list[dict]) -> list[dict]:
    """CF 전환 비율행의 0% 둔갑(분자 결측)을 '-' 로 — 실제 0 과 결측 0 혼동 차단."""
    if not data:
        return data
    cols = list(data[0].keys())
    labelKey, yearCols = cols[0], cols[1:]
    for row in data:
        label = str(row.get(labelKey, ""))
        if any(h in label for h in _CF_RATIO_HINT):
            for yk in yearCols:
                if str(row.get(yk, "")).strip() in _ZERO_PCT:
                    row[yk] = "-"
    return data


# 표와 모순되거나 버그인 파생 metric 라벨 — 드롭 (데이터는 표가 SSOT)
_DROP_METRIC_LABELS = {"FCF 양수 연속", "마진 방향", "전환 신호"}
# 영문 metric 값 → 한글
_METRIC_VALUE_KO = {
    "dcf": "FCFF DCF",
    "relative": "상대가치",
    "ddm": "DDM",
    "contracting": "",
    "expanding": "",
    "stable": "",
    "decline": "",
    "growth": "",
}


def _fixMetricsBlock(metrics: list[dict]) -> list[dict]:
    out = []
    for m in metrics:
        label = str(m.get("label", "")).strip()
        if label in _DROP_METRIC_LABELS:
            continue
        val = str(m.get("value", "")).strip()
        ko = _METRIC_VALUE_KO.get(val.lower())
        if ko is not None:
            val = ko
        if not val or val in ("판별 불가", "판별불가", "-", "None"):
            continue
        out.append({"label": label, "value": val})
    return out


def _dropOrphanHeadings(blocks: list[dict]) -> list[dict]:
    """내용(비-heading) 없는 고아 heading 제거 — 빈 블록 드롭 후 댕글링 제목 정리."""
    out: list[dict] = []
    n = len(blocks)
    for i, b in enumerate(blocks):
        if b.get("type") == "heading":
            # 바로 다음 블록이 없거나 또 heading 이면 고아 → 제거
            if i + 1 >= n or blocks[i + 1].get("type") == "heading":
                continue
        out.append(b)
    return out


def _stripJudgment(text: str) -> str:
    """판정 형용사 절 제거 (C-2: raw 측정값만, 판정 프로즈 미표면화). 측정 문장은 보존."""
    out = _JUDGMENT_RE.sub("", text)
    out = re.sub(r"\s{2,}", " ", out).strip()
    out = re.sub(r"^[.\s]+", "", out)
    return out


# 검증 안 된 *방향* 주장 (표와 모순 위험) — "부채가 지속적으로 증가하는 추세다" 류
_TREND_RE = re.compile(
    r"[가-힣A-Za-z]+(가|이|은|는|도)?\s*(지속적으로\s*|꾸준히\s*|계속\s*)?(증가|감소|상승|하락|확대|축소)"
    r"하(는|고 있는)\s*추세(이?다|이며|임)?\.?"
)


def _cleanStr(text: str) -> str:
    """C-2 일관 정화 — 본문/요약 모든 narrate 프로즈에 적용.

    ① 백만원 raw 에 조 오접미된 수치 재스케일 ② 판정형용사 절 제거
    ③ 검증 안 된 전환 괄호(급락 X→Y) 제거 ④ 검증 안 된 방향 추세 주장 제거.
    측정값 문장(원가율 +1.4%p 등)은 보존.
    """
    if not text:
        return text
    text = re.sub(r"-?\d{6,}\.?\d*조", lambda m: _rescaleManwon(m.group()), text)
    text = _JUDGMENT_RE.sub("", text)
    text = re.sub(r"\s*\d{4}\s*년?에?\s*(급락|급등|하락 전환|상승 전환)\s*\([^)]*\)\.?", "", text)
    text = re.sub(r"\s*(급락|급등|하락 전환|상승 전환)\s*\([^)]*\)\.?", "", text)
    text = _TREND_RE.sub("", text)
    # 본문과 모순되는 lifecycle "전환 신호: 쇠퇴 방향 (score 0.55)." 절 통째 제거 (괄호 포함)
    text = re.sub(r"\s*전환 신호[:：][^()]*(\([^)]*\))?\.?", "", text)
    # 피어 "상위 0%" = 최상위인데 0%로 읽혀 혼동 → 명확화
    text = re.sub(r"상위\s*0\s*%", "최상위(상위 1% 미만)", text)
    text = re.sub(r"\(\s*\)", "", text)  # 빈 괄호 '( )' 제거
    text = re.sub(r"\s+\)", ")", text)  # ') 앞 stray space ("삼각검증 )" → "삼각검증)")
    text = re.sub(r"\.{2,}", ".", text)  # 이중 마침표 '..' → '.'
    text = re.sub(r"\s+\.", ".", text)  # ' .' → '.'
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = re.sub(r"^[.\s—–-]+", "", text).strip()
    return text


def bakeStoryReport(code: str, bakedAt: str) -> dict | None:
    """단일 회사 reportPayload bake. 자격 미달 시 None(honest-skip)."""
    import dartlab
    from dartlab.story import buildStory, getSectionMeta, sixActScore
    from dartlab.story.catalog import ACT_HEADERS

    c = dartlab.Company(code)
    corpName = getattr(c, "corpName", "") or ""

    story = buildStory(c, type="full", detail=True)
    base = json.loads(story.render("json"))  # {stockCode, corpName, sections[], summaryCard?, circulationSummary?}

    sections = base.get("sections", [])
    nonEmpty = [s for s in sections if s.get("blocks")]
    # 섹션 enrich: act / actHeader / sourceEngine
    actsCovered: set[str] = set()
    for s in sections:
        key = s.get("key", "")
        meta = getSectionMeta(key) if key else None
        act = getattr(meta, "act", 0) if meta else 0
        s["act"] = act
        hdr = ACT_HEADERS.get(str(act)) if act else None
        s["actHeader"] = hdr[0] if hdr else None
        s["sourceEngine"] = SECTION_SOURCE_ENGINE.get(key, "analysis")
        # C-2 일관 정화 + 빈/무의미 블록 제거 (표 데이터가 SSOT, 빈 placeholder 제거)
        cleaned: list[dict] = []
        for b in s.get("blocks", []):
            bt = b.get("type")
            if bt == "chart":
                continue  # P2 — placeholder 무가치 + 빈 차트(series=null) 위험. 표가 데이터 보유
            if bt == "table" and b.get("data"):
                b["data"] = _guardMissingRatios(_dropEmptyRows(_fixTableUnits(b["data"])))
                if not b["data"]:
                    continue
            elif bt == "text":
                b["text"] = _cleanStr(b.get("text", ""))
                if not b["text"]:
                    continue
            elif bt == "metrics":
                b["metrics"] = _fixMetricsBlock(b.get("metrics", []))
                if not b["metrics"]:
                    continue
            cleaned.append(b)
        s["blocks"] = _dropOrphanHeadings(cleaned)
        # summary 정화: 단위 재스케일 + 잘린 흔적·빈 판정 제거 (payload 자기정합)
        if s.get("summary"):
            summ = _cleanStr(s["summary"])
            truncated = (
                bool(re.search(r"\d$", summ))
                and "%" not in summ[-4:]
                and "조" not in summ[-2:]
                and "기" not in summ[-2:]
            )
            if truncated or "판별 불가" in summ or "판별불가" in summ:
                summ = ""
            s["summary"] = summ
        if act and s.get("blocks"):
            actsCovered.add(str(act))

    # evidenceFrame (score 분리)
    try:
        evidenceFrame = _splitEvidenceFrame(sixActScore(c).asDict())
    except Exception as exc:  # noqa: BLE001 — dev probe, 광범위 catch 의도
        print(f"  [warn] sixActScore 실패: {type(exc).__name__}: {exc}", flush=True)
        evidenceFrame = {"axes": {}, "_internalScore": {}}

    summaryCard = base.get("summaryCard") or {}
    conclusion = (summaryCard.get("conclusion") or "").strip()

    # ── 핵심 발견 + 종합 의견 (측정값 우선 · 불안정 프로즈 제거) ──
    # C-2 규칙: raw 측정값을 표면화하되 판정형용사·검증 안 된 전환수치(급락 X→Y)는 제거.
    def _byKey(key: str) -> dict | None:
        return next((x for x in sections if x.get("key") == key and x.get("blocks")), None)

    def _cleanText(sec: dict) -> str:
        for b in sec.get("blocks", []):
            if b.get("type") == "text" and (b.get("text") or "").strip():
                t = _stripJudgment(b["text"].strip())
                # 검증 안 된 전환 절(YYYY(년)에 급락 (X%→Y%)) 통째 제거 — narrate 오수치 차단
                t = re.sub(r"\s*\d{4}\s*년?에?\s*(급락|급등|하락 전환|상승 전환)\s*\([^)]*\)\.?", "", t)
                t = re.sub(r"\s*(급락|급등|하락 전환|상승 전환)\s*\([^)]*\)\.?", "", t)
                t = re.sub(r"\s{2,}", " ", t).strip()
                return t
        return ""

    def _latestFromTables(sec: dict | None, rowLabel: str) -> str | None:
        if not sec:
            return None
        for b in sec.get("blocks", []):
            if b.get("type") == "table" and b.get("data"):
                cols = list(b["data"][0].keys())
                labelKey, yearKeys = cols[0], cols[1:]
                for row in b["data"]:
                    if str(row.get(labelKey, "")).strip() == rowLabel:
                        for yk in yearKeys:
                            v = row.get(yk)
                            if v not in (None, "", "-"):
                                return str(v)
        return None

    keyFindings = []
    for s in sections:
        if not s.get("blocks"):
            continue
        txt = _cleanText(s)
        if txt and len(txt) > 8 and ":" not in txt[:14]:
            keyFindings.append(
                {
                    "key": s["key"],
                    "title": s.get("title", s["key"]),
                    "act": s.get("act"),
                    "sourceEngine": s.get("sourceEngine"),
                    "finding": txt,
                }
            )

    def _minYearFromTable(sec: dict | None, rowLabel: str) -> tuple[str, str] | None:
        """행의 최저값 연도+값 — 변곡점(저점) 자동 추출."""
        if not sec:
            return None
        for b in sec.get("blocks", []):
            if b.get("type") == "table" and b.get("data"):
                cols = list(b["data"][0].keys())
                labelKey, yearCols = cols[0], cols[1:]
                for row in b["data"]:
                    if str(row.get(labelKey, "")).strip() == rowLabel:
                        vals = []
                        for yk in yearCols:
                            raw = str(row.get(yk, "")).strip().rstrip("%").replace(",", "")
                            try:
                                vals.append((float(raw), yk, str(row.get(yk))))
                            except ValueError:
                                continue
                        if len(vals) >= 3:
                            return min(vals, key=lambda x: x[0])[1:]
        return None

    # 종합 의견 = 측정값 추출(표) + 변곡점 + 신뢰 가능한 생애주기·피어 서술
    measured = []
    secProfit, secStab = _byKey("수익성"), _byKey("안정성")
    for label, sec in (("영업이익률", secProfit), ("매출총이익률", secProfit), ("부채비율", secStab)):
        v = _latestFromTables(sec, label)
        if v:
            measured.append(f"{label} {v}")
    measuredLine = " · ".join(measured)
    inflection = ""
    mn = _minYearFromTable(secProfit, "영업이익률")
    latest = _latestFromTables(secProfit, "영업이익률")
    if mn and latest and mn[1] != latest:  # 저점이 최신연도가 아니면 = 회복 변곡점
        inflection = f"{mn[0]} 영업이익률 {mn[1]} 저점 후 회복"
    lifecycle = _cleanText(_byKey("가치평가") or {})
    peer = _cleanText(_byKey("매출전망") or {})
    narrativeOverview = ". ".join(p.rstrip(". ") for p in [measuredLine, inflection, lifecycle, peer] if p).strip()
    narrativeOverview = re.sub(r"\.{2,}", ".", narrativeOverview) + (
        "." if narrativeOverview and not narrativeOverview.endswith(".") else ""
    )

    # conclusion 보강: 약하면 grades 합성 (절대 등급 — 동종 백분위 아님)
    grades = summaryCard.get("grades") or {}
    if (not conclusion or len(conclusion) < 12) and grades:
        gradeStr = " · ".join(f"{k} {v}" for k, v in grades.items())
        summaryCard["conclusion"] = f"재무 등급 — {gradeStr}"
        conclusion = summaryCard["conclusion"]
    summaryCard["gradesNote"] = "절대 등급 (동종 대비 백분위 아님)"

    # ── headline KPI 밴드 (한눈 핵심 숫자) ──
    def _findMetricVal(label: str) -> str | None:
        for s in sections:
            for b in s.get("blocks", []):
                if b.get("type") == "metrics":
                    for m in b.get("metrics", []):
                        if str(m.get("label", "")).strip() == label:
                            return str(m.get("value", "")).strip()
        return None

    headlineKpis = []
    for lab, val in (
        ("영업이익률", _latestFromTables(secProfit, "영업이익률")),
        ("매출총이익률", _latestFromTables(secProfit, "매출총이익률")),
        ("부채비율", _latestFromTables(secStab, "부채비율")),
        ("매출 CAGR", _findMetricVal("매출 CAGR")),
        ("ROIC-WACC", _findMetricVal("ROIC - WACC")),
        ("배당성향", _findMetricVal("배당성향")),
    ):
        if val:
            headlineKpis.append({"label": lab, "value": val})

    # ── strengths / warnings (등급 + ROIC-WACC 신호 기반) — 통찰 표면 채움 ──
    if not summaryCard.get("strengths"):
        summaryCard["strengths"] = [f"{area} 등급 {g}" for area, g in grades.items() if g in ("A", "B")]
    if not summaryCard.get("warnings"):
        warns = [f"{area} 등급 {g}" for area, g in grades.items() if g in ("D", "F")]
        rw = _findMetricVal("ROIC - WACC")
        if rw and rw.strip().startswith("-"):
            warns.append(f"ROIC가 WACC 미달 ({rw})")
        summaryCard["warnings"] = warns

    # ── 일회성 손익 자동 플래그 (순이익률 >100% = 비경상 가능) ──
    extraNotes: list[str] = []
    for s in sections:
        if s.get("key") != "수익성":
            continue
        for b in s.get("blocks", []):
            if b.get("type") == "table" and b.get("data"):
                cols = list(b["data"][0].keys())
                for row in b["data"]:
                    if str(row.get(cols[0], "")).strip() == "순이익률":
                        for yk in cols[1:]:
                            raw = str(row.get(yk, "")).rstrip("%").replace(",", "")
                            try:
                                if float(raw) > 100:
                                    extraNotes.append(f"{yk} 순이익률 {row[yk]} (일회성 손익 가능 — 정상화 전)")
                            except ValueError:
                                continue

    # ── honest-skip reject-gate ──
    coreActsWithBlocks = len({s["key"] for s in nonEmpty if s["key"] in CORE_SECTIONS})
    qualifies = bool(conclusion) and len(nonEmpty) >= MIN_NONEMPTY_SECTIONS and coreActsWithBlocks >= CORE_ACTS_REQUIRED
    if not qualifies:
        reason = (
            f"conclusion={'Y' if conclusion else 'N'} nonEmpty={len(nonEmpty)}"
            f"(<{MIN_NONEMPTY_SECTIONS}?) coreSections={coreActsWithBlocks}(<{CORE_ACTS_REQUIRED}?)"
        )
        print(f"  [skip] {code} {corpName} — {reason}", flush=True)
        return None

    provenanceFrame = _provenanceFrame(sections)
    engineCount = len(provenanceFrame["engines"])
    qualityLabel = "verified" if (len(nonEmpty) >= 8 and engineCount >= 3) else "conditional"

    payload = {
        "schemaVersion": 1,
        "engine": "dartlab.story",
        "bakedAt": bakedAt,
        "stockCode": base.get("stockCode", code),
        "corpName": base.get("corpName", corpName),
        "template": getattr(story, "template", None),
        "circulationSummary": base.get("circulationSummary", ""),
        "summaryCard": summaryCard,
        "narrativeOverview": narrativeOverview,  # 종합 의견 (리드 섹션 측정값 문장 합성)
        "headlineKpis": headlineKpis,  # 한눈 KPI 밴드 (핵심 6지표)
        "keyFindings": keyFindings,  # 핵심 발견 spine (섹션별 측정값 한 줄)
        "assumptionsNote": (
            "WACC 는 전기간 동일 가정(단순화) · 절대 등급은 동종 백분위 아님 · 경계연도 일부 지표 결측 가능"
            + ("  ·  " + " · ".join(extraNotes) if extraNotes else "")
        ),
        "evidenceFrame": evidenceFrame,  # sixActScore ready 축 (fresh 경로엔 보통 빈약)
        "provenanceFrame": provenanceFrame,  # ★신뢰 가능한 정직 토대 — 실제 엔진 출처 집계
        "sections": sections,
        "meta": {
            "nonEmptySectionCount": len(nonEmpty),
            "actsCovered": sorted(actsCovered),
            "engineCount": engineCount,
            "qualityLabel": qualityLabel,
        },
    }
    return payload


def main(argv: list[str]) -> int:
    codes = argv[1:] or ["005930"]
    bakedAt: str | None = None
    realCodes: list[str] = []
    for a in codes:
        if a.startswith("--at="):
            bakedAt = a.split("=", 1)[1]
        else:
            realCodes.append(a)
    if not bakedAt:
        from datetime import date

        bakedAt = date.today().isoformat()

    outDir = Path(__file__).resolve().parents[3] / "landing" / "static" / "story"
    outDir.mkdir(parents=True, exist_ok=True)
    skipped = []
    for code in realCodes:
        print(f"[bake] {code} (bakedAt={bakedAt}) ...", flush=True)
        try:
            payload = bakeStoryReport(code, bakedAt)
        except Exception as exc:  # noqa: BLE001
            print(f"  [error] {code} — {type(exc).__name__}: {exc}", flush=True)
            skipped.append({"code": code, "reason": f"{type(exc).__name__}: {exc}"})
            continue
        if payload is None:
            skipped.append({"code": code, "reason": "reject-gate"})
            continue
        outPath = outDir / f"report-{code}.json"
        outPath.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        m = payload["meta"]
        print(
            f"  [ok] {code} {payload['corpName']} → {outPath.name} "
            f"sections={m['nonEmptySectionCount']} acts={m['actsCovered']} "
            f"label={m['qualityLabel']} bytes={outPath.stat().st_size}",
            flush=True,
        )
    if skipped:
        (outDir / "report-_skipped.json").write_text(json.dumps(skipped, ensure_ascii=False), encoding="utf-8")
        print(f"[skipped] {len(skipped)} → report-_skipped.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
