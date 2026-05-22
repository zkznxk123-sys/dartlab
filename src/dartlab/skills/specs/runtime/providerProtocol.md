---
id: runtime.providerProtocol
title: Provider Protocol 동일 surface — 3-regulator drop-in
kind: curated
scope: builtin
status: observed
category: runtime
purpose: dart/edgar/edinet 3 provider 가 만족해야 하는 Protocol 5 종 SSOT 와 새 regulator (SGX·FSA 등) 추가 4 단계 절차를 명시한다. P-PR 트랙의 method-level symmetry baseline 의 기준.
whenToUse:
  - 새 regulator provider 추가 직전
  - dart vs edgar method 비대칭 검증 (`providerSymmetry.json` baseline)
  - CompanyProtocol isinstance 통과 여부 디버깅
  - 3 provider 의 docs / finance / filings namespace 시그니처 정합 확인
inputs:
  - 신규 regulator 명 + 도메인 (예 sgx.com.sg)
  - 기존 Company 클래스 (참조용)
  - "_SYMMETRY_MAP 의 dart_only / edinet_deferred 항목"
outputs:
  - Protocol 만족 isinstance 결과
  - method 비대칭 baseline 갱신본
  - 새 provider 폴더 구조 (10 sub-folder mirror)
capabilityRefs: []
toolRefs: []
knowledgeRefs:
  - operation.architecture
  - operation.code
  - engines.company
sourceRefs:
  - dartlab://skills/runtime.providerProtocol
procedure:
  - 새 regulator 의 도메인·식별자 (CIK·corp_code 등) 체계 정리.
  - "providers/{name}/company.py 의 Company 가 CompanyProtocol 12 method 구현."
  - "providers/{name}/{docs,finance,filings} namespace 가 각 Provider Protocol 구현."
  - "providers/{name}/__init__.py 에 Company + 3 namespace re-export, providers/__init__.py __all__ 추가."
  - "tests/test_providerContract.py baseline 갱신 + providerSymmetry.json 의 _SYMMETRY_MAP 등록."
requiredEvidence:
  - skillRef
  - executionRef
  - sourceRef
expectedOutputs:
  - "3+ provider 모두 isinstance(Company(code), CompanyProtocol) == True"
  - "providerSymmetry.json 의 신규 provider 항목 missing/shallow 카운트"
  - "폴더 mirror 10 sub-folder 통과 (folderMirror.py)"
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: limited
    notes:
      - Pyodide 는 외부 HTTP 호출 제한 — provider 의 fetch 메서드는 fixture 의존만 가능.
failureModes:
  - "__init__.py 에 logic 추가 (룰 4 위반)"
  - "dart-only 한국 특화 메서드를 edgar 에 무리하게 패리티 강제 (예 keywordTrend 미국 시장 부재)"
  - "Protocol 시그니처 미스매치 (예 period keyword 누락) — isinstance 통과 못 함"
forbidden:
  - "본 Protocol 우회한 duck-typing (hasattr 직접 사용) 금지 — isinstance 강제"
  - "Protocol 시그니처 변경 시 3 provider 동시 갱신 누락 금지"
  - "_SYMMETRY_MAP.edinet_deferred 의 5 method 강제 구현 금지 (사용자 명시적 deferred)"
examples:
  - "SGX (싱가포르) provider 추가 시 CompanyProtocol 12 method 구현 후 baseline 갱신"
  - "FSA (UK) provider 추가 시 _SYMMETRY_MAP.rename_map 에 dart_method → fsa_method 매핑 등록"
  - "edinet 의 5 deferred method 가 liveFilings baseline 영구 제외 처리"
source:
  type: curated
  format: markdown
lastUpdated: '2026-05-12'
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## 무엇을 하나

dart · edgar · edinet 3 provider 의 공통 표면을 정의하는 **5 Protocol** SSOT 와 그 SSOT 위에 새 regulator 를 drop-in 으로 얹는 4 단계 절차를 박는다. P-PR 트랙의 method-level symmetry baseline (`providerSymmetry.json`) 의 객관 기준이 본 spec.

## Protocol 5 종 (SSOT 위치)

| Protocol | 위치 | 핵심 메서드 |
|---|---|---|
| `CompanyProtocol` | `src/dartlab/core/protocols.py:69-225` | `__enter__` / `__exit__` / `show` / `select` / `trace` / `diff` / `filings` / `disclosure` / `liveFilings` / `readFiling` / `view` / `quant` / `ask` + `index` / `topics` / `sections` property |
| `DocsProvider` | `src/dartlab/core/protocols.py:366-419` | `fetchFiling(stockCode, *, period)` / `listSections(...)` / `iterSections(...)` |
| `FinanceProvider` | `src/dartlab/core/protocols.py:422-476` | `fetchStatements(...)` / `listAccounts(...)` / `iterAccounts(...)` |
| `FilingsProvider` | `src/dartlab/core/protocols.py:480-513` | `search(query, *, market=None, limit=20)` / `iterSearch(...)` |
| `MemorySafeProvider` | `src/dartlab/core/protocols.py:517-540` | `cleanupCache() -> int` / `memorySnapshot() -> dict[str, int]` |

5 종 모두 `@runtime_checkable` — `isinstance(co, CompanyProtocol)` 가능.

## 새 provider 추가 4 단계

