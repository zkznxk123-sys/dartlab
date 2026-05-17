"""FRED/ECOS 카탈로그 전체 → HF macro 벌크 parquet 빌드.

GitHub Actions workflow (`.github/workflows/macroData.yml`) 가 호출한다.
운영자 cron 전용 스크립트이며, 라이브러리 기본 경로는 이 결과를 HF 에서 소비한다.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl


def _utcNow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _requireEnv(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} 환경변수 필수 (운영자 macro 벌크 빌드).")
    return value


def _readExisting(outDir: Path) -> tuple[pl.DataFrame, pl.DataFrame]:
    obsPath = outDir / "observations.parquet"
    manifestPath = outDir / "manifest.parquet"
    obs = pl.read_parquet(obsPath) if obsPath.exists() else pl.DataFrame()
    manifest = pl.read_parquet(manifestPath) if manifestPath.exists() else pl.DataFrame()
    return obs, manifest


def _fallbackSeries(existingObs: pl.DataFrame, seriesId: str) -> pl.DataFrame:
    if existingObs.is_empty() or "seriesId" not in existingObs.columns:
        return pl.DataFrame(schema={"seriesId": pl.Utf8, "date": pl.Date, "value": pl.Float64})
    return existingObs.filter(pl.col("seriesId") == seriesId)


def _stats(df: pl.DataFrame) -> dict[str, object]:
    if df.is_empty():
        return {"rowCount": 0, "startDate": None, "latestDate": None}
    dates = df.get_column("date").drop_nulls()
    if len(dates) == 0:
        return {"rowCount": df.height, "startDate": None, "latestDate": None}
    return {"rowCount": df.height, "startDate": str(dates.min()), "latestDate": str(dates.max())}


def _write(outDir: Path, observations: list[pl.DataFrame], manifestRows: list[dict]) -> None:
    outDir.mkdir(parents=True, exist_ok=True)
    if observations:
        obs = pl.concat(observations, how="diagonal_relaxed")
    else:
        obs = pl.DataFrame(schema={"seriesId": pl.Utf8, "date": pl.Date, "value": pl.Float64})
    obs = obs.with_columns(pl.col("date").cast(pl.Date), pl.col("value").cast(pl.Float64)).sort(["seriesId", "date"])
    manifest = pl.DataFrame(manifestRows)
    obs.write_parquet(outDir / "observations.parquet", compression="zstd")
    manifest.write_parquet(outDir / "manifest.parquet", compression="zstd")
    print(f"[macro] wrote {outDir} observations={obs.height} series={manifest.height}")


def buildFred(outDir: Path) -> None:
    from dartlab.gather.fred import Fred
    from dartlab.gather.fred.catalog import getAllEntries

    key = _requireEnv("FRED_API_KEY")
    fred = Fred(apiKey=key)
    existingObs, _ = _readExisting(outDir)
    updatedAt = _utcNow()
    observations: list[pl.DataFrame] = []
    manifestRows: list[dict] = []

    for entry in getAllEntries():
        status = "ok"
        err = ""
        try:
            df = fred.series(entry.id)
            df = df.with_columns(pl.lit(entry.id).alias("seriesId")).select("seriesId", "date", "value")
        except Exception as exc:
            fallback = _fallbackSeries(existingObs, entry.id)
            df = fallback
            status = "stale" if not fallback.is_empty() else "error"
            err = f"{type(exc).__name__}: {exc}"
            print(f"[fred] {entry.id}: {status} ({err})")
        observations.append(df)
        st = _stats(df)
        manifestRows.append(
            {
                "source": "fred",
                "seriesId": entry.id,
                "label": entry.label,
                "group": entry.group,
                "frequency": entry.frequency,
                "unit": entry.unit,
                "description": entry.description,
                "rowCount": st["rowCount"],
                "startDate": st["startDate"],
                "latestDate": st["latestDate"],
                "providerUpdatedAt": None,
                "updatedAtUtc": updatedAt,
                "status": status,
                "error": err,
            }
        )
    fred.close()
    _write(outDir, observations, manifestRows)


def buildEcos(outDir: Path) -> None:
    from dartlab.gather.ecos import Ecos
    from dartlab.gather.ecos.catalog import getAllIds, getEntry

    key = _requireEnv("ECOS_API_KEY")
    ecos = Ecos(apiKey=key)
    existingObs, _ = _readExisting(outDir)
    updatedAt = _utcNow()
    observations: list[pl.DataFrame] = []
    manifestRows: list[dict] = []

    for seriesId in getAllIds():
        entry = getEntry(seriesId)
        if entry is None:
            continue
        status = "ok"
        err = ""
        try:
            df = ecos.series(seriesId)
            df = df.with_columns(pl.lit(seriesId).alias("seriesId")).select("seriesId", "date", "value")
        except Exception as exc:
            fallback = _fallbackSeries(existingObs, seriesId)
            df = fallback
            status = "stale" if not fallback.is_empty() else "error"
            err = f"{type(exc).__name__}: {exc}"
            print(f"[ecos] {seriesId}: {status} ({err})")
        observations.append(df)
        st = _stats(df)
        manifestRows.append(
            {
                "source": "ecos",
                "seriesId": entry.id,
                "label": entry.label,
                "group": entry.group,
                "frequency": entry.frequency,
                "unit": entry.unit,
                "description": entry.description,
                "rowCount": st["rowCount"],
                "startDate": st["startDate"],
                "latestDate": st["latestDate"],
                "providerUpdatedAt": None,
                "updatedAtUtc": updatedAt,
                "status": status,
                "error": err,
            }
        )
    ecos.close()
    _write(outDir, observations, manifestRows)


def deploy(localRoot: Path, *, repoId: str) -> None:
    from huggingface_hub import HfApi, create_repo

    token = _requireEnv("HF_TOKEN")
    create_repo(repoId, token=token, repo_type="dataset", exist_ok=True)
    api = HfApi(token=token)
    for subdir in ("fred", "ecos"):
        src = localRoot / subdir
        if not src.is_dir():
            continue
        files = list(src.glob("*.parquet"))
        if not files:
            continue
        commit = api.upload_folder(
            folder_path=str(src),
            path_in_repo=f"macro/{subdir}",
            repo_id=repoId,
            repo_type="dataset",
            commit_message=f"build: macro {subdir} parquet ({len(files)} files)",
        )
        print(f"[hf] macro/{subdir}: {getattr(commit, 'commit_url', None)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["fred", "ecos", "all"], default="all")
    parser.add_argument("--out", default="data/macro")
    parser.add_argument("--repo-id", default="eddmpython/dartlab-data")
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()

    root = Path(args.out)
    if args.source in ("fred", "all"):
        buildFred(root / "fred")
    if args.source in ("ecos", "all"):
        buildEcos(root / "ecos")
    if args.push:
        deploy(root, repoId=args.repo_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
