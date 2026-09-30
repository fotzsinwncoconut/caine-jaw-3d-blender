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
    """Create gingival collar (upper or lower)"""
    
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
    
    # Create vertices for parabolic collar
    verts = []
    segments = 32
    
    for i in range(segments):
        u = (i / (segments - 1)) * 2 - 1
        x, y = parabolic_arch_curve(u, params["depth"], params["width"])
        
        # Base ring
        verts.append(bm.verts.new((x, y, z_base)))
        # Top ring
        verts.append(bm.verts.new((x, y, z_top)))
    
    # Create faces
    for i in range(segments - 1):
        v0_base = verts[i * 2]
        v0_top = verts[i * 2 + 1]
        v1_base = verts[(i + 1) * 2]
        v1_top = verts[(i + 1) * 2 + 1]
        
        bm.faces.new([v0_base, v1_base, v1_top, v0_top])
    
    # Cap ends with triangles
    if is_upper:
        # Create chevron notch at center
        center_verts = []
        for z in [z_base, z_top]:
            center_verts.append(bm.verts.new((0, 0, z)))
        
        # Connect to arch for chevron effect
        angle_rad = math.radians(params["chevron_angle"] / 2)
        chevron_depth = 15.0
        chevron_vert = bm.verts.new((0, -chevron_depth, (z_base + z_top) / 2))
        
        for v in center_verts:
            bm.faces.new([v, center_verts[0] if v.co.z == z_base else center_verts[1], chevron_vert])
    
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
    # Labial surface bisected into 4 kite facets
    verts = [
        # Base corners
        bm.verts.new((x_center - half_w, y_pos - half_d, z_base)),  # 0: BL
        bm.verts.new((x_center + half_w, y_pos - half_d, z_base)),  # 1: BR
        bm.verts.new((x_center + half_w, y_pos + half_d, z_base)),  # 2: BR-post
        bm.verts.new((x_center - half_w, y_pos + half_d, z_base)),  # 3: BL-post
        
        # Apex (cusp)
        bm.verts.new((x_center, y_pos - half_d * 0.5, z_top)),      # 4: apex labial
        
        # Central ridge (lingual)
        bm.verts.new((x_center, y_pos + half_d * 0.3, z_top * 0.8)), # 5: lingual crest
    ]
    
    # Create facets
    # Labial mesial
    bm.faces.new([verts[0], verts[4], verts[5]])
    # Labial distal
    bm.faces.new([verts[1], verts[4], verts[5]])
    # Lingual mesial
    bm.faces.new([verts[3], verts[5], verts[0]])
    # Lingual distal
    bm.faces.new([verts[2], verts[5], verts[1]])
    # Base faces
    bm.faces.new([verts[0], verts[1], verts[2], verts[3]])
    
    bm.to_mesh(mesh)
    bm.free()
    
    mesh.update()
    obj.shade_flat()  # Keep faceted appearance
    
    return obj

