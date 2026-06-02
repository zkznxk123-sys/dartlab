"""Horizon Meaning Learner V235 - 이론강화: 교집합 합성 + balAPinc 방향성 + log-Dice 가중.

V234 가 지론(경험=의미 그래프, graded 비교)을 정면 지지했으나 두 약점:
    (C) 미세대역(비슷/어느정도/무관) 격차 미미, (D) 복합 = naive union 반증(합집합이 복합어로 안 감).
V235 는 정통(임베딩 없는 count/그래프) 개념으로 그 둘을 친다:
    [B/#5,#6] 복합 합성연산자: union(반증된 기준) vs 교집합-기하평균(둘이 *함께* 허락한 맥락) vs head가중
        (한국어 복합어 head-final: 매출채권 head=채권). Mitchell&Lapata(count 벡터) — 덧셈<곱셈/교집합 가설.
        측정: cos(composed, *관찰된* prof(복합어)) vs 최선부분 vs 랜덤. 관찰 복합어 = 합성 gold(distant).
    [A/#3] balAPinc 방향성 포함측도: 대칭 cos 가 못 가르는 동일(대칭) vs 비슷/상하위(비대칭)를 분리하는가.
    [A/#1] log-Dice 가중 vs SPPMI: 어떤 공기 가중이 등급을 또렷하게 하는가.

    데이터·라벨·null·OOM 가드는 V234 동일. 임베딩/GPU 0.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV235Test.py
    DARTLAB_HORIZON_V235_FILE_LIMIT=40 uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV235Test.py

검증 기준:
    1. allFilings 본문 + accountMappings 만. R1~R5. dartlab import 없음. 파일별 load+del.
    2. 등급 정답 = referential(sj/code) ordinal scaffold(정의 아님). 단일토큰 korName 라벨.
    3. 평가 = 검색 MRR 아님. band AUC/ladder(가중×시그니처) + 복합 연산자 비교 + 셔플 null. 결정적.
    4. 복합 gold = 코퍼스 관찰 prof(복합어). composed 가 부분·랜덤보다 가까운가.

결과:
    py_compile 통과. 결정적.

    40-file: docs=13450 vocab=3147 profiledS=2759 labeledS=110, total~50s, 임베딩/GPU 0
    [A] 가중 x 시그니처 (band 평균 / AUC(동일>무관) / ladder)
      SPPMI    raw_cos 0.0932/0.0332/0.0235/0.0177  AUC 0.680  3/3
               2hop_set 0.1401/0.0584/0.0479/0.0431 AUC 0.728  3/3   <- 최고(V234 재확인)
               balApinc 0.0529/0.0154/0.0100/0.0075 AUC 0.675  3/3
      logDice  raw_cos AUC 0.658 / 2hop_set 0.673 / balApinc 0.660   <- 전반 SPPMI 열위
    [A/#3] 방향성 비대칭: 16f 동일0.098<비슷0.147 이었으나 40f 동일0.202>비슷0.109 부호역전(불안정).
    null(셔플) AUC=0.506 vs real 0.680 -> 경험 덕(붕괴) 재확인.
    [B] 복합 n=250: 최선부분 cos=0.212 ≫ 랜덤 0.018.
        union 0.170 (우위율0.07) / intersectGeo 0.048 (0.02, 최악) / head+shared 0.155 (0.07)
        -> 합성연산자 *전부* 최선부분 미달.

결론:
    이론강화 시도 — 정통 3 개념(#1 log-Dice, #3 balAPinc/방향성, #5 교집합합성) 모두 *이 회계도메인에선*
    baseline 미개선. 정직한 음성이 이론을 더 또렷이 한다(잣대 교정 반영 — 검색 아닌 등급·복합·null).

    (A) 미세대역: SPPMI 2hop_set(V234)가 여전히 최고(0.728). log-Dice·balApinc 무익 — 가중·비대칭 교체로
        미세대역 안 열림. 단서는 동일(동의)에 집중, 비슷/어느정도는 분포의 한계(단조지만 격차 미미).
    (A/#3) 방향성(asymmetry)은 16f→40f 부호역전 = 불안정. 동의 vs 상하위 분리축으로 못 씀(이 라벨·n=22 에서).
    (B) 복합 = 정통 합성연산자 전부 반증. 핵심 발견: 복합어 분포 ≈ *head 단일부분*(0.21), 부분 결합은 희석만.
        intersectGeo 붕괴(0.05) = 두 부분이 top-salient 맥락을 거의 안 나눔 → 복합어는 "맥락 교집합"이 아니라
        head 지배 신규개체. ⇒ **복합의 '새 의미'는 분포 그래프 대수로 합성되지 않는다 — 분포는 head 만 따라감.**
        모디파이어의 의미기여(결합축적)는 분포에 없고 *구조/referential* 필요(V230 과 정합).

    종합: 코어 지론(경험 비교=graded 단서, 즉시·임베딩無)은 V234·V235 양쪽서 robust(null 통과, AUC 0.73).
    그러나 *교과서식 분포 강화(가중·방향·합성)는 이 도메인서 무익* — 이론의 진짜 다음 칸은 분포 미세조정이 아니라
    **결합축의 구조적 grounding**: 복합·미세대역을 부분의 분포합이 아니라 accountMappings 계층(parent/child/
    sibling)·sj 관계로 합성·변별. 분포는 계열축 단서까지, 그 이상은 구조. (memory project_experience_meaning_graph
    의 crux 중 '뭉뜽거림'은 2hop_set 으로 정착, '복합'은 분포 경로 닫힘 → 구조 경로로 이관.)

    다음(V236): 계열(분포 2hop_set) + 결합(accountMappings 계층 구조)을 한 점수로 — 복합어를 부분 canonical 의
    계층관계로 합성하고 분포 단서와 RRF 결합. 2층 의미표상 end-to-end.
"""

