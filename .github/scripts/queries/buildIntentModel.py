"""공시 Q&A 라우팅 — 단일 파이프라인 (build + verify + 회귀게이트). 진입점 하나, 신경 끌 수 있게.

흩어진 스크립트(buildIntentModelV2·buildVerify·selfProbe·canonProbe·groundTruth·mergeConfirmed) 를 여기로 통합.
앞으로 시드 추가 = curatedQuestions.json 편집 후 아래 한 줄. 그게 전부.

  uv run python -X utf8 .github/scripts/queries/buildIntentModel.py            # build + verify + gate (기본)
  uv run python -X utf8 .github/scripts/queries/buildIntentModel.py build      # 모델만 재빌드 + 번들 복사
  uv run python -X utf8 .github/scripts/queries/buildIntentModel.py verify 005930 035720 ...   # 검증만
  uv run python -X utf8 .github/scripts/queries/buildIntentModel.py query 051910 "배당 주나?" ...  # 정성 점검(실제 도달 섹션)

입력(SSOT): curatedQuestions.json(라우팅 학습원) · intentSpec.json(섹션 target + canon) — 본 스크립트 옆.
출력: intentModel.json + landing/src/lib/viewer/intentModel.json(프론트 fallback 번들). HF dart/queries/intentModel.json 가 라이브 주경로.
검증: heldoutB.json(병합 안 한 held-out) 로 일반화 측정 + 회귀게이트(baseline 하락 시 FAIL).
메커니즘: query→intent(IDF route, glue 제거)→target 섹션 scope + canon 어휘보강→RRF(plain 보존). 매퍼0·모델0·dense0.
"""

from __future__ import annotations

import gc
import html
import json
import math
import os
import re
import shutil
import sys
import types
from collections import Counter, defaultdict

sys.modules.setdefault("dartlab.scan", types.ModuleType("dartlab.scan"))
from dartlab.providers.dart.panel.read import readWide  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))  # SSOT 입력(intentSpec·curatedQuestions·heldoutB) 이 스크립트 옆
BUNDLE_PATH = "ui/packages/surfaces/src/viewer/lib/intentModel.json"  # 프론트 fallback 번들(repo 루트 기준, 단계-6 viewer surface 승격). HF 가 주경로, 이건 fallback
RECENT, CELL_CAP, K1, B, RRF_K, TOPK, GLUE_FRAC = 6, 500, 1.5, 0.75, 60, 120, 0.34
TAG, WS, PRE = re.compile(r"<[^>]+>"), re.compile(r"\s+"), re.compile(r"^\d{4}Q\d$")
HANGUL, ASCII = re.compile(r"[가-힣]+"), re.compile(r"[A-Za-z]{2,20}")
# 회귀 baseline — 신규 시드가 이 아래로 떨어뜨리면 FAIL(개선-or-동률만 통과). 측정 갱신 시 함께 올린다.
BASELINE = {"loo_route": 0.70, "heldout_route": 0.78, "section_hit": 0.82}
MARGIN = 0.03


def bg(t):
    o = []
    for run in HANGUL.findall(t):
        o.extend(run[i : i + 2] for i in range(len(run) - 1)) if len(run) > 1 else o.append(run)
    o.extend(m.lower() for m in ASCII.findall(t))
    return o


def strip(r):
    return WS.sub(" ", TAG.sub(" ", html.unescape(r or ""))).strip()


# ── BUILD ──
def build():
    spec = json.load(open(f"{BASE}/intentSpec.json", encoding="utf-8"))["intents"]
    cq = json.load(open(f"{BASE}/curatedQuestions.json", encoding="utf-8"))["questions"]
    intents = list(spec)
    bagf = {it: Counter() for it in intents}
    for it in intents:
        for q in cq[it]:
            for b in bg(q):
                bagf[it][b] += 1
    NI = len(intents)
    dfi = Counter()
    for it in intents:
        for b in bagf[it]:
            dfi[b] += 1
    glue = {b for b, d in dfi.items() if d >= NI * GLUE_FRAC}  # 다수 intent 공유 = 비변별(자동 제거)
    idf = {b: math.log((NI + 1) / (d + 0.5)) for b, d in dfi.items()}
    out = {"v": 2, "intents": {}}
    for it in intents:
        dl = math.sqrt(sum(bagf[it].values())) or 1.0
        w = {b: round(idf[b] * c / dl, 5) for b, c in bagf[it].items() if b not in glue}
        route = dict(sorted(w.items(), key=lambda kv: -kv[1])[:TOPK])
        out["intents"][it] = {
            "sections": spec[it]["sections"],
            "canon": spec[it]["canon"],
            "route": route,
            "n": len(cq[it]),
        }
    json.dump(out, open(f"{BASE}/intentModel.json", "w", encoding="utf-8"), ensure_ascii=False)
    shutil.copy(f"{BASE}/intentModel.json", BUNDLE_PATH)  # 프론트 fallback 번들 갱신
    nq = sum(len(v) for v in cq.values())
    print(
        f"[build] 시드 {nq} · intent {NI} · glue 제거 {len(glue)} · {os.path.getsize(f'{BASE}/intentModel.json')}B → intentModel.json + 번들"
    )
    return out


