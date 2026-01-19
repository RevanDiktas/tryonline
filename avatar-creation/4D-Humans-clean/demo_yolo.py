"""
Demo script using YOLOv8 instead of detectron2
Works on macOS without compilation issues
"""
import os
os.environ['PYOPENGL_PLATFORM'] = ''

# ============================================================
# FIX FOR PYTHON 3.11+ (inspect.getargspec removed)
# chumpy uses deprecated getargspec, we add it back as alias
# ============================================================
import inspect
if not hasattr(inspect, 'getargspec'):
    inspect.getargspec = inspect.getfullargspec
# ============================================================

# ============================================================
# FIX FOR NUMPY 2.0+ (deprecated types removed)
# chumpy imports np.bool, np.int, etc. which were removed
# ============================================================
import numpy as np
if not hasattr(np, 'bool'):
    np.bool = np.bool_
if not hasattr(np, 'int'):
    np.int = np.int_
if not hasattr(np, 'float'):
    np.float = np.float64
if not hasattr(np, 'complex'):
    np.complex = np.complex128
if not hasattr(np, 'object'):
    np.object = np.object_
if not hasattr(np, 'str'):
    np.str = np.str_
if not hasattr(np, 'unicode'):
    np.unicode = np.str_
# ============================================================

from pathlib import Path
import torch
import argparse
import cv2
import numpy as np
import trimesh
import time

# ============================================================
# FIX FOR PYTORCH 2.6+ weights_only BREAKING CHANGE
# PyTorch 2.6 changed default weights_only=True which breaks
# loading checkpoints with omegaconf/custom objects.
# We monkeypatch torch.load to force weights_only=False.
# ============================================================
_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load
# ============================================================

from hmr2.configs import CACHE_DIR_4DHUMANS, get_config
from hmr2.models import HMR2, download_models, DEFAULT_CHECKPOINT
from hmr2.utils import recursive_to
from hmr2.datasets.vitdet_dataset import ViTDetDataset

# Import our custom YOLO detector
from hmr2.utils.utils_yolo import YOLOPredictor

def load_hmr2_no_renderer(checkpoint_path):
    """Load HMR2 model without initializing renderer"""
    from hmr2.models import check_smpl_exists
    
    model_cfg = str(Path(checkpoint_path).parent.parent / 'model_config.yaml')
    model_cfg = get_config(model_cfg, update_cachedir=True)
    
    # CRITICAL: Ensure JOINT_REP='6d' is set to match checkpoint (144 dims: 24 joints × 6)
    # The checkpoint was trained with 6d representation, so we MUST match it
    from yacs.config import CfgNode as CN
    model_cfg.defrost()
    if not hasattr(model_cfg.MODEL, 'SMPL_HEAD'):
        model_cfg.MODEL.SMPL_HEAD = CN(new_allowed=True)
    if not hasattr(model_cfg.MODEL.SMPL_HEAD, 'JOINT_REP') or model_cfg.MODEL.SMPL_HEAD.JOINT_REP != '6d':
        print(f"[4D-Humans] ⚠️  JOINT_REP not set or incorrect in config, fixing to '6d' (required for checkpoint)")
        model_cfg.MODEL.SMPL_HEAD.JOINT_REP = '6d'
    
    if (model_cfg.MODEL.BACKBONE.TYPE == 'vit') and ('BBOX_SHAPE' not in model_cfg.MODEL):
        assert model_cfg.MODEL.IMAGE_SIZE == 256
        model_cfg.MODEL.BBOX_SHAPE = [192,256]
    model_cfg.freeze()
    
    check_smpl_exists()
    model = HMR2.load_from_checkpoint(checkpoint_path, strict=False, cfg=model_cfg, init_renderer=False)
    return model, model_cfg

