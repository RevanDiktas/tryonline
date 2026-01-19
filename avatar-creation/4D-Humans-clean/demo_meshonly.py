"""
Demo script for 4D-Humans that generates meshes without rendering
This bypasses the OpenGL/EGL issues on macOS by skipping renderer initialization
"""
# CRITICAL: Set this BEFORE any imports to disable OpenGL/EGL loading
import os
os.environ['PYOPENGL_PLATFORM'] = ''

from pathlib import Path
import torch
import argparse
import cv2
import numpy as np
import trimesh

from hmr2.configs import CACHE_DIR_4DHUMANS, get_config
from hmr2.models import HMR2, download_models, DEFAULT_CHECKPOINT
from hmr2.utils import recursive_to
from hmr2.datasets.vitdet_dataset import ViTDetDataset, DEFAULT_MEAN, DEFAULT_STD

def load_hmr2_no_renderer(checkpoint_path):
    """Load HMR2 model without initializing renderer"""
    from hmr2.models import check_smpl_exists
    
    model_cfg = str(Path(checkpoint_path).parent.parent / 'model_config.yaml')
    model_cfg = get_config(model_cfg, update_cachedir=True)
    
    # CRITICAL: Ensure JOINT_REP='6d' is set to match checkpoint (144 dims: 24 joints × 6)
    from yacs.config import CfgNode as CN
    model_cfg.defrost()
    if not hasattr(model_cfg.MODEL, 'SMPL_HEAD'):
        model_cfg.MODEL.SMPL_HEAD = CN(new_allowed=True)
    if not hasattr(model_cfg.MODEL.SMPL_HEAD, 'JOINT_REP') or model_cfg.MODEL.SMPL_HEAD.JOINT_REP != '6d':
        print(f"[4D-Humans] ⚠️  JOINT_REP not set or incorrect in config, fixing to '6d' (required for checkpoint)")
        model_cfg.MODEL.SMPL_HEAD.JOINT_REP = '6d'
    
    # Override some config values, to crop bbox correctly
    if (model_cfg.MODEL.BACKBONE.TYPE == 'vit') and ('BBOX_SHAPE' not in model_cfg.MODEL):
        assert model_cfg.MODEL.IMAGE_SIZE == 256, f"MODEL.IMAGE_SIZE ({model_cfg.MODEL.IMAGE_SIZE}) should be 256 for ViT backbone"
        model_cfg.MODEL.BBOX_SHAPE = [192,256]
    model_cfg.freeze()
    
    # Ensure SMPL model exists
    check_smpl_exists()
    
    # Load model WITHOUT renderer initialization
    model = HMR2.load_from_checkpoint(checkpoint_path, strict=False, cfg=model_cfg, init_renderer=False)
    return model, model_cfg

def main():
    import time
    start = time.time()
    parser = argparse.ArgumentParser(description='HMR2 demo - mesh generation only (no rendering)')
    parser.add_argument('--checkpoint', type=str, default=DEFAULT_CHECKPOINT, help='Path to pretrained model checkpoint')
    parser.add_argument('--img_folder', type=str, default='example_data/images', help='Folder with input images')
    parser.add_argument('--out_folder', type=str, default='demo_out', help='Output folder to save mesh results')
    parser.add_argument('--detector', type=str, default='vitdet', choices=['vitdet', 'regnety'], help='Using regnety improves runtime')
    parser.add_argument('--batch_size', type=int, default=1, help='Batch size for inference/fitting')
    parser.add_argument('--file_type', nargs='+', default=['*.jpg', '*.png'], help='List of file extensions to consider')

    args = parser.parse_args()

    # Download and load checkpoints (without renderer)
    download_models(CACHE_DIR_4DHUMANS)
    model, model_cfg = load_hmr2_no_renderer(args.checkpoint)

    # Setup HMR2.0 model
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    model = model.to(device)
    model.eval()

    # Load detector
    from hmr2.utils.utils_detectron2 import DefaultPredictor_Lazy
    if args.detector == 'vitdet':
        from detectron2.config import LazyConfig
        import hmr2
        cfg_path = Path(hmr2.__file__).parent/'configs'/'cascade_mask_rcnn_vitdet_h_75ep.py'
        detectron2_cfg = LazyConfig.load(str(cfg_path))
        detectron2_cfg.train.init_checkpoint = "https://dl.fbaipublicfiles.com/detectron2/ViTDet/COCO/cascade_mask_rcnn_vitdet_h/f328730692/model_final_f05665.pkl"
        for i in range(3):
            detectron2_cfg.model.roi_heads.box_predictors[i].test_score_thresh = 0.25
        detector = DefaultPredictor_Lazy(detectron2_cfg)
    elif args.detector == 'regnety':
        from detectron2 import model_zoo
        from detectron2.config import get_cfg
        detectron2_cfg = get_cfg()
        detectron2_cfg.merge_from_file(model_zoo.get_config_file("new_baselines/mask_rcnn_regnety_4gf_dds_FPN_400ep_LSJ.py"))
        detectron2_cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("new_baselines/mask_rcnn_regnety_4gf_dds_FPN_400ep_LSJ.py")
        detectron2_cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
        detectron2_cfg.MODEL.ROI_HEADS.NMS_THRESH_TEST = 0.4
        detector = DefaultPredictor_Lazy(detectron2_cfg)

    # Setup output folder
    os.makedirs(args.out_folder, exist_ok=True)

    # Get all images in folder
    img_paths = []
    for file_type in args.file_type:
        img_paths.extend(list(Path(args.img_folder).glob(file_type)))
    img_paths = sorted(img_paths)

    print(f"Found {len(img_paths)} images in {args.img_folder}")

    # Process each image
    for img_idx, img_path in enumerate(img_paths):
        print(f"\n[{img_idx+1}/{len(img_paths)}] Processing: {img_path.name}")
        
        img_cv2 = cv2.imread(str(img_path))
        
        # Detect humans
        det_out = detector(img_cv2)
        det_instances = det_out['instances']
        valid_idx = (det_instances.pred_classes == 0) & (det_instances.scores > 0.5)
        boxes = det_instances.pred_boxes.tensor[valid_idx].cpu().numpy()
        
        if len(boxes) == 0:
            print(f"  ⚠ No humans detected in {img_path.name}")
            continue
        
        print(f"  ✓ Detected {len(boxes)} person(s)")
        
        # Create dataset
        dataset = ViTDetDataset(model_cfg, img_cv2, boxes)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)
        
        # Process each detected person
        for person_idx, batch in enumerate(dataloader):
            batch = recursive_to(batch, device)
            
            with torch.no_grad():
                out = model(batch)
            
            # Get SMPL parameters
            pred_cam = out['pred_cam']
            pred_vertices = out['pred_vertices']
            
            # Save mesh for each person in batch
            batch_size = pred_vertices.shape[0]
            for i in range(batch_size):
                person_id = person_idx * args.batch_size + i
                
                # Get vertices and faces
                vertices = pred_vertices[i].cpu().numpy()
                faces = model.smpl.faces
                
                # Create mesh
                mesh = trimesh.Trimesh(vertices, faces, process=False)
                
                # Save mesh
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
    
    end = time.time()
    print(f"\n{'='*60}")
    print(f"✓ Processing complete!")
    print(f"  Total time: {end-start:.2f} seconds")
    print(f"  Output folder: {args.out_folder}")
    print(f"  Files: .obj meshes and .npz parameters")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()

