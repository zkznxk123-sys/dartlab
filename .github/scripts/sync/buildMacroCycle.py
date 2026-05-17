"""macro cycle 분석 결과 JSON 빌드 — KR/US 경기 국면 (sync 단계 책임).

``dartlab.macro.cycles.cycle.analyzeCycle`` 는 FRED/ECOS macro indicator 를 fetch 해
phase/confidence/signals/sectorStrategy 를 산출한다. 본 분석은 외부 API 의존이므로
**sync 단계**에서 미리 계산해 HF dataset 의 ``macro/cycle/{kr,us}.json`` 으로 publish.

prebuild ``buildMacroJson.py`` 는 본 JSON 을 다운로드해서 SECTOR_SENSITIVITY 매핑만
수행 (offline, 외부 API 호출 0).

실행::

    uv run python -X utf8 .github/scripts/sync/buildMacroCycle.py
    uv run python -X utf8 .github/scripts/sync/buildMacroCycle.py --push   # HF publish

환경변수:
    HF_TOKEN: --push 시 필수
    FRED_API_KEY / ECOS_API_KEY: macro indicator fetch (HF bulk cache 우선 사용).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _analyzeMarket(market: str) -> dict:
    """analyzeCycle 호출 wrapper — 시계열 제거 + asOf 포함."""
    from dartlab.macro.cycles.cycle import analyzeCycle

    result = analyzeCycle(market=market)
    result.pop("timeseries", None)
    result.setdefault("market", market)
    result["computedAt"] = datetime.now(timezone.utc).isoformat()
    return result


def buildCycle(outDir: Path) -> dict[str, Path]:
    """KR + US cycle 분석 JSON 빌드."""
    outDir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    for market in ("KR", "US"):
        t0 = time.time()
        print(f"[macroCycle] {market} analyzing …", flush=True)
        try:
            result = _analyzeMarket(market)
        except Exception as e:
            print(f"[macroCycle] {market} 실패: {type(e).__name__}: {e}", flush=True)
            continue
        path = outDir / f"{market.lower()}.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=0), encoding="utf-8")
        kb = path.stat().st_size / 1024
        print(
            f"[macroCycle] {market}: phase={result.get('phase')} "
            f"confidence={result.get('confidence')} → {path} ({kb:.1f}KB, {time.time() - t0:.0f}s)",
            flush=True,
        )
        written[market.lower()] = path

    return written


def deploy(written: dict[str, Path], *, repoId: str) -> None:
    """HF dataset macro/cycle/ 에 publish."""
    import os

    from huggingface_hub import HfApi

    token = os.environ.get("HF_TOKEN", "")
    if not token:
        print("[macroCycle] HF_TOKEN 없음 — publish 스킵")
        return

    api = HfApi(token=token)
    for market, path in written.items():
        commit = api.upload_file(
            path_or_fileobj=str(path),
            path_in_repo=f"macro/cycle/{market}.json",
            repo_id=repoId,
            repo_type="dataset",
            commit_message=f"build: macro cycle {market}.json",
        )
        print(f"[hf] macro/cycle/{market}.json: {getattr(commit, 'commit_url', None)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/macro/cycle", help="출력 디렉토리 (기본 data/macro/cycle)")
    parser.add_argument("--repo-id", default="eddmpython/dartlab-data")
    parser.add_argument("--push", action="store_true", help="HF dataset publish 활성화")
    args = parser.parse_args()

    written = buildCycle(Path(args.out))
    if not written:
        print("[macroCycle] 결과 0 건 — exit 1")
        return 1
    if args.push:
        deploy(written, repoId=args.repo_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
