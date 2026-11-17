"""make.py's rig step for the flyer shape, in Blender: butterflies, moths and dragonflies pictured from above with
their wings spread. The mesh is laid flat first (below), then a skeleton is placed from it and every vertex is
weighted by where it is, at most four bones a vertex.

    blender -b -P blender_rig_flyer.py -- <clean.blend> <rig.blend> <joints.json> <place|keep> <template|unirig> <unirig-skin.npz>

Same arguments as blender_rig.py. place: the lie of the mesh and the joints are found from the mesh and written to
joints.json (a kept art/<id>/joints.json is never overwritten: make.py passes "keep" for it, and its lie, joints and
measures are used as they are, so a wrong guess is fixed by hand once). The rigger makes no difference here: the
weights are always by geometry (bone heat fails on sheets as thin as a wing, and UniRig knows no insects).

Laying flat. The clean step turns a mesh by where a standing animal's head is, which says nothing about an insect
seen from above: it may leave it head first or tail first, a few degrees askew, or standing on a wing tip. Here the
thin side is turned to the vertical with the pictured side up, the body's line (the line the outline mirrors about)
is laid along the head's axis with the head forward, and the origin is put at the middle of the thorax: a flier's
origin is at mid-body, not on the ground. Root is there.

Bones: Root; Body (the thorax), Head, Abdomen1 and Abdomen2 (a dragonfly: Abdomen3 too) down the body; WingFL,
WingFR, WingBL, WingBR hinged along the body at the thorax's sides (a butterfly's forewing and hindwing are one
sheet: the two bones share its hinge line and blend across the notch between the wings).

Joint positions are in glTF metres: x the animal's left, y up, z forward (where the head points)."""
import json, math, os, sys
import bpy
import numpy as np
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_common as common      # noqa: E402

clean, out_blend, joints_path, mode, rigger, unirig_npz = common.args()
bpy.ops.wm.open_mainfile(filepath=clean)
mesh = bpy.data.objects["Mesh"]
for o in list(bpy.context.scene.objects):
    if o is not mesh: bpy.data.objects.remove(o)
creature = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(clean)))))

# The sub-kinds. A creature not listed is told by its proportions: a dragonfly's body is most of its length.
KINDS = {
    "arctic-skipper": "butterfly", "emerald-swallowtail": "butterfly", "glasswing": "butterfly", "meadow-white": "butterfly",
    "harvest-moon-moth": "moth", "lamp-moth": "moth", "nightshade-moth": "moth", "snow-moth": "moth",
    "boreal-emerald": "dragonfly", "neon-darter": "dragonfly", "pond-skimmer": "dragonfly", "ruby-darter": "dragonfly",
}
# Along the body from the front of the head (0) to the end of the abdomen (1): where the neck and the waist are.
BODY = {"butterfly": (0.15, 0.45), "moth": (0.15, 0.50), "dragonfly": (0.14, 0.36)}
ABDOMEN = {"butterfly": 2, "moth": 2, "dragonfly": 3}
WINGS = ("WingFL", "WingFR", "WingBL", "WingBR")
SPLIT = {"butterfly": 12.0, "moth": 12.0, "dragonfly": 5.0}    # degrees behind straight out, when no notch is found
# The mesher and the picture. It lays most top views flat itself, the pictured side up and the picture's left at
# the raw mesh's -x (glTF axes); one it leaves standing as it was pictured faces PICTURED. The briefs ask for the
# head at the picture's left.
PICTURED = (0.0, 0.0, 1.0)


def gltf(v): return (v[0], v[2], -v[1])              # Blender -> glTF
def blender(p): return Vector((p[0], -p[2], p[1]))   # glTF -> Blender


def mesh_arrays():
    me = mesh.data
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    me.calc_loop_triangles()
    tris = np.empty(len(me.loop_triangles) * 3, dtype=np.int32); me.loop_triangles.foreach_get("vertices", tris)
    edges = np.empty(len(me.edges) * 2, dtype=np.int32); me.edges.foreach_get("vertices", edges)
    return co, tris.reshape(-1, 3), edges.reshape(-1, 2)