# ── route (brower queryCanon 와 동일 식) ──
def make_predict(model):
    def predict(q, k=1):
        qc = Counter(bg(q))
        sc = {it: sum(c * e["route"].get(b, 0) for b, c in qc.items()) for it, e in model.items()}
        sc = {it: s for it, s in sc.items() if s > 0}
        return [it for it, _ in sorted(sc.items(), key=lambda kv: -kv[1])[:k]]

    return predict


# ── corpus + search (arm E: scope + canon, RRF) ──
def corpus_of(code):
    wide = readWide(code, periods=None, tag=False)
    pcols = sorted((c for c in wide.columns if PRE.match(c)), reverse=True)[:RECENT]
    seen, cor = set(), []
    for r in wide.iter_rows(named=True):
        sec = r.get("sectionLeaf") or ""
        for p in pcols:
            t = strip(r.get(p))
            if not t:
                continue
            k = (sec, t[:80])
            if k in seen:
                continue
            seen.add(k)
            cor.append({"sec": sec, "text": (sec + " " + t)[:CELL_CAP]})
    del wide
    gc.collect()
    return cor


def bm25(toks, df, avgdl, n, terms, restrict=None):
    sc = defaultdict(float)
    pool = restrict if restrict is not None else range(n)
    for t in set(terms):
        d = df.get(t, 0)
        if d <= 0:
            continue
        idf = math.log((n - d + 0.5) / (d + 0.5) + 1.0)
        for i in pool:
            tf = toks[i].get(t, 0)
            if tf:
                sc[i] += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * sum(toks[i].values()) / avgdl))
    return [i for i in sorted(sc, key=lambda i: -sc[i])]


def rrf(*orders):
    rms = [{p: r for r, p in enumerate(o)} for o in orders]
    pool = set()
    for o in orders:
        pool |= set(o[:50])
    return sorted(pool, key=lambda p: -sum(1 / (RRF_K + rm[p]) for rm in rms if p in rm))


