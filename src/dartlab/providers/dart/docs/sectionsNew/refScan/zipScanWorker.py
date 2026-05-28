"""zip 풀어서 XML 추출 + aclassExtractor 호출 → ref entry 누적.

P-S1 (5 baseline) 및 P-S3 (102k zip 전체) 의 entry point.
multiprocessing 은 P-S3 에서만 활성화 (P-S1 는 단일 process — debug 용이).

LLM Specifications:
    AntiPatterns:
        - zip 안 여러 XML 가정 금지 — DART zip 1 개당 XML 1 개 (실측 확인).
        - period 추출 시 zip filename 만 의존 금지 — rcept_no.xml 양식이 변경
          가능. ``rcept_no`` 별도 보유 + period 는 caller (sectionsBuilder)
          또는 docs.parquet 의 메타 통해 매핑.
        - rcept_no → period 매핑은 본 모듈에서 안 함 (zipDocsXml / zipCollector
          영역). 본 모듈은 zip path + rcept_no 만 carry.
    OutputSchema:
        - ``scanZipFiles(paths) -> pl.DataFrame`` 11 col Layer 1 schema.
        - ``scanRefBaseline(codes) -> pl.DataFrame`` 5 baseline + 전 기간.
    Prerequisites:
        - ``data/dart/original/docs/{code}/*.zip`` 로컬.
        - polars, lxml.
    Freshness:
        - P-S10 (분기 cron) — mtime > sinceDate 만 처리하는 increment 변형.
    Dataflow:
        - zip path list → 각 zip 열기 → XML 추출 → extractAclassEntries
          → corp / rcept_no / aggregator 누적 → (rawId, rawTitleCanonical)
          기준 group → corpCount/periodCount/occurrenceCount 산출.
    TargetMarkets:
        - KR (DART). EDGAR 는 별도 worker.

마스터 플랜: v5 §2.2 + §5.2 buildRefTable 알고리즘.
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import re
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import polars as pl

import dartlab.config as _cfg
from dartlab.providers.dart.docs.sectionsNew.refScan.aclassExtractor import extractAclassEntries

_log = logging.getLogger(__name__)

# zip filename 양식: "{rcept_no}.zip" (rcept_no 14 자리).
_RCEPT_RE = re.compile(r"^(\d{14})\.zip$", re.IGNORECASE)


def _rceptFromZip(path: Path) -> str | None:
    """zip 파일명 → rcept_no (14 자리). 양식 불일치는 None.

    Examples:
        >>> _rceptFromZip(Path("20260515002181.zip"))
        '20260515002181'
        >>> _rceptFromZip(Path("invalid.zip")) is None
        True
    """
    m = _RCEPT_RE.match(path.name)
    return m.group(1) if m else None


def _decodeXmlBytes(raw: bytes) -> str:
    """raw bytes → utf-8 string. trial decode (utf-8 strict → cp949 fallback).

    DART 옛 분기 zip 은 XML declaration 에 ``encoding="utf-8"`` 박지만 *실제*
    byte stream 은 cp949/EUC-KR. declaration 무시하고 utf-8 strict decode
    시도 → UnicodeDecodeError 시 cp949 fallback.

    실측 (005930 2015Q4 / 2016Q1~Q3): declaration utf-8 + 실제 cp949 → 한국어
    깨짐 회귀.
    """
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass
    try:
        return raw.decode("cp949")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def _readXml(zipPath: Path) -> str:
    """zip 안 첫 .xml 파일 → utf-8 string.

    declaration encoding 거짓말 (옛 양식 utf-8 선언이나 실제 cp949) 회피 —
    trial decode (utf-8 strict → cp949 fallback).
    """
    try:
        with zipfile.ZipFile(zipPath) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
            if not names:
                return ""
            with zf.open(names[0]) as f:
                raw = f.read()
    except (zipfile.BadZipFile, OSError, KeyError) as exc:
        _log.warning("zip read 실패 %s: %s", zipPath, exc)
        return ""
    return _decodeXmlBytes(raw)


def scanZipFiles(
    zipPaths: Iterable[Path],
    *,
    minCorpCount: int = 3,
    verbose: bool = False,
) -> pl.DataFrame:
    """zip path iterable → Layer 1 ``sectionsXbrlRef.parquet`` DataFrame.

    Args:
        zipPaths: 처리할 zip 파일 path iterable.
        minCorpCount: SSOT 입성 최소 회사 수 (기본 3, P-S3 검증 게이트).
            P-S1 (5 baseline) 검증 시 1 로 낮춰 모든 entry 확인 가능.
        verbose: 진행 로그.

    Returns:
        Layer 1 schema 11 col DataFrame:
            rawId / rawTitleCanonical / rawTitleVariants / parentRawId /
            taxonomyVersion / firstSeenPeriod / lastSeenPeriod / corpCount /
            periodCount / occurrenceCount / marketNs.

        marketNs 는 항상 ``"kr"``. taxonomyVersion 은 [추정] — 본 P-S1 단계
        에선 NULL, P-S3 에서 IFRS taxonomy 매핑 추가 layer 로.

    Examples:
        >>> from pathlib import Path
        >>> paths = list(Path("data/dart/original/docs/005930").glob("*.zip"))[:2]
        >>> df = scanZipFiles(paths, minCorpCount=1)
        >>> df.columns
        ['rawId', 'rawTitleCanonical', 'rawTitleVariants', 'parentRawId', 'taxonomyVersion', 'firstSeenPeriod', 'lastSeenPeriod', 'corpCount', 'periodCount', 'occurrenceCount', 'marketNs']

    LLM Specifications:
        AntiPatterns:
            - corp 추출 시 zipPath.parent.name 가정 — 호출자가 표준 구조
              유지 책임 (data/dart/original/docs/{code}/{rcept_no}.zip).
            - period 추출은 본 P-S1 에서 NULL — rcept_no → period 매핑은
              docs.parquet 또는 별 lookup 필요. P-S3 에서 통합.
        OutputSchema:
            - polars DataFrame, 11 col.
        Prerequisites:
            - zip 양식: ``{code}/{rcept_no}.zip``.
        Freshness:
            - minCorpCount 기본값 3 — 5 baseline P-S1 에선 1 로 낮춰 검증.
    """
    # (rawId, rawTitleCanonical) → 집계 bag
    bag: dict[tuple[str, str], dict] = defaultdict(
        lambda: {
            "titles": Counter(),
            "corps": set(),
            "rcepts": set(),
            "parent": None,
        }
    )

    processed = 0
    failed = 0
    for zp in zipPaths:
        zp = Path(zp)
        corp = zp.parent.name  # data/dart/original/docs/{code}/...
        rcept = _rceptFromZip(zp) or zp.stem
        xml = _readXml(zp)
        if not xml:
            failed += 1
            continue
        entries = extractAclassEntries(xml)
        if not entries:
            failed += 1
            continue
        for entry in entries:
            k = (entry["rawId"], entry["rawTitleCanonical"])
            v = bag[k]
            v["titles"][entry["rawTitleRaw"]] += 1
            v["corps"].add(corp)
            v["rcepts"].add(rcept)
            # parent 일관성 — 첫 발견 우선 (보통 stable)
            if v["parent"] is None and entry["parentRawId"]:
                v["parent"] = entry["parentRawId"]
        processed += 1
        if verbose and processed % 200 == 0:
            _log.info("scanned %d zip, %d entries", processed, len(bag))

    if verbose:
        _log.info(
            "총 processed=%d failed=%d unique=(rawId,title)=%d",
            processed,
            failed,
            len(bag),
        )

    rows = []
    for (rawId, titleCanonical), v in bag.items():
        if len(v["corps"]) < minCorpCount:
            continue
        variants = [t for t, _ in v["titles"].most_common()]
        rows.append(
            {
                "rawId": rawId,
                "rawTitleCanonical": titleCanonical,
                "rawTitleVariants": variants,
                "parentRawId": v["parent"],
                "taxonomyVersion": None,
                "firstSeenPeriod": None,
                "lastSeenPeriod": None,
                "corpCount": len(v["corps"]),
                "periodCount": len(v["rcepts"]),  # P-S1 단계: rcept 수 = period proxy
                "occurrenceCount": int(sum(v["titles"].values())),
                "marketNs": "kr",
            }
        )

    if not rows:
        return pl.DataFrame(
            schema={
                "rawId": pl.Utf8,
                "rawTitleCanonical": pl.Utf8,
                "rawTitleVariants": pl.List(pl.Utf8),
                "parentRawId": pl.Utf8,
                "taxonomyVersion": pl.Utf8,
                "firstSeenPeriod": pl.Utf8,
                "lastSeenPeriod": pl.Utf8,
                "corpCount": pl.UInt32,
                "periodCount": pl.UInt32,
                "occurrenceCount": pl.UInt32,
                "marketNs": pl.Utf8,
            }
        )

    return pl.DataFrame(
        rows,
        schema_overrides={
            "corpCount": pl.UInt32,
            "periodCount": pl.UInt32,
            "occurrenceCount": pl.UInt32,
        },
    ).sort(["corpCount", "occurrenceCount"], descending=[True, True])


def _zipToEntries(zipPath: Path) -> tuple[str, str, list[dict]]:
    """multiprocessing worker — 단일 zip → (corp, rcept, entries).

    pickleable function. Pool.imap 으로 사용.
    """
    zp = Path(zipPath)
    corp = zp.parent.name
    rcept = _rceptFromZip(zp) or zp.stem
    xml = _readXml(zp)
    if not xml:
        return (corp, rcept, [])
    return (corp, rcept, extractAclassEntries(xml))


def scanAllZips(
    *,
    baseDir: Path | str | None = None,
    minCorpCount: int = 3,
    numWorkers: int = 8,
    progressEvery: int = 2000,
    verbose: bool = True,
) -> pl.DataFrame:
    """P-S3 entry — 전종목 zip → Layer 1 ref table (multiprocessing).

    Args:
        baseDir: ``data/dart/original/docs/`` 경로. None = config default.
        minCorpCount: SSOT 입성 minimum corpCount. 기본 3 (plan 강제).
        numWorkers: multiprocessing.Pool workers. 기본 8.
        progressEvery: 진행 로그 빈도.
        verbose: 진행 로그.

    Returns:
        Layer 1 schema DataFrame (11 col).

    Examples:
        >>> df = scanAllZips(numWorkers=8)  # ~ 1.5~5 시간
        >>> df.height >= 200  # plan 검증 게이트
        True

    LLM Specifications:
        AntiPatterns:
            - Pool.map 사용 금지 — large input 시 memory 폭발. imap 사용.
            - chunk size 1 fix 금지 — IO heavy 라 chunk 큰 게 더 빠름.
        OutputSchema:
            - polars DataFrame, 11 col, corpCount desc 정렬.
        Prerequisites:
            - data/dart/original/docs/{code}/*.zip 로컬 (~30 GB).
        Freshness:
            - 분기 incremental rebuild (P-S10) — mtime > sinceDate 만 필터링.
    """
    if baseDir is None:
        baseDir = Path(_cfg.dataDir) / "dart" / "original" / "docs"
    baseDir = Path(baseDir)
    if not baseDir.exists():
        _log.error("baseDir 없음: %s", baseDir)
        return pl.DataFrame()
    allZips = sorted(baseDir.glob("*/*.zip"))
    if verbose:
        _log.info("전종목 zip: %d", len(allZips))

    bag: dict[tuple[str, str], dict] = defaultdict(
        lambda: {
            "titles": Counter(),
            "corps": set(),
            "rcepts": set(),
            "parent": None,
        }
    )
    processed = 0
    failed = 0
    t0 = time.perf_counter()

    with mp.Pool(processes=numWorkers) as pool:
        # imap chunk = 32: IO 병목 + worker context switching 균형
        for corp, rcept, entries in pool.imap_unordered(_zipToEntries, allZips, chunksize=32):
            if not entries:
                failed += 1
            else:
                for entry in entries:
                    k = (entry["rawId"], entry["rawTitleCanonical"])
                    v = bag[k]
                    v["titles"][entry["rawTitleRaw"]] += 1
                    v["corps"].add(corp)
                    v["rcepts"].add(rcept)
                    if v["parent"] is None and entry["parentRawId"]:
                        v["parent"] = entry["parentRawId"]
            processed += 1
            if verbose and processed % progressEvery == 0:
                elapsed = time.perf_counter() - t0
                rate = processed / elapsed if elapsed > 0 else 0
                eta = (len(allZips) - processed) / rate if rate > 0 else 0
                _log.info(
                    "[%d/%d] %.1f zip/s, ETA %.1f min, unique entries=%d, failed=%d",
                    processed,
                    len(allZips),
                    rate,
                    eta / 60,
                    len(bag),
                    failed,
                )

    if verbose:
        elapsed = time.perf_counter() - t0
        _log.info(
            "완료: processed=%d failed=%d unique=%d wall=%.1f min",
            processed,
            failed,
            len(bag),
            elapsed / 60,
        )

    rows = []
    for (rawId, titleCanonical), v in bag.items():
        if len(v["corps"]) < minCorpCount:
            continue
        variants = [t for t, _ in v["titles"].most_common()]
        rows.append(
            {
                "rawId": rawId,
                "rawTitleCanonical": titleCanonical,
                "rawTitleVariants": variants,
                "parentRawId": v["parent"],
                "taxonomyVersion": None,
                "firstSeenPeriod": None,
                "lastSeenPeriod": None,
                "corpCount": len(v["corps"]),
                "periodCount": len(v["rcepts"]),
                "occurrenceCount": int(sum(v["titles"].values())),
                "marketNs": "kr",
            }
        )

    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(
        rows,
        schema_overrides={
            "corpCount": pl.UInt32,
            "periodCount": pl.UInt32,
            "occurrenceCount": pl.UInt32,
        },
    ).sort(["corpCount", "occurrenceCount"], descending=[True, True])


