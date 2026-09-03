"""
workers/tasks.py — ARQ Trainer Worker

ฟังก์ชันหลัก: train_model()
Flow:
  1. Download dataset (.parquet) จาก MinIO bucket 'datasets/{dataset_name}/'
  2. Load HuggingFace Dataset จาก parquet files
  3. Tokenize + align NER labels (subword token -> label -100)
  4. Fine-tune AutoModelForTokenClassification (base: bert-base-cased)
  5. TrainerCallback เขียน log ทุก step/epoch ลงไฟล์
  6. Evaluate ด้วย seqeval (precision, recall, f1)
  7. Save model + tokenizer แล้ว upload ทั้งโฟลเดอร์ + log -> MinIO 'models/{model_name}/v{timestamp}/'
  8. คืน summary dict เป็นผลลัพธ์ของ job

อ้างอิง: https://huggingface.co/learn/llm-course/en/chapter7/2
"""

import os
import shutil
import tempfile
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.redis_client import get_arq_redis_settings
from core.minio_client import download_file, upload_file, list_objects, ensure_bucket
from core.logger import setup_custom_logger

logger = setup_custom_logger("workers.tasks")

# ── Constants ─────────────────────────────────────────────
DATASETS_BUCKET = "datasets"
MODELS_BUCKET = "models"
LOG_DIR = Path(os.environ.get("LOG_DIR", "/logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ── Trainer Callback (เขียน log ทุก step/epoch) ───────────

def _make_log_callback(log_path: Path):
    """
    สร้าง TrainerCallback ที่เขียน training log ลงไฟล์ทุก step/epoch
    เป็น closure เพื่อให้ log_path ถูก capture ไว้
    """
    from transformers import TrainerCallback

    class FileLogCallback(TrainerCallback):
        def __init__(self):
            self._fh = open(log_path, "w", encoding="utf-8")
            self._fh.write(f"Training started at {datetime.now(timezone.utc).isoformat()}\n")
            self._fh.write("-" * 60 + "\n")
            self._fh.flush()

        def on_log(self, args, state, control, logs=None, **kwargs):
            if logs:
                line = json.dumps({"step": state.global_step, **logs})
                self._fh.write(line + "\n")
                self._fh.flush()

        def on_epoch_end(self, args, state, control, **kwargs):
            self._fh.write(
                f"[epoch {state.epoch:.1f}] step={state.global_step}\n"
            )
            self._fh.flush()

        def on_train_end(self, args, state, control, **kwargs):
            self._fh.write("-" * 60 + "\n")
            self._fh.write(f"Training ended at {datetime.now(timezone.utc).isoformat()}\n")
            self._fh.close()

    return FileLogCallback()


# ── Label alignment (subword -> -100) ─────────────────────

def _align_labels_with_tokens(labels, word_ids):
    """
    แปลง word-level labels ให้ตรงกับ subword tokens
    token ที่ไม่ใช่ word เริ่มต้น (e.g. ##ing) ใช้ label -100 (ignored in loss)
    """
    new_labels = []
    current_word = None
    for word_id in word_ids:
        if word_id is None:
            new_labels.append(-100)
        elif word_id != current_word:
            current_word = word_id
            new_labels.append(labels[word_id])
        else:
            # subword token ของ word เดิม
            new_labels.append(-100)
    return new_labels


def _tokenize_and_align(examples, tokenizer, label_col: str):
    """Tokenize batch พร้อม align labels สำหรับ Token Classification"""
    tokenized = tokenizer(
        examples["tokens"],
        truncation=True,
        is_split_into_words=True,
        padding="max_length",
        max_length=128,
    )
    all_labels = []
    for i, labels in enumerate(examples[label_col]):
        word_ids = tokenized.word_ids(batch_index=i)
        all_labels.append(_align_labels_with_tokens(labels, word_ids))
    tokenized["labels"] = all_labels
    return tokenized


# ── Main worker function ───────────────────────────────────

async def train_model(
    ctx: dict,
    dataset_name: str,
    model_name: str,
    base_model: str = "bert-base-cased",
    num_epochs: int = 3,
    batch_size: int = 8,
    max_steps: int = -1,
    user_id: str = "system",
) -> dict[str, Any]:
    """
    ARQ worker function: fine-tune Token Classification model

    Args:
        ctx:          ARQ context (ไม่ใช้ในงานนี้ แต่ ARQ ต้องการเป็น arg แรก)
        dataset_name: ชื่อ dataset ใน MinIO 'datasets/' bucket
        model_name:   ชื่อโมเดลที่จะบันทึกลง MinIO 'models/' bucket
        base_model:   HuggingFace model ID สำหรับ fine-tune
        num_epochs:   จำนวน epoch
        batch_size:   Batch size ต่อ step
        max_steps:    จำกัด step (-1 = ตาม num_epochs)
        user_id:      UUID ของ user ที่ submit job

    Returns:
        summary dict พร้อม metrics และ MinIO path
    """
    job_id = ctx.get("job_id", "unknown")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"train_{job_id}.log"
    workdir = Path(tempfile.mkdtemp(prefix=f"train_{job_id}_"))

    logger.info(
        f"[train_model] START job_id={job_id} dataset={dataset_name} "
        f"model={model_name} base={base_model} epochs={num_epochs} user={user_id}"
    )

    try:
        # ── Step 1: Download dataset parquet files จาก MinIO ──
        logger.info(f"[train_model] Downloading dataset '{dataset_name}' from MinIO...")
        dataset_dir = workdir / "dataset"
        dataset_dir.mkdir()

        objects = list_objects(DATASETS_BUCKET, prefix=f"{dataset_name}/")
        if not objects:
            raise FileNotFoundError(
                f"No files found in MinIO bucket '{DATASETS_BUCKET}/{dataset_name}/' "
                f"— run scripts/load_hf_dataset_to_minio.py first"
            )

        local_parquets: dict[str, str] = {}  # split -> local_path
        for obj_name in objects:
            split = Path(obj_name).stem  # e.g. "train", "validation", "test"
            local_path = str(dataset_dir / Path(obj_name).name)
            download_file(DATASETS_BUCKET, obj_name, local_path)
            local_parquets[split] = local_path
            logger.info(f"[train_model] Downloaded split '{split}' -> {local_path}")

        # ── Step 2: Load HuggingFace Dataset ──
        from datasets import DatasetDict, load_dataset  # type: ignore

        logger.info("[train_model] Loading dataset from parquet files...")
        data_files = {split: path for split, path in local_parquets.items()}
        raw_datasets = load_dataset("parquet", data_files=data_files)

        # ตรวจหา label column (ner_tags หรือ labels หรือ ner_labels)
        sample = raw_datasets[list(raw_datasets.keys())[0]]
        label_col = None
        for candidate in ["ner_tags", "labels", "ner_labels", "pos_tags"]:
            if candidate in sample.column_names:
                label_col = candidate
                break
        if label_col is None:
            raise ValueError(
                f"Cannot find NER label column. Available: {sample.column_names}"
            )

        # ตรวจสอบว่ามี 'tokens' column
        if "tokens" not in sample.column_names:
            raise ValueError(
                f"Cannot find 'tokens' column. Available: {sample.column_names}"
            )

        # สร้าง label2id / id2label จาก train split
        train_split = raw_datasets.get("train", list(raw_datasets.values())[0])
        all_label_ids: set[int] = set()
        for row in train_split[label_col]:
            all_label_ids.update(row)
        sorted_ids = sorted(all_label_ids)

        # พยายาม decode label names จาก ClassLabel feature
        try:
            feature = train_split.features[label_col]
            if hasattr(feature, "feature"):
                feature = feature.feature  # Sequence wrapping
            id2label = {i: feature.int2str(i) for i in sorted_ids}
        except Exception:
            id2label = {i: str(i) for i in sorted_ids}
        label2id = {v: k for k, v in id2label.items()}

        logger.info(f"[train_model] Labels ({len(id2label)}): {id2label}")

        # ── Step 3: Tokenize + Align Labels ──
        from transformers import AutoTokenizer  # type: ignore

        logger.info(f"[train_model] Tokenizing with {base_model}...")
        tokenizer = AutoTokenizer.from_pretrained(base_model)

        tokenized_datasets = raw_datasets.map(
            lambda examples: _tokenize_and_align(examples, tokenizer, label_col),
            batched=True,
            remove_columns=raw_datasets[list(raw_datasets.keys())[0]].column_names,
        )

        # ── Step 4: Setup Model ──
        from transformers import (  # type: ignore
            AutoModelForTokenClassification,
            DataCollatorForTokenClassification,
            TrainingArguments,
            Trainer,
        )

        logger.info(f"[train_model] Loading model {base_model}...")
        model = AutoModelForTokenClassification.from_pretrained(
            base_model,
            num_labels=len(id2label),
            id2label=id2label,
            label2id=label2id,
            ignore_mismatched_sizes=True,
        )

        data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)
        output_dir = str(workdir / "model_output")

        # ── Step 5: Training Arguments + Log Callback ──
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            max_steps=max_steps if max_steps > 0 else -1,
            logging_steps=10,
            save_strategy="no",          # ไม่ save checkpoint ระหว่างทาง (save ทีเดียวตอนจบ)
            eval_strategy="epoch" if "validation" in tokenized_datasets else "no",
            load_best_model_at_end=False,
            report_to="none",            # ไม่ใช้ wandb/mlflow
            fp16=False,                  # GPU build สามารถเปิด fp16=True ได้
            push_to_hub=False,
        )

        log_callback = _make_log_callback(log_path)

        # ── Step 6: Evaluate function (seqeval) ──
        import evaluate  # type: ignore
        import numpy as np  # type: ignore

        metric = evaluate.load("seqeval")

        def compute_metrics(p):
            predictions, labels = p
            predictions = np.argmax(predictions, axis=2)
            true_labels = [
                [id2label[l] for l in label if l != -100]
                for label in labels
            ]
            true_predictions = [
                [id2label[pred] for pred, l in zip(prediction, label) if l != -100]
                for prediction, label in zip(predictions, labels)
            ]
            results = metric.compute(
                predictions=true_predictions, references=true_labels
            )
            return {
                "precision": results["overall_precision"],
                "recall":    results["overall_recall"],
                "f1":        results["overall_f1"],
                "accuracy":  results["overall_accuracy"],
            }

        # ── Training ──
        eval_dataset = tokenized_datasets.get("validation") if "validation" in tokenized_datasets else None
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_datasets["train"],
            eval_dataset=eval_dataset,
            tokenizer=tokenizer,
            data_collator=data_collator,
            compute_metrics=compute_metrics if eval_dataset else None,
            callbacks=[log_callback],
        )

        logger.info("[train_model] Training started...")
        train_result = trainer.train()
        logger.info(f"[train_model] Training done: {train_result.metrics}")

        # ── Step 7: Save model + tokenizer ──
        logger.info("[train_model] Saving model...")
        trainer.save_model(output_dir)
        tokenizer.save_pretrained(output_dir)

        # บันทึก label map
        label_map_path = os.path.join(output_dir, "label_map.json")
        with open(label_map_path, "w", encoding="utf-8") as f:
            json.dump({"id2label": {str(k): v for k, v in id2label.items()}, "label2id": label2id}, f, indent=2)

        # ── Step 8: Upload model + log -> MinIO ──
        minio_prefix = f"{model_name}/v{timestamp}"
        ensure_bucket(MODELS_BUCKET)

        # upload ทุกไฟล์ในโฟลเดอร์ model_output
        for f in Path(output_dir).rglob("*"):
            if f.is_file():
                rel = f.relative_to(output_dir)
                obj_name = f"{minio_prefix}/{rel}"
                upload_file(MODELS_BUCKET, obj_name, str(f))

        # upload training log
        log_obj = f"{minio_prefix}/train.log"
        upload_file(MODELS_BUCKET, log_obj, str(log_path), content_type="text/plain")

        logger.info(f"[train_model] Uploaded to MinIO: {MODELS_BUCKET}/{minio_prefix}/")

        # summary
        metrics = train_result.metrics
        summary = {
            "status": "complete",
            "job_id": job_id,
            "model_name": model_name,
            "dataset_name": dataset_name,
            "base_model": base_model,
            "minio_path": f"{MODELS_BUCKET}/{minio_prefix}/",
            "log_path": f"{MODELS_BUCKET}/{log_obj}",
            "num_labels": len(id2label),
            "train_runtime_sec": round(metrics.get("train_runtime", 0), 1),
            "train_loss": round(metrics.get("train_loss", 0), 4),
            "timestamp_utc": timestamp,
        }
        logger.info(f"[train_model] DONE: {summary}")
        return summary

    except Exception as e:
        logger.error(f"[train_model] FAILED job_id={job_id}: {e}", exc_info=True)
        # เขียน error ลง log file
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n[ERROR] {datetime.now(timezone.utc).isoformat()}: {e}\n")
            upload_file(MODELS_BUCKET, f"{model_name}/v{timestamp}/train.log", str(log_path), content_type="text/plain")
        except Exception:
            pass
        raise

    finally:
        # ล้าง workdir ชั่วคราว
        shutil.rmtree(workdir, ignore_errors=True)


# ── Worker Settings ────────────────────────────────────────

class WorkerSettings:
    """
    ARQ WorkerSettings — ถูกใช้โดย Dockerfile.trainer ผ่าน:
      arq app.features.workers.tasks.WorkerSettings

    job_timeout=7200 เพราะงานเทรน BERT อาจใช้เวลา 1-2 ชั่วโมง
    max_jobs=1 เพราะ GPU มีจำนวนจำกัด (1 job ต่อ GPU ต่อ worker instance)
    """
    functions = [train_model]
    redis_settings = get_arq_redis_settings()
    job_timeout = 7200   # 2 ชั่วโมง
    max_jobs = 1          # จำกัด concurrency เพราะ GPU