def create_dentition(params):
    """Create all teeth (upper and lower arches)"""
    
    teeth_objects = []
    
    for arch_idx in range(2):  # 0=upper, 1=lower
        is_upper = (arch_idx == 0)
        z_base = params["upper_collar_z_min"] if is_upper else params["lower_collar_z_min"]
        z_top = params["upper_collar_z_max"] if is_upper else params["lower_collar_z_max"]
        
        # Distribute teeth along arch
        for tooth_idx in range(params["teeth_per_arch"]):
            u = (tooth_idx / (params["teeth_per_arch"] - 1)) * 2 - 1
            x_center, y_pos = parabolic_arch_curve(u, params["depth"], params["width"])
            
            tooth = create_tooth(
                x_center=x_center,
                y_pos=y_pos,
                z_base=z_base,
                z_top=z_top,
                width=params["central_incisor_width"] * 0.8,
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
    
    # Simple cube top hat perched on upper collar
    hat_width = 40.0
    hat_depth = 50.0
    hat_height = 35.0
    z_mount = params["upper_collar_z_max"]
    
    # Tilt angle
    tilt_rad = math.radians(params["top_hat_tilt"])
    
    verts = []
    
    # Base (at mount point)
    for x in [-hat_width/2, hat_width/2]:
        for y in [0, hat_depth]:
            verts.append(bm.verts.new((x, y, z_mount)))
    
    # Top (tilted)
    for x in [-hat_width/2, hat_width/2]:
        for y in [0, hat_depth]:
            z_offset = hat_height * math.cos(tilt_rad)
            x_offset = hat_height * math.sin(tilt_rad)
            verts.append(bm.verts.new((x + x_offset, y, z_mount + z_offset)))
    
    # Create cube faces
    # Bottom
    bm.faces.new([verts[0], verts[1], verts[3], verts[2]])
    # Top
    bm.faces.new([verts[4], verts[6], verts[7], verts[5]])
    # Sides
    bm.faces.new([verts[0], verts[4], verts[5], verts[1]])
    bm.faces.new([verts[2], verts[3], verts[7], verts[6]])
    bm.faces.new([verts[0], verts[2], verts[6], verts[4]])
    bm.faces.new([verts[1], verts[5], verts[7], verts[3]])
    
    bm.to_mesh(mesh)
    bm.free()
    
    mesh.update()
    obj.shade_smooth()
    
    return obj

# ============================================================================
# MAIN GENERATION FUNCTION
# ============================================================================

def generate_caine_jaw():
    """Main function: Generate complete Caine jaw assembly"""
    
    # Clear existing mesh objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Create materials
    materials = create_materials()
    
    # Create assembly collection
    caine_collection = bpy.data.collections.new("CaineJawAssembly")
    bpy.context.scene.collection.children.link(caine_collection)
    
    print("🦷 Generating Caine Jaw 3D Model...")
    print(f"   Parameters: {PARAMS['width']}mm × {PARAMS['depth']}mm × {PARAMS['total_height']}mm")
    
    # Create upper and lower collars (gingiva)
    upper_collar = create_gingival_collar(PARAMS, is_upper=True)
    lower_collar = create_gingival_collar(PARAMS, is_upper=False)
    
    upper_collar.data.materials.append(materials["gingiva"])
    lower_collar.data.materials.append(materials["gingiva"])
    
    bpy.context.collection.objects.unlink(upper_collar)
    bpy.context.collection.objects.unlink(lower_collar)
    caine_collection.objects.link(upper_collar)
    caine_collection.objects.link(lower_collar)
    
    # Create dentition
    teeth = create_dentition(PARAMS)
    for tooth in teeth:
        tooth.data.materials.append(materials["tooth"])
        bpy.context.collection.objects.unlink(tooth)
        caine_collection.objects.link(tooth)
    
    # Create top hat
    top_hat = create_top_hat(PARAMS)
    top_hat.data.materials.append(materials["hat"])
    bpy.context.collection.objects.unlink(top_hat)
    caine_collection.objects.link(top_hat)
    
    # Set up camera for isometric view
    bpy.ops.object.camera_add(
        location=(
            100 * math.cos(math.radians(PARAMS["isometric_azimuth"])),
            100 * math.sin(math.radians(PARAMS["isometric_azimuth"])),
            80
        )
    )
    camera = bpy.context.active_object
    camera.name = "IsometricCamera"
    camera.rotation_euler = (
        math.radians(90 - PARAMS["isometric_elevation"]),
        0,
        math.radians(PARAMS["isometric_azimuth"])
    )
    bpy.context.scene.camera = camera
    bpy.context.collection.objects.unlink(camera)
    caine_collection.objects.link(camera)
    
    # Add lighting
    bpy.ops.object.light_add(type='SUN', location=(100, 100, 150))
    sun = bpy.context.active_object
    sun.data.energy = 2.0
    bpy.context.collection.objects.unlink(sun)
    caine_collection.objects.link(sun)
    
    print(f"✓ Created gingival collars (upper + lower)")
    print(f"✓ Created {len(teeth)} teeth")
    print(f"✓ Created top hat assembly")
    print(f"✓ Set up isometric camera and lighting")
    print("\n🎬 Ready for animation!")

# ============================================================================
# EXECUTE
# ============================================================================

if __name__ == "__main__":
    generate_caine_jaw()