def scanRefBaseline(
    codes: list[str] | None = None,
    *,
    minCorpCount: int = 1,
    verbose: bool = False,
) -> pl.DataFrame:
    """P-S1 검증용 — 5 baseline 종목의 전 기간 zip scan.

    Args:
        codes: 종목코드 list. None = 5 baseline default.
        minCorpCount: P-S1 기본 1 (5 회사 중 1 이상 발견 entry 모두 보기).
        verbose: 진행 로그.

    Returns:
        Layer 1 schema DataFrame. 5 baseline 의 모든 ACLASS entry.

    Examples:
        >>> df = scanRefBaseline(codes=['005930'], minCorpCount=1)
        >>> df.height > 50  # 005930 단일 분기 95 ACLASS × 42 분기 → 다양
        True

    LLM Specifications:
        AntiPatterns:
            - 5 baseline 외 종목 default 추가 금지 — P-S1 의 검증 게이트
              (사용자 사전조사 005930=32 / 035720=48 / 207940=67) 와 일치.
        OutputSchema:
            - polars DataFrame, 11 col.
    """
    if codes is None:
        codes = ["005930", "005380", "035720", "207940", "000660"]
    baseDir = Path(_cfg.dataDir) / "dart" / "original" / "docs"
    allZips: list[Path] = []
    for code in codes:
        codeDir = baseDir / code
        if not codeDir.exists():
            _log.warning("종목 디렉터리 없음: %s", codeDir)
            continue
        zips = sorted(codeDir.glob("*.zip"))
        allZips.extend(zips)
        if verbose:
            _log.info("%s: %d zip", code, len(zips))
    if verbose:
        _log.info("총 %d zip across %d codes", len(allZips), len(codes))
    return scanZipFiles(allZips, minCorpCount=minCorpCount, verbose=verbose)
