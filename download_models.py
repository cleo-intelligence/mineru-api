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
import json
import shutil

# Model storage location (Render persistent disk mounted at /root/.cache)
MODELS_DIR = os.environ.get("MINERU_MODELS_DIR", "/root/.cache/models")

# Set HF cache to persistent disk to avoid filling /tmp
os.environ["HF_HOME"] = "/root/.cache/huggingface"
os.environ["HF_HUB_CACHE"] = "/root/.cache/huggingface/hub"

# Model repositories
# Layout, MFD, TabRec from PDF-Extract-Kit
HF_REPO_PDF_KIT = "opendatalab/PDF-Extract-Kit"
# UniMERNet (MFR) from official repo - has complete weights
HF_REPO_UNIMERNET_SMALL = "wanderkid/unimernet_small"

# Config file path
CONFIG_PATH = "/root/magic-pdf.json"


def is_formula_enabled() -> bool:
    """Check if formula recognition is enabled in config."""
    # Check local config in repo first
    repo_config = os.path.join(os.path.dirname(__file__), "magic-pdf.json")
    config_paths = [repo_config, CONFIG_PATH]
    
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    config = json.load(f)
                enabled = config.get("formula-config", {}).get("enable", True)
                print(f"[Models] Formula recognition enabled: {enabled} (from {path})")
                return enabled
            except Exception as e:
                print(f"[Models] Could not read config {path}: {e}")
    
    # Default to True if no config found
    print("[Models] No config found, assuming formula recognition enabled")
    return True


def check_models_exist() -> bool:
    """Check if essential models are already downloaded."""
    if not os.path.exists(MODELS_DIR):
        print(f"[Models] Directory does not exist: {MODELS_DIR}")
        return False
    
    # Check for key model files (MinerU expected paths)
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


def check_unimernet_complete() -> bool:
    """Check if UniMERNet model has complete weights (not just config files)."""
    mfr_dir = os.path.join(MODELS_DIR, "MFR")
    if not os.path.exists(mfr_dir):
        return False
    
    # Check unimernet_small for complete weights
    for model_name in ["unimernet_small"]:
        model_path = os.path.join(mfr_dir, model_name)
        if os.path.islink(model_path):
            model_path = os.path.realpath(model_path)
        
        if not os.path.exists(model_path):
            print(f"[Models] UniMERNet {model_name} not found")
            return False
        
        # Check for pytorch_model.bin with substantial size (should be ~773MB for small)
        bin_file = os.path.join(model_path, "pytorch_model.bin")
        if os.path.exists(bin_file):
            size_mb = os.path.getsize(bin_file) / 1024 / 1024
            if size_mb > 100:  # Should be at least 100MB for a real model
                print(f"[Models] UniMERNet {model_name}: pytorch_model.bin = {size_mb:.1f} MB ✓")
                return True
            else:
                print(f"[Models] UniMERNet {model_name}: pytorch_model.bin too small ({size_mb:.1f} MB)")
                return False
        
        # Also check for .pth file
        pth_file = os.path.join(model_path, "pytorch_model.pth")
        if os.path.exists(pth_file):
            size_mb = os.path.getsize(pth_file) / 1024 / 1024
            if size_mb > 100:
                print(f"[Models] UniMERNet {model_name}: pytorch_model.pth = {size_mb:.1f} MB ✓")
                return True
            else:
                print(f"[Models] UniMERNet {model_name}: pytorch_model.pth too small ({size_mb:.1f} MB)")
                return False
        
        print(f"[Models] UniMERNet {model_name}: No model weights found")
        return False
    
    return False


