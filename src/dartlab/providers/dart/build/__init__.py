"""DART build — raw(zip/xml) → parquet 변환·저장 (network 0).

수집 일원화(ETL 분할): fetch 는 gather/dart 전담, 본 패키지는 Transform 전담.

- panel title rows — zip document.xml → ``<TITLE>`` 단위 rows (parseSectionsByTitle).
- ``saver`` — enrich(재무/보고서 컬럼) + 정렬 + atomic parquet write.

gather 수집 orchestration 은 ``core.dartBuild`` DIP 로 본 패키지 함수를 위임받는다
(gather↛providers). import 시점에 ``DartBuildProvider`` 를 register.
"""

from __future__ import annotations


class _DartBuildProvider:
    """core.dartBuild.DartBuildProvider 구현 — raw→parquet 변환을 providers 가 전담."""

    def parseSectionsByTitle(self, *args, **kwargs):
        """zip XML → panel title rows.

        Args:
            *args: delegated parser positional arguments.
            **kwargs: delegated parser keyword arguments.

        Returns:
            Delegated ``parseSectionsByTitle`` result.

        Raises:
            Parser exceptions propagate unchanged.

        Example:
            >>> hasattr(_DartBuildProvider(), "parseSectionsByTitle")
            True
        """
        from dartlab.providers.dart.panel.build.titleRows import parseSectionsByTitle

        return parseSectionsByTitle(*args, **kwargs)

    def splitLargeContent(self, *args, **kwargs):
        """content 셀 분할.

        Args:
            *args: delegated splitter positional arguments.
            **kwargs: delegated splitter keyword arguments.

        Returns:
            Delegated ``splitLargeContent`` result.

        Raises:
            Splitter exceptions propagate unchanged.

        Example:
            >>> hasattr(_DartBuildProvider(), "splitLargeContent")
            True
        """
        from dartlab.providers.dart.panel.build.titleRows import splitLargeContent

        return splitLargeContent(*args, **kwargs)

    def writeParquetSorted(self, *args, **kwargs):
        """정렬 atomic parquet write.

        Args:
            *args: delegated writer positional arguments.
            **kwargs: delegated writer keyword arguments.

        Returns:
            Delegated ``writeParquetSorted`` result.

        Raises:
            Writer exceptions propagate unchanged.

        Example:
            >>> hasattr(_DartBuildProvider(), "writeParquetSorted")
            True
        """
        from dartlab.providers.dart.build.saver import writeParquetSorted

        return writeParquetSorted(*args, **kwargs)

    def enrichFinance(self, *args, **kwargs):
        """재무 컬럼 보강.

        Args:
            *args: delegated enrich positional arguments.
            **kwargs: delegated enrich keyword arguments.

        Returns:
            Delegated ``enrichFinance`` result.

        Raises:
            Enricher exceptions propagate unchanged.

        Example:
            >>> hasattr(_DartBuildProvider(), "enrichFinance")
            True
        """
        from dartlab.providers.dart.build.saver import enrichFinance

        return enrichFinance(*args, **kwargs)

    def enrichReport(self, *args, **kwargs):
        """보고서 컬럼 보강.

        Args:
            *args: delegated enrich positional arguments.
            **kwargs: delegated enrich keyword arguments.

        Returns:
            Delegated ``enrichReport`` result.

        Raises:
            Enricher exceptions propagate unchanged.

        Example:
            >>> hasattr(_DartBuildProvider(), "enrichReport")
            True
        """
        from dartlab.providers.dart.build.saver import enrichReport

        return enrichReport(*args, **kwargs)

    def save(self, *args, **kwargs):
        """append+dedup write.

        Args:
            *args: delegated save positional arguments.
            **kwargs: delegated save keyword arguments.

        Returns:
            Delegated ``save`` result.

        Raises:
            Saver exceptions propagate unchanged.

        Example:
            >>> hasattr(_DartBuildProvider(), "save")
            True
        """
        from dartlab.providers.dart.build.saver import save

        return save(*args, **kwargs)

    def saveReplacingByKeys(self, *args, **kwargs):
        """key 기준 replace 증분 write.

        Args:
            *args: delegated save positional arguments.
            **kwargs: delegated save keyword arguments.

        Returns:
            Delegated ``saveReplacingByKeys`` result.

        Raises:
            Saver exceptions propagate unchanged.

        Example:
            >>> hasattr(_DartBuildProvider(), "saveReplacingByKeys")
            True
        """
        from dartlab.providers.dart.build.saver import saveReplacingByKeys

        return saveReplacingByKeys(*args, **kwargs)

    def korColumns(self, *args, **kwargs):
        """한글 컬럼 rename.

        Args:
            *args: delegated rename positional arguments.
            **kwargs: delegated rename keyword arguments.

        Returns:
            Delegated ``korColumns`` result.

        Raises:
            Renamer exceptions propagate unchanged.

        Example:
            >>> hasattr(_DartBuildProvider(), "korColumns")
            True
        """
        from dartlab.providers.dart.build.saver import korColumns

        return korColumns(*args, **kwargs)

    def xmlChunkToMixed(self, *args, **kwargs):
        """xml chunk → mixed string (panel XML adapter).

        Args:
            *args: delegated XML positional arguments.
            **kwargs: delegated XML keyword arguments.

        Returns:
            Delegated ``xmlChunkToMixed`` result.

        Raises:
            XML conversion exceptions propagate unchanged.

        Example:
            >>> hasattr(_DartBuildProvider(), "xmlChunkToMixed")
            True
        """
        from dartlab.providers.dart.sectionXml import xmlChunkToMixed

        return xmlChunkToMixed(*args, **kwargs)


def _registerDartBuildProvider() -> None:
    """import 시점 등록 — circular import 회피 위해 함수 내부 lazy import."""
    from dartlab.core.dartBuild import registerDartBuildProvider

    registerDartBuildProvider(_DartBuildProvider())


_registerDartBuildProvider()
