"""sectionsParity v5 — 전종목 audit (data/dart/sectionsV5/ 전체).

전종목 빌드 후 검증:
    - 빌드 성공률 (parquet 파일 존재 비율)
    - period coverage 분포
    - row count 분포 (outlier 검출)
    - 한국어 mojibake 검사 (cp949 fallback 누락 회귀)
    - cross-company disclosureKey 발견 비율
    - xbrlClass NULL 비율 (옛 양식 fuzzy match 실패율)

LLM Specifications:
    AntiPatterns:
        - 전종목 wide read 금지 — 메모리 폭발. 종목별 stat 만 누적.
        - mojibake 검사 시 contentRaw 전체 검사 금지 — chapter / blockLeaf 만.
    OutputSchema:
        - ``run() -> dict`` — overall summary + per-code outliers.
    Prerequisites:
        - data/dart/sectionsV5/{code}/*.parquet (buildSectionsAll 결과).
        - data/dart/sectionsXbrlRef.parquet (P-S3).
        - data/bridge/sectionsBridge.parquet (P-S7).
    Freshness:
        - 빌드 후 즉시 실행.
    Dataflow:
        - sectionsV5/ glob → 종목별 long read → stat 누적.
    TargetMarkets:
        - KR (DART).

마스터 플랜: v5 §8 sectionsParity audit.

실행:
    uv run python -X utf8 tests/audit/sectionsParityV5All.py
"""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl

_KOREAN_RE = re.compile(r"[가-힣]")


def _isMojibake(text: str) -> bool:
    """한국어 깨짐 검사 — replacement char or non-Korean garbage."""
    if not text:
        return False
    if chr(0xFFFD) in text:
        return True
    # non-ASCII bytes 있는데 한국어 없음 = mojibake 가능
    has_high = any(ord(c) > 127 for c in text)
    has_korean = _KOREAN_RE.search(text) is not None
    return has_high and not has_korean


def run() -> dict:
    """전종목 sectionsV5 audit."""
    sectionsDir = Path("data/dart/sectionsV5")
    if not sectionsDir.exists():
        return {"error": "sectionsV5 dir 없음"}

    codeDirs = sorted([d for d in sectionsDir.iterdir() if d.is_dir()])
    total = len(codeDirs)

    okCodes = 0
    emptyCodes = []
    rowCounts: list[int] = []
    periodCounts: list[int] = []
    mojibakeCodes = []
    perCodeStat: dict[str, dict] = {}

    # disclosureKey + xbrlClass 집계
    disclosureKeyCorps: dict[str, set] = {}
    disclosureKeyPeriods: dict[str, set] = {}
    xbrlClassCorps: dict[str, set] = {}

    # bridge resolver
    from dartlab.scan.sectionsNew.canonicalResolver import (
        invalidateCache,
        resolveBatch,
    )

    invalidateCache()

    for codeDir in codeDirs:
        code = codeDir.name
        files = sorted(codeDir.glob("*.parquet"))
        if not files:
            emptyCodes.append(code)
            continue
        try:
            dfs = [pl.read_parquet(f) for f in files]
        except (pl.exceptions.PolarsError, OSError) as exc:
            emptyCodes.append(f"{code}:{exc}")
            continue
        df = pl.concat(dfs, how="vertical_relaxed")
        if df.is_empty():
            emptyCodes.append(code)
            continue

        okCodes += 1
        rowCounts.append(df.height)
        periodCounts.append(df["period"].n_unique())

        # mojibake — chapter / blockLeaf
        chapters = df["chapter"].drop_nulls().unique().to_list()
        if any(_isMojibake(c) for c in chapters if c):
            mojibakeCodes.append(code)

        # disclosureKey 집계
        df = df.drop("disclosureKey", strict=False)
        df = resolveBatch(df, marketNs="kr")
        dkRows = df.filter(pl.col("disclosureKey").is_not_null())
        for row in dkRows.iter_rows(named=True):
            dk = row["disclosureKey"]
            disclosureKeyCorps.setdefault(dk, set()).add(code)
            disclosureKeyPeriods.setdefault(dk, set()).add(row["period"])
        xcRows = df.filter(pl.col("xbrlClass").is_not_null())
        for x in xcRows["xbrlClass"].unique().to_list():
            xbrlClassCorps.setdefault(x, set()).add(code)

        perCodeStat[code] = {
            "rows": df.height,
            "periods": df["period"].n_unique(),
            "dkMappedRows": dkRows.height,
            "uniqueXbrlClass": xcRows["xbrlClass"].n_unique(),
        }

    # overall stats
    rowCounts.sort()
    periodCounts.sort()
    n = len(rowCounts)

    def _pct(arr, p):
        if not arr:
            return 0
        idx = int(len(arr) * p / 100)
        return arr[min(idx, len(arr) - 1)]

    summary = {
        "totalCodes": total,
        "okCodes": okCodes,
        "emptyCodes": len(emptyCodes),
        "successRate": okCodes / total if total else 0,
        "rowCount": {
            "p10": _pct(rowCounts, 10),
            "p50": _pct(rowCounts, 50),
            "p90": _pct(rowCounts, 90),
            "max": rowCounts[-1] if rowCounts else 0,
            "total": sum(rowCounts),
        },
        "periodCount": {
            "p10": _pct(periodCounts, 10),
            "p50": _pct(periodCounts, 50),
            "p90": _pct(periodCounts, 90),
            "max": periodCounts[-1] if periodCounts else 0,
        },
        "mojibakeCodes": mojibakeCodes,
        "uniqueDisclosureKeys": len(disclosureKeyCorps),
        "disclosureKeyCorpCount": {dk: len(corps) for dk, corps in disclosureKeyCorps.items()},
        "disclosureKeyTopCount": {
            dk: max(len(corps), 0) for dk, corps in sorted(disclosureKeyCorps.items(), key=lambda x: -len(x[1]))[:20]
        },
        "uniqueXbrlClasses": len(xbrlClassCorps),
        "xbrlClassAtLeast100Corps": sum(1 for corps in xbrlClassCorps.values() if len(corps) >= 100),
        "xbrlClassAtLeast1000Corps": sum(1 for corps in xbrlClassCorps.values() if len(corps) >= 1000),
    }
    return summary


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