from __future__ import annotations

import html
import json
import math
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[3]
ALL_FILINGS_DIR = ROOT / "data" / "dart" / "allFilings"
MAPPING_PATH = ROOT / "src" / "dartlab" / "reference" / "data" / "accountMappings.json"

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V235_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V235_ROWS_PER_FILE", "600"))
BODY_CHARS = int(os.environ.get("DARTLAB_HORIZON_V235_BODY_CHARS", "6000"))
VOCAB_SIZE = int(os.environ.get("DARTLAB_HORIZON_V235_VOCAB", "3000"))
CO_TOPM = int(os.environ.get("DARTLAB_HORIZON_V235_CO_TOPM", "40"))
MIN_CO = int(os.environ.get("DARTLAB_HORIZON_V235_MIN_CO", "3"))
PROF_TOPK = int(os.environ.get("DARTLAB_HORIZON_V235_PROF_TOPK", "40"))
SPPMI_SHIFT = float(os.environ.get("DARTLAB_HORIZON_V235_SPPMI_SHIFT", "0.7"))
MIN_PROF = int(os.environ.get("DARTLAB_HORIZON_V235_MIN_PROF", "6"))
MAX_LABELED = int(os.environ.get("DARTLAB_HORIZON_V235_MAX_LABELED", "500"))
CODE_PREFIX = int(os.environ.get("DARTLAB_HORIZON_V235_CODE_PREFIX", "3"))
TWOHOP_CAP = int(os.environ.get("DARTLAB_HORIZON_V235_TWOHOP_CAP", "120"))
HEAD_W = float(os.environ.get("DARTLAB_HORIZON_V235_HEAD_W", "0.65"))

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
NUM_RE = re.compile(r"\d")
HANGUL_RE = re.compile(r"[가-힣]+")
TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")


def cleanText(value, *, limit=None) -> str:
    text = "" if value is None else str(value)
    if limit is not None and len(text) > limit:
        text = text[:limit]
    text = html.unescape(text)
    text = TAG_RE.sub(" ", text)
    text = text.replace("\xa0", " ")
    return SPACE_RE.sub(" ", text).strip()


def bodyStems(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text) if 2 <= len(t) <= 14 and not NUM_RE.search(t) and HANGUL_RE.fullmatch(t)]


def loadLabels() -> dict[str, tuple]:
    d = json.load(open(MAPPING_PATH, encoding="utf-8"))
    mappings: dict[str, str] = d["mappings"]
    standard: dict[str, dict] = d["standardAccounts"]
    labels: dict[str, tuple] = {}
    for kor, canon in mappings.items():
        k = kor.strip()
        if not (2 <= len(k) <= 14) or NUM_RE.search(k) or not HANGUL_RE.fullmatch(k):
            continue
        m = standard.get(canon)
        if not m:
            continue
        code = str(m.get("code") or "")
        if not code:
            continue
        labels.setdefault(k, (canon, m.get("sj", "?"), code[:CODE_PREFIX], code))
    return labels


