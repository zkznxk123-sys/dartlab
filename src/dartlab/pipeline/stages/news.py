"""News stage — 헤드라인 아카이브(A) + 감성/토픽 enrich(B) + GDELT forward(D) + 네이버(N).

워크플로 충실 재현:
- ``runNewsHeadlines``(A): ``syncNewsHeadlines.py --market KR/US --once --max-queries`` +
  ``bulkUploadHf.py newsHeadlines --since 86400``. max-queries=env NEWS_MAX_QUERIES_KR/US(150/80).
- ``runNewsEnrich``(B): ``enrichNewsHeadlines.py --market KR/US --since 86400 --model <m>`` +
  ``bulkUploadHf.py newsEnriched --since 86400``. 로컬 headlines(A 직후) 를 읽어 sentiment+topic
  부착(모델 미가용 시 lm_dict/query-proxy fallback). model=env NEWS_ENRICH_MODEL(기본 lm_dict).
- ``runGdeltForward``(D): ``syncGdeltBackfill.py --start <today-N> --end <yesterday> --step-minutes
  <s> --markets ...`` + ``bulkUploadHf.py newsGdelt --since 86400``. yesterday(완성된 UTC 일) 까지
  N일 lookback upsert(누락 자가복구). N=env GDELT_LOOKBACK_DAYS(2), s=GDELT_STEP_MINUTES(360).
- ``runNaverNews``(N): ``syncNaverNews.py --once --max-queries`` + ``bulkUploadHf.py newsNaver
  --since 86400``. KR 제목+스니펫 → **private** repo. 무키 시 green-noop. max-queries=env
  NAVER_MAX_QUERIES(200). 언론사 저작권 비공개 캐시 전용(공개 dartlab-data 안 감).
"""

from __future__ import annotations

import os
from datetime import date, timedelta

from dartlab.pipeline.stages._runner import runScript
from dartlab.pipeline.types import PipelineMode, StageResult


def runNewsHeadlines(
    *, category: str = "news", mode: PipelineMode = "recent", codes=None, upload: bool = True, token=None
) -> StageResult:
    """뉴스 헤드라인 — KR/US fetch + bulk since-upload(newsHeadlines).

    Args:
        category: 카테고리 라벨.
        mode: 미사용.
        codes: 미사용.
        upload: bulkUploadHf 수행 여부.
        token: 미사용(bulkUploadHf 가 env>.env 해석).

    Returns:
        StageResult.

    Raises:
        없음.

    Example:
        >>> runNewsHeadlines(upload=False)  # doctest: +SKIP
        StageResult(category='newsHeadlines', ...)
    """
    krQ = os.environ.get("NEWS_MAX_QUERIES_KR", "150")
    usQ = os.environ.get("NEWS_MAX_QUERIES_US", "80")
    script = ".github/scripts/sync/syncNewsHeadlines.py"
    rc1 = runScript(script, "--market", "KR", "--once", "--max-queries", krQ)
    rc2 = runScript(script, "--market", "US", "--once", "--max-queries", usQ)
    res = StageResult(category="newsHeadlines")
    if rc1 != 0 or rc2 != 0:
        res.report.err = 1
        res.report.failures.append(f"news fetch rc=KR:{rc1}/US:{rc2}")
        return res
    res.report.ok = 1
    if upload:
        rc3 = runScript(".github/scripts/sync/bulkUploadHf.py", "newsHeadlines", "--since", "86400")
        if rc3 != 0:
            res.report.fail = 1
            res.report.failures.append(f"news upload rc={rc3}")
    return res


def runNewsEnrich(
    *, category: str = "newsEnrich", mode: PipelineMode = "recent", codes=None, upload: bool = True, token=None
) -> StageResult:
    """뉴스 헤드라인 감성/토픽 enrich (Phase B) — 로컬 headlines 읽어 enrich + newsEnriched 업로드.

    ``runNewsHeadlines`` 직후 같은 잡에서 호출(headlines 가 로컬). KR/US 각각 ``enrichNewsHeadlines.py
    --since 86400`` 으로 최근 raw 를 sentiment(lm_dict fallback)+topic(query-proxy fallback) 부착해
    ``data/news/public/rss_enriched`` 에 쓰고 ``bulkUploadHf newsEnriched --since 86400`` 으로 변경분만 push.

    Args:
        category: 카테고리 라벨.
        mode: 미사용.
        codes: 미사용.
        upload: bulkUploadHf 수행 여부.
        token: 미사용(bulkUploadHf 가 env>.env 해석).

    Returns:
        StageResult (raw 0 건이면 ok·업로드 0).

    Raises:
        없음.

    Example:
        >>> runNewsEnrich(upload=False)  # doctest: +SKIP
        StageResult(category='newsEnriched', ...)
    """
    model = os.environ.get("NEWS_ENRICH_MODEL", "lm_dict")
    script = ".github/scripts/sync/enrichNewsHeadlines.py"
    rc1 = runScript(script, "--market", "KR", "--since", "86400", "--model", model)
    rc2 = runScript(script, "--market", "US", "--since", "86400", "--model", model)
    res = StageResult(category="newsEnriched")
    if rc1 != 0 or rc2 != 0:
        res.report.err = 1
        res.report.failures.append(f"news enrich rc=KR:{rc1}/US:{rc2}")
        return res
    res.report.ok = 1
    if upload:
        rc3 = runScript(".github/scripts/sync/bulkUploadHf.py", "newsEnriched", "--since", "86400")
        if rc3 != 0:
            res.report.fail = 1
            res.report.failures.append(f"news enrich upload rc={rc3}")
    return res


