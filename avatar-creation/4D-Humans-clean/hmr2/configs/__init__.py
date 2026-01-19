import os
from typing import Dict
from pathlib import Path
from yacs.config import CfgNode as CN

# Check if RunPod Network Volume is mounted
# RunPod mounts Network Volumes at /runpod-volume (fixed path)
RUNPOD_VOLUME_PATH = Path("/runpod-volume")
VOLUME_CACHE_DIR = RUNPOD_VOLUME_PATH / "4DHumans"

# Default cache directory (what the code expects - where build-time models are saved)
CACHE_DIR = os.path.join(os.environ.get("HOME"), ".cache")
DEFAULT_CACHE_DIR_4DHUMANS = os.path.join(CACHE_DIR, "4DHumans")

# PRIORITY: Check if models exist in DEFAULT location first (from build-time download)
# This is where models are baked into the Docker image
BUILD_CACHE_DIR = Path(DEFAULT_CACHE_DIR_4DHUMANS)
BUILD_CHECKPOINT = BUILD_CACHE_DIR / "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt"

# Lazy cache directory determination - defer expensive filesystem checks until first access
# This prevents slow container startup when this module is imported
_CACHE_DIR_4DHUMANS = None

def _get_cache_dir_4dhumans():
    """
    Lazy function to determine cache directory.
    Only performs expensive filesystem checks when first called.
    """
    global _CACHE_DIR_4DHUMANS
    if _CACHE_DIR_4DHUMANS is not None:
        return _CACHE_DIR_4DHUMANS
    
    # Check if volume has models (checkpoint must exist, not just directory)
    VOLUME_CHECKPOINT = VOLUME_CACHE_DIR / "logs/train/multiruns/hmr2/0/checkpoints/epoch=35-step=1000000.ckpt"
    try:
        volume_has_models = VOLUME_CHECKPOINT.exists() and VOLUME_CHECKPOINT.stat().st_size > 2 * 1024**3  # > 2GB
    except Exception:
        volume_has_models = False
    
    # PRIORITY 1: Build-time models (baked into image)
    if BUILD_CHECKPOINT.exists():
        try:
            file_size_gb = BUILD_CHECKPOINT.stat().st_size / (1024**3)
            if file_size_gb > 2.0:
                _CACHE_DIR_4DHUMANS = str(BUILD_CACHE_DIR)
                print(f"[Config] ✓ Using build-time models from image cache: {_CACHE_DIR_4DHUMANS}")
                print(f"[Config]   Checkpoint found: {file_size_gb:.2f} GB")
            else:
                # Checkpoint exists but is too small (corrupted or incomplete)
                print(f"[Config] ⚠️  Build checkpoint exists but is too small ({file_size_gb:.2f} GB), checking volume...")
                if volume_has_models:
                    _CACHE_DIR_4DHUMANS = str(VOLUME_CACHE_DIR)
                    print(f"[Config] Using RunPod Network Volume cache: {_CACHE_DIR_4DHUMANS}")
                else:
                    _CACHE_DIR_4DHUMANS = DEFAULT_CACHE_DIR_4DHUMANS
                    print(f"[Config] Using default cache (will download models): {_CACHE_DIR_4DHUMANS}")
        except Exception as e:
            print(f"[Config] ⚠️  Error checking build checkpoint: {e}, checking volume...")
            if volume_has_models:
                _CACHE_DIR_4DHUMANS = str(VOLUME_CACHE_DIR)
                print(f"[Config] Using RunPod Network Volume cache: {_CACHE_DIR_4DHUMANS}")
            else:
                _CACHE_DIR_4DHUMANS = DEFAULT_CACHE_DIR_4DHUMANS
                print(f"[Config] Using default cache (will download models): {_CACHE_DIR_4DHUMANS}")
    # PRIORITY 2: Volume has models (runtime caching)
    elif RUNPOD_VOLUME_PATH.exists() and volume_has_models:
        _CACHE_DIR_4DHUMANS = str(VOLUME_CACHE_DIR)
        print(f"[Config] Using RunPod Network Volume cache: {_CACHE_DIR_4DHUMANS}")
        try:
            print(f"[Config]   Checkpoint found in volume: {VOLUME_CHECKPOINT.stat().st_size / (1024**3):.2f} GB")
        except Exception:
            pass
    else:
        # Use default location (or symlink created by handler)
        _CACHE_DIR_4DHUMANS = DEFAULT_CACHE_DIR_4DHUMANS
        if RUNPOD_VOLUME_PATH.exists():
            print(f"[Config] Network Volume exists but no models found, using default: {_CACHE_DIR_4DHUMANS}")
            print(f"[Config] Handler will create symlink to volume if needed")
        else:
            print(f"[Config] Using default cache directory: {_CACHE_DIR_4DHUMANS}")
    
    return _CACHE_DIR_4DHUMANS

# Public API: CACHE_DIR_4DHUMANS - use lazy property-like access
# For backward compatibility with Path(), os.path.join(), etc.
class _LazyCacheDir:
    """Lazy property that defers cache directory determination until first access."""
    def __str__(self):
        return _get_cache_dir_4dhumans()
    
    def __repr__(self):
        return repr(_get_cache_dir_4dhumans())
    
    def __eq__(self, other):
        return str(self) == str(other) if isinstance(other, str) else False
    
    def __fspath__(self):
        """Implement os.PathLike protocol for pathlib.Path() compatibility."""
        return _get_cache_dir_4dhumans()
    
    def __hash__(self):
        """Make it hashable for use in dicts/sets."""
        return hash(_get_cache_dir_4dhumans())

