"""mappingHashRecommend 회귀 가드.

본 모듈은 *후보 추천 보조 도구* (자동 매핑 X). 회귀 가드 6 종:
- top_k 반환 길이 / sj 필터 / 알려진 변형 매칭 / lazy load idempotent /
  카카오 None sample deterministic snapshot / 미매핑 한글 low confidence.

회귀 시그널 — sample top-1 환각 변경 시 fail (운영자 검토 패턴 회귀).
"""

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module", autouse=True)
def _resetCache():
    """module 단위 cache reset — 다른 fixture 의 사전 patch 와 격리."""
    from dartlab.reference.mapping import mappingHashRecommend as M

    M._invalidate()
    yield
    M._invalidate()


def test_recommend_returns_top_k():
    """topK=3 → 정확히 3 개 (사전 충분히 큰 환경)."""
    from dartlab.reference.mapping.mappingHashRecommend import recommend

    cands = recommend("매출액", sj="IS", topK=3)
    assert len(cands) == 3
    assert all(hasattr(c, "snakeId") and hasattr(c, "confidence") for c in cands)


def test_recommend_sj_filter():
    """sj='BS' 입력 시 모든 후보의 d['sj'] == 'BS' (가드 strict)."""
    from dartlab.reference.mapping import mappingHashRecommend as M
    from dartlab.reference.mapping.mappingHashRecommend import recommend

    cache = M._loadDict()
    snakeToSj = {d["snake"]: d["sj"] for d in cache}
    cands = recommend("유동자산", sj="BS", topK=5)
    assert cands, "sj=BS 후보 없음 — 사전 손상 의심"
    for c in cands:
        assert snakeToSj.get(c.snakeId) == "BS", f"sj 필터 위반: {c.snakeId} sj={snakeToSj.get(c.snakeId)}"


def test_recommend_known_pair_high():
    """사전 박힌 *비유동상각후원가금융자산* 입력 → financial_assets_at_amortised_cost + confidence high.

    V10 카카오 None 실증 케이스. 단일 답이 압도적인 경우 high confidence.
    """
    from dartlab.reference.mapping.mappingHashRecommend import recommend

    cands = recommend("비유동상각후원가금융자산", sj="BS")
    assert cands, "후보 0 — 사전 또는 hash 로직 회귀"
    top = cands[0]
    assert top.snakeId == "financial_assets_at_amortised_cost", f"top-1 snakeId 회귀: got={top.snakeId}"
    assert top.confidence == "high", f"confidence 약화 회귀: got={top.confidence}"
    assert top.overlap >= 0.5, f"overlap 약화: got={top.overlap}"


def test_recommend_kakao_sample_deterministic():
    """카카오 None 29 중 3 sample — top-1 snakeId deterministic snapshot.

    환각 변경 시 fail (사람 검토 패턴 회귀).
    """
    from dartlab.reference.mapping.mappingHashRecommend import recommend

    snapshot = {
        ("장기매도가능증권의 처분", "CF"): "decrease_in_availableforsale_financial_assets",
        ("비유동상각후원가금융자산", "BS"): "financial_assets_at_amortised_cost",
        ("기타투자활동 현금 유입", "CF"): "cash_flows_from_investing_activities",
    }
    for (nm, sj), expectedSnake in snapshot.items():
        cands = recommend(nm, sj=sj)
        assert cands, f"후보 0: {nm!r}"
        assert cands[0].snakeId == expectedSnake, (
            f"snapshot 회귀: {nm!r} → got={cands[0].snakeId} expected={expectedSnake}"
        )


def test_recommend_empty_input():
    """빈 한글 입력 → 빈 list (방어)."""
    from dartlab.reference.mapping.mappingHashRecommend import recommend

    assert recommend("") == []
    assert recommend("", sj="BS") == []


def test_recommend_lazy_load_idempotent():
    """_loadDict() 여러 번 호출 결과 동일 (singleton cache)."""
    from dartlab.reference.mapping import mappingHashRecommend as M

    a = M._loadDict()
    b = M._loadDict()
    assert a is b, "lazy cache singleton 위반 — 매 호출마다 재계산"
    assert len(a) > 30_000, f"사전 한글 매핑 부족: {len(a)}"
