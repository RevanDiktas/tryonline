"""
Process video to extract 3D meshes and measurements
Processes every Nth frame to avoid redundancy
"""
import cv2
import numpy as np
import torch
import trimesh
import argparse
from pathlib import Path
import json
import time

from hmr2.configs import CACHE_DIR_4DHUMANS, get_config
from hmr2.models import HMR2, download_models, DEFAULT_CHECKPOINT
from hmr2.utils import recursive_to
from hmr2.datasets.vitdet_dataset import ViTDetDataset
from hmr2.utils.utils_yolo import YOLOPredictor

def extract_frames(video_path, frame_interval=30, max_frames=None):
    """
    Extract frames from video
    
    Args:
        video_path: Path to video file
        frame_interval: Extract every Nth frame (default 30 = 1 per second for 30fps)
        max_frames: Maximum number of frames to extract
    
    Returns:
        list of (frame_number, frame_image)
    """
    print(f"📹 Opening video: {video_path}")
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        print("❌ Failed to open video")
        return []
    
    # Get video properties
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps if fps > 0 else 0
    
    print(f"   Total frames: {total_frames}")
    print(f"   FPS: {fps:.2f}")
    print(f"   Duration: {duration:.2f} seconds")
    print(f"   Extracting every {frame_interval} frames")
    
    frames = []
    frame_count = 0
    extracted_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % frame_interval == 0:
            frames.append((frame_count, frame))
            extracted_count += 1
            
            if max_frames and extracted_count >= max_frames:
                break
        
        frame_count += 1
    
    cap.release()
    
    print(f"✓ Extracted {len(frames)} frames")
    return frames

def process_video_to_meshes(video_path, output_dir, frame_interval=30, max_frames=10, 
                            target_height_cm=None):
    """
    Process video and generate 3D meshes for detected people
    
    Args:
        video_path: Path to video
        output_dir: Output directory
        frame_interval: Extract every Nth frame
        max_frames: Maximum frames to process
        target_height_cm: If provided, scale meshes to this height
    
    Returns:
        dict with processing results
    """
    start_time = time.time()
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    print("\n" + "="*70)
    print("VIDEO PROCESSING PIPELINE")
    print("="*70)
    
    # Load models
    print("\n📦 Loading HMR2 model...")
    download_models(CACHE_DIR_4DHUMANS)
    model, model_cfg = load_hmr2_no_renderer(DEFAULT_CHECKPOINT)
    
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    model = model.to(device)
    model.eval()
    print(f"✓ Model loaded on {device}")
    
    print("\n📦 Loading YOLO detector...")
    detector = YOLOPredictor(confidence=0.5)
    
    # Extract frames
    print("\n📹 Extracting frames from video...")
    frames = extract_frames(video_path, frame_interval, max_frames)
    
    if not frames:
        print("❌ No frames extracted")
        return
    
    # Process each frame
    results = {
        'video_path': str(video_path),
        'total_frames_processed': len(frames),
        'frames': {}
    }
    
    print(f"\n🎬 Processing {len(frames)} frames...")
    print("="*70)
    
    total_people = 0
    
    for idx, (frame_num, frame) in enumerate(frames):
        print(f"\n[Frame {idx+1}/{len(frames)}] Frame #{frame_num}")
        
        # Detect people
        det_out = detector(frame)
        det_instances = det_out['instances']
        valid_idx = (det_instances.pred_classes == 0) & (det_instances.scores > 0.5)
        boxes = det_instances.pred_boxes.tensor[valid_idx].cpu().numpy()
        
        if len(boxes) == 0:
            print("  ⚠️  No people detected")
            results['frames'][frame_num] = {'people_count': 0, 'meshes': []}
            continue
        
        print(f"  ✓ Detected {len(boxes)} person(s)")
        total_people += len(boxes)
        
        # Create dataset
        dataset = ViTDetDataset(model_cfg, frame, boxes)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=1, shuffle=False, num_workers=0)
        
        frame_meshes = []
        
        for person_idx, batch in enumerate(dataloader):
            batch = recursive_to(batch, device)
            
            with torch.no_grad():
                out = model(batch)
            
            pred_vertices = out['pred_vertices'][0].cpu().numpy()
            
            # Scale if height provided
            if target_height_cm:
                mesh_height = (pred_vertices[:, 1].max() - pred_vertices[:, 1].min()) * 100
                scale_factor = target_height_cm / mesh_height
                pred_vertices = pred_vertices * scale_factor
            
            # Save mesh
            mesh = trimesh.Trimesh(pred_vertices, model.smpl.faces, process=False)
            mesh_filename = f"frame{frame_num:04d}_person{person_idx}.obj"
            mesh_path = output_dir / mesh_filename
            mesh.export(str(mesh_path))
            
            # Calculate measurements
            measurements = calculate_quick_measurements(pred_vertices, target_height_cm)
            
            frame_meshes.append({
                'mesh_file': mesh_filename,
                'measurements': measurements
            })
            
            print(f"  ✓ Person {person_idx}: {mesh_filename}")
            if target_height_cm:
                print(f"     Height: {measurements['height_cm']:.1f}cm, "
                      f"Chest: {measurements.get('chest_circumference_cm', 0):.1f}cm")
        
        results['frames'][frame_num] = {
            'people_count': len(boxes),
            'meshes': frame_meshes
        }
    
    # Save results
    results['total_people_detected'] = total_people
    results['processing_time_seconds'] = time.time() - start_time
    
    results_file = output_dir / 'video_processing_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*70)
    print("✅ VIDEO PROCESSING COMPLETE!")
    print("="*70)
    print(f"   Frames processed: {len(frames)}")
    print(f"   Total people detected: {total_people}")
    print(f"   Time: {results['processing_time_seconds']:.2f} seconds")
    print(f"   Output: {output_dir}/")
    print(f"   Results: {results_file}")
    print("="*70)
    
    return results

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

