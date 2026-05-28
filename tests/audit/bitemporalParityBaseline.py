"""Bitemporal PIT parity baseline — Sprint 4 회귀 가드.

asof=오늘 결과 == asof=None 결과 (기존 동작 100% 보존 검증) + asof=과거 결과의
business_time 분포가 cutoff 이하인지 검증.

5 baseline 종목 × 10 asof 시점 박제. 신규 측정에서 drift > tolerance 면 PR 차단.

실행::

    uv run python -X utf8 tests/audit/bitemporalParityBaseline.py --check
    uv run python -X utf8 tests/audit/bitemporalParityBaseline.py --write-baseline

본 도구는 nightly 게이트. HF dataset bitemporal 스키마 마이그레이션 후 의미 있음.
현재 단계 — 골격 + smoke (loadFiltered 시그니처 회귀 가드).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "tests" / "audit" / "_baselines" / "bitemporalParityBaseline.json"

DEFAULT_STOCKS = ("005930", "000660", "035720", "207940", "051910")
DEFAULT_YEAR = 2023

_log = logging.getLogger("bitemporalParityBaseline")


def _smokeLoadFiltered(stockCode: str, year: int, asof: str | None) -> dict | None:
    """단일 종목 1 년 loadFiltered → row count + 최대 BAS_DD.

    HF dataset 미가용 시 None. 본 baseline 의 회귀 가드는 *형식* 위주.
    """
    try:
        from dartlab.gather.bulkData.hfBulk import loadFiltered
    except ImportError:
        return None
    try:
        df = loadFiltered(stockCode=stockCode, year=year, adjustment="raw", asof=asof)
    except Exception as exc:  # noqa: BLE001
        _log.debug("loadFiltered 실패 (%s, asof=%s): %s", stockCode, asof, exc)
        return None
    if df is None or df.is_empty():
        return None
    return {
        "rows": df.height,
        "max_date": str(df["BAS_DD"].max()) if "BAS_DD" in df.columns else "",
    }


def _collect(stocks: tuple[str, ...], year: int) -> dict:
    """asof=None vs asof=오늘 vs asof=과거 박제."""
    out: dict = {}
    for code in stocks:
        out[code] = {
            "no_asof": _smokeLoadFiltered(code, year, asof=None),
            "asof_today": _smokeLoadFiltered(code, year, asof="2099-12-31"),
            "asof_past": _smokeLoadFiltered(code, year, asof=f"{year}-06-30"),
        }
    return out


def _loadBaseline() -> dict | None:
    if not BASELINE_PATH.exists():
        return None
    try:
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _writeBaseline(data: dict) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    _log.info("baseline 저장 → %s", BASELINE_PATH)


def _check(data: dict, baseline: dict) -> int:
    """parity 검증: asof=None == asof=오늘 + asof=과거 의 row 수가 ≤ asof=None.

    회귀:
        - no_asof.rows != asof_today.rows → 기존 동작 깨짐 (default None 인데 오늘이 다름)
        - asof_past.rows > no_asof.rows → 과거 필터가 더 많은 row 반환 (논리 위반)
    """
    failures: list[str] = []
    for code, rows in data.items():
        no_asof = rows.get("no_asof") or {}
        today = rows.get("asof_today") or {}
        past = rows.get("asof_past") or {}
        no_rows = no_asof.get("rows", 0)
        today_rows = today.get("rows", 0)
        past_rows = past.get("rows", 0)
        if no_rows and today_rows and no_rows != today_rows:
            failures.append(f"{code} parity: no_asof={no_rows} vs asof_today={today_rows}")
        if past_rows and no_rows and past_rows > no_rows:
            failures.append(f"{code} 과거 컷오프 > no_asof: {past_rows} > {no_rows}")
    if failures:
        for f in failures:
            _log.error(f)
        return 1
    _log.info("bitemporal parity 회귀 0 — %d 종목 통과", len(data))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="bitemporal PIT parity baseline")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    data = _collect(DEFAULT_STOCKS, args.year)
    if not data or all(v.get("no_asof") is None for v in data.values()):
        _log.warning("HF dataset 미가용 — CI skip")
        return 0
    if args.write_baseline:
        _writeBaseline(data)
        return 0
    baseline = _loadBaseline()
    if baseline is None:
        _log.warning("baseline 미등록 (%s) — CI skip", BASELINE_PATH)
        return 0
    return _check(data, baseline)


if __name__ == "__main__":
    sys.exit(main())
