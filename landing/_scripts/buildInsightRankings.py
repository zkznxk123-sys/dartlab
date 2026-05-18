"""인사이트 랭킹 — 200개 회사 JSON 집계 → landing/static/map/insights.json

랭킹:
- 공급망 집중도 (HHI 높은 top 10)
- 공급망 분산 (HHI 낮은 top 10, 정밀 엣지 5건 이상)
- 가장 연결된 기업 (공급사+고객사 합 top 10)
- 산업 다양성 top 10
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPANIES_DIR = ROOT / "landing" / "static" / "map" / "companies"
OUT = ROOT / "landing" / "static" / "map" / "insights.json"


def _brief(data: dict) -> dict:
    """개별 회사 JSON에서 랭킹에 필요한 요약 필드만 추출한다.

    Parameters
    ----------
    data : dict
        회사별 JSON 전체 (ego + supplyInsights 포함).

    Returns
    -------
    dict
        stockCode : str — 종목코드
        corpName : str — 회사명
        industry : str — 산업 ID
        revenue : float | None — 매출 (억원)
        hhi : float — HHI (0~10000)
        hhiRisk : str — 위험 라벨
        supplierCount : int — 공급사 수 (건)
        customerCount : int — 고객사 수 (건)
        preciseEdgeCount : int — 정밀 엣지 수 (건)
        top1Ratio : float — 최대 공급사 비중 (%)
        top3Ratio : float — 상위 3사 비중 (%)
        industryDiversity : int — 공급 산업 다양성 (개)
    """
    ego = data.get("ego", {})
    sup = data.get("supplyInsights", {}) or {}
    return {
        "stockCode": ego.get("stockCode"),
        "corpName": ego.get("corpName"),
        "industry": ego.get("industry"),
        "revenue": ego.get("revenue"),
        "hhi": sup.get("hhi", 0),
        "hhiRisk": sup.get("hhiRisk", ""),
        "supplierCount": sup.get("supplierCount", 0),
        "customerCount": sup.get("customerCount", 0),
        "preciseEdgeCount": sup.get("preciseEdgeCount", 0),
        "top1Ratio": sup.get("top1Ratio", 0),
        "top3Ratio": sup.get("top3Ratio", 0),
        "industryDiversity": sup.get("industryDiversity", 0),
    }


def main() -> None:
    """회사별 JSON을 집계하여 5개 랭킹(집중/분산/연결/다양성/의존도)을 insights.json에 저장한다."""
    files = sorted(COMPANIES_DIR.glob("*.json"))
    entries = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        entries.append(_brief(data))

    print(f"로드: {len(entries)}사")

    # 1. 공급망 집중도 top (HHI 높음) — 정밀 엣지 5건 이상만
    concentrated = sorted(
        [e for e in entries if e["preciseEdgeCount"] >= 5 and e["hhi"] > 0],
        key=lambda e: e["hhi"],
        reverse=True,
    )[:10]

    # 2. 공급망 분산 top (HHI 낮음)
    diversified = sorted(
        [e for e in entries if e["preciseEdgeCount"] >= 5 and e["hhi"] > 0],
        key=lambda e: e["hhi"],
    )[:10]

    # 3. 가장 연결된 기업 (공급사+고객사)
    connected = sorted(
        entries,
        key=lambda e: (e["supplierCount"] + e["customerCount"]),
        reverse=True,
    )[:10]

    # 4. 산업 다양성 top
    diverse_industries = sorted(
        [e for e in entries if e["industryDiversity"] > 0],
        key=lambda e: e["industryDiversity"],
        reverse=True,
    )[:10]

    # 5. 최대 의존도 위험 (top1 ratio 높음)
    dependent = sorted(
        [e for e in entries if e["preciseEdgeCount"] >= 3 and e["top1Ratio"] > 0],
        key=lambda e: e["top1Ratio"],
        reverse=True,
    )[:10]

    out = {
        "totalCompanies": len(entries),
        "rankings": {
            "concentrated": {
                "title": "공급망 집중도 (HHI 높은 기업)",
                "description": "상위 공급사 의존도가 높은 기업. 공급망 리스크 주시.",
                "entries": concentrated,
            },
            "diversified": {
                "title": "공급망 분산 (HHI 낮은 기업)",
                "description": "공급사 다변화가 잘 된 기업. 안정적 공급 구조.",
                "entries": diversified,
            },
            "connected": {
                "title": "가장 연결된 기업",
                "description": "공급사·고객사 수가 많은 허브 기업.",
                "entries": connected,
            },
            "diverseIndustries": {
                "title": "산업 다양성 top",
                "description": "여러 산업에 걸쳐 공급망이 분산된 기업.",
                "entries": diverse_industries,
            },
            "dependent": {
                "title": "최대 의존도 위험",
                "description": "단일 공급사에 매출 비중이 크게 치우친 기업.",
                "entries": dependent,
            },
        },
    }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"생성: {OUT} ({len(out['rankings'])}개 랭킹)")


if __name__ == "__main__":
    main()
