"""panel artifact builder entry — 종목별 zip → 회사당 flat 단일 parquet.

zip → XML → walker(손실0/dup0) → horizontalize(무손실 concat) → disclosureKey 부착
→ splitLeafTypes(text/table) (BUILD) → 전 period concat → ``data/dart/panel/{code}.parquet``
(17-col, flat 단일파일 — HF 파일폭발 회피). long 포맷(재료); 수평화·격자는 READ.

period 는 표지 사업연도 종료일 → ``..period.periodFromEnd`` (결산월 무관 12월결산화). 전 XML 중
명시 사업연도 표지를 가진 본문 우선(``_resolvePeriod``) — 첫 sorted XML 첨부 오귀속 가드.
XML 표지 파싱(lxml)은 본 build 층 책임 — core 는 (year, month) 순수 변환만(R2).

LLM Specifications:
    AntiPatterns:
        - 한 종목 빌드 중 다른 종목 zip read 금지 — strict per-corp.
        - period 매핑 시 rcept_no 직접 사용 금지 — 표지 사업연도 종료일 기준.
        - 별도 문서 parquet schema 호환 금지 — 신 17-col PANEL_SCHEMA 단독.
        - contentRaw 태그 strip 금지 — etree.tostring 원본(R4).
        - 회사당 폴더/{period}.parquet 분할 금지 — flat 단일파일 (증분은 period upsert).
    OutputSchema:
        - ``buildPanel(code) -> dict[period, rowCount]``.
        - 출력: ``data/dart/panel/{code}.parquet`` (17-col, flat).
    Prerequisites:
        - data/original/dart/docs/{code}/*.zip (로컬).
        - refDf (panelXbrlRef.parquet 또는 5 baseline scan).
    Freshness:
        - ref table 갱신 후 옛 양식 매핑 재빌드 가능. 증분 online 은 period upsert.
    Dataflow:
        - zip → XML → walker → horizontalize → resolveBatch(disclosureKey) →
          splitLeafTypes → 전 period concat → flat parquet write.
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
from .leafSplit import splitLeafTypes
from .refScan import scanRefBaseline
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
    # 패키지 동봉(git 추적·wheel) — data/ 가 아님. 뼈대는 코드와 함께 버전·공유 (data/ 는 gitignore).
    return Path(__file__).resolve().parent / "refScan" / "panelXbrlRef.parquet"


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


def _resolvePeriod(roots: list, rceptNo: str) -> str:
    """zip 의 전 XML root 중 **명시 사업연도 표지를 가진 본문 우선**으로 period 1회 결정.

    sorted XML 의 첫 XML 은 첨부(감사보고서·내부회계 등, 표지 없음)일 수 있어 ACODE 휴리스틱으로
    분기 오귀속 위험. 따라서 전 root 를 훑어 ``_FISCAL_PERIOD_RE`` 명시 매치(보통 본문 표지)를 1순위로,
    없을 때만 첫 root 의 ACODE+접수월 fallback(``_periodFromXml``).

    Args:
        roots: 파싱 성공 lxml root list (≥1).
        rceptNo: 접수번호 (fallback 연·월).

    Returns:
        "YYYYQn" period 키.

    Raises:
        없음.

    Example:
        >>> _resolvePeriod([bodyRoot, attachRoot], "20240514000001")  # doctest: +SKIP
    """
    for root in roots:
        try:
            bodyText = "".join(root.itertext())[:5000]
        except (TypeError, AttributeError):
            continue
        m = _FISCAL_PERIOD_RE.search(bodyText)
        if m:
            return periodFromEnd(int(m.group(1)), int(m.group(2)))
    return _periodFromXml(roots[0], rceptNo)  # 표지 없음 → 첫 root ACODE fallback


def _xmlsToPeriodRows(
    xmls: list[str],
    rcept: str,
    code: str,
    refDf: pl.DataFrame | None,
    matchThreshold: float,
) -> dict[str, list[dict]]:
    """한 zip(rcept)의 XML 문자열 list → {period: [row]} (zip/bytes/online 공통 walker 코어).

    period 는 전 XML 중 명시 사업연도 표지를 가진 본문 우선(``_resolvePeriod``)으로 1회 결정 → 같은 zip
    의 모든 XML row 에 동일 부착(1 zip = 1 rcept = 1 report = 1 period). walker(손실0/dup0) row 에
    period/corp/rceptNo/disclosureKey(None) 부착. buildPanel(disk)·buildPanelFromStream(online) 둘 다 호출.

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
    roots = []
    for xml in xmls:
        try:
            root = etree.fromstring(xml.encode("utf-8"), parser)
        except (etree.XMLSyntaxError, ValueError):
            continue
        if root is not None:
            roots.append(root)
    if not roots:
        return {}
    period = _resolvePeriod(roots, rcept)  # 본문 표지 우선 (첫 sorted XML 첨부 오귀속 가드)
    periodRows: dict[str, list[dict]] = {}
    for root in roots:
        era = detectSchemaEra(root)
        for row in walkSections(root, era, refDf, matchThreshold=matchThreshold):
            row["period"] = period
            row["corp"] = code
            row["rceptNo"] = rcept
            row["disclosureKey"] = None
            periodRows.setdefault(period, []).append(row)
    return periodRows


