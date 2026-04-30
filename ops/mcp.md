# MCP

**주체**: MCP 서버 (`dartlab.mcp` — stdio · SSE 전송으로 MCP 호환 실행 환경에 dartlab 엔진 노출).
**현재**: `python -m dartlab.mcp` stdio 서버 + SSE ASGI 앱 + `.mcp.json` 자동 설치 헬퍼 + workspace 7 tools + Intelligence Pack/Map/Analysis Graph 리소스. VSCode 확장이 활성화 시 `.mcp.json` 에 자동 등록.
**방향**: 외부 실행 환경도 `inspect → compute → verify → answer` 흐름을 따르게 하고, 엔진별 도구는 compatibility 표면으로 유지.

MCP (Model Context Protocol) 는 MCP 호환 실행 환경이 dartlab 엔진을 도구로 호출하도록 하는 표준 전송 계층. `dartlab.ask` 내부 tool 체계와 **독립된 L4 표현층** — 원천 (Python API + docstring + Analysis Graph) 은 공유하지만 전송·직렬화·결과 포맷은 MCP 규격에 맞게 별도.

각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 1. 한눈에 보기

| 항목 | 내용 |
|---|---|
| 레이어 | L4 (표현) — `vscode/` 와 동등 |
| 진입점 | `python -m dartlab.mcp` (stdio) · `dartlab.mcp.create_sse_app()` (SSE) |
| 도구 | workspace 7 tools + Intelligence Pack/Map/API discovery + compatibility 엔진 도구 |
| 리소스 | `dartlab://info` · `dartlab://intelligence-pack` · `dartlab://intelligence-map` · `dartlab://graph` · `dartlab://graph/status` · `dartlab://scan/{axis}` · `dartlab://macro/{axis}` · `dartlab://company/{code}/topics` |
| 의존성 | `mcp[cli]>=1.0` (`pyproject.toml` 기본 의존) |
| 상태 | 서버 안정 · 문서화 이 문서로 착수 |

---

## 2. 설치 — `.mcp.json` 에 dartlab 서버를 등록한다

사용자가 MCP 호환 실행 환경에서 dartlab 을 쓰려면 `.mcp.json` 에 서버를 등록한다.

### 자동 설치 (프로젝트 루트에서)

```bash
dartlab mcp --install
# → 현재 디렉토리에 .mcp.json 생성 또는 "dartlab" 서버 항목 추가
```

### 수동 설정 (`.mcp.json`)

```json
{
  "mcpServers": {
    "dartlab": {
      "command": "uv",
      "args": ["run", "python", "-X", "utf8", "-m", "dartlab.mcp"]
    }
  }
}
```

`uv` 가 없는 환경이면 `"command": "python", "args": ["-X", "utf8", "-m", "dartlab.mcp"]` 도 가능.

---

## 3. 실행 경로

```
MCP 호환 실행 환경
    ↓ stdio JSON-RPC
python -m dartlab.mcp
    ↓ asyncio.run(run_stdio)
mcp.server.stdio.stdio_server
    ↓ MCP SDK (Server, Tool, Resource)
create_server()
    ├─ list_tools  → workspace tools + Intelligence Pack/Map + generated compatibility tools
    ├─ call_tool   → _executeTool → dartlab 엔진 호출 (Company, scan, macro, gather, search)
    └─ read_resource → dartlab://{scheme}/{path}
```

### SSE 모드 (HTTP)

웹 배포나 원격 브릿지가 필요하면 SSE 앱을 직접 실행하거나 FastAPI 에 마운트:

```python
from dartlab.mcp import create_sse_app

app = create_sse_app()   # Starlette ASGI — /sse (SSE endpoint) + /messages/ (POST)
# 또는
from dartlab.mcp import run_sse
run_sse(host="127.0.0.1", port=8001)
```

---

## 4. 도구 체계 — 기본 표면은 workspace agent다

MCP의 기본 추천 표면은 `workspace_status`, `read_text`, `inspect_data`, `run_python`, `search_workspace`, `create_artifact`, `finalize_answer` 7개다. 외부 실행 환경도 엔진 함수명을 먼저 맞히는 대신 Intelligence Pack으로 환경을 보고, 데이터를 inspect하고, `run_python`에서 DartLab 라이브러리를 써서 계산한 뒤 `finalize_answer`로 검산한다.

엔진별 MCP 도구 목록은 compatibility다. 이 목록은 `scripts/build/generateSpec.py` 가 dartlab 공개 API 의 시그니처 + 독스트링을 읽어 `src/dartlab/mcp/_generated_tools.py` 를 재생성한다. 수정이 필요하면 원본 함수의 시그니처·독스트링을 고치고 `generateSpec` 을 재실행한다.

