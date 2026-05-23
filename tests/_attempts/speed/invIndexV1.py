"""invIndexV1 — DART 공시 BM25 역인덱스 (의미 X, 빠른 lexical 검색).

배경
----
semantic v1~v14 모두 evalSet 객관 평가에서 P@5 < 0.30 fail. 의미 트랙 폐기,
역인덱스 기반 lexical 검색기를 base layer 로 만든다. 이 prototype 이 검증되면
dartlab search 본격 도입 후보.

비교 base
--------
- FM-index (`fmIndexBench`/`fmIndexMmap`) — substring 정확 매칭 µs 단위. 부분
  매칭·랭킹 X. 한 쿼리당 occurrence 만 count.
- 본 파일 — 토큰 단위 부분 매칭 + BM25 랭킹. 부분/AND/IDF 가중. corpus
  넓혀도 query latency ~ms.

설계
----
- 단위: rcept (공시) — 검색 결과 = 공시 리스트
- 텍스트: report_nm + section_title + section_content concat per rcept
- 토큰: `[가-힣]+|[a-zA-Z0-9]+` regex split + lowercase + len ≥ 2
- 랭킹: BM25 (k1=1.5, b=0.75) — 표준 Okapi 공식
- MAX_DOC_TOKENS=10000 (한 doc tokens cap, OOM 방지)
- 저장: `data/_scratch_fm/invIdx/` — postings.pkl + meta.parquet
- 환경 변수 N_FILES (default 10) — 빌드 corpus 크기 조절

평가
----
evalSet.QUERIES 12 자연어 쿼리 × P@5/P@10/R@5/R@10/MRR + 자연어 snippet 데모.

결과 (2026-05-21, N_FILES=10 = 7,905 공시)
------------------------------------------
빌드: 42s. 인덱스 206K terms, postings 44MB, meta 0.4MB. avg_dl 1,487 tokens/doc.
검색 latency: 0.06~0.19 ms (CPU, in-memory dict + numpy).

evalSet 객관 평가 (12 쿼리, P@5 / P@10 / MRR):
| 쿼리 | #정답 | P@5 | P@10 | MRR |
|---|---|---|---|---|
| 대표이사 누가 바뀌었나 | 11 | 0.80 | 0.60 | 1.00 |
| 합병 결정 | 26 | 0.80 | 0.60 | 1.00 |
| 전환사채 발행 | 106 | 0.60 | 0.70 | 1.00 |
| 최대주주 변경 | 52 | 1.00 | 0.90 | 1.00 |
| 감자 결정 | 48 | 1.00 | 1.00 | 1.00 |
| 배당 지급 | 827 | 1.00 | 0.80 | 1.00 |
| 주주총회 결과 | 25 | 0.40 | 0.30 | 0.33 |
| 특허 분쟁 | 69 | 0.00 | 0.40 | 0.17 |
| 공장 짓는 회사 | 13 | 0.00 | 0.10 | 0.14 |
| 회사가 돈 빌렸나 | 5 | 0.00 | 0.00 | 0.00 |
| 유상증자한 회사 | 115 | 0.00 | 0.00 | 0.00 |
| 자사주 사들였나 | 123 | 0.00 | 0.00 | 0.00 |
| **평균** | | **0.47** | **0.45** | **0.55** |

비교:
- semantic v1~v14 평균 P@5 < 0.30 → BM25 lexical 가 *절대적으로 우수*.
- 8/12 쿼리 매칭 강함 (직접 토큰 매칭).
- 4/12 fail — 자연어 ↔ 도메인 어휘 갭 (lexical 의 본질적 상한):
  - "유상증자한 회사" — 어미 "한" 때문에 corpus "유상증자" 와 별 token (어간 분리 또는
    char ngram 으로 완화 가능)
  - "회사가 돈 빌렸나" — corpus "사채/차입" 과 공유 토큰 0 (동의어 사전 필요)
  - "자사주 사들였나" — corpus "자기주식" 과 다른 표기 (동의어 사전 필요)
  - "공장 짓는 회사" — corpus "시설투자/신규시설" 과 다른 표기 (동의어 사전 필요)

다음 후보
--------
- V2: char-2gram 보조 인덱스 추가 — "유상증자한" → "유상", "상증", "증자" 부분 매칭
- V3: 동의어 사전 (자사주↔자기주식, 돈빌리다↔사채/차입) hybrid
- N_FILES=65 (전체 corpus) 빌드 → 빌드 시간 ~4.5 분 추정, postings ~300MB
- dartlab.search 본격 도입 검토 — 본 V1 (또는 V2) 이 검증되면
"""

from __future__ import annotations

import os
import pickle
import re
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import polars as pl

# evalSet 는 sibling 폴더 (tests/_attempts/semantic/) 에 있다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "semantic"))
from evalSet import QUERIES, labelRelevance  # noqa: E402