def download_unimernet_models():
    """
    Download UniMERNet models from official wanderkid repo.
    These have complete weights unlike the PDF-Extract-Kit version.
    """
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("[Models] Installing huggingface_hub...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "huggingface_hub"], check=True)
        from huggingface_hub import snapshot_download
    
    mfr_dir = os.path.join(MODELS_DIR, "MFR")
    os.makedirs(mfr_dir, exist_ok=True)
    
    # Download unimernet_small (773MB) - this is what magic-pdf uses by default
    print(f"[Models] Downloading UniMERNet from {HF_REPO_UNIMERNET_SMALL}...")
    print(f"[Models] This contains the complete model weights (~773MB)...")
    
    try:
        target_dir = os.path.join(mfr_dir, "unimernet_small")
        
        # Remove existing incomplete model
        if os.path.exists(target_dir):
            # Check if it's a symlink
            if os.path.islink(target_dir):
                os.remove(target_dir)
            else:
                shutil.rmtree(target_dir)
        
        # Download directly to target
        local_dir = snapshot_download(
            repo_id=HF_REPO_UNIMERNET_SMALL,
            local_dir=target_dir,
            local_dir_use_symlinks=False,
            cache_dir=os.environ["HF_HUB_CACHE"],
        )
        
        print(f"[Models] UniMERNet downloaded to: {local_dir}")
        
        # List downloaded files
        print(f"[Models] UniMERNet files:")
        for item in os.listdir(target_dir):
            item_path = os.path.join(target_dir, item)
            if os.path.isfile(item_path):
                size = os.path.getsize(item_path)
                print(f"[Models]   {item} ({size / 1024 / 1024:.1f} MB)")
        
        # Verify pytorch_model.bin exists and has content
        bin_file = os.path.join(target_dir, "pytorch_model.bin")
        if os.path.exists(bin_file):
            size_mb = os.path.getsize(bin_file) / 1024 / 1024
            print(f"[Models] ✓ pytorch_model.bin downloaded: {size_mb:.1f} MB")
        else:
            print(f"[Models] ✗ pytorch_model.bin not found!")
            return False
        
        return True
        
    except Exception as e:
        print(f"[Models] UniMERNet download error: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_symlink_safe(target_path: str, link_path: str, link_name: str, target_name: str):
    """Safely create a symlink, handling existing files/symlinks."""
    if os.path.islink(link_path):
        os.remove(link_path)
        print(f"[Models]   Removed existing symlink {link_name}")
    elif os.path.exists(link_path):
        print(f"[Models]   {link_name} already exists as directory/file, skipping")
        return False
    
    try:
        abs_target = os.path.realpath(target_path)
        os.symlink(abs_target, link_path)
        print(f"[Models]   Created symlink {link_name} -> {target_name}")
        return True
    except Exception as e:
        print(f"[Models]   Failed to create symlink {link_name}: {e}")
        return False


def create_mfr_symlinks():
    """Create symlinks for MFR (Math Formula Recognition) models."""
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
            # Show size of model files
            bin_file = os.path.join(item_path, "pytorch_model.bin")
            pth_file = os.path.join(item_path, "pytorch_model.pth")
            if os.path.exists(bin_file):
                size = os.path.getsize(bin_file) / 1024 / 1024
                print(f"[Models]   {item}/ (pytorch_model.bin: {size:.1f} MB)")
            elif os.path.exists(pth_file):
                size = os.path.getsize(pth_file) / 1024 / 1024
                print(f"[Models]   {item}/ (pytorch_model.pth: {size:.1f} MB)")
            else:
                print(f"[Models]   {item}/ (no model weights)")
        else:
            print(f"[Models]   {item} (file)")
    
    # Create symlinks from magic-pdf expected names to actual unimernet_small
    unimernet_small = os.path.join(mfr_dir, "unimernet_small")
    
    if os.path.exists(unimernet_small) and os.path.isdir(unimernet_small):
        symlink_map = {
            # magic-pdf looks for these names
            "unimernet_hf_small_2503": "unimernet_small",
            "unimernet_small_2501": "unimernet_small",
            # Also create base/tiny pointing to small as fallback
            "unimernet_hf_base_2503": "unimernet_small",
            "unimernet_hf_tiny_2503": "unimernet_small",
            "unimernet_base_2501": "unimernet_small",
            "unimernet_tiny_2501": "unimernet_small",
        }
        
        for link_name, target_name in symlink_map.items():
            link_path = os.path.join(mfr_dir, link_name)
            target_path = os.path.join(mfr_dir, target_name)
            
            if os.path.exists(link_path) and os.path.isdir(link_path) and not os.path.islink(link_path):
                print(f"[Models]   {link_name} already exists as real directory")
                continue
            
            if not os.path.exists(target_path):
                print(f"[Models]   Target {target_name} not found, skipping {link_name}")
                continue
            
            create_symlink_safe(target_path, link_path, link_name, target_name)
    
    # Verify symlinks
    print(f"[Models] Verifying MFR symlinks...")
    for test_name in ["unimernet_hf_small_2503"]:
        test_path = os.path.join(mfr_dir, test_name)
        if os.path.exists(test_path):
            real_path = os.path.realpath(test_path)
            print(f"[Models]   {test_name} -> {os.path.basename(real_path)} ✓")
            bin_path = os.path.join(test_path, "pytorch_model.bin")
            if os.path.exists(bin_path):
                size = os.path.getsize(bin_path) / 1024 / 1024
                print(f"[Models]     pytorch_model.bin: {size:.1f} MB ✓")
            else:
                print(f"[Models]     WARNING: pytorch_model.bin not found!")
        else:
            print(f"[Models]   {test_name} NOT FOUND ✗")


def create_directory_structure():
    """Create the directory structure expected by MinerU magic-pdf."""
    print(f"[Models] Checking and fixing directory structure...")
    
    # Show current structure
    print(f"[Models] Current structure of {MODELS_DIR}:")
    for root, dirs, files in os.walk(MODELS_DIR):
        level = root.replace(MODELS_DIR, '').count(os.sep)
        if level > 2:
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
    
    # Fix Layout structure
    layout_flat = os.path.join(MODELS_DIR, "Layout", "model_final.pth")
    layout_nested = os.path.join(MODELS_DIR, "Layout", "LayoutLMv3", "model_final.pth")
    
    if os.path.exists(layout_flat) and not os.path.exists(layout_nested):
        print(f"[Models] Creating Layout/LayoutLMv3/ structure...")
        layoutlmv3_dir = os.path.join(MODELS_DIR, "Layout", "LayoutLMv3")
        os.makedirs(layoutlmv3_dir, exist_ok=True)
        
        layout_dir = os.path.join(MODELS_DIR, "Layout")
        for item in os.listdir(layout_dir):
            if item != "LayoutLMv3":
                src = os.path.join(layout_dir, item)
                dst = os.path.join(layoutlmv3_dir, item)
                print(f"[Models]   Moving {item} -> LayoutLMv3/{item}")
                shutil.move(src, dst)
    
    # Fix MFD structure
    mfd_flat = os.path.join(MODELS_DIR, "MFD", "weights.pt")
    mfd_yolo = os.path.join(MODELS_DIR, "MFD", "YOLO")
    yolo_model = os.path.join(mfd_yolo, "yolo_v8_ft.pt")
    
    if os.path.exists(mfd_flat) and not os.path.exists(yolo_model):
        print(f"[Models] Creating MFD/YOLO/ structure...")
        os.makedirs(mfd_yolo, exist_ok=True)
        dst = os.path.join(mfd_yolo, "yolo_v8_ft.pt")
        print(f"[Models]   Moving weights.pt -> YOLO/yolo_v8_ft.pt")
        shutil.move(mfd_flat, dst)
    
    # Move other MFD files to YOLO/
    mfd_dir = os.path.join(MODELS_DIR, "MFD")
    if os.path.exists(mfd_dir):
        for item in os.listdir(mfd_dir):
            if item != "YOLO" and not os.path.isdir(os.path.join(mfd_dir, item)):
                src = os.path.join(mfd_dir, item)
                dst = os.path.join(mfd_yolo, item)
                if not os.path.exists(dst):
                    print(f"[Models]   Moving {item} -> YOLO/{item}")
                    os.makedirs(mfd_yolo, exist_ok=True)
                    shutil.move(src, dst)
    
    # Create MFR symlinks only if formula is enabled
    if is_formula_enabled():
        create_mfr_symlinks()
    else:
        print("[Models] Formula recognition disabled, skipping MFR symlinks")


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
    
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(os.environ["HF_HOME"], exist_ok=True)
    
    try:
        # Download PDF-Extract-Kit for Layout, MFD, TabRec
        print(f"[Models] Downloading from {HF_REPO_PDF_KIT}...")
        print(f"[Models] This will take a while (~10GB)...")
        
        temp_download_dir = "/root/.cache/hf_download_temp"
        os.makedirs(temp_download_dir, exist_ok=True)
        
        local_dir = snapshot_download(
            repo_id=HF_REPO_PDF_KIT,
            local_dir=temp_download_dir,
            local_dir_use_symlinks=False,
            cache_dir=os.environ["HF_HUB_CACHE"],
        )
        
        print(f"[Models] Downloaded to: {local_dir}")
        
        # Move models to MODELS_DIR
        src_models = os.path.join(local_dir, "models")
        if os.path.exists(src_models):
            print(f"[Models] Found 'models' directory, moving to {MODELS_DIR}")
            if os.path.exists(MODELS_DIR):
                shutil.rmtree(MODELS_DIR)
            shutil.move(src_models, MODELS_DIR)
            print(f"[Models] Models moved successfully!")
        else:
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
                return False
        
        # Cleanup temp
        if os.path.exists(temp_download_dir):
            shutil.rmtree(temp_download_dir)
        
        # Fix directory structure
        create_directory_structure()
        
        print("[Models] PDF-Extract-Kit download complete!")
        return True
        
    except Exception as e:
        print(f"[Models] Download error: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_config():
    """Create magic-pdf.json config pointing to persistent models."""
    # Read formula enabled state from repo config
    formula_enabled = is_formula_enabled()
    
    config_content = f'''{{
    "device-mode": "cpu",
    "models-dir": "{MODELS_DIR}",
    "table-config": {{
        "model": "rapid_table",
        "enable": false
    }},
    "formula-config": {{
        "model": "unimernet_small",
        "enable": {"true" if formula_enabled else "false"}
    }},
    "layout-config": {{
        "model": "layoutlmv3"
    }}
}}'''
    
    with open(CONFIG_PATH, 'w') as f:
        f.write(config_content)
    
    print(f"[Models] Config written to {CONFIG_PATH}")
    print(f"[Models] Formula recognition: {'enabled' if formula_enabled else 'DISABLED (saves ~1GB RAM)'}")


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
    print(f"[Models] Force download: {force}")
    
    # Check formula config
    formula_enabled = is_formula_enabled()
    print(f"[Models] Formula recognition: {'ENABLED' if formula_enabled else 'DISABLED'}")
    
    show_disk_usage()
    
    # Check if we need to download UniMERNet with complete weights
    need_unimernet = False
    if formula_enabled:
        if os.path.exists(MODELS_DIR) and os.listdir(MODELS_DIR):
            create_directory_structure()
            if not check_unimernet_complete():
                print("[Models] UniMERNet weights incomplete - need to download from official repo")
                need_unimernet = True
    else:
        print("[Models] Skipping UniMERNet check (formula recognition disabled)")
    
    # Download base models if needed
    if force or not check_models_exist():
        if not force and os.path.exists(MODELS_DIR) and os.listdir(MODELS_DIR):
            print("[Models] Models exist but structure may be wrong, attempting fix...")
            create_directory_structure()
            if check_models_exist():
                print("[Models] Structure fixed!")
            else:
                print("[Models] Structure still wrong, re-downloading...")
                success = download_models()
                if not success:
                    print("[Models] WARNING: Download failed.")
                    show_disk_usage()
                    sys.exit(1)
                if formula_enabled:
                    need_unimernet = True
        else:
            success = download_models()
            if not success:
                print("[Models] WARNING: Download failed.")
                show_disk_usage()
                sys.exit(1)
            if formula_enabled:
                need_unimernet = True
    
    # Download complete UniMERNet weights if needed AND formula is enabled
    if formula_enabled and (need_unimernet or not check_unimernet_complete()):
        print("[Models] ----------------------------------------")
        print("[Models] Downloading complete UniMERNet weights...")
        print("[Models] ----------------------------------------")
        if download_unimernet_models():
            print("[Models] UniMERNet download complete!")
            # Recreate symlinks
            create_mfr_symlinks()
        else:
            print("[Models] WARNING: UniMERNet download failed. Formula recognition may not work.")
    elif not formula_enabled:
        print("[Models] ----------------------------------------")
        print("[Models] Skipping UniMERNet download (formula recognition disabled)")
        print("[Models] This saves ~773MB download and ~1GB RAM at runtime")
        print("[Models] ----------------------------------------")
    
    create_config()
    show_disk_usage()
    print("[Models] Ready!")


if __name__ == "__main__":
    main()
