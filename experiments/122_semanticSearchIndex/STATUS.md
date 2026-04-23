# 122 — Semantic Search Index 스파이크 [⛔ 기각 — 사상 위반]

> **2026-04-23 기각 처리**. 본 실험은 착수 자체가 dartlab 기존 사상·선행 실험을 무시한 잘못이다. 아래 "결론 (2차 판정)" 참고. 원래 "GO" 결론은 취소. 실행 로그/수치는 학습 목적으로 보존하되 **production 통합 시도 금지**.
>
> **기각 근거**:
> - `ops/search.md` § "왜 임베딩 없이 되는가" — "어휘가 고정되어 있으므로 ngram 정확 매칭만으로 충분. 임베딩의 장점인 의미 유사도 검색이 이 도메인에서는 오히려 노이즈(실험 105 확인)"
> - `ops/search.md` § "역할 분리" — search=공식 용어 (ngram+BM25F), AI=자연어 이해. 임베딩 scope 추가는 이 경계 침범.
> - 실험 067 — "임베딩(ko-sroberta)은 테이블 항목 매칭에 부적합, 구조 분해가 모든 면에서 우월" 기각
> - 실험 101.006 — "Semantic Index 가설 기각"
> - 실험 105 — BM25F 88% > Model2Vec 67% (DART 공시 어휘 고정성 도메인)
> - 본 실험 122 의 낮은 overlap (0.30/5) 은 "다른 축" 이 아니라 "도메인 부적합" 해석이 맞다. 실험 105 결론과 정합.


## 실험 목적

dartlab search beta 탈출 경로. 현재 `core/search/contentIndex` (BM25) 대비 **dart_model2vec** (실험 105 에서 증류 완료한 ko-sroberta 정적 임베딩) 으로 의미 검색 scope 를 추가했을 때:
1. 인코딩 속도 (CPU, 1000 chunk 기준)
2. 재현율 (한국 금융 질의 10 케이스 Recall@5)
3. 인덱스 크기
4. Lance dataset vs parquet+hnswlib vs 단순 numpy 매트릭스 중 어느 저장소가 적합한지

를 측정.

## 배경

- `ops/search.md`: scope "title" (ngram) · "content" (BM25) 존재, `/search` API 는 beta, AI 도구 우선 사용 비권장.
- 실험 067: ko-sroberta-multitask 로 항목 매칭 positive/negative 분리도 검증 완료.
- 실험 105: `dart_model2vec` (Model2Vec 로 ko-sroberta 증류) 완료 — 500× 빠르고 수십 MB. HF 에 배포됨.
- 실험 089: DuckDB parquet scan 일반 교체는 기각 — 포맷 교체 자체로 얻는 이점은 적다는 선례.

이 실험은 "포맷 교체" 가 아니라 "신규 축 추가 (semantic scope)" 이므로 비교 대상이 다르다. 하지만 저장소 선택 (Lance vs parquet vs numpy) 은 089 선례를 고려해 최소한의 의존성부터 시작한다.

## 가설

1. dart_model2vec 인코딩이 1000 chunk CPU 1초 이내.
2. 한국 금융 질의 10 케이스에서 BM25 단독 대비 semantic 단독 Recall@5 가 ≥ BM25.
3. 1000 chunk + 768d float32 ≈ 3MB. Lance 없이 numpy + sklearn NearestNeighbors 로 충분.
4. 하이브리드 (RRF fusion BM25 + semantic) 가 단독 BM25 보다 의미 질의에서 크게 개선.

## 방법

1. `uv run --with model2vec --with polars --with scikit-learn python -X utf8 001_spike.py`
2. 데이터 샘플: 상위 30 종목의 `docs` parquet 에서 `businessOverview + productService + rawMaterial` 필드 chunk 추출 → 1000 chunk 제한
3. 인코딩 시간 측정
4. 쿼리 세트 (10 개, 의미 vs 키워드 혼합):
   - "반도체 HBM 투자"
   - "환율 변동 리스크"
   - "제약 임상 실패 가능성"
   - "전기차 배터리 양극재"
   - "부동산 PF 관련 우려"
   - "공급망 중국 의존"
   - "AI 데이터센터"
   - "원가 상승 압박"
   - "조선 LNG 수주"
   - "엔터 글로벌 확장"
