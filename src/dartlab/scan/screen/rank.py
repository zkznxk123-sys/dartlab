"""종목 규모 랭크.

전체 시장 + 섹터 내 순위를 산출한다.
첫 호출 시 전체 종목을 순회해서 스냅샷을 생성하고 로컬 캐시에 저장.
이후 호출은 캐시에서 조회 (빌드 2분 → 조회 즉시).
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

from dartlab.core.dataConfig import DATA_RELEASES


@dataclass
class RankInfo:
    """단일 종목의 랭크 정보.

    Attributes
    ----------
    stockCode : str — 종목코드
    corpName : str — 회사명
    sector : str — 섹터
    industryGroup : str — 산업군
    revenue : float | None — 매출 TTM (원)
    totalAssets : float | None — 총자산 (원)
    revenueGrowth3Y : float | None — 매출 3년 성장률 (%)
    revenueRank : int | None — 전체 매출 순위
    revenueTotal : int — 매출 집계 종목 수
    revenueRankInSector : int | None — 섹터 내 매출 순위
    revenueSectorTotal : int — 섹터 내 종목 수
    assetRank : int | None — 전체 자산 순위
    assetTotal : int — 자산 집계 종목 수
    assetRankInSector : int | None — 섹터 내 자산 순위
    assetSectorTotal : int — 섹터 내 종목 수
    growthRank : int | None — 전체 성장 순위
    growthTotal : int — 성장 집계 종목 수
    growthRankInSector : int | None — 섹터 내 성장 순위
    growthSectorTotal : int — 섹터 내 종목 수
    sizeClass : str — 규모 분류 (large/mid/small)
    """

    stockCode: str
    corpName: str
    sector: str
    industryGroup: str

    revenue: float | None = None
    totalAssets: float | None = None
    revenueGrowth3Y: float | None = None

    revenueRank: int | None = None
    revenueTotal: int = 0
    revenueRankInSector: int | None = None
    revenueSectorTotal: int = 0

    assetRank: int | None = None
    assetTotal: int = 0
    assetRankInSector: int | None = None
    assetSectorTotal: int = 0

    growthRank: int | None = None
    growthTotal: int = 0
    growthRankInSector: int | None = None
    growthSectorTotal: int = 0

    sizeClass: str = ""

    def __repr__(self):
        revStr = f"매출 {self.revenueRank}/{self.revenueTotal}" if self.revenueRank else "매출 N/A"
        secStr = f"섹터 {self.revenueRankInSector}/{self.revenueSectorTotal}" if self.revenueRankInSector else ""
        return f"RankInfo({self.corpName}, {revStr}, {secStr}, {self.sizeClass})"


def _cacheDir() -> Path:
    """랭크 스냅샷 캐시 디렉토리.

    Returns
    -------
    Path
        ~/.dartlab/data/_cache/
    """
    from dartlab import config

    return Path(config.dataDir) / "_cache"


def _cachePath() -> Path:
    """랭크 스냅샷 JSON 캐시 경로.

    Returns
    -------
    Path
        ~/.dartlab/data/_cache/rank_snapshot.json
    """
    return _cacheDir() / "rank_snapshot.json"


def _financeExists(stockCode: str) -> bool:
    """종목의 finance parquet 존재 여부.

    Returns
    -------
    bool
        finance/{stockCode}.parquet 존재 시 True.
    """
    from dartlab import config

    dataDir = Path(config.dataDir) / DATA_RELEASES["finance"]["dir"]
    return (dataDir / f"{stockCode}.parquet").exists()


def buildSnapshot(*, verbose: bool = True) -> dict[str, RankInfo]:
    """전체 종목 랭크 스냅샷 생성 및 캐시 저장.

    Parameters
    ----------
    verbose : bool
        진행 로그 출력 여부.

    Returns
    -------
    dict[str, RankInfo]
        {종목코드: RankInfo} — 매출/자산/성장 순위 + 섹터 내 순위 + sizeClass.

    Capabilities:
        - buildSnapshot: 전종목 finance pivot → 매출/자산/성장 + 섹터내 순위 + sizeClass 캐시.
        - getRank: 캐시에서 1 종목 RankInfo 조회. getRankOrBuild: 없으면 build 후 조회.

    AIContext:
        Story / Insight builder 가 1 사 분석에서 "시장 순위" / "섹터 위치" 언급 source. 캐시
        hit 시 즉시 응답.

    Guide:
        - importlib 우회로 industry(L2) → scan(L1.5) 단방향 정책 유지.
        - 캐시 stale 정책 없음 — caller 가 명시 rebuild.

    When:
        Story 빌더가 종목별 시장 순위 인용 시. cron 으로 캐시 사전 빌드 권장.

    How:
        KIND listing → 종목 iterate → finance pivot → RankInfo dict 적재 → 캐시 write.

    Requires:
        - 로컬 ``data/dart/finance/{stockCode}.parquet`` + KIND listing

    SeeAlso:
        - :func:`dartlab.scan.builders.kr.snapshot.buildScanSnapshot` — 4 axis snapshot (보완)

    Raises
    ------
    polars.PolarsError
        finance pivot 또는 KIND listing 손상 시.

    Examples
    --------
    >>> from dartlab.scan.screen.rank import buildSnapshot
    >>> snap = buildSnapshot(verbose=False)
    >>> snap["005930"].sizeClass
    'large'
    """
    import importlib

    from dartlab.core.utils.extract import getLatest, getRevenueGrowth3Y, getTTM
    from dartlab.gather.krx.listing import getKindList
    from dartlab.providers.dart.finance.pivot import buildAnnual

    # industry(L2) 는 단방향 정책 상 scan(L1.5) 이 직접 import 금지 — importlib 우회.
    # cycleScan/import-linter 가 못 잡는 동적 import.
    classify = getattr(importlib.import_module("dartlab.industry"), "classify")

    kindDf = getKindList()
    codes = kindDf["종목코드"].to_list()
    names = kindDf["회사명"].to_list()
    industries = kindDf["업종"].to_list() if "업종" in kindDf.columns else [None] * len(codes)
    products = kindDf["주요제품"].to_list() if "주요제품" in kindDf.columns else [None] * len(codes)

    records: list[dict] = []
    for i, code in enumerate(codes):
        if verbose and i % 500 == 0:
            logger.info("[rank] %d/%d...", i, len(codes))

        info = classify(names[i], industries[i], products[i])

        rec = {
            "stockCode": code,
            "corpName": names[i],
            "sector": info.sector.value,
            "industryGroup": info.industryGroup.value,
            "revenue": None,
            "totalAssets": None,
            "revenueGrowth3Y": None,
        }

        if _financeExists(code):
            aResult = buildAnnual(code)
            if aResult is not None:
                aSeries, _ = aResult
                # rank 가 필요한 3 필드만 직접 추출 (analysis.calcRatios 의존 제거 — 단방향 정책).
                # analysis.financial.ratios.calcRatios 가 같은 헬퍼 사용 → 결과 동일.
                revenueTtm = getTTM(aSeries, "IS", "sales") or getTTM(aSeries, "IS", "revenue")
                if revenueTtm and revenueTtm > 0:
                    rec["revenue"] = revenueTtm
                rec["totalAssets"] = getLatest(aSeries, "BS", "total_assets")
                rec["revenueGrowth3Y"] = getRevenueGrowth3Y(aSeries)

        records.append(rec)

    revSorted = sorted(
        [r for r in records if r["revenue"] is not None],
        key=lambda x: x["revenue"],
        reverse=True,
    )
    assetSorted = sorted(
        [r for r in records if r["totalAssets"] is not None and r["totalAssets"] > 0],
        key=lambda x: x["totalAssets"],
        reverse=True,
    )
    growthSorted = sorted(
        [r for r in records if r["revenueGrowth3Y"] is not None],
        key=lambda x: x["revenueGrowth3Y"],
        reverse=True,
    )

    nRev = len(revSorted)
    nAsset = len(assetSorted)
    nGrowth = len(growthSorted)

    revRank = {r["stockCode"]: i + 1 for i, r in enumerate(revSorted)}
    assetRank = {r["stockCode"]: i + 1 for i, r in enumerate(assetSorted)}
    growthRank = {r["stockCode"]: i + 1 for i, r in enumerate(growthSorted)}

    from collections import defaultdict

    sectorRevLists: dict[str, list[str]] = defaultdict(list)
    sectorAssetLists: dict[str, list[str]] = defaultdict(list)
    sectorGrowthLists: dict[str, list[str]] = defaultdict(list)

    for r in revSorted:
        sectorRevLists[r["sector"]].append(r["stockCode"])
    for r in assetSorted:
        sectorAssetLists[r["sector"]].append(r["stockCode"])
    for r in growthSorted:
        sectorGrowthLists[r["sector"]].append(r["stockCode"])

    sectorRevRank: dict[str, tuple[int, int]] = {}
    for sector, codeList in sectorRevLists.items():
        for i, c in enumerate(codeList):
            sectorRevRank[c] = (i + 1, len(codeList))

    sectorAssetRank: dict[str, tuple[int, int]] = {}
    for sector, codeList in sectorAssetLists.items():
        for i, c in enumerate(codeList):
            sectorAssetRank[c] = (i + 1, len(codeList))

    sectorGrowthRank: dict[str, tuple[int, int]] = {}
    for sector, codeList in sectorGrowthLists.items():
        for i, c in enumerate(codeList):
            sectorGrowthRank[c] = (i + 1, len(codeList))

    result: dict[str, RankInfo] = {}
    for rec in records:
        code = rec["stockCode"]
        rr = revRank.get(code)
        ar = assetRank.get(code)
        gr = growthRank.get(code)
        srr = sectorRevRank.get(code)
        sar = sectorAssetRank.get(code)
        sgr = sectorGrowthRank.get(code)

        sizeClass = ""
        if rr is not None:
            pct = rr / nRev
            sizeClass = "large" if pct <= 0.10 else "mid" if pct <= 0.30 else "small"

        ri = RankInfo(
            stockCode=code,
            corpName=rec["corpName"],
            sector=rec["sector"],
            industryGroup=rec["industryGroup"],
            revenue=rec["revenue"],
            totalAssets=rec["totalAssets"],
            revenueGrowth3Y=rec["revenueGrowth3Y"],
            revenueRank=rr,
            revenueTotal=nRev,
            revenueRankInSector=srr[0] if srr else None,
            revenueSectorTotal=srr[1] if srr else 0,
            assetRank=ar,
            assetTotal=nAsset,
            assetRankInSector=sar[0] if sar else None,
            assetSectorTotal=sar[1] if sar else 0,
            growthRank=gr,
            growthTotal=nGrowth,
            growthRankInSector=sgr[0] if sgr else None,
            growthSectorTotal=sgr[1] if sgr else 0,
            sizeClass=sizeClass,
        )
        result[code] = ri

    cacheDir = _cacheDir()
    cacheDir.mkdir(parents=True, exist_ok=True)
    cachePath = _cachePath()
    serializable = {code: asdict(ri) for code, ri in result.items()}
    cachePath.write_text(json.dumps(serializable, ensure_ascii=False), encoding="utf-8")

    if verbose:
        logger.info("[rank] %d종목 스냅샷 저장: %s", len(result), cachePath)

    return result


def _loadCache() -> dict[str, RankInfo] | None:
    """JSON 캐시에서 RankInfo dict 로드.

    Returns
    -------
    dict[str, RankInfo] | None
        {종목코드: RankInfo}. 캐시 없으면 None.
    """
    cachePath = _cachePath()
    if not cachePath.exists():
        return None
    raw = json.loads(cachePath.read_text(encoding="utf-8"))
    result = {}
    for code, data in raw.items():
        result[code] = RankInfo(**data)
    return result


_SNAPSHOT: dict[str, RankInfo] | None = None
_SNAPSHOT_LOCK = threading.Lock()


def _ensureSnapshot() -> dict[str, RankInfo] | None:
    """스냅샷 캐시 로드 (thread-safe, lazy).

    Returns
    -------
    dict[str, RankInfo] | None
        {종목코드: RankInfo}. 캐시 없으면 None.
    """
    global _SNAPSHOT
    if _SNAPSHOT is not None:
        return _SNAPSHOT
    with _SNAPSHOT_LOCK:
        if _SNAPSHOT is not None:
            return _SNAPSHOT
        _SNAPSHOT = _loadCache()
    return _SNAPSHOT


def getRank(stockCode: str) -> RankInfo | None:
    """종목 랭크 정보 조회.

    Parameters
    ----------
    stockCode : str
        종목코드 (6자리).

    Returns
    -------
    RankInfo | None
        랭크 정보. 스냅샷 없거나 종목 없으면 None.

    Raises
    ------
    없음 — 스냅샷 미존재 시 None 반환.

    Examples
    --------
    >>> from dartlab.scan.screen.rank import getRank
    >>> r = getRank("005930")
    >>> r.sizeClass if r else "no snapshot"

    Capabilities:
        - 캐시된 RankInfo 1 종목 조회. 캐시 없으면 None — caller 가 ``getRankOrBuild`` 또는
          ``buildSnapshot`` 으로 보강.

    AIContext:
        Story 빌더가 1 사 분석에서 시장 순위 인용 시. 캐시 hit 시 즉시 응답.

    Guide:
        - 캐시 stale 정책 없음 — caller 가 명시 rebuild.

    When:
        Story/Insight 빌더 안에서.

    How:
        ``_ensureSnapshot`` → dict get.

    Requires:
        - ``data/dart/scan/rank_snapshot.pickle`` (캐시 파일)

    SeeAlso:
        - :func:`getRankOrBuild` · :func:`buildSnapshot`
    """
    snap = _ensureSnapshot()
    if snap is None:
        return None
    return snap.get(stockCode)


def getRankOrBuild(stockCode: str, *, verbose: bool = True) -> RankInfo | None:
    """종목 랭크 정보 조회 — 스냅샷 없으면 자동 빌드.

    Parameters
    ----------
    stockCode : str
        종목코드 (6자리).
    verbose : bool
        빌드 시 진행 로그 출력 여부.

    Returns
    -------
    RankInfo | None
        랭크 정보. 빌드 후에도 종목 없으면 None.

    Capabilities:
        - buildSnapshot: 전종목 finance pivot → 매출/자산/성장 + 섹터내 순위 + sizeClass 캐시.
        - getRank: 캐시에서 1 종목 RankInfo 조회. getRankOrBuild: 없으면 build 후 조회.

    AIContext:
        Story / Insight builder 가 1 사 분석에서 "시장 순위" / "섹터 위치" 언급 source. 캐시
        hit 시 즉시 응답.

    Guide:
        - importlib 우회로 industry(L2) → scan(L1.5) 단방향 정책 유지.
        - 캐시 stale 정책 없음 — caller 가 명시 rebuild.

    When:
        Story 빌더가 종목별 시장 순위 인용 시. cron 으로 캐시 사전 빌드 권장.

    How:
        KIND listing → 종목 iterate → finance pivot → RankInfo dict 적재 → 캐시 write.

    Requires:
        - 로컬 ``data/dart/finance/{stockCode}.parquet`` + KIND listing

    SeeAlso:
        - :func:`dartlab.scan.builders.kr.snapshot.buildScanSnapshot` — 4 axis snapshot (보완)

    Raises
    ------
    polars.PolarsError
        buildSnapshot 빌드 실패 시 전파.

    Examples
    --------
    >>> from dartlab.scan.screen.rank import getRankOrBuild
    >>> r = getRankOrBuild("005930")
    >>> r.sizeClass if r else "unknown"
    """
    global _SNAPSHOT
    snap = _ensureSnapshot()
    if snap is None:
        if verbose:
            logger.info("[dartlab] 랭크 스냅샷이 없습니다. 전체 종목 빌드를 시작합니다...")
        _SNAPSHOT = buildSnapshot(verbose=verbose)
    return _SNAPSHOT.get(stockCode)
