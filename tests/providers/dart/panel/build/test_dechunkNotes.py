"""panel build dechunkNotes — 미분해 주석 블록 → 항목별 NT_* sub-note 분류 (구조무관, preamble 무손실).

``dechunkNotes`` 가 disclosureKey-null 주석 블록을 본문 "N. 제목" 헤더(택소노미 매칭 ≥ _MIN_HEADERS)로
감지·분할하고, 노트 앞 preamble(재무제표 본표)을 원 블록에 보존하는지 검증. 합성 입력(데이터 0).
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.providers.dart.panel.build.dechunkNotes import dechunkNotes
from dartlab.providers.dart.panel.build.noteTaxonomyData import NOTE_TAXONOMY
from dartlab.providers.dart.panel.schema import PANEL_SCHEMA

pytestmark = pytest.mark.unit


def _row(**kw) -> dict:
    """PANEL_SCHEMA 14-col 기본행 + 덮어쓰기."""
    base = dict.fromkeys(PANEL_SCHEMA, None)
    base.update(blockOrder=0, period="2020Q4", corp="000000", rceptNo="20210101000001", xbrlMatched=False)
    base.update(kw)
    return base


# 택소노미에서 실재 연결 NT_ 키 2개 픽 (회사 무관 표준)
_INV = NOTE_TAXONOMY["consolidated|재고자산"]  # NT_D826380
_BORROW = NOTE_TAXONOMY.get("consolidated|차입금")


def test_dechunk_splits_chunk_into_nt_rows() -> None:
    """주석 덩어리(헤더 ≥3) → 항목별 NT_* sub-note 행 분할."""
    body = (
        "<P>전문</P>"
        "<SPAN>1. 재고자산</SPAN>재고 본문 테이블"
        "<SPAN>2. 차입금</SPAN>차입 본문 테이블"
        "<SPAN>3. 일반적 사항</SPAN>일반 본문"
    )
    df = pl.DataFrame(
        [_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)],
        schema=PANEL_SCHEMA,
    )
    out = dechunkNotes(df)
    nt = out.filter(pl.col("disclosureKey").str.starts_with("NT_"))
    assert _INV in nt["disclosureKey"].to_list()  # 재고자산 항목화
    assert nt.height >= 3  # 최소 3개 노트 분할


def test_dechunk_preserves_preamble() -> None:
    """노트 앞 preamble(재무제표 본표)은 원 블록에 보존 — byte 무손실."""
    body = "<P>재무제표 본표 전문</P><SPAN>1. 재고자산</SPAN>x<SPAN>2. 차입금</SPAN>y<SPAN>3. 사채</SPAN>z"
    df = pl.DataFrame([_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    out = dechunkNotes(df)
    pre = out.filter(pl.col("disclosureKey").is_null())
    assert pre.height >= 1
    assert any("재무제표 본표 전문" in (c or "") for c in pre["contentRaw"].to_list())


def test_dechunk_below_min_headers_untouched() -> None:
    """매칭 헤더 < _MIN_HEADERS(3) 면 노트 블록 아님 — 원본 보존(오탐 차단)."""
    body = "<P>사업 개요에서 재고자산을 언급</P><SPAN>1. 재고자산</SPAN>한 항목뿐"
    df = pl.DataFrame(
        [_row(chapter="II. 사업의 내용", sectionLeaf="1. 사업의 내용", contentRaw=body)], schema=PANEL_SCHEMA
    )
    out = dechunkNotes(df)
    assert out.height == 1
    assert out.filter(pl.col("disclosureKey").str.starts_with("NT_")).height == 0


def test_dechunk_scope_from_consolidated_marker() -> None:
    """scope = chapter+sectionLeaf '연결' 마커 — 별도(연결 없음)는 standalone NT_ 코드."""
    body = "<SPAN>1. 재고자산</SPAN>a<SPAN>2. 차입금</SPAN>b<SPAN>3. 사채</SPAN>c"
    df = pl.DataFrame([_row(chapter="(첨부)재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    out = dechunkNotes(df)
    nt = out.filter(pl.col("disclosureKey").str.starts_with("NT_"))
    standalone = NOTE_TAXONOMY["standalone|재고자산"]  # NT_D826385
    assert standalone in nt["disclosureKey"].to_list()
    assert _INV not in nt["disclosureKey"].to_list()  # 연결 코드 아님


def test_dechunk_empty_passthrough() -> None:
    """빈 df / 주석 블록 없음 → 입력 그대로."""
    empty = pl.DataFrame(schema=PANEL_SCHEMA)
    assert dechunkNotes(empty).height == 0
    plain = pl.DataFrame([_row(disclosureKey="BS", chapter="x", contentRaw="표")], schema=PANEL_SCHEMA)
    assert dechunkNotes(plain).height == 1


def test_dechunk_skips_native_scope() -> None:
    """이미 itemized native NT_*(xbrlClass NT_C_) 가 있는 scope 덩어리는 분해 생략(이중수록 차단)."""
    body = "<SPAN>1. 재고자산</SPAN>a<SPAN>2. 차입금</SPAN>b<SPAN>3. 사채</SPAN>c"
    df = pl.DataFrame(
        [
            _row(disclosureKey=_INV, xbrlClass="NT_C_D826380", chapter="III. 재무에 관한 사항", contentRaw="네이티브"),
            _row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body),
        ],
        schema=PANEL_SCHEMA,
    )
    out = dechunkNotes(df)
    # 연결 scope native 존재 → (첨부) 덩어리 분해 안 함 → 덩어리 원본 보존, 새 NT_ 행 미생성
    assert out.filter(pl.col("disclosureKey").is_null() & pl.col("sectionLeaf").eq("주석")).height == 1
