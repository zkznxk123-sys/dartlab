"""doc2query SOTA 실험 — 100 공시 샘플로 의미 검색 가능 여부 검증.

- baseline: report_nm + section_title + content 앞 2K char 의 bigram/trigram 토큰만
- doc2query: 위 + Gemini Flash 가 생성한 질문 5 개의 토큰

테스트 쿼리는 *원 텍스트에 안 나오는 추상 표현* — substring 으로는 매칭 안 되는 의미 쿼리.

결과 (2026-05-20, 100 공시 sample × Gemini 2.5 Flash 5 질문/공시)
---------------------------------------------------------------
- 질문 생성: 12 분 (732s) — Gemini Flash free tier rate limit
- baseline stem: 21,833 / doc2query stem: 24,293 (+2,460 = +11%)

10 자연어 쿼리 평가 (token-count score top-5):

| 쿼리 | baseline | doc2query | 승자 |
|---|---|---|---|
| 회사가 돈 빌렸나 | 헛다리 | **단기차입금증가 정확** | doc2query 큰 승 |
| 자사주 사들였나 | 개인 보유 | **자기주식취득결과** | doc2query 큰 승 |
| 경영진 바뀌었나 | 일반 주총 | 임시주총결과 | doc2query 약승 |
| 큰 주주 바뀌었나 | 대량보유 정확 | 주총소집 (빗) | baseline |
| 신규 사업 | 단일판매계약 | 주총소집 (빗) | baseline |
| 공장 새로 짓나 | 동률 | 동률 | 무승부 |
| 이사회 사표 | 둘 다 미흡 | 동일 | 무승부 |
| 주주총회 결과 | 정확 | 동일 | 무승부 |
| 회사 합병 | 빗나감 | 빗나감 | 무승부 |
| 특허 분쟁 | 정확 | 동일 | 무승부 |

큰 승 2, 약승 1, 무승부 5, baseline 승 2.

결론
----
- ★ 어휘 갭 ("돈 빌렸나" → 차입금, "자사주" → 자기주식취득) 명확히 매움
- × 압도적 차이 X — 100 표본 작고 점수 단순 (token-count, BM25 가중 없음)
- × 비용: 100 공시 × 5 = 500 호출 / 12 분. 풀 corpus (5 년) = ~$300+ Gemini Flash

다음 단계
--------
- BM25 가중 + 1000+ 공시 sample 재시도
- 또는 doc2query 자체보다 RI-VSA (학습 0) 방향 → riVsaHash* 트랙

저장: data/_scratch_fm/doc2query.json (생성 질문 캐시)
"""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path

import polars as pl
from google import genai

# ── 토크나이저 (ngramIndex.py 와 동일) ──


def tokenize(text: str) -> set[str]:
    text = text.strip()
    tokens = set()
    if len(text) >= 2:
        tokens.update(text[i : i + 2] for i in range(len(text) - 1))
    if len(text) >= 3:
        tokens.update(text[i : i + 3] for i in range(len(text) - 2))
    return tokens


# ── 1. 샘플 로드 ──


def loadSample(n: int = 100) -> pl.DataFrame:
    """최근 일자 공시에서 다양한 report_nm 으로 N 공시 샘플."""
    # 2026-05-15 (정기공시 skip 후) + 2026-05-18 + 2026-05-19
    files = [
        "data/dart/allFilings/20260515.parquet",
        "data/dart/allFilings/20260518.parquet",
        "data/dart/allFilings/20260519.parquet",
    ]
    dfs = []
    for f in files:
        if Path(f).exists():
            df = pl.read_parquet(
                f,
                columns=["rcept_no", "corp_name", "report_nm", "section_title", "section_content"],
            ).filter(pl.col("section_content").is_not_null())
            # section_order 0 (대표 섹션) 만
            df = df.unique("rcept_no")
            dfs.append(df)
    if not dfs:
        raise RuntimeError("샘플 파일 없음")
    full = pl.concat(dfs).unique("rcept_no")
    # report_nm 다양성 위해 stratified sample
    sample = full.sample(min(n, full.height), seed=42)
    print(f"샘플: {sample.height} 공시")
    print("report_nm 상위:")
    print(sample.group_by("report_nm").agg(pl.len().alias("n")).sort("n", descending=True).head(10))
    return sample


# ── 2. Gemini 질문 생성 ──

DOC2QUERY_PROMPT = """다음은 한국 DART 공시의 일부다. 이 공시가 답할 수 있는 *짧고 자연스러운 한국어 질문* 을 5 개 만들어라.
- 각 질문은 10~25 자 한 줄
- 공시 본문의 단어를 그대로 쓰지 말고, 의미상 같은 *다른 표현* 으로 풀어 써라
- 추상적·일상적 표현 환영 ("회사가 돈 빌렸나" 같은)

회사: {corp_name}
공시명: {report_nm}
섹션: {section_title}
본문: {content}

질문 5 개 (JSON 배열):"""


