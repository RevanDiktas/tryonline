from .smpl_wrapper import SMPL
from .hmr2 import HMR2
from .discriminator import Discriminator

from ..utils.download import cache_url
from ..configs import CACHE_DIR_4DHUMANS


def _download_from_dropbox(dropbox_url, output_path, expected_size_mb_min=None, expected_size_mb_max=None):
    """
    Helper function to download a file from Dropbox.
    
    Args:
        dropbox_url: Dropbox direct download URL (must have ?dl=1)
        output_path: Where to save the file
        expected_size_mb_min: Minimum expected size in MB (for validation)
        expected_size_mb_max: Maximum expected size in MB (for validation)
    
    Returns:
        bool: True if download succeeded, False otherwise
    """
    import os
    from ..utils.download import download_url
    
    if os.path.exists(output_path):
        return True  # File already exists
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        # Ensure Dropbox URL has dl=1 for direct download
        if "dropbox.com" in dropbox_url and "?dl=" not in dropbox_url:
            dropbox_url = dropbox_url + "?dl=1" if "?" not in dropbox_url else dropbox_url.replace("?dl=0", "?dl=1")
        
        temp_file = output_path + ".tmp"
        print(f"[DEBUG] Downloading from Dropbox: {dropbox_url}")
        download_url(dropbox_url, temp_file)
        
        if os.path.exists(temp_file):
            file_size_mb = os.path.getsize(temp_file) / (1024 * 1024)
            
            # Validate size if expected
            if expected_size_mb_min and file_size_mb < expected_size_mb_min:
                print(f"⚠️  Downloaded file is too small: {file_size_mb:.1f}MB (expected at least {expected_size_mb_min}MB)")
                os.remove(temp_file)
                return False
            
            if expected_size_mb_max and file_size_mb > expected_size_mb_max:
                print(f"⚠️  Downloaded file is too large: {file_size_mb:.1f}MB (expected at most {expected_size_mb_max}MB)")
                os.remove(temp_file)
                return False
            
            # Move to final location
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(temp_file, output_path)
            print(f"✅ Downloaded from Dropbox! ({file_size_mb:.1f}MB)")
            return True
        else:
            print(f"⚠️  Download failed: temp file not found")
            return False
            
    except Exception as e:
        print(f"⚠️  Dropbox download failed: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False

def _ensure_smpl_joint_regressor_exists(data_dir):
    """
    Helper function to download or create SMPL_to_J19.pkl if it doesn't exist.
    Tries to download from Dropbox if URL is provided.
    """
    import os
    
    joint_regressor_path = os.path.join(data_dir, "SMPL_to_J19.pkl")
    
    if os.path.exists(joint_regressor_path):
        return  # File already exists
    
    os.makedirs(data_dir, exist_ok=True)
    
    # Try downloading from Dropbox
    DROPBOX_JOINT_REGRESSOR_URL = os.environ.get("DROPBOX_JOINT_REGRESSOR_URL")
    
    if DROPBOX_JOINT_REGRESSOR_URL:
        print(f"Attempting to download SMPL_to_J19.pkl from Dropbox...")
        if _download_from_dropbox(DROPBOX_JOINT_REGRESSOR_URL, joint_regressor_path, 
                                  expected_size_mb_min=0.1, expected_size_mb_max=10):
            return
    
    # If download failed or not configured, we'll make it optional in config
    print(f"⚠️  SMPL_to_J19.pkl not found. The code will work without extra joints.")
    print(f"  To download it, set DROPBOX_JOINT_REGRESSOR_URL environment variable.")

def _ensure_smpl_mean_params_exists(data_dir):
    """
    Helper function to download or create smpl_mean_params.npz if it doesn't exist.
    Tries to download from Dropbox if URL is provided, then falls back to creating default values.
    """
    import os
    import numpy as np
    
    mean_params_path = os.path.join(data_dir, "smpl_mean_params.npz")
    
    # CRITICAL: Check if existing file has correct dimension (144, not 72)
    # The checkpoint requires 144 dimensions (6d representation: 24 joints × 6)
    if os.path.exists(mean_params_path):
        try:
            existing_params = np.load(mean_params_path)
            if 'pose' in existing_params:
                existing_pose_dim = existing_params['pose'].shape[0] if len(existing_params['pose'].shape) > 0 else len(existing_params['pose'])
                if existing_pose_dim == 144:
                    return  # File exists and has correct dimension
                else:
                    print(f"⚠️  Existing smpl_mean_params.npz has wrong dimension ({existing_pose_dim}, expected 144)")
                    print(f"  Regenerating with correct dimension...")
                    os.remove(mean_params_path)  # Delete old file
            else:
                print(f"⚠️  Existing smpl_mean_params.npz missing 'pose' key, regenerating...")
                os.remove(mean_params_path)
        except Exception as e:
            print(f"⚠️  Error checking existing smpl_mean_params.npz: {e}, regenerating...")
            if os.path.exists(mean_params_path):
                os.remove(mean_params_path)
    
    os.makedirs(data_dir, exist_ok=True)
    
    # Try downloading from Dropbox
    DROPBOX_MEAN_PARAMS_URL = os.environ.get("DROPBOX_MEAN_PARAMS_URL")
    
    if DROPBOX_MEAN_PARAMS_URL:
        print(f"Attempting to download smpl_mean_params.npz from Dropbox...")
        if _download_from_dropbox(DROPBOX_MEAN_PARAMS_URL, mean_params_path,
                                  expected_size_mb_min=0.1, expected_size_mb_max=10):
            return
    
    print(f"⚠️  Cannot download from Dropbox, creating default smpl_mean_params.npz...")
    print(f"  To download it, set DROPBOX_MEAN_PARAMS_URL environment variable.")
    
    # CRITICAL: pose dimension must match checkpoint requirements
    # Checkpoint uses JOINT_REP='6d' (6d rotation representation)
    # 24 joints (23 body + 1 root) × 6 dims = 144 dimensions
    # This MUST match the checkpoint's training config or we get dimension mismatch
    pose_dim = 144  # 6d representation: 24 joints × 6 = 144
    
    # Fall back to creating default mean parameters
    mean_params = {
        'pose': np.zeros(pose_dim, dtype=np.float32),  # Neutral pose (all zeros, 6d format)
        'shape': np.zeros(10, dtype=np.float32),  # Mean shape (all zeros)
        'cam': np.array([0.0, 0.0, 1.0], dtype=np.float32)  # Default camera: no translation, scale=1
    }
    
    np.savez(mean_params_path, **mean_params)
    print(f"  Created default: {mean_params_path}")

def _ensure_config_files_exist(checkpoint_path):
    """
    Helper function to ensure model_config.yaml and dataset_config.yaml exist
    for a given checkpoint path.
    """
    import os
    config_dir = os.path.dirname(os.path.dirname(checkpoint_path))  # logs/train/multiruns/hmr2/0/
    model_config_path = os.path.join(config_dir, "model_config.yaml")
    dataset_config_path = os.path.join(config_dir, "dataset_config.yaml")
    
    # Also ensure smpl_mean_params.npz and SMPL_to_J19.pkl exist
    from ..configs import CACHE_DIR_4DHUMANS
    data_dir = os.path.join(CACHE_DIR_4DHUMANS, "data")
    _ensure_smpl_mean_params_exists(data_dir)
    _ensure_smpl_joint_regressor_exists(data_dir)
    
    if not os.path.exists(model_config_path):
        print(f"Creating default model_config.yaml...")
        os.makedirs(config_dir, exist_ok=True)
        try:
            from ..configs import default_config, CACHE_DIR_4DHUMANS
            from yacs.config import CfgNode as CN
            default_cfg = default_config()
            default_cfg.defrost()
            
            # Add SMPL section (required for get_config with update_cachedir=True)
            if 'SMPL' not in default_cfg:
                default_cfg.SMPL = CN(new_allowed=True)
                default_cfg.SMPL.DATA_DIR = os.path.join(CACHE_DIR_4DHUMANS, "data")
                default_cfg.SMPL.MODEL_PATH = "data/smpl"
                default_cfg.SMPL.GENDER = "neutral"
                default_cfg.SMPL.NUM_BODY_JOINTS = 23
                default_cfg.SMPL.MEAN_PARAMS = "data/smpl_mean_params.npz"
                
                # Only set JOINT_REGRESSOR_EXTRA if file exists, otherwise leave it unset
                joint_regressor_path = os.path.join(CACHE_DIR_4DHUMANS, "data/SMPL_to_J19.pkl")
                if os.path.exists(joint_regressor_path):
                    default_cfg.SMPL.JOINT_REGRESSOR_EXTRA = "data/SMPL_to_J19.pkl"
                else:
                    # Don't set it - SMPL will work without extra joints (code checks if joint_regressor_extra is None)
                    print(f"  Note: SMPL_to_J19.pkl not found, SMPL will work without extra joints")
            
            # Add LOSS_WEIGHTS section with default values (required for HMR2 model initialization)
            if 'LOSS_WEIGHTS' not in default_cfg or not hasattr(default_cfg.LOSS_WEIGHTS, 'ADVERSARIAL'):
                if 'LOSS_WEIGHTS' not in default_cfg:
                    default_cfg.LOSS_WEIGHTS = CN(new_allowed=True)
                
                # Set default loss weights (inference doesn't need adversarial loss, set to 0)
                default_cfg.LOSS_WEIGHTS.ADVERSARIAL = 0.0  # Disabled for inference
                default_cfg.LOSS_WEIGHTS.KEYPOINTS_3D = 1.0
                default_cfg.LOSS_WEIGHTS.KEYPOINTS_2D = 1.0
                default_cfg.LOSS_WEIGHTS.BODY_POSE = 0.1
                default_cfg.LOSS_WEIGHTS.BETAS = 0.001
                default_cfg.LOSS_WEIGHTS.GLOBAL_ORIENT = 0.1
                default_cfg.LOSS_WEIGHTS.TRANSL = 1.0
                print(f"  Added default LOSS_WEIGHTS (ADVERSARIAL=0.0 for inference)")
            
            # Add MODEL.BACKBONE section (required for HMR2 model loading)
            if 'MODEL' not in default_cfg:
                default_cfg.MODEL = CN(new_allowed=True)
            
            # Set MODEL.IMAGE_SIZE to 256 (required for ViT backbone)
            default_cfg.MODEL.IMAGE_SIZE = 256
            default_cfg.MODEL.IMAGE_MEAN = [0.485, 0.456, 0.406]
            default_cfg.MODEL.IMAGE_STD = [0.229, 0.224, 0.225]
            
            # Add BACKBONE section (required for demo_yolo.py)
            if 'BACKBONE' not in default_cfg.MODEL:
                default_cfg.MODEL.BACKBONE = CN(new_allowed=True)
                default_cfg.MODEL.BACKBONE.TYPE = 'vit'
            
            # Add SMPL_HEAD section (required for build_smpl_head)
            if 'SMPL_HEAD' not in default_cfg.MODEL:
                default_cfg.MODEL.SMPL_HEAD = CN(new_allowed=True)
                default_cfg.MODEL.SMPL_HEAD.TYPE = 'transformer_decoder'
                default_cfg.MODEL.SMPL_HEAD.IN_CHANNELS = 2048
                # CRITICAL: Set JOINT_REP='6d' to match checkpoint (144 dims: 24 joints × 6)
                # This MUST match the checkpoint's training config or we get dimension mismatch
                default_cfg.MODEL.SMPL_HEAD.JOINT_REP = '6d'
                default_cfg.MODEL.SMPL_HEAD.TRANSFORMER_INPUT = 'zero'  # or 'mean_shape' (both work, 'zero' is default)
                default_cfg.MODEL.SMPL_HEAD.TRANSFORMER_DECODER = CN(new_allowed=True)
                default_cfg.MODEL.SMPL_HEAD.TRANSFORMER_DECODER.depth = 6
                default_cfg.MODEL.SMPL_HEAD.TRANSFORMER_DECODER.heads = 8
                default_cfg.MODEL.SMPL_HEAD.TRANSFORMER_DECODER.mlp_dim = 1024
                default_cfg.MODEL.SMPL_HEAD.TRANSFORMER_DECODER.dim_head = 64
                default_cfg.MODEL.SMPL_HEAD.TRANSFORMER_DECODER.dropout = 0.0
                default_cfg.MODEL.SMPL_HEAD.TRANSFORMER_DECODER.emb_dropout = 0.0
                default_cfg.MODEL.SMPL_HEAD.TRANSFORMER_DECODER.norm = 'layer'
                default_cfg.MODEL.SMPL_HEAD.TRANSFORMER_DECODER.context_dim = 1280
            
            default_cfg.freeze()
            
            with open(model_config_path, 'w') as f:
                f.write(default_cfg.dump())
            print(f"  Created: {model_config_path}")
        except Exception as e:
            print(f"  ⚠️  Failed to create model_config.yaml: {e}")
            raise
    
    if not os.path.exists(dataset_config_path):
        print(f"Creating default dataset_config.yaml...")
        try:
            from hmr2.configs import dataset_config as get_dataset_config
            dataset_cfg = get_dataset_config()
            with open(dataset_config_path, 'w') as f:
                f.write(dataset_cfg.dump())
            print(f"  Created: {dataset_config_path}")
        except Exception as e:
            print(f"  ⚠️  Failed to create dataset_config.yaml: {e}")
            # If datasets_tar.yaml is missing, this might fail, but model_config is more critical
            # Only raise if model_config also doesn't exist
            if not os.path.exists(model_config_path):
                raise


def download_models(folder=CACHE_DIR_4DHUMANS):
    """Download checkpoints and files for running inference.
    """
    import os
    import sys
    from pathlib import Path
    
    # Import CACHE_DIR_4DHUMANS at function level to avoid UnboundLocalError
    # (Python treats it as local if imported later in the function)
    from ..configs import CACHE_DIR_4DHUMANS as _CACHE_DIR
    
    # PRIORITY 1: Check if models exist in DEFAULT location (from build-time download in image)
    DEFAULT_CACHE = Path(os.path.join(os.environ.get("HOME"), ".cache", "4DHumans"))
    default_checkpoint = DEFAULT_CACHE / "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt"
    
    build_models_found = False
    if default_checkpoint.exists():
        try:
            file_size_gb = default_checkpoint.stat().st_size / (1024**3)
            if file_size_gb > 2.0:
                print(f"[DEBUG download_models] ✓ Found checkpoint in image cache (from build): {default_checkpoint} ({file_size_gb:.2f} GB)")
                print(f"[DEBUG download_models]   Using build-time models (baked into image)")
                folder = str(DEFAULT_CACHE)
                _CACHE_DIR = folder
                build_models_found = True
                print(f"[DEBUG download_models]   Updated folder to: {folder}")
            else:
                print(f"[DEBUG download_models] ⚠️  Build checkpoint too small ({file_size_gb:.2f} GB), checking volume...")
        except Exception as e:
            print(f"[DEBUG download_models] ⚠️  Error checking build checkpoint: {e}, checking volume...")
    
    # PRIORITY 2: Check if RunPod volume exists and has models (for runtime caching)
    # Only check volume if we didn't find build-time models
    if not build_models_found:
        RUNPOD_VOLUME_PATH = Path("/runpod-volume")
        VOLUME_CACHE_DIR = RUNPOD_VOLUME_PATH / "4DHumans"
        
        if RUNPOD_VOLUME_PATH.exists():
            print(f"[DEBUG download_models] RunPod Network Volume detected at {RUNPOD_VOLUME_PATH}")
            # Check if volume has cached models
            volume_checkpoint = VOLUME_CACHE_DIR / "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt"
            if volume_checkpoint.exists():
                try:
                    file_size_gb = volume_checkpoint.stat().st_size / (1024**3)
                    if file_size_gb > 2.0:
                        print(f"[DEBUG download_models] ✓ Found checkpoint in Network Volume: {volume_checkpoint} ({file_size_gb:.2f} GB)")
                        print(f"[DEBUG download_models]   Using volume cache (persistent across jobs)")
                        # Use volume directory directly
                        folder = str(VOLUME_CACHE_DIR)
                        _CACHE_DIR = folder
                        print(f"[DEBUG download_models]   Updated folder to: {folder}")
                    else:
                        print(f"[DEBUG download_models] ⚠️  Volume checkpoint too small ({file_size_gb:.2f} GB)")
                except Exception as e:
                    print(f"[DEBUG download_models] ⚠️  Error checking volume checkpoint: {e}")
    
    # CRITICAL: Print immediately to ensure we see this function is being called
    print(f"[DEBUG download_models] FUNCTION CALLED - folder={folder}")
    sys.stdout.flush()
    
    os.makedirs(folder, exist_ok=True)
    
    # Check both the cache folder AND the local 4D-Humans-clean folder
    script_dir = Path(__file__).parent.parent  # hmr2 folder
    local_data_folder = script_dir.parent  # 4D-Humans-clean folder
    
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
    
    # Check if BOTH checkpoint AND SMPL files exist
    checkpoint_exists = os.path.exists(cache_files[1])
    smpl_exists = os.path.exists(cache_files[0])
    
    # Also check for basicModel files (v1.0.0 and v1.1.0) as they can be converted
    smpl_basic_v1 = os.path.join(folder, "data/basicModel_neutral_lbs_10_207_0_v1.0.0.pkl")
    smpl_basic_v11 = os.path.join(folder, "data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl")
    smpl_basic_v11_alt = os.path.join(folder, "data/basicModel_neutral_lbs_10_207_0_v1.1.0.pkl")
    smpl_exists = smpl_exists or os.path.exists(smpl_basic_v1) or os.path.exists(smpl_basic_v11) or os.path.exists(smpl_basic_v11_alt)
    
    print(f"[DEBUG download_models] CACHE_DIR_4DHUMANS = {_CACHE_DIR}")
    print(f"[DEBUG download_models] folder = {folder}")
    print(f"[DEBUG download_models] Current working directory: {os.getcwd()}")
    print(f"[DEBUG download_models] checkpoint_exists={checkpoint_exists}, smpl_exists={smpl_exists}")
    print(f"[DEBUG download_models] cache_files[0] (SMPL_NEUTRAL)={cache_files[0]}, exists={os.path.exists(cache_files[0])}")
    print(f"[DEBUG download_models] cache_files[1] (checkpoint)={cache_files[1]}, exists={os.path.exists(cache_files[1])}")
    print(f"[DEBUG download_models] smpl_basic_v1={smpl_basic_v1}, exists={os.path.exists(smpl_basic_v1)}")
    print(f"[DEBUG download_models] smpl_basic_v11={smpl_basic_v11}, exists={os.path.exists(smpl_basic_v11)}")
    print(f"[DEBUG download_models] smpl_basic_v11_alt={smpl_basic_v11_alt}, exists={os.path.exists(smpl_basic_v11_alt)}")
    
    if checkpoint_exists and smpl_exists:
        print("HMR2 data found in cache, skipping download.")
        # Ensure config files exist even if found in cache
        expected_checkpoint = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")
        _ensure_config_files_exist(expected_checkpoint)
        return
    elif checkpoint_exists and not smpl_exists:
        print(f"⚠️  Checkpoint found but SMPL files missing. Downloading from Dropbox...")
        
        # Download from Dropbox (required)
        DROPBOX_SMPL_NEUTRAL_URL = os.environ.get("DROPBOX_SMPL_NEUTRAL_URL")
        smpl_basic_model_v11 = os.path.join(folder, "data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl")
        smpl_dir = os.path.dirname(smpl_basic_model_v11)
        os.makedirs(smpl_dir, exist_ok=True)
        
        if not DROPBOX_SMPL_NEUTRAL_URL:
            print(f"⚠️  DROPBOX_SMPL_NEUTRAL_URL not set. SMPL files required for pipeline.")
            print(f"  Set DROPBOX_SMPL_NEUTRAL_URL environment variable in RunPod endpoint settings.")
            print(f"  See DROPBOX_ENV_VARS_GUIDE.md for instructions.")
        elif _download_from_dropbox(DROPBOX_SMPL_NEUTRAL_URL, smpl_basic_model_v11,
                                     expected_size_mb_min=200, expected_size_mb_max=300):
            print(f"✅ SMPL downloaded from Dropbox!")
            expected_checkpoint = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")
            _ensure_config_files_exist(expected_checkpoint)
            data_dir = os.path.join(folder, "data")
            _ensure_smpl_mean_params_exists(data_dir)
            _ensure_smpl_joint_regressor_exists(data_dir)
            return
        else:
            print(f"⚠️  Failed to download SMPL from Dropbox. Pipeline may fail without SMPL files.")
        # Continue to tar.gz download below if Dropbox failed
    elif not checkpoint_exists:
        # Checkpoint missing - will try Dropbox download above
        pass
    
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
            print(f"[DEBUG download_models] HMR2 checkpoint found at {checkpoint_path}")
            # Still copy to expected cache location if not already there
            expected_cache_path = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")
            if checkpoint_path != expected_cache_path and not os.path.exists(expected_cache_path):
                import shutil
                os.makedirs(os.path.dirname(expected_cache_path), exist_ok=True)
                shutil.copy(checkpoint_path, expected_cache_path)
                print(f"[DEBUG download_models] Copied checkpoint to expected location")
            
            # Ensure config files exist even if checkpoint was already there
            _ensure_config_files_exist(expected_cache_path)
            
            # CRITICAL FIX: Check for SMPL even when checkpoint is found in alternative path
            print(f"[DEBUG download_models] Checkpoint found, now checking for SMPL files...")
            smpl_file = os.path.join(folder, "data/smpl/SMPL_NEUTRAL.pkl")
            smpl_basic_v1 = os.path.join(folder, "data/basicModel_neutral_lbs_10_207_0_v1.0.0.pkl")
            smpl_basic_v11 = os.path.join(folder, "data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl")
            smpl_basic_v11_alt = os.path.join(folder, "data/basicModel_neutral_lbs_10_207_0_v1.1.0.pkl")
            
            smpl_exists = (os.path.exists(smpl_file) or 
                          os.path.exists(smpl_basic_v1) or 
                          os.path.exists(smpl_basic_v11) or 
                          os.path.exists(smpl_basic_v11_alt))
            
            print(f"[DEBUG download_models] SMPL check: smpl_exists={smpl_exists}")
            print(f"[DEBUG download_models]   smpl_file={smpl_file}, exists={os.path.exists(smpl_file)}")
            print(f"[DEBUG download_models]   smpl_basic_v1={smpl_basic_v1}, exists={os.path.exists(smpl_basic_v1)}")
            print(f"[DEBUG download_models]   smpl_basic_v11={smpl_basic_v11}, exists={os.path.exists(smpl_basic_v11)}")
            print(f"[DEBUG download_models]   smpl_basic_v11_alt={smpl_basic_v11_alt}, exists={os.path.exists(smpl_basic_v11_alt)}")
            
            if not smpl_exists:
                print(f"[DEBUG download_models] ⚠️  SMPL files missing! Attempting download from Dropbox...")
                # Download from Dropbox
                DROPBOX_SMPL_NEUTRAL_URL = os.environ.get("DROPBOX_SMPL_NEUTRAL_URL")
                smpl_basic_model_v11 = os.path.join(folder, "data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl")
                
                if not DROPBOX_SMPL_NEUTRAL_URL:
                    print(f"[DEBUG download_models] ⚠️  DROPBOX_SMPL_NEUTRAL_URL not set. SMPL files required.")
                elif _download_from_dropbox(DROPBOX_SMPL_NEUTRAL_URL, smpl_basic_model_v11,
                                           expected_size_mb_min=200, expected_size_mb_max=300):
                    print(f"[DEBUG download_models] ✅ SMPL downloaded from Dropbox!")
                else:
                    print(f"[DEBUG download_models] ⚠️  Failed to download SMPL from Dropbox.")
            else:
                print(f"[DEBUG download_models] ✅ SMPL files found, all good!")
            
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
    
    # Download from Dropbox (required - no Google Drive fallback)
    DROPBOX_CHECKPOINT_URL = os.environ.get("DROPBOX_CHECKPOINT_URL")
    
    checkpoint_dest = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")
    
    # IMPORTANT: Check if checkpoint already exists before attempting download
    # This handles cases where volume has cached models from previous runs
    if os.path.exists(checkpoint_dest):
        file_size_gb = os.path.getsize(checkpoint_dest) / (1024**3)
        if file_size_gb > 2.0:  # Checkpoint should be ~2.5GB
            print(f"✅ Checkpoint found in cache (volume working!): {checkpoint_dest} ({file_size_gb:.2f} GB)")
            _ensure_config_files_exist(checkpoint_dest)
            data_dir = os.path.join(_CACHE_DIR, "data")
            _ensure_smpl_mean_params_exists(data_dir)
            _ensure_smpl_joint_regressor_exists(data_dir)
            return  # Skip download, use cached files
    
    # Download checkpoint from Dropbox (required)
    if not os.path.exists(checkpoint_dest):
        if not DROPBOX_CHECKPOINT_URL:
            error_msg = (
                f"ERROR: Checkpoint not found and DROPBOX_CHECKPOINT_URL not set.\n"
                f"Required file: epoch=35-step=1000000.ckpt\n"
                f"Location: {checkpoint_dest}\n"
                f"\nSolution: Set DROPBOX_CHECKPOINT_URL environment variable in RunPod endpoint settings.\n"
                f"See DROPBOX_ENV_VARS_GUIDE.md for instructions."
            )
            print(error_msg)
            raise FileNotFoundError(error_msg)
        
        print(f"Checkpoint not found. Downloading from Dropbox...")
        if _download_from_dropbox(DROPBOX_CHECKPOINT_URL, checkpoint_dest, 
                                  expected_size_mb_min=2000, expected_size_mb_max=3000):
            # Validate size after download
            if os.path.exists(checkpoint_dest):
                file_size = os.path.getsize(checkpoint_dest)
                file_size_mb = file_size / 1024 / 1024
                if file_size_mb > 2000:
                    print(f"✅ Checkpoint downloaded from Dropbox! ({file_size_mb:.1f}MB)")
                    # Ensure config files exist after downloading
                    _ensure_config_files_exist(checkpoint_dest)
                    data_dir = os.path.join(_CACHE_DIR, "data")
                    _ensure_smpl_mean_params_exists(data_dir)
                    _ensure_smpl_joint_regressor_exists(data_dir)
                    
                    # Check if SMPL files exist - if not, download from Dropbox
                    smpl_file = os.path.join(folder, "data/smpl/SMPL_NEUTRAL.pkl")
                    smpl_basic_model_v1 = os.path.join(folder, "data/basicModel_neutral_lbs_10_207_0_v1.0.0.pkl")
                    smpl_basic_model_v11 = os.path.join(folder, "data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl")
                    
                    if not os.path.exists(smpl_file) and not os.path.exists(smpl_basic_model_v1) and not os.path.exists(smpl_basic_model_v11):
                        print("⚠️  SMPL files not found. Downloading from Dropbox...")
                        DROPBOX_SMPL_NEUTRAL_URL = os.environ.get("DROPBOX_SMPL_NEUTRAL_URL")
                        if DROPBOX_SMPL_NEUTRAL_URL:
                            if _download_from_dropbox(DROPBOX_SMPL_NEUTRAL_URL, smpl_basic_model_v11,
                                                      expected_size_mb_min=200, expected_size_mb_max=300):
                                print(f"✅ SMPL downloaded from Dropbox!")
                        else:
                            print(f"⚠️  DROPBOX_SMPL_NEUTRAL_URL not set. SMPL files required for pipeline.")
                    else:
                        print("✅ SMPL files found, skipping download")
                    return
                else:
                    print(f"⚠️  Downloaded file size unexpected: {file_size_mb:.1f}MB (expected ~2500MB)")
                    os.remove(checkpoint_dest)
        else:
            error_msg = (
                f"ERROR: Failed to download checkpoint from Dropbox.\n"
                f"Required file: epoch=35-step=1000000.ckpt\n"
                f"Location: {checkpoint_dest}\n"
                f"\nSolutions:\n"
                f"1. Verify DROPBOX_CHECKPOINT_URL is correct in RunPod endpoint settings\n"
                f"2. Ensure Dropbox link has ?dl=1 for direct download\n"
                f"3. Mount checkpoint via RunPod Volumes\n"
                f"4. Include checkpoint in Docker image build"
            )
            print(error_msg)
            raise FileNotFoundError(error_msg)
    
    download_files = {
        "hmr2_data.tar.gz"      : ["https://people.eecs.berkeley.edu/~jathushan/projects/4dhumans/hmr2_data.tar.gz", folder],
    }

    for file_name, url in download_files.items():
        output_path = os.path.join(url[1], file_name)
        if not os.path.exists(output_path):
            print("Attempting to download file: " + file_name)
            try:
                # output = gdown.cached_download(url[0], output_path, fuzzy=True)
                cache_url(url[0], output_path)  # Download file
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
                checkpoint_paths = [
                    os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt"),
                    str(local_data_folder / "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt"),
                    os.path.join(folder, "checkpoints/epoch=35-step=1000000.ckpt"),
                    str(local_data_folder / "checkpoints/epoch=35-step=1000000.ckpt"),
                    "/workspace/checkpoints/epoch=35-step=1000000.ckpt",
                    "/workspace/models/epoch=35-step=1000000.ckpt",
                    "/runpod-volume/epoch=35-step=1000000.ckpt",
                ]
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
                print(f"Extracting {file_name}...")
                print(f"  Command: tar -xzf {output_path} -C {url[1]}")
                result = os.system(f"tar -xzf {output_path} -C {url[1]}")
                if result != 0:
                    print(f"⚠️  tar extraction returned non-zero exit code: {result}")
                else:
                    print(f"✅ Successfully extracted {file_name}")
                
                # After extracting, ensure config files exist
                expected_checkpoint = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")
                if os.path.exists(expected_checkpoint):
                    _ensure_config_files_exist(expected_checkpoint)
                
                # Verify SMPL files were extracted
                smpl_check = os.path.join(folder, "data/smpl/SMPL_NEUTRAL.pkl")
                if os.path.exists(smpl_check):
                    print(f"✅ SMPL files found after extraction: {smpl_check}")
                else:
                    print(f"⚠️  WARNING: SMPL files not found after extraction at {smpl_check}")
                    print(f"    Listing contents of {os.path.join(folder, 'data')}...")
                    data_dir = os.path.join(folder, "data")
                    if os.path.exists(data_dir):
                        import subprocess
                        subprocess.run(["find", data_dir, "-name", "*SMPL*", "-o", "-name", "*smpl*"], check=False)

def check_smpl_exists():
    import os
    import subprocess
    import shutil
    # Get absolute paths
    cache_dir = os.path.abspath(CACHE_DIR_4DHUMANS)
    candidates = [
        f'{cache_dir}/data/smpl/SMPL_NEUTRAL.pkl',
        # Check cache directory first
        f'{cache_dir}/data/basicModel_neutral_lbs_10_207_0_v1.0.0.pkl',
        f'{cache_dir}/data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl',
        f'{cache_dir}/data/basicModel_neutral_lbs_10_207_0_v1.1.0.pkl',
        # Also check relative paths (for local development)
        f'data/basicModel_neutral_lbs_10_207_0_v1.0.0.pkl',
        f'data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl',  # Also check v1.1.0 (lowercase)
        f'data/basicModel_neutral_lbs_10_207_0_v1.1.0.pkl',  # Also check v1.1.0 (mixed case)
    ]
    
    # Debug: print what we're checking
    # CACHE_DIR_4DHUMANS is imported at top of file
    print(f"[DEBUG check_smpl_exists] CACHE_DIR_4DHUMANS = {CACHE_DIR_4DHUMANS}")
    print(f"[DEBUG check_smpl_exists] cache_dir (abs) = {cache_dir}")
    print(f"[DEBUG check_smpl_exists] Current working directory: {os.getcwd()}")
    
    candidates_exist = [os.path.exists(c) for c in candidates]
    
    # Debug: print which files exist
    for i, (cand, exists) in enumerate(zip(candidates, candidates_exist)):
        if exists:
            print(f"[DEBUG check_smpl_exists] ✅ Found: {cand}")
        else:
            print(f"[DEBUG check_smpl_exists] ❌ Not found: {cand}")
    
    if not any(candidates_exist):
        # List what's actually in the cache directory
        if os.path.exists(cache_dir):
            print(f"[DEBUG check_smpl_exists] Listing contents of {cache_dir}/data:")
            data_dir = os.path.join(cache_dir, "data")
            if os.path.exists(data_dir):
                result = subprocess.run(["find", data_dir, "-name", "*.pkl", "-type", "f"], capture_output=True, text=True)
                if result.stdout:
                    print(f"[DEBUG check_smpl_exists] Found .pkl files in data dir:")
                    for line in result.stdout.strip().split('\n'):
                        print(f"[DEBUG check_smpl_exists]   {line}")
                else:
                    print(f"[DEBUG check_smpl_exists] No .pkl files found in {data_dir}")
            
            # Also check the checkpoint directory and temp folders (where files might have been downloaded)
            # Search in both checkpoint directory and entire cache for temp folders
            search_dirs = [cache_dir]  # Search entire cache directory recursively
            checkpoint_dir = os.path.join(cache_dir, "logs/train/multiruns/hmr2/0/checkpoints")
            if os.path.exists(checkpoint_dir):
                search_dirs.append(checkpoint_dir)
            
            print(f"[DEBUG check_smpl_exists] Checking cache directory and temp folders for .pkl files:")
            all_pkl_files = []
            for search_dir in search_dirs:
                if os.path.exists(search_dir):
                    result = subprocess.run(["find", search_dir, "-name", "*.pkl", "-type", "f"], capture_output=True, text=True)
                    if result.stdout:
                        all_pkl_files.extend(result.stdout.strip().split('\n'))
            
            if all_pkl_files:
                print(f"[DEBUG check_smpl_exists] Found .pkl files:")
                smpl_files_moved = []
                for file_path in all_pkl_files:
                    file_path = file_path.strip()
                    if not file_path:
                        continue
                    print(f"[DEBUG check_smpl_exists]   {file_path}")
                    # Check if this looks like a SMPL file (not a checkpoint)
                    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    # Check if it's a SMPL file (contains "basicmodel" and is reasonable size, but not the checkpoint)
                    if ("basicmodel" in file_path.lower()) and file_size < 500_000_000 and "epoch=" not in file_path:  # Less than 500MB (checkpoints are 2.5GB)
                        # Determine correct path based on filename
                        filename = os.path.basename(file_path).lower()
                        if "neutral" in filename:
                            correct_path = os.path.join(cache_dir, "data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl")
                        elif "basicmodel_f" in filename or "female" in filename:
                            correct_path = os.path.join(cache_dir, "data/basicmodel_f_lbs_10_207_0_v1.1.0.pkl")
                        elif "basicmodel_m" in filename or "male" in filename:
                            correct_path = os.path.join(cache_dir, "data/basicmodel_m_lbs_10_207_0_v1.1.0.pkl")
                        else:
                            # Default to neutral
                            correct_path = os.path.join(cache_dir, "data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl")
                        
                        print(f"[DEBUG check_smpl_exists] ⚠️  Found SMPL file in wrong location! ({file_size/1024/1024:.1f}MB)")
                        print(f"[DEBUG check_smpl_exists] Moving {file_path} to {correct_path}...")
                        try:
                            os.makedirs(os.path.dirname(correct_path), exist_ok=True)
                            if os.path.exists(correct_path):
                                print(f"[DEBUG check_smpl_exists] Target path already exists, removing old file...")
                                os.remove(correct_path)
                            shutil.move(file_path, correct_path)
                            print(f"[DEBUG check_smpl_exists] ✅ Moved successfully!")
                            smpl_files_moved.append(correct_path)
                        except Exception as e:
                            import traceback
                            print(f"[DEBUG check_smpl_exists] ⚠️  Failed to move file: {e}")
                            traceback.print_exc()
                
                # After moving files, recheck candidates
                if smpl_files_moved:
                    print(f"[DEBUG check_smpl_exists] Rechecking after moving {len(smpl_files_moved)} files...")
                    candidates_exist = [os.path.exists(c) for c in candidates]
                    # Update debug output
                    for i, (cand, exists) in enumerate(zip(candidates, candidates_exist)):
                        if exists:
                            print(f"[DEBUG check_smpl_exists] ✅ Found: {cand}")
        
        if not any(candidates_exist):
            raise FileNotFoundError(f"SMPL model not found. Please download it from https://smplify.is.tue.mpg.de/ and place it at data/basicModel_neutral_lbs_10_207_0_v1.0.0.pkl")

    # Code expects SMPL models at CACHE_DIR_4DHUMANS/data/smpl/SMPL_NEUTRAL.pkl, SMPL_MALE.pkl, SMPL_FEMALE.pkl
    # Convert basicmodel files if needed
    smpl_dir = os.path.join(cache_dir, "data", "smpl")
    os.makedirs(smpl_dir, exist_ok=True)
    
    # Convert NEUTRAL model
    neutral_target = os.path.join(smpl_dir, "SMPL_NEUTRAL.pkl")
    if not os.path.exists(neutral_target):
        # Find which basicModel file exists (skip first candidate which is SMPL_NEUTRAL)
        for i in range(1, len(candidates)):
            if candidates_exist[i] and "neutral" in candidates[i].lower():
                convert_pkl(candidates[i], neutral_target)
                break
    
    # Convert MALE model
    male_target = os.path.join(smpl_dir, "SMPL_MALE.pkl")
    male_sources = [
        os.path.join(cache_dir, "data", "basicmodel_m_lbs_10_207_0_v1.1.0.pkl"),
        os.path.join(cache_dir, "data", "basicModel_m_lbs_10_207_0_v1.1.0.pkl"),
        os.path.join(cache_dir, "data", "basicmodel_m_lbs_10_207_0_v1.0.0.pkl"),
        os.path.join(cache_dir, "data", "basicModel_m_lbs_10_207_0_v1.0.0.pkl"),
    ]
    # Also check temp folders where files might have been downloaded
    checkpoint_dir = os.path.join(cache_dir, "logs/train/multiruns/hmr2/0/checkpoints")
    if os.path.exists(checkpoint_dir):
        for temp_dir_name in os.listdir(checkpoint_dir):
            if "temp_" in temp_dir_name:  # Check for any temp folders (legacy cleanup)
                temp_dir = os.path.join(checkpoint_dir, temp_dir_name)
                if os.path.isdir(temp_dir):
                    # Search for basicmodel_m files in temp folder
                    for root, dirs, files in os.walk(temp_dir):
                        for f in files:
                            if ("basicmodel_m" in f.lower() or "male" in f.lower()) and f.endswith(".pkl"):
                                temp_file = os.path.join(root, f)
                                # Move to data directory if not already there
                                data_file = os.path.join(cache_dir, "data", f)
                                if not os.path.exists(data_file):
                                    os.makedirs(os.path.dirname(data_file), exist_ok=True)
                                    try:
                                        shutil.move(temp_file, data_file)
                                        print(f"[DEBUG check_smpl_exists] ✅ Moved MALE model from temp folder: {data_file}")
                                    except Exception as e:
                                        print(f"[DEBUG check_smpl_exists] ⚠️  Could not move MALE model: {e}")
                                male_sources.insert(0, data_file)  # Prioritize moved file
                                break
    
    if not os.path.exists(male_target):
        for source in male_sources:
            if os.path.exists(source):
                convert_pkl(source, male_target)
                print(f"[DEBUG check_smpl_exists] ✅ Converted MALE model: {male_target}")
                break
    
    # Convert FEMALE model
    female_target = os.path.join(smpl_dir, "SMPL_FEMALE.pkl")
    female_sources = [
        os.path.join(cache_dir, "data", "basicmodel_f_lbs_10_207_0_v1.1.0.pkl"),
        os.path.join(cache_dir, "data", "basicModel_f_lbs_10_207_0_v1.1.0.pkl"),
        os.path.join(cache_dir, "data", "basicmodel_f_lbs_10_207_0_v1.0.0.pkl"),
        os.path.join(cache_dir, "data", "basicModel_f_lbs_10_207_0_v1.0.0.pkl"),
    ]
    # Also check temp folders where files might have been downloaded
    checkpoint_dir = os.path.join(cache_dir, "logs/train/multiruns/hmr2/0/checkpoints")
    if os.path.exists(checkpoint_dir):
        for temp_dir_name in os.listdir(checkpoint_dir):
            if "temp_" in temp_dir_name:  # Check for any temp folders (legacy cleanup)
                temp_dir = os.path.join(checkpoint_dir, temp_dir_name)
                if os.path.isdir(temp_dir):
                    # Search for basicmodel_f files in temp folder
                    for root, dirs, files in os.walk(temp_dir):
                        for f in files:
                            if ("basicmodel_f" in f.lower() or "female" in f.lower()) and f.endswith(".pkl"):
                                temp_file = os.path.join(root, f)
                                # Move to data directory if not already there
                                data_file = os.path.join(cache_dir, "data", f)
                                if not os.path.exists(data_file):
                                    os.makedirs(os.path.dirname(data_file), exist_ok=True)
                                    try:
                                        shutil.move(temp_file, data_file)
                                        print(f"[DEBUG check_smpl_exists] ✅ Moved FEMALE model from temp folder: {data_file}")
                                    except Exception as e:
                                        print(f"[DEBUG check_smpl_exists] ⚠️  Could not move FEMALE model: {e}")
                                female_sources.insert(0, data_file)  # Prioritize moved file
                                break
    
    if not os.path.exists(female_target):
        for source in female_sources:
            if os.path.exists(source):
                convert_pkl(source, female_target)
                print(f"[DEBUG check_smpl_exists] ✅ Converted FEMALE model: {female_target}")
                break

    return True

# Convert SMPL pkl file to be compatible with Python 3
# Script is from https://rebeccabilbro.github.io/convert-py2-pickles-to-py3/
def convert_pkl(old_pkl, new_pkl):
    """
    Convert a Python 2 pickle to Python 3
    """
    import dill
    import pickle
    import os

    print(f"[DEBUG convert_pkl] Converting {old_pkl} to {new_pkl}...")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(new_pkl), exist_ok=True)
    
    # Convert Python 2 "ObjectType" to Python 3 object
    dill._dill._reverse_typemap["ObjectType"] = object

    # Open the pickle using latin1 encoding
    with open(old_pkl, "rb") as f:
        loaded = pickle.load(f, encoding="latin1")

    # Re-save as Python 3 pickle
    with open(new_pkl, "wb") as outfile:
        pickle.dump(loaded, outfile)
    
    print(f"[DEBUG convert_pkl] ✅ Successfully converted to {new_pkl}")

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
