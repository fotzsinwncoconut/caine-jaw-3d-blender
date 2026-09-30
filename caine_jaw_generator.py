"""
Caine Jaw 3D Model Generator for Blender
Reverse-engineered from CAD drawing: CAD-REV-DENT-089-A
Creates parametric biomechanical dental arch assembly
"""

import bpy
import bmesh
import math
from mathutils import Vector, Matrix

# ============================================================================
# DIMENSIONAL PARAMETERS (all in mm)
# ============================================================================

PARAMS = {
    # Assembly dimensions
    "width": 160.0,           # Overall X
    "depth": 115.0,           # Overall Y
    "arch_height": 100.0,     # Z from base to dorsal
    "total_height": 145.0,    # Including top hat
    
    # Gingival collars
    "upper_collar_z_min": 72.0,
    "upper_collar_z_max": 100.0,
    "lower_collar_z_min": 0.0,
    "lower_collar_z_max": 28.0,
    
    # Dentition
    "dentition_exposure": 44.0,
    "intercanine_width": 88.0,
    "central_incisor_width": 18.0,
    "arch_radius": 52.0,
    "wall_thickness": 24.0,
    "tooth_protrusion": 9.2,
    
    # Angles
    "labial_inclination": 12.0,      # degrees
    "chevron_angle": 72.0,           # degrees
    "top_hat_tilt": 14.0,            # degrees
    "isometric_azimuth": 40.0,       # degrees
    "isometric_elevation": 28.0,     # degrees
    
    # Tooth count
    "teeth_per_arch": 14,
    "total_teeth": 28,
}

# ============================================================================
# MATERIALS
# ============================================================================

def create_materials():
    """Create gingiva and tooth materials"""
    
    # Gingiva material (pale periwinkle)
    gingiva_mat = bpy.data.materials.new(name="Gingiva")
    gingiva_mat.use_nodes = True
    bsdf = gingiva_mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.69, 0.73, 0.85, 1.0)  # #B0B9D8
    bsdf.inputs['Roughness'].default_value = 0.4
    
    # Tooth material (off-white faceted)
    tooth_mat = bpy.data.materials.new(name="Teeth")
    tooth_mat.use_nodes = True
    bsdf = tooth_mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.97, 0.98, 0.99, 1.0)  # #F8FAFC
    bsdf.inputs['Roughness'].default_value = 0.3
    bsdf.inputs['Metallic'].default_value = 0.1
    
    # Top hat material (dark graphite)
    hat_mat = bpy.data.materials.new(name="TopHat")
    hat_mat.use_nodes = True
    bsdf = hat_mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.1, 0.12, 0.15, 1.0)  # #1A1F26
    bsdf.inputs['Roughness'].default_value = 0.6
    
    return {"gingiva": gingiva_mat, "tooth": tooth_mat, "hat": hat_mat}

# ============================================================================
# ARCH GEOMETRY
# ============================================================================

def parabolic_arch_curve(u, depth=115.0, width=160.0):
    """
    Generate parabolic arch curve point
    u: parameter in [-1, 1]
    Returns (x, y) coordinates
    """
    x = 78.0 * math.copysign(1, u) * (0.24 * abs(u) + 0.76 * pow(abs(u), 0.80))
    y = depth * pow(abs(u), 1.85)
    return (x, y)

