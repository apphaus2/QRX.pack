"""make.py's rig step for the bird shape, in Blender: a skeleton placed from the mesh and skin weights, at most four a
vertex. Two kinds, by the creature's id (KINDS below) or, for an id not listed, by the mesh's proportions:

  bird   stands side-on on two legs, wings folded against the body.
         Root, Body, Neck, Head, Tail1, Tail2, WingL, WingLTip, WingR, WingRTip, LegL, ShinL, FootL, LegR, ShinR, FootR
  bat    pictured in flight, wings spread.
         Root, Body, Head, Tail1, WingL, WingLTip, WingR, WingRTip

    blender -b -P blender_rig_bird.py -- <clean.blend> <rig.blend> <joints.json> <place|keep> <template|unirig> <unirig-skin.npz>

The arguments are blender_rig.py's. place: the joints are found from the mesh and written to joints.json (a kept
art/<id>/joints.json is never overwritten: make.py passes "keep" for it, and its joints are used as they are, so a wrong
guess is fixed by hand once). Weights are Blender's automatic (bone heat) weights for both riggers: UniRig's weights are
for the quadruped skeleton, so "unirig" is logged and done as "template".

A bird's folded wing is only a picture on the side of its body: lifting those faces would tear the body or drag a web
of skin behind them. So the body is left whole and each wing is a thin copy of the faces under the folded wing, lying
just outside them, weighted to the wing's two bones and to Body at its shoulder. At rest it sits on the body and looks
like the picture; in a clip it opens as a wing with two sides, and the body under it is still closed and feathered.
A bat's wings are already there, spread: they take bone heat like the rest.

Joint positions are in glTF metres: x the animal's left, y up, z forward (where the head points)."""
import json, math, os, sys
import bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_common as common      # noqa: E402

clean, out_blend, joints_path, mode, rigger, unirig_npz = common.args()
creature = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(clean)))))
bpy.ops.wm.open_mainfile(filepath=clean)
mesh = bpy.data.objects["Mesh"]
for o in list(bpy.context.scene.objects):
    if o is not mesh: bpy.data.objects.remove(o)

KINDS = {"chimney-bat": "bat", "dusk-bat": "bat"}          # every other id of this shape is a bird, unless it is far wider than long

BAT_TURNS = {}             # id -> degrees, for a bat whose head the quarter turn below would put at the wrong end

LEGS = ("L", "R")
BIRD_BONES = [
    ("Root", None, "root", "root_up"),
    ("Body", "Root", "hips", "chest"),
    ("Neck", "Body", "neck", "skull"),
    ("Head", "Neck", "skull", "nose"),
    ("Tail1", "Body", "tail0", "tail1"),
    ("Tail2", "Tail1", "tail1", "tail2"),
] + [b for s in LEGS for b in (
    ("Wing" + s, "Body", "wing_" + s, "wing_mid_" + s),
    ("Wing" + s + "Tip", "Wing" + s, "wing_mid_" + s, "wing_tip_" + s),
    ("Leg" + s, "Body", "top_" + s, "mid_" + s),
    ("Shin" + s, "Leg" + s, "mid_" + s, "low_" + s),
    ("Foot" + s, "Shin" + s, "low_" + s, "toe_" + s))]
BAT_BONES = [
    ("Root", None, "root", "root_up"),
    ("Body", "Root", "hips", "chest"),
    ("Head", "Body", "skull", "nose"),
    ("Tail1", "Body", "tail0", "tail1"),
] + [b for s in LEGS for b in (
    ("Wing" + s, "Body", "wing_" + s, "wing_mid_" + s),
    ("Wing" + s + "Tip", "Wing" + s, "wing_mid_" + s, "wing_tip_" + s))]

# A bird's folded wing, on the side of the body, in the body's own frame: u runs from the root of the tail (0) to the
# base of the neck (1), v from the middle of the side towards the back, in half thicknesses of the body.
WING_U = (-0.12, 0.84)        # from just over the root of the tail to the shoulder
WING_LOW = (0.30, -0.20)      # the lower edge's v at the tail end and at its lowest, under the shoulder
WING_FRONT = 0.58             # ahead of this u the lower edge rounds up to the shoulder
WING_FACING = 0.25            # a face is on the side when its normal leans this far outward
WING_GAP = 0.006              # how far outside the body the wing lies, of the creature's length
WING_THICK = 0.004            # how thick the wing is, of the creature's length