### 도구 카테고리

| 카테고리 | 도구 | 설명 |
|---|---|---|
| 빠른 판단 | `companyInsights` | 7 영역 등급 + 투자 프로파일. 분석 시작 시 먼저 쓰는 도구 |
| 종목 조회 | `searchCompany` | 종목코드 (005930) · 회사명 (삼성전자) · 부분검색 |
| 원본 데이터 | `companyFinancials` · `companyRatios` · `companyShow` · `companyTopics` · `companyProfile` · `companyFilings` · `companyDiff` | IS·BS·CF 원본, 비율, 토픽 |
| 심층 분석 | `companyAnalysis` · `companyValuation` · `companyForecast` | 14 축 재무 + 밸류에이션 + 매출예측 |
| 신용·지배구조 | `companyCredit` · `companyGovernance` · `companyAudit` | 등급·사외이사·감사 리스크 |
| 시장·거시 | `marketScan` · `macroAnalysis` · `gatherData` · `topdownScreen` | 전종목 횡단 · 매크로 · 외부 데이터 · 탑다운 스크린 |
| 기술적 분석 | `quantAnalysis` · `companyQuant` · `companyGather` | 지표·변동성·수급 |
| 검색·카탈로그 | `dartlabSearch` · `dartlabListing` | 공시 원문 · 카탈로그 |
| 보고서 | `companyStory` | 정리된 보고서 (사용자 명시 요청 시) |
| API Discovery | `listDartlabApi` · `searchDartlabApi` · `verifyDartlabApi` | 런타임 introspection — MCP 실행 환경이 dartlab API 를 메타 조회 |
| Analysis Graph | `contextForQuestion` · `queryAnalysisGraph` · `impactForGraphNode` · `explainDartlabTool` | 질문별 route/contract/tool/evidence/visual 요구사항 조회 |
| Process Map | `planDartlabQuestion` · `validateDartlabPlan` · `listDartlabProcesses` | 질문 유형별 requiredTools/evidence/artifact/visual/freshness/acceptance 계약 조회 |
| Intelligence Pack/Map | `describeDartlabIntelligencePack` · `describeDartlabIntelligenceMap` | generated Pack 원문과 workspace agent가 보는 API/Data/Graph/Process/Recipe 요약 |

### 리소스 (`read_resource`)

MCP 클라이언트가 능동적으로 구독 가능한 URI:

| URI | 내용 |
|---|---|
| `dartlab://info` | 버전 · 도구 수 · 현재 캐시된 종목코드 |
| `dartlab://intelligence-pack` | generated Intelligence Pack 원문 |
| `dartlab://intelligence-map` | Financial Workspace Agent가 소비하는 API/Data/Graph/Process/Recipe 요약 |
| `dartlab://graph` | Analysis Graph 전체 payload |
| `dartlab://graph/status` | graphVersion · sourceHash · node/edge/contract/route 요약 |
| `dartlab://graph/{kind}/{id}` | 특정 graph node 와 인접 edge |
| `dartlab://scan/{axis}` | `profitability` · `growth` 등 전종목 횡단 분석 결과 |
| `dartlab://macro/{axis}` | `종합` · `사이클` 등 매크로 스냅샷 |
| `dartlab://company/{code}/topics` | 해당 종목에서 `companyShow` 로 조회 가능한 토픽 목록 |

캐시에 로드된 Company 는 런타임에 `company/{code}/topics` 리소스로 자동 노출.

**반복 실패** — `_generated_tools.py` 를 수동 수정 → generateSpec 재실행 시 덮어써서 사라짐. 원본 함수 시그니처·독스트링에서 고친다.

### Process Map 소비

MCP 도구도 AI runtime 과 같은 Process Map 을 소비한다. `planDartlabQuestion` 은 질문에 맞는 계약 후보를 짧은 구조로 보여주고, `validateDartlabPlan` 은 제안된 도구가 `requiredTools`, `requiredEvidence`, `requiredArtifacts`, `requiredVisuals`, `freshness`, `acceptanceCriteria` 를 충족할 수 있는지 검증한다.

Workspace-native 경로는 MCP 의 기본 추천 표면이다. 외부 실행 환경도 엔진 함수 수십 개를 먼저 맞히는 대신 `workspace_status → search_workspace/read_text/inspect_data → run_python → create_artifact → finalize_answer` 흐름을 쓴다. `workspace_status`와 `search_workspace`는 Pack을 먼저 보고, 없거나 stale이면 runtime fallback을 쓴다. 이 7개 tool 은 `/api/ask` 내부 agent 와 같은 구현을 소비한다. 기존 엔진별 MCP tool 은 호환용으로 유지하지만 새 품질 규칙이나 질문별 예외를 거기에 추가하지 않는다.

