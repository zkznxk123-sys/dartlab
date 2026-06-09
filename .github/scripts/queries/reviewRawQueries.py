"""수집된 raw 질문 review — 미라우팅·신규 군집을 추려 운영자가 curatedQuestions 승격 판단하게 한다.

수집 루프의 게이트: raw(Worker 적재) 를 현 intentModel 로 라우팅 → route score 0(미분류) 인 질문이
*신규 어휘/패턴* 후보. 빈도·군집으로 노이즈를 깎고, 의미있는 군집만 운영자에게 보인다(자동 승격 0 — round2 노이즈 교훈).

실행: uv run --with huggingface-hub python -X utf8 .github/scripts/queries/reviewRawQueries.py [--min-count N]
출력: 라우팅 분포 + 미분류 상위 군집(대표 질문·빈도). raw 없으면 "신규 질문 없음".
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
HANGUL, ASCII = re.compile(r"[가-힣]+"), re.compile(r"[A-Za-z]{2,20}")
REPO = "eddmpython/dartlab-data"


def bg(t):
    o = []
    for run in HANGUL.findall(t):
        o.extend(run[i : i + 2] for i in range(len(run) - 1)) if len(run) > 1 else o.append(run)
    o.extend(m.lower() for m in ASCII.findall(t))
    return o


def route_top(model, q):
    qc = Counter(bg(q))
    best, bs = None, 0.0
    for it, e in model.items():
        s = sum(c * e["route"].get(b, 0) for b, c in qc.items())
        if s > bs:
            bs, best = s, it
    return best, bs


def load_raw():
    """HF raw 샤드 전수 로드. 부재/빈 경우 [] (graceful)."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("huggingface_hub 없음 — `uv run --with huggingface-hub` 로 실행")
        return []
    try:
        local = snapshot_download(repo_id=REPO, repo_type="dataset", allow_patterns="dart/queries/raw/**")
    except Exception as e:
        print(f"raw 다운로드 실패(아직 수집 전일 수 있음): {e}")
        return []
    out = []
    for f in Path(local, "dart", "queries", "raw").rglob("*.json"):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-count", type=int, default=2, help="군집 최소 빈도(일회성 노이즈 컷)")
    args = ap.parse_args()

    model = json.load(open(BASE / "intentModel.json", encoding="utf-8"))["intents"]
    raw = load_raw()
    if not raw:
        print("신규 질문 없음 (raw 비어있음). Worker 배포·수집 후 다시 실행.")
        return

    routed, unrouted = 0, []
    for r in raw:
        q = (r.get("q") or "").strip()
        if not q:
            continue
        it, sc = route_top(model, q)
        if sc > 0:
            routed += 1
        else:
            unrouted.append(q)

    print(f"■ raw {len(raw)} · 라우팅됨 {routed} · 미분류 {len(unrouted)}")

    # 미분류 군집화 — 정규화 질문 빈도(일회성/노이즈 컷). distinctive bigram 도 집계해 신규 어휘 힌트.
    norm = Counter(q.replace(" ", "").lower() for q in unrouted)
    clusters = [(q, n) for q, n in norm.most_common() if n >= args.min_count]
    bgs = Counter(b for q in unrouted for b in set(bg(q)))
    known_route = set(b for e in model.values() for b in e["route"])
    new_bgs = [(b, n) for b, n in bgs.most_common(20) if b not in known_route and n >= args.min_count]

    print(f"\n■ 승격 후보 군집(빈도 ≥{args.min_count}): {len(clusters)}")
    for q, n in clusters[:30]:
        print(f"   ×{n}  {q}")
    print(
        f"\n■ 신규 어휘 힌트(어느 route 에도 없는 bigram): {', '.join(f'{b}×{n}' for b, n in new_bgs[:20]) or '없음'}"
    )
    print("\n→ 운영자: 의미있는 군집만 curatedQuestions.json 에 intent 라벨 달아 추가 → push → 파이프라인 자동 재학습.")


if __name__ == "__main__":
    main()
