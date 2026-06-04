"""DART 재무공시 doc accessor 구현 — ``FinanceDocAccessor`` Protocol 등록.

``core/financeDocAccessor.py`` 의 Protocol 을 만족하는 DART 구체 구현. ``analysis/financial``
이 stockCode → 단발 호출하는 메서드 위임. **docs 농장 은퇴 (2026-06)**: sanction ·
contingentLiability · executive · relatedPartyTx 4 개는 정부 native 태깅 없어 panel 재현
불가 → None 반환(신호 드롭, consumer 전부 None 내성). report/finance 기반 메서드
(pivotDividend · buildAnnual · buildTimeseries · accountLabels · exportModules) 는 생존.

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
            - 위임 모듈 — ``providers.dart.docs.finance.*`` 의 동명 함수.
            - ``getFinanceDocAccessor()`` — analysis/financial 이 본 accessor 호출 entry.

        Requires:
            - dartlab

        Capabilities:
            - analysis/financial 이 stockCode → 단발 doc 호출 시 본 Protocol 구현체 위임. 예외 silent
              (None 반환) — caller 가 graceful fallback.

        Guide:
            - 사용자 직접 호출 X — analysis 모듈이 자동 dispatch.

        AIContext:
            internal Protocol adapter — AI 가 직접 호출 X. analysis 모듈이 본 accessor 사용.

        LLM Specifications:
            AntiPatterns:
                - 사용자 직접 호출 X — analysis 모듈이 dispatch.
                - 예외 silent (None 반환) → caller None 분기 의무.
            OutputSchema:
                - 위임 모듈 결과 (DataFrame/dict 등) 또는 None (예외 시).
            Prerequisites:
                - 본 회사 docs/finance parquet (위임 모듈별).
            Freshness:
                - 위임 모듈 데이터 갱신 시점.
            Dataflow:
                - stockCode → providers.dart.docs.finance.X → 본 메서드.
            TargetMarkets:
                - KR (DART) 한정.
        """
        # docs.finance.sanction 농장 은퇴 — 구조화 제재 데이터(sanctionDf)는 정부 native 태깅
        # 없어 panel 재현 불가. 신호 드롭(consumer 전부 None 내성). 텍스트는 panel.search("제재").
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
            - 위임 모듈 — ``providers.dart.docs.finance.*`` 의 동명 함수.
            - ``getFinanceDocAccessor()`` — analysis/financial 이 본 accessor 호출 entry.

        Requires:
            - dartlab

        Capabilities:
            - analysis/financial 이 stockCode → 단발 doc 호출 시 본 Protocol 구현체 위임. 예외 silent
              (None 반환) — caller 가 graceful fallback.

        Guide:
            - 사용자 직접 호출 X — analysis 모듈이 자동 dispatch.

        AIContext:
            internal Protocol adapter — AI 가 직접 호출 X. analysis 모듈이 본 accessor 사용.

        LLM Specifications:
            AntiPatterns:
                - 사용자 직접 호출 X — analysis 모듈이 dispatch.
                - 예외 silent (None 반환) → caller None 분기 의무.
            OutputSchema:
                - 위임 모듈 결과 (DataFrame/dict 등) 또는 None (예외 시).
            Prerequisites:
                - 본 회사 docs/finance parquet (위임 모듈별).
            Freshness:
                - 위임 모듈 데이터 갱신 시점.
            Dataflow:
                - stockCode → providers.dart.docs.finance.X → 본 메서드.
            TargetMarkets:
                - KR (DART) 한정.
        """
        # docs.finance.contingentLiability 농장 은퇴 — 구조화 우발부채 데이터 panel 재현 불가.
        # 신호 드롭(consumer None 내성). 텍스트는 panel.search("우발부채").
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
            - 위임 모듈 — ``providers.dart.docs.finance.*`` 의 동명 함수.
            - ``getFinanceDocAccessor()`` — analysis/financial 이 본 accessor 호출 entry.

        Requires:
            - dartlab

        Capabilities:
            - analysis/financial 이 stockCode → 단발 doc 호출 시 본 Protocol 구현체 위임. 예외 silent
              (None 반환) — caller 가 graceful fallback.

        Guide:
            - 사용자 직접 호출 X — analysis 모듈이 자동 dispatch.

        AIContext:
            internal Protocol adapter — AI 가 직접 호출 X. analysis 모듈이 본 accessor 사용.

        LLM Specifications:
            AntiPatterns:
                - 사용자 직접 호출 X — analysis 모듈이 dispatch.
                - 예외 silent (None 반환) → caller None 분기 의무.
            OutputSchema:
                - 위임 모듈 결과 (DataFrame/dict 등) 또는 None (예외 시).
            Prerequisites:
                - 본 회사 docs/finance parquet (위임 모듈별).
            Freshness:
                - 위임 모듈 데이터 갱신 시점.
            Dataflow:
                - stockCode → providers.dart.docs.finance.X → 본 메서드.
            TargetMarkets:
                - KR (DART) 한정.
        """
        # docs.finance.executive 농장 은퇴 — 개인별 임원 시계열 panel 재현 불가. 신호 드롭
        # (consumer None 내성). 텍스트는 panel.search("임원").
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
            - 위임 모듈 — ``providers.dart.docs.finance.*`` 의 동명 함수.
            - ``getFinanceDocAccessor()`` — analysis/financial 이 본 accessor 호출 entry.

        Requires:
            - dartlab

        Capabilities:
            - analysis/financial 이 stockCode → 단발 doc 호출 시 본 Protocol 구현체 위임. 예외 silent
              (None 반환) — caller 가 graceful fallback.

        Guide:
            - 사용자 직접 호출 X — analysis 모듈이 자동 dispatch.

        AIContext:
            internal Protocol adapter — AI 가 직접 호출 X. analysis 모듈이 본 accessor 사용.

        LLM Specifications:
            AntiPatterns:
                - 사용자 직접 호출 X — analysis 모듈이 dispatch.
                - 예외 silent (None 반환) → caller None 분기 의무.
            OutputSchema:
                - 위임 모듈 결과 (DataFrame/dict 등) 또는 None (예외 시).
            Prerequisites:
                - 본 회사 docs/finance parquet (위임 모듈별).
            Freshness:
                - 위임 모듈 데이터 갱신 시점.
            Dataflow:
                - stockCode → providers.dart.docs.finance.X → 본 메서드.
            TargetMarkets:
                - KR (DART) 한정.
        """
        # docs.finance.relatedPartyTx 농장 은퇴 — 구조화 거래(guaranteeDf/assetTxDf/revenueTxDf)
        # panel 재현 불가. 신호 드롭(consumer None 내성). 텍스트는 panel.search("특수관계자").
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
            - 위임 모듈 — ``providers.dart.docs.finance.*`` 의 동명 함수.
            - ``getFinanceDocAccessor()`` — analysis/financial 이 본 accessor 호출 entry.

        Requires:
            - dartlab

        Capabilities:
            - analysis/financial 이 stockCode → 단발 doc 호출 시 본 Protocol 구현체 위임. 예외 silent
              (None 반환) — caller 가 graceful fallback.

        Guide:
            - 사용자 직접 호출 X — analysis 모듈이 자동 dispatch.

        AIContext:
            internal Protocol adapter — AI 가 직접 호출 X. analysis 모듈이 본 accessor 사용.

        LLM Specifications:
            AntiPatterns:
                - 사용자 직접 호출 X — analysis 모듈이 dispatch.
                - 예외 silent (None 반환) → caller None 분기 의무.
            OutputSchema:
                - 위임 모듈 결과 (DataFrame/dict 등) 또는 None (예외 시).
            Prerequisites:
                - 본 회사 docs/finance parquet (위임 모듈별).
            Freshness:
                - 위임 모듈 데이터 갱신 시점.
            Dataflow:
                - stockCode → providers.dart.docs.finance.X → 본 메서드.
            TargetMarkets:
                - KR (DART) 한정.
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
            - 위임 모듈 — ``providers.dart.docs.finance.*`` 의 동명 함수.
            - ``getFinanceDocAccessor()`` — analysis/financial 이 본 accessor 호출 entry.

        Requires:
            - dartlab

        Capabilities:
            - analysis/financial 이 stockCode → 단발 doc 호출 시 본 Protocol 구현체 위임. 예외 silent
              (None 반환) — caller 가 graceful fallback.

        Guide:
            - 사용자 직접 호출 X — analysis 모듈이 자동 dispatch.

        AIContext:
            internal Protocol adapter — AI 가 직접 호출 X. analysis 모듈이 본 accessor 사용.

        LLM Specifications:
            AntiPatterns:
                - 사용자 직접 호출 X — analysis 모듈이 dispatch.
                - 예외 silent (None 반환) → caller None 분기 의무.
            OutputSchema:
                - 위임 모듈 결과 (DataFrame/dict 등) 또는 None (예외 시).
            Prerequisites:
                - 본 회사 docs/finance parquet (위임 모듈별).
            Freshness:
                - 위임 모듈 데이터 갱신 시점.
            Dataflow:
                - stockCode → providers.dart.docs.finance.X → 본 메서드.
            TargetMarkets:
                - KR (DART) 한정.
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
            - 위임 모듈 — ``providers.dart.docs.finance.*`` 의 동명 함수.
            - ``getFinanceDocAccessor()`` — analysis/financial 이 본 accessor 호출 entry.

        Requires:
            - dartlab

        Capabilities:
            - analysis/financial 이 stockCode → 단발 doc 호출 시 본 Protocol 구현체 위임. 예외 silent
              (None 반환) — caller 가 graceful fallback.

        Guide:
            - 사용자 직접 호출 X — analysis 모듈이 자동 dispatch.

        AIContext:
            internal Protocol adapter — AI 가 직접 호출 X. analysis 모듈이 본 accessor 사용.

        LLM Specifications:
            AntiPatterns:
                - 사용자 직접 호출 X — analysis 모듈이 dispatch.
                - 예외 silent (None 반환) → caller None 분기 의무.
            OutputSchema:
                - 위임 모듈 결과 (DataFrame/dict 등) 또는 None (예외 시).
            Prerequisites:
                - 본 회사 docs/finance parquet (위임 모듈별).
            Freshness:
                - 위임 모듈 데이터 갱신 시점.
            Dataflow:
                - stockCode → providers.dart.docs.finance.X → 본 메서드.
            TargetMarkets:
                - KR (DART) 한정.
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
            - 위임 모듈 — ``providers.dart.docs.finance.*`` 의 동명 함수.
            - ``getFinanceDocAccessor()`` — analysis/financial 이 본 accessor 호출 entry.

        Requires:
            - dartlab

        Capabilities:
            - analysis/financial 이 stockCode → 단발 doc 호출 시 본 Protocol 구현체 위임. 예외 silent
              (None 반환) — caller 가 graceful fallback.

        Guide:
            - 사용자 직접 호출 X — analysis 모듈이 자동 dispatch.

        AIContext:
            internal Protocol adapter — AI 가 직접 호출 X. analysis 모듈이 본 accessor 사용.

        LLM Specifications:
            AntiPatterns:
                - 사용자 직접 호출 X — analysis 모듈이 dispatch.
                - 예외 silent (None 반환) → caller None 분기 의무.
            OutputSchema:
                - 위임 모듈 결과 (DataFrame/dict 등) 또는 None (예외 시).
            Prerequisites:
                - 본 회사 docs/finance parquet (위임 모듈별).
            Freshness:
                - 위임 모듈 데이터 갱신 시점.
            Dataflow:
                - stockCode → providers.dart.docs.finance.X → 본 메서드.
            TargetMarkets:
                - KR (DART) 한정.
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
            - 위임 모듈 — ``providers.dart.docs.finance.*`` 의 동명 함수.
            - ``getFinanceDocAccessor()`` — analysis/financial 이 본 accessor 호출 entry.

        Requires:
            - dartlab

        Capabilities:
            - analysis/financial 이 stockCode → 단발 doc 호출 시 본 Protocol 구현체 위임. 예외 silent
              (None 반환) — caller 가 graceful fallback.

        Guide:
            - 사용자 직접 호출 X — analysis 모듈이 자동 dispatch.

        AIContext:
            internal Protocol adapter — AI 가 직접 호출 X. analysis 모듈이 본 accessor 사용.

        LLM Specifications:
            AntiPatterns:
                - 사용자 직접 호출 X — analysis 모듈이 dispatch.
                - 예외 silent (None 반환) → caller None 분기 의무.
            OutputSchema:
                - 위임 모듈 결과 (DataFrame/dict 등) 또는 None (예외 시).
            Prerequisites:
                - 본 회사 docs/finance parquet (위임 모듈별).
            Freshness:
                - 위임 모듈 데이터 갱신 시점.
            Dataflow:
                - stockCode → providers.dart.docs.finance.X → 본 메서드.
            TargetMarkets:
                - KR (DART) 한정.
        """
        try:
            from dartlab.providers.dart.company import listExportModules

            return list(listExportModules())
        except (ImportError, AttributeError):
            return []


registerFinanceDocAccessor(DartFinanceDocAccessor())
