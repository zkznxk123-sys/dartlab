"""편집 카드 캐러셀 계약 빌드 — 블로그 글 frontmatter `carousel:` → 단일 `carousels/index.json`.

SSOT = 블로그 글(`blog/05-company-reports/{NN}-{code}-{slug}/index.md`) frontmatter 의 `carousel:` 블록.
한 글 = 한 스토리(회사+주제) = 산문(본문) + 캐러셀(frontmatter). 손글 편집 카피(editorial/editorialBeat/
editorialStat)가 캐러셀의 *중심점(계약)* 이고, landing /cards 가 **굽지 않고** 라이브 렌더한다. 차트·핵심
지표는 그 뒤에 ReportModel 에서 덧붙인다. (옛 `sns/carousels/E*/hook.json` 분리 SSOT 폐기 →
`migrate_carousels_to_blog.py` 로 frontmatter 에 이관됨.)

키 = **글 슬러그**(`003230-samyang-foods`) → 회사당 N편(1:N). 같은 회사 다른 주제 글이 각자 계약.

계약(글당 1파일):
  { code, slug, name, sector?, title?, caption?, pinnedComment?, date?,
    slides: [ {layout, date?|kicker?, line?, sub?, bigNumber?, unit?, context?, image?} ],
    spec?: { hero?, order?, notes? } }
  layout ∈ editorial(커버) | editorialBeat(헤드라인 비트) | editorialStat(큰 숫자)
  image = semantic 파일명(확장자·해시 없음) — 렌더가 hfMedia 매니페스트로 해시 파일명 해석.
  spec = 자동 덱 큐레이션 오버레이(hero/order/notes) — 계약에 실어 /cards 가 blog 번들 비의존.

Serve = HF `eddmpython/dartlab-media` **단일** `carousels/index.json`(posts[]=전 계약, 슬라이드까지·
date 내림차순). 피드·상세 모두 이 1회 fetch 로(별도 인덱스 파일·per-slug round-trip 0). per-slug 파일
안 만든다 — 글 추가/삭제는 이 한 파일 재발행. `carousel:` 블록 있는 글만 계약 → /cards 기본 피드 = 이 글들.

Usage(운영자 로컬·HF_TOKEN=.env):
  uv run python -X utf8 blog/_scripts/build_carousel_contracts.py --dry-run   # 계획만(올리는 것·지울 것)
  uv run python -X utf8 blog/_scripts/build_carousel_contracts.py             # hfMedia 에 발행
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

import yaml
from huggingface_hub import CommitOperationAdd, CommitOperationDelete, HfApi

from dartlab.core.dataConfig import HF_MEDIA_REPO
from dartlab.core.hfRetry import retryHfCall
from dartlab.pipeline.hfUpload import _resolveHfToken

ROOT = Path(__file__).resolve().parents[2]
BLOG_DIR = ROOT / "blog" / "05-company-reports"
MEDIA_PREFIX = "carousels"

_SLIDE_LAYOUTS = ("editorial", "editorialBeat", "editorialStat")
# 슬라이드가 채택하는 필드(나머지 키는 무시). image=semantic 파일명(해시 없음).
_SLIDE_FIELDS = ("date", "kicker", "line", "sub", "bigNumber", "unit", "context", "image")


def _read_frontmatter(md_path: Path) -> dict:
    """index.md 의 `---` frontmatter 블록 → dict(없거나 깨지면 빈 dict). 본문(산문)은 안 읽음."""
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)  # ['', frontmatter, body…]
    if len(parts) < 3:
        return {}
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        sys.stderr.write(f"  bad frontmatter in {md_path.parent.name}: {exc}\n")
        return {}
    return fm if isinstance(fm, dict) else {}


def _slug_from_folder(folder_name: str) -> str:
    """폴더명 `02-003230-samyang-foods` → 슬러그 `003230-samyang-foods`(NN- 접두 제거·posts.ts 와 동일)."""
    return re.sub(r"^\d+-", "", folder_name)


def _code_from(fm: dict, slug: str) -> str:
    """frontmatter stockCode 권위 → 없으면 슬러그 첫 세그먼트가 6자리면 코드."""
    code = str(fm.get("stockCode", "")).strip()
    if code:
        return code
    first = slug.split("-", 1)[0]
    return first if (first.isdigit() and len(first) == 6) else ""


def _normalize_slide(raw: object) -> dict | None:
    """frontmatter 슬라이드 → 계약 슬라이드. editorial 3종만(나머지 layout 무시)."""
    if not isinstance(raw, dict):
        return None
    layout = raw.get("layout")
    if layout not in _SLIDE_LAYOUTS:
        return None
    slide: dict = {"layout": layout}
    for f in _SLIDE_FIELDS:
        v = raw.get(f)
        if v not in (None, ""):
            slide[f] = v
    return slide


def _spec_from(carousel: dict) -> dict | None:
    """자동 덱 큐레이션 오버레이(hero/order/notes) 추출 — 없으면 None."""
    spec: dict = {}
    if carousel.get("hero"):
        spec["hero"] = str(carousel["hero"])
    if isinstance(carousel.get("order"), list):
        spec["order"] = [str(k) for k in carousel["order"]]
    if isinstance(carousel.get("notes"), dict):
        spec["notes"] = {str(k): str(v) for k, v in carousel["notes"].items()}
    return spec or None


def build_contracts(blog_dir: Path = BLOG_DIR) -> dict[str, dict]:
    """블로그 글 → 슬러그별 계약(`carousel:` 블록 있는 글만). 같은 회사 다른 슬러그 = 각자 계약(1:N)."""
    contracts: dict[str, dict] = {}
    for md in sorted(blog_dir.glob("*/index.md")):
        fm = _read_frontmatter(md)
        carousel = fm.get("carousel")
        if not isinstance(carousel, dict):
            continue
        slug = _slug_from_folder(md.parent.name)
        code = _code_from(fm, slug)
        if not code:
            sys.stderr.write(f"  skip(no code): {md.parent.name}\n")
            continue
        slides = [s for raw in (carousel.get("slides") or []) if (s := _normalize_slide(raw))]
        if not slides:
            sys.stderr.write(f"  skip(no slides): {md.parent.name}\n")
            continue
        contract: dict = {
            "code": code,
            "slug": slug,
            "name": str(fm.get("corpName") or carousel.get("name") or code),
            "slides": slides,
        }
        sector = carousel.get("sector") or fm.get("sector")
        if sector:
            contract["sector"] = str(sector)
        title = carousel.get("title") or fm.get("title")
        if title:
            contract["title"] = str(title)
        caption = carousel.get("caption")
        if caption:
            contract["caption"] = str(caption).strip()
        pinned = carousel.get("pinnedComment")
        if pinned:
            contract["pinnedComment"] = str(pinned).strip()
        date = str(fm.get("date") or "").strip()
        if date:
            contract["date"] = date
        spec = _spec_from(carousel)
        if spec:
            contract["spec"] = spec
        if slug in contracts:
            sys.stderr.write(f"  dup slug(덮어쓰기 방지): {slug}\n")
        contracts[slug] = contract
    return contracts


def _existing_carousel_jsons(api: HfApi, repo: str) -> set[str]:
    """repo 의 carousels/*.json 현재 목록(best-effort·공개 repo 는 토큰 없이도 list 가능)."""
    try:
        files = api.list_repo_files(repo_id=repo, repo_type="dataset")
    except Exception:
        return set()
    return {f for f in files if f.startswith(f"{MEDIA_PREFIX}/") and f.endswith(".json")}


def build_index(contracts: dict[str, dict]) -> list[dict]:
    """발간 최신순(date 내림차순, 동률 슬러그) **전체 계약** 배열 — 단일 index.json 의 posts[].
    피드·상세 모두 이 한 파일로(별도 인덱스·per-slug round-trip 0). date 없으면 맨 뒤."""
    return sorted(
        contracts.values(),
        key=lambda c: (c.get("date") or "", c["slug"]),
        reverse=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="게시 안 함, 요약만")
    parser.add_argument("--repo", default=HF_MEDIA_REPO)
    args = parser.parse_args()

    contracts = build_contracts()
    posts = build_index(contracts)
    n_slides = sum(len(c["slides"]) for c in contracts.values())
    n_companies = len({c["code"] for c in contracts.values()})
    print(f"계약: {len(contracts)}편(글) · {n_companies}개 회사 · {n_slides}개 편집 슬라이드 (+ index.json)")

    if args.dry_run:
        for p in posts[:8]:
            c = contracts[p["slug"]]
            layouts = ", ".join(s["layout"] for s in c["slides"][:4])
            print(f"  {c['code']} {p['slug']} · {len(c['slides'])}장 [{layouts}…] {p.get('date', '')}")
        if len(posts) > 8:
            print(f"  … 총 {len(posts)}편")
        # 회사당 다편(1:N) 확인 표시
        by_code: dict[str, list[str]] = {}
        for c in contracts.values():
            by_code.setdefault(c["code"], []).append(c["slug"])
        multi = {k: v for k, v in by_code.items() if len(v) > 1}
        if multi:
            print(f"  회사당 N편(1:N): {', '.join(f'{k}={len(v)}편' for k, v in multi.items())}")
        stale = _existing_carousel_jsons(HfApi(), args.repo) - {f"{MEDIA_PREFIX}/index.json"}
        if stale:
            print(f"  옛 파일 {len(stale)}개 삭제 예정(단일 index.json 만 유지): {', '.join(sorted(stale)[:6])} …")
        print("dry-run — 게시 안 함.")
        return

    api = HfApi(token=_resolveHfToken())
    with tempfile.TemporaryDirectory() as td:
        # 단일 파일 — 전 계약(슬라이드까지)을 index.json 하나에. per-slug 파일 안 만듦.
        idx = Path(td) / "index.json"
        idx.write_text(json.dumps({"posts": posts}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ops = [CommitOperationAdd(path_in_repo=f"{MEDIA_PREFIX}/index.json", path_or_fileobj=str(idx))]
        # 그 외 carousels/*.json(옛 code-키·옛 per-slug) 전부 삭제 — 단일 index.json 만 유지(폴더 청결).
        stale = sorted(_existing_carousel_jsons(api, args.repo) - {f"{MEDIA_PREFIX}/index.json"})
        ops += [CommitOperationDelete(path_in_repo=p) for p in stale]
        retryHfCall(
            api.create_commit,
            repo_id=args.repo,
            repo_type="dataset",
            operations=ops,
            commit_message=f"carousels single index: {len(contracts)} posts ({n_companies} companies), -{len(stale)} stale",
        )
    print(f"완료 — {args.repo} carousels/index.json 단일 파일 게시({len(contracts)}편, 옛 {len(stale)}개 삭제).")


if __name__ == "__main__":
    main()
