"""applyOverrides 의 ``exclude: true`` 메커니즘 unit 테스트.

stage1-3 (KSIC/제품/docs) 의 분류 오류를 영구 차단하는 능력 검증.
실 overrides.json 의존 X — _loadOverrides 를 monkeypatch.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]


def _makeNode(stockCode: str, industry: str, stage: str = "solution"):
    from dartlab.industry.types import IndustryNode

    return IndustryNode(
        stockCode=stockCode,
        corpName=f"corp-{stockCode}",
        industry=industry,
        stage=stage,
        confidence=0.8,
        source="auto",
    )


class TestApplyOverridesExclude:
    def test_exclude_removes_pair(self, monkeypatch):
        """(stockCode, industryId) 쌍이 exclude 되면 노드 리스트에서 제거."""
        from dartlab.industry.build import stage4_review

        monkeypatch.setattr(
            stage4_review,
            "_loadOverrides",
            lambda: {
                "software": [
                    {"stockCode": "034730", "exclude": True, "note": "SK 지주사 오분류"},
                ]
            },
        )

        nodes = [
            _makeNode("034730", "software"),
            _makeNode("034730", "energy"),  # 다른 산업 매핑은 보존
            _makeNode("035420", "software"),  # NAVER 정상
        ]
        out = stage4_review.applyOverrides(nodes)
        keys = {(n.stockCode, n.industry) for n in out}

        assert ("034730", "software") not in keys, "software exclude 적용 실패"
        assert ("034730", "energy") in keys, "다른 산업 매핑은 영향 받으면 안 됨"
        assert ("035420", "software") in keys, "다른 종목은 영향 받으면 안 됨"

    def test_exclude_blocks_stage_re_addition(self, monkeypatch):
        """exclude 된 종목은 같은 industryId 의 일반 매핑이 있어도 절대 추가되지 않는다."""
        from dartlab.industry.build import stage4_review

        # 같은 (code, industryId) 에 exclude 와 일반 매핑이 동시 존재 — exclude 우선
        monkeypatch.setattr(
            stage4_review,
            "_loadOverrides",
            lambda: {
                "software": [
                    {"stockCode": "034730", "exclude": True},
                ],
            },
        )

        nodes = [_makeNode("034730", "software")]
        out = stage4_review.applyOverrides(nodes)
        assert len(out) == 0, "exclude 된 노드가 여전히 존재"

    def test_normal_override_still_works(self, monkeypatch):
        """exclude 와 무관한 일반 매핑 (stage 덮어쓰기) 은 정상 작동."""
        from dartlab.industry.build import stage4_review

        monkeypatch.setattr(
            stage4_review,
            "_loadOverrides",
            lambda: {
                "semiconductor": [
                    {"stockCode": "058470", "stage": "test", "confidence": 1.0},
                ]
            },
        )

        nodes = [_makeNode("058470", "semiconductor", stage="ic")]
        out = stage4_review.applyOverrides(nodes)
        assert len(out) == 1
        assert out[0].stage == "test", "stage 덮어쓰기 실패"
        assert out[0].confidence == 1.0
        assert out[0].source == "manual"

    def test_exclude_and_redirect_combo(self, monkeypatch):
        """exclude 로 software 제거 + 다른 산업에 신규 추가 — SK 정정 시나리오."""
        from dartlab.industry.build import stage4_review

        monkeypatch.setattr(
            stage4_review,
            "_loadOverrides",
            lambda: {
                "software": [
                    {"stockCode": "018670", "exclude": True},
                ],
                "energy": [
                    {
                        "stockCode": "018670",
                        "corpName": "SK가스",
                        "stage": "distribution",
                        "confidence": 1.0,
                    },
                ],
            },
        )

        nodes = [_makeNode("018670", "software")]
        out = stage4_review.applyOverrides(nodes)

        # software 에서 제거 + energy 에 신규
        keys = {(n.stockCode, n.industry, n.stage) for n in out}
        assert ("018670", "software", "solution") not in keys
        assert ("018670", "energy", "distribution") in keys

    def test_no_overrides_unchanged(self, monkeypatch):
        """overrides.json 비어있으면 노드 그대로 반환."""
        from dartlab.industry.build import stage4_review

        monkeypatch.setattr(stage4_review, "_loadOverrides", lambda: {})

        nodes = [_makeNode("005930", "semiconductor"), _makeNode("035420", "software")]
        out = stage4_review.applyOverrides(nodes)
        assert len(out) == 2
        assert {(n.stockCode, n.industry) for n in out} == {
            ("005930", "semiconductor"),
            ("035420", "software"),
        }
