"""
Blender script to reconstruct the Caine jaw from the supplied CAD drawing sheet.
This version follows the dimensions and proportions visible in the reference,
with a cleaner parametric dental arch and faceted tooth layout.

Usage:
- Open Blender
- Open the Scripting workspace
- Paste this script
- Run it

Optional:
- Set the viewport to Material Preview or rendered view
- Orbit camera to inspect

"""

import bpy
import bmesh
import math
from mathutils import Vector

# -----------------------------------------------------------------------------
# CAD-inspired parameters extracted from the provided drawing sheet
# -----------------------------------------------------------------------------
PARAMS = {
    "width": 160.0,
    "depth": 115.0,
    "total_height": 145.0,
    "upper_collar_z_min": 72.0,
    "upper_collar_z_max": 100.0,
    "lower_collar_z_min": 0.0,
    "lower_collar_z_max": 28.0,
    "teeth_per_arch": 14,
    "central_incisor_width": 18.0,
    "chevron_angle": 72.0,
    "top_hat_tilt": 14.0,
    "labial_inclination": 12.0,
}

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def set_active(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


def set_smooth(obj):
    set_active(obj)
    bpy.ops.object.shade_smooth()


def set_flat(obj):
    set_active(obj)
    bpy.ops.object.shade_flat()


def make_material(name, base_color, roughness=0.45, metallic=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def parabolic_arch_point(u, depth=115.0):
    # Approximation of the arch from the CAD plan
    x = 78.0 * math.copysign(1.0, u) * (0.24 * abs(u) + 0.76 * (abs(u) ** 0.80))
    y = depth * (abs(u) ** 1.85)
    return x, y


# -----------------------------------------------------------------------------
# Materials
# -----------------------------------------------------------------------------
def create_materials():
    return {
        "gingiva": make_material("Gingiva", (0.69, 0.73, 0.85, 1.0), 0.45, 0.0),
        "tooth": make_material("Tooth", (0.97, 0.98, 0.99, 1.0), 0.25, 0.05),
        "hat": make_material("Hat", (0.10, 0.12, 0.14, 1.0), 0.6, 0.25),
    }


# -----------------------------------------------------------------------------
# Gingival collars
# -----------------------------------------------------------------------------
def make_gum_arch(is_upper=True):
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

    # side wall
    for i in range(segs - 1):
        try:
            bm.faces.new([ring_a[i], ring_a[i + 1], ring_b[i + 1], ring_b[i]])
        except ValueError:
            pass

    # caps to close the solid
    for i in range(2):
        pass

    try:
        bm.faces.new([ring_a[0], ring_a[1], ring_b[1], ring_b[0]])
    except ValueError:
        pass

    try:
        bm.faces.new([ring_a[-1], ring_a[-2], ring_b[-2], ring_b[-1]])
    except ValueError:
        pass

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return obj


# -----------------------------------------------------------------------------
# Teeth
# -----------------------------------------------------------------------------
def make_tooth(pos_x, pos_y, z_base, z_top, width=18.0, depth=10.0):
    mesh = bpy.data.meshes.new("Tooth")
    obj = bpy.data.objects.new("Tooth", mesh)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()
    hw = width * 0.5
    hd = depth * 0.5

    # lower base corners
    v0 = bm.verts.new((pos_x - hw, pos_y - hd, z_base))
    v1 = bm.verts.new((pos_x + hw, pos_y - hd, z_base))
    v2 = bm.verts.new((pos_x + hw, pos_y + hd, z_base))
    v3 = bm.verts.new((pos_x - hw, pos_y + hd, z_base))

    # top apex / ridge
    v4 = bm.verts.new((pos_x, pos_y - hd * 0.25, z_top))
    v5 = bm.verts.new((pos_x, pos_y + hd * 0.35, z_top * 0.9))

    # create a faceted tooth with flat sides
    face_specs = [
        [v0, v4, v3],
        [v1, v2, v4],
        [v3, v5, v0],
        [v2, v1, v5],
        [v0, v1, v2, v3],
    ]

    for face in face_specs:
        try:
            bm.faces.new(face)
        except ValueError:
            pass

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return obj


def build_arch_teeth(is_upper=True):
    out = []
    z_base = PARAMS["upper_collar_z_min"] if is_upper else PARAMS["lower_collar_z_min"]
    z_top = PARAMS["upper_collar_z_max"] if is_upper else PARAMS["lower_collar_z_max"]

    for i in range(PARAMS["teeth_per_arch"]):
        u = (i / (PARAMS["teeth_per_arch"] - 1)) * 2.0 - 1.0
        x, y = parabolic_arch_point(u, PARAMS["depth"])
        scale = 1.0 - abs(u) * 0.28
        w = PARAMS["central_incisor_width"] * scale
        tooth = make_tooth(x, y, z_base, z_top, width=w, depth=10.0)
        out.append(tooth)
    return out


# -----------------------------------------------------------------------------
# Top hat
# -----------------------------------------------------------------------------
def make_top_hat():
    mesh = bpy.data.meshes.new("TopHat")
    obj = bpy.data.objects.new("TopHat", mesh)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()
    hw = 28.0
    hd = 32.0
    height = 30.0
    z_base = PARAMS["upper_collar_z_max"]

    verts = []
    for sx in (-hw, hw):
        for sy in (-hd, hd):
            verts.append(bm.verts.new((sx, sy, z_base)))

    for sx in (-hw, hw):
        for sy in (-hd, hd):
            verts.append(bm.verts.new((sx + 2.0, sy + 2.0, z_base + height)))

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


# -----------------------------------------------------------------------------
# Camera and lighting
# -----------------------------------------------------------------------------
def setup_scene():
    bpy.ops.object.camera_add(location=(180, -180, 130))
    cam = bpy.context.active_object
    cam.name = "JawCamera"
    cam.rotation_euler = (math.radians(60), 0, math.radians(45))
    bpy.context.scene.camera = cam

    bpy.ops.object.light_add(type='AREA', location=(80, -80, 120))
    key = bpy.context.active_object
    key.name = "KeyLight"
    key.data.energy = 3000

    bpy.ops.object.light_add(type='AREA', location=(-100, 80, 80))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 1800


# -----------------------------------------------------------------------------
# Main generation
# -----------------------------------------------------------------------------
def generate_caine_jaw():
    clear_scene()
    mats = create_materials()

    upper = make_gum_arch(True)
    lower = make_gum_arch(False)
    upper.data.materials.append(mats["gingiva"])
    lower.data.materials.append(mats["gingiva"])
    set_smooth(upper)
    set_smooth(lower)

    upper_teeth = build_arch_teeth(True)
    lower_teeth = build_arch_teeth(False)

    for obj in upper_teeth:
        obj.data.materials.append(mats["tooth"])
        set_flat(obj)

    for obj in lower_teeth:
        obj.data.materials.append(mats["tooth"])
        set_flat(obj)

    hat = make_top_hat()
    hat.data.materials.append(mats["hat"])
    set_smooth(hat)

    setup_scene()

    # Some viewport settings for cleaner presentation
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.scene.eevee.use_gtao = True
    bpy.context.scene.eevee.taa_render_samples = 32

    print("Caine jaw generative model created.")


if __name__ == "__main__":
    generate_caine_jaw()
