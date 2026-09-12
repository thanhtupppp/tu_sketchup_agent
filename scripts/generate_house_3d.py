"""
Enhanced Generator for Nha Cap 4 (11.5m x 20.5m) 3D Architectural Model.
Supports modular export:
- Body: Foundation, Columns, Walls, Doors, Windows, Pavement
- Roof: Main Pitched Roof, Front Porch Gable Roof, Side Porch Roof, Fascia Trims
This enables instant architectural cutaway floor plan views in SketchUp!
"""

import math
import os
import sys

def generate_dae_xml(geoms_subset, output_path: str):
    materials_def = {
        "Roof_Tile":    {"diffuse": [0.17, 0.24, 0.31, 1.0], "specular": [0.15, 0.15, 0.15, 1.0], "shininess": 15}, # Dark slate blue
        "Ridge_Cap":    {"diffuse": [0.12, 0.18, 0.24, 1.0], "specular": [0.25, 0.25, 0.25, 1.0], "shininess": 25},
        "Wall_Mat":     {"diffuse": [0.96, 0.96, 0.94, 1.0], "specular": [0.05, 0.05, 0.05, 1.0], "shininess": 5},  # Off-white
        "Wall_Accent":  {"diffuse": [0.86, 0.88, 0.88, 1.0], "specular": [0.1, 0.1, 0.1, 1.0], "shininess": 10},
        "Plinth_Mat":   {"diffuse": [0.36, 0.43, 0.49, 1.0], "specular": [0.15, 0.15, 0.15, 1.0], "shininess": 15}, # Granite
        "Porch_Stone":  {"diffuse": [0.20, 0.29, 0.37, 1.0], "specular": [0.25, 0.25, 0.25, 1.0], "shininess": 30}, # Dark granite steps
        "Floor_Tile":   {"diffuse": [0.92, 0.93, 0.94, 1.0], "specular": [0.4, 0.4, 0.4, 1.0], "shininess": 60},
        "Column_Mat":   {"diffuse": [0.97, 0.97, 0.98, 1.0], "specular": [0.2, 0.2, 0.2, 1.0], "shininess": 30},
        "Door_Wood":    {"diffuse": [0.29, 0.18, 0.09, 1.0], "specular": [0.15, 0.15, 0.15, 1.0], "shininess": 20}, # Walnut wood
        "Glass_Mat":    {"diffuse": [0.36, 0.68, 0.89, 0.45], "specular": [0.9, 0.9, 0.9, 1.0], "shininess": 90, "transparent": True},
        "Gold_Handle":  {"diffuse": [0.85, 0.72, 0.30, 1.0], "specular": [0.9, 0.85, 0.5, 1.0], "shininess": 100}, # Gold hardware
        "Fascia_White": {"diffuse": [0.98, 0.98, 0.98, 1.0], "specular": [0.1, 0.1, 0.1, 1.0], "shininess": 10},
        "Pavement_Mat": {"diffuse": [0.75, 0.75, 0.73, 1.0], "specular": [0.05, 0.05, 0.05, 1.0], "shininess": 5}
    }

    xml_lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">',
        '  <asset>',
        '    <contributor><authoring_tool>TuSketchupAgent 3D Architect Pro</authoring_tool></contributor>',
        '    <unit name="meter" meter="1.0"/>',
        '    <up_axis>Z_UP</up_axis>',
        '  </asset>',
        '  <library_effects>'
    ]

    for mat_id, prop in materials_def.items():
        diff = prop["diffuse"]
        spec = prop["specular"]
        shin = prop["shininess"]
        trans = prop.get("transparent", False)
        xml_lines.append(f'    <effect id="{mat_id}-effect">')
        xml_lines.append('      <profile_COMMON>')
        xml_lines.append('        <technique sid="common">')
        xml_lines.append('          <phong>')
        xml_lines.append(f'            <diffuse><color>{diff[0]} {diff[1]} {diff[2]} {diff[3]}</color></diffuse>')
        xml_lines.append(f'            <specular><color>{spec[0]} {spec[1]} {spec[2]} {spec[3]}</color></specular>')
        xml_lines.append(f'            <shininess><float>{shin}</float></shininess>')
        if trans:
            xml_lines.append('            <transparency><float>0.45</float></transparency>')
        xml_lines.append('          </phong>')
        xml_lines.append('        </technique>')
        xml_lines.append('      </profile_COMMON>')
        xml_lines.append('    </effect>')
    xml_lines.append('  </library_effects>')

    xml_lines.append('  <library_materials>')
    for mat_id in materials_def.keys():
        xml_lines.append(f'    <material id="{mat_id}-material" name="{mat_id}">')
        xml_lines.append(f'      <instance_effect url="#{mat_id}-effect"/>')
        xml_lines.append('    </material>')
    xml_lines.append('  </library_materials>')

    xml_lines.append('  <library_geometries>')
    for gname, tri_list in geoms_subset.items():
        if not tri_list:
            continue
        
        pos_array = []
        norm_array = []
        mat_tris = {}
        for (p0, p1, p2, norm, mat) in tri_list:
            if mat not in mat_tris:
                mat_tris[mat] = []
            
            idx0 = len(pos_array) // 3
            pos_array.extend([round(p0[0], 4), round(p0[1], 4), round(p0[2], 4)])
            norm_array.extend([round(norm[0], 3), round(norm[1], 3), round(norm[2], 3)])
            
            idx1 = len(pos_array) // 3
            pos_array.extend([round(p1[0], 4), round(p1[1], 4), round(p1[2], 4)])
            norm_array.extend([round(norm[0], 3), round(norm[1], 3), round(norm[2], 3)])
            
            idx2 = len(pos_array) // 3
            pos_array.extend([round(p2[0], 4), round(p2[1], 4), round(p2[2], 4)])
            norm_array.extend([round(norm[0], 3), round(norm[1], 3), round(norm[2], 3)])
            
            mat_tris[mat].append((idx0, idx1, idx2))

        vtx_count = len(pos_array) // 3
        pos_str = " ".join(str(v) for v in pos_array)
        norm_str = " ".join(str(v) for v in norm_array)

        xml_lines.append(f'    <geometry id="{gname}-geom" name="{gname}">')
        xml_lines.append('      <mesh>')
        xml_lines.append(f'        <source id="{gname}-pos">')
        xml_lines.append(f'          <float_array id="{gname}-pos-array" count="{len(pos_array)}">{pos_str}</float_array>')
        xml_lines.append('          <technique_common>')
        xml_lines.append(f'            <accessor source="#{gname}-pos-array" count="{vtx_count}" stride="3">')
        xml_lines.append('              <param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/>')
        xml_lines.append('            </accessor>')
        xml_lines.append('          </technique_common>')
        xml_lines.append('        </source>')
        xml_lines.append(f'        <source id="{gname}-norm">')
        xml_lines.append(f'          <float_array id="{gname}-norm-array" count="{len(norm_array)}">{norm_str}</float_array>')
        xml_lines.append('          <technique_common>')
        xml_lines.append(f'            <accessor source="#{gname}-norm-array" count="{vtx_count}" stride="3">')
        xml_lines.append('              <param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/>')
        xml_lines.append('            </accessor>')
        xml_lines.append('          </technique_common>')
        xml_lines.append('        </source>')
        xml_lines.append(f'        <vertices id="{gname}-vtx">')
        xml_lines.append(f'          <input semantic="POSITION" source="#{gname}-pos"/>')
        xml_lines.append(f'          <input semantic="NORMAL" source="#{gname}-norm"/>')
        xml_lines.append('        </vertices>')

        for mat, indices in mat_tris.items():
            p_str = " ".join(f"{i0} {i1} {i2}" for (i0, i1, i2) in indices)
            xml_lines.append(f'        <triangles count="{len(indices)}" material="{mat}">')
            xml_lines.append(f'          <input semantic="VERTEX" source="#{gname}-vtx" offset="0"/>')
            xml_lines.append(f'          <p>{p_str}</p>')
            xml_lines.append('        </triangles>')

        xml_lines.append('      </mesh>')
        xml_lines.append('    </geometry>')
    xml_lines.append('  </library_geometries>')

    xml_lines.append('  <library_visual_scenes>')
    xml_lines.append('    <visual_scene id="Scene" name="Scene">')
    for gname, tri_list in geoms_subset.items():
        if not tri_list:
            continue
        xml_lines.append(f'      <node id="{gname}-node" name="{gname}">')
        xml_lines.append(f'        <instance_geometry url="#{gname}-geom">')
        xml_lines.append('          <bind_material>')
        xml_lines.append('            <technique_common>')
        for mat_id in materials_def.keys():
            xml_lines.append(f'              <instance_material symbol="{mat_id}" target="#{mat_id}-material"/>')
        xml_lines.append('            </technique_common>')
        xml_lines.append('          </bind_material>')
        xml_lines.append('        </instance_geometry>')
        xml_lines.append('      </node>')
    xml_lines.append('    </visual_scene>')
    xml_lines.append('  </library_visual_scenes>')

    xml_lines.append('  <scene>')
    xml_lines.append('    <instance_visual_scene url="#Scene"/>')
    xml_lines.append('  </scene>')
    xml_lines.append('</COLLADA>')

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(xml_lines))
    print(f"Exported DAE ({os.path.basename(output_path)}): {os.path.getsize(output_path)} bytes")

