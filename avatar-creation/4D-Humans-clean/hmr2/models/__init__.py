from .smpl_wrapper import SMPL
from .hmr2 import HMR2
from .discriminator import Discriminator

from ..utils.download import cache_url
from ..configs import CACHE_DIR_4DHUMANS


def _download_from_gdrive_folder(file_name, output_path, folder_id=None, file_id=None):
    """
    Helper function to download a file from Google Drive.
    Can use either a file_id directly, or search for file_name in a folder_id.
    """
    import os
    import sys
    import subprocess
    import shutil
    
    if os.path.exists(output_path):
        return True  # File already exists
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        # Install gdown if not available
        try:
            import gdown
        except ImportError:
            print("Installing gdown...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "gdown"])
            import gdown
        
        # If we have a direct file_id, use it
        if file_id:
            gdrive_url = f"https://drive.google.com/uc?id={file_id}"
            print(f"[DEBUG] Downloading {file_name} from: {gdrive_url}")
            temp_file = os.path.join(os.path.dirname(output_path), f"temp_{file_name}_{os.getpid()}")
            gdown.download(gdrive_url, output=temp_file, quiet=False)
            
            if os.path.exists(temp_file):
                if os.path.exists(output_path):
                    os.remove(output_path)
                shutil.move(temp_file, output_path)
                print(f"✅ Downloaded {file_name} from Google Drive!")
                return True
        
        # If we have a folder_id, try to download the entire folder and extract the file
        # Note: gdown folder download requires folder to be shared with "anyone with link"
        if folder_id:
            print(f"[DEBUG] Attempting to download {file_name} from folder {folder_id}...")
            # Try using gdown folder download
            temp_folder = os.path.join(os.path.dirname(output_path), f"temp_gdrive_folder_{os.getpid()}")
            try:
                os.makedirs(temp_folder, exist_ok=True)
                # gdown.download_folder can download a folder if shared properly
                gdown.download_folder(f"https://drive.google.com/drive/folders/{folder_id}", output=temp_folder, quiet=False, use_cookies=False)
                
                # Search for the file in the downloaded folder
                for root, dirs, files in os.walk(temp_folder):
                    for f in files:
                        if f == file_name or f.lower() == file_name.lower():
                            found_file = os.path.join(root, f)
                            shutil.move(found_file, output_path)
                            print(f"✅ Found and moved {file_name} from Google Drive folder!")
                            shutil.rmtree(temp_folder, ignore_errors=True)
                            return True
                
                shutil.rmtree(temp_folder, ignore_errors=True)
            except Exception as e:
                print(f"[DEBUG] Folder download failed: {e}")
                if os.path.exists(temp_folder):
                    shutil.rmtree(temp_folder, ignore_errors=True)
        
    except Exception as e:
        print(f"[DEBUG] Download failed: {e}")
        import traceback
        traceback.print_exc()
    
    return False

def _ensure_smpl_joint_regressor_exists(data_dir):
    """
    Helper function to download or create SMPL_to_J19.pkl if it doesn't exist.
    Tries to download from Google Drive first, then makes config optional if missing.
    """
    import os
    import sys
    
    joint_regressor_path = os.path.join(data_dir, "SMPL_to_J19.pkl")
    
    if os.path.exists(joint_regressor_path):
        return  # File already exists
    
    os.makedirs(data_dir, exist_ok=True)
    
    # Try downloading from Google Drive first
    # Can use either individual file ID or folder ID
    # Default folder ID: https://drive.google.com/drive/folders/1bxWXAKEOdBLiFIXQqnxoTjwVIbrqmY8O
    GOOGLE_DRIVE_JOINT_REGRESSOR_ID = os.environ.get("GOOGLE_DRIVE_JOINT_REGRESSOR_ID")
    GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "1bxWXAKEOdBLiFIXQqnxoTjwVIbrqmY8O")  # For downloading from folder
    
    if GOOGLE_DRIVE_JOINT_REGRESSOR_ID or GOOGLE_DRIVE_FOLDER_ID:
        print(f"Attempting to download SMPL_to_J19.pkl from Google Drive...")
        if _download_from_gdrive_folder("SMPL_to_J19.pkl", joint_regressor_path, 
                                        folder_id=GOOGLE_DRIVE_FOLDER_ID, 
                                        file_id=GOOGLE_DRIVE_JOINT_REGRESSOR_ID):
            return
    
    # If download failed or not configured, we'll make it optional in config
    print(f"⚠️  SMPL_to_J19.pkl not found. The code will work without extra joints.")
    print(f"  To download it, set GOOGLE_DRIVE_JOINT_REGRESSOR_ID or GOOGLE_DRIVE_FOLDER_ID environment variable.")

