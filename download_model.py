#!/usr/bin/env python3
"""
Script to download a small LLM model for task decomposition.
Model: Qwen2.5-0.5B-Instruct in GGUF format (quantized)
License: Apache 2.0
Size: ~491MB (Q4_K_M quantized GGUF format)

This script downloads the model and saves it locally for offline inference.
Using GGUF format with llama-cpp-python for efficient CPU inference.

Note: Requires at least 600MB of free disk space for download and extraction.
Run with: python download_model.py
Verify with: python download_model.py --verify
"""

import os
import sys
from huggingface_hub import hf_hub_download

# Model configuration - using quantized GGUF format for smaller size
# Qwen2.5-0.5B is a compact instruction-tuned model suitable for task decomposition
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
MODEL_FILE = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
LOCAL_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
LOCAL_MODEL_FILE = os.path.join(LOCAL_MODEL_PATH, MODEL_FILE)

def check_disk_space(required_mb=600):
    """Check if there's enough disk space available."""
    import shutil
    workspace_path = os.path.dirname(os.path.abspath(__file__))
    total, used, free = shutil.disk_usage(workspace_path)
    free_mb = free / (1024 * 1024)
    
    print(f"Available disk space: {free_mb:.2f} MB")
    print(f"Required space: ~{required_mb} MB")
    print(f"Model file size: ~491 MB")
    print(f"Buffer for operations: ~100 MB")
    
    if free_mb < required_mb:
        print(f"\nWARNING: Insufficient disk space!")
        print(f"Please free up at least {required_mb - free_mb:.2f} MB more.")
        print(f"\nTips to free space:")
        print(f"  - Clear pip cache: pip cache purge")
        print(f"  - Clear system cache: rm -rf ~/.cache/*")
        print(f"  - Remove unused packages")
        return False
    return True

def download_model():
    """Download the model from Hugging Face Hub."""
    print(f"\nDownloading model: {MODEL_NAME}")
    print(f"File: {MODEL_FILE}")
    print(f"Target directory: {LOCAL_MODEL_PATH}")
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(LOCAL_MODEL_PATH, exist_ok=True)
        
        # Download the single GGUF file
        downloaded_path = hf_hub_download(
            repo_id=MODEL_NAME,
            filename=MODEL_FILE,
            local_dir=LOCAL_MODEL_PATH,
            force_download=False,
            resume_download=True,
        )
        
        print(f"\n✓ Model successfully downloaded to: {downloaded_path}")
        
        # Show file size
        size_mb = os.path.getsize(downloaded_path) / (1024 * 1024)
        print(f"✓ File size: {size_mb:.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error downloading model: {e}")
        return False

def verify_model():
    """Verify that the model can be loaded."""
    print("\n" + "=" * 60)
    print("Verifying model...")
    print("=" * 60)
    
    if not os.path.exists(LOCAL_MODEL_FILE):
        print(f"✗ Model file not found: {LOCAL_MODEL_FILE}")
        print("Please run 'python download_model.py' first.")
        return False
    
    try:
        from llama_cpp import Llama
        
        print(f"Loading model from: {LOCAL_MODEL_FILE}")
        llm = Llama(
            model_path=LOCAL_MODEL_FILE,
            n_ctx=512,
            n_threads=2,
            verbose=False
        )
        
        print("✓ Model verification successful!")
        print(f"✓ Context window: 512 tokens")
        print(f"✓ Ready for inference")
        return True
        
    except ImportError as e:
        print(f"✗ llama-cpp-python not installed: {e}")
        print("Install with: pip install llama-cpp-python")
        return False
    except Exception as e:
        print(f"✗ Model verification failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Qwen2.5-0.5B-Instruct GGUF Model Downloader")
    print("=" * 60)
    print("\nThis script downloads a compact LLM for task decomposition.")
    print("The model will be stored locally for offline inference.\n")
    
    # Check disk space first
    if not check_disk_space(600):
        print("\nAborting due to insufficient disk space.")
        sys.exit(1)
    
    # Download the model
    if download_model():
        print("\n✓ Download complete!")
        print("\nTo verify the model, run:")
        print("  python download_model.py --verify\n")
        # Optionally verify
        if len(sys.argv) > 1 and sys.argv[1] == "--verify":
            verify_model()
    else:
        print("\n✗ Download failed!")
        sys.exit(1)