def runGdeltForward(
    *, category: str = "gdeltForward", mode: PipelineMode = "recent", codes=None, upload: bool = True, token=None
) -> StageResult:
    """GDELT GKG forward 일별 (Phase D) — yesterday 까지 N일 lookback upsert + newsGdelt 업로드.

    ``syncGdeltBackfill.py`` 를 ``--start (today-N) --end (today-1)`` 로 호출 — yesterday 는 완성된
    UTC 일이라 안전(today 는 미완성이라 제외). N일 lookback + day upsert(url unique) 로 직전 run 누락
    자가복구. markets/step 은 env 로 조정. ``bulkUploadHf newsGdelt --since 86400`` push.

    Args:
        category: 카테고리 라벨.
        mode: 미사용.
        codes: 미사용.
        upload: bulkUploadHf 수행 여부.
        token: 미사용(bulkUploadHf 가 env>.env 해석).

    Returns:
        StageResult.

    Raises:
        없음.

    Example:
        >>> runGdeltForward(upload=False)  # doctest: +SKIP
        StageResult(category='newsGdelt', ...)
    """
    lookback = int(os.environ.get("GDELT_LOOKBACK_DAYS") or "2")
    step = os.environ.get("GDELT_STEP_MINUTES", "360")
    markets = (os.environ.get("GDELT_MARKETS") or "KR US JP CN GLOBAL").split()
    today = date.today()
    start = (today - timedelta(days=lookback)).isoformat()
    end = (today - timedelta(days=1)).isoformat()  # yesterday — 완성된 UTC 일(today 미완성 제외)
    res = StageResult(category="newsGdelt")
    rc = runScript(
        ".github/scripts/sync/syncGdeltBackfill.py",
        "--start",
        start,
        "--end",
        end,
        "--step-minutes",
        step,
        "--markets",
        *markets,
    )
    if rc != 0:
        res.report.err = 1
        res.report.failures.append(f"gdelt forward rc={rc} ({start}~{end})")
        return res
    res.report.ok = 1
    if upload:
        rc2 = runScript(".github/scripts/sync/bulkUploadHf.py", "newsGdelt", "--since", "86400")
        if rc2 != 0:
            res.report.fail = 1
            res.report.failures.append(f"gdelt upload rc={rc2}")
    return res


def runNaverNews(
    *, category: str = "naverNews", mode: PipelineMode = "recent", codes=None, upload: bool = True, token=None
) -> StageResult:
    """네이버 뉴스 (private) — KR fetch + bulk since-upload(newsNaver, private repo).

    ``syncNaverNews.py --once --max-queries`` (KR 시총상위+매크로 시드, 제목+스니펫) →
    ``data/news/private/naver`` upsert → ``bulkUploadHf.py newsNaver --since 86400`` 로
    **private** repo(`eddmpython/dartlab-news-private`) push. 언론사 저작권 비공개 캐시 전용 —
    공개 dartlab-data 안 감. NAVER 자격증명 미설정 시 syncNaverNews 가 무해 종료(rc=0,
    업로드 0) → green-noop. max-queries=env NAVER_MAX_QUERIES(200).

    Args:
        category: 카테고리 라벨.
        mode: 미사용.
        codes: 미사용.
        upload: bulkUploadHf 수행 여부.
        token: 미사용(bulkUploadHf 가 env>.env 해석).

    Returns:
        StageResult (무키/결과 0 이면 ok·업로드 0).

    Raises:
        없음.

    Example:
        >>> runNaverNews(upload=False)  # doctest: +SKIP
        StageResult(category='newsNaver', ...)
    """
    maxQ = os.environ.get("NAVER_MAX_QUERIES", "5000")  # 기본=전체 상장사 커버(옛 200=시총상위 100만)
    pages = os.environ.get("NAVER_PAGES", "1")  # 1=일별 증분(최근 100), 10=백필(쿼리당 ≤1000)
    days = os.environ.get("NAVER_DAYS", "1")  # 1=일별 cutoff, 0=백필(cutoff 없음)
    rc1 = runScript(
        ".github/scripts/sync/syncNaverNews.py",
        "--once",
        "--max-queries",
        maxQ,
        "--pages",
        pages,
        "--days",
        days,
    )
    res = StageResult(category="newsNaver")
    if rc1 != 0:
        res.report.err = 1
        res.report.failures.append(f"naver fetch rc={rc1}")
        return res
    res.report.ok = 1
    if upload:
        rc2 = runScript(".github/scripts/sync/bulkUploadHf.py", "newsNaver", "--since", "86400")
        if rc2 != 0:
            res.report.fail = 1
            res.report.failures.append(f"naver upload rc={rc2}")
    return res
