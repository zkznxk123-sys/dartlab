"""panel 셀 세분화 build — 재무 5표 native XBRL `<TE ACODE ACONTEXT>` → 셀 행 (lxml, build 서브트리).

정부가 재무·주석 표의 모든 숫자에 박은 `<TE ACODE="ifrs-full_Revenue" ACONTEXT="CFY2025dFY_..._
ConsolidatedMember">333,605,938</TE>` 를 재무 5표(BS/IS/CIS/CF/SCE)에 한해 셀 단위로 분해 →
``data/dart/panelCell/{code}/{period}.parquet`` (13-col CELL_SCHEMA). 메인 14-col buildPanel 경로는
**literally 미수정** — 셀은 독립 평행 artifact (wide 정체성 불가침). ACONTEXT 는 2025-03 사업보고서부터만
박히므로(실측) 그 이전 period 는 셀 0 → 파일 미생성 (graceful 저하).

저장 원칙: ACONTEXT 분해(ctxYear/ctxFlow/ctxScope/axisPath)·acode·label 은 정부 truth 위 결정론적
순수 규칙이라 build 에서 굽고, freq(분기/연도) 선택은 표현이라 read(``..cell.readCellWide``). valueRaw 는
콤마·괄호 그대로 무손실.

LLM Specifications:
    AntiPatterns:
        - valueRaw 숫자화(콤마/괄호 제거) build 금지 — 불변 원본, 파싱은 read.
        - 5표 외(NT_* 주석) 셀화 금지 — canonicalKey 필터 (확정 범위).
        - buildPanel(메인 14-col) 수정 금지 — 독립 평행 함수.
    OutputSchema:
        - ``buildPanelCells(code) -> dict[period, cellRowCount]``.
        - 출력: ``data/dart/panelCell/{code}/{period}.parquet`` (13-col).
    Prerequisites:
        - data/dart/original/docs/{code}/*.zip (로컬). lxml.
    Freshness:
        - ACONTEXT 양식 변경 시 decodeAcontext + cellSchema 동시 정합.
    Dataflow:
        - zip → XML → iterTableGroups(5표) → TR/TE → decodeAcontext → 13-col parquet.
    TargetMarkets:
        - KR (DART). ACONTEXT 2025-03+.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from pathlib import Path

import polars as pl
from lxml import etree

import dartlab.config as _cfg

from ..cellSchema import CELL_SCHEMA
from ..mapper import canonicalKey
from .builder import _periodFromXml, _readZip
from .refScan.aclassExtractor import iterTableGroups

_log = logging.getLogger(__name__)

# 재무 5표 statement (canonicalKey(ACLASS)). SCE(자본변동표)=EF, CIS(포괄손익)=IS3 (ACLASS 실측).
CELL_STATEMENTS: frozenset[str] = frozenset({"BS", "IS2", "IS3", "CF", "EF"})

# ACONTEXT period 토큰: prefix(당기/전기/전전기) + FY + 4자리연도 + 흐름/시점(d|e) + marker.
# marker = FY(연간) / FQ?(1분기) / HY?(반기·2분기) / TQ?(3분기), 접미 A(누적)·Q(단독)·∅(시점).
_PERIOD_RE = re.compile(r"^(BP|P|C)FY(\d{4})([de])(FY|FQA|FQQ|FQ|HYA|HYQ|HY|TQA|TQQ|TQ)$")
_AXIS_PREFIXES = ("ifrs-full", "dart")

# marker base(접미 제거) → 분기번호. FY=연간(4분기). FQ=1·HY=2(반기)·TQ=3.
_MARKER_QUARTER = {"FY": 4, "FQ": 1, "HY": 2, "TQ": 3}


def _markerToQuarterMode(marker: str) -> tuple[int, str]:
    """period marker → (ctxQuarter, ctxMode). FY=연간, 접미 A=누적·Q=단독·∅=시점bare.

    Examples:
        >>> _markerToQuarterMode("FY")
        (4, 'Y')
        >>> _markerToQuarterMode("FQA")
        (1, 'A')
        >>> _markerToQuarterMode("TQQ")
        (3, 'Q')
        >>> _markerToQuarterMode("HY")
        (2, 'P')
    """
    if marker == "FY":
        return (4, "Y")
    base = marker[:2]  # FQ/HY/TQ (항상 2글자)
    suffix = marker[2:]  # "", "A"(누적), "Q"(단독)
    mode = suffix if suffix in ("A", "Q") else "P"
    return (_MARKER_QUARTER[base], mode)


def _axisMembers(segs: list[str]) -> list[str]:
    """ACONTEXT 의 axis 부분 토큰 list → Member 로 끝나는 토큰만 (axis 드롭, 멤버 보존).

    토큰은 ``_`` 로 잘려 들어오므로 ``ifrs-full``/``dart``/``entity`` prefix 로 재조합 후
    ``Member`` 접미만 남긴다 (``...Axis`` 는 멤버에 1:1 종속이라 멤버가 정체성).

    Args:
        segs: ACONTEXT 를 ``_`` split 한 뒤 period 토큰 제외한 나머지 segment list.

    Returns:
        Member 토큰 list (예: ``["ConsolidatedMember", "RetainedEarningsMember"]``).

    표준 ``ifrs-full_``/``dart_`` prefix 는 벗기고(가독), 회사 네임스페이스 ``entity...`` 는 보존.

    Examples:
        >>> _axisMembers(["ifrs-full", "ConsolidatedAndSeparateFinancialStatementsAxis",
        ...               "ifrs-full", "ConsolidatedMember"])
        ['ConsolidatedMember']
    """
    tokens: list[str] = []
    buf: list[str] = []
    for s in segs:
        if s in _AXIS_PREFIXES or s.startswith("entity"):
            if buf:
                tokens.append("_".join(buf))
            buf = [s]
        else:
            buf.append(s)
    if buf:
        tokens.append("_".join(buf))
    members = [t for t in tokens if t.endswith("Member")]
    return [
        m[len("ifrs-full_") :] if m.startswith("ifrs-full_") else m[len("dart_") :] if m.startswith("dart_") else m
        for m in members
    ]


def decodeAcontext(ctx: str) -> tuple[int, str, int, str, str] | None:
    """ACONTEXT attribute → (ctxYear, ctxFlow, ctxQuarter, ctxMode, axisPath) 결정론적 분해.

    period 토큰 ``(C|P|BP)FY{year}{d|e}{marker}`` 를 regex 로 분해하고(marker→분기·모드), 나머지
    axis/member 쌍에서 Member 만 ``|`` join. (``tests/_attempts/panelCellFeasibility.py::_decodeContext``
    의 시도 로직을 정식 본체화 + 전 분기 토큰(FQ/HY/TQ/FY) 포착 — 우회 아님.)

    Args:
        ctx: TE 의 ACONTEXT attribute (예 ``"CFY2025dFY_ifrs-full_...Axis_ifrs-full_ConsolidatedMember"``).

    Returns:
        ``(ctxYear, ctxFlow, ctxQuarter, ctxMode, axisPath)`` — ctxYear=실연도(int), ctxFlow="d"|"e",
        ctxQuarter=1/2/3/4, ctxMode="Y"(연간)|"A"(누적)|"Q"(단독)|"P"(시점bare), axisPath=멤버 ``|``
        join. period 토큰 미매칭 시 None.

    Examples:
        >>> decodeAcontext("CFY2025dFY_ifrs-full_X_ifrs-full_ConsolidatedMember")
        (2025, 'd', 4, 'Y', 'ConsolidatedMember')
        >>> decodeAcontext("BPFY2023eFY_ifrs-full_X_ifrs-full_ConsolidatedMember")
        (2023, 'e', 4, 'Y', 'ConsolidatedMember')
        >>> decodeAcontext("CFY2025dTQA_ifrs-full_X_ifrs-full_ConsolidatedMember")
        (2025, 'd', 3, 'A', 'ConsolidatedMember')
        >>> decodeAcontext("CFY2025dFQQ_ifrs-full_X_ifrs-full_ConsolidatedMember")
        (2025, 'd', 1, 'Q', 'ConsolidatedMember')
        >>> decodeAcontext("garbage") is None
        True

    Raises:
        없음 — 미매칭은 None.

    SeeAlso:
        - ``iterCellRows`` — 본 분해를 TE 마다 호출.
        - ``..cell.readCellWide`` — 분해 결과 컬럼(ctxFlow/ctxQuarter/ctxMode)으로 freq 선택.

    Requires:
        - 없음 (순수 문자열). lxml 무관.

    Capabilities:
        - 정부 기간 문법을 산수 0 으로 (당기/전기/전전기 × 흐름/시점 × 연간/분기 누적·단독·시점).

    Guide:
        - build/cell 내부 호출. read 는 분해 결과 컬럼만 보고 본 함수 미호출(R2).

    AIContext:
        - 결정론 분해 — 005930 전 ACONTEXT 필링(FQ/HY/TQ/FY) 전건 매칭 실측.

    When:
        - TE 셀의 ACONTEXT 를 (연도, 흐름/시점, 분기, 모드, 축경로)로 풀 때.

    How:
        - ``_`` split → period 토큰 regex → marker→(분기,모드) → 나머지 _axisMembers.

    LLM Specifications:
        AntiPatterns:
            - period 토큰 빼기 산수 금지 — 정부가 단독/누적/연간 다 박음, 토큰만 읽음.
            - 분기 토큰 일부(FQ/HY)만 포착 금지 — 전 분기 marker 전수.
        OutputSchema:
            - ``tuple[int, str, int, str, str] | None``.
        Prerequisites:
            - 없음.
        Freshness:
            - 양식 변경 시 _PERIOD_RE/_MARKER_QUARTER 재검증.
        Dataflow:
            - ctx → split → regex → (year, flow, quarter, mode) + members.
        TargetMarkets:
            - KR (DART).
    """
    if not ctx:
        return None
    parts = ctx.split("_")
    m = _PERIOD_RE.match(parts[0])
    if m is None:
        return None
    ctxYear = int(m.group(2))
    ctxFlow = m.group(3)
    ctxQuarter, ctxMode = _markerToQuarterMode(m.group(4))
    axisPath = "|".join(_axisMembers(parts[1:]))
    return (ctxYear, ctxFlow, ctxQuarter, ctxMode, axisPath)


def _teText(te) -> str:
    """TE element 의 inner text (태그 제거) — valueRaw/label 용. 콤마·괄호 보존.

    Args:
        te: TE lxml element.

    Returns:
        itertext concat strip (예 ``"333,605,938"``, ``"(1,234)"``, ``"매출액 (주30)"``).
    """
    return "".join(te.itertext()).strip()  # noqa: E501  # element.itertext OK


def _rowLabel(tes: list) -> str:
    """같은 TR 의 첫 ACODE-없는 TE 한글 라벨 (value 셀과 100% 동거 실측).

    Args:
        tes: 한 TR 의 TE element list.

    Returns:
        첫 ACODE-없는 TE 의 text. 없으면 "".
    """
    for te in tes:
        if not (te.get("ACODE", "") or "").strip():
            txt = _teText(te)
            if txt:
                return txt
    return ""


def iterCellRows(root, *, period: str, code: str, rcept: str) -> Iterator[dict]:
    """본문 XML root → 재무 5표 셀 행 (13-col CELL_SCHEMA dict) iter.

    ``iterTableGroups`` 로 TABLE-GROUP 열거 → ``canonicalKey(ACLASS) in CELL_STATEMENTS`` 만(NT_*
    자동 제외) → TR 별 첫 ACODE-없는 TE=label, ACONTEXT TE=value 셀. ctx 0 표(2025-03 이전)는
    자연히 0 행 emit.

    Args:
        root: lxml 본문 root.
        period: 보고서 period (YYYYQn, ``_periodFromXml`` 결과).
        code: 종목코드.
        rcept: 접수번호.

    Yields:
        CELL_SCHEMA 13-col dict (corp/rceptNo/filingPeriod/statement/scope/acode/label/
        ctxYear/ctxFlow/ctxScope/axisPath/valueRaw/cellOrder).

    Raises:
        없음 — 분해 실패 TE skip.

    Example:
        >>> for row in iterCellRows(root, period="2025Q4", code="005930", rcept="2026..."):  # doctest: +SKIP
        ...     pass

    SeeAlso:
        - ``..build.refScan.aclassExtractor.iterTableGroups`` — TABLE-GROUP 열거 (재사용).
        - ``decodeAcontext`` — ACONTEXT 분해.
        - ``..mapper.canonicalKey`` — ACLASS → statement.

    Requires:
        - lxml root.

    Capabilities:
        - 5표 표 셀을 native 라벨(추측 0)로 (개념, 기간, 축, 값) 행화 + 한글 라벨 동거.

    Guide:
        - buildPanelCells 내부 호출. 주석(NT_*)은 canonicalKey 필터로 제외.

    AIContext:
        - 순수 추출 — tree 변경 0.

    When:
        - 5표 셀을 artifact 행으로 추출할 때.

    How:
        - iterTableGroups → 5표 필터 → TR/TE → decodeAcontext → dict.

    LLM Specifications:
        AntiPatterns:
            - NT_* 주석 셀화 금지 (확정 범위). value 숫자화 금지(read).
        OutputSchema:
            - ``Iterator[dict]`` (13-col).
        Prerequisites:
            - lxml root.
        Freshness:
            - 양식 변경 시 CELL_STATEMENTS/decodeAcontext 재검증.
        Dataflow:
            - root → TABLE-GROUP(5표) → TR/TE → cell dict.
        TargetMarkets:
            - KR (DART).
    """
    for tg, _parent in iterTableGroups(root):
        rawAclass = (tg.get("ACLASS", "") or "").strip()
        statement = canonicalKey(rawAclass)
        if statement not in CELL_STATEMENTS:
            continue
        scope = "standalone" if "_S" in rawAclass.replace("{XBRL}", "") else "consolidated"
        order = 0
        for tr in tg.iter("TR"):
            tes = list(tr.iter("TE"))
            if not tes:
                continue
            label = _rowLabel(tes)
            for te in tes:
                actx = (te.get("ACONTEXT", "") or "").strip()
                acode = (te.get("ACODE", "") or "").strip()
                if not actx or not acode:
                    continue
                decoded = decodeAcontext(actx)
                if decoded is None:
                    continue
                ctxYear, ctxFlow, ctxQuarter, ctxMode, axisPath = decoded
                yield {
                    "corp": code,
                    "rceptNo": rcept,
                    "filingPeriod": period,
                    "statement": statement,
                    "scope": scope,
                    "acode": acode,
                    "label": label,
                    "ctxYear": ctxYear,
                    "ctxFlow": ctxFlow,
                    "ctxQuarter": ctxQuarter,
                    "ctxMode": ctxMode,
                    "axisPath": axisPath,
                    "valueRaw": _teText(te),
                    "cellOrder": order,
                }
                order += 1


def buildPanelCells(
    code: str,
    *,
    outBaseDir: Path | str | None = None,
    overwrite: bool = True,
    verbose: bool = False,
) -> dict[str, int]:
    """종목별 셀 artifact 빌드 — zip → 5표 셀 → period sharded 13-col parquet (독립 평행).

    메인 buildPanel(14-col)과 별개로 자체 zip 루프. ctx TE 0 인 period(2025-03 이전)는 셀 0 → 파일
    미생성. refDf 불요 (셀은 ACLASS 정확한 신양식만 존재).

    Args:
        code: 종목코드.
        outBaseDir: 출력 base dir. None = ``data/dart/panelCell``.
        overwrite: 기존 period parquet overwrite.
        verbose: 진행 로그.

    Returns:
        ``{period: cellRowCount}`` (셀 있는 period 만). zip dir 부재 시 빈 dict.

    Raises:
        없음 — zip/XML 실패 skip.

    Example:
        >>> buildPanelCells("005930", verbose=True)  # doctest: +SKIP
        {'2025Q4': 663, '2025Q3': ...}

    SeeAlso:
        - ``buildPanel`` — 메인 14-col (본 함수가 미수정으로 보존).
        - ``..cell.readCellWide`` — 본 artifact 소비 (freq).

    Requires:
        - data/dart/original/docs/{code}/*.zip. polars. lxml.

    Capabilities:
        - 한 종목 5표를 native 셀 artifact 로 — 추측 0, 메인 wide 무손상.

    Guide:
        - 운영자/CI build-time. ``python -X utf8 -m ...build --cells --codes 005930``.

    AIContext:
        - strict per-corp. 독립 파스(메인 경로 literally 미수정 보장).

    When:
        - 5표 셀 artifact 를 (재)생산할 때.

    How:
        - zip → XML → iterCellRows → period group → 13-col parquet write.

    LLM Specifications:
        AntiPatterns:
            - buildPanel 수정해 셀 끼우기 금지 — 독립 평행(wide 불가침).
            - 빈 period parquet write 금지 — 셀 0 이면 파일 미생성.
        OutputSchema:
            - ``dict[str, int]`` + data/dart/panelCell/{code}/{period}.parquet.
        Prerequisites:
            - 로컬 zip.
        Freshness:
            - zip 갱신 시 재빌드.
        Dataflow:
            - zip → iterCellRows → period group → write.
        TargetMarkets:
            - KR (DART).
    """
    if outBaseDir is None:
        outBaseDir = Path(_cfg.dataDir) / "dart" / "panelCell"
    outDir = Path(outBaseDir) / code

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
            if period is None:
                period = _periodFromXml(root, rcept)
            for row in iterCellRows(root, period=period, code=code, rcept=rcept):
                periodRows.setdefault(period, []).append(row)

    result: dict[str, int] = {}
    if not any(periodRows.values()):
        return result
    outDir.mkdir(parents=True, exist_ok=True)
    for period, rows in periodRows.items():
        if not rows:
            continue
        df = pl.DataFrame(rows, schema=CELL_SCHEMA)
        outPath = outDir / f"{period}.parquet"
        if outPath.exists() and not overwrite:
            continue
        df.write_parquet(str(outPath), compression="zstd")
        result[period] = df.height
        if verbose:
            _log.info("  cell %s %s: %d row", code, period, df.height)
    return result