def calculate_quick_measurements(vertices, actual_height_cm=None):
    """Quick measurement calculation"""
    measurements = {}
    
    y_min = vertices[:, 1].min()
    y_max = vertices[:, 1].max()
    y_range = y_max - y_min
    
    measurements['height_cm'] = actual_height_cm if actual_height_cm else y_range * 100
    
    # Chest
    chest_y = y_min + (y_range * 0.75)
    chest_mask = np.abs(vertices[:, 1] - chest_y) < (y_range * 0.04)
    if chest_mask.sum() > 0:
        chest_verts = vertices[chest_mask]
        width = chest_verts[:, 0].max() - chest_verts[:, 0].min()
        depth = chest_verts[:, 2].max() - chest_verts[:, 2].min()
        measurements['chest_circumference_cm'] = np.pi * (width + depth) / 2 * 100
    
    return measurements

def main():
    parser = argparse.ArgumentParser(description='Process video to extract 3D meshes')
    parser.add_argument('--video', type=str, default='example_data/videos/gymnasts.mp4',
                       help='Input video file')
    parser.add_argument('--output', type=str, default='video_output',
                       help='Output directory')
    parser.add_argument('--frame-interval', type=int, default=30,
                       help='Extract every Nth frame (default: 30 = 1 per second at 30fps)')
    parser.add_argument('--max-frames', type=int, default=10,
                       help='Maximum frames to process (default: 10)')
    parser.add_argument('--height', type=float,
                       help='Target height in cm for scaling (optional)')
    
    args = parser.parse_args()
    
    results = process_video_to_meshes(
        video_path=args.video,
        output_dir=args.output,
        frame_interval=args.frame_interval,
        max_frames=args.max_frames,
        target_height_cm=args.height
    )
    
    print("\n💡 Next steps:")
    print(f"   1. Check meshes in: {args.output}/")
    print(f"   2. Open in Blender: open -a Blender {args.output}/frame*.obj")
    print(f"   3. View results: cat {args.output}/video_processing_results.json")
    print()

if __name__ == '__main__':
    main()


