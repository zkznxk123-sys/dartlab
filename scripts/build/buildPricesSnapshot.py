"""prices-snapshot.json 빌드 — 스크리너용 회사 단위 가격 스냅샷.

산업지도 ecosystem.json 의 회사 목록과 stockCode 로 join 가능한 가격·시총 스냅샷
JSON 을 생성한다. /screener 라우트가 ecosystem.json + quarters.json + 이 파일을
병렬 fetch 후 frontend 에서 join 한다.

데이터 흐름:
    1. dartlab.industry.build.pipeline.loadNodes() 로 전종목 stockCode 확보
    2. gather._hfBulk.loadFiltered(start=1y_ago, adjustment="raw") 단일 호출로
       전종목 1 년 일별 OHLCV + MKTCAP + LIST_SHRS 일괄 수신
    3. ISU_CD 별 group → 마지막 거래일·1m/3m/1y 수익률·1y 변동성·52w H/L·30d 평균거래량 계산
    4. landing/static/map/prices-snapshot.json 으로 직렬화

사용법::

    uv run python -X utf8 scripts/build/buildPricesSnapshot.py

빌드 주기:
    .github/workflows/buildPricesSnapshot.yml — 매일 KST 18:00 (KRX 빌드 17:00 후 1 시간)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from dartlab.gather._hfBulk import loadFiltered  # noqa: E402
from dartlab.industry.build.pipeline import loadNodes  # noqa: E402

OUT_PATH = ROOT / "landing" / "static" / "map" / "prices-snapshot.json"

# 스냅샷 계산용 lookback 기준 거래일 (월력 일수 아님 — 조회는 월력으로 하되 비교 인덱스는 거래일 기준)
TRADING_DAYS_1M = 21
TRADING_DAYS_3M = 63
TRADING_DAYS_1Y = 252


def _safeFloat(v: object) -> float | None:
    """폴라스 결과·null 안전 변환."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _pctReturn(latest: float | None, past: float | None) -> float | None:
    """단순 수익률 (%, 소수점 둘째)."""
    if latest is None or past is None or past == 0:
        return None
    return round((latest / past - 1) * 100, 2)


def _annualizedVol(closes: list[float]) -> float | None:
    """일별 로그 수익률의 표준편차 × sqrt(252) → 연환산 변동성 (%, 소수점 둘째)."""
    if len(closes) < 30:
        return None
    rets: list[float] = []
    for i in range(1, len(closes)):
        if closes[i - 1] is None or closes[i - 1] <= 0 or closes[i] is None or closes[i] <= 0:
            continue
        rets.append(math.log(closes[i] / closes[i - 1]))
    if len(rets) < 30:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return round((var**0.5) * (252**0.5) * 100, 2)


def _snapshotForGroup(g: pl.DataFrame) -> dict:
    """단일 종목의 시계열 → 스냅샷 dict.

    g 는 BAS_DD 오름차순 정렬된 DataFrame. 컬럼:
        BAS_DD, ISU_CD, TDD_OPNPRC, TDD_HGPRC, TDD_LWPRC, TDD_CLSPRC,
        ACC_TRDVOL, MKTCAP, LIST_SHRS, FLUC_RT
    """
    if g.is_empty():
        return {}

    # 종가·거래량·고저·시총 시계열 추출 (raw OHLCV는 모두 string 가능 — 캐스팅 필수)
    closes = [_safeFloat(v) for v in g["TDD_CLSPRC"].to_list()]
    highs = [_safeFloat(v) for v in g["TDD_HGPRC"].to_list()]
    lows = [_safeFloat(v) for v in g["TDD_LWPRC"].to_list()]
    volumes = [_safeFloat(v) for v in g["ACC_TRDVOL"].to_list()]
    mktcaps = [_safeFloat(v) for v in g["MKTCAP"].to_list()]
    dates = g["BAS_DD"].to_list()

    n = len(closes)
    last = n - 1
    latestClose = closes[last] if last >= 0 else None
    latestMcap = mktcaps[last] if last >= 0 else None
    latestDate = dates[last] if last >= 0 else None

    # 수익률 — 거래일 기준 lookback
    return1m = _pctReturn(latestClose, closes[last - TRADING_DAYS_1M]) if last - TRADING_DAYS_1M >= 0 else None
    return3m = _pctReturn(latestClose, closes[last - TRADING_DAYS_3M]) if last - TRADING_DAYS_3M >= 0 else None
    return1y = _pctReturn(latestClose, closes[last - TRADING_DAYS_1Y]) if last - TRADING_DAYS_1Y >= 0 else None

    # 52주 (≈ 1y 거래일) 고저
    window = closes[max(0, last - TRADING_DAYS_1Y) : last + 1]
    highWindow = [h for h in highs[max(0, last - TRADING_DAYS_1Y) : last + 1] if h is not None]
    lowWindow = [lo for lo in lows[max(0, last - TRADING_DAYS_1Y) : last + 1] if lo is not None]
    week52High = max(highWindow) if highWindow else None
    week52Low = min(lowWindow) if lowWindow else None

    # 30 일 평균 거래량
    volWindow = [v for v in volumes[max(0, last - 30) : last + 1] if v is not None]
    volumeAvg30d = round(sum(volWindow) / len(volWindow)) if volWindow else None

    # 1y 변동성
    closesValid = [c for c in window if c is not None]
    volatility1y = _annualizedVol(closesValid)

    return {
        "currentPrice": latestClose,
        "marketCap": latestMcap,
        "return1m": return1m,
        "return3m": return3m,
        "return1y": return1y,
        "volatility1y": volatility1y,
        "week52High": week52High,
        "week52Low": week52Low,
        "volumeAvg30d": volumeAvg30d,
        "foreignPct": None,  # v1 미수집 — 추후 KRX 외인보유 통계 gather 시 활성화
        "beta": None,  # v1 미계산 — KOSPI 시계열 join 추가 시 활성화
        "priceUpdated": str(latestDate) if latestDate else None,
    }


