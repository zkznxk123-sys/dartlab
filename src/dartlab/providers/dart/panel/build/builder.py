"""panel artifact builder entry — 종목별 zip → period sharded parquet.

zip → XML → walker(손실0/dup0) → horizontalize(무손실 concat) → disclosureKey 부착
(BUILD) → period 별 group → ``data/dart/panel/{code}/{period}.parquet`` (panel SSOT).

period 는 표지 사업연도 종료일 → ``..period.periodFromEnd`` (결산월 무관 12월결산화).
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
        - data/original/dart/docs/{code}/*.zip (로컬).
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

import io
import logging
import re
import zipfile
from collections.abc import Iterable
from pathlib import Path

import polars as pl
from lxml import etree

import dartlab.config as _cfg

from ..mapper import resolveBatch
from ..period import periodFromEnd
from ..schema import PANEL_SCHEMA
from .dechunkNotes import dechunkNotes
from .horizontalize import horizontalize
from .refScan import scanRefBaseline
from .signature import simhash
from .walker import detectSchemaEra, walkSections

_log = logging.getLogger(__name__)

_RCEPT_RE = re.compile(r"^(\d{14})\.zip$", re.IGNORECASE)


def panelXbrlRefPath() -> "Path":
    """panelXbrlRef ref table 경로 — refScan 산출 + build(v1 fuzzy) 입력 SSOT.

    Args:
        없음.

    Returns:
        ``data/dart/panelXbrlRef.parquet`` Path.

    Raises:
        없음.

    Example:
        >>> panelXbrlRefPath().name
        'panelXbrlRef.parquet'

    SeeAlso:
        - ``refScan.scanAllZips`` — 본 경로 생산.
        - ``buildPanelAll`` — 본 ref 로 옛 양식(v1) fuzzy 매칭.

    Requires:
        - dartlab.config.

    Capabilities:
        - ref truth 단일 경로 — refScan write·build read 공유 (build 가 ref 경로 SSOT 소유).

    Guide:
        - refScan 후 build(v1 fuzzy)·online sync entry 가 본 경로 참조.

    AIContext:
        - 경로 계산만 — 부작용 0.

    LLM Specifications:
        AntiPatterns:
            - 경로 분산 하드코딩 금지 — 본 함수 단일.
        OutputSchema:
            - ``pathlib.Path``.
        Prerequisites:
            - config.dataDir.
        Freshness:
            - 정적.
        Dataflow:
            - config.dataDir → data/dart/panelXbrlRef.parquet.
        TargetMarkets:
            - KR (DART).
    """
    return Path(_cfg.dataDir) / "dart" / "panelXbrlRef.parquet"


# 표지 "사업연도 YYYY년 MM월 DD일 부터 YYYY년 MM월 DD일 까지" — 종료(year, month) 추출.
_FISCAL_PERIOD_RE = re.compile(
    r"사업연도\s+\d{4}\s*년\s+\d{1,2}\s*월\s+\d{1,2}\s*일\s+부터\s+(\d{4})\s*년\s+(\d{1,2})\s*월\s+\d{1,2}\s*일"
)


def _zipToXmls(zf: zipfile.ZipFile) -> list[str]:
    """열린 ZipFile → 모든 .xml 의 decoded 문자열 list (입력원 무관 공유 코어).

    DART zip 의 모든 XML — 사업보고서(Q4) 첨부 양식(감사보고서·내부회계관리제도 등)도 포함.
    declaration encoding 거짓말(옛 양식 utf-8 선언이나 실제 cp949) 회피 (_decodeXmlBytes trial).

    Args:
        zf: 열린 ``zipfile.ZipFile`` (Path/BytesIO 무관).

    Returns:
        sorted .xml name 순서의 decoded XML 문자열 list.

    Raises:
        없음 — caller(_readZip/_readZipBytes)가 BadZipFile/OSError/KeyError 흡수.

    Example:
        >>> with zipfile.ZipFile(p) as zf: _zipToXmls(zf)  # doctest: +SKIP
    """
    from .refScan.zipScanWorker import _decodeXmlBytes

    xmls: list[str] = []
    names = sorted(n for n in zf.namelist() if n.lower().endswith(".xml"))
    for n in names:
        with zf.open(n) as f:
            raw = f.read()
        xmls.append(_decodeXmlBytes(raw))
    return xmls


def _readZip(zp: Path) -> tuple[str | None, list[str]]:
    """로컬 zip 파일 경로 → (rcept_no, [xml strings]). (A) 디스크 트랙.

    Args:
        zp: zip 파일 경로.

    Returns:
        ``(rcept_no, [xml str])``. read 실패 시 ``(None, [])``.

    Raises:
        없음 — BadZipFile/OSError/KeyError 흡수.

    Example:
        >>> _readZip(Path("data/original/dart/docs/005930/...zip"))  # doctest: +SKIP
    """
    m = _RCEPT_RE.match(zp.name)
    rcept = m.group(1) if m else zp.stem
    try:
        with zipfile.ZipFile(zp) as zf:
            xmls = _zipToXmls(zf)
    except (zipfile.BadZipFile, OSError, KeyError) as exc:
        _log.warning("zip read 실패 %s: %s", zp, exc)
        return (None, [])
    return (rcept, xmls)


def _readZipBytes(raw: bytes, rcept: str) -> tuple[str | None, list[str]]:
    """zip bytes(메모리) → (rcept_no, [xml strings]). (B) online 1패스 트랙 — 디스크 0.

    ``_readZip``(Path)의 bytes 쌍둥이 — ``zipfile.ZipFile(io.BytesIO(raw))`` 로 디스크 저장 없이
    동일 ``_zipToXmls`` 코어 호출. online (DART API → 메모리 zip) 경로 전용.

    Args:
        raw: DART document.xml API 가 반환한 zip bytes.
        rcept: 접수번호 (provenance — bytes 엔 파일명 없음).

    Returns:
        ``(rcept, [xml str])``. read 실패 시 ``(None, [])``.

    Raises:
        없음 — BadZipFile/OSError/KeyError 흡수.

    Example:
        >>> _readZipBytes(zipBytes, "20240514000001")  # doctest: +SKIP
    """
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            xmls = _zipToXmls(zf)
    except (zipfile.BadZipFile, OSError, KeyError) as exc:
        _log.warning("zip bytes read 실패 %s: %s", rcept, exc)
        return (None, [])
    return (rcept, xmls)


def _periodFromXml(root, rceptNo: str) -> str:
    """XML 표지의 "사업연도" 종료일 → calendar quarter (..period.periodFromEnd).

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