def gltf(v): return (v.x, v.z, -v.y)                 # Blender -> glTF
def blender(p): return Vector((p[0], -p[2], p[1]))   # glTF -> Blender


def mean(pts): return tuple(sum(c) / len(pts) for c in zip(*pts))
def lerp(a, b, t): return tuple(p + (q - p) * t for p, q in zip(a, b))
def sub(a, b): return tuple(p - q for p, q in zip(a, b))
def unit(a):
    n = math.sqrt(sum(c * c for c in a)) or 1.0
    return tuple(c / n for c in a)


def measure():
    global points, tris, xs, ys, zs, H, L, W, S
    points = [gltf(mesh.matrix_world @ v.co) for v in mesh.data.vertices]
    tris = [[points[i] for i in p.vertices] for p in mesh.data.polygons]
    xs, ys, zs = zip(*points)
    H, L, W = max(ys), max(zs) - min(zs), max(xs) - min(xs)
    S = max(H, L, W)


measure()
kind = KINDS.get(creature) or ("bat" if W > 1.15 * L else "bird")
if kind == "bat" and (L > 1.15 * W or creature in BAT_TURNS):
    # The clean step lays the longest side along the body, and a bat in flight is widest across its wings: turn it
    # a quarter so the wings lie to the sides. The head is the end the wings do not trail towards.
    core = [p for p in points if abs(p[2]) < 0.12 * L]
    outer = [p for p in points if abs(p[2]) > 0.25 * L]
    middle = (min(p[0] for p in core) + max(p[0] for p in core)) / 2
    head_x = -1 if sum(p[0] for p in outer) / len(outer) > middle else 1
    quarter = BAT_TURNS.get(creature, -90 * head_x)             # degrees about the vertical, glTF +x towards +z
    from mathutils import Matrix
    mesh.data.transform(mesh.matrix_world.inverted() @ Matrix.Rotation(math.radians(quarter), 4, "Z") @ mesh.matrix_world)
    mesh.data.update()
    measure()
    common.log("the wings lay along the body's axis: turned %d degrees about the vertical (make.py --turn at the clean step is the lasting fix)" % quarter)
common.log("%s is rigged as a %s (%.3f long, %.3f wide, %.3f tall)" % (creature, kind, L, W, H))
BONES = BAT_BONES if kind == "bat" else BIRD_BONES


def slice_at(h):
    """Where the surface crosses the height h: (x, z) points on each triangle edge that crosses it."""
    out = []
    for t in tris:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            if (a[1] - h) * (b[1] - h) < 0:
                s = (h - a[1]) / (b[1] - a[1])
                out.append((a[0] + s * (b[0] - a[0]), a[2] + s * (b[2] - a[2])))
    return out


def groups(values, gap):
    values = sorted(values); out = [[values[0]]] if values else []
    for v in values[1:]:
        if v - out[-1][-1] > gap: out.append([v])
        else: out[-1].append(v)
    return out


def body_frame(joints):
    """The body's side-on frame from the tail's root to the neck's base: origin, the axis, the way to the back (both in
    (y, z)) and the axis's length."""
    t0, n = joints["tail0"], joints["neck"]
    ay, az = n[1] - t0[1], n[2] - t0[2]
    length = math.hypot(ay, az) or 1e-6
    ay, az = ay / length, az / length
    return t0, (ay, az), (az, -ay), length        # level and facing +z, the back is up; upright, the back is behind


def uv_of(p, frame):
    t0, (ay, az), (dy, dz), length = frame
    y, z = p[1] - t0[1], p[2] - t0[2]
    return (y * ay + z * az) / length, y * dy + z * dz


def body_band(joints, frame):
    """Across the body's side, between the belly and the back: the middle's v and the half thickness."""
    vs = sorted(uv_of(p, frame)[1] for p in points if 0.15 < uv_of(p, frame)[0] < 0.85 and p[1] > joints["mid_L"][1])
    if not vs: return 0.0, 0.2 * S
    lo, hi = vs[int(0.03 * (len(vs) - 1))], vs[int(0.97 * (len(vs) - 1))]
    return (lo + hi) / 2, max((hi - lo) / 2, 0.05 * S)


