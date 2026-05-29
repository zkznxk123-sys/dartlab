"""v5 sections artifact builder entry — 종목별 zip → period sharded parquet.

LLM Specifications:
    AntiPatterns:
        - 한 종목 빌드 중 다른 종목 zip read 금지 — strict per-corp.
        - period 매핑 시 rcept_no 직접 사용 금지 — DART 의 rcept_no → period
          (YYYYQn) 매핑 룰 활용 (zipCollector / docs.parquet 메타 참조).
        - 옛 docs.parquet schema 호환 금지 — 신 14 col schema 단독.
    OutputSchema:
        - ``buildSections(code) -> dict[period, rowCount]``
        - 출력: ``data/dart/docs/{code}/{period}.parquet`` (신 sections SSOT, 옛 docs.parquet 위치 대체).
        - 14 col schema.
    Prerequisites:
        - data/dart/original/docs/{code}/*.zip
        - refDf (Layer 1 ref table, P-S3 결과 또는 5 baseline scan).
    Freshness:
        - ref table 갱신 후 옛 양식 매핑 재빌드 가능.
    Dataflow:
        - zip → XML → walker → row list → period 별 group → parquet write.
    TargetMarkets:
        - KR (DART).

마스터 플랜: v5 §2.4 + §3.3.
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import re
import time
import zipfile
from pathlib import Path

import polars as pl
from lxml import etree

import dartlab.config as _cfg
from dartlab.providers.dart.docs.sectionsNew.refScan import scanRefBaseline
from dartlab.providers.dart.docs.sectionsNew.walker import (
    detectSchemaEra,
    walkSections,
)

_log = logging.getLogger(__name__)

_RCEPT_RE = re.compile(r"^(\d{14})\.zip$", re.IGNORECASE)

# 14 col schema 동결 (마스터 플랜 v5 §3.3)
SCHEMA_V5: dict[str, pl.DataType] = {
    "chapter": pl.Utf8,
    "sectionLeaf": pl.Utf8,
    "blockLeaf": pl.Utf8,
    "xbrlClass": pl.Utf8,
    "xbrlMatched": pl.Boolean,
    "xbrlMatchScore": pl.Float32,
    "atocId": pl.Utf8,
    "aassocnote": pl.Utf8,
    "blockOrder": pl.UInt32,
    "contentRaw": pl.Utf8,
    "period": pl.Utf8,
    "corp": pl.Utf8,
    "rceptNo": pl.Utf8,
    "disclosureKey": pl.Utf8,  # P-S7 canonicalResolver 가 채움. P-S4 단계 NULL.
}


def _readZip(zp: Path) -> tuple[str | None, list[str]]:
    """zip → (rcept_no, [xml strings ...]). encoding trial decode.

    DART zip 의 모든 XML 파일 처리 — 사업보고서 (Q4) 첨부 양식 (감사보고서,
    내부회계관리제도, 기타 disclosure 등) 도 sections 에 포함. 첨부 누락 시 Q4
    annual report 의 substantial content 가 떨어짐 — feedback_no_content_plain_precompute
    원칙 위반.

    declaration encoding 거짓말 (옛 양식 utf-8 선언이나 실제 cp949) 회피 —
    utf-8 strict → cp949 fallback.
    """
    from dartlab.providers.dart.docs.sectionsNew.refScan.zipScanWorker import _decodeXmlBytes

    m = _RCEPT_RE.match(zp.name)
    rcept = m.group(1) if m else zp.stem
    xmls: list[str] = []
    try:
        with zipfile.ZipFile(zp) as zf:
            names = sorted(n for n in zf.namelist() if n.lower().endswith(".xml"))
            for n in names:
                with zf.open(n) as f:
                    raw = f.read()
                xmls.append(_decodeXmlBytes(raw))
    except (zipfile.BadZipFile, OSError, KeyError) as exc:
        _log.warning("zip read 실패 %s: %s", zp, exc)
        return (None, [])
    return (rcept, xmls)


# 표지 "사업연도 YYYY년 MM월 DD일 부터 YYYY년 MM월 DD일 까지" 패턴
# 결산월 무관 universal — 회사의 *실제 보고기간 종료일* 기반 calendar quarter 매핑.
# 12월 결산 / 3월 결산 / 6월 결산 / 9월 결산 모두 동일 작동:
#   - 12월 결산 1Q = 1~3월 → end 03 → Q1
#   - 3월 결산 1Q = 4~6월 → end 06 → Q2 (12월 결산 양식 normalize)
_FISCAL_PERIOD_RE = re.compile(
    r"사업연도\s+\d{4}\s*년\s+\d{1,2}\s*월\s+\d{1,2}\s*일\s+부터\s+(\d{4})\s*년\s+(\d{1,2})\s*월\s+\d{1,2}\s*일"
)
# 종료월 → calendar quarter (12월 결산 양식)
_MONTH_TO_QUARTER = {
    1: "Q4",
    2: "Q4",
    3: "Q1",  # 03/31 종료 = Q1
    4: "Q1",
    5: "Q1",
    6: "Q2",  # 06/30 종료 = Q2
    7: "Q2",
    8: "Q2",
    9: "Q3",  # 09/30 종료 = Q3
    10: "Q3",
    11: "Q3",
    12: "Q4",  # 12/31 종료 = Q4
}


def _periodFromXml(root, rceptNo: str) -> str:
    """XML 표지의 "사업연도" 종료일 → calendar quarter (YYYYQn).

    결산월 무관 universal — 회사의 *실제 보고기간 종료일* 의 *달력월* 기반.
    예시:
        - 12월 결산 005930 의 Q3 분기보고서 → "사업연도 2024-01-01 부터 2024-09-30"
          → end month=9 → 2024Q3
        - 3월 결산 회사의 Q1 분기보고서 → "사업연도 ... 부터 2024-06-30"
          → end month=6 → 2024Q2 (12월 결산 양식 normalize)

    fallback (사업연도 패턴 미발견): DOCUMENT-NAME ACODE + rcept_no 접수월 추정.
    """
    # XML 표지 텍스트 추출 (BODY 전체 itertext, 첫 5000 char 만)
    try:
        bodyText = "".join(root.itertext())[:5000]
    except (TypeError, AttributeError):
        bodyText = ""

    m = _FISCAL_PERIOD_RE.search(bodyText)
    if m:
        endYear = m.group(1)
        endMonth = int(m.group(2))
        suffix = _MONTH_TO_QUARTER.get(endMonth, "Q4")
        # 1~2월 종료 (이상 case) 는 Q4 의 직전년도 양식 (12월 결산화)
        if endMonth in (1, 2):
            try:
                endYear = str(int(endYear) - 1)
            except ValueError:
                pass
        return f"{endYear}{suffix}"

    # fallback — ACODE + 접수월
    docName = root.find(".//DOCUMENT-NAME")
    acode = (docName.get("ACODE", "") if docName is not None else "") or ""
    year = rceptNo[:4]
    month = int(rceptNo[4:6]) if rceptNo[4:6].isdigit() else 1
    if acode == "11011":
        suffix = "Q4"
        if month <= 4:
            try:
                year = str(int(year) - 1)
            except ValueError:
                pass
    elif acode == "11012":
        suffix = "Q2"
    elif acode == "11013":
        suffix = "Q1" if month <= 6 else "Q3"
    elif acode == "11014":
        suffix = "Q3"
    elif acode in ("00760", "00761"):
        suffix = "Q4"
        if month <= 4:
            try:
                year = str(int(year) - 1)
            except ValueError:
                pass
    else:
        suffix = "Q4"
    return f"{year}{suffix}"


def buildSections(
    code: str,
    *,
    refDf: pl.DataFrame | None = None,
    matchThreshold: float = 0.70,
    outBaseDir: Path | str | None = None,
    overwrite: bool = True,
    verbose: bool = False,
) -> dict[str, int]:
    """종목별 sections artifact 빌드.

    Args:
        code: 종목코드 (예: "005930").
        refDf: Layer 1 ref table. None = 5 baseline scan 사용 (P-S3 결과 없으면).
        matchThreshold: fuzzy match Jaccard threshold (P-S2 검증 0.70).
        outBaseDir: 출력 base dir. None = config default.
        overwrite: 기존 period parquet overwrite 여부.
        verbose: 진행 로그.

    Returns:
        ``{period: rowCount}`` dict.
    """
    if outBaseDir is None:
        # 사용자 결정: 신규 artifact 가 옛 docs.parquet 위치 대체 (data/dart/docs/).
        outBaseDir = Path(_cfg.dataDir) / "dart" / "docs"
    outBaseDir = Path(outBaseDir)
    outDir = outBaseDir / code
    outDir.mkdir(parents=True, exist_ok=True)

    if refDf is None:
        refDf = scanRefBaseline(minCorpCount=1)

    # 가속: refMatcher token set pre-compute (worker init 후 이미 done 이면 skip)
    from dartlab.providers.dart.docs.sectionsNew.refScan.refMatcher import (
        _REF_TOKENS as _existing,
    )
    from dartlab.providers.dart.docs.sectionsNew.refScan.refMatcher import (
        precomputeRefTokens,
        setGlobalRefTokens,
    )

    if _existing is None:
        setGlobalRefTokens(precomputeRefTokens(refDf))

    zipDir = Path(_cfg.dataDir) / "dart" / "original" / "docs" / code
    if not zipDir.exists():
        _log.warning("zip dir 없음: %s", zipDir)
        return {}

    parser = etree.XMLParser(recover=True, huge_tree=True)
    periodRows: dict[str, list[dict]] = {}
    for zp in sorted(zipDir.glob("*.zip")):
        rcept, xmls = _readZip(zp)
        if not xmls or not rcept:
            continue
        # period 는 zip 의 첫 XML (메인 보고서 표지) 에서 결정.
        period: str | None = None
        for xmlIdx, xml in enumerate(xmls):
            try:
                root = etree.fromstring(xml.encode("utf-8"), parser)
            except (etree.XMLSyntaxError, ValueError):
                continue
            if root is None:
                continue
            era = detectSchemaEra(root)
            if period is None:
                period = _periodFromXml(root, rcept)
            # 통합 walker — 모든 era 동일 알고리즘 (container 직속 자식 단위 emit).
            # walkerV1 은 폐기 — 옛 양식 P heading 검출 휴리스틱이 중복/손실 원인이었음.
            for row in walkSections(root, era, refDf, matchThreshold=matchThreshold):
                row["period"] = period
                row["corp"] = code
                row["rceptNo"] = rcept
                row["disclosureKey"] = None
                periodRows.setdefault(period, []).append(row)

    result: dict[str, int] = {}
    for period, rows in periodRows.items():
        if not rows:
            continue
        df = pl.DataFrame(rows, schema=SCHEMA_V5)
        outPath = outDir / f"{period}.parquet"
        if outPath.exists() and not overwrite:
            continue
        df.write_parquet(str(outPath), compression="zstd")
        result[period] = df.height
        if verbose:
            _log.info("  %s %s: %d row", code, period, df.height)

    return result


_GLOBAL_REF: pl.DataFrame | None = None


def _initWorker(refPath: str) -> None:
    """multiprocessing worker init — ref table load + token pre-compute.

    가속 핵심: refMatcher 의 token set 을 worker 시작 시 한 번 계산
    → buildSections 의 매 row matchToRef 호출에서 row iter 회피.
    """
    global _GLOBAL_REF
    _GLOBAL_REF = pl.read_parquet(refPath)
    # token pre-compute (refMatcher 의 _REF_TOKENS 채움)
    from dartlab.providers.dart.docs.sectionsNew.refScan.refMatcher import (
        precomputeRefTokens,
        setGlobalRefTokens,
    )

    refTokens = precomputeRefTokens(_GLOBAL_REF)
    setGlobalRefTokens(refTokens)


def _buildOne(args: tuple[str, str, str]) -> tuple[str, int, int, float]:
    """worker entry — (code, refPath, outBaseDir) → (code, periodCount, totalRow, elapsed).

    pickleable. refPath 는 ignored (initializer 가 _GLOBAL_REF set).
    """
    code, refPath, outBaseDir = args
    global _GLOBAL_REF
    ref = _GLOBAL_REF
    if ref is None:
        ref = pl.read_parquet(refPath)
    t0 = time.perf_counter()
    try:
        result = buildSections(
            code,
            refDf=ref,
            outBaseDir=Path(outBaseDir),
            overwrite=True,
            verbose=False,
        )
        return (code, len(result), sum(result.values()), time.perf_counter() - t0)
    except (OSError, ValueError, RuntimeError, pl.exceptions.PolarsError) as exc:
        _log.warning("buildSections 실패 %s: %s", code, exc)
        return (code, 0, 0, time.perf_counter() - t0)


def buildSectionsAll(
    *,
    refPath: str | Path = "data/dart/sectionsXbrlRef.parquet",
    outBaseDir: str | Path = "data/dart/docs",
    codes: list[str] | None = None,
    numWorkers: int = 8,
    progressEvery: int = 50,
    verbose: bool = True,
) -> dict[str, tuple[int, int]]:
    """전종목 sectionsV5 빌드 — multiprocessing 8 코어.

    Args:
        refPath: Layer 1 ref parquet.
        outBaseDir: 출력 base dir.
        codes: 종목 list. None = ``data/dart/original/docs/`` 의 모든 종목.
        numWorkers: Pool workers. 기본 8.
        progressEvery: 진행 로그 빈도.
        verbose: 진행 로그.

    Returns:
        ``{code: (periodCount, totalRow)}`` dict.

    예상 시간 (8 코어): 5 baseline 130s = 26s/code (단일) → 8코어 = 3.25s/code
        전종목 2,928 × 3.25s = ~9,500s = ~2.6 시간.
    """
    import dartlab.config as _cfg

    if codes is None:
        baseDir = Path(_cfg.dataDir) / "dart" / "original" / "docs"
        codes = sorted([d.name for d in baseDir.iterdir() if d.is_dir()])

    if verbose:
        _log.info("buildSectionsAll: %d 종목, %d workers", len(codes), numWorkers)

    refPathStr = str(refPath)
    outBaseStr = str(outBaseDir)
    Path(outBaseStr).mkdir(parents=True, exist_ok=True)

    args = [(c, refPathStr, outBaseStr) for c in codes]
    result: dict[str, tuple[int, int]] = {}
    processed = 0
    failed = 0
    totalRows = 0
    t0 = time.perf_counter()
    with mp.Pool(processes=numWorkers, initializer=_initWorker, initargs=(refPathStr,)) as pool:
        for code, pcount, rowCount, elapsed in pool.imap_unordered(_buildOne, args, chunksize=4):
            result[code] = (pcount, rowCount)
            processed += 1
            totalRows += rowCount
            if pcount == 0:
                failed += 1
            if verbose and processed % progressEvery == 0:
                wall = time.perf_counter() - t0
                rate = processed / wall if wall > 0 else 0
                eta = (len(codes) - processed) / rate if rate > 0 else 0
                _log.info(
                    "[%d/%d] %.1f code/s, ETA %.1f min, totalRows=%d, failed=%d",
                    processed,
                    len(codes),
                    rate,
                    eta / 60,
                    totalRows,
                    failed,
                )
    if verbose:
        wall = time.perf_counter() - t0
        _log.info(
            "완료: %d codes, %d failed, %d totalRows, %.1f min",
            len(codes),
            failed,
            totalRows,
            wall / 60,
        )
    return result


def buildSectionsBaseline(
    codes: list[str] | None = None,
    *,
    refDf: pl.DataFrame | None = None,
    verbose: bool = True,
) -> dict[str, dict[str, int]]:
    """5 baseline 빌드 — P-S4 / P-S5 검증.

    Args:
        codes: 종목코드 list. None = 5 baseline default.
        refDf: ref table. None = scanRefBaseline.
        verbose: 진행 로그.

    Returns:
        ``{code: {period: rowCount}}`` 중첩 dict.
    """
    if codes is None:
        codes = ["005930", "005380", "035720", "207940", "000660"]
    if refDf is None:
        refDf = scanRefBaseline(minCorpCount=1)
    out: dict[str, dict[str, int]] = {}
    for code in codes:
        if verbose:
            _log.info("== %s 빌드 시작 ==", code)
        out[code] = buildSections(code, refDf=refDf, verbose=verbose)
        if verbose:
            total = sum(out[code].values())
            _log.info(
                "== %s 완료: %d period, %d total row ==",
                code,
                len(out[code]),
                total,
            )
    return out
