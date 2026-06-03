import bpy
import sys

argv = sys.argv
argv = argv[argv.index("--") + 1:]

input_path = argv[0]
output_path = argv[1]
decimate_ratio = float(argv[2])

# Clean scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Import PLY (Blender 5 syntax)
bpy.ops.wm.ply_import(filepath=input_path)

obj = bpy.context.selected_objects[0]
bpy.context.view_layer.objects.active = obj

# Decimate
decimate = obj.modifiers.new(name="Decimate", type='DECIMATE')
decimate.ratio = decimate_ratio
bpy.ops.object.modifier_apply(modifier="Decimate")

# Export GLB
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB'
)

print("GLB Exported Successfully")  