"""sections 정밀도 진단 — textPath depth + mapping rate + chapter dedup 손실량.

3 지표 측정 baseline. 각 지표 자체는 *의미 변경 0* — 현재 동작의 정밀도 수준을
박제하고, 후속 PR 에서 정밀도 향상 시 본 baseline 위 회귀 가드로 동작.

지표:
1. textPathDepth — sections() 결과의 textPath 컬럼 " > " split 길이 분포.
   - depth=1 row 비율 (heading 1 단계만 살아남은 row)
   - depth 평균
   - notes topic (financialNotes/consolidatedNotes) 의 depth 평균
2. mappingRate — mapper.py 의 mapSectionTitle 매핑률. 원본 section_title 의
   몇 %가 16 canonical topic 으로 매핑되는지.
3. chapterDedup8charLoss — pipeline.py 의 8자 임계 dedup 으로 drop 된 row 수.
   8자 미만 line 만 있는 chapter-only block 의 총 개수.

실행:
    uv run python -X utf8 tests/audit/sectionsPrecisionAudit.py --check
    uv run python -X utf8 tests/audit/sectionsPrecisionAudit.py --write-baseline
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "tests" / "audit" / "_baselines" / "sectionsPrecisionBaseline.json"
DEFAULT_STOCKS = ("005380", "005930", "000660", "035420", "068270")
REGRESSION_TOLERANCE = 0.05


def _textPathDepthStats(df: pl.DataFrame) -> dict[str, float]:
    if "textPath" not in df.columns:
        return {}
    rows = df.select(pl.col("textPath").cast(pl.Utf8))
    depths: list[int] = []
    notesDepths: list[int] = []
    notesTopics = {"financialNotes", "consolidatedNotes"}
    topicCol = df["topic"].cast(pl.Utf8).to_list() if "topic" in df.columns else [""] * df.height
    pathList = rows["textPath"].to_list()
    for path, topic in zip(pathList, topicCol, strict=False):
        if not path:
            continue
        depth = len([s for s in path.split(" > ") if s.strip()])
        depths.append(depth)
        if topic in notesTopics:
            notesDepths.append(depth)
    if not depths:
        return {"depthRows": 0}
    depth1Count = sum(1 for d in depths if d == 1)
    return {
        "depthRows": len(depths),
        "depthMean": round(sum(depths) / len(depths), 2),
        "depth1Ratio": round(depth1Count / len(depths), 3),
        "notesDepthMean": round(sum(notesDepths) / len(notesDepths), 2) if notesDepths else 0.0,
        "notesRows": len(notesDepths),
    }


def _mappingRate(stockCode: str) -> dict[str, float | int]:
    from dartlab.core.dataLoader import loadData
    from dartlab.providers.dart.docs.sectionsArchive.mapper import measureMappingRate

    df = loadData(stockCode, category="docs", columns=["section_title"])
    if df is None or df.is_empty():
        return {}
    titles = [t for t in df["section_title"].to_list() if isinstance(t, str)]
    result = measureMappingRate(titles)
    return {
        "total": int(result.get("total", 0)),
        "mapped": int(result.get("mapped", 0)),
        "rate": round(float(result.get("rate", 0.0)), 2),
        "unmappedUnique": len(result.get("unmapped_top", [])),
    }


def _chapter8charLossCount(stockCode: str) -> int:
    """8 자 미만 line 만 있는 chapter-only block 의 개수 측정.

    pipeline 의 chapter dedup 로직을 흉내내어, chapter row 본문 안 ``_splitContentBlocks``
    결과 중 모든 line < 8 자인 block 만 카운트. sub-section 과 비교는 안 함 (전체 후보).
    """
    from dartlab.core.dataLoader import loadData
    from dartlab.providers.dart.docs.sectionsArchive.chunker import parseMajorNum
    from dartlab.providers.dart.docs.sectionsArchive.reportRows import _splitContentBlocks
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBase import detectContentCol

    try:
        df = loadData(stockCode, category="docs", columns=["section_title", "section_content", "content"])
    except (FileNotFoundError, ValueError):
        return 0
    if df is None or df.is_empty():
        return 0
    ccol = detectContentCol(df)
    count = 0
    for title, content in zip(df["section_title"].to_list(), df[ccol].to_list(), strict=False):
        if not isinstance(title, str) or not isinstance(content, str):
            continue
        if parseMajorNum(title.strip()) is None:
            continue
        for _blockType, blockText in _splitContentBlocks(content):
            lines = [ln.strip() for ln in blockText.splitlines() if ln.strip()]
            if not lines:
                continue
            if all(len(ln) < 8 for ln in lines):
                count += 1
    return count


def precisionAuditPerStock(stockCode: str) -> dict[str, object] | None:
    from dartlab.providers.dart.docs.sectionsArchive.pipeline import sections

    try:
        df = sections(stockCode, topics=None)
    except (FileNotFoundError, ValueError):
        return None
    if df is None or df.is_empty():
        return None
    return {
        "textPath": _textPathDepthStats(df),
        "mapping": _mappingRate(stockCode),
        "chapter8charLoss": _chapter8charLossCount(stockCode),
    }


def _loadBaseline() -> dict[str, dict] | None:
    if not BASELINE_PATH.exists():
        return None
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _writeBaseline(report: dict[str, dict]) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.stderr.write(f"[sectionsPrecisionAudit] baseline 박제 → {BASELINE_PATH.relative_to(REPO_ROOT)}\n")


def _checkAgainstBaseline(current: dict[str, dict], baseline: dict[str, dict]) -> list[str]:
    errors: list[str] = []
    for stockCode, cur in current.items():
        if stockCode not in baseline:
            sys.stderr.write(f"[sectionsPrecisionAudit] WARN {stockCode}: baseline 부재\n")
            continue
        base = baseline[stockCode]
        baseRate = float(base.get("mapping", {}).get("rate", 100.0))
        curRate = float(cur.get("mapping", {}).get("rate", 100.0))
        if curRate < baseRate - REGRESSION_TOLERANCE * 100:
            errors.append(f"{stockCode}: mappingRate {curRate:.1f} < baseline {baseRate:.1f} - 5%")
        baseDepth = float(base.get("textPath", {}).get("depthMean", 0.0))
        curDepth = float(cur.get("textPath", {}).get("depthMean", 0.0))
        if baseDepth > 0 and curDepth < baseDepth * (1 - REGRESSION_TOLERANCE):
            errors.append(f"{stockCode}: textPath depthMean {curDepth:.2f} < baseline {baseDepth:.2f} × 0.95")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stocks", default=",".join(DEFAULT_STOCKS))
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--check", action="store_true", default=True)
    args = parser.parse_args()

    stocks = [s.strip() for s in args.stocks.split(",") if s.strip()]
    report: dict[str, dict] = {}

    for stockCode in stocks:
        result = precisionAuditPerStock(stockCode)
        if result is None:
            sys.stderr.write(f"[sectionsPrecisionAudit] SKIP {stockCode}: data 부재\n")
            continue
        report[stockCode] = result
        tp = result["textPath"]
        mp = result["mapping"]
        loss = result["chapter8charLoss"]
        sys.stderr.write(
            f"[sectionsPrecisionAudit] {stockCode}: depth={tp.get('depthMean')} "
            f"depth1Ratio={tp.get('depth1Ratio')} notesDepth={tp.get('notesDepthMean')} "
            f"mappingRate={mp.get('rate')}% chapter8charLoss={loss}\n"
        )

    if args.write_baseline:
        _writeBaseline(report)
        return 0
    if not report:
        sys.stderr.write("[sectionsPrecisionAudit] WARN: 측정 0 건 — exit 0\n")
        return 0
    baseline = _loadBaseline()
    if baseline is None:
        sys.stderr.write("[sectionsPrecisionAudit] WARN: baseline 부재 — --write-baseline 후 재실행\n")
        return 0
    errors = _checkAgainstBaseline(report, baseline)
    if errors:
        sys.stderr.write("[sectionsPrecisionAudit] FAIL — 정밀도 회귀:\n")
        for line in errors:
            sys.stderr.write(f"  - {line}\n")
        return 1
    sys.stderr.write(f"[sectionsPrecisionAudit] PASS — {len(report)}/{len(stocks)} 종목 통과\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
