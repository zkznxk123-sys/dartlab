"""docs source namespace accessor.

``company.py`` 에서 분리된 accessor 클래스. ``c._docs.X`` 모든 접근의 본체.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from dartlab.providers.dart.accessor.sectionsSource import _SectionsSource

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


class _DocsAccessor:
    """docs source namespace — Company 의 docs 관련 모든 표면 위임 (DART 공시 원문)."""

    def __init__(self, company: "Company"):
        self._company = company
        self._sectionsAccessor = _SectionsSource(company)

    @property
    def raw(self) -> pl.DataFrame | None:
        """원본 docs parquet — 정규화 전 DART 공시 원본.

        Returns:
            전체 raw row DataFrame 또는 None (데이터 부재).

        Raises:
            없음.

        Example:
            >>> c._docs.raw.head()
        """
        return self._company.rawDocs

    def filings(self) -> pl.DataFrame:
        """공시 목록 — DART 정기/수시 보고서 메타.

        Returns:
            ``rcept_no/report_nm/rcept_dt`` 등 컬럼 DataFrame.

        Raises:
            없음.

        Example:
            >>> c._docs.filings().head(10)
        """
        return self._company._filings()

    @property
    def sections(self) -> "_SectionsSource | None":
        """sections sub-namespace — ``c._docs.sections.X`` 진입점.

        Returns:
            ``_SectionsSource`` 또는 None (docs 부재).

        Raises:
            없음.

        Example:
            >>> c._docs.sections.frame()
        """
        return self._sectionsAccessor if self._company._hasDocs else None

    def sectionsOrdered(self, *, recentFirst: bool = True, annualAsQ4: bool = True) -> pl.DataFrame | None:
        """sections 시간순 정렬 — period 축 ordered DataFrame.

        Args:
            recentFirst: True 면 최근 period 가 앞.
            annualAsQ4: 연도 단위 보고서를 Q4 로 취급.

        Returns:
            정렬된 DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._docs.sectionsOrdered(recentFirst=True)

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars
        """
        sections = self.sections
        return None if sections is None else sections.ordered(recentFirst=recentFirst, annualAsQ4=annualAsQ4)

    def sectionsCoverage(
        self,
        *,
        topic: str | None = None,
        recentFirst: bool = True,
        annualAsQ4: bool = True,
    ) -> pl.DataFrame | None:
        """topic × period 커버리지 매트릭스 — 데이터 결손 식별.

        Args:
            topic: 특정 topic 만 (None 이면 전체).
            recentFirst: True 면 최근 period 우선.
            annualAsQ4: 연도 단위 보고서를 Q4 로 취급.

        Returns:
            커버리지 DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._docs.sectionsCoverage()

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars
        """
        sections = self.sections
        return (
            None if sections is None else sections.coverage(topic=topic, recentFirst=recentFirst, annualAsQ4=annualAsQ4)
        )

    def sectionsFreq(self, freqScope: str, *, includeMixed: bool = True) -> pl.DataFrame | None:
        """sections freq 집계 — section_title 출현 빈도.

        Args:
            freqScope: ``"annual"``/``"quarterly"``/``"all"`` 등 범위.
            includeMixed: 정기+수시 혼합 보고서 포함.

        Returns:
            빈도 DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._docs.sectionsFreq("annual")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars
        """
        sections = self.sections
        return None if sections is None else sections.freq(freqScope, includeMixed=includeMixed)

    def sectionsSemanticRegistry(
        self,
        *,
        topic: str | None = None,
        freqScope: str = "all",
        includeMixed: bool = True,
    ) -> pl.DataFrame | None:
        """semantic registry — section_title 의 의미 매핑 카탈로그.

        Args:
            topic: 특정 topic 필터.
            freqScope: 범위 (annual/quarterly/all).
            includeMixed: 혼합 포함.

        Returns:
            registry DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._docs.sectionsSemanticRegistry(freqScope="annual")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars
        """
        sections = self.sections
        return (
            None
            if sections is None
            else sections.semanticRegistry(topic=topic, freqScope=freqScope, includeMixed=includeMixed)
        )

    def sectionsSemanticCollisions(
        self,
        *,
        topic: str | None = None,
        freqScope: str = "all",
        includeMixed: bool = True,
    ) -> pl.DataFrame | None:
        """semantic collisions — 같은 의미 다른 title.

        Args:
            topic: 특정 topic 필터.
            freqScope: 범위.
            includeMixed: 혼합 포함.

        Returns:
            collision DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._docs.sectionsSemanticCollisions()

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars
        """
        sections = self.sections
        return (
            None
            if sections is None
            else sections.semanticCollisions(topic=topic, freqScope=freqScope, includeMixed=includeMixed)
        )

    def sectionsStructureRegistry(
        self,
        *,
        topic: str | None = None,
        freqScope: str = "all",
        includeMixed: bool = True,
        nodeType: str | None = None,
    ) -> pl.DataFrame | None:
        """structure registry — 섹션 트리 노드 카탈로그.

        Args:
            topic: 특정 topic 필터.
            freqScope: 범위.
            includeMixed: 혼합 포함.
            nodeType: ``"section"``/``"table"`` 등 노드 종류.

        Returns:
            registry DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._docs.sectionsStructureRegistry(nodeType="section")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars
        """
        sections = self.sections
        return (
            None
            if sections is None
            else sections.structureRegistry(
                topic=topic,
                freqScope=freqScope,
                includeMixed=includeMixed,
                nodeType=nodeType,
            )
        )

    def sectionsStructureCollisions(
        self,
        *,
        topic: str | None = None,
        freqScope: str = "all",
        includeMixed: bool = True,
        nodeType: str | None = None,
    ) -> pl.DataFrame | None:
        """structure collisions — 트리 충돌 (같은 path 다른 의미).

        Args:
            topic: 특정 topic 필터.
            freqScope: 범위.
            includeMixed: 혼합 포함.
            nodeType: 노드 종류.

        Returns:
            collision DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._docs.sectionsStructureCollisions()

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars
        """
        sections = self.sections
        return (
            None
            if sections is None
            else sections.structureCollisions(
                topic=topic,
                freqScope=freqScope,
                includeMixed=includeMixed,
                nodeType=nodeType,
            )
        )

    def sectionsStructureEvents(
        self,
        *,
        topic: str | None = None,
        freqScope: str = "all",
        includeMixed: bool = True,
        changedOnly: bool = True,
        nodeType: str | None = None,
    ) -> pl.DataFrame | None:
        """structure events — 기간 별 구조 변화 이벤트.

        Args:
            topic: 특정 topic 필터.
            freqScope: 범위.
            includeMixed: 혼합 포함.
            changedOnly: True 면 변경된 노드만.
            nodeType: 노드 종류.

        Returns:
            events DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._docs.sectionsStructureEvents(changedOnly=True)

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars
        """
        sections = self.sections
        return (
            None
            if sections is None
            else sections.structureEvents(
                topic=topic,
                freqScope=freqScope,
                includeMixed=includeMixed,
                changedOnly=changedOnly,
                nodeType=nodeType,
            )
        )

    def sectionsStructureSummary(
        self,
        *,
        topic: str | None = None,
        freqScope: str = "all",
        includeMixed: bool = True,
        nodeType: str | None = None,
    ) -> pl.DataFrame | None:
        """structure summary — 노드 별 통계 요약.

        Args:
            topic: 특정 topic 필터.
            freqScope: 범위.
            includeMixed: 혼합 포함.
            nodeType: 노드 종류.

        Returns:
            summary DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._docs.sectionsStructureSummary()

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars
        """
        sections = self.sections
        return (
            None
            if sections is None
            else sections.structureSummary(
                topic=topic,
                freqScope=freqScope,
                includeMixed=includeMixed,
                nodeType=nodeType,
            )
        )

    def sectionsStructureChanges(
        self,
        *,
        topic: str | None = None,
        freqScope: str = "all",
        includeMixed: bool = True,
        nodeType: str | None = None,
        latestOnly: bool = True,
        changedOnly: bool = True,
    ) -> pl.DataFrame | None:
        """structure changes — 노드 path 의 시간순 변화 추적.

        Args:
            topic: 특정 topic 필터.
            freqScope: 범위.
            includeMixed: 혼합 포함.
            nodeType: 노드 종류.
            latestOnly: 최근 변경만.
            changedOnly: 변경된 행만.

        Returns:
            changes DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._docs.sectionsStructureChanges(latestOnly=True)

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars
        """
        sections = self.sections
        return (
            None
            if sections is None
            else sections.structureChanges(
                topic=topic,
                freqScope=freqScope,
                includeMixed=includeMixed,
                nodeType=nodeType,
                latestOnly=latestOnly,
                changedOnly=changedOnly,
            )
        )

    @property
    def retrievalBlocks(self) -> pl.DataFrame | None:
        """retrieval 용 chunk 블록 — RAG 검색 표면 SSOT.

        Returns:
            ``block_id/text/topic/period`` 컬럼 DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._docs.retrievalBlocks.head()
        """
        return self._company._retrievalBlocks()

    @property
    def contextSlices(self) -> pl.DataFrame | None:
        """context window 단위 슬라이스 — LLM 입력 최적화.

        Returns:
            슬라이스 DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._docs.contextSlices.head()
        """
        return self._company._contextSlices()

    @property
    def notes(self):
        """주석 (notes) accessor — 재무제표 footnote 진입점.

        Returns:
            ``Notes`` 인스턴스 (lazy).

        Raises:
            없음.

        Example:
            >>> c._docs.notes.text("commitments")
        """
        return self._company._notesAccessor

    @property
    def business(self):
        """사업의 내용 — deprecated alias (``c.show("business")`` 권장).

        Returns:
            BusinessResult 또는 None.

        Raises:
            DeprecationWarning: 호출 시 발생 (alias 패턴).

        Example:
            >>> c._docs.business  # deprecated
            >>> c.show("business")  # 권장

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars
        """
        import warnings

        warnings.warn("docs.business → show('business') 경로 권장", DeprecationWarning, stacklevel=2)
        return self._company._getPrimary("business")

    @property
    def mdna(self):
        """MD&A — deprecated alias (``c.show("mdna")`` 권장).

        Returns:
            MdnaResult 또는 None.

        Raises:
            DeprecationWarning: 호출 시 발생 (alias 패턴).

        Example:
            >>> c._docs.mdna  # deprecated
            >>> c.show("mdna")  # 권장

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars
        """
        import warnings

        warnings.warn("docs.mdna → show('mdna') 경로 권장", DeprecationWarning, stacklevel=2)
        return self._company._getPrimary("mdna")

    @property
    def rawMaterial(self):
        """원재료 — deprecated alias (``c.show("rawMaterial")`` 권장).

        Returns:
            rawMaterial subtable 또는 fallback primary.

        Raises:
            DeprecationWarning: 호출 시 발생.

        Example:
            >>> c._docs.rawMaterial  # deprecated
            >>> c.show("rawMaterial")  # 권장

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars
        """
        import warnings

        warnings.warn("docs.rawMaterial → show('rawMaterial') 경로 권장", DeprecationWarning, stacklevel=2)
        return self._company._sectionsSubtopicWide("rawMaterial") or self._company._safePrimary("rawMaterial")

    def subtables(self, topic: str, *, raw: bool = False) -> pl.DataFrame | None:
        """topic 서브테이블 추출 — long/wide 변환 옵션.

        Args:
            topic: topic 이름 (예: ``"rawMaterial"``).
            raw: True 면 long format, False 면 wide format.

        Returns:
            서브테이블 DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._docs.subtables("rawMaterial", raw=False)
        """
        return self._company._sectionsSubtopicLong(topic) if raw else self._company._sectionsSubtopicWide(topic)