ALLFILINGS_DIR = Path("data/dart/allFilings")
ASSETS_DIR = Path("data/_scratch_fm/invIdx")
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
POSTINGS_PATH = ASSETS_DIR / "postings.pkl"
META_PATH = ASSETS_DIR / "meta.parquet"

TOKEN_RE = re.compile(r"[가-힣]+|[a-zA-Z0-9]+")
MIN_TOK_LEN = 2
MAX_DOC_TOKENS = 10_000
N_FILES = int(os.environ.get("N_FILES", "10"))


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [t for t in TOKEN_RE.findall(text.lower()) if len(t) >= MIN_TOK_LEN]


def buildIndex() -> tuple[dict[str, np.ndarray], np.ndarray, pl.DataFrame]:
    """parquet → posting list per term, doc_lens, doc meta."""
    files = sorted(p for p in ALLFILINGS_DIR.glob("2026*.parquet") if "_meta" not in p.name)
    files = files[:N_FILES]
    print(f"[files] {len(files)} parquet (N_FILES={N_FILES})")

    postings: dict[str, list[tuple[int, int]]] = {}
    docLens: list[int] = []
    docMetaRows: list[tuple[str, str, str]] = []  # (rcept_no, report_nm, snippet)

    docId = 0
    t0 = time.perf_counter()
    for fi, f in enumerate(files):
        df = (
            pl.read_parquet(
                f,
                columns=["rcept_no", "report_nm", "section_title", "section_content"],
            )
            .filter(pl.col("section_content").is_not_null())
            .group_by("rcept_no")
            .agg(
                pl.col("report_nm").first().alias("report_nm"),
                pl.col("section_title").str.join(" ").alias("titles"),
                pl.col("section_content").str.join(" ").alias("contents"),
            )
        )
        for row in df.iter_rows():
            rcept_no, rn, titles, contents = row
            text = (rn or "") + " " + (titles or "") + " " + (contents or "")
            tokens = tokenize(text)
            if len(tokens) > MAX_DOC_TOKENS:
                tokens = tokens[:MAX_DOC_TOKENS]
            counter = Counter(tokens)
            for term, tf in counter.items():
                postings.setdefault(term, []).append((docId, tf))
            docLens.append(len(tokens))
            snippet = text[:300].replace("\n", " ").replace("\r", " ")
            docMetaRows.append((rcept_no, rn or "", snippet))
            docId += 1
        del df
        if (fi + 1) % 5 == 0 or fi == len(files) - 1:
            elapsed = time.perf_counter() - t0
            print(
                f"  [build] file {fi + 1}/{len(files)} | docs {docId:,} | "
                f"terms {len(postings):,} | elapsed {elapsed:.0f}s"
            )

    nDocs = docId
    print(f"[build] docs {nDocs:,} | terms {len(postings):,} | {time.perf_counter() - t0:.0f}s")

    # posting list → numpy (doc_id, tf) per term
    t0 = time.perf_counter()
    postingArrays: dict[str, np.ndarray] = {term: np.asarray(plist, dtype=np.int32) for term, plist in postings.items()}
    print(f"[finalize] posting → numpy | {time.perf_counter() - t0:.1f}s")

    docLensArr = np.asarray(docLens, dtype=np.int32)
    metaDf = pl.DataFrame(
        {
            "doc_id": list(range(nDocs)),
            "rcept_no": [r[0] for r in docMetaRows],
            "report_nm": [r[1] for r in docMetaRows],
            "snippet": [r[2] for r in docMetaRows],
        }
    )
    return postingArrays, docLensArr, metaDf


def saveIndex(postings: dict[str, np.ndarray], docLens: np.ndarray, metaDf: pl.DataFrame) -> None:
    t0 = time.perf_counter()
    with open(POSTINGS_PATH, "wb") as f:
        pickle.dump({"postings": postings, "docLens": docLens}, f, protocol=4)
    metaDf.write_parquet(META_PATH)
    pSize = POSTINGS_PATH.stat().st_size / 1e6
    mSize = META_PATH.stat().st_size / 1e6
    print(f"[save] {time.perf_counter() - t0:.1f}s | postings {pSize:.0f}MB | meta {mSize:.0f}MB")


def loadIndex() -> tuple[dict[str, np.ndarray], np.ndarray, pl.DataFrame]:
    with open(POSTINGS_PATH, "rb") as f:
        d = pickle.load(f)
    metaDf = pl.read_parquet(META_PATH)
    return d["postings"], d["docLens"], metaDf


