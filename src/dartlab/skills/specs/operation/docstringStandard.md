---
id: operation.docstringStandard
title: capability docstring 의 LLM Specifications 섹션 표준
category: operation
kind: curated
scope: builtin
status: unverified
purpose: capability docstring 에 LLM 친화 메타 (AntiPatterns / OutputSchema / Prerequisites / Freshness / Dataflow / TargetMarkets) 6 sub-key 표준 정의. 사람용 (Capabilities / Args / Returns / Example) 과 분리해 LLM 비교 선택 정확도를 높인다.
whenToUse:
  - capability docstring 작성
  - 새 함수 추가 후 LLM 메타 보강
  - docstring 표준 확인
  - 사람용/LLM용 분리 설계
  - mcp tool description 자동 생성 입력
linkedSkills:
  - operation.code
  - operation.apiContract
toolRefs:
  - read
  - ReadCapability
requiredEvidence:
  - skillRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: supported
lastUpdated: '2026-05-06'
---

## 목적

capability docstring 은 두 독자 — 사람 (개발자·기여자) + LLM (자동화 에이전트) — 를 위해 작성된다. 두 독자의 정보 욕구가 다르다.

**사람용** (기존):
- `Capabilities:` — 무엇을 할 수 있나
- `Args:` — 파라미터 의미
- `Returns:` — 반환 타입과 구조
- `Example::` — 실행 예시
- `Guide:` — 자연어 질문 ↔ 함수 호출 매핑
- `SeeAlso:` — 관련 함수
- `Requires:` — 필요 조건 (API 키, 데이터)
- `AIContext:` — LLM 시나리오 짧은 멘션

**LLM용** (신규 — 본 표준):
- `## LLM Specifications` 섹션 안 6 sub-key
- 사람이 읽기 어려운 형식 OK (LLM 비교 선택용 메타)
- `ReadCapability` payload 와 `mcp` tool description 자동 생성에 직접 사용

두 영역은 같은 docstring 안에 공존. SSOT 분리 X — 한 곳에서 두 독자를 모두 지원.

## 6 sub-keys

### AntiPatterns (필수)
**LLM 이 흔히 저지르는 오용 1~3 개**. bullet list 형식.

```
AntiPatterns:
    - 분기 데이터인데 monthly average 비교
    - 한국 회사에 미국 GAAP 가정
    - axis="all" 같은 미지원 값 (price/flow/macro/news 만)
```

### OutputSchema (필수, DataFrame 반환 함수 한정)
**반환 컬럼명 + dtype + 단위**. bullet list 형식. 한국어 컬럼명 그대로 명시.

```
OutputSchema:
    - 자산총계 : float — BS 자산 총계 (원)
    - snakeId : str — 영문 snake_case 계정 식별자
    - 2025Q4, 2025Q3, ... : float — 분기 값 (원 단위)
```

### Prerequisites (선택)
**호출 전 필요한 사전 단계**. dict 호출, 데이터 수집 의존 등. bullet 형식.

```
Prerequisites:
    - Company.gather('price') 우선 호출
    - DART_API_KEY 환경변수
```

### Freshness (필수)
**데이터 갱신 주기·기준 시점**. 한 줄 또는 짧은 문단.

```
Freshness:
    분기 마감 후 45일 (DART 공시 마감일). c.update() 로 증분 갱신.
```

### Dataflow (선택)
**다른 함수와의 호출 순서·의존**. 화살표 표기.

```
Dataflow:
    gather(raw) → finance(시계열) → ratios(파생)
    disclosure(목록) → readFiling(원문)
```

### TargetMarkets (선택)
**지원하는 시장**. bullet 형식.

```
TargetMarkets:
    - KR (DART)
    - US (EDGAR)
```

## 작성 예시

`src/dartlab/providers/dart/company.py` ([GitHub](https://github.com/eddmpython/dartlab/blob/master/src/dartlab/providers/dart/company.py)) 의 `_showImpl` docstring 끝부분:

```
LLM Specifications:
    AntiPatterns:
        - 분기 컬럼명을 "Q4_2025" 로 추측 (실제는 "2025Q4")
        - freq="M" 같은 미지원 값 (Q/Y/YTD 만)
        - finance topic 에 raw=True 후 비율 계산 (정제 단계 누락)
    OutputSchema:
        - snakeId : str — 영문 snake_case 계정 식별자 (finance 한정)
        - 항목 : str — 한글 계정명
        - 2025Q4, 2025Q3, ... : float — 분기 값 (원 단위, freq="Q" 기본)
        - 2025, 2024, ... : float — 연간 합산 (원 단위, freq="Y")
    Freshness:
        분기 마감 후 45일 (DART 공시 마감일). c.update() 로 증분 갱신.
```

## 검증

`src/dartlab/skills/generateSpec.py` ([GitHub](https://github.com/eddmpython/dartlab/blob/master/src/dartlab/skills/generateSpec.py)) 의 `_parseDocstringSections` 가 `## LLM Specifications` 또는 `LLM Specifications:` 헤더를 인식해 `_parseLLMSpecs(value)` 로 sub-key 6 종 (AntiPatterns / OutputSchema / Prerequisites / Freshness / Dataflow / TargetMarkets) 추출 → `entry["llmSpecs"]` 에 박힌다. 이 `llmSpecs` 는:

- `dartlab/core/capability/_generated.py` 의 capability catalog
- `dartlab.ai.tools.readCapability.readCapability(...)` 의 payload
- `dartlab/mcp/_generated_tools.py` 의 mcp tool description 일부 (자동 생성)

세 곳에서 동시에 사용된다. 한 docstring 변경 → `uv run python -X utf8 src/dartlab/skills/generateSpec.py` 재실행 → 세 산출물 동기 갱신.

## 진행 페이스

전체 200+ capability 의 LLM Specifications 일괄 갱신은 1 회 작업으로 강행 X. 운영자가 손대는 capability 에서 자연 누적. 우선 채울 후보:

- Company 핵심 10 메서드 (show / analysis / disclosure / filings / readFiling / sections / gather / update / credit / quant) — **현재 완료**
- 자주 호출되는 dartlab.* 모듈 함수 (scan / macro / search / capabilities)
- ratios / debt / capital / governance 같은 _scanRelated 메서드

## 무엇을 하지 않는가

- Capabilities/Args/Returns/Example 같은 사람용 섹션 제거 — **금지**. 두 독자 영역 공존.
- LLM Specifications 섹션 안에 sub-key 6 외 임의 키 추가 — generateSpec.py parser 가 인식 못 함.
- 자동 생성 — capability 자체는 docstring 으로 작성, 즉 운영자 수동. parser 가 자동 추출.
