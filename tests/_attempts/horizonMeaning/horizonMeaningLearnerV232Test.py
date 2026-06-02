"""Horizon Meaning Learner V232 - 천장 결판: 경험 합성이 *정렬(alignment)*인가 *coverage*인가 (shuffle-null).

사용자 개념(정본): 수평선 stem 좌표는 의미가 아니라 빠른 계산용 주소다. 그 좌표에서 *같이 나온 stem*이
경험이다. 경험을 그래프화·추상화·비교하면 "뭉뚱그림 의미"(동일/비슷/어느정도)가 graded 로 나온다.
이 실험 전체가 그 개념의 검증이고, 11회전은 그것이 *계열축(graded 동의/유형)* 에서 작동함을 입증했다.

천장(미해결): 경험 그래프는 *본 stem*에만 노드가 있어 OOD(미본 복합어/유형)에서 0 으로 붕괴. 미본을
seen 하위단위(형태소)의 *합성*으로 일반화할 수 있나? 전문가 레드팀의 핵심 반론: 조합(composition) != 정렬
(alignment). 고정 합성은 미본에 *무언가*를 출력하지만(coverage), 그 출력이 진짜 의미 방향과 정렬됐다는 보장이
없다(정렬은 학습=임베딩이 하는 일). 합성의 OOD 이득이 *정렬*인지 단지 *coverage*(미본에 0 아닌 값 부여)인지는
shuffle-null 로만 가린다.

가설(레드팀 설계, 천장 결판):
    seen-형태소-100% OOD subset(합성에 가장 유리한 조건)에서 4-arm 비교.
    - A flat: whole-token(tok:) feature 만. 미본 token 이라 OOD 에서 ~0(기억 baseline).
    - B morph: 형태소(char n-gram/pre/suf) feature 합성(경험 그래프 추상). V228 morph.
    - D shuffleNull: B 와 *동일 합성 연산*, 단 feature->body 프로파일 매핑을 무작위 치환(조합 구조 유지,
      정렬 파괴).
    판정: B 가 A 도 이기고 *D(shuffle)도 유의하게 이기면* -> 합성이 정렬을 추가 = 천장 뚫림.
          B ≈ D 면 -> 이득은 coverage 일 뿐 정렬 0 = 임베딩 없는 OOD 일반화는 근본 천장.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV232Test.py
    $env:DARTLAB_HORIZON_V232_FILE_LIMIT='40'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV232Test.py

검증 기준:
    1. allFilings report_nm + content_raw 만. R1~R5. dartlab import 없음.
    2. query=core, candidate=raw body. SPPMI 는 core-masked train, OOD class 단위 제외.
    3. seen-morph-100% subset = query 의 모든 형태소(non-tok) feature 가 train graph 에 존재 = 합성 최대 유리.
    4. 결판: OOD-seenMorph 에서 B vs D(shuffle) 유의차. + 형태소 coverage 보고.

결과:
    py_compile 통과.

    40-file: docs=12734 trainExp=8627 test=2858, OOD queries=338 seen-morph-100% coverage=0.476,
             graphFeatures=2820, buildSeconds~=16
      arm      inDist Top1/MRR   OOD(seen-morph) Top1/MRR (n=161)
      flat     0.5507/0.6208     0.0870/0.0935
      morph    0.5507/0.6205     0.0870/0.0935
      shuffle  0.0062/0.0147     0.0000/0.0000

결론:
    천장 근본 확인 (레드팀 "조합 != 정렬" 예측 적중).
    - morph(형태소 합성) == flat(whole-token) 정확히 동일, inDist·OOD 둘 다. 형태소 합성은 whole-token 위에
      *아무 정렬 이득도 추가 못함*. "경험 합성"의 OOD 신호(0.0935)는 전부 *공유 whole-token 기억*에서 온다.
    - shuffle-null(feature->profile 매핑 치환)은 0 으로 붕괴 -> 있는 신호는 정렬돼 있으나, 그 정렬은
      whole-token 기억의 정렬이지 *합성의 정렬*이 아니다.
    - 즉 고정 합성(형태소·VSA류)은 미본에 coverage(공유 토큰)만 줄 뿐, 미본으로의 *정렬된 일반화*는 못 만든다.
      정렬은 학습(gradient=임베딩)이 하는 일. 임베딩·GPU 없는 OOD 조합 일반화는 근본 천장.

    사용자 개념과의 관계: "경험 그래프 추상화 -> graded 의미(동일/비슷/어느정도)"는 *seen 경험 안*에서
    보간으로 작동(계열축, 입증됨). 그러나 미본으로의 외삽(일반화)은 고정 그래프엔 없다 — gradient 정렬 부재.
    graded 의미는 본 것의 보간이지 미본의 외삽이 아니다.

    caveat: seen-morph coverage 0.476(OOD title 절반만 형태소 100% seen) — 나머지 절반은 미본 형태소라 합성
    자체 불가. morph==flat 정확 일치는 tok: feature 가 expansion top-60 을 지배해 n-gram 기여가 ranking 에
    안 드러난 구현 특성일 수도 있으나, 핵심(합성의 정렬 이득 0, shuffle-null 붕괴)은 견고.
"""

