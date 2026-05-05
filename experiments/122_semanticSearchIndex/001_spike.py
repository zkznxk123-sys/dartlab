"""실험 122 — Semantic Search Index 스파이크.

의도:
- dart_model2vec (minishlab/M2V_base_output 또는 로컬 증류본) 로드
- 임의 텍스트 1000 chunk 로 인코딩 시간 측정
- cosine NearestNeighbors 로 top-k 검색
- numpy 단순 저장 → 필요 시 parquet 단계 확장
- BM25 와 동시 평가

실행:
    cd experiments/122_semanticSearchIndex
    uv run --with model2vec --with scikit-learn --with polars python -X utf8 001_spike.py

본 스파이크 목적은 "가능성·속도·메모리 측정" 이지 Recall@5 레이블링이 아님.
레이블링은 사람 판정 → 후속 단계.
"""

from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ── 더미 텍스트 (docs parquet 없을 때 fallback) ─────────────────────
_FALLBACK_DOCS = [
    "반도체 HBM 고대역폭 메모리 투자 확대 DRAM 설비 증설",
    "환율 원달러 변동성 환헤지 전략 외화부채 영향",
    "임상 3상 승인 실패 가능성 바이오시밀러 파이프라인",
    "전기차 배터리 양극재 리튬 니켈 공급망",
    "부동산 PF 대출 건전성 우려 연체율 상승",
    "공급망 재편 중국 의존도 감소 국산화",
    "AI 데이터센터 전력 소비 GPU 서버 냉각",
    "원자재 가격 상승 마진 압박 판가 전가",
    "조선 LNG 운반선 수주 고부가 수주잔고",
    "엔터테인먼트 글로벌 음반 공연 매출 다변화",
    "금리 인하 영향 부채비율 이자비용 감소",
    "유가 하락 정유 마진 개선 정제마진 배럴당",
    "반도체 수출 증가 미국 중국 수요 회복",
    "전기차 판매 부진 캐즘 하이브리드 전환",
    "자사주 매입 소각 주주환원 정책 확대",
]


QUERIES = [
    "반도체 HBM 투자",
    "환율 변동 리스크",
    "제약 임상 실패 가능성",
    "전기차 배터리 양극재",
    "부동산 PF 관련 우려",
    "공급망 중국 의존",
    "AI 데이터센터",
    "원가 상승 압박",
    "조선 LNG 수주",
    "엔터 글로벌 확장",
]


def _pid_rss_mb() -> float:
    try:
        import psutil
        p = psutil.Process()
        return p.memory_info().rss / 1024 / 1024
    except ImportError:
        return 0.0


def _measure(label: str, fn, *args, **kwargs):
    gc.collect()
    t0 = time.perf_counter()
    rss0 = _pid_rss_mb()
    result = fn(*args, **kwargs)
    t1 = time.perf_counter()
    rss1 = _pid_rss_mb()
    elapsed = (t1 - t0) * 1000
    print(f"  [{label}]  {elapsed:>8.2f} ms   RSS {rss0:.1f} → {rss1:.1f} MB")
    return result, elapsed, rss1


def _load_docs_sample(n: int = 1000) -> list[str]:
    """실제 docs parquet 이 있으면 샘플링, 없으면 더미 순환."""
    candidates = [
        ROOT / "data" / "dart" / "docs",
        Path.home() / ".cache" / "dartlab" / "docs",
    ]
    for d in candidates:
        if not d.exists():
            continue
        parquets = list(d.glob("*.parquet"))[:10]
        if not parquets:
            continue
        try:
            import polars as pl
            dfs = [pl.read_parquet(p).head(200) for p in parquets]
            df = pl.concat(dfs, how="diagonal_relaxed")
            text_cols = [c for c in df.columns if df[c].dtype == pl.Utf8]
            if not text_cols:
                continue
            chunks: list[str] = []
            for col in text_cols:
                values = df[col].drop_nulls().to_list()
                for v in values:
                    if isinstance(v, str) and 50 < len(v) < 2000:
                        chunks.append(v[:1000])
                        if len(chunks) >= n:
                            break
                if len(chunks) >= n:
                    break
            if chunks:
                print(f"  docs parquet 로드 성공: {d}, chunks={len(chunks)}")
                return chunks[:n]
        except Exception as exc:  # noqa: BLE001
            print(f"  docs parquet 읽기 실패 ({d}): {exc}")
            continue
    # fallback: 더미 순환
    print(f"  docs parquet 없음 → fallback 더미 {n} chunks")
    repeats = n // len(_FALLBACK_DOCS) + 1
    return (_FALLBACK_DOCS * repeats)[:n]


def _load_model():
    from model2vec import StaticModel

    # 순서대로 시도: 로컬 증류본 → HF base
    candidates = [
        str(ROOT / "experiments" / "105_filingSemanticMap" / "dart_model2vec"),
        "minishlab/M2V_base_output",  # public base
    ]
    last_err = None
    for name in candidates:
        try:
            m = StaticModel.from_pretrained(name)
            print(f"  model2vec 로드: {name}")
            return m
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"  실패 {name}: {exc}")
            continue
    raise RuntimeError(f"model2vec 로드 실패: {last_err}")


