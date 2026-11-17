"""make.py's clean step, in Blender: the raw mesh turned to the pack's axes, sized, stood on the ground, decimated
under the triangle limit and its texture baked onto one 1024 px base-colour map.

    blender -b -P blender_clean.py -- <raw.glb> <clean.blend> <clean.glb> <size m> <mesher> <turn degrees | auto>

The turn is about the vertical: the one that brings the head to glTF +Z. "auto" lays the longest horizontal side
along the body and puts the head at the end with more surface in its upper half (a thin tail held up has little);
what it chose is printed and written to clean.json beside the output, and --turn on make.py overrides it."""
import bmesh, json, math, os, sys
import bpy
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_common as common      # noqa: E402

TRIANGLES = 9500          # under SPEC.md's 10,000 guideline, with room for the rig step's leg split
TEXTURE = 1024
LOOSE = 0.01              # loose pieces with less than this share of the faces are dropped (specks, a stray plane)

raw, out_blend, out_glb, size, mesher, turn = common.args()
size = float(size)
common.reset()
bpy.ops.import_scene.gltf(filepath=raw)
objects = common.mesh_objects()
for o in bpy.context.scene.objects: o.select_set(o in objects)
bpy.context.view_layer.objects.active = objects[0]
if len(objects) > 1: bpy.ops.object.join()
high = bpy.context.view_layer.objects.active
for o in list(bpy.context.scene.objects):
    if o is not high: bpy.data.objects.remove(o)
high.parent = None
high.modifiers.clear(); high.vertex_groups.clear()        # a mesh that came rigged loses its old skin here
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
high.name = "high"
log_facts = {"raw_faces": len(high.data.polygons)}

# Loose pieces. The importer splits vertices at UV seams, so weld them first (positions only; the UVs stay per corner).
bm = bmesh.new(); bm.from_mesh(high.data)
lo0, hi0 = common.bounds([high])
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=max(hi0 - lo0) * 1e-5)
pieces, seen = [], set()
for f in bm.faces:
    if f.index in seen: continue
    stack, piece = [f], []
    seen.add(f.index)
    while stack:
        g = stack.pop(); piece.append(g)
        for e in g.edges:
            for h in e.link_faces:
                if h.index not in seen: seen.add(h.index); stack.append(h)
    pieces.append(piece)
total = len(bm.faces)
dropped = [p for p in pieces if len(p) < LOOSE * total]
bmesh.ops.delete(bm, geom=[f for p in dropped for f in p], context="FACES")
bm.to_mesh(high.data); bm.free()
log_facts.update(pieces=len(pieces), dropped=len(dropped))
common.log("raw: %d faces in %d pieces, %d small ones dropped" % (total, len(pieces), len(dropped)))


def verts(o): return [o.matrix_world @ v.co for v in o.data.vertices]


# The turn: the body along Blender's Y (glTF Z), then the head to -Y.
if turn == "auto":
    lo, hi = common.bounds([high])
    angle = 90.0 if (hi.x - lo.x) > (hi.y - lo.y) else 0.0
    high.data.transform(Matrix.Rotation(math.radians(angle), 4, "Z")); high.data.update()
    lo, hi = common.bounds([high])
    mid = (lo.z + hi.z) / 2
    def upper_area(sign):
        cut = (lo.y + hi.y) / 2 + sign * (hi.y - lo.y) * 0.3
        return sum(p.area for p in high.data.polygons if (p.center.y - cut) * sign > 0 and p.center.z > mid)
    if upper_area(+1) > upper_area(-1):      # the head is at +Y: turn it round to -Y
        high.data.transform(Matrix.Rotation(math.pi, 4, "Z")); angle += 180
    turn_used = angle % 360
else:
    turn_used = float(turn) % 360
    high.data.transform(Matrix.Rotation(math.radians(turn_used), 4, "Z"))
high.data.update()
common.log("turned %.0f degrees about the vertical (%s)" % (turn_used, "auto" if turn == "auto" else "given"))

# Size, ground and centre.
lo, hi = common.bounds([high])
longest = max(hi - lo)
s = size / longest
high.data.transform(Matrix.Diagonal((s, s, s, 1))); high.data.update()
lo, hi = common.bounds([high])
high.data.transform(Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))); high.data.update()
lo, hi = common.bounds([high])
common.log("box %s to %s m" % (tuple(round(c, 4) for c in lo), tuple(round(c, 4) for c in hi)))

