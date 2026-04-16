"""EDGAR scan 프리빌드 — 전종목 재무 지표를 단일 parquet로 합산.

DART scan/builder.py 패턴을 EDGAR에 이식.
200개 단위 배치 + 중간 파일 병합 + 메모리 안전.

사용법::

    from dartlab.scan.edgarBuilder import buildEdgarScan
    path = buildEdgarScan(sinceYear=2021, verbose=True)
"""

from __future__ import annotations

import gc
from pathlib import Path

import polars as pl

_BATCH_SIZE = 200


def buildEdgarFinance(*, sinceYear: int = 2021, verbose: bool = False) -> Path:
    """전종목 EDGAR finance → scan/finance.parquet.

    각 CIK parquet에서 최신 연간 BS/IS/CF 주요 계정을 추출하여
    하나의 wide DataFrame으로 합산한다.
    """
    from dartlab import config as _cfg

    edgarDir = Path(_cfg.dataDir) / "edgar" / "finance"
    outDir = Path(_cfg.dataDir) / "edgar" / "scan"
    outDir.mkdir(parents=True, exist_ok=True)

    if not edgarDir.exists():
        raise FileNotFoundError(f"EDGAR finance 디렉토리 없음: {edgarDir}")

    parquets = sorted(edgarDir.glob("*.parquet"))
    if not parquets:
        raise FileNotFoundError("EDGAR finance parquet 없음")

    if verbose:
        print(f"[edgarBuilder] {len(parquets)} CIK parquets → scan/finance.parquet")

    # 주요 계정
    # DART 호환 snakeId 기준 — scan 소비자(_edgar_scan.py) 가 total_assets/total_liabilities 사용.
    # EDGAR primary tag 해결은 EdgarMapper.getTagsForSnakeIds() 가 SNAKEID_ALIASES 역방향으로 자동 처리.
    # ebitda 는 XBRL 원본 태그 없음 — 파생 계산 대상이라 제외.
    targetAccounts = [
        # IS
        "sales",
        "cost_of_goods_sold",
        "gross_profit",
        "operating_profit",
        "net_profit",
        "research_and_development",
        "selling_general_and_administrative",
        "interest_expense",
        "depreciation_amortization",
        # IS — 업종 특례 (REIT/은행)
        "funds_from_operations",
        "rental_income",
        "net_interest_income",
        "noninterest_income",
        "provision_for_loan_losses",
        # BS
        "total_assets",
        "current_assets",
        "total_liabilities",
        "current_liabilities",
        "total_stockholders_equity",
        "cash_and_cash_equivalents",
        "inventories",
        "trade_and_other_receivables",
        "trade_and_other_payables",
        "property_plant_and_equipment",
        "goodwill",
        "intangible_assets",
        "treasury_stock",
        "retained_earnings",
        "shortterm_borrowings",
        "longterm_borrowings",
        # CF
        "operating_cashflow",
        "investing_cashflow",
        "financing_cash_flow",
        "capex",
        "dividends_paid",
        "share_repurchase",
    ]

    # snakeId → XBRL 태그 역조회 테이블 (사전 빌드, map_elements 회피)
    snakeIdToTags = _buildReverseTagMap(targetAccounts)

    # CIK → SIC 매핑 (meta/sub/*.parquet 전분기 병합, 최신 filed 우선)
    sicMap = _buildCikToSicMap()

    batchFiles: list[Path] = []
    records: list[dict] = []

    for idx, fp in enumerate(parquets):
        cik = fp.stem
        try:
            df = pl.read_parquet(fp)
            if df.is_empty():
                continue

            # 10-K만, sinceYear 이후 + 상한 (달력 연도+1, 비12월결산 커버)
            # 일부 companyfacts.zip 엔트리에 fy=29953000 / 43465 (Excel 날짜코드) 같은
            # 잘못된 값이 섞여 있음 → 미래 연도 필터로 제거.
            from datetime import datetime as _dt

            maxFy = _dt.utcnow().year + 1
            annual = df.filter(
                (pl.col("form") == "10-K")
                & (pl.col("fy") >= sinceYear)
                & (pl.col("fy") <= maxFy)
            )
            if annual.is_empty():
                continue

            latestFy = annual["fy"].max()
            latest = annual.filter(pl.col("fy") == latestFy)
            entityName = latest["entityName"][0] if latest.height > 0 else ""

            # 10-K 는 비교재무제표로 과거 2~3년 데이터를 같은 fy 라벨로 포함한다.
            # 해당 fy 의 **standalone 연간 값만** 선택 — end date 가 fy 연도의 +/- 1 년
            # 범위에 들고 연간(duration ≥ 300일) 또는 frame=CY{latestFy} 인 행.
            latest = latest.with_columns(
                (pl.col("end") - pl.col("start")).dt.total_days().alias("_dur")
            )
            fyAnnual = latest.filter(
                (pl.col("_dur").is_null() | (pl.col("_dur") > 300))
                & (
                    pl.col("end").dt.year().is_between(latestFy - 1, latestFy)
                    | pl.col("frame").str.starts_with(f"CY{latestFy}")
                )
            )
            if fyAnnual.is_empty():
                continue

            # snakeId 매핑 → 값 추출. end 가 최대인 값(해당 fy 결산일) 우선.
            record: dict = {
                "stockCode": cik,
                "corpName": entityName,
                "fy": int(latestFy),
                "sic": sicMap.get(cik),
                "sector": _sicToSector(sicMap.get(cik)),
            }
            usdRows = fyAnnual.filter(pl.col("unit").str.contains("(?i)USD"))
            for snakeId in targetAccounts:
                candidateTags = snakeIdToTags.get(snakeId, [])
                if not candidateTags:
                    continue
                tagRows = usdRows.filter(pl.col("tag").is_in(candidateTags))
                if tagRows.height > 0:
                    # end date DESC → 가장 최신 결산일 값 우선
                    val = tagRows.sort(["end", "filed"], descending=[True, True])["val"][0]
                    record[snakeId] = val

            records.append(record)

        except (pl.exceptions.ComputeError, OSError):
            continue

        # 배치 저장
        if len(records) >= _BATCH_SIZE:
            batchPath = outDir / f"_batch_{len(batchFiles):04d}.parquet"
            pl.DataFrame(records).write_parquet(batchPath)
            batchFiles.append(batchPath)
            records.clear()
            gc.collect()
            if verbose:
                print(f"  batch {len(batchFiles)}: {idx + 1}/{len(parquets)}")

    # 나머지
    if records:
        batchPath = outDir / f"_batch_{len(batchFiles):04d}.parquet"
        pl.DataFrame(records).write_parquet(batchPath)
        batchFiles.append(batchPath)

    # 병합
    if not batchFiles:
        raise ValueError("프리빌드할 데이터 없음")

    frames = [pl.read_parquet(p) for p in batchFiles]
    merged = pl.concat(frames, how="diagonal_relaxed")

    outPath = outDir / "finance.parquet"
    merged.write_parquet(outPath, compression="zstd")

    # 임시 파일 정리
    for bp in batchFiles:
        bp.unlink(missing_ok=True)

    if verbose:
        print(f"[edgarBuilder] 완료: {outPath} ({merged.height}행, {merged.width}열)")

    return outPath


