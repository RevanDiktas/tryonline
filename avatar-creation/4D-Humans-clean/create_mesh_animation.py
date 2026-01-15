"""
Create video/animation from sequence of 3D meshes
Play meshes like frames in a video loop
"""
import os
os.environ['PYOPENGL_PLATFORM'] = ''

import numpy as np
import trimesh
import argparse
from pathlib import Path
import subprocess
import tempfile
import shutil

try:
    import pyrender
    import PIL.Image as Image
    RENDERING_AVAILABLE = True
except ImportError:
    RENDERING_AVAILABLE = False
    print("⚠️  pyrender not available - will generate Blender script instead")

def render_mesh_to_image(mesh, camera_distance=2.5, resolution=(800, 800)):
    """
    Render a mesh to an image using pyrender
    """
    if not RENDERING_AVAILABLE:
        raise ImportError("pyrender required for rendering")
    
    # Create scene
    scene = pyrender.Scene()
    
    # Add mesh
    mesh_pyrender = pyrender.Mesh.from_trimesh(mesh)
    scene.add(mesh_pyrender)
    
    # Add camera
    camera = pyrender.PerspectiveCamera(yfov=np.pi / 3.0)
    camera_pose = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, camera_distance],
        [0.0, 0.0, 0.0, 1.0],
    ])
    scene.add(camera, pose=camera_pose)
    
    # Add light
    light = pyrender.DirectionalLight(color=np.ones(3), intensity=3.0)
    scene.add(light, pose=camera_pose)
    
    # Render
    renderer = pyrender.OffscreenRenderer(*resolution)
    color, _ = renderer.render(scene)
    renderer.delete()
    
    return color

