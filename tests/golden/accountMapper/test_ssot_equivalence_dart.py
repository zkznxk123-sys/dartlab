"""Golden 회귀 가드 — DART account 매퍼 SSOT 동등성.

이 테스트의 oracle 은 *독립 reference 구현* (`_normalize`) 으로, production
``AccountMapper.map()`` 을 호출하지 않는다. reference 는 단일 SSOT 구조 (JSON
``layers`` 가 있으면 거기서, 없으면 in-code dict 에서) 만 읽어 12 단계 fallback 을
재현한다. production map() 이 이 spec 과 1 입력이라도 어긋나면 fail.

목적: account 매퍼를 흩어진 5 dict → 단일 SSOT owner 로 통합하는 마이그레이션
(steady-wibbling-eagle 플랜 S0~S4) 전 구간에서 *byte-identical 보존* 강제.
production 이 in-code dict 를 쓰든 (통합 전) owner 를 쓰든 (통합 후) 결과 불변.

검증 근거: 145,926 입력 0 불일치 (tests/_attempts/accountMapperSSOT 실험).
본 가드는 그 동등성을 결정적(parquet 비의존) universe 로 영구 고정.
"""

from __future__ import annotations

import re

import pytest

pytestmark = pytest.mark.unit

# 독립 spec 상수 — production 알고리즘 조각 미import (진짜 oracle)
_PREFIX_RE = re.compile(r"^(?:ifrs-full_|ifrs_|dart_|ifrs-smes_)")
_PAREN_RE = re.compile(r"\([^)]*\)")
_KOR_TRIM_SUFFIXES = ("액", "등", "외")


def _buildLayered() -> dict:
    """단일 SSOT 구조 — accountMappings.json layers + mappings (독립 oracle, production 미참조)."""
    from dartlab.core.accounts.data import loadAccounts

    data = loadAccounts()
    return {
        "idSynonym": data["layers"]["idSynonym"],
        "nameSynonym": data["layers"]["nameSynonym"],
        "nameToSnake": data["mappings"],
    }


class _ReferenceNormalizer:
    """SSOT 만으로 DART account → snakeId 재현 (12 단계 독립 spec)."""

    def __init__(self, ssot: dict):
        self.idSynonym = ssot["idSynonym"]
        self.nameSynonym = ssot["nameSynonym"]
        self.m = ssot["nameToSnake"]
        self._ns: dict[str, str] | None = None
        self._np: dict[str, str] | None = None
        self._nh: dict[str, str] | None = None

    def _noSpace(self) -> dict[str, str]:
        if self._ns is None:
            idx: dict[str, str] = {}
            for k, sid in self.m.items():
                s = k.replace(" ", "").replace("\t", "").replace("​", "")
                if s != k and s not in self.m:
                    idx[s] = sid
            self._ns = idx
        return self._ns

    def _noParen(self) -> dict[str, str]:
        if self._np is None:
            idx: dict[str, str] = {}
            for k, sid in self.m.items():
                ns = k.replace(" ", "")
                s = _PAREN_RE.sub("", ns)
                if s != ns and s and s not in self.m:
                    idx[s] = sid
            self._np = idx
        return self._np

    def _noHyphen(self) -> dict[str, str]:
        if self._nh is None:
            idx: dict[str, str] = {}
            for k, sid in self.m.items():
                s = k.replace("-", "").replace("–", "").replace("—", "")
                if s != k and s not in self.m:
                    idx[s] = sid
            self._nh = idx
        return self._nh

    def normalize(self, accountId: str, accountNm: str) -> str | None:
        m = self.m
        stripped = _PREFIX_RE.sub("", accountId) if accountId else ""
        normalizedId = self.idSynonym.get(stripped, stripped)

        if accountNm and accountNm in m:
            return m[accountNm]
        if stripped and stripped in m:
            return m[stripped]

        normalizedNm = self.nameSynonym.get(accountNm, accountNm) if accountNm else ""
        if normalizedNm and normalizedNm in m:
            return m[normalizedNm]
        if normalizedId and normalizedId in m:
            return m[normalizedId]

        if normalizedNm:
            noSpace = normalizedNm.replace(" ", "")
            if noSpace != normalizedNm and noSpace in m:
                return m[noSpace]
            ns = self._noSpace()
            if noSpace in ns:
                return ns[noSpace]

            noParen = _PAREN_RE.sub("", noSpace)
            if noParen != noSpace and noParen in m:
                return m[noParen]
            np = self._noParen()
            if noParen in np:
                return np[noParen]
            if noSpace != noParen and noSpace in np:
                return np[noSpace]

            noHyphen = noSpace.replace("-", "").replace("–", "").replace("—", "")
            if noHyphen in m:
                return m[noHyphen]
            nh = self._noHyphen()
            if noHyphen in nh:
                return nh[noHyphen]

            for sfx in _KOR_TRIM_SUFFIXES:
                if not noSpace.endswith(sfx):
                    continue
                trimmed = noSpace[: -len(sfx)]
                if not trimmed:
                    continue
                if trimmed in m:
                    return m[trimmed]
                if trimmed in ns:
                    return ns[trimmed]
                if trimmed in np:
                    return np[trimmed]
                if trimmed in nh:
                    return nh[trimmed]

        return None


