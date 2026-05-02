# MCP

**주체**: MCP 서버 (`dartlab.mcp` — stdio · SSE 전송으로 MCP 호환 실행 환경에 dartlab 엔진 노출).
**현재**: `python -m dartlab.mcp` stdio 서버 + SSE ASGI 앱 + `.mcp.json` 자동 설치 헬퍼 + Ask Workbench canonical tools. VSCode 확장이 활성화 시 `.mcp.json` 에 자동 등록.
**방향**: 외부 실행 환경도 `inspect → compute → verify → answer` 흐름을 따르게 한다. 기본 모드는 canonical-only이며, 엔진별 도구는 명시 opt-in compatibility 표면으로만 유지.

MCP (Model Context Protocol) 는 MCP 호환 실행 환경이 dartlab workbench 를 호출하도록 하는 표준 전송 계층. `dartlab.ask` 와 같은 Ask Workbench action 을 소비하는 **L4 표현층**이며, AI 구조를 따로 정의하지 않는다.

각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 1. 한눈에 보기

| 항목 | 내용 |
|---|---|
| 레이어 | L4 (표현) — `vscode/` 와 동등 |
| 진입점 | `python -m dartlab.mcp` (stdio) · `dartlab.mcp.create_sse_app()` (SSE) |
| 도구 | Ask Workbench canonical tools + 공용 skills tools 기본. compatibility 엔진 도구는 opt-in |
| 리소스 | `dartlab://info` · `dartlab://ask-workbench` · `dartlab://skills` · 필요 시 compatibility 리소스 |
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

공식 stdio 경로는 설치된 Python/venv에서 모듈을 직접 실행하는 방식이다.
`uvx dartlab mcp` 는 cold install 출력이 stdio 프로토콜을 오염시킬 수 있으므로 Desktop attach 품질 기준의 기본 경로로 쓰지 않는다.

```json
{
  "mcpServers": {
    "dartlab": {
      "command": "python",
      "args": ["-X", "utf8", "-m", "dartlab.mcp"],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

개발 checkout 에서만 `uv run python -X utf8 -m dartlab.mcp` 를 사용한다. 이 경우에도 stdout 은 JSON-RPC 전용이어야 한다.

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
    ├─ list_tools  → 기본: canonical Ask Workbench tools only
    ├─ list_tools  → opt-in compatibility: legacy namespace 엔진 도구
    ├─ call_tool   → canonical action 또는 명시 compatibility adapter
    └─ read_resource → dartlab://{scheme}/{path}
```

### SSE 모드 (HTTP)

웹 배포나 원격 브릿지가 필요하면 SSE 앱을 직접 실행하거나 FastAPI 에 마운트:

SSE/HTTP는 원격 실행 표면이므로 기본 개발 문서 예시는 localhost 바인딩만 허용한다. 공개 네트워크 노출은 인증, origin 검증, workspace trust, rate limit, session TTL, artifact retention 정책이 구현된 뒤에만 가능하다.

```python
from dartlab.mcp import create_sse_app

app = create_sse_app()   # Starlette ASGI — /sse (SSE endpoint) + /messages/ (POST)
# 또는
from dartlab.mcp import run_sse
run_sse(host="127.0.0.1", port=8001)
```

---

## 4. 도구 체계 — 기본 표면은 Ask Workbench Kernel이다

AI 설계 SSOT는 루트 `ASK_WORKBENCH_KERNEL.md`다.

MCP의 기본 추천 표면은 `start_ask_session`, `ask_kernel_status`, `search_reference`, `read_context`, `inspect_dataset`, `run_python`, `compile_visual`, `finalize_answer`와 공용 skill 조회 도구다. 외부 실행 환경도 엔진 함수명을 먼저 맞히는 대신 kernel session을 시작하고, 필요한 문서·capability·skill·데이터셋을 확인하고, `run_python`에서 DartLab 라이브러리를 써서 계산한 뒤 `finalize_answer`로 검산한다.

