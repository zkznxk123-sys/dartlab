# dartlab fine-tuning 모델 선택 ledger

> 마스터 플랜 v2 트랙 8 PR-T4. 운영자가 SFT/DPO 학습 trigger 시 선택 가능한 base 모델 비교표.

## 1 순위 — Qwen/Qwen2.5-7B-Instruct ⭐

| 항목 | 평가 |
|---|---|
| 라이센스 | **Apache 2.0** — 상용 배포 자유 |
| 한국어 | 중 — multi-lingual base, dartlab 코퍼스 SFT 로 향상 가능 |
| Tool calling | **native** — function calling protocol 내장 (OpenAI 호환 양식) |
| LoRA / QLoRA | **호환** — peft adapter 정상 작동 |
| GPU 요구 | 24GB VRAM 1 장 (QLoRA 4-bit) — RTX 3090 / 4090 가능 |
| 추론 속도 | tokens/s 양호 (Llama 7B 동급) |
| dartlab 인프라 | [providers/ollama.py](../providers/ollama.py) 호환 — 학습 후 ollama 배포 가능 |

**근거**: 종합 1 순위.

## 2 순위 — Qwen/Qwen2.5-14B-Instruct

| 항목 | 평가 |
|---|---|
| 라이센스 | Apache 2.0 |
| 한국어 | 중상 — 7B 보다 깊은 reasoning |
| Tool calling | native |
| LoRA | 호환 |
| GPU 요구 | 48GB VRAM (QLoRA) — A6000 / 2x 3090 |
| 추론 속도 | 7B 의 ~50% (cost 2x) |

**선택 시기**: dartlab eval 상 7B 가 ceiling 친 경우 (quality strict ≥ 80) 운영자 별도 결정.

## 3 순위 — beomi/Llama-3-Open-Ko-8B

| 항목 | 평가 |
|---|---|
| 라이센스 | Llama 3 Community |
| 한국어 | **상 (Korean native)** — 한국어 corpus 우선 학습 |
| Tool calling | 부분 (Llama 3 의 tool-use 패턴 → JSON tool calling 추가 학습 필요) |
| LoRA | 호환 |
| GPU 요구 | 24GB VRAM |
| 추론 속도 | 양호 |

**선택 시기**: 한국어 fluency 가 최우선 + tool calling 학습 데이터 별도 박을 수 있을 때.

## 5 순위 — OpenAI fine-tune API (gpt-4o-mini)

| 항목 | 평가 |
|---|---|
| 라이센스 | 종속 (closed) |
| 한국어 | 상 |
| Tool calling | native |
| LoRA | ❌ (closed API) |
| GPU 요구 | 0 (cloud) |
| 비용 | $25/1M training tokens + $0.075/$0.300 inference per 1M (gpt-4o-mini) |
| Lock-in | **높음** — closed model, dataset 이전 불가 |

**비추**: lock-in 위험. 학습 dataset 박은 노력이 OpenAI 종속으로 묶임.

## 의사결정

**기본**: Qwen2.5-7B-Instruct. 운영자 명시 override 시 다른 선택 가능.
**학습 트리거 조건**: trace 200+ 누적 AND GPU 24GB 확보 AND 운영자 명시 결정. 3 AND.

## 학습 코맨드 (PR-T5)

```bash
pip install dartlab[ft]  # PR-T4 의 ft extra
uv run python -X utf8 -m dartlab.ai.training.runSft \
    --dataset data/_training/sft_v1.jsonl \
    --base-model Qwen/Qwen2.5-7B-Instruct \
    --out data/_models/dartlab-ko-ft-v1
```

## A/B 비교 (PR-T3)

```bash
uv run --no-sync python -X utf8 tests/_attempts/aiAbHarness.py \
    --providerA "ollama:qwen2.5:7b-instruct-q4_K_M" \
    --providerB "ollama:dartlab-ko-ft:v1" \
    --n-runs 3
```

성공 임계: strictQualityScore (B) ≥ score (A) + 10 점 AND latency p50 (B) ≤ p50 (A) × 1.1.
