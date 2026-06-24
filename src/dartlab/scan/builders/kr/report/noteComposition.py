"""KR scan 주석 구성(비용 성격별·부문별 매출) parquet builder — panel cellsFromContent SSOT.

터미널이 "비용 체질"·"부문별 매출"을 *빠르게* 보여주도록, panel.parquet 의 주석 표 contentRaw 를
``providers.dart.panel.build.cell.cellsFromContent`` (정부 XBRL 택소노미 셀 분해)로 풀어 tidy parquet
``dart/scan/report/noteComposition.parquet`` 로 굽는다. 런타임은 이걸 직독해 group→% 만 한다(정규식 파싱 0).

왜 cellsFromContent 인가: 비용은 ``acode``(ifrs-full_RawMaterialsAndConsumablesUsed=원재료 등)가 곧 언어무관
카테고리고, 부문은 ``axisPath`` 가 세그먼트명을 운반한다 — 런타임 정규식/매트릭스 파서(노이즈·총계·이름변경
취약)를 대체한다. ACONTEXT XBRL 태깅은 2025-03 사업보고서부터라 *최근 분기만* 정밀(옛 기간 미수록 — 상세는 viewer).

추출 규약(실측 검증):
    - 비용(cost): acode 카테고리 + label 한글명, valueWon(단위 환산). 제외 = ExpenseByNature(총계)·
      ChangesInInventories(재고변동). 당기 = ctxYear==period연도 & ctxMode∈{A,Y}.
    - 부문(segment): acode=Revenue, axisPath ⊃ OperatingSegments|ReportableSegments|BusinessSegments(화이트),
      지역/고객/제품/집계 멤버 제외(블랙). seg name = leaf 토큰 정규화. ≥2 세그먼트만 수록(단일부문 자동 배제).

LLM Specifications:
    AntiPatterns:
        - 런타임(TS)에서 표 정규식 재파싱 금지 — 본 bake 의 tidy 출력만 소비(SSOT).
        - acode/axisPath 무시하고 위치/라벨 추론 금지 — 정부 택소노미가 정본.
        - 옛(비-XBRL) 기간 강제 수록 금지 — ACONTEXT 없는 기간은 자연 0행(최근만).
    OutputSchema:
        - ``dart/scan/report/noteComposition.parquet`` (stockCode·period·kind·name·acode·valueWon·scope).
    Prerequisites:
        - data/dart/panel/{code}.parquet (panel build 결과, contentRaw 보유).
    Freshness:
        - scan prebuild 워크플로가 재빌드. panel 갱신 후 재실행.
    Dataflow:
        - panel glob → 회사별 cost/segment 블록 → cellsFromContent → 필터/단위환산 → tidy concat → parquet.
    TargetMarkets:
        - KR (DART). 부문/비용 주석 보유사. 최근(ACONTEXT 2025-03+) 분기.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import polars as pl

from dartlab.core.logger import getLogger
from dartlab.scan.builders.kr.common import BATCH_SIZE as _BATCH
from dartlab.scan.builders.kr.common import mergeBatchFiles as _mergeBatchFiles
from dartlab.scan.builders.kr.common import panelDir as _panelDir
from dartlab.scan.builders.kr.common import releaseNativeMemory as _releaseNativeMemory
from dartlab.scan.builders.kr.common import reportDir as _reportDir
from dartlab.scan.builders.kr.common import say as _say

_log = getLogger(__name__)

# ── 블록 식별(blockLeaf/sectionLeaf 정규식) ──
_COST_BLK = re.compile(r"비용의\s*성격별|성격별\s*분류|성격별\s*비용|영업비용의\s*성격별")
_SEG_BLK = re.compile(r"부문정보|영업부문|부문별\s*정보|부문별\s*보고|사업부문")

# ── 비용: 제외 acode(총계·재고변동) ──
_COST_DROP = re.compile(r"ExpenseByNature|ChangesInInventories")
# ── 부문: 화이트(영업/보고부문 축)·블랙(지역·고객·제품)·집계멤버 ──
_SEG_AXIS = re.compile(r"OperatingSegments|ReportableSegments|BusinessSegments")
_SEG_NONSEG = re.compile(
    r"Geograph|Countr|Domestic|Foreign|Overseas|MajorCustomer|ProductsAndServices|"
    r"Americas|Europe|Asia|Africa|China|Japan|Korea|NorthAmerica|SouthAmerica|MiddleEast|Oceania"
)
_SEG_AGG = re.compile(
    r"^(Operating|Consolidated|Total|Reportable|Business|Intersegment)?Segments?$|^(Operating|Consolidated|Total|Reportable)$"
)
# 2-letter 국가코드 leaf(삼성 'CN'=중국 류) — 영업부문명은 이렇게 짧은 코드가 아니다.
_SEG_CC = re.compile(
    r"^(Cn|Us|Jp|Kr|Uk|De|Fr|Eu|In|Vn|Sg|Hk|Tw|Au|Ca|Br|Ru|Mx|Id|Th|My|Ph|It|Es|Nl|Pl|Tr|Ae|Sa)$", re.IGNORECASE
)

_UNIT = re.compile(r"단위\s*[:：]?\s*([십백천만억]*\s*원)")

_NOTE_SCHEMA = {
    "stockCode": pl.Utf8,
    "period": pl.Utf8,
    "kind": pl.Utf8,  # 'cost' | 'segment'
    "name": pl.Utf8,  # 비용=한글 라벨 / 부문=세그먼트명
    "acode": pl.Utf8,  # 비용=ifrs/dart acode / 부문='ifrs-full_Revenue'
    "valueWon": pl.Float64,  # 원 환산 당기 값
    "scope": pl.Utf8,  # 'consolidated'
}


def _toNum(raw: str) -> float | None:
    s = (raw or "").strip()
    neg = s.startswith("(") and s.endswith(")")
    c = re.sub(r"[(),]", "", s)
    if not re.fullmatch(r"-?\d+", c):
        return None
    v = float(c)
    return -v if neg else v


def _unitMult(contentRaw: str) -> float:
    m = _UNIT.search(contentRaw or "")
    if not m:
        return 1e6  # 백만원 최빈 기본
    u = m.group(1).replace(" ", "")
    if "십억" in u:
        return 1e9
    if "백만" in u:
        return 1e6
    if "억" in u:
        return 1e8
    if "천" in u:
        return 1e3
    return 1.0


def _segName(axis: str) -> str:
    """axisPath leaf 토큰 → 읽을 세그먼트명. entity 접두·택소노미 꼬리·집계어 제거.

    예: 'entity..._DxSegmentsMemberOfReportableSegmentsMemberOf...' → 'Dx',
        'PharmaceuticalSectorOfEntitysTotalForSegmentConsolidationItemsMember' → 'Pharmaceutical'.
    """
    last = axis.split("|")[-1]
    last = re.sub(r"^entity\d+_", "", last)
    # 택소노미 꼬리 — '(Member)Of{Entity|Reportable|Disclosure|...}...' 이후 전부 제거
    last = re.sub(
        r"(Member)?Of(Entity|Reportable|Disclosure|Consolidat|Segment|Operating|Total|Group|Geograph|Countr).*$",
        "",
        last,
    )
    last = re.sub(r"MemberOf.*$", "", last)
    # 후행 택소노미 명사 제거(가독)
    last = re.sub(r"(Member|Segments?|Business|Sector|Division|Operations?)$", "", last)
    return last.strip()


def _extractCompany(code: str, panelPath: Path, *, recentN: int = 8) -> list[dict]:
    """한 회사 panel → 최근 분기 cost/segment tidy 행. ACONTEXT(XBRL) 셀만(최근). 실패=빈 list."""
    from dartlab.providers.dart.panel.build.cell import cellsFromContent

    try:
        df = (
            pl.scan_parquet(panelPath)
            .select(["period", "sectionLeaf", "chapter", "blockLeaf", "leafType", "contentRaw", "rceptNo"])
            .collect()
        )
    except Exception:
        return []
    if df.is_empty():
        return []
    out: list[dict] = []
    for kind, blkRe in (("cost", _COST_BLK), ("segment", _SEG_BLK)):
        mask = [
            bool(blkRe.search(str(b or "")) or blkRe.search(str(s or "")))
            for b, s in zip(df["blockLeaf"], df["sectionLeaf"])
        ]
        cn = df.filter(pl.Series(mask))
        if cn.is_empty():
            continue
        periods = sorted(cn["period"].unique().to_list(), reverse=True)[:recentN]
        for period in periods:
            yr = int(period[:4]) if period[:4].isdigit() else None
            if yr is None:
                continue
            sub = cn.filter(pl.col("period") == period)
            cons = sub.filter(
                (pl.col("sectionLeaf").str.contains("연결")) | (pl.col("chapter").str.contains("연결"))
            ).filter(pl.col("leafType") == "table")
            if cons.is_empty():
                cons = sub.filter(pl.col("leafType") == "table")
            # 단위는 블록 전체에서 1회 검출 — 마커가 표 본문 아닌 형제(헤더 라벨) 프래그먼트에 있는 경우 방어
            mult = _unitMult(" ".join(r or "" for r in cons["contentRaw"].to_list()))
            agg: dict[str, dict] = {}
            for raw, rc in zip(cons["contentRaw"].to_list(), cons["rceptNo"].to_list()):
                raw = raw or ""
                if "ACONTEXT" not in raw:
                    continue  # 최근(XBRL)만
                for c in cellsFromContent(
                    raw, statement=kind.upper(), scope="consolidated", period=period, code=code, rcept=rc or ""
                ):
                    if c.get("ctxYear") != yr or c.get("ctxMode") not in ("A", "Y"):
                        continue
                    acode = c.get("acode") or ""
                    v = _toNum(c.get("valueRaw"))
                    if v is None or v <= 0:
                        continue
                    if kind == "cost":
                        if not acode or _COST_DROP.search(acode):
                            continue
                        name = (c.get("label") or "").strip() or acode
                        key = acode
                        agg[key] = {
                            "name": name,
                            "acode": acode,
                            "valueWon": agg.get(key, {}).get("valueWon", 0.0) + v * mult,
                        }
                    else:
                        if "Revenue" not in acode:
                            continue
                        ax = c.get("axisPath") or ""
                        if not _SEG_AXIS.search(ax) or _SEG_NONSEG.search(ax):
                            continue
                        nm = _segName(ax)
                        if not nm or _SEG_AGG.search(nm) or _SEG_CC.match(nm):
                            continue
                        agg[nm] = {
                            "name": nm,
                            "acode": "ifrs-full_Revenue",
                            "valueWon": agg.get(nm, {}).get("valueWon", 0.0) + v * mult,
                        }
            # 부문은 ≥2 세그먼트만(단일부문 배제). 비용은 ≥3 항목.
            if kind == "segment" and len(agg) < 2:
                continue
            if kind == "cost" and len(agg) < 3:
                continue
            for rec in agg.values():
                out.append(
                    {
                        "stockCode": code,
                        "period": period,
                        "kind": kind,
                        "name": rec["name"],
                        "acode": rec["acode"],
                        "valueWon": rec["valueWon"],
                        "scope": "consolidated",
                    }
                )
    return out


def buildNoteComposition(*, recentN: int = 8, verbose: bool = True, limit: int | None = None) -> Path | None:
    """panel 전체 → ``dart/scan/report/noteComposition.parquet`` (cost/segment 최근 분기 구성).

    Parameters
    ----------
    recentN : int
        회사별 최근 분기 수 상한(블록별).
    verbose : bool
        진행 로그.
    limit : int | None
        앞 N개 회사만(검증용). None=전체.

    Returns
    -------
    Path | None
        출력 parquet 경로. 패널 없으면 None.
    """
    panels = sorted(_panelDir().glob("*.parquet"))
    if limit is not None:
        panels = panels[:limit]
    if not panels:
        _say("noteComposition: panel parquet 없음")
        return None
    outPath = _reportDir() / "noteComposition.parquet"
    batchDir = _reportDir() / "_noteCompBatch"
    batchDir.mkdir(parents=True, exist_ok=True)
    for old in batchDir.glob("*.parquet"):
        old.unlink()
    rows: list[dict] = []
    nBatch = 0
    t0 = time.time()
    for i, p in enumerate(panels):
        code = p.stem
        rows.extend(_extractCompany(code, p, recentN=recentN))
        if (i + 1) % _BATCH == 0:
            if rows:
                pl.DataFrame(rows, schema=_NOTE_SCHEMA).write_parquet(batchDir / f"batch_{nBatch:05d}.parquet")
                nBatch += 1
                rows = []
            _releaseNativeMemory()
            _say(f"noteComposition: {i + 1}/{len(panels)} ({time.time() - t0:.0f}s)")
    if rows:
        pl.DataFrame(rows, schema=_NOTE_SCHEMA).write_parquet(batchDir / f"batch_{nBatch:05d}.parquet")
        nBatch += 1
    if nBatch == 0:
        _say("noteComposition: 추출 0행")
        return None
    n = _mergeBatchFiles(batchDir, outPath, how="vertical")
    _say(f"noteComposition: {outPath.name} {n}행 ({time.time() - t0:.0f}s)")
    return outPath
