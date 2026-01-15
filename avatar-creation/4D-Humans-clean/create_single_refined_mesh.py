"""
Create ONE refined mesh from MULTIPLE photos of the SAME person
Averages SMPL parameters for better accuracy
"""
import os
os.environ['PYOPENGL_PLATFORM'] = ''

import torch
import numpy as np
import trimesh
import argparse
from pathlib import Path
import cv2
import time

from hmr2.configs import CACHE_DIR_4DHUMANS, get_config
from hmr2.models import HMR2, download_models, DEFAULT_CHECKPOINT
from hmr2.utils import recursive_to
from hmr2.datasets.vitdet_dataset import ViTDetDataset
from hmr2.utils.utils_yolo import YOLOPredictor

def load_hmr2_no_renderer(checkpoint_path):
    """Load HMR2 without renderer"""
    from hmr2.models import check_smpl_exists
    
    model_cfg = str(Path(checkpoint_path).parent.parent / 'model_config.yaml')
    model_cfg = get_config(model_cfg, update_cachedir=True)
    
    if (model_cfg.MODEL.BACKBONE.TYPE == 'vit') and ('BBOX_SHAPE' not in model_cfg.MODEL):
        model_cfg.defrost()
        model_cfg.MODEL.BBOX_SHAPE = [192,256]
        model_cfg.freeze()
    
    check_smpl_exists()
    model = HMR2.load_from_checkpoint(checkpoint_path, strict=False, cfg=model_cfg, init_renderer=False)
    return model, model_cfg

