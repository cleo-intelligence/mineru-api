#!/usr/bin/env python3
"""
Download MinerU models from Hugging Face to persistent storage.
Uses huggingface_hub for reliable incremental downloads.

IMPORTANT: Downloads directly to /root/.cache/models (persistent disk).

Usage:
    python download_models.py [--force]
"""
import os
import sys
import shutil

# Model storage location (Render persistent disk mounted at /root/.cache)
MODELS_DIR = os.environ.get("MINERU_MODELS_DIR", "/root/.cache/models")

# Set HF cache to persistent disk to avoid filling /tmp
os.environ["HF_HOME"] = "/root/.cache/huggingface"
os.environ["HF_HUB_CACHE"] = "/root/.cache/huggingface/hub"

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


def fix_mfr_model_files(model_dir: str):
    """
    Fix MFR model files to be compatible with transformers.
    transformers expects pytorch_model.bin but the repo may have pytorch_model.pth
    """
    if not os.path.isdir(model_dir):
        return
        
    pth_file = os.path.join(model_dir, "pytorch_model.pth")
    bin_file = os.path.join(model_dir, "pytorch_model.bin")
    
    # Check if .bin already exists
    if os.path.exists(bin_file):
        print(f"[Models]   pytorch_model.bin already exists in {os.path.basename(model_dir)}")
        return
    
    # If .pth exists, create symlink to .bin
    if os.path.exists(pth_file):
        print(f"[Models]   Creating symlink pytorch_model.bin -> pytorch_model.pth in {os.path.basename(model_dir)}")
        try:
            os.symlink("pytorch_model.pth", bin_file)
        except Exception as e:
            print(f"[Models]   Failed to create symlink: {e}")
            try:
                shutil.copy2(pth_file, bin_file)
                print(f"[Models]   Copied pytorch_model.pth to pytorch_model.bin")
            except Exception as e2:
                print(f"[Models]   Failed to copy: {e2}")


def create_symlink_safe(target_path: str, link_path: str, link_name: str, target_name: str):
    """
    Safely create a symlink, handling existing files/symlinks.
    """
    # Remove existing symlink if it exists
    if os.path.islink(link_path):
        os.remove(link_path)
        print(f"[Models]   Removed existing symlink {link_name}")
    elif os.path.exists(link_path):
        print(f"[Models]   {link_name} already exists as directory/file, skipping")
        return False
    
    # Create symlink using absolute path for reliability
    try:
        abs_target = os.path.realpath(target_path)
        os.symlink(abs_target, link_path)
        print(f"[Models]   Created symlink {link_name} -> {target_name}")
        return True
    except Exception as e:
        print(f"[Models]   Failed to create symlink {link_name}: {e}")
        return False


