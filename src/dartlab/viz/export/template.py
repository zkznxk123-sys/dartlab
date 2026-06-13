"""Excel 내보내기 템플릿 — 시트 구성 정의.

템플릿은 여러 SheetSpec으로 구성되며, 각 SheetSpec은
데이터 소스(source), 표시할 컬럼, 연도 범위, 정렬을 정의한다.

source 는 discriminated union (``SheetSource``):
    - ``ModuleSource(kind="module", name)`` — 모듈/재무 시트 ("IS"/"BS"/"CF"/"ratios"/"dividend"/...).
    - ``PanelTableSource(kind="panelTable", ...)`` — 공시 panel 의 단일 표 (병합 보존 격자 export).

하위호환: ``SheetSpec(source="IS")`` 처럼 문자열 source 는 ``ModuleSource`` 로 자동 정규화된다.
기존 PRESET·저장된 사용자 템플릿(JSON 의 ``"source": "IS"``) 은 무변경 로드된다.

사용법::

    from dartlab.viz.export.template import ExcelTemplate, SheetSpec, PRESETS, PanelTableSource

    t = ExcelTemplate(name="나만의 양식", sheets=[
        SheetSpec(source="IS", label="손익계산서"),                       # str → ModuleSource
        SheetSpec(source="BS", label="재무상태표", columns=["sales", "net_profit"]),
        SheetSpec(source=PanelTableSource(                                # 공시 표
            kind="panelTable",
            chapter="I. 회사의 개요", sectionLeaf="1. 회사의 개요",
            blockLeaf="", leafType="table", leafSeq=3,
            periodMode="asFiled", period="2025Q4",
        ), label="회사 개요표"),
    ])

    # 프리셋 사용
    full = PRESETS["full"]
    summary = PRESETS["summary"]
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Union


@dataclass
class ModuleSource:
    """모듈/재무 시트 소스 — 기존 export writer (IS/BS/CF/ratios/dividend/...) 분기.

    Args:
        kind: 항상 "module" (discriminator).
        name: 모듈/재무 시트 이름 ("IS"/"BS"/"CF"/"ratios"/"dividend"/"audit"/...).

    Example:
        >>> ModuleSource(kind="module", name="IS").name
        'IS'

    Raises:
        없음 — 순수 dataclass.
    """

    name: str
    kind: Literal["module"] = "module"


@dataclass
class PanelTableSource:
    """공시 panel 의 단일 표 소스 — 병합 보존 격자(.xlsx) export.

    panel wide 행은 ``(chapter, sectionLeaf, blockLeaf, leafType, disclosureKey, scope,
    leafSeq)`` 7-필드로 *유일* 식별된다(실측: 1627 행 0 충돌). disclosureKey 는 대부분의
    공시 표(회사개요·계열사·지배구조)에서 None 이라 **선택** 필드다 — 제공된 필드만으로
    매칭하고, 같은 섹션의 표가 여러 개면 ``leafSeq`` 가 정밀 디스앰비그한다.

    Args:
        kind: 항상 "panelTable" (discriminator).
        chapter: 정부표준 14노드 chapter 라벨 ("I. 회사의 개요" 등).
        sectionLeaf: 섹션 leaf 라벨 ("1. 회사의 개요" 등).
        blockLeaf: 블록 leaf (표 제목, 종종 "").
        leafType: "table" / "text" (export 격자는 보통 "table").
        disclosureKey: 회사 간 이식 키 (재무·일부 공시만 보유, 없으면 None).
        scope: "consolidated"/"standalone"/None.
        leafSeq: wide 행의 섹션 내 ordinal — 같은 섹션 다중 표 디스앰비그 (None = 첫 매칭).
        periodMode: "asFiled" (단일 기간 원본 격자) / "horizontalized" (항목×기간).
        period: asFiled 면 단일 기간("2025Q4"); horizontalized 면 None (전 기간).

    Example:
        >>> s = PanelTableSource(kind="panelTable", chapter="I. 회사의 개요",
        ...     sectionLeaf="1. 회사의 개요", leafType="table", periodMode="asFiled",
        ...     period="2025Q4")
        >>> (s.chapter, s.periodMode)
        ('I. 회사의 개요', 'asFiled')

    Raises:
        없음 — 순수 dataclass.
    """

    chapter: str = ""
    sectionLeaf: str = ""
    blockLeaf: str = ""
    leafType: str = "table"
    disclosureKey: str | None = None
    scope: str | None = None
    leafSeq: int | None = None
    periodMode: Literal["asFiled", "horizontalized"] = "asFiled"
    period: str | None = None
    kind: Literal["panelTable"] = "panelTable"


SheetSource = Union[ModuleSource, PanelTableSource]


def _coerceSource(source: Any) -> SheetSource:
    """source(str | dict | dataclass) → SheetSource 정규화 (하위호환 흡수).

    Args:
        source: 문자열 모듈명, 직렬화 dict(kind 분기), 또는 이미 SheetSource dataclass.

    Returns:
        ModuleSource | PanelTableSource.

    Example:
        >>> _coerceSource("IS").name
        'IS'
        >>> _coerceSource({"kind": "panelTable", "chapter": "I."}).chapter
        'I.'

    Raises:
        TypeError: source 가 str/dict/SheetSource 어느 것도 아닐 때.
    """
    if isinstance(source, (ModuleSource, PanelTableSource)):
        return source
    if isinstance(source, str):
        return ModuleSource(kind="module", name=source)
    if isinstance(source, dict):
        kind = source.get("kind", "module")
        if kind == "panelTable":
            fields = {k: v for k, v in source.items() if k != "kind"}
            return PanelTableSource(kind="panelTable", **fields)
        # default/module — name 필수, 옛 dict 형태도 흡수
        name = source.get("name", "")
        return ModuleSource(kind="module", name=name)
    raise TypeError(f"SheetSpec.source 는 str/dict/SheetSource 여야 함: {type(source)!r}")


@dataclass
class SheetSpec:
    """단일 시트 명세.

    Args:
        source: 시트 데이터 소스 — 문자열(모듈명, ModuleSource 로 정규화) 또는
            ModuleSource/PanelTableSource. dict 도 fromDict 경로에서 정규화된다.
        label: 시트 라벨 (빈 값이면 source 에서 파생).
        columns: 컬럼 필터 (모듈 source 한정).
        years: 연도 필터 (모듈 source 한정).
        sortBy: 정렬 기준 컬럼.
        maxRows: 최대 행 수 (0 = 무제한).

    Example:
        >>> SheetSpec(source="IS").source.name
        'IS'
        >>> SheetSpec(source="IS", label="").label
        'IS'

    Raises:
        TypeError: source 정규화 실패 (str/dict/SheetSource 아님).
    """

    source: Any
    label: str = ""
    columns: list[str] = field(default_factory=list)
    years: list[str] = field(default_factory=list)
    sortBy: str = ""
    maxRows: int = 0

    def __post_init__(self) -> None:
        self.source = _coerceSource(self.source)
        if not self.label:
            # 라벨 기본값 — ModuleSource 는 name, PanelTableSource 는 blockLeaf/sectionLeaf.
            if isinstance(self.source, ModuleSource):
                self.label = self.source.name
            else:
                self.label = self.source.blockLeaf or self.source.sectionLeaf or "표"


@dataclass
class ExcelTemplate:
    """Excel 내보내기 템플릿."""

    name: str
    sheets: list[SheetSpec] = field(default_factory=list)
    description: str = ""
    createdAt: float = field(default_factory=time.time)
    updatedAt: float = field(default_factory=time.time)
    templateId: str = ""

    def __post_init__(self) -> None:
        if not self.templateId:
            self.templateId = f"t_{int(self.createdAt * 1000)}"

    def addSheet(self, spec: SheetSpec) -> None:
        """시트 추가.

        Args:
            spec: 추가할 SheetSpec.

        Example:
            >>> t = ExcelTemplate(name="x"); t.addSheet(SheetSpec(source="IS")); len(t.sheets)
            1

        Raises:
            없음.
        """
        self.sheets.append(spec)
        self.updatedAt = time.time()

    def removeSheet(self, index: int) -> None:
        """인덱스로 시트 제거.

        Args:
            index: 제거할 시트 인덱스 (범위 밖이면 무동작).

        Example:
            >>> t = ExcelTemplate(name="x", sheets=[SheetSpec(source="IS")]); t.removeSheet(0); len(t.sheets)
            0

        Raises:
            없음 — 범위 밖 인덱스는 무시.
        """
        if 0 <= index < len(self.sheets):
            self.sheets.pop(index)
            self.updatedAt = time.time()

    def moveSheet(self, fromIdx: int, toIdx: int) -> None:
        """시트 순서 이동.

        Args:
            fromIdx: 옮길 시트의 현재 인덱스.
            toIdx: 목표 인덱스.

        Example:
            >>> t = ExcelTemplate(name="x", sheets=[SheetSpec(source="IS"), SheetSpec(source="BS")])
            >>> t.moveSheet(0, 1); t.sheets[0].source.name
            'BS'

        Raises:
            없음 — 범위 밖 인덱스는 무시.
        """
        if 0 <= fromIdx < len(self.sheets) and 0 <= toIdx < len(self.sheets):
            sheet = self.sheets.pop(fromIdx)
            self.sheets.insert(toIdx, sheet)
            self.updatedAt = time.time()

    def toDict(self) -> dict[str, Any]:
        """JSON 직렬화용 dict — source 는 항상 신 dict 형식으로 직렬화.

        Returns:
            asdict 결과 (중첩 source dataclass 포함).

        Example:
            >>> ExcelTemplate(name="x", sheets=[SheetSpec(source="IS")]).toDict()["sheets"][0]["source"]["kind"]
            'module'

        Raises:
            없음.
        """
        return asdict(self)

    def toJson(self) -> str:
        """JSON 문자열.

        Returns:
            indent=2 ensure_ascii=False JSON.

        Example:
            >>> '"name"' in ExcelTemplate(name="x").toJson()
            True

        Raises:
            없음.
        """
        return json.dumps(self.toDict(), ensure_ascii=False, indent=2)

    @classmethod
    def fromDict(cls, d: dict[str, Any]) -> ExcelTemplate:
        """dict에서 복원 — source 가 str/dict 어느 쪽이든 SheetSpec 이 정규화한다.

        Args:
            d: toDict() 또는 옛 형식(``"source": "IS"`` 문자열) dict.

        Returns:
            ExcelTemplate. 기존 저장 템플릿(문자열 source)·신 dict source 모두 무변경 로드.

        Example:
            >>> ExcelTemplate.fromDict({"name": "x", "sheets": [{"source": "IS"}]}).sheets[0].source.name
            'IS'

        Raises:
            KeyError: ``name`` 누락.
        """
        sheets = [SheetSpec(**s) for s in d.get("sheets", [])]
        return cls(
            name=d["name"],
            sheets=sheets,
            description=d.get("description", ""),
            createdAt=d.get("createdAt", time.time()),
            updatedAt=d.get("updatedAt", time.time()),
            templateId=d.get("templateId", ""),
        )

    @classmethod
    def fromJson(cls, s: str) -> ExcelTemplate:
        """JSON 문자열에서 복원.

        Args:
            s: toJson() 또는 옛 형식 JSON 문자열.

        Returns:
            ExcelTemplate.

        Example:
            >>> ExcelTemplate.fromJson('{"name": "x", "sheets": [{"source": "IS"}]}').name
            'x'

        Raises:
            json.JSONDecodeError: 잘못된 JSON.
        """
        return cls.fromDict(json.loads(s))


def _buildFullPreset() -> ExcelTemplate:
    """전체 데이터 프리셋 — 모든 시트 포함."""
    return ExcelTemplate(
        name="전체",
        templateId="preset_full",
        description="모든 데이터 소스를 포함하는 전체 내보내기.",
        sheets=[
            SheetSpec(source="IS", label="손익계산서"),
            SheetSpec(source="BS", label="재무상태표"),
            SheetSpec(source="CF", label="현금흐름표"),
            SheetSpec(source="ratios", label="재무비율"),
            SheetSpec(source="fsSummary", label="요약재무정보"),
            SheetSpec(source="dividend", label="배당"),
            SheetSpec(source="majorHolder", label="최대주주"),
            SheetSpec(source="employee", label="직원현황"),
            SheetSpec(source="executive", label="임원현황"),
            SheetSpec(source="executivePay", label="임원보수"),
            SheetSpec(source="audit", label="감사의견"),
            SheetSpec(source="boardOfDirectors", label="이사회"),
            SheetSpec(source="shareCapital", label="주식현황"),
            SheetSpec(source="rnd", label="R&D"),
            SheetSpec(source="segments", label="부문정보"),
            SheetSpec(source="productService", label="주요제품"),
            SheetSpec(source="subsidiary", label="자회사투자"),
            SheetSpec(source="affiliate", label="관계기업투자"),
            SheetSpec(source="bond", label="채무증권"),
            SheetSpec(source="contingentLiability", label="우발부채"),
            SheetSpec(source="capitalChange", label="자본변동"),
            SheetSpec(source="fundraising", label="증자감자"),
            SheetSpec(source="relatedPartyTx", label="관계자거래"),
            SheetSpec(source="tangibleAsset", label="유형자산"),
            SheetSpec(source="costByNature", label="비용성격별분류"),
            SheetSpec(source="riskDerivative", label="위험관리"),
            SheetSpec(source="sanction", label="제재현황"),
            SheetSpec(source="affiliateGroup", label="계열사"),
            SheetSpec(source="internalControl", label="내부통제"),
            SheetSpec(source="salesOrder", label="매출수주"),
            SheetSpec(source="otherFinance", label="기타재무"),
            SheetSpec(source="companyHistory", label="연혁"),
        ],
    )


def _buildSummaryPreset() -> ExcelTemplate:
    """요약 프리셋 — 핵심 시트만."""
    return ExcelTemplate(
        name="요약",
        templateId="preset_summary",
        description="핵심 재무 데이터만 포함하는 요약 내보내기.",
        sheets=[
            SheetSpec(source="IS", label="손익계산서"),
            SheetSpec(source="BS", label="재무상태표"),
            SheetSpec(source="CF", label="현금흐름표"),
            SheetSpec(source="ratios", label="재무비율"),
            SheetSpec(source="dividend", label="배당"),
            SheetSpec(source="majorHolder", label="최대주주"),
        ],
    )


def _buildGovernancePreset() -> ExcelTemplate:
    """지배구조 프리셋."""
    return ExcelTemplate(
        name="지배구조",
        templateId="preset_governance",
        description="지배구조 관련 데이터 모음.",
        sheets=[
            SheetSpec(source="majorHolder", label="최대주주"),
            SheetSpec(source="executive", label="임원현황"),
            SheetSpec(source="executivePay", label="임원보수"),
            SheetSpec(source="boardOfDirectors", label="이사회"),
            SheetSpec(source="audit", label="감사의견"),
            SheetSpec(source="internalControl", label="내부통제"),
            SheetSpec(source="shareholderMeeting", label="주주총회"),
        ],
    )


PRESETS: dict[str, ExcelTemplate] = {
    "full": _buildFullPreset(),
    "summary": _buildSummaryPreset(),
    "governance": _buildGovernancePreset(),
}
