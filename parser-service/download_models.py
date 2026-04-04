"""
VendorAuditAI — One-time model download into the Modal persistent volume.

Run this ONCE before deploying modal_app.py.  It downloads ~1 GB of
DeepDoc model weights from HuggingFace into the 'vendorauditai-models'
volume so that live parse requests never block on a download.

Usage
-----
    modal run download_models.py

What gets downloaded
--------------------
  InfiniFlow/deepdoc
    det.onnx          OCR text detection model
    rec.onnx          OCR text recognition model
    ocr.res           OCR character dictionary
    layout.onnx       YOLOv10 layout recognition model
    tsr.onnx          Table structure recognition model
    (+ any auxiliary config files in the repo)

  InfiniFlow/text_concat_xgb_v1.0
    updown_concat_xgb.model    XGBoost PDF line-ordering model

All files land at /vol/rag/res/deepdoc/ which matches the path DeepDoc
resolves when RAG_PROJECT_BASE=/vol is set in the container.
"""

from pathlib import Path

import modal

# Must match the volume name used in modal_app.py
models_volume = modal.Volume.from_name("vendorauditai-models", create_if_missing=True)

VOLUME_PATH = Path("/vol")
MODELS_PATH = VOLUME_PATH / "rag" / "res" / "deepdoc"

app = modal.App("vendorauditai-model-downloader")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("huggingface_hub>=0.24.0")
)


@app.function(
    image=image,
    volumes={str(VOLUME_PATH): models_volume},
    timeout=600,                    # HuggingFace download can be slow
    memory=4096,
)
def download_models():
    """Download all DeepDoc model weights into the persistent volume."""
    from huggingface_hub import snapshot_download

    MODELS_PATH.mkdir(parents=True, exist_ok=True)

    repos = [
        (
            "InfiniFlow/deepdoc",
            "OCR + layout recognition + table structure models",
        ),
        (
            "InfiniFlow/text_concat_xgb_v1.0",
            "XGBoost PDF line-ordering model",
        ),
    ]

    for repo_id, description in repos:
        print(f"\nDownloading {repo_id}")
        print(f"  {description}")
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(MODELS_PATH),
            local_dir_use_symlinks=False,
        )
        print(f"  Done.")

    # Commit so the volume reflects the new files immediately
    models_volume.commit()

    # Print what landed in the volume
    print("\nFiles in volume:")
    total_mb = 0
    for f in sorted(MODELS_PATH.rglob("*")):
        if f.is_file():
            size_mb = f.stat().st_size / (1024 * 1024)
            total_mb += size_mb
            print(f"  {f.relative_to(VOLUME_PATH)}  ({size_mb:.1f} MB)")
    print(f"\nTotal: {total_mb:.1f} MB")


@app.local_entrypoint()
def main():
    download_models.remote()