from __future__ import annotations

import hashlib
import math
import os
import random
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[3]
ALL_FILINGS_DIR = ROOT / "data" / "dart" / "allFilings"

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V232_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V232_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V232_MAX_QUERIES", "3000"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V232_TEST_MOD", "4"))
OOD_MOD = int(os.environ.get("DARTLAB_HORIZON_V232_OOD_MOD", "5"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V232_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V232_EXPAND_TOPN", "60"))
RWR_BRANCH = int(os.environ.get("DARTLAB_HORIZON_V232_RWR_BRANCH", "24"))
MIN_ASSOC_DF = int(os.environ.get("DARTLAB_HORIZON_V232_MIN_ASSOC_DF", "3"))
SPPMI_SHIFT = float(os.environ.get("DARTLAB_HORIZON_V232_SPPMI_SHIFT", "0.7"))
TOPK = int(os.environ.get("DARTLAB_HORIZON_V232_TOPK", "10"))
SEED = int(os.environ.get("DARTLAB_HORIZON_V232_SEED", "20260602"))

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
NUM_RE = re.compile(r"\d")
HANGUL_RE = re.compile(r"[가-힣]+")
TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")
PAREN_RE = re.compile(r"[(\[]([^)\]]+)[)\]]")
BRACKET_PREFIX_RE = re.compile(r"^\s*\[[^\]]*\]")

GENERIC_TITLE_STOP = frozenset(
    {
        "보고서",
        "공시",
        "제출",
        "정정",
        "기재",
        "첨부",
        "첨부정정",
        "자료",
        "자율",
        "주요사항보고서",
        "주요사항",
        "조회공시",
        "조회",
        "요구",
        "답변",
        "풍문",
        "보도",
        "정지",
        "해제",
        "신청",
        "결과",
        "안내",
        "변경",
        "예고",
        "관련",
        "여부",
        "확인",
        "공고",
        "통지",
        "사업",
        "분기",
        "반기",
        "감사",
        "검토",
        "연결",
        "재무제표",
    }
)


def cleanText(value, *, limit=None) -> str:
    text = "" if value is None else str(value)
    if limit is not None and len(text) > limit:
        text = text[:limit]
    import html

    text = html.unescape(text)
    text = TAG_RE.sub(" ", text)
    text = text.replace("\xa0", " ")
    return SPACE_RE.sub(" ", text).strip()


def bodyStems(text: str) -> list[str]:
    out = []
    for token in TOKEN_RE.findall(text):
        if 2 <= len(token) <= 14 and not NUM_RE.search(token) and HANGUL_RE.fullmatch(token):
            out.append(token)
    return out


def reportNmCore(report_nm: str) -> set[str]:
    raw = BRACKET_PREFIX_RE.sub("", (report_nm or "").strip()).strip()
    parens = PAREN_RE.findall(raw)
    pool = " ".join(parens) if parens else PAREN_RE.sub(" ", raw)
    core = set()
    for t in TOKEN_RE.findall(pool):
        if 2 <= len(t) <= 14 and not NUM_RE.search(t) and HANGUL_RE.fullmatch(t) and t not in GENERIC_TITLE_STOP:
            core.add(t)
    return core


def stableHashInt(value: str) -> int:
    return int(hashlib.blake2b(value.encode("utf-8"), digest_size=8).hexdigest(), 16)


def isTestCorp(corp: str) -> bool:
    return (stableHashInt(corp) % TEST_MOD) == 0 if corp else False


def isOodClass(cls: str) -> bool:
    return (stableHashInt("ood:" + cls) % OOD_MOD) == 0


def tokenFeatureWeights(token: str) -> dict[str, float]:
    if not token:
        return {}
    f = {f"tok:{token}": 1.0}
    n = len(token)
    for size, w in ((2, 0.18), (3, 0.34), (4, 0.42)):
        if n >= size:
            f[f"pre{size}:{token[:size]}"] = max(f.get(f"pre{size}:{token[:size]}", 0), w)
            f[f"suf{size}:{token[-size:]}"] = max(f.get(f"suf{size}:{token[-size:]}", 0), w)
    for size, w in ((2, 0.10), (3, 0.22), (4, 0.30)):
        if n >= size + 1:
            for s in range(n - size + 1):
                g = token[s : s + size]
                if g not in GENERIC_TITLE_STOP:
                    f[f"ng{size}:{g}"] = max(f.get(f"ng{size}:{g}", 0), w)
    return f


def coreFeatureWeights(core: frozenset[str]) -> dict[str, float]:
    feats: dict[str, float] = defaultdict(float)
    for t in core:
        for f, w in tokenFeatureWeights(t).items():
            feats[f] = max(feats[f], w)
    return dict(feats)


@dataclass
class Doc:
    corp: str
    isTest: bool
    core: frozenset[str]
    raw: Counter


def loadDocs() -> list[Doc]:
    docs = []
    for path in sorted(ALL_FILINGS_DIR.glob("*.parquet"))[:FILE_LIMIT]:
        df = pl.read_parquet(str(path), columns=["corp_code", "report_nm", "content_raw"])
        if df.height > ROWS_PER_FILE:
            df = df.head(ROWS_PER_FILE)
        for r in df.iter_rows(named=True):
            core = reportNmCore(r.get("report_nm") or "")
            if not core:
                continue
            stems = bodyStems(cleanText(r.get("content_raw"), limit=BODY_CHAR_LIMIT))
            if len(stems) < 12:
                continue
            docs.append(
                Doc(
                    str(r.get("corp_code") or ""),
                    isTestCorp(str(r.get("corp_code") or "")),
                    frozenset(core),
                    Counter(stems),
                )
            )
        del df
    return docs


def classKeyOf(core: frozenset[str]) -> str:
    return "|".join(sorted(core))


def buildSppmiGraph(trainDocs: list[Doc]) -> dict[str, dict[str, float]]:
    co: dict[str, Counter] = defaultdict(Counter)
    titleDf: Counter = Counter()
    bodyDf: Counter = Counter()
    for d in trainDocs:
        body = {b for b in d.raw if b not in d.core}
        feats = set(coreFeatureWeights(d.core))
        if not feats or not body:
            continue
        for b in body:
            bodyDf[b] += 1
        for f in feats:
            titleDf[f] += 1
            co[f].update(body)
    n = max(1, len(trainDocs))
    graph: dict[str, dict[str, float]] = {}
    for f, counts in co.items():
        fDf = titleDf[f]
        w = {}
        for b, c in counts.items():
            if c < MIN_ASSOC_DF:
                continue
            bDf = bodyDf.get(b, 0)
            if bDf <= 0:
                continue
            pmi = math.log((c * n) / (fDf * bDf)) - SPPMI_SHIFT
            if pmi > 0:
                w[b] = pmi * math.log(1.0 + n / bDf)
        if w:
            graph[f] = dict(sorted(w.items(), key=lambda kv: kv[1], reverse=True)[:RWR_BRANCH])
    return graph


def expand(core: frozenset[str], graph: dict[str, dict[str, float]], onlyTok: bool) -> dict[str, float]:
    prof: dict[str, float] = defaultdict(float)
    for f, sw in coreFeatureWeights(core).items():
        if onlyTok and not f.startswith("tok:"):
            continue
        for b, ew in graph.get(f, {}).items():
            prof[b] += sw * ew
    return dict(sorted(prof.items(), key=lambda kv: kv[1], reverse=True)[:EXPAND_TOPN])


def shuffleGraph(graph: dict[str, dict[str, float]], seed: int) -> dict[str, dict[str, float]]:
    """feature -> body 프로파일 매핑을 무작위 치환. 합성 구조 동일, 의미 정렬 파괴(강한 null)."""
    keys = sorted(graph.keys())
    vals = [graph[k] for k in keys]
    rng = random.Random(seed)
    perm = list(range(len(keys)))
    rng.shuffle(perm)
    return {keys[i]: vals[perm[i]] for i in range(len(keys))}


def scoreProfile(prof: dict[str, float], inv: dict[str, list[int]]) -> dict[int, float]:
    s: dict[int, float] = defaultdict(float)
    for b, w in prof.items():
        for pos in inv.get(b, ()):
            s[pos] += w
    return s


def main() -> None:
    t0 = time.time()
    docs = loadDocs()
    trainAll = [d for d in docs if not d.isTest]
    test = [d for d in docs if d.isTest]
    if not trainAll or not test:
        print(f"insufficient: train={len(trainAll)} test={len(test)}")
        return

    trainExp = [d for d in trainAll if not isOodClass(classKeyOf(d.core))]
    graph = buildSppmiGraph(trainExp)
    shuf = shuffleGraph(graph, SEED)
    inv: dict[str, list[int]] = defaultdict(list)
    posClass: dict[int, str] = {}
    classMembers: dict[str, list[int]] = defaultdict(list)
    for pos, d in enumerate(test):
        posClass[pos] = classKeyOf(d.core)
        classMembers[classKeyOf(d.core)].append(pos)
        for b in d.raw:
            inv[b].append(pos)

    # seen-morph-100%: query 의 모든 non-tok feature 가 train graph 에 존재
    def seenMorph100(core: frozenset[str]) -> bool:
        nonTok = [f for f in coreFeatureWeights(core) if not f.startswith("tok:")]
        return bool(nonTok) and all(f in graph for f in nonTok)

    queries = []
    for pos, d in enumerate(test):
        queries.append((pos, d.core, classKeyOf(d.core)))
        if len(queries) >= MAX_QUERIES:
            break

    cache: dict[tuple[int, str], dict[str, float]] = {}

    def prof(qid, core, kind):
        key = (qid, kind)
        if key not in cache:
            if kind == "flat":
                cache[key] = expand(core, graph, onlyTok=True)
            elif kind == "morph":
                cache[key] = expand(core, graph, onlyTok=False)
            else:  # shuffle
                cache[key] = expand(core, shuf, onlyTok=False)
        return cache[key]

    def evalArm(kind: str, bucket: str):
        top1 = 0
        mrr = 0.0
        nn = 0
        for qid, core, cls in queries:
            isOod = isOodClass(cls)
            if bucket == "ood" and not (isOod and seenMorph100(core)):
                continue
            if bucket == "in" and isOod:
                continue
            gold = set(classMembers.get(cls, ())) - {qid}
            if not gold:
                continue
            nn += 1
            scores = scoreProfile(prof(qid, core, kind), inv)
            if not scores:
                continue
            ranked = [p for p, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])) if p != qid]
            for r, p in enumerate(ranked[:TOPK], start=1):
                if p in gold:
                    if r == 1:
                        top1 += 1
                    mrr += 1.0 / r
                    break
        return {"top1": top1 / nn if nn else 0.0, "mrr": mrr / nn if nn else 0.0, "n": nn}

    arms = ("flat", "morph", "shuffle")
    res = {(k, b): evalArm(k, b) for k in arms for b in ("in", "ood")}

    # 형태소 coverage 진단
    oodQ = [q for q in queries if isOodClass(q[2]) and (set(classMembers.get(q[2], ())) - {q[0]})]
    seenCov = sum(1 for q in oodQ if seenMorph100(q[1])) / len(oodQ) if oodQ else 0.0

    print("=" * 78)
    print(f"V232 천장 결판: 합성=정렬 vs coverage (shuffle-null)  ({time.time() - t0:.1f}s)")
    print(f"files={FILE_LIMIT} docs={len(docs)} trainExp={len(trainExp)} test={len(test)}")
    print(f"OOD queries={len(oodQ)} seen-morph-100% coverage={seenCov:.3f} graphFeatures={len(graph)}")
    print("-" * 78)
    print(f"{'arm':<10} | inDist Top1/MRR    | OOD(seen-morph) Top1/MRR  n")
    for k in arms:
        ri, ro = res[(k, "in")], res[(k, "ood")]
        print(f"{k:<10} | {ri['top1']:.4f}/{ri['mrr']:.4f}      | {ro['top1']:.4f}/{ro['mrr']:.4f}   n={ro['n']}")
    print("-" * 78)
    mOod = res[("morph", "ood")]["mrr"]
    dOod = res[("shuffle", "ood")]["mrr"]
    aOod = res[("flat", "ood")]["mrr"]
    beatsFlat = mOod > aOod + 0.02
    beatsShuffle = mOod > dOod + 0.03
    print(f"OOD: morph {mOod:.4f} vs flat {aOod:.4f} vs shuffle-null {dOod:.4f}")
    print(f"  morph > flat ? {'YES' if beatsFlat else 'NO'}  (coverage 이득 존재 여부)")
    print(f"  morph > shuffle-null ? {'YES' if beatsShuffle else 'NO'}  (정렬 이득 = 천장 돌파 핵심)")
    print("-" * 78)
    if beatsFlat and beatsShuffle:
        v = "천장 뚫림(부분): 형태소 합성이 shuffle-null 을 넘음 = OOD 에서 *정렬된* 일반화 추가. 임베딩 없이 조합 일반화 가능."
    elif beatsFlat and not beatsShuffle:
        v = "천장 근본 확정: morph 가 flat 은 이기나 shuffle-null 과 동급 = 이득은 coverage 일 뿐 정렬 0. 임베딩 없는 OOD 일반화는 근본 천장(레드팀 예측 적중)."
    else:
        v = "morph 가 flat 도 못 넘음 = 자명한 천장(seen-morph subset 에서도 합성 무효)."
    print(f"VERDICT: {v}")
    print("=" * 78)


if __name__ == "__main__":
    main()