엔진별 MCP 도구 목록은 compatibility다. 기본 attach 에서는 canonical Workbench tool 만 노출한다. compatibility 도구가 필요하면 명시 설정으로 legacy namespace 를 열어야 한다. 새 품질 규칙이나 질문별 예외는 compatibility 도구에 추가하지 않는다.

### 기본 도구

| 도구 | 역할 |
|---|---|
| `start_ask_session` | 질문과 release policy 기반 세션을 시작 |
| `ask_kernel_status` | kernel 상태와 RuntimeDatasetCatalog 요약 |
| `search_reference` | 설계·ops·docstring·capability·dataset catalog 짧은 검색 |
| `read_context` | source-addressed bounded text window |
| `inspect_dataset` | runtime dataset schema/latest/entity/metric/sample 확인 |
| `run_python` | DartLab workspace 안에서 bounded Python 실행 |
| `compile_visual` | table rows 기반 검증된 visual spec 생성 |
| `finalize_answer` | ref 기반 검산 후 답변 release |
| `listDartlabSkills` | 공용 SkillSpec 목록 |
| `searchDartlabSkills` | 공용 SkillSpec 검색 |
| `explainDartlabSkill` | 단일 SkillSpec 설명 |
| `checkDartlabSkillEvidence` | SkillSpec required evidence 충족 확인 |

`inspect_data` 는 외부 호환 alias 일 뿐 canonical 도구명이 아니다.

### 리소스 (`read_resource`)

MCP 클라이언트가 능동적으로 구독 가능한 URI:

| URI | 내용 |
|---|---|
| `dartlab://info` | 버전 · 도구 수 · 현재 캐시된 종목코드 |
| `dartlab://ask-workbench` | Ask Workbench Kernel 설계 요약 |
| `dartlab://skills` | 공용 SkillSpec 목록 |
| `dartlab://skills/{id}` | 단일 SkillSpec |
| compatibility 리소스 | 명시 opt-in 일 때만 엔진별 조회 리소스 제공 |

compatibility 리소스는 AI 구조를 정의하지 않는다. 기본 MCP attach 에서는 workbench 리소스만 보장한다.

**반복 실패** — `_generated_tools.py` 를 수동 수정 → generateSpec 재실행 시 덮어써서 사라짐. 원본 함수 시그니처·독스트링에서 고친다.

### Workbench 소비

MCP 도구도 `/api/ask` 와 같은 Ask Workbench Kernel 을 소비한다. 외부 실행 환경도 엔진 함수 수십 개를 먼저 맞히는 대신 `start_ask_session → search_reference/read_context/inspect_dataset → run_python → compile_visual → finalize_answer` 흐름을 쓴다. 기존 엔진별 MCP tool 은 호환용으로 유지하지만 새 품질 규칙이나 질문별 예외를 거기에 추가하지 않는다.

| Canonical MCP tool | MCP 역할 |
|---|---|
| `start_ask_session` | AskSession 생성, release policy 반환 |
| `ask_kernel_status` | 환경·RuntimeDatasetCatalog·provider capability 확인 |
| `search_reference` | 설계·ops·source·docstring·recipe 검색 |
| `read_context` | source-addressed small context window 읽기 |
| `inspect_dataset` | runtime dataset schema/latest/head/tail 확인 |
| `run_python` | DartLab/Polars 계산 실행 |
| `compile_visual` | source ref 기반 visual spec 컴파일 |
| `finalize_answer` | 검증된 최종 답변 제출 |

MCP 경로에서 별도 지식 그래프나 수동 planner 를 만들지 않는다. 외부 실행 환경이 dartlab 을 이해해야 할 때도 기본 표면은 Ask Workbench action 과 공용 `dartlab.skills` resolver 이며, 엔진별 generated 도구와 graph 리소스는 compatibility 이다. MCP 는 skill 을 새로 정의하지 않는다.

---

