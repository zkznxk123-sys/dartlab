"""전체 코퍼스 매핑 동등성 영구 가드 (적대적 검토 MED-3).

자매 ``test_ssot_equivalence_dart`` 는 결정적 universe(dict 키 + 변형)로 *항상* 돈다.
본 가드는 그 보완 — **전 종목 실 parquet(data/dart/finance/*.parquet)의 모든 고유
계정** 에 대해 production ``AccountMapper.map`` 과 독립 재구현이 byte-identical 임을
검증한다. 옛 코드(e6857503f) 격리실행으로 145,873 입력 0 불일치가 증명된 그 검증을
영구화 — 로컬 pre-push 에서 실데이터 회귀를 잡는다.

``requires_data`` — 로컬 parquet 필요(CI 에서 skip). 데이터 부재 시 자동 skip.
streaming scan + map() 만 (Company 객체 미생성) → 메모리 안전.
"""

from __future__ import annotations

import glob
import re

import pytest

pytestmark = pytest.mark.requires_data

_FINANCE_GLOB = "data/dart/finance/*.parquet"
_PREFIX_RE = re.compile(r"^(?:ifrs-full_|ifrs_|dart_|ifrs-smes_)")
_PAREN_RE = re.compile(r"\([^)]*\)")
_KOR_TRIM_SUFFIXES = ("액", "등", "외")


def _buildReference():
    """독립 재구현 normalize — SSOT layers/mappings 만 읽음 (production 미참조).

    인덱스 빌드 조건은 production 과 정확히 동일 (noParen 은 괄호제거≠공백제거).
    """
    from dartlab.core.accounts.data import loadAccounts

    data = loadAccounts()
    m = data["mappings"]
    idSyn = data["layers"]["idSynonym"]
    nameSyn = data["layers"]["nameSynonym"]
    ns: dict[str, str] = {}
    np: dict[str, str] = {}
    nh: dict[str, str] = {}
    for k, s in m.items():
        a = k.replace(" ", "").replace("\t", "").replace("​", "")
        if a != k and a not in m:
            ns[a] = s
        nos = k.replace(" ", "")
        sp = _PAREN_RE.sub("", nos)
        if sp != nos and sp and sp not in m:
            np[sp] = s
        h = k.replace("-", "").replace("–", "").replace("—", "")
        if h != k and h not in m:
            nh[h] = s

    def normalize(aid: str, anm: str) -> str | None:
        st = _PREFIX_RE.sub("", aid) if aid else ""
        nid = idSyn.get(st, st)
        if anm and anm in m:
            return m[anm]
        if st and st in m:
            return m[st]
        nnm = nameSyn.get(anm, anm) if anm else ""
        if nnm and nnm in m:
            return m[nnm]
        if nid and nid in m:
            return m[nid]
        if nnm:
            nsp = nnm.replace(" ", "")
            if nsp != nnm and nsp in m:
                return m[nsp]
            if nsp in ns:
                return ns[nsp]
            npr = _PAREN_RE.sub("", nsp)
            if npr != nsp and npr in m:
                return m[npr]
            if npr in np:
                return np[npr]
            if nsp != npr and nsp in np:
                return np[nsp]
            noh = nsp.replace("-", "").replace("–", "").replace("—", "")
            if noh in m:
                return m[noh]
            if noh in nh:
                return nh[noh]
            for sx in _KOR_TRIM_SUFFIXES:
                if nsp.endswith(sx):
                    tr = nsp[: -len(sx)]
                    if tr:
                        if tr in m:
                            return m[tr]
                        if tr in ns:
                            return ns[tr]
                        if tr in np:
                            return np[tr]
                        if tr in nh:
                            return nh[tr]
        return None

    return normalize


def test_full_corpus_map_equivalence() -> None:
    """전 종목 실 parquet 의 모든 고유 (id,nm) → production == 독립재구현 0 불일치."""
    import polars as pl

    files = sorted(glob.glob(_FINANCE_GLOB))
    if len(files) < 100:
        pytest.skip(f"DART finance parquet 부족 ({len(files)}) — requires_data")

    from dartlab.providers.dart.finance.mapper import AccountMapper

    ref = _buildReference()
    base = AccountMapper.get()
    df = (
        pl.scan_parquet(files, extra_columns="ignore", missing_columns="insert")
        .select(
            pl.col("account_id").cast(pl.String).fill_null(""),
            pl.col("account_nm").cast(pl.String).fill_null(""),
        )
        .unique()
        .collect(engine="streaming")
    )
    assert df.height > 50_000, f"코퍼스 너무 작음 ({df.height})"

    mismatches = [
        (aid, anm, base.map(aid, anm), ref(aid, anm))
        for aid, anm in df.iter_rows()
        if base.map(aid, anm) != ref(aid, anm)
    ]
    assert not mismatches, f"{len(mismatches)} 불일치 (전수 회귀). 샘플: {mismatches[:10]}"