# The low copy: decimated, unwrapped fresh.
low = high.copy(); low.data = high.data.copy(); low.name = "Mesh"
bpy.context.scene.collection.objects.link(low)
faces = sum(len(p.vertices) - 2 for p in low.data.polygons)
ratio = min(1.0, TRIANGLES / max(faces, 1))
for attempt in range(6):
    test = low.data.copy()
    probe = bpy.data.objects.new("probe", test); bpy.context.scene.collection.objects.link(probe)
    mod = probe.modifiers.new("decimate", "DECIMATE"); mod.ratio = ratio; mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = probe
    for o in bpy.context.scene.objects: o.select_set(o is probe)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    tris = sum(len(p.vertices) - 2 for p in probe.data.polygons)
    if tris <= TRIANGLES or ratio < 1e-3:
        old = low.data; low.data = probe.data; bpy.data.objects.remove(probe); bpy.data.meshes.remove(old)
        break
    bpy.data.objects.remove(probe); ratio *= TRIANGLES / tris * 0.98
common.log("decimated %d to %d triangles (ratio %.4f)" % (faces, tris, ratio))
log_facts.update(triangles=tris)
for o in bpy.context.scene.objects: o.select_set(o is low)
bpy.context.view_layer.objects.active = low
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.quads_convert_to_tris()
for layer in list(low.data.uv_layers): low.data.uv_layers.remove(layer)
low.data.uv_layers.new(name="UVMap")
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0, correct_aspect=True, scale_to_bounds=True)
bpy.ops.uv.pack_islands(margin=0.004, rotate=True)
bpy.ops.object.mode_set(mode="OBJECT")
for attribute in list(low.data.color_attributes): low.data.color_attributes.remove(attribute)
for p in low.data.polygons: p.use_smooth = True

# The bake: the high mesh's base colour onto the low one's new map.
image = bpy.data.images.new("fur", TEXTURE, TEXTURE, alpha=False)
material = bpy.data.materials.new("fur"); material.use_nodes = True
nodes = material.node_tree.nodes
bsdf = nodes["Principled BSDF"]
bsdf.inputs["Metallic"].default_value = 0.0; bsdf.inputs["Roughness"].default_value = 0.8
tex = nodes.new("ShaderNodeTexImage"); tex.image = image
material.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
low.data.materials.clear(); low.data.materials.append(material)
nodes.active = tex
# Only the base colour is baked: a source material left metallic (glTF's default when none is written, as trimesh
# does) bakes black as diffuse, so the high mesh's materials are made non-metallic first.
for slot in high.material_slots:
    if slot.material and slot.material.use_nodes:
        for node in slot.material.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                for link in list(node.inputs["Metallic"].links): slot.material.node_tree.links.remove(link)
                node.inputs["Metallic"].default_value = 0.0
scene = common.cycles(16)
bake = scene.render.bake
bake.use_selected_to_active = True; bake.use_pass_direct = False; bake.use_pass_indirect = False; bake.use_pass_color = True
bake.cage_extrusion = size * 0.02; bake.max_ray_distance = size * 0.06; bake.margin = 8
for o in bpy.context.scene.objects: o.select_set(o in (high, low))
bpy.context.view_layer.objects.active = low
bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"})
image.filepath_raw = os.path.join(os.path.dirname(out_blend), "fur.png"); image.file_format = "PNG"; image.save()
image.pack()
common.log("baked the base colour onto %dx%d" % (TEXTURE, TEXTURE))

# Keep the high mesh in the .blend (hidden) for a later rebake; export the low one alone.
high.hide_render = True; high.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
for o in bpy.context.scene.objects: o.select_set(o is low)
bpy.ops.export_scene.gltf(filepath=out_glb, use_selection=True, export_format="GLB", export_image_format="JPEG", export_jpeg_quality=92,
                          export_yup=True, export_apply=True, export_animations=False, export_vertex_color="NONE")
with open(os.path.join(os.path.dirname(out_blend), "clean.json"), "w") as f:
    json.dump(dict(log_facts, turn=turn_used, turn_mode="auto" if turn == "auto" else "given", mesher=mesher, size=size,
                   box=[list(lo), list(hi)]), f, indent=2)
common.look(os.path.join(os.path.dirname(out_blend), "look-clean"), [low])
