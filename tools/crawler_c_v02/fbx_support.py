import numpy as np

def noise(size, cells, rng):
    grid = rng.random((cells, cells), dtype=np.float32)
    p = np.arange(size, dtype=np.float32) * cells / size
    a = p.astype(np.int32)
    f = p - a
    f = f * f * (3 - 2 * f)
    b = (a + 1) % cells
    lo = grid[a[:, None], a] * (1 - f) + grid[a[:, None], b] * f
    hi = grid[b[:, None], a] * (1 - f) + grid[b[:, None], b] * f
    return lo * (1 - f[:, None]) + hi * f[:, None]


def install_pbr_export():
    # ufbx's Blender PBR interpretation is opt-in and is not enabled by MyEngine.
    # Export the supported physical-material descriptor, retaining legacy texture links.
    # This patches only this process; Blender and engine installation files are untouched.
    from io_scene_fbx import export_fbx_bin as fbx
    from io_scene_fbx.fbx_utils import elem_props_set
    if getattr(fbx.fbx_data_material_elements, "lab_pbr", False):
        return
    original=fbx.fbx_data_material_elements
    def export_material(root, mat, scene_data):
        original(root, mat, scene_data)
        element=root.elems[-1]
        assert element.id==b"Material"
        props=next(e for e in element.elems if e.id==b"Properties70")
        for e in element.elems:
            if e.id==b"ShadingModel":
                e.props.clear()
                e.props_type.clear()
                e.add_string(b"PhysicalMaterial")
        for p in props.elems:
            if p.id==b"P" and p.props[0][4:]==b"ShadingModel":
                p.props.pop()
                p.props_type.pop()
                p.add_string(b"PhysicalMaterial")
        bsdf=mat.node_tree.nodes["Principled BSDF"]
        elem_props_set(props,"p_integer",b"3dsMax|ClassIDa",0x3d6b1cec)
        elem_props_set(props,"p_integer",b"3dsMax|ClassIDb",0xdeadc001-0x100000000)
        prefix=b"3dsMax|Parameters|"
        elem_props_set(props,"p_color",prefix+b"base_color",(1.,1.,1.))
        for key,value in [(b"base_weight",1.),(b"metalness",bsdf.inputs["Metallic"].default_value),
                          (b"roughness",bsdf.inputs["Roughness"].default_value),
                          (b"cutout",bsdf.inputs["Alpha"].default_value)]:
            elem_props_set(props,"p_number",prefix+key,value)
    export_material.lab_pbr=True
    fbx.fbx_data_material_elements=export_material