| Workspace agent tool | MCP 역할 |
|---|---|
| `workspace_status` | 환경·data root·공통 데이터 위치 확인 |
| `read_text` | ops/source/docstring 읽기 |
| `inspect_data` | 데이터 schema/latest/head/tail 확인 |
| `run_python` | DartLab/Polars 계산 실행 |
| `search_workspace` | 문서·소스·capabilities·데이터 검색 |
| `create_artifact` | CSV/JSON/visual 산출 |
| `finalize_answer` | 검증된 최종 답변 제출 |

MCP 경로에서 별도 지식 그래프나 수동 planner 를 만들지 않는다. 외부 실행 환경이 dartlab 을 이해해야 할 때도 원천은 Python API docstring/capabilities/AIContract 이며, `generateSpec.py` 가 만든 Intelligence Pack과 generated graph만 공식 표면이다.

---

## 5. AI tool 과의 관계 — 독립 registry, 공유 원천

| 축 | `dartlab.ask` 내부 AI tool | MCP 도구 |
|---|---|---|
| 생성 시점 | 런타임 (`buildTools()` 매 호출) | 빌드 타임 (`_generated_tools.py`) |
| 스키마 원천 | `inspect.signature` + docstring + CAPABILITIES | `scripts/build/generateSpec.py` 에서 동일 원천 읽어 JSON 고정 |
| 결과 포맷 | `ToolResponse` (`llmText` · `uiData` · `dataAsOf`) | MCP `TextContent` (문자열만, 12,000 자 상한) |
| 사용 주체 | dartlab AI 엔진 (`ask`) | MCP 호환 실행 환경 |
| 블랙리스트 | `ai/tools/__init__.py::_BLACKLIST` (`setup` · Company class 등 제외) | 자동 생성 대상 중 비분석·고위험 API 제외 |

**공통**: Python 함수 시그니처와 독스트링이 단일 진실의 원천. 한쪽만 갱신하지 않고 `generateSpec.py` 로 양쪽 재생성.

---

## 6. 운영 원칙

### 결과 크기 상한 — 12,000 자에서 자른다

MCP 실행 컨텍스트 절약을 위해 도구 결과 문자열은 `_MCP_MAX_RESULT_CHARS = 12000` 로 잘라낸다 (초과 시 "결과 잘림, 전체 N 자. 범위를 좁혀 재조회하세요" 안내 포함). AI tool 의 `ToolResponse` 와 다른 이유 — MCP 경로는 스트리밍 지원이 환경마다 다르고 단일 응답이 너무 크면 tool loop 가 깨진다.

### Company 캐시

- 상한 5 인스턴스 · TTL 10 분 (`_CACHE_MAX` · `_CACHE_TTL`).
- LRU 정책. 새 종목 로드 시 가장 오래된 항목 제거.
- Company 로딩 자체가 수초 걸리므로 같은 종목 반복 질의에 유효.

### 에러 처리

`_executeTool` 는 모든 엔진 예외를 잡고 `dartlab.core.desk.guide.handleError(e, feature=...)` 로 친절 메시지 생성. 사용자에게 "데이터 없음 → gather 먼저 수집하세요" 같은 해결책이 포함된 응답을 돌려준다 (프로젝트 사용자 편의 원칙).

### 블랙리스트

MCP 에 노출하지 않는 도구:
- `ask` · `Company` · `setup` · `collect` · `config` 등 비분석 API.
- legacy `pythonExec` (AI legacy loop 전용). Workspace-native MCP 는 `run_python` 을 권한 프로파일로 제한해 쓴다.
- `companySections` (전체 sections 지도는 메모리 부담이 크다. `companyTopics` → `companyShow(topic)` 또는 분석/공시 경량 도구를 사용한다).

### 로깅

- `logging.getLogger("dartlab.mcp")` 가 stderr 로 INFO 레벨 출력.
- 도구 호출·Company 로딩·에러 모두 기록.
- stdio 전송은 stdout 을 JSON-RPC 로 점유하므로 진단 로그는 반드시 stderr.

**반복 실패** — stdio 전송에서 stdout 에 `print()` 찍으면 JSON-RPC 파싱 깨짐. 로그는 stderr 고정.

---

## 7. VSCode 확장과의 연계