# Initialize immediately but make it fast (skip expensive checks for container startup)
# Set a default immediately, detailed checks happen lazily in _get_cache_dir_4dhumans()
try:
    # Quick check: just see if build checkpoint exists (fast - no size check yet)
    if BUILD_CHECKPOINT.exists():
        _CACHE_DIR_4DHUMANS = str(BUILD_CACHE_DIR)
    elif RUNPOD_VOLUME_PATH.exists():
        # Volume exists, use it as default (detailed size check happens lazily)
        _CACHE_DIR_4DHUMANS = str(VOLUME_CACHE_DIR)
    else:
        _CACHE_DIR_4DHUMANS = DEFAULT_CACHE_DIR_4DHUMANS
except Exception:
    # On any error, use default
    _CACHE_DIR_4DHUMANS = DEFAULT_CACHE_DIR_4DHUMANS

# Create lazy cache dir object - will resolve on first use
CACHE_DIR_4DHUMANS = _LazyCacheDir()

def to_lower(x: Dict) -> Dict:
    """
    Convert all dictionary keys to lowercase
    Args:
      x (dict): Input dictionary
    Returns:
      dict: Output dictionary with all keys converted to lowercase
    """
    return {k.lower(): v for k, v in x.items()}

_C = CN(new_allowed=True)

_C.GENERAL = CN(new_allowed=True)
_C.GENERAL.RESUME = True
_C.GENERAL.TIME_TO_RUN = 3300
_C.GENERAL.VAL_STEPS = 100
_C.GENERAL.LOG_STEPS = 100
_C.GENERAL.CHECKPOINT_STEPS = 20000
_C.GENERAL.CHECKPOINT_DIR = "checkpoints"
_C.GENERAL.SUMMARY_DIR = "tensorboard"
_C.GENERAL.NUM_GPUS = 1
_C.GENERAL.NUM_WORKERS = 4
_C.GENERAL.MIXED_PRECISION = True
_C.GENERAL.ALLOW_CUDA = True
_C.GENERAL.PIN_MEMORY = False
_C.GENERAL.DISTRIBUTED = False
_C.GENERAL.LOCAL_RANK = 0
_C.GENERAL.USE_SYNCBN = False
_C.GENERAL.WORLD_SIZE = 1

_C.TRAIN = CN(new_allowed=True)
_C.TRAIN.NUM_EPOCHS = 100
_C.TRAIN.BATCH_SIZE = 32
_C.TRAIN.SHUFFLE = True
_C.TRAIN.WARMUP = False
_C.TRAIN.NORMALIZE_PER_IMAGE = False
_C.TRAIN.CLIP_GRAD = False
_C.TRAIN.CLIP_GRAD_VALUE = 1.0
_C.LOSS_WEIGHTS = CN(new_allowed=True)

_C.DATASETS = CN(new_allowed=True)

_C.MODEL = CN(new_allowed=True)
_C.MODEL.IMAGE_SIZE = 224

_C.EXTRA = CN(new_allowed=True)
_C.EXTRA.FOCAL_LENGTH = 5000

_C.DATASETS.CONFIG = CN(new_allowed=True)
_C.DATASETS.CONFIG.SCALE_FACTOR = 0.3
_C.DATASETS.CONFIG.ROT_FACTOR = 30
_C.DATASETS.CONFIG.TRANS_FACTOR = 0.02
_C.DATASETS.CONFIG.COLOR_SCALE = 0.2
_C.DATASETS.CONFIG.ROT_AUG_RATE = 0.6
_C.DATASETS.CONFIG.TRANS_AUG_RATE = 0.5
_C.DATASETS.CONFIG.DO_FLIP = True
_C.DATASETS.CONFIG.FLIP_AUG_RATE = 0.5
_C.DATASETS.CONFIG.EXTREME_CROP_AUG_RATE = 0.10

def default_config() -> CN:
    """
    Get a yacs CfgNode object with the default config values.
    """
    # Return a clone so that the defaults will not be altered
    # This is for the "local variable" use pattern
    return _C.clone()

def dataset_config(name='datasets_tar.yaml') -> CN:
    """
    Get dataset config file
    Returns:
      CfgNode: Dataset config as a yacs CfgNode object.
    """
    cfg = CN(new_allowed=True)
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), name)
    cfg.merge_from_file(config_file)
    cfg.freeze()
    return cfg

def dataset_eval_config() -> CN:
    return dataset_config('datasets_eval.yaml')

def get_config(config_file: str, merge: bool = True, update_cachedir: bool = False) -> CN:
    """
    Read a config file and optionally merge it with the default config file.
    Args:
      config_file (str): Path to config file.
      merge (bool): Whether to merge with the default config or not.
    Returns:
      CfgNode: Config as a yacs CfgNode object.
    """
    if merge:
      cfg = default_config()
    else:
      cfg = CN(new_allowed=True)
    cfg.merge_from_file(config_file)

    if update_cachedir:
      def update_path(path: str) -> str:
        if os.path.isabs(path):
          return path
        # Resolve lazy cache dir if needed
        cache_dir = str(_get_cache_dir_4dhumans()) if _CACHE_DIR_4DHUMANS is None else _CACHE_DIR_4DHUMANS
        return os.path.join(cache_dir, path)

      cfg.SMPL.MODEL_PATH = update_path(cfg.SMPL.MODEL_PATH)
      # Only update JOINT_REGRESSOR_EXTRA if it exists in config (it's optional)
      if hasattr(cfg.SMPL, 'JOINT_REGRESSOR_EXTRA') and cfg.SMPL.JOINT_REGRESSOR_EXTRA:
        cfg.SMPL.JOINT_REGRESSOR_EXTRA = update_path(cfg.SMPL.JOINT_REGRESSOR_EXTRA)
      cfg.SMPL.MEAN_PARAMS = update_path(cfg.SMPL.MEAN_PARAMS)

    cfg.freeze()
    return cfg
