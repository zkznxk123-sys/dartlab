"""Stage D — LoRA 파인튜닝 (Unsloth + QLoRA).

Gemma 4 8B 또는 Qwen 3.5 9B 위에 dartlab 공시 분석 QLoRA.

사전 준비:
    pip install unsloth trl datasets

실행 (A100/Colab):
    python scripts/finslm/trainLoRA.py --base gemma4-8b --data data/finslm/train.jsonl

출력:
    outputs/finslm-lora/      (LoRA adapter)
    outputs/finslm-merged/    (16-bit merged)
    outputs/finslm-gguf/      (GGUF q4_k_m)
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="FinSLM LoRA Training")
    parser.add_argument("--base", default="unsloth/gemma-3-8b-it", help="Base model (HF path)")
    parser.add_argument("--data", default="data/finslm/train.jsonl", help="Training data")
    parser.add_argument("--val", default="data/finslm/val.jsonl", help="Validation data")
    parser.add_argument("--output", default="outputs/finslm-lora", help="Output directory")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--rank", type=int, default=64)
    parser.add_argument("--alpha", type=int, default=128)
    parser.add_argument("--max-seq-length", type=int, default=4096)
    parser.add_argument("--gguf", action="store_true", help="Export GGUF after training")
    args = parser.parse_args()

    print(f"Base: {args.base}")
    print(f"Data: {args.data}")
    print(f"Epochs: {args.epochs}, LR: {args.lr}, Rank: {args.rank}")
    print()

    # 1. 모델 로드
    try:
        from unsloth import FastModel
    except ImportError:
        print("[ERROR] pip install unsloth 필요")
        return 1

    print("[1/5] 모델 로드...")
    model, tokenizer = FastModel.from_pretrained(
        args.base,
        max_seq_length=args.max_seq_length,
        load_in_4bit=True,
    )

    # 2. LoRA 적용
    print("[2/5] LoRA 적용...")
    model = FastModel.get_peft_model(
        model,
        r=args.rank,
        lora_alpha=args.alpha,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_dropout=0.05,
    )

    # 3. 데이터셋 로드
    print("[3/5] 데이터셋 로드...")
    from datasets import load_dataset

    dataset = load_dataset(
        "json",
        data_files={
            "train": args.data,
            "val": args.val,
        },
    )

    # ShareGPT 포맷 → chat template 변환
    from unsloth.chat_templates import get_chat_template, standardize_sharegpt

    tokenizer = get_chat_template(tokenizer, chat_template="chatml")
    dataset = standardize_sharegpt(dataset)

    def _apply_template(examples):
        texts = tokenizer.apply_chat_template(
            examples["conversations"],
            tokenize=False,
            add_generation_prompt=False,
        )
        return {"text": texts}

    dataset = dataset.map(_apply_template, batched=True)

    # 4. 학습
    print("[4/5] 학습 시작...")
    from trl import SFTConfig, SFTTrainer

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset["train"],
        eval_dataset=dataset["val"],
        args=SFTConfig(
            output_dir=args.output,
            num_train_epochs=args.epochs,
            per_device_train_batch_size=args.batch,
            gradient_accumulation_steps=4,
            learning_rate=args.lr,
            lr_scheduler_type="cosine",
            warmup_ratio=0.1,
            save_strategy="epoch",
            eval_strategy="epoch",
            logging_steps=10,
            bf16=True,
            optim="adamw_8bit",
            seed=42,
            max_seq_length=args.max_seq_length,
            dataset_text_field="text",
        ),
    )

    stats = trainer.train()
    print(f"\n학습 완료: {stats.metrics}")

    # 5. 저장
    print("[5/5] 저장...")
    # LoRA adapter
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    print(f"  LoRA adapter → {args.output}")

    # Merged 16-bit
    merged_path = args.output.replace("-lora", "-merged")
    model.save_pretrained_merged(merged_path, tokenizer)
    print(f"  Merged 16-bit → {merged_path}")

    # GGUF
    if args.gguf:
        gguf_path = args.output.replace("-lora", "-gguf")
        model.save_pretrained_gguf(gguf_path, tokenizer, quantization_method="q4_k_m")
        print(f"  GGUF q4_k_m → {gguf_path}")

    print("\n완료!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