VSCode 확장 활성화 시 작업 공간 루트의 `.mcp.json` 과 `.vscode/mcp.json` 에 dartlab MCP 서버를 자동 등록한다 (`ops/vscode.md` §MCP 자동 등록). 결과적으로 같은 workspace 를 쓰는 MCP 호환 실행 환경이 `dartlab` 서버를 바로 인식한다.

---

## 8. 테스트

```bash
bash scripts/dev/test-lock.sh tests/test_mcp.py tests/test_mcp_tools.py -m unit -v
```

커버 범위:
- 도구 정의 구조 (`_TOOLS` · `required` ⊆ `params` · 이름 유일성 · 설명 길이).
- `_TOOL_FEATURE_MAP` 커버리지 (도구 ↔ guide feature 매핑).
- `_fmt` · `_fmtDict` 포맷터.
- MCP SDK 없을 때 `create_server` 가 `ImportError("MCP SDK 필요")` 발생.
- `installMcpConfig` 가 `.mcp.json` 에 dartlab 항목 추가 (기존 설정 보존).

---

## 9. 설치 가이드 — 실행 환경별

### 로컬 workspace

```bash
cd <프로젝트 루트>
dartlab mcp --install
# → ./.mcp.json 생성. MCP 호환 실행 환경이 해당 workspace 를 열 때 자동 인식.
```

### 프로젝트 설정 파일

프로젝트 루트의 `.mcp.json` 만 있으면 자동 인식. 없으면 `dartlab mcp --install` 실행.

### 원격 SSE

```bash
uv run python -c "from dartlab.mcp import run_sse; run_sse(host='0.0.0.0', port=8001)"
```

클라이언트 설정:

```json
{
  "mcpServers": {
    "dartlab-remote": {
      "url": "http://your-host:8001/sse"
    }
  }
}
```

---

## 관련 코드

| 경로 | 역할 |
|---|---|
| `src/dartlab/mcp/__init__.py` | 서버 구성 · `_executeTool` · `create_server` · `run_stdio` · `run_sse` · `installMcpConfig` |
| `src/dartlab/mcp/__main__.py` | `python -m dartlab.mcp` 진입점 |
| `src/dartlab/mcp/_generated_tools.py` | `_TOOLS` · `TOOL_FEATURE_MAP` (`generateSpec.py` 자동 생성, 수동 수정 금지) |
| `scripts/build/generateSpec.py` | 공개 API → CAPABILITIES · `_generated_tools.py` · `llms.txt` · 스킬 reference · Intelligence Pack 재생성 |
| `src/dartlab/cli/` | `dartlab mcp --install` CLI 진입 |
| `src/dartlab/ai/tools/__init__.py` | AI tool auto discovery (MCP 와 원천 공유) |
| `tests/test_mcp.py` · `tests/test_mcp_tools.py` | 단위 테스트 |
| `ui/vscode/src/extension.ts` | VSCode 확장 활성화 시 `.mcp.json` 자동 등록 |

---

## 관련 문서

- [ops/ai.md](ai.md) — AI 엔진 4 축 + 8+1 원칙 (MCP 도구 설계의 사상 원천).
- [ops/vscode.md](vscode.md) — VSCode 확장 MCP 자동 등록 + stdio 프로토콜.
- [ops/code.md](code.md) — 독스트링 9 섹션 + CAPABILITIES 자동 생성 규약.
- [ops/api-contract.md](api-contract.md) — 공개 API 계약 (MCP 가 노출하는 표면의 원칙).

---

## 요약 — 명제 8 줄

1. MCP 서버는 MCP 호환 실행 환경에 dartlab 엔진을 노출하는 L4 표현층, `ask` 내부 AI tool 과 독립.
2. 설치는 `dartlab mcp --install` → `.mcp.json` 자동 생성 또는 수동 설정 블록 추가.
3. 전송 2 경로 — stdio (`python -m dartlab.mcp`) + SSE (`create_sse_app()` Starlette ASGI).
4. 엔진 도구 + API discovery + Intelligence Pack/Analysis Graph/Process Map 도구, SSOT 는 Python API · docstring · capabilities · AIContract → `generateSpec.py` 자동 생성.
5. 결과는 12,000 자에서 잘라내고 "범위 좁혀 재조회" 안내, Company 캐시 5 개 × 10 분.
6. 에러는 `handleError(feature=...)` 로 친절 메시지, stdio 로그는 stderr (stdout JSON-RPC 점유).
7. 블랙리스트 — `ask` · Company class · `setup` · `collect` · `pythonExec` (보안 리스크).
8. VSCode 확장이 activation 시 `.mcp.json` · `.vscode/mcp.json` 자동 등록 → MCP 호환 실행 환경이 즉시 인식.
