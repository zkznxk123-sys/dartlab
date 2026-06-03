"""sync stage online 1패스 panel 빌더 — DART API → 메모리 zip → 14-col parquet (디스크 zip 0).

plan snazzy-wibbling-origami P6. ``buildPanel.py``(로컬 zip 트랙 A)의 online 쌍둥이(트랙 B):

    docs.parquet rcept → streamZipBytes(providers, 메모리) → buildPanelFromStream(providers.panel.build)
        → dist/changed_panel.txt → uploadData(SYNC_CATEGORY=panel)

R1(gather↛providers): 본 entry 는 ``.github/scripts``(dartlab 패키지 밖, import 가드 비대상)라
providers fetch + gather build 를 한 프로세스에서 조합한다 (``syncRecent.py`` 동형 패턴 — 정공,
이관 아님). online 은 **refScan 절대 안 함** — HF seed ``panelXbrlRef`` 를 refDf 로 주입(zip 부재
로 자동 scanRefBaseline 불가). 산출물은 buildPanel(A)과 바이트 동형(같은 build core).

사용법:
    python .github/scripts/sync/onlinePanel.py --changed       # dist/changed_docs.txt 종목
    python .github/scripts/sync/onlinePanel.py --codes 005930,000660

환경변수:
    DARTLAB_DATA_DIR: 데이터 경로 (기본 ./data)
    DART_API_KEYS: OpenDART 키 (쉼표 구분, 멀티키 로테이션 + 020 cooldown)
    PANEL_WORKERS: streamZipBytes fetch ThreadPool workers (기본 4 — 발열/메모리 가드, 8 아님)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _resolveChangedCodes() -> list[str]:
    """dist/changed_docs.txt 또는 dist/changed.txt 에서 변경된 docs 종목코드 추출."""
    for p in (Path("dist/changed_docs.txt"), Path("dist/changed.txt")):
        if not p.exists():
            continue
        names = [n.strip() for n in p.read_text(encoding="utf-8").splitlines() if n.strip()]
        codes = [Path(n).stem for n in names]
        return [c for c in codes if c.isdigit() and len(c) == 6]
    return []


def _writeChangedPanel(codes: list[str], dataDir: str) -> None:
    """uploadData(SYNC_CATEGORY=panel) 증분 업로드용 changed list 작성.

    종목별 period 파일 상대경로 ``{code}/{period}.parquet`` (data/dart/panel 기준 상대).
    (_index/_label 은 PRD jazzy-napping-seal 에서 폐기 — panel artifact 는 period shard 단일.)
    """
    panelBase = Path(dataDir) / "dart" / "panel"
    lines: list[str] = []
    for code in codes:
        d = panelBase / code
        if not d.exists():
            continue
        for p in sorted(d.glob("*.parquet")):
            lines.append(f"{code}/{p.name}")

    distDir = Path("dist")
    distDir.mkdir(exist_ok=True)
    target = distDir / "changed_panel.txt"
    target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(f"[onlinePanel] dist/changed_panel.txt: {len(lines)} entries")


def main() -> int:
    """online 1패스 panel 빌드 CLI entry — providers fetch + gather build 조합 (R1 layer-밖)."""
    parser = argparse.ArgumentParser(description="online 1패스 panel 빌더 (디스크 zip 0)")
    parser.add_argument("--codes", help="쉼표 구분 종목 코드 list (예: 005930,000660)")
    parser.add_argument("--changed", action="store_true", help="dist/changed_docs.txt 또는 dist/changed.txt 기반")
    args = parser.parse_args()

    if "DARTLAB_DATA_DIR" not in os.environ:
        os.environ["DARTLAB_DATA_DIR"] = os.path.join(os.getcwd(), "data")
    dataDir = os.environ["DARTLAB_DATA_DIR"]
    workers = int(os.environ.get("PANEL_WORKERS", "4"))

    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    else:
        codes = _resolveChangedCodes()
    if not codes:
        print("[onlinePanel] 대상 0 종목 — 종료")
        _writeChangedPanel([], dataDir)
        return 0

    import polars as pl

    from dartlab.gather.dart.client import DartClient
    from dartlab.gather.dart.document import buildTargetsFromDocsParquet, streamZipBytes
    from dartlab.providers.dart.panel.build import buildPanelFromStream, panelXbrlRefPath

    refPath = panelXbrlRefPath()
    if not refPath.exists():
        print(f"[onlinePanel] panelXbrlRef 없음: {refPath} — HF seed 선행 필요 (online 은 refScan 안 함)")
        return 1
    refDf = pl.read_parquet(str(refPath))

    panelBase = Path(dataDir) / "dart" / "panel"
    client = DartClient()
    built = 0
    totalRows = 0
    print(f"[onlinePanel] 대상 {len(codes)} 종목 — fetch workers={workers} (디스크 zip 0)")
    for code in codes:
        targets = buildTargetsFromDocsParquet(codes=[code])  # docs.parquet rcept (per-corp)
        if not targets:
            continue
        # 종목 단위 stream — bytes 메모리 bound (Q4 대형 zip 폭주 가드).
        docStream = ((rceptNo, raw) for _code, rceptNo, raw in streamZipBytes(client, targets, workers=workers))
        res = buildPanelFromStream(code, docStream, refDf=refDf, outBaseDir=panelBase, overwrite=True)
        if res:
            built += 1
            totalRows += sum(res.values())

    print(f"[onlinePanel] online 빌드: {built}/{len(codes)} 종목, {totalRows} rows")
    _writeChangedPanel(codes, dataDir)

    return 0 if built else 1


if __name__ == "__main__":
    sys.exit(main())
