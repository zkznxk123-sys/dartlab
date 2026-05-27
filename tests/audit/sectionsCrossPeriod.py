"""cross-period prefix misalignment audit — 같은 row 안 cell 내용이 다른 period 사이
*무관 본문* 인 경우만 실제 misalign 으로 카운트.

알고리즘:
1. sections wide DataFrame 의 각 row 마다 visible period (있는 cell) 들의 본문 prefix
   (period marker strip 후 첫 30 chars 정규화) 추출.
2. 2 개 이상 visible 인 row 에서 prefix 가 모두 다르면 *real misalign* 후보.
3. 단, prefix 중 하나가 다른 prefix 의 superset/subset 이면 (예: Q1 본문이 Q4 본문보다
   짧지만 prefix 일치) 정상 매칭으로 인정.

usage:
    uv run python -X utf8 tests/audit/sectionsCrossPeriod.py --codes 005930,000660 [--strict]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dartlab.core.textNormalize import stripPeriodMarkers  # noqa: E402

_NONWORD_RE = re.compile(r"[\s\.,()()\[\]【】\"'·:;~~\-—_<>/]+")
_PREFIX_LEN = 30
_MIN_LEN = 8


def _prefix(value: str | None) -> str:
    if not value:
        return ""
    stripped = stripPeriodMarkers(value)
    norm = _NONWORD_RE.sub("", stripped).lower()
    if len(norm) < _MIN_LEN:
        return ""
    return norm[:_PREFIX_LEN]


def auditCode(code: str) -> dict:
    """단일 종목 audit — cross-period misalignment 카운트.

    - text block: prefix 첫 30 chars 비교, substring compatible 인정.
    - table block: headerHash 비교 (data row 변동은 정상 — period 별 값만 다른 같은 표).
    """
    from dartlab import Company
    from dartlab.providers.dart.docs.sections.tableParser import tableHeaderHash

    company = Company(code)
    sections = company.sections
    if sections is None:
        return {"code": code, "rows": 0, "misalign": 0, "samples": []}

    periods = [c for c in sections.columns if re.fullmatch(r"\d{4}(?:Q[1-4])?", c)]
    misalign = 0
    samples: list[dict] = []
    rows = sections.height

    for row in sections.iter_rows(named=True):
        cells = {p: row.get(p) for p in periods}
        nonEmpty = {p: v for p, v in cells.items() if v}
        if len(nonEmpty) < 2:
            continue

        if row.get("blockType") == "table":
            # 표는 headerHash 비교 — 같은 hash 면 같은 schema 표 (data 변동 무관).
            hashes = {p: tableHeaderHash(v) for p, v in nonEmpty.items()}
            uniqHashes = set(h for h in hashes.values() if h and h != "empty")
            if len(uniqHashes) <= 1:
                continue
            misalign += 1
            if len(samples) < 5:
                samples.append(
                    {
                        "topic": row["topic"],
                        "blockOrder": row["blockOrder"],
                        "blockType": "table",
                        "segmentKey": row["segmentKey"][:80] if row.get("segmentKey") else None,
                        "hashes": hashes,
                    }
                )
            continue

        # text block — prefix 비교
        prefixes = {p: _prefix(v) for p, v in nonEmpty.items()}
        unique_prefixes = set(p for p in prefixes.values() if p)
        if len(unique_prefixes) < 2:
            continue
        # 한 prefix 가 다른 prefix 의 substring 인 case → 정상 매칭
        sorted_prefixes = sorted(unique_prefixes, key=len)
        all_compatible = True
        shortest = sorted_prefixes[0]
        for longer in sorted_prefixes[1:]:
            if not (shortest in longer or longer in shortest):
                all_compatible = False
                break
        if all_compatible:
            continue
        misalign += 1
        if len(samples) < 5:
            samples.append(
                {
                    "topic": row["topic"],
                    "blockOrder": row["blockOrder"],
                    "blockType": "text",
                    "segmentKey": row["segmentKey"][:80] if row.get("segmentKey") else None,
                    "prefixes": {p: pf for p, pf in prefixes.items()},
                }
            )
    return {"code": code, "rows": rows, "misalign": misalign, "samples": samples}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codes", required=True, help="comma-separated stockCodes")
    parser.add_argument("--strict", action="store_true", help="exit 1 if any code has misalign > 0")
    parser.add_argument("--budget", type=int, default=400, help="per-code misalign 허용 (strict 와 무관, 정보용)")
    args = parser.parse_args()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    total = 0
    results = []
    for code in codes:
        r = auditCode(code)
        results.append(r)
        print(f"[{code}] rows={r['rows']} misalign={r['misalign']} {'OK' if r['misalign'] <= args.budget else 'OVER'}")
        for sample in r["samples"]:
            print(f"  - {sample['topic']}/{sample['blockOrder']} {sample['blockType']}")
            for p, pf in sample["prefixes"].items():
                print(f"    {p}: {pf!r}")
        total += r["misalign"]

    print(f"\n=== TOTAL: {total} cross-period misaligns across {len(codes)} codes ===")
    print(json.dumps({"total": total, "perCode": {r["code"]: r["misalign"] for r in results}}, ensure_ascii=False))

    if args.strict and total > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
