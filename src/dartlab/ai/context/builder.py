"""ContextBuilder — Phase 1 메인 진입점.

질문 + Company + provider → ContextBundle.

설계:
1. classifyIntent() 로 질문 의도 파악
2. legacy selectors 호출 → 기존 5개 pre-grounding을 ContextPart로
3. (Phase 1.5) intent별 act selector 호출
4. budget.trim() 으로 토큰 예산 적용
5. ContextBundle 반환

Phase 1 보장: 기존 _analyze_inner 동작과 동일 (legacy selectors만 사용).
DARTLAB_CONTEXT_V2=1 환경 변수로 활성화.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dartlab.ai.context.bundle import ContextBundle, ContextPart
from dartlab.ai.context.budget import budgetFor, trim
from dartlab.ai.context.intent import Intent, classifyIntent
from dartlab.ai.context.selectors import (
    selectCompanySearch,
    selectDisclosureBrief,
    selectExternalSearch,
    selectInsightHints,
    selectMemoryHints,
    selectPlaybookBullets,
)


@dataclass
class ContextBuilder:
    """질문 → ContextBundle 빌더.

    사용::

        bundle = ContextBuilder(
            question="삼성전자 마진 추세는?",
            company=c,
            provider="gemini",
        ).build()

        userParts = bundle.toUserParts()  # 기존 _analyze_inner 호환
    """

    question: str
    company: Any | None = None
    provider: str | None = None
    budgetTokens: int | None = None  # None → provider별 기본값

    def build(self) -> ContextBundle:
        if not self.question or not self.question.strip():
            return ContextBundle(intent=Intent.ACT_ALL.value)

        # Company 메타 추출
        stockCode = (
            getattr(self.company, "stockCode", None)
            or getattr(self.company, "ticker", None)
            if self.company is not None
            else None
        )
        corpName = getattr(self.company, "corpName", None) if self.company is not None else None

        # 1. Intent 분류
        intentResult = classifyIntent(self.question, hasCompany=self.company is not None)

        # 2. selector 호출 (legacy + ACE playbook + analysis calc)
        parts: list[ContextPart] = []
        parts.extend(selectCompanySearch(self.question, self.company))
        parts.extend(selectDisclosureBrief(stockCode))
        parts.extend(selectExternalSearch(self.question, stockCode, corpName))
        parts.extend(selectMemoryHints(stockCode))
        parts.extend(selectInsightHints(stockCode, self.company))
        # ACE evolving playbook — intent별 학습된 분석 지침 주입
        parts.extend(selectPlaybookBullets(intentResult.intent.value, self.company))
        # intent → analysis calc selector 라우팅
        parts.extend(self._selectCalcForIntent(intentResult.intent))
        # Phase 2: 인과 질문("왜") → graph traversal
        try:
            from dartlab.ai.context.selectors.graph import selectGraphCauses
            parts.extend(selectGraphCauses(self.question, self.company))
        except ImportError:
            pass

        # 3. 분석 대상 라벨 (CRITICAL — 항상 포함)
        if corpName and stockCode:
            from dartlab.ai.context.bundle import PartPriority
            from dartlab.ai.context.encoder import estimateTokens

            label = f"분석 대상: {corpName} (종목코드: {stockCode})"
            parts.insert(
                0,
                ContextPart(
                    key="company.label",
                    text=label,
                    priority=PartPriority.CRITICAL,
                    estimatedTokens=estimateTokens(label),
                    source="company.meta",
                ),
            )

        # 4. concept selector (Company 불필요)
        if intentResult.intent == Intent.CONCEPT:
            try:
                from dartlab.ai.context.selectors.concept import selectConcept
                parts.extend(selectConcept(self.question))
            except ImportError:
                pass

        # 5. 예산 트리밍
        budget = self.budgetTokens or budgetFor(self.provider)
        kept, dropped = trim(parts, budgetTokens=budget)

        totalTokens = sum(p.estimatedTokens for p in kept)
        return ContextBundle(
            parts=kept,
            intent=intentResult.intent.value,
            totalTokens=totalTokens,
            droppedKeys=dropped,
        )

    def _selectCalcForIntent(self, intent: Intent) -> list[ContextPart]:
        """intent → analysis calc selector 라우팅.

        Company 없으면 빈 리스트. calc 실패 시 빈 리스트 (graceful).
        ACT_ALL → 핵심 3개(margin + cashflow + distress)만.
        """
        if self.company is None:
            return []
        try:
            _ROUTER = {
                Intent.ACT1_BUSINESS: "dartlab.ai.context.selectors.act1",
                Intent.ACT2_PROFIT: "dartlab.ai.context.selectors.act2",
                Intent.ACT3_CASH: "dartlab.ai.context.selectors.act3",
                Intent.ACT4_STABILITY: "dartlab.ai.context.selectors.act4",
                Intent.ACT5_CAPITAL: "dartlab.ai.context.selectors.act5",
                Intent.ACT6_OUTLOOK: "dartlab.ai.context.selectors.act6",
                Intent.COMPARE: "dartlab.ai.context.selectors.compare",
            }
            if intent == Intent.ACT_ALL:
                # 핵심 3축만 주입 (마진 + 현금흐름 + 안정성)
                parts: list[ContextPart] = []
                try:
                    from dartlab.ai.context.selectors.act2 import selectAct2
                    parts.extend(selectAct2(self.company))
                except (ImportError, Exception):
                    pass
                try:
                    from dartlab.ai.context.selectors.act3 import selectAct3
                    parts.extend(selectAct3(self.company))
                except (ImportError, Exception):
                    pass
                try:
                    from dartlab.ai.context.selectors.act4 import selectAct4
                    parts.extend(selectAct4(self.company))
                except (ImportError, Exception):
                    pass
                return parts

            module_path = _ROUTER.get(intent)
            if not module_path:
                return []

            import importlib
            mod = importlib.import_module(module_path)
            # 함수 이름 규칙: selectAct{N}, selectCompare
            fn_name = f"select{intent.value.split('_')[0].title()}" if "_" in intent.value else f"select{intent.value.title()}"
            # 실제 함수명 매핑
            _FN_NAMES = {
                Intent.ACT1_BUSINESS: "selectAct1",
                Intent.ACT2_PROFIT: "selectAct2",
                Intent.ACT3_CASH: "selectAct3",
                Intent.ACT4_STABILITY: "selectAct4",
                Intent.ACT5_CAPITAL: "selectAct5",
                Intent.ACT6_OUTLOOK: "selectAct6",
                Intent.COMPARE: "selectCompare",
            }
            fn = getattr(mod, _FN_NAMES[intent])
            if intent == Intent.COMPARE:
                return fn(self.company)
            return fn(self.company)
        except (ImportError, AttributeError, KeyError, Exception):
            return []
