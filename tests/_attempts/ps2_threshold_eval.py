"""P-S2 threshold evaluation — 옛 양식 TITLE → ref table fuzzy match.

목표: precision ≥ 0.85, recall ≥ 0.70.

알고리즘:
    1. 5 baseline 의 옛 양식 (2023Q3 이전, ATOCID 없음) zip 추출
    2. TABLE-GROUP TITLE + ACLASS 페어 수집
       - ACLASS 있는 페어 = positive sample (trueRawId = stripped ACLASS)
    3. ref table 은 P-S1 결과 (5 baseline 통합) 사용
    4. matchToRef threshold sweep (0.40 ~ 0.95) → precision/recall/F1 측정

실행:
    uv run python -X utf8 tests/_attempts/ps2_threshold_eval.py
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from lxml import etree

from dartlab.providers.dart.docs.sectionsNew.refScan import scanRefBaseline
from dartlab.providers.dart.docs.sectionsNew.refScan.aclassExtractor import _hasATOCID
from dartlab.providers.dart.docs.sectionsNew.refScan.refMatcher import evaluateThreshold

_XBRL_RE = re.compile(r"^\{XBRL\}")
_ATOCID_RE = re.compile(r"<TITLE[^>]*ATOCID=\"\d+\"")


def _stripXbrl(s: str) -> str:
    return _XBRL_RE.sub("", s).strip()


def _readXml(zp: Path) -> str | None:
    try:
        with zipfile.ZipFile(zp) as zf:
            names = [n for n in zf.namelist() if n.endswith(".xml")]
            if not names:
                return None
            with zf.open(names[0]) as f:
                return f.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def collectOldFormatLabeled(codes: list[str], maxPerCode: int = 30) -> list[dict]:
    """옛 양식 zip 에서 (title, true_rawId) 페어 수집.

    옛 양식 = ATOCID 없는 zip. ACLASS 있는 TABLE-GROUP 의 TITLE 을 ground truth
    로 사용 (rawId = ACLASS attribute stripped).
    """
    parser = etree.XMLParser(recover=True, huge_tree=True)
    rows: list[dict] = []
    for code in codes:
        d = Path(f"data/dart/original/docs/{code}")
        zips = sorted(d.glob("*.zip"))
        oldFormatZips: list[Path] = []
        for zp in zips:
            xml = _readXml(zp)
            if not xml:
                continue
            if not _ATOCID_RE.search(xml):
                oldFormatZips.append(zp)
        # 옛 양식 zip 중 가장 최근 (양식 가까운) 2~3 개만
        sampleZips = oldFormatZips[-3:] if len(oldFormatZips) >= 3 else oldFormatZips
        codeSamples: list[dict] = []
        for zp in sampleZips:
            xml = _readXml(zp)
            if not xml:
                continue
            try:
                root = etree.fromstring(xml.encode("utf-8"), parser)
            except Exception:
                continue
            if root is None or _hasATOCID(root):
                continue
            for tg in root.iter("TABLE-GROUP"):
                acls = (tg.get("ACLASS", "") or "").strip()
                if not acls:
                    continue
                rawId = _stripXbrl(acls)
                titleEl = tg.find("./TITLE")
                if titleEl is None:
                    titleEl = tg.find("./HEAD/TITLE")
                if titleEl is None:
                    continue
                title = "".join(titleEl.itertext()).strip()
                if not title:
                    continue
                codeSamples.append({"title": title, "trueRawId": rawId, "code": code, "zip": zp.stem})
                if len(codeSamples) >= maxPerCode:
                    break
            if len(codeSamples) >= maxPerCode:
                break
        rows.extend(codeSamples)
        print(f"  {code}: 옛 양식 zip {len(oldFormatZips)} 중 sample {len(sampleZips)} → {len(codeSamples)} labeled")
    return rows


def main() -> None:
    print("== P-S2: 옛 양식 라벨링 + threshold sweep ==")
    print()
    print("[1] ref table 로드 (P-S1 결과)")
    refDf = scanRefBaseline(
        codes=["005930", "005380", "035720", "207940", "000660"],
        minCorpCount=1,
    )
    print(f"  ref entry: {refDf.height} (corpCount≥1)")
    print(f"  corpCount≥3 SSOT: {refDf.filter(__import__('polars').col('corpCount') >= 3).height}")
    print()
    print("[2] 옛 양식 라벨링 (자동 — ACLASS 있는 옛 양식 row)")
    labeled = collectOldFormatLabeled(
        codes=["005930", "005380", "035720", "207940", "000660"],
        maxPerCode=30,
    )
    print(f"  총 labeled: {len(labeled)}")
    print()
    print("[3] threshold sweep")
    metrics = evaluateThreshold(labeled, refDf)
    print(metrics)
    print()
    # 게이트 검증: precision ≥ 0.85, recall ≥ 0.70
    pass_rows = metrics.filter(
        (__import__("polars").col("precision") >= 0.85) & (__import__("polars").col("recall") >= 0.70)
    )
    print(f"[4] 게이트 통과 threshold: {pass_rows['threshold'].to_list()}")
    if pass_rows.height > 0:
        # F1 최대 선택
        best = pass_rows.sort("f1", descending=True).head(1)
        print(
            f"  best (F1 max): threshold={best['threshold'][0]:.2f} "
            f"precision={best['precision'][0]:.3f} recall={best['recall'][0]:.3f} "
            f"f1={best['f1'][0]:.3f}"
        )
    else:
        print("  게이트 통과 threshold 없음 — ref table 확장 (P-S3) 필요 가능성")


if __name__ == "__main__":
    main()