### 1. `providers/{name}/company.py` 의 `Company` 가 `CompanyProtocol` 구현

12 메서드 + 3 property 시그니처 그대로. dart-only 메서드 (`codeName` / `keywordTrend` / `news` / `listing` / `credit` 등 18) 는 본 Protocol 에 없음 — 신규 provider 는 구현 의무 없음.

```python
# providers/sgx/company.py 예시
from dartlab.core.protocols import CompanyProtocol

class Company:  # implements CompanyProtocol structurally
    def __init__(self, stockCode: str) -> None: ...
    def __enter__(self) -> "Company": ...
    def __exit__(self, *_: object) -> None: ...
    # show / select / trace / ... 12 method + 3 property
```

### 2. `providers/{name}/{docs,finance,filings}` namespace 가 각 Provider Protocol 구현

```python
# providers/sgx/docs/__init__.py
from dartlab.core.protocols import DocsProvider, FilingResult, Section

class _SgxDocs:  # implements DocsProvider
    def fetchFiling(self, stockCode: str, *, period: str) -> FilingResult | None: ...
    def listSections(self, stockCode: str, *, period: str) -> list[Section]: ...
    def iterSections(self, stockCode: str, *, period: str) -> Iterator[Section]: ...
```

### 3. `providers/{name}/__init__.py` 에 Company + 3 namespace re-export

```python
"""SGX (싱가포르 거래소) 데이터 소스 엔진."""
from dartlab.providers.sgx import docs, finance, filings
from dartlab.providers.sgx.company import Company

__all__ = ["finance", "docs", "filings", "Company"]
```

`providers/__init__.py` 의 `__all__` 에 `"sgx"` 추가.

### 4. baseline 갱신

- `tests/test_providerContract.py` 의 provider iteration 에 `"sgx"` 추가.
- `tests/audit/_baselines/providerSymmetry.json` 에 신규 provider 항목 등록.
- `tests/audit/providerSymmetry.py` 의 `_SYMMETRY_MAP` 에 SGX-specific rename / dart_only / sgx_deferred 항목 등록.

## 3 provider asymmetry (현 상태)

### dart (한국, 50,855 LoC)
가장 깊은 구현. 한국 시장 특화 18 메서드 보유 — edgar 패리티 대상 아님. `_SYMMETRY_MAP.dart_only` 영구 등록:

| 카테고리 | 메서드 |
|---|---|
| 식별자 | `codeName` / `resolve` / `status` |
| 시장 메타 | `listing` / `industry` |
| 검색 / 뉴스 | `search` / `keywordTrend` / `news` / `publicSentiment` |
| 분석 결합 | `credit` / `marketScan` / `keywordTrend` / `watch` / `story` / `analysis` / `validateStory` |
| 데이터 | `gather` / `table` / `rawDocs` / `rawFinance` / `rawReport` |

### edgar (미국, 15,010 LoC)
P-PR6/7/8 후 dart 패리티 도달. XBRL / 10-K sections / Form 4 / DEF 14A / 8-K — 자체 구현 확장 (외부 `edgartools` 미도입).

### edinet (일본, 2,856 LoC)
**5 method 사용자 명시적 deferred** — `_SYMMETRY_MAP.edinet_deferred` 영구 등록:

- `ask` (LLM 통합)
- `quant` (기술적 분석)
- `disclosure` (공시 검색 확장)
- `liveFilings` (실시간 공시)
- `readFiling` (원문 읽기)

본 5 method 는 EDINET API 한정 차이 + 우선순위 결정. P-PR8 strict 전환 시 baseline 영구 제외.

## 검증

```bash
uv run python -X utf8 -c "
from dartlab.core.protocols import CompanyProtocol
from dartlab.providers import dart, edgar, edinet
for mod, code in [(dart, '005930'), (edgar, 'AAPL'), (edinet, '7203')]:
    co = mod.Company(code)
    assert isinstance(co, CompanyProtocol), f'{mod.__name__}: CompanyProtocol fail'
    print(f'{mod.__name__}: CompanyProtocol OK')
"
```

`tests/test_providerContract.py` 의 `test_company_isinstance_runtime` + `test_provider_namespaces_isinstance` 자동화.

## 폴더 mirror (10 sub-folder)

| 폴더 | 책임 |
|---|---|
| `accessor/` | provider-specific data access (DartClient · SEC API client 등) |
| `builder/` | 캐시 빌더 (filings catalog · finance statements 등) |
| `bulk/` | bulk 적재 (corp_code dump · companyfacts batch 등) |
| `docs/` | 공시 본문 파싱 (`DocsProvider` 구현) |
| `finance/` | 재무제표 정규화 (`FinanceProvider` 구현) |
| `openapi/` | raw HTTP client / API key |
| `ops/` | 운영 유틸 (calendar / disclosure schedule 등) |
| `parse/` | 표·HTML·XBRL 파서 |
| `report/` | 정형 report (옵션) |
| `search/` | 도메인 검색 (`FilingsProvider` 구현) |

누락 폴더는 placeholder `__init__.py` 만 — Protocol contract 만족 위해.

## 다음 단계

- `engines.company` — Company facade 사용법
- `engines.dart` / `engines.edgar` / `engines.edinet` — provider 별 엔진 사용법
- `operation.code` § 11 룰 — 모든 provider 준수 룰
- `operation.architecture` § 3-provider mirror — 아키텍처 SSOT
