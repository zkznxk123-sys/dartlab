"""
블로그 글 SEO 자동 스코어링.
전체 기업이야기 글을 순회하며 SEO 품질을 점수화한다.

사용: uv run python -X utf8 scripts/blog/audit_seo.py
"""

import os
import re
import sys

BLOG_DIR = "blog/05-company-reports"
FORBIDDEN_PATTERNS = [
    r"~입니다$",  # 존댓말 (블로그 톤 아님)
    r"살펴보겠습니다",
    r"알아보겠습니다",
    r"~하겠습니다$",
    r"분석해 보겠습니다",
]


def score_post(folder_path: str) -> dict:
    """단일 글의 SEO 점수를 산출한다."""
    index_path = os.path.join(folder_path, "index.md")
    if not os.path.isfile(index_path):
        return None

    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    # frontmatter 분리
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    frontmatter = parts[1]
    body = parts[2]

    scores = {}
    total = 0
    max_total = 0

    # 1. Frontmatter 완성도 (20점)
    fm_score = 0
    fm_max = 20
    required_fields = ["title", "description", "category", "series", "stockCode", "tags", "ogImage"]
    for field in required_fields:
        if field + ":" in frontmatter:
            fm_score += 2
        else:
            fm_score += 0
    # description 길이
    desc_match = re.search(r'description:\s*"(.+?)"', frontmatter, re.DOTALL)
    if desc_match:
        desc_len = len(desc_match.group(1))
        if 80 <= desc_len <= 200:
            fm_score += 4
        elif desc_len > 200:
            fm_score += 2
        else:
            fm_score += 1
    # tags 개수
    tag_count = frontmatter.count("  - ")
    if tag_count >= 5:
        fm_score += 2
    elif tag_count >= 3:
        fm_score += 1
    scores["frontmatter"] = min(fm_score, fm_max)
    total += scores["frontmatter"]
    max_total += fm_max

    # 2. 본문 길이 (15점)
    body_len = len(body.replace(" ", "").replace("\n", ""))
    len_max = 15
    if body_len >= 12000:
        len_score = 15
    elif body_len >= 8000:
        len_score = 12
    elif body_len >= 5000:
        len_score = 8
    else:
        len_score = 3
    scores["length"] = len_score
    scores["length_chars"] = body_len
    total += len_score
    max_total += len_max

    # 3. H2 구조 (15점)
    h2s = re.findall(r"^## (.+)$", body, re.MULTILINE)
    h2_max = 15
    h2_count = len(h2s)
    if 5 <= h2_count <= 15:
        h2_score = 10
    elif h2_count > 15:
        h2_score = 7
    elif h2_count >= 3:
        h2_score = 5
    else:
        h2_score = 2
    # H2에 한국어 포함
    korean_h2 = sum(1 for h in h2s if re.search(r"[가-힣]", h))
    if korean_h2 == h2_count and h2_count > 0:
        h2_score += 5
    elif korean_h2 > h2_count * 0.7:
        h2_score += 3
    scores["h2"] = min(h2_score, h2_max)
    scores["h2_count"] = h2_count
    total += scores["h2"]
    max_total += h2_max

    # 4. 내부 링크 (15점)
    internal_links = re.findall(r"\(/blog/[^)]+\)", body)
    il_max = 15
    il_count = len(internal_links)
    if il_count >= 5:
        il_score = 15
    elif il_count >= 3:
        il_score = 10
    elif il_count >= 1:
        il_score = 5
    else:
        il_score = 0
    scores["internal_links"] = il_score
    scores["internal_links_count"] = il_count
    total += il_score
    max_total += il_max

    # 5. 외부 출처 (10점)
    external_links = re.findall(r"\(https?://[^)]+\)", body)
    el_max = 10
    el_count = len(external_links)
    if el_count >= 5:
        el_score = 10
    elif el_count >= 3:
        el_score = 7
    elif el_count >= 1:
        el_score = 3
    else:
        el_score = 0
    scores["external_links"] = el_score
    scores["external_links_count"] = el_count
    total += el_score
    max_total += el_max

    # 6. 시각 자산 (15점)
    images = re.findall(r"!\[.+?\]\(.+?\)", body)
    svg_count = sum(1 for i in images if ".svg" in i)
    img_count = sum(1 for i in images if ".webp" in i or ".png" in i or ".jpg" in i)
    vis_max = 15
    vis_total = svg_count + img_count
    if vis_total >= 5:
        vis_score = 15
    elif vis_total >= 3:
        vis_score = 10
    elif vis_total >= 1:
        vis_score = 5
    else:
        vis_score = 0
    scores["visuals"] = vis_score
    scores["svg_count"] = svg_count
    scores["img_count"] = img_count
    total += vis_score
    max_total += vis_max

    # 7. dartlab 코드 포함 (10점)
    code_blocks = re.findall(r"```python\n.+?```", body, re.DOTALL)
    code_max = 10
    if len(code_blocks) >= 3:
        code_score = 10
    elif len(code_blocks) >= 1:
        code_score = 5
    else:
        code_score = 0
    scores["code_blocks"] = code_score
    scores["code_count"] = len(code_blocks)
    total += code_score
    max_total += code_max

    scores["total"] = total
    scores["max"] = max_total
    scores["pct"] = round(total / max_total * 100) if max_total > 0 else 0

    # 건강 상태
    if scores["pct"] >= 85:
        scores["health"] = "🟢"
    elif scores["pct"] >= 70:
        scores["health"] = "🟡"
    else:
        scores["health"] = "🔴"

    return scores


def main():
    if not os.path.isdir(BLOG_DIR):
        print(f"디렉토리 없음: {BLOG_DIR}")
        sys.exit(1)

    results = []
    for folder in sorted(os.listdir(BLOG_DIR)):
        fp = os.path.join(BLOG_DIR, folder)
        if not os.path.isdir(fp):
            continue
        s = score_post(fp)
        if s:
            results.append((folder, s))

    # 콘솔 출력
    print(f"\n{'=' * 80}")
    print(f"블로그 SEO 스코어링 — {len(results)}편")
    print(f"{'=' * 80}\n")

    print(f"{'글':<45} {'점수':>6} {'건강':>4} {'글자':>7} {'H2':>4} {'링크':>4} {'SVG':>4} {'IMG':>4} {'코드':>4}")
    print("-" * 90)

    for folder, s in results:
        name = folder[:44]
        print(
            f"{name:<45} {s['pct']:>5}% {s['health']:>4} {s['length_chars']:>6} {s['h2_count']:>4} {s['internal_links_count']:>4} {s['svg_count']:>4} {s['img_count']:>4} {s['code_count']:>4}"
        )

    # 약한 글 경고
    weak = [(f, s) for f, s in results if s["pct"] < 70]
    if weak:
        print(f"\n⚠️ 리라이트 후보 ({len(weak)}편):")
        for f, s in weak:
            issues = []
            if s["internal_links_count"] < 3:
                issues.append(f"내부링크 {s['internal_links_count']}개")
            if s["svg_count"] + s["img_count"] < 3:
                issues.append(f"시각자산 {s['svg_count'] + s['img_count']}개")
            if s["length_chars"] < 8000:
                issues.append(f"글자수 {s['length_chars']}")
            print(f"  🔴 {f}: {s['pct']}% — {', '.join(issues)}")

    print(f"\n평균: {sum(s['pct'] for _, s in results) // len(results)}%")


if __name__ == "__main__":
    main()
