"""build_carousel_contracts + migrate_carousels_to_blog 단위 테스트(운영자 로컬·CI 무관).

핵심 회귀 가드:
  - 같은 코드 다글(slug A·B) → 계약 2개·index posts 2엔트리(덮어쓰기 0) = 1:N.
  - index posts date 내림차순.
  - carousel: 없는 글 = 계약 없음. 슬라이드 0 = skip.
  - _normalize_slide layout enum.
  - migration _inject 멱등(2회 = 동일).

실행: uv run python -X utf8 -m pytest blog/_scripts/test_carousel_contracts.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_carousel_contracts as bcc  # noqa: E402
import migrate_carousels_to_blog as mig  # noqa: E402


def _write_post(
    blog_dir: Path, folder: str, *, code: str, date: str, with_carousel: bool, slides_yaml: str = ""
) -> None:
    """fixture 블로그 글 index.md 작성(frontmatter + 본문)."""
    d = blog_dir / folder
    d.mkdir(parents=True, exist_ok=True)
    carousel = ""
    if with_carousel:
        carousel = f"""carousel:
  title: "포스트 {folder}"
  caption: |
    캡션 문단1.

    캡션 문단2.
  pinnedComment: "근거·면책"
{slides_yaml}"""
    (d / "index.md").write_text(
        f"""---
title: "글 {folder}"
date: {date}
stockCode: "{code}"
corpName: "테스트{code}"
{carousel}---
본문 산문. 숫자 21 과 7배.
""",
        encoding="utf-8",
    )


_SLIDES_A = """  slides:
    - layout: editorial
      line: "커버 라인 A"
      image: hero-a
    - layout: editorialStat
      kicker: "마진"
      bigNumber: "21%"
"""
_SLIDES_B = """  slides:
    - layout: editorialBeat
      line: "비트 라인 B"
"""


def test_one_to_n_same_code_two_slugs(tmp_path: Path) -> None:
    """같은 코드(999999) 다른 슬러그 2글 → 계약 2개(덮어쓰기 0) = 1:N."""
    blog = tmp_path / "blog"
    _write_post(blog, "01-999999-aaa", code="999999", date="2026-01-02", with_carousel=True, slides_yaml=_SLIDES_A)
    _write_post(blog, "02-999999-bbb", code="999999", date="2026-01-01", with_carousel=True, slides_yaml=_SLIDES_B)
    contracts = bcc.build_contracts(blog)
    assert set(contracts.keys()) == {"999999-aaa", "999999-bbb"}
    assert contracts["999999-aaa"]["code"] == "999999"
    assert contracts["999999-bbb"]["code"] == "999999"
    assert len(contracts["999999-aaa"]["slides"]) == 2
    assert len(contracts["999999-bbb"]["slides"]) == 1


def test_index_date_desc(tmp_path: Path) -> None:
    """index posts = date 내림차순(인스타식 최신순)."""
    blog = tmp_path / "blog"
    _write_post(blog, "01-999999-aaa", code="999999", date="2026-01-02", with_carousel=True, slides_yaml=_SLIDES_A)
    _write_post(blog, "02-888888-bbb", code="888888", date="2026-03-09", with_carousel=True, slides_yaml=_SLIDES_B)
    posts = bcc.build_index(bcc.build_contracts(blog))
    assert [p["slug"] for p in posts] == ["888888-bbb", "999999-aaa"]
    assert posts[0]["date"] == "2026-03-09"


def test_no_carousel_excluded(tmp_path: Path) -> None:
    """carousel: 없는 글 = 계약 없음(자동 덱만, 피드 비노출)."""
    blog = tmp_path / "blog"
    _write_post(blog, "01-777777-ccc", code="777777", date="2026-01-01", with_carousel=False)
    assert bcc.build_contracts(blog) == {}


def test_carousel_without_slides_skipped(tmp_path: Path) -> None:
    """carousel: 있어도 editorial 슬라이드 0이면 skip."""
    blog = tmp_path / "blog"
    _write_post(
        blog, "01-666666-ddd", code="666666", date="2026-01-01", with_carousel=True, slides_yaml="  slides: []\n"
    )
    assert bcc.build_contracts(blog) == {}


def test_spec_overlay_carried(tmp_path: Path) -> None:
    """hero/order/notes 오버레이가 계약 spec 에 실린다(blog 번들 비의존)."""
    blog = tmp_path / "blog"
    sy = _SLIDES_A + "  hero: cover-x\n  order:\n    - segment\n  notes:\n    segment: 손글 한줄\n"
    _write_post(blog, "01-555555-eee", code="555555", date="2026-01-01", with_carousel=True, slides_yaml=sy)
    c = bcc.build_contracts(blog)["555555-eee"]
    assert c["spec"]["hero"] == "cover-x"
    assert c["spec"]["order"] == ["segment"]
    assert c["spec"]["notes"] == {"segment": "손글 한줄"}


@pytest.mark.parametrize(
    "raw,expect",
    [
        ({"layout": "editorial", "line": "x", "image": "y"}, {"layout": "editorial", "line": "x", "image": "y"}),
        ({"layout": "editorialStat", "bigNumber": "21%"}, {"layout": "editorialStat", "bigNumber": "21%"}),
        ({"layout": "bottomLeft", "line": "x"}, None),  # editorial 3종 아님 → None
        ({"line": "x"}, None),  # layout 없음
        ("notadict", None),
    ],
)
def test_normalize_slide(raw, expect) -> None:
    assert bcc._normalize_slide(raw) == expect


def test_migration_idempotent(tmp_path: Path) -> None:
    """_inject 2회 = 동일(이미 carousel: 있으면 두 번째는 False)."""
    blog = tmp_path / "blog"
    _write_post(blog, "01-444444-fff", code="444444", date="2026-01-01", with_carousel=False)
    idx = blog / "01-444444-fff" / "index.md"
    block = {"title": "T", "slides": [{"layout": "editorial", "line": "L"}]}
    assert mig._inject(idx, block) is True
    first = idx.read_text(encoding="utf-8")
    assert mig._has_carousel(idx) is True
    assert mig._inject(idx, block) is False  # 멱등 — 두 번째 주입 안 함
    assert idx.read_text(encoding="utf-8") == first  # 본문/frontmatter 불변


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
