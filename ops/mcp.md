# MCP

**주체**: MCP 서버 (`dartlab.mcp` — stdio · SSE 전송으로 외부 LLM 클라이언트에 dartlab 엔진 노출).
**현재**: `python -m dartlab.mcp` stdio 서버 + SSE ASGI 앱 + `.mcp.json` 자동 설치 헬퍼 + 도구 자동 생성 (`_generated_tools.py`) + Analysis Graph 리소스/도구. VSCode 확장이 활성화 시 `.mcp.json` 에 자동 등록.
**방향**: AI tool 자동 등록과 MCP 도구 목록의 공통 원천 (docstring/Analysis Graph) 공유 폭 확장 · resource URI 체계화 · 외부 클라이언트별 설치 가이드.

MCP (Model Context Protocol) 는 외부 LLM 클라이언트가 dartlab 엔진을 도구로 호출하도록 하는 표준 전송 계층. `dartlab.ask` 내부 tool 체계와 **독립된 L4 표현층** — 원천 (Python API + docstring) 은 공유하지만 전송·직렬화·결과 포맷은 MCP 규격에 맞게 별도.

각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 1. 한눈에 보기

| 항목 | 내용 |
|---|---|
| 레이어 | L4 (표현) — `vscode/` 와 동등 |
| 진입점 | `python -m dartlab.mcp` (stdio) · `dartlab.mcp.create_sse_app()` (SSE) |
| 도구 | 엔진 도구 자동 생성 + API discovery + Analysis Graph 도구 |
| 리소스 | `dartlab://info` · `dartlab://graph` · `dartlab://graph/status` · `dartlab://scan/{axis}` · `dartlab://macro/{axis}` · `dartlab://company/{code}/topics` |
| 의존성 | `mcp[cli]>=1.0` (`pyproject.toml` 기본 의존) |
| 상태 | 서버 안정 · 문서화 이 문서로 착수 |

---

## 2. 설치 — `.mcp.json` 에 dartlab 서버를 등록한다

사용자가 MCP 호환 클라이언트 (Claude Desktop · Claude Code · Codex · Cursor · Copilot) 에서 dartlab 을 쓰려면 `.mcp.json` 에 서버를 등록한다.

### 자동 설치 (프로젝트 루트에서)

```bash
dartlab mcp --install
# → 현재 디렉토리에 .mcp.json 생성 또는 "dartlab" 서버 항목 추가
```

### 수동 설정 (`.mcp.json` · Claude Desktop 설정)

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
클라이언트 (Claude Desktop 등)
    ↓ stdio JSON-RPC
python -m dartlab.mcp
    ↓ asyncio.run(run_stdio)
mcp.server.stdio.stdio_server
    ↓ MCP SDK (Server, Tool, Resource)
create_server()
    ├─ list_tools  → _generated_tools.py + discovery + graph tools
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

## 4. 도구 체계 — SSOT 는 dartlab Python API 와 docstring

MCP 도구 목록은 **수동 나열 없음**. `scripts/build/generateSpec.py` 가 dartlab 공개 API 의 시그니처 + 독스트링을 읽어 `src/dartlab/mcp/_generated_tools.py` 를 재생성한다. 수정이 필요하면 원본 함수의 시그니처·독스트링을 고치고 `generateSpec` 을 재실행한다.

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
| API Discovery | `listDartlabApi` · `searchDartlabApi` · `verifyDartlabApi` | 런타임 introspection — 외부 LLM 이 dartlab API 를 메타 조회 |
| Analysis Graph | `contextForQuestion` · `queryAnalysisGraph` · `impactForGraphNode` | 질문별 route/contract/tool/evidence/visual 요구사항 조회 |

### 리소스 (`read_resource`)

MCP 클라이언트가 능동적으로 구독 가능한 URI:

| URI | 내용 |
|---|---|
| `dartlab://info` | 버전 · 도구 수 · 현재 캐시된 종목코드 |
| `dartlab://graph` | Analysis Graph 전체 payload |
| `dartlab://graph/status` | graphVersion · sourceHash · node/edge/contract/route 요약 |
| `dartlab://graph/{kind}/{id}` | 특정 graph node 와 인접 edge |
| `dartlab://scan/{axis}` | `profitability` · `growth` 등 전종목 횡단 분석 결과 |
| `dartlab://macro/{axis}` | `종합` · `사이클` 등 매크로 스냅샷 |
| `dartlab://company/{code}/topics` | 해당 종목에서 `companyShow` 로 조회 가능한 토픽 목록 |

캐시에 로드된 Company 는 런타임에 `company/{code}/topics` 리소스로 자동 노출.

**반복 실패** — `_generated_tools.py` 를 수동 수정 → generateSpec 재실행 시 덮어써서 사라짐. 원본 함수 시그니처·독스트링에서 고친다.

---

## 5. AI tool 과의 관계 — 독립 registry, 공유 원천

