#!/usr/bin/env python3
"""
Download MinerU models from Hugging Face to persistent storage.
Uses huggingface_hub for reliable incremental downloads.

IMPORTANT: Downloads directly to /root/cache/models (persistent disk).

Usage:
    python download_models.py [--force]
"""
import os
import sys
import shutil

# Model storage location (Render persistent disk mounted at /root/cache)
MODELS_DIR = os.environ.get("MINERU_MODELS_DIR", "/root/cache/models")

# Set HF cache to persistent disk to avoid filling /tmp
os.environ["HF_HOME"] = "/root/cache/huggingface"
os.environ["HF_HUB_CACHE"] = "/root/cache/huggingface/hub"

# Hugging Face model repository
HF_REPO = "wanderkid/PDF-Extract-Kit"


def check_models_exist() -> bool:
    """Check if essential models are already downloaded."""
    if not os.path.exists(MODELS_DIR):
        print(f"[Models] Directory does not exist: {MODELS_DIR}")
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
        else:
            size = os.path.getsize(full_path)
            print(f"[Models] Found: {key_file} ({size / 1024 / 1024:.1f} MB)")
    
    print(f"[Models] Essential models found in {MODELS_DIR}")
    return True


def download_models():
    """Download models using huggingface_hub directly to persistent disk."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("[Models] Installing huggingface_hub...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "huggingface_hub"], check=True)
        from huggingface_hub import snapshot_download
    
    print(f"[Models] Target directory: {MODELS_DIR}")
    print(f"[Models] HF_HOME: {os.environ.get('HF_HOME')}")
    
    # Ensure directories exist
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(os.environ["HF_HOME"], exist_ok=True)
    
    try:
        print(f"[Models] Downloading from {HF_REPO}...")
        print(f"[Models] This will take a while (~10GB)...")
        
        # Download to a temp location first, then move
        temp_download_dir = "/root/cache/hf_download_temp"
        os.makedirs(temp_download_dir, exist_ok=True)
        
        # Download the entire repo
        local_dir = snapshot_download(
            repo_id=HF_REPO,
            local_dir=temp_download_dir,
            local_dir_use_symlinks=False,
            cache_dir=os.environ["HF_HUB_CACHE"],
        )
        
        print(f"[Models] Downloaded to: {local_dir}")
        
        # List what was downloaded
        print(f"[Models] Contents of download dir:")
        for item in os.listdir(local_dir):
            item_path = os.path.join(local_dir, item)
            if os.path.isdir(item_path):
                print(f"  [DIR] {item}/")
            else:
                size = os.path.getsize(item_path)
                print(f"  [FILE] {item} ({size / 1024 / 1024:.1f} MB)")
        
        # Move models directory to final location
        src_models = os.path.join(local_dir, "models")
        if os.path.exists(src_models):
            print(f"[Models] Moving models from {src_models} to {MODELS_DIR}")
            
            # Remove existing if any
            if os.path.exists(MODELS_DIR):
                shutil.rmtree(MODELS_DIR)
            
            # Move models
            shutil.move(src_models, MODELS_DIR)
            print(f"[Models] Models moved successfully!")
            
            # List final contents
            print(f"[Models] Final contents of {MODELS_DIR}:")
            for item in os.listdir(MODELS_DIR):
                print(f"  {item}/")
        else:
            # Models might be at root level
            print(f"[Models] No 'models' subdir found, checking root level...")
            
            # Check if model files are at root
            for item in ["Layout", "MFD", "OCR", "MFR", "TabRec"]:
                src = os.path.join(local_dir, item)
                if os.path.exists(src):
                    dst = os.path.join(MODELS_DIR, item)
                    print(f"[Models] Moving {item} to {dst}")
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.move(src, dst)
        
        # Cleanup temp download dir
        if os.path.exists(temp_download_dir):
            shutil.rmtree(temp_download_dir)
        
        print("[Models] Download complete!")
        return True
        
    except Exception as e:
        print(f"[Models] Download error: {e}")
        import traceback
        traceback.print_exc()
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


def show_disk_usage():
    """Show disk usage for debugging."""
    import subprocess
    print("\n[Models] Disk usage:")
    subprocess.run(["df", "-h", "/root/cache"], check=False)
    print("\n[Models] Directory sizes in /root/cache:")
    subprocess.run(["du", "-sh", "/root/cache/*"], shell=True, check=False)


def main():
    force = "--force" in sys.argv
    
    print(f"[Models] ========================================")
    print(f"[Models] MinerU Model Downloader")
    print(f"[Models] ========================================")
    print(f"[Models] Models directory: {MODELS_DIR}")
    print(f"[Models] Force download: {force}")
    
    show_disk_usage()
    
    if force or not check_models_exist():
        success = download_models()
        if not success:
            print("[Models] WARNING: Download failed. Tesseract fallback will be used.")
            show_disk_usage()
            sys.exit(1)
    
    create_config()
    show_disk_usage()
    print("[Models] Ready!")


if __name__ == "__main__":
    main()
