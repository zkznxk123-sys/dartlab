"""CompareDisclosure — DART 공시 본문 시계열 diff + 의미 분류 AI 도구.

frame.disclosureDiff 가 순수 sentence diff 를 가공. 본 도구는 그 위에서
*의미 분류* (가이던스 방향 · 리스크 추가 · 회계정책 변경 · 사업 라인 변경)
키워드 매칭을 수행하고 ``disclosureRef`` ref 발급 + 답변 chip 신호를 만든다.

외부 LLM 차별화 — Bloomberg/AlphaSense/Tegus 는 PDF/HTML 단발 만 본다.
동일 회사 N-1 vs N 시계열 비교는 dartlab 의 DART 공시 parquet 자산이 있어야
한다. 도구 결과는 finance 사용자 (애널리스트·PB) 가 매분기 손으로 하던
"이번에 새로 추가된 리스크 / 가이던스 변화" 식별 작업을 자동화한다.
"""

from __future__ import annotations

from typing import Any

from dartlab.ai.contracts import Ref

from .types import ToolResult

# 의미 분류 키워드 - L1.5 frame 밖 (룰 매칭은 frame 금지) AI 도구 안에 둔다.
_KEYWORDS: dict[str, tuple[str, ...]] = {
    "guidanceUp": ("성장", "확대", "증가", "개선", "회복", "상향", "호조", "강화"),
    "guidanceDown": ("감소", "둔화", "위축", "악화", "하향", "축소", "부진", "약세"),
    "riskAdded": ("위험", "리스크", "우려", "악재", "불확실", "소송", "분쟁"),
    "accountingChange": ("회계정책", "추정 변경", "회계 변경", "회계처리", "재무제표 재작성", "정정공시"),
    "businessLineShift": ("신사업", "신규 사업", "사업 철수", "분할", "합병", "양도", "인수"),
}


def compareDisclosure(
    stockCode: str,
    periodA: str,
    periodB: str,
    *,
    topN: int = 10,
) -> ToolResult:
    """N-1 vs N 분기 공시 본문 diff + 의미 분류.

    Parameters
    ----------
    stockCode : str
        6 자리 종목코드.
    periodA : str
        N-1 기 표기 (예: ``"2024.09"`` 또는 ``"분기보고서 (2024.09)"``).
    periodB : str
        N 기 표기. periodA 와 같은 양식.
    topN : int
        intensityScore 상위 N 섹션만 의미 분류 (기본 10).

    Returns
    -------
    ToolResult
        ok=True 면 ``data`` 에 ``topSections`` (list[dict]) +
        ``semanticTagCounts`` (dict[str, int]) + chip 권장 문자열.
        refs 에 ``disclosureRef`` 1 개 발급 — payload 에 분류 결과 요약.
    """
    try:
        from dartlab.frame.disclosureDiff import diffDisclosure
    except ImportError as exc:
        return ToolResult(False, "frame.disclosureDiff import 실패", error=f"import_error: {exc}")

    try:
        diff = diffDisclosure(str(stockCode), str(periodA), str(periodB))
    except FileNotFoundError as exc:
        return ToolResult(False, f"공시 본문 자산 없음: {stockCode}", error=f"docs_not_found: {exc}")
    except ValueError as exc:
        return ToolResult(False, str(exc), error="period_not_found")
    except Exception as exc:  # noqa: BLE001
        return ToolResult(False, f"diff 실패: {type(exc).__name__}", error=f"diff_failed: {exc}")

    if diff.height == 0:
        return ToolResult(
            True,
            f"{stockCode} {periodA} → {periodB}: 변화 0 (동일 본문)",
            data={"topSections": [], "semanticTagCounts": {}, "chipText": ""},
        )

    topRows = diff.head(int(topN)).to_dicts()
    tagCounts: dict[str, int] = dict.fromkeys(_KEYWORDS, 0)
    sectionTags: list[dict[str, Any]] = []
    for row in topRows:
        added = row.get("addedSampleLines") or []
        removed = row.get("removedSampleLines") or []
        section_tags = _classifyChange(added, removed)
        for tag in section_tags:
            tagCounts[tag] = tagCounts.get(tag, 0) + 1
        sectionTags.append(
            {
                "sectionTitle": row["sectionTitle"],
                "intensityScore": row["intensityScore"],
                "addedLineCount": row["addedLineCount"],
                "removedLineCount": row["removedLineCount"],
                "semanticTags": sorted(section_tags),
                "addedSamplePreview": (added[:2] if added else []),
                "removedSamplePreview": (removed[:2] if removed else []),
            }
        )

    chipText = _buildChip(tagCounts, len(topRows))
    summary = (
        f"{stockCode} {periodA} → {periodB}: 변화 {diff.height} 섹션, "
        f"top {len(topRows)} 분류 — " + ", ".join(f"{k}={v}" for k, v in tagCounts.items() if v > 0)
    )
    ref = Ref(
        id=f"disclosureDiff:{stockCode}:{periodA}->{periodB}",
        kind="disclosureRef",
        title=f"공시 diff · {stockCode} · {periodA} → {periodB}",
        source="frame.disclosureDiff",
        payload={
            "stockCode": stockCode,
            "periodA": periodA,
            "periodB": periodB,
            "sectionChanged": int(diff.height),
            "topSections": [s["sectionTitle"] for s in sectionTags],
            "semanticTagCounts": tagCounts,
            "chipText": chipText,
            "intensityTotal": int(diff["intensityScore"].sum()),
            "confidence": 90,
            "confidenceMethod": "deterministic",
            "dataAsOf": periodB,
        },
        sourceType="internal",
    )
    return ToolResult(
        True,
        summary,
        data={
            "topSections": sectionTags,
            "semanticTagCounts": tagCounts,
            "chipText": chipText,
            "sectionChanged": int(diff.height),
        },
        refs=[ref],
    )


def _classifyChange(added: list[str], removed: list[str]) -> set[str]:
    """sample line 안 키워드 매칭으로 semantic tag 집합 반환."""
    tags: set[str] = set()
    addedText = " ".join(added).lower()
    removedText = " ".join(removed).lower()
    for tag, kws in _KEYWORDS.items():
        addedHit = any(kw in addedText for kw in kws)
        removedHit = any(kw in removedText for kw in kws)
        if tag == "guidanceUp" and addedHit:
            tags.add(tag)
        elif tag == "guidanceDown" and addedHit:
            tags.add(tag)
        elif tag == "riskAdded" and addedHit and not removedHit:
            tags.add(tag)
        elif tag == "accountingChange" and (addedHit or removedHit):
            tags.add(tag)
        elif tag == "businessLineShift" and (addedHit or removedHit):
            tags.add(tag)
    return tags


def _buildChip(tagCounts: dict[str, int], topNCount: int) -> str:
    """답변 헤더용 chip 문자열 — 분류 카운트 요약."""
    activeTags = {k: v for k, v in tagCounts.items() if v > 0}
    if not activeTags:
        return ""
    labelMap = {
        "guidanceUp": "가이던스 상향",
        "guidanceDown": "가이던스 하향",
        "riskAdded": "리스크 추가",
        "accountingChange": "회계정책 변경",
        "businessLineShift": "사업 라인 변경",
    }
    parts = [f"{labelMap.get(k, k)} {v}곳" for k, v in activeTags.items()]
    return "📋 공시 diff: " + " · ".join(parts) + " [conf:90]"


__all__ = ["compareDisclosure"]