def searchBM25(
    query: str,
    postings: dict[str, np.ndarray],
    docLens: np.ndarray,
    nDocs: int,
    avgDl: float,
    topK: int = 20,
    k1: float = 1.5,
    b: float = 0.75,
) -> tuple[np.ndarray, np.ndarray]:
    qTokens = list(set(tokenize(query)))
    scores = np.zeros(nDocs, dtype=np.float32)
    for term in qTokens:
        plist = postings.get(term)
        if plist is None:
            continue
        df = len(plist)
        idf = float(np.log((nDocs - df + 0.5) / (df + 0.5) + 1.0))
        docIds = plist[:, 0]
        tfs = plist[:, 1].astype(np.float32)
        dls = docLens[docIds].astype(np.float32)
        norm = (1.0 - b) + b * (dls / avgDl)
        contrib = idf * tfs * (k1 + 1.0) / (tfs + k1 * norm)
        np.add.at(scores, docIds, contrib)
    topK = min(topK, nDocs)
    if topK == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float32)
    part = np.argpartition(-scores, topK - 1)[:topK]
    order = part[np.argsort(-scores[part])]
    return order, scores[order]


def main() -> None:
    print("=" * 72)
    print(f"invIndexV1 — DART 공시 BM25 역인덱스 (N_FILES={N_FILES})")
    print("=" * 72)

    if POSTINGS_PATH.exists() and META_PATH.exists():
        print("[cache] reload")
        t0 = time.perf_counter()
        postings, docLens, metaDf = loadIndex()
        print(f"[cache] reload {time.perf_counter() - t0:.1f}s")
    else:
        postings, docLens, metaDf = buildIndex()
        saveIndex(postings, docLens, metaDf)

    nDocs = len(docLens)
    avgDl = float(docLens.mean()) if nDocs > 0 else 1.0
    print(f"[index] docs {nDocs:,} | terms {len(postings):,} | avg_dl {avgDl:.0f}")

    docReportNms = metaDf["report_nm"].to_list()
    docRceptNos = metaDf["rcept_no"].to_list()
    docSnippets = metaDf["snippet"].to_list()

    # ── 평가 ──
    print()
    print("─── 평가 (evalSet 12 쿼리, BM25 lexical) ───")
    print(f"{'쿼리':<22} {'#정답':>6} {'P@5':>6} {'P@10':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6} {'lat_ms':>8}")
    print("-" * 80)
    p5s, p10s, r5s, r10s, mrrs, lats = [], [], [], [], [], []
    for q in QUERIES:
        rel = labelRelevance(docReportNms, q.relevance)
        totalRel = int(rel.sum())
        if totalRel == 0:
            print(f"{q.text:<22} {0:>6d} {'nan':>6} {'nan':>6} {'nan':>6} {'nan':>6} {'nan':>6} {'nan':>8}")
            continue
        t0 = time.perf_counter()
        order, _ = searchBM25(q.text, postings, docLens, nDocs, avgDl, topK=10)
        latMs = (time.perf_counter() - t0) * 1000
        hitRel = [bool(rel[int(did)]) for did in order]
        p5 = sum(hitRel[:5]) / 5
        p10 = sum(hitRel[:10]) / 10
        r5 = sum(hitRel[:5]) / totalRel
        r10 = sum(hitRel[:10]) / totalRel
        rr = 0.0
        for rank, h in enumerate(hitRel, 1):
            if h:
                rr = 1.0 / rank
                break
        p5s.append(p5)
        p10s.append(p10)
        r5s.append(r5)
        r10s.append(r10)
        mrrs.append(rr)
        lats.append(latMs)
        print(f"{q.text:<22} {totalRel:>6d} {p5:>6.2f} {p10:>6.2f} {r5:>6.2f} {r10:>6.2f} {rr:>6.2f} {latMs:>8.2f}")
    print("-" * 80)
    if p5s:
        print(
            f"{'평균':<22} {'':>6} {np.mean(p5s):>6.2f} {np.mean(p10s):>6.2f} "
            f"{np.mean(r5s):>6.2f} {np.mean(r10s):>6.2f} {np.mean(mrrs):>6.2f} "
            f"{np.mean(lats):>8.2f}"
        )

    # ── 자연어 쿼리 snippet ──
    print()
    print("─── snippet 데모 (top 5) ───")
    SHOW = [
        "회사가 돈 빌렸나",
        "자사주 사들였나",
        "공장 짓는 회사",
        "유상증자한 회사",
        "주주총회 결과",
        "전환사채 발행",
        "대표이사 변경",
    ]
    for q in SHOW:
        order, scores = searchBM25(q, postings, docLens, nDocs, avgDl, topK=5)
        print(f'\n❓ "{q}"')
        for did, sc in zip(order, scores):
            did = int(did)
            print(
                f"  score={float(sc):7.2f}  rcept={docRceptNos[did]}  "
                f"rn={docReportNms[did][:30]:30s}  snip={docSnippets[did][:80]}"
            )


if __name__ == "__main__":
    main()