| 축 | `dartlab.ask` 내부 AI tool | MCP 도구 |
|---|---|---|
| 생성 시점 | 런타임 (`buildTools()` 매 호출) | 빌드 타임 (`_generated_tools.py`) |
| 스키마 원천 | `inspect.signature` + docstring + CAPABILITIES | `scripts/build/generateSpec.py` 에서 동일 원천 읽어 JSON 고정 |
| 결과 포맷 | `ToolResponse` (`llmText` · `uiData` · `dataAsOf`) | MCP `TextContent` (문자열만, 12,000 자 상한) |
| 사용 주체 | dartlab AI 엔진 (`ask`) | 외부 LLM 클라이언트 (Claude · Codex 등) |
| 블랙리스트 | `ai/tools/__init__.py::_BLACKLIST` (`setup` · Company class 등 제외) | 수동 선정 26 개 (사용자 분석 흐름 중심) |

**공통**: Python 함수 시그니처와 독스트링이 단일 진실의 원천. 한쪽만 갱신하지 않고 `generateSpec.py` 로 양쪽 재생성.

---

## 6. 운영 원칙

### 결과 크기 상한 — 12,000 자에서 자른다

외부 LLM 컨텍스트 절약을 위해 도구 결과 문자열은 `_MCP_MAX_RESULT_CHARS = 12000` 로 잘라낸다 (초과 시 "결과 잘림, 전체 N 자. 범위를 좁혀 재조회하세요" 안내 포함). AI tool 의 `ToolResponse` 와 다른 이유 — MCP 클라이언트는 스트리밍 지원이 일관되지 않고 단일 응답이 너무 크면 에이전트 루프가 깨진다.

### Company 캐시

- 상한 5 인스턴스 · TTL 10 분 (`_CACHE_MAX` · `_CACHE_TTL`).
- LRU 정책. 새 종목 로드 시 가장 오래된 항목 제거.
- Company 로딩 자체가 수초 걸리므로 같은 종목 반복 질의에 유효.

### 에러 처리

`_executeTool` 는 모든 엔진 예외를 잡고 `dartlab.core.desk.guide.handleError(e, feature=...)` 로 친절 메시지 생성. 사용자에게 "데이터 없음 → gather 먼저 수집하세요" 같은 해결책이 포함된 응답을 돌려준다 (CLAUDE.md 사용자 편의 원칙).

### 블랙리스트

MCP 에 노출하지 않는 도구:
- `ask` · `Company` · `setup` · `collect` · `config` 등 비분석 API.
- `pythonExec` (AI tool 엔진 전용 escape hatch — 외부 LLM 에 임의 코드 실행 노출은 보안 리스크).
- `companySections` (전체 sections 지도는 메모리 부담이 크다. `companyTopics` → `companyShow(topic)` 또는 분석/공시 경량 도구를 사용한다).

### 로깅

- `logging.getLogger("dartlab.mcp")` 가 stderr 로 INFO 레벨 출력.
- 도구 호출·Company 로딩·에러 모두 기록.
- stdio 전송은 stdout 을 JSON-RPC 로 점유하므로 진단 로그는 반드시 stderr.

**반복 실패** — stdio 전송에서 stdout 에 `print()` 찍으면 JSON-RPC 파싱 깨짐. 로그는 stderr 고정.

---

## 7. VSCode 확장과의 연계

VSCode 확장 활성화 시 작업 공간 루트의 `.mcp.json` 과 `.vscode/mcp.json` 에 dartlab MCP 서버를 자동 등록한다 (`ops/vscode.md` §MCP 자동 등록). 결과적으로 Claude Code 나 Copilot 이 `@dartlab` 도구를 바로 인식한다.

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

## 9. 설치 가이드 — 클라이언트별

### Claude Desktop

```bash
cd <프로젝트 루트>
dartlab mcp --install
# → ./.mcp.json 생성. Claude Desktop 이 해당 디렉토리를 열 때 자동 인식.
```

또는 Claude Desktop 설정 파일 (`~/Library/Application Support/Claude/claude_desktop_config.json` (mac) · `%APPDATA%/Claude/claude_desktop_config.json` (win)) 에 위 "수동 설정" 섹션의 블록 추가.

### Claude Code · Codex · Cursor

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
| `scripts/build/generateSpec.py` | 공개 API → CAPABILITIES · `_generated_tools.py` · `llms.txt` · 스킬 reference 재생성 |
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

1. MCP 서버는 외부 LLM 클라이언트에 dartlab 엔진을 노출하는 L4 표현층, `ask` 내부 AI tool 과 독립.
2. 설치는 `dartlab mcp --install` → `.mcp.json` 자동 생성 또는 수동 설정 블록 추가.
3. 전송 2 경로 — stdio (`python -m dartlab.mcp`) + SSE (`create_sse_app()` Starlette ASGI).
4. 26 도구 + 3 API discovery + 4 리소스, SSOT 는 Python API · docstring → `generateSpec.py` 자동 생성.
5. 결과는 12,000 자에서 잘라내고 "범위 좁혀 재조회" 안내, Company 캐시 5 개 × 10 분.
6. 에러는 `handleError(feature=...)` 로 친절 메시지, stdio 로그는 stderr (stdout JSON-RPC 점유).
7. 블랙리스트 — `ask` · Company class · `setup` · `collect` · `pythonExec` (보안 리스크).
8. VSCode 확장이 activation 시 `.mcp.json` · `.vscode/mcp.json` 자동 등록 → Claude Code · Copilot 즉시 인식.
