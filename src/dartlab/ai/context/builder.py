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

from dartlab.ai.context.budget import budgetFor, trim
from dartlab.ai.context.bundle import ContextBundle, ContextPart
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
            getattr(self.company, "stockCode", None) or getattr(self.company, "ticker", None)
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
        # SuperMaster — 질문 관련 API top-k + 과거 성공 사례 top-k 동적 주입
        parts.extend(self._gatherSuperMaster(stockCode))
        # 엔진 가이드 — scan/macro/analysis 등 무인자 가이드를 LLM에 직접 주입
        parts.extend(self._injectEngineGuides())
        # intent → analysis calc selector 라우팅
        parts.extend(self._selectCalcForIntent(intentResult.intent))

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
            _FN_NAMES = {
                Intent.ACT1_BUSINESS: "selectAct1",
                Intent.ACT2_PROFIT: "selectAct2",
                Intent.ACT3_CASH: "selectAct3",
                Intent.ACT4_STABILITY: "selectAct4",
                Intent.ACT5_CAPITAL: "selectAct5",
                Intent.ACT6_OUTLOOK: "selectAct6",
            }
            fn = getattr(mod, _FN_NAMES[intent])
            return fn(self.company)
        except (ImportError, AttributeError, KeyError, Exception):
            return []

    def _gatherSuperMaster(self, stockCode: str | None) -> list[ContextPart]:
        """SuperMaster — CAPABILITIES + Experience retrieval.

        질문 관련 API 상위 5개 + 과거 성공 사례 상위 3개를 HIGH priority로 주입.
        하부 엔진이 바뀌어도 동적 적응.
        """
        try:
            from dartlab.ai.context.bundle import PartPriority
            from dartlab.ai.context.encoder import estimateTokens
            from dartlab.ai.superfeature import getSuperMaster

            master = getSuperMaster()
            api_text, example_text = master.gather(self.question, stockCode=stockCode)

            parts: list[ContextPart] = []
            if api_text:
                parts.append(
                    ContextPart(
                        key="supermaster.apis",
                        text=api_text,
                        priority=PartPriority.HIGH,
                        estimatedTokens=estimateTokens(api_text),
                        source="supermaster:capability",
                    )
                )
            if example_text:
                parts.append(
                    ContextPart(
                        key="supermaster.examples",
                        text=example_text,
                        priority=PartPriority.HIGH,
                        estimatedTokens=estimateTokens(example_text),
                        source="supermaster:experience",
                    )
                )
            return parts
        except (ImportError, Exception):
            return []

    def _injectEngineGuides(self) -> list[ContextPart]:
        """모든 엔진의 무인자 가이드를 LLM에 직접 주입.

        scan 20축, macro 11축, analysis 15축, credit, quant, gather —
        AI가 어떤 기능이 있는지 코드 실행 전에 안다.
        하부 엔진 변화 시 자동 반영. 하드코딩 0.
        """
        try:
            import dartlab
            from dartlab.ai.context.bundle import PartPriority
            from dartlab.ai.context.encoder import estimateTokens

            parts: list[ContextPart] = []

            # scan 가이드 (Company 불필요)
            try:
                scan_guide = dartlab.scan()
                if scan_guide is not None:
                    text = f'<context source="guide:scan">\n## scan 가이드 (전종목 횡단분석)\n{scan_guide}\n</context>'
                    parts.append(ContextPart(
                        key="guide.scan", text=text,
                        priority=PartPriority.MEDIUM,
                        estimatedTokens=estimateTokens(text),
                        source="guide:scan",
                    ))
            except Exception:
                pass

            # macro 가이드 (Company 불필요)
            try:
                macro_guide = dartlab.macro()
                if macro_guide is not None:
                    text = f'<context source="guide:macro">\n## macro 가이드 (경제/시장)\n{macro_guide}\n</context>'
                    parts.append(ContextPart(
                        key="guide.macro", text=text,
                        priority=PartPriority.MEDIUM,
                        estimatedTokens=estimateTokens(text),
                        source="guide:macro",
                    ))
            except Exception:
                pass

            # Company-bound 가이드
            if self.company is not None:
                for name, fn_name in [("analysis", "analysis"), ("credit", "credit"), ("quant", "quant")]:
                    try:
                        fn = getattr(self.company, fn_name)
                        guide = fn()
                        if guide is not None:
                            text = f'<context source="guide:{name}">\n## {name} 가이드\n{guide}\n</context>'
                            parts.append(ContextPart(
                                key=f"guide.{name}", text=text,
                                priority=PartPriority.LOW,
                                estimatedTokens=estimateTokens(text),
                                source=f"guide:{name}",
                            ))
                    except Exception:
                        pass

            return parts
        except (ImportError, Exception):
            return []
