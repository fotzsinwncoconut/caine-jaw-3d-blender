"""
CAINE JAW 3D - FINAL PRODUCTION GENERATOR
Blender script for generating the reverse-engineered Caine jaw model
with animation, professional materials, and export-ready output.

Features:
- Parametric dental arch geometry from CAD specifications
- 14 teeth per arch (upper/lower) with faceted topology
- Gingival collars with anatomical curvature
- Top hat accessory assembly
- 360° rotation animation
- Studio lighting + isometric camera
- Export to GLB/OBJ

Usage:
1. Open Blender
2. Switch to Scripting workspace
3. Paste this script
4. Run (Alt+P)
5. Wait for completion
6. Go to final frame (end key) to see animation
7. File → Export as GLB/OBJ

"""

import bpy
import bmesh
import math
from mathutils import Vector, Matrix

# ==================== PARAMETERS ====================

PARAMS = {
    "width": 160.0,
    "depth": 115.0,
    "arch_height": 100.0,
    "total_height": 145.0,
    "upper_collar_z_min": 72.0,
    "upper_collar_z_max": 100.0,
    "lower_collar_z_min": 0.0,
    "lower_collar_z_max": 28.0,
    "teeth_per_arch": 14,
    "central_incisor_width": 18.0,
    "arch_radius": 52.0,
    "chevron_angle": 72.0,
    "top_hat_tilt": 14.0,
    "labial_inclination": 12.0,
}

ANIMATION = {
    "frame_start": 1,
    "frame_end": 120,
    "fps": 30,
}

# ==================== UTILITIES ====================

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)


