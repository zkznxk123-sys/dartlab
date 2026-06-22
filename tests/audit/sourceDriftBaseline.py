"""source drift baseline — 동시 2 소스 가격 일치도 박제 + 회귀 가드.

목적: fallback chain 의 1·2 순위 source 가 같은 종목·같은 시점에 대해 얼마나
일치하는지 측정해서 baseline JSON 에 박제. 신규 측정에서 drift 가 baseline +
tolerance 를 넘으면 회귀로 판정.

실행::

    uv run python -X utf8 tests/audit/sourceDriftBaseline.py --check
    uv run python -X utf8 tests/audit/sourceDriftBaseline.py --write-baseline
    uv run python -X utf8 tests/audit/sourceDriftBaseline.py --stocks 005930,AAPL

baseline: ``tests/audit/_baselines/sourceDriftBaseline.json`` — 5 종목 박제 (현재 **미생성**).
부재 시 ``--check`` 는 ``[DRIFT-UNVERIFIED]`` 경고 + exit 0 — drift 회귀가 검증되지 않음을 명시.
네트워크 호출 실패 (source 양쪽 또는 한쪽 None) 시 그 종목 silent skip.

**현재 배선 상태 (정직)**: 본 도구는 CI(``tests/run.py``)·nightly 어디에도 배선되지 않았고
baseline 도 부재라 gov↔krx 가격 fallback drift 회귀가 *무검증*이다. 활성화 = 운영자가
① ``--write-baseline`` 1 회 네트워크 실행으로 baseline 박제 → ② nightly 데이터 잡에 ``--check``
배선 (라이브 네트워크 25 회 / 종목당 ~3s 라 fast tier 부적합 → nightly 전용). (debt-honesty P2-8)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "tests" / "audit" / "_baselines" / "sourceDriftBaseline.json"

# 5 baseline ticker — KR 3 (대형주 시총 1·2·코스닥 1) + US 2 (mega cap)
DEFAULT_STOCKS = (
    ("005930", "KR"),  # 삼성전자
    ("000660", "KR"),  # SK 하이닉스
    ("035720", "KR"),  # 카카오
    ("AAPL", "US"),
    ("MSFT", "US"),
)
REGRESSION_TOLERANCE = 0.005  # 0.5%p — drift 증가 허용 폭

_log = logging.getLogger("sourceDriftBaseline")


async def _measureDrift(stockCode: str, market: str) -> float | None:
    """단일 종목 대해 chain 1·2 순위 source 가격 차이 측정.

    Returns:
        diff_pct (0.0~1.0+) 또는 None (한쪽이라도 fetch 실패).
    """
    from dartlab.gather.domains import getPriceFallback, loadDomain
    from dartlab.gather.infra.consolidation import checkDiff
    from dartlab.gather.infra.http import GatherHttpClient
    from dartlab.gather.marketConfig import getMarketConfig
    from dartlab.gather.types import GatherError

    chain = getPriceFallback(market)
    if len(chain) < 2:
        return None
    config = getMarketConfig(market)

    client = GatherHttpClient()
    results = []
    try:
        for source_name in chain[:2]:
            try:
                module = loadDomain(source_name)
                if not hasattr(module, "fetchPrice"):
                    return None
                snap = await module.fetchPrice(stockCode, client, market=market)
                if snap is None:
                    return None
                snap.currency = config.currency
                snap.market = market
                snap.source = source_name
                results.append(snap)
            except (GatherError, ImportError, OSError) as exc:
                _log.debug("fetch 실패 %s/%s: %s", stockCode, source_name, exc)
                return None
    finally:
        await client.close()

    if len(results) != 2:
        return None
    try:
        result = checkDiff(results[0], results[1], threshold=1.0, archive=False)
    except ValueError:
        return None
    return result.diff_pct


async def _collectBaseline(stocks: tuple[tuple[str, str], ...]) -> dict[str, dict]:
    """모든 baseline 종목 측정 → JSON-ready dict 반환."""
    out: dict[str, dict] = {}
    for stockCode, market in stocks:
        diff = await _measureDrift(stockCode, market)
        if diff is None:
            _log.warning("baseline skip %s (%s) — fetch 실패", stockCode, market)
            continue
        out[stockCode] = {"market": market, "diff_pct": float(diff)}
    return out


def _loadBaseline() -> dict | None:
    if not BASELINE_PATH.exists():
        return None
    try:
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _log.error("baseline 로드 실패 %s: %s", BASELINE_PATH, exc)
        return None


def _writeBaseline(data: dict) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    _log.info("baseline 저장 → %s (%d 종목)", BASELINE_PATH, len(data))


def _check(data: dict, baseline: dict) -> int:
    """신규 측정 vs baseline. drift 증가 > tolerance 면 exit 1."""
    failures = []
    for stockCode, newRow in data.items():
        if stockCode not in baseline:
            _log.info("신규 종목 %s (baseline 미등록) — skip", stockCode)
            continue
        old = baseline[stockCode]["diff_pct"]
        new = newRow["diff_pct"]
        if new > old + REGRESSION_TOLERANCE:
            failures.append((stockCode, old, new))

    if failures:
        for stockCode, old, new in failures:
            _log.error(
                "drift 회귀 %s: baseline %.4f → 신규 %.4f (Δ%.4f > tolerance %.4f)",
                stockCode,
                old,
                new,
                new - old,
                REGRESSION_TOLERANCE,
            )
        return 1
    _log.info("drift 회귀 0 — %d 종목 baseline 통과", len(data))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="source drift baseline 박제 / 검증")
    parser.add_argument("--check", action="store_true", help="baseline 대비 검증 (default)")
    parser.add_argument("--write-baseline", action="store_true", help="신규 baseline 박제")
    parser.add_argument("--stocks", help="쉼표 구분 종목 (기본 5 baseline)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.stocks:
        # "005930:KR,AAPL:US" 형식. market 미지정 시 KR 가정.
        stocks = []
        for tok in args.stocks.split(","):
            if ":" in tok:
                code, mkt = tok.split(":", 1)
                stocks.append((code.strip(), mkt.strip()))
            else:
                stocks.append((tok.strip(), "KR"))
        stocks_tuple = tuple(stocks)
    else:
        stocks_tuple = DEFAULT_STOCKS

    data = asyncio.run(_collectBaseline(stocks_tuple))

    if not data:
        _log.warning("측정 결과 0 종목 — 네트워크 격리 or fallback chain < 2")
        return 0

    if args.write_baseline:
        _writeBaseline(data)
        return 0

    baseline = _loadBaseline()
    if baseline is None:
        _log.warning(
            "[DRIFT-UNVERIFIED] baseline 미등록 (%s) — gov↔krx 가격 drift 회귀 *무검증*. "
            "운영자 --write-baseline 1 회 실행 + nightly 배선 필요 (debt-honesty P2-8)",
            BASELINE_PATH,
        )
        return 0
    return _check(data, baseline)


if __name__ == "__main__":
    sys.exit(main())
