"""Horizon Meaning Learner V234 - 지론 정면 검증: 경험=의미 그래프, "뭉뜽거림" 비교가 graded 단서를 주는가.

프레이밍(운영자 지론, memory project_experience_meaning_graph):
    경험 자체가 의미다. 한 stem 의 "같이 나온 stem 들"이 경험이고 그게 의미 그래프(재귀). 정의하지 않고 *비교*만
    한다 — 동일/비슷/어느정도/무관 의 graded 단서. 벡터(확정값·수만계산) 아님 — 그래프라 즉시 비교, 복합어는
    그래프 병합으로 새 의미. 비교 가능케 하려면 그래프를 "뭉뜽거려"야 한다(추상/시그니처) — 이게 열쇠이자 미해결.

    V233 까지는 *문서검색 MRR* 을 쟀다(대리지표). V234 는 지론 본체를 정면으로 잰다:
    (A) 등급: stem↔stem 경험그래프 비교가 동일>비슷>어느정도>무관 *순서*를 단서로 주는가 (검색정확도 아님).
    (B) 뭉뜽거림: raw(weighted) / set / 2hop-set / class-anchor 중 어느 추상이 collapse 없이 등급을 보존하는가.
    (C) 복합: prof(매출)⊕prof(채권) 병합이 실제 prof(매출채권) 으로 이동하는가 (vs 부분·랜덤).
    (D) null: 경험(이웃)을 stem 간 셔플하면 등급이 무너지는가 (= 등급이 경험 덕인가).

    데이터: allFilings content_raw 본문 stem 공기(共起, 문서단위). 등급 정답눈금 = accountMappings 의
    referential(canonical/sj/code) — *정의*가 아니라 순서 검증용 ordinal scaffold(V230 확립). 임베딩/GPU 0.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV234Test.py
    $env:DARTLAB_HORIZON_V234_FILE_LIMIT='40'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV234Test.py

검증 기준:
    1. allFilings 본문 + accountMappings 만. R1~R5. dartlab import 없음. 파일별 load+del(OOM 가드).
    2. 등급 정답은 referential(sj/code) — char 유사 아님. 단일토큰 korName 만 라벨.
    3. 평가 = 검색 MRR 아님. band 별 평균 sim + AUC(동일>무관 확률) + 복합 재현 + 셔플 null.
    4. 즉시비교 비용(쿼리당 µs) 측정 — 벡터 대비 "계산 폭발 없음" 확인.

결과:
    py_compile 통과. 결정적(2hop cap 을 가중치순 고정; null 은 곱셈순열로 인접보존 버그 제거).

    40-file: docs=13450 vocab=3147 profiled=2759 labeledStems=110 pairs=5995, total~30s, 비교 44.5 µs/pair (GPU 0)
      signature   동일      비슷    어느정도    무관     AUC(동일>무관)  ladder
      raw        0.0932  0.0332  0.0235  0.0177     0.680      3/3
      set        0.0623  0.0243  0.0186  0.0157     0.646      3/3
      2hop       0.1401  0.0584  0.0479  0.0431     0.728      3/3
      class      0.1541  0.0526  0.0451  0.0351     0.705      3/3
    null(경험 셔플) raw AUC=0.506 vs real raw AUC=0.680 -> 등급은 경험 덕(null 붕괴)
    복합 n=200: composed→복합어 cos=0.175 / 최선부분 0.214 / 랜덤 0.019 / composed 우위율=0.08
    (16-file 도 동형: 2hop AUC 0.769, null 0.539 vs 0.664, 복합 우위율 0.07.)

결론:
    지론 정면검증 — 3 지지 + 1 반증. (검색 MRR 아닌 등급·복합·null 로 측정 = 잣대 교정 반영.)

    (A) 경험=의미 graded 단서 = 성립. 4 뭉뜽거림 모두 ladder 3/3(동일>비슷>어느정도>무관 단조). 셔플 null
        붕괴(0.680->0.506)로 등급이 *경험 덕*임 확정(artifact 아님). 즉시비교 44µs/pair·임베딩/GPU 0 =
        지론의 "벡터(확정값·수만계산) 아닌 즉시비교" 데이터로 확인.
    (B) 뭉뜽거림이 열쇠 = 확인. set 0.646 < raw 0.680 < class 0.705 < 2hop 0.728. *무가중 2홉 집합겹침*
        ("경험의 경험"을 집합으로 — 사용자가 말한 재귀)이 최고. V233 의 가중 RWR(over-smooth, 검색)과 대비:
        같은 2차라도 집합-도달성은 sharpen, 가중확산은 뭉갬 → 뭉뜽거림 *방식*이 결정적 변수.
    (C) 강도 정직: 단서는 동일(동의/변형)에서 강하고 비슷/어느정도/무관 미세대역은 단조지만 격차 미미
        (AUC 0.73 = 쓸만한 단서지 벡터정밀 아님 — 지론의 "확정값 아닌 단서" 그대로). 미세대역 sharpening 미해결.
    (D) 복합 = naive union 반증. prof(s1)⊕prof(s2) 합집합은 prof(복합어)로 이동 안 함(composed 0.175 <
        최선부분 0.214, 우위율 0.08). 단 부분 단독(0.214) ≫ 랜덤(0.019) = 부분이 복합어 의미를 *담고는 있음*
        (합성 신호 존재). 결합은 일어나나 *합(union)이 틀린 연산자* — head 지배/특이도(idf)가중/교집합-부스트 등
        병합연산 재설계 필요.

    종합: 지론의 "경험=의미 · graded 비교 · 즉시비교 · 재귀(2홉 집합) 유효"는 데이터로 지지. "그래프 병합=새 의미"는
    naive union 에선 미지지 — 합성 연산자가 다음 표적. memory project_experience_meaning_graph 의 crux(좋은
    뭉뜽거림)는 2홉-집합으로 한 칸 전진, 복합은 미해결로 남음.

    다음(V235): (1) 복합 합성연산자 — union 대신 head-weighted / idf가중 / 교집합-부스트로 prof(복합어) 재현 회복.
    (2) 미세대역 sharpening — 2홉 집합에 salient-feature 가중 도입(collapse 경계 탐색).
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

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V234_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V234_ROWS_PER_FILE", "600"))
BODY_CHARS = int(os.environ.get("DARTLAB_HORIZON_V234_BODY_CHARS", "6000"))
VOCAB_SIZE = int(os.environ.get("DARTLAB_HORIZON_V234_VOCAB", "3000"))
CO_TOPM = int(os.environ.get("DARTLAB_HORIZON_V234_CO_TOPM", "40"))
MIN_CO = int(os.environ.get("DARTLAB_HORIZON_V234_MIN_CO", "3"))
PROF_TOPK = int(os.environ.get("DARTLAB_HORIZON_V234_PROF_TOPK", "40"))
SPPMI_SHIFT = float(os.environ.get("DARTLAB_HORIZON_V234_SPPMI_SHIFT", "0.7"))
MIN_PROF = int(os.environ.get("DARTLAB_HORIZON_V234_MIN_PROF", "6"))
MAX_LABELED = int(os.environ.get("DARTLAB_HORIZON_V234_MAX_LABELED", "500"))
CODE_PREFIX = int(os.environ.get("DARTLAB_HORIZON_V234_CODE_PREFIX", "3"))
TWOHOP_CAP = int(os.environ.get("DARTLAB_HORIZON_V234_TWOHOP_CAP", "120"))

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
    """단일토큰 korName -> (canonical, sj, codeFamily, code). referential ordinal scaffold."""
    d = json.load(open(MAPPING_PATH, encoding="utf-8"))
    mappings: dict[str, str] = d["mappings"]
    standard: dict[str, dict] = d["standardAccounts"]
    labels: dict[str, tuple] = {}
    for kor, canon in mappings.items():
        k = kor.strip()
        if not (2 <= len(k) <= 14) or NUM_RE.search(k) or not HANGUL_RE.fullmatch(k):
            continue  # 단일 한글 토큰만
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
    # pass1: df
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
    vocab |= {s for s in labels if s in df1}  # 라벨 stem 은 무조건 포함
    # pass2: 문서단위 공기 (doc 의 top-CO_TOPM vocab stem 간)
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
                a = top[i]
                ca = co[a]
                for j in range(len(top)):
                    if i != j:
                        ca[top[j]] += 1
        del d
    return co, sdf, nDocs, vocab


def buildProfiles(co, sdf, nDocs):
    prof: dict[str, dict[str, float]] = {}
    logN = math.log(max(1, nDocs))
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
            pmi = (math.log(c) + logN) - (math.log(dfa) + math.log(dfb)) - SPPMI_SHIFT
            if pmi > 0:
                w[b] = pmi
        if len(w) >= 1:
            prof[a] = dict(sorted(w.items(), key=lambda kv: kv[1], reverse=True)[:PROF_TOPK])
    return prof


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


def auc(pos: list[float], neg: list[float]) -> float:
    """P(pos > neg) — Mann-Whitney. 0.5=무변별."""
    if not pos or not neg:
        return 0.5
    allv = sorted([(v, 0) for v in neg] + [(v, 1) for v in pos])
    rank = 0.0
    i = 0
    n = len(allv)
    rankSumPos = 0.0
    while i < n:
        j = i
        while j < n and allv[j][0] == allv[i][0]:
            j += 1
        avg = (i + 1 + j) / 2.0  # 1-based 평균 순위(동점 처리)
        for k in range(i, j):
            rank = avg
            if allv[k][1] == 1:
                rankSumPos += rank
        i = j
    nPos = len(pos)
    nNeg = len(neg)
    u = rankSumPos - nPos * (nPos + 1) / 2.0
    return u / (nPos * nNeg)


def main() -> None:
    t0 = time.time()
    labels = loadLabels()
    co, sdf, nDocs, vocab = loadCooccurrence(labels)
    prof = buildProfiles(co, sdf, nDocs)
    del co

    # 뭉뜽거림 시그니처들
    anchor: dict[str, str] = {}
    setSig: dict[str, set] = {}
    twoSig: dict[str, set] = {}
    classSig: dict[str, dict] = {}
    for s, p in prof.items():
        keys = set(p)
        setSig[s] = keys
        anchor[s] = max(p.items(), key=lambda kv: (kv[1], kv[0]))[0]
    for s, p in prof.items():
        two = set(setSig[s])
        for n, _ in sorted(p.items(), key=lambda kv: (-kv[1], kv[0])):  # 가중치 순(결정적)
            two |= setSig.get(n, set())
            if len(two) > TWOHOP_CAP:
                break
        twoSig[s] = two
        cls: dict[str, float] = defaultdict(float)
        for n, wv in p.items():
            cls[anchor.get(n, n)] += wv
        classSig[s] = dict(cls)

    # 라벨 stem (프로필 충분한 것만)
    lab = [s for s in labels if s in prof and len(prof[s]) >= MIN_PROF]
    lab = sorted(lab)[:MAX_LABELED]

    sims = {"raw": {}, "set": {}, "2hop": {}, "class": {}}
    bandSims = {sg: defaultdict(list) for sg in sims}
    nPairs = 0
    tCmp = time.time()
    for i in range(len(lab)):
        a = lab[i]
        for j in range(i + 1, len(lab)):
            b = lab[j]
            bd = band(labels[a], labels[b])
            nPairs += 1
            bandSims["raw"][bd].append(cosine(prof[a], prof[b]))
            bandSims["set"][bd].append(jaccard(setSig[a], setSig[b]))
            bandSims["2hop"][bd].append(jaccard(twoSig[a], twoSig[b]))
            bandSims["class"][bd].append(cosine(classSig[a], classSig[b]))
    cmpMs = (time.time() - tCmp) / max(1, nPairs) * 1e6  # µs/pair (4 sig 합산)

    bandsOrder = ["동일", "비슷", "어느정도", "무관"]
    print("=" * 80)
    print(f"V234 경험=의미 그래프: 뭉뜽거림 비교가 graded 단서를 주는가  (total {time.time() - t0:.1f}s)")
    print(
        f"files={FILE_LIMIT} docs={nDocs} vocab={len(vocab)} profiled={len(prof)} labeledStems={len(lab)} pairs={nPairs}"
    )
    print(f"즉시비교 비용 = {cmpMs:.1f} µs/pair (4 시그니처 합산, 임베딩/GPU 0)")
    print("-" * 80)
    print(f"{'signature':<8} " + "  ".join(f"{b:>8}" for b in bandsOrder) + "   AUC(동일>무관)  ladder?")
    best = None
    for sg in ["raw", "set", "2hop", "class"]:
        means = {}
        for b in bandsOrder:
            vs = bandSims[sg][b]
            means[b] = sum(vs) / len(vs) if vs else 0.0
        a = auc(bandSims[sg]["동일"], bandSims[sg]["무관"])
        # ladder = 단조감소(동일>=비슷>=어느정도>=무관) 충족 단계 수
        seq = [means[b] for b in bandsOrder]
        mono = sum(1 for k in range(len(seq) - 1) if seq[k] >= seq[k + 1] - 1e-9)
        ladder = f"{mono}/3"
        print(f"{sg:<8} " + "  ".join(f"{means[b]:8.4f}" for b in bandsOrder) + f"   {a:11.3f}   {ladder}")
        if best is None or a > best[1]:
            best = (sg, a, mono, means)

    # null: 경험(프로필)을 stem 간 셔플 -> 등급 무너지는가. 인접보존 회전은 라벨구조가 새므로
    # 곱셈순열(stride⊥n)로 인접을 흩는다 — 동일/무관 라벨이 임의 프로필을 받아 변별이 사라져야 정상.
    print("-" * 80)
    nL = len(lab)
    stride = nL // 2 + 1
    while math.gcd(stride, nL) != 1:
        stride += 1
    permProf = {lab[k]: prof[lab[(k * stride + 1) % nL]] for k in range(nL)}
    nullPos, nullNeg = [], []
    for i in range(len(lab)):
        for j in range(i + 1, len(lab)):
            bd = band(labels[lab[i]], labels[lab[j]])
            if bd == "동일":
                nullPos.append(cosine(permProf[lab[i]], permProf[lab[j]]))
            elif bd == "무관":
                nullNeg.append(cosine(permProf[lab[i]], permProf[lab[j]]))
    nullAuc = auc(nullPos, nullNeg)
    realAuc = auc(bandSims["raw"]["동일"], bandSims["raw"]["무관"])
    print(
        f"null(경험 셔플) raw AUC = {nullAuc:.3f}  vs  real raw AUC = {realAuc:.3f}  "
        f"-> {'등급은 경험 덕 (null 붕괴)' if realAuc - nullAuc > 0.05 else '경험 무관(주의)'}"
    )

    # 복합: prof(s1)⊕prof(s2) 가 prof(복합어)로 이동하는가
    print("-" * 80)
    comps = []
    profStems = set(prof)
    for c in sorted(profStems):
        if len(c) < 4 or len(prof[c]) < MIN_PROF:
            continue
        for cut in range(2, len(c) - 1):
            s1, s2 = c[:cut], c[cut:]
            if s1 in profStems and s2 in profStems and len(prof[s1]) >= MIN_PROF and len(prof[s2]) >= MIN_PROF:
                comps.append((c, s1, s2))
                break
        if len(comps) >= 200:
            break
    if comps:
        gains = []
        randStems = sorted(profStems)
        for idx, (c, s1, s2) in enumerate(comps):
            merged: dict[str, float] = defaultdict(float)
            for k, v in prof[s1].items():
                merged[k] += v
            for k, v in prof[s2].items():
                merged[k] += v
            simComposed = cosine(merged, prof[c])
            simPart = max(cosine(prof[s1], prof[c]), cosine(prof[s2], prof[c]))
            rnd = randStems[(idx * 7 + 3) % len(randStems)]
            simRand = cosine(prof[rnd], prof[c])
            gains.append((simComposed, simPart, simRand))
        mc = sum(g[0] for g in gains) / len(gains)
        mp = sum(g[1] for g in gains) / len(gains)
        mr = sum(g[2] for g in gains) / len(gains)
        better = sum(1 for g in gains if g[0] >= g[1] and g[0] > g[2]) / len(gains)
        print(
            f"복합 재현 n={len(comps)}: composed→복합어 cos={mc:.3f}  최선부분 {mp:.3f}  랜덤 {mr:.3f}  "
            f"composed 우위율={better:.2f}"
        )
    else:
        print("복합: 분해 가능한 복합어 stem 부족(샘플 0)")

    print("-" * 80)
    sg, a, mono, _ = best
    print(
        f"VERDICT: 최고 뭉뜽거림='{sg}' AUC={a:.3f} ladder={mono}/3. "
        f"{'graded 단서 성립(동일>무관 변별 + 단조)' if a > 0.6 and mono >= 2 else '단서 약함 — 뭉뜽거림 재설계 필요'}"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
