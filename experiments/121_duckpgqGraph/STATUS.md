# 121 — DuckPGQ 그래프 쿼리 스파이크

## 실험 목적

`industry.edges` · `hop2.py` · `calcChainPosition` 의 peer 탐색을 DuckDB PGQ (SQL/PGQ) 로 대체했을 때 k-hop · shortest path · centrality 쿼리가 현재 Python 루프 대비 속도/메모리 측면에서 이점이 있는지 검증.

## 배경

- 현재: `industry/edges.json` (6.3MB, ~3k edges) + `nodes.json` (829KB, ~2.7k nodes) 를 Python dict 로 로드, hop2 는 set 확장 루프로 2-hop 계산.
- 실험 089 에서 DuckDB 일반 parquet scan 교체는 **기각** (병목이 SQL pushdown 이 아니라 Python 재구성에 있음). 그래프 쿼리는 별개 — 그래프 알고리즘(k-hop, shortest path, PageRank) 자체가 SQL/PGQ 로 표현되면 Python 루프 제거가 가능하므로 이점이 다르다.

## 가설

1. DuckDB 1.1.3+ + `duckpgq` community extension 이 Windows/Linux 양쪽에서 INSTALL/LOAD 에 성공한다.
2. 18k 엣지 + 2.7k 노드 규모에서 k-hop (k=2, k=3) 쿼리가 5× 이상 빠르다 (Python 루프 대비).
3. shortest path / betweenness (또는 degree centrality fallback) 가 1초 이하에 끝난다.
4. 피크 RSS 가 100MB 이하로 유지된다.

## 방법

1. `uv run --with duckdb --with psutil python -X utf8 001_spike.py` 로 실행 (inline 의존성).
2. INSTALL/LOAD duckpgq 시도 → 실패 시 fallback: 재귀 CTE + JOIN 으로 k-hop 구현 후 비교.
3. 데이터 로드: `edges.json` / `nodes.json` → DuckDB 테이블.
4. 쿼리 시나리오:
   - k=1 suppliers of "005930" (삼성전자)
   - k=2 suppliers (MATCH ... 1..2)
   - shortest path ("005930" → "000660" SK하이닉스) if exists
   - degree centrality — semiconductor 산업 내 entry/exit degree
5. 각 쿼리 wall clock 과 peak RSS 기록.
6. Python baseline: 같은 쿼리를 set expansion 으로 직접 구현해 대조.

## 결과 (2026-04-23 실행 완료)

- **duckpgq INSTALL**: 실패. Windows amd64 용 community extension 바이너리가 DuckDB 1.5.2 에서 404 (미빌드). Candidate extensions: ducklake, odbc, uc_catalog, autocomplete, md — duckpgq 없음.
- **k-hop latency** (삼성전자 기준):

  | 쿼리 | Python set expansion | DuckDB 재귀 CTE | 비율 |
  |---|---|---|---|
  | 1-hop | 10.9 ms | 18.3 ms | 1.7× 느림 |
  | 2-hop | 9.8 ms | 30.8 ms | 3.1× 느림 |
  | 3-hop | 9.5 ms | 44.4 ms | 4.7× 느림 |

- **degree centrality (semiconductor)**: Python 1.9 ms vs DuckDB SQL GROUP BY 3.9 ms. 2× 느림.
- **피크 RSS**: Python 46 MB, DuckDB 로드 후 170 MB (+124 MB 오버헤드, 테이블 로드 897 ms).
- **duckpgq 사용 가능**: False.
- 샘플 규모: nodes=2,664 · edges=18,418.

## 결론 (판정)

**NO-GO.**

근거:
1. DuckPGQ 는 Windows 에서 community extension 미빌드 — 개발·CI·사용자 환경 중 절반 실패.
2. 사용 가능한 DuckDB 재귀 CTE 경로도 Python set expansion 대비 1.7~4.7× 느리다. 테이블 로드 오버헤드 (+124 MB RAM, +897 ms) 를 더하면 더 악화.
3. 현재 Python 구현이 18k edges 규모에서 이미 10 ms 이내. 대체 동기 부여 없음.
4. 실험 089 (DuckDB parquet scan 기각) 의 교훈 "병목은 SQL pushdown 이 아니라 Python 재구성에 있다" 가 그래프 쿼리에도 동일 적용.

### 향후 경로

- `industry.paths(fromCode, toCode)` · `industry.centrality(...)` 같은 신규 API 가 필요하면 순수 Python + `networkx` 로 구현. 본 스파이크 결과상 DuckDB/DuckPGQ 도입 이득 없음.
- 현 단계에서 `industry.edges` / `hop2.py` 교체 불필요.
- DuckPGQ / DuckDB 기반 그래프 쿼리 도입은 본 실험 근거로 기각.

## 실험일

2026-04-23 — 결과 기록 완료.

