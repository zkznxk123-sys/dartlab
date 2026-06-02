"""panel build dechunkNotes — 미분해 주석 블록 → 항목별 NT_* sub-note 분류 (구조무관, preamble 무손실).

``dechunkNotes`` 가 disclosureKey-null 주석 블록을 본문 "N. 제목" 헤더(통합 검출 — taxonomy 최장 prefix-match
+ 표셀 가드 + monotonic)로 감지·분할하고, 노트 앞 preamble(재무제표 본표)을 원 블록에 보존하는지 검증.
delimited/concatenated 양 포맷 + TD phantom 가드 + longest-prefix 포함. 합성 입력(데이터 0).
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
    """재무제표 영역 덩어리 → 매칭 항목별 NT_* sub-note 분할 (임계 없음)."""
    body = "<P>전문</P><SPAN>1. 재고자산</SPAN>재고 본문<SPAN>2. 차입금</SPAN>차입 본문"
    df = pl.DataFrame(
        [_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)],
        schema=PANEL_SCHEMA,
    )
    out = dechunkNotes(df)
    nt = out.filter(pl.col("disclosureKey").str.starts_with("NT_"))
    assert _INV in nt["disclosureKey"].to_list()  # 재고자산 항목화
    assert nt.height >= 2  # 매칭 노트만큼 (임계 없음)


def test_dechunk_preserves_preamble() -> None:
    """노트 앞 preamble(재무제표 본표)은 원 블록에 보존 — byte 무손실."""
    body = "<P>재무제표 본표 전문</P><SPAN>1. 재고자산</SPAN>x<SPAN>2. 차입금</SPAN>y<SPAN>3. 사채</SPAN>z"
    df = pl.DataFrame([_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    out = dechunkNotes(df)
    pre = out.filter(pl.col("disclosureKey").is_null())
    assert pre.height >= 1
    assert any("재무제표 본표 전문" in (c or "") for c in pre["contentRaw"].to_list())


def test_dechunk_non_note_block_untouched() -> None:
    """재무제표 영역 gate 밖(사업보고서 TOC)은 헤더가 매칭돼도 미처리 — 오염 차단."""
    body = "<P>사업 개요</P><SPAN>1. 재고자산</SPAN>본문<SPAN>2. 차입금</SPAN>본문<SPAN>3. 사채</SPAN>본문"
    df = pl.DataFrame(
        [_row(chapter="II. 사업의 내용", sectionLeaf="1. 사업의 개요", contentRaw=body)], schema=PANEL_SCHEMA
    )
    out = dechunkNotes(df)
    assert out.height == 1  # gate 제외 → 원본 보존
    assert out.filter(pl.col("disclosureKey").str.starts_with("NT_")).height == 0


def test_dechunk_monotonic_guard_rejects_table_item() -> None:
    """노트 본문 내 표/목록 항목(번호 역행)은 헤더로 오인 안 함 — phantom 차단."""
    # 진짜 노트 #14 차입금, 그 본문 안에 표셀 '>3. 배당금<'(번호 역행) → 배당금 phantom 미생성.
    body = "<SPAN>14. 차입금</SPAN>차입 내역 표 <TD>3. 배당금</TD> 표 안 항목<SPAN>15. 사채</SPAN>사채 본문"
    df = pl.DataFrame([_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    out = dechunkNotes(df)
    blocks = out.filter(pl.col("disclosureKey").str.starts_with("NT_"))["blockLeaf"].to_list()
    assert "배당금" not in blocks  # 번호 역행(3<14) → 표셀, 헤더 아님
    assert "차입금" in blocks and "사채" in blocks  # 진짜 노트(단조 14→15)는 itemize


def test_dechunk_unmatched_title_narrative() -> None:
    """재무제표 영역이라도 뼈대 미등재(모호/비표준) 제목은 narrative 유지 — 추정 0."""
    body = "<SPAN>1. 가공의비표준노트제목</SPAN>본문<SPAN>2. 또다른가공제목</SPAN>본문"
    df = pl.DataFrame([_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    out = dechunkNotes(df)
    assert out.filter(pl.col("disclosureKey").str.starts_with("NT_")).height == 0  # 미매칭 → NT_ 0
    assert out.filter(pl.col("disclosureKey").is_null()).height == 1  # 덩어리 원본 보존


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


def test_dechunk_concatenated_header() -> None:
    """옛 concatenated 포맷 — 번호.제목이 앞 산문에 붙고 제목이 본문으로 이어짐(태그경계 0) → 표준 NT_ 분해."""
    # delimited `>`/`[:<]` 경계 없이 헤더가 산문에 직접 붙음(`…입니다.2. 중요한 회계정책…`) — 현 delimited regex 로는 0.
    body = "당기말 자본금은 6,176,250,000원입니다.2. 중요한 회계정책 회사의 재무제표는 다음과 같다3. 영업부문당사는 단일부문으로 구성"
    df = pl.DataFrame([_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    out = dechunkNotes(df)
    keys = out.filter(pl.col("disclosureKey").str.starts_with("NT_"))["disclosureKey"].to_list()
    assert NOTE_TAXONOMY["consolidated|중요한회계정책"] in keys  # 산문에 붙은 헤더 분해
    assert NOTE_TAXONOMY["consolidated|영업부문"] in keys  # 제목이 본문으로 이어져도 prefix-match


def test_dechunk_td_cell_guard() -> None:
    """표 셀(<TD>…</TD>) 내 노트유사 번호제목은 헤더 아님 — phantom 0 (전 corpus 유일 오탐 클래스 가드)."""
    body = "<SPAN>1. 재고자산</SPAN>재고본문 <TD>2. 차입금</TD> 표안항목 <SPAN>3. 사채</SPAN>사채본문"
    df = pl.DataFrame([_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    out = dechunkNotes(df)
    blocks = out.filter(pl.col("disclosureKey").str.starts_with("NT_"))["blockLeaf"].to_list()
    assert "차입금" not in blocks  # 표 셀 → 거부 (phantom 0)
    assert "재고자산" in blocks and "사채" in blocks  # 셀 밖 진짜 헤더는 분해


def test_dechunk_longest_prefix() -> None:
    """후보 본문에 최장 등재 제목 우선 — 짧은 prefix('유형자산') 오선택 안 함."""
    body = "<SPAN>1. 유형자산및무형자산</SPAN>처분 내역은 다음과 같습니다"
    df = pl.DataFrame([_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    out = dechunkNotes(df)
    nt = out.filter(pl.col("disclosureKey").str.starts_with("NT_"))
    assert nt.height >= 1
    assert "유형자산및무형자산" in nt["blockLeaf"].to_list()  # 최장 제목 (not "유형자산")


def test_dechunk_emits_all_dedup_is_read() -> None:
    """BUILD 는 dedup 안 함 — native 와 (첨부)덩어리 공존 시 둘 다 emit, 중복 제거는 READ(dedupKeyed)."""
    body = "<SPAN>1. 재고자산</SPAN>a<SPAN>2. 차입금</SPAN>b<SPAN>3. 사채</SPAN>c"
    df = pl.DataFrame(
        [
            _row(disclosureKey=_INV, xbrlClass="NT_C_D826380", chapter="III. 재무에 관한 사항", contentRaw="네이티브"),
            _row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body),
        ],
        schema=PANEL_SCHEMA,
    )
    out = dechunkNotes(df)
    # native(_INV) + 분해된 _INV 둘 다 존재 (BUILD dedup 안 함) → READ 가 xbrlClass 우선 dedup.
    inv = out.filter(pl.col("disclosureKey") == _INV)
    assert inv.height == 2  # native 1 + 분해 1
    assert "NT_C_D826380" in inv["xbrlClass"].to_list()  # native 보존
