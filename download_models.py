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

# Official Hugging Face model repository (has correct structure)
HF_REPO = "opendatalab/PDF-Extract-Kit"


def check_models_exist() -> bool:
    """Check if essential models are already downloaded."""
    if not os.path.exists(MODELS_DIR):
        print(f"[Models] Directory does not exist: {MODELS_DIR}")
        return False
    
    # Check for key model files (MinerU expected paths)
    # MinerU magic-pdf expects these specific paths
    key_files = [
        "Layout/LayoutLMv3/model_final.pth",
        "MFD/YOLO/yolo_v8_ft.pt",
    ]
    
    all_found = True
    for key_file in key_files:
        full_path = os.path.join(MODELS_DIR, key_file)
        if not os.path.exists(full_path):
            print(f"[Models] Missing: {key_file}")
            all_found = False
        else:
            size = os.path.getsize(full_path)
            print(f"[Models] Found: {key_file} ({size / 1024 / 1024:.1f} MB)")
    
    if all_found:
        print(f"[Models] Essential models found in {MODELS_DIR}")
    return all_found


def create_directory_structure():
    """
    Create the directory structure expected by MinerU magic-pdf.
    The downloaded models might have a flat structure, but magic-pdf expects:
    - Layout/LayoutLMv3/model_final.pth
    - MFD/YOLO/yolo_v8_ft.pt
    - etc.
    """
    print(f"[Models] Checking and fixing directory structure...")
    
    # Show current structure
    print(f"[Models] Current structure of {MODELS_DIR}:")
    for root, dirs, files in os.walk(MODELS_DIR):
        level = root.replace(MODELS_DIR, '').count(os.sep)
        indent = '  ' * level
        folder = os.path.basename(root) or MODELS_DIR
        print(f"{indent}{folder}/")
        for f in files[:5]:
            size = os.path.getsize(os.path.join(root, f))
            print(f"{indent}  {f} ({size / 1024 / 1024:.1f} MB)")
        if len(files) > 5:
            print(f"{indent}  ... and {len(files) - 5} more files")
    
    # Create required subdirectories if they don't exist
    # MinerU expects: Layout/LayoutLMv3/, MFD/YOLO/, etc.
    
    # Check if Layout/model_final.pth exists but Layout/LayoutLMv3 doesn't
    layout_flat = os.path.join(MODELS_DIR, "Layout", "model_final.pth")
    layout_nested = os.path.join(MODELS_DIR, "Layout", "LayoutLMv3", "model_final.pth")
    
    if os.path.exists(layout_flat) and not os.path.exists(layout_nested):
        print(f"[Models] Creating Layout/LayoutLMv3/ structure...")
        layoutlmv3_dir = os.path.join(MODELS_DIR, "Layout", "LayoutLMv3")
        os.makedirs(layoutlmv3_dir, exist_ok=True)
        
        # Move all files from Layout/ to Layout/LayoutLMv3/
        layout_dir = os.path.join(MODELS_DIR, "Layout")
        for item in os.listdir(layout_dir):
            if item != "LayoutLMv3":
                src = os.path.join(layout_dir, item)
                dst = os.path.join(layoutlmv3_dir, item)
                print(f"[Models]   Moving {item} -> LayoutLMv3/{item}")
                shutil.move(src, dst)
    
    # Check if MFD/weights.pt exists but MFD/YOLO doesn't
    mfd_flat = os.path.join(MODELS_DIR, "MFD", "weights.pt")
    mfd_yolo = os.path.join(MODELS_DIR, "MFD", "YOLO")
    yolo_model = os.path.join(mfd_yolo, "yolo_v8_ft.pt")
    
    if os.path.exists(mfd_flat) and not os.path.exists(yolo_model):
        print(f"[Models] Creating MFD/YOLO/ structure...")
        os.makedirs(mfd_yolo, exist_ok=True)
        
        # Rename weights.pt to yolo_v8_ft.pt and move to YOLO/
        dst = os.path.join(mfd_yolo, "yolo_v8_ft.pt")
        print(f"[Models]   Moving weights.pt -> YOLO/yolo_v8_ft.pt")
        shutil.move(mfd_flat, dst)
    
    # Also check for any other MFD files that need to be in YOLO/
    mfd_dir = os.path.join(MODELS_DIR, "MFD")
    if os.path.exists(mfd_dir):
        for item in os.listdir(mfd_dir):
            if item != "YOLO" and not os.path.isdir(os.path.join(mfd_dir, item)):
                # It's a file, check if it should be in YOLO
                src = os.path.join(mfd_dir, item)
                dst = os.path.join(mfd_yolo, item)
                if not os.path.exists(dst):
                    print(f"[Models]   Moving {item} -> YOLO/{item}")
                    os.makedirs(mfd_yolo, exist_ok=True)
                    shutil.move(src, dst)


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
    print(f"[Models] Repository: {HF_REPO}")
    
    # Ensure directories exist
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(os.environ["HF_HOME"], exist_ok=True)
    
    try:
        print(f"[Models] Downloading from {HF_REPO}...")
        print(f"[Models] This will take a while (~10GB)...")
        
        # Download to a temp location first
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
                # Show subdirectory contents
                for sub in os.listdir(item_path)[:5]:
                    sub_path = os.path.join(item_path, sub)
                    if os.path.isdir(sub_path):
                        print(f"    [DIR] {sub}/")
                    else:
                        size = os.path.getsize(sub_path)
                        print(f"    [FILE] {sub} ({size / 1024 / 1024:.1f} MB)")
            else:
                size = os.path.getsize(item_path)
                print(f"  [FILE] {item} ({size / 1024 / 1024:.1f} MB)")
        
        # The opendatalab/PDF-Extract-Kit repo has models in a 'models' subdirectory
        src_models = os.path.join(local_dir, "models")
        if os.path.exists(src_models):
            print(f"[Models] Found 'models' directory, moving to {MODELS_DIR}")
            
            # Remove existing if any
            if os.path.exists(MODELS_DIR):
                shutil.rmtree(MODELS_DIR)
            
            # Move models
            shutil.move(src_models, MODELS_DIR)
            print(f"[Models] Models moved successfully!")
        else:
            # Models might be at root level (different repo structure)
            print(f"[Models] No 'models' subdir found, checking root level...")
            
            # Check if model directories are at root
            model_dirs = ["Layout", "MFD", "MFR", "OCR", "TabRec"]
            found_any = False
            
            for item in model_dirs:
                src = os.path.join(local_dir, item)
                if os.path.exists(src):
                    dst = os.path.join(MODELS_DIR, item)
                    print(f"[Models] Moving {item} to {dst}")
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.move(src, dst)
                    found_any = True
            
            if not found_any:
                print(f"[Models] ERROR: No model directories found!")
                print(f"[Models] Contents of {local_dir}:")
                for item in os.listdir(local_dir):
                    print(f"  {item}")
                return False
        
        # Fix directory structure to match MinerU expectations
        create_directory_structure()
        
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
    print(f"[Models] HuggingFace repo: {HF_REPO}")
    print(f"[Models] Force download: {force}")
    
    show_disk_usage()
    
    # If models exist but structure might be wrong, fix it
    if os.path.exists(MODELS_DIR) and os.listdir(MODELS_DIR):
        create_directory_structure()
    
    if force or not check_models_exist():
        if not force and os.path.exists(MODELS_DIR) and os.listdir(MODELS_DIR):
            # Models exist but structure is wrong - try to fix
            print("[Models] Models exist but structure may be wrong, attempting fix...")
            create_directory_structure()
            if check_models_exist():
                print("[Models] Structure fixed!")
            else:
                print("[Models] Structure still wrong, re-downloading...")
                success = download_models()
                if not success:
                    print("[Models] WARNING: Download failed. Tesseract fallback will be used.")
                    show_disk_usage()
                    sys.exit(1)
        else:
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
