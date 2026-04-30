# AI

> 상위 사상: [philosophy.md](philosophy.md) · 자가개선 루프: [coreloop.md](coreloop.md)

**주체**: AI 엔진 (`dartlab.ask` · 서버 `/api/ask`).
**공식 명칭**: DartLab Financial Workspace Agent.
**현재**: 공개 진입점은 유지하고, 내부 기본 경로는 workspace-native 단일 경로로 수렴한다.
**방향**: 모델이 DartLab workspace 를 직접 보고·읽고·실행하고·검산한 뒤 답하는 금융 분석 에이전트.

이 문서가 AI 엔진 구조의 단일 진실의 원천이다.

---

## 1. 공개 진입점은 유지한다

```python
import dartlab

dartlab.ask("최근 주가지수를 보고 강세 지수를 찾아봐라")
dartlab.Company("005930").ask("최근 공시 중요한 내용 찾아줘")
```

사용자는 `dartlab.ask()`와 `/api/ask`만 본다. 내부 구현이 바뀌어도 기존 `answer`/`artifacts` 소비자는 깨지지 않는다. 새 필드(`evidence`, `claims`, `visuals`, `limits`, `responseMeta`)는 additive 확장이다.

---

## 2. 공식 루프는 하나다

```
Observe -> Inspect -> Compute -> Verify -> Answer
```

요청마다 `AgentSession`을 만든다. 세션은 `question`, `workspaceRoot`, `dataRoot`, `currentDate`, `observations`, `executions`, `artifacts`, `visuals`, `limits`, `finalAnswer`를 기록한다.

LLM-facing tool은 7개만 둔다.

| Tool | 역할 |
|---|---|
| `workspace_status` | 현재 날짜, workspace/data root, Intelligence Pack 확인 |
| `read_text` | ops/source/docstring 읽기 |
| `inspect_data` | parquet/csv/tsv schema, head/tail, latest/asOf, column role 확인 |
| `run_python` | DartLab/Polars 계산 실행 |
| `search_workspace` | Intelligence Pack 우선 검색 후 문서·소스·데이터 검색 |
| `create_artifact` | 재사용 가능한 CSV/JSON/visual 산출 |
| `finalize_answer` | 관찰·계산·검산 후 최종 답변 제출 |

`gather`, `scan`, `macro`, `Company`, `analysis`, `credit`, `quant`, `viz`는 LLM tool이 아니다. `run_python` 안에서 사용하는 DartLab 라이브러리다.

---

## 3. DartLab Intelligence Pack을 쓴다

Intelligence Pack은 수동 planner가 아니다. 이미 있는 공식 원천을 설치형 generated artifact로 압축한 이해 팩이다. 위치는 `src/dartlab/ai/intelligence/pack.json` 이며 직접 수정하지 않는다. 원천을 고친 뒤 `scripts/build/generateSpec.py` 로 재생성한다.

| Map | 원천 | 용도 |
|---|---|---|
| API Map | `dartlab.__all__`, 공개 docstring | 어떤 라이브러리 API를 쓸 수 있는지 확인 |
| Capability Skill Map | 공개 docstring + capabilities + AIContract | 어떤 API를 언제 쓰고, 입력·출력·검산·실패 조건이 무엇인지 확인 |
| Data Catalog | generated dataset catalog + local data root fallback | 어떤 데이터셋을 inspect 할지 찾기 |
| Analysis Graph | generated graph | 질문별 contract/process/visual 요구 확인 |
| Process Map | generated process maps | 필요한 evidence/artifact/visual 계약 확인 |
| Recipe Map | 승인된 성공 trace | 반복 가능한 분석 절차 후보 |
| Visual Contract | ops/viz.md + generated contract | 시각 설명 산출물이 의미 있는지 확인 |
| Safety Policy | ops + runtime 제한 | 고메모리 경로, 날짜 혼동, 실행 실패 은폐 차단 |

