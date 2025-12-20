#!/usr/bin/env python3
"""
Download MinerU models from Hugging Face to persistent storage.
Run this script on first deployment or when models need updating.

Models are downloaded to /data/models (Render persistent disk).
The magic-pdf.json config points to this location.

Usage:
    python download_models.py [--force]
    
Options:
    --force    Re-download even if models exist
"""
import os
import sys
import shutil
import subprocess

# Model storage location (Render persistent disk)
MODELS_DIR = os.environ.get("MINERU_MODELS_DIR", "/data/models")

# Hugging Face model repository
HF_REPO = "wanderkid/PDF-Extract-Kit"

# Required model subdirectories
REQUIRED_MODELS = [
    "MFD",      # Formula detection
    "Layout",   # Layout analysis
    "OCR",      # OCR models
]


def check_models_exist() -> bool:
    """Check if models are already downloaded."""
    if not os.path.exists(MODELS_DIR):
        return False
    
    for model in REQUIRED_MODELS:
        model_path = os.path.join(MODELS_DIR, model)
        if not os.path.exists(model_path):
            print(f"[Models] Missing: {model}")
            return False
    
    print(f"[Models] All models found in {MODELS_DIR}")
    return True


def download_models():
    """Download models from Hugging Face using git lfs."""
    print(f"[Models] Downloading models to {MODELS_DIR}...")
    
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(MODELS_DIR), exist_ok=True)
    
    # Clone with git lfs
    try:
        # First, check if git-lfs is available
        subprocess.run(["git", "lfs", "version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[Models] ERROR: git-lfs not installed. Installing...")
        subprocess.run(["apt-get", "update"], check=True)
        subprocess.run(["apt-get", "install", "-y", "git-lfs"], check=True)
        subprocess.run(["git", "lfs", "install"], check=True)
    
    # Clone the repository
    temp_dir = "/tmp/pdf-extract-kit"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    print(f"[Models] Cloning {HF_REPO}...")
    subprocess.run([
        "git", "clone", "--depth", "1",
        f"https://huggingface.co/{HF_REPO}",
        temp_dir
    ], check=True)
    
    # Move models to persistent storage
    src_models = os.path.join(temp_dir, "models")
    if os.path.exists(src_models):
        if os.path.exists(MODELS_DIR):
            shutil.rmtree(MODELS_DIR)
        shutil.move(src_models, MODELS_DIR)
        print(f"[Models] Models installed to {MODELS_DIR}")
    else:
        raise Exception(f"Models directory not found in {temp_dir}")
    
    # Cleanup
    shutil.rmtree(temp_dir)
    
    print("[Models] Download complete!")


def create_config():
    """Create magic-pdf.json config pointing to persistent models."""
    config_path = "/root/magic-pdf.json"
    config_content = f'''{{
    "device-mode": "cpu",
    "models-dir": "{MODELS_DIR}",
    "table-config": {{
        "model": "rapid_table",
        "enable": false
    }},
    "formula-config": {{
        "model": "unimernet_small",
        "enable": true
    }},
    "layout-config": {{
        "model": "layoutlmv3"
    }}
}}'''
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    print(f"[Models] Config written to {config_path}")


def main():
    force = "--force" in sys.argv
    
    if force or not check_models_exist():
        download_models()
    
    create_config()
    print("[Models] Ready!")


if __name__ == "__main__":
    main()
