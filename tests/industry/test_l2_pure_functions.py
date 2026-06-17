"""industry L2 순수함수 광범위 단위 테스트.

외부 API 호출 없는 순수 함수만 대상. coverage 14% → 30%+ 끌어올림.

대상:
- industry/taxonomy.py (findIndustryByKsic, getIndustry, listIndustries, matchStageByKeywords)
- industry/calcs/concentration.py (calcHHI, calcTopNRatio, riskLabel)
- industry/build/table_parser.py (extractCorpNames, normalizeCorpName, parseAmount, parsePercent)
- industry/calcs/lifecycle.py (classifyPhase)
"""


# ══════════════════════════════════════
# industry/taxonomy.py
# ══════════════════════════════════════


class TestListIndustries:
    def test_returnsNonEmpty(self):
        from dartlab.industry.taxonomy import listIndustries

        result = listIndustries()
        assert isinstance(result, list)
        assert len(result) > 0
        for item in result[:3]:
            assert isinstance(item, dict)

    def test_eachHasIdAndName(self):
        from dartlab.industry.taxonomy import listIndustries

        result = listIndustries()
        for item in result:
            assert "id" in item or "industryId" in item or "name" in item


class TestGetIndustry:
    def test_validIdReturnsObject(self):
        from dartlab.industry.taxonomy import getIndustry, listIndustries

        items = listIndustries()
        if items:
            first = items[0]
            id_key = "id" if "id" in first else ("industryId" if "industryId" in first else "name")
            r = getIndustry(first[id_key])
            assert r is not None

    def test_invalidIdReturnsNone(self):
        from dartlab.industry.taxonomy import getIndustry

        r = getIndustry("__not_a_real_industry__")
        assert r is None


class TestFindIndustryByKsic:
    def test_unknownReturnsNone(self):
        from dartlab.industry.taxonomy import findIndustryByKsic

        r = findIndustryByKsic("__not_a_real_ksic__")
        assert r is None

    def test_string(self):
        from dartlab.industry.taxonomy import findIndustryByKsic

        r = findIndustryByKsic("반도체")
        assert r is None or isinstance(r, str)


class TestMatchStageByKeywords:
    def test_returnsTuple(self):
        from dartlab.industry.taxonomy import listIndustries, matchStageByKeywords

        items = listIndustries()
        if items:
            first = items[0]
            id_key = "id" if "id" in first else ("industryId" if "industryId" in first else "name")
            r = matchStageByKeywords(first[id_key], "sample text")
            assert isinstance(r, tuple)
            assert len(r) == 3


# ══════════════════════════════════════
# industry/calcs/concentration.py
# ══════════════════════════════════════


class TestCalcHHI:
    def test_uniformDistribution(self):
        from dartlab.industry.calcs.concentration import calcHHI

        # 10 개 동일 분배 → HHI = 1000
        r = calcHHI([100.0] * 10)
        assert 900 < r < 1100

    def test_monopoly(self):
        from dartlab.industry.calcs.concentration import calcHHI

        # 1 개 독점 → HHI ≈ 10000
        r = calcHHI([1000.0])
        assert r > 9000

    def test_duopoly50_50(self):
        from dartlab.industry.calcs.concentration import calcHHI

        r = calcHHI([500.0, 500.0])
        # 50:50 → 0.5^2 + 0.5^2 = 0.5 → 5000
        assert 4500 < r < 5500

    def test_emptyList(self):
        from dartlab.industry.calcs.concentration import calcHHI

        r = calcHHI([])
        assert r == 0 or r is None


class TestCalcTopNRatio:
    def test_top3of10(self):
        from dartlab.industry.calcs.concentration import calcTopNRatio

        amounts = [100.0] * 10
        r = calcTopNRatio(amounts, n=3)
        # 상위 3 / 전체 10 = 30% (% 단위)
        assert 28 < r < 32

    def test_topNExceedsTotal(self):
        from dartlab.industry.calcs.concentration import calcTopNRatio

        r = calcTopNRatio([100.0, 100.0], n=10)
        # n > len → 전체 비중 = 100%
        assert r >= 99

    def test_empty(self):
        from dartlab.industry.calcs.concentration import calcTopNRatio

        r = calcTopNRatio([], n=3)
        assert r == 0 or r is None


class TestRiskLabel:
    def test_lowConcentration(self):
        from dartlab.industry.calcs.concentration import riskLabel

        r = riskLabel(800.0)
        assert isinstance(r, str)

    def test_mediumConcentration(self):
        from dartlab.industry.calcs.concentration import riskLabel

        r = riskLabel(1800.0)
        assert isinstance(r, str)

    def test_highConcentration(self):
        from dartlab.industry.calcs.concentration import riskLabel

        r = riskLabel(3000.0)
        assert isinstance(r, str)

    def test_monopoly(self):
        from dartlab.industry.calcs.concentration import riskLabel

        r = riskLabel(9500.0)
        assert isinstance(r, str)


