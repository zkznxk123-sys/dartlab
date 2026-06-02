"""panel build dechunkNotes — 미분해 주석 블록 → 제목별 행 **분할**(null key). NT_ 정렬은 READ(alignNotes).

``dechunkNotes`` 가 disclosureKey-null 주석 블록을 본문 "N. 제목" 헤더(통합 검출 — taxonomy 최장 prefix-match
+ 표셀 가드 + monotonic)로 감지·분할해 **blockLeaf=제목, disclosureKey=null** 행으로 쪼개고, 노트 앞
preamble(재무제표 본표)을 원 블록에 보존하는지 검증. NT_ 부여는 안 함(READ alignNotes 담당). delimited/
concatenated 양 포맷 + TD phantom 가드 + longest-prefix 포함. 합성 입력(데이터 0).
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.providers.dart.panel.build.dechunkNotes import dechunkNotes
from dartlab.providers.dart.panel.schema import PANEL_SCHEMA

pytestmark = pytest.mark.unit


def _row(**kw) -> dict:
    """PANEL_SCHEMA 14-col 기본행 + 덮어쓰기."""
    base = dict.fromkeys(PANEL_SCHEMA, None)
    base.update(blockOrder=0, period="2020Q4", corp="000000", rceptNo="20210101000001", xbrlMatched=False)
    base.update(kw)
    return base


def _splitTitles(out: pl.DataFrame) -> list[str]:
    """분할된 제목 행(blockLeaf 보유 + disclosureKey null)의 제목 목록."""
    return out.filter(pl.col("disclosureKey").is_null() & pl.col("blockLeaf").is_not_null())["blockLeaf"].to_list()


def test_dechunk_splits_chunk_into_title_rows() -> None:
    """재무제표 영역 덩어리 → 매칭 항목별 제목 행 분할 (blockLeaf=제목, disclosureKey=null — NT_ 는 READ)."""
    body = "<P>전문</P><SPAN>1. 재고자산</SPAN>재고 본문<SPAN>2. 차입금</SPAN>차입 본문"
    df = pl.DataFrame([_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    out = dechunkNotes(df)
    titles = _splitTitles(out)
    assert "재고자산" in titles and "차입금" in titles  # 제목 분할
    assert out.filter(pl.col("disclosureKey").str.starts_with("NT_")).height == 0  # BUILD 는 NT_ 미부여


def test_dechunk_preserves_preamble() -> None:
    """노트 앞 preamble(재무제표 본표)은 원 블록에 보존 — byte 무손실."""
    body = "<P>재무제표 본표 전문</P><SPAN>1. 재고자산</SPAN>x<SPAN>2. 차입금</SPAN>y<SPAN>3. 사채</SPAN>z"
    df = pl.DataFrame([_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    out = dechunkNotes(df)
    pre = out.filter(pl.col("disclosureKey").is_null() & pl.col("blockLeaf").is_null())
    assert pre.height >= 1
    assert any("재무제표 본표 전문" in (c or "") for c in pre["contentRaw"].to_list())


def test_dechunk_lossless_byte_exact() -> None:
    """preamble + Σ제목행 content = 원 블록 (byte-exact 무손실, slice strip 0)."""
    body = "서문 전문<SPAN>1. 재고자산</SPAN>재고본문<SPAN>2. 차입금</SPAN>차입본문<SPAN>3. 사채</SPAN>사채본문"
    df = pl.DataFrame([_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    out = dechunkNotes(df)
    rejoined = "".join(c or "" for c in out["contentRaw"].to_list())
    assert rejoined == body  # 손실·중복 0


def test_dechunk_non_note_block_untouched() -> None:
    """재무제표 영역 gate 밖(사업보고서 TOC)은 헤더가 매칭돼도 미처리 — 오염 차단."""
    body = "<P>사업 개요</P><SPAN>1. 재고자산</SPAN>본문<SPAN>2. 차입금</SPAN>본문<SPAN>3. 사채</SPAN>본문"
    df = pl.DataFrame(
        [_row(chapter="II. 사업의 내용", sectionLeaf="1. 사업의 개요", contentRaw=body)], schema=PANEL_SCHEMA
    )
    out = dechunkNotes(df)
    assert out.height == 1  # gate 제외 → 원본 보존
    assert _splitTitles(out) == []  # 분할 안 함


def test_dechunk_monotonic_guard_rejects_table_item() -> None:
    """노트 본문 내 표/목록 항목(번호 역행)은 헤더로 오인 안 함 — phantom 차단."""
    body = "<SPAN>14. 차입금</SPAN>차입 내역 표 <TD>3. 배당금</TD> 표 안 항목<SPAN>15. 사채</SPAN>사채 본문"
    df = pl.DataFrame([_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    titles = _splitTitles(dechunkNotes(df))
    assert "배당금" not in titles  # 번호 역행(3<14) → 표셀, 헤더 아님
    assert "차입금" in titles and "사채" in titles  # 진짜 노트(단조 14→15)는 분할


def test_dechunk_unmatched_title_narrative() -> None:
    """재무제표 영역이라도 뼈대 미등재(모호/비표준) 제목은 narrative 유지 — 추정 0."""
    body = "<SPAN>1. 가공의비표준노트제목</SPAN>본문<SPAN>2. 또다른가공제목</SPAN>본문"
    df = pl.DataFrame([_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    out = dechunkNotes(df)
    assert _splitTitles(out) == []  # 미매칭 → 분할 0
    assert out.height == 1  # 덩어리 원본 보존


def test_dechunk_scope_section_label() -> None:
    """scope = chapter+sectionLeaf '연결' 마커 — 별도(연결 없음)는 sectionLeaf '5. 재무제표 주석'."""
    body = "<SPAN>1. 재고자산</SPAN>a<SPAN>2. 차입금</SPAN>b<SPAN>3. 사채</SPAN>c"
    df = pl.DataFrame([_row(chapter="(첨부)재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    out = dechunkNotes(df)
    sub = out.filter(pl.col("blockLeaf").is_not_null())
    assert "재고자산" in sub["blockLeaf"].to_list()
    assert sub["sectionLeaf"].to_list() == ["5. 재무제표 주석"] * sub.height  # standalone 라벨


def test_dechunk_empty_passthrough() -> None:
    """빈 df / 주석 블록 없음 → 입력 그대로."""
    empty = pl.DataFrame(schema=PANEL_SCHEMA)
    assert dechunkNotes(empty).height == 0
    plain = pl.DataFrame([_row(disclosureKey="BS", chapter="x", contentRaw="표")], schema=PANEL_SCHEMA)
    assert dechunkNotes(plain).height == 1


def test_dechunk_concatenated_header() -> None:
    """옛 concatenated 포맷 — 번호.제목이 앞 산문에 붙고 제목이 본문으로 이어짐(태그경계 0) → 제목 분할."""
    body = "당기말 자본금은 6,176,250,000원입니다.2. 중요한 회계정책 회사의 재무제표는 다음과 같다3. 영업부문당사는 단일부문으로 구성"
    df = pl.DataFrame([_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    titles = _splitTitles(dechunkNotes(df))
    assert "중요한회계정책" in titles  # 산문에 붙은 헤더 분할
    assert "영업부문" in titles  # 제목이 본문으로 이어져도 prefix-match


def test_dechunk_td_cell_guard() -> None:
    """표 셀(<TD>…</TD>) 내 노트유사 번호제목은 헤더 아님 — phantom 0 (전 corpus 유일 오탐 클래스 가드)."""
    body = "<SPAN>1. 재고자산</SPAN>재고본문 <TD>2. 차입금</TD> 표안항목 <SPAN>3. 사채</SPAN>사채본문"
    df = pl.DataFrame([_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    titles = _splitTitles(dechunkNotes(df))
    assert "차입금" not in titles  # 표 셀 → 거부 (phantom 0)
    assert "재고자산" in titles and "사채" in titles  # 셀 밖 진짜 헤더는 분할


def test_dechunk_longest_prefix() -> None:
    """후보 본문에 최장 등재 제목 우선 — 짧은 prefix('유형자산') 오선택 안 함."""
    body = "<SPAN>1. 유형자산및무형자산</SPAN>처분 내역은 다음과 같습니다"
    df = pl.DataFrame([_row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body)], schema=PANEL_SCHEMA)
    titles = _splitTitles(dechunkNotes(df))
    assert "유형자산및무형자산" in titles  # 최장 제목 (not "유형자산")


def test_dechunk_native_row_untouched() -> None:
    """native NT_ 행(disclosureKey 보유)은 gate 밖 — 불변 통과. 옛 덩어리만 분할(정렬·dedup 은 READ)."""
    body = "<SPAN>1. 재고자산</SPAN>a<SPAN>2. 차입금</SPAN>b"
    df = pl.DataFrame(
        [
            _row(
                disclosureKey="NT_D826380",
                xbrlClass="NT_C_D826380",
                chapter="III. 재무에 관한 사항",
                contentRaw="네이티브",
            ),
            _row(chapter="(첨부)연결재무제표", sectionLeaf="주석", contentRaw=body),
        ],
        schema=PANEL_SCHEMA,
    )
    out = dechunkNotes(df)
    native = out.filter(pl.col("disclosureKey") == "NT_D826380")
    assert native.height == 1 and native["xbrlClass"].to_list() == ["NT_C_D826380"]  # native 불변
    assert "재고자산" in _splitTitles(out)  # 옛 덩어리는 제목 분할(null key)