# ── VERIFY + GATE ──
def verify(codes):
    model = json.load(open(f"{BASE}/intentModel.json", encoding="utf-8"))["intents"]
    cq = json.load(open(f"{BASE}/curatedQuestions.json", encoding="utf-8"))["questions"]
    predict = make_predict(model)

    # (1) LOO 라우팅 (curated 내부 일관성) — 본 질문 기여 제거하고 예측
    bagf = {it: Counter() for it in model}
    for it in model:
        for q in cq[it]:
            for b in bg(q):
                bagf[it][b] += 1
    NI = len(model)
    dfi = Counter()
    for it in model:
        for b in bagf[it]:
            dfi[b] += 1
    glue = {b for b, d in dfi.items() if d >= NI * GLUE_FRAC}
    idf = {b: math.log((NI + 1) / (d + 0.5)) for b, d in dfi.items()}
    dl = {it: math.sqrt(sum(bagf[it].values())) or 1.0 for it in model}
    loo_c = loo_n = 0
    for it in model:
        for q in cq[it]:
            qc = Counter(b for b in bg(q) if b not in glue)
            sc = {}
            for jt in model:
                s = 0.0
                for b, c in qc.items():
                    wj = bagf[jt][b] - (c if jt == it else 0)
                    if wj > 0:
                        s += c * idf.get(b, 0) * wj
                sc[jt] = s / dl[jt]
            pred = max(sc, key=lambda k: sc[k]) if sc else None
            loo_n += 1
            loo_c += pred == it
    loo = loo_c / loo_n

    # (2) held-out 라우팅 (병합 안 한 새 질문 = 일반화)
    held = [tuple(x) for x in json.load(open(f"{BASE}/heldoutB.json", encoding="utf-8"))["items"]]
    hc = sum(1 for q, exp in held if (predict(q) or [None])[0] == exp)
    held_route = hc / len(held)

    # (3) held-out top-6 섹션도달 (arm E) — 회사별
    sect_rates = []
    for code in codes:
        cor = corpus_of(code)
        n = len(cor)
        toks = [Counter(bg(c["text"])) for c in cor]
        df = Counter()
        for t in toks:
            for x in t:
                df[x] += 1
        avgdl = sum(sum(t.values()) for t in toks) / max(1, n)
        present = set(c["sec"] for c in cor)
        hit = tot = 0
        for q, exp in held:
            tgt = model[exp]["sections"]
            if not any(any(t in s for s in present) for t in tgt):
                continue
            tot += 1
            qbg = bg(q)
            plain = bm25(toks, df, avgdl, n, qbg)
            pis = predict(q)
            pit = pis[0] if pis else None
            psec = model[pit]["sections"] if pit else []
            r1 = [i for i in range(n) if any(t in cor[i]["sec"] for t in psec)]
            qc = qbg + (bg(" ".join(model[pit]["canon"])) if pit else [])
            scoped = bm25(toks, df, avgdl, n, qc, restrict=r1) if r1 else []
            order = rrf(plain, scoped) if scoped else plain
            hit += any(any(t in cor[i]["sec"] for t in tgt) for i in order[:6])
        sect_rates.append((code, hit / tot if tot else 0))
        print(f"[verify] {code} held-out top-6 섹션도달: {hit}/{tot} = {hit / max(1, tot):.1%}")
        del cor, toks
        gc.collect()
    sect = sum(r for _, r in sect_rates) / len(sect_rates) if sect_rates else 0

    print(f"\n[verify] LOO 라우팅 {loo:.1%} · held-out 라우팅 {held_route:.1%} · held-out 섹션도달(평균) {sect:.1%}")
    # 회귀게이트
    fails = []
    if loo < BASELINE["loo_route"] - MARGIN:
        fails.append(f"LOO {loo:.1%} < {BASELINE['loo_route']:.0%}-{MARGIN:.0%}")
    if held_route < BASELINE["heldout_route"] - MARGIN:
        fails.append(f"held-out route {held_route:.1%} < {BASELINE['heldout_route']:.0%}-{MARGIN:.0%}")
    if sect < BASELINE["section_hit"] - MARGIN:
        fails.append(f"section {sect:.1%} < {BASELINE['section_hit']:.0%}-{MARGIN:.0%}")
    if fails:
        print("❌ GATE FAIL — 회귀:", "; ".join(fails))
        return False
    print("✅ GATE PASS — 회귀 없음 (개선-or-동률)")
    return True


# ── QUERY (정성 점검 — 한 회사에 실제 질문 던져 예측 intent + top-6 도달 섹션 눈으로) ──
def query(code, questions):
    model = json.load(open(f"{BASE}/intentModel.json", encoding="utf-8"))["intents"]
    predict = make_predict(model)
    cor = corpus_of(code)
    n = len(cor)
    toks = [Counter(bg(c["text"])) for c in cor]
    df = Counter()
    for t in toks:
        for x in t:
            df[x] += 1
    avgdl = sum(sum(t.values()) for t in toks) / max(1, n)
    print(f"■ {code} corpus {n}\n")
    for q in questions:
        qbg = bg(q)
        plain = bm25(toks, df, avgdl, n, qbg)
        pis = predict(q)
        pit = pis[0] if pis else None
        psec = model[pit]["sections"] if pit else []
        r1 = [i for i in range(n) if any(t in cor[i]["sec"] for t in psec)]
        qc = qbg + (bg(" ".join(model[pit]["canon"])) if pit else [])
        scoped = bm25(toks, df, avgdl, n, qc, restrict=r1) if r1 else []
        order = rrf(plain, scoped) if scoped else plain
        secs = []
        for i in order[:6]:
            s = cor[i]["sec"][:26]
            if s and s not in secs:
                secs.append(s)
        print(f"Q: {q}\n   intent→{pit} | top섹션: {' / '.join(secs[:4])}\n")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("build", "verify", "all", "query") else "all"
    if cmd == "query":
        code = next((a for a in sys.argv[2:] if a.isdigit()), "005930")
        qs = [a for a in sys.argv[2:] if not a.isdigit()]
        query(code, qs or ["돈 잘 벌어?", "감사 적정 받았어?", "최대주주 누구야?"])
        return
    codes = [a for a in sys.argv[2:] if a.isdigit()] or ["005930", "035720"]
    if cmd in ("build", "all"):
        build()
    if cmd in ("verify", "all"):
        ok = verify(codes)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