def create_mfr_symlinks():
    """
    Create symlinks for MFR (Math Formula Recognition) models.
    
    The HuggingFace repo opendatalab/PDF-Extract-Kit may have:
    - MFR/UniMERNet/ (single model directory - older structure)
    - MFR/unimernet_small/, MFR/unimernet_base/, MFR/unimernet_tiny/ (newer structure)
    
    magic-pdf expects names like:
    - MFR/unimernet_small/ or MFR/unimernet_hf_small_2503/
    
    We need to create symlinks to map all the names correctly.
    """
    mfr_dir = os.path.join(MODELS_DIR, "MFR")
    if not os.path.exists(mfr_dir):
        print(f"[Models] MFR directory not found, skipping symlinks")
        return
    
    print(f"[Models] Creating MFR model symlinks...")
    print(f"[Models] MFR directory contents:")
    for item in os.listdir(mfr_dir):
        item_path = os.path.join(mfr_dir, item)
        if os.path.islink(item_path):
            target = os.readlink(item_path)
            print(f"[Models]   {item} -> {target} (symlink)")
        elif os.path.isdir(item_path):
            print(f"[Models]   {item}/ (directory)")
        else:
            print(f"[Models]   {item} (file)")
    
    # Step 1: Handle the case where only UniMERNet exists (older HF repo structure)
    # Map UniMERNet -> unimernet_small, unimernet_base, unimernet_tiny
    unimernet_dir = os.path.join(mfr_dir, "UniMERNet")
    
    if os.path.exists(unimernet_dir) and os.path.isdir(unimernet_dir) and not os.path.islink(unimernet_dir):
        print(f"[Models] Found UniMERNet directory, creating symlinks for all model sizes...")
        
        # Create symlinks for all expected names pointing to UniMERNet
        for model_name in ["unimernet_small", "unimernet_base", "unimernet_tiny"]:
            model_path = os.path.join(mfr_dir, model_name)
            if not os.path.exists(model_path):
                create_symlink_safe(unimernet_dir, model_path, model_name, "UniMERNet")
    
    # Step 2: Fix .pth -> .bin in all model directories
    # Check all possible model directory names
    model_dirs_to_check = [
        "UniMERNet",
        "unimernet_small", 
        "unimernet_base", 
        "unimernet_tiny",
        "unimernet_small_2501",
        "unimernet_base_2501",
        "unimernet_tiny_2501",
    ]
    
    for model_name in model_dirs_to_check:
        model_path = os.path.join(mfr_dir, model_name)
        # Follow symlinks to get actual directory
        if os.path.exists(model_path):
            real_path = os.path.realpath(model_path)
            if os.path.isdir(real_path):
                fix_mfr_model_files(real_path)
    
    # Step 3: Create symlinks from magic-pdf expected names to actual names
    # magic-pdf looks for names like unimernet_hf_small_2503
    symlink_map = {
        # 2503 variants (older magic-pdf versions)
        "unimernet_hf_small_2503": "unimernet_small",
        "unimernet_hf_base_2503": "unimernet_base", 
        "unimernet_hf_tiny_2503": "unimernet_tiny",
        # 2501 variants (newer magic-pdf versions)
        "unimernet_small_2501": "unimernet_small",
        "unimernet_base_2501": "unimernet_base",
        "unimernet_tiny_2501": "unimernet_tiny",
    }
    
    for link_name, target_name in symlink_map.items():
        link_path = os.path.join(mfr_dir, link_name)
        target_path = os.path.join(mfr_dir, target_name)
        
        # Skip if link already exists as directory
        if os.path.exists(link_path) and os.path.isdir(link_path) and not os.path.islink(link_path):
            print(f"[Models]   {link_name} already exists as real directory")
            continue
        
        # Check if target exists (could be a directory or symlink)
        if not os.path.exists(target_path):
            print(f"[Models]   Target {target_name} not found, skipping {link_name}")
            continue
        
        create_symlink_safe(target_path, link_path, link_name, target_name)
    
    # Verify the symlinks work
    print(f"[Models] Verifying MFR symlinks...")
    for test_name in ["unimernet_hf_small_2503", "unimernet_hf_base_2503", "unimernet_hf_tiny_2503"]:
        test_path = os.path.join(mfr_dir, test_name)
        if os.path.exists(test_path):
            real_path = os.path.realpath(test_path)
            print(f"[Models]   {test_name} -> {os.path.basename(real_path)} ✓")
            # Check for pytorch_model.bin
            bin_path = os.path.join(test_path, "pytorch_model.bin")
            if os.path.exists(bin_path):
                print(f"[Models]     pytorch_model.bin found ✓")
            else:
                print(f"[Models]     WARNING: pytorch_model.bin not found!")
        else:
            print(f"[Models]   {test_name} NOT FOUND ✗")


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
        if level > 2:  # Limit depth
            continue
        indent = '  ' * level
        folder = os.path.basename(root) or MODELS_DIR
        print(f"{indent}{folder}/")
        for f in files[:5]:
            fpath = os.path.join(root, f)
            if os.path.islink(fpath):
                target = os.readlink(fpath)
                print(f"{indent}  {f} -> {target}")
            else:
                try:
                    size = os.path.getsize(fpath)
                    print(f"{indent}  {f} ({size / 1024 / 1024:.1f} MB)")
                except:
                    print(f"{indent}  {f}")
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
    
    # Create MFR symlinks for formula recognition
    create_mfr_symlinks()


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
        temp_download_dir = "/root/.cache/hf_download_temp"
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
    # All features enabled for maximum quality
    config_content = f'''{{
    "device-mode": "cpu",
    "models-dir": "{MODELS_DIR}",
    "table-config": {{
        "model": "rapid_table",
        "enable": true
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
    subprocess.run(["df", "-h", "/root/.cache"], check=False)
    print("\n[Models] Directory sizes in /root/.cache:")
    subprocess.run(["du", "-sh", "/root/.cache/*"], shell=True, check=False)


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