SSOT는 ops 문서, docstring, capabilities, AIContract, data schema, 승인된 recipe다. Pack/Graph/Process/Workspace는 산출물이며 새 규칙 원천이 아니다. Pack이 없거나 schema/sourceHash 검증에 실패하면 runtime fallback으로 동작하되, 그 상태는 trace와 responseMeta에 남긴다.

---

## 4. 검산이 품질의 중심이다

`finalize_answer`가 최종 gate다. 형식 강제보다 거짓말 방지를 우선한다.

반드시 막는다.

- 데이터 기준일과 현재일 혼동
- observation/artifact에 없는 숫자 단정
- 실패한 실행을 성공처럼 말하기
- 계산형 질문인데 성공한 `run_python` 없음
- 데이터 질문인데 `inspect_data` 또는 관측값 없음
- 랭킹·비교·시계열 질문인데 의미 있는 visual 없음
- 단일값·단일막대·축 없는 visual

CSV는 핵심 품질이 아니다. 사용자가 원하거나 UI가 같은 계산표를 재사용해야 할 때 제공하는 산출물이다. 핵심은 `Observation -> Execution -> Verification -> Judgment`다.

---

## 5. Visual Explanation은 계산표에서 컴파일한다

visual은 장식이 아니다. 랭킹·비교·시계열·구조/인과 질문에서 사용자가 판단을 빨리 이해하게 하는 설명 산출물이다.

차트는 최소 2개 category와 2개 숫자값이 있어야 한다. 단일 `summary` 막대, 단일 종목 현재값 막대, placeholder 차트는 runtime과 UI에서 모두 버린다.

diagram은 구조·흐름·인과를 설명할 때만 쓴다. 근거 없는 diagram은 만들지 않는다.

상세 계약은 [viz.md](viz.md)가 SSOT다.

---

## 6. UI와 MCP는 같은 에이전트를 소비한다

web과 VSCode는 같은 Agent Trace 이벤트를 보여준다.

```
observe / inspect / compute / verify / artifact / chart / done
```

MCP도 workspace 7 tools와 `dartlab://intelligence-pack`을 기본 표면으로 둔다. 기존 엔진별 MCP tool은 compatibility로 유지하되 새 품질 규칙을 추가하지 않는다.

---

## 7. Legacy 구조는 기본 경로가 아니다

다음 구조는 공식 ask 경로에서 제거한다.

- legacy `toolLoop.py`
- text-first `quality.py`
- 프롬프트 규칙 누적 방식
- capabilities 직접 tool 노출
- plugin install hint
- 별도 reflection agent

공개 import 호환이 필요한 파일은 얇은 shim만 남긴다. shim에는 새 기능을 추가하지 않는다. 새 개선은 `workspace_agent`, `workspace_verify`, `workspace_visual`, `intelligence_pack`, `intelligence_map`으로만 들어간다.

Pack 운영 순서는 고정한다.

1. 공개 API docstring 또는 AIContract를 고친다.
2. `scripts/build/generateSpec.py` 를 실행한다.
3. `pack.json` drift와 Pack search를 확인한다.
4. 서버 경유 직접 audit로 실제 답변 품질을 판정한다.

---

## 8. 품질 선언은 직접 audit 후에만 한다

자동 테스트는 회귀 확인용이다. 품질 결론은 서버 경유 응답 원문을 사람이 직접 읽고 P/T/C/V로 판정한다.

필수 직접 질문:

- 최근 주가지수를 보고 강세 지수를 찾아봐라
- 최근 주가가 많이 오른 종목 찾아줘
- 삼성전자와 SK하이닉스 경쟁력 비교
- 삼성전자 최근 공시 중요한 내용 찾아줘

성공 기준:

- 날짜 오인 0
- 실행 실패 은폐 0
- 단일 막대 chart 0
- 의미 없는 diagram 0
- C/V 0
- 최종 목표 P=12

완벽 선언은 구현 완료가 아니라 서버·web·VSCode·visual 직접 audit 통과 후에만 가능하다.
