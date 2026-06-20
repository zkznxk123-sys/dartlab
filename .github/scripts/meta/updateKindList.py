"""KRX KIND 상장법인 목록 크롤링 → Parquet 생성.

GitHub Actions에서 독립 실행되는 스크립트.
패키지 import 없이 단독으로 동작한다.
"""

from __future__ import annotations

import hashlib
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

import polars as pl
import requests

KIND_URL = "https://kind.krx.co.kr/corpgeneral/corpList.do"
KIND_DATA = {
    "method": "download",
    "searchType": "13",
    "fiscalYearEnd": "all",
    "location": "all",
}
# KRX KIND 는 기본 python-requests UA 에 드물게 비-테이블 오류 페이지를 반환한다(WAF/혼잡). 브라우저
# UA + 짧은 재시도로 일시 응답을 흡수 — 2026-06 cron 단발 실패(테이블 미발견)가 재시도 0 갭이었다.
KIND_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
_RETRIES = 3
_BACKOFF_SEC = 2.0

OUTPUT_DIR = Path("dist")
OUTPUT_FILE = OUTPUT_DIR / "corpList.parquet"


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._inTable = False
        self._inTr = False
        self._inCell = False
        self._rows: list[list[str]] = []
        self._row: list[str] = []
        self._cell = ""

    def handle_starttag(self, tag: str, attrs):
        if tag == "table":
            self._inTable = True
        elif tag == "tr" and self._inTable:
            self._inTr = True
            self._row = []
        elif tag in ("td", "th") and self._inTr:
            self._inCell = True
            self._cell = ""

    def handle_endtag(self, tag: str):
        if tag in ("td", "th") and self._inCell:
            self._inCell = False
            self._row.append(self._cell.strip())
        elif tag == "tr" and self._inTr:
            self._inTr = False
            if self._row:
                self._rows.append(self._row)
        elif tag == "table":
            self._inTable = False

    def handle_data(self, data: str):
        if self._inCell:
            self._cell += data


def _fetchKindRows() -> list[list[str]]:
    """KRX KIND 다운로드 → 표 행. 일시 장애(비-테이블 응답·네트워크)는 짧게 재시도 후 소진 시 종료."""
    lastErr = "알 수 없는 오류"
    for attempt in range(_RETRIES):
        try:
            r = requests.post(KIND_URL, data=KIND_DATA, headers=KIND_HEADERS, timeout=30)
            html = r.content.decode("euc-kr", errors="replace")
            parser = _TableParser()
            parser.feed(html)
            if len(parser._rows) >= 2:
                return parser._rows
            lastErr = "KIND 응답에서 테이블을 찾을 수 없음"
        except requests.RequestException as exc:
            lastErr = f"KIND 요청 실패: {type(exc).__name__}"
        if attempt < _RETRIES - 1:
            print(f"{lastErr} — 재시도 {attempt + 1}/{_RETRIES - 1}")
            time.sleep(_BACKOFF_SEC * (attempt + 1))
    print(lastErr)
    sys.exit(1)


def fetchKind() -> pl.DataFrame:
    rows = _fetchKindRows()

    header = rows[0]
    data = rows[1:]
    records = [dict(zip(header, r)) for r in data if len(r) == len(header)]
    df = pl.DataFrame(records)

    if "종목코드" not in df.columns:
        print("종목코드 컬럼이 없음")
        sys.exit(1)

    df = df.with_columns(pl.col("종목코드").cast(pl.Utf8).str.zfill(6))
    df = df.filter(pl.col("종목코드").str.contains(r"^[0-9A-Z]{6}$"))
    df = df.filter(~pl.col("회사명").str.contains(r"스팩|리츠"))
    df = df.unique(subset=["종목코드"]).sort("종목코드")
    return df


def fileHash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    print("KRX KIND 상장법인 목록 크롤링 시작")
    df = fetchKind()
    print(f"{df.height}개 종목 수집 완료")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.write_parquet(str(OUTPUT_FILE))

    newHash = fileHash(OUTPUT_FILE)
    print(f"파일 생성 완료: {OUTPUT_FILE} (hash: {newHash[:12]})")

    existingHashFile = Path("dist/previous.sha256")
    if existingHashFile.exists():
        oldHash = existingHashFile.read_text().strip()
        if oldHash == newHash:
            print("변경 없음 — 업로드 스킵")
            Path("dist/SKIP").touch()
        else:
            print("변경 감지 — 업로드 진행")
    else:
        print("이전 해시 없음 — 업로드 진행")

    existingHashFile.write_text(newHash)