def _writeCompanyFile(
    periodRows: dict[str, list[dict]],
    *,
    code: str,
    outBaseDir: Path,
    overwrite: bool,
    merge: bool,
    verbose: bool,
) -> dict[str, int]:
    """{period: [row]} → 회사당 단일 17-col parquet write (flat: ``data/dart/panel/{code}.parquet``).

    HF 파일폭발 회피(92k→~3k 파일) + read 1 open. 포맷은 long(재료) — 수평화는 READ(뼈대변경 재빌드 0).
    각 period 를 horizontalize→resolveBatch→dechunkNotes→splitLeafTypes(text/table) 처리 후
    전 period concat. **merge** 분기: full rebuild(buildPanel)는 clean overwrite, 증분(buildPanelFromStream)은
    기존 파일을 읽어 **이번에 빌드한 period 만 교체**하고 나머지 period 보존(flat 단일파일이라 통째 덮으면
    기존 분기 소실 — period 단위 upsert 로 가드).

    Args:
        periodRows: ``{period: [row dict]}`` 누적 결과.
        code: 종목코드 (로그용).
        outBaseDir: ``data/dart/panel`` 출력 base dir (caller 가 mkdir).
        overwrite: 기존 파일 overwrite 여부 (merge=False 시만 의미 — 존재+not overwrite 면 skip).
        merge: True 면 기존 파일 read 후 이번 period 만 교체(증분 upsert). False 면 통째 write.
        verbose: 진행 로그.

    Returns:
        ``{period: rowCount}`` 이번에 write 한 period 의 row 수.

    Raises:
        없음.

    Example:
        >>> _writeCompanyFile(rows, code="005930", outBaseDir=p, overwrite=True, merge=False, verbose=False)  # doctest: +SKIP
    """
    parts: list[pl.DataFrame] = []
    result: dict[str, int] = {}
    for period, rows in periodRows.items():
        if not rows:
            continue
        # 빌드 입력 = 15-col (leafType 제외 — 병합·분해 후 leafSplit 가 부여).
        df = pl.DataFrame(rows, schema={k: v for k, v in PANEL_SCHEMA.items() if k != "leafType"})
        df = horizontalize(df)
        df = resolveBatch(df, marketNs="kr")  # KR within = native canonicalKey
        df = dechunkNotes(df)  # 미분해 주석 블록 → 항목별 NT_* sub-note (구조무관 분류). 본문+첨부 중복
        # 제거(dedupKeyed)는 BUILD 아님 — READ 정렬(readWide)에서 read-time 처리(재빌드 무관).
        # text/table 분리(확실한 결정론 경계, 무손실) + leafType — 정렬을 같은 타입끼리(표↔표).
        df = splitLeafTypes(df)
        df = df.select(list(PANEL_SCHEMA.keys()))
        # 순서 보존: horizontalize 가 narrative 섹션을 1행(min blockOrder)으로 병합해 split leaf 들이 같은
        # blockOrder 를 상속(순서 소실) → split 후 문서순서(현 행순서, char-parity 0 입증)를 distinct
        # blockOrder 로 재부여. 각 leaf 가 뼈대 위치를 가짐(표↔표·경계 자른 뒤 위치 보존).
        df = df.with_columns(pl.int_range(pl.len(), dtype=pl.UInt32).alias("blockOrder"))
        parts.append(df)
        result[period] = df.height
    if not parts:
        return {}
    outPath = outBaseDir / f"{code}.parquet"
    if outPath.exists() and not overwrite and not merge:
        return result
    outBaseDir.mkdir(parents=True, exist_ok=True)
    full = pl.concat(parts, how="vertical")
    if merge and outPath.exists():
        # 증분 upsert: 기존에서 이번 빌드 period 제거 후 신규로 교체 (나머지 period 보존).
        existing = pl.read_parquet(str(outPath))
        kept = existing.filter(~pl.col("period").is_in(list(result.keys())))
        full = pl.concat([kept, full], how="vertical")
    # 문서순서를 명시 _ord 로 박아 정렬 — blockOrder 는 한 period 내 여러 XML(본문+첨부)서 충돌해
    # leaf 고유키 아님(part 순서를 sort 안정성에 못 맡김). period 별 rows 는 concat 시 이미 문서순서로
    # 인접하므로 global _ord 는 period 내 단조 = 문서순서 → (period,_ord) 고유키로 결정론 정렬.
    full = full.with_row_index("_ord").sort("period", "_ord").drop("_ord")
    # row_group_size 고정 — period 오름차순 정렬이라 최신기는 연속 tail. 다중 row group 으로 써야
    # 런타임 range read(rowStart/rowEnd)가 최신 분기 행만 fetch 한다. 미설정 시 Polars 가 전체를 단일
    # row group 으로 기록 → contentRaw(파일의 99.6%, 단일 컬럼청크) 통째 다운로드(13~16MB)라 주석
    # 글랜스가 콜드 수십 초. 2000 행/그룹 = 최신 8분기 tail ≈ 3~4MB(실측, 13MB→3.6MB). 파일 ~+15%(허용).
    full.write_parquet(str(outPath), compression="zstd", row_group_size=2000)
    if verbose:
        _log.info("  %s: %d period, %d row → %s", code, len(result), full.height, outPath.name)
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
    """종목별 panel artifact 빌드 — zip → 회사당 flat 17-col parquet (full rebuild, clean overwrite).

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
        - 한 종목의 전 기간 공시를 17-col flat panel artifact 로 — 손실0/dup0/태그무손실.

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
            - 회사당 폴더/{period}.parquet 분할 금지 — flat 단일 {code}.parquet.
            - contentRaw 태그 strip 금지 (R4).
        OutputSchema:
            - ``dict[str, int]`` + 부수효과 data/dart/panel/{code}.parquet (17-col flat).
        Prerequisites:
            - 로컬 zip + refDf (또는 baseline scan).
        Freshness:
            - ref/zip 갱신 시 재빌드.
        Dataflow:
            - zip → walker → horizontalize → resolveBatch → splitLeafTypes → concat → write.
        TargetMarkets:
            - KR (DART).
    """
    if outBaseDir is None:
        outBaseDir = Path(_cfg.dataDir) / "dart" / "panel"
    outBaseDir = Path(outBaseDir)  # flat: data/dart/panel/{code}.parquet (per-company 폴더 없음)

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

    # full rebuild — 전 zip 처리라 모든 period 보유 → clean overwrite (merge=False).
    return _writeCompanyFile(
        periodRows, code=code, outBaseDir=outBaseDir, overwrite=overwrite, merge=False, verbose=verbose
    )


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
    """online 1패스 — (rcept, zipBytes) 스트림 → flat 17-col parquet (period upsert). 디스크 zip 0.

    ``buildPanel`` 의 메모리 쌍둥이 — 로컬 zip 대신 DART API 가 흘리는 zip bytes 를 받아 동일
    코어(``_readZipBytes`` → ``_xmlsToPeriodRows`` → ``_writeCompanyFile``)로 17-col artifact
    생산. 산출물은 ``buildPanel`` 과 row 동형(같은 walker/horizontalize/resolveBatch/splitLeafTypes/zstd),
    입력원만 stream. **증분**이라 ``_writeCompanyFile(merge=True)`` — 기존 {code}.parquet 을 읽어 이번
    분기 period 만 교체(나머지 보존, flat 단일파일 소실 가드). ``data/original/dart/docs`` 에 zip 을 만들지
    않음 → refScan 불가라 refDf 필수 (online 은 HF seed ``panelXbrlRef.parquet`` 강제 주입, 자동 scan 금지).

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
        - ``_readZipBytes`` / ``_xmlsToPeriodRows`` / ``_writeCompanyFile`` — 공유 코어.
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
            - 증분 시 통째 overwrite 금지 — period upsert(merge=True) 로 기존 분기 보존.
        OutputSchema:
            - ``dict[str, int]`` + 부수효과 data/dart/panel/{code}.parquet (17-col flat, period upsert).
        Prerequisites:
            - refDf (HF seed). docStream (providers streamZipBytes).
        Freshness:
            - 분기 incremental — 신규 rcept 만.
        Dataflow:
            - docStream → _readZipBytes → _xmlsToPeriodRows → _writeCompanyFile(merge) → parquet.
        TargetMarkets:
            - KR (DART).
    """
    if refDf is None:
        raise ValueError(
            "buildPanelFromStream: refDf 필수 — online 1패스는 zip 부재로 자동 scanRefBaseline 금지 (HF seed panelXbrlRef 주입)."
        )

    if outBaseDir is None:
        outBaseDir = Path(_cfg.dataDir) / "dart" / "panel"
    outBaseDir = Path(outBaseDir)  # flat: {code}.parquet

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

    # 증분 online — stream 은 신규 분기만 → 기존 파일 read 후 이번 period 만 교체 (merge=True).
    return _writeCompanyFile(
        periodRows, code=code, outBaseDir=outBaseDir, overwrite=overwrite, merge=True, verbose=verbose
    )


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