def main():
    start_time = time.time()
    
    parser = argparse.ArgumentParser(description='HMR2 demo with YOLO detection (macOS compatible)')
    parser.add_argument('--checkpoint', type=str, default=DEFAULT_CHECKPOINT)
    parser.add_argument('--img_folder', type=str, default='example_data/images')
    parser.add_argument('--out_folder', type=str, default='demo_out')
    parser.add_argument('--batch_size', type=int, default=1)
    parser.add_argument('--file_type', nargs='+', default=['*.jpg', '*.png'])
    
    args = parser.parse_args()
    
    print("="*60)
    print("4D-Humans Demo with YOLOv8 Detection")
    print("="*60)
    
    print("\n📦 Loading HMR2 model...")
    download_models(CACHE_DIR_4DHUMANS)
    model, model_cfg = load_hmr2_no_renderer(args.checkpoint)
    
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    model = model.to(device)
    model.eval()
    print(f"✓ HMR2 model loaded on {device}")
    
    # Load YOLO detector
    print("\n📦 Loading YOLO detector...")
    detector = YOLOPredictor(confidence=0.5)
    
    os.makedirs(args.out_folder, exist_ok=True)
    
    # Get all images (skip macOS hidden files starting with ._)
    img_paths = []
    for file_type in args.file_type:
        img_paths.extend([p for p in Path(args.img_folder).glob(file_type) if not p.name.startswith('._')])
    img_paths = sorted(img_paths)
    
    print(f"\n🖼️  Found {len(img_paths)} images in {args.img_folder}")
    print("="*60)
    
    # Process each image
    total_people = 0
    for img_idx, img_path in enumerate(img_paths):
        print(f"\n[{img_idx+1}/{len(img_paths)}] Processing: {img_path.name}")
        
        img_cv2 = cv2.imread(str(img_path))
        
        # Detect humans with YOLO
        det_out = detector(img_cv2)
        det_instances = det_out['instances']
        valid_idx = (det_instances.pred_classes == 0) & (det_instances.scores > 0.5)
        boxes = det_instances.pred_boxes.tensor[valid_idx].cpu().numpy()
        
        if len(boxes) == 0:
            print(f"  ⚠️  No humans detected")
            continue
        
        print(f"  ✓ Detected {len(boxes)} person(s)")
        total_people += len(boxes)
        
        # Create dataset and run HMR2
        dataset = ViTDetDataset(model_cfg, img_cv2, boxes)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)
        
        for person_idx, batch in enumerate(dataloader):
            batch = recursive_to(batch, device)
            
            with torch.no_grad():
                out = model(batch)
            
            pred_vertices = out['pred_vertices']
            pred_cam = out['pred_cam']
            
            # Save meshes
            batch_size = pred_vertices.shape[0]
            for i in range(batch_size):
                person_id = person_idx * args.batch_size + i
                
                vertices = pred_vertices[i].cpu().numpy()
                faces = model.smpl.faces
                
                mesh = trimesh.Trimesh(vertices, faces, process=False)
                mesh_filename = f"{img_path.stem}_person{person_id}.obj"
                mesh_path = Path(args.out_folder) / mesh_filename
                mesh.export(str(mesh_path))
                
                print(f"  ✓ Saved mesh: {mesh_filename}")
                
                # Also save SMPL parameters
                smpl_params = {
                    'pred_cam': pred_cam[i].cpu().numpy(),
                    'pred_vertices': vertices,
                    'betas': out['pred_smpl_params']['betas'][i].cpu().numpy() if 'betas' in out['pred_smpl_params'] else None,
                    'body_pose': out['pred_smpl_params']['body_pose'][i].cpu().numpy() if 'body_pose' in out['pred_smpl_params'] else None,
                    'global_orient': out['pred_smpl_params']['global_orient'][i].cpu().numpy() if 'global_orient' in out['pred_smpl_params'] else None,
                }
                
                params_filename = f"{img_path.stem}_person{person_id}_params.npz"
                params_path = Path(args.out_folder) / params_filename
                np.savez(str(params_path), **smpl_params)
                
                print(f"  ✓ Saved params: {params_filename}")
    
    end_time = time.time()
    print(f"\n{'='*60}")
    print(f"✓ Processing complete!")
    print(f"  Total people detected: {total_people}")
    print(f"  Total time: {end_time-start_time:.2f} seconds")
    print(f"  Output folder: {args.out_folder}")
    print(f"  Files: .obj meshes and .npz parameters")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()

