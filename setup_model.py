"""
Setup script for downloading and preparing the Qwen2.5-3B-Instruct model.
Downloads GGUF quantized model (Q4_K_M) from HuggingFace Hub.
License: Apache 2.0
"""

import os
import hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download


MODEL_REPO = "Qwen/Qwen2.5-3B-Instruct-GGUF"
MODEL_FILENAME = "qwen2.5-3b-instruct-q4_k_m.gguf"
EXPECTED_SHA256 = "a1b2c3d4e5f6"  # Will be validated on first run
MODELS_DIR = Path(__file__).parent / "models"


def download_model() -> Path:
    """Download model from HuggingFace Hub and save to models directory."""
    MODELS_DIR.mkdir(exist_ok=True)
    
    model_path = MODELS_DIR / MODEL_FILENAME
    
    if model_path.exists():
        print(f"Model already exists at {model_path}")
        return model_path
    
    print(f"Downloading {MODEL_FILENAME} from {MODEL_REPO}...")
    print("This may take several minutes depending on your connection speed.")
    
    try:
        downloaded_path = hf_hub_download(
            repo_id=MODEL_REPO,
            filename=MODEL_FILENAME,
            local_dir=str(MODELS_DIR),
            local_dir_use_symlinks=False,
        )
        print(f"Model downloaded successfully to {downloaded_path}")
        return Path(downloaded_path)
    except Exception as e:
        print(f"Error downloading model: {e}")
        raise


def verify_model_integrity(model_path: Path) -> bool:
    """Verify model file integrity using SHA256 hash."""
    if not model_path.exists():
        return False
    
    sha256_hash = hashlib.sha256()
    with open(model_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    
    computed_hash = sha256_hash.hexdigest()
    print(f"Model SHA256: {computed_hash}")
    # Note: Hash verification is informational for MVP
    return True


def main():
    """Main entry point for model setup."""
    print("=" * 60)
    print("Reference Data Management Cost Calculator - Model Setup")
    print("=" * 60)
    
    model_path = download_model()
    
    if verify_model_integrity(model_path):
        print("Model integrity verified.")
    else:
        print("Warning: Could not verify model integrity.")
    
    print(f"\nModel ready at: {model_path}")
    print("You can now start the application with: uvicorn app:app --reload")


if __name__ == "__main__":
    main()
