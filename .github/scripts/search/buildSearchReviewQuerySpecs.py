"""Build diversified query specs for search quality review packs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

FILING_TITLE_QUERIES: tuple[str, ...] = (
    "유상증자 공시 원문",
    "무상증자 결정 공시",
    "전환사채 발행 결정",
    "신주인수권부사채 발행",
    "자기주식 취득 결정",
    "자기주식 처분 결정",
    "현금배당 결정",
    "주식배당 결정",
    "대표이사 변경",
    "최대주주 변경 공시",
    "주주총회 소집 의안",
    "정기주주총회 결과",
    "감사보고서 제출",
    "사업보고서 제출",
    "분기보고서 제출",
    "반기보고서 제출",
    "단일판매 공급계약 체결",
    "대규모 수주 계약 공시",
    "타법인 주식 취득 결정",
    "타법인 주식 처분 결정",
    "회사합병 결정 주요사항보고서",
    "회사분할 결정 공시",
    "영업양수도 결정",
    "유형자산 양수 결정",
    "유형자산 처분 결정",
    "소송 등의 제기 신청",
    "횡령 배임 혐의 발생",
    "영업정지 공시",
    "회생절차 개시 신청",
    "상장폐지 관련 공시",
    "투자판단 관련 주요경영사항",
    "대량보유 지분 변동 보고",
)

FILING_CONTENT_QUERIES: tuple[str, ...] = (
    "환율 리스크 사업보고서 본문",
    "반도체 HBM 투자 사업의 내용",
    "우발부채 소송 충당부채 주석",
    "매출채권 대손충당금 주석",
    "재고자산 평가손실 주석",
    "연구개발비 증가 사업보고서",
    "수주잔고 감소 사업보고서",
    "원재료 가격 상승 위험요인",
    "금리 변동 위험 사업보고서",
    "유동성 위험 관리 주석",
    "특수관계자 거래 주석",
    "종속기업 투자 손상 주석",
    "영업권 손상차손 주석",
    "계속기업 불확실성 감사보고서",
    "내부회계관리제도 검토의견",
    "환경 규제 위험 사업보고서",
    "사이버 보안 위험 사업보고서",
    "고객사 집중도 위험요인",
    "해외 매출 비중 사업의 내용",
    "CAPEX 설비투자 계획 사업보고서",
    "배터리 소재 투자 사업의 내용",
    "AI 데이터센터 투자 사업보고서",
    "부동산 PF 우발채무 주석",
    "파생상품 평가손익 주석",
    "매출 인식 정책 주석",
    "리스부채 만기 분석 주석",
    "법인세 불확실성 주석",
    "퇴직급여 확정급여채무 주석",
    "공정가치 서열체계 주석",
    "현금흐름 악화 원인 사업보고서",
    "신규 사업 추진 위험요인",
    "해외 법인 손실 사업보고서",
)

NEWS_QUERIES: tuple[str, ...] = (
    "공시 말고 뉴스로 반도체 투자",
    "공시 말고 뉴스로 환율 기사",
    "뉴스 기사 AI 반도체 수출",
    "뉴스로 배터리 소재 투자",
    "뉴스로 HBM 공급 계약",
    "뉴스로 미국 금리 영향",
    "뉴스로 원달러 환율 급등",
    "뉴스로 실적 전망 하향",
    "뉴스로 자사주 매입 발표",
    "뉴스로 대규모 수주 소식",
    "뉴스로 공장 증설 발표",
    "뉴스로 구조조정 기사",
    "뉴스로 검찰 수사 이슈",
    "뉴스로 소송 분쟁 이슈",
    "뉴스로 경영권 분쟁",
    "뉴스로 배당 확대 발표",
    "뉴스로 신제품 출시",
    "뉴스로 해외 진출",
    "뉴스로 공급망 차질",
    "뉴스로 유가 상승 영향",
    "뉴스로 전기차 수요 둔화",
    "뉴스로 데이터센터 투자",
    "뉴스로 바이오 임상 결과",
    "뉴스로 건설 수주",
)

EDGAR_QUERIES: tuple[str, ...] = (
    "EDGAR 10-K risk factors",
    "EDGAR revenue recognition liquidity",
    "management discussion and analysis cash flow",
    "EDGAR goodwill impairment risk",
    "EDGAR supply chain disruption risk",
    "EDGAR cybersecurity incident risk",
    "EDGAR foreign exchange risk factors",
    "EDGAR interest rate risk disclosure",
    "EDGAR segment revenue discussion",
    "EDGAR restructuring charges",
    "EDGAR legal proceedings note",
    "EDGAR critical accounting estimates",
    "EDGAR material weakness internal control",
    "EDGAR debt maturity liquidity",
    "EDGAR customer concentration risk",
    "EDGAR inventory impairment",
    "EDGAR capital expenditures outlook",
    "EDGAR share repurchase program",
    "EDGAR dividend policy discussion",
    "EDGAR pending acquisition risk",
    "EDGAR climate regulation risk",
    "EDGAR tax contingency disclosure",
    "EDGAR operating lease obligations",
    "EDGAR derivative hedging disclosure",
)

NO_ANSWER_QUERIES: tuple[str, ...] = (
    "없는회사 2099년 합병 공시",
    "zzqwvxnotlistedalpha999",
    "가상의기업 2098년 유상증자 공시",
    "테스트없는회사 2097년 대표이사 변경",
    "nonexistenttickerxyz 2099 10-K risk factors",
    "없는상장사 2096년 반도체 수주",
    "허구회사 2095년 감사보고서 제출",
    "ghost corporation 2099 liquidity disclosure",
    "공시 말고 뉴스로 zzqwvxnotlistedalpha999",
    "뉴스로 없는회사 2099년 배터리 투자",
    "EDGAR nonexistent issuer 2099 annual report",
    "가짜종목 2099년 상장폐지 공시",
)

KIND_CONFIG: dict[str, dict[str, Any]] = {
    "filingTitle": {"targetKindHint": "filing", "scope": "auto", "queries": FILING_TITLE_QUERIES},
    "filingContent": {"targetKindHint": "filing", "scope": "content", "queries": FILING_CONTENT_QUERIES},
    "news": {"targetKindHint": "news", "scope": "news", "queries": NEWS_QUERIES},
    "edgar": {"targetKindHint": "edgar", "scope": "auto", "queries": EDGAR_QUERIES},
    "noAnswer": {"targetKindHint": "noAnswer", "scope": "auto", "queries": NO_ANSWER_QUERIES},
}

DEFAULT_COUNTS: dict[str, int] = {
    "filingTitle": 28,
    "filingContent": 28,
    "news": 20,
    "edgar": 20,
    "noAnswer": 12,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="Output query spec JSON path")
    parser.add_argument("--total", type=int, default=108, help="Target total specs before de-dupe.")
    parser.add_argument("--counts", help="JSON object or comma list like filingTitle=28,news=20.")
    parser.add_argument(
        "--extra-query-spec", action="append", default=[], help="Additional JSON/JSONL/TXT query specs."
    )
    parser.add_argument("--format", choices=("json", "jsonl"), default="json")
    args = parser.parse_args(argv)

    specs = buildReviewQuerySpecs(
        total=args.total,
        counts=_parseCounts(args.counts),
        extraSpecs=_loadExtraSpecs(args.extra_query_spec),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "jsonl":
        out.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in specs) + "\n", encoding="utf-8"
        )
    else:
        out.write_text(
            json.dumps({"queries": specs, "summary": _summary(specs)}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps({"queryCount": len(specs), "coverage": _coverage(specs)}, ensure_ascii=False, sort_keys=True))
    return 0


def buildReviewQuerySpecs(
    *,
    total: int = 108,
    counts: Mapping[str, int] | None = None,
    extraSpecs: Iterable[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    """Build deterministic, target-balanced review query specs."""
    requested = dict(counts or DEFAULT_COUNTS)
    if counts is None and total != sum(DEFAULT_COUNTS.values()):
        requested = _scaledCounts(total)
    specs: list[dict[str, Any]] = []
    for kind, count in requested.items():
        if count <= 0:
            continue
        config = KIND_CONFIG.get(kind)
        if not config:
            raise ValueError(f"unknown query kind: {kind}")
        for query in _takeCycled(config["queries"], count):
            specs.append(
                {
                    "query": query,
                    "targetKindHint": config["targetKindHint"],
                    "scope": config["scope"],
                    "reviewBucket": kind,
                }
            )
    specs.extend(dict(row) for row in extraSpecs)
    return _dedupeSpecs(specs)


def _scaledCounts(total: int) -> dict[str, int]:
    total = max(1, int(total))
    baseTotal = sum(DEFAULT_COUNTS.values())
    scaled = {kind: max(1, int(count * total / baseTotal)) for kind, count in DEFAULT_COUNTS.items()}
    while sum(scaled.values()) < total:
        for kind in DEFAULT_COUNTS:
            scaled[kind] += 1
            if sum(scaled.values()) >= total:
                break
    while sum(scaled.values()) > total:
        for kind in reversed(DEFAULT_COUNTS):
            if scaled[kind] > 1:
                scaled[kind] -= 1
            if sum(scaled.values()) <= total:
                break
    return scaled


def _takeCycled(values: Sequence[str], count: int) -> list[str]:
    if not values:
        return []
    return [values[index % len(values)] for index in range(count)]


def _dedupeSpecs(specs: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for spec in specs:
        row = dict(spec)
        query = str(row.get("query") or row.get("q") or "").strip()
        if not query or query in seen:
            continue
        row["query"] = query
        seen.add(query)
        out.append(row)
    return out


def _coverage(specs: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in specs:
        target = str(row.get("targetKindHint") or "unknown")
        out[target] = out.get(target, 0) + 1
    return out


def _summary(specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    byBucket: dict[str, int] = {}
    for row in specs:
        bucket = str(row.get("reviewBucket") or "extra")
        byBucket[bucket] = byBucket.get(bucket, 0) + 1
    return {
        "queryCount": len(specs),
        "coverageByTargetHint": _coverage(specs),
        "coverageByReviewBucket": byBucket,
        "releaseEvidence": False,
    }


def _parseCounts(value: str | None) -> dict[str, int] | None:
    if not value:
        return None
    text = value.strip()
    if text.startswith("{"):
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("--counts JSON must be an object")
        return {str(key): int(val) for key, val in data.items()}
    out: dict[str, int] = {}
    for part in text.split(","):
        if not part.strip():
            continue
        key, raw = part.split("=", 1)
        out[key.strip()] = int(raw)
    return out


def _loadExtraSpecs(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        if p.suffix.lower() == ".jsonl":
            rows.extend(_specFromLine(line) for line in text.splitlines() if line.strip())
        elif p.suffix.lower() == ".txt":
            rows.extend({"query": line.strip()} for line in text.splitlines() if line.strip())
        else:
            data = json.loads(text) if text.strip() else []
            if isinstance(data, list):
                rows.extend(_normalizeSpec(item) for item in data)
            elif isinstance(data, dict):
                values = data.get("queries") or data.get("rows") or data.get("querySpecs")
                if not isinstance(values, list):
                    raise ValueError(f"unsupported query spec shape: {p}")
                rows.extend(_normalizeSpec(item) for item in values)
            else:
                raise ValueError(f"unsupported query spec shape: {p}")
    return rows


def _specFromLine(line: str) -> dict[str, Any]:
    text = line.strip()
    if text.startswith("{"):
        return _normalizeSpec(json.loads(text))
    return {"query": text}


def _normalizeSpec(item: Any) -> dict[str, Any]:
    if isinstance(item, str):
        return {"query": item}
    if isinstance(item, Mapping):
        return dict(item)
    raise ValueError(f"unsupported query spec item: {item!r}")


if __name__ == "__main__":
    raise SystemExit(main())
