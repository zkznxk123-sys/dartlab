"""캐러셀이 실제로 가리키는 hero 이미지를 전수 스캔 — 평면 벡터·도식·인포그래픽(=쓰레기 후보)을 색복잡도로 잡는다.

## 왜 색복잡도인가
생성형(FLUX) hero 이미지 중 일부가 **실사 사진이 아니라 평면 벡터 도식/인포그래픽**으로 나온다
(예: 막대그래프 모양, 텍스트가 박힌 설명 카드, 단색 그라데이션 배경). 이런 건 흑백 풀블리드 카드
배경으로 깔리면 깨져 보인다. 평면 그래픽은 색이 수십 개뿐이고, 실사 사진은 수천 개다 — 200×200
으로 줄여 5bit/채널로 양자화한 뒤 고유색 수를 세면 둘이 갈린다.

## 한계 (눈검수 필수)
색복잡도는 **자동 판정이 아니라 우선순위**다. 어두운/흑백 실사 사진(야간 정유탑·검은 분말·폐허)도
색이 적어 같이 잡힌다. 그래서 색<THRESH 또는 이름패턴(bg-*·grid·gap·chart·structure 등) 으로
**의심 목록만** 뽑고, 사람이 Read 로 한 장씩 보고 쓰레기 여부를 확정한다. 핀터레스트 등 저작권
있는 소스 금지 — 교체는 `fetch_cc0_images.py`(Wikimedia Commons·Openverse PD/CC0) 로만.

## 사용
    uv run python -X utf8 blog/_scripts/audit_carousel_images.py            # 의심 목록(색<600 또는 이름패턴)
    uv run python -X utf8 blog/_scripts/audit_carousel_images.py --all      # 전체(색 오름차순)
    uv run python -X utf8 blog/_scripts/audit_carousel_images.py --max 250  # 색<250 만(평면 벡터에 집중)
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BLOG = ROOT / "blog" / "05-company-reports"
ASSETS = ROOT / "sns" / "assets"
NAME_HINT = re.compile(
    r"(^bg-|grid|timeline|gap|chart|structure|diagram|ess-containers|cell-production|valuation)", re.I
)


def companyKey(folder: str) -> str:
    """블로그 폴더명(NN-코드-슬러그)에서 회사 키(6자리 코드 또는 티커)를 뽑는다."""
    for p in folder.split("-"):
        if p.isdigit() and len(p) == 6:
            return p
        if p.isalpha() and p.isupper() and 1 <= len(p) <= 5:
            return p
    parts = folder.split("-")
    return parts[1] if len(parts) > 1 else folder


def foldersForKey(code: str) -> list[Path]:
    """sns/assets 아래 그 회사 키에 해당하는 자산 폴더들(코드·코드-슬러그 병합)."""
    return [d for d in sorted(ASSETS.iterdir()) if d.is_dir() and (d.name == code or d.name.split("-")[0] == code)]


def readCarousel(md: Path) -> dict | None:
    """블로그 index.md frontmatter 의 carousel 블록(없거나 파싱 실패면 None)."""
    text = md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return None
    try:
        fm = yaml.safe_load(m.group(1))
    except Exception:
        return None
    return fm.get("carousel") if isinstance(fm, dict) else None


def resolveImage(code: str, image: str) -> Path | None:
    """슬라이드 image 프리픽스를 실제 파일로(resolveSlideImage 동형: name.startswith(image+'.'))."""
    for d in foldersForKey(code):
        for f in sorted(d.iterdir()):
            if f.is_file() and f.name.startswith(image + "."):
                return f
    return None


def colorComplexity(f: Path) -> int:
    """200×200·5bit/채널 양자화 후 고유색 수. 평면 벡터≈수십, 실사≈수천. 실패 시 -1."""
    try:
        im = Image.open(f).convert("RGB").resize((200, 200))
        return len({(r >> 3, g >> 3, b >> 3) for r, g, b in im.get_flattened_data()})
    except Exception:
        return -1


def scanRows() -> list[tuple[int, str, str, str, bool]]:
    """전 캐러셀 hero 이미지 → (색복잡도, 코드, 이미지명, 폴더, 이름패턴여부) 리스트(중복 제거)."""
    seen: set[Path] = set()
    rows: list[tuple[int, str, str, str, bool]] = []
    for md in sorted(BLOG.glob("*/index.md")):
        car = readCarousel(md)
        if not car:
            continue
        code = companyKey(md.parent.name)
        imgs = [s.get("image") for s in (car.get("slides") or []) if s.get("image")]
        for img in dict.fromkeys(imgs):
            f = resolveImage(code, img)
            if f is None or f in seen:
                continue
            seen.add(f)
            rows.append((colorComplexity(f), code, img, md.parent.name, bool(NAME_HINT.search(img))))
    rows.sort()
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="캐러셀 hero 이미지 색복잡도 감사(평면 벡터/도식 탐지)")
    parser.add_argument("--all", action="store_true", help="전체 출력(색 오름차순)")
    parser.add_argument("--max", type=int, default=600, help="이 값 미만 색복잡도만(기본 600)")
    args = parser.parse_args()

    rows = scanRows()
    shown = rows if args.all else [r for r in rows if r[0] < args.max or r[4]]
    print(f"총 {len(rows)}장 · 표시 {len(shown)}장 (색<{args.max} 또는 이름패턴)")
    print("  색복잡도  힌트  코드      이미지명                    캐러셀")
    for cc, code, img, folder, nh in shown:
        print(f"  {cc:>6}  {'NAME' if nh else '    '}  {code:>7}  {img:<26} {folder}")
    print("\n→ 색<~250 = 평면 벡터/도식 거의 확실. 250~600 = 눈검수 필요(어두운 실사 섞임).")
    print("  교체: fetch_cc0_images.py(Commons·Openverse PD/CC0) → 눈검수 → build_index → publish_assets_hf.")


if __name__ == "__main__":
    main()
