"""Stage B-2 — 생성된 review 보고서 → QA 페어 추출.

publishBatch 완료 후 실행.
blog/05-company-reports/*/index.md → data/finslm/raw/review_pairs.jsonl

실행:
    uv run python -X utf8 scripts/finslm/extractReviews.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BLOG_DIR = ROOT / "blog" / "05-company-reports"
OUT = ROOT / "data" / "finslm" / "raw" / "review_pairs.jsonl"

SYSTEM_PROMPT = (
    "당신은 dartlab 한국/미국 공시 분석 전문가입니다. "
    "재무제표 데이터를 기반으로 기업을 분석합니다. "
    "숫자는 원본 그대로 인용하고, 근거 없는 주장은 하지 않습니다. "
    "6막 서사 구조(사업이해→수익성→현금→안정성→자본배분→전망)로 분석합니다."
)


def _sharegpt(system: str, human: str, gpt: str, meta: dict) -> dict:
    return {
        "conversations": [
            {"from": "system", "value": system},
            {"from": "human", "value": human},
            {"from": "gpt", "value": gpt},
        ],
        "metadata": meta,
    }


def main() -> int:
    dirs = sorted(BLOG_DIR.glob("*/"))
    pairs: list[dict] = []

    for d in dirs:
        idx = d / "index.md"
        if not idx.exists():
            continue
        text = idx.read_text(encoding="utf-8")
        if len(text) < 500:
            continue

        # frontmatter
        fm_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        meta: dict[str, str] = {}
        if fm_match:
            for line in fm_match.group(1).split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"')

        code = meta.get("stockCode", "")
        corp = meta.get("corpName", d.name)
        template = meta.get("storyTemplate", "")
        body = text[fm_match.end():].strip() if fm_match else text

        # 전체 보고서 QA
        pairs.append(_sharegpt(
            SYSTEM_PROMPT,
            f"{corp}({code}) 종합 재무분석 보고서를 작성해줘.",
            body[:10000],
            {"stock_code": code, "intent": "act_all", "source": "review_batch", "template": template},
        ))

        # 6막 분리
        act_re = re.compile(r"^(#{1,3})\s*((?:제\s*\d막|1막|2막|3막|4막|5막|6막).+)", re.MULTILINE)
        acts = list(act_re.finditer(body))
        for i, m in enumerate(acts):
            start = m.end()
            end = acts[i + 1].start() if i + 1 < len(acts) else len(body)
            title = m.group(2).strip()
            content = body[start:end].strip()
            if len(content) > 100:
                pairs.append(_sharegpt(
                    SYSTEM_PROMPT,
                    f"{corp}({code})의 {title}을 분석해줘.",
                    content[:5000],
                    {"stock_code": code, "intent": f"review_act", "source": "review_batch"},
                ))

        # 섹션별 (## 헤더)
        section_re = re.compile(r"^##\s+(?!제\d막)(.+)", re.MULTILINE)
        sects = list(section_re.finditer(body))
        for i, m in enumerate(sects):
            start = m.end()
            end = sects[i + 1].start() if i + 1 < len(sects) else len(body)
            sec_name = m.group(1).strip()
            content = body[start:end].strip()
            if len(content) > 100 and len(content) < 5000:
                pairs.append(_sharegpt(
                    SYSTEM_PROMPT,
                    f"{corp}({code})의 {sec_name} 분석.",
                    content[:4000],
                    {"stock_code": code, "intent": "review_section", "source": "review_batch"},
                ))

    # 저장
    with open(OUT, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"[review] {len(pairs)}개 페어 → {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