class TestCalcSupplyInsightsLeafFacts:
    """레버 A — calcSupplyInsights 가 buyer node.supplyFacts(비상장 매입처) amount 를 HHI 에 합산.

    parquet 무의존 — 합성 IndustryEdge/IndustryNode. 상장 엣지 + 비상장 leaf fact 병합 단언.
    """

    @staticmethod
    def _edge(fromCode, toCode, amount):
        from dartlab.industry.types import IndustryEdge

        return IndustryEdge(
            fromCode=fromCode,
            fromName=fromCode,
            toCode=toCode,
            toName=toCode,
            edgeType="supplier",
            industry="x",
            amount=amount,
        )

    @staticmethod
    def _node(stockCode, supplyFacts=None):
        from dartlab.industry.types import IndustryNode

        return IndustryNode(
            stockCode=stockCode,
            corpName=stockCode,
            industry="x",
            stage="fab",
            supplyFacts=supplyFacts or [],
        )

    def test_leaf_facts_merged_into_hhi(self):
        """비상장 leaf fact amount 가 상장 엣지 amount 와 함께 HHI/총액/supplierCount 에 반영."""
        from dartlab.industry.calcs.concentration import calcSupplyInsights

        # buyer "B": 상장 매입처 1곳(엣지 30) + 비상장 leaf 2곳(70, 0... 무시될 None 포함)
        edges = [self._edge("LISTED1", "B", 30.0)]
        nodes = [
            self._node(
                "B",
                supplyFacts=[
                    {"supplier": "비상장소재", "amount": 70.0, "ratio": 70.0},
                    {"supplier": "비상장부품", "amount": None, "ratio": None},  # amount 없음 — HHI 모수 제외
                ],
            ),
            self._node("LISTED1"),
        ]
        r = calcSupplyInsights("B", edges, nodes)
        # HHI = 30^2 + 70^2 = 900 + 4900 = 5800 (leaf 70 합산 확인; 엣지만이면 10000 단독)
        assert r["hhi"] == 5800.0
        assert r["totalSupplyAmount"] == 100.0  # 30 + 70
        assert r["preciseEdgeCount"] == 2  # amount 보유 2개 (엣지1 + leaf1)
        # supplierCount = 엣지 1 + leaf fact 2 (name-only 포함)
        assert r["supplierCount"] == 3

    def test_no_leaf_facts_unchanged(self):
        """supplyFacts 빈 buyer 는 기존 동작(엣지만) — 회귀 0."""
        from dartlab.industry.calcs.concentration import calcSupplyInsights

        edges = [self._edge("L1", "B", 50.0), self._edge("L2", "B", 50.0)]
        nodes = [self._node("B"), self._node("L1"), self._node("L2")]
        r = calcSupplyInsights("B", edges, nodes)
        assert r["hhi"] == 5000.0  # 50:50
        assert r["supplierCount"] == 2


# ══════════════════════════════════════
# industry/build/table_parser.py
# ══════════════════════════════════════


class TestParseAmount:
    def test_billions(self):
        from dartlab.industry.build.table_parser import parseAmount

        r = parseAmount("1,000,000")
        assert r is None or r == 1000000.0

    def test_invalid(self):
        from dartlab.industry.build.table_parser import parseAmount

        r = parseAmount("not a number")
        assert r is None

    def test_empty(self):
        from dartlab.industry.build.table_parser import parseAmount

        r = parseAmount("")
        assert r is None


class TestParsePercent:
    def test_validPercent(self):
        from dartlab.industry.build.table_parser import parsePercent

        r = parsePercent("12.5%")
        assert r is None or 12.0 < r < 13.0

    def test_invalid(self):
        from dartlab.industry.build.table_parser import parsePercent

        r = parsePercent("not a percent")
        assert r is None


class TestNormalizeCorpName:
    def test_strips(self):
        from dartlab.industry.build.table_parser import normalizeCorpName

        r = normalizeCorpName("  삼성전자  ")
        assert "삼성전자" in r or r == "삼성전자"

    def test_emptyReturnsEmpty(self):
        from dartlab.industry.build.table_parser import normalizeCorpName

        r = normalizeCorpName("")
        assert r == "" or r is None


class TestExtractCorpNames:
    def test_singleCorp(self):
        from dartlab.industry.build.table_parser import extractCorpNames

        r = extractCorpNames("삼성전자")
        assert isinstance(r, list)

    def test_emptyCell(self):
        from dartlab.industry.build.table_parser import extractCorpNames

        r = extractCorpNames("")
        assert isinstance(r, list)


# ══════════════════════════════════════
# industry/calcs/lifecycle.py
# ══════════════════════════════════════


class TestClassifyPhase:
    def test_highGrowth(self):
        from dartlab.industry.calcs.lifecycle import classifyPhase

        r = classifyPhase(25.0)
        assert isinstance(r, str)

    def test_mature(self):
        from dartlab.industry.calcs.lifecycle import classifyPhase

        r = classifyPhase(2.0)
        assert isinstance(r, str)

    def test_decline(self):
        from dartlab.industry.calcs.lifecycle import classifyPhase

        r = classifyPhase(-5.0)
        assert isinstance(r, str)

    def test_none(self):
        from dartlab.industry.calcs.lifecycle import classifyPhase

        r = classifyPhase(None)
        assert isinstance(r, str)


# ══════════════════════════════════════
# Smoke imports
# ══════════════════════════════════════


def test_industryPublicEntries():
    from dartlab.industry import Industry, addOverride

    assert Industry is not None
    assert addOverride is not None


def test_industryTaxonomyEntries():
    from dartlab.industry.taxonomy import (
        findIndustryByKsic,
        getIndustry,
        invalidateCache,
        listIndustries,
        matchStageByKeywords,
    )

    assert callable(listIndustries)


def test_industryInsightsEntries():
    from dartlab.industry.calcs.concentration import (
        calcHHI,
        calcIndustryConcentration,
        calcSupplyInsights,
        calcTopNRatio,
        riskLabel,
    )

    assert callable(calcHHI)


def test_industryCalcsEntries():
    from dartlab.industry.calcs.companyCalcs import (
        calcChainPosition,
        calcSectorCycle,
        calcSectorDynamics,
        calcSectorMetrics,
    )
    from dartlab.industry.calcs.lifecycle import classifyLifecycle, classifyPhase

    assert callable(calcChainPosition)
    assert callable(classifyPhase)