def add_material(name, base_color, roughness=0.45, metallic=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def parabolic_arch_point(u, depth=115.0):
    x = 78.0 * math.copysign(1.0, u) * (0.24 * abs(u) + 0.76 * (abs(u) ** 0.80))
    y = depth * (abs(u) ** 1.85)
    return x, y


def set_smooth(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()


def set_flat(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_flat()


# ==================== GEOMETRY GENERATION ====================

def create_gum_arch(is_upper=True):
    name = "UpperGum" if is_upper else "LowerGum"
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()

    z0 = PARAMS["upper_collar_z_min"] if is_upper else PARAMS["lower_collar_z_min"]
    z1 = PARAMS["upper_collar_z_max"] if is_upper else PARAMS["lower_collar_z_max"]

    segs = 32
    ring_a = []
    ring_b = []

    for i in range(segs):
        u = (i / (segs - 1)) * 2.0 - 1.0
        x, y = parabolic_arch_point(u, PARAMS["depth"])
        ring_a.append(bm.verts.new((x, y, z0)))
        ring_b.append(bm.verts.new((x, y, z1)))

    for i in range(segs - 1):
        try:
            bm.faces.new([ring_a[i], ring_a[i + 1], ring_b[i + 1], ring_b[i]])
        except ValueError:
            pass

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return obj


def create_tooth(pos_x, pos_y, z_base, z_top, width=18.0, depth=10.0):
    mesh = bpy.data.meshes.new("Tooth")
    obj = bpy.data.objects.new("Tooth", mesh)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()
    hw = width * 0.5
    hd = depth * 0.5

    v0 = bm.verts.new((pos_x - hw, pos_y - hd, z_base))
    v1 = bm.verts.new((pos_x + hw, pos_y - hd, z_base))
    v2 = bm.verts.new((pos_x + hw, pos_y + hd, z_base))
    v3 = bm.verts.new((pos_x - hw, pos_y + hd, z_base))
    v4 = bm.verts.new((pos_x, pos_y - hd * 0.25, z_top))
    v5 = bm.verts.new((pos_x, pos_y + hd * 0.35, z_top * 0.9))

    faces = [
        [v0, v4, v3],
        [v1, v2, v4],
        [v3, v5, v0],
        [v2, v1, v5],
        [v0, v1, v2, v3],
    ]

    for face in faces:
        try:
            bm.faces.new(face)
        except ValueError:
            pass

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return obj


def create_arch_teeth(is_upper=True):
    out = []
    z_base = PARAMS["upper_collar_z_min"] if is_upper else PARAMS["lower_collar_z_min"]
    z_top = PARAMS["upper_collar_z_max"] if is_upper else PARAMS["lower_collar_z_max"]

    for i in range(PARAMS["teeth_per_arch"]):
        u = (i / (PARAMS["teeth_per_arch"] - 1)) * 2.0 - 1.0
        x, y = parabolic_arch_point(u, PARAMS["depth"])
        scale = 1.0 - abs(u) * 0.28
        w = PARAMS["central_incisor_width"] * scale
        tooth = create_tooth(x, y, z_base, z_top, width=w, depth=10.0)
        out.append(tooth)
    return out


def create_top_hat():
    mesh = bpy.data.meshes.new("TopHat")
    obj = bpy.data.objects.new("TopHat", mesh)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()
    hw = 28.0
    hd = 32.0
    h = 30.0
    z_base = PARAMS["upper_collar_z_max"]

    verts = []
    for sx in (-hw, hw):
        for sy in (-hd, hd):
            verts.append(bm.verts.new((sx, sy, z_base)))

    for sx in (-hw, hw):
        for sy in (-hd, hd):
            verts.append(bm.verts.new((sx + 2.0, sy + 2.0, z_base + h)))

    faces = [
        [verts[0], verts[1], verts[3], verts[2]],
        [verts[4], verts[5], verts[7], verts[6]],
        [verts[0], verts[2], verts[6], verts[4]],
        [verts[1], verts[3], verts[7], verts[5]],
        [verts[0], verts[1], verts[5], verts[4]],
        [verts[2], verts[3], verts[7], verts[6]],
    ]

    for face in faces:
        try:
            bm.faces.new(face)
        except ValueError:
            pass

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return obj


# ==================== ANIMATION ====================

def setup_animation(objects):
    scene = bpy.context.scene
    scene.frame_start = ANIMATION["frame_start"]
    scene.frame_end = ANIMATION["frame_end"]
    scene.render.fps = ANIMATION["fps"]

    for obj in objects:
        obj.rotation_mode = 'XYZ'
        obj.keyframe_insert("rotation_euler", frame=ANIMATION["frame_start"])
        obj.rotation_z = 2 * math.pi
        obj.keyframe_insert("rotation_euler", frame=ANIMATION["frame_end"])

    for fc in scene.objects[0].animation_data.action.fcurves:
        fc.modifiers.new(type='CYCLES')


# ==================== LIGHTING & CAMERA ====================

def setup_lighting_and_camera():
    bpy.ops.object.camera_add(location=(180, -180, 130))
    cam = bpy.context.active_object
    cam.name = "JawCamera"
    cam.rotation_euler = (math.radians(60), 0, math.radians(45))
    bpy.context.scene.camera = cam

    bpy.ops.object.light_add(type='AREA', location=(80, -80, 120))
    key = bpy.context.active_object
    key.name = "KeyLight"
    key.data.energy = 3500
    key.data.angle = math.radians(45)

    bpy.ops.object.light_add(type='AREA', location=(-100, 80, 80))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 1800
    fill.data.angle = math.radians(60)

    bpy.ops.object.light_add(type='SUN', location=(0, 0, 200))
    sky = bpy.context.active_object
    sky.name = "SkyLight"
    sky.data.energy = 1.0


# ==================== RENDER SETTINGS ====================

def setup_render():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_depth = '16'
    scene.eevee.use_gtao = True
    scene.eevee.gtao_distance = 1.0
    scene.eevee.taa_render_samples = 32
    scene.eevee.use_bloom = True
    scene.eevee.bloom_intensity = 0.1
    scene.eevee.bloom_threshold = 0.8


# ==================== MAIN EXECUTION ====================

def main():
    print("=" * 60)
    print("CAINE JAW 3D MODEL GENERATOR - PRODUCTION VERSION")
    print("=" * 60)

    clear_scene()

    materials = {
        "gingiva": add_material("Gingiva", (0.69, 0.73, 0.85, 1.0), 0.45, 0.0),
        "tooth": add_material("Tooth", (0.97, 0.98, 0.99, 1.0), 0.25, 0.05),
        "hat": add_material("Hat", (0.10, 0.12, 0.14, 1.0), 0.6, 0.25),
    }

    print("\n[1/5] Creating gingival collars...")
    upper = create_gum_arch(True)
    lower = create_gum_arch(False)
    upper.data.materials.append(materials["gingiva"])
    lower.data.materials.append(materials["gingiva"])
    set_smooth(upper)
    set_smooth(lower)

    print("[2/5] Creating teeth (upper arch)...")
    upper_teeth = create_arch_teeth(True)
    for obj in upper_teeth:
        obj.data.materials.append(materials["tooth"])
        set_flat(obj)

    print("[3/5] Creating teeth (lower arch)...")
    lower_teeth = create_arch_teeth(False)
    for obj in lower_teeth:
        obj.data.materials.append(materials["tooth"])
        set_flat(obj)

    print("[4/5] Creating top hat accessory...")
    hat = create_top_hat()
    hat.data.materials.append(materials["hat"])
    set_smooth(hat)

    print("[5/5] Setting up camera, lighting, and animation...")
    setup_lighting_and_camera()
    setup_render()

    all_objects = [upper, lower] + upper_teeth + lower_teeth + [hat]
    setup_animation(all_objects)

    print("\n" + "=" * 60)
    print("✓ MODEL GENERATION COMPLETE!")
    print("=" * 60)
    print(f"Total objects: {len(all_objects)}")
    print(f"Animation: {ANIMATION['frame_start']}-{ANIMATION['frame_end']} frames")
    print(f"Export: File → Export as GLB/OBJ")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