def place_bird():
    """The joints of a standing bird: legs found by cutting below the belly, the head at the top and front, the tail
    the far end behind, the wings folded along each side."""
    centre_z = sum(zs) / len(zs)
    # The feet: of what touches the ground, the group nearest the middle (a long tail may touch it too).
    low = slice_at(0.04 * H) or [(p[0], p[2]) for p in points if p[1] < 0.06 * H]
    g = groups([p[1] for p in low], 0.05 * L)
    feet = min(g, key=lambda grp: abs((grp[0] + grp[-1]) / 2 - centre_z))
    fz0, fz1 = feet[0] - 0.03 * L, feet[-1] + 0.03 * L

    def leg_slice(h): return [p for p in slice_at(h) if fz0 - 0.04 * L <= p[1] <= fz1 + 0.04 * L]

    # The belly: going up, where what stands on the feet turns from two sticks into the body.
    extents, belly, h = [], None, 0.06 * H
    while h < 0.75 * H:
        pts = leg_slice(h)
        if pts:
            run = max(groups([p[1] for p in slice_at(h)], 0.03 * L), key=lambda grp: sum(1 for v in grp if fz0 <= v <= fz1))
            extent = max(run[-1] - run[0], max(p[0] for p in pts) - min(p[0] for p in pts))
            if not extents and extent > 0.3 * L: belly = h; common.log("no legs to see: the body sits on its feet"); break
            thin = min(extents) if extents else extent
            if extents and extent > max(2.5 * thin, 0.3 * L): belly = h; break
            extents.append(extent)
        h += 0.01 * H
    if belly is None: belly = 0.2 * H; common.log("found no belly above the legs: taken as a fifth of the height")
    belly = max(belly - 0.01 * H, 0.05 * H)

    def columns(h, seeds=None):
        """The two legs at height h, (x, z) each, left first: two clusters of the cut."""
        pts = leg_slice(h)
        if not pts: return None
        a, b = seeds or (max(pts, key=lambda p: p[0]), min(pts, key=lambda p: p[0]))
        for _ in range(6):
            near_a = [p for p in pts if math.dist(p, a) <= math.dist(p, b)] or [a]
            near_b = [p for p in pts if math.dist(p, a) > math.dist(p, b)] or [b]
            a, b = mean(near_a), mean(near_b)
        if a[0] < b[0]: a, b = b, a
        if a[0] - b[0] < 0.02 * L:                    # one stick, or one leg right behind the other
            mid = (a[0] + b[0]) / 2
            a, b = (mid + 0.02 * L, a[1]), (mid - 0.02 * L, b[1])
        return a, b

    joints = {}
    knee_h, ankle_h = 0.92 * belly, max(0.3 * belly, 0.035 * H)
    knee = columns(0.6 * belly)                      # the two sticks are clearest between the toes and the belly
    if knee is None: raise SystemExit("make: found no legs under the body; place the joints by hand in %s" % joints_path)
    ankle = columns(ankle_h, columns(0.45 * belly, knee) or knee) or knee
    knee = columns(knee_h, columns(0.75 * belly, knee) or knee) or knee
    leg_z = (knee[0][1] + knee[1][1]) / 2
    top_here = max((p[1] for p in points if abs(p[2] - leg_z) < 0.05 * L), default=H)
    for i, s in enumerate(LEGS):
        sign = 1 if s == "L" else -1
        kx, kz = knee[i]; ax, az = ankle[i]
        toes = [p for p in points if p[1] < ankle_h and fz0 <= p[2] <= fz1 and (p[0] - (ankle[0][0] + ankle[1][0]) / 2) * sign > 0]
        toe_z = max((p[2] for p in toes), default=az + 0.05 * L)
        joints["top_" + s] = (kx * 0.85, belly + 0.3 * (top_here - belly), kz - 0.02 * L)
        joints["mid_" + s] = (kx, knee_h, kz)
        joints["low_" + s] = (ax, ankle_h, az)
        joints["toe_" + s] = (ax, 0.0, max(toe_z, az + 0.02 * L))
    joints["root"] = (0.0, 0.0, leg_z)
    joints["root_up"] = (0.0, 0.25 * belly, leg_z)

    # The head: the top of the front half. The beak's tip is its foremost point.
    upper = [p for p in points if p[1] > belly]
    c0 = mean(upper)
    front_top = max(p[1] for p in points if p[2] > c0[2])
    head_r = 0.11 * S
    nose = max((p for p in points if p[1] > front_top - 3.2 * head_r and p[1] > belly + 0.3 * (front_top - belly)), key=lambda p: p[2])
    head_pts = [p for p in points if p[1] > front_top - 2.4 * head_r and p[2] > nose[2] - 3.0 * head_r] or [nose]
    hc = mean(head_pts)
    hc = (0.0, hc[1], hc[2])
    # The body: what is above the belly and is not the head; then again without the tail.
    torso = [p for p in upper if math.dist((p[1], p[2]), (hc[1], hc[2])) > 1.3 * head_r] or upper
    c = mean(torso)
    c = (0.0, c[1], c[2])
    rear = [p for p in points if p[2] < c[2]]
    tip = max(rear, key=lambda p: math.dist((p[1], p[2]), (c[1], c[2])))
    reach = math.dist((tip[1], tip[2]), (c[1], c[2]))
    ty, tz = (tip[1] - c[1]) / reach, (tip[2] - c[2]) / reach

    def station(t, half=0.05):
        """The surface around the line from the body's middle to the tail's tip, at t of the way."""
        return [p for p in points if abs(((p[1] - c[1]) * ty + (p[2] - c[2]) * tz) / reach - t) < half
                and abs(-(p[1] - c[1]) * tz + (p[2] - c[2]) * ty) < 0.35 * reach]
    widths = {}
    for k in range(4, 20):
        pts = station(k / 20)
        widths[k] = (max(p[0] for p in pts) - min(p[0] for p in pts)) if pts else 0.0
    body_w = max(widths.values()) or W
    base = next((k for k in range(7, 17) if all(widths[j] < 0.55 * body_w for j in range(k, 20))), 12) / 20

    def on_line(t, pts=None):
        pts = station(t)
        m = mean(pts) if pts else (0.0, c[1] + ty * reach * t, c[2] + tz * reach * t)
        return (0.0, m[1], m[2])
    joints["tail0"] = on_line(base)
    joints["tail1"] = on_line(base + 0.5 * (1 - base))
    joints["tail2"] = (0.0, tip[1], tip[2])
    torso = [p for p in torso if ((p[1] - c[1]) * ty + (p[2] - c[2]) * tz) / reach < base] or torso
    c = mean(torso)
    c = (0.0, c[1], c[2])
    toward = unit(sub(c, hc))
    joints["nose"] = (0.0, nose[1], nose[2])
    joints["skull"] = tuple(hc[k] + toward[k] * 0.45 * head_r for k in range(3))
    joints["neck"] = tuple(hc[k] + toward[k] * 1.25 * head_r for k in range(3))
    joints["hips"] = lerp(c, joints["tail0"], 0.5)
    joints["chest"] = lerp(c, joints["neck"], 0.55)

    # The wings, folded: the shoulder high on the side behind the neck, the tip over the root of the tail.
    frame = body_frame(joints)
    t0, (ay, az), (dy, dz), length = frame
    middle, thick = body_band(joints, frame)

    def at(u, v): return (t0[1] + ay * u * length + dy * (middle + v * thick), t0[2] + az * u * length + dz * (middle + v * thick))

    def side_x(yz, sign):
        near = [p[0] * sign for p in points if p[0] * sign > 0 and math.dist((p[1], p[2]), yz) < 0.035 * S]
        return sign * (max(near) if near else 0.12 * S)
    for s in LEGS:
        sign = 1 if s == "L" else -1
        for name, u, v in (("wing_", 0.72, 0.30), ("wing_mid_", 0.36, 0.22), ("wing_tip_", WING_U[0] + 0.04, 0.45)):
            yz = at(u, v)
            joints[name + s] = (side_x(yz, sign), yz[0], yz[1])
    found = {"kind": "bird", "belly": round(belly, 4), "height": round(H, 4), "length": round(L, 4), "body_thickness": round(2 * thick, 4),
             "tail_from": round(base, 2)}
    return joints, found


