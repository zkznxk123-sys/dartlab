"""sns/carousels/E* 손글 편집 카피 → 매칭 블로그 글 frontmatter `carousel:` 블록 주입.

E-폴더 hook.json(editorial/editorialBeat/editorialStat 카드) + caption.txt + comment_pinned.txt + meta.json
→ carousel: YAML 블록 → blog/05-company-reports/{NN}-{code}-{slug}/index.md frontmatter 에 주입.
이로써 손글 SSOT 가 sns/carousels 분리본 → 블로그 글 frontmatter 단일로 이관(build_carousel_contracts 가 그걸 읽음).

매핑 = code 기준(E-폴더엔 blogSlug 없음). code → 블로그 글 정확히 1편이면 **자동 주입**(--apply).
다편(000660·005930·267260…)·무매칭은 **제안만**(운영자 배치) + sidecar `_carousel_block.yaml` 로 쉽게 붙여넣기.
멱등 — 이미 carousel: 있으면 skip. 본문(산문) 무변경(frontmatter 끝에만 추가).

Usage(운영자 로컬·1회성 이관·이미 31편 완료):
  uv run python -X utf8 blog/_scripts/migrate_carousels_to_blog.py --dry-run   # 계획만
  uv run python -X utf8 blog/_scripts/migrate_carousels_to_blog.py --apply     # 1:1 자동 주입
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CAROUSELS_DIR = ROOT / "sns" / "carousels"
BLOG_DIR = ROOT / "blog" / "05-company-reports"

_SLIDE_LAYOUTS = ("editorial", "editorialBeat", "editorialStat")
_SLIDE_FIELDS = ("date", "kicker", "line", "sub", "bigNumber", "unit", "context")


# ── YAML 가독성: 여러 줄 문자열은 `|` 블록 스칼라로(캡션·고정댓글) ──
def _str_representer(dumper, data):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


yaml.add_representer(str, _str_representer)


def _image_stem(bg: str | None) -> str | None:
    if not bg:
        return None
    name = bg.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[0] or None


def _slide_from_card(card: dict) -> dict | None:
    layout = card.get("hookLayout")
    if layout not in _SLIDE_LAYOUTS:
        return None
    hook = card.get("hook", {})
    slide: dict = {"layout": layout}
    for f in _SLIDE_FIELDS:
        v = hook.get(f)
        if v not in (None, ""):
            slide[f] = v
    img = _image_stem(card.get("bgImage"))
    if img:
        slide["image"] = img
    return slide


def _read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    t = path.read_text(encoding="utf-8").strip()
    return t or None


def _read_meta(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except json.JSONDecodeError:
        return {}


def _carousel_block(folder: Path) -> dict | None:
    """E-폴더 → carousel: 블록 dict({title?,caption?,pinnedComment?,slides[]}). 슬라이드 0이면 None."""
    try:
        data = json.loads((folder / "hook.json").read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return None
    slides = [s for c in data.get("cards", []) if (s := _slide_from_card(c))]
    if not slides:
        return None
    block: dict = {}
    meta = _read_meta(folder / "meta.json")
    title = str(meta.get("title", "")).strip()
    if title:
        block["title"] = title
    caption = _read_text(folder / "caption.txt")
    if caption:
        block["caption"] = caption
    pinned = _read_text(folder / "comment_pinned.txt")
    if pinned:
        block["pinnedComment"] = pinned
    block["slides"] = slides
    return block


def _code_of_folder(name: str) -> str:
    """블로그 폴더명 `02-003230-samyang-foods` → code `003230`(6자리 또는 티커 대문자)."""
    m = re.match(r"^\d+-([0-9A-Za-z]+)-", name)
    return m.group(1).upper() if m and m.group(1).isalpha() else (m.group(1) if m else "")


def _code_of_e(folder: Path) -> str:
    meta = _read_meta(folder / "meta.json")
    code = str(meta.get("stockCode") or meta.get("sourceCompany") or "").strip()
    return code.upper() if code.isalpha() else code


def _blog_by_code() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for d in sorted(BLOG_DIR.iterdir()):
        if not d.is_dir() or not (d / "index.md").exists():
            continue
        code = _code_of_folder(d.name)
        if code:
            out.setdefault(code, []).append(d.name)
    return out


def _has_carousel(index_md: Path) -> bool:
    text = index_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)
    fm = text[3 : end if end > 0 else len(text)]
    return bool(re.search(r"^carousel:", fm, re.M))


def _inject(index_md: Path, block: dict) -> bool:
    """index.md frontmatter 끝에 carousel: 블록 주입(본문 무변경). 이미 있으면 False."""
    text = index_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)  # 닫는 --- 의 \n 위치
    if end < 0:
        return False
    if re.search(r"^carousel:", text[3:end], re.M):
        return False
    yaml_block = yaml.dump({"carousel": block}, allow_unicode=True, sort_keys=False, width=10000).rstrip()
    new_text = text[:end] + "\n" + yaml_block + text[end:]
    index_md.write_text(new_text, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="계획만(기본)")
    parser.add_argument("--apply", action="store_true", help="1:1 자동 주입 실행")
    parser.add_argument(
        "--place",
        action="append",
        default=[],
        help="다편 회사 명시 배치 `E폴더=블로그폴더`(반복 가능). 토픽 매칭 운영자 판단.",
    )
    args = parser.parse_args()

    blog_by_code = _blog_by_code()
    e_folders = [d for d in sorted(CAROUSELS_DIR.iterdir()) if d.is_dir() and d.name.startswith("E")]
    e_by_code: dict[str, list[str]] = {}
    for d in e_folders:
        c = _code_of_e(d)
        if c:
            e_by_code.setdefault(c, []).append(d.name)

    auto, ambiguous, no_blog, no_slides = [], [], [], []
    for d in e_folders:
        code = _code_of_e(d)
        block = _carousel_block(d)
        if not block:
            no_slides.append(d.name)
            continue
        candidates = blog_by_code.get(code, [])
        if len(candidates) == 1 and len(e_by_code.get(code, [])) == 1:
            auto.append((d, code, candidates[0], block))
        elif not candidates:
            no_blog.append((d.name, code))
            (d / "_carousel_block.yaml").write_text(
                yaml.dump({"carousel": block}, allow_unicode=True, sort_keys=False, width=10000),
                encoding="utf-8",
            )
        else:
            ambiguous.append((d.name, code, candidates))
            (d / "_carousel_block.yaml").write_text(
                yaml.dump({"carousel": block}, allow_unicode=True, sort_keys=False, width=10000),
                encoding="utf-8",
            )

    print(
        f"E-폴더 {len(e_folders)}개 — 자동매칭 {len(auto)} · 다편/충돌 {len(ambiguous)} · 무블로그 {len(no_blog)} · 무슬라이드 {len(no_slides)}"
    )
    print("\n[자동 1:1] (code→블로그 1편·E 1개):")
    n_inject = n_skip = 0
    for d, code, folder, block in auto:
        idx = BLOG_DIR / folder / "index.md"
        if _has_carousel(idx):
            print(f"  skip(이미 carousel:): {code} → {folder}")
            n_skip += 1
            continue
        if args.apply:
            ok = _inject(idx, block)
            print(f"  {'주입' if ok else '실패'}: {code} {d.name} → {folder} ({len(block['slides'])}장)")
            n_inject += ok
        else:
            print(f"  주입예정: {code} {d.name} → {folder} ({len(block['slides'])}장)")
    if ambiguous:
        print("\n[다편/충돌] (운영자 배치 — sidecar _carousel_block.yaml 생성):")
        for name, code, cands in ambiguous:
            print(f"  {code} {name} → 후보 {cands}")
    if no_blog:
        print("\n[무블로그] (블로그 글 없음 — 글 작성 후 배치, sidecar 생성):")
        for name, code in no_blog:
            print(f"  {code} {name}")
    if no_slides:
        print(f"\n[무슬라이드] {no_slides}")
    # 다편 회사 명시 배치(운영자 토픽 매칭) — `--place E폴더=블로그폴더`
    if args.place:
        print("\n[명시 배치] (다편 회사 — 토픽 매칭):")
        for spec in args.place:
            e_name, _, blog_folder = spec.partition("=")
            block = _carousel_block(CAROUSELS_DIR / e_name)
            idx = BLOG_DIR / blog_folder / "index.md"
            if not block or not idx.exists():
                print(f"  실패(경로): {spec}")
                continue
            if _has_carousel(idx):
                print(f"  skip(이미 carousel:): {spec}")
                continue
            if args.apply:
                ok = _inject(idx, block)
                print(f"  {'주입' if ok else '실패'}: {e_name} → {blog_folder} ({len(block['slides'])}장)")
                n_inject += ok
            else:
                print(f"  주입예정: {e_name} → {blog_folder} ({len(block['slides'])}장)")

    if args.apply:
        print(f"\n완료 — {n_inject}편 주입(skip {n_skip}). blog git diff 눈검수 후 발행.")
    else:
        print("\ndry-run — 주입 안 함. --apply 로 1:1 자동 주입.")


if __name__ == "__main__":
    main()