def _xmlsToPeriodRows(
    xmls: list[str],
    rcept: str,
    code: str,
    refDf: pl.DataFrame | None,
    matchThreshold: float,
) -> dict[str, list[dict]]:
    """한 zip(rcept)의 XML 문자열 list → {period: [row]} (zip/bytes/online 공통 walker 코어).

    period 는 첫 파싱 성공 XML 의 표지 사업연도 종료일로 1회 결정 → 같은 zip 의 모든 XML row 에
    동일 부착(1 zip = 1 rcept = 1 report = 1 period). walker(손실0/dup0) row 에 period/corp/
    rceptNo/disclosureKey(None) 부착. buildPanel(disk)·buildPanelFromStream(online) 둘 다 호출.

    Args:
        xmls: 한 zip 의 decoded XML 문자열 list.
        rcept: 접수번호.
        code: 종목코드.
        refDf: 옛 양식(v1) fuzzy 매칭 ref table.
        matchThreshold: fuzzy Jaccard threshold.

    Returns:
        ``{period: [row dict]}``. 파싱 가능한 XML 0 이면 빈 dict.

    Raises:
        없음 — XML 파싱 실패 XML 은 skip.

    Example:
        >>> _xmlsToPeriodRows(xmls, "20240514000001", "005930", ref, 0.70)  # doctest: +SKIP
    """
    parser = etree.XMLParser(recover=True, huge_tree=True)
    periodRows: dict[str, list[dict]] = {}
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
    return periodRows