def create_mesh_video_with_rendering(mesh_paths, output_video, fps=10, resolution=(800, 800)):
    """
    Create video from mesh sequence by rendering each frame
    """
    if not RENDERING_AVAILABLE:
        print("❌ pyrender not available. Install with: pip install pyrender")
        return False
    
    print(f"🎬 Creating video from {len(mesh_paths)} meshes...")
    print(f"   FPS: {fps}")
    print(f"   Resolution: {resolution[0]}x{resolution[1]}")
    print()
    
    # Create temp directory for frames
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Render each mesh
        for idx, mesh_path in enumerate(mesh_paths):
            print(f"  [{idx+1}/{len(mesh_paths)}] Rendering: {Path(mesh_path).name}")
            
            # Load mesh
            mesh = trimesh.load(str(mesh_path))
            
            # Render to image
            img = render_mesh_to_image(mesh, resolution=resolution)
            
            # Save frame
            frame_path = temp_dir / f"frame_{idx:04d}.png"
            Image.fromarray(img).save(str(frame_path))
        
        print()
        print("📹 Encoding video with ffmpeg...")
        
        # Create video with ffmpeg
        cmd = [
            'ffmpeg',
            '-framerate', str(fps),
            '-i', str(temp_dir / 'frame_%04d.png'),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-y',
            str(output_video)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Video created: {output_video}")
            return True
        else:
            print(f"❌ ffmpeg failed: {result.stderr}")
            return False

def create_blender_animation_script(mesh_paths, output_script, fps=10):
    """
    Create Blender Python script to play meshes as animation
    """
    script = f'''import bpy
import os

# Settings
mesh_paths = {[str(p) for p in mesh_paths]}
fps = {fps}
output_video = "{output_script.parent / 'mesh_animation.mp4'}"

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Set FPS
bpy.context.scene.render.fps = fps

# Import all meshes
mesh_objects = []
for idx, mesh_path in enumerate(mesh_paths):
    print(f"Loading mesh {{idx+1}}/{{len(mesh_paths)}}: {{mesh_path}}")
    
    # Import mesh
    bpy.ops.wm.obj_import(filepath=mesh_path)
    
    # Get the imported object
    obj = bpy.context.selected_objects[0]
    obj.name = f"mesh_frame_{{idx:04d}}"
    
    # Hide by default
    obj.hide_viewport = True
    obj.hide_render = True
    
    mesh_objects.append(obj)

print(f"\\n✅ Loaded {{len(mesh_objects)}} meshes")

# Create keyframe animation (show/hide meshes)
for idx, obj in enumerate(mesh_objects):
    frame_num = idx + 1
    
    # Show this mesh on its frame
    obj.hide_viewport = False
    obj.hide_render = False
    obj.keyframe_insert(data_path="hide_viewport", frame=frame_num)
    obj.keyframe_insert(data_path="hide_render", frame=frame_num)
    
    # Hide on next frame
    if idx < len(mesh_objects) - 1:
        obj.hide_viewport = True
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_viewport", frame=frame_num + 1)
        obj.keyframe_insert(data_path="hide_render", frame=frame_num + 1)

# Set frame range
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = len(mesh_objects)

# Add camera
bpy.ops.object.camera_add(location=(0, -3, 1))
camera = bpy.context.object
camera.rotation_euler = (1.2, 0, 0)
bpy.context.scene.camera = camera

# Add light
bpy.ops.object.light_add(type='SUN', location=(5, 5, 5))
light = bpy.context.object
light.data.energy = 3.0

# Add material to meshes
material = bpy.data.materials.new(name="BodyMaterial")
material.use_nodes = True
bsdf = material.node_tree.nodes.get('Principled BSDF')
if bsdf:
    bsdf.inputs['Base Color'].default_value = (0.8, 0.7, 0.6, 1.0)  # Skin tone
    bsdf.inputs['Roughness'].default_value = 0.7

for obj in mesh_objects:
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)

print("\\n✅ Animation setup complete!")
print(f"   Total frames: {{len(mesh_objects)}}")
print(f"   FPS: {fps}")
print("\\n💡 To play:")
print("   - Press SPACEBAR to play animation")
print("   - Use timeline scrubber to navigate frames")
print("\\n💡 To render video:")
print("   - Go to: Render > Render Animation")
print(f"   - Output will be saved as: {{output_video}}")

# Save blend file
blend_path = "{output_script.parent / 'mesh_animation.blend'}"
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print(f"\\n💾 Saved Blender file: {{blend_path}}")
'''
    
    output_script.write_text(script)
    print(f"✅ Created Blender script: {output_script}")
    print()
    print("💡 To use:")
    print(f"   blender --python {output_script}")
    print("   or open Blender and run the script from Text Editor")
    
    return True

def create_mesh_sequence_summary(mesh_paths, output_dir):
    """
    Create a summary HTML viewer for mesh sequence
    """
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>Mesh Sequence Viewer</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #1a1a1a;
            color: #ffffff;
        }}
        h1 {{ color: #4CAF50; }}
        .controls {{
            background: #2a2a2a;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        .frame-info {{
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
        }}
        button {{
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
            margin: 5px;
            border-radius: 5px;
        }}
        button:hover {{ background: #45a049; }}
        input[type="range"] {{
            width: 100%;
            margin: 10px 0;
        }}
        .mesh-list {{
            background: #2a2a2a;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
        }}
        .mesh-item {{
            padding: 5px;
            margin: 2px 0;
            font-family: monospace;
        }}
        .current {{ color: #4CAF50; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>🎬 Mesh Sequence Viewer</h1>
    
    <div class="controls">
        <div class="frame-info">
            Frame: <span id="currentFrame">1</span> / <span id="totalFrames">{len(mesh_paths)}</span>
        </div>
        
        <input type="range" id="frameSlider" min="1" max="{len(mesh_paths)}" value="1" />
        
        <div>
            <button onclick="playPause()">▶️ Play / ⏸️ Pause</button>
            <button onclick="prevFrame()">⏮️ Previous</button>
            <button onclick="nextFrame()">⏭️ Next</button>
            <button onclick="reset()">🔄 Reset</button>
        </div>
        
        <div style="margin-top: 10px;">
            <label>FPS: <input type="number" id="fpsInput" value="10" min="1" max="60" style="width: 60px;" /></label>
        </div>
    </div>
    
    <div class="mesh-list">
        <h3>📁 Mesh Files ({len(mesh_paths)} total)</h3>
        <div id="meshList"></div>
    </div>
    
    <script>
        const meshPaths = {[str(p.name) for p in mesh_paths]};
        let currentFrame = 1;
        let isPlaying = false;
        let playInterval = null;
        
        function updateDisplay() {{
            document.getElementById('currentFrame').textContent = currentFrame;
            document.getElementById('frameSlider').value = currentFrame;
            
            // Update mesh list
            const meshListDiv = document.getElementById('meshList');
            meshListDiv.innerHTML = meshPaths.map((mesh, idx) => {{
                const frameNum = idx + 1;
                const className = frameNum === currentFrame ? 'mesh-item current' : 'mesh-item';
                return `<div class="${{className}}">${{frameNum}}. ${{mesh}}</div>`;
            }}).join('');
        }}
        
        function nextFrame() {{
            currentFrame = currentFrame >= {len(mesh_paths)} ? 1 : currentFrame + 1;
            updateDisplay();
        }}
        
        function prevFrame() {{
            currentFrame = currentFrame <= 1 ? {len(mesh_paths)} : currentFrame - 1;
            updateDisplay();
        }}
        
        function playPause() {{
            isPlaying = !isPlaying;
            
            if (isPlaying) {{
                const fps = parseInt(document.getElementById('fpsInput').value) || 10;
                const interval = 1000 / fps;
                playInterval = setInterval(nextFrame, interval);
            }} else {{
                if (playInterval) {{
                    clearInterval(playInterval);
                    playInterval = null;
                }}
            }}
        }}
        
        function reset() {{
            currentFrame = 1;
            isPlaying = false;
            if (playInterval) {{
                clearInterval(playInterval);
                playInterval = null;
            }}
            updateDisplay();
        }}
        
        document.getElementById('frameSlider').addEventListener('input', (e) => {{
            currentFrame = parseInt(e.target.value);
            updateDisplay();
        }});
        
        // Initialize
        updateDisplay();
        
        console.log('Mesh Sequence Viewer Ready!');
        console.log(`Total meshes: {len(mesh_paths)}`);
    </script>
    
    <div style="margin-top: 30px; padding: 20px; background: #2a2a2a; border-radius: 10px;">
        <h3>💡 How to View 3D Meshes:</h3>
        <p><strong>Option 1: Blender (Recommended)</strong></p>
        <pre>blender --python mesh_animation_blender.py</pre>
        
        <p><strong>Option 2: Manual in Blender</strong></p>
        <ol>
            <li>Open Blender</li>
            <li>File > Import > Wavefront (.obj)</li>
            <li>Navigate through meshes using this viewer as reference</li>
        </ol>
        
        <p><strong>Option 3: Create Video</strong></p>
        <pre>python create_mesh_animation.py --meshes {output_dir}/*.obj --output animation.mp4</pre>
    </div>
</body>
</html>'''
    
    html_path = output_dir / 'mesh_sequence_viewer.html'
    html_path.write_text(html_content)
    print(f"✅ Created HTML viewer: {html_path}")
    print(f"   Open with: open {html_path}")
    
    return html_path

def main():
    parser = argparse.ArgumentParser(
        description='Create video/animation from sequence of 3D meshes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Create video from mesh sequence (requires pyrender)
  python create_mesh_animation.py --meshes frame_*.obj --output animation.mp4 --fps 10

  # Create Blender script (works on macOS without rendering)
  python create_mesh_animation.py --meshes frame_*.obj --blender-script --fps 10

  # Create HTML viewer
  python create_mesh_animation.py --meshes frame_*.obj --html-only
        '''
    )
    
    parser.add_argument('--meshes', nargs='+', required=True, help='List of mesh files in sequence')
    parser.add_argument('--folder', type=str, help='Folder containing mesh sequence')
    parser.add_argument('--output', type=str, default='mesh_animation.mp4', help='Output video file')
    parser.add_argument('--fps', type=int, default=10, help='Frames per second (default: 10)')
    parser.add_argument('--resolution', type=int, nargs=2, default=[800, 800], help='Video resolution (default: 800 800)')
    parser.add_argument('--blender-script', action='store_true', help='Create Blender script instead of video')
    parser.add_argument('--html-only', action='store_true', help='Only create HTML viewer')
    
    args = parser.parse_args()
    
    # Collect mesh paths
    mesh_paths = []
    
    if args.meshes:
        mesh_paths.extend([Path(p) for p in args.meshes])
    
    if args.folder:
        folder = Path(args.folder)
        mesh_paths.extend(sorted(folder.glob('*.obj')))
    
    if not mesh_paths:
        print("❌ No meshes found")
        return
    
    # Sort by name (assumes sequential naming)
    mesh_paths = sorted(set(mesh_paths))
    
    print("\n" + "="*70)
    print("MESH ANIMATION CREATOR")
    print("="*70)
    print(f"Meshes: {len(mesh_paths)}")
    print(f"FPS: {args.fps}")
    print("="*70)
    print()
    
    output_dir = Path(args.output).parent if Path(args.output).parent != Path('.') else Path('.')
    
    # Create HTML viewer
    html_path = create_mesh_sequence_summary(mesh_paths, output_dir)
    print()
    
    if args.html_only:
        print("✅ HTML viewer created. Open in browser to navigate frames.")
        return
    
    # Create Blender script or video
    if args.blender_script or not RENDERING_AVAILABLE:
        script_path = output_dir / 'mesh_animation_blender.py'
        create_blender_animation_script(mesh_paths, script_path, args.fps)
        print()
        print("✅ Blender animation script created!")
        print(f"\n💡 To view animation:")
        print(f"   blender --python {script_path}")
    else:
        # Create video with rendering
        success = create_mesh_video_with_rendering(
            mesh_paths,
            args.output,
            fps=args.fps,
            resolution=tuple(args.resolution)
        )
        
        if success:
            print(f"\n✅ Video created: {args.output}")
            print(f"   Play with: open {args.output}")

if __name__ == '__main__':
    main()