def process_multiple_images_to_single_mesh(image_paths, output_dir, person_name="person", 
                                          target_height_cm=None, select_best=False):
    """
    Process multiple images of the SAME person and create ONE refined mesh
    
    Args:
        image_paths: List of image paths (all of same person)
        output_dir: Output directory
        person_name: Name for the output files
        target_height_cm: Optional height in cm for scaling
        select_best: If True, select best quality image. If False, average SMPL params
    
    Returns:
        Path to final mesh
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    print("\n" + "="*70)
    print("MULTI-IMAGE TO SINGLE MESH PIPELINE")
    print("="*70)
    print(f"Input images: {len(image_paths)}")
    print(f"Output name: {person_name}")
    if target_height_cm:
        print(f"Target height: {target_height_cm}cm")
    print("="*70)
    print()
    
    # Load models
    print("📦 Loading HMR2 model...")
    download_models(CACHE_DIR_4DHUMANS)
    model, model_cfg = load_hmr2_no_renderer(DEFAULT_CHECKPOINT)
    
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    model = model.to(device)
    model.eval()
    print(f"✓ Model loaded on {device}\n")
    
    print("📦 Loading YOLO detector...")
    detector = YOLOPredictor(confidence=0.5)
    print()
    
    # Process each image and collect SMPL parameters
    all_betas = []
    all_poses = []
    all_global_orients = []
    all_vertices = []
    all_confidences = []
    
    print(f"🖼️  Processing {len(image_paths)} images...\n")
    
    for idx, img_path in enumerate(image_paths, 1):
        img_path = Path(img_path)
        if img_path.name.startswith('._'):
            print(f"  [{idx}/{len(image_paths)}] Skipping: {img_path.name}")
            continue
        
        print(f"  [{idx}/{len(image_paths)}] Processing: {img_path.name}")
        
        # Load image
        img_cv2 = cv2.imread(str(img_path))
        if img_cv2 is None:
            print(f"    ⚠️  Failed to load, skipping")
            continue
        
        # Detect person
        det_out = detector(img_cv2)
        det_instances = det_out['instances']
        valid_idx = (det_instances.pred_classes == 0) & (det_instances.scores > 0.5)
        boxes = det_instances.pred_boxes.tensor[valid_idx].cpu().numpy()
        
        if len(boxes) == 0:
            print(f"    ⚠️  No person detected, skipping")
            continue
        
        # Use the largest bounding box (likely the main person)
        if len(boxes) > 1:
            areas = [(box[2]-box[0])*(box[3]-box[1]) for box in boxes]
            largest_idx = np.argmax(areas)
            boxes = [boxes[largest_idx]]
            print(f"    ℹ️  Multiple people detected, using largest")
        
        print(f"    ✓ Detected person (confidence: {det_instances.scores[valid_idx][0]:.2f})")
        
        # Create dataset
        dataset = ViTDetDataset(model_cfg, img_cv2, boxes)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=1, shuffle=False, num_workers=0)
        
        # Run model
        batch = next(iter(dataloader))
        batch = recursive_to(batch, device)
        
        with torch.no_grad():
            out = model(batch)
        
        # Extract SMPL parameters
        betas = out['pred_smpl_params']['betas'][0].cpu().numpy()  # (10,) body shape
        body_pose = out['pred_smpl_params']['body_pose'][0].cpu().numpy()  # (23, 3, 3) pose
        global_orient = out['pred_smpl_params']['global_orient'][0].cpu().numpy()  # (1, 3, 3) global rotation
        vertices = out['pred_vertices'][0].cpu().numpy()  # (6890, 3)
        
        # Calculate confidence (based on detection score)
        confidence = float(det_instances.scores[valid_idx][0])
        
        all_betas.append(betas)
        all_poses.append(body_pose)
        all_global_orients.append(global_orient)
        all_vertices.append(vertices)
        all_confidences.append(confidence)
        
        print(f"    ✓ Extracted SMPL parameters")
    
    if len(all_betas) == 0:
        print("\n❌ No valid detections in any image!")
        return None
    
    print(f"\n✓ Successfully processed {len(all_betas)} images")
    print()
    
    # Combine results
    if select_best:
        # Select the image with highest confidence
        best_idx = np.argmax(all_confidences)
        print(f"📊 Selecting best quality image (#{best_idx+1}, confidence: {all_confidences[best_idx]:.2f})")
        
        final_betas = all_betas[best_idx]
        final_body_pose = all_poses[best_idx]
        final_global_orient = all_global_orients[best_idx]
        final_vertices = all_vertices[best_idx]
    else:
        # Average SMPL parameters (weighted by confidence)
        print(f"📊 Averaging SMPL parameters across {len(all_betas)} images...")
        
        confidences = np.array(all_confidences)
        weights = confidences / confidences.sum()
        
        # Weighted average of betas (body shape)
        final_betas = np.average(all_betas, axis=0, weights=weights)
        
        # For poses, use the median (more robust than mean for rotation matrices)
        final_body_pose = np.median(all_poses, axis=0)
        final_global_orient = np.median(all_global_orients, axis=0)
        
        # Average vertices directly
        final_vertices = np.average(all_vertices, axis=0, weights=weights)
        
        print(f"    Confidence weights: {', '.join([f'{w:.2f}' for w in weights])}")
    
    # Scale if height provided
    if target_height_cm:
        print(f"\n📏 Scaling to target height: {target_height_cm}cm")
        mesh_height_cm = (final_vertices[:, 1].max() - final_vertices[:, 1].min()) * 100
        scale_factor = target_height_cm / mesh_height_cm
        final_vertices = final_vertices * scale_factor
        print(f"    Original height: {mesh_height_cm:.2f}cm")
        print(f"    Scale factor: {scale_factor:.4f}")
    
    # Create final mesh
    print(f"\n💾 Saving final mesh...")
    mesh = trimesh.Trimesh(final_vertices, model.smpl.faces, process=False)
    
    mesh_path = output_dir / f"{person_name}_refined.obj"
    mesh.export(str(mesh_path))
    print(f"    ✓ Mesh: {mesh_path}")
    
    # Save SMPL parameters
    params_path = output_dir / f"{person_name}_refined_params.npz"
    np.savez(
        str(params_path),
        betas=final_betas,
        body_pose=final_body_pose,
        global_orient=final_global_orient,
        num_images_used=len(all_betas),
        confidences=all_confidences,
        method='average' if not select_best else 'best_selection'
    )
    print(f"    ✓ SMPL params: {params_path}")
    
    print("\n" + "="*70)
    print("✅ SINGLE REFINED MESH CREATED!")
    print("="*70)
    print(f"   Input images: {len(image_paths)}")
    print(f"   Used images: {len(all_betas)}")
    print(f"   Output mesh: {mesh_path}")
    print(f"   Method: {'Best selection' if select_best else 'Weighted average'}")
    if target_height_cm:
        print(f"   Height: {target_height_cm}cm")
    print("="*70)
    print()
    
    return mesh_path

def main():
    parser = argparse.ArgumentParser(
        description='Create ONE refined mesh from MULTIPLE images of the same person',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Average multiple photos into one mesh
  python create_single_refined_mesh.py --images photo1.jpg photo2.jpg photo3.jpg --name john --height 192

  # Use all images in a folder
  python create_single_refined_mesh.py --folder my_photos/ --name john --height 192

  # Select best quality instead of averaging
  python create_single_refined_mesh.py --images *.jpg --name john --height 192 --select-best
        '''
    )
    
    parser.add_argument('--images', nargs='+', help='List of image files (all of same person)')
    parser.add_argument('--folder', type=str, help='Folder containing images (all of same person)')
    parser.add_argument('--name', type=str, default='person', help='Name for output files')
    parser.add_argument('--output', type=str, default='refined_mesh', help='Output directory')
    parser.add_argument('--height', type=float, help='Target height in cm for scaling')
    parser.add_argument('--select-best', action='store_true',
                       help='Select best quality image instead of averaging')
    
    args = parser.parse_args()
    
    # Collect image paths
    image_paths = []
    
    if args.images:
        image_paths.extend(args.images)
    
    if args.folder:
        folder = Path(args.folder)
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
            image_paths.extend([str(p) for p in folder.glob(ext)])
    
    if not image_paths:
        print("❌ Error: No images provided. Use --images or --folder")
        parser.print_help()
        return
    
    # Remove duplicates
    image_paths = list(set(image_paths))
    
    if len(image_paths) < 2:
        print("⚠️  Warning: Only 1 image provided. Consider using demo_yolo.py instead.")
        print("   This script is designed for multiple images of the same person.")
        print()
    
    # Process
    mesh_path = process_multiple_images_to_single_mesh(
        image_paths=image_paths,
        output_dir=args.output,
        person_name=args.name,
        target_height_cm=args.height,
        select_best=args.select_best
    )
    
    if mesh_path:
        print("💡 Next steps:")
        print(f"   1. View in Blender: open -a Blender {mesh_path}")
        print(f"   2. Extract measurements:")
        if args.height:
            print(f"      python extract_accurate_measurements.py --mesh {mesh_path} --height {args.height}")
        else:
            print(f"      python extract_accurate_measurements.py --mesh {mesh_path} --height [YOUR_HEIGHT]")
        print()

if __name__ == '__main__':
    main()

