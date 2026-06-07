"""Golden 회귀 가드 — 라벨 cascade + EDGAR tag 매핑 SSOT 동등성.

회의론자가 "5 개 양립불가 alias semantic" 이라 경고한 영역 중 라벨 양방향 전파
(``getKoreanLabels`` 6 단계) 와 EDGAR alias + ``STMT_OVERRIDES`` (tuple 차원) 를
독립 reference 구현으로 재현해 production 과 byte-identical 보존을 강제.

reference 는 단일 SSOT (JSON ``layers``/``edgar`` 우선, 없으면 in-code) 만 읽고
production (`getKoreanLabels`/`getEnglishLabels`/`EdgarMapper`) 을 호출하지 않는다.

검증 근거: getKoreanLabels 5,966 키 0 차이 · EdgarMapper 62,060 입력 0 불일치
(tests/_attempts/accountMapperSSOT 실험).
"""

from __future__ import annotations

import re

import pytest

pytestmark = pytest.mark.unit

_NUM_PREFIX = re.compile(r"^\d+[.\s·]+")


# ── SSOT 로드 (단일 진실의 원천만 읽음 — production 코드 미참조 독립 oracle) ──
def _snakeAlias() -> dict[str, str]:
    from dartlab.core.accounts.data import loadAccounts

    return loadAccounts()["layers"]["snakeAlias"]


def _deriveEdgarIndexes(accounts: list, learnedTags: dict) -> tuple[dict, dict]:
    """accounts + learnedTags(소스) → tagMap·stmtTagMap(파생).

    EdgarMapper._loadData 와 동일 규칙 — commonTags 가 learnedTags 를 덮어씀.
    이 파생이 owner edgar 모듈이 따라야 할 spec.
    """
    stmtTagMap: dict[str, dict[str, str]] = {}
    commonTagMap: dict[str, str] = {}
    for acct in accounts:
        sid = acct["snakeId"]
        stmt = acct["stmt"]
        for tag in acct.get("commonTags", []):
            tl = tag.lower()
            commonTagMap[tl] = sid
            stmtTagMap.setdefault(tl, {})[stmt] = sid
    tagMap: dict[str, str] = {}
    for tag, sid in learnedTags.items():
        tagMap[tag.lower()] = sid
    for tag, sid in commonTagMap.items():
        tagMap[tag] = sid
    return tagMap, stmtTagMap


def _edgarSSOT() -> dict:
    """EDGAR tag SSOT — JSON ``edgar`` 소스에서 인덱스 파생 (독립 oracle)."""
    from dartlab.core.accounts.data import loadAccounts

    edgar = loadAccounts()["edgar"]
    tagMap, stmtTagMap = _deriveEdgarIndexes(edgar["accounts"], edgar["learnedTags"])
    return {
        "accounts": edgar["accounts"],
        "tagMap": tagMap,
        "stmtTagMap": stmtTagMap,
        "stmtOverrides": edgar["stmtOverrides"],
    }


# ── 독립 reference 구현 ──
def _koreanLabelsRef() -> dict[str, str]:
    """getKoreanLabels 6 단계 독립 재현."""
    from dartlab.core.utils.labels import (
        _loadAccountMappings,
        _loadEdgarStandardAccounts,
        _loadLabelSupplements,
    )

    data = _loadAccountMappings()
    stdAccounts = data.get("standardAccounts", {})
    mappings = data.get("mappings", {})
    snakeAlias = _snakeAlias()
    edgarLabels = _loadEdgarStandardAccounts()
    supplements = _loadLabelSupplements()

    result: dict[str, str] = {}
    used: set[str] = set()

    for snakeId, meta in stdAccounts.items():
        korName = meta.get("korName")
        if korName:
            result[snakeId] = korName
            used.add(korName)

    for snakeId, korName in edgarLabels.items():
        if korName and result.get(snakeId) in (None, snakeId):
            result[snakeId] = korName

    for sid, name in supplements.items():
        if result.get(sid) in (None, sid):
            result[sid] = name

    if mappings:
        reverse: dict[str, list[str]] = {}
        for name, snakeId in mappings.items():
            if any("가" <= ch <= "힣" for ch in name):
                reverse.setdefault(snakeId, []).append(name)
        for snakeId, names in reverse.items():
            if snakeId in result and result[snakeId] != snakeId:
                continue
            candidate = min(names, key=len)
            if candidate in used:
                alt = sorted(names, key=len)
                chosen = next((n for n in alt if n not in used), snakeId)
                result[snakeId] = chosen
            else:
                result[snakeId] = candidate
            used.add(result[snakeId])

    for src, tgt in snakeAlias.items():
        if tgt in result and result.get(src) in (None, src):
            result[src] = result[tgt]
    for src, tgt in snakeAlias.items():
        if src in result and result.get(tgt) in (None, tgt):
            result[tgt] = result[src]

    for sid in result:
        val = result[sid]
        if val and val.startswith("*"):
            val = val[1:]
        if val and val[0].isdigit():
            cleaned = _NUM_PREFIX.sub("", val)
            if cleaned:
                val = cleaned
        result[sid] = val

    return result


