"""mapper.py fallback 사전 변형 흡수 회귀 가드.

cycle 5 (2026-05-18) 회귀 — 매핑 138 박은 직후 nonstd_ 17 행 재발.
원인 = mapper.map() fallback 이 *입력 쪽* 만 normalize 하고 *사전 키* 변형을
역인덱스로 못 잡음. 본 가드는 사전쪽 noSpace/noParen 역인덱스 동작 검증.

회귀 시그널 — 본 테스트 실패는 곧 cycle 6+ 의 nonstd_ 재발 위험.
"""

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def mapper():
    from dartlab.core.utils.labels import _loadAccountMappings
    from dartlab.providers.dart.finance.mapper import AccountMapper

    _loadAccountMappings.cache_clear()
    AccountMapper.release()
    return AccountMapper.get()


def test_cycle5_patched_mappings(mapper) -> None:
    """cycle 5 박은 3 매핑이 실제 mapper.map() 결과로 snakeId 반환."""
    assert mapper.map("", "순확정급여자산 재측정요소") == "remeasurement_elements_of_defined_benefit_plans"
    assert mapper.map("", "현금의 기타유입") == "other_cash_inflows"
    assert mapper.map("", "현금의 기타유출입") == "other_cash_inflows_outflows"


def test_dict_no_paren_index_absorbs_variant(mapper) -> None:
    """사전 ``'X(Y)'`` 변형이 입력 ``'X'`` 로 조회될 때 자동 흡수.

    cycle 5 의 케이스 b 본질 — 사전에 ``'현금의기타유입(유출)'`` 만 있고
    입력이 ``'현금의 기타유입'`` 인 경우, 매핑 patch 없이도
    noParen 역인덱스가 흡수해야 함.
    """
    # 사전 키 직접 조회 — patch 의 결과 (직접 hit 단계)
    assert mapper.map("", "현금의기타유입(유출)") == "other_cash_inflows_outflows"
    # 입력 ↔ 사전 변형 흡수 — patch 가 없어도 동일 snakeId
    saved = mapper._mappings.pop("현금의 기타유입", None)
    mapper.__class__._noParenIndex = None  # idx 캐시 리셋
    try:
        got = mapper.map("", "현금의 기타유입")
        assert got == "other_cash_inflows_outflows", f"noParen idx 흡수 실패: got={got!r}"
    finally:
        if saved is not None:
            mapper._mappings["현금의 기타유입"] = saved
            mapper.__class__._noParenIndex = None


def test_dict_no_space_index_absorbs_variant(mapper) -> None:
    """사전 키에 공백 있는 변형이 입력 공백 없는 경우 자동 흡수.

    ACCOUNT_NAME_SYNONYMS 에 ``'당기 순이익': '당기순이익'`` 처럼 이미
    in-code 동의어로 해결되는 케이스가 많지만, 사전 자체에 ``'X Y'``
    형태가 박힌 경우 (희귀) 도 흡수.
    """
    # 사전에 임시로 공백 있는 키 박고 검증
    cls = mapper.__class__
    sentinel_key = "한글 공백 변형_unit_test_sentinel"
    sentinel_snake = "sales"  # 임의의 알려진 snakeId
    mapper._mappings[sentinel_key] = sentinel_snake
    cls._noSpaceIndex = None
    try:
        got = mapper.map("", sentinel_key.replace(" ", ""))
        assert got == sentinel_snake
    finally:
        mapper._mappings.pop(sentinel_key, None)
        cls._noSpaceIndex = None


def test_hyphen_index_still_works(mapper) -> None:
    """기존 noHyphen 역인덱스 (실험 081-001) 회귀 가드."""
    # 사전에 ``'X-Y'`` 형태가 있으면 입력 ``'XY'`` 도 흡수해야 함
    cls = mapper.__class__
    sentinel_key = "단위테스트_하이픈-가드_sentinel"
    sentinel_snake = "sales"
    mapper._mappings[sentinel_key] = sentinel_snake
    cls._noHyphenIndex = None
    try:
        got = mapper.map("", sentinel_key.replace("-", ""))
        assert got == sentinel_snake
    finally:
        mapper._mappings.pop(sentinel_key, None)
        cls._noHyphenIndex = None


def test_unmapped_returns_none(mapper) -> None:
    """완전 미매핑은 None — 환각 매핑 회귀 가드."""
    assert mapper.map("", "절대로존재하지않을_unit_test_key_zzz_999") is None


def test_suffix_trim_absorbs_eok(mapper) -> None:
    """입력 '액' 1글자 suffix 흡수 — 사전 base 키로 fallback.

    cycle 12 회귀: cycle 10 박은 '영업양도로 인한 현금 유입' 와
    '영업양도로 인한 현금유입액' 가 'equality-only' 매칭으로 다른 키 취급 →
    매번 액 suffix 변형 patch 필요. 본 가드는 *입력에 액 suffix 있을 때*
    사전 base 키로 자동 fallback 보장.
    """
    cls = mapper.__class__
    sentinel_base = "테스트_액suffix_가드_sentinel"
    sentinel_trim = sentinel_base + "액"
    sentinel_snake = "sales"
    mapper._mappings[sentinel_base] = sentinel_snake
    cls._noSpaceIndex = cls._noParenIndex = cls._noHyphenIndex = None
    try:
        got = mapper.map("", sentinel_trim)
        assert got == sentinel_snake, f"액 suffix 흡수 실패: got={got!r}"
    finally:
        mapper._mappings.pop(sentinel_base, None)
        cls._noSpaceIndex = cls._noParenIndex = cls._noHyphenIndex = None


def test_suffix_trim_eok_preserves_meaning(mapper) -> None:
    """'매출액' 같은 base key 직접 매핑은 suffix-trim 영향 안 받음 — idempotent."""
    assert mapper.map("", "매출액") == "sales"
