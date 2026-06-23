"""데이터 제공자 — DART (한국) · EDGAR (미국 SEC). EDINET (일본 금융청) 은 동결(frozen).

활성 2 regulator (DART·EDGAR) 의 공시·재무·검색을 동일 Protocol surface 로 노출하는 dartlab 의 L1
데이터 계층. **EDINET 은 API 통신 불가로 동결** — `__all__` 에서 제외(미래 API 복구 옵션 보존 위해 코드는
유지). 게이트는 이미 deferred 처리(`providerSymmetry._EDINET_DEFERRED` · `providerContract` strict 제외).
(debt-honesty P2-1)

폴더 mirror 골격 (3 provider 모두 동일):
    accessor / builder / bulk / docs / finance / openapi / ops / parse / report / search

설계 SSOT:
    engines.dart · engines.edgar · engines.edinet (`src/dartlab/skills/specs/engines/`)

11 룰 강행 (`operation.code` SSOT):
    rule 6  docstring 9 섹션 (P-PR2/3 sweep 중)
    rule 8  fetchX(limit=) keyword 의무 — full-df 차단
    rule 9  eager cross-scan 금지 — streaming engine 또는 slim index
    rule 11 Company context manager — `with Company(c) as c:` evict + RSS 회수

메모리·실행 주의:
    Polars 네이티브 힙은 gc 회수 불가 — multi-company loop 시 with block + cleanupCache.
    streaming engine 미지원 연산 (pivot / over / asof) 은 inline `# polars-streaming-unsupported:` 마킹.
    Windows cp949 회피 — 모든 실행은 `uv run python -X utf8`.

새 provider 추가 절차 (`runtime.providerProtocol` SSOT):
    1. `providers/{name}/company.py` 의 `Company` 가 `CompanyProtocol` 구현
    2. `providers/{name}/{docs,finance,filings}` namespace 가 각 Provider Protocol 구현
    3. `providers/{name}/__init__.py` 에 Company + 3 namespace re-export
    4. `providers/__init__.py` `__all__` 에 추가 + `tests/test_providerContract.py` baseline 갱신
"""

# EDINET 은 API 통신 불가로 동결(frozen) — 활성 advertise 에서 제외. 코드(providers/edinet/**)는
# 미래 복구 옵션 보존 위해 유지하되 active provider 가 아니다. 직접 import(dartlab.providers.edinet)는
# 여전히 가능. 게이트는 _EDINET_DEFERRED 로 이미 deferred. (debt-honesty P2-1)
__all__ = ["dart", "edgar"]
