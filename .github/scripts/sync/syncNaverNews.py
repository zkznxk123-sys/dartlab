"""네이버 뉴스 forward-only archive cron — private (언론사 저작권).

네이버 검색 API daily fan-out (KRX 시총상위 + 매크로 키워드, KR 전용) → 일별 parquet
upsert (`data/news/private/naver/`) → private HF push 후보. 제목+스니펫 메타데이터.

⚠ 공개 dartlab-data 안 감 — `repoFor("newsNaver")` = 전용 private repo
(`eddmpython/dartlab-news-private`). 라이선스: 언론사 저작권 비공개 캐시 전용.

실행::

    uv run python -X utf8 .github/scripts/sync/syncNaverNews.py --once
    uv run python -X utf8 .github/scripts/sync/syncNaverNews.py --once --max-queries 30  # smoke

HF push 는 `.github/scripts/sync/bulkUploadHf.py newsNaver --since 86400` (private repo).
syncNewsHeadlines 와 대칭 — KR 시드(매크로 키워드 + 시총상위 종목)를 재사용한다.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date as _date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))  # 동일 dir syncNewsHeadlines 시드 재사용
_log = logging.getLogger("syncNaverNews")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="naver news daily archive cron (private)")
    parser.add_argument("--days", type=int, default=1, help="네이버 lookback 윈도우 (0=cutoff 없음=깊은 백필)")
    parser.add_argument(
        "--pages",
        type=int,
        default=1,
        help="쿼리당 start 페이징 깊이 (1=최근 100건, 최대 10=1000건). 백필=10. "
        "⚠ 네이버 일 쿼터 25k — 종목×pages 가 이를 넘으면 --stock-seed-limit 로 슬라이스해 여러 날 나눠 실행.",
    )
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--max-queries", type=int, default=5000, help="시드 상한 (smoke/test). 기본=전체 상장사 커버")
    parser.add_argument("--stock-seed-limit", type=int, default=5000, help="시총 상위 N 종목 (기본 5000=전체 상장사)")
    parser.add_argument("--once", action="store_true", help="1 회 실행 후 종료 (cron 표준).")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # 자격증명 가드 — 키 없으면 무해 종료 (cron noop).
    from dartlab.core.providers.dataCredentials import isConfigured

    if not (isConfigured("naver") and isConfigured("naverSecret")):
        _log.warning("네이버 자격증명(NAVER_CLIENT_ID/NAVER_CLIENT_SECRET) 미설정 — skip")
        return 0

    # KR 시드 재사용 (syncNewsHeadlines 와 대칭 — 매크로 키워드 + 시총상위 종목명).
    from syncNewsHeadlines import _MACRO_KEYWORDS_KR, _stockSeedKR

    stockSeed = _stockSeedKR(args.stock_seed_limit)
    queries = list(dict.fromkeys(stockSeed + _MACRO_KEYWORDS_KR))[: args.max_queries]
    if not queries:
        _log.warning("query 시드 0 — abort")
        return 1
    _log.info(
        "naver KR queries=%d (stock=%d, macro=%d)",
        len(queries),
        len(stockSeed),
        len(_MACRO_KEYWORDS_KR),
    )

    from dartlab.gather.sources.naverNews import fetchHeadlinesForArchive
    from dartlab.gather.sources.newsIo import writeDailyParquet
    from dartlab.gather.sources.newsSources import getNewsSource

    df = fetchHeadlinesForArchive(
        queries,
        market="KR",
        days=args.days,
        concurrency=args.concurrency,
        pages=args.pages,
    )
    _log.info("네이버 fetch 완료 — %d 헤드라인 (dedup url, pages=%d)", df.height, args.pages)

    if df.is_empty():
        _log.warning("결과 0 — cache 무변경")
        return 0

    target, total, added = writeDailyParquet(df, dir=getNewsSource("naver").dir, market="KR", day=_date.today())
    _log.info("저장 완료 — %s (total=%d, added=%d)", target, total, added)

    # bulkUploadHf 호환 changed 리스트 (private repo 업로드 대상).
    distDir = REPO_ROOT / "dist"
    distDir.mkdir(parents=True, exist_ok=True)
    (distDir / "changed_newsNaver.txt").write_text(f"KR/{_date.today().isoformat()}.parquet\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
