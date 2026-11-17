"""make.py's rig step for the fish shape, in Blender: a spine chain placed from the mesh and skin weights written from
it, at most four a vertex. Four kinds of body share it, chosen by the creature's id (KINDS below) or, for an id not
listed, from the mesh's proportions:

    fish      Root, Body, Head, Tail1..Tail4 (Tail3 and Tail4 are the tail fin), FinL and FinR where the mesh has side fins
    eel       Root, Body, Chest, Head, Tail1..Tail6
    ray       Root, Body, Head, Tail1..Tail3 (Tail1 alone for a stub), WingL1, WingL2, WingR1, WingR2
    seahorse  Root, Body, Chest, Head, Tail1..Tail3: upright, the chain runs from the head down to the curled tail

    blender -b -P blender_rig_fish.py -- <clean.blend> <rig.blend> <joints.json> <place|keep> <template|unirig> <unirig-skin.npz>

Same arguments as blender_rig.py. place: the joints are found from the mesh and written to joints.json; keep: a kept
art/<id>/joints.json is used as it is. The weights are not bone heat (it fails on fins, which are two surfaces that
touch) and not UniRig's: each vertex is weighted by where it lies along the chain, blended across each joint, and a
fin or wing vertex by how far out it is. So the rigger argument only names the files, as it does for a quadruped.

The clean step's guess at which end is the head (more surface in the upper half) is wrong for most fish: here the
head is the thick end (a seahorse's: the side its snout is on), and the mesh is turned half a turn when it faces
backwards. That is logged, and make.py's --turn at the clean step makes it unnecessary.

Joint positions are in glTF metres: x the animal's left, y up, z forward (where the head points)."""
import json, math, os, sys
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_common as common      # noqa: E402

clean, out_blend, joints_path, mode, rigger, unirig_npz = common.args()
bpy.ops.wm.open_mainfile(filepath=clean)
mesh = bpy.data.objects["Mesh"]
for o in list(bpy.context.scene.objects):
    if o is not mesh: bpy.data.objects.remove(o)
mesh.data.transform(mesh.matrix_world); mesh.matrix_world = Matrix.Identity(4); mesh.data.update()
creature = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(out_blend)))))

KINDS = {
    "arctic-char": "fish", "fountain-koi": "fish", "icefish": "fish", "mangrove-goby": "fish", "pond-goldfish": "fish",
    "sand-minnow": "fish", "violet-fantail": "fish",
    "aurora-eel": "eel", "marsh-eel": "eel",
    "mud-ray": "ray", "speckled-ray": "ray", "starlit-ray": "ray",
    "reed-seahorse": "seahorse", "thorny-seahorse": "seahorse",
}
# The chain from the front to the back and where each bone ends along it (0 the nose or the top of the head, 1 the end of
# the tail). A fish's and a ray's are fitted to the mesh in place().
CHAINS = {
    "fish": ["Head", "Body", "Tail1", "Tail2", "Tail3", "Tail4"],
    "eel": ["Head", "Chest", "Body", "Tail1", "Tail2", "Tail3", "Tail4", "Tail5", "Tail6"],
    "ray": ["Head", "Body", "Tail1", "Tail2", "Tail3"],
    "seahorse": ["Head", "Chest", "Body", "Tail1", "Tail2", "Tail3"],
}
ENDS = {
    "eel": [0.0, 0.10, 0.22, 0.36, 0.47, 0.58, 0.69, 0.80, 0.90, 1.0],
    "seahorse": [0.0, 0.27, 0.42, 0.58, 0.72, 0.86, 1.0],
}
BLEND = 0.5               # of the shorter bone at a joint: how far each side of it the two bones share the skin
WING = (0.20, 0.60)       # of the half span: where a ray's inner wing bone starts and where its outer one does
THIN = 0.022              # of the length: a surface with its other side nearer than this is a fin