# 변형 경로(공백/괄호/하이픈/suffix)를 강제로 타는 결정적 케이스
_VARIANT_INPUTS: list[tuple[str, str]] = [
    ("", "현금의 기타유입"),
    ("", "현금의기타유입(유출)"),
    ("", "매출 액"),
    ("", "당기 순이익"),
    ("", "영업양도로 인한 현금유입액"),
    ("ifrs-full_Revenue", "매출액"),
    ("ifrs-full_Revenue", ""),
    ("dart_OperatingIncomeLoss", ""),
]


def _universe() -> list[tuple[str, str]]:
    """결정적 입력 universe — SSOT 전 키 + 변형 케이스 (parquet 비의존)."""
    from dartlab.core.accounts.data import loadAccounts

    data = loadAccounts()
    pairs: set[tuple[str, str]] = set(_VARIANT_INPUTS)
    for k in data["mappings"]:
        pairs.add(("", k))
    for k in data["layers"]["idSynonym"]:
        pairs.add((k, ""))
        pairs.add(("ifrs-full_" + k, ""))
    for k in data["layers"]["nameSynonym"]:
        pairs.add(("", k))
    return sorted(pairs)


@pytest.fixture(scope="module")
def _production():
    from dartlab.core.utils.labels import _loadAccountMappings
    from dartlab.providers.dart.finance.mapper import AccountMapper

    _loadAccountMappings.cache_clear()
    AccountMapper.release()
    return AccountMapper.get()


def test_dart_normalize_equivalence(_production) -> None:
    """production map() == 독립 SSOT spec — 전 universe 0 불일치."""
    ref = _ReferenceNormalizer(_buildLayered())
    universe = _universe()
    assert len(universe) > 30_000, f"universe 너무 작음 ({len(universe)}) — SSOT 로드 실패 의심"

    mismatches = [
        (i, n, _production.map(i, n), ref.normalize(i, n))
        for i, n in universe
        if _production.map(i, n) != ref.normalize(i, n)
    ]
    assert not mismatches, f"{len(mismatches)} 불일치 (통합 회귀). 샘플: {mismatches[:10]}"


def test_dart_variant_paths_resolve(_production) -> None:
    """변형 경로 케이스가 production·spec 양쪽에서 동일 결과 (경로 sanity)."""
    ref = _ReferenceNormalizer(_buildLayered())
    for accId, accNm in _VARIANT_INPUTS:
        assert _production.map(accId, accNm) == ref.normalize(accId, accNm)
