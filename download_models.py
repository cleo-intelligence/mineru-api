#!/usr/bin/env python3
"""
Download MinerU models from Hugging Face to persistent storage.
Uses huggingface_hub for reliable incremental downloads.

Usage:
    python download_models.py [--force]
"""
import os
import sys

# Model storage location (Render persistent disk mounted at /root/cache)
MODELS_DIR = os.environ.get("MINERU_MODELS_DIR", "/root/cache/models")

# Hugging Face model repository
HF_REPO = "wanderkid/PDF-Extract-Kit"

# Only download essential models for CPU mode (skip GPU-only models)
ESSENTIAL_SUBDIRS = [
    "Layout/LayoutLMv3",
    "MFD/YOLO",
    "OCR",
]


def check_models_exist() -> bool:
    """Check if essential models are already downloaded."""
    if not os.path.exists(MODELS_DIR):
        return False
    
    # Check for key model files
    key_files = [
        "Layout/LayoutLMv3/model_final.pth",
        "MFD/YOLO/yolo_v8_ft.pt",
    ]
    
    for key_file in key_files:
        full_path = os.path.join(MODELS_DIR, key_file)
        if not os.path.exists(full_path):
            print(f"[Models] Missing: {key_file}")
            return False
    
    print(f"[Models] Essential models found in {MODELS_DIR}")
    return True


def download_models():
    """Download models using huggingface_hub (more reliable than git clone)."""
    try:
        from huggingface_hub import snapshot_download, hf_hub_download
    except ImportError:
        print("[Models] Installing huggingface_hub...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "huggingface_hub"], check=True)
        from huggingface_hub import snapshot_download, hf_hub_download
    
    print(f"[Models] Downloading models to {MODELS_DIR}...")
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    # Download only the models subdirectory
    try:
        print(f"[Models] Downloading from {HF_REPO}...")
        
        # Use snapshot_download with allow_patterns to get only models/
        local_dir = snapshot_download(
            repo_id=HF_REPO,
            local_dir=MODELS_DIR,
            local_dir_use_symlinks=False,
            allow_patterns=["models/**"],
            ignore_patterns=["*.md", "*.txt", "*.json", ".git*"],
        )
        
        # The files are downloaded to MODELS_DIR/models/, move them up
        downloaded_models = os.path.join(MODELS_DIR, "models")
        if os.path.exists(downloaded_models):
            import shutil
            for item in os.listdir(downloaded_models):
                src = os.path.join(downloaded_models, item)
                dst = os.path.join(MODELS_DIR, item)
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.move(src, dst)
            os.rmdir(downloaded_models)
        
        print(f"[Models] Download complete!")
        return True
        
    except Exception as e:
        print(f"[Models] Download error: {e}")
        print("[Models] Trying alternative download method...")
        
        # Fallback: download individual essential files
        try:
            essential_files = [
                "models/Layout/LayoutLMv3/model_final.pth",
                "models/Layout/LayoutLMv3/config.json",
                "models/MFD/YOLO/yolo_v8_ft.pt",
            ]
            
            for file_path in essential_files:
                print(f"[Models] Downloading {file_path}...")
                local_path = hf_hub_download(
                    repo_id=HF_REPO,
                    filename=file_path,
                    local_dir=MODELS_DIR,
                    local_dir_use_symlinks=False,
                )
                print(f"[Models] Downloaded to {local_path}")
            
            return True
        except Exception as e2:
            print(f"[Models] Fallback download also failed: {e2}")
            return False


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
    
    print(f"[Models] Models directory: {MODELS_DIR}")
    print(f"[Models] Force download: {force}")
    
    if force or not check_models_exist():
        success = download_models()
        if not success:
            print("[Models] WARNING: Download failed. Tesseract fallback will be used.")
            sys.exit(1)
    
    create_config()
    print("[Models] Ready!")


if __name__ == "__main__":
    main()
