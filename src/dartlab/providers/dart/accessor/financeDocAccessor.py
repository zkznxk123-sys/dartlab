"""DART 재무공시 doc accessor 구현 — ``FinanceDocAccessor`` Protocol 등록.

``core/financeDocAccessor.py`` 의 Protocol 을 만족하는 DART 구체 구현. ``analysis/financial``
이 stockCode → 단발 doc 호출하는 5 메서드 (sanction · contingentLiability · executive ·
relatedPartyTx · pivotDividend) 를 위임.

import 시점에 자동 register — analysis 가 ``getFinanceDocAccessor()`` 호출 시 provider 자동 로드.
"""

from __future__ import annotations

from typing import Any

from dartlab.core.financeDocAccessor import registerFinanceDocAccessor


class DartFinanceDocAccessor:
    """DART providers 의 단발 doc 호출 모음 — ``FinanceDocAccessor`` Protocol 구현체."""

    def sanction(self, stockCode: str) -> Any | None:
        """제재 공시 doc 조회 — ``providers/dart/docs/finance/sanction`` 위임.

        Args:
            stockCode: 종목코드.

        Returns:
            sanction 결과 또는 None (조회 실패).

        Raises:
            없음 (ValueError/KeyError/TypeError/AttributeError/FileNotFoundError 모두 None 반환).

        Example:
            >>> DartFinanceDocAccessor().sanction("005930")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        from dartlab.providers.dart.docs.finance.sanction import sanction

        try:
            return sanction(stockCode)
        except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
            return None

    def contingentLiability(self, stockCode: str) -> Any | None:
        """우발부채 doc 조회 — ``providers/dart/docs/finance/contingentLiability`` 위임.

        Args:
            stockCode: 종목코드.

        Returns:
            contingentLiability 결과 또는 None.

        Raises:
            없음.

        Example:
            >>> DartFinanceDocAccessor().contingentLiability("005930")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        from dartlab.providers.dart.docs.finance.contingentLiability import contingentLiability

        try:
            return contingentLiability(stockCode)
        except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
            return None

    def executive(self, stockCode: str) -> Any | None:
        """임원 보수/이력 doc 조회 — ``providers/dart/docs/finance/executive`` 위임.

        Args:
            stockCode: 종목코드.

        Returns:
            executive 결과 또는 None.

        Raises:
            없음.

        Example:
            >>> DartFinanceDocAccessor().executive("005930")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        from dartlab.providers.dart.docs.finance.executive import executive

        try:
            return executive(stockCode)
        except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
            return None

    def relatedPartyTx(self, stockCode: str) -> Any | None:
        """특수관계자 거래 doc 조회 — ``providers/dart/docs/finance/relatedPartyTx`` 위임.

        Args:
            stockCode: 종목코드.

        Returns:
            relatedPartyTx 결과 또는 None.

        Raises:
            없음.

        Example:
            >>> DartFinanceDocAccessor().relatedPartyTx("005930")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        from dartlab.providers.dart.docs.finance.relatedPartyTx import relatedPartyTx

        try:
            return relatedPartyTx(stockCode)
        except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
            return None

    def pivotDividend(self, stockCode: str) -> Any | None:
        """배당 pivot 조회 — ``providers/dart/report/pivot.pivotDividend`` 위임.

        Args:
            stockCode: 종목코드.

        Returns:
            DividendResult 또는 None.

        Raises:
            없음.

        Example:
            >>> DartFinanceDocAccessor().pivotDividend("005930")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        from dartlab.providers.dart.report.pivot import pivotDividend

        try:
            return pivotDividend(stockCode)
        except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
            return None

    def buildAnnual(self, stockCode: str) -> Any | None:
        """연간 시리즈 빌드 — ``providers/dart/finance/pivot.buildAnnual`` 위임.

        Args:
            stockCode: 종목코드.

        Returns:
            ``(series, years)`` 튜플 또는 None.

        Raises:
            없음.

        Example:
            >>> DartFinanceDocAccessor().buildAnnual("005930")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        from dartlab.providers.dart.finance.pivot import buildAnnual

        try:
            return buildAnnual(stockCode)
        except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
            return None

    def buildTimeseries(self, stockCode: str) -> Any | None:
        """분기 시리즈 빌드 — ``providers/dart/finance/pivot.buildTimeseries`` 위임.

        Args:
            stockCode: 종목코드.

        Returns:
            ``(series, periods)`` 튜플 또는 None.

        Raises:
            없음.

        Example:
            >>> DartFinanceDocAccessor().buildTimeseries("005930")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        from dartlab.providers.dart.finance.pivot import buildTimeseries

        try:
            return buildTimeseries(stockCode)
        except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
            return None

    def accountLabels(self) -> dict[str, str]:
        """계정 코드 → 한글 라벨 — ``providers/dart/finance/mapper.AccountMapper`` 위임.

        Returns:
            ``{snakeId: 한글 라벨}`` dict. 실패 시 빈 dict.

        Raises:
            없음 (ImportError/FileNotFoundError/AttributeError 모두 빈 dict).

        Example:
            >>> DartFinanceDocAccessor().accountLabels()["sales"]

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        try:
            from dartlab.providers.dart.finance.mapper import AccountMapper

            return dict(AccountMapper.get().labelMap())
        except (ImportError, FileNotFoundError, AttributeError):
            return {}

    def exportModules(self) -> list[tuple[str, str]]:
        """Export 가능한 DART 모듈 list — ``providers/dart/company.listExportModules`` 위임.

        Returns:
            ``[(prop, label), ...]`` 리스트. 실패 시 빈 리스트.

        Raises:
            없음.

        Example:
            >>> DartFinanceDocAccessor().exportModules()[:5]

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        try:
            from dartlab.providers.dart.company import listExportModules

            return list(listExportModules())
        except (ImportError, AttributeError):
            return []


registerFinanceDocAccessor(DartFinanceDocAccessor())
