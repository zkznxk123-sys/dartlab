"""ZIP(document.xml) 기반 DART 공시문서 수집기.

collector.py(HTML 크롤링)보다 빠르고 품질 동등.
실험 092_zipDocsCompare에서 검증 완료.

사용법::

    from dartlab.providers.dart.openapi.zipCollector import ZipDocsCollector

    collector = ZipDocsCollector("005930")
    collector.collect(quarters=8)
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
from bs4 import BeautifulSoup
from lxml import etree

import dartlab.config as _cfg
from dartlab.core.dataConfig import DATA_RELEASES
from dartlab.providers.dart.openapi.client import DartClient
from dartlab.providers.dart.openapi.corpCode import findCorpCode, loadCorpCodes
from dartlab.providers.dart.openapi.disclosure import listFilings
from dartlab.providers.dart.openapi.zipDocsXml import (
    MAX_CELL_BYTES,
    parseSectionsByTitle,
    splitLargeContent,
)

# DART 원본 zip 디렉토리. CLAUDE.md "DART 원본 zip 비공개" — 로컬 임시 보관 전용.
_ORIGINAL_DOCS_DIR_NAME = "dart/original/docs"

# rebuildFromZips streaming parquet schema — regular string (large_string 회피).
# cell split (MAX_CELL_BYTES=1MB) 으로 pa.string() 32-bit offset 안전.
_REBUILD_SCHEMA = pa.schema(
    [
        ("corp_code", pa.string()),
        ("corp_name", pa.string()),
        ("stock_code", pa.string()),
        ("year", pa.string()),
        ("rcept_date", pa.string()),
        ("rcept_no", pa.string()),
        ("report_type", pa.string()),
        ("section_order", pa.int64()),
        ("section_title", pa.string()),
        ("section_url", pa.string()),
        ("section_content", pa.string()),
        ("atocid", pa.string()),
        ("assocnote", pa.string()),
    ]
)

# ── 정규식 (모듈 레벨 컴파일) ──

_RE_WHITESPACE = re.compile(r"\s+")
_RE_MULTI_NEWLINE = re.compile(r"\n{3,}")

# zip XML 의 DOCUMENT-NAME ACODE → report_type 매핑. DART 공식 보고서 코드:
#   11011: 사업보고서, 11012: 반기보고서, 11013: 1분기보고서, 11014: 3분기보고서.
_RE_DOC_NAME = re.compile(r'<DOCUMENT-NAME\s+ACODE="(\d+)"[^>]*>([^<]+)</DOCUMENT-NAME>')
# rcept_date YYYYMMDD 의 month → reportKind 휴리스틱 (사업보고서 = 전년도 사업연도):
#   03~04: annual (전년도), 05: Q1, 08: semi, 11: Q3.
# ACODE → (name, fiscal end month). 사업기간 종료 month — report_type "(YYYY.MM)" 의 MM.
_REPORT_ACODE_MAP = {
    "11011": ("사업보고서", "12"),
    "11012": ("반기보고서", "06"),
    "11013": ("분기보고서", "03"),
    "11014": ("분기보고서", "09"),
}


def _extractMetaFromXml(xml: str, rcptNo: str) -> tuple[str, str, str]:
    """zip XML 의 첫 2KB 에서 (year, rcept_date, report_type) 추출.

    rcept_date = rcept_no 앞 8자리 (YYYYMMDD). year = 사업연도 (annual 인 경우 rcept
    year - 1, 그 외 rcept year). report_type = "{kind} ({year}.{fiscalMonth})" —
    selectReport 의 _REPORT_KIND_MAP regex (예: ``분기보고서.*\\d{4}\\.03`` for Q1)
    호환. fiscalMonth = ACODE 별 사업기간 종료 month (사업 12 / 반기 06 / Q1 03 / Q3 09).
    """
    rcptDate = rcptNo[:8] if len(rcptNo) >= 8 and rcptNo[:8].isdigit() else ""
    rcptYear = rcptDate[:4] if rcptDate else ""

    head = xml[:2000]
    m = _RE_DOC_NAME.search(head)
    acode = m.group(1) if m else ""
    kindFiscal = _REPORT_ACODE_MAP.get(acode)
    if not kindFiscal:
        return rcptYear, rcptDate, ""
    kind, fiscalMonth = kindFiscal

    # 사업연도 = annual (사업보고서) 인 경우 rcept year - 1 (12월 결산), 그 외 rcept year
    if kind == "사업보고서" and rcptYear:
        try:
            year = str(int(rcptYear) - 1)
        except ValueError:
            year = rcptYear
    else:
        year = rcptYear

    reportType = f"{kind} ({year}.{fiscalMonth})" if year else kind
    return year, rcptDate, reportType


# ── XML → 텍스트 변환 ──


def _tableToMarkdown(table) -> str:
    """HTML table → markdown."""
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells: list[str] = []
        for cell in tr.find_all(["td", "th", "te"]):
            colspan = int(cell.get("colspan", 1))
            text = cell.get_text(strip=True)
            text = _RE_WHITESPACE.sub(" ", text)
            text = text.replace("|", "｜")
            cells.append(text)
            cells.extend("" for _ in range(colspan - 1))
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    maxCols = max(len(row) for row in rows)
    for row in rows:
        while len(row) < maxCols:
            row.append("")
    lines = [
        "| " + " | ".join(rows[0]) + " |",
        "| " + " | ".join(["---"] * maxCols) + " |",
    ]
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _xmlToText(xmlStr: str) -> str:
    """DART XML → 텍스트. table-group 경계 분리 + SPAN bold 줄바꿈."""
    soup = BeautifulSoup(xmlStr, "lxml")

    for tag in soup(["script", "style", "meta", "link", "header", "footer", "nav"]):
        tag.decompose()

    for tg in soup.find_all("table-group"):
        tgTitle = tg.find("title", recursive=False)
        if tgTitle:
            titleText = tgTitle.get_text(strip=True)
            if titleText:
                newP = soup.new_tag("p")
                newP.string = titleText
                tg.insert_before(newP)
            tgTitle.decompose()
        tg.unwrap()

    for span in soup.find_all("span"):
        usermark = span.get("usermark", "")
        if "B" in usermark.split() and span.string:
            span.insert_after("\n")

    for pgbrk in soup.find_all("pgbrk"):
        pgbrk.replace_with("\n")

    for table in soup.find_all("table"):
        md = _tableToMarkdown(table)
        if md:
            table.replace_with(BeautifulSoup(f"\n\n{md}\n\n", "lxml"))
        else:
            table.decompose()

    for br in soup.find_all("br"):
        br.replace_with("\n")

    for p in soup.find_all(["p", "div", "li"]):
        p.insert_after("\n")

    text = soup.get_text()
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    text = _RE_MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def _getFullContent(element) -> str:
    """SECTION-1 전체 content (하위 section 포함 + 자기 title 포함)."""
    titleEl = element.find("title")
    titleText = ""
    if titleEl is not None:
        titleText = etree.tostring(titleEl, method="text", encoding="unicode").strip()
        titleText = _RE_WHITESPACE.sub(" ", titleText)

    xmlStr = etree.tostring(element, encoding="unicode")
    tag = element.tag
    xmlStr = re.sub(rf"^<{re.escape(tag)}[^>]*>", "", xmlStr, count=1)
    xmlStr = re.sub(rf"</{re.escape(tag)}>$", "", xmlStr)
    xmlStr = re.sub(r"<title[^>]*>.*?</title>", "", xmlStr, flags=re.DOTALL | re.IGNORECASE, count=1)
    body = _xmlToText(xmlStr)
    if titleText and body:
        return f"{titleText}\n{body}"
    return body or titleText


def _getOwnContent(element) -> str:
    """SECTION-2 자신만 (하위 section 제외, TITLE 제거)."""
    xmlStr = etree.tostring(element, encoding="unicode")
    tag = element.tag
    xmlStr = re.sub(rf"^<{re.escape(tag)}[^>]*>", "", xmlStr, count=1)
    xmlStr = re.sub(rf"</{re.escape(tag)}>$", "", xmlStr)
    xmlStr = re.sub(r"<title[^>]*>.*?</title>", "", xmlStr, flags=re.DOTALL | re.IGNORECASE, count=1)
    for d in range(1, 4):
        xmlStr = re.sub(
            rf"<section-{d}[^>]*>.*?</section-{d}>",
            "",
            xmlStr,
            flags=re.DOTALL | re.IGNORECASE,
        )
    return _xmlToText(xmlStr)


def _parseSections(xmlContent: str) -> list[dict]:
    """DART XML → 섹션 목록 (정공법 — ``<TITLE>`` hierarchy 직접 사용).

    기존 SECTION-1/SECTION-2 통째 본문 추출은 chapter 본문이 4MB 통째 cell 에
    들어가 sections layer 가 regex 로 sub-section 분리 → 추론 오류 다발. 본
    구현은 ``zipDocsXml.parseSectionsByTitle`` 로 위임 — 각 ``<TITLE>`` 별로 row
    를 분리 + AASSOCNOTE/ATOCID hierarchy 보존 + ``<SPAN USERMARK B>`` 가/나/다
    marker 를 markdown ``## prefix`` 로 변환.

    회귀 보장: 기존 schema 호환 (``order``/``title``/``content``) + 추가 컬럼
    ``atocid``/``assocnote`` (sections layer 가 활용 가능).
    """
    from dartlab.providers.dart.openapi.zipDocsXml import parseSectionsByTitle

    return parseSectionsByTitle(xmlContent)


def _xmlFromZip(zipPath: Path) -> str | None:
    """로컬 zip 의 가장 큰 XML 을 utf-8 string 으로 (rebuildFromZips offline 경로)."""
    try:
        with zipfile.ZipFile(zipPath) as zf:
            names = zf.namelist()
            if not names:
                return None
            largest = max(names, key=lambda n: zf.getinfo(n).file_size)
            raw = zf.read(largest)
    except zipfile.BadZipFile:
        return None
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def _rcpRowsToTable(
    meta: dict,
    stockCode: str,
    corpCode: str,
    corpName: str,
    rcptNo: str,
    rows: list[dict],
) -> pa.Table:
    """rcept 의 row dict list → pyarrow Table (schema 강제). 큰 본문은 split.

    section_content > MAX_CELL_BYTES row 는 markdown paragraph 단위 split → multiple
    row (같은 atocid/assocnote 유지, section_order 는 split index 만큼 증가).
    """
    expanded: list[dict] = []
    for r in rows:
        content = r.get("content", "") or ""
        if len(content) <= MAX_CELL_BYTES:
            expanded.append(r)
            continue
        for p in splitLargeContent(content):
            expanded.append({**r, "content": p})

    n = len(expanded)
    cols = {
        "corp_code": [meta.get("corp_code", "") or corpCode] * n,
        "corp_name": [meta.get("corp_name", "") or corpName] * n,
        "stock_code": [meta.get("stock_code", "") or stockCode] * n,
        "year": [meta.get("year", "") or ""] * n,
        "rcept_date": [meta.get("rcept_date", "") or ""] * n,
        "rcept_no": [rcptNo] * n,
        "report_type": [meta.get("report_type", "") or ""] * n,
        "section_order": list(range(n)),
        "section_title": [r["title"] for r in expanded],
        "section_url": [""] * n,
        "section_content": [r["content"] for r in expanded],
        "atocid": [r.get("atocid", "") or "" for r in expanded],
        "assocnote": [r.get("assocnote", "") or "" for r in expanded],
    }
    return pa.Table.from_pydict(cols, schema=_REBUILD_SCHEMA)


def _collectOneZip(client: DartClient, rceptNo: str) -> list[dict] | None:
    """단일 rcept_no ZIP → 섹션 추출."""
    try:
        raw = client.getBytes("document.xml", {"rcept_no": rceptNo})
    except (RuntimeError, OSError):
        return None

    if raw is None:
        return None

    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        return None
    names = zf.namelist()
    if not names:
        return None

    largest = max(names, key=lambda n: zf.getinfo(n).file_size)
    content = zf.read(largest)

    xmlContent = None
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            xmlContent = content.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if xmlContent is None:
        xmlContent = content.decode("utf-8", errors="replace")

    return _parseSections(xmlContent)


# ── 수집기 ──


def _docsDataDir() -> Path:
    """docs parquet 저장 디렉토리."""
    root = Path(_cfg.dataDir)
    d = root / DATA_RELEASES["docs"]["dir"]
    d.mkdir(parents=True, exist_ok=True)
    return d


class ZipDocsCollector:
    """ZIP(document.xml) 기반 DART 공시문서 수집기."""

    def __init__(
        self,
        stockCode: str,
        *,
        client: DartClient | None = None,
        corpCode: str | None = None,
        corpName: str | None = None,
    ):
        self.stockCode = stockCode
        self._client = client or DartClient()

        if corpCode and corpName:
            self._corpCode = corpCode
            self._corpName = corpName
        else:
            corpCodes = loadCorpCodes(self._client)
            match = corpCodes.filter(pl.col("stock_code") == stockCode)
            if match.height > 0:
                self._corpCode = match["corp_code"][0]
                self._corpName = match["corp_name"][0]
            else:
                self._corpCode = findCorpCode(self._client, stockCode) or ""
                self._corpName = stockCode

        self._dataDir = _docsDataDir()
        self._parquetPath = self._dataDir / f"{stockCode}.parquet"
        self._existingReports: set[str] = set()
        self._loadExisting()

    def _loadExisting(self) -> None:
        """기존 parquet에서 이미 수집된 rcept_no 세트 로드."""
        if self._parquetPath.exists():
            try:
                df = pl.scan_parquet(self._parquetPath).select("rcept_no").collect(engine="streaming")
                self._existingReports = set(df["rcept_no"].unique().to_list())
            except (pl.exceptions.ComputeError, OSError):
                self._existingReports = set()

    def collect(
        self,
        *,
        includeQuarterly: bool = True,
        showProgress: bool = True,
        onProgress=None,
    ) -> int:
        """2016Q1부터 전체 정기보고서 수집 → parquet 저장. 반환: 저장된 섹션 수.

        Args:
            includeQuarterly: 인자.
            showProgress: 인자.
            onProgress: 인자.

        Raises:
            없음.

        Example:
            >>> collect(...)

        Returns:
            int — 수집 건수.

        SeeAlso:
            - ``DocsCollector`` (collector.py) — HTML 기반 대안.
            - ``_collectOneZip`` — 단일 ZIP 처리 backend.

        Requires:
            - bs4
            - dartlab
            - io
            - lxml
            - polars

        Capabilities:
            - DART document.xml ZIP 다운로드 + XML → markdown/text + 섹션 분할. collector.py
              (HTML) 보다 빠르고 품질 동등.

        Guide:
            - 운영자 수집 파이프라인 — 사용자 API 직접 호출 X.

        AIContext:
            internal ZIP collector — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - DART_API_KEY 일일 한도 초과 시 실패.
                - ZIP 손상 (BadZipFile) → 빈 결과.
            OutputSchema:
                - list[dict] / int / Path — 함수별.
            Prerequisites:
                - 인터넷 + DART_API_KEY + rceptNo.
            Freshness:
                - DART OpenAPI 실시간.
            Dataflow:
                - rceptNo → document.xml ZIP → XML 파싱 → markdown/text → 본 결과.
            TargetMarkets:
                - KR (DART) docs ZIP.
        """
        from dartlab.core.messaging import emit

        # 공시 목록 조회 (K-IFRS 전면 도입 이후)
        filings = listFilings(
            self._client,
            self.stockCode,
            start="20160101",
            filingType="A",
            fetchAll=True,
        )
        if filings.height == 0:
            return 0

        # 정기보고서만 + 분기보고서 선택
        reportFilter = r"사업보고서|반기보고서"
        if includeQuarterly:
            reportFilter += r"|분기보고서"
        filings = filings.filter(pl.col("report_nm").str.contains(reportFilter))
        filings = filings.sort("rcept_dt", descending=True)

        # 이미 수집된 것 제외
        newFilings = filings.filter(~pl.col("rcept_no").is_in(list(self._existingReports)))
        if newFilings.height == 0:
            return 0

        # ZIP 수집
        from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

        from dartlab.core.logger import getConsole

        allSections: list[dict] = []
        failCount = 0
        total = newFilings.height

        _progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=getConsole(),
            disable=not showProgress,
        )
        _task = _progress.add_task(f"docs 수집 | {self._corpName}", total=total)
        with _progress:
            for rowIdx, row in enumerate(newFilings.iter_rows(named=True)):
                rceptNo = row["rcept_no"]
                rceptDt = row["rcept_dt"]
                reportNm = row["report_nm"]

                # 결산연도: report_nm에서 추출 (예: "사업보고서 (2025.12)" → "2025")
                ym = re.search(r"\((\d{4})\.\d{2}\)", reportNm)
                year = ym.group(1) if ym else rceptDt[:4]

                _progress.update(_task, description=f"docs | {self._corpName} | {reportNm}")
                if onProgress:
                    onProgress(f"docs {rowIdx + 1}/{total} {reportNm}")

                sections = _collectOneZip(self._client, rceptNo)
                if sections is None:
                    failCount += 1
                    _progress.advance(_task)
                    continue

                for s in sections:
                    allSections.append(
                        {
                            "corp_code": self._corpCode,
                            "corp_name": self._corpName,
                            "stock_code": self.stockCode,
                            "year": year,
                            "rcept_date": rceptDt,
                            "rcept_no": rceptNo,
                            "report_type": reportNm,
                            "section_order": s["order"],
                            "section_title": s["title"],
                            "section_url": "",
                            "section_content": s["content"],
                            "atocid": s.get("atocid", ""),
                            "assocnote": s.get("assocnote", ""),
                        }
                    )
                _progress.advance(_task)

        if not allSections:
            return 0

        # parquet 저장 (기존 파일 있으면 누적, Phase A — sort + row_group_size 적용)
        from dartlab.providers.dart.openapi.saver import writeParquetSorted

        newDf = pl.DataFrame(allSections)

        if self._parquetPath.exists():
            existingDf = pl.read_parquet(self._parquetPath)
            combinedDf = pl.concat([existingDf, newDf], how="diagonal_relaxed")
        else:
            combinedDf = newDf

        writeParquetSorted(combinedDf, self._parquetPath)

        self._loadExisting()

        savedCount = len(allSections)
        if showProgress:
            emit(
                "collect:done",
                label="docs",
                sizeStr=f"{savedCount}섹션, {total - failCount}/{total}건",
            )
        return savedCount

    def rebuildFromZips(self, *, srcDir: Path | None = None, outPath: Path | None = None) -> int:
        """``data/dart/original/docs/{code}/*.zip`` 로컬 zip 만으로 parquet 풀 재빌드.

        API 호출 0. streaming pyarrow ParquetWriter + cell split (``MAX_CELL_BYTES``) +
        regular string schema. zip = SSOT, parquet = derived 원칙 — zip 만 있으면
        언제든 복원. 본 method 는 ``ZipDocsCollector`` 의 offline primary 빌더 (안정성
        검증 우선).

        회귀 차단:
        - section_content > 1MB row 는 paragraph (\\n\\n) 단위 split → multiple row
          (같은 ``atocid``/``assocnote`` 유지, section_order 증가). polars iter_rows
          PyObject panic 차단.
        - row group 단위 incremental write (rcept 단위) → 메모리 누적 0.
        - ``meta_corp_code``/``corp_name``/``year``/``rcept_date``/``report_type`` 정보는
          기존 parquet 의 meta 만 scan + select (큰 본문 안 읽음).

        Args:
            srcDir: 종목 zip 디렉토리. 기본 ``data/dart/original/docs/{code}/``.
            outPath: 출력 parquet 경로. 기본 ``data/dart/docs/{code}.parquet``.

        Returns:
            int — 작성된 row 수.

        Raises:
            FileNotFoundError: srcDir 에 zip 0 개.

        Example:
            >>> collector.rebuildFromZips()  # doctest: +SKIP
        """
        root = Path(_cfg.dataDir)
        codeDir = srcDir or (root / _ORIGINAL_DOCS_DIR_NAME / self.stockCode)
        if not codeDir.exists():
            raise FileNotFoundError(f"original zip dir not found: {codeDir}")
        zips = sorted(codeDir.glob("*.zip"))
        if not zips:
            raise FileNotFoundError(f"no zip in {codeDir}")

        outPath = outPath or self._parquetPath
        outPath.parent.mkdir(parents=True, exist_ok=True)

        # 기존 parquet 의 meta 정보만 (큰 본문 안 읽음)
        rcptMeta: dict[str, dict] = {}
        if self._parquetPath.exists():
            try:
                metaDf = (
                    pl.scan_parquet(self._parquetPath)
                    .select(
                        [
                            "corp_code",
                            "corp_name",
                            "stock_code",
                            "year",
                            "rcept_date",
                            "rcept_no",
                            "report_type",
                        ]
                    )
                    .unique(subset=["rcept_no"])
                    .collect()
                )
                for r in metaDf.iter_rows(named=True):
                    rcptMeta[r["rcept_no"]] = r
            except (pl.exceptions.ComputeError, OSError):
                pass

        written = 0
        skipped = 0
        # version="1.0" — VSCode parquet viewer / DuckDB 등 1.0 호환 reader 대응
        # (기본 2.6 은 일부 third-party viewer 가 못 읽음). pyarrow / polars / pandas
        # 는 1.0 / 2.x 모두 정상 read.
        with pq.ParquetWriter(outPath, _REBUILD_SCHEMA, compression="snappy", version="1.0") as writer:
            for zp in zips:
                rcptNo = zp.stem
                xml = _xmlFromZip(zp)
                if xml is None:
                    skipped += 1
                    continue
                try:
                    rows = parseSectionsByTitle(xml)
                except (ValueError, AttributeError, KeyError):
                    # XML 형식 오류 / 누락 element — 다음 zip 진행.
                    skipped += 1
                    continue
                if not rows:
                    skipped += 1
                    continue
                # zip XML 의 <DOCUMENT-NAME ACODE> + rcept_no 앞 8자리 = primary source
                # (year / rcept_date / report_type). 옛 parquet 의 meta 는 corp_code/
                # corp_name 만 fallback — 직전 rebuild 의 잘못된 report_type 이 살아남
                # 아 새 빌드를 오염시키지 않도록.
                xmlYear, xmlDate, xmlReportType = _extractMetaFromXml(xml, rcptNo)
                metaFromParquet = rcptMeta.get(rcptNo, {})
                meta = {
                    "corp_code": metaFromParquet.get("corp_code") or self._corpCode,
                    "corp_name": metaFromParquet.get("corp_name") or self._corpName,
                    "stock_code": metaFromParquet.get("stock_code") or self.stockCode,
                    "year": xmlYear or metaFromParquet.get("year", ""),
                    "rcept_date": xmlDate or metaFromParquet.get("rcept_date", ""),
                    "report_type": xmlReportType or metaFromParquet.get("report_type", ""),
                }
                table = _rcpRowsToTable(meta, self.stockCode, self._corpCode, self._corpName, rcptNo, rows)
                writer.write_table(table)
                written += table.num_rows
                del table, rows
        return written
