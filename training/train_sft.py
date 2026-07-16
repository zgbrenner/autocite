# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "accelerate>=1.10",
#   "datasets>=4.0",
#   "peft>=0.18",
#   "trackio>=0.10",
#   "transformers>=4.57",
#   "trl>=0.26",
# ]
# ///
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


MODEL_ID = "Qwen/Qwen3.5-0.8B"


def training_defaults() -> dict[str, Any]:
    return {
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "learning_rate": 2e-4,
        "epochs": 3,
        "max_length": 1024,
        "seed": 42,
        "report_to": ["trackio"],
        "push_to_hub": True,
    }


def _load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        from training.build_dataset import build_records, write_jsonl

        records = build_records("training/seed_examples.jsonl", seed=42)
        write_jsonl(records, path)
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    from datasets import Dataset
    from peft import LoraConfig
    from trl import SFTConfig, SFTTrainer

    defaults = training_defaults()
    dataset_path = Path(os.getenv("AUTOCITE_DATASET", "training/autocite_slm.jsonl"))
    records = _load_records(dataset_path)

    def conversational(row: dict[str, Any]) -> dict[str, Any]:
        messages = list(row["messages"])
        return {
            "prompt": messages[:-1],
            "completion": [messages[-1]],
        }

    train_rows = [conversational(row) for row in records if row["split"] == "train"]
    eval_rows = [conversational(row) for row in records if row["split"] == "validation"]
    if not train_rows or not eval_rows:
        raise ValueError("Dataset must contain non-empty train and validation splits")

    hub_model_id = os.getenv("AUTOCITE_HUB_MODEL", "sonomos/AutoCite-0.8B")
    output_dir = os.getenv("AUTOCITE_OUTPUT_DIR", "outputs/autocite-0.8b-lora")
    trainer = SFTTrainer(
        model=MODEL_ID,
        train_dataset=Dataset.from_list(train_rows),
        eval_dataset=Dataset.from_list(eval_rows),
        peft_config=LoraConfig(
            r=defaults["lora_r"],
            lora_alpha=defaults["lora_alpha"],
            lora_dropout=defaults["lora_dropout"],
            target_modules="all-linear",
            bias="none",
        ),
        args=SFTConfig(
            output_dir=output_dir,
            learning_rate=defaults["learning_rate"],
            num_train_epochs=defaults["epochs"],
            max_length=defaults["max_length"],
            per_device_train_batch_size=2,
            per_device_eval_batch_size=2,
            gradient_accumulation_steps=8,
            gradient_checkpointing=True,
            eval_strategy="steps",
            eval_steps=25,
            save_steps=25,
            logging_steps=5,
            seed=defaults["seed"],
            report_to=defaults["report_to"],
            project="autocite-slm",
            run_name="qwen3.5-0.8b-bluebook-sft",
            push_to_hub=defaults["push_to_hub"],
            hub_model_id=hub_model_id,
            completion_only_loss=True,
        ),
    )
    trainer.train()
    trainer.push_to_hub()


if __name__ == "__main__":
    main()