def place_bat():
    """The joints of a bat in flight: the body is what lies near the middle, each wing what reaches out to its side."""
    body_half = 0.09 * W
    core = [p for p in points if abs(p[0]) < body_half]
    cy, cz = sorted(p[1] for p in core), sorted(p[2] for p in core)
    # The body's own length: the wings' membranes reach past it at the back, so take the densest run along z.
    z0, z1 = min(cz), max(cz)
    lo_y, hi_y = cy[int(0.03 * (len(cy) - 1))], cy[int(0.97 * (len(cy) - 1))]
    nose = max(core, key=lambda p: p[2])
    length = z1 - z0
    mid_y = (lo_y + hi_y) / 2
    front = [p for p in core if p[2] > z1 - 0.3 * length]
    rear = [p for p in core if p[2] < z0 + 0.3 * length]
    middle = [p for p in core if z0 + 0.3 * length <= p[2] <= z1 - 0.3 * length] or core
    my = mean(middle)[1]
    fy = mean(front)[1] if front else my
    ry = mean(rear)[1] if rear else my
    joints = {
        "root": (0.0, 0.0, (z0 + z1) / 2), "root_up": (0.0, max(0.25 * my, 0.005), (z0 + z1) / 2),
        "hips": (0.0, my, z0 + 0.35 * length), "chest": (0.0, my, z0 + 0.66 * length),
        "skull": (0.0, fy, z1 - 0.26 * length), "nose": (0.0, nose[1], nose[2]),
        "tail0": (0.0, ry, z0 + 0.3 * length), "tail1": (0.0, ry, z0),
    }
    for s in LEGS:
        sign = 1 if s == "L" else -1
        side = [p for p in points if p[0] * sign > body_half]
        if not side: raise SystemExit("make: found no %s wing; place the joints by hand in %s" % ("left" if sign > 0 else "right", joints_path))
        shoulder = (sign * 0.6 * body_half, my + 0.25 * (hi_y - my), z0 + 0.62 * length)
        tip = max(side, key=lambda p: math.dist(p, shoulder))
        reach = math.dist(tip, shoulder)
        band = [p for p in side if 0.42 * reach < math.dist(p, shoulder) < 0.58 * reach] or [lerp(shoulder, tip, 0.5)]
        joints["wing_" + s], joints["wing_mid_" + s], joints["wing_tip_" + s] = shoulder, mean(band), tip
    return joints, {"kind": "bat", "height": round(H, 4), "length": round(L, 4), "width": round(W, 4), "body_length": round(length, 4)}