def samples(co, tris, n=240000):
    """Points spread evenly over the surface (the same ones every run): vertices alone are too few to measure by."""
    a, b, c = co[tris[:, 0]], co[tris[:, 1]], co[tris[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    rng = np.random.default_rng(0)
    pick = rng.choice(len(tris), n, p=area / area.sum())
    u, v = rng.random(n), rng.random(n)
    over = u + v > 1
    u[over], v[over] = 1 - u[over], 1 - v[over]
    return a[pick] + u[:, None] * (b[pick] - a[pick]) + v[:, None] * (c[pick] - a[pick])


def mirror_score(along, across, reach, cells=72):
    """How much of the outline lies on its own mirror image about the line across = 0 (1: all of it)."""
    h, _, _ = np.histogram2d(along, across, bins=(cells, cells), range=((-reach, reach), (-reach, reach)))
    return float(np.minimum(h, h[:, ::-1]).sum() / max(h.sum(), 1.0))


def hint():
    """Where the clean step left the picture's left (the head, by the brief) and the pictured side, in Blender's axes;
    None when clean.json is not there. The raw mesh's glTF (x, y, z) is Blender's (x, -z, y), then clean's turn."""
    path = os.path.join(os.path.dirname(clean), "clean.json")
    if not os.path.exists(path): return None
    turn = math.radians(json.load(open(path)).get("turn", 0.0))
    spin = np.array(Matrix.Rotation(turn, 3, "Z"))
    left = spin @ np.array((-1.0, 0.0, 0.0))
    pictured = spin @ np.array((PICTURED[0], -PICTURED[2], PICTURED[1]))
    return left, pictured


def lie(points):
    """The turn (3x3, Blender axes) that lays the insect flat: rows are its left, its back end and its upper side."""
    centre = points.mean(0)
    p = points - centre
    values, vectors = np.linalg.eigh(np.cov(p.T))
    thin, e1, e2 = vectors[:, 0], vectors[:, 2], vectors[:, 1]
    flatness = math.sqrt(values[0] / values[1])
    u, v = p @ e1, p @ e2
    reach = float(np.hypot(u, v).max())

    def score(degrees, shift=0.0):
        a = math.radians(degrees)
        return mirror_score(u * math.cos(a) + v * math.sin(a), -u * math.sin(a) + v * math.cos(a) - shift, reach)
    best = max(np.arange(0.0, 180.0, 3.0), key=score)
    best = max(np.arange(best - 3.0, best + 3.01, 0.5), key=score)
    shift = 0.0
    for _ in range(2):
        shift = max(np.linspace(shift - 0.03 * reach, shift + 0.03 * reach, 25), key=lambda s: score(best, s))
        best = max(np.arange(best - 1.5, best + 1.51, 0.25), key=lambda d: score(d, shift))
    a = math.radians(best)
    axis = e1 * math.cos(a) + e2 * math.sin(a)                 # along the body, either way round
    centre = centre + shift * (-e1 * math.sin(a) + e2 * math.cos(a))     # onto the mirror line
    other = score(best + 90.0)
    facts = {"flatness": round(flatness, 3), "mirror": round(score(best, shift), 3), "mirror_across": round(other, 3)}
    h = hint()
    if h is not None:
        left, pictured = h
        if abs(float(thin[2])) > 0.8: pictured = np.array((0.0, 0.0, 1.0))     # the mesher laid it flat itself, pictured side up
        if abs(float(axis @ left)) < 0.5:
            common.log("the line the outline mirrors about is across the picture, not along it: the head's end is taken from the body's shape")
            h = None
        else:
            if axis @ left < 0: axis = -axis
            if thin @ pictured < 0: thin = -thin
            if abs(float(thin @ pictured)) < 0.8: common.log("the thin side is not the picture's depth (%.2f): check which side is up" % abs(float(thin @ pictured)))
    facts["head"] = "the picture's left" if h is not None else "the body's shape"
    side = np.cross(thin, axis)                                 # left = up x forward
    turn = np.array((side, -axis, thin))
    return turn, centre, facts, h is None


def measure(points, kind):
    """The body, in the laid mesh (x left, y back, z up): where it starts and ends, how wide and thick it is."""
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    half = float(np.abs(x).max())
    cell = 2 * half / 200
    ix = np.round(x / cell).astype(int); iy = np.floor((y - y.min()) / cell).astype(int)
    nx, ny = int(ix.max() - ix.min() + 1), int(iy.max() + 1)
    lo = np.full((ny, nx), np.inf); hi = np.full((ny, nx), -np.inf)
    np.minimum.at(lo, (iy, ix - ix.min()), z); np.maximum.at(hi, (iy, ix - ix.min()), z)
    thick = np.where(np.isfinite(lo), hi - lo, 0.0)
    filled = np.isfinite(lo)
    mid = -int(ix.min())                                       # the column of x = 0
    strip = slice(mid - 2, mid + 3)
    centre = thick[:, strip].max(1)
    smooth = np.convolve(centre, np.ones(5) / 5, mode="same")
    wing = float(np.median(thick[filled & (np.abs(np.arange(nx) - mid)[None, :] * cell > 0.3 * half)])) if filled.any() else 0.0
    peak = int(smooth.argmax())
    # The body: rows about the thickest one whose middle is filled (a dragonfly's abdomen is hardly thicker than a
    # wing), and for a butterfly, whose hindwings may close behind the abdomen, thicker than a wing too.
    def body_row(r): return filled[r, strip].any() and (kind == "dragonfly" or smooth[r] > max(1.5 * wing, 0.12 * smooth[peak]))
    first = last = peak
    gap = 0
    for r in range(peak - 1, -1, -1):
        if body_row(r): first = r; gap = 0
        else:
            gap += 1
            if gap > 2: break
    gap = 0
    for r in range(peak + 1, ny):
        if body_row(r): last = r; gap = 0
        else:
            gap += 1
            if gap > 2: break
    y0, y1 = y.min() + first * cell, y.min() + (last + 1) * cell
    length = y1 - y0
    neck, waist = (y0 + f * length for f in BODY[kind])
    rows = [r for r in range(first, last + 1) if neck <= y.min() + (r + 0.5) * cell <= waist]
    # The thorax's half width: going out from the middle, where the thickness has fallen to half the middle's.
    widths = []
    for r in rows:
        k = 0
        while mid + k + 1 < nx and mid - k - 1 >= 0 and max(thick[r, mid + k + 1], thick[r, mid - k - 1]) > 0.5 * centre[r]: k += 1
        widths.append((k + 0.5) * cell)
    width = float(np.median(widths)) if widths else 0.04 * half
    width = min(max(width, 0.03 * half), 0.2 * half)
    def middle(yy):
        r = min(max(int((yy - y.min()) / cell), 0), ny - 1)
        cells = [c for c in range(mid - 2, mid + 3) if filled[r, c]]
        return float(np.mean([(lo[r, c] + hi[r, c]) / 2 for c in cells])) if cells else 0.0
    return {"half": half, "y0": float(y0), "y1": float(y1), "neck": float(neck), "waist": float(waist), "width": width,
            "wing_thick": wing, "body_thick": float(smooth[peak]), "thick_at": float(y.min() + (peak + 0.5) * cell),
            "z": middle((neck + waist) / 2), "z_head": middle((y0 + neck) / 2), "z_tail": middle(y1 - 0.1 * length)}


def head_by_shape(points):
    """True when the head is at the -y end of the laid mesh, told from the body alone: the thorax and head, the
    thickest part of the body, are nearer the head's end than the abdomen's (for a dragonfly, by far)."""
    m = measure(points, "dragonfly")
    return m["thick_at"] < (m["y0"] + m["y1"]) / 2


def split_angle(points, m, kind, sign):
    """Degrees behind straight out from the thorax's side where the forewing ends and the hindwing begins on one side:
    the deepest notch in the wings' outline as seen from the wing's root."""
    x, y = points[:, 0] * sign, points[:, 1]
    out = x > m["width"]
    angle = np.degrees(np.arctan2(y[out] - (m["neck"] + m["waist"]) / 2, x[out] - m["width"]))
    far = np.hypot(y[out] - (m["neck"] + m["waist"]) / 2, x[out] - m["width"])
    edges = np.arange(-90.0, 90.01, 4.0)
    reach = np.zeros(len(edges) - 1)
    which = np.clip(np.digitize(angle, edges) - 1, 0, len(reach) - 1)
    np.maximum.at(reach, which, far)
    reach = np.convolve(np.pad(reach, 1, mode="edge"), np.ones(3) / 3, mode="valid")
    centres = (edges[:-1] + edges[1:]) / 2
    best, depth = None, 0.06 * m["half"]
    for i in range(1, len(reach) - 1):
        if not -40.0 <= centres[i] <= 60.0: continue
        d = min(reach[:i].max(), reach[i + 1:].max()) - reach[i]
        if d > depth: best, depth = centres[i], d
    return (float(best), True) if best is not None else (SPLIT[kind], False)


# ---- the lie of the mesh, the kind, the measures and the joints
mesh.data.transform(mesh.matrix_world); mesh.matrix_world = Matrix.Identity(4)
co, tris, edges = mesh_arrays()
if mode == "keep":
    kept = json.load(open(joints_path))
    joints, found = kept["joints"], kept["found"]
    kind = found["kind"]
    lay = Matrix(found["lay"])
    mesh.data.transform(lay); mesh.data.update()
    co, tris, edges = mesh_arrays()
    common.log("lie, joints and measures kept from", joints_path)
else:
    cloud = samples(co, tris)
    turn, centre, facts, unsure = lie(cloud)
    laid = (cloud - centre) @ turn.T
    if unsure and not head_by_shape(laid):
        turn = np.array((-turn[0], -turn[1], turn[2])); laid = (cloud - centre) @ turn.T
    told = head_by_shape(laid)
    if not told: common.log("the body's shape says the head is at the other end (its thickest part is nearer the tail): look at look-rigged-top.png")
    kind = KINDS.get(creature)
    if kind is None:
        m = measure(laid, "dragonfly")
        kind = "dragonfly" if (m["y1"] - m["y0"]) > 0.8 * (laid[:, 1].max() - laid[:, 1].min()) and m["half"] * 2 < 1.6 * (m["y1"] - m["y0"]) else "butterfly"
        common.log("%s is in no table here: taken for a %s by its proportions" % (creature, kind))
    m = measure(laid, kind)
    # The origin: the middle of the thorax.
    origin = np.array((0.0, (m["neck"] + m["waist"]) / 2, m["z"]))
    lay = Matrix.Translation(Vector(-origin)) @ Matrix(turn).to_4x4() @ Matrix.Translation(Vector(-centre))
    mesh.data.transform(lay); mesh.data.update()
    laid = laid - origin
    for k in ("y0", "y1", "neck", "waist", "thick_at"): m[k] -= origin[1]
    for k in ("z", "z_head", "z_tail"): m[k] -= origin[2]
    co, tris, edges = mesh_arrays()
    lo, hi = co.min(0), co.max(0)
    common.log("laid flat (%s): thin side %.3f of the next, mirrors about its body %.2f (across it %.2f), head from %s; box %s to %s m"
               % (kind, facts["flatness"], facts["mirror"], facts["mirror_across"], facts["head"],
                  tuple(round(float(c), 4) for c in lo), tuple(round(float(c), 4) for c in hi)))
    length = m["y1"] - m["y0"]
    common.log("body %.3f m of %.3f (head to %.3f, thorax to %.3f), half width %.4f, thickness %.4f (a wing %.4f), span %.3f m"
               % (length, hi[1] - lo[1], m["neck"] - m["y0"], m["waist"] - m["y0"], m["width"], m["body_thick"], m["wing_thick"], 2 * m["half"]))
    splits = {}
    for side, sign in (("L", 1), ("R", -1)):
        splits[side], notch = split_angle(laid, m, kind, sign)
        common.log("wings %s: the forewing ends %.0f degrees behind straight out (%s)" % (side, splits[side], "the notch in the outline" if notch else "no notch found: the usual place"))
    w, zw = m["width"], 0.0
    near = laid[(np.abs(laid[:, 0]) > w) & (np.abs(laid[:, 0]) < 3 * w) & (laid[:, 1] > m["neck"]) & (laid[:, 1] < m["waist"])]
    if len(near): zw = float(np.median(near[:, 2]))
    third = (m["waist"] - m["neck"]) / 3
    def b2g(x, y, z): return [round(float(c), 5) for c in gltf((x, y, z))]
    joints = {"root": b2g(0, 0, 0), "root_up": b2g(0, 0, 0.1 * length),
              "waist": b2g(0, m["waist"], 0), "neck": b2g(0, m["neck"], 0), "nose": b2g(0, m["y0"], m["z_head"])}
    n = ABDOMEN[kind]
    for i in range(n + 1):
        t = i / n
        joints["abdomen%d" % i] = b2g(0, m["waist"] + t * (m["y1"] - m["waist"]), t * m["z_tail"])
    for name in WINGS:
        sign = 1 if name.endswith("L") else -1
        yy = -third / 2 if name[4] == "F" else third / 2
        reach = np.abs(laid[laid[:, 0] * sign > 0][:, 0]).max()
        joints["wing_" + name[4:]] = b2g(sign * w, yy, zw)
        joints["wing_%s_tip" % name[4:]] = b2g(sign * float(reach), yy, zw)
    found = {"kind": kind, "width": round(m["width"], 5), "span": round(2 * m["half"], 5), "length": round(float(length), 5),
             "split": {k: round(v, 1) for k, v in splits.items()}, "lay": [[round(float(c), 6) for c in row] for row in lay], **facts}
    with open(joints_path, "w") as f:
        json.dump({"joints": joints, "found": found, "axes": "glTF metres: x left, y up, z forward; lay is the turn (Blender axes) that laid clean.blend's mesh flat"}, f, indent=2)
    common.log("joints placed from the mesh, written to %s" % joints_path)

BONES = [("Root", None, "root", "root_up"), ("Body", "Root", "waist", "neck"), ("Head", "Body", "neck", "nose")]
BONES += [("Abdomen%d" % (i + 1), "Body" if i == 0 else "Abdomen%d" % i, "abdomen%d" % i, "abdomen%d" % (i + 1)) for i in range(ABDOMEN[kind])]
BONES += [(name, "Body", "wing_" + name[4:], "wing_%s_tip" % name[4:]) for name in WINGS]

# ---- the armature
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
    b.align_roll(Vector((0, 0, 1)) if abs((b.tail - b.head).normalized().z) < 0.9 else Vector((0, -1, 0)))
bpy.ops.object.mode_set(mode="OBJECT")
data.bones["Root"].use_deform = False
rig["kind"], rig["span"], rig["length"] = kind, float(found["span"]), float(found["length"])

# ---- weights, by where each vertex is. Down the body: Head, Body, the abdomen's pieces, each fading into the next
# about the joint between them. Out from the thorax's side: the wings, fading in over a short band so the root bends
# and does not crease; fore and hind by the angle seen from the wing's root.
x, y = co[:, 0], co[:, 1]
width = float(found["width"])
cuts = [blender(joints["neck"]).y, blender(joints["waist"]).y] + [blender(joints["abdomen%d" % i]).y for i in range(1, ABDOMEN[kind])]
ends = [blender(joints["nose"]).y] + cuts + [blender(joints["abdomen%d" % ABDOMEN[kind]]).y]
chain_names = ["Head", "Body"] + ["Abdomen%d" % (i + 1) for i in range(ABDOMEN[kind])]
chain = np.zeros((len(co), len(chain_names)))
chain[:, 0] = 1.0
for i, cut in enumerate(cuts):
    fade = 0.2 * min(ends[i + 1] - ends[i], ends[i + 2] - ends[i + 1])
    t = np.clip((y - (cut - fade)) / (2 * fade), 0.0, 1.0)
    t = t * t * (3 - 2 * t)                                 # how far past this joint
    chain[:, i + 1] = t
for i in range(len(chain_names) - 1): chain[:, i] -= chain[:, i + 1]     # each piece: past its joint, not yet past the next

# A wing vertex: outside the thorax's width, in a piece of surface (of what lies outside it) that reaches well out.
# Legs and feelers reach a little way and stay with the body.
outside = np.abs(x) > width
parent_of = np.arange(len(co))
def find(i):
    while parent_of[i] != i:
        parent_of[i] = parent_of[parent_of[i]]; i = parent_of[i]
    return i
for a, b in edges[outside[edges[:, 0]] & outside[edges[:, 1]] & (x[edges[:, 0]] * x[edges[:, 1]] > 0)]:
    ra, rb = find(a), find(b)
    if ra != rb: parent_of[ra] = rb
roots = np.array([find(i) for i in range(len(co))])
half = float(found["span"]) / 2
is_wing = np.zeros(len(co), dtype=bool)
pieces = 0
for r in np.unique(roots[outside]):
    members = (roots == r) & outside
    if np.abs(x[members]).max() > 0.4 * half: is_wing |= members; pieces += 1
band = 0.8 * width
out = np.clip((np.abs(x) - width) / band, 0.0, 1.0)
out = np.where(is_wing, out * out * (3 - 2 * out), 0.0)
angle = np.degrees(np.arctan2(y, np.abs(x) - width))
split = np.where(x > 0, found["split"]["L"], found["split"]["R"])
BLEND = 9.0                                                 # degrees either side of the split
fore = np.clip((split + BLEND - angle) / (2 * BLEND), 0.0, 1.0)
fore = fore * fore * (3 - 2 * fore)
weights = {name: chain[:, i] * (1 - out) for i, name in enumerate(chain_names)}
weights["WingFL"] = out * fore * (x > 0); weights["WingBL"] = out * (1 - fore) * (x > 0)
weights["WingFR"] = out * fore * (x <= 0); weights["WingBR"] = out * (1 - fore) * (x <= 0)
names = list(weights)
table = np.stack([weights[n] for n in names], axis=1)
table[table < 1e-3] = 0.0
keep = np.argsort(-table, axis=1)[:, :4]                    # by construction no vertex has more than four; this holds it
limited = np.zeros_like(table); rows = np.arange(len(co))[:, None]
limited[rows, keep] = table[rows, keep]
lonely = int((limited.sum(1) < 1e-6).sum())
limited[limited.sum(1) < 1e-6, names.index("Body")] = 1.0
limited /= limited.sum(1, keepdims=True)
for j, name in enumerate(names):
    group = mesh.vertex_groups.new(name=name)
    for i in np.nonzero(limited[:, j] > 0)[0]: group.add([int(i)], float(limited[i, j]), "REPLACE")
most = int((limited > 0).sum(1).max())
common.log("weights by geometry (%s): %d wing pieces, %s" % ("the rigger asked for is %s, which knows no wings" % rigger if rigger != "template" else "no bone heat",
                                                             pieces, ", ".join("%s %d" % (n, int((limited[:, j] > 0.5).sum())) for j, n in enumerate(names))))
common.log("%d vertices had no weight and took Body's; at most %d bones a vertex" % (lonely, most))
if pieces < 2 or min(int((limited[:, names.index(n)] > 0.5).sum()) for n in WINGS) == 0:
    raise SystemExit("make: a wing has no vertices of its own (the wings were not told from the body); place the joints by hand in %s" % joints_path)

mesh.parent = rig
m = mesh.modifiers.new("Skeleton", "ARMATURE"); m.object = rig
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
for o in bpy.context.scene.objects: o.select_set(o in (mesh, rig))
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=os.path.join(os.path.dirname(out_blend), "rig-%s.glb" % rigger), use_selection=True, export_format="GLB",
                          export_skins=True, export_animations=False, export_def_bones=False, export_image_format="JPEG")
with open(os.path.join(os.path.dirname(out_blend), "rig.json"), "w") as f:
    json.dump({"rigger": "geometry", "shape": "flyer", "kind": kind, "joints": mode, "unweighted_fixed": lonely, "max_influences": most,
               "bones": [b[0] for b in BONES]}, f, indent=2)