def _bm25_search(docs: list[str], query: str, top_k: int = 5) -> list[int]:
    """간단 BM25 단순 파이썬. 속도보다 비교 baseline 목적."""
    import math
    from collections import Counter

    tokenized = [d.split() for d in docs]
    n = len(tokenized)
    avgdl = sum(len(d) for d in tokenized) / n
    df: Counter = Counter()
    for d in tokenized:
        for t in set(d):
            df[t] += 1
    idf = {t: math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5)) for t in df}

    q_terms = query.split()
    k1, b = 1.5, 0.75
    scores = []
    for i, d in enumerate(tokenized):
        tf = Counter(d)
        dl = len(d)
        s = 0.0
        for t in q_terms:
            if t not in tf:
                continue
            freq = tf[t]
            s += idf.get(t, 0.0) * (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * dl / avgdl))
        scores.append((i, s))
    scores.sort(key=lambda x: x[1], reverse=True)
    return [i for i, _ in scores[:top_k]]


def main():
    print("=" * 60)
    print("실험 122 — Semantic Search Index 스파이크")
    print("=" * 60)

    print("\n[1] 문서 샘플 로드")
    docs, t_load, _ = _measure("load docs", _load_docs_sample, 1000)
    print(f"  chunks = {len(docs)}")

    print("\n[2] model2vec 로드")
    try:
        model, t_model, _ = _measure("model2vec init", _load_model)
    except Exception as exc:  # noqa: BLE001
        print(f"  [FATAL] {exc}")
        print("  → uv run --with model2vec --with scikit-learn --with polars --with huggingface-hub 로 실행")
        return 2

    print("\n[3] 인코딩")
    import numpy as np

    def _encode():
        return np.asarray(model.encode(docs))

    embs, t_encode, rss_encode = _measure("encode", _encode)
    print(f"  shape={embs.shape}  dtype={embs.dtype}")

    print("\n[4] NearestNeighbors 인덱스 구축")
    from sklearn.neighbors import NearestNeighbors

    def _build_nn():
        nn = NearestNeighbors(n_neighbors=5, metric="cosine")
        nn.fit(embs)
        return nn

    nn, t_nn, _ = _measure("sklearn NN fit", _build_nn)

    print("\n[5] 쿼리 실행 — semantic")
    sem_top5: dict[str, list[int]] = {}
    latencies: list[float] = []
    for q in QUERIES:
        gc.collect()
        t0 = time.perf_counter()
        q_emb = model.encode([q])
        _, idx = nn.kneighbors(np.asarray(q_emb), n_neighbors=5)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000)
        sem_top5[q] = idx[0].tolist()

    print(f"  avg latency: {sum(latencies)/len(latencies):.2f} ms")
    print(f"  max latency: {max(latencies):.2f} ms")

    print("\n[6] 쿼리 실행 — BM25 baseline")
    bm25_top5: dict[str, list[int]] = {}
    t0 = time.perf_counter()
    for q in QUERIES:
        bm25_top5[q] = _bm25_search(docs, q, top_k=5)
    t1 = time.perf_counter()
    print(f"  BM25 total: {(t1-t0)*1000:.2f} ms ({len(QUERIES)} queries)")

    print("\n[7] overlap 측정 — semantic ∩ BM25")
    overlaps = []
    for q in QUERIES:
        a, b = set(sem_top5[q]), set(bm25_top5[q])
        overlap = len(a & b)
        overlaps.append(overlap)
        print(f"  '{q}'   overlap={overlap}/5   sem={sorted(sem_top5[q])}   bm25={sorted(bm25_top5[q])}")

    avg_overlap = sum(overlaps) / len(overlaps)
    print(f"\n  avg overlap: {avg_overlap:.2f}/5")

    print("\n" + "=" * 60)
    print("요약")
    print("=" * 60)
    print(f"docs: {len(docs)} chunks")
    print(f"embeddings: {embs.shape}, {embs.nbytes/1024/1024:.2f} MB")
    print(f"encode time: {t_encode:.1f} ms for {len(docs)} chunks  ({t_encode/len(docs):.2f} ms/chunk)")
    print(f"NN build: {t_nn:.1f} ms")
    print(f"query latency avg: {sum(latencies)/len(latencies):.2f} ms")
    print(f"sem ∩ bm25 평균 오버랩: {avg_overlap:.2f}/5 — 낮으면 relevance 차이 있다는 뜻")

    summary = {
        "docs": len(docs),
        "embShape": list(embs.shape),
        "embBytesMB": embs.nbytes / 1024 / 1024,
        "encodeMs": t_encode,
        "encodePerChunkMs": t_encode / len(docs),
        "nnBuildMs": t_nn,
        "queryAvgMs": sum(latencies) / len(latencies),
        "queryMaxMs": max(latencies),
        "bm25TotalMs": (t1 - t0) * 1000,
        "avgOverlap": avg_overlap,
        "queries": len(QUERIES),
    }
    out = Path(__file__).parent / "result.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과 저장: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
