"""gov/prices date 샤드 → landing/map/prices-snapshot.json (터미널·scan·companyLive 시세 스냅샷).

소비처(landing)가 부팅 시 1파일로 읽는 전종목 시세 요약. 원천은 매 영업일 cron 이
upsert 하는 ``gov/prices/date/{YYYY}.parquet`` (KRX raw schema) — 본 스크립트는 그
레이아웃 파생일 뿐 외부 API 호출 0 (prebuild offline 규약).

출력 shape (schemaVersion 1 — 기존 소비처 ``types.ts PriceRow`` 와 동일)::

    {
      "schemaVersion": 1,
      "builtAt": "2026-06-12T05:00:00+00:00",
      "lookbackDays": 400,
      "count": 2555,
      "data": {
        "005930": {
          "currentPrice": 60400.0, "marketCap": 3.6e14,
          "return1m": 1.2, "return3m": -3.4, "return1y": 11.0,
          "volatility1y": 22.19, "week52High": 71400.0, "week52Low": 55600.0,
          "volumeAvg30d": 66554, "foreignPct": null, "beta": null,
          "priceUpdated": "20260611"
        }, ...
      }
    }

실행::

    uv run python -X utf8 .github/scripts/prebuild/buildPricesSnapshot.py [--skip-upload]
    # ~20초, <500MB. HF_TOKEN 필요 (업로드 시).

wiring: buildGovPriceData.yml daily 분기 마지막 스텝 — date 샤드 upsert 직후 같은
러너 로컬 캐시(data/gov/prices/date)를 재사용해 HF 재다운로드 0.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _hfRetry import retryHfCall  # noqa: E402

HF_REPO = "eddmpython/dartlab-data"
PATH_IN_REPO = "landing/map/prices-snapshot.json"
OUT_LOCAL = ROOT / "landing" / "static" / "map" / "prices-snapshot.json"
LOOKBACK_DAYS = 400  # 달력일 — return1y(252거래일) + 휴장 버퍼
LOCAL_DATE_DIR = ROOT / "data" / "gov" / "prices" / "date"

# 거래일 오프셋 (마지막 봉 기준) — 1M/3M/1Y
_RET_OFFSETS = {"return1m": 21, "return3m": 63, "return1y": 252}


def _env(name: str) -> str:
    """환경변수 우선, 없으면 repo 루트 .env 직독."""
    val = os.environ.get(name, "").strip()
    if val:
        return val
    envPath = ROOT / ".env"
    if envPath.exists():
        m = dict(re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", envPath.read_text(encoding="utf-8"), re.M))
        return m.get(name, "").strip().strip('"').strip("'")
    return ""


def _loadYearShard(year: int) -> pl.DataFrame | None:
    """date 샤드 1개 — 과거 연도는 로컬 캐시 우선(불변), 현재 연도는 로컬+HF 병합.

    러너는 actions/cache 가 방금 upsert 한 파일이라 로컬=최신이지만, 운영자 로컬의
    data/ 는 며칠 묵을 수 있다(6/11 누락 실측). 현재 연도만 HF 와 dedup-merge 해
    어느 환경에서든 둘 중 신선한 쪽이 이긴다 (buildGovData upsert 와 동일 규약).
    """
    local = LOCAL_DATE_DIR / f"{year}.parquet"
    localDf = pl.read_parquet(local) if local.exists() else None
    if localDf is not None and year < date.today().year:
        return localDf
    try:
        from huggingface_hub import hf_hub_download

        cached = retryHfCall(
            hf_hub_download,
            repo_id=HF_REPO,
            repo_type="dataset",
            filename=f"gov/prices/date/{year}.parquet",
            token=_env("HF_TOKEN") or None,
            # Windows 비심링크 열화 캐시가 같은 ref 의 옛 blob 을 재서빙(6/11 누락 실측) — 신선도가
            # 본 스크립트의 존재 이유라 강제 재다운로드. 러너는 로컬 캐시 우선이라 이 경로 자체가 드묾.
            force_download=True,
        )
        hfDf = pl.read_parquet(cached)
        if localDf is None or localDf.is_empty():
            return hfDf
        return pl.concat([localDf, hfDf], how="diagonal_relaxed").unique(subset=["BAS_DD", "ISU_CD"], keep="last")
    except Exception as exc:  # noqa: BLE001 — 연초 등 미존재 연도는 정상 (로컬 있으면 로컬로)
        print(f"[snapshot] {year} HF 실패 — 로컬 폴백 ({type(exc).__name__})")
        return localDf


def loadWindow(asOf: date) -> pl.DataFrame:
    """최근 LOOKBACK_DAYS 달력일 전종목 일별 — KRX raw → 슬림 표준 컬럼."""
    cutoff = (asOf - timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d")
    frames: list[pl.DataFrame] = []
    for year in range(int(cutoff[:4]), asOf.year + 1):
        df = _loadYearShard(year)
        if df is not None and not df.is_empty():
            frames.append(df)
            print(f"[snapshot] {year}: {df.height}행")
    if not frames:
        raise SystemExit("[snapshot] date 샤드 0건 — 원천 부재")
    raw = pl.concat(frames, how="diagonal_relaxed")
    # ISU_CD: gov 시대 'A'+코드 / KRX 이관분 코드 단독 혼재 — 'A' 제거 후 6자리만 (buildGovData 규약 동일)
    out = (
        raw.select(["BAS_DD", "ISU_CD", "TDD_CLSPRC", "TDD_HGPRC", "TDD_LWPRC", "ACC_TRDVOL", "MKTCAP"])
        .with_columns(pl.col("ISU_CD").cast(pl.Utf8).str.replace(r"^A", "").alias("stockCode"))
        .drop("ISU_CD")
        .filter(pl.col("stockCode").str.contains(r"^\d{6}$") & (pl.col("BAS_DD") >= pl.lit(cutoff)))
        .with_columns(
            [
                pl.col(c).cast(pl.Float64, strict=False)
                for c in ("TDD_CLSPRC", "TDD_HGPRC", "TDD_LWPRC", "ACC_TRDVOL", "MKTCAP")
            ]
        )
        .unique(subset=["BAS_DD", "stockCode"], keep="last")
        .sort(["stockCode", "BAS_DD"])
    )
    return out


def _retPct(closes: list[float | None], bars: int) -> float | None:
    if len(closes) <= bars:
        return None
    last, prev = closes[-1], closes[-1 - bars]
    if last is None or prev is None or prev == 0:
        return None
    return round((last / prev - 1) * 100, 2)


def _volatility1y(closes: list[float | None]) -> float | None:
    """일별 로그수익률 표본표준편차 × √252 × 100 (최근 252수익률, 최소 60개)."""
    window = [c for c in closes[-253:] if c is not None and c > 0]
    rets = [math.log(window[i] / window[i - 1]) for i in range(1, len(window)) if window[i - 1] > 0]
    if len(rets) < 60:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return round(math.sqrt(var) * math.sqrt(252) * 100, 2)


def buildRows(window: pl.DataFrame) -> dict[str, dict]:
    """종목별 시세 요약 — 2,500여 그룹 Python 루프 (행수 ~70만, 수 초)."""
    data: dict[str, dict] = {}
    for partKey, grp in window.partition_by("stockCode", as_dict=True).items():
        code = partKey[0] if isinstance(partKey, tuple) else partKey
        closes = grp["TDD_CLSPRC"].to_list()
        if not closes or closes[-1] is None:
            continue
        highs = [v for v in grp["TDD_HGPRC"].to_list()[-252:] if v is not None]
        lows = [v for v in grp["TDD_LWPRC"].to_list()[-252:] if v is not None]
        vols = [v for v in grp["ACC_TRDVOL"].to_list()[-30:] if v is not None]
        mktcap = grp["MKTCAP"].to_list()[-1]
        data[str(code)] = {
            "currentPrice": closes[-1],
            "marketCap": mktcap,
            "return1m": _retPct(closes, _RET_OFFSETS["return1m"]),
            "return3m": _retPct(closes, _RET_OFFSETS["return3m"]),
            "return1y": _retPct(closes, _RET_OFFSETS["return1y"]),
            "volatility1y": _volatility1y(closes),
            "week52High": max(highs) if highs else None,
            "week52Low": min(lows) if lows else None,
            "volumeAvg30d": int(sum(vols) / len(vols)) if vols else None,
            "foreignPct": None,  # gov 원천에 없음 — schemaVersion 1 유지 (기존에도 null)
            "beta": None,
            "priceUpdated": str(grp["BAS_DD"].to_list()[-1]),
        }
    return data


def main() -> None:
    # prebuild = offline only (HF 다운로드/업로드만 — offlineGuard 기본 허용 호스트).
    from dartlab.core.offlineGuard import enforceOffline

    enforceOffline()

    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-upload", action="store_true", help="로컬 JSON 만 생성 (검증용)")
    args = parser.parse_args()

    today = date.today()
    window = loadWindow(today)
    data = buildRows(window)
    latest = max((r["priceUpdated"] for r in data.values()), default="")
    payload = {
        "schemaVersion": 1,
        "builtAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lookbackDays": LOOKBACK_DAYS,
        "count": len(data),
        "data": data,
    }
    OUT_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    OUT_LOCAL.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[snapshot] {len(data)}종목, 최신 {latest} → {OUT_LOCAL} ({OUT_LOCAL.stat().st_size / 1e6:.1f}MB)")

    if args.skip_upload:
        return
    token = _env("HF_TOKEN")
    if not token:
        raise SystemExit("[snapshot] HF_TOKEN 없음 — 업로드 불가 (--skip-upload 로 로컬만 생성 가능)")
    from huggingface_hub import HfApi

    retryHfCall(
        HfApi(token=token).upload_file,
        path_or_fileobj=str(OUT_LOCAL),
        path_in_repo=PATH_IN_REPO,
        repo_id=HF_REPO,
        repo_type="dataset",
        commit_message=f"갱신: prices-snapshot {latest} ({len(data)}종목)",
    )
    print(f"[snapshot] HF 업로드 완료 → {PATH_IN_REPO}")


if __name__ == "__main__":
    main()
