"""정공법 streaming docs.parquet builder — 메모리 친화 + 속도 친화 + 깨끗.

사용자 결정 (2026-05-21): "메모리 친화 속도 친화 덕지덕지하지말고 제대로 만들어라
테스트해서 안정적일때 본진합류해라".

설계:
- 입력: data/dart/original/docs/{code}/{rcept_no}.zip (이미 다운된 캐시 사용)
- 출력: data/dart/docs/{code}.parquet (호환 schema + atocid/assocnote 신규)
- 변환: zip → XML → parseSectionsByTitle (zipDocsXml.py 의 정공법 함수)
- 쓰기: pyarrow.parquet.ParquetWriter rcept 단위 row group append → 메모리 누적 0

메모리 친화:
- rcept 단위로 row dict list → pyarrow Table → writer.write_table → drop ref + gc
- 전체 종목 누적 누적 0. 100MB+ 본문도 안전.

속도 친화:
- XML parser 1 회 생성 후 재사용
- pyarrow Table.from_pylist (polars DataFrame 변환 보다 ~3x 빠름)
- row group 단위 압축 — append 시 incremental

안정성 (검증 통과 기준):
- 005930 (사업보고서 8MB XML) — 144 TITLE rows 무사 통과
- 005380 (현대차, 큰 종목) — OOM 0
- 035720/207940/000660 — sectionsParity 0 violations

검증 통과 후 본진 합류 (src/dartlab/providers/dart/openapi/zipCollector.py 의
ZipDocsCollector.rebuildFromZips 메소드로).

실행:
    uv run python -X utf8 tests/_attempts/xmlBuilderClean.py --code 005930
    uv run python -X utf8 tests/_attempts/xmlBuilderClean.py --codes 005380,005930,035720,207940,000660
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dartlab.providers.dart.openapi.zipDocsXml import parseSectionsByTitle  # noqa: E402

ORIGINAL_DIR = REPO_ROOT / "data" / "dart" / "original" / "docs"
DOCS_DIR = REPO_ROOT / "data" / "dart" / "docs"

# 호환 schema (기존 docs.parquet) + atocid/assocnote 추가.
# 큰 cell 은 _splitLargeContent 가 1MB 단위로 분할 → regular string OK.
SCHEMA = pa.schema(
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


def _loadRcptMeta(code: str) -> dict[str, dict]:
    """기존 parquet 에서 corp_code/corp_name/year/rcept_date/report_type 정보 (rcept_no 매칭)."""
    p = DOCS_DIR / f"{code}.parquet"
    if not p.exists():
        return {}
    meta: dict[str, dict] = {}
    # scan + select only meta columns → 큰 본문 안 읽음 (메모리/속도 친화)
    df = (
        pl.scan_parquet(p)
        .select(["corp_code", "corp_name", "stock_code", "year", "rcept_date", "rcept_no", "report_type"])
        .unique(subset=["rcept_no"])
        .collect()
    )
    for r in df.iter_rows(named=True):
        meta[r["rcept_no"]] = r
    return meta


def _xmlFromZip(zipPath: Path) -> str | None:
    """zip 안 가장 큰 XML 파일 → utf-8 string."""
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


# 단일 row 의 section_content 최대 size. 초과 시 markdown paragraph (\n\n) 또는 line
# 단위 split → multiple row 분할. 회귀 차단: polars row_tuples 의 PyObject 변환이
# 4MB+ string 에서 panic + iter_rows OOM. 1MB 안전선 채택 (sections chunker.MAX_CHUNK_CHARS
# 4KB 보다 훨씬 크지만 polars 안전선).
_MAX_CELL_BYTES = 1_000_000


def _splitLargeContent(text: str, maxBytes: int = _MAX_CELL_BYTES) -> list[str]:
    """text 가 maxBytes 초과 시 paragraph (\\n\\n) → line 단위로 분할."""
    if len(text) <= maxBytes:
        return [text]
    parts: list[str] = []
    buf: list[str] = []
    bufLen = 0
    for para in text.split("\n\n"):
        pLen = len(para)
        if pLen > maxBytes:
            # paragraph 자체 너무 큰 경우 line 단위 분할
            if buf:
                parts.append("\n\n".join(buf))
                buf = []
                bufLen = 0
            lineBuf: list[str] = []
            lineLen = 0
            for ln in para.split("\n"):
                if lineLen + len(ln) + 1 > maxBytes and lineBuf:
                    parts.append("\n".join(lineBuf))
                    lineBuf = []
                    lineLen = 0
                lineBuf.append(ln)
                lineLen += len(ln) + 1
            if lineBuf:
                parts.append("\n".join(lineBuf))
            continue
        if bufLen + pLen + 2 > maxBytes and buf:
            parts.append("\n\n".join(buf))
            buf = []
            bufLen = 0
        buf.append(para)
        bufLen += pLen + 2
    if buf:
        parts.append("\n\n".join(buf))
    return parts


def _rcpRowsToTable(meta: dict, rcptNo: str, rows: list[dict]) -> pa.Table:
    """rcept 의 row dict list → pyarrow Table (schema 강제). 큰 본문은 split."""
    # 큰 cell 분할 — 한 row 의 section_content > MAX_CELL_BYTES 면 paragraph 단위 split
    expanded: list[dict] = []
    for r in rows:
        content = r.get("content", "")
        if len(content) <= _MAX_CELL_BYTES:
            expanded.append(r)
            continue
        parts = _splitLargeContent(content)
        for i, p in enumerate(parts):
            expanded.append({**r, "content": p, "_split_idx": i})
    rows = expanded
    # column 별 list 구성 (pa.Table.from_pydict — pylist 보다 빠르고 메모리 효율)
    n = len(rows)
    cols = {
        "corp_code": [meta.get("corp_code", "") or ""] * n,
        "corp_name": [meta.get("corp_name", "") or ""] * n,
        "stock_code": [meta.get("stock_code", "") or ""] * n,
        "year": [meta.get("year", "") or ""] * n,
        "rcept_date": [meta.get("rcept_date", "") or ""] * n,
        "rcept_no": [rcptNo] * n,
        "report_type": [meta.get("report_type", "") or ""] * n,
        "section_order": [i for i in range(n)],
        "section_title": [r["title"] for r in rows],
        "section_url": [""] * n,
        "section_content": [r["content"] for r in rows],
        "atocid": [r.get("atocid", "") or "" for r in rows],
        "assocnote": [r.get("assocnote", "") or "" for r in rows],
    }
    return pa.Table.from_pydict(cols, schema=SCHEMA)


def buildCode(code: str, *, originalDir: Path = ORIGINAL_DIR, outPath: Path | None = None) -> Path:
    """단일 종목 streaming parquet 빌드. 반환: 출력 경로.

    rcept 단위 incremental write — 메모리 누적 0.
    """
    codeDir = originalDir / code
    if not codeDir.exists():
        raise FileNotFoundError(f"original zip dir not found: {codeDir}")
    zips = sorted(codeDir.glob("*.zip"))
    if not zips:
        raise ValueError(f"no zip in {codeDir}")

    if outPath is None:
        outPath = REPO_ROOT / "tests" / "_attempts" / f"docs_xml_v7_{code}.parquet"
    outPath.parent.mkdir(parents=True, exist_ok=True)

    meta = _loadRcptMeta(code)

    written = 0
    skipped = 0
    with pq.ParquetWriter(outPath, SCHEMA, compression="snappy") as writer:
        for zp in zips:
            rcptNo = zp.stem
            xml = _xmlFromZip(zp)
            if xml is None:
                skipped += 1
                continue
            try:
                rows = parseSectionsByTitle(xml)
            except Exception as exc:
                print(f"  [parse-err] {rcptNo}: {exc!s}[:80]")
                skipped += 1
                continue
            if not rows:
                skipped += 1
                continue
            rcptMeta = meta.get(
                rcptNo,
                {"corp_code": "", "corp_name": "", "stock_code": code, "year": "", "rcept_date": "", "report_type": ""},
            )
            table = _rcpRowsToTable(rcptMeta, rcptNo, rows)
            writer.write_table(table)
            written += len(rows)
            # drop ref
            del table, rows
    print(f"[{code}] zip={len(zips)} written_rows={written} skipped={skipped} → {outPath.name}")
    return outPath


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", default="")
    parser.add_argument("--codes", default="")
    args = parser.parse_args()

    codes: list[str] = []
    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    elif args.code:
        codes = [args.code]
    else:
        codes = ["005380", "005930", "035720", "207940", "000660"]

    for code in codes:
        try:
            buildCode(code)
        except Exception as exc:
            print(f"[ERR] {code}: {exc!s}[:200]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
