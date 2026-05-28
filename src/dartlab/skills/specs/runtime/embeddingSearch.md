---
id: runtime.embeddingSearch
title: Embedding Search — provider/protocol 등록
kind: curated
scope: builtin
status: drafted
category: runtime
purpose: embedding provider 등록 패턴 + cosine similarity search SSOT. **status=drafted — providers/embeddingProvider.py 코드 미신설 (Phase 3.B A-track)**. 본 spec 은 코드 작성 시 따를 표준 인터페이스.
whenToUse:
  - embedding search
  - semantic search
  - cosine similarity
  - embedding provider
  - vector search
inputs:
  - text (query 또는 document chunk)
  - provider config (Anthropic / local)
outputs:
  - embedding vector (np.array)
  - top-k similarity results
toolRefs: []
knowledgeRefs:
  - runtime.ragPipeline
  - runtime.toolComposition
sourceRefs:
  - dartlab://skills/runtime.embeddingSearch
requiredEvidence:
  - skillRef
  - executionRef
runtimeCompatibility:
  server:
    status: limited
  localPython:
    status: limited
  mcp:
    status: limited
  webAi:
    status: limited
  pyodide:
    status: limited
linkedSkills:
  - runtime.ragPipeline
  - runtime.toolComposition
---

## 표준 인터페이스 (코드 작성 시)

```python
class EmbeddingProvider(Protocol):
    def embed(self, text: str | list[str]) -> np.ndarray: ...
    def embed_batch(self, texts: list[str], batch_size: int = 100) -> np.ndarray: ...

class AnthropicEmbeddingProvider:
    """Anthropic embedding API"""

class LocalEmbeddingProvider:
    """Sentence-transformers fallback (의존성 X — numpy direct)"""
```

## 검색 패턴

```python
# 1. embed query
query_vec = provider.embed("HBM 양산")

# 2. cosine similarity vs document corpus
docs = load_section_embeddings()   # gather/sectionEmbedding 출력
scores = (docs @ query_vec) / (np.linalg.norm(docs, axis=1) * np.linalg.norm(query_vec))

# 3. top-k
top_k = np.argsort(scores)[-10:][::-1]
```

## storage

- section_content (dartlab DART 공시) → 한 번 embed → `gather/sectionEmbedding.parquet` cache.
- 갱신: 신규 공시 발견 시 incremental embed.
- 의존성: numpy direct, scipy/sklearn 0.

## 강행 룰

1. provider 단일 SSOT — `providers/embeddingProvider.py`.
2. embedding 결과 외부 본문 시 untrusted wrap (RAG pipeline 적용).
3. cosine similarity 외 다른 metric 사용 시 명시.

## 기본 검증

embed 결과 dim 일관 (Anthropic 1024 / local model 384). batch size 100 기본. cache hit 율 측정.
