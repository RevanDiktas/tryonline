from .smpl_wrapper import SMPL
from .hmr2 import HMR2
from .discriminator import Discriminator

from ..utils.download import cache_url
from ..configs import CACHE_DIR_4DHUMANS


def _ensure_config_files_exist(checkpoint_path):
    """
    Helper function to ensure model_config.yaml and dataset_config.yaml exist
    for a given checkpoint path.
    """
    import os
    config_dir = os.path.dirname(os.path.dirname(checkpoint_path))  # logs/train/multiruns/hmr2/0/
    model_config_path = os.path.join(config_dir, "model_config.yaml")
    dataset_config_path = os.path.join(config_dir, "dataset_config.yaml")
    
    if not os.path.exists(model_config_path):
        print(f"Creating default model_config.yaml...")
        os.makedirs(config_dir, exist_ok=True)
        from hmr2.configs import default_config
        default_cfg = default_config()
        with open(model_config_path, 'w') as f:
            f.write(default_cfg.dump())
        print(f"  Created: {model_config_path}")
    
    if not os.path.exists(dataset_config_path):
        print(f"Creating default dataset_config.yaml...")
        from hmr2.configs import dataset_config as get_dataset_config
        dataset_cfg = get_dataset_config()
        with open(dataset_config_path, 'w') as f:
            f.write(dataset_cfg.dump())
        print(f"  Created: {dataset_config_path}")


