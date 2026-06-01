"""panel 전역 정부-택소노미 뼈대(spine) 생성 — 최신 사업보고서 문서순서·계층 → spineData.py.

panel wide 의 행 순서·계층은 **정부 IFRS 택소노미/기업공시서식 속성** = 회사 무관 전역 truth.
``blockOrder`` 는 보고서마다 0 리셋이라 read 가 재발견할 수 없고, ``canonicalKey`` 는 정렬 가능
번호가 아니다 (실측: 주석 문서순 ≠ D-번호 오름차순). → 정부 표시순서를 **빌드 시 1회 명시
spine 으로 굽는다.**

알고리즘 (회사별 → consensus):
    1. 각 종목 최신 사업보고서(Q4) zip 을 raw 파싱 (stale parquet 무관, build 헬퍼 재사용).
    2. walker → horizontalize → resolveBatch 로 read 와 동일 section-granular 행 산출.
    3. ``rowIdentity`` 별 문서순서(blockOrder) rank + chapter 대순서 rank + ``extractAclassEntries``
       parentRawId→canonicalKey 트리.
    4. 다종목이면 identity 별 median rank consensus (단일 부트스트랩은 그 회사 정부순서 그대로).
    5. ``spineData.py`` 생성 — ``SPINE_ROWS`` ordered tuple literal (git-diff 추적, import 로드).

산출은 **순수 코드** (루트 data orphan parquet 아님) — git diff 로 정부 순서/트리 변화 추적,
``import`` 만으로 read 표면이 로드 (importlib.resources 불요).

LLM Specifications:
    AntiPatterns:
        - 분기보고서를 뼈대로 금지 — 분기 ⊄ 연간(배당·임원·주총 누락). 최신 Q4 사업보고서만.
        - stale parquet artifact read 금지 — raw zip 직접 파싱(disclosureKey 미부착 무관).
        - spine 을 parquet 로 저장 금지 — 순수 .py(git 추적·import 로드).
    OutputSchema:
        - ``buildSpine(codes, *, outModulePath, refDf) -> dict`` (생성 통계).
        - 부수효과: ``spine/spineData.py`` (SPINE_ROWS tuple).
    Prerequisites:
        - data/dart/original/docs/{code}/*.zip 로컬. lxml.
    Freshness:
        - corpus 재빌드/확대 시 재생성 (consensus 강화).
    Dataflow:
        - zip → walker → horizontalize → rowIdentity·blockOrder·parentKey → consensus → spineData.py.
    TargetMarkets:
        - KR (DART). EDGAR 는 별도 spine (후속).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

import polars as pl
from lxml import etree

import dartlab.config as _cfg

from ..mapper import canonicalKey, resolveBatch, rowIdentity
from ..schema import PANEL_SCHEMA
from .builder import _readZip, _xmlsToPeriodRows
from .horizontalize import horizontalize
from .refScan import extractAclassEntries, scanRefBaseline

_log = logging.getLogger(__name__)

# 생성 모듈 기본 경로 (패키지 내 spine/spineData.py).
_DEFAULT_SPINE_MODULE = Path(__file__).resolve().parents[1] / "spine" / "spineData.py"


def _latestAnnualBundle(
    code: str, refDf: pl.DataFrame | None, matchThreshold: float
) -> tuple[str, list[dict], list[str]] | None:
    """한 종목의 최신 사업보고서(Q4) → (period, element-rows, xmls). 없으면 None.

    Args:
        code: 종목코드.
        refDf: 옛 양식 fuzzy 매칭 ref table.
        matchThreshold: fuzzy Jaccard threshold.

    Returns:
        ``(period, rows, xmls)`` — 최신 Q4 의 walker element rows + 그 zip 의 XML 문자열들.
        zip 없음/Q4 없음 시 None.

    Raises:
        없음 — zip read 실패는 skip.
    """
    zipDir = Path(_cfg.dataDir) / "dart" / "original" / "docs" / code
    if not zipDir.exists():
        return None
    best: tuple[str, list[dict], list[str]] | None = None
    for zp in sorted(zipDir.glob("*.zip")):
        rcept, xmls = _readZip(zp)
        if not xmls or not rcept:
            continue
        periodRows = _xmlsToPeriodRows(xmls, rcept, code, refDf, matchThreshold)
        for period, rows in periodRows.items():
            if not period.endswith("Q4"):
                continue
            if best is None or period > best[0]:
                best = (period, rows, xmls)
    return best


def _parentKeyMap(xmls: list[str]) -> dict[str, str | None]:
    """최신 사업보고서 XML 들 → ``canonicalKey(rawId) -> canonicalKey(parentRawId)`` 트리.

    ``extractAclassEntries`` 의 parentRawId(TABLE-GROUP 중첩)를 canonicalKey 로 정규화. 같은
    canonicalKey 가 여러 parent 면 첫 발견 우선 (정부 양식 내 안정). Phase 2 셀 세분화 토대.

    Args:
        xmls: 최신 사업보고서 zip 의 decoded XML 문자열 list.

    Returns:
        ``{canonicalKey: parentCanonicalKey | None}``. parent 없으면 None.

    Raises:
        없음 — XML parse 실패 XML 은 skip.
    """
    parser = etree.XMLParser(recover=True, huge_tree=True)
    tree: dict[str, str | None] = {}
    for xml in xmls:
        try:
            root = etree.fromstring(xml.encode("utf-8"), parser)
        except (etree.XMLSyntaxError, ValueError):
            continue
        if root is None:
            continue
        for entry in extractAclassEntries(xml):
            key = canonicalKey(entry.get("rawId"))
            if key is None or key in tree:
                continue
            tree[key] = canonicalKey(entry.get("parentRawId"))
    return tree


def _companySpine(
    code: str, refDf: pl.DataFrame | None, matchThreshold: float
) -> list[tuple[str, int, str | None, int]] | None:
    """한 종목 최신 사업보고서 → ``[(identity, order, parentKey, chapterRank)]`` (문서순서).

    walker → horizontalize → resolveBatch 로 read 와 동일 section-granular 행 산출 후 ``rowIdentity``
    별 문서순서(blockOrder) rank + chapter 대순서 dense rank + parentKey 트리.

    Args:
        code: 종목코드.
        refDf: 옛 양식 fuzzy 매칭 ref table.
        matchThreshold: fuzzy Jaccard threshold.

    Returns:
        ``[(identity, order, parentKey, chapterRank)]`` (identity 중복 0, order 단조) 또는 None.

    Raises:
        없음.
    """
    bundle = _latestAnnualBundle(code, refDf, matchThreshold)
    if bundle is None:
        return None
    _period, rows, xmls = bundle
    if not rows:
        return None
    df = pl.DataFrame(rows, schema=PANEL_SCHEMA)
    df = horizontalize(df)
    df = resolveBatch(df)  # disclosureKey 부착
    if df.is_empty():
        return None

    parentTree = _parentKeyMap(xmls)

    # chapter 대순서 = 첫 등장 blockOrder 기준 dense rank.
    chapterFirst: dict[str, int] = {}
    for ch, bo in zip(df["chapter"].to_list(), df["blockOrder"].to_list(), strict=True):
        chk = ch or ""
        if chk not in chapterFirst or bo < chapterFirst[chk]:
            chapterFirst[chk] = bo
    chapterRankOf = {ch: i for i, (ch, _) in enumerate(sorted(chapterFirst.items(), key=lambda kv: kv[1]))}

    out: list[tuple[str, int, str | None, int]] = []
    seen: set[str] = set()
    order = 0
    for r in df.sort("blockOrder").iter_rows(named=True):
        ident = rowIdentity(r.get("disclosureKey"), r.get("chapter"), r.get("sectionLeaf"))
        if ident in seen:
            continue
        seen.add(ident)
        parentKey = parentTree.get(r.get("disclosureKey")) if r.get("disclosureKey") else None
        out.append((ident, order, parentKey, chapterRankOf.get(r.get("chapter") or "", 0)))
        order += 1
    return out


def _consensus(
    perCompany: list[list[tuple[str, int, str | None, int]]],
) -> list[tuple[str, int, str | None, int]]:
    """다종목 회사별 spine → identity 별 median rank consensus → 최종 ordered rows.

    identity 별 (order, chapterRank) median + parentKey 첫 non-null 채택 → (chapterRank, order)
    정렬 후 dense spineOrder 0..N 재부여. 단일 종목이면 그 순서 그대로.

    Args:
        perCompany: 회사별 ``[(identity, order, parentKey, chapterRank)]`` list.

    Returns:
        consensus ``[(identity, spineOrder, parentKey, chapterRank)]`` (spineOrder 0..N 단조).

    Raises:
        없음.
    """
    orders: dict[str, list[int]] = defaultdict(list)
    chRanks: dict[str, list[int]] = defaultdict(list)
    parents: dict[str, str | None] = {}
    for company in perCompany:
        for ident, order, parentKey, chRank in company:
            orders[ident].append(order)
            chRanks[ident].append(chRank)
            if ident not in parents or parents[ident] is None:
                parents[ident] = parentKey

    def _median(xs: list[int]) -> float:
        s = sorted(xs)
        n = len(s)
        mid = n // 2
        return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2

    ranked = [(ident, _median(chRanks[ident]), _median(orders[ident]), parents[ident]) for ident in orders]
    ranked.sort(key=lambda t: (t[1], t[2], t[0]))
    return [
        (ident, spineOrder, parentKey, int(chMed))
        for spineOrder, (ident, chMed, _orderMed, parentKey) in enumerate(ranked)
    ]


def _renderModule(rows: list[tuple[str, int, str | None, int]]) -> str:
    """consensus rows → ``spineData.py`` 소스 문자열 (SPINE_ROWS tuple literal).

    Args:
        rows: ``[(identity, spineOrder, parentKey, chapterRank)]``.

    Returns:
        생성 모듈 소스 (헤더 + SPINE_ROWS).

    Raises:
        없음.
    """
    header = (
        '"""panel 전역 정부-택소노미 뼈대 데이터 — spineBuilder.buildSpine 생성물 (사람 미수정).\n\n'
        "각 행 = (identity, spineOrder, parentKey, chapterRank). identity = canonicalKey(keyed) /\n"
        "NARR::chapter␟section(narrative). spineOrder = 정부 문서 표시순서, chapterRank = 챕터 대순서,\n"
        "parentKey = TABLE-GROUP 트리 부모(canonicalKey, Phase 2 셀 세분화 토대).\n\n"
        "재생성: ``python -X utf8 -m dartlab.providers.dart.panel.build --spine --codes <codes>``.\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "SPINE_ROWS: tuple[tuple[str, int, str | None, int], ...] = (\n"
    )

    def _q(s: str | None) -> str:
        """ruff 호환 double-quote 직렬화 (생성물 재포맷 0)."""
        if s is None:
            return "None"
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

    body = "".join(
        f"    ({_q(ident)}, {order}, {_q(parentKey)}, {chRank}),\n" for ident, order, parentKey, chRank in rows
    )
    return header + body + ")\n"


