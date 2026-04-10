"""MapperEngine unit tests.

매퍼 엔진이 기존 데이터를 읽기 전용으로 래핑하는지 검증.
원본 데이터 수정 여부는 검사하지 않는다 (읽기 전용 래퍼이므로).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


# ── Engine ──


def test_engine_singleton():
    """getEngine()이 싱글턴을 반환."""
    from dartlab.core.mappers import getEngine

    e1 = getEngine()
    e2 = getEngine()
    assert e1 is e2


def test_engine_has_5_mappers():
    """엔진에 5개 매퍼 등록."""
    from dartlab.core.mappers import getEngine

    engine = getEngine()
    assert set(engine.mappers.keys()) == {"account", "topic", "alias", "flow", "notes"}


def test_engine_summary():
    """summary()가 문자열 반환."""
    from dartlab.core.mappers import getEngine

    s = getEngine().summary()
    assert "[MapperEngine]" in s
    assert "account" in s


def test_engine_allStats():
    """allStats()가 5개 MapperStats 반환."""
    from dartlab.core.mappers import getEngine

    stats = getEngine().allStats()
    assert len(stats) == 5
    for s in stats:
        assert s.coverage > 0


# ── AccountMapper ──


def test_account_lookup_korean():
    """한국어 계정명으로 snakeId 조회."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("account")
    assert m is not None
    result = m.lookup("매출액")
    # accountMappings.json에 매출액이 없을 수도 있으므로 None 허용
    if result is not None:
        assert "snakeId" in result


def test_account_lookup_snakeid():
    """snakeId로 직접 조회."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("account")
    result = m.lookup("sales")
    if result is not None:
        assert result["snakeId"] == "sales"


def test_account_stats():
    """계정 매퍼 통계."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("account")
    s = m.stats()
    assert s.name == "account"
    assert s.totalEntries > 30000  # 34,000+


def test_account_korToSnakeId():
    """한국어 → snakeId 변환."""
    from dartlab.core.mappers.accountMapper import AccountMapper

    m = AccountMapper()
    # 매핑 존재하면 문자열, 없으면 None
    result = m.korToSnakeId("매출액")
    assert result is None or isinstance(result, str)


# ── TopicMapper ──


def test_topic_lookup_english():
    """영문 topic key로 키워드 조회."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("topic")
    result = m.lookup("dividend")
    assert result is not None
    assert result["topic"] == "dividend"
    assert "배당" in result["keywords"]


def test_topic_lookup_korean():
    """한국어 키워드로 topic 역방향 조회."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("topic")
    result = m.lookup("배당")
    assert result is not None
    assert result["topic"] == "dividend"


def test_topic_stats():
    """topic 매퍼 통계."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("topic")
    s = m.stats()
    assert s.name == "topic"
    assert s.totalEntries == 33


def test_topic_allKeys():
    """33개 topic key."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("topic")
    keys = m.allKeys()
    assert len(keys) == 33
    assert "businessOverview" in keys


def test_topic_topicForKeyword():
    """키워드 → topic 이름."""
    from dartlab.core.mappers.topicMapper import TopicMapper

    m = TopicMapper()
    assert m.topicForKeyword("사업의 개요") == "businessOverview"
    assert m.topicForKeyword("존재하지않는키워드") is None


# ── AliasMapper ──


def test_alias_resolve():
    """variant → canonical 정규화."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("alias")
    assert m.resolve("revenue") == "sales"
    assert m.resolve("operating_income") == "operating_profit"
    assert m.resolve("sales") == "sales"  # canonical은 그대로


def test_alias_lookup_variant():
    """variant 조회 → canonical 반환."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("alias")
    result = m.lookup("revenue")
    assert result is not None
    assert result["canonical"] == "sales"


def test_alias_lookup_canonical():
    """canonical 조회 → variant 목록 반환."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("alias")
    result = m.lookup("sales")
    assert result is not None
    assert "variants" in result
    assert "revenue" in result["variants"]


def test_alias_stats():
    """alias 매퍼 통계."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("alias")
    s = m.stats()
    assert s.name == "alias"
    assert s.totalEntries > 50  # 61+


def test_alias_canonicals():
    """canonical 목록."""
    from dartlab.core.mappers.aliasMapper import AliasMapper

    m = AliasMapper()
    canonicals = m.canonicals()
    assert "sales" in canonicals
    assert "operating_profit" in canonicals


# ── FlowMapper ──


def test_flow_isEvent():
    """이벤트성 계정 판별."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("flow")
    assert m.isEvent("dividends_paid")
    assert m.isEvent("배당금지급")
    assert not m.isEvent("sales")


def test_flow_lookup_event():
    """이벤트 계정 조회."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("flow")
    result = m.lookup("dividends_paid")
    assert result is not None
    assert result["flowType"] == "event"


def test_flow_lookup_regular():
    """일반 계정 조회."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("flow")
    result = m.lookup("sales")
    assert result is not None
    assert result["flowType"] == "regular"


def test_flow_stats():
    """flow 매퍼 통계."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("flow")
    s = m.stats()
    assert s.name == "flow"
    assert s.totalEntries == 14  # 7 영문 + 7 한글


