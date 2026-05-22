"""DART 보고서 원본 zip 파일 그대로 다운로드 — OpenDART API key 사용.

사용자 지시 (2026-05-21):
- "data에 오리지널폴더를 만들고 3개정도 종목 기간을 파서로 해서 파케로 하지말고
  진짜 오리지널 파일을 3개 모든기간 받아봐라"
- "api 키써서하라고"

endpoint: https://opendart.fss.or.kr/api/document.xml?crtfc_key=<key>&rcept_no=<rcpNo>
응답: zip — 안에 XBRL XML + HTML + image 원본. unzip 후 진짜 원본 구조 확인 가능.

대상: 005380 / 005930 / 035720 의 모든 rcept.
저장: data/original/{stock_code}/{rcept_no}.zip

실행: uv run python -X utf8 tests/_attempts/fetchOriginalDocs.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dartlab.providers.dart.openapi.client import DartClient  # noqa: E402

CODES: list[str] = []  # 빈 list = data/dart/docs/*.parquet 의 모든 종목
DELAY_SEC = 0.2  # API key 인증이라 rate limit 너그러움
OUT_DIR = REPO_ROOT / "data" / "dart" / "original" / "docs"


def fetchCode(code: str, client: DartClient) -> None:
    import polars as pl

    parquet = REPO_ROOT / "data" / "dart" / "docs" / f"{code}.parquet"
    if not parquet.exists():
        print(f"[skip] {code}: parquet missing")
        return
    df = pl.read_parquet(parquet)
    rcepts = sorted(df.select("rcept_no").unique().to_series().to_list(), reverse=True)
    print(f"[{code}] rcept_no: {len(rcepts)} 건")

    outCode = OUT_DIR / code
    outCode.mkdir(parents=True, exist_ok=True)

    saved = 0
    skipped = 0
    failed = 0
    for rcpNo in rcepts:
        outPath = outCode / f"{rcpNo}.zip"
        if outPath.exists() and outPath.stat().st_size > 1000:
            skipped += 1
            continue
        try:
            raw = client.getBytes("document.xml", {"rcept_no": rcpNo})
            if raw and len(raw) > 1000:
                outPath.write_bytes(raw)
                saved += 1
            else:
                failed += 1
                print(f"  [empty] {rcpNo} ({len(raw) if raw else 0} bytes)")
        except Exception as exc:
            failed += 1
            print(f"  [ERR] {rcpNo}: {exc!s}[:100]")
        time.sleep(DELAY_SEC)

    print(f"  [{code}] saved={saved} skipped={skipped} failed={failed}")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = DartClient()
    if CODES:
        codes = CODES
    else:
        # 모든 종목 (data/dart/docs/*.parquet)
        codes = sorted(p.stem for p in (REPO_ROOT / "data" / "dart" / "docs").glob("*.parquet"))
    print(f"target: {len(codes)} codes")
    for i, code in enumerate(codes, 1):
        print(f"\n[{i}/{len(codes)}] {code}")
        try:
            fetchCode(code, client)
        except Exception as exc:
            print(f"  [ERR] {code}: {exc!s}[:100]")
    print(f"\n=== DONE === saved at: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