def band(la: tuple, lb: tuple) -> str:
    canonA, sjA, famA, _ = la
    canonB, sjB, famB, _ = lb
    if canonA == canonB:
        return "동일"
    if sjA == sjB and famA == famB:
        return "비슷"
    if sjA == sjB:
        return "어느정도"
    return "무관"


def loadCooccurrence(labels: dict[str, tuple]):
    paths = sorted(ALL_FILINGS_DIR.glob("*.parquet"))[:FILE_LIMIT]
    df1: Counter = Counter()
    nDocs = 0
    for path in paths:
        d = pl.read_parquet(str(path), columns=["content_raw"])
        if d.height > ROWS_PER_FILE:
            d = d.head(ROWS_PER_FILE)
        for r in d.iter_rows(named=True):
            stems = bodyStems(cleanText(r.get("content_raw"), limit=BODY_CHARS))
            if len(stems) < 12:
                continue
            nDocs += 1
            for s in set(stems):
                df1[s] += 1
        del d
    vocab = {s for s, _ in df1.most_common(VOCAB_SIZE)}
    vocab |= {s for s in labels if s in df1}
    co: dict[str, Counter] = defaultdict(Counter)
    sdf: Counter = Counter()
    for path in paths:
        d = pl.read_parquet(str(path), columns=["content_raw"])
        if d.height > ROWS_PER_FILE:
            d = d.head(ROWS_PER_FILE)
        for r in d.iter_rows(named=True):
            stems = bodyStems(cleanText(r.get("content_raw"), limit=BODY_CHARS))
            if len(stems) < 12:
                continue
            tf = Counter(s for s in stems if s in vocab)
            top = [s for s, _ in tf.most_common(CO_TOPM)]
            for s in top:
                sdf[s] += 1
            for i in range(len(top)):
                ca = co[top[i]]
                for j in range(len(top)):
                    if i != j:
                        ca[top[j]] += 1
        del d
    return co, sdf, nDocs, vocab


def buildProfiles(co, sdf, nDocs, mode: str):
    """mode='sppmi' | 'logdice'. stem -> top-k {neighbor: weight}."""
    prof: dict[str, dict[str, float]] = {}
    logN = math.log(max(1, nDocs))
    log2 = math.log(2.0)
    for a, counts in co.items():
        dfa = sdf.get(a, 0)
        if dfa <= 0:
            continue
        w = {}
        for b, c in counts.items():
            if c < MIN_CO:
                continue
            dfb = sdf.get(b, 0)
            if dfb <= 0:
                continue
            if mode == "sppmi":
                val = (math.log(c) + logN) - (math.log(dfa) + math.log(dfb)) - SPPMI_SHIFT
            else:  # logdice: 14 + log2(2*c/(dfa+dfb))
                val = 14.0 + math.log(2.0 * c / (dfa + dfb)) / log2
            if val > 0:
                w[b] = val
        if w:
            prof[a] = dict(sorted(w.items(), key=lambda kv: kv[1], reverse=True)[:PROF_TOPK])
    return prof


def buildTwoSig(prof):
    setSig = {s: set(p) for s, p in prof.items()}
    twoSig = {}
    for s, p in prof.items():
        two = set(setSig[s])
        for n, _ in sorted(p.items(), key=lambda kv: (-kv[1], kv[0])):
            two |= setSig.get(n, set())
            if len(two) > TWOHOP_CAP:
                break
        twoSig[s] = two
    return setSig, twoSig


