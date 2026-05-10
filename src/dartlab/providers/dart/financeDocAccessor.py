"""DART 재무공시 doc accessor 구현 — FinanceDocAccessor Protocol 등록.

core/financeDocAccessor.py 의 Protocol 을 만족하는 DART 구체 구현.
analysis/financial 이 stockCode → 단발 doc 호출하는 5 메서드 (sanction · contingentLiability ·
executive · relatedPartyTx · pivotDividend) 를 위임.

import 시점에 자동 register — analysis 가 getFinanceDocAccessor() 호출 시 provider 자동 로드.
"""

from __future__ import annotations

from typing import Any

from dartlab.core.financeDocAccessor import registerFinanceDocAccessor


class DartFinanceDocAccessor:
    """DART providers 의 단발 doc 호출 모음 — FinanceDocAccessor Protocol 구현체."""

    def sanction(self, stockCode: str) -> Any | None:
        """제재 공시 doc 조회 — providers/dart/docs/finance/sanction 위임. 실패 시 None."""
        from dartlab.providers.dart.docs.finance.sanction import sanction

        try:
            return sanction(stockCode)
        except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
            return None

    def contingentLiability(self, stockCode: str) -> Any | None:
        """우발부채 doc 조회 — providers/dart/docs/finance/contingentLiability 위임. 실패 시 None."""
        from dartlab.providers.dart.docs.finance.contingentLiability import contingentLiability

        try:
            return contingentLiability(stockCode)
        except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
            return None

    def executive(self, stockCode: str) -> Any | None:
        """임원 보수/이력 doc 조회 — providers/dart/docs/finance/executive 위임. 실패 시 None."""
        from dartlab.providers.dart.docs.finance.executive import executive

        try:
            return executive(stockCode)
        except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
            return None

    def relatedPartyTx(self, stockCode: str) -> Any | None:
        """특수관계자 거래 doc 조회 — providers/dart/docs/finance/relatedPartyTx 위임. 실패 시 None."""
        from dartlab.providers.dart.docs.finance.relatedPartyTx import relatedPartyTx

        try:
            return relatedPartyTx(stockCode)
        except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
            return None

    def pivotDividend(self, stockCode: str) -> Any | None:
        """배당 pivot 조회 — providers/dart/report/pivot 위임. 실패 시 None."""
        from dartlab.providers.dart.report.pivot import pivotDividend

        try:
            return pivotDividend(stockCode)
        except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
            return None

    def buildAnnual(self, stockCode: str) -> Any | None:
        """연간 시리즈 빌드 — providers/dart/finance/pivot.buildAnnual 위임. 실패 시 None."""
        from dartlab.providers.dart.finance.pivot import buildAnnual

        try:
            return buildAnnual(stockCode)
        except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
            return None

    def buildTimeseries(self, stockCode: str) -> Any | None:
        """분기 시리즈 빌드 — providers/dart/finance/pivot.buildTimeseries 위임. 실패 시 None."""
        from dartlab.providers.dart.finance.pivot import buildTimeseries

        try:
            return buildTimeseries(stockCode)
        except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
            return None


registerFinanceDocAccessor(DartFinanceDocAccessor())