def download_models(folder=CACHE_DIR_4DHUMANS):
    """Download checkpoints and files for running inference.
    """
    import os
    import sys
    from pathlib import Path
    
    os.makedirs(folder, exist_ok=True)
    
    # Check both the cache folder AND the local 4D-Humans-clean folder
    script_dir = Path(__file__).parent.parent  # hmr2 folder
    local_data_folder = script_dir.parent  # 4D-Humans-clean folder
    
    # Essential files to check
    essential_checks = [
        ("data/smpl/SMPL_NEUTRAL.pkl", "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt"),
    ]
    
    # Check cache folder
    cache_files = [
        os.path.join(folder, "data/smpl/SMPL_NEUTRAL.pkl"),
        os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt"),
    ]
    
    # Check local folder
    local_files = [
        local_data_folder / "data/smpl/SMPL_NEUTRAL.pkl",
        local_data_folder / "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt",
    ]
    
    if all(os.path.exists(f) for f in cache_files):
        print("HMR2 data found in cache, skipping download.")
        # Ensure config files exist even if found in cache
        expected_checkpoint = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")
        _ensure_config_files_exist(expected_checkpoint)
        return
    
    # Check if checkpoint exists in either location (primary check)
    # Also check common RunPod mount paths
    checkpoint_paths = [
        os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt"),
        str(local_data_folder / "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt"),
        os.path.join(folder, "checkpoints/epoch=35-step=1000000.ckpt"),  # Alternative location
        str(local_data_folder / "checkpoints/epoch=35-step=1000000.ckpt"),  # Alternative location
        "/workspace/checkpoints/epoch=35-step=1000000.ckpt",  # RunPod volume mount
        "/workspace/models/epoch=35-step=1000000.ckpt",  # Alternative RunPod mount
        "/runpod-volume/epoch=35-step=1000000.ckpt",  # Common RunPod volume path
    ]
    
    for checkpoint_path in checkpoint_paths:
        if os.path.exists(checkpoint_path):
            print(f"HMR2 checkpoint found at {checkpoint_path}, skipping download.")
            # Still copy to expected cache location if not already there
            expected_cache_path = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")
            if checkpoint_path != expected_cache_path and not os.path.exists(expected_cache_path):
                import shutil
                os.makedirs(os.path.dirname(expected_cache_path), exist_ok=True)
                shutil.copy(checkpoint_path, expected_cache_path)
                print(f"  Copied checkpoint to expected location")
            
            # Ensure config files exist even if checkpoint was already there
            _ensure_config_files_exist(expected_cache_path)
            
            return
    
    if all(f.exists() for f in local_files):
        print("HMR2 data found locally, copying to cache...")
        # Copy essential files to cache
        import shutil
        for local_f in local_files:
            rel_path = local_f.relative_to(local_data_folder)
            cache_path = os.path.join(folder, str(rel_path))
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            if not os.path.exists(cache_path):
                shutil.copy(str(local_f), cache_path)
                print(f"  Copied {rel_path}")
        
        # Also copy config files
        config_files = [
            "logs/train/multiruns/hmr2/0/model_config.yaml",
            "logs/train/multiruns/hmr2/0/dataset_config.yaml",
            "data/smpl_mean_params.npz",
            "data/SMPL_to_J19.pkl",
            "data/smpl/SMPL_MALE.pkl",
            "data/smpl/SMPL_FEMALE.pkl",
        ]
        for cf in config_files:
            local_cf = local_data_folder / cf
            cache_cf = os.path.join(folder, cf)
            if local_cf.exists() and not os.path.exists(cache_cf):
                os.makedirs(os.path.dirname(cache_cf), exist_ok=True)
                shutil.copy(str(local_cf), cache_cf)
                print(f"  Copied {cf}")
        
        # Ensure config files exist even if they weren't in local directory
        expected_checkpoint = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")
        _ensure_config_files_exist(expected_checkpoint)
        return
    
    # Try downloading checkpoint from Google Drive if not found
    # Replace this with your Google Drive file ID after uploading
    # Get file ID from: https://drive.google.com/file/d/FILE_ID_HERE/view
    GOOGLE_DRIVE_CHECKPOINT_FILE_ID = os.environ.get("GOOGLE_DRIVE_CHECKPOINT_ID")  # Can set via env var
    # Or hardcode it: GOOGLE_DRIVE_CHECKPOINT_FILE_ID = "YOUR_FILE_ID_HERE"
    
    checkpoint_dest = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")
    
    # Only try Google Drive if checkpoint doesn't exist and we have a file ID
    if not os.path.exists(checkpoint_dest) and GOOGLE_DRIVE_CHECKPOINT_FILE_ID:
        print(f"Checkpoint not found. Attempting to download from Google Drive...")
        try:
            import subprocess
            # Install gdown if not available
            try:
                import gdown
            except ImportError:
                print("Installing gdown...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "gdown"])
                import gdown
            
            os.makedirs(os.path.dirname(checkpoint_dest), exist_ok=True)
            
            # Google Drive URL format
            gdrive_url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_CHECKPOINT_FILE_ID}"
            print(f"Downloading from: {gdrive_url}")
            print("(This may take 10-30 minutes for 2.5GB file...)")
            
            gdown.download(gdrive_url, checkpoint_dest, quiet=False)
            
            if os.path.exists(checkpoint_dest):
                print(f"✅ Checkpoint downloaded from Google Drive!")
                
                # After downloading checkpoint, create default config files if they don't exist
                _ensure_config_files_exist(checkpoint_dest)
                
                return
            else:
                print(f"⚠️  Download completed but file not found at {checkpoint_dest}")
        except Exception as e:
            print(f"⚠️  Google Drive download failed: {e}")
            print("Falling back to check other locations...")
    
    download_files = {
        "hmr2_data.tar.gz"      : ["https://people.eecs.berkeley.edu/~jathushan/projects/4dhumans/hmr2_data.tar.gz", folder],
    }

    for file_name, url in download_files.items():
        output_path = os.path.join(url[1], file_name)
        if not os.path.exists(output_path):
            print("Attempting to download file: " + file_name)
            try:
                # output = gdown.cached_download(url[0], output_path, fuzzy=True)
                output = cache_url(url[0], output_path)
                if not os.path.exists(output_path):
                    print(f"Warning: Download failed or file not found at {output_path}. Models may need to be provided via volume mount.")
                    # Check if essential files already exist elsewhere (e.g., mounted volumes)
                    essential_checkpoint = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")
                    if os.path.exists(essential_checkpoint):
                        print(f"Found checkpoint at {essential_checkpoint}, skipping download.")
                        _ensure_config_files_exist(essential_checkpoint)
                        return
                    raise FileNotFoundError(f"Required model file not found: {output_path}")
            except Exception as e:
                print(f"Warning: Failed to download {file_name}: {e}")
                # Check if essential files exist elsewhere
                essential_checkpoint = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")
                if os.path.exists(essential_checkpoint):
                    print(f"Found checkpoint at {essential_checkpoint}, continuing despite download failure.")
                    _ensure_config_files_exist(essential_checkpoint)
                    return
                # If download fails and files don't exist, check one more time for checkpoint
                # in case it was mounted or copied while we were trying to download
                for checkpoint_path in checkpoint_paths:
                    if os.path.exists(checkpoint_path):
                        print(f"Found checkpoint at {checkpoint_path} after download failure. Continuing...")
                        # Copy to expected location if different
                        expected_checkpoint = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")
                        if checkpoint_path != expected_checkpoint and not os.path.exists(expected_checkpoint):
                            import shutil
                            os.makedirs(os.path.dirname(expected_checkpoint), exist_ok=True)
                            shutil.copy(checkpoint_path, expected_checkpoint)
                            print(f"  Copied checkpoint to expected location")
                        # Ensure config files exist (use expected location)
                        if os.path.exists(expected_checkpoint):
                            _ensure_config_files_exist(expected_checkpoint)
                        return
                
                # Final error if nothing found
                error_msg = (
                    f"ERROR: HMR2 checkpoint file not found and download failed.\n"
                    f"Required file: epoch=35-step=1000000.ckpt\n"
                    f"Checked locations:\n"
                    f"  - {os.path.join(folder, 'logs/train/multiruns/hmr2/0/checkpoints/')}\n"
                    f"  - {local_data_folder / 'checkpoints/'}\n"
                    f"  - /workspace/checkpoints/\n"
                    f"\nSolutions:\n"
                    f"1. Mount checkpoint via RunPod Volumes\n"
                    f"2. Include checkpoint in Docker image build\n"
                    f"3. Ensure download URL is accessible"
                )
                print(error_msg)
                raise FileNotFoundError(error_msg)

            # if ends with tar.gz, tar -xzf
            if file_name.endswith(".tar.gz"):
                print("Extracting file: " + file_name)
                os.system("tar -xvf " + output_path + " -C " + url[1])
                
                # After extracting, ensure config files exist
                expected_checkpoint = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")
                if os.path.exists(expected_checkpoint):
                    _ensure_config_files_exist(expected_checkpoint)

