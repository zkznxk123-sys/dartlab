"""OpenDART CORPCODE.xml → Parquet 발행 (gather SSOT 위임).

GitHub Actions(``kindlist.yml``)에서 실행되는 발행 래퍼. CORPCODE.xml ZIP 다운로드·
unzip·XML 파싱은 **중복 구현하지 않고** gather 엔진 SSOT(``loadCorpCodes``)를 그대로
호출한다 — 별도빌드 금지, 공동작업대(gather) 경유. ``loadCorpCodes`` 는 DART client
``getBytes`` 를 쓰므로 전송계층 일시장애 재시도도 함께 상속한다. 본 스크립트의 책임은 sink
플러밍(corp_code 정렬 + parquet 쓰기 + 변경 해시 + 업로드 SKIP 신호)뿐이다.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import polars as pl

from dartlab.gather.dart.client import DartClient
from dartlab.gather.dart.corpCode import loadCorpCodes

OUTPUT_DIR = Path("dist")
OUTPUT_FILE = OUTPUT_DIR / "dartList.parquet"


def fileHash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    print("OpenDART CORPCODE 목록 — gather SSOT(loadCorpCodes) 호출")
    client = DartClient()  # DART_API_KEY/DART_API_KEYS env 해소(미설정 시 명확한 ValueError)
    df = loadCorpCodes(client, refresh=True).sort("corp_code")  # 수집·파싱·재시도 = gather 단일 경로
    if df.height == 0:
        print("CORPCODE 수집 실패 — 빈 결과")
        sys.exit(1)
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
