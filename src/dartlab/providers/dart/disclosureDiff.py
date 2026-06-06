"""disclosureDiff — DART 공시 본문 시계열 sentence-level diff (panel SSOT).

같은 회사의 두 period (예: 2024Q3 vs 2025Q3) 의 sectionLeaf 매칭 후 contentRaw 의
unified diff 를 산출한다. 외부 LLM 은 PDF/HTML 단발만 보고 동일 회사 시계열 비교를
하지 않는다 — 본 모듈은 dartlab 의 panel 자산(``providers.dart.panel`` 수평화 본문)
위에서만 성립하는 *시계열 diff* 의 L1.5 가공 SSOT 다.

L1.5 frame 책임 — raw(panel) 결합 → 분석 ready. 의미 분류(가이던스 방향·리스크
추가·회계정책 변경)는 본 모듈에 박지 않는다. AI 도구(compareDisclosure) 또는 L2
분석엔진(analysis disclosureDelta·scan watch)이 본 diff 결과 위에서 분류한다.

입력원은 panel(sectionLeaf/contentRaw/period) 단일 SSOT이다.
"""

from __future__ import annotations

import difflib

import polars as pl


def diffDisclosure(
    code: str,
    periodA: str,
    periodB: str,
    *,
    maxSampleLines: int = 5,
    longDf: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """두 period 의 동일 sectionLeaf 별 sentence-level diff (panel 본문).

    Args:
        code: 6 자리 종목코드 (예: ``"005930"``).
        periodA: N-1 기 panel period (예: ``"2024Q3"``).
        periodB: N 기 panel period (예: ``"2025Q3"``).
        maxSampleLines: section 별 added/removed sample line 최대 수 (기본 5).
        longDf: panel long override (테스트용). None 이면 ``panel.read.readLong`` 호출.

    Returns:
        pl.DataFrame — sectionOrder · sectionTitle · addedLineCount · removedLineCount ·
        intensityScore(added+removed) · addedSampleLines · removedSampleLines.
        intensityScore 내림차순(가장 큰 변화 섹션이 먼저). diff 0 이면 빈 프레임.

    Raises:
        ValueError: periodA 또는 periodB 의 본문 행 0 — 가용 period enum 노출.

    Example:
        >>> diffDisclosure("005930", "2024Q3", "2025Q3")  # doctest: +SKIP
    """
    df = longDf
    if df is None:
        from dartlab.providers.dart.panel.read import readLong

        df = readLong(code, periods=[periodA, periodB])
    if df is None or df.is_empty():
        raise ValueError(f"panel 본문 없음: code={code}")

    sectionsA = _sectionsForPeriod(df, periodA, "periodA")
    sectionsB = _sectionsForPeriod(df, periodB, "periodB")
    common = sorted(set(sectionsA) & set(sectionsB), key=lambda s: sectionsB[s][0])

    rows: list[dict] = []
    for sectionTitle in common:
        orderA, textA = sectionsA[sectionTitle]
        orderB, textB = sectionsB[sectionTitle]
        if not textA and not textB:
            continue
        addedLines: list[str] = []
        removedLines: list[str] = []
        for line in difflib.unified_diff(textA.split("\n"), textB.split("\n"), lineterm="", n=0):
            if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
                continue
            stripped = line[1:].strip()
            if not stripped:
                continue
            if line.startswith("+"):
                addedLines.append(stripped)
            elif line.startswith("-"):
                removedLines.append(stripped)
        if not addedLines and not removedLines:
            continue
        rows.append(
            {
                "sectionOrder": int(orderB),
                "sectionTitle": sectionTitle,
                "addedLineCount": len(addedLines),
                "removedLineCount": len(removedLines),
                "intensityScore": len(addedLines) + len(removedLines),
                "addedSampleLines": addedLines[:maxSampleLines],
                "removedSampleLines": removedLines[:maxSampleLines],
            }
        )

    if not rows:
        return pl.DataFrame(
            schema={
                "sectionOrder": pl.Int64,
                "sectionTitle": pl.Utf8,
                "addedLineCount": pl.Int64,
                "removedLineCount": pl.Int64,
                "intensityScore": pl.Int64,
                "addedSampleLines": pl.List(pl.Utf8),
                "removedSampleLines": pl.List(pl.Utf8),
            }
        )
    return pl.DataFrame(rows).sort("intensityScore", descending=True)


def _sectionsForPeriod(df: pl.DataFrame, period: str, label: str) -> dict[str, tuple[int, str]]:
    """panel long → ``{sectionLeaf: (sortOrder, 본문)}`` (한 period, 블록 contentRaw 결합)."""
    sub = df.filter(pl.col("period") == period)
    if sub.is_empty():
        available = sorted(df["period"].unique().to_list())
        raise ValueError(f"{label}='{period}' 매칭 본문 없음. 가용: {available}")
    orderCol = "blockOrder" if "blockOrder" in sub.columns else None
    out: dict[str, tuple[int, list[str]]] = {}
    order = 0
    for row in sub.iter_rows(named=True):
        title = row.get("sectionLeaf") or ""
        if not title:
            continue
        content = row.get("contentRaw") or ""
        ordVal = row.get(orderCol) if orderCol else None
        ordInt = int(ordVal) if ordVal is not None else order
        if title not in out:
            out[title] = (ordInt, [])
        out[title][1].append(content)
        order += 1
    return {title: (ordInt, "\n".join(parts)) for title, (ordInt, parts) in out.items()}


__all__ = ["diffDisclosure"]
