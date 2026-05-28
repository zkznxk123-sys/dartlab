"""SFT (Supervised Fine-Tuning) 실 학습 trigger — 마스터 플랜 v2 트랙 8 PR-T5.

PR-T1 (traceToDataset) 산출 SFT JSONL + PR-T4 의 ``[ft]`` extra 활성 시 실 학습 1 회.
QLoRA 4-bit (24GB VRAM 1 장 가능) — Qwen2.5-7B-Instruct 기본.

운영자 결정 트리거 (4 AND):
    1. trace 200+ 누적 (PR-T1 buildSftDataset stats.totalTraces ≥ 200)
    2. GPU 24GB+ VRAM 확보
    3. 운영자 명시 실행 결정 (CLAUDE.md 사용자 트리거 규약)
    4. A/B baseline 측정 완료 (PR-T3 aiAbHarness)

import 자체에 ML 의존성 0 — ``runSftTraining`` 호출 시점에 lazy import. ``[ft]`` 미설치 시
RuntimeError 메시지로 명확히 안내.

CLI 사용 (PR-T5):
    uv run python -X utf8 -m dartlab.ai.training.runSft \\
        --dataset data/_training/sft_v1.jsonl \\
        --base-model Qwen/Qwen2.5-7B-Instruct \\
        --out data/_models/dartlab-ko-ft-v1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def _checkFtExtraInstalled() -> tuple[bool, list[str]]:
    """[ft] extra 패키지 6 종 모두 import 가능 검사 — 누락 list 반환."""
    import importlib

    missing: list[str] = []
    for pkg in ("transformers", "peft", "trl", "datasets", "accelerate"):
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing.append(pkg)
    return (len(missing) == 0, missing)


def _readJsonlSamples(path: Path) -> list[dict[str, Any]]:
    """SFT JSONL 파일 → sample dict list (messages key 보유 검사)."""
    import json

    out: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            sample = json.loads(line)
            if "messages" in sample and isinstance(sample["messages"], list):
                out.append(sample)
    return out


def runSftTraining(
    *,
    datasetPath: str | Path,
    baseModel: str = "Qwen/Qwen2.5-7B-Instruct",
    outDir: str | Path,
    epochs: int = 1,
    learningRate: float = 2e-5,
    batchSize: int = 4,
    gradientAccumulationSteps: int = 4,
    loadIn4bit: bool = True,
    loraR: int = 16,
    loraAlpha: int = 32,
    maxSeqLen: int = 4096,
    dryRun: bool = False,
) -> dict[str, Any]:
    """QLoRA SFT 학습 1 회 실행 → adapter 저장 경로 반환.

    Sig:
        runSftTraining(*, datasetPath, baseModel="Qwen/Qwen2.5-7B-Instruct", outDir,
            epochs=1, learningRate=2e-5, batchSize=4, gradientAccumulationSteps=4,
            loadIn4bit=True, loraR=16, loraAlpha=32, maxSeqLen=4096, dryRun=False) -> stats
    Args:
        datasetPath: PR-T1 buildSftDataset 산출 JSONL.
        baseModel: HF Hub model id 또는 로컬 경로 (기본 Qwen2.5-7B-Instruct).
        outDir: adapter 저장 디렉터리.
        epochs / learningRate / batchSize / gradientAccumulationSteps: 학습 hyperparam.
        loadIn4bit: True 면 bitsandbytes 4-bit (24GB VRAM 가능). Linux only.
        loraR / loraAlpha: LoRA rank / scaling.
        maxSeqLen: max sequence length.
        dryRun: True 면 dataset 검증 + ft extra 검사만 (실 학습 0).
    Returns:
        ``{"dryRun": bool, "datasetSize": N, "adapterPath": str | None, "baseModel": ...,
        "epochs", "learningRate", "ftInstalled": bool, "missingPackages": [...]}``
    Raises:
        RuntimeError: [ft] extra 미설치 시 안내 메시지.
        FileNotFoundError: datasetPath 누락.
    """
    ds_path = Path(datasetPath).expanduser()
    if not ds_path.exists():
        raise FileNotFoundError(f"dataset 누락: {ds_path}")

    samples = _readJsonlSamples(ds_path)
    ds_size = len(samples)

    ft_ok, missing = _checkFtExtraInstalled()

    if dryRun:
        return {
            "dryRun": True,
            "datasetSize": ds_size,
            "adapterPath": None,
            "baseModel": baseModel,
            "epochs": epochs,
            "learningRate": learningRate,
            "ftInstalled": ft_ok,
            "missingPackages": missing,
        }

    if not ft_ok:
        raise RuntimeError(f"[ft] extra 미설치 — `pip install dartlab[ft]` 실행 후 재시도. 누락 패키지: {missing}")

    # 실 학습 — 의존성 lazy import. 본 함수가 호출되기 전에는 transformers 등 0 import.
    # ruff: ignore F401 — 실제 사용 (trainer 빌드).
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    out_dir = Path(outDir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) tokenizer
    tokenizer = AutoTokenizer.from_pretrained(baseModel, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 2) model — QLoRA 4-bit (선택)
    quant_cfg = None
    if loadIn4bit:
        quant_cfg = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype="bfloat16",
            bnb_4bit_use_double_quant=True,
        )
    model = AutoModelForCausalLM.from_pretrained(
        baseModel,
        quantization_config=quant_cfg,
        trust_remote_code=True,
        device_map="auto",
    )

    # 3) LoRA config
    lora_cfg = LoraConfig(
        r=loraR,
        lora_alpha=loraAlpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    # 4) dataset
    ds = Dataset.from_list(samples)

    # 5) trainer
    cfg = SFTConfig(
        output_dir=str(out_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batchSize,
        gradient_accumulation_steps=gradientAccumulationSteps,
        learning_rate=learningRate,
        max_seq_length=maxSeqLen,
        logging_steps=10,
        save_strategy="epoch",
        bf16=True,
    )
    trainer = SFTTrainer(model=model, tokenizer=tokenizer, args=cfg, train_dataset=ds, peft_config=lora_cfg)
    trainer.train()
    trainer.save_model(str(out_dir))

    return {
        "dryRun": False,
        "datasetSize": ds_size,
        "adapterPath": str(out_dir),
        "baseModel": baseModel,
        "epochs": epochs,
        "learningRate": learningRate,
        "ftInstalled": True,
        "missingPackages": [],
    }


def _parseArgs(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="dartlab.training.runSft",
        description="DartLab SFT QLoRA 학습 trigger (PR-T5).",
    )
    parser.add_argument("--dataset", required=True, help="SFT JSONL 경로 (PR-T1 산출).")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-7B-Instruct", help="base model id.")
    parser.add_argument("--out", required=True, help="adapter 저장 디렉터리.")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--no-4bit", action="store_true", help="QLoRA 4-bit 비활성 (full bf16).")
    parser.add_argument("--dry-run", action="store_true", help="dataset 검증만 (실 학습 0).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI 진입 — args parse + runSftTraining 호출.

    Args:
        argv: CLI 인자 리스트. None 이면 ``sys.argv[1:]`` 사용.

    Returns:
        int: 0 = 성공, 1 = ft 미설치, 2 = dataset 누락.
    """
    args = _parseArgs(argv if argv is not None else sys.argv[1:])
    try:
        stats = runSftTraining(
            datasetPath=args.dataset,
            baseModel=args.base_model,
            outDir=args.out,
            epochs=args.epochs,
            learningRate=args.learning_rate,
            batchSize=args.batch_size,
            loadIn4bit=not args.no_4bit,
            dryRun=args.dry_run,
        )
    except FileNotFoundError as exc:
        sys.stderr.write(f"[runSft] {exc}\n")
        return 2
    except RuntimeError as exc:
        sys.stderr.write(f"[runSft] {exc}\n")
        return 1
    sys.stdout.write(f"[runSft] {stats}\n")
    return 0


__all__ = ["runSftTraining", "main"]


if __name__ == "__main__":
    sys.exit(main())
