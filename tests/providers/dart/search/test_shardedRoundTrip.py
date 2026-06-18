"""sidecar(STORED) round-trip + BM25 byte-parity — npz 폐기 기반(P0) 게이트.

``saveShardedSegment`` 산출(postings/terms/docLengths.bin)을 ``loadShardedSegment`` 가 무손실 복원해
CSR(offsets/docIds/termFreqs/docLengths)이 빌더 원본과 array-equal 이고, ``_scoreBM25`` 결과가 npz 로드와
동일함을 검증한다. 이 게이트가 통과해야 엔진이 npz 없이 sidecar 만으로 검색 가능(PRD 기둥1·§13).
"""

from __future__ import annotations

import numpy as np
import polars as pl

from dartlab.providers.dart.search.fieldIndex import (
    _decodeVarintStream,
    _encodeVarintArray,
    _IncrementalBuilder,
    _scoreBM25,
    loadShardedSegment,
    saveSegment,
    saveShardedSegment,
    tokenizeContent,
)


def _meta(n: int) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "rcept_no": [f"R{i:08d}" for i in range(n)],
            "section_order": [0] * n,
            "corp_code": [f"C{i}" for i in range(n)],
            "corp_name": [f"회사{i}" for i in range(n)],
            "stock_code": [f"{i:06d}" for i in range(n)],
            "rcept_dt": ["20260618"] * n,
            "report_nm": ["분기보고서"] * n,
            "section_title": [""] * n,
            "text": ["t"] * n,
            "source": ["panel"] * n,
            "sourceRef": [""] * n,
            "sourceDataAsOf": ["20260618"] * n,
            "contentLen": [10] * n,
            "url": [""] * n,
            "evidenceText": ["e"] * n,
        }
    )


def _build(docs: list[str]) -> dict:
    b = _IncrementalBuilder()
    for d in docs:
        b.addDoc(d)
    return b.finalize()


def test_decode_varint_stream_roundtrip():
    # 빈 스트림은 _encodeVarintArray(빈 배열) 미지원(.max 불가)이라 디코드만 직접 검증.
    assert _decodeVarintStream(b"", 0).tolist() == []
    cases = [
        [0],
        [1, 300, 5, 127, 128, 16383, 16384, 1 << 20, 1 << 27],
        list(range(0, 5000, 7)),
    ]
    for vals in cases:
        arr = np.array(vals, dtype=np.int64)
        raw, _ = _encodeVarintArray(arr)
        out = _decodeVarintStream(raw, len(arr))
        assert out.tolist() == vals


def test_sharded_roundtrip_and_bm25_parity(tmp_path):
    docs = [
        "삼성전자 반도체 매출 증가 영업이익",
        "현대차 자동차 영업이익 매출",
        "반도체 수요 매출 증가 HBM 투자",
        "배당 자사주 소각 주주환원 정책",
        "삼성 반도체 배당 유상증자",
        "현대차 배당 자사주",
    ]
    idx0 = _build(docs)
    meta = _meta(len(docs))
    saveSegment(idx0, meta, "main", tmp_path)
    saveShardedSegment(idx0, meta, "main", tmp_path)

    res = loadShardedSegment("main", tmp_path)
    assert res is not None
    idxS, metaS = res

    # CSR 무손실 복원
    for key in ("offsets", "docIds", "termFreqs", "docLengths"):
        assert np.array_equal(idxS[key], idx0[key]), f"{key} 불일치"
    assert idxS["nDocs"] == idx0["nDocs"]
    assert idxS["stemDict"] == idx0["stemDict"]
    assert metaS.height == len(docs)

    # BM25 byte-parity (sidecar 복원 idx == npz 원본 idx)
    for q in ["반도체 매출", "배당 자사주", "삼성 반도체", "현대차 배당", "HBM 투자", "없는단어"]:
        toks = tokenizeContent(q)
        np.testing.assert_array_equal(_scoreBM25(idxS, toks), _scoreBM25(idx0, toks))