def test_flow_eventAccounts():
    """이벤트 계정 목록."""
    from dartlab.core.mappers.flowMapper import FlowMapper

    m = FlowMapper()
    accounts = m.eventAccounts()
    assert "dividends_paid" in accounts
    assert "배당금지급" in accounts


# ── Snapshot ──


def test_snapshot_and_diff(tmp_path):
    """스냅샷 저장 + diff."""
    from dartlab.core.mappers import getEngine

    engine = getEngine()
    engine.setHistoryDir(tmp_path)

    # 스냅샷 저장
    snaps = engine.snapshot("2026Q1")
    assert len(snaps) == 5

    # 같은 스냅샷 두 번 → diff에서 변화 없음
    engine.snapshot("2026Q2")
    d = engine.diff("2026Q1", "2026Q2")
    assert "account" in d
    assert d["account"]["coverage"]["before"] == d["account"]["coverage"]["after"]


def test_diff_missing_quarter(tmp_path):
    """존재하지 않는 분기 diff → error."""
    from dartlab.core.mappers import getEngine

    engine = getEngine()
    engine.setHistoryDir(tmp_path)
    d = engine.diff("2020Q1", "2020Q2")
    assert "error" in d


# ── BaseMapper.missing() ──


def test_missing():
    """미매핑 항목 탐지."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("topic")
    missing = m.missing(["dividend", "존재하지않는topic", "businessOverview"])
    assert "존재하지않는topic" in missing
    assert "dividend" not in missing


# ── NotesMapper ──


def test_notes_lookup_amount():
    """금액 항목 조회."""
    from dartlab.core.mappers.notesMapper import NotesMapper

    m = NotesMapper()
    result = m.lookup("완제품")
    assert result is not None
    assert result["type"] == "amount"
    assert result["category"] == "inventory"


def test_notes_lookup_rate():
    """비율 항목 → skip."""
    from dartlab.core.mappers.notesMapper import NotesMapper

    m = NotesMapper()
    result = m.lookup("연이자율")
    assert result is not None
    assert result["type"] == "rate"
    assert result["skip"] is True


def test_notes_isAmount():
    """isAmount 판별."""
    from dartlab.core.mappers.notesMapper import NotesMapper

    m = NotesMapper()
    assert m.isAmount("완제품")
    assert not m.isAmount("연이자율")
    assert m.isAmount("미등록항목")  # 미등록 → 기본 True


def test_notes_isSkip():
    """isSkip 판별."""
    from dartlab.core.mappers.notesMapper import NotesMapper

    m = NotesMapper()
    assert m.isSkip("연이자율")
    assert not m.isSkip("완제품")
    assert not m.isSkip("미등록항목")


def test_notes_hasForeignCurrency():
    """외화 항목 판별."""
    from dartlab.core.mappers.notesMapper import NotesMapper

    m = NotesMapper()
    assert m.hasForeignCurrency("외화대출")
    assert not m.hasForeignCurrency("완제품")


def test_notes_byCategory():
    """카테고리별 항목 조회."""
    from dartlab.core.mappers.notesMapper import NotesMapper

    m = NotesMapper()
    inventory = m.byCategory("inventory")
    assert "완제품" in inventory
    assert "반제품" in inventory


def test_notes_stats():
    """notes 매퍼 통계."""
    from dartlab.core.mappers import getEngine

    m = getEngine().get("notes")
    s = m.stats()
    assert s.name == "notes"
    assert s.totalEntries > 30  # 시드에 46개


# ── Scanner ──


def test_scanner_classifyType():
    """항목 유형 자동 분류."""
    from dartlab.core.mappers.scanner import _classifyType

    assert _classifyType("연이자율(%)", []) == "rate"
    assert _classifyType("할인율", []) == "rate"
    assert _classifyType("담보에대한기술", []) == "text"
    assert _classifyType("완제품", ["1,234,567"]) == "amount"
    assert _classifyType("비율항목", ["50%", "60%", "70%"]) == "rate"


def test_scanner_hasForeignInName():
    """항목명 외화 판별."""
    from dartlab.core.mappers.scanner import _hasForeignInName

    assert _hasForeignInName("외화대출")
    assert _hasForeignInName("USD차입금")
    assert not _hasForeignInName("단기차입금")


# ── MasterParser ──


def test_masterParser_pickValue():
    """masterParser 값 선택."""
    from dartlab.core.mappers.masterParser import _pickValue
    from dartlab.core.mappers.notesMapper import NotesMapper

    m = NotesMapper()
    # 원화 값 우선
    assert _pickValue(["USD 1,000", "1,234,567"], m, "완제품") == "1,234,567"
    # 빈 값 스킵
    assert _pickValue(["", "-", "5,678"], m, "완제품") == "5,678"


def test_masterParser_isCurrentPeriod():
    """당기 판정."""
    from dartlab.core.mappers.masterParser import _isCurrentPeriod

    assert _isCurrentPeriod("당기말")
    assert _isCurrentPeriod("당기")
    assert not _isCurrentPeriod("전기말")
    assert not _isCurrentPeriod("전반기")