def _ensure_smpl_mean_params_exists(data_dir):
    """
    Helper function to download or create smpl_mean_params.npz if it doesn't exist.
    Tries to download from Google Drive first, then falls back to creating default values.
    """
    import os
    import sys
    import numpy as np
    
    mean_params_path = os.path.join(data_dir, "smpl_mean_params.npz")
    
    if os.path.exists(mean_params_path):
        return  # File already exists
    
    os.makedirs(data_dir, exist_ok=True)
    
    # Try downloading from Google Drive first
    # Can use either individual file ID or folder ID
    # Default folder ID: https://drive.google.com/drive/folders/1bxWXAKEOdBLiFIXQqnxoTjwVIbrqmY8O
    # Default file ID: https://drive.google.com/file/d/1cqbspPE9LM2ysB_YvBcRZR3JGVb3ve_I/view
    GOOGLE_DRIVE_MEAN_PARAMS_ID = os.environ.get("GOOGLE_DRIVE_MEAN_PARAMS_ID", "1cqbspPE9LM2ysB_YvBcRZR3JGVb3ve_I")
    GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "1bxWXAKEOdBLiFIXQqnxoTjwVIbrqmY8O")  # For downloading from folder
    
    if GOOGLE_DRIVE_MEAN_PARAMS_ID or GOOGLE_DRIVE_FOLDER_ID:
        print(f"Attempting to download smpl_mean_params.npz from Google Drive...")
        if _download_from_gdrive_folder("smpl_mean_params.npz", mean_params_path,
                                        folder_id=GOOGLE_DRIVE_FOLDER_ID,
                                        file_id=GOOGLE_DRIVE_MEAN_PARAMS_ID):
            return
    
    print(f"⚠️  Cannot download from Google Drive, creating default smpl_mean_params.npz...")
    
    # Fall back to creating default mean parameters
    mean_params = {
        'pose': np.zeros(72, dtype=np.float32),  # Neutral pose (all zeros)
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
    from hmr2.configs import CACHE_DIR_4DHUMANS
    data_dir = os.path.join(CACHE_DIR_4DHUMANS, "data")
    _ensure_smpl_mean_params_exists(data_dir)
    _ensure_smpl_joint_regressor_exists(data_dir)
    
    if not os.path.exists(model_config_path):
        print(f"Creating default model_config.yaml...")
        os.makedirs(config_dir, exist_ok=True)
        try:
            from hmr2.configs import default_config, CACHE_DIR_4DHUMANS
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
                
                # Only set JOINT_REGRESSOR_EXTRA if file exists, otherwise leave it unset
                joint_regressor_path = os.path.join(CACHE_DIR_4DHUMANS, "data/SMPL_to_J19.pkl")
                if os.path.exists(joint_regressor_path):
                    default_cfg.SMPL.JOINT_REGRESSOR_EXTRA = "data/SMPL_to_J19.pkl"
                else:
                    # Don't set it - SMPL will work without extra joints
                    print(f"  Note: SMPL_to_J19.pkl not found, SMPL will work without extra joints")
            
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
        print(f"⚠️  Checkpoint found but SMPL files missing. Trying Google Drive first...")
        # Try Google Drive SMPL download first
        # Default folder ID: https://drive.google.com/drive/folders/1bxWXAKEOdBLiFIXQqnxoTjwVIbrqmY8O
        GOOGLE_DRIVE_SMPL_FILE_ID = os.environ.get("GOOGLE_DRIVE_SMPL_ID")
        GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "1bxWXAKEOdBLiFIXQqnxoTjwVIbrqmY8O")
        print(f"[DEBUG] GOOGLE_DRIVE_SMPL_ID env var value: {GOOGLE_DRIVE_SMPL_FILE_ID}")
        print(f"[DEBUG] GOOGLE_DRIVE_FOLDER_ID env var value: {GOOGLE_DRIVE_FOLDER_ID}")
        
        # Try downloading from folder first
        if GOOGLE_DRIVE_FOLDER_ID:
            print(f"[DEBUG] Attempting to download SMPL from folder {GOOGLE_DRIVE_FOLDER_ID}...")
            smpl_basic_model_v11 = os.path.join(folder, "data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl")
            if _download_from_gdrive_folder("basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl", smpl_basic_model_v11,
                                           folder_id=GOOGLE_DRIVE_FOLDER_ID, file_id=None):
                # Validate size
                if os.path.exists(smpl_basic_model_v11):
                    file_size = os.path.getsize(smpl_basic_model_v11)
                    file_size_mb = file_size / 1024 / 1024
                    if 200 < file_size_mb < 300:
                        print(f"✅ SMPL downloaded from folder! ({file_size_mb:.1f}MB)")
                        return
                    else:
                        print(f"[WARNING] Downloaded file size unexpected: {file_size_mb:.1f}MB")
        
        if GOOGLE_DRIVE_SMPL_FILE_ID:
            print(f"  Attempting to download SMPL model from Google Drive...")
            try:
                import subprocess
                # Install gdown if not available
                try:
                    import gdown
                except ImportError:
                    print("Installing gdown...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "gdown"])
                    import gdown
                
                smpl_basic_model_v11 = os.path.abspath(os.path.join(folder, "data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl"))
                smpl_dir = os.path.dirname(smpl_basic_model_v11)
                os.makedirs(smpl_dir, exist_ok=True)
                gdrive_smpl_url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_SMPL_FILE_ID}"
                print(f"[DEBUG download_models] Current working directory: {os.getcwd()}")
                print(f"[DEBUG download_models] Downloading SMPL from: {gdrive_smpl_url}")
                print(f"[DEBUG download_models] Target directory: {smpl_dir}")
                print(f"[DEBUG download_models] Target file: {smpl_basic_model_v11}")
                print(f"[DEBUG download_models] Directory exists: {os.path.exists(smpl_dir)}")
                print(f"[DEBUG download_models] Directory is writable: {os.access(smpl_dir, os.W_OK) if os.path.exists(smpl_dir) else False}")
                
                # WORKAROUND: gdown seems to ignore output parameter sometimes.
                # Download to a temporary file in the target directory first, then move/rename
                temp_file = os.path.join(smpl_dir, f"temp_smpl_download_{os.getpid()}.pkl")
                print(f"[DEBUG download_models] Downloading to temp file: {temp_file}")
                
                try:
                    # Download to temp file
                    result = gdown.download(gdrive_smpl_url, output=temp_file, quiet=False)
                    print(f"[DEBUG download_models] gdown.download() returned: {result}")
                    
                    # Verify temp file was created
                    if not os.path.exists(temp_file):
                        print(f"[DEBUG download_models] ⚠️  Temp file not found! Checking current directory...")
                        # gdown might have downloaded to current directory with auto-generated name
                        cwd_files = [f for f in os.listdir(os.getcwd()) if f.endswith('.pkl') and os.path.getsize(os.path.join(os.getcwd(), f)) > 100_000_000]
                        if cwd_files:
                            print(f"[DEBUG download_models] Found .pkl files in current dir: {cwd_files}")
                            temp_file = os.path.abspath(os.path.join(os.getcwd(), cwd_files[0]))
                            print(f"[DEBUG download_models] Using: {temp_file}")
                    
                    # Also check checkpoint directory (where gdown seems to be putting it sometimes)
                    checkpoint_dir = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints")
                    if os.path.exists(checkpoint_dir) and not os.path.exists(temp_file):
                        checkpoint_files = [f for f in os.listdir(checkpoint_dir) if f.endswith('.pkl') and os.path.getsize(os.path.join(checkpoint_dir, f)) > 100_000_000 and f != "epoch=35-step=1000000.ckpt"]
                        if checkpoint_files:
                            print(f"[DEBUG download_models] Found .pkl in checkpoint dir: {checkpoint_files}")
                            temp_file = os.path.join(checkpoint_dir, checkpoint_files[0])
                            print(f"[DEBUG download_models] Using: {temp_file}")
                    
                    if os.path.exists(temp_file):
                        file_size = os.path.getsize(temp_file)
                        print(f"[DEBUG download_models] ✅ Downloaded file found: {temp_file} ({file_size / 1024 / 1024:.1f}MB)")
                        
                        # Move to final location
                        if os.path.exists(smpl_basic_model_v11):
                            print(f"[DEBUG download_models] Removing existing file at target location...")
                            os.remove(smpl_basic_model_v11)
                        
                        import shutil
                        shutil.move(temp_file, smpl_basic_model_v11)
                        print(f"[DEBUG download_models] ✅ Moved to final location: {smpl_basic_model_v11}")
                        
                        # Verify final location
                        if os.path.exists(smpl_basic_model_v11):
                            final_size = os.path.getsize(smpl_basic_model_v11)
                            final_size_mb = final_size / 1024 / 1024
                            print(f"[DEBUG download_models] ✅ File confirmed at final location ({final_size_mb:.1f}MB)")
                            
                            # Validate size - SMPL should be ~247MB, checkpoint is ~2500MB
                            if final_size_mb > 2000:
                                print(f"[ERROR download_models] ⚠️  CRITICAL: File is {final_size_mb:.1f}MB - this is the checkpoint, not SMPL!")
                                print(f"[ERROR download_models] ⚠️  GOOGLE_DRIVE_SMPL_ID is set to checkpoint ID!")
                                print(f"[ERROR download_models] ⚠️  Current SMPL ID: {GOOGLE_DRIVE_SMPL_FILE_ID}")
                                print(f"[ERROR download_models] ⚠️  Expected SMPL ID: 1A2qaP3xWZRuBOPaNx0-tovBBhtftxuSv")
                                os.remove(smpl_basic_model_v11)
                                raise ValueError(
                                    f"CRITICAL ERROR: GOOGLE_DRIVE_SMPL_ID is set to checkpoint file ID!\n"
                                    f"  Current ID: {GOOGLE_DRIVE_SMPL_FILE_ID}\n"
                                    f"  Expected SMPL ID: 1A2qaP3xWZRuBOPaNx0-tovBBhtftxuSv\n"
                                    f"  Checkpoint ID: 1ISfMrpiiwoSzLoQXsXsX5FUcOxZY5Bzu\n"
                                    f"  Fix: Set GOOGLE_DRIVE_SMPL_ID to SMPL file ID in RunPod environment variables"
                                )
                            elif 200 < final_size_mb < 300:
                                print(f"[DEBUG download_models] ✅ File size validated - SMPL file confirmed")
                            else:
                                print(f"[WARNING download_models] ⚠️  Unexpected file size: {final_size_mb:.1f}MB (expected ~247MB)")
                        else:
                            print(f"[DEBUG download_models] ❌ File not found after move!")
                            raise FileNotFoundError(f"File not found after moving to {smpl_basic_model_v11}")
                    else:
                        print(f"[DEBUG download_models] ❌ Download failed - temp file not found!")
                        raise FileNotFoundError(f"Download failed - file not found at {temp_file}")
                        
                except Exception as e:
                    print(f"[DEBUG download_models] Exception during download: {e}")
                    import traceback
                    traceback.print_exc()
                    # Clean up temp file if it exists
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except Exception:
                            pass
                    raise
                if os.path.exists(smpl_basic_model_v11):
                    print(f"✅ SMPL model downloaded from Google Drive to {smpl_basic_model_v11}!")
                    # Verify check_smpl_exists can find it
                    print(f"[DEBUG] Testing check_smpl_exists() can find the file...")
                    import os
                    test_paths = [
                        f'{CACHE_DIR_4DHUMANS}/data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl',
                        f'{CACHE_DIR_4DHUMANS}/data/basicModel_neutral_lbs_10_207_0_v1.1.0.pkl',
                        smpl_basic_model_v11,
                    ]
                    for tp in test_paths:
                        print(f"[DEBUG]   Checking: {tp} -> exists={os.path.exists(tp)}")
                    expected_checkpoint = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")
                    _ensure_config_files_exist(expected_checkpoint)
                    # Ensure smpl_mean_params.npz and SMPL_to_J19.pkl exist
                    data_dir = os.path.join(folder, "data")
                    _ensure_smpl_mean_params_exists(data_dir)
                    _ensure_smpl_joint_regressor_exists(data_dir)
                    return
            except Exception as e:
                print(f"⚠️  Google Drive SMPL download failed: {e}")
                print("  Will try hmr2_data.tar.gz as fallback...")
        else:
            print("  GOOGLE_DRIVE_SMPL_ID not set, will try hmr2_data.tar.gz...")
        # Continue to tar.gz download below if Google Drive failed
    elif not checkpoint_exists:
        # Checkpoint missing, will try Google Drive or tar.gz
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
                print(f"[DEBUG download_models] ⚠️  SMPL files missing! Attempting download...")
                # Try Google Drive SMPL download
                GOOGLE_DRIVE_SMPL_FILE_ID = os.environ.get("GOOGLE_DRIVE_SMPL_ID")
                print(f"[DEBUG download_models] GOOGLE_DRIVE_SMPL_ID={GOOGLE_DRIVE_SMPL_FILE_ID}")
                if GOOGLE_DRIVE_SMPL_FILE_ID:
                    print(f"[DEBUG download_models] Attempting to download SMPL from Google Drive...")
                    try:
                        import subprocess
                        try:
                            import gdown
                        except ImportError:
                            print("[DEBUG download_models] Installing gdown...")
                            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "gdown"])
                            import gdown
                        
                        smpl_basic_model_v11 = os.path.abspath(os.path.join(folder, "data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl"))
                        smpl_dir = os.path.dirname(smpl_basic_model_v11)
                        os.makedirs(smpl_dir, exist_ok=True)
                        gdrive_smpl_url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_SMPL_FILE_ID}"
                        print(f"[DEBUG download_models] Downloading SMPL from: {gdrive_smpl_url}")
                        print(f"[DEBUG download_models] Downloading SMPL to: {smpl_basic_model_v11}")
                        
                        # Use temp file approach
                        temp_file = os.path.join(smpl_dir, f"temp_smpl_download_{os.getpid()}.pkl")
                        print(f"[DEBUG download_models] Downloading to temp file: {temp_file}")
                        
                        result = gdown.download(gdrive_smpl_url, output=temp_file, quiet=False)
                        print(f"[DEBUG download_models] gdown.download() returned: {result}")
                        
                        # Check if file exists, search if needed
                        if not os.path.exists(temp_file):
                            checkpoint_dir = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints")
                            if os.path.exists(checkpoint_dir):
                                checkpoint_files = [f for f in os.listdir(checkpoint_dir) if f.endswith('.pkl') and os.path.getsize(os.path.join(checkpoint_dir, f)) > 100_000_000 and f != "epoch=35-step=1000000.ckpt"]
                                if checkpoint_files:
                                    temp_file = os.path.join(checkpoint_dir, checkpoint_files[0])
                                    print(f"[DEBUG download_models] Found in checkpoint dir: {temp_file}")
                        
                        # Move to final location
                        if os.path.exists(temp_file):
                            import shutil
                            if os.path.exists(smpl_basic_model_v11):
                                os.remove(smpl_basic_model_v11)
                            shutil.move(temp_file, smpl_basic_model_v11)
                            print(f"[DEBUG download_models] ✅ Moved to: {smpl_basic_model_v11}")
                            if os.path.exists(smpl_basic_model_v11):
                                # Validate file size
                                file_size = os.path.getsize(smpl_basic_model_v11)
                                file_size_mb = file_size / 1024 / 1024
                                print(f"[DEBUG download_models] File confirmed ({file_size_mb:.1f}MB)")
                                
                                # Validate size - SMPL should be ~247MB, checkpoint is ~2500MB
                                if file_size_mb > 2000:
                                    print(f"[ERROR download_models] ⚠️  CRITICAL: File is {file_size_mb:.1f}MB - this is the checkpoint, not SMPL!")
                                    print(f"[ERROR download_models] ⚠️  GOOGLE_DRIVE_SMPL_ID is set to checkpoint ID!")
                                    print(f"[ERROR download_models] ⚠️  Current SMPL ID: {GOOGLE_DRIVE_SMPL_FILE_ID}")
                                    os.remove(smpl_basic_model_v11)
                                    raise ValueError(
                                        f"CRITICAL ERROR: GOOGLE_DRIVE_SMPL_ID is set to checkpoint file ID!\n"
                                        f"  Current ID: {GOOGLE_DRIVE_SMPL_FILE_ID}\n"
                                        f"  Expected SMPL ID: 1A2qaP3xWZRuBOPaNx0-tovBBhtftxuSv\n"
                                        f"  Checkpoint ID: 1ISfMrpiiwoSzLoQXsXsX5FUcOxZY5Bzu"
                                    )
                                elif 200 < file_size_mb < 300:
                                    print(f"[DEBUG download_models] ✅ SMPL file size validated")
                                else:
                                    print(f"[WARNING download_models] ⚠️  Unexpected size: {file_size_mb:.1f}MB (expected ~247MB)")
                        else:
                            print(f"[DEBUG download_models] ❌ Download failed - file not found")
                    except Exception as e:
                        print(f"[DEBUG download_models] ⚠️  SMPL download failed: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"[DEBUG download_models] GOOGLE_DRIVE_SMPL_ID not set, cannot download SMPL")
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
    
    # Try downloading checkpoint from Google Drive if not found
    # Can use either individual file ID or folder ID
    # Default folder ID: https://drive.google.com/drive/folders/1bxWXAKEOdBLiFIXQqnxoTjwVIbrqmY8O
    GOOGLE_DRIVE_CHECKPOINT_FILE_ID = os.environ.get("GOOGLE_DRIVE_CHECKPOINT_ID")  # Can set via env var
    GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "1bxWXAKEOdBLiFIXQqnxoTjwVIbrqmY8O")  # For downloading from folder
    
    checkpoint_dest = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt")
    
    # Try Google Drive if checkpoint doesn't exist - try folder first, then individual file ID
    if not os.path.exists(checkpoint_dest) and (GOOGLE_DRIVE_FOLDER_ID or GOOGLE_DRIVE_CHECKPOINT_FILE_ID):
        # Try downloading from folder first
        if GOOGLE_DRIVE_FOLDER_ID:
            print(f"Checkpoint not found. Attempting to download from Google Drive folder...")
            if _download_from_gdrive_folder("epoch=35-step=1000000.ckpt", checkpoint_dest,
                                           folder_id=GOOGLE_DRIVE_FOLDER_ID, file_id=None):
                # Validate size after download
                if os.path.exists(checkpoint_dest):
                    file_size = os.path.getsize(checkpoint_dest)
                    file_size_mb = file_size / 1024 / 1024
                    if file_size_mb > 2000:
                        print(f"✅ Checkpoint downloaded from Google Drive folder! ({file_size_mb:.1f}MB)")
                        # Ensure config files exist after downloading
                        _ensure_config_files_exist(checkpoint_dest)
                        from hmr2.configs import CACHE_DIR_4DHUMANS
                        data_dir = os.path.join(CACHE_DIR_4DHUMANS, "data")
                        _ensure_smpl_mean_params_exists(data_dir)
                        _ensure_smpl_joint_regressor_exists(data_dir)
                        return
                    else:
                        print(f"[WARNING checkpoint download] Downloaded file size unexpected: {file_size_mb:.1f}MB (expected ~2500MB)")
        
        # Try individual file ID if folder download didn't work
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
                checkpoint_dest = os.path.abspath(checkpoint_dest)
                gdrive_url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_CHECKPOINT_FILE_ID}"
                print(f"Downloading checkpoint from: {gdrive_url}")
                print(f"Downloading checkpoint to: {checkpoint_dest}")
                print("(This may take 10-30 minutes for 2.5GB file...)")
                
                # Use output parameter explicitly to avoid path confusion
                print(f"[DEBUG checkpoint download] Starting download...")
                gdown.download(gdrive_url, output=checkpoint_dest, quiet=False)
                
                if os.path.exists(checkpoint_dest):
                    file_size = os.path.getsize(checkpoint_dest)
                    file_size_mb = file_size / 1024 / 1024
                    print(f"[DEBUG checkpoint download] File exists, size: {file_size_mb:.1f}MB")
                    
                    # VALIDATION: Checkpoint should be ~2.5GB (2500MB), SMPL is ~247MB
                    # If file is ~247MB, it's actually the SMPL file (wrong ID configured!)
                    if file_size_mb < 500:
                        print(f"[ERROR checkpoint download] ⚠️  CRITICAL: Downloaded file is only {file_size_mb:.1f}MB!")
                        print(f"[ERROR checkpoint download] ⚠️  Expected checkpoint size: ~2500MB (2.5GB)")
                        print(f"[ERROR checkpoint download] ⚠️  This looks like the SMPL file, not the checkpoint!")
                        print(f"[ERROR checkpoint download] ⚠️  Check GOOGLE_DRIVE_CHECKPOINT_ID environment variable!")
                        print(f"[ERROR checkpoint download] ⚠️  Current ID: {GOOGLE_DRIVE_CHECKPOINT_FILE_ID}")
                        print(f"[ERROR checkpoint download] ⚠️  Expected checkpoint ID: 1ISfMrpiiwoSzLoQXsXsX5FUcOxZY5Bzu")
                        print(f"[ERROR checkpoint download] ⚠️  SMPL ID: 1A2qaP3xWZRuBOPaNx0-tovBBhtftxuSv")
                        print(f"[ERROR checkpoint download] ⚠️  REMOVING incorrect file and raising error...")
                        os.remove(checkpoint_dest)
                        raise ValueError(
                            f"CRITICAL ERROR: GOOGLE_DRIVE_CHECKPOINT_ID is set to SMPL file ID!\n"
                            f"  Current ID: {GOOGLE_DRIVE_CHECKPOINT_FILE_ID}\n"
                            f"  Expected checkpoint ID: 1ISfMrpiiwoSzLoQXsXsX5FUcOxZY5Bzu\n"
                            f"  SMPL ID: 1A2qaP3xWZRuBOPaNx0-tovBBhtftxuSv\n"
                            f"  Fix: Set GOOGLE_DRIVE_CHECKPOINT_ID to checkpoint ID in RunPod environment variables"
                        )
                    
                    if file_size_mb < 2000:
                        print(f"[WARNING checkpoint download] ⚠️  Checkpoint file seems small ({file_size_mb:.1f}MB), expected ~2500MB")
                    else:
                        print(f"✅ Checkpoint downloaded from Google Drive! ({file_size_mb:.1f}MB)")
                    
                    # After downloading checkpoint, create default config files if they don't exist
                    _ensure_config_files_exist(checkpoint_dest)
                    
                    # Ensure smpl_mean_params.npz and SMPL_to_J19.pkl exist
                    from hmr2.configs import CACHE_DIR_4DHUMANS
                    data_dir = os.path.join(CACHE_DIR_4DHUMANS, "data")
                    _ensure_smpl_mean_params_exists(data_dir)
                    _ensure_smpl_joint_regressor_exists(data_dir)
                    
                    # Check if SMPL files exist - if not, try Google Drive first, then tar.gz
                    smpl_file = os.path.join(folder, "data/smpl/SMPL_NEUTRAL.pkl")
                    # Check for both v1.0.0 and v1.1.0 versions
                    smpl_basic_model_v1 = os.path.join(folder, "data/basicModel_neutral_lbs_10_207_0_v1.0.0.pkl")
                    smpl_basic_model_v11 = os.path.join(folder, "data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl")
                    
                    if not os.path.exists(smpl_file) and not os.path.exists(smpl_basic_model_v1) and not os.path.exists(smpl_basic_model_v11):
                        print("⚠️  SMPL files not found. Trying Google Drive first...")
                        
                        # Try downloading SMPL model from Google Drive if provided
                        # Default folder ID: https://drive.google.com/drive/folders/1bxWXAKEOdBLiFIXQqnxoTjwVIbrqmY8O
                        GOOGLE_DRIVE_SMPL_FILE_ID = os.environ.get("GOOGLE_DRIVE_SMPL_ID")
                        GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "1bxWXAKEOdBLiFIXQqnxoTjwVIbrqmY8O")
                        
                        # Try downloading from folder first
                        if GOOGLE_DRIVE_FOLDER_ID:
                            print(f"[DEBUG checkpoint->SMPL download] Attempting to download SMPL from folder {GOOGLE_DRIVE_FOLDER_ID}...")
                            if _download_from_gdrive_folder("basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl", smpl_basic_model_v11,
                                                           folder_id=GOOGLE_DRIVE_FOLDER_ID, file_id=None):
                                # Validate size
                                if os.path.exists(smpl_basic_model_v11):
                                    file_size = os.path.getsize(smpl_basic_model_v11)
                                    file_size_mb = file_size / 1024 / 1024
                                    if 200 < file_size_mb < 300:
                                        print(f"[DEBUG checkpoint->SMPL download] ✅ SMPL downloaded from folder! ({file_size_mb:.1f}MB)")
                                    else:
                                        print(f"[WARNING checkpoint->SMPL download] Downloaded file size unexpected: {file_size_mb:.1f}MB")
                        
                        if GOOGLE_DRIVE_SMPL_FILE_ID:
                            print(f"  Attempting to download SMPL model from Google Drive...")
                            try:
                                # Download to v1.1.0 path (user has v1.1.0)
                                smpl_basic_model_v11 = os.path.abspath(os.path.join(folder, "data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl"))
                                smpl_dir = os.path.dirname(smpl_basic_model_v11)
                                os.makedirs(smpl_dir, exist_ok=True)
                                gdrive_smpl_url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_SMPL_FILE_ID}"
                                print(f"[DEBUG checkpoint->SMPL download] Downloading SMPL from: {gdrive_smpl_url}")
                                print(f"[DEBUG checkpoint->SMPL download] Downloading SMPL to: {smpl_basic_model_v11}")
                                
                                # WORKAROUND: Download to temp file first, then move
                                temp_file = os.path.join(smpl_dir, f"temp_smpl_download_{os.getpid()}.pkl")
                                print(f"[DEBUG checkpoint->SMPL download] Downloading to temp file: {temp_file}")
                                
                                gdown.download(gdrive_smpl_url, output=temp_file, quiet=False)
                                
                                # Check if file exists, and if not, search for it
                                if not os.path.exists(temp_file):
                                    print(f"[DEBUG checkpoint->SMPL download] Temp file not found, searching...")
                                    # Check checkpoint directory
                                    checkpoint_dir = os.path.join(folder, "logs/train/multiruns/hmr2/0/checkpoints")
                                    if os.path.exists(checkpoint_dir):
                                        checkpoint_files = [f for f in os.listdir(checkpoint_dir) if f.endswith('.pkl') and os.path.getsize(os.path.join(checkpoint_dir, f)) > 100_000_000 and f != "epoch=35-step=1000000.ckpt"]
                                        if checkpoint_files:
                                            temp_file = os.path.join(checkpoint_dir, checkpoint_files[0])
                                            print(f"[DEBUG checkpoint->SMPL download] Found in checkpoint dir: {temp_file}")
                                
                                # Move to final location
                                if os.path.exists(temp_file):
                                    import shutil
                                    if os.path.exists(smpl_basic_model_v11):
                                        os.remove(smpl_basic_model_v11)
                                    shutil.move(temp_file, smpl_basic_model_v11)
                                    print(f"[DEBUG checkpoint->SMPL download] ✅ Moved to: {smpl_basic_model_v11}")
                                if os.path.exists(smpl_basic_model_v11):
                                    print(f"✅ SMPL model downloaded from Google Drive!")
                                    # check_smpl_exists() will convert it to SMPL_NEUTRAL.pkl
                                    return
                            except Exception as e:
                                print(f"⚠️  Google Drive SMPL download failed: {e}")
                                print("  Will try hmr2_data.tar.gz as fallback...")
                        
                        # Continue to tar.gz download below
                    else:
                        print("✅ SMPL files found, skipping download")
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
        # Check cache directory first (where we download from Google Drive)
        f'{cache_dir}/data/basicModel_neutral_lbs_10_207_0_v1.0.0.pkl',
        f'{cache_dir}/data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl',
        f'{cache_dir}/data/basicModel_neutral_lbs_10_207_0_v1.1.0.pkl',
        # Also check relative paths (for local development)
        f'data/basicModel_neutral_lbs_10_207_0_v1.0.0.pkl',
        f'data/basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl',  # Also check v1.1.0 (lowercase)
        f'data/basicModel_neutral_lbs_10_207_0_v1.1.0.pkl',  # Also check v1.1.0 (mixed case)
    ]
    
    # Debug: print what we're checking
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
            
            # Also check the checkpoint directory (where file might have been incorrectly downloaded)
            checkpoint_dir = os.path.join(cache_dir, "logs/train/multiruns/hmr2/0/checkpoints")
            if os.path.exists(checkpoint_dir):
                print(f"[DEBUG check_smpl_exists] Checking checkpoint directory for .pkl files:")
                result = subprocess.run(["find", checkpoint_dir, "-name", "*.pkl", "-type", "f"], capture_output=True, text=True)
                if result.stdout:
                    print(f"[DEBUG check_smpl_exists] Found .pkl files in checkpoint dir:")
                    for line in result.stdout.strip().split('\n'):
                        file_path = line.strip()
                        print(f"[DEBUG check_smpl_exists]   {file_path}")
                        # Check if this looks like a SMPL file (not a checkpoint)
                        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                        if ("basicmodel" in file_path.lower() or "basicModel" in file_path) and file_size < 500_000_000:  # Less than 500MB (checkpoints are 2.5GB)
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
                                # Retry check
                                if os.path.exists(correct_path):
                                    candidates_exist[2] = True  # Update the v1.1.0 lowercase candidate
                                    print(f"[DEBUG check_smpl_exists] ✅ File now found at correct location!")
                                    break
                            except Exception as e:
                                import traceback
                                print(f"[DEBUG check_smpl_exists] ⚠️  Failed to move file: {e}")
                                traceback.print_exc()
        
        if not any(candidates_exist):
            raise FileNotFoundError(f"SMPL model not found. Please download it from https://smplify.is.tue.mpg.de/ and place it at data/basicModel_neutral_lbs_10_207_0_v1.0.0.pkl")

    # Code expects SMPL model at CACHE_DIR_4DHUMANS/data/smpl/SMPL_NEUTRAL.pkl. Convert if needed
    if not candidates_exist[0]:
        # Find which basicModel file exists (skip first candidate which is SMPL_NEUTRAL)
        for i in range(1, len(candidates)):
            if candidates_exist[i]:
                convert_pkl(candidates[i], candidates[0])
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
