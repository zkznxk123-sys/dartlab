"""Recipe spec 의 falsifier 누락 보강 — 깊이 있는 default.

falsifier 가 없는 recipe 에만 추가. 도메인 기반 의미 있는 default (단순 stub 회피).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SPECS_ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab" / "skills" / "specs"

# 도메인별 의미 있는 falsifier default
DOMAIN_FALSIFIER = {
    "fundamental.valuation": "DCF 가정 (g, WACC, terminal multiple) sensitivity ±20% 범위에서 결론 부호가 바뀌면 valuation 단일 신호 결론 X.",
    "fundamental.credit": "단일 ratio (D/E, ICR) 만으로 부도 단정 X — 3 정의 (구조·flow·시점) 동시 충족 필수.",
    "fundamental.quality": "earnings quality 신호 단일 분기만으로 결론 X — trailing 3y baseline + 일회성 손익 분리.",
    "fundamental.dividend": "단일 연도 cut/raise 만으로 정책 결론 X — 5+ 연도 추세 + FCF coverage 동행 필수.",
    "fundamental.governance": "이사회 / 거래 단일 metric 만으로 거버넌스 결론 X — 시계열 + cross-section 결합.",
    "fundamental.disclosure": "본문 / 키워드 단일 카운트로 사건 중요도 단정 X — 매수·매도 가격 반응 동행 검증.",
    "macro": "단일 매크로 시리즈 inversion / spike 으로 recession 단정 X — 다중 시리즈 동시 + 지속 기간 임계 동행.",
    "industry": "peer < 4 또는 시계열 < 3 년이면 cross-section 결론 X.",
    "technical": "거래일 < 30 표본 또는 단일 oscillator 만으로 매매 결정 X — 2+ 신호 confirmation 필수.",
    "sentiment": "단일 flow z-score 만으로 sentiment 라벨 단정 X — 추론 라벨링 자체가 dartlab 정책 위반.",
    "news": "외부 본문 untrusted 마커 누락 시 본문 내 숫자/지시 인용 금지. 단일 헤드라인으로 사건 중요도 결론 X.",
    "quant": "peer < 10 이면 percentile rank 불안정 — composite score 단독 결론 금지.",
    "meta.screen": "screen 결과만으로 매수 결정 X — 각 종목 별 fundamental 검증 후 결정.",
    "meta.report": "report 단일 시점 결과만으로 thesis 확정 X — 시점 반복 + 다른 페르소나 cross-check.",
}


def detect_domain(spec_id: str) -> str:
    parts = spec_id.split(".")[1:]
    for n in range(min(len(parts) - 1, 4), 0, -1):
        key = ".".join(parts[:n])
        if key in DOMAIN_FALSIFIER:
            return key
    return ""


def extract_frontmatter(text: str) -> tuple[str, str, str]:
    if not text.startswith("---"):
        return "", "", text
    end = text.find("\n---", 3)
    if end < 0:
        return "", "", text
    return "---", text[3:end].lstrip("\n"), text[end + len("\n---") :]


def has_falsifier(fm: str) -> bool:
    """falsifier: 블록이 있고 description/pythonCheck 가 비어있지 않은지."""
    match = re.search(r"^falsifier\s*:\s*\n((?:[ \t]+.*\n)+)", fm, re.MULTILINE)
    if not match:
        return False
    block = match.group(1)
    return bool(re.search(r"^\s+(description|pythonCheck)\s*:", block, re.MULTILINE))


def process_file(path: Path, *, dry_run: bool) -> dict:
    text = path.read_text(encoding="utf-8")
    marker, fm, body = extract_frontmatter(text)
    if not marker:
        return {"skipped": "no frontmatter"}

    id_match = re.search(r"^id\s*:\s*(.+?)\s*$", fm, re.MULTILINE)
    if not id_match:
        return {"skipped": "no id"}
    spec_id = id_match.group(1).strip().strip('"').strip("'")
    if not spec_id.startswith("recipes."):
        return {"skipped": "not recipe"}

    if has_falsifier(fm):
        return {"unchanged": True}

    domain = detect_domain(spec_id)
    desc = DOMAIN_FALSIFIER.get(domain)
    if not desc:
        return {"skipped": f"no domain match: {spec_id}"}

    addition = f'falsifier:\n  description: "{desc}"\n'
    new_fm = fm.rstrip("\n") + "\n" + addition

    if not dry_run:
        new_text = marker + "\n" + new_fm.rstrip("\n") + "\n---" + body
        path.write_text(new_text, encoding="utf-8")

    return {"id": spec_id, "domain": domain}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        ap.error("--dry-run 또는 --apply 명시")

    files = sorted(SPECS_ROOT.rglob("*.md"))
    total = 0
    sample = []
    for p in files:
        result = process_file(p, dry_run=args.dry_run)
        if result.get("unchanged") or result.get("skipped"):
            continue
        total += 1
        if len(sample) < 15:
            sample.append(f"  {result['id']:60s} ({result['domain']})")

    print(f"{'DRY-RUN' if args.dry_run else 'APPLIED'} — {total} recipes falsifier 보강")
    for s in sample:
        print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
