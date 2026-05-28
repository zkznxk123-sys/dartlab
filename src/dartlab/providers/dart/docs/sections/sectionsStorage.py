"""sections artifact SSOT 영속화 read/write — period-sharded parquet.

본 모듈은 ``operation.sectionsRefactor`` 의 *SSOT 통합* 단계의 read 진입점이다.
기존 ``data/dart/docs/{code}.parquet`` + 런타임 sections() build (6~18s) 의 콜드 비용을
zip ingest 시점 1 회 영속화로 옮긴다. 본 모듈은 *읽기 전용 SSOT* — 빌더는 별도
``sectionsBuilder.py`` 가 담당.

저장 양식 (period-sharded long format):
    ``data/dart/sections/{code}/{period}.parquet``
    schema: topic / blockType / blockOrder / segmentKey / content + (향후 다컬럼 확장)

read 의 핵심 효과:
    - polars mmap parquet → 런타임 XML parse 0
    - columnar projection — 필요 컬럼만 페이지 fault (분석 path 가 content_raw 페이지 fault 안 함)
    - period filter — viewer 가 한 period 만 보면 그 파일 page 만 RAM
    - lazy pivot — long → wide 변환은 호출 시점

본 단계 (MVP) 는 *단일 content 컬럼* + 기존 cell 양식 그대로 (mixed string). 다음
단계에서 content_raw / content_plain / content_table_struct 3 컬럼 분리.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

_log = logging.getLogger(__name__)

# data/dart/sections/{code}/{period}.parquet — docs.parquet 과 같은 dataDir 아래
# 별 디렉터리 위계. period-sharded.
_SECTIONS_REL = "dart/sections"


def sectionsDir(stockCode: str) -> Path:
    """종목별 sections artifact 디렉터리 path.

    Args:
        stockCode: 종목코드 (6 자리).

    Returns:
        ``data/dart/sections/{stockCode}/`` Path. 미생성 (caller 가 builder 호출 시 자동 mkdir).

    Raises:
        없음.

    Example:
        >>> sectionsDir("005930").name
        '005930'
    """
    return Path(_cfg.dataDir) / _SECTIONS_REL / stockCode


def sectionsPath(stockCode: str, period: str) -> Path:
    """단일 period parquet path.

    Args:
        stockCode: 종목코드.
        period: ``"2025"`` / ``"2025Q1"`` / ``"2025Q2"`` / ``"2025Q3"`` 양식.

    Returns:
        period 별 parquet 파일 path.

    Raises:
        없음.

    Example:
        >>> sectionsPath("005930", "2025Q1").name
        '2025Q1.parquet'
    """
    return sectionsDir(stockCode) / f"{period}.parquet"


def listAvailablePeriods(stockCode: str) -> list[str]:
    """저장된 period 목록 (newer first). 디렉터리 미생성 시 빈 list.

    Args:
        stockCode: 종목코드.

    Returns:
        period 문자열 list. 정렬: 연도 desc, 분기 desc (annual=Q4 후).

    Raises:
        없음.

    Example:
        >>> listAvailablePeriods("005930")  # doctest: +SKIP
        ['2025Q3', '2025', '2025Q1', '2024', ...]
    """
    d = sectionsDir(stockCode)
    if not d.exists():
        return []
    periods = [p.stem for p in d.glob("*.parquet") if not p.stem.startswith("_")]
    return sorted(periods, key=_periodSortKey, reverse=True)


def _periodSortKey(period: str) -> tuple[int, int]:
    """period → (year, quarter rank) sort key. annual=4, Q1=1, Q2=2, Q3=3, Q4=4.

    sections() 가 annual 을 ``"2025Q4"`` 양식으로 emit 하므로 Q4 = annual = rank 4.
    ``"2025"`` 양식도 동일 rank 4 (호환).
    """
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
    return (year, 4)  # annual (no suffix)


def hasSectionsArtifact(stockCode: str) -> bool:
    """artifact 가 1 개 이상 period 존재하면 True.

    HF 다운로드 검증 / sectionsBuilder 가 빌드 필요 판단에 사용.

    Args:
        stockCode: 종목코드.

    Returns:
        bool — 1 개 이상 period parquet 존재 시 True.

    Raises:
        없음.

    Example:
        >>> hasSectionsArtifact("005930")  # doctest: +SKIP
        True
    """
    return bool(listAvailablePeriods(stockCode))


# HF 다운로드 시도 캐시 — 한 종목 1 회만 시도 (실패 시 반복 호출 회피).
_HF_DOWNLOAD_ATTEMPTED: set[str] = set()


def _ensureFromHf(stockCode: str) -> bool:
    """artifact 부재 시 HF dataset 에서 lazy 다운로드 — sections category nested 양식.

    plan snazzy-wibbling-origami PR-4b-ii. ``huggingface_hub.snapshot_download`` 의
    allow_patterns 으로 *한 종목 디렉터리만* 선택 다운로드 (전체 dataset 무관). 한
    종목 ~1.5MB × 분기 수 = ~수 MB. 첫 호출 시 1 회 다운로드, 이후 mmap.

    환경변수 ``DARTLAB_NO_HF_DOWNLOAD=1`` 또는 offline 환경 시 skip.

    Args:
        stockCode: 종목코드.

    Returns:
        bool — 다운로드 성공 또는 이미 존재 시 True.

    Raises:
        없음 — 네트워크 실패 / huggingface_hub 미설치 / 다른 IO 에러는 warning + False.
    """
    if hasSectionsArtifact(stockCode):
        return True
    import os as _os

    if _os.environ.get("DARTLAB_NO_HF_DOWNLOAD", "").strip() in ("1", "true", "True"):
        return False
    # 한 종목 당 1 회만 시도 (실패 시 반복 HF 호출 회피).
    if stockCode in _HF_DOWNLOAD_ATTEMPTED:
        return False
    _HF_DOWNLOAD_ATTEMPTED.add(stockCode)
    try:
        from huggingface_hub import snapshot_download

        from dartlab.core.dataConfig import DATA_RELEASES, HF_REPO

        sectionsDirRel = DATA_RELEASES["sections"]["dir"]
        snapshot_download(
            repo_id=HF_REPO,
            repo_type="dataset",
            allow_patterns=[f"{sectionsDirRel}/{stockCode}/*.parquet"],
            local_dir=str(Path(_cfg.dataDir)),
        )
        return hasSectionsArtifact(stockCode)
    except Exception as exc:  # noqa: BLE001 — HF/네트워크 모든 에러 silent (fallback path 진행)
        _log.warning("sections artifact HF 다운로드 실패 (%s): %s — fallback path 진행", stockCode, exc)
        return False


def loadSectionsLong(
    stockCode: str,
    *,
    periods: list[str] | None = None,
    columns: list[str] | None = None,
) -> pl.DataFrame | None:
    """sections artifact long format read — period-sharded glob + columnar projection.

    MVP 단계: schema = (topic, blockType, blockOrder, segmentKey, period, content).
    polars ``scan_parquet([files]).select(columns)`` 로 select 안 한 컬럼은 페이지 fault 0.

    Args:
        stockCode: 종목코드.
        periods: 특정 period 만 read. None = 전체 period.
        columns: 특정 컬럼만 select. None = 전체.

    Returns:
        long format DataFrame 또는 None (artifact 부재).

    Raises:
        없음 — IO 에러는 warning + None.

    Example:
        >>> df = loadSectionsLong("005930", periods=["2025", "2024"])  # doctest: +SKIP
    """
    # artifact 부재 시 HF lazy 다운로드 (DARTLAB_NO_HF_DOWNLOAD 미설정 + 첫 시도).
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
            # 옛 schema (content_plain / content_table_struct 부재) 호환 — 실 schema 와
            # 교집합 만 select. polars ColumnNotFoundError 회귀 차단. 호출자는 결과 컬럼
            # 부재로 자체 fallback 판단 (예: loadSectionsWide 가 valueColumn None 검증).
            availableSchema = set(scan.collect_schema().names())
            wantedCols = [c for c in columns if c in availableSchema]
            if not wantedCols:
                _log.warning(
                    "sectionsLong (%s): 요청 columns %s 모두 schema (%s) 부재 — None",
                    stockCode,
                    columns,
                    sorted(availableSchema)[:10],
                )
                return None
            scan = scan.select(wantedCols)
        return scan.collect()
    except (OSError, pl.exceptions.ComputeError, pl.exceptions.ShapeError) as exc:
        _log.warning("sectionsLong load 실패 (%s): %s", stockCode, exc)
        return None


def loadSectionsWide(
    stockCode: str,
    *,
    periods: list[str] | None = None,
    valueColumn: str = "content",
) -> pl.DataFrame | None:
    """sections artifact wide format read — long → pivot(period).

    long format 을 read 후 pivot 으로 wide 양식 복원. ``valueColumn`` 으로 cell 값
    종류 선택 — ``"content"`` (mixed, viewer 전용), ``"content_plain"`` (분석/show),
    ``"content_table_struct"`` (finance 표 파서).

    plan snazzy-wibbling-origami PR-2 — ``Company.sections`` default 가 plain.
    ``c.sectionsRaw()`` 가 mixed.

    Args:
        stockCode: 종목코드.
        periods: 특정 period 만 wide 컬럼으로. None = 전체.
        valueColumn: pivot value 컬럼 — ``"content"`` / ``"content_plain"`` /
            ``"content_table_struct"``. default ``"content"`` (옛 호환).

    Returns:
        wide format DataFrame 또는 None.

    Raises:
        없음.

    Example:
        >>> df = loadSectionsWide("005930")  # doctest: +SKIP
        >>> df.columns  # doctest: +SKIP
        ['topic', 'blockType', 'blockOrder', 'segmentKey', '2025Q3', '2025', '2024', ...]
        >>> df_plain = loadSectionsWide("005930", valueColumn="content_plain")  # doctest: +SKIP
    """
    # 필요 컬럼만 read — columnar projection 으로 다른 content* + 거대 path variants 페이지
    # fault 0. wide pivot 후 cell 중복으로 메모리 폭주 → 정공법 = pivot 입력 long 자체를 좁힘.
    # 한 종목 long parquet ~54MB → 필수 컬럼만 ~10MB 로 5x 절감. 사용자 비전 "메모리 한 자리 MB".
    _MINIMAL_META = (
        "chapter",
        "topic",
        "blockType",
        "blockOrder",
        "textNodeType",
        "textLevel",
        "textPath",
        "textPathKey",
        "segmentKey",
        "source",
    )
    selectCols = list(_MINIMAL_META) + ["period", valueColumn]
    long = loadSectionsLong(stockCode, periods=periods, columns=selectCols)
    # 옛 schema 호환 — valueColumn (content_plain 등) 부재 시 content (mixed) 로 fallback +
    # stripTags 처리. 신 builder 가 빌드한 artifact 는 plain/table_struct 모두 보유 → 정상 path.
    # 옛 schema: loadSectionsLong 이 교집합 select → long 은 not None 이지만 valueColumn
    # 컬럼 부재. 그래서 두 조건 (None/empty OR valueColumn 부재) 모두 fallback 트리거.
    needsFallback = (long is None or long.is_empty()) or (valueColumn not in long.columns)
    if needsFallback:
        if valueColumn == "content":
            return None
        _log.info(
            "loadSectionsWide (%s): valueColumn '%s' 부재 (옛 schema) — content fallback + stripTags",
            stockCode,
            valueColumn,
        )
        fallbackCols = list(_MINIMAL_META) + ["period", "content"]
        long = loadSectionsLong(stockCode, periods=periods, columns=fallbackCols)
        if long is None or long.is_empty():
            return None
        if valueColumn == "content_plain":
            # polars native regex vectorize — Python map_elements 25k row × overhead 회피.
            # _HTML_TAG_RE / _MULTISPACE 동일 양식. 100x 빠름 (옛 2.4s → ~50ms 측정).
            long = long.with_columns(
                pl.col("content").str.replace_all(r"<[^>]+>", " ").str.replace_all(r"[ \t]+", " ").str.strip_chars()
            )
        elif valueColumn == "content_table_struct":
            # HTML <table>...</table> 만 추출. 표 없는 row 는 "". polars regex extract_all
            # → list.join. native vectorize.
            long = long.with_columns(pl.col("content").str.extract_all(r"(?i)<table[\s\S]*?</table>").list.join("\n\n"))
        # 호출자가 valueColumn 이름으로 pivot 하므로 content → valueColumn 으로 rename.
        long = long.rename({"content": valueColumn})
    if valueColumn not in long.columns:
        _log.warning("sectionsWide: valueColumn '%s' 부재 (사용 가능: %s)", valueColumn, long.columns)
        return None
    metaCols = [c for c in long.columns if c not in ("period", valueColumn)]
    try:
        return long.pivot(
            values=valueColumn,
            index=metaCols,
            on="period",
            aggregate_function="first",
        )
    except (pl.exceptions.ComputeError, pl.exceptions.ShapeError) as exc:
        _log.warning("sectionsWide pivot 실패 (%s): %s", stockCode, exc)
        return None