def create_gingival_collar(params, is_upper=True):
    """Create gingival collar (upper or lower) - improved geometry"""
    
    mesh = bpy.data.meshes.new("GingivalCollar_U" if is_upper else "GingivalCollar_L")
    obj = bpy.data.objects.new("GingivalCollar_U" if is_upper else "GingivalCollar_L", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    if is_upper:
        z_base = params["upper_collar_z_min"]
        z_top = params["upper_collar_z_max"]
    else:
        z_base = params["lower_collar_z_min"]
        z_top = params["lower_collar_z_max"]
    
    segments = 32
    verts_base = []
    verts_top = []
    
    # Create base and top rings
    for i in range(segments):
        u = (i / (segments - 1)) * 2 - 1
        x, y = parabolic_arch_curve(u, params["depth"], params["width"])
        
        verts_base.append(bm.verts.new((x, y, z_base)))
        verts_top.append(bm.verts.new((x, y, z_top)))
    
    # Create side faces (quads)
    for i in range(segments - 1):
        bm.faces.new([
            verts_base[i], 
            verts_base[i + 1], 
            verts_top[i + 1], 
            verts_top[i]
        ])
    
    # Cap the ends with triangles
    # Front cap
    bm.faces.new([verts_base[0], verts_top[0], verts_base[1]])
    bm.faces.new([verts_top[0], verts_top[1], verts_base[1]])
    
    # Back cap
    bm.faces.new([verts_base[-1], verts_base[-2], verts_top[-1]])
    bm.faces.new([verts_base[-2], verts_top[-2], verts_top[-1]])
    
    bm.to_mesh(mesh)
    bm.free()
    
    mesh.update()
    obj.shade_smooth()
    
    return obj

def create_tooth(x_center, y_pos, z_base, z_top, width=18.0, depth=12.0):
    """Create a single faceted tooth (diamond shape)"""
    
    mesh = bpy.data.meshes.new("Tooth")
    obj = bpy.data.objects.new("Tooth", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    half_w = width / 2
    half_d = depth / 2
    
    # Create diamond faceted tooth geometry
    verts = [
        # Base corners
        bm.verts.new((x_center - half_w, y_pos - half_d, z_base)),  # 0: BL
        bm.verts.new((x_center + half_w, y_pos - half_d, z_base)),  # 1: BR
        bm.verts.new((x_center + half_w, y_pos + half_d, z_base)),  # 2: BR-post
        bm.verts.new((x_center - half_w, y_pos + half_d, z_base)),  # 3: BL-post
        
        # Apex (cusp)
        bm.verts.new((x_center, y_pos - half_d * 0.3, z_top)),      # 4: apex labial
        
        # Lingual crest
        bm.verts.new((x_center, y_pos + half_d * 0.2, z_top * 0.85)), # 5: lingual crest
    ]
    
    # Create facets (avoid duplicate verts)
    # Mesial labial face
    bm.faces.new([verts[0], verts[4], verts[3]])
    # Distal labial face
    bm.faces.new([verts[1], verts[2], verts[4]])
    # Mesial lingual face
    bm.faces.new([verts[3], verts[5], verts[0]])
    # Distal lingual face
    bm.faces.new([verts[2], verts[1], verts[5]])
    # Base face
    bm.faces.new([verts[0], verts[1], verts[2], verts[3]])
    # Apex to lingual
    bm.faces.new([verts[4], verts[5], verts[4]])
    
    bm.to_mesh(mesh)
    bm.free()
    
    mesh.update()
    obj.shade_flat()
    
    return obj

def create_dentition(params):
    """Create all teeth (upper and lower arches)"""
    
    teeth_objects = []
    
    for arch_idx in range(2):  # 0=upper, 1=lower
        is_upper = (arch_idx == 0)
        z_base = params["upper_collar_z_min"] if is_upper else params["lower_collar_z_min"]
        z_top = params["upper_collar_z_max"] if is_upper else params["lower_collar_z_max"]
        z_center = (z_base + z_top) / 2
        
        # Distribute teeth along arch
        for tooth_idx in range(params["teeth_per_arch"]):
            u = (tooth_idx / (params["teeth_per_arch"] - 1)) * 2 - 1
            x_center, y_pos = parabolic_arch_curve(u, params["depth"], params["width"])
            
            # Scale tooth size - smaller towards back
            size_scale = 1.0 - abs(u) * 0.3
            tooth_width = params["central_incisor_width"] * size_scale
            
            tooth = create_tooth(
                x_center=x_center,
                y_pos=y_pos,
                z_base=z_base,
                z_top=z_top,
                width=tooth_width,
                depth=10.0
            )
            teeth_objects.append(tooth)
    
    return teeth_objects

def create_top_hat(params):
    """Create top hat accessory assembly"""
    
    mesh = bpy.data.meshes.new("TopHat")
    obj = bpy.data.objects.new("TopHat", mesh)
    bpy.context.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    hat_width = 40.0
    hat_depth = 50.0
    hat_height = 35.0
    z_mount = params["upper_collar_z_max"]
    
    tilt_rad = math.radians(params["top_hat_tilt"])
    
    verts = []
    
    # Base ring (at mount point)
    for x in [-hat_width/2, hat_width/2]:
        for y in [0, hat_depth]:
            verts.append(bm.verts.new((x, y, z_mount)))
    
    # Top ring (tilted)
    for x in [-hat_width/2, hat_width/2]:
        for y in [0, hat_depth]:
            z_offset = hat_height * math.cos(tilt_rad)
            x_offset = hat_height * math.sin(tilt_rad) * 0.3
            verts.append(bm.verts.new((x + x_offset, y, z_mount + z_offset)))
    
    # Create cube faces (6 faces for rectangular prism)
    # Bottom
    bm.faces.new([verts[0], verts[2], verts[3], verts[1]])
    # Top
    bm.faces.new([verts[4], verts[5], verts[7], verts[6]])
    # Front
    bm.faces.new([verts[0], verts[1], verts[5], verts[4]])
    # Back
    bm.faces.new([verts[2], verts[6], verts[7], verts[3]])
    # Left
    bm.faces.new([verts[0], verts[4], verts[6], verts[2]])
    # Right
    bm.faces.new([verts[1], verts[3], verts[7], verts[5]])
    
    bm.to_mesh(mesh)
    bm.free()
    
    mesh.update()
    obj.shade_smooth()
    
    return obj

def create_camera_and_lights(params):
    """Set up camera and lighting for isometric view"""
    
    # Camera
    bpy.ops.object.camera_add()
    camera = bpy.context.active_object
    camera.name = "IsometricCamera"
    
    dist = 250
    az_rad = math.radians(params["isometric_azimuth"])
    el_rad = math.radians(params["isometric_elevation"])
    
    camera.location = (
        dist * math.cos(az_rad) * math.cos(el_rad),
        dist * math.sin(az_rad) * math.cos(el_rad),
        dist * math.sin(el_rad)
    )
    
    # Point camera at origin
    direction = Vector(camera.location).normalized() * -1
    camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    
    bpy.context.scene.camera = camera
    
    # Sun light
    bpy.ops.object.light_add(type='SUN', location=(150, 150, 200))
    sun = bpy.context.active_object
    sun.name = "SunLight"
    sun.data.energy = 2.5
    sun.data.angle = math.radians(15)
    
    # Ambient light
    bpy.ops.object.light_add(type='SUN', location=(-100, -100, 100))
    ambient = bpy.context.active_object
    ambient.name = "AmbientLight"
    ambient.data.energy = 0.8
    
    return camera, sun, ambient

# ============================================================================
# MAIN GENERATION FUNCTION
# ============================================================================

def generate_caine_jaw():
    """Main function: Generate complete Caine jaw assembly"""
    
    # Clear existing mesh objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Recreate default camera
    bpy.ops.object.camera_add(location=(7.4, -7.4, 6.5))
    
    # Create materials
    materials = create_materials()
    
    # Create assembly collection
    caine_collection = bpy.data.collections.new("CaineJawAssembly")
    bpy.context.scene.collection.children.link(caine_collection)
    
    print("=" * 70)
    print("🦷 CAINE JAW 3D MODEL GENERATOR")
    print("=" * 70)
    print(f"Dimensions: {PARAMS['width']}mm × {PARAMS['depth']}mm × {PARAMS['total_height']}mm")
    print(f"Teeth: {PARAMS['total_teeth']} ({PARAMS['teeth_per_arch']} per arch)")
    print()
    
    # Create gingival collars
    print("Creating gingival collars...")
    upper_collar = create_gingival_collar(PARAMS, is_upper=True)
    lower_collar = create_gingival_collar(PARAMS, is_upper=False)
    
    upper_collar.data.materials.append(materials["gingiva"])
    lower_collar.data.materials.append(materials["gingiva"])
    
    bpy.context.collection.objects.unlink(upper_collar)
    bpy.context.collection.objects.unlink(lower_collar)
    caine_collection.objects.link(upper_collar)
    caine_collection.objects.link(lower_collar)
    print("  ✓ Upper collar")
    print("  ✓ Lower collar")
    
    # Create dentition
    print("Creating dentition...")
    teeth = create_dentition(PARAMS)
    for i, tooth in enumerate(teeth):
        tooth.data.materials.append(materials["tooth"])
        bpy.context.collection.objects.unlink(tooth)
        caine_collection.objects.link(tooth)
    print(f"  ✓ {len(teeth)} teeth created")
    
    # Create top hat
    print("Creating top hat assembly...")
    top_hat = create_top_hat(PARAMS)
    top_hat.data.materials.append(materials["hat"])
    bpy.context.collection.objects.unlink(top_hat)
    caine_collection.objects.link(top_hat)
    print("  ✓ Top hat")
    
    # Set up camera and lights
    print("Setting up camera and lights...")
    camera, sun, ambient = create_camera_and_lights(PARAMS)
    bpy.context.collection.objects.unlink(camera)
    bpy.context.collection.objects.unlink(sun)
    bpy.context.collection.objects.unlink(ambient)
    caine_collection.objects.link(camera)
    caine_collection.objects.link(sun)
    caine_collection.objects.link(ambient)
    print("  ✓ Isometric camera")
    print("  ✓ Sun light")
    print("  ✓ Ambient light")
    
    # Set viewport shading to Material Preview
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
    
    print()
    print("=" * 70)
    print("✓ MODEL GENERATION COMPLETE!")
    print("=" * 70)
    print("\n💡 Tips for animation:")
    print("  1. Select the CaineJawAssembly collection")
    print("  2. Use Rotation keyframes for 360° spin")
    print("  3. Add Zoom keyframes with the camera")
    print("  4. Render at 1080p or 4K for best quality")
    print()

# ============================================================================
# EXECUTE
# ============================================================================

if __name__ == "__main__":
    generate_caine_jaw()
