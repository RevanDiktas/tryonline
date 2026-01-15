"""
Extract frames from video for processing
Simple and lightweight
"""
import cv2
import argparse
from pathlib import Path

def extract_frames(video_path, output_dir, frame_interval=30, max_frames=10):
    """
    Extract frames from video to image files
    
    Args:
        video_path: Path to video
        output_dir: Output directory for frames
        frame_interval: Save every Nth frame
        max_frames: Maximum frames to save
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    print(f"📹 Opening video: {video_path}")
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        print("❌ Failed to open video")
        return
    
    # Get video info
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps if fps > 0 else 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"   Resolution: {width}x{height}")
    print(f"   Total frames: {total_frames}")
    print(f"   FPS: {fps:.2f}")
    print(f"   Duration: {duration:.2f} seconds")
    print(f"   Extracting every {frame_interval} frames (≈ {frame_interval/fps:.2f} seconds apart)")
    print()
    
    saved_frames = []
    frame_count = 0
    extracted_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % frame_interval == 0:
            frame_filename = f"frame_{frame_count:05d}.jpg"
            frame_path = output_dir / frame_filename
            cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            timestamp = frame_count / fps
            print(f"✓ Saved frame {extracted_count+1}/{max_frames}: {frame_filename} "
                  f"(t={timestamp:.2f}s)")
            
            saved_frames.append(str(frame_path))
            extracted_count += 1
            
            if max_frames and extracted_count >= max_frames:
                break
        
        frame_count += 1
    
    cap.release()
    
    print(f"\n✅ Extracted {len(saved_frames)} frames to: {output_dir}/")
    print(f"\n💡 Next step - Process with HMR2:")
    print(f"   python demo_yolo.py --img_folder {output_dir} --out_folder video_meshes --batch_size=1")
    print()
    
    return saved_frames

def main():
    parser = argparse.ArgumentParser(description='Extract frames from video')
    parser.add_argument('--video', type=str, required=True,
                       help='Input video file')
    parser.add_argument('--output', type=str, default='video_frames',
                       help='Output directory for frames')
    parser.add_argument('--interval', type=int, default=30,
                       help='Save every Nth frame (default: 30)')
    parser.add_argument('--max-frames', type=int, default=10,
                       help='Maximum frames to extract (default: 10)')
    
    args = parser.parse_args()
    
    extract_frames(args.video, args.output, args.interval, args.max_frames)

if __name__ == '__main__':
    main()


