"""mapping_signals — 5 신호 평가 단위 테스트.

사용자 보고 예시 5 계정을 fixture 로 사용해, autoEligible 합성이
실제 자동 적용 가능 케이스만 통과시키고 오타·noise 는 거부하는지 검증.
"""

from __future__ import annotations

import pytest

from dartlab.core.observability import mapping_signals as ms

pytestmark = pytest.mark.unit


_STANDARD_ACCOUNTS = {
    "other_financial_assets": {"korName": "기타금융자산"},
    "controlling_equity": {"korName": "지배기업소유주지분"},
    "total_assets": {"korName": "자산총계"},
    "investments_in_subsidiaries_cash_flow": {"korName": "종속기업취득으로인한순현금흐름"},
    "dividends_paid": {"korName": "출자금의중간분배"},
}

_MAPPINGS = {
    "자산총계": "total_assets",
}


class TestSignalFrequency:
    @pytest.mark.parametrize("n,expected", [(5, True), (10, True), (4, False), (0, False)])
    def test_threshold(self, n, expected) -> None:
        assert ms.signalFrequency(n) is expected


class TestSignalCorporateDispersion:
    def test_three_unique_passes(self) -> None:
        assert ms.signalCorporateDispersion(["005930", "000660", "035720"]) is True

    def test_two_unique_fails(self) -> None:
        assert ms.signalCorporateDispersion(["005930", "000660", "005930"]) is False

    def test_blanks_excluded(self) -> None:
        assert ms.signalCorporateDispersion(["005930", "", ""]) is False

    def test_empty(self) -> None:
        assert ms.signalCorporateDispersion([]) is False


class TestSignalKorNameMatch:
    def test_high_similarity_passes(self) -> None:
        snake, score = ms.signalKorNameMatch("기타의금융자산", _STANDARD_ACCOUNTS)
        assert snake == "other_financial_assets"
        assert score >= 0.85

    def test_unrelated_returns_none(self) -> None:
        snake, score = ms.signalKorNameMatch("커피전문점매출", _STANDARD_ACCOUNTS)
        assert snake is None
        assert score < 0.85

    def test_empty_inputs(self) -> None:
        assert ms.signalKorNameMatch("", _STANDARD_ACCOUNTS) == (None, 0.0)
        assert ms.signalKorNameMatch("자산총계", {}) == (None, 0.0)


class TestSignalIfrsSynonym:
    def test_direct_hit(self) -> None:
        assert ms.signalIfrsSynonym("", "자산총계", _MAPPINGS) == "total_assets"

    def test_normalized_hit(self) -> None:
        # 공백·괄호 제거 정규화 후 mappings 매칭.
        assert ms.signalIfrsSynonym("", "자산 총계 ", _MAPPINGS) == "total_assets"

    def test_no_hit(self) -> None:
        assert ms.signalIfrsSynonym("", "없는것", _MAPPINGS) is None


class TestSignalTypoReject:
    def test_one_jamo_diff_rejected(self) -> None:
        rejected, fix = ms.signalTypoReject("지배지업소유주지분", _STANDARD_ACCOUNTS)
        assert rejected is True
        assert fix == "지배기업소유주지분"

    def test_exact_match_not_typo(self) -> None:
        rejected, fix = ms.signalTypoReject("자산총계", _STANDARD_ACCOUNTS)
        assert rejected is False
        assert fix is None

    def test_far_string_not_typo(self) -> None:
        rejected, fix = ms.signalTypoReject("기타의금융자산", _STANDARD_ACCOUNTS)
        assert rejected is False
        assert fix is None


class TestEvaluate:
    def test_other_financial_assets_passes_all(self) -> None:
        """`기타의금융자산` — S1·S2·S3 통과, S5 거부 아님."""
        r = ms.evaluate(
            accountId="-표준계정코드 미사용-",
            accountNm="기타의금융자산",
            occurrenceCount=14,
            stockCodes=["005930", "000660", "035720"],
            standardAccounts=_STANDARD_ACCOUNTS,
            mappings={},
        )
        assert r.autoEligible is True
        assert r.suggestedSnakeId == "other_financial_assets"
        assert r.confidence >= 0.85

    def test_typo_rejected_even_with_signals(self) -> None:
        """`지배지업소유주지분` — typo 거부, autoEligible False."""
        r = ms.evaluate(
            accountId="-표준계정코드 미사용-",
            accountNm="지배지업소유주지분",
            occurrenceCount=6,
            stockCodes=["005930", "000660", "035720"],
            standardAccounts=_STANDARD_ACCOUNTS,
            mappings={},
        )
        assert r.autoEligible is False
        assert r.s5TypoSuspect is True
        assert r.s5SuggestedFix == "지배기업소유주지분"

    def test_low_frequency_rejected(self) -> None:
        r = ms.evaluate(
            accountId="",
            accountNm="기타의금융자산",
            occurrenceCount=3,
            stockCodes=["005930", "000660", "035720"],
            standardAccounts=_STANDARD_ACCOUNTS,
            mappings={},
        )
        assert r.s1Frequency is False
        assert r.autoEligible is False

    def test_single_corporate_rejected(self) -> None:
        r = ms.evaluate(
            accountId="",
            accountNm="기타의금융자산",
            occurrenceCount=14,
            stockCodes=["005930", "005930", "005930"],
            standardAccounts=_STANDARD_ACCOUNTS,
            mappings={},
        )
        assert r.s2Dispersion is False
        assert r.autoEligible is False

    def test_ifrs_synonym_hit_uses_s4(self) -> None:
        """mappings 에 정확 hit 이 있으면 S4 우선 사용."""
        r = ms.evaluate(
            accountId="",
            accountNm="자산총계",
            occurrenceCount=5,
            stockCodes=["005930", "000660", "035720"],
            standardAccounts=_STANDARD_ACCOUNTS,
            mappings=_MAPPINGS,
        )
        assert r.suggestedSnakeId == "total_assets"
        assert r.s4IfrsSynonymSnakeId == "total_assets"
        assert r.autoEligible is True

    def test_breakdown_dict(self) -> None:
        r = ms.evaluate(
            accountId="",
            accountNm="기타의금융자산",
            occurrenceCount=14,
            stockCodes=["005930", "000660", "035720"],
            standardAccounts=_STANDARD_ACCOUNTS,
            mappings={},
        )
        bd = r.breakdown()
        assert bd["s1"] is True
        assert bd["s2"] is True
        assert bd["s3Snake"] == "other_financial_assets"
        assert bd["s5Typo"] is False
