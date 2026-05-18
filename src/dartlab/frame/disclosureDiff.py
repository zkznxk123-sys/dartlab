"""disclosureDiff — DART 공시 본문 시계열 sentence-level diff.

같은 회사의 두 보고서 (예: 2024.09 분기보고서 vs 2025.09 분기보고서) 의
section_title 매칭 후 section_content 의 unified diff 를 산출한다. 외부 LLM
은 PDF/HTML 단발 만 보고 동일 회사 시계열 비교를 하지 않는다 — 본 모듈은
dartlab 의 DART 공시 시계열 parquet 자산 (gather.dartDoc 산출물) 위에서만
성립하는 *시계열 diff* 의 가공 표면이다.

L1.5 frame 책임 — raw 결합 → 분석 ready. 의미 분류 (가이던스 방향·리스크
추가·회계정책 변경) 는 본 모듈에 박지 않는다. AI 도구 (compareDisclosure)
또는 L2 분석엔진이 본 diff 결과 위에서 분류한다.
"""

from __future__ import annotations

import difflib
from pathlib import Path

import polars as pl

_FIXTURE_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "dart" / "docs"


def diffDisclosure(
    stockCode: str,
    periodA: str,
    periodB: str,
    *,
    fixturePath: Path | None = None,
    maxSampleLines: int = 5,
) -> pl.DataFrame:
    """두 보고서의 동일 section_title 별 sentence-level diff.

    Parameters
    ----------
    stockCode : str
        6 자리 종목코드 (예: ``"005930"``).
    periodA : str
        N-1 기 report_type 표기 (예: ``"분기보고서 (2024.09)"``) 또는 안쪽
        분기 표기 (``"2024.09"``) — 후자는 분기보고서 / 반기보고서 / 사업
        보고서 자동 매칭.
    periodB : str
        N 기 report_type. periodA 와 같은 양식.
    fixturePath : Path | None
        테스트용 override. 기본은 ``tests/fixtures/dart/docs/{stockCode}.parquet``.
    maxSampleLines : int
        section 별 added/removed sample line 최대 수 (기본 5).

    Returns
    -------
    pl.DataFrame
        sectionOrder · section_title · addedLineCount · removedLineCount ·
        intensityScore (added+removed) · addedSampleLines · removedSampleLines.
        intensityScore 내림차순 정렬 — 가장 큰 변화 섹션이 먼저.

    Raises
    ------
    FileNotFoundError
        ``{stockCode}.parquet`` 없음.
    ValueError
        periodA 또는 periodB 매칭 보고서 없음 — 가용 보고서 enum 노출.
    """
    docsPath = (fixturePath or _FIXTURE_DIR) / f"{stockCode}.parquet"
    if not docsPath.exists():
        raise FileNotFoundError(f"공시 본문 parquet 없음: {docsPath}")
    df = pl.read_parquet(docsPath)
    aFrame = _selectReport(df, periodA, "periodA")
    bFrame = _selectReport(df, periodB, "periodB")

    sectionsA = {row["section_title"]: (row["section_order"], row["section_content"] or "") for row in aFrame.iter_rows(named=True)}
    sectionsB = {row["section_title"]: (row["section_order"], row["section_content"] or "") for row in bFrame.iter_rows(named=True)}
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


def _selectReport(df: pl.DataFrame, period: str, label: str) -> pl.DataFrame:
    """``report_type`` 정확 매칭 또는 분기 표기 (예: ``"2024.09"``) 매칭."""
    direct = df.filter(pl.col("report_type") == period)
    if direct.height:
        return direct.sort("section_order")
    contains = df.filter(pl.col("report_type").str.contains(period, literal=True))
    if contains.height:
        types = contains["report_type"].unique().to_list()
        if len(types) > 1:
            raise ValueError(f"{label}='{period}' 가 {len(types)} 개 보고서에 매칭: {types}. 정확 표기 (예: '분기보고서 (2024.09)') 사용.")
        return contains.sort("section_order")
    available = sorted(df["report_type"].unique().to_list())
    raise ValueError(f"{label}='{period}' 매칭 보고서 없음. 가용: {available}")


__all__ = ["diffDisclosure"]
