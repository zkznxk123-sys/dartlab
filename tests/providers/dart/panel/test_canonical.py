"""panel canonical L1 TOC — 드리프트 챕터 → 정부표준 14 노드 흡수 ((첨부)→III) 검증.

``canonical.canonicalChapterExpr`` 가 회사별 드리프트 챕터((첨부)재무제표·감사보고서 변형)를 14 canonical
노드로 bounded 매핑하는지 — (첨부) 잔존 0, 미매칭 원본 보존, rank 정부 문서순서. READ-time 파생(데이터 0).
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_canonical_chapter_absorbs_attachment() -> None:
    """(첨부)재무제표/(첨부)연결재무제표 → 'III. 재무에 관한 사항' 흡수 (phantom 챕터 0)."""
    from dartlab.providers.dart.panel.canonical import canonicalChapterExpr

    ch = ["(첨부)재 무 제 표", "(첨부)연 결 재 무 제 표", "III. 재무에 관한 사항", "II. 사업의 내용"]
    df = pl.DataFrame({"chapter": ch, "sectionPath": ch})  # top-level → sectionPath = chapter
    out = df.select(canonicalChapterExpr())["canonicalChapter"].to_list()
    assert out == ["III. 재무에 관한 사항", "III. 재무에 관한 사항", "III. 재무에 관한 사항", "II. 사업의 내용"]
    assert not any("첨부" in c for c in out)  # (첨부) 잔존 0


def test_canonical_chapter_recovers_collapsed_from_path() -> None:
    """붕괴 chapter(II 로 몰림) → sectionPath 깊은 canonical 원소(IV/III)로 진짜 챕터 복원."""
    from dartlab.providers.dart.panel.canonical import canonicalChapterExpr

    df = pl.DataFrame(
        {
            "chapter": ["II. 사업의 내용", "II. 사업의 내용", "II. 사업의 내용"],
            "sectionPath": [
                "II. 사업의 내용␟VI. 이사회 등 회사의 기관에 관한 사항",  # 진짜 VI (이사회 키워드)
                "II. 사업의 내용␟7. 기타␟III. 재무에 관한 사항␟2. 연결재무제표",  # 진짜 III (가장 깊은 canonical)
                "II. 사업의 내용␟2. 주요 제품 및 서비스",  # canonical 원소 없음 → II 유지
            ],
        }
    )
    out = df.select(canonicalChapterExpr())["canonicalChapter"].to_list()
    assert out[0] == "VI. 이사회 등 회사의 기관에 관한 사항"  # 깊은 canonical 원소 복원
    assert out[1] == "III. 재무에 관한 사항"  # deepest canonical = III (연결재무제표도 재무제표 키워드 → III)
    assert out[2] == "II. 사업의 내용"  # subsection(주요 제품)만 → II 유지


def test_canonical_chapter_audit_and_preserve() -> None:
    """감사보고서 → V 흡수, 14 밖 챕터·null 은 원본 보존 (honest — 강제 접지 않음)."""
    from dartlab.providers.dart.panel.canonical import canonicalChapterExpr

    ch = ["독립된 감사인의 감사보고서", "별난 회사 챕터", None]
    df = pl.DataFrame({"chapter": ch, "sectionPath": ch})
    out = df.select(canonicalChapterExpr())["canonicalChapter"].to_list()
    assert out[0] == "V. 회계감사인의 감사의견 등"
    assert out[1] == "별난 회사 챕터"  # 미매칭 원본 보존
    assert out[2] is None


def test_canonical_rank_government_order() -> None:
    """canonicalRankExpr — canonical 라벨 → 정부 문서순서, 미등재는 null (nulls_last)."""
    from dartlab.providers.dart.panel.canonical import CANONICAL_RANK, canonicalRankExpr

    df = pl.DataFrame({"chapter": ["I. 회사의 개요", "III. 재무에 관한 사항", "별난챕터"]})
    out = df.select(canonicalRankExpr())["_canonRank"].to_list()
    assert out[0] < out[1]  # I < III (정부 문서순서)
    assert out[2] is None
    assert CANONICAL_RANK["III. 재무에 관한 사항"] == 3
