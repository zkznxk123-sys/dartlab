"""sections artifact columnar projection 강제 가드 — PR-5 plan snazzy-wibbling-origami.

3-content-column SSOT 의 핵심: 분석 path 는 ``content_plain`` (또는 wide ``content``)
만 read. ``content_raw`` / ``content_table_struct`` 는 viewer / finance 표 파서 전용.
잘못 select 하면 페이지 fault 200~500MB 회귀.

본 가드는 AST scan 으로 호출자 패턴을 정적 강제:

1. **content_raw 컬럼 select 제한** — ``loadSectionsLong(columns=[...,"content_raw"])``
   호출자는 viewer / parse 화이트리스트만.
2. **content_table_struct 컬럼 select 제한** — finance / parse 화이트리스트만.
3. **Company.sectionsRaw() / sectionsTables() 호출자 제한** — 같은 화이트리스트.
4. **xmlChunkToMixed 런타임 호출 0 강제** — sectionsBuilder + zipCollector + legacy
   periodIter (fallback) 만 허용. 분석 path 에서 호출 시 sections build 6~18s 회귀.

위반 시 RuntimeError 대신 *PR 차단* (CI assert) — 실수로 메모리 폭주 path 진입 0.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab"

# content_raw / sectionsRaw() — viewer 시각 렌더링 + 표 native 파서 전용.
_RAW_ALLOWED_PREFIXES: tuple[str, ...] = (
    "server/",  # viewer API (companyApi.py 등)
    "providers/dart/docs/viewer",  # viewer builder
    "providers/dart/docs/sections/",  # sections layer 자체 (definition + fallback)
    "providers/dart/parse/",  # htmlTableParser / tableHorizontalizer (raw HTML 직접 파싱)
    "providers/dart/company.py",  # Company surface (method 정의)
    "providers/edgar/",  # EDGAR sections (별도 SSOT, EDGAR own content_raw schema)
    # 수집 일원화: allFilings raw 본문 *생산* 콜렉터 → gather (구 providers/dart/openapi).
    "gather/dart/allFilingsCollector",  # content_raw 컬럼 생성(저장) — raw producer
)

# content_table_struct / sectionsTables() — finance 표 파서 전용.
_TABLES_ALLOWED_PREFIXES: tuple[str, ...] = (
    "providers/dart/parse/",  # tableHorizontalizer 등
    "providers/dart/docs/sections/",  # sections layer 자체
    "providers/dart/docs/finance/",  # finance 표 분석
    "providers/dart/builder/",  # dataDispatcher 등
    "providers/dart/company.py",  # Company surface (method 정의)
    "server/",  # viewer / finance API
)

# xmlChunkToMixed — build-time 전용. analysis 런타임 path 호출 0.
_MIXED_ALLOWED_PREFIXES: tuple[str, ...] = (
    # 수집 일원화(L1 ETL 재정의): zip ingest fetch 는 gather, build seam·변환은 core/providers.
    "gather/dart/zipCollector",  # zip ingest 시점 사전 계산 (구 providers/dart/openapi/zipCollector)
    "core/dartBuild",  # DartBuildProvider DIP seam delegate (build 위임)
    "providers/dart/build/",  # DartBuildProvider 구현 (raw→parquet build)
    "providers/dart/docs/sections/sectionsBuilder",  # sections artifact 빌더
    "providers/dart/docs/sections/xmlAdapter",  # 정의 위치
    "providers/dart/docs/sections/periodIter",  # legacy fallback (artifact 부재 환경)
    "providers/dart/docs/sections/pipeline",  # legacy runtime build (artifact 부재)
)


def _relPath(pyFile: Path) -> str:
    return str(pyFile.relative_to(ROOT)).replace("\\", "/")


def _isAllowed(rel: str, allowed: tuple[str, ...]) -> bool:
    return any(rel == p or rel.startswith(p) for p in allowed)


def _walkPyFiles() -> list[Path]:
    return [p for p in ROOT.rglob("*.py") if "skills" not in p.parts]


def _findStringLiterals(tree: ast.AST) -> list[tuple[int, str]]:
    """AST 안 모든 string literal 의 (lineno, value) list."""
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append((node.lineno, node.value))
    return out


def _findCalls(tree: ast.AST, names: tuple[str, ...]) -> list[tuple[int, str]]:
    """attr 또는 함수명 매칭 Call 의 (lineno, name) list."""
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        nm: str | None = None
        if isinstance(func, ast.Attribute):
            nm = func.attr
        elif isinstance(func, ast.Name):
            nm = func.id
        if nm in names:
            out.append((node.lineno, nm))
    return out


def test_content_raw_select_whitelist() -> None:
    """``content_raw`` 문자열 등장 파일은 viewer / parse / sections 화이트리스트만."""
    violations: list[str] = []
    for pyFile in _walkPyFiles():
        try:
            tree = ast.parse(pyFile.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for lineno, s in _findStringLiterals(tree):
            if s != "content_raw":
                continue
            rel = _relPath(pyFile)
            if _isAllowed(rel, _RAW_ALLOWED_PREFIXES):
                continue
            violations.append(f"{rel}:{lineno}: 'content_raw' select 금지 (viewer/parse 전용)")
    assert not violations, "content_raw select 위반:\n" + "\n".join(violations)


def test_content_table_struct_select_whitelist() -> None:
    """``content_table_struct`` 문자열 등장 파일은 finance / parse / sections 화이트리스트만."""
    violations: list[str] = []
    for pyFile in _walkPyFiles():
        try:
            tree = ast.parse(pyFile.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for lineno, s in _findStringLiterals(tree):
            if s != "content_table_struct":
                continue
            rel = _relPath(pyFile)
            if _isAllowed(rel, _TABLES_ALLOWED_PREFIXES):
                continue
            violations.append(f"{rel}:{lineno}: 'content_table_struct' select 금지 (finance/parse 전용)")
    assert not violations, "content_table_struct select 위반:\n" + "\n".join(violations)


def test_sectionsRaw_caller_whitelist() -> None:
    """``Company.sectionsRaw()`` 호출자는 viewer/parse 화이트리스트만."""
    violations: list[str] = []
    for pyFile in _walkPyFiles():
        try:
            tree = ast.parse(pyFile.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for lineno, nm in _findCalls(tree, ("sectionsRaw",)):
            rel = _relPath(pyFile)
            if _isAllowed(rel, _RAW_ALLOWED_PREFIXES):
                continue
            violations.append(f"{rel}:{lineno}: sectionsRaw() 호출 금지 (viewer/parse 전용)")
    assert not violations, "sectionsRaw() 호출 위반:\n" + "\n".join(violations)


def test_sectionsTables_caller_whitelist() -> None:
    """``Company.sectionsTables()`` 호출자는 finance/parse 화이트리스트만."""
    violations: list[str] = []
    for pyFile in _walkPyFiles():
        try:
            tree = ast.parse(pyFile.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for lineno, nm in _findCalls(tree, ("sectionsTables",)):
            rel = _relPath(pyFile)
            if _isAllowed(rel, _TABLES_ALLOWED_PREFIXES):
                continue
            violations.append(f"{rel}:{lineno}: sectionsTables() 호출 금지 (finance/parse 전용)")
    assert not violations, "sectionsTables() 호출 위반:\n" + "\n".join(violations)


def test_xml_chunk_to_mixed_caller_whitelist() -> None:
    """``xmlChunkToMixed`` 호출자는 build-time 화이트리스트만 — 런타임 분석 path 금지."""
    violations: list[str] = []
    for pyFile in _walkPyFiles():
        try:
            tree = ast.parse(pyFile.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for lineno, nm in _findCalls(tree, ("xmlChunkToMixed",)):
            rel = _relPath(pyFile)
            if _isAllowed(rel, _MIXED_ALLOWED_PREFIXES):
                continue
            violations.append(f"{rel}:{lineno}: xmlChunkToMixed() 호출 금지 (build-time 전용)")
    assert not violations, "xmlChunkToMixed() 호출 위반:\n" + "\n".join(violations)
