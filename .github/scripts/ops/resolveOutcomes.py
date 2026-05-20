"""decisions outcome resolver sweep — N 일 경과 pending → resolved 자동 전이.

전제: `outcomeLog.storeDecision` 가 분석 시점 의사결정을 pending 으로 박았고,
N 일 (기본 30) 경과 후 시장 종가로 alpha 산출하여 resolved 로 전이.

흐름:
1. ~/.dartlab/decisions/{KR,US}/*.md glob (DARTLAB_HOME env redirect 가능)
2. filename stem = stockCode → tryResolvePending 호출 (defaultPriceLookup 주입)
3. KR 만 가격 lookup 가능 (defaultPriceLookup 가 US 미구현 → None 반환 → pending 유지)
4. 결과 카운트 stdout

**실행 환경**: ~/.dartlab/decisions/ 는 *운영자 로컬* 에 박힌다 — GitHub Actions
runner 에 없으므로 cron workflow 자리 X. 운영자가 로컬에서 수동 실행 또는
Windows Task Scheduler / Unix cron 으로 일일 등록.

권장 호출:
    uv run python -X utf8 .github/scripts/ops/resolveOutcomes.py

외부 가격 API (KRX) 호출이라 prebuild offline 가드 무관 — ops 카테고리.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# UTF-8 강제 (Windows cp949 회피)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]


def _resolveDecisionsRoot() -> Path:
    """DARTLAB_DECISIONS_ROOT > DARTLAB_HOME/decisions > ~/.dartlab/decisions.

    `outcomeLog._decisionsRoot` 의 로직과 일치 — private 함수 import 회피.
    """
    explicit = os.environ.get("DARTLAB_DECISIONS_ROOT")
    if explicit:
        return Path(explicit)
    dartlab_home = os.environ.get("DARTLAB_HOME")
    base = Path(dartlab_home) if dartlab_home else Path.home() / ".dartlab"
    return base / "decisions"


def main() -> int:
    """decisions sweep entry point. exit code = 0 성공, 1 fatal 실패."""
    from dartlab.ai.memory.wiring import defaultPriceLookup, tryResolvePending

    decisions_root = _resolveDecisionsRoot()
    if not decisions_root.exists():
        print(f"decisions root 없음: {decisions_root} — 종료 (0 sweep)")
        return 0

    total_resolved = 0
    total_files = 0
    market_breakdown: dict[str, int] = {}

    for market_dir in sorted(decisions_root.iterdir()):
        if not market_dir.is_dir():
            continue
        market = market_dir.name
        for md_file in sorted(market_dir.glob("*.md")):
            total_files += 1
            stock_code = md_file.stem
            try:
                resolved = tryResolvePending(
                    stockCode=stock_code,
                    market=market,
                    pricer=defaultPriceLookup if market == "KR" else None,
                    benchmarkPricer=None,
                    benchmarkSymbol=None,
                )
            except Exception as exc:
                print(f"  [WARN] {market}/{stock_code} 처리 실패: {exc}")
                continue
            if resolved > 0:
                print(f"  [OK] {market}/{stock_code} → resolved {resolved}")
                total_resolved += resolved
                market_breakdown[market] = market_breakdown.get(market, 0) + resolved

    print("")
    print(f"=== sweep 완료: {total_files} 파일 검사, {total_resolved} entries 전이 ===")
    for market, cnt in sorted(market_breakdown.items()):
        print(f"  - {market}: {cnt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