def _edgarMapRef(ssot: dict, tag: str, stmt: str) -> str | None:
    key = f"{tag}|{stmt}"
    if key in ssot["stmtOverrides"]:
        return ssot["stmtOverrides"][key]
    tagLower = tag.lower()
    if stmt and tagLower in ssot["stmtTagMap"]:
        stmtMap = ssot["stmtTagMap"][tagLower]
        if stmt in stmtMap:
            return stmtMap[stmt]
    return ssot["tagMap"].get(tagLower)


def _edgarMapToDartRef(ssot: dict, alias: dict, tag: str, stmt: str) -> str | None:
    sid = _edgarMapRef(ssot, tag, stmt)
    if sid is None:
        return None
    return alias.get(sid, sid)


# ── 테스트 ──
def test_korean_labels_equivalence() -> None:
    """getKoreanLabels() == 독립 spec — 키 집합·값 0 차이."""
    from dartlab.core.utils.labels import getKoreanLabels

    gold = getKoreanLabels()
    got = _koreanLabelsRef()
    assert set(gold) == set(got), f"키 차이 {len(set(gold) ^ set(got))}"
    valDiff = {k: (gold[k], got[k]) for k in gold if gold[k] != got[k]}
    assert not valDiff, f"값 차이 {len(valDiff)}: {list(valDiff.items())[:10]}"
    assert len(gold) > 3_000, f"라벨 수 비정상 ({len(gold)})"


def test_english_labels_equivalence() -> None:
    """getEnglishLabels() == SSOT labelEn (또는 in-code _EDGAR_LABELS)."""
    from dartlab.core.utils.labels import _EDGAR_LABELS, _loadAccountMappings, getEnglishLabels

    layers = _loadAccountMappings().get("layers")
    expected = layers["labelEn"] if (layers and "labelEn" in layers) else dict(_EDGAR_LABELS)
    assert getEnglishLabels() == expected


def test_edgar_map_equivalence() -> None:
    """EdgarMapper.map/mapToDart == 독립 spec — commonTags×stmt 전수 0 불일치."""
    from dartlab.providers.edgar.finance.mapper import STMT_OVERRIDES, EdgarMapper

    EdgarMapper._ensureLoaded()
    ssot = _edgarSSOT()
    alias = _snakeAlias()

    tags: set[str] = set(EdgarMapper._tagMap)
    for acct in EdgarMapper._accounts:
        tags.update(acct.get("commonTags", []))
    for tg, _st in STMT_OVERRIDES:
        tags.add(tg)
    stmts = ["IS", "BS", "CF", "CI", ""]

    mmMap = mmDart = n = 0
    for tg in tags:
        for st in stmts:
            n += 1
            if EdgarMapper.map(tg, st) != _edgarMapRef(ssot, tg, st):
                mmMap += 1
            if EdgarMapper.mapToDart(tg, st) != _edgarMapToDartRef(ssot, alias, tg, st):
                mmDart += 1
    assert n > 10_000, f"EDGAR universe 너무 작음 ({n})"
    assert mmMap == 0 and mmDart == 0, f"EDGAR 불일치 map={mmMap} mapToDart={mmDart}"