def build_all_models():
    geoms = {
        "Foundation": [],
        "Columns": [],
        "Walls_Ext": [],
        "Walls_Int": [],
        "Doors": [],
        "Windows_Frames": [],
        "Windows_Glass": [],
        "Roof_Main": [],
        "Roof_Porch": [],
        "Fascia_Trim": [],
        "Hardware": [],
        "Site_Pavement": []
    }
    
    def add_quad(geom_name, p0, p1, p2, p3, norm, mat):
        geoms[geom_name].append((p0, p1, p2, norm, mat))
        geoms[geom_name].append((p0, p2, p3, norm, mat))

    def add_tri(geom_name, p0, p1, p2, norm, mat):
        geoms[geom_name].append((p0, p1, p2, norm, mat))

    def add_box(geom_name, x0, y0, z0, x1, y1, z1, mat):
        add_quad(geom_name, [x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [0, 0, -1], mat)
        add_quad(geom_name, [x0, y0, z1], [x0, y1, z1], [x1, y1, z1], [x1, y0, z1], [0, 0, 1], mat)
        add_quad(geom_name, [x0, y0, z0], [x0, y1, z0], [x0, y1, z1], [x0, y0, z1], [-1, 0, 0], mat)
        add_quad(geom_name, [x1, y0, z0], [x1, y0, z1], [x1, y1, z1], [x1, y1, z0], [1, 0, 0], mat)
        add_quad(geom_name, [x0, y0, z0], [x0, y0, z1], [x1, y0, z1], [x1, y0, z0], [0, -1, 0], mat)
        add_quad(geom_name, [x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1], [0, 1, 0], mat)

    def compute_normal(p0, p1, p2):
        u = [p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2]]
        v = [p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2]]
        nx = u[1]*v[2] - u[2]*v[1]
        ny = u[2]*v[0] - u[0]*v[2]
        nz = u[0]*v[1] - u[1]*v[0]
        l = math.sqrt(nx*nx + ny*ny + nz*nz)
        if l < 1e-6:
            return [0, 0, 1]
        return [nx/l, ny/l, nz/l]

    def add_sloped_beam(geom_name, p_start, p_end, width_y, height_z, mat):
        p0 = [p_start[0], p_start[1] - width_y/2, p_start[2] - height_z/2]
        p1 = [p_start[0], p_start[1] + width_y/2, p_start[2] - height_z/2]
        p2 = [p_start[0], p_start[1] + width_y/2, p_start[2] + height_z/2]
        p3 = [p_start[0], p_start[1] - width_y/2, p_start[2] + height_z/2]

        p4 = [p_end[0], p_end[1] - width_y/2, p_end[2] - height_z/2]
        p5 = [p_end[0], p_end[1] + width_y/2, p_end[2] - height_z/2]
        p6 = [p_end[0], p_end[1] + width_y/2, p_end[2] + height_z/2]
        p7 = [p_end[0], p_end[1] - width_y/2, p_end[2] + height_z/2]

        add_quad(geom_name, p0, p4, p5, p1, compute_normal(p0, p4, p5), mat)
        add_quad(geom_name, p1, p5, p6, p2, compute_normal(p1, p5, p6), mat)
        add_quad(geom_name, p2, p6, p7, p3, compute_normal(p2, p6, p7), mat)
        add_quad(geom_name, p3, p7, p4, p0, compute_normal(p3, p7, p4), mat)
        add_quad(geom_name, p0, p1, p2, p3, compute_normal(p0, p1, p2), mat)
        add_quad(geom_name, p4, p7, p6, p5, compute_normal(p4, p7, p6), mat)

    # 1. FOUNDATION & STEPS (+0.45m)
    add_box("Foundation", 0.0, 0.0, 0.0, 20.6, 10.1, 0.45, "Plinth_Mat")
    add_box("Foundation", 0.02, 0.02, 0.44, 20.58, 10.08, 0.45, "Floor_Tile")

    add_box("Foundation", -2.6, 3.2, 0.0, 0.0, 7.2, 0.45, "Plinth_Mat")
    add_box("Foundation", -2.58, 3.22, 0.44, 0.0, 7.18, 0.45, "Floor_Tile")

    add_box("Foundation", -3.5, 2.4, 0.0, -2.6, 8.0, 0.15, "Porch_Stone")
    add_box("Foundation", -3.2, 2.7, 0.15, -2.6, 7.7, 0.30, "Porch_Stone")
    add_box("Foundation", -2.9, 3.0, 0.30, -2.6, 7.4, 0.45, "Porch_Stone")

    add_box("Foundation", 13.8, -1.5, 0.0, 16.5, 0.0, 0.45, "Plinth_Mat")
    add_box("Foundation", 13.82, -1.48, 0.44, 16.48, 0.0, 0.45, "Floor_Tile")
    add_box("Foundation", 13.5, -2.1, 0.0, 16.8, -1.5, 0.15, "Porch_Stone")
    add_box("Foundation", 13.65, -1.8, 0.15, 16.65, -1.5, 0.30, "Porch_Stone")

    add_box("Site_Pavement", -5.5, -3.5, -0.05, 23.5, 13.0, 0.0, "Pavement_Mat")

    # 2. COLUMNS
    col_coords = [(-2.3, 3.6), (-2.3, 6.8)]
    for cx, cy in col_coords:
        add_box("Columns", cx-0.32, cy-0.32, 0.45, cx+0.32, cy+0.32, 1.25, "Plinth_Mat")
        add_box("Columns", cx-0.34, cy-0.34, 1.20, cx+0.34, cy+0.34, 1.25, "Fascia_White")
        add_box("Columns", cx-0.20, cy-0.20, 1.25, cx+0.20, cy+0.20, 3.95, "Column_Mat")
        add_box("Columns", cx-0.26, cy-0.26, 3.95, cx+0.26, cy+0.26, 4.15, "Column_Mat")
        add_box("Columns", cx-0.32, cy-0.32, 4.15, cx+0.32, cy+0.32, 4.35, "Column_Mat")

    add_box("Columns", -2.6, 3.2, 4.15, -2.0, 7.2, 4.35, "Fascia_White")

    side_col_coords = [(14.2, -1.1), (16.1, -1.1)]
    for cx, cy in side_col_coords:
        add_box("Columns", cx-0.25, cy-0.25, 0.45, cx+0.25, cy+0.25, 1.15, "Plinth_Mat")
        add_box("Columns", cx-0.16, cy-0.16, 1.15, cx+0.16, cy+0.16, 3.95, "Column_Mat")
        add_box("Columns", cx-0.22, cy-0.22, 3.95, cx+0.22, cy+0.22, 4.35, "Column_Mat")
    add_box("Columns", 13.9, -1.3, 4.15, 16.4, -0.9, 4.35, "Fascia_White")

    # 3. EXTERIOR WALLS
    wall_h = 4.35
    sill_h = 1.35
    win_top = 3.15
    door_top = 3.15

    add_box("Walls_Ext", 0.0, 0.0, 0.45, 0.22, 0.8, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 0.0, 0.8, 0.45, 0.22, 2.4, sill_h, "Wall_Mat")
    add_box("Walls_Ext", 0.0, 0.8, win_top, 0.22, 2.4, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 0.0, 2.4, 0.45, 0.22, 3.2, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 0.0, 3.2, 0.45, 0.22, 4.0, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 0.0, 4.0, door_top, 0.22, 6.6, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 0.0, 6.6, 0.45, 0.22, 7.2, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 0.0, 7.2, 0.45, 0.22, 8.0, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 0.0, 8.0, 0.45, 0.22, 9.6, sill_h, "Wall_Mat")
    add_box("Walls_Ext", 0.0, 8.0, win_top, 0.22, 9.6, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 0.0, 9.6, 0.45, 0.22, 10.1, wall_h, "Wall_Mat")

    add_box("Walls_Ext", 0.0, 9.88, 0.45, 2.5, 10.1, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 2.5, 9.88, 0.45, 4.1, 10.1, sill_h, "Wall_Mat")
    add_box("Walls_Ext", 2.5, 9.88, win_top, 4.1, 10.1, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 4.1, 9.88, 0.45, 9.8, 10.1, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 9.8, 9.88, 0.45, 11.4, 10.1, sill_h, "Wall_Mat")
    add_box("Walls_Ext", 9.8, 9.88, win_top, 11.4, 10.1, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 11.4, 9.88, 0.45, 14.5, 10.1, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 14.5, 9.88, 0.45, 16.1, 10.1, sill_h, "Wall_Mat")
    add_box("Walls_Ext", 14.5, 9.88, win_top, 16.1, 10.1, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 16.1, 9.88, 0.45, 18.5, 10.1, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 18.5, 9.88, 0.45, 19.5, 10.1, 2.7, "Wall_Mat")
    add_box("Walls_Ext", 18.5, 9.88, 3.4, 19.5, 10.1, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 19.5, 9.88, 0.45, 20.6, 10.1, wall_h, "Wall_Mat")

    add_box("Walls_Ext", 0.0, 0.0, 0.45, 2.5, 0.22, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 2.5, 0.0, 0.45, 4.1, 0.22, sill_h, "Wall_Mat")
    add_box("Walls_Ext", 2.5, 0.0, win_top, 4.1, 0.22, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 4.1, 0.0, 0.45, 14.4, 0.22, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 14.4, 0.0, 3.05, 15.6, 0.22, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 15.6, 0.0, 0.45, 16.2, 0.22, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 16.2, 0.0, 0.45, 17.6, 0.22, sill_h, "Wall_Mat")
    add_box("Walls_Ext", 16.2, 0.0, win_top, 17.6, 0.22, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 17.6, 0.0, 0.45, 20.6, 0.22, wall_h, "Wall_Mat")

    add_box("Walls_Ext", 20.38, 0.0, 0.45, 20.6, 4.8, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 20.38, 4.8, 2.85, 20.6, 5.8, wall_h, "Wall_Mat")
    add_box("Walls_Ext", 20.38, 5.8, 0.45, 20.6, 10.1, wall_h, "Wall_Mat")

    add_box("Walls_Ext", -0.03, 0.0, 0.45, 0.0, 10.1, 0.95, "Plinth_Mat")
    add_box("Walls_Ext", 0.0, 10.1, 0.45, 20.6, 10.13, 0.95, "Plinth_Mat")
    add_box("Walls_Ext", 0.0, -0.03, 0.45, 20.6, 0.0, 0.95, "Plinth_Mat")
    add_box("Walls_Ext", 20.6, 0.0, 0.45, 20.63, 10.1, 0.95, "Plinth_Mat")

    for z_groove in [1.5, 2.0, 2.5, 3.0, 3.6]:
        add_box("Fascia_Trim", -0.015, 0.0, z_groove, 0.0, 3.2, z_groove + 0.03, "Wall_Accent")
        add_box("Fascia_Trim", -0.015, 7.2, z_groove, 0.0, 10.1, z_groove + 0.03, "Wall_Accent")
        add_box("Fascia_Trim", 0.0, 10.1, z_groove, 20.6, 10.115, z_groove + 0.03, "Wall_Accent")
        add_box("Fascia_Trim", 0.0, -0.015, z_groove, 20.6, 0.0, z_groove + 0.03, "Wall_Accent")

    # 4. INTERIOR WALLS
    add_box("Walls_Int", 0.22, 7.15, 0.45, 6.8, 7.26, wall_h, "Wall_Mat")
    add_box("Walls_Int", 6.8, 7.15, 2.7, 7.8, 7.26, wall_h, "Wall_Mat")
    add_box("Walls_Int", 7.8, 7.15, 0.45, 8.6, 7.26, wall_h, "Wall_Mat")

    add_box("Walls_Int", 0.22, 3.15, 0.45, 6.8, 3.26, wall_h, "Wall_Mat")
    add_box("Walls_Int", 6.8, 3.15, 2.7, 7.8, 3.26, wall_h, "Wall_Mat")
    add_box("Walls_Int", 7.8, 3.15, 0.45, 8.6, 3.26, wall_h, "Wall_Mat")

    add_box("Walls_Int", 8.5, 0.22, 0.45, 8.61, 3.6, wall_h, "Wall_Mat")
    add_box("Walls_Int", 8.5, 3.6, 3.3, 8.61, 6.8, wall_h, "Wall_Mat")
    add_box("Walls_Int", 8.5, 6.8, 0.45, 8.61, 9.88, wall_h, "Wall_Mat")

    add_box("Walls_Int", 8.61, 7.15, 2.7, 9.8, 7.26, wall_h, "Wall_Mat")
    add_box("Walls_Int", 9.8, 7.15, 0.45, 13.8, 7.26, wall_h, "Wall_Mat")

    add_box("Walls_Int", 13.7, 0.22, 0.45, 13.81, 2.0, wall_h, "Wall_Mat")
    add_box("Walls_Int", 13.7, 2.0, 3.3, 13.81, 5.5, wall_h, "Wall_Mat")
    add_box("Walls_Int", 13.7, 5.5, 0.45, 13.81, 9.88, wall_h, "Wall_Mat")
    add_box("Walls_Int", 13.7, 7.26, 0.45, 13.81, 9.88, wall_h, "Wall_Mat")

    add_box("Walls_Int", 17.2, 0.22, 0.45, 17.31, 4.5, wall_h, "Wall_Mat")
    add_box("Walls_Int", 17.2, 4.5, 2.7, 17.31, 5.5, wall_h, "Wall_Mat")
    add_box("Walls_Int", 17.2, 5.5, 0.45, 17.31, 9.88, wall_h, "Wall_Mat")
    add_box("Walls_Int", 17.31, 4.95, 0.45, 20.38, 5.06, wall_h, "Wall_Mat")

    # 5. DOORS & WINDOWS
    add_box("Doors", 0.06, 4.0, 0.45, 0.16, 4.10, 3.15, "Door_Wood")
    add_box("Doors", 0.06, 6.50, 0.45, 0.16, 6.60, 3.15, "Door_Wood")
    add_box("Doors", 0.06, 4.10, 3.05, 0.16, 6.50, 3.15, "Door_Wood")
    add_box("Doors", 0.06, 4.10, 2.50, 0.16, 6.50, 2.58, "Door_Wood")

    for i in range(4):
        dy0 = 4.10 + i * 0.60
        dy1 = dy0 + 0.60
        add_box("Doors", 0.08, dy0, 0.45, 0.14, dy0+0.08, 2.50, "Door_Wood")
        add_box("Doors", 0.08, dy1-0.08, 0.45, 0.14, dy1, 2.50, "Door_Wood")
        add_box("Doors", 0.08, dy0+0.08, 0.45, 0.14, dy1-0.08, 0.85, "Door_Wood")
        add_box("Doors", 0.08, dy0+0.08, 2.42, 0.14, dy1-0.08, 2.50, "Door_Wood")
        add_box("Doors", 0.08, dy0+0.08, 1.45, 0.14, dy1-0.08, 1.53, "Door_Wood")
        add_box("Windows_Glass", 0.105, dy0+0.08, 0.85, 0.115, dy1-0.08, 1.45, "Glass_Mat")
        add_box("Windows_Glass", 0.105, dy0+0.08, 1.53, 0.115, dy1-0.08, 2.42, "Glass_Mat")
        add_box("Windows_Glass", 0.105, dy0+0.02, 2.58, 0.115, dy1-0.02, 3.05, "Glass_Mat")

    add_box("Hardware", 0.04, 5.26, 1.35, 0.07, 5.28, 1.65, "Gold_Handle")
    add_box("Hardware", 0.04, 5.32, 1.35, 0.07, 5.34, 1.65, "Gold_Handle")

    def add_window_4leaf(x0, y0, z0, x1, y1, z1, is_x_plane=True):
        if is_x_plane:
            add_box("Windows_Frames", x0-0.03, y0, z0, x1+0.03, y0+0.06, z1, "Door_Wood")
            add_box("Windows_Frames", x0-0.03, y1-0.06, z0, x1+0.03, y1, z1, "Door_Wood")
            add_box("Windows_Frames", x0-0.03, y0+0.06, z0, x1+0.03, y1-0.06, z0+0.06, "Door_Wood")
            add_box("Windows_Frames", x0-0.03, y0+0.06, z1-0.06, x1+0.03, y1-0.06, z1, "Door_Wood")
            w = (y1 - y0 - 0.12) / 4.0
            for k in range(1, 4):
                my = y0 + 0.06 + k * w
                add_box("Windows_Frames", x0-0.02, my-0.03, z0+0.06, x1+0.02, my+0.03, z1-0.06, "Door_Wood")
            for k in range(4):
                gy0 = y0 + 0.06 + k * w + 0.015
                gy1 = gy0 + w - 0.03
                add_box("Windows_Glass", (x0+x1)/2 - 0.005, gy0, z0+0.06, (x0+x1)/2 + 0.005, gy1, z1-0.06, "Glass_Mat")
            add_box("Fascia_Trim", x0-0.08, y0-0.05, z0-0.06, x0, y1+0.05, z0, "Fascia_White")
        else:
            add_box("Windows_Frames", x0, y0-0.03, z0, x0+0.06, y1+0.03, z1, "Door_Wood")
            add_box("Windows_Frames", x1-0.06, y0-0.03, z0, x1, y1+0.03, z1, "Door_Wood")
            add_box("Windows_Frames", x0+0.06, y0-0.03, z0, x1-0.06, y1+0.03, z0+0.06, "Door_Wood")
            add_box("Windows_Frames", x0+0.06, y0-0.03, z1-0.06, x1-0.06, y1+0.03, z1, "Door_Wood")
            mx = (x0 + x1) / 2
            add_box("Windows_Frames", mx-0.03, y0-0.02, z0+0.06, mx+0.03, y1+0.02, z1-0.06, "Door_Wood")
            w = (x1 - x0 - 0.12) / 2.0
            for k in range(2):
                gx0 = x0 + 0.06 + k * w + 0.015
                gx1 = gx0 + w - 0.03
                add_box("Windows_Glass", gx0, (y0+y1)/2 - 0.005, z0+0.06, gx1, (y0+y1)/2 + 0.005, z1-0.06, "Glass_Mat")
            add_box("Fascia_Trim", x0-0.05, y0-0.08, z0-0.06, x1+0.05, y0, z0, "Fascia_White")

    add_window_4leaf(0.08, 0.8, sill_h, 0.14, 2.4, win_top, is_x_plane=True)
    add_window_4leaf(0.08, 8.0, sill_h, 0.14, 9.6, win_top, is_x_plane=True)

    add_window_4leaf(2.5, 9.94, sill_h, 4.1, 10.0, win_top, is_x_plane=False)
    add_window_4leaf(9.8, 9.94, sill_h, 11.4, 10.0, win_top, is_x_plane=False)
    add_window_4leaf(14.5, 9.94, sill_h, 16.1, 10.0, win_top, is_x_plane=False)
    add_window_4leaf(2.5, 0.10, sill_h, 4.1, 0.16, win_top, is_x_plane=False)
    add_window_4leaf(16.2, 0.10, sill_h, 17.6, 0.16, win_top, is_x_plane=False)

    add_box("Doors", 14.4, 0.08, 0.45, 15.6, 0.14, 3.05, "Door_Wood")
    add_box("Windows_Glass", 14.5, 0.105, 1.0, 15.5, 0.115, 2.9, "Glass_Mat")

    # 6. CEILING & BEAMS
    add_box("Walls_Ext", -0.3, -0.3, 4.35, 20.9, 10.4, 4.55, "Wall_Accent")
    add_box("Walls_Ext", -2.8, 3.0, 4.35, 0.0, 7.4, 4.55, "Wall_Accent")
    add_box("Fascia_Trim", -0.35, -0.35, 4.50, 20.95, 10.45, 4.60, "Fascia_White")

    # 7. MAIN PITCHED ROOF
    x_start = -0.7
    x_end = 21.3
    y_right_eaves = -0.8
    y_left_eaves = 10.9
    y_ridge = 5.05
    z_eaves = 4.30
    z_ridge = 6.95

    p_re0 = [x_start, y_right_eaves, z_eaves]
    p_re1 = [x_end, y_right_eaves, z_eaves]
    p_rr1 = [x_end, y_ridge, z_ridge]
    p_rr0 = [x_start, y_ridge, z_ridge]
    add_quad("Roof_Main", p_re0, p_re1, p_rr1, p_rr0, compute_normal(p_re0, p_re1, p_rr1), "Roof_Tile")

    p_le0 = [x_start, y_left_eaves, z_eaves]
    p_le1 = [x_end, y_left_eaves, z_eaves]
    p_lr1 = [x_end, y_ridge, z_ridge]
    p_lr0 = [x_start, y_ridge, z_ridge]
    add_quad("Roof_Main", p_le0, p_lr0, p_lr1, p_le1, compute_normal(p_le0, p_lr1, p_le1), "Roof_Tile")

    add_box("Roof_Main", x_start-0.08, y_ridge-0.20, z_ridge-0.05, x_end+0.08, y_ridge+0.20, z_ridge+0.08, "Ridge_Cap")
    add_box("Fascia_Trim", x_start, y_right_eaves-0.05, z_eaves-0.22, x_end, y_right_eaves, z_eaves+0.04, "Fascia_White")
    add_box("Fascia_Trim", x_start, y_left_eaves, z_eaves-0.22, x_end, y_left_eaves+0.05, z_eaves+0.04, "Fascia_White")

    add_tri("Walls_Ext", [0.0, 0.0, 4.55], [0.0, 10.1, 4.55], [0.0, y_ridge, z_ridge-0.12], [-1, 0, 0], "Wall_Mat")
    add_tri("Walls_Ext", [20.6, 0.0, 4.55], [20.6, y_ridge, z_ridge-0.12], [20.6, 10.1, 4.55], [1, 0, 0], "Wall_Mat")

    add_sloped_beam("Fascia_Trim", [x_start, y_right_eaves, z_eaves], [x_start, y_ridge, z_ridge], 0.12, 0.22, "Fascia_White")
    add_sloped_beam("Fascia_Trim", [x_start, y_left_eaves, z_eaves], [x_start, y_ridge, z_ridge], 0.12, 0.22, "Fascia_White")
    add_sloped_beam("Fascia_Trim", [x_end, y_right_eaves, z_eaves], [x_end, y_ridge, z_ridge], 0.12, 0.22, "Fascia_White")
    add_sloped_beam("Fascia_Trim", [x_end, y_left_eaves, z_eaves], [x_end, y_ridge, z_ridge], 0.12, 0.22, "Fascia_White")

    # 8. FRONT PORCH PITCHED GABLE ROOF
    px_start = -3.2
    px_end = 0.6
    py_right = 2.8
    py_left = 7.6
    py_ridge = 5.20
    pz_eaves = 4.25
    pz_ridge = 5.85

    pp_re0 = [px_start, py_right, pz_eaves]
    pp_re1 = [px_end, py_right, pz_eaves]
    pp_rr1 = [px_end, py_ridge, pz_ridge]
    pp_rr0 = [px_start, py_ridge, pz_ridge]
    add_quad("Roof_Porch", pp_re0, pp_re1, pp_rr1, pp_rr0, compute_normal(pp_re0, pp_re1, pp_rr1), "Roof_Tile")

    pp_le0 = [px_start, py_left, pz_eaves]
    pp_le1 = [px_end, py_left, pz_eaves]
    pp_lr1 = [px_end, py_ridge, pz_ridge]
    pp_lr0 = [px_start, py_ridge, pz_ridge]
    add_quad("Roof_Porch", pp_le0, pp_lr0, pp_lr1, pp_le1, compute_normal(pp_le0, pp_lr1, pp_le1), "Roof_Tile")

    add_box("Roof_Porch", px_start-0.08, py_ridge-0.18, pz_ridge-0.04, px_end, py_ridge+0.18, pz_ridge+0.06, "Ridge_Cap")
    add_sloped_beam("Fascia_Trim", [px_start, py_right, pz_eaves], [px_start, py_ridge, pz_ridge], 0.14, 0.22, "Fascia_White")
    add_sloped_beam("Fascia_Trim", [px_start, py_left, pz_eaves], [px_start, py_ridge, pz_ridge], 0.14, 0.22, "Fascia_White")
    add_box("Fascia_Trim", px_start, py_right-0.04, pz_eaves-0.18, px_end, py_right, pz_eaves+0.04, "Fascia_White")
    add_box("Fascia_Trim", px_start, py_left, pz_eaves-0.18, px_end, py_left+0.04, pz_eaves+0.04, "Fascia_White")

    add_tri("Walls_Ext", [-2.6, 3.2, 4.35], [-2.6, 7.2, 4.35], [-2.6, py_ridge, pz_ridge-0.10], [-1, 0, 0], "Wall_Accent")

    cx_vent = -2.62
    cy_vent = py_ridge
    cz_vent = 5.08
    r_vent = 0.35
    segs = 24
    for s in range(segs):
        ang0 = 2 * math.pi * s / segs
        ang1 = 2 * math.pi * (s + 1) / segs
        p0 = [cx_vent, cy_vent, cz_vent]
        p1 = [cx_vent, cy_vent + r_vent * math.cos(ang0), cz_vent + r_vent * math.sin(ang0)]
        p2 = [cx_vent, cy_vent + r_vent * math.cos(ang1), cz_vent + r_vent * math.sin(ang1)]
        add_tri("Windows_Glass", p0, p1, p2, [-1, 0, 0], "Glass_Mat")
        rf = 0.44
        p1f = [cx_vent-0.015, cy_vent + rf * math.cos(ang0), cz_vent + rf * math.sin(ang0)]
        p2f = [cx_vent-0.015, cy_vent + rf * math.cos(ang1), cz_vent + rf * math.sin(ang1)]
        add_quad("Fascia_Trim", p1, p2, p2f, p1f, [-1, 0, 0], "Fascia_White")

    add_box("Fascia_Trim", cx_vent-0.02, cy_vent-0.02, cz_vent-r_vent, cx_vent, cy_vent+0.02, cz_vent+r_vent, "Fascia_White")
    add_box("Fascia_Trim", cx_vent-0.02, cy_vent-r_vent, cz_vent-0.02, cx_vent, cy_vent+r_vent, cz_vent+0.02, "Fascia_White")

    for lz in [4.52, 4.66, 4.80]:
        span_w = (pz_ridge - lz) / (pz_ridge - 4.35) * 1.85
        add_box("Fascia_Trim", -2.63, py_ridge - span_w, lz, -2.61, py_ridge + span_w, lz + 0.04, "Fascia_White")

    # 9. SIDE PORCH ROOF
    sp_x0 = 13.4
    sp_x1 = 16.9
    sp_y_eaves = -2.0
    sp_y_ridge = 0.2
    sp_z_eaves = 4.25
    sp_z_ridge = 5.25
    add_quad("Roof_Porch", 
             [sp_x0, sp_y_eaves, sp_z_eaves],
             [sp_x1, sp_y_eaves, sp_z_eaves],
             [sp_x1, sp_y_ridge, sp_z_ridge],
             [sp_x0, sp_y_ridge, sp_z_ridge],
             compute_normal([sp_x0, sp_y_eaves, sp_z_eaves], [sp_x1, sp_y_eaves, sp_z_eaves], [sp_x1, sp_y_ridge, sp_z_ridge]),
             "Roof_Tile")
    add_box("Fascia_Trim", sp_x0, sp_y_eaves-0.04, sp_z_eaves-0.18, sp_x1, sp_y_eaves, sp_z_eaves+0.04, "Fascia_White")
    add_sloped_beam("Fascia_Trim", [sp_x0, sp_y_eaves, sp_z_eaves], [sp_x0, sp_y_ridge, sp_z_ridge], 0.12, 0.18, "Fascia_White")
    add_sloped_beam("Fascia_Trim", [sp_x1, sp_y_eaves, sp_z_eaves], [sp_x1, sp_y_ridge, sp_z_ridge], 0.12, 0.18, "Fascia_White")

    # --- SUBSET 1: Entire Model Combined ---
    full_path = os.path.abspath("tests/scratch/nha_cap_4_11_5x20_5.dae")
    generate_dae_xml(geoms, full_path)

    # --- SUBSET 2: Body Only (Without Roofs and Ceiling) for Interior Cutaway View ---
    body_geoms = {
        "Foundation": geoms["Foundation"],
        "Columns": geoms["Columns"],
        "Walls_Ext": geoms["Walls_Ext"],
        "Walls_Int": geoms["Walls_Int"],
        "Doors": geoms["Doors"],
        "Windows_Frames": geoms["Windows_Frames"],
        "Windows_Glass": geoms["Windows_Glass"],
        "Hardware": geoms["Hardware"],
        "Site_Pavement": geoms["Site_Pavement"]
    }
    body_path = os.path.abspath("tests/scratch/nha_cap_4_body.dae")
    generate_dae_xml(body_geoms, body_path)

    # --- SUBSET 3: Roof Only ---
    roof_geoms = {
        "Roof_Main": geoms["Roof_Main"],
        "Roof_Porch": geoms["Roof_Porch"],
        "Fascia_Trim": geoms["Fascia_Trim"]
    }
    roof_path = os.path.abspath("tests/scratch/nha_cap_4_roof.dae")
    generate_dae_xml(roof_geoms, roof_path)

if __name__ == "__main__":
    build_all_models()