def buildSpine(
    codes: list[str] | None = None,
    *,
    outModulePath: Path | str | None = None,
    refDf: pl.DataFrame | None = None,
    matchThreshold: float = 0.70,
    verbose: bool = True,
) -> dict[str, int]:
    """전역 정부-택소노미 spine 생성 — 최신 사업보고서 문서순서·계층 → spineData.py.

    Args:
        codes: 종목코드 list. None = ["005930"] 부트스트랩.
        outModulePath: 생성 모듈 경로. None = ``panel/spine/spineData.py``.
        refDf: 옛 양식 fuzzy 매칭 ref table. None = baseline scan.
        matchThreshold: fuzzy Jaccard threshold (검증 0.70).
        verbose: 진행 로그.

    Returns:
        ``{"codes": 처리 종목수, "rows": spine 행수}``.

    Raises:
        없음 — zip 없는 종목은 skip.

    Example:
        >>> buildSpine(["005930"], verbose=False)  # doctest: +SKIP
        {'codes': 1, 'rows': 96}

    SeeAlso:
        - ``spine.SPINE`` — 생성물 read 표면 dict.
        - ``read.readWide`` — spine 으로 wide 행 정렬.
        - ``mapper.rowIdentity`` — 행 identity SSOT.

    Requires:
        - data/dart/original/docs/{code}/*.zip. lxml. polars.

    Capabilities:
        - 정부 문서순서·계층을 회사 무관 전역 뼈대(순수 코드)로 1회 굽는다 — read 재발견 0.

    Guide:
        - 운영자/CI build-time 호출 (``--spine``). corpus 확대 시 재생성으로 consensus 강화.

    AIContext:
        - raw zip 직접 파싱 (stale parquet 무관). 다종목 median rank consensus.

    When:
        - panel 행 정렬 기준(정부 뼈대)을 (재)생성할 때.

    How:
        - 종목별 최신 Q4 → walker→horizontalize→rowIdentity·blockOrder·parentKey → consensus → 모듈 생성.

    LLM Specifications:
        AntiPatterns:
            - 분기보고서 뼈대 금지 — 최신 Q4 사업보고서만.
            - parquet 저장 금지 — 순수 .py(git 추적).
        OutputSchema:
            - ``dict[str, int]`` + 부수효과 spineData.py.
        Prerequisites:
            - 로컬 zip. refDf (또는 baseline scan).
        Freshness:
            - corpus 재빌드/확대 시 재생성.
        Dataflow:
            - zip → walker → horizontalize → identity·order·parent → consensus → spineData.py.
        TargetMarkets:
            - KR (DART).
    """
    if codes is None:
        codes = ["005930"]
    if refDf is None:
        refDf = scanRefBaseline(minCorpCount=1)
    outPath = Path(outModulePath) if outModulePath else _DEFAULT_SPINE_MODULE

    perCompany: list[list[tuple[str, int, str | None, int]]] = []
    processed = 0
    for code in codes:
        company = _companySpine(code, refDf, matchThreshold)
        if company is None:
            if verbose:
                _log.warning("spine skip (zip/Q4 없음): %s", code)
            continue
        perCompany.append(company)
        processed += 1
        if verbose:
            _log.info("spine scanned %s: %d rows", code, len(company))

    rows = _consensus(perCompany) if perCompany else []
    outPath.parent.mkdir(parents=True, exist_ok=True)
    outPath.write_text(_renderModule(rows), encoding="utf-8")
    _ruffFormat(outPath)  # 긴 identity 줄 분할 등 ruff 정본화 (생성물 CI 게이트 통과)
    if verbose:
        _log.info("spine 생성: %s (codes=%d, rows=%d)", outPath, processed, len(rows))
    return {"codes": processed, "rows": len(rows)}


def _ruffFormat(path: Path) -> None:
    """생성 모듈을 ruff format 정본화 (실패는 무시 — ruff 부재 환경 안전).

    Args:
        path: 포맷할 .py 경로.

    Returns:
        None.

    Raises:
        없음 — subprocess 실패는 흡수 (생성물은 이미 valid python).
    """
    import subprocess

    try:
        subprocess.run(
            ["uv", "run", "ruff", "format", str(path)],
            check=False,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        pass