def buildEdgarScan(*, sinceYear: int = 2021, verbose: bool = False) -> Path:
    """전체 EDGAR scan 프리빌드."""
    return buildEdgarFinance(sinceYear=sinceYear, verbose=verbose)


def _buildCikToSicMap() -> dict[str, str]:
    """meta/sub/*.parquet 전 분기 병합 → CIK → SIC 매핑 (최신 filed 우선).

    SIC(Standard Industrial Classification) 는 SEC submission 메타 (sub.txt) 의
    sic 필드에 기업별로 기록됨. REIT/은행/ETF 같은 특수 업종을 구분하는 데 사용.
    분기 벌크 (`{Y}q{Q}.zip` → `meta/sub/*.parquet`) 가 없으면 빈 dict 반환.
    """
    from dartlab import config as _cfg

    metaSubDir = Path(_cfg.dataDir) / "edgar" / "meta" / "sub"
    if not metaSubDir.exists():
        return {}
    parquets = sorted(metaSubDir.glob("*.parquet"))
    if not parquets:
        return {}

    frames: list[pl.DataFrame] = []
    for p in parquets:
        try:
            df = pl.read_parquet(p, columns=["cik", "sic", "filed"])
            frames.append(df)
        except (pl.exceptions.ComputeError, OSError):
            continue
    if not frames:
        return {}

    merged = pl.concat(frames, how="vertical_relaxed").filter(pl.col("sic").is_not_null())
    if merged.is_empty():
        return {}

    # CIK 별 최신 filed 행 (filed 가 동일할 때 첫 번째)
    latest = merged.sort("filed", descending=True).group_by("cik").head(1)
    return dict(zip(latest["cik"].to_list(), latest["sic"].to_list()))


# SIC 대분류 → 섹터 매핑 (SEC 4-digit SIC 앞 2자리 기준, Fama-French 풍)
# https://www.sec.gov/info/edgar/siccodes.htm
_SIC_SECTOR_RANGES: list[tuple[int, int, str]] = [
    (100, 999, "agriculture"),
    (1000, 1499, "mining"),
    (1500, 1799, "construction"),
    (2000, 3999, "manufacturing"),
    (4000, 4899, "transportation_utilities"),
    (4900, 4999, "utilities"),
    (5000, 5199, "wholesale"),
    (5200, 5999, "retail"),
    (6000, 6099, "banks"),
    (6100, 6199, "credit"),
    (6200, 6299, "securities"),
    (6300, 6499, "insurance"),
    (6500, 6599, "real_estate"),
    (6700, 6770, "holding_other"),
    (6798, 6798, "reit"),  # Real Estate Investment Trusts
    (6770, 6799, "fund"),
    (7000, 8999, "services"),
    (9100, 9729, "public_admin"),
]


def _sicToSector(sic: str | None) -> str | None:
    """SIC 코드 → 섹터 분류. 매칭 실패 시 None."""
    if not sic:
        return None
    try:
        code = int(sic)
    except (ValueError, TypeError):
        return None
    for lo, hi, sector in _SIC_SECTOR_RANGES:
        if lo <= code <= hi:
            return sector
    return None


def _buildReverseTagMap(snakeIds: list[str]) -> dict[str, list[str]]:
    """snakeId → XBRL 태그 목록 역조회 테이블.

    EdgarMapper.getTagsForSnakeIds()를 개별 snakeId씩 호출하여
    snakeId별 후보 태그 목록을 구축. map_elements 회피.
    """
    from dartlab.providers.edgar.finance.mapper import EdgarMapper

    result: dict[str, list[str]] = {}
    for sid in snakeIds:
        tags = EdgarMapper.getTagsForSnakeIds([sid])
        result[sid] = sorted(tags)
    return result


def _guessStmt(snakeId: str) -> str:
    """snakeId로 재무제표 유형 추정."""
    if snakeId in ("sales", "operating_profit", "net_profit", "interest_expense", "depreciation_amortization"):
        return "IS"
    if snakeId in ("operating_cashflow", "investing_cashflow", "financing_cash_flow", "capex", "dividends_paid"):
        return "CF"
    return "BS"
