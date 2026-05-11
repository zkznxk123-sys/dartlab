"""Scan.docsSections + buildDocsIndex 단위 테스트 — P3 (whimsical 흡수).

전 종목 raw parquet 일괄 lazy scan 사고 (STATUS_STACK_BUFFER_OVERRUN) 재발 방지.

fixture: tmp_path 의 합성 dart docs parquet 3 개 + scan/docsIndex.parquet 빌드.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def _fakeDocsParquet(path: Path, stockCode: str, corpName: str, sections: list[dict]) -> None:
    """합성 docs parquet 1 개 작성."""
    rows = []
    for i, sec in enumerate(sections):
        rows.append(
            {
                "stock_code": stockCode,
                "corp_name": corpName,
                "year": sec.get("year", 2024),
                "rcept_date": sec.get("rcept_date", "20240328"),
                "rcept_no": sec.get("rcept_no", "20240328000001"),
                "report_type": sec.get("report_type", "annual"),
                "section_order": i,
                "section_title": sec["section_title"],
                "section_url": sec.get("section_url", "https://dart.fss.or.kr/example"),
                "section_content": sec.get("section_content", ""),
            }
        )
    pl.DataFrame(rows).write_parquet(str(path))


@pytest.fixture
def docsFixture(tmp_path: Path) -> Path:
    """3 회사 × 다양한 섹션 fixture."""
    docsDir = tmp_path / "docs"
    docsDir.mkdir()
    _fakeDocsParquet(
        docsDir / "005930.parquet",
        "005930",
        "삼성전자",
        [
            {"section_title": "사업의 개요", "section_content": "반도체와 모바일이 주력 사업이다. " * 30},
            {"section_title": "신용평가에 관한 사항", "section_content": "Moody's Aa3, S&P A+ 등급. " * 20},
        ],
    )
    _fakeDocsParquet(
        docsDir / "000660.parquet",
        "000660",
        "SK하이닉스",
        [
            {"section_title": "신용평가에 관한 사항", "section_content": ""},  # 헤더-only
            {"section_title": "임원의 보수", "section_content": "임원 평균 보수 5억원. " * 10},
        ],
    )
    _fakeDocsParquet(
        docsDir / "035420.parquet",
        "035420",
        "NAVER",
        [
            {"section_title": "사업의 개요", "section_content": "검색 엔진과 광고가 주력. | 영역 | 매출 |"},
        ],
    )
    return docsDir


# ─── buildDocsIndex ───────────────────────────────────────────────────


def test_buildDocsIndex_minimal_fixture(docsFixture: Path, tmp_path: Path) -> None:
    """3 회사 docs 로 빌드 → schema · row 수 검증."""
    from dartlab.scan.builder.docsIndex import buildDocsIndex

    outPath = tmp_path / "docsIndex.parquet"
    result = buildDocsIndex(docsDir=docsFixture, outputPath=outPath, batchSize=2, sinceYear=2016)

    assert result == outPath
    assert outPath.exists()

    df = pl.read_parquet(str(outPath))
    assert df.height == 5  # 2 + 2 + 1
    assert set(df.columns) == {
        "stockCode",
        "corpName",
        "year",
        "reportType",
        "periodKey",
        "sectionOrder",
        "sectionTitle",
        "sectionUrl",
        "contentLength",
        "hasTable",
        "docId",
    }


def test_buildDocsIndex_no_content_column(docsFixture: Path, tmp_path: Path) -> None:
    """산출 parquet 에 section_content 가 들어가지 않음 (회귀 가드)."""
    from dartlab.scan.builder.docsIndex import buildDocsIndex

    outPath = tmp_path / "docsIndex.parquet"
    buildDocsIndex(docsDir=docsFixture, outputPath=outPath, sinceYear=2016)
    df = pl.read_parquet(str(outPath))
    assert "section_content" not in df.columns
    assert "content" not in df.columns


def test_buildDocsIndex_content_length_zero_for_placeholder(docsFixture: Path, tmp_path: Path) -> None:
    """헤더-only 섹션 (`section_content=""`) 은 contentLength=0."""
    from dartlab.scan.builder.docsIndex import buildDocsIndex

    outPath = tmp_path / "docsIndex.parquet"
    buildDocsIndex(docsDir=docsFixture, outputPath=outPath, sinceYear=2016)
    df = pl.read_parquet(str(outPath))
    placeholders = df.filter((pl.col("stockCode") == "000660") & (pl.col("sectionTitle") == "신용평가에 관한 사항"))
    assert placeholders.height == 1
    assert placeholders["contentLength"][0] == 0


def test_buildDocsIndex_has_table_detection(docsFixture: Path, tmp_path: Path) -> None:
    """본문에 `|` 포함 시 hasTable=True (markdown table 감지)."""
    from dartlab.scan.builder.docsIndex import buildDocsIndex

    outPath = tmp_path / "docsIndex.parquet"
    buildDocsIndex(docsDir=docsFixture, outputPath=outPath, sinceYear=2016)
    df = pl.read_parquet(str(outPath))
    naver = df.filter(pl.col("stockCode") == "035420")
    assert naver.height == 1
    assert naver["hasTable"][0] is True


def test_buildDocsIndex_empty_docs_dir(tmp_path: Path) -> None:
    """parquet 0 건 시 FileNotFoundError."""
    from dartlab.scan.builder.docsIndex import buildDocsIndex

    emptyDir = tmp_path / "empty"
    emptyDir.mkdir()
    with pytest.raises(FileNotFoundError, match="parquet"):
        buildDocsIndex(docsDir=emptyDir, outputPath=tmp_path / "out.parquet")


# ─── Scan.docsSections ───────────────────────────────────────────────


def test_docsSections_missing_index_clear_error(monkeypatch, tmp_path: Path) -> None:
    """인덱스 미빌드 시 FileNotFoundError + 안내 메시지."""
    from dartlab.scan import Scan

    monkeypatch.setattr("dartlab.core.dataLoader._dataDir", lambda subdir: str(tmp_path / subdir))
    scan = Scan()
    with pytest.raises(FileNotFoundError, match="prebuildData.py"):
        scan.docsSections(year=2024)


def test_docsSections_filter_by_section_title(docsFixture: Path, tmp_path: Path, monkeypatch) -> None:
    """sectionTitle="신용평가" 키워드 부분 매칭."""
    from dartlab.scan import Scan
    from dartlab.scan.builder.docsIndex import buildDocsIndex

    scanDir = tmp_path / "scan"
    scanDir.mkdir()
    indexPath = scanDir / "docsIndex.parquet"
    buildDocsIndex(docsDir=docsFixture, outputPath=indexPath, sinceYear=2016)

    monkeypatch.setattr("dartlab.core.dataLoader._dataDir", lambda subdir: str(tmp_path / subdir))

    scan = Scan()
    df = scan.docsSections(sectionTitle="신용평가")
    assert df.height == 2  # 005930 + 000660
    assert set(df["stockCode"].to_list()) == {"005930", "000660"}


def test_docsSections_only_with_content(docsFixture: Path, tmp_path: Path, monkeypatch) -> None:
    """onlyWithContent=True 는 contentLength=0 placeholder 제외."""
    from dartlab.scan import Scan
    from dartlab.scan.builder.docsIndex import buildDocsIndex

    scanDir = tmp_path / "scan"
    scanDir.mkdir()
    buildDocsIndex(docsDir=docsFixture, outputPath=scanDir / "docsIndex.parquet", sinceYear=2016)

    monkeypatch.setattr("dartlab.core.dataLoader._dataDir", lambda subdir: str(tmp_path / subdir))

    scan = Scan()
    df = scan.docsSections(sectionTitle="신용평가", onlyWithContent=True)
    assert df.height == 1  # 000660 의 placeholder 제외, 005930 만 남음
    assert df["stockCode"][0] == "005930"


def test_docsSections_limit_enforced(docsFixture: Path, tmp_path: Path, monkeypatch) -> None:
    """limit 기본값 100 → 5 row 모두 반환. limit=2 → 2 row."""
    from dartlab.scan import Scan
    from dartlab.scan.builder.docsIndex import buildDocsIndex

    scanDir = tmp_path / "scan"
    scanDir.mkdir()
    buildDocsIndex(docsDir=docsFixture, outputPath=scanDir / "docsIndex.parquet", sinceYear=2016)

    monkeypatch.setattr("dartlab.core.dataLoader._dataDir", lambda subdir: str(tmp_path / subdir))

    scan = Scan()
    assert scan.docsSections().height == 5  # default limit=100, 5 rows
    assert scan.docsSections(limit=2).height == 2  # 룰 8


def test_docsSections_market_us_not_implemented(tmp_path: Path, monkeypatch) -> None:
    """market="US" 는 P3.5 NotImplementedError."""
    from dartlab.scan import Scan

    monkeypatch.setattr("dartlab.core.dataLoader._dataDir", lambda subdir: str(tmp_path / subdir))
    scan = Scan()
    with pytest.raises(NotImplementedError, match="P3.5"):
        scan.docsSections(market="US")


def test_iterDocsSections_yields_dicts(docsFixture: Path, tmp_path: Path, monkeypatch) -> None:
    """iterDocsSections 가 dict yield (룰 10 pair)."""
    from dartlab.scan import Scan
    from dartlab.scan.builder.docsIndex import buildDocsIndex

    scanDir = tmp_path / "scan"
    scanDir.mkdir()
    buildDocsIndex(docsDir=docsFixture, outputPath=scanDir / "docsIndex.parquet", sinceYear=2016)

    monkeypatch.setattr("dartlab.core.dataLoader._dataDir", lambda subdir: str(tmp_path / subdir))

    scan = Scan()
    rows = list(scan.iterDocsSections(sectionTitle="신용평가"))
    assert len(rows) == 2
    assert all(isinstance(r, dict) for r in rows)
    assert all("stockCode" in r and "contentLength" in r for r in rows)