def genQueries(client: genai.Client, row: dict) -> list[str]:
    content = (row.get("section_content") or "")[:2000]
    prompt = DOC2QUERY_PROMPT.format(
        corp_name=row["corp_name"],
        report_nm=row["report_nm"],
        section_title=row.get("section_title", "") or "",
        content=content,
    )
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": {"type": "ARRAY", "items": {"type": "STRING"}},
                "temperature": 0.3,
            },
        )
        questions = json.loads(resp.text)
        return [q.strip() for q in questions if q.strip()][:5]
    except Exception as e:
        print(f"  ! err: {e}")
        return []


# ── 3. 인덱스 빌드 ──


def buildIndex(docs: list[dict], *, use_doc2query: bool, doc_queries: dict[str, list[str]]) -> dict:
    """stem → docId set 역인덱스."""
    inv: dict[str, set[int]] = defaultdict(set)
    for did, d in enumerate(docs):
        text = f"{d['report_nm']} {d.get('section_title') or ''} {(d.get('section_content') or '')[:2000]}"
        toks = tokenize(text)
        if use_doc2query:
            for q in doc_queries.get(d["rcept_no"], []):
                toks |= tokenize(q)
        for t in toks:
            inv[t].add(did)
    return inv


def search(inv: dict, docs: list[dict], query: str, top_k: int = 10) -> list[tuple[int, dict, int]]:
    """쿼리 토큰화 → docId 점수 (= 매칭된 토큰 수) → top-k."""
    qtoks = tokenize(query)
    score: dict[int, int] = defaultdict(int)
    for t in qtoks:
        for did in inv.get(t, ()):
            score[did] += 1
    ranked = sorted(score.items(), key=lambda x: -x[1])[:top_k]
    return [(did, docs[did], s) for did, s in ranked]


# ── 4. 메인 ──


def main() -> None:
    print("=" * 72)
    print("doc2query SOTA 실험")
    print("=" * 72)

    sample = loadSample(100)
    docs = sample.to_dicts()

    # Gemini 클라이언트
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        # .env load
        from pathlib import Path

        for line in Path(".env").read_text().splitlines():
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip()
                os.environ["GEMINI_API_KEY"] = key
                break
    client = genai.Client(api_key=key)

    # 질문 생성
    print()
    print(f"질문 생성: {len(docs)} 공시 × 5 질문 = {len(docs) * 5} 질문")
    doc_queries: dict[str, list[str]] = {}
    t0 = time.time()
    for i, d in enumerate(docs, 1):
        qs = genQueries(client, d)
        doc_queries[d["rcept_no"]] = qs
        if i % 10 == 0:
            elapsed = time.time() - t0
            print(f"  [{i}/{len(docs)}] {elapsed:.0f}s")
    elapsed = time.time() - t0
    print(f"질문 생성 완료: {elapsed:.0f}s")

    # 인덱스 두 종
    inv_base = buildIndex(docs, use_doc2query=False, doc_queries=doc_queries)
    inv_d2q = buildIndex(docs, use_doc2query=True, doc_queries=doc_queries)
    print("\n인덱스 stem 수:")
    print(f"  baseline: {len(inv_base):,}")
    print(f"  doc2query: {len(inv_d2q):,} (+{len(inv_d2q) - len(inv_base):,})")

    # 테스트 쿼리 — *원 텍스트에 없을* 의미 쿼리
    test_queries = [
        "회사가 돈 빌렸나",
        "경영진이 바뀌었나",
        "자사주 사들였나",
        "큰 주주가 바뀌었나",
        "공장 새로 짓나",
        "이사회 누가 사표 냈나",
        "주주총회 결과는",
        "회사 합병하나",
        "신규 사업 시작했나",
        "특허 분쟁 있나",
    ]

    print()
    print("─── 의미 검색 비교 ───")
    print()
    for q in test_queries:
        base_hits = search(inv_base, docs, q, top_k=5)
        d2q_hits = search(inv_d2q, docs, q, top_k=5)

        print(f'❓ "{q}"')
        print(f"  baseline   {len(base_hits)} hits:")
        for did, d, s in base_hits[:3]:
            print(f"    s={s:2d}  [{d['report_nm'][:30]}] {d['corp_name']}")
        print(f"  doc2query  {len(d2q_hits)} hits:")
        for did, d, s in d2q_hits[:3]:
            print(f"    s={s:2d}  [{d['report_nm'][:30]}] {d['corp_name']}")
        print()

    # 결과 저장
    out = Path("data/_scratch_fm/doc2query.json")
    out.write_text(json.dumps(doc_queries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"질문 저장: {out}")


if __name__ == "__main__":
    main()
