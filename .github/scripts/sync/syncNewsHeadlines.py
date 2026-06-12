"""news headlines forward-only archive cron — Phase A.

Google News RSS daily fan-out (KOSPI200 + 매크로 키워드) → 일별 parquet upsert →
HF push 후보. 본문 archive 영구 제외 (ToS) — 메타데이터 (date/title/source/url +
market/query/captured_at) 만 박는다.

실행::

    uv run python -X utf8 .github/scripts/sync/syncNewsHeadlines.py --market KR --once
    uv run python -X utf8 .github/scripts/sync/syncNewsHeadlines.py --market US --once
    uv run python -X utf8 .github/scripts/sync/syncNewsHeadlines.py --market KR --once --max-queries 30  # smoke

본 도구는 sync/ 카테고리 — online (외부 RSS → 로컬 archive). HF push 는 별도
`.github/scripts/sync/bulkUploadHf.py newsHeadlines --force` 또는 dataSync.yml
Job 자동.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date as _date
from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[3]
_log = logging.getLogger("syncNewsHeadlines")

# 저장 경로·upsert 는 gather.sources.newsIo.writeDailyParquet 공유 (dir SSOT=newsSources).

# 매크로 키워드 — 시장 무관 narrative 시그널 (반복 fetch 안전, RSS 검색 결과 차별화).
_MACRO_KEYWORDS_KR = [
    "한국은행 기준금리",
    "원달러 환율",
    "코스피 지수",
    "코스닥 지수",
    "외국인 매매",
    "기관 매매",
    "삼성전자 실적",
    "SK하이닉스 실적",
    "반도체 업황",
    "조선 수주",
    "자동차 수출",
    "2차전지 수요",
    "바이오 임상",
    "AI 반도체",
    "데이터센터 투자",
    "중국 경제 지표",
    "미중 무역 갈등",
    "지정학 리스크",
    "유가 변동",
    "천연가스 가격",
    "물가 상승률",
    "수출 부진",
    "수입 둔화",
    "경상수지",
    "건설 경기",
    "부동산 시장",
    "가계부채",
    "기업 실적 발표",
    "M&A 동향",
    "IPO 시장",
    "공모주",
    "ETF 자금 유입",
    "공매도 잔고",
    "전기차 배터리",
    "수소 경제",
    "원전 정책",
    "재생에너지",
    "통신 5G",
    "방산 수출",
    "K-콘텐츠",
    "엔터테인먼트 매출",
    "화학 업황",
    "철강 가격",
    "정유 마진",
    "유통 매출",
    "물류 운임",
    "항공 여객",
    "관광 회복",
    "금융지주 실적",
    "보험 손해율",
]

_MACRO_KEYWORDS_US = [
    "Federal Reserve rate decision",
    "FOMC minutes",
    "US CPI inflation",
    "US PCE inflation",
    "US nonfarm payrolls",
    "US unemployment rate",
    "US GDP growth",
    "US retail sales",
    "US ISM manufacturing",
    "US ISM services",
    "US housing starts",
    "US Treasury yield",
    "10-year Treasury",
    "2-year Treasury",
    "US dollar index",
    "VIX volatility",
    "S&P 500 outlook",
    "Nasdaq earnings",
    "Russell 2000",
    "AI semiconductor stocks",
    "Nvidia earnings",
    "Apple revenue",
    "Microsoft cloud",
    "Amazon AWS",
    "Tesla deliveries",
    "Meta advertising",
    "Google search",
    "TSMC capacity",
    "Intel foundry",
    "Boeing orders",
    "China economy",
    "European Central Bank",
    "Bank of Japan policy",
    "yen carry trade",
    "oil price WTI",
    "Brent crude",
    "natural gas LNG",
    "gold price",
    "copper demand",
    "bitcoin price",
    "M&A activity US",
    "IPO market US",
    "private equity",
    "venture capital",
    "high yield spreads",
    "leveraged loans",
    "commercial real estate",
    "regional bank stress",
    "geopolitical risk Middle East",
    "Taiwan strait",
]


def _stockSeedKR(limit: int) -> list[str]:
    """KRX 시총 상위 종목명 추출 — hfBulk.loadFiltered 의 최근 1 일 사용."""
    try:
        from dartlab.gather.bulkData.hfBulk import loadFiltered

        df = loadFiltered(adjustment="raw")
        if df is None or df.is_empty():
            return []
        if "ISU_NM" not in df.columns or "MKTCAP" not in df.columns:
            return []
        # 최근 1 일 + mktcap desc + 종목명 unique
        recent = (
            df.sort("BAS_DD", descending=True)
            .group_by("ISU_CD")
            .agg(
                pl.col("ISU_NM").first(),
                pl.col("MKTCAP").first(),
            )
        )
        names = recent.sort("MKTCAP", descending=True)["ISU_NM"].head(limit).to_list()
        return [n for n in names if n]
    except Exception as exc:
        _log.warning("KRX stock seed 추출 실패: %s — 종목 시드 0 으로 fallback", exc)
        return []


def _stockSeedUS(limit: int) -> list[str]:
    """US 시드 — KRX 와 달리 dartlab 내장 listing 부재. S&P top 30 하드코딩."""
    SP_TOP30 = [
        "Apple stock",
        "Microsoft stock",
        "Nvidia stock",
        "Amazon stock",
        "Google stock",
        "Meta stock",
        "Tesla stock",
        "Berkshire Hathaway stock",
        "JPMorgan Chase stock",
        "Exxon Mobil stock",
        "Eli Lilly stock",
        "UnitedHealth stock",
        "Visa stock",
        "Mastercard stock",
        "Johnson Johnson stock",
        "Procter Gamble stock",
        "Home Depot stock",
        "Bank of America stock",
        "AbbVie stock",
        "Costco stock",
        "Walmart stock",
        "Chevron stock",
        "Merck stock",
        "Coca-Cola stock",
        "Adobe stock",
        "Pfizer stock",
        "PepsiCo stock",
        "Cisco stock",
        "Disney stock",
        "Salesforce stock",
    ]
    return SP_TOP30[:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="news headlines daily archive cron")
    parser.add_argument("--market", choices=["KR", "US"], required=True)
    parser.add_argument("--days", type=int, default=1, help="RSS lookback 윈도우")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--max-queries", type=int, default=200, help="시드 상한 (smoke/test)")
    parser.add_argument("--stock-seed-limit", type=int, default=100, help="시총 상위 N 종목")
    parser.add_argument(
        "--once",
        action="store_true",
        help="1 회 실행 후 종료 (cron 표준). 미지정 시 동일 (placeholder).",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    market = args.market.upper()
    if market == "KR":
        macroSeed = _MACRO_KEYWORDS_KR
        stockSeed = _stockSeedKR(args.stock_seed_limit)
    else:
        macroSeed = _MACRO_KEYWORDS_US
        stockSeed = _stockSeedUS(args.stock_seed_limit)

    queries = list(dict.fromkeys(stockSeed + macroSeed))[: args.max_queries]
    if not queries:
        _log.warning("query 시드 0 — abort (market=%s)", market)
        return 1
    _log.info("market=%s queries=%d (stock=%d, macro=%d)", market, len(queries), len(stockSeed), len(macroSeed))

    from dartlab.gather.sources.news import fetchHeadlinesForArchive

    df = fetchHeadlinesForArchive(
        queries,
        market=market,
        days=args.days,
        concurrency=args.concurrency,
    )
    _log.info("RSS fetch 완료 — %d 헤드라인 (dedup url 적용)", df.height)

    if df.is_empty():
        _log.warning("결과 0 — cache 무변경")
        return 0

    from dartlab.gather.sources.newsIo import writeDailyParquet
    from dartlab.gather.sources.newsSources import getNewsSource

    target, total, added = writeDailyParquet(df, dir=getNewsSource("rss").dir, market=market, day=_date.today())
    _log.info("저장 완료 — %s (total=%d, added=%d)", target, total, added)

    # uploadData.py 호환 changed 리스트
    distDir = REPO_ROOT / "dist"
    distDir.mkdir(parents=True, exist_ok=True)
    (distDir / "changed_newsHeadlines.txt").write_text(
        f"{market}/{_date.today().isoformat()}.parquet\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
