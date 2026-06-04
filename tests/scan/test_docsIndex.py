"""Scan.docsSections + buildDocsIndex 단위 테스트 — P3 (whimsical 흡수).

전 종목 raw parquet 일괄 lazy scan 사고 (STATUS_STACK_BUFFER_OVERRUN) 재발 방지.

docs.parquet 농장 은퇴 후 buildDocsIndex 는 panel SSOT(``sectionTexts(code)``)에서 본문을
회수한다. fixture 는 panel dir 의 종목 parquet(코드 enum 용)과 ``sectionTexts`` monkeypatch
(본문 주입)로 합성 — 옛 docs.parquet 직접 작성 대체.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

pytestmark = pytest.mark.unit


# code → [(sectionLeaf, contentRaw), ...] — sectionTexts monkeypatch 가 반환할 합성 본문.
_FIXTURE_SECTIONS: dict[str, list[tuple[str, str]]] = {
    "005930": [
        ("사업의 개요", "반도체와 모바일이 주력 사업이다. " * 30),
        ("신용평가에 관한 사항", "Moody's Aa3, S&P A+ 등급. " * 20),
    ],
    "000660": [
        ("신용평가에 관한 사항", ""),  # 헤더-only → contentLength 0
        ("임원의 보수", "임원 평균 보수 5억원. " * 10),
    ],
    "035420": [
        ("사업의 개요", "검색 엔진과 광고가 주력. <TABLE><TR><TD>영역</TD><TD>매출</TD></TR></TABLE>"),
    ],
}


@pytest.fixture
def docsFixture(tmp_path: Path, monkeypatch) -> Path:
    """3 회사 panel fixture — 종목 parquet(코드 enum) + sectionTexts 본문 주입."""
    panelDir = tmp_path / "panel"
    panelDir.mkdir()
    for code in _FIXTURE_SECTIONS:
        # 코드 enum 용 placeholder — buildDocsIndex 는 glob 으로 종목만 발견, 본문은 sectionTexts.
        pl.DataFrame({"_": [1]}).write_parquet(str(panelDir / f"{code}.parquet"))

    def _fakeSectionTexts(code: str, *args, **kwargs):
        secs = _FIXTURE_SECTIONS.get(code)
        if not secs:
            return None
        rows = [
            {
                "period": "2024Q4",
                "sectionLeaf": title,
                "contentRaw": content,
                "blockOrder": i,
                "rceptNo": "20240328000001",
            }
            for i, (title, content) in enumerate(secs)
        ]
        return pl.DataFrame(rows)

    monkeypatch.setattr("dartlab.providers.dart.sections.sectionTexts", _fakeSectionTexts)
    return panelDir


# ─── buildDocsIndex ───────────────────────────────────────────────────


def test_buildDocsIndex_minimal_fixture(docsFixture: Path, tmp_path: Path) -> None:
    """3 회사 docs 로 빌드 → schema · row 수 검증."""
    from dartlab.scan.builders.kr.docsIndex import buildDocsIndex

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
    """산출 parquet 에 본문 컬럼이 들어가지 않음 (회귀 가드)."""
    from dartlab.scan.builders.kr.docsIndex import buildDocsIndex

    outPath = tmp_path / "docsIndex.parquet"
    buildDocsIndex(docsDir=docsFixture, outputPath=outPath, sinceYear=2016)
    df = pl.read_parquet(str(outPath))
    assert "section_content" not in df.columns
    assert "contentRaw" not in df.columns
    assert "content" not in df.columns


def test_buildDocsIndex_content_length_zero_for_placeholder(docsFixture: Path, tmp_path: Path) -> None:
    """헤더-only 섹션 (`contentRaw=""`) 은 contentLength=0."""
    from dartlab.scan.builders.kr.docsIndex import buildDocsIndex

    outPath = tmp_path / "docsIndex.parquet"
    buildDocsIndex(docsDir=docsFixture, outputPath=outPath, sinceYear=2016)
    df = pl.read_parquet(str(outPath))
    placeholders = df.filter((pl.col("stockCode") == "000660") & (pl.col("sectionTitle") == "신용평가에 관한 사항"))
    assert placeholders.height == 1
    assert placeholders["contentLength"][0] == 0


def test_buildDocsIndex_has_table_detection(docsFixture: Path, tmp_path: Path) -> None:
    """본문에 `<TABLE` 포함 시 hasTable=True (raw XML 테이블 감지)."""
    from dartlab.scan.builders.kr.docsIndex import buildDocsIndex

    outPath = tmp_path / "docsIndex.parquet"
    buildDocsIndex(docsDir=docsFixture, outputPath=outPath, sinceYear=2016)
    df = pl.read_parquet(str(outPath))
    naver = df.filter(pl.col("stockCode") == "035420")
    assert naver.height == 1
    assert naver["hasTable"][0] is True


def test_buildDocsIndex_empty_docs_dir(tmp_path: Path) -> None:
    """parquet 0 건 시 FileNotFoundError."""
    from dartlab.scan.builders.kr.docsIndex import buildDocsIndex

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
    from dartlab.scan.builders.kr.docsIndex import buildDocsIndex

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
    from dartlab.scan.builders.kr.docsIndex import buildDocsIndex

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
    from dartlab.scan.builders.kr.docsIndex import buildDocsIndex

    scanDir = tmp_path / "scan"
    scanDir.mkdir()
    buildDocsIndex(docsDir=docsFixture, outputPath=scanDir / "docsIndex.parquet", sinceYear=2016)

    monkeypatch.setattr("dartlab.core.dataLoader._dataDir", lambda subdir: str(tmp_path / subdir))

    scan = Scan()
    assert scan.docsSections().height == 5  # default limit=100, 5 rows
    assert scan.docsSections(limit=2).height == 2  # 룰 8


def test_docsSections_market_invalid(tmp_path: Path, monkeypatch) -> None:
    """market 미지원 값은 ValueError."""
    from dartlab.scan import Scan

    monkeypatch.setattr("dartlab.core.dataLoader._dataDir", lambda subdir: str(tmp_path / subdir))
    scan = Scan()
    with pytest.raises(ValueError, match="KR/US/JP"):
        scan.docsSections(market="ZZ")


def test_docsSections_market_us_routes_to_edgar(tmp_path: Path, monkeypatch) -> None:
    """market="US" → data/edgar/scan/docsIndex.parquet 경로 미빌드 시 안내 메시지."""
    from dartlab.scan import Scan

    monkeypatch.setattr("dartlab.core.dataLoader._getDataRoot", lambda: tmp_path)
    scan = Scan()
    with pytest.raises(FileNotFoundError, match="edgar"):
        scan.docsSections(market="US")


def test_docsSections_market_jp_routes_to_edinet(tmp_path: Path, monkeypatch) -> None:
    """market="JP" → data/edinet/scan/docsIndex.parquet 경로 미빌드 시 안내 메시지."""
    from dartlab.scan import Scan

    monkeypatch.setattr("dartlab.core.dataLoader._getDataRoot", lambda: tmp_path)
    scan = Scan()
    with pytest.raises(FileNotFoundError, match="edinet"):
        scan.docsSections(market="JP")


def test_iterDocsSections_yields_dicts(docsFixture: Path, tmp_path: Path, monkeypatch) -> None:
    """iterDocsSections 가 dict yield (룰 10 pair)."""
    from dartlab.scan import Scan
    from dartlab.scan.builders.kr.docsIndex import buildDocsIndex

    scanDir = tmp_path / "scan"
    scanDir.mkdir()
    buildDocsIndex(docsDir=docsFixture, outputPath=scanDir / "docsIndex.parquet", sinceYear=2016)

    monkeypatch.setattr("dartlab.core.dataLoader._dataDir", lambda subdir: str(tmp_path / subdir))

    scan = Scan()
    rows = list(scan.iterDocsSections(sectionTitle="신용평가"))
    assert len(rows) == 2
    assert all(isinstance(r, dict) for r in rows)
    assert all("stockCode" in r and "contentLength" in r for r in rows)
