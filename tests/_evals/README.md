# `tests/_evals/` — dartlab.ai 에이전트 출력 회귀 (Track 3)

> 본 SSOT — [tests/POLICY.md](../POLICY.md) §5 Track 3.

## 목적

dartlab 정체성 = 자가개선 루프. 에이전트가 prompt/tool 바뀐 뒤에도 *같은 질문에 동등 품질의 답* 을 내는지 회귀 검증한다. syrupy 가 CLI 화면 회귀를 잡듯, 본 트랙은 에이전트 출력 회귀를 잡는다.

## 6 채점 신호

| 신호 | 의미 | 채점 방식 |
|---|---|---|
| `factual_correctness` | 기대 키워드 (회사명/숫자/항목) 등장 | 룰 (substring) |
| `evidence_citation` | Ref/source 인용 여부 | 룰 (`[ref:` 또는 `출처:` 패턴) |
| `tool_use_appropriate` | 기대 도구 호출 (search/analyze 등) | 룰 (tool log) |
| `format_compliance` | 응답 구조 (JSON/markdown/표) | 룰 (parser) |
| `reasoning_depth` | 단순 사실 ≠ 깊이 — 인과 사슬 길이 | 외부 모델 judge |
| `no_hallucination` | 환각 키워드 (`예상`, `아마도`, 미존재 회사) | 룰 + 외부 모델 cross-check |

룰 기반 4 신호는 CI Fast 안에서 무료 실행 가능. 외부 모델 judge 2 신호는 `eval` 마커 + 운영자 트리거.

## 디렉토리 구조

```
tests/_evals/
├── eval_set.jsonl       # 질문 + 기대 평가 (한 줄 = 한 case)
├── judge.py             # 6 신호 채점기 (룰 + 옵션 외부 모델)
├── runner.py            # 에이전트 실행 + judge 호출
├── test_eval_smoke.py   # CI Fast (룰 기반 mock case)
├── test_eval_live.py    # 운영자 트리거 (실 호출, 비용)
├── _runs/               # 결과 ledger (gitignored)
└── README.md (본 파일)
```

## eval_set.jsonl 스키마

```jsonc
{
  "id": "samsung_overview_v1",                              // 고유
  "question": "삼성전자 5 분기 매출 추세 알려줘",
  "expected_signals": {
    "factual_correctness": ["삼성전자", "005930", "분기", "매출"],
    "evidence_citation": true,
    "tool_use_appropriate": ["finance", "analyze"],
    "format_compliance": "markdown_with_table",
    "min_reasoning_depth": 2,                              // 외부 judge
    "forbidden_hallucinations": ["예상", "아마도"]
  },
  "tags": ["domain:finance", "level:basic"],
  "baseline_score": 0.85                                   // 회귀 임계
}
```

## 실행

### CI Fast (룰 기반, 무료)

```powershell
$env:DARTLAB_TEST_LOCKED="1"; $env:UV_NO_SYNC="1"
uv run python -X utf8 -m pytest tests/_evals/test_eval_smoke.py -v
```

### 운영자 트리거 (실 호출, $)

```powershell
$env:OPENAI_API_KEY="..."  # 또는 ANTHROPIC_API_KEY
$env:DARTLAB_EVAL_LIVE="1"
uv run python -X utf8 -m pytest tests/_evals/test_eval_live.py -m eval -v
```

비용 추정: case 당 $0.01~0.05 (judge 추가 호출 포함). 50 case ≈ $1~3 / run.

### 결과 비교

```powershell
$env:UV_NO_SYNC="1"
uv run python -X utf8 -m tests._evals.runner --compare-baseline
```

## 갱신 절차

1. **새 케이스 추가** — PR 에서 `eval_set.jsonl` 에 한 줄 추가. CI Fast 룰 채점 통과 확인.
2. **baseline 갱신** — 운영자 트리거 1 회 → 결과 ledger 의 평균 점수를 `baseline_score` 에 기록.
3. **회귀** — 다음 run 의 점수가 `baseline_score - 0.05` 이하면 fail.

## 의도적으로 안 하는 것

- **외부 평가 프레임워크 (inspect-ai 등) 의존** — dartlab 도메인 깊이가 깊어 자체 채점기가 적합. 외부 도구 추가는 비용 대비 가치 낮음.
- **CI Fast 에서 실 호출** — 비용 + flaky. 운영자 트리거 + nightly 한정.
- **judge 결과를 단일 점수로 함수 평균** — 6 신호 분리 보고. 한 신호 실패는 다른 신호 평균으로 상쇄되지 않음.
