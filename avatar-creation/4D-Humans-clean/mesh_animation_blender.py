import bpy
import os

# Settings
mesh_paths = ['rotation_meshes/frame_0001_person0.obj', 'rotation_meshes/frame_0002_person0.obj', 'rotation_meshes/frame_0003_person0.obj', 'rotation_meshes/frame_0004_person0.obj', 'rotation_meshes/frame_0005_person0.obj', 'rotation_meshes/frame_0006_person0.obj', 'rotation_meshes/frame_0007_person0.obj', 'rotation_meshes/frame_0008_person0.obj', 'rotation_meshes/frame_0009_person0.obj', 'rotation_meshes/frame_0010_person0.obj', 'rotation_meshes/frame_0011_person0.obj', 'rotation_meshes/frame_0012_person0.obj', 'rotation_meshes/frame_0013_person0.obj', 'rotation_meshes/frame_0014_person0.obj', 'rotation_meshes/frame_0015_person0.obj', 'rotation_meshes/frame_0016_person0.obj', 'rotation_meshes/frame_0017_person0.obj', 'rotation_meshes/frame_0018_person0.obj', 'rotation_meshes/frame_0019_person0.obj', 'rotation_meshes/frame_0020_person0.obj', 'rotation_meshes/frame_0021_person0.obj', 'rotation_meshes/frame_0022_person0.obj', 'rotation_meshes/frame_0023_person0.obj', 'rotation_meshes/frame_0024_person0.obj', 'rotation_meshes/frame_0025_person0.obj', 'rotation_meshes/frame_0026_person0.obj', 'rotation_meshes/frame_0027_person0.obj', 'rotation_meshes/frame_0028_person0.obj', 'rotation_meshes/frame_0029_person0.obj', 'rotation_meshes/frame_0030_person0.obj', 'rotation_meshes/frame_0031_person0.obj']
fps = 10
output_video = "mesh_animation.mp4"

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Set FPS
bpy.context.scene.render.fps = fps

# Import all meshes
mesh_objects = []
for idx, mesh_path in enumerate(mesh_paths):
    print(f"Loading mesh {idx+1}/{len(mesh_paths)}: {mesh_path}")
    
    # Import mesh
    bpy.ops.wm.obj_import(filepath=mesh_path)
    
    # Get the imported object
    obj = bpy.context.selected_objects[0]
    obj.name = f"mesh_frame_{idx:04d}"
    
    # Hide by default
    obj.hide_viewport = True
    obj.hide_render = True
    
    mesh_objects.append(obj)

print(f"\n✅ Loaded {len(mesh_objects)} meshes")

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

print("\n✅ Animation setup complete!")
print(f"   Total frames: {len(mesh_objects)}")
print(f"   FPS: 10")
print("\n💡 To play:")
print("   - Press SPACEBAR to play animation")
print("   - Use timeline scrubber to navigate frames")
print("\n💡 To render video:")
print("   - Go to: Render > Render Animation")
print(f"   - Output will be saved as: {output_video}")

# Save blend file
blend_path = "mesh_animation.blend"
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print(f"\n💾 Saved Blender file: {blend_path}")
