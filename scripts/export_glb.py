import sys
import trimesh

if len(sys.argv) < 3:
    print("Usage: python export_glb.py input_mesh.ply output_model.glb")
    sys.exit(1)

input_path = sys.argv[1]
output_path = sys.argv[2]

# Force load as mesh
mesh = trimesh.load(input_path, force='mesh')

if mesh.is_empty:
    print("Mesh is empty. Cannot export.")
    sys.exit(1)

# --- SAFE CLEANUP (Trimesh 4.x Compatible) ---
mesh.remove_unreferenced_vertices()
mesh.merge_vertices()

# Generate normals if missing
if mesh.vertex_normals is None or len(mesh.vertex_normals) == 0:
    mesh.rezero()
    mesh.vertex_normals  # accessing forces generation

# Optional repair (safe call)
try:
    trimesh.repair.fill_holes(mesh)
except:
    pass

# Export GLB
mesh.export(output_path)

print(f"GLB exported successfully to: {output_path}")