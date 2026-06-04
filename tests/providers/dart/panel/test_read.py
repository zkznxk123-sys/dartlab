"""panel read 엔진 mirror — scope/anchor/long/wide 순수 단위 (데이터 0).

``providers/dart/panel/read.py`` 의 1:1 mirror. scopeExpr(연결/별도)·anchorLatest(era drift
최신기준 정렬)는 합성 DataFrame 으로, _panelDir/readLong/readWide 는 artifact 부재 None 경로로
검증 (read 표면 network/lxml 0, R2). 실데이터 수평화는 tests/panel/test_panel_intra.py 담당.
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_scope_expr_consolidated_standalone() -> None:
    """xbrlClass → scope: _S=standalone, 그 외/None=consolidated."""
    from dartlab.providers.dart.panel.read import scopeExpr

    df = pl.DataFrame({"xbrlClass": ["BS_C", "BS_S", "BS", "NT_S_D826385", None]})
    assert df.select(scopeExpr())["scope"].to_list() == [
        "consolidated",
        "standalone",
        "consolidated",
        "standalone",
        "consolidated",
    ]


def test_anchor_latest_propagates_latest_label() -> None:
    """(disclosureKey, scope) 그룹의 최신 period 라벨을 과거 기간에 덮어쓴다 (한 행 정렬)."""
    from dartlab.providers.dart.panel.read import anchorLatest

    df = pl.DataFrame(
        {
            "disclosureKey": ["inv", "inv"],
            "period": ["2023Q4", "2024Q4"],
            "chapter": ["A", "A"],
            "sectionLeaf": ["oldName", "newName"],
            "blockLeaf": ["", ""],
            "xbrlClass": ["NT_C", "NT_C"],
        }
    )
    out = anchorLatest(df)
    assert "scope" in out.columns
    # 최신(2024Q4) 라벨 newName 이 두 기간 모두에 통일 → era drift 흡수.
    assert set(out["sectionLeaf"].to_list()) == {"newName"}


def test_anchor_latest_passthrough_when_no_key() -> None:
    """disclosureKey 컬럼 부재 시 원본 그대로 (방어)."""
    from dartlab.providers.dart.panel.read import anchorLatest

    df = pl.DataFrame({"period": ["2024Q4"], "chapter": ["A"]})
    assert anchorLatest(df).equals(df)


def test_panel_dir_path_market_namespace() -> None:
    """_panelDir: kr→dart/panel, us→edgar/panel."""
    from dartlab.providers.dart.panel.read import _panelDir

    assert _panelDir("005930", "kr").as_posix().endswith("dart/panel/005930")
    assert _panelDir("AAPL", "us").as_posix().endswith("edgar/panel/AAPL")


def test_read_long_and_wide_none_when_absent() -> None:
    """artifact 없는 종목 → readLong/readWide 모두 None (데이터 로드 0)."""
    from dartlab.providers.dart.panel.read import readLong, readWide

    assert readLong("000000nonexistent") is None
    assert readWide("000000nonexistent") is None
    assert readWide("000000nonexistent", tag=False) is None


def test_strip_expr_removes_tags_and_collapses_whitespace() -> None:
    """_stripExpr: <태그> 제거 + 연속공백 1칸 + 양끝 trim (순수 polars, lxml 0)."""
    from dartlab.providers.dart.panel.read import _stripExpr

    df = pl.DataFrame({"c": ["<TABLE-GROUP><TD>재고</TD>  <TD>290</TD></TABLE-GROUP>"]})
    assert df.select(_stripExpr("c"))["c"][0] == "재고 290"


def test_order_by_spine_period_columns_latest_first() -> None:
    """orderBySpine: period 열 최신순(내림차순) 배치, index 컬럼 먼저."""
    from dartlab.providers.dart.panel.read import orderBySpine

    wide = pl.DataFrame(
        {
            "chapter": ["I. 회사의 개요"],
            "sectionLeaf": ["1. 회사의 개요"],
            "disclosureKey": [None],
            "2015Q4": ["a"],
            "2026Q1": ["b"],
            "2020Q2": ["c"],
        }
    )
    out = orderBySpine(wide, ["chapter", "sectionLeaf", "disclosureKey"])
    periodCols = [c for c in out.columns if c[:4].isdigit()]
    assert periodCols == ["2026Q1", "2020Q2", "2015Q4"]  # 최신순
    assert out.columns[:3] == ["chapter", "sectionLeaf", "disclosureKey"]  # index 먼저


def test_order_by_spine_government_order() -> None:
    """orderBySpine: SPINE 등재 행을 (chapterRank, spineOrder) 정부순서로 정렬."""
    from dartlab.providers.dart.panel.read import orderBySpine
    from dartlab.providers.dart.panel.spine import SPINE, spineOrderOf

    if not SPINE:
        pytest.skip("spineData 비어있음 (buildSpine 미실행)")
    # 정부순서상 재고(NT_D826380)보다 뒤인 항목을 일부러 앞 행에 두고 정렬 복원 확인.
    later = next((k for k in SPINE if (spineOrderOf(k) or 0) > (spineOrderOf("NT_D826380") or 0)), None)
    if later is None or later.startswith("NARR::"):
        pytest.skip("비교 대상 keyed 항목 부족")
    wide = pl.DataFrame(
        {
            "chapter": ["III. 재무에 관한 사항", "III. 재무에 관한 사항"],
            "sectionLeaf": ["x", "y"],
            "disclosureKey": [later, "NT_D826380"],
            "2026Q1": ["a", "b"],
        }
    )
    out = orderBySpine(wide, ["chapter", "sectionLeaf", "disclosureKey"])
    # spineOrder 작은 NT_D826380 이 later 보다 먼저.
    assert out["disclosureKey"].to_list() == ["NT_D826380", later]


def test_order_by_spine_unranked_rows_last() -> None:
    """orderBySpine: SPINE 미등재 행은 chapter 말미(nulls_last)."""
    from dartlab.providers.dart.panel.read import orderBySpine
    from dartlab.providers.dart.panel.spine import SPINE

    if not SPINE:
        pytest.skip("spineData 비어있음")
    wide = pl.DataFrame(
        {
            "chapter": ["I. 회사의 개요", "I. 회사의 개요"],
            "sectionLeaf": ["__unranked__", "1. 회사의 개요"],
            "disclosureKey": ["__NOT_IN_SPINE__", None],
            "2026Q1": ["a", "b"],
        }
    )
    out = orderBySpine(wide, ["chapter", "sectionLeaf", "disclosureKey"])
    # 등재된 narrative(1.회사의 개요)가 미등재(__unranked__)보다 먼저.
    assert out["disclosureKey"].to_list()[-1] == "__NOT_IN_SPINE__"


def _noteRow(**kw) -> dict:
    """alignNotes 테스트용 최소 행 (chapter/sectionLeaf/blockLeaf/disclosureKey/period)."""
    base = {"chapter": None, "sectionLeaf": None, "blockLeaf": None, "disclosureKey": None, "period": "2020Q4"}
    base.update(kw)
    return base


def test_align_notes_skeleton_match() -> None:
    """옛 split 주석행(null key, blockLeaf=제목)이 회사 native 뼈대(scope,제목)→NT_ 에 정렬."""
    from dartlab.providers.dart.panel.read import alignNotes

    df = pl.DataFrame(
        [
            # 최근 native 뼈대 (연결 재고자산 → NT_D826380)
            _noteRow(
                chapter="III. 재무에 관한 사항",
                sectionLeaf="3. 연결재무제표 주석",
                blockLeaf="재고자산",
                disclosureKey="NT_D826380",
                period="2025Q4",
            ),
            # 옛 split 주석행 (같은 제목, null key)
            _noteRow(
                chapter="(첨부)연결재무제표", sectionLeaf="3. 연결재무제표 주석", blockLeaf="재고자산", period="2020Q4"
            ),
        ]
    )
    out = alignNotes(df)
    aligned = out.filter(pl.col("period") == "2020Q4")
    assert aligned["disclosureKey"].to_list() == ["NT_D826380"]  # 옛 행이 최근 뼈대로 정렬


def test_align_notes_unmatched_stays_narrative() -> None:
    """어느 뼈대(자기·전역)에도 없는 제목은 null 유지 — 가짜 NT_ 0."""
    from dartlab.providers.dart.panel.read import alignNotes

    df = pl.DataFrame(
        [
            _noteRow(
                chapter="III. 재무에 관한 사항",
                sectionLeaf="3. 연결재무제표 주석",
                blockLeaf="재고자산",
                disclosureKey="NT_D826380",
                period="2025Q4",
            ),
            # 전역 taxonomy 에도 없는 가공 제목 → 정렬 안 됨(narrative)
            _noteRow(
                chapter="(첨부)연결재무제표",
                sectionLeaf="3. 연결재무제표 주석",
                blockLeaf="가공의비표준제목xyz",
                period="2020Q4",
            ),
        ]
    )
    out = alignNotes(df)
    assert out.filter(pl.col("blockLeaf") == "가공의비표준제목xyz")["disclosureKey"].to_list() == [None]


def test_align_notes_global_fallback_no_own_skeleton() -> None:
    """회사 자기 native 노트 0(뼈대 없음)이라도 표준 제목은 전역 taxonomy 로 정렬 — cross-company 흡수."""
    from dartlab.providers.dart.panel.read import alignNotes

    df = pl.DataFrame(
        [
            # native NT_ 0 — 옛 split 표준 제목만
            _noteRow(
                chapter="(첨부)연결재무제표", sectionLeaf="3. 연결재무제표 주석", blockLeaf="재고자산", period="2020Q4"
            )
        ]
    )
    out = alignNotes(df)
    assert out["disclosureKey"].to_list() == ["NT_D826380"]  # 전역 표준(연결 재고자산)으로 정렬


def test_align_notes_scope_separation() -> None:
    """scope 분리 — 연결 split 행은 별도 native(826385)가 아니라 연결 표준(826380)으로 정렬."""
    from dartlab.providers.dart.panel.read import alignNotes

    df = pl.DataFrame(
        [
            # 별도 native 뼈대 (재고자산 별도 → NT_D826385)
            _noteRow(
                chapter="(첨부)재무제표",
                sectionLeaf="5. 재무제표 주석",
                blockLeaf="재고자산",
                disclosureKey="NT_D826385",
                period="2025Q4",
            ),
            # 연결 split 행 (연결 마커) — 별도 native 와 scope 달라 그 코드 안 받고, 전역 연결 표준(826380) 받음
            _noteRow(
                chapter="(첨부)연결재무제표", sectionLeaf="3. 연결재무제표 주석", blockLeaf="재고자산", period="2020Q4"
            ),
        ]
    )
    out = alignNotes(df)
    consol = out.filter(pl.col("period") == "2020Q4")
    assert consol["disclosureKey"].to_list() == ["NT_D826380"]  # 별도(826385) 아님 — scope 분리 + 전역 연결 표준


def test_align_notes_non_note_region_untouched() -> None:
    """비-주석 narrative 행(sectionLeaf 에 '주석' 없음)은 표준 제목이어도 정렬 안 함 — 오정렬 차단."""
    from dartlab.providers.dart.panel.read import alignNotes

    df = pl.DataFrame(
        [
            # 사업의 내용 같은 비-주석 영역에 '재고자산' 제목 — 전역에 있어도 안 채움
            _noteRow(
                chapter="II. 사업의 내용", sectionLeaf="3. 원재료 및 생산설비", blockLeaf="재고자산", period="2020Q4"
            )
        ]
    )
    out = alignNotes(df)
    assert out["disclosureKey"].to_list() == [None]  # 주석영역 아님 → null 유지


def test_ensure_panel_from_hf_transient_vs_absent(monkeypatch, tmp_path) -> None:
    """ensurePanelFromHf — 일시실패는 영구 마킹 안 함(재시도 가능), 부재는 1회 마킹(silent-empty 신호).

    회귀 가드: 옛 코드는 시도 *전* 마킹 → 일시 네트워크 실패가 세션 내내 영구 empty 였다.
    또 snapshot_download 는 HF 에 파일 없어도 예외 없이 '성공'(0파일)하므로 부재를 별도 구분해야 한다.
    """
    import huggingface_hub

    import dartlab.config as cfg
    from dartlab.providers.dart.panel import read as R

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    monkeypatch.setattr(R, "_HF_PANEL_ATTEMPTED", set())
    monkeypatch.delenv("DARTLAB_NO_HF_DOWNLOAD", raising=False)

    calls = {"n": 0}

    def transientDownload(**k):
        calls["n"] += 1
        raise RuntimeError("429 transient")  # 파일 안 만듦

    monkeypatch.setattr(huggingface_hub, "snapshot_download", transientDownload)
    R.ensurePanelFromHf("005930")
    R.ensurePanelFromHf("005930")  # 영구 마킹 안 됐으면 다시 시도
    assert calls["n"] == 2  # 재시도됨(일시실패 비영구)
    assert "kr:005930" not in R._HF_PANEL_ATTEMPTED

    def absentDownload(**k):
        calls["n"] += 1  # 성공하나 파일 0 (HF 에 artifact 부재)

    monkeypatch.setattr(huggingface_hub, "snapshot_download", absentDownload)
    before = calls["n"]
    R.ensurePanelFromHf("000660")
    R.ensurePanelFromHf("000660")  # 부재 마킹 → 2번째는 호출 안 됨
    assert calls["n"] == before + 1  # 1회만(부재 영구 마킹)
    assert "kr:000660" in R._HF_PANEL_ATTEMPTED
