"""OpenFIGI 30k 종목 야간 cron — figiCache.parquet 박제.

Sprint 3 (Symbology) 활성화 도구. KRX listing → OpenFIGI bulk lookup →
``data/symbology/figiCache.parquet`` 영구화. 무인증 25 req/min × 5 ID/req =
125 ID/min → 30,000 종목 약 4 시간. 인증 발급 시 60 req/min × 10 ID/req → 1 시간.

실행::

    uv run python -X utf8 .github/scripts/sync/buildSymbologyCache.py --dry-run
    uv run python -X utf8 .github/scripts/sync/buildSymbologyCache.py --limit 50
    uv run python -X utf8 .github/scripts/sync/buildSymbologyCache.py  # 전수 (4 시간)

OPENFIGI_API_KEY 환경변수 있으면 자동 인증 모드 (5 배 빠름).

본 도구는 sync/ 카테고리 — online (외부 API → 로컬 cache). 결과 parquet 은
사용자가 명시 결심 후 별도 HF push (선택).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[3]
_log = logging.getLogger("buildSymbologyCache")


def _fetchKrxListing() -> list[str]:
    """KRX 상장사 종목 코드 리스트 — HF dataset 활용 (offline 가능).

    Returns:
        ['005930', '000660', ...] — 코스피·코스닥 단축코드.
    """
    try:
        from dartlab.gather.bulkData.hfBulk import loadFiltered

        df = loadFiltered(adjustment="raw")
        if df is None or df.is_empty():
            _log.warning("KRX bulkData 부재 — listing 0 종목")
            return []
        if "ISU_CD" not in df.columns:
            return []
        return sorted(df["ISU_CD"].unique().to_list())
    except Exception as exc:
        _log.error("KRX listing fetch 실패: %s", exc)
        return []


def _buildItemsForKr(codes: list[str]) -> list[dict]:
    """KRX 종목 코드 → OpenFIGI lookup 요청 dict.

    KRX 거래소 = OpenFIGI exchCode 'KS' (코스피) / 'KQ' (코스닥). 본 도구는
    KS 로 일괄 시도 후 실패 시 KQ 재시도 (caller 단순화 — 1 round 만).
    """
    return [{"idType": "TICKER", "idValue": code, "exchCode": "KS"} for code in codes]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenFIGI 30k 종목 cache 박제")
    parser.add_argument("--limit", type=int, help="첫 N 종목만 (테스트용)")
    parser.add_argument("--dry-run", action="store_true", help="lookup 0, listing 만 보고")
    parser.add_argument("--out", type=Path, default=None, help="cache 파일 경로 (default symbology._CACHE_FILE)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    api_key = os.environ.get("OPENFIGI_API_KEY")
    _log.info("OPENFIGI_API_KEY %s", "있음 (인증 모드 60 req/min)" if api_key else "없음 (무인증 25 req/min)")

    codes = _fetchKrxListing()
    if not codes:
        _log.warning("KRX listing 0 종목 — HF bulkData 미가용 / 네트워크 격리")
        return 0
    if args.limit:
        codes = codes[: args.limit]
    _log.info("KRX listing %d 종목", len(codes))

    if args.dry_run:
        _log.info("DRY-RUN — lookup 0, 첫 10: %s", codes[:10])
        return 0

    from dartlab.gather.mapping import symbology

    if args.out is not None:
        # caller 가 명시한 경로로 cache 변경 (테스트/스테이징 용)
        symbology._CACHE_FILE = args.out
        symbology._CACHE_DIR = args.out.parent

    # bulk lookup — symbology.lookupBulk 가 rate-limit sleep 내장
    items = _buildItemsForKr(codes)
    _log.info("OpenFIGI lookup 시작 — %d 종목 (예상 %d분)", len(items), len(items) // 125 + 1)
    results = symbology.lookupBulk(items, apiKey=api_key)
    _log.info("lookup 완료 — %d 응답", len(results))

    # cache 통합 저장 — 기존 cache + 신규 result 통합
    cache = symbology.loadCache()
    rows: list[dict] = []
    for req, res in zip(items, results, strict=False):
        if "error" in res:
            continue
        rows.append(
            {
                "id_type": "TICKER",
                "id_value": req["idValue"],
                "exch_code": req.get("exchCode", ""),
                "figi": res.get("figi", ""),
                "ticker": res.get("ticker", req["idValue"]),
                "name": res.get("name", ""),
            }
        )
    if not rows:
        _log.warning("lookup 0 건 성공 — cache 무변경")
        return 0
    new_rows = pl.DataFrame(rows)
    merged = pl.concat([cache, new_rows], how="diagonal_relaxed").unique(
        subset=["id_type", "id_value", "exch_code"],
        keep="last",
    )
    symbology.saveCache(merged)
    _log.info("cache 저장 완료 — %d → %d rows", cache.height, merged.height)
    return 0


if __name__ == "__main__":
    sys.exit(main())
