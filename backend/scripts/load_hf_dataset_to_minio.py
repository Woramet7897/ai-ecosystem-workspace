"""
scripts/load_hf_dataset_to_minio.py — Load HuggingFace dataset into MinIO

รันครั้งเดียวตอน setup เพื่อเตรียม training data ใน MinIO

Usage:
    uv run python scripts/load_hf_dataset_to_minio.py --dataset eriktks/conll2003

Flow:
    1. Download dataset จาก HuggingFace Hub (ใช้ id แบบ namespace เช่น eriktks/conll2003
       เพื่อเลี่ยงปัญหา loading-script ใน datasets v4+)
    2. Save แต่ละ split เป็น .parquet
    3. Upload ขึ้น MinIO bucket 'datasets/{dataset_name}/{split}.parquet'
"""

import argparse
import sys
import tempfile
from pathlib import Path

# เพิ่ม backend root เข้า sys.path เพื่อ import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from datasets import load_dataset  # type: ignore
except ImportError:
    print("[ERROR] datasets not installed. Run: uv add datasets")
    sys.exit(1)

from core.minio_client import upload_file, ensure_bucket
from core.logger import setup_custom_logger

logger = setup_custom_logger("load_hf_dataset")

DATASETS_BUCKET = "datasets"


def load_and_upload(hf_dataset_id: str, dataset_name: str | None = None) -> None:
    """
    Download dataset จาก HuggingFace แล้ว upload แต่ละ split ขึ้น MinIO

    Args:
        hf_dataset_id:  HuggingFace dataset ID เช่น 'eriktks/conll2003'
        dataset_name:   ชื่อโฟลเดอร์ใน MinIO (default: ส่วนหลังของ hf_dataset_id)
    """
    if dataset_name is None:
        dataset_name = hf_dataset_id.split("/")[-1]

    print(f"[INFO] Loading '{hf_dataset_id}' from HuggingFace Hub...")
    print(f"[INFO] Will upload to MinIO: {DATASETS_BUCKET}/{dataset_name}/")

    try:
    # ใช้ revision="refs/convert/parquet" เพื่อดึงเวอร์ชัน parquet ที่ HF
    # auto-convert ให้ทุก dataset — เลี่ยงปัญหา loading-script ที่ datasets v4+
    # เลิกรองรับแล้ว (repo เดิมยังมีไฟล์ conll2003.py แนบอยู่)
        raw_datasets = load_dataset(
        hf_dataset_id,
        revision="refs/convert/parquet",
        trust_remote_code=False,
    )
    except Exception as e:
        print(f"[ERROR] Failed to load dataset: {e}")
        sys.exit(1)

    ensure_bucket(DATASETS_BUCKET)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        splits = list(raw_datasets.keys())
        print(f"[INFO] Splits found: {splits}")

        for split in splits:
            parquet_path = tmp / f"{split}.parquet"
            print(f"[INFO] Saving split '{split}' to {parquet_path}...")
            raw_datasets[split].to_parquet(str(parquet_path))

            obj_name = f"{dataset_name}/{split}.parquet"
            print(f"[INFO] Uploading {obj_name} -> MinIO bucket '{DATASETS_BUCKET}'...")
            upload_file(
                DATASETS_BUCKET,
                obj_name,
                str(parquet_path),
                content_type="application/octet-stream",
            )
            print(f"[OK] Uploaded {obj_name} ({parquet_path.stat().st_size // 1024} KB)")

    print(f"\n[OK] All splits uploaded to MinIO: {DATASETS_BUCKET}/{dataset_name}/")
    print(f"[INFO] Now you can train with: POST /training/queue dataset_name={dataset_name!r}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load HuggingFace dataset and upload to MinIO"
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="HuggingFace dataset ID e.g. 'eriktks/conll2003'",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Override dataset folder name in MinIO (default: last part of --dataset)",
    )
    args = parser.parse_args()
    load_and_upload(args.dataset, args.name)


if __name__ == "__main__":
    main()