## 5. compatibility 도구와의 관계 — 공유 원천, 기본 비노출

| 축 | Ask Workbench 기본 도구 | compatibility MCP 도구 |
|---|---|---|
| 생성 시점 | 런타임 (`src/dartlab/ai/mcp.py`) | 빌드 타임 (`_generated_tools.py`) |
| 스키마 원천 | Ask Workbench action contract | 공개 API 시그니처 + docstring |
| 결과 포맷 | ref/trace/result bundle 친화 구조 | MCP `TextContent` 중심 |
| 사용 주체 | `dartlab.ask`, `/api/ask`, MCP 기본 표면 | 명시 opt-in MCP 호환 사용자 |
| 품질 규칙 | `ASK_WORKBENCH_KERNEL.md` 의 verify/release | 새 품질 규칙 추가 금지 |

compatibility 도구는 Python API docstring 을 반영할 수 있지만 AI kernel 을 정의하지 않는다.

---

## 6. 운영 원칙

### stdio 순도 — stdout 은 MCP 메시지만 쓴다

stdio 전송에서 stdout 은 JSON-RPC 프레임 전용이다.

불변식:

```text
stdout
  MCP JSON-RPC 메시지만 허용.

stderr
  진단 로그 허용.

file log
  긴 디버그 로그 허용.

process startup
  initialize 전후 사람이 읽는 배너, 진행률, 설치 로그, print 출력 금지.
```

MCP 규격상 stdio 서버는 stdin 으로 JSON-RPC 를 읽고 stdout 으로 JSON-RPC 를 쓰며, 로그는 stderr 로만 보내야 한다. 따라서 `dartlab mcp` production 경로는 다음을 통과해야 한다.

```text
python -m dartlab.mcp
  stdout first line is JSON-RPC only after client request.

dartlab mcp
  no CLI banner, no progress print, no package install output on stdout.

uvx dartlab mcp
  cold install 로그가 stdout 으로 섞이면 Desktop attach 품질 대상에서 제외하고
  설치형 command 또는 python -m dartlab.mcp 설정을 공식 권장한다.
```

로거 정책:

```text
dartlab.mcp logger
  stderr handler 1개만 둔다.
  propagate=false.
  같은 메시지가 두 번 찍히면 실패.

dartlab root logger
  MCP stdio 모드에서는 stdout handler 금지.
```

현재 GitHub issue #28 진단 기준:

```text
증상
  Desktop 은 running 으로 보이나 tool attach 실패.
  수동 실행에서 "MCP 서버 초기화", "DartLab MCP 서버 시작" 로그가 중복 표시.

1차 원인 후보
  dartlab.mcp logger 가 stderr handler 를 붙이고 propagate=true 로 root dartlab logger 까지 전파되어 로그가 중복된다.
  Desktop 이 stderr 를 에러처럼 취급하거나 attach 안정성을 낮출 수 있다.

2차 원인 후보
  설정 예시는 uvx dartlab mcp 인데 로그에는 uv run dartlab mcp 가 보인다.
  실제 Desktop 설정 또는 캐시된 설정이 문서와 다를 수 있다.

3차 원인 후보
  현재 새 AI 구조 전환 중 MCP compatibility code 가 과거 dartlab.ai.runtime.* 를 참조한다.
  attach 후 resources/tools 호출 시 ImportError 로 process 가 종료될 수 있다.

조치 원칙
  새 AI 구현에서는 MCP 가 ai_backup 또는 old runtime 을 import 하지 않는다.
  stdio conformance 테스트는 attach 품질 게이트로 둔다.
  Desktop 설정은 installed python module path 또는 uv run python -m dartlab.mcp 를 공식 경로로 고정한다.
```

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
- legacy `pythonExec` (AI legacy loop 전용). Ask Workbench MCP 는 `run_python` 을 권한 프로파일로 제한해 쓴다.
- `companySections` (전체 sections 지도는 메모리 부담이 크다. `companyTopics` → `companyShow(topic)` 또는 분석/공시 경량 도구를 사용한다).

