"""ai/context Phase 1 단위 테스트.

scope:
- intent.classifyIntent: 8개 분류 + Company 유무 분기
- encoder.encodeTOON / encodeAuto / estimateTokens
- budget.trim: CRITICAL 보호 + 우선순위 트리밍
- builder.ContextBuilder.build: legacy selectors 통합 + 트리밍 적용

heavy/network 의존성 없음 (legacy selectors 는 import 실패 시 빈 리스트 반환).
"""

from __future__ import annotations

import json

import pytest

from dartlab.ai.context import (
    ContextBuilder,
    ContextBundle,
    ContextPart,
    Intent,
    PartPriority,
    classifyIntent,
)
from dartlab.ai.context.budget import budgetFor, trim
from dartlab.ai.context.encoder import encodeAuto, encodeTOON, estimateTokens

pytestmark = pytest.mark.unit


# ── intent ────────────────────────────────────────────────


class TestIntent:
    def test_empty_question(self):
        r = classifyIntent("", hasCompany=True)
        assert r.intent == Intent.ACT_ALL

    def test_act2_profit(self):
        r = classifyIntent("삼성전자 영업이익률 추세", hasCompany=True)
        assert r.intent == Intent.ACT2_PROFIT
        assert "영업이익률" in r.matchedKeywords

    def test_act3_cash(self):
        r = classifyIntent("OCF 가 NI 를 제대로 따라가나", hasCompany=True)
        assert r.intent == Intent.ACT3_CASH

    def test_act4_stability(self):
        r = classifyIntent("부채비율 위험한가", hasCompany=True)
        assert r.intent == Intent.ACT4_STABILITY

    def test_act5_capital(self):
        r = classifyIntent("배당 정책이 어떻게 되어 있나", hasCompany=True)
        assert r.intent == Intent.ACT5_CAPITAL

    def test_act6_outlook(self):
        r = classifyIntent("적정 PER 얼마쯤", hasCompany=True)
        assert r.intent == Intent.ACT6_OUTLOOK

    def test_compare(self):
        r = classifyIntent("동종업계 대비 마진 순위", hasCompany=True)
        # compare 가 act2 보다 우선
        assert r.intent == Intent.COMPARE

    def test_concept_no_company(self):
        r = classifyIntent("dartlab 사용법 알려줘", hasCompany=False)
        assert r.intent == Intent.CONCEPT

    def test_no_company_prefers_concept_compare(self):
        # Company 없이 막 키워드만 있어도 concept/compare 로 떨어지거나 ACT_ALL
        r = classifyIntent("부채비율이 뭐야", hasCompany=False)
        # 막 키워드만 있고 concept/compare 매칭 없음 → ACT_ALL fallback
        assert r.intent in (Intent.ACT_ALL, Intent.ACT4_STABILITY)


# ── encoder ───────────────────────────────────────────────


class TestEncoder:
    def test_estimate_tokens_empty(self):
        assert estimateTokens("") == 0

    def test_estimate_tokens_basic(self):
        # 30 chars → ~10 tokens
        assert estimateTokens("a" * 30) == 10

    def test_encode_flat_list(self):
        rows = [
            {"year": 2023, "rev": 100, "op": 10},
            {"year": 2024, "rev": 120, "op": 15},
        ]
        out = encodeTOON(rows)
        lines = out.split("\n")
        assert lines[0] == "year|rev|op"
        assert lines[1] == "2023|100|10"
        assert lines[2] == "2024|120|15"

    def test_encode_dict(self):
        d = {"name": "삼성전자", "code": "005930"}
        out = encodeTOON(d)
        assert "name: 삼성전자" in out
        assert "code: 005930" in out

    def test_encode_nested(self):
        d = {
            "company": "삼성전자",
            "history": [
                {"year": 2023, "margin": 0.13},
                {"year": 2024, "margin": 0.15},
            ],
        }
        out = encodeTOON(d)
        assert "history:" in out
        assert "year|margin" in out

    def test_encode_auto_small_uses_json(self):
        d = {"a": 1, "b": 2}
        out = encodeAuto(d)
        # 작은 입력 → JSON
        parsed = json.loads(out)
        assert parsed == d

    def test_encode_auto_large_uses_toon(self):
        rows = [{"year": y, "rev": y * 100} for y in range(2010, 2025)]
        out = encodeAuto(rows)
        # 큰 입력 → TOON 헤더 포함
        assert "year|rev" in out

    def test_encode_none_value(self):
        d = {"a": None, "b": 1}
        out = encodeTOON(d)
        assert "a: -" in out


