"""통합 데이터 레지스트리 — 단일 진실의 원천.

모듈 추가 = _entries.py에 DataEntry 한 줄 추가 → Company, Excel, LLM tool, API, UI 전부 자동 반영.

소비처:
- company.py        → property 디스패치 (_MODULE_REGISTRY 생성)
- notes.py          → 주석 접근 (_REGISTRY 생성)
- export/sources.py → Excel 소스 트리
- ai/tools_registry → LLM tool 스키마 자동 생성
- ai/context.py     → LLM 컨텍스트 빌더
- ai/metadata.py    → 호환 레이어 (MODULE_META → registry 위임)
- server/           → API spec
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ColumnMeta:
    """DataFrame 컬럼 메타데이터 (LLM 컨텍스트용)."""

    name: str
    description: str
    unit: str = ""


@dataclass(frozen=True)
class DataEntry:
    """데이터 소스 메타데이터 — registry의 최소 단위.

    category별 역할:
    - finance: 시계열 재무제표 (annual.IS, timeseries.BS 등)
    - report: 공시 파싱 모듈 (dividend, employee 등)
    - notes: K-IFRS 주석 (notes.receivables 등)
    - disclosure: 서술형 공시 (business, mdna 등)
    - raw: 원본 parquet (rawDocs, rawFinance, rawReport)
    - analysis: L2 분석 엔진 (ratios, insight, sector, rank)
    """

    name: str
    label: str
    category: str
    dataType: str
    description: str

    modulePath: str | None = None
    funcName: str | None = None
    extractor: Any = None

    # DART API 의 apiType 이름 — topic name 과 다를 때만 명시.
    # 없으면 topic name 과 apiType 동일 취급.
    # 예: audit topic 의 DART apiType = "auditOpinion".
    apiType: str | None = None

    # notes 카테고리 전용 dispatch 정보 (notes.py 가 소비).
    # (callerModuleName, koreanKeyword) 튜플.
    # callerModuleName 이 "notesDetail" 이면 _call_notesDetail(koreanKeyword) 호출,
    # 아니면 _call_module(callerModuleName) 호출.
    notesDispatch: tuple[str, str] | None = None

    # topic 단축 alias — 사용자가 `show("board")` 처럼 짧은 이름으로 접근 가능.
    # 2026-04-21 Q1.4: company.py 의 _TOPIC_ALIASES 하드코딩 dict 를 이관.
    aliases: tuple[str, ...] = ()

    requires: str | None = None
    unit: str = "백만원"
    columns: tuple[ColumnMeta, ...] = ()
    analysisHints: tuple[str, ...] = ()
    relatedModules: tuple[str, ...] = ()
    maxRows: int = 30

    # AI 노출 메타데이터
    aiExposed: bool = True
    aiCategory: str = "data"
    aiHint: str = ""
    aiQuestionTypes: tuple[str, ...] = ()
    aiKeywords: tuple[str, ...] = ()


# DataEntry 목록은 _entries.py에서 관리 (942줄 → 별도 파일)
from dartlab.frame.types import _BUSINESS_ALIASES as _BUSINESS_ALIASES  # noqa: I001, E402
from dartlab.frame.types import _ENTRIES as _ENTRIES  # noqa: I001, E402


# ── 인덱스 (O(1) 조회) ──

_INDEX: dict[str, DataEntry] = {e.name: e for e in _ENTRIES}
_BY_CATEGORY: dict[str, list[DataEntry]] = {}
for _e in _ENTRIES:
    _BY_CATEGORY.setdefault(_e.category, []).append(_e)


# alias → canonical name 역인덱스.
# 출처 2가지 병합: (1) DataEntry.aliases 필드, (2) _entries.py 의 _BUSINESS_ALIASES 맵.
# resolveAlias() 가 이 인덱스로 단일 조회.
_ALIAS_TO_NAME: dict[str, str] = {}
for _name, _aliases in _BUSINESS_ALIASES.items():
    for _a in _aliases:
        _ALIAS_TO_NAME[_a] = _name
for _e in _ENTRIES:
    for _a in _e.aliases:
        _ALIAS_TO_NAME[_a] = _e.name


# ── 동적 등록 (플러그인용) ──


class PluginNameCollisionError(ValueError):
    """플러그인 DataEntry 이름이 기존 항목과 충돌."""


def _rebuildIndices() -> None:
    """_INDEX, _BY_CATEGORY, _ALIAS_TO_NAME 파생 인덱스 재구축."""
    global _INDEX, _BY_CATEGORY, _ALIAS_TO_NAME
    _INDEX = {e.name: e for e in _ENTRIES}
    _BY_CATEGORY = {}
    for e in _ENTRIES:
        _BY_CATEGORY.setdefault(e.category, []).append(e)
    _ALIAS_TO_NAME = {}
    for name, aliases in _BUSINESS_ALIASES.items():
        for a in aliases:
            _ALIAS_TO_NAME[a] = name
    for e in _ENTRIES:
        for a in e.aliases:
            _ALIAS_TO_NAME[a] = e.name


def registerEntry(entry: DataEntry, *, source: str = "core") -> None:
    """DataEntry를 레지스트리에 동적 추가.

    Args:
        entry: 추가할 DataEntry.
        source: 출처 태그 (예: "plugin:esg-scores").

    Raises:
        PluginNameCollisionError: 이름이 기존 항목과 충돌할 때.
    """
    if entry.name in _INDEX:
        raise PluginNameCollisionError(f"이름 '{entry.name}' 이미 존재")
    _ENTRIES.append(entry)
    _rebuildIndices()


def unregisterEntry(name: str) -> None:
    """DataEntry를 레지스트리에서 제거 (테스트용)."""
    _ENTRIES[:] = [e for e in _ENTRIES if e.name != name]
    _rebuildIndices()


# ── public API ──


def getEntries(*, category: str | None = None) -> list[DataEntry]:
    """전체 또는 카테고리별 엔트리 반환."""
    if category is None:
        return list(_ENTRIES)
    return list(_BY_CATEGORY.get(category, []))


def getEntry(name: str) -> DataEntry | None:
    """이름으로 단일 엔트리 조회."""
    return _INDEX.get(name)


def resolveAlias(topicOrAlias: str) -> str:
    """alias 라면 canonical topic name 리턴, 아니면 그대로.

    예: ``resolveAlias("board")`` → ``"boardOfDirectors"``.
    ``resolveAlias("boardOfDirectors")`` → ``"boardOfDirectors"`` (이미 canonical).
    """
    return _ALIAS_TO_NAME.get(topicOrAlias, topicOrAlias)


def getCategories() -> list[str]:
    """등록된 카테고리 목록."""
    return list(_BY_CATEGORY.keys())


def getModuleEntries() -> list[DataEntry]:
    """Company property 디스패치에 사용할 엔트리만 (modulePath가 있는 report + disclosure).

    BS/IS/CF/fsSummary는 제외 — company.py에서 statements 내부 디스패치로 별도 처리.
    """
    _SKIP = frozenset({"BS", "IS", "CF", "fsSummary", "holderOverview"})
    return [
        e
        for e in _ENTRIES
        if e.modulePath is not None and e.category in ("report", "disclosure") and e.name not in _SKIP
    ]


def getNotesEntries() -> list[DataEntry]:
    """Notes 접근용 엔트리만."""
    return [e for e in _ENTRIES if e.category == "notes"]


def buildModuleDescription() -> str:
    """LLM tool description용 모듈 목록 문자열 자동 생성.

    모든 카테고리(finance 제외)의 aiExposed=True 엔트리를 포함.
    """
    parts = []
    for e in _ENTRIES:
        if e.category == "finance" or not e.aiExposed:
            continue
        parts.append(f"{e.name}({e.label})")
    return ", ".join(parts)


def buildFeatureDescription(category: str | None = None) -> str:
    """카테고리별 사용 가능한 기능을 상세히 안내한다.

    Args:
        category: finance, report, disclosure, notes, analysis, raw, all.
                  None이면 "all"과 동일.
    """
    target = (category or "all").lower()
    sections: list[str] = []

    for cat, entries in _BY_CATEGORY.items():
        if target != "all" and cat != target:
            continue
        exposed = [e for e in entries if e.aiExposed]
        if not exposed:
            continue
        lines = [f"## {cat} ({len(exposed)}개)"]
        for e in exposed:
            hint = f" — {e.aiHint}" if e.aiHint else ""
            lines.append(f"- **{e.name}** ({e.label}): {e.description}{hint}")
        sections.append("\n".join(lines))

    if not sections:
        available = ", ".join(sorted(_BY_CATEGORY.keys()))
        return f"'{category}' 카테고리가 없습니다. 사용 가능: {available}"

    return "\n\n".join(sections)


def buildQuestionModules() -> dict[str, list[str]]:
    """DataEntry.aiQuestionTypes → {질문유형: [모듈명]} 역인덱스 자동 생성."""
    result: dict[str, list[str]] = {}
    for e in _ENTRIES:
        if not e.aiExposed:
            continue
        for qt in e.aiQuestionTypes:
            result.setdefault(qt, []).append(e.name)
    return result


def buildKeywordMap() -> dict[str, list[str]]:
    """DataEntry.aiKeywords → {키워드: [모듈명]} 역인덱스."""
    result: dict[str, list[str]] = {}
    for e in _ENTRIES:
        if not e.aiExposed:
            continue
        for kw in e.aiKeywords:
            result.setdefault(kw, []).append(e.name)
    return result