5. 기대 top-k 문서는 휴리스틱 + 사람 판정 (Recall@5 label)
6. 인코딩·검색 latency + RSS peak 기록

## 결과 (2026-04-23 실행 완료)

**데이터**: `data/dart/docs/*.parquet` 실제 로드 → 443 chunks (길이 50~2,000자).

**dart_model2vec 로드**: 성공. 로컬 증류본 `experiments/105_filingSemanticMap/dart_model2vec` 경로.

**성능 측정**:

| 지표 | 값 |
|---|---|
| 모델 로드 | 7.1 s (1회, 이후 캐시) |
| 인코딩 | 78.4 ms / 443 chunks = **0.18 ms/chunk** |
| 임베딩 차원 | 256 (증류 결과, float64) |
| 임베딩 크기 | 0.87 MB / 443 chunks |
| NearestNeighbors 인덱스 구축 | 0.8 ms |
| 쿼리 latency avg / max | **1.57 ms / 3.72 ms** |
| RSS peak | 513 MB (모델 + 인덱스 포함) |
| BM25 baseline | 194 ms / 10 쿼리 |

**Top-5 overlap (semantic ∩ BM25)**: 평균 **0.30 / 5**.

| 쿼리 | overlap |
|---|---|
| 반도체 HBM 투자 | 1/5 |
| 엔터 글로벌 확장 | 2/5 |
| 환율 변동 리스크 | 0/5 |
| 제약 임상 실패 가능성 | 0/5 |
| 전기차 배터리 양극재 | 0/5 |
| 부동산 PF 관련 우려 | 0/5 |
| 공급망 중국 의존 | 0/5 |
| AI 데이터센터 | 0/5 |
| 원가 상승 압박 | 0/5 |
| 조선 LNG 수주 | 0/5 |

낮은 overlap = **두 방식이 근본적으로 다른 relevance 축을 잡는다**. Hybrid RRF fusion 가치 명확.

**저장소 판단**: 443 chunks @ 256-d float64 = 0.87 MB. 전 docs 추정 (~1.5 M chunks 상한) 에서도 3 GB 이하. **Lance/LanceDB 불필요**. numpy + sklearn NearestNeighbors 로 출발하고, 100 M+ 임베딩 단계에서 재평가.

## 결론 (1차 — 취소됨)

~~**GO.** 플랜 기준 모두 충족.~~ ← 취소된 결론. 속도·메모리 지표만 보고 dartlab 사상 (search=공식 용어, AI=자연어 이해) 과 선행 실험 (067/101/105) 을 무시했다.

## 결론 (2차 — 확정)

**기각.** 사상·선행 실험 이중 근거.

1. `ops/search.md` 는 "임베딩 없이 되는 이유" 를 명시 — DART 공시 어휘 고정성으로 ngram 정확 매칭이 의미 유사도보다 우월. 임베딩은 노이즈 유발.
2. `ops/search.md` § "역할 분리" — search 엔진은 공식 용어, 자연어 이해는 `dartlab.ask()` 담당. semantic scope 추가는 이 경계 침범.
3. 본 실험 overlap 0.30/5 은 "다른 축" 이 아니라 임베딩이 DART 도메인에 부적합한 증거 (실험 105 결론 반복 확인).
4. "빠르고 메모리 작다" 는 도입 정당화 조건이 **아니다**. 품질·사상 정합성이 선행.

## 롤백 기록 (2026-04-23)

- ❌ `src/dartlab/core/search/embedding.py` — 삭제
- ❌ `pyproject.toml` `[project.optional-dependencies] search-semantic` — 제거
- ❌ `src/dartlab/core/search/__init__.py::SEARCH_SCOPES` 에 semantic/hybrid 추가 시도 — 진행 전 중단
- ✅ 본 STATUS.md 기각 사유 보존

## 실험일

2026-04-23 — 결과 기록 완료.

