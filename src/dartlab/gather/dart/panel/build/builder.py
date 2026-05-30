"""panel artifact builder entry — 종목별 zip → period sharded parquet.

zip → XML → walker(손실0/dup0) → horizontalize(무손실 concat) → disclosureKey 부착
(BUILD) → period 별 group → ``data/dart/panel/{code}/{period}.parquet`` (panel SSOT).

period 는 표지 사업연도 종료일 → ``core.panel.periodFromEnd`` (결산월 무관 12월결산화).
XML 표지 파싱(lxml)은 본 build 층 책임 — core 는 (year, month) 순수 변환만(R2).

LLM Specifications:
    AntiPatterns:
        - 한 종목 빌드 중 다른 종목 zip read 금지 — strict per-corp.
        - period 매핑 시 rcept_no 직접 사용 금지 — 표지 사업연도 종료일 기준.
        - 옛 docs.parquet schema 호환 금지 — 신 14-col PANEL_SCHEMA 단독.
        - contentRaw 태그 strip 금지 — etree.tostring 원본(R4).
    OutputSchema:
        - ``buildPanel(code) -> dict[period, rowCount]``.
        - 출력: ``data/dart/panel/{code}/{period}.parquet`` (14-col).
    Prerequisites:
        - data/dart/original/docs/{code}/*.zip (로컬).
        - refDf (panelXbrlRef.parquet 또는 5 baseline scan).
    Freshness:
        - ref table 갱신 후 옛 양식 매핑 재빌드 가능.
    Dataflow:
        - zip → XML → walker → horizontalize → resolveBatch(disclosureKey) →
          period group → parquet write.
    TargetMarkets:
        - KR (DART).
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
from dartlab.core.panel import PANEL_SCHEMA, periodFromEnd, resolveBatch

from .horizontalize import horizontalize
from .refScan import scanRefBaseline
from .walker import detectSchemaEra, walkSections

_log = logging.getLogger(__name__)

_RCEPT_RE = re.compile(r"^(\d{14})\.zip$", re.IGNORECASE)

# 표지 "사업연도 YYYY년 MM월 DD일 부터 YYYY년 MM월 DD일 까지" — 종료(year, month) 추출.
_FISCAL_PERIOD_RE = re.compile(
    r"사업연도\s+\d{4}\s*년\s+\d{1,2}\s*월\s+\d{1,2}\s*일\s+부터\s+(\d{4})\s*년\s+(\d{1,2})\s*월\s+\d{1,2}\s*일"
)


def _readZip(zp: Path) -> tuple[str | None, list[str]]:
    """zip → (rcept_no, [xml strings]). encoding trial decode.

    DART zip 의 모든 XML 처리 — 사업보고서(Q4) 첨부 양식(감사보고서·내부회계관리제도 등)도
    panel 에 포함. declaration encoding 거짓말(옛 양식 utf-8 선언이나 실제 cp949) 회피.

    Args:
        zp: zip 파일 경로.

    Returns:
        ``(rcept_no, [xml str])``. read 실패 시 ``(None, [])``.

    Raises:
        없음 — BadZipFile/OSError/KeyError 흡수.

    Example:
        >>> _readZip(Path("data/dart/original/docs/005930/...zip"))  # doctest: +SKIP
    """
    from .refScan.zipScanWorker import _decodeXmlBytes

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


def _periodFromXml(root, rceptNo: str) -> str:
    """XML 표지의 "사업연도" 종료일 → calendar quarter (core.panel.periodFromEnd).

    1순위 = 표지 "사업연도 ... 부터 YYYY년 MM월" 종료(year, month) → periodFromEnd.
    fallback = DOCUMENT-NAME ACODE + rcept_no 접수월 추정 (표지 패턴 미발견 시).

    Args:
        root: lxml etree root.
        rceptNo: 접수번호 (fallback 연·월 추정).

    Returns:
        "YYYYQn" period 키.

    Raises:
        없음.

    Example:
        >>> _periodFromXml(root, "20240514000001")  # doctest: +SKIP
    """
    try:
        bodyText = "".join(root.itertext())[:5000]
    except (TypeError, AttributeError):
        bodyText = ""

    m = _FISCAL_PERIOD_RE.search(bodyText)
    if m:
        return periodFromEnd(int(m.group(1)), int(m.group(2)))

    # fallback — ACODE + 접수월
    docName = root.find(".//DOCUMENT-NAME")
    acode = (docName.get("ACODE", "") if docName is not None else "") or ""
    year = rceptNo[:4]
    month = int(rceptNo[4:6]) if rceptNo[4:6].isdigit() else 1
    if acode == "11011":
        suffix = "Q4"
        if month <= 4:
            year = _prevYear(year)
    elif acode == "11012":
        suffix = "Q2"
    elif acode == "11013":
        suffix = "Q1" if month <= 6 else "Q3"
    elif acode == "11014":
        suffix = "Q3"
    elif acode in ("00760", "00761"):
        suffix = "Q4"
        if month <= 4:
            year = _prevYear(year)
    else:
        suffix = "Q4"
    return f"{year}{suffix}"


def _prevYear(year: str) -> str:
    """연도 문자열 → 직전 연도 문자열 (변환 실패 시 원본).

    Args:
        year: "YYYY" 문자열.

    Returns:
        직전 연도 "YYYY". int 변환 실패 시 원본 그대로.

    Raises:
        없음.

    Example:
        >>> _prevYear("2024")
        '2023'
    """
    try:
        return str(int(year) - 1)
    except ValueError:
        return year


def buildPanel(
    code: str,
    *,
    refDf: pl.DataFrame | None = None,
    matchThreshold: float = 0.70,
    outBaseDir: Path | str | None = None,
    overwrite: bool = True,
    verbose: bool = False,
) -> dict[str, int]:
    """종목별 panel artifact 빌드 — zip → period sharded 14-col parquet.

    Args:
        code: 종목코드 (예: "005930").
        refDf: panelXbrlRef ref table. None = 5 baseline scan.
        matchThreshold: 옛 양식 fuzzy match Jaccard threshold (검증 0.70).
        outBaseDir: 출력 base dir. None = ``data/dart/panel``.
        overwrite: 기존 period parquet overwrite 여부.
        verbose: 진행 로그.

    Returns:
        ``{period: rowCount}`` dict. zip dir 부재 시 빈 dict.

    Raises:
        없음 — zip read/parse 실패는 흡수해 skip.

    Example:
        >>> buildPanel("005930", verbose=True)  # doctest: +SKIP
        {'2025Q4': 142, '2025Q3': 98, ...}

    SeeAlso:
        - ``buildPanelAll`` — 전종목 multiprocessing 빌드.
        - ``horizontalize`` — element→section 수평화.
        - ``core.panel.resolveBatch`` — disclosureKey 부착.

    Requires:
        - data/dart/original/docs/{code}/*.zip. polars. lxml.

    Capabilities:
        - 한 종목의 전 기간 공시를 14-col panel artifact 로 — 손실0/dup0/태그무손실.

    Guide:
        - 운영자/CI build-time 호출. runtime read 는 providers/dart/panel.

    AIContext:
        - strict per-corp 빌드 — 다른 종목 zip 미접근.

    LLM Specifications:
        AntiPatterns:
            - period 별 parquet 외 단일 flat parquet 금지 — nested {code}/{period}.
            - contentRaw 태그 strip 금지 (R4).
        OutputSchema:
            - ``dict[str, int]`` + 부수효과 data/dart/panel/{code}/{period}.parquet.
        Prerequisites:
            - 로컬 zip + refDf (또는 baseline scan).
        Freshness:
            - ref/zip 갱신 시 재빌드.
        Dataflow:
            - zip → walker → horizontalize → resolveBatch → period group → write.
        TargetMarkets:
            - KR (DART).
    """
    if outBaseDir is None:
        outBaseDir = Path(_cfg.dataDir) / "dart" / "panel"
    outBaseDir = Path(outBaseDir)
    outDir = outBaseDir / code
    outDir.mkdir(parents=True, exist_ok=True)

    if refDf is None:
        refDf = scanRefBaseline(minCorpCount=1)

    # 가속: refMatcher token set pre-compute (worker init 후 이미 done 이면 skip)
    from .refScan.refMatcher import _REF_TOKENS as _existing
    from .refScan.refMatcher import precomputeRefTokens, setGlobalRefTokens

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
        period: str | None = None
        for xml in xmls:
            try:
                root = etree.fromstring(xml.encode("utf-8"), parser)
            except (etree.XMLSyntaxError, ValueError):
                continue
            if root is None:
                continue
            era = detectSchemaEra(root)
            if period is None:
                period = _periodFromXml(root, rcept)
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
        df = pl.DataFrame(rows, schema=PANEL_SCHEMA)
        df = horizontalize(df)
        df = resolveBatch(df, marketNs="kr")
        df = df.select(list(PANEL_SCHEMA.keys()))
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

    refMatcher token set 을 worker 시작 시 한 번 계산 → 매 row matchToRef 의 row iter 회피.

    Args:
        refPath: ref parquet 경로.

    Returns:
        None.

    Raises:
        없음.

    Example:
        >>> _initWorker("data/dart/panelXbrlRef.parquet")  # doctest: +SKIP
    """
    global _GLOBAL_REF
    _GLOBAL_REF = pl.read_parquet(refPath)
    from .refScan.refMatcher import precomputeRefTokens, setGlobalRefTokens

    setGlobalRefTokens(precomputeRefTokens(_GLOBAL_REF))


def _buildOne(args: tuple[str, str, str]) -> tuple[str, int, int, float]:
    """worker entry — (code, refPath, outBaseDir) → (code, periodCount, totalRow, elapsed).

    Args:
        args: ``(code, refPath, outBaseDir)`` 튜플. pickleable.

    Returns:
        ``(code, periodCount, totalRow, elapsed)``. 실패 시 (code, 0, 0, elapsed).

    Raises:
        없음 — 빌드 실패 흡수.

    Example:
        >>> _buildOne(("005930", "ref.parquet", "data/dart/panel"))  # doctest: +SKIP
    """
    code, refPath, outBaseDir = args
    global _GLOBAL_REF
    ref = _GLOBAL_REF
    if ref is None:
        ref = pl.read_parquet(refPath)
    t0 = time.perf_counter()
    try:
        result = buildPanel(code, refDf=ref, outBaseDir=Path(outBaseDir), overwrite=True, verbose=False)
        return (code, len(result), sum(result.values()), time.perf_counter() - t0)
    except (OSError, ValueError, RuntimeError, pl.exceptions.PolarsError) as exc:
        _log.warning("buildPanel 실패 %s: %s", code, exc)
        return (code, 0, 0, time.perf_counter() - t0)


def buildPanelAll(
    *,
    refPath: str | Path = "data/dart/panelXbrlRef.parquet",
    outBaseDir: str | Path = "data/dart/panel",
    codes: list[str] | None = None,
    numWorkers: int = 8,
    progressEvery: int = 50,
    verbose: bool = True,
) -> dict[str, tuple[int, int]]:
    """전종목 panel 빌드 — multiprocessing.

    Args:
        refPath: panelXbrlRef ref parquet.
        outBaseDir: 출력 base dir.
        codes: 종목 list. None = ``data/dart/original/docs/`` 의 모든 종목.
        numWorkers: Pool workers (IO heavy, 기본 8).
        progressEvery: 진행 로그 빈도.
        verbose: 진행 로그.

    Returns:
        ``{code: (periodCount, totalRow)}`` dict.

    Raises:
        없음 — 종목별 실패 흡수.

    Example:
        >>> buildPanelAll(codes=["005930", "005380"])  # doctest: +SKIP

    SeeAlso:
        - ``buildPanel`` — 단일 종목 빌드.
        - ``buildPanelBaseline`` — 5 baseline 검증.

    Requires:
        - data/dart/original/docs/{code}/*.zip 전종목. multiprocessing.

    Capabilities:
        - 전종목(~2,900) panel artifact 일괄 생산 (8코어 ~2.6h).

    Guide:
        - CI sync 잡 또는 운영자. memory 무관(strict per-corp worker).

    AIContext:
        - imap_unordered chunk=4 — IO/CPU 균형.

    LLM Specifications:
        AntiPatterns:
            - Pool.map 금지 — large input memory 폭발. imap_unordered.
            - worker 간 ref 재로드 금지 — _initWorker 1회 load.
        OutputSchema:
            - ``dict[str, tuple[int, int]]``.
        Prerequisites:
            - 전종목 zip + ref parquet.
        Freshness:
            - 분기 incremental — changed code 만.
        Dataflow:
            - codes → Pool(_initWorker) → _buildOne → 집계.
        TargetMarkets:
            - KR (DART).
    """
    if codes is None:
        baseDir = Path(_cfg.dataDir) / "dart" / "original" / "docs"
        codes = sorted([d.name for d in baseDir.iterdir() if d.is_dir()])

    if verbose:
        _log.info("buildPanelAll: %d 종목, %d workers", len(codes), numWorkers)

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
        for code, pcount, rowCount, _elapsed in pool.imap_unordered(_buildOne, args, chunksize=4):
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
        _log.info("완료: %d codes, %d failed, %d totalRows, %.1f min", len(codes), failed, totalRows, wall / 60)
    return result


def buildPanelBaseline(
    codes: list[str] | None = None,
    *,
    refDf: pl.DataFrame | None = None,
    verbose: bool = True,
) -> dict[str, dict[str, int]]:
    """5 baseline panel 빌드 — 검증(손실0/dup0).

    Args:
        codes: 종목코드 list. None = 5 baseline default.
        refDf: ref table. None = scanRefBaseline.
        verbose: 진행 로그.

    Returns:
        ``{code: {period: rowCount}}`` 중첩 dict.

    Raises:
        없음.

    Example:
        >>> buildPanelBaseline(["005930"])  # doctest: +SKIP

    SeeAlso:
        - ``buildPanel`` — 단일 종목.
        - ``buildPanelAll`` — 전종목.

    Requires:
        - baseline zip + refDf.

    Capabilities:
        - 검증 게이트(G1 손실0/dup0) 입력 빌드.

    Guide:
        - CLI ``python -m dartlab.gather.dart.panel.build.builder`` 기본 경로.

    AIContext:
        - 단일 process — debug 용이.

    LLM Specifications:
        AntiPatterns:
            - 5 baseline 외 default 추가 금지 — 검증 게이트 일치.
        OutputSchema:
            - ``dict[str, dict[str, int]]``.
        Prerequisites:
            - baseline zip.
        Freshness:
            - 검증 시점.
        Dataflow:
            - codes → buildPanel 순차 → 중첩 dict.
        TargetMarkets:
            - KR (DART).
    """
    if codes is None:
        codes = ["005930", "005380", "035720", "207940", "000660"]
    if refDf is None:
        refDf = scanRefBaseline(minCorpCount=1)
    out: dict[str, dict[str, int]] = {}
    for code in codes:
        if verbose:
            _log.info("== %s 빌드 시작 ==", code)
        out[code] = buildPanel(code, refDf=refDf, verbose=verbose)
        if verbose:
            total = sum(out[code].values())
            _log.info("== %s 완료: %d period, %d total row ==", code, len(out[code]), total)
    return out


def _main() -> None:
    """CLI entry — ``python -m dartlab.gather.dart.panel.build.builder --codes 005930``.

    Args:
        없음 (argparse).

    Returns:
        None.

    Raises:
        없음.

    Example:
        >>> _main()  # doctest: +SKIP
    """
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description="panel artifact 빌드")
    ap.add_argument("--codes", type=str, default="", help="콤마구분 종목코드. 빈값=5 baseline")
    ap.add_argument("--ref", type=str, default="data/dart/panelXbrlRef.parquet", help="ref parquet")
    ap.add_argument("--out", type=str, default="data/dart/panel", help="출력 base dir")
    ap.add_argument("--all", action="store_true", help="전종목 빌드 (multiprocessing)")
    args = ap.parse_args()

    refDf: pl.DataFrame | None = None
    refPath = Path(args.ref)
    if refPath.exists():
        refDf = pl.read_parquet(str(refPath))
        _log.info("ref table load: %s (%d entry)", refPath, refDf.height)

    if args.all:
        buildPanelAll(refPath=args.ref, outBaseDir=args.out)
        return

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] or None
    out = buildPanelBaseline(codes=codes, refDf=refDf, verbose=True)
    total = sum(sum(p.values()) for p in out.values())
    _log.info("=== 완료 %d 종목, %d panel rows ===", len(out), total)


if __name__ == "__main__":
    _main()
