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


def test_canonical_chapter_absorbs_dividend_and_securities() -> None:
    """배당/증권발행 표준 III 하위 절이 top-level(모챕터 없음)로 드리프트 시 → III 흡수 (stray 챕터 0).

    옛 era 는 '6. 배당에 관한 사항'·'7. 증권의 발행을 통한 자금조달에 관한 사항'을 III 모챕터 없이
    top-level 로 실어(sectionPath 에 III 원소 0) chapter 로 샌다. L3 표준 절 키워드(배당에관한사항·증권의발행)로 흡수.
    """
    from dartlab.providers.dart.panel.canonical import canonicalChapterExpr

    ch = ["6. 배당에 관한 사항", "7. 증권의 발행을 통한 자금조달에 관한 사항", "8. 기타 재무에 관한 사항"]
    df = pl.DataFrame({"chapter": ch, "sectionPath": ch})  # top-level → sectionPath = chapter (III 원소 없음)
    out = df.select(canonicalChapterExpr())["canonicalChapter"].to_list()
    assert out == ["III. 재무에 관한 사항"] * 3  # 셋 다 III 흡수 (stray 챕터로 새지 않음)


def test_canonical_chapter_detail_table_stays_xii() -> None:
    """XII(상세표) 안 상세표 제목이 챕터 키워드를 포함해도 XII 유지 — deepest 오배정(IX/X) 차단."""
    from dartlab.providers.dart.panel.canonical import canonicalChapterExpr

    df = pl.DataFrame(
        {
            "chapter": ["XII. 상세표"] * 3,
            "sectionPath": [
                "XII. 상세표␟2. 계열회사 현황(상세)",  # '계열회사' 키워드 → 옛 로직은 IX 오배정
                "XII. 상세표␟5. 대주주와의 영업거래(상세)",  # '대주주' → 옛 로직은 X 오배정
                "XII. 상세표␟1. 연결대상 종속회사 현황(상세)",
            ],
        }
    )
    out = df.select(canonicalChapterExpr())["canonicalChapter"].to_list()
    assert out == ["XII. 상세표"] * 3  # 부록 컨테이너 우선 — 상세표 자식은 항상 XII


def test_canonical_chapter_nt_orphan_recovers_to_finance() -> None:
    """구조신호 0(chapter·sectionPath 공백) NT_ 주석 orphan → III 복원, front-matter(키 ∅)는 honest-gap 보존.

    (첨부)재무제표 flat <P ID> 주석은 SECTION 부재로 chapter·sectionPath 둘 다 공백으로 새는 회귀
    (2025+ 35사 15,217행 실측). NT_ 표준코드 = 정의상 재무제표 주석이라 III 복원은 honest(추측 0).
    같은 공백이라도 disclosureKey 없는 front-matter(표지·정정)는 그대로(강제 배정 금지).
    """
    from dartlab.providers.dart.panel.canonical import canonicalChapterExpr

    df = pl.DataFrame(
        {
            "chapter": ["", "", "", "II. 사업의 내용"],
            "sectionPath": ["", "", "", "II. 사업의 내용␟V. 회계감사인의 감사의견 등"],
            "disclosureKey": ["NT_D838000", None, "CF_X", "NT_D838000"],
        }
    )
    out = df.select(canonicalChapterExpr(noteKeyCol="disclosureKey"))["canonicalChapter"].to_list()
    assert out[0] == "III. 재무에 관한 사항"  # NT_ orphan → III 복원
    assert out[1] == ""  # front-matter(키 ∅) → 원본 보존 (honest-gap, 강제 0)
    assert out[2] == ""  # NT_ 외 키 → 보존 (NT_ 한정, 추측 배정 금지)
    assert out[3] == "V. 회계감사인의 감사의견 등"  # 구조신호(경로) 가 NT_ 복원보다 우선
    # noteKeyCol 미지정(기본) = 복원 비활성 — 기존 호출 계약 불변
    legacy = df.select(canonicalChapterExpr())["canonicalChapter"].to_list()
    assert legacy[0] == ""


def test_report_chapter_labels_exclude_certs() -> None:
    """REPORT_CHAPTER_LABELS = navigable 보고서 챕터(I~XII) — cert 노드(cover/expert) 제외, I~XII 전부 포함."""
    from dartlab.providers.dart.panel.canonical import CERT_NODE_IDS, REPORT_CHAPTER_LABELS

    assert CERT_NODE_IDS == frozenset({"cover", "expert"})
    assert "【 대표이사 등의 확인 】" not in REPORT_CHAPTER_LABELS  # cover 제외
    assert "【 전문가의 확인 】" not in REPORT_CHAPTER_LABELS  # expert 제외
    assert "I. 회사의 개요" in REPORT_CHAPTER_LABELS
    assert "III. 재무에 관한 사항" in REPORT_CHAPTER_LABELS
    assert "XII. 상세표" in REPORT_CHAPTER_LABELS
    assert len(REPORT_CHAPTER_LABELS) == 12  # I~XII (14 - cover - expert)


def test_canonical_rank_government_order() -> None:
    """canonicalRankExpr — canonical 라벨 → 정부 문서순서, 미등재는 null (nulls_last)."""
    from dartlab.providers.dart.panel.canonical import CANONICAL_RANK, canonicalRankExpr

    df = pl.DataFrame({"chapter": ["I. 회사의 개요", "III. 재무에 관한 사항", "별난챕터"]})
    out = df.select(canonicalRankExpr())["_canonRank"].to_list()
    assert out[0] < out[1]  # I < III (정부 문서순서)
    assert out[2] is None
    assert CANONICAL_RANK["III. 재무에 관한 사항"] == 3
