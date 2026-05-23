"""RI-VSA 평가 셋트 (A) — recall@k / precision@k / MRR.

목적
----
지금까지 v1~v7 의 stem 응집 (자기↔자사 d=9 등) 은 *해시 자체 품질* 의 측정.
실제 *검색 품질* (자연어 쿼리 → 관련 공시 회수) 은 측정 X.
이 모듈이 그 평가의 SSOT.

설계
----
- 자연어 쿼리 12 개 (riVsaSearch v4 와 동일)
- 각 쿼리당 *정답 정의* = report_nm regex (도메인 룰, 수동 라벨링 회피)
- 메트릭 — recall@k, precision@k, MRR. 표본은 corpus 의 모든 공시.

정답 정의 (relevance rules)
--------------------------
| 쿼리 | report_nm regex (정답) |
|---|---|
| 회사가 돈 빌렸나 | (단기차입|장기차입|회사채발행|사채.*결정) |
| 유상증자한 회사 | 유상증자 |
| 대표이사 누가 바뀌었나 | 대표이사.*변경|임원ㆍ주요주주특정증권등 |
| 자사주 사들였나 | 자기주식.*(취득|처분).*결정 |
| 합병 결정 | 합병 |
| 전환사채 발행 | 전환사채 |
| 최대주주 변경 | 최대주주.*변경 |
| 공장 짓는 회사 | (공장|시설).*투자|신규시설 |
| 특허 분쟁 | 소송|특허 |
| 주주총회 결과 | 주주총회결과 |
| 감자 결정 | 감자 |
| 배당 지급 | (현금ㆍ현물)?배당.*결정 |

사용
----
    from evalSet import QUERIES, evaluate

    section_hashes = ...  # (n_sec, 32) uint8
    query_hashes = {q: ... for q in QUERIES}  # (32,) uint8 each
    report_nms = ...      # list[str] per section
    rcept_nos = ...       # list[str] per section

    scores = evaluate(section_hashes, query_hashes, report_nms, rcept_nos)
    # → {query: {'recall@5': .., 'precision@5': .., 'mrr': ..}}

결과
----
실행 결과는 riVsaSearchV2 에서 채워진다 (본 모듈은 라이브러리).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass(frozen=True)
class Query:
    text: str
    relevance: re.Pattern  # report_nm 매칭


# 정답 정의 — report_nm regex 기반.
# 한국어 한자ㆍ띄어쓰기 다양성 고려.
QUERIES: tuple[Query, ...] = (
    Query("회사가 돈 빌렸나", re.compile(r"(단기차입|장기차입|회사채|사채발행)")),
    Query("유상증자한 회사", re.compile(r"유상증자")),
    Query("대표이사 누가 바뀌었나", re.compile(r"대표이사.*변경")),
    Query("자사주 사들였나", re.compile(r"자기주식.*(취득|처분).*결정")),
    Query("합병 결정", re.compile(r"합병")),
    Query("전환사채 발행", re.compile(r"전환사채")),
    Query("최대주주 변경", re.compile(r"최대주주.*변경")),
    Query("공장 짓는 회사", re.compile(r"(시설.*투자|신규시설|공장.*신설)")),
    Query("특허 분쟁", re.compile(r"(소송|특허.*분쟁)")),
    Query("주주총회 결과", re.compile(r"주주총회결과")),
    Query("감자 결정", re.compile(r"감자")),
    Query("배당 지급", re.compile(r"배당.*결정")),
)


def labelRelevance(report_nms: list[str], pattern: re.Pattern) -> np.ndarray:
    """report_nm 마다 정답 여부 0/1 boolean 배열."""
    return np.asarray(
        [bool(pattern.search(r or "")) for r in report_nms],
        dtype=bool,
    )


def topKBySection(
    section_hashes: np.ndarray,
    query_hash: np.ndarray,
    k: int,
) -> tuple[np.ndarray, np.ndarray]:
    """쿼리 해시 → 섹션 top-k (id, distance). 섹션 단위 (rcept 중복 허용)."""
    xored = np.bitwise_xor(section_hashes, query_hash[None, :])
    dist = np.unpackbits(xored, axis=1).sum(axis=1)
    k = min(k, len(dist))
    part = np.argpartition(dist, k - 1)[:k]
    order = part[np.argsort(dist[part])]
    return order, dist[order]


def topKDeduped(
    section_hashes: np.ndarray,
    query_hash: np.ndarray,
    rcept_nos: list[str],
    k: int,
    pool: int = 200,
) -> tuple[np.ndarray, np.ndarray]:
    """rcept 중복 제거 top-k. pool 만큼 뽑아 dedup 후 k 슬라이스."""
    order, dist = topKBySection(section_hashes, query_hash, pool)
    seen: set[str] = set()
    uniq_ids: list[int] = []
    uniq_dist: list[int] = []
    for sid, d in zip(order, dist):
        r = rcept_nos[int(sid)]
        if r in seen:
            continue
        seen.add(r)
        uniq_ids.append(int(sid))
        uniq_dist.append(int(d))
        if len(uniq_ids) >= k:
            break
    return np.asarray(uniq_ids, dtype=np.int64), np.asarray(uniq_dist, dtype=np.int32)


def evaluate(
    section_hashes: np.ndarray,
    query_hash_fn: Callable[[str], np.ndarray],
    report_nms: list[str],
    rcept_nos: list[str],
    *,
    ks: tuple[int, ...] = (5, 10),
) -> dict[str, dict[str, float]]:
    """각 쿼리당 precision@k / recall@k / MRR. 공시 단위 (rcept 중복 제거)."""
    out: dict[str, dict[str, float]] = {}
    # rcept → relevance — 한 rcept 의 어떤 섹션이라도 정답이면 정답.
    rcept_first_idx: dict[str, int] = {}
    for i, r in enumerate(rcept_nos):
        rcept_first_idx.setdefault(r, i)
    rcepts = list(rcept_first_idx.keys())

    for q in QUERIES:
        rel_by_section = labelRelevance(report_nms, q.relevance)
        total_relevant_rcepts = sum(1 for r in rcepts if rel_by_section[rcept_first_idx[r]])
        scores: dict[str, float] = {"total_relevant": float(total_relevant_rcepts)}

        if total_relevant_rcepts == 0:
            for k in ks:
                scores[f"recall@{k}"] = float("nan")
                scores[f"precision@{k}"] = float("nan")
            scores["mrr"] = float("nan")
            out[q.text] = scores
            continue

        qh = query_hash_fn(q.text)
        max_k = max(ks)
        hit_ids, hit_dists = topKDeduped(section_hashes, qh, rcept_nos, k=max_k, pool=max_k * 30)

        # 각 hit 의 정답 여부 (section_id 단위 → relevance)
        hit_rel = [bool(rel_by_section[sid]) for sid in hit_ids]

        for k in ks:
            hit_top = hit_rel[:k]
            scores[f"precision@{k}"] = sum(hit_top) / k
            scores[f"recall@{k}"] = sum(hit_top) / total_relevant_rcepts

        # MRR — 첫 정답 순위
        rr = 0.0
        for rank, h in enumerate(hit_rel, 1):
            if h:
                rr = 1.0 / rank
                break
        scores["mrr"] = rr
        out[q.text] = scores

    return out


def formatReport(scores: dict[str, dict[str, float]]) -> str:
    """평가 결과 표 형식 출력 — 한 hash 자산의 점수."""
    lines = []
    lines.append(f"{'쿼리':<22} {'#정답':>6} {'P@5':>6} {'P@10':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
    lines.append("-" * 70)
    p5s, p10s, r5s, r10s, mrrs = [], [], [], [], []
    for q, s in scores.items():
        n = int(s["total_relevant"])
        p5 = s["precision@5"]
        p10 = s["precision@10"]
        r5 = s["recall@5"]
        r10 = s["recall@10"]
        mrr = s["mrr"]
        if not np.isnan(p5):
            p5s.append(p5)
            p10s.append(p10)
            r5s.append(r5)
            r10s.append(r10)
            mrrs.append(mrr)
        lines.append(f"{q:<22} {n:>6d} {p5:>6.2f} {p10:>6.2f} {r5:>6.2f} {r10:>6.2f} {mrr:>6.2f}")
    lines.append("-" * 70)
    if p5s:
        lines.append(
            f"{'평균':<22} {'':>6} {np.mean(p5s):>6.2f} {np.mean(p10s):>6.2f} "
            f"{np.mean(r5s):>6.2f} {np.mean(r10s):>6.2f} {np.mean(mrrs):>6.2f}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    # 단독 실행 — 정답 라벨 분포 확인
    from pathlib import Path

    import polars as pl

    files = sorted(p for p in Path("data/dart/allFilings").glob("2026*.parquet") if "_meta" not in p.name)
    df = pl.concat([pl.read_parquet(f, columns=["rcept_no", "report_nm"]) for f in files])
    df = df.unique("rcept_no")
    rcept_count = df.height
    report_nms = df["report_nm"].to_list()
    print(f"corpus 공시 (rcept unique): {rcept_count:,}")
    print()
    print("─── 정답 분포 ───")
    for q in QUERIES:
        mask = labelRelevance(report_nms, q.relevance)
        n = int(mask.sum())
        pct = 100 * n / rcept_count
        print(f"  {q.text:<22} → {n:>5d} 공시 ({pct:>5.2f}%)")