def gltf(v): return (v.x, v.z, -v.y)                 # Blender -> glTF
def blender(p): return Vector((p[0], -p[2], p[1]))   # glTF -> Blender
def smooth(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)
def median(values): values = sorted(values); return values[len(values) // 2] if values else 0.0


def box():
    co = [v.co for v in mesh.data.vertices]
    return (Vector((min(p.x for p in co), min(p.y for p in co), min(p.z for p in co))),
            Vector((max(p.x for p in co), max(p.y for p in co), max(p.z for p in co))))


lo, hi = box()
W, L, H = hi.x - lo.x, hi.y - lo.y, hi.z - lo.z
kind = KINDS.get(creature)
if kind is None:
    kind = "seahorse" if H > 1.3 * L else "ray" if W > 0.55 * L else "eel" if L > 6.5 * max(W, H) else "fish"
    common.log("%s is not in the fish rig's table: taken as a %s from its proportions" % (creature, kind))
upright = kind == "seahorse"


def faces_backwards():
    """True when the head is at Blender +Y (glTF -Z)."""
    co = [v.co for v in mesh.data.vertices]
    if upright:        # the snout: in the top of the animal, the side that reaches further from the trunk's middle
        trunk = median([p.y for p in co if lo.z + 0.35 * H < p.z < lo.z + 0.65 * H])
        top = [p.y for p in co if p.z > lo.z + 0.72 * H]
        return max(top) - trunk > trunk - min(top)
    # The thick end: where the body's thickness (each slice's median distance from the middle plane) has its centre.
    n, total, moment = 24, 0.0, 0.0
    for i in range(n):
        y0, y1 = lo.y + L * i / n, lo.y + L * (i + 1) / n
        t = median([abs(p.x) for p in co if y0 <= p.y <= y1])
        total += t; moment += t * ((y0 + y1) / 2 - (lo.y + hi.y) / 2)
    where = moment / max(total, 1e-9) / L
    if abs(where) < 0.01: common.log("the thick end is not clear (%.3f of the length from the middle): left as the clean step turned it" % where)
    return where >= 0.01


turned = faces_backwards()
if turned:
    mesh.data.transform(Matrix.Rotation(math.pi, 4, "Z")); mesh.data.update()
    lo, hi = box()
    common.log("the head was at the back (the clean step's turn was half a turn out): turned to face glTF +Z")
verts = [v.co.copy() for v in mesh.data.vertices]
half = max(abs(lo.x), abs(hi.x))
# Where each vertex lies along the chain: 0 at the nose (a seahorse: the top of its head), 1 at the end of the tail.
along = [(hi.z - p.z) / H for p in verts] if upright else [(p.y - lo.y) / L for p in verts]


def slab(u, width=0.02):
    """The vertices near u along the chain, at least eight of them."""
    while True:
        found = [i for i, a in enumerate(along) if abs(a - u) <= width]
        if len(found) >= 8 or width > 0.5: return found
        width *= 1.5


def centre(u):
    """The middle of the body at u, as a glTF point on the middle plane: thick parts count for more than fins."""
    found = slab(u)
    weight = [1.0 if kind == "ray" else abs(verts[i].x) + 0.1 * half for i in found]
    total = sum(weight)
    if upright: return gltf(Vector((0, sum(verts[i].y * w for i, w in zip(found, weight)) / total, hi.z - u * H)))
    return gltf(Vector((0, lo.y + u * L, sum(verts[i].z * w for i, w in zip(found, weight)) / total)))


def profile(n=40):
    """Per slice along the chain: the widest |x| and the median |x|."""
    out = []
    for k in range(n):
        xs = [abs(verts[i].x) for i, a in enumerate(along) if k / n <= a <= (k + 1) / n]
        out.append(((k + 0.5) / n, max(xs, default=0.0), median(xs)))
    return out


_thin = []


def thin_vertices():
    """The vertices of fins: sheets whose other side is close. Seen by a ray cast inward from each vertex."""
    if _thin: return _thin[0]
    me = mesh.data
    tree = BVHTree.FromPolygons([tuple(v) for v in verts], [tuple(p.vertices) for p in me.polygons])
    limit = THIN * max(L, H)
    thin = [False] * len(verts)
    for v in me.vertices:
        n = v.normal
        hit = tree.ray_cast(v.co - n * 1e-5, -n, limit * 4)
        thin[v.index] = hit[3] is not None and hit[3] < limit
    near = [[] for _ in verts]
    for e in me.edges:
        a, b = e.vertices; near[a].append(b); near[b].append(a)
    for _ in range(2):          # a fin's rim looks along the sheet and sees nothing: it goes with its neighbours
        thin = [sum(thin[j] for j in near[i]) * 2 >= max(len(near[i]), 1) if near[i] else thin[i] for i in range(len(verts))]
    _thin.append((thin, near))
    return thin, near


def side_fins(ends):
    """A fish's pectoral fins: per side, the largest connected patch of fin that stands out from the front of the body.
    Returns {"L": [vertex indices], "R": [...]} with a side left out when it has none."""
    thin, near = thin_vertices()
    out = {}
    for side, sign in (("L", 1), ("R", -1)):
        want = set(i for i, p in enumerate(verts) if thin[i] and p.x * sign > 0.25 * half and 0.06 < along[i] < ends[2])
        best = []
        while want:
            stack, patch = [want.pop()], []
            while stack:
                i = stack.pop(); patch.append(i)
                for j in near[i]:
                    if j in want: want.remove(j); stack.append(j)
            reach = max(abs(verts[i].x) for i in patch)
            if len(patch) > len(best) and reach > 0.6 * half and sum(along[i] for i in patch) / len(patch) < ends[1] + 0.08: best = patch
        if len(best) >= 12: out[side] = best
    return out


def fin_joints(patch):
    """Root (the middle of the fin's inner quarter) and tip (the vertex furthest from it), as Blender vectors."""
    inner = sorted(patch, key=lambda i: abs(verts[i].x))[:max(3, len(patch) // 4)]
    root = sum((verts[i] for i in inner), Vector()) / len(inner)
    tip = max((verts[i] for i in patch), key=lambda p: (p - root).length)
    return root, tip


def place():
    """The joints from the mesh, and what was found on the way."""
    found = {"kind": kind, "length": round(L, 4), "height": round(H, 4), "width": round(W, 4)}
    chain = list(CHAINS[kind])
    if kind == "fish":
        # The tail fin starts where the body's thickness runs out; the bones are spread before and behind that.
        thin, n = thin_vertices()[0], 40
        solid = [[not thin[i] for i, a in enumerate(along) if k / n <= a <= (k + 1) / n] for k in range(n)]
        stem = max([(k + 1) / n for k in range(n) if solid[k] and sum(solid[k]) * 2 > len(solid[k])], default=0.8)
        stem = max(0.55, min(0.9, stem))
        ends = [0.0, 0.3 * stem, 0.6 * stem, 0.8 * stem, stem, (1 + stem) / 2, 1.0]
        found["tail_fin_from"] = round(stem, 3)
    elif kind == "ray":
        # The whip of the tail starts behind the disc, where the width has fallen to under a fifth of the span.
        prof = profile()
        widest = max(prof, key=lambda s: s[1])
        whip = next((u for u, w, _ in prof if u > widest[0] and w < 0.18 * widest[1]), 1.0)
        whip = max(0.4, min(0.9, whip - 0.5 / len(prof)))
        if 1 - whip > 0.2: ends = [0.0, 0.25 * whip, whip, whip + (1 - whip) / 3, whip + 2 * (1 - whip) / 3, 1.0]
        else: chain = chain[:3]; ends = [0.0, 0.25 * whip, whip, 1.0]
        found["tail_from"] = round(whip, 3); found["widest_at"] = round(widest[0], 3)
    else:
        ends = list(ENDS[kind])
    names = ["nose"] + [b.lower() for b in chain[1:]] + ["tail_tip"]
    joints = {name: centre(u) for name, u in zip(names, ends)}
    if upright:
        head = [i for i, a in enumerate(along) if a < ends[1]]
        joints["nose"] = gltf(min((verts[i] for i in head), key=lambda p: p.y))      # the tip of the snout
    joints["root"] = (0.0, 0.0, 0.0)
    joints["root_up"] = (0.0, 0.25 * H, 0.0)
    if kind == "fish":
        for side, patch in side_fins(ends).items():
            root, tip = fin_joints(patch)
            joints["fin_" + side.lower()] = gltf(root); joints["fin_%s_tip" % side.lower()] = gltf(tip)
        found["side_fins"] = sorted(k[4].upper() for k in joints if k in ("fin_l", "fin_r"))
    if kind == "ray":
        u = found["widest_at"]
        y = lo.y + u * L
        for side, sign in (("l", 1), ("r", -1)):
            def at(x):
                near = sorted(range(len(verts)), key=lambda i: (verts[i].x - x) ** 2 + (verts[i].y - y) ** 2)[:8]
                return gltf(Vector((x, y, sum(verts[i].z for i in near) / len(near))))
            joints["wing_" + side] = at(sign * WING[0] * half)
            joints["wing_%s_mid" % side] = at(sign * WING[1] * half)
            joints["wing_%s_tip" % side] = at(sign * half)
    return {k: [round(c, 5) for c in v] for k, v in joints.items()}, found, chain


if mode == "keep":
    kept = json.load(open(joints_path))
    joints = kept["joints"]
    chain = [b for b in CHAINS[kind] if b == "Head" or b.lower() in joints]
    common.log("joints kept from", joints_path)
else:
    joints, found, chain = place()
    with open(joints_path, "w") as f:
        json.dump({"joints": joints, "found": found, "kind": kind, "axes": "glTF metres: x left, y up, z forward"}, f, indent=2)
    common.log("joints placed from the mesh for a %s: %s; written to %s" % (kind, ", ".join("%s %s" % kv for kv in found.items() if kv[0] != "kind"), joints_path))

# Bones: name -> (parent, head joint, tail joint). Body and what is in front of it point forward, the tail bones back.
names = ["nose"] + [b.lower() for b in chain[1:]] + ["tail_tip"]
base = chain.index("Body")
BONES = [("Root", None, "root", "root_up")]
for k in range(base, -1, -1): BONES.append((chain[k], chain[k + 1] if k < base else "Root", names[k + 1], names[k]))
for k in range(base + 1, len(chain)): BONES.append((chain[k], chain[k - 1], names[k], names[k + 1]))
for side in ("L", "R"):
    s = side.lower()
    if "fin_" + s in joints: BONES.append(("Fin" + side, "Body", "fin_" + s, "fin_%s_tip" % s))
    if "wing_" + s in joints:
        BONES.append(("Wing%s1" % side, "Body", "wing_" + s, "wing_%s_mid" % s))
        BONES.append(("Wing%s2" % side, "Wing%s1" % side, "wing_%s_mid" % s, "wing_%s_tip" % s))
# Where each bone of the chain ends along it, from the joints (so joints moved by hand move the weights with them).
def place_along(p): return (hi.z - blender(p).z) / H if upright else (blender(p).y - lo.y) / L
ends = [0.0] + [max(0.0, min(1.0, place_along(joints[n]))) for n in names[1:-1]] + [1.0]
if any(b <= a for a, b in zip(ends, ends[1:])): raise SystemExit("make: the chain's joints are out of order along the body in %s" % joints_path)


def chain_weights(u):
    """The one or two bones of the chain that hold a vertex at u."""
    k = max(i for i in range(len(chain)) if ends[i] <= u or i == 0)
    k = min(k, len(chain) - 1)
    size = [b - a for a, b in zip(ends, ends[1:])]
    if k > 0:
        h = BLEND * min(size[k - 1], size[k])
        if u < ends[k] + h:
            w = 0.5 + 0.5 * (u - ends[k]) / h
            return {chain[k]: w, chain[k - 1]: 1 - w}
    if k < len(chain) - 1:
        h = BLEND * min(size[k], size[k + 1])
        if u > ends[k + 1] - h:
            w = 0.5 + 0.5 * (ends[k + 1] - u) / h
            return {chain[k]: w, chain[k + 1]: 1 - w}
    return {chain[k]: 1.0}


weights = [chain_weights(u) for u in along]
report = []
# A fish's side fins: each takes its own patch, from nothing at its root to all of it from under halfway out.
fins = side_fins(ends) if kind == "fish" and any(k.startswith("fin_") for k in joints) else {}
for side, patch in fins.items():
    s = side.lower()
    if "fin_" + s not in joints: continue
    root, tip = blender(joints["fin_" + s]), blender(joints["fin_%s_tip" % s])
    axis = tip - root
    for i in patch:
        f = smooth((verts[i] - root).dot(axis) / max(axis.length_squared, 1e-12) / 0.45)
        if f <= 0: continue
        weights[i] = {b: w * (1 - f) for b, w in weights[i].items()}
        weights[i]["Fin" + side] = f
    report.append("Fin%s holds %d vertices" % (side, len(patch)))
# A ray's wings: by how far out a vertex is, whatever the chain says of it.
if any(k.startswith("wing_") for k in joints):
    for i, p in enumerate(verts):
        side = "L" if p.x > 0 else "R"
        x = abs(p.x) / max(half, 1e-9)
        outer = smooth((x - (WING[1] - 0.14)) / 0.28)
        inner = smooth((x - (WING[0] - 0.10)) / 0.20) * (1 - outer)
        if inner + outer <= 0: continue
        weights[i] = {b: w * (1 - inner - outer) for b, w in weights[i].items()}
        if inner > 0: weights[i]["Wing%s1" % side] = inner
        if outer > 0: weights[i]["Wing%s2" % side] = outer
    report.append("wings from %.0f%% of the half span" % (100 * WING[0]))

# The armature.
data = bpy.data.armatures.new("Skeleton")
rig = bpy.data.objects.new("Skeleton", data)
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
for o in bpy.context.scene.objects: o.select_set(o is rig)
bpy.ops.object.mode_set(mode="EDIT")
for name, parent, head, tail in BONES:
    b = data.edit_bones.new(name)
    b.head, b.tail = blender(joints[head]), blender(joints[tail])
    if (b.tail - b.head).length < 1e-4: b.tail = b.head + Vector((0, 0, 0.005))
    if parent: b.parent = data.edit_bones[parent]; b.use_connect = False
    b.align_roll(Vector((0, -1, 0)) if abs((b.tail - b.head).normalized().y) < 0.9 else Vector((0, 0, 1)))
bpy.ops.object.mode_set(mode="OBJECT")
data.bones["Root"].use_deform = False

# Weights: the four largest of each vertex, made to sum to one.
mesh.vertex_groups.clear()
groups = {name: mesh.vertex_groups.new(name=name) for name, _, _, _ in BONES if name != "Root"}
most = 0
for i, held in enumerate(weights):
    top = sorted(((w, b) for b, w in held.items() if w > 1e-4), reverse=True)[:4]
    total = sum(w for w, _ in top)
    for w, b in top: groups[b].add([i], w / total, "REPLACE")
    most = max(most, len(top))
lonely = sum(1 for v in mesh.data.vertices if not any(g.weight > 1e-4 for g in v.groups))
common.log("weights from the chain (%s)%s" % (", ".join("%s to %.2f" % (b, e) for b, e in zip(chain, ends[1:])), "".join("; " + r for r in report)))
common.log("%d vertices had no weight; at most %d bones a vertex" % (lonely, most))
if lonely: raise SystemExit("make: %d of %d vertices have no bone" % (lonely, len(verts)))
mesh.parent = rig
if not any(m.type == "ARMATURE" for m in mesh.modifiers):
    m = mesh.modifiers.new("Skeleton", "ARMATURE"); m.object = rig
# What the clips step reads: the kind, the chain and the sizes its moves are scaled by.
rig["qrx_rig"] = json.dumps({"kind": kind, "chain": chain, "length": L, "height": H, "width": W, "bones": [b[0] for b in BONES]})
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
for o in bpy.context.scene.objects: o.select_set(o in (mesh, rig))
bpy.ops.export_scene.gltf(filepath=os.path.join(os.path.dirname(out_blend), "rig-%s.glb" % rigger), use_selection=True, export_format="GLB",
                          export_skins=True, export_animations=False, export_def_bones=False, export_image_format="JPEG")
with open(os.path.join(os.path.dirname(out_blend), "rig.json"), "w") as f:
    json.dump({"rigger": rigger, "joints": mode, "kind": kind, "turned": turned, "unweighted_fixed": lonely, "max_influences": most,
               "bones": [b[0] for b in BONES]}, f, indent=2)
