"""OpenDART CORPCODE.xml → Parquet 변환.

GitHub Actions에서 독립 실행되는 스크립트.
패키지 import 없이 단독으로 동작한다.
DART_API_KEY 환경변수 필요.
"""

from __future__ import annotations

import hashlib
import io
import os
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import polars as pl
import requests

DART_API_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
OUTPUT_DIR = Path("dist")
OUTPUT_FILE = OUTPUT_DIR / "dartList.parquet"


def fetchDartList(apiKey: str) -> pl.DataFrame:
    """OpenDART corpCode.xml ZIP 다운로드 → DataFrame."""
    r = requests.get(DART_API_URL, params={"crtfc_key": apiKey}, timeout=60)
    if r.status_code != 200:
        print(f"OpenDART API 응답 실패: HTTP {r.status_code}")
        sys.exit(1)

    try:
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        xmlData = zf.read("CORPCODE.xml")
    except (zipfile.BadZipFile, KeyError) as e:
        print(f"corpCode.xml ZIP 손상: {e}")
        sys.exit(1)

    try:
        tree = ET.XML(xmlData)
    except ET.ParseError as e:
        print(f"corpCode.xml XML 파싱 실패: {e}")
        sys.exit(1)

    records = []
    for item in tree.findall("list"):
        record = {child.tag: (child.text or "") for child in item}
        records.append(record)

    if not records:
        print("corpCode.xml에 데이터가 없음")
        sys.exit(1)

    df = pl.DataFrame(records)
    # corp_code: 8자리, corp_name: 회사명, stock_code: 6자리(상장사만), modify_date
    df = df.sort("corp_code")
    return df


def fileHash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    apiKey = os.environ.get("DART_API_KEY", "")
    if not apiKey:
        print("DART_API_KEY 환경변수가 없음")
        sys.exit(1)

    print("OpenDART CORPCODE.xml 수집 시작")
    df = fetchDartList(apiKey)
    listed = df.filter(pl.col("stock_code").str.strip_chars() != "")
    print(f"{df.height}개 법인 수집 (상장: {listed.height})")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.write_parquet(str(OUTPUT_FILE))

    newHash = fileHash(OUTPUT_FILE)
    print(f"파일 생성 완료: {OUTPUT_FILE} (hash: {newHash[:12]})")

    existingHashFile = Path("dist/dartList_previous.sha256")
    if existingHashFile.exists():
        oldHash = existingHashFile.read_text().strip()
        if oldHash == newHash:
            print("변경 없음 — 업로드 스킵")
            Path("dist/SKIP_DARTLIST").touch()
        else:
            print("변경 감지 — 업로드 진행")
    else:
        print("이전 해시 없음 — 업로드 진행")

    existingHashFile.write_text(newHash)
