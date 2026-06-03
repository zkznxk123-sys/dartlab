"""sections artifact SSOT read API — period sharded, raw XML 보존, 단순 단일 schema.

plan snazzy-wibbling-origami 사용자 비전 100%:
    - 단일 schema: chapter / topic / section_order / section_title /
                   section_content (raw XML) + 메타 / period
    - 추가 파일 0 (_index, _raw 폐기)
    - 추가 컬럼 0 (content_plain, content_table_struct 폐기)
    - docs.parquet 완전 폐기 가능 (sections artifact 가 모든 정보 보유)

저장:
    ``data/dart/sections/{code}/{period}.parquet``

호출:
    - ``loadSectionsLong`` — period sharded long read (메모리 절약, lazy projection)
    - ``loadSectionsWide`` — wide pivot (period 컬럼 N개, cell = raw XML)
    - ``Company.sectionsRaw()`` — wide 그대로 (viewer / parser 룰)
    - ``Company.sections`` — wide + cell strip (polars native regex, ~0.3s)
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

_log = logging.getLogger(__name__)

# 사용자 결정 (plan snazzy-wibbling-origami): 신규 artifact 가 옛 docs.parquet 위치를
# 폴더명까지 대체. data/dart/docs/{code}/{period}.parquet. 옛 flat data/dart/docs/{code}.parquet
# 와 파일 vs 디렉터리로 공존 (옛 flat 은 사용자 명시 전 보존, 코드는 하위폴더만 read).
_SECTIONS_REL = "dart/docs"


def sectionsDir(stockCode: str) -> Path:
    """종목별 sections artifact 디렉터리 path.

    Args:
        stockCode: 종목코드.

    Returns:
        ``{dataDir}/dart/docs/{stockCode}`` Path. 존재 여부는 검사하지 않는다.

    Example:
        >>> sectionsDir("005930").name
        '005930'

    Raises:
        없음 — 순수 경로 조합.
    """
    return Path(_cfg.dataDir) / _SECTIONS_REL / stockCode


def sectionsPath(stockCode: str, period: str) -> Path:
    """단일 period parquet path.

    Args:
        stockCode: 종목코드.
        period: period 라벨 (예 ``2024Q1``).

    Returns:
        ``{sectionsDir}/{period}.parquet`` Path.

    Example:
        >>> sectionsPath("005930", "2024Q1").name
        '2024Q1.parquet'

    Raises:
        없음 — 순수 경로 조합.
    """
    return sectionsDir(stockCode) / f"{period}.parquet"


def listAvailablePeriods(stockCode: str, *, limit: int | None = None) -> list[str]:
    """저장된 period 목록 (newer first). 디렉터리 미생성 시 빈 list.

    Args:
        stockCode: 종목코드.
        limit: 반환할 최근(newer-first) period 최대 개수. None = 전체.

    Returns:
        newer-first 정렬된 period 라벨 list. 디렉터리 부재면 빈 list.
        limit 지정 시 가장 최근 limit 개만.

    Example:
        >>> "2024Q1" in listAvailablePeriods("005930")  # doctest: +SKIP
        True

    Raises:
        없음 — 디렉터리 부재를 빈 list 로 흡수한다.
    """
    d = sectionsDir(stockCode)
    if not d.exists():
        return []
    periods = [p.stem for p in d.glob("*.parquet") if not p.stem.startswith("_")]
    ordered = sorted(periods, key=_periodSortKey, reverse=True)
    return ordered[:limit] if limit is not None else ordered


def _periodSortKey(period: str) -> tuple[int, int]:
    """period → (year, quarter rank). sectionsBuilder 가 annual 을 Q4 alias 로 emit."""
    if not period or len(period) < 4 or not period[:4].isdigit():
        return (-1, -1)
    year = int(period[:4])
    if period.endswith("Q1"):
        return (year, 1)
    if period.endswith("Q2"):
        return (year, 2)
    if period.endswith("Q3"):
        return (year, 3)
    if period.endswith("Q4"):
        return (year, 4)
    return (year, 4)


def hasSectionsArtifact(stockCode: str) -> bool:
    """artifact 가 1 개 이상 period 존재하면 True.

    Args:
        stockCode: 종목코드.

    Returns:
        period parquet 가 1 개 이상이면 True, 디렉터리 부재·빈 디렉터리면 False.

    Example:
        >>> hasSectionsArtifact("005930")
        True

    Raises:
        없음 — listAvailablePeriods 가 디렉터리 부재를 빈 list 로 흡수한다.
    """
    return bool(listAvailablePeriods(stockCode))


_HF_DOWNLOAD_ATTEMPTED: set[str] = set()


def _ensureFromHf(stockCode: str) -> bool:
    """artifact 부재 시 HF dataset 에서 lazy 다운로드 — 한 종목 디렉터리만.

    환경변수 ``DARTLAB_NO_HF_DOWNLOAD=1`` 또는 offline 시 skip.
    한 종목 1 회만 시도 (실패 시 반복 회피).
    """
    if hasSectionsArtifact(stockCode):
        return True
    import os as _os

    if _os.environ.get("DARTLAB_NO_HF_DOWNLOAD", "").strip() in ("1", "true", "True"):
        return False
    if stockCode in _HF_DOWNLOAD_ATTEMPTED:
        return False
    _HF_DOWNLOAD_ATTEMPTED.add(stockCode)
    try:
        from huggingface_hub import snapshot_download

        from dartlab.core.dataConfig import DATA_RELEASES, repoFor

        sectionsDirRel = DATA_RELEASES["sections"]["dir"]
        snapshot_download(
            repo_id=repoFor("sections"),
            repo_type="dataset",
            allow_patterns=[f"{sectionsDirRel}/{stockCode}/*.parquet"],
            local_dir=str(Path(_cfg.dataDir)),
        )
        return hasSectionsArtifact(stockCode)
    except Exception as exc:  # noqa: BLE001
        _log.warning("sections artifact HF 다운로드 실패 (%s): %s", stockCode, exc)
        return False


def loadSectionsLong(
    stockCode: str,
    *,
    periods: list[str] | None = None,
    columns: list[str] | None = None,
) -> pl.DataFrame | None:
    """sections artifact long format read — period sharded glob + columnar projection.

    schema: chapter / topic / section_order / section_title / section_content (raw XML)
           + 메타 (rcept_no/rcept_date/section_url/corp_name/atocid/assocnote) + period.

    Args:
        stockCode: 종목코드.
        periods: 특정 period 만. None = 전체.
        columns: select 할 컬럼 list. None = 전체.

    Returns:
        long format DataFrame 또는 None.

    Example:
        >>> df = loadSectionsLong("005930", periods=["2024Q1"])
        >>> "section_content" in df.columns
        True

    Raises:
        없음 — OSError/ComputeError/ShapeError 는 내부에서 포착해 경고 로그 후 None 반환.
    """
    if not hasSectionsArtifact(stockCode):
        _ensureFromHf(stockCode)
    available = listAvailablePeriods(stockCode)
    if not available:
        return None
    targetPeriods = available if periods is None else [p for p in available if p in set(periods)]
    if not targetPeriods:
        return None
    files = [str(sectionsPath(stockCode, p)) for p in targetPeriods]
    try:
        scan = pl.scan_parquet(files)
        if columns:
            availableSchema = set(scan.collect_schema().names())
            wantedCols = [c for c in columns if c in availableSchema]
            if not wantedCols:
                return None
            scan = scan.select(wantedCols)
        df = scan.collect()
    except (OSError, pl.exceptions.ComputeError, pl.exceptions.ShapeError) as exc:
        _log.warning("sectionsLong load 실패 (%s): %s", stockCode, exc)
        return None
    # 신 sectionsNew schema → 옛 docs.parquet 호환 컬럼 자동 양립. 기존 sectionsLegacy
    # caller (loadSectionsWide / dataLoader synthesis / c.sections 의 wide pivot 등) 가
    # topic / section_title / section_content / section_order 컬럼 의존. 신 chain 의
    # blockLeaf / contentRaw / blockOrder / disclosureKey 와 자동 매핑.
    if "blockLeaf" in df.columns and "section_title" not in df.columns:
        df = df.rename(
            {
                "blockLeaf": "section_title",
                "contentRaw": "section_content",
                "blockOrder": "section_order",
            }
        )
    if "topic" not in df.columns:
        if "disclosureKey" in df.columns and "xbrlClass" in df.columns:
            df = df.with_columns(pl.coalesce([pl.col("disclosureKey"), pl.col("xbrlClass")]).alias("topic"))
        elif "disclosureKey" in df.columns:
            df = df.with_columns(pl.col("disclosureKey").alias("topic"))
        elif "xbrlClass" in df.columns:
            df = df.with_columns(pl.col("xbrlClass").alias("topic"))
    if "rceptNo" in df.columns and "rcept_no" not in df.columns:
        df = df.rename({"rceptNo": "rcept_no"})
    if "corp" in df.columns and "stock_code" not in df.columns:
        df = df.rename({"corp": "stock_code"})
    return df


def loadSectionsWide(
    stockCode: str,
    *,
    periods: list[str] | None = None,
) -> pl.DataFrame | None:
    """sections artifact wide pivot — section_content (raw XML) cell.

    index = (chapter, topic, section_order, section_title)
    columns = period (N개)
    values = section_content (raw XML 그대로)

    viewer / sectionsRaw 가 cell 그대로 사용. ``Company.sections`` 는 cell 에 polars
    native regex strip 적용.

    Args:
        stockCode: 종목코드.
        periods: 특정 period 만. None = 전체.

    Returns:
        wide DataFrame 또는 None.

    Example:
        >>> wide = loadSectionsWide("005930")
        >>> any(c.endswith("Q1") or c.endswith("Q4") for c in wide.columns)
        True

    Raises:
        없음 — pivot 실패(ComputeError/ShapeError)는 내부 포착 후 None 반환.
    """
    long = loadSectionsLong(stockCode, periods=periods)
    if long is None or long.is_empty():
        return None
    if "period" not in long.columns or "section_content" not in long.columns:
        return None
    try:
        # artifact 는 BUILD 단계에서 이미 canonical 섹션/주석 단위로 수평화됨 (v5Builder.
        # _groupToSections, key = coalesce(xbrlClass, sectionLeaf, blockLeaf)). RUNTIME 은
        # 무거운 grouping 없이 동일 canonical 키로 cheap pivot 만 — period 간 한 줄 정렬.
        # 메타 컬럼 (period 별 상이) 은 pivot 전 drop.
        metaCols = ("rcept_no", "rcept_date", "section_url", "corp_name", "atocid", "assocnote")
        long = long.drop([c for c in metaCols if c in long.columns])
        keyParts = [
            pl.col(c).replace("", None) for c in ("xbrlClass", "sectionLeaf", "section_title") if c in long.columns
        ]
        long = long.with_columns(pl.coalesce(keyParts).fill_null("").alias("_key"))
        # period 무관 대표 메타 (정렬·표시·필터용) — pre-grouped 라 입력 작음, join 저렴.
        # sectionLeaf (SECTION-N 절 이름 "6. 배당에 관한 사항") 노출 필수 — show/select 가
        # c.sections 직접 필터로 동작하려면 사람이 읽는 절 이름이 컬럼에 있어야 한다.
        metaAggs = [pl.col("section_title").drop_nulls().first().alias("section_title")]
        if "sectionLeaf" in long.columns:
            metaAggs.append(pl.col("sectionLeaf").drop_nulls().first().alias("sectionLeaf"))
        if "topic" in long.columns:
            metaAggs.append(pl.col("topic").drop_nulls().first().alias("topic"))
        if "section_order" in long.columns:
            metaAggs.append(pl.col("section_order").min().alias("section_order"))
        keyMeta = long.group_by(["chapter", "_key"], maintain_order=True).agg(metaAggs)
        wide = long.pivot(
            values="section_content",
            index=["chapter", "_key"],
            on="period",
            aggregate_function="first",
        ).join(keyMeta, on=["chapter", "_key"], how="left")
        if "section_order" in wide.columns:
            wide = wide.sort("section_order", "chapter")
        return wide.drop("_key")
    except (pl.exceptions.ComputeError, pl.exceptions.ShapeError) as exc:
        _log.warning("sectionsWide pivot 실패 (%s): %s", stockCode, exc)
        return None


def loadSectionsRawXml(stockCode: str) -> pl.DataFrame | None:
    """sections artifact 를 docs.parquet 합성용 row-major DataFrame 으로 read.

    loader.DartDocsLoader.synthesizeToPath (옛 dataLoader._trySynthesizeDocsFromSections,
    PR-4b) 가 docs.parquet 부재 시 본 함수 → year/report_kind 부착 → docs.parquet 양식 저장.

    schema 변환 — sectionsNew (chapter/sectionLeaf/blockLeaf/contentRaw/blockOrder/
    xbrlClass/disclosureKey/period/corp/rceptNo) → docs.parquet 호환 (topic/
    section_title/section_content/section_order/stock_code/rcept_no/period) :

        - chapter       → chapter         (그대로)
        - sectionLeaf   → section_leaf    (그대로, 보조 컬럼)
        - blockLeaf     → section_title   (블록 라벨)
        - contentRaw    → section_content (raw XML 보존)
        - blockOrder    → section_order   (정수 순서)
        - disclosureKey → topic           (universal canonical key, null 시 xbrlClass fallback)
        - corp          → stock_code      (DART 종목코드)
        - rceptNo       → rcept_no        (공시 접수번호)
        - period        → period          (YYYYQ[1-4], year/report_kind 합성용)

    topic 변환 — disclosureKey (IFRS taxonomy snakeId) 가 신 chain canonical. 옛 16
    카테고리 매핑은 별도 bridge (Layer 3 tier2/3 확장 시).

    Args:
        stockCode: 종목코드.

    Returns:
        DataFrame 또는 None (artifact 부재).

    Example:
        >>> raw = loadSectionsRawXml("005930")
        >>> "section_content" in raw.columns
        True

    Raises:
        없음 — loadSectionsLong 에 위임, 내부에서 실패를 None 으로 흡수한다.
    """
    # loadSectionsLong 이 이미 신 schema → 옛 호환 자동 rename (topic/section_title/
    # section_content/section_order/stock_code/rcept_no). 본 함수는 별도 변환 없이 그대로 노출.
    return loadSectionsLong(stockCode, columns=None)


def loadSectionsIndex(stockCode: str) -> pl.DataFrame | None:
    """sections artifact 의 period 별 메타 (rcept_no/corp_name/...) index.

    loader.DartDocsLoader.synthesizeToPath 가 본 함수 → period 별 unique 메타를
    rawXml 결과에 join. 옛 _index.parquet 폐기 (plan snazzy-wibbling-origami) —
    sectionsNew artifact 의 행별 메타 컬럼에서 직접 추출.

    Returns:
        DataFrame ``period / rcept_no [+ 부속 메타]`` unique by period. None = artifact 부재.

    Example:
        >>> idx = loadSectionsIndex("005930")
        >>> idx.columns
        ['period', 'rcept_no']

    Raises:
        없음 — artifact·필수 컬럼(rcept_no/period) 부재 시 None 반환.
    """
    long = loadSectionsLong(stockCode, columns=None)
    if long is None or long.is_empty():
        return None
    # period 별 unique 메타 — loadSectionsLong 이 rceptNo→rcept_no 자동 rename 후 반환.
    if "rcept_no" not in long.columns or "period" not in long.columns:
        return None
    return long.select(["period", "rcept_no"]).unique(subset=["period"])


def stripTagsExpr(col: str) -> pl.Expr:
    """polars native regex tag strip — XML 태그 제거 + 다중 공백 정리.

    rust SIMD 가속. Python map_elements 대비 50x 빠름. ``Company.sections`` 가 wide
    cell 들에 본 expr 일괄 적용 → 0.3s 안 strip 완료.

    Args:
        col: 대상 컬럼명.

    Returns:
        pl.Expr — strip 결과 string.

    Example:
        >>> import polars as pl
        >>> pl.DataFrame({"x": ["<p>가</p>"]}).select(stripTagsExpr("x")).item()
        '가'

    Raises:
        없음 — 순수 expr 빌더. 평가 시 col 이 DataFrame 에 없으면 polars 가
        ColumnNotFoundError 를 던진다.
    """
    return pl.col(col).str.replace_all(r"<[^>]+>", " ").str.replace_all(r"[ \t]+", " ").str.strip_chars()