def check_smpl_exists():
    import os
    candidates = [
        f'{CACHE_DIR_4DHUMANS}/data/smpl/SMPL_NEUTRAL.pkl',
        f'data/basicModel_neutral_lbs_10_207_0_v1.0.0.pkl',
    ]
    candidates_exist = [os.path.exists(c) for c in candidates]
    if not any(candidates_exist):
        raise FileNotFoundError(f"SMPL model not found. Please download it from https://smplify.is.tue.mpg.de/ and place it at {candidates[1]}")

    # Code edxpects SMPL model at CACHE_DIR_4DHUMANS/data/smpl/SMPL_NEUTRAL.pkl. Copy there if needed
    if (not candidates_exist[0]) and candidates_exist[1]:
        convert_pkl(candidates[1], candidates[0])

    return True

# Convert SMPL pkl file to be compatible with Python 3
# Script is from https://rebeccabilbro.github.io/convert-py2-pickles-to-py3/
def convert_pkl(old_pkl, new_pkl):
    """
    Convert a Python 2 pickle to Python 3
    """
    import dill
    import pickle

    # Convert Python 2 "ObjectType" to Python 3 object
    dill._dill._reverse_typemap["ObjectType"] = object

    # Open the pickle using latin1 encoding
    with open(old_pkl, "rb") as f:
        loaded = pickle.load(f, encoding="latin1")

    # Re-save as Python 3 pickle
    with open(new_pkl, "wb") as outfile:
        pickle.dump(loaded, outfile)

DEFAULT_CHECKPOINT=f'{CACHE_DIR_4DHUMANS}/logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt'
def load_hmr2(checkpoint_path=DEFAULT_CHECKPOINT):
    from pathlib import Path
    from ..configs import get_config
    model_cfg = str(Path(checkpoint_path).parent.parent / 'model_config.yaml')
    model_cfg = get_config(model_cfg, update_cachedir=True)

    # Override some config values, to crop bbox correctly
    if (model_cfg.MODEL.BACKBONE.TYPE == 'vit') and ('BBOX_SHAPE' not in model_cfg.MODEL):
        model_cfg.defrost()
        assert model_cfg.MODEL.IMAGE_SIZE == 256, f"MODEL.IMAGE_SIZE ({model_cfg.MODEL.IMAGE_SIZE}) should be 256 for ViT backbone"
        model_cfg.MODEL.BBOX_SHAPE = [192,256]
        model_cfg.freeze()

    # Ensure SMPL model exists
    check_smpl_exists()

    model = HMR2.load_from_checkpoint(checkpoint_path, strict=False, cfg=model_cfg)
    return model, model_cfg