### 로깅

- `logging.getLogger("dartlab.mcp")` 가 stderr 로 INFO 레벨 출력.
- 도구 호출·Company 로딩·에러 모두 기록.
- stdio 전송은 stdout 을 JSON-RPC 로 점유하므로 진단 로그는 반드시 stderr.
- `dartlab.mcp` 로거는 `propagate = False` 로 중복 출력을 막는다.

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

### 로컬 SSE 개발

```bash
uv run python -c "from dartlab.mcp import run_sse; run_sse(host='127.0.0.1', port=8001)"
```

클라이언트 설정:

```json
{
  "mcpServers": {
    "dartlab-remote": {
      "url": "http://127.0.0.1:8001/sse"
    }
  }
}
```

공개 네트워크 원격 SSE 예시는 인증, origin 검증, rate limit, session TTL, workspace trust, artifact retention 구현 전까지 문서화하지 않는다.

---

## 관련 코드

| 경로 | 역할 |
|---|---|
| `src/dartlab/mcp/__init__.py` | 서버 구성 · `_executeTool` · `create_server` · `run_stdio` · `run_sse` · `installMcpConfig` |
| `src/dartlab/mcp/__main__.py` | `python -m dartlab.mcp` 진입점 |
| `src/dartlab/mcp/_generated_tools.py` | `_TOOLS` · `TOOL_FEATURE_MAP` (`generateSpec.py` 자동 생성, 수동 수정 금지) |
| `scripts/build/generateSpec.py` | 공개 API → CAPABILITIES · `_generated_tools.py` · `llms.txt` · 스킬 reference 재생성 |
| `src/dartlab/cli/` | `dartlab mcp --install` CLI 진입 |
| `src/dartlab/ai/mcp.py` | Ask Workbench canonical MCP handlers |
| `tests/test_mcp.py` · `tests/test_mcp_tools.py` | 단위 테스트 |
| `ui/vscode/src/extension.ts` | VSCode 확장 활성화 시 `.mcp.json` 자동 등록 |

---

## 관련 문서

- [../ASK_WORKBENCH_KERNEL.md](../ASK_WORKBENCH_KERNEL.md) — AI 엔진 설계 SSOT.
- [ops/vscode.md](vscode.md) — VSCode 확장 MCP 자동 등록 + stdio 프로토콜.
- [ops/code.md](code.md) — 독스트링 9 섹션 + CAPABILITIES 자동 생성 규약.
- [ops/api-contract.md](api-contract.md) — 공개 API 계약 (MCP 가 노출하는 표면의 원칙).

---

## 요약 — 명제 8 줄

1. MCP 서버는 MCP 호환 실행 환경에 dartlab 엔진을 노출하는 L4 표현층, `ask` 내부 AI tool 과 독립.
2. 설치는 `dartlab mcp --install` → `.mcp.json` 자동 생성 또는 수동 설정 블록 추가.
3. 전송 2 경로 — stdio (`python -m dartlab.mcp`) + SSE (`create_sse_app()` Starlette ASGI).
4. 기본 노출은 canonical Ask Workbench tools only. 엔진 도구/API discovery/graph 도구는 opt-in compatibility이며 SSOT 는 Python API · docstring · capabilities · AIContract → `generateSpec.py` 자동 생성.
5. 결과는 12,000 자에서 잘라내고 "범위 좁혀 재조회" 안내, Company 캐시 5 개 × 10 분.
6. 에러는 `handleError(feature=...)` 로 친절 메시지, stdio 로그는 stderr (stdout JSON-RPC 점유).
7. 블랙리스트 — `ask` · Company class · `setup` · `collect` · `pythonExec` (보안 리스크).
8. VSCode 확장이 activation 시 `.mcp.json` · `.vscode/mcp.json` 자동 등록 → MCP 호환 실행 환경이 즉시 인식.