if mode == "keep":
    joints = json.load(open(joints_path))["joints"]
    common.log("joints kept from", joints_path)
else:
    joints, found = place_bat() if kind == "bat" else place_bird()
    joints = {k: [round(c, 5) for c in v] for k, v in joints.items()}
    with open(joints_path, "w") as f: json.dump({"joints": joints, "found": found, "axes": "glTF metres: x left, y up, z forward"}, f, indent=2)
    common.log("joints placed from the mesh, written to %s: %s" % (joints_path, ", ".join("%s %s" % kv for kv in found.items())))
missing = [j for b in BONES for j in b[2:] if j not in joints]
if missing: raise SystemExit("make: %s has no joint named %s (a %s needs them)" % (joints_path, ", ".join(sorted(set(missing))), kind))


def seg_dist(p, a, b):
    ab = [b[k] - a[k] for k in range(3)]; ap = [p[k] - a[k] for k in range(3)]
    t = max(0.0, min(1.0, sum(x * y for x, y in zip(ab, ap)) / max(sum(x * x for x in ab), 1e-12)))
    return math.dist(p, [a[k] + t * ab[k] for k in range(3)])


def own_leg(i):
    """The bones of the one leg vertex i belongs to below the body, else None: bone heat gives a thin leg weight from
    the other leg beside it, which leaves it bent when they move apart."""
    if kind != "bird": return None
    g = points[i]
    if g[1] > 0.85 * joints["mid_L"][1]: return None
    zs_leg = [joints[k + s][2] for k in ("mid_", "low_", "toe_") for s in LEGS]
    if not (min(zs_leg) - 0.08 * L <= g[2] <= max(zs_leg) + 0.08 * L): return None
    def d(s): return min(seg_dist(g, joints["mid_" + s], joints["low_" + s]), seg_dist(g, joints["low_" + s], joints["toe_" + s]))
    s = min(LEGS, key=d)
    if d(s) > 0.12 * L: return None                 # a tail that hangs low is not a leg
    return [b + s for b in ("Leg", "Shin", "Foot")]


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
shells = kind == "bird"
if shells:
    for b in data.bones:
        if b.name.startswith("Wing"): b.use_deform = False       # the body takes no weight from a folded wing's bones