def buildSnapshot(*, lookbackDays: int = 400) -> dict:
    """전종목 가격 스냅샷 빌드.

    Parameters
    ----------
    lookbackDays : int
        HF 에서 받아올 일수 (월력). 252 거래일 (1Y) 보장 위해 기본 400 일.

    Returns
    -------
    dict
        ``{stockCode: snapshot_dict}`` 형태. ecosystem.json 과 stockCode 로 join.
    """
    nodes = loadNodes()
    targetCodes = {n.stockCode for n in nodes}
    print(f"  - 대상 종목 {len(targetCodes)} 개")

    end = date.today()
    start = end - timedelta(days=lookbackDays)
    print(f"  - HF 로드: {start} ~ {end} ({lookbackDays} 일)")

    df = loadFiltered(start=start, end=end, adjustment="raw")
    if df is None or df.is_empty():
        raise RuntimeError("HF krx-prices 응답 비어있음 — 빌드 중단")

    # ecosystem 회사로 필터 + 정렬
    df = df.filter(pl.col("ISU_CD").is_in(list(targetCodes))).sort(["ISU_CD", "BAS_DD"])
    print(f"  - 매칭 행 {df.height:,} / 종목 {df['ISU_CD'].n_unique()} 개")

    out: dict[str, dict] = {}
    for code, group in df.group_by("ISU_CD"):
        codeStr = code[0] if isinstance(code, tuple) else code
        snap = _snapshotForGroup(group)
        if snap:
            out[str(codeStr)] = snap

    print(f"  - 스냅샷 산출 {len(out)} 사")
    return out


def _uploadToHf(jsonPath: Path) -> None:
    """생성된 prices-snapshot.json 을 HF dataset 에 업로드.

    landing 배포가 HF 에서 pull 해 가는 구조 (.github/workflows/docs.yml 의 seed 단계).
    HF_TOKEN 없으면 로컬 파일만 남기고 스킵.
    """
    import os

    token = os.environ.get("HF_TOKEN", "")
    if not token:
        print("[buildPricesSnapshot] HF_TOKEN 없음 → HF 업로드 스킵 (로컬 파일만)")
        return

    from huggingface_hub import HfApi

    from dartlab.core.dataConfig import DATA_RELEASES, HF_REPO

    cfg = DATA_RELEASES["industryMap"]
    dirPath = cfg["dir"]  # landing/map
    repoPath = f"{dirPath}/{jsonPath.name}"
    sizeKb = jsonPath.stat().st_size / 1024
    print(f"[buildPricesSnapshot] HF 업로드: {jsonPath} → {HF_REPO}/{repoPath} ({sizeKb:.1f} KB)")

    api = HfApi(token=token)
    api.upload_file(
        path_or_fileobj=str(jsonPath),
        repo_id=HF_REPO,
        repo_type="dataset",
        path_in_repo=repoPath,
        commit_message="prices-snapshot: auto-rebuild",
    )
    print("[buildPricesSnapshot] HF 업로드 완료")


def main() -> int:
    parser = argparse.ArgumentParser(description="prices-snapshot.json 빌드")
    parser.add_argument("--lookback", type=int, default=400, help="HF 로드 lookback 월력 일수")
    parser.add_argument("--out", type=Path, default=OUT_PATH, help="출력 JSON 경로")
    parser.add_argument("--no-upload", action="store_true", help="HF 업로드 생략 (로컬만)")
    args = parser.parse_args()

    print("[buildPricesSnapshot] 시작")
    snapshot = buildSnapshot(lookbackDays=args.lookback)

    builtAt = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = {
        "schemaVersion": 1,
        "builtAt": builtAt,
        "lookbackDays": args.lookback,
        "count": len(snapshot),
        "data": snapshot,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    sizeKb = args.out.stat().st_size / 1024
    print(f"[buildPricesSnapshot] 완료 → {args.out} ({sizeKb:.1f} KB)")

    if not args.no_upload:
        _uploadToHf(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