# ── budget ────────────────────────────────────────────────


class TestBudget:
    def test_budget_for_known_provider(self):
        assert budgetFor("gemini") > 1000
        assert budgetFor("ollama") > 0

    def test_budget_for_unknown_provider(self):
        assert budgetFor("unknown_xyz") == budgetFor(None)

    def test_trim_under_budget(self):
        parts = [
            ContextPart("a", "x" * 30, PartPriority.HIGH, 10),
            ContextPart("b", "y" * 30, PartPriority.LOW, 10),
        ]
        kept, dropped = trim(parts, budgetTokens=100)
        assert len(kept) == 2
        assert dropped == []

    def test_trim_drops_low_priority(self):
        parts = [
            ContextPart("high", "h" * 30, PartPriority.HIGH, 50),
            ContextPart("low", "l" * 30, PartPriority.LOW, 50),
        ]
        kept, dropped = trim(parts, budgetTokens=60)
        assert "high" in [p.key for p in kept]
        assert "low" in dropped

    def test_trim_critical_always_kept(self):
        parts = [
            ContextPart("crit", "c" * 30, PartPriority.CRITICAL, 5000),
            ContextPart("opt", "o" * 30, PartPriority.OPTIONAL, 5000),
        ]
        kept, dropped = trim(parts, budgetTokens=100)
        assert "crit" in [p.key for p in kept]
        assert "opt" in dropped

    def test_trim_preserves_priority_order(self):
        parts = [
            ContextPart("low", "x", PartPriority.LOW, 1),
            ContextPart("high", "x", PartPriority.HIGH, 1),
            ContextPart("critical", "x", PartPriority.CRITICAL, 1),
        ]
        kept, _ = trim(parts, budgetTokens=100)
        # 정렬 결과: critical → high → low
        assert [p.key for p in kept] == ["critical", "high", "low"]


# ── builder ───────────────────────────────────────────────


class _FakeCompany:
    def __init__(self, code="005930", name="삼성전자"):
        self.stockCode = code
        self.corpName = name


class TestContextBuilder:
    def test_empty_question_returns_empty_bundle(self):
        b = ContextBuilder(question="").build()
        assert isinstance(b, ContextBundle)
        assert len(b) == 0

    def test_build_no_company(self):
        # company 없을 때도 크래시하지 않음
        b = ContextBuilder(question="dartlab 사용법", company=None).build()
        assert isinstance(b, ContextBundle)
        # legacy selectors 는 데이터/네트워크 의존이라 빈 결과 가능
        # 그러나 intent 는 항상 분류됨
        assert b.intent in (i.value for i in Intent)

    def test_build_with_company_includes_label(self):
        c = _FakeCompany()
        b = ContextBuilder(question="마진 추세", company=c).build()
        keys = b.keys()
        # company.label 은 CRITICAL 로 항상 포함
        assert "company.label" in keys
        # 라벨 part 텍스트에 종목코드가 포함
        label_part = next(p for p in b.parts if p.key == "company.label")
        assert "005930" in label_part.text
        assert "삼성전자" in label_part.text

    def test_build_intent_classified(self):
        c = _FakeCompany()
        b = ContextBuilder(question="ROE 추이가 어떻게 돼", company=c).build()
        assert b.intent == Intent.ACT2_PROFIT.value

    def test_to_user_parts_compatible(self):
        c = _FakeCompany()
        b = ContextBuilder(question="비용구조", company=c).build()
        ups = b.toUserParts()
        assert isinstance(ups, list)
        assert all(isinstance(x, str) for x in ups)