rig["kind"] = kind

# Weights.
if rigger == "unirig": common.log("UniRig's weights are for the quadruped skeleton: a %s takes Blender's bone heat" % kind)
for o in bpy.context.scene.objects: o.select_set(o in (mesh, rig))
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
common.log("weights from Blender's bone heat")
bpy.context.view_layer.objects.active = mesh
for o in bpy.context.scene.objects: o.select_set(o is mesh)
for g in list(mesh.vertex_groups):
    if g.name == "Root": mesh.vertex_groups.remove(g)
bones = [(b.name, rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local) for b in data.bones if b.use_deform]
def to_segment(p, a, b):
    ab = b - a; t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-12))); return (a + ab * t - p).length
heated = sum(1 for v in mesh.data.vertices if any(g.weight > 1e-4 for g in v.groups))
if heated < 0.98 * len(mesh.data.vertices):
    # Bone heat fails on surfaces that touch (a thin wing's two sides, feathers lying on each other): then every
    # vertex takes its nearest bones by distance, which bends less smoothly but never leaves a piece behind.
    common.log("bone heat left %d of %d vertices without a bone: weights by distance to the bones instead" % (len(mesh.data.vertices) - heated, len(mesh.data.vertices)))
    for g in list(mesh.vertex_groups): mesh.vertex_groups.remove(g)
    for name, _, _ in bones: mesh.vertex_groups.new(name=name)
    for v in mesh.data.vertices:
        p = mesh.matrix_world @ v.co
        near = sorted((to_segment(p, a, b), name) for name, a, b in bones)[:3]
        d0 = max(near[0][0], 1e-5)
        for dist, name in near:
            w = (d0 / max(dist, 1e-5)) ** 4
            if w > 0.02: mesh.vertex_groups[name].add([v.index], w, "REPLACE")
names = {g.index: g.name for g in mesh.vertex_groups}
owned = 0
for v in mesh.data.vertices:
    leg = own_leg(v.index)
    if not leg: continue
    strays = [g for g in v.groups if names[g.group] not in leg and g.weight > 0]
    for g in strays: mesh.vertex_groups[g.group].remove([v.index])
    owned += bool(strays)
    if not any(names[g.group] in leg and g.weight > 1e-4 for g in v.groups):
        p = mesh.matrix_world @ v.co
        near = min((b for b in bones if b[0] in leg), key=lambda b: to_segment(p, b[1], b[2]))
        (mesh.vertex_groups.get(near[0]) or mesh.vertex_groups.new(name=near[0])).add([v.index], 1.0, "REPLACE")
common.log("%d low leg vertices had weight from other bones and were kept to their own leg" % owned)
bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
# Any vertex the heat left without a bone takes the nearest bone's.
lonely = 0
for v in mesh.data.vertices:
    if not any(g.weight > 1e-4 for g in v.groups):
        p = mesh.matrix_world @ v.co
        leg = own_leg(v.index)
        name = min((b for b in bones if not leg or b[0] in leg), key=lambda b: to_segment(p, b[1], b[2]))[0]
        (mesh.vertex_groups.get(name) or mesh.vertex_groups.new(name=name)).add([v.index], 1.0, "REPLACE"); lonely += 1
most = max((sum(1 for g in v.groups if g.weight > 1e-4) for v in mesh.data.vertices), default=0)
common.log("%d vertices had no weight and took the nearest bone's; at most %d bones a vertex" % (lonely, most))


