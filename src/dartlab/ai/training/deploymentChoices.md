# dartlab fine-tuned 모델 배포 옵션

> 마스터 플랜 v2 트랙 8 PR-T4. 학습된 LoRA adapter 또는 merged weights 의 배포 경로.

## 옵션 A — Ollama 로컬 배포 ⭐

**적합**: 운영자 1 인 / 소규모 개발자 그룹 / 로컬 추론.

```bash
# 1) LoRA adapter merge (학습 후)
uv run python -X utf8 -m dartlab.ai.training.mergeLora \
    --base Qwen/Qwen2.5-7B-Instruct \
    --adapter data/_models/dartlab-ko-ft-v1 \
    --out data/_models/dartlab-ko-ft-v1-merged

# 2) GGUF 양자화 (llama.cpp convert + quantize Q4_K_M)
python -m llama_cpp.convert data/_models/dartlab-ko-ft-v1-merged \
    --outfile dartlab-ko-ft-v1.gguf
llama-quantize dartlab-ko-ft-v1.gguf dartlab-ko-ft-v1-q4_K_M.gguf Q4_K_M

# 3) Ollama Modelfile
cat > Modelfile <<EOF
FROM dartlab-ko-ft-v1-q4_K_M.gguf
TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ .Response }}<|im_end|>"""
PARAMETER stop "<|im_end|>"
EOF

# 4) Ollama 등록
ollama create dartlab-ko-ft:v1 -f Modelfile
ollama run dartlab-ko-ft:v1
```

dartlab 호환: `providers/ollama.py` 가 본 모델 자동 인식. provider="ollama" model="dartlab-ko-ft:v1" 설정 후 즉시 사용.

## 옵션 B — vLLM 자체 호스팅

**적합**: 다수 사용자 / API gateway / batch inference.

```bash
vllm serve data/_models/dartlab-ko-ft-v1-merged --port 8000
```

dartlab 호환: `providers/__init__.py` 의 OpenAICompatibleProvider 가 `DARTLAB_OPENAI_COMPAT_BASE_URL=http://localhost:8000/v1` 설정 시 즉시 사용.

## 옵션 C — HuggingFace Hub 공개

**적합**: 외부 사용자 다운로드 / 모델 reuse.

```bash
huggingface-cli upload dartlab-ko-ft data/_models/dartlab-ko-ft-v1
```

라이센스: Qwen2.5 = Apache 2.0 → 자유 배포. Llama 3 기반은 Community License 종속 (별도 검토).

## 옵션 D — RunPod / Lambda / Modal 임시 GPU

**적합**: 학습만 (배포는 옵션 A/B/C 와 결합).

비용: A100 24GB ≈ $0.79~$1.99/hour. 7B Qwen QLoRA 1 epoch = 2~4 시간 → 학습 1 회 < $10.

## 의사결정

**기본 흐름**: 옵션 A (Ollama 로컬). 외부 사용자 공개가 결정되면 옵션 C 추가.

## 운영자 결정 트리거

PR-T5 의 `runSft` 실행은 4 조건 AND 후 진행:
1. trace 200+ 누적 (PR-T1 의 `buildSftDataset` stats.totalTraces ≥ 200)
2. GPU 24GB 확보 (로컬 또는 RunPod)
3. 운영자 명시 결정 (CLAUDE.md 의 사용자 트리거 규약)
4. A/B 비교 baseline (현 provider 의 strict quality score 측정 완료)

성공 임계 (PR-T3 aiAbHarness):
- strictQualityScore (FT) ≥ base + 10 점 (절대치)
- latency p50 (FT) ≤ base × 1.1