def cosine(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.0
    small, big = (a, b) if len(a) <= len(b) else (b, a)
    dot = sum(v * big.get(k, 0.0) for k, v in small.items())
    if dot <= 0:
        return 0.0
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na > 0 and nb > 0 else 0.0


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / len(a | b) if inter else 0.0


def apinc(u: dict, v: dict) -> float:
    """비대칭 평균정밀 포함도 — u 의 특징이 v 에 얼마나 (상위로) 포함되나."""
    if not u or not v:
        return 0.0
    vRank = {f: r for r, (f, _) in enumerate(sorted(v.items(), key=lambda kv: (-kv[1], kv[0])), start=1)}
    nv = len(v)
    incl = 0
    total = 0.0
    for r, (f, _) in enumerate(sorted(u.items(), key=lambda kv: (-kv[1], kv[0])), start=1):
        if f in vRank:
            incl += 1
            total += (incl / r) * (1.0 - vRank[f] / (nv + 1))
    return total / len(u)


def linMeasure(u: dict, v: dict) -> float:
    shared = set(u) & set(v)
    if not shared:
        return 0.0
    den = sum(u.values()) + sum(v.values())
    return (sum(u[f] for f in shared) + sum(v[f] for f in shared)) / den if den > 0 else 0.0


def balApincSym(u: dict, v: dict) -> float:
    lin = linMeasure(u, v)
    if lin <= 0:
        return 0.0
    ba = math.sqrt(max(0.0, apinc(u, v)) * lin)
    bb = math.sqrt(max(0.0, apinc(v, u)) * lin)
    return math.sqrt(ba * bb)


def asymmetry(u: dict, v: dict) -> float:
    a, b = apinc(u, v), apinc(v, u)
    return abs(a - b) / (a + b) if (a + b) > 0 else 0.0


def auc(pos: list[float], neg: list[float]) -> float:
    if not pos or not neg:
        return 0.5
    allv = sorted([(v, 0) for v in neg] + [(v, 1) for v in pos])
    i = 0
    n = len(allv)
    rankSumPos = 0.0
    while i < n:
        j = i
        while j < n and allv[j][0] == allv[i][0]:
            j += 1
        avg = (i + 1 + j) / 2.0
        for k in range(i, j):
            if allv[k][1] == 1:
                rankSumPos += avg
        i = j
    nPos, nNeg = len(pos), len(neg)
    return (rankSumPos - nPos * (nPos + 1) / 2.0) / (nPos * nNeg)


def bandTable(lab, labels, prof, twoSig):
    bandsOrder = ["동일", "비슷", "어느정도", "무관"]
    sims = {"raw_cos": defaultdict(list), "2hop_set": defaultdict(list), "balApinc": defaultdict(list)}
    for i in range(len(lab)):
        a = lab[i]
        for j in range(i + 1, len(lab)):
            b = lab[j]
            bd = band(labels[a], labels[b])
            sims["raw_cos"][bd].append(cosine(prof[a], prof[b]))
            sims["2hop_set"][bd].append(jaccard(twoSig[a], twoSig[b]))
            sims["balApinc"][bd].append(balApincSym(prof[a], prof[b]))
    out = {}
    for sg, bs in sims.items():
        means = {b: (sum(bs[b]) / len(bs[b]) if bs[b] else 0.0) for b in bandsOrder}
        seq = [means[b] for b in bandsOrder]
        mono = sum(1 for k in range(len(seq) - 1) if seq[k] >= seq[k + 1] - 1e-9)
        out[sg] = (means, auc(bs["동일"], bs["무관"]), mono)
    return out, bandsOrder


def main() -> None:
    t0 = time.time()
    labels = loadLabels()
    co, sdf, nDocs, vocab = loadCooccurrence(labels)
    profS = buildProfiles(co, sdf, nDocs, "sppmi")
    profD = buildProfiles(co, sdf, nDocs, "logdice")
    del co
    _, twoS = buildTwoSig(profS)
    _, twoD = buildTwoSig(profD)

    labS = sorted([s for s in labels if s in profS and len(profS[s]) >= MIN_PROF])[:MAX_LABELED]
    labD = sorted([s for s in labels if s in profD and len(profD[s]) >= MIN_PROF])[:MAX_LABELED]

    print("=" * 84)
    print(f"V235 이론강화: 교집합 합성 + balAPinc 방향성 + log-Dice 가중  (total {time.time() - t0:.1f}s)")
    print(f"files={FILE_LIMIT} docs={nDocs} vocab={len(vocab)} profiledS={len(profS)} labeledS={len(labS)}")
    print("-" * 84)
    print("[A] 미세대역 — 가중 x 시그니처 (band 평균 sim / AUC(동일>무관) / ladder)")
    for tag, prof, two, lab in [("SPPMI", profS, twoS, labS), ("logDice", profD, twoD, labD)]:
        tbl, order = bandTable(lab, labels, prof, two)
        print(f"  -- {tag} (labeled={len(lab)}) --")
        print("     " + f"{'sig':<10}" + "  ".join(f"{b:>8}" for b in order) + "    AUC    ladder")
        for sg, (means, a, mono) in tbl.items():
            print(f"     {sg:<10}" + "  ".join(f"{means[b]:8.4f}" for b in order) + f"   {a:.3f}   {mono}/3")

    # 방향성(asymmetry)이 대역과 상관? 동일=대칭(낮음) vs 비슷/상하위=비대칭(높음) 기대
    print("-" * 84)
    asymByBand = defaultdict(list)
    for i in range(len(labS)):
        for j in range(i + 1, len(labS)):
            bd = band(labels[labS[i]], labels[labS[j]])
            if bd in ("동일", "비슷"):
                asymByBand[bd].append(asymmetry(profS[labS[i]], profS[labS[j]]))
    for b in ("동일", "비슷"):
        vs = asymByBand[b]
        print(f"[A/#3] 방향성 비대칭 평균 {b}={sum(vs) / len(vs):.3f} (n={len(vs)})" if vs else f"  {b} n=0")

    # null (SPPMI raw)
    print("-" * 84)
    nL = len(labS)
    stride = nL // 2 + 1
    while math.gcd(stride, nL) != 1:
        stride += 1
    permProf = {labS[k]: profS[labS[(k * stride + 1) % nL]] for k in range(nL)}
    nPos, nNeg, rPos, rNeg = [], [], [], []
    for i in range(nL):
        for j in range(i + 1, nL):
            bd = band(labels[labS[i]], labels[labS[j]])
            if bd == "동일":
                nPos.append(cosine(permProf[labS[i]], permProf[labS[j]]))
                rPos.append(cosine(profS[labS[i]], profS[labS[j]]))
            elif bd == "무관":
                nNeg.append(cosine(permProf[labS[i]], permProf[labS[j]]))
                rNeg.append(cosine(profS[labS[i]], profS[labS[j]]))
    print(
        f"null(셔플) AUC={auc(nPos, nNeg):.3f} vs real AUC={auc(rPos, rNeg):.3f} -> "
        f"{'경험 덕(null 붕괴)' if auc(rPos, rNeg) - auc(nPos, nNeg) > 0.05 else '주의'}"
    )

    # [B] 복합 연산자: union vs 교집합-기하 vs head가중. gold=관찰 prof(복합어)
    print("-" * 84)
    profStems = set(profS)
    comps = []
    for c in sorted(profStems):
        if len(c) < 4 or len(profS[c]) < MIN_PROF:
            continue
        for cut in range(2, len(c) - 1):
            s1, s2 = c[:cut], c[cut:]  # s1=수식, s2=head(한국어 head-final)
            if s1 in profStems and s2 in profStems and len(profS[s1]) >= MIN_PROF and len(profS[s2]) >= MIN_PROF:
                comps.append((c, s1, s2))
                break
        if len(comps) >= 250:
            break

    def opUnion(p1, p2):
        m = defaultdict(float)
        for k, v in p1.items():
            m[k] += v
        for k, v in p2.items():
            m[k] += v
        return dict(m)

    def opIntersectGeo(p1, p2):
        return {k: math.sqrt(p1[k] * p2[k]) for k in (set(p1) & set(p2))}

    def opHead(p1, p2):  # p2=head 가중 + 공유 부스트
        m = defaultdict(float)
        for k, v in p1.items():
            m[k] += (1 - HEAD_W) * v
        for k, v in p2.items():
            m[k] += HEAD_W * v
        for k in set(p1) & set(p2):
            m[k] += math.sqrt(p1[k] * p2[k])
        return dict(m)

    ops = {"union": opUnion, "intersectGeo": opIntersectGeo, "head+shared": opHead}
    if comps:
        rand = sorted(profStems)
        agg = {nm: [0.0, 0] for nm in ops}
        partAcc, randAcc = 0.0, 0.0
        for idx, (c, s1, s2) in enumerate(comps):
            target = profS[c]
            simPart = max(cosine(profS[s1], target), cosine(profS[s2], target))
            simRand = cosine(profS[rand[(idx * 7 + 3) % len(rand)]], target)
            partAcc += simPart
            randAcc += simRand
            for nm, fn in ops.items():
                sc = cosine(fn(profS[s1], profS[s2]), target)
                agg[nm][0] += sc
                if sc >= simPart and sc > simRand:
                    agg[nm][1] += 1
        nC = len(comps)
        print(f"[B] 복합 합성 n={nC}: 최선부분 cos={partAcc / nC:.3f}  랜덤 {randAcc / nC:.3f}")
        for nm in ops:
            print(f"    {nm:<14} composed cos={agg[nm][0] / nC:.3f}  우위율(>=부분 & >랜덤)={agg[nm][1] / nC:.2f}")
    else:
        print("[B] 복합: 샘플 0")
    print("=" * 84)


if __name__ == "__main__":
    main()
