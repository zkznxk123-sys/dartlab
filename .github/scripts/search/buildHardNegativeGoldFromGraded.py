"""Derive a trustworthy hard-negative search gold from the EXISTING human-reviewed graded refs.

Non-circular alternative to ``buildSearchHardNegativeGold.py`` (which mints queries + forbidden refs from the
ranker's own ``EVENT_RULES``/``inferEventRole`` = self-scored gold, a reject-listed methodology). This builder
adds **zero new labels**: every reviewed filing gold row already carries >=2 graded ``expectedSourceRefs`` where
``expectedSourceRef`` is the reviewer-chosen PRIMARY and the rest are acceptable secondaries. From those human grades
it derives forbidden hard-negatives so the release gate's hard-negative metrics (``hardNegativeWinRate`` /
``forbiddenTop1/3/10Rate`` / ``constraintViolationRate``) stop being skipped.

Why: the live release gold (``tests/fixtures/search/queryLogGold.real.jsonl``) has 0 ``forbiddenSourceRefs`` across
all rows, so ``qualityGate`` skips every hard-negative metric (``hardNegativeRows <= 0``). The constraint reranker's
ability to separate near-miss filings is therefore unmeasured. This builder revives that gate from human grades.

Mechanism (deterministic, build-time only, no ranker logic referenced):
  - Group the reviewed filing queries by a CURATED event family (``_FAMILIES`` below; grouping reads only the
    human-written query text, never the ranker's event rules — the non-circular invariant).
  - For each query, ``forbiddenSourceRefs`` = (union of OTHER same-family queries' PRIMARY refs) - (this query's own
    ``expectedSourceRefs``). This is the "right event, wrong specific filing" hard negative, human-grounded.
  - Carry the reviewer ``primaryRef`` so a ``primaryRankWinRate`` (primary ranked at/above its own secondaries) is
    measurable. Provenance (``goldOrigin``/``reviewStatus``) is preserved; the ranker never sees ``expectedSourceRef``.

Output JSONL is consumed unchanged by ``evaluateSearchGold.py`` / ``evaluateQueryGoldRows``.

Sig:
    main(argv: list[str] | None = None) -> int

Example:
    uv run python -X utf8 .github/scripts/search/buildHardNegativeGoldFromGraded.py \
      --gold tests/fixtures/search/queryLogGold.real.jsonl \
      --out tests/fixtures/search/queryLogGold.hardNegative.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ── 큐레이션된 query -> 이벤트 패밀리 (gold-construction artifact; 랭커 EVENT_RULES/inferEventRole 비참조). ──
# tier "event": 혼동 가능한 공시 이벤트(유상↔무상증자, 취득↔처분). tier "note": 같은 보고서종 다른 섹션/토픽.
_FAMILIES: dict[str, dict] = {
    "capital-raise": {
        "tier": "event",
        "queries": ["유상증자 공시 원문", "무상증자 결정 공시", "전환사채 발행 결정", "신주인수권부사채 발행"],
    },
    "treasury-stock": {"tier": "event", "queries": ["자기주식 취득 결정", "자기주식 처분 결정"]},
    "dividend": {"tier": "event", "queries": ["현금배당 결정", "주식배당 결정"]},
    "governance": {
        "tier": "event",
        "queries": ["대표이사 변경", "최대주주 변경 공시", "주주총회 소집 의안", "정기주주총회 결과"],
    },
    "periodic-report": {
        "tier": "event",
        "queries": ["감사보고서 제출", "사업보고서 제출", "분기보고서 제출", "반기보고서 제출"],
    },
    "supply-contract": {"tier": "event", "queries": ["단일판매 공급계약 체결", "대규모 수주 계약 공시"]},
    "other-corp-stake": {"tier": "event", "queries": ["타법인 주식 취득 결정", "타법인 주식 처분 결정"]},
    "restructuring": {
        "tier": "event",
        "queries": ["회사합병 결정 주요사항보고서", "회사분할 결정 공시", "영업양수도 결정"],
    },
    "asset-trade": {"tier": "event", "queries": ["유형자산 양수 결정", "유형자산 처분 결정"]},
    "adverse-event": {"tier": "event", "queries": ["소송 등의 제기 신청", "횡령 배임 혐의 발생", "영업정지 공시"]},
    "note-risk-factor": {
        "tier": "note",
        "queries": [
            "환율 리스크 사업보고서 본문",
            "금리 변동 위험 사업보고서",
            "원재료 가격 상승 위험요인",
            "유동성 위험 관리 주석",
            "환경 규제 위험 사업보고서",
            "사이버 보안 위험 사업보고서",
            "고객사 집중도 위험요인",
        ],
    },
    "note-asset-liability": {
        "tier": "note",
        "queries": [
            "매출채권 대손충당금 주석",
            "재고자산 평가손실 주석",
            "종속기업 투자 손상 주석",
            "영업권 손상차손 주석",
            "부동산 PF 우발채무 주석",
            "리스부채 만기 분석 주석",
            "퇴직급여 확정급여채무 주석",
        ],
    },
    "note-pl-tax": {
        "tier": "note",
        "queries": [
            "우발부채 소송 충당부채 주석",
            "특수관계자 거래 주석",
            "파생상품 평가손익 주석",
            "매출 인식 정책 주석",
            "법인세 불확실성 주석",
        ],
    },
    "note-business-content": {
        "tier": "note",
        "queries": [
            "반도체 HBM 투자 사업의 내용",
            "연구개발비 증가 사업보고서",
            "수주잔고 감소 사업보고서",
            "해외 매출 비중 사업의 내용",
            "배터리 소재 투자 사업의 내용",
        ],
    },
    "note-audit": {"tier": "note", "queries": ["계속기업 불확실성 감사보고서", "내부회계관리제도 검토의견"]},
}


def _familyByQuery() -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for fam, spec in _FAMILIES.items():
        for q in spec["queries"]:
            out[q] = (fam, spec["tier"])
    return out


def deriveHardNegativeRows(goldRows: list[dict]) -> tuple[list[dict], dict]:
    """사람-검수 graded gold 행에서 cross-query-sibling forbidden 을 유도한 (derivedRows, stats).

    Args:
        goldRows: queryLogGold.real.jsonl 파싱 행 리스트.

    Returns:
        (derivedRows, stats) — derivedRows 는 filing 행에 ``forbiddenSourceRefs``/``primaryRef``/``eventFamily``/
        ``familyTier`` 를 추가한 사본(원 provenance 보존). stats 는 substrate 통계.

    Raises:
        없음.

    Example:
        >>> rows, st = deriveHardNegativeRows([])
        >>> st["hardNegativeRows"]
        0
    """
    famOf = _familyByQuery()
    filing = [r for r in goldRows if r.get("targetKind") == "filing"]
    famPrimaries: dict[str, list[tuple[str, str]]] = {}
    for r in filing:
        fam = famOf.get(r["query"])
        if fam:
            famPrimaries.setdefault(fam[0], []).append((r["query"], r.get("expectedSourceRef") or ""))

    derived: list[dict] = []
    sizes: list[int] = []
    byTier = {"event": 0, "note": 0}
    unmapped: list[str] = []
    for r in filing:
        q = r["query"]
        fam = famOf.get(q)
        own = set(r.get("expectedSourceRefs") or [])
        if not fam:
            unmapped.append(q)
            forbidden: list[str] = []
        else:
            sib = {p for (sq, p) in famPrimaries.get(fam[0], []) if sq != q and p}
            forbidden = sorted(sib - own)
        out = dict(r)
        out["forbiddenSourceRefs"] = forbidden
        out["primaryRef"] = r.get("expectedSourceRef") or ""
        if fam:
            out["eventFamily"], out["familyTier"] = fam
        derived.append(out)
        if forbidden:
            sizes.append(len(forbidden))
            if fam:
                byTier[fam[1]] += 1
    sizes.sort()
    stats = {
        "totalFilingRows": len(filing),
        "mappedRows": len(filing) - len(unmapped),
        "hardNegativeRows": len(sizes),
        "hardNegativeRowsByTier": byTier,
        "forbiddenSetSize": {
            "min": sizes[0] if sizes else 0,
            "median": sizes[len(sizes) // 2] if sizes else 0,
            "mean": round(sum(sizes) / len(sizes), 2) if sizes else 0.0,
            "max": sizes[-1] if sizes else 0,
        },
        "unmappedQueries": unmapped,
        "degenerate": not sizes,
    }
    return derived, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", required=True, help="Human-reviewed query-log gold JSONL (input).")
    parser.add_argument("--out", required=True, help="Derived hard-negative gold JSONL (output).")
    parser.add_argument("--summary-out", help="Optional substrate stats JSON path.")
    parser.add_argument("--min-hard-negative-rows", type=int, default=40)
    args = parser.parse_args(argv)

    goldRows = [json.loads(line) for line in Path(args.gold).read_text(encoding="utf-8").splitlines() if line.strip()]
    derived, stats = deriveHardNegativeRows(goldRows)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in derived) + "\n", encoding="utf-8")
    if args.summary_out:
        Path(args.summary_out).write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "hardNegativeRows": stats["hardNegativeRows"],
                "degenerate": stats["degenerate"],
                "byTier": stats["hardNegativeRowsByTier"],
                "out": str(out),
            },
            ensure_ascii=False,
        )
    )
    ok = stats["hardNegativeRows"] >= args.min_hard_negative_rows and not stats["degenerate"]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