def smooth(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def wing_shells():
    """Each folded wing as its own thin sheet over the body (see the top of this file)."""
    import bmesh
    frame = body_frame(joints)
    mw = mesh.matrix_world; inv = mw.inverted()
    middle, thick = body_band(joints, frame)
    for b in data.bones:
        if b.name.startswith("Wing"): b.use_deform = True; mesh.vertex_groups.new(name=b.name)
    index = {g.name: g.index for g in mesh.vertex_groups}
    bm = bmesh.new(); bm.from_mesh(mesh.data)
    bm.normal_update()
    deform = bm.verts.layers.deform.verify()

    def lower(u):
        """The lower edge of the folded wing: v at u."""
        tail_v, low_v = WING_LOW
        if u > WING_FRONT: return low_v + (1.6 - low_v) * smooth((u - WING_FRONT) / (WING_U[1] - WING_FRONT)) ** 2
        return low_v + (tail_v - low_v) * smooth((WING_FRONT - u) / (WING_FRONT - WING_U[0]))
    report = []
    for s in LEGS:
        sign = 1 if s == "L" else -1
        def inside(f):
            if (mw.to_3x3() @ f.normal).x * sign < WING_FACING: return False
            g = gltf(mw @ f.calc_center_median())
            if g[0] * sign <= 0: return False
            u, v = uv_of(g, frame)
            return WING_U[0] <= u <= WING_U[1] and (v - middle) / thick >= lower(u)
        chosen = set(f for f in bm.faces if inside(f))
        if not chosen: report.append("%s: no faces under the wing" % s); continue
        # One piece: the largest of what was chosen.
        pieces, seen = [], set()
        for f in chosen:
            if f in seen: continue
            stack, piece = [f], []
            seen.add(f)
            while stack:
                g = stack.pop(); piece.append(g)
                for e in g.edges:
                    for h in e.link_faces:
                        if h in chosen and h not in seen: seen.add(h); stack.append(h)
            pieces.append(piece)
        patch = set(max(pieces, key=len))
        for _ in range(3):                             # a face that sticks out of the edge on two sides goes: a smoother rim
            spikes = [f for f in patch if sum(1 for e in f.edges if not any(h in patch for h in e.link_faces if h is not f)) >= 2]
            patch.difference_update(spikes)
        patch = list(patch)
        copy = bmesh.ops.duplicate(bm, geom=patch)["geom"]
        faces = [g for g in copy if isinstance(g, bmesh.types.BMFace)]
        verts = [g for g in copy if isinstance(g, bmesh.types.BMVert)]
        for v in verts: v.co = inv @ (mw @ v.co + (mw.to_3x3() @ v.normal).normalized() * (WING_GAP + WING_THICK) * S)
        before = set(bm.verts)
        bmesh.ops.solidify(bm, geom=faces, thickness=WING_THICK * S)
        verts += [v for v in bm.verts if v not in before]
        # Weights: Body at the shoulder, so the wing's root stays on the body, then the arm, then the hand.
        a, m, t = (blender(joints[k + s]) for k in ("wing_", "wing_mid_", "wing_tip_"))
        arm, hand = (m - a).length, (t - m).length
        for v in verts:
            p = mw @ v.co
            along = (p - a).dot((m - a).normalized())
            beyond = (p - m).dot((t - m).normalized())
            w_body = 1 - smooth(along / (0.3 * arm))
            w_hand = smooth(0.5 + beyond / (0.35 * hand)) if hand > 1e-6 else 0.0
            w = {"Body": w_body, "Wing" + s: (1 - w_body) * (1 - w_hand), "Wing" + s + "Tip": (1 - w_body) * w_hand}
            v[deform].clear()
            for name, weight in w.items():
                if weight > 1e-4: v[deform][index[name]] = weight
        report.append("%s %d faces" % (s, len(patch)))
    bm.to_mesh(mesh.data); bm.free(); mesh.data.update()
    common.log("wings: a sheet over the body for each, " + "; ".join(report))


if shells: wing_shells()
mesh.parent = rig
if not any(m.type == "ARMATURE" for m in mesh.modifiers):
    m = mesh.modifiers.new("Skeleton", "ARMATURE"); m.object = rig
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
for o in bpy.context.scene.objects: o.select_set(o in (mesh, rig))
bpy.ops.export_scene.gltf(filepath=os.path.join(os.path.dirname(out_blend), "rig-%s.glb" % rigger), use_selection=True, export_format="GLB",
                          export_skins=True, export_animations=False, export_def_bones=False, export_image_format="JPEG")
with open(os.path.join(os.path.dirname(out_blend), "rig.json"), "w") as f:
    json.dump({"rigger": rigger, "kind": kind, "joints": mode, "unweighted_fixed": lonely, "max_influences": most, "bones": [b[0] for b in BONES]}, f, indent=2)