def _writePeriodShards(
    periodRows: dict[str, list[dict]],
    *,
    code: str,
    outDir: Path,
    overwrite: bool,
    verbose: bool,
) -> dict[str, int]:
    """{period: [row]} → period 별 14-col parquet write (disk/online 공통 write 코어).

    horizontalize(무손실 concat) → resolveBatch(disclosureKey 부착) → 14-col select → zstd write.
    buildPanel·buildPanelFromStream 의 동일 write 단계.

    Args:
        periodRows: ``{period: [row dict]}`` 누적 결과.
        code: 종목코드 (로그용).
        outDir: ``data/dart/panel/{code}`` 출력 디렉터리 (caller 가 mkdir).
        overwrite: 기존 period parquet overwrite 여부.
        verbose: 진행 로그.

    Returns:
        ``{period: rowCount}`` write 결과.

    Raises:
        없음.

    Example:
        >>> _writePeriodShards(rows, code="005930", outDir=p, overwrite=True, verbose=False)  # doctest: +SKIP
    """
    result: dict[str, int] = {}
    for period, rows in periodRows.items():
        if not rows:
            continue
        # 빌드 입력 = 15-col (contentSig 제외 — horizontalize 병합 + dechunkNotes 분해 후 최종 contentRaw 에 계산).
        df = pl.DataFrame(rows, schema={k: v for k, v in PANEL_SCHEMA.items() if k != "contentSig"})
        df = horizontalize(df)
        df = resolveBatch(df, marketNs="kr")  # KR within = native canonicalKey
        df = dechunkNotes(df)  # 미분해 주석 블록 → 항목별 NT_* sub-note (구조무관 분류). 본문+첨부 중복
        # 제거(dedupKeyed)는 BUILD 아님 — READ 정렬(readWide)에서 read-time 처리(재빌드 무관).
        # contentSig = 병합·분해 완료된 최종 leaf contentRaw 의 SimHash (READ 서사구조 수평화 정렬 앵커, per-leaf 결정론).
        df = df.with_columns(pl.col("contentRaw").map_elements(simhash, return_dtype=pl.UInt64).alias("contentSig"))
        df = df.select(list(PANEL_SCHEMA.keys()))
        outPath = outDir / f"{period}.parquet"
        if outPath.exists() and not overwrite:
            continue
        df.write_parquet(str(outPath), compression="zstd")
        result[period] = df.height
        if verbose:
            _log.info("  %s %s: %d row", code, period, df.height)
    return result


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
        - ``..mapper.resolveBatch`` — disclosureKey(=native canonicalKey) 부착.

    Requires:
        - data/original/dart/docs/{code}/*.zip. polars. lxml.

    Capabilities:
        - 한 종목의 전 기간 공시를 14-col panel artifact 로 — 손실0/dup0/태그무손실.

    Guide:
        - 운영자/CI build-time 호출. runtime read 는 providers/dart/panel.

    AIContext:
        - strict per-corp 빌드 — 다른 종목 zip 미접근.

    When:
        - 운영자/CI 가 한 종목의 panel artifact 를 (재)생산할 때.

    How:
        - 로컬 zip → walker → horizontalize → resolveBatch → period 별 parquet write.

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

    zipDir = Path(_cfg.dataDir) / "original" / "dart" / "docs" / code
    if not zipDir.exists():
        _log.warning("zip dir 없음: %s", zipDir)
        return {}

    periodRows: dict[str, list[dict]] = {}
    for zp in sorted(zipDir.glob("*.zip")):
        rcept, xmls = _readZip(zp)
        if not xmls or not rcept:
            continue
        for period, rows in _xmlsToPeriodRows(xmls, rcept, code, refDf, matchThreshold).items():
            periodRows.setdefault(period, []).extend(rows)

    return _writePeriodShards(periodRows, code=code, outDir=outDir, overwrite=overwrite, verbose=verbose)


def buildPanelFromStream(
    code: str,
    docStream: Iterable[tuple[str, bytes]],
    *,
    refDf: pl.DataFrame | None = None,
    matchThreshold: float = 0.70,
    outBaseDir: Path | str | None = None,
    overwrite: bool = True,
    verbose: bool = False,
) -> dict[str, int]:
    """online 1패스 — (rcept, zipBytes) 스트림 → period sharded 14-col parquet. 디스크 zip 0.

    ``buildPanel`` 의 메모리 쌍둥이 — 로컬 zip 대신 DART API 가 흘리는 zip bytes 를 받아 동일
    코어(``_readZipBytes`` → ``_xmlsToPeriodRows`` → ``_writePeriodShards``)로 14-col artifact
    생산. 산출물은 ``buildPanel`` 과 바이트 동형(같은 walker/horizontalize/resolveBatch/zstd),
    입력원만 stream. ``data/original/dart/docs`` 에 zip 을 만들지 않음 → refScan 불가라 refDf 필수
    (online 은 HF seed ``panelXbrlRef.parquet`` 를 강제 주입, 자동 scanRefBaseline 금지).

    Args:
        code: 종목코드 (예 "005930").
        docStream: ``(rceptNo, zipBytes)`` iterable — providers ``streamZipBytes`` 산출(메모리).
        refDf: panelXbrlRef ref table. **None 이면 ValueError** (online 엔 zip 없어 자동 scan 불가).
        matchThreshold: 옛 양식 fuzzy Jaccard threshold (검증 0.70).
        outBaseDir: 출력 base dir. None = ``data/dart/panel``.
        overwrite: 기존 period parquet overwrite 여부.
        verbose: 진행 로그.

    Returns:
        ``{period: rowCount}`` dict. stream 빈/전부 실패 시 빈 dict.

    Raises:
        ValueError: ``refDf is None`` (online 1패스는 ref 자동 scan 금지 — HF seed 필수).

    Example:
        >>> from dartlab.providers.dart.openapi import DartClient, streamZipBytes  # doctest: +SKIP
        >>> stream = ((r, b) for _, r, b in streamZipBytes(DartClient(), [("005930", rcept)]))  # doctest: +SKIP
        >>> buildPanelFromStream("005930", stream, refDf=ref)  # doctest: +SKIP
        {'2025Q1': 142}

    SeeAlso:
        - ``buildPanel`` — 로컬 zip(A) 디스크 트랙 쌍둥이.
        - ``_readZipBytes`` / ``_xmlsToPeriodRows`` / ``_writePeriodShards`` — 공유 코어.
        - ``providers.dart.openapi.streamZipBytes`` — (rcept, bytes) 스트림 생산.

    Requires:
        - polars. lxml. refDf (HF seed panelXbrlRef). providers streamZipBytes (호출측).

    Capabilities:
        - 신규 분기를 zip 디스크 저장 없이 즉시 panel artifact 화 (증분 online sync 트랙).

    Guide:
        - layer-밖 sync entry(`.github/scripts/sync/onlinePanel.py`)가 providers fetch 와 조합 호출.
          gather↛providers(R1) 라 gather 내부에서 fetch 금지 — bytes 만 받음.

    AIContext:
        - strict per-corp (한 종목 stream 만). bytes 는 즉시 소비 후 폐기 (메모리 bounded).

    When:
        - CI online sync 가 신규/변경 분기를 zip 없이 panel 화할 때.

    How:
        - docStream 각 (rcept,bytes) → _readZipBytes → _xmlsToPeriodRows 누적 → _writePeriodShards.

    LLM Specifications:
        AntiPatterns:
            - refDf None 시 scanRefBaseline 자동 호출 금지 — online 엔 zip 없음(ValueError).
            - 전 종목 stream 한 번에 모으기 금지 — 종목 단위 호출(bytes 메모리 폭주 가드).
            - zip 디스크 저장 금지 — 메모리 1패스 (data/original/dart/docs 안 만듦).
        OutputSchema:
            - ``dict[str, int]`` + 부수효과 data/dart/panel/{code}/{period}.parquet.
        Prerequisites:
            - refDf (HF seed). docStream (providers streamZipBytes).
        Freshness:
            - 분기 incremental — 신규 rcept 만.
        Dataflow:
            - docStream → _readZipBytes → _xmlsToPeriodRows → _writePeriodShards → parquet.
        TargetMarkets:
            - KR (DART).
    """
    if refDf is None:
        raise ValueError(
            "buildPanelFromStream: refDf 필수 — online 1패스는 zip 부재로 자동 scanRefBaseline 금지 (HF seed panelXbrlRef 주입)."
        )

    if outBaseDir is None:
        outBaseDir = Path(_cfg.dataDir) / "dart" / "panel"
    outDir = Path(outBaseDir) / code
    outDir.mkdir(parents=True, exist_ok=True)

    # 가속: refMatcher token set pre-compute (worker init 후 이미 done 이면 skip).
    from .refScan.refMatcher import _REF_TOKENS as _existing
    from .refScan.refMatcher import precomputeRefTokens, setGlobalRefTokens

    if _existing is None:
        setGlobalRefTokens(precomputeRefTokens(refDf))

    periodRows: dict[str, list[dict]] = {}
    for rcept, raw in docStream:
        r2, xmls = _readZipBytes(raw, rcept)
        if not xmls or not r2:
            continue
        for period, rows in _xmlsToPeriodRows(xmls, r2, code, refDf, matchThreshold).items():
            periodRows.setdefault(period, []).extend(rows)

    return _writePeriodShards(periodRows, code=code, outDir=outDir, overwrite=overwrite, verbose=verbose)


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
        - CLI ``python -m dartlab.providers.dart.panel.build`` 기본 경로.

    AIContext:
        - 단일 process — debug 용이.

    When:
        - 5 baseline 손실0/dup0 검증·디버그 시.

    How:
        - scanRefBaseline ref 로 종목별 buildPanel 순차 호출 → 중첩 dict.

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
