"""make.py's rig step for the soft shape, in Blender: the boneless animals. Two kinds, told apart by the creature's id
(KINDS below) or, for an id not listed, by its proportions:

    jelly   a bell with tentacles hanging below it (frost-jelly, lantern-jelly, moon-jelly)
    snail   a foot and a head with two eye stalks, a rigid shell on top (garden-snail, meadow-snail)

    blender -b -P blender_rig_soft.py -- <clean.blend> <rig.blend> <joints.json> <place|keep> <template|unirig> <unirig-skin.npz>

place: the joints are found from the mesh and written to joints.json with what was measured ("found"). keep: a kept
art/<id>/joints.json is used as it is, joints and "found" both, so a wrong guess is fixed by hand once.

The weights are not Blender's bone heat (it fails on thin strands and on surfaces that touch) and not UniRig's (its
skeletons are for animals with limbs): they are written here from where each vertex lies, at most four a vertex and
none left out. The rigger argument is taken for make.py's sake and only names the files.

jelly bones: Root (on the ground under the bell's axis), Body (the bell's middle), Head (the bell's top), Bell1 to
Bell8 (ribs from the axis out to the rim, like an umbrella's: turning them in is the pulse), Tent<i>a, Tent<i>b,
Tent<i>c under each rib (the tentacles of that eighth), Arm1 to Arm3 down the middle (the mouth arms).
snail bones: Root, Body (the foot under the shell), Shell (rigid: every shell vertex is its alone), Neck, Head,
StalkL, StalkL2, StalkR, StalkR2 (the eye stalks), Tail1, Tail2 (the foot behind the shell).

Joint positions are in glTF metres: x the animal's left, y up, z forward (where the head points)."""
import json, math, os, sys
import bpy
import numpy as np
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_common as common      # noqa: E402

clean, out_blend, joints_path, mode, rigger, unirig_npz = common.args()
creature = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(out_blend)))))
bpy.ops.wm.open_mainfile(filepath=clean)
mesh = bpy.data.objects["Mesh"]
for o in list(bpy.context.scene.objects):
    if o is not mesh: bpy.data.objects.remove(o)

KINDS = {"frost-jelly": "jelly", "lantern-jelly": "jelly", "moon-jelly": "jelly", "garden-snail": "snail", "meadow-snail": "snail"}
# Where a jelly's bell ends, as a share of its height from the ground, when the measurement below gets it wrong.
RIM = {}
RIBS = 8                  # a jelly's bell ribs, and its tentacle chains
CHAIN = ("a", "b", "c")   # the bones down each tentacle chain


def gltf(v): return (v.x, v.z, -v.y)                 # Blender -> glTF
def blender(p): return Vector((p[0], -p[2], p[1]))   # glTF -> Blender


def points():
    return np.array([gltf(mesh.matrix_world @ v.co) for v in mesh.data.vertices], dtype=float)


def surface():
    """The vertices and each face's middle: enough points that a thin slice of the body is never empty."""
    mids = [gltf(mesh.matrix_world @ f.center) for f in mesh.data.polygons]
    return np.vstack([points(), np.array(mids, dtype=float)]) if mids else points()


def smooth(lo, hi, v):
    if hi == lo: return 1.0 if v >= hi else 0.0
    t = max(0.0, min(1.0, (v - lo) / (hi - lo)))
    return t * t * (3 - 2 * t)


def kind_of(P):
    if creature in KINDS: return KINDS[creature]
    for word in ("jelly", "snail"):
        if word in creature: return word
    size = P.max(0) - P.min(0)
    return "jelly" if size[1] > 0.75 * max(size[0], size[2]) else "snail"     # a jelly hangs; a snail lies along the ground


# ---------------------------------------------------------------------------------------------------- the jelly

def rib_direction(i, found):
    """Rib i's (1-based) horizontal direction, glTF (x, z), on the bell's own ellipse: rib 1 points forward."""
    a = math.tau * (i - 1) / RIBS
    return found["rx"] * math.sin(a), found["rz"] * math.cos(a)


def place_jelly(P):
    """The bell's axis, its top and its rim. From the top down the bell widens and may curl in again to its rim; below
    it the tentacles are much narrower, or hang in strands with gaps between them (the rim is where either begins)."""
    H = float(P[:, 1].max())
    bins = 40
    edges = np.linspace(0.0, H, bins + 1)
    ax = az = 0.0
    sx = sz = 1.0                                           # a bell flatter one way than the other is measured as a circle
    for _ in range(3):
        r = np.hypot((P[:, 0] - ax) / sx, (P[:, 2] - az) / sz)
        angle = np.arctan2((P[:, 0] - ax) / sx, (P[:, 2] - az) / sz)
        rad, cover = [], []
        for b in range(bins):
            inside = (P[:, 1] >= edges[b]) & (P[:, 1] <= edges[b + 1])
            if inside.sum() < 3: rad.append(None); cover.append(None); continue
            rad.append(float(np.percentile(r[inside], 95)))
            outer = inside & (r > 0.6 * rad[-1])
            cover.append(len(set(np.floor((angle[outer] + math.pi) / math.tau * 24).astype(int) % 24)) / 24.0)
        widest, rim_bin = 0.0, bins - 1
        for b in range(bins - 1, -1, -1):
            if rad[b] is None: continue
            widest = max(widest, rad[b])
            below_top = b < bins - 1 - bins // 8           # the crown is small and sparse: not the rim yet
            if below_top and (rad[b] < 0.72 * widest or cover[b] < 0.7): break
            rim_bin = b
        rim = float(edges[rim_bin])
        if creature in RIM: rim = RIM[creature] * H
        bell = P[P[:, 1] >= rim]
        ax = float(bell[:, 0].min() + bell[:, 0].max()) / 2; az = float(bell[:, 2].min() + bell[:, 2].max()) / 2
        wx, wz = float(np.ptp(bell[:, 0])), float(np.ptp(bell[:, 2]))
        sx, sz = max(wx / max(wx, wz), 0.2), max(wz / max(wx, wz), 0.2)
    bell = P[P[:, 1] >= rim]
    rx = float(bell[:, 0].max() - bell[:, 0].min()) / 2; rz = float(bell[:, 2].max() - bell[:, 2].min()) / 2
    bh = H - rim
    found = {"kind": "jelly", "height": H, "rim": rim, "axis": [ax, az], "rx": rx, "rz": rz}
    # The mouth arms: what hangs near the axis below the rim.
    rn = np.hypot((P[:, 0] - ax) / rx, (P[:, 2] - az) / rz)
    inner = P[(P[:, 1] < rim) & (rn < 0.4)]
    arm_low = float(inner[:, 1].min()) if len(inner) else rim * 0.5
    found["arm_low"] = arm_low
    joints = {"root": (ax, 0.0, az), "root_up": (ax, 0.25 * max(rim, 0.3 * bh), az),
              "body": (ax, rim + 0.45 * bh, az), "crown": (ax, rim + 0.8 * bh, az), "top": (ax, H, az),
              "hub": (ax, rim + 0.6 * bh, az)}
    for i in range(1, RIBS + 1):
        dx, dz = rib_direction(i, found)
        joints["rim%d" % i] = (ax + dx, rim, az + dz)
        for k in range(1, len(CHAIN) + 1):                  # the tentacles hang a little inside the rim
            joints["tent%d_%d" % (i, k)] = (ax + 0.85 * dx, rim * (1 - k / len(CHAIN)), az + 0.85 * dz)
    for k in range(0, 4):
        joints["arm%d" % k] = (ax, rim + (arm_low - rim) * k / 3, az)
    return joints, found


def bones_jelly():
    out = [("Root", None, "root", "root_up"), ("Body", "Root", "body", "crown"), ("Head", "Body", "crown", "top")]
    for i in range(1, RIBS + 1):
        out.append(("Bell%d" % i, "Body", "hub", "rim%d" % i))
        last, at = "Bell%d" % i, "rim%d" % i
        for k, letter in enumerate(CHAIN, 1):
            out.append(("Tent%d%s" % (i, letter), last, at, "tent%d_%d" % (i, k)))
            last, at = "Tent%d%s" % (i, letter), "tent%d_%d" % (i, k)
    for k in range(1, 4):
        out.append(("Arm%d" % k, "Arm%d" % (k - 1) if k > 1 else "Body", "arm%d" % (k - 1), "arm%d" % k))
    return out


def chain_weights(c, count, first_blend=0.35, blend=0.3):
    """Along a hanging chain of `count` bones, c from 0 (its top) to count (its end): [(bone index, weight)], index -1
    being the chain's parent. All the parent's at the top, so the skin is whole where the chain begins."""
    c = max(0.0, min(count - 1e-6, c))
    k = int(c); u = c - k
    if k == 0:
        w = smooth(0.0, first_blend, u)
        out = [(-1, 1 - w), (0, w)]
    elif u < blend: out = [(k - 1, 0.5 * (1 - u / blend)), (k, 1 - 0.5 * (1 - u / blend))]
    else: out = [(k, 1.0)]
    if u > 1 - blend and k + 1 < count:
        share = 0.5 * (1 - (1 - u) / blend)
        out = [(b, w * (1 - share)) for b, w in out] + [(k + 1, share)]
    return out


def weights_jelly(P, found):
    ax, az = found["axis"]; rim, H, rx, rz = found["rim"], found["height"], found["rx"], found["rz"]
    bh = H - rim
    arm_len = max(rim - found["arm_low"], 1e-6)
    out = []
    for x, y, z in P:
        nx, nz = (x - ax) / rx, (z - az) / rz
        rn = math.hypot(nx, nz)
        s = (math.atan2(nx, nz) % math.tau) / math.tau * RIBS
        i0 = int(s) % RIBS; f = smooth(0.0, 1.0, s - int(s))
        ribs = [(i0 + 1, 1 - f), ((i0 + 1) % RIBS + 1, f)]
        outer = smooth(0.3, 0.75, rn)
        w = {}
        def add(name, value):
            if value > 0: w[name] = w.get(name, 0.0) + value
        if y >= rim:
            head = smooth(rim + 0.45 * bh, rim + 0.9 * bh, y)
            for i, share in ribs: add("Bell%d" % i, outer * share)
            add("Head", (1 - outer) * head); add("Body", (1 - outer) * (1 - head))
        else:
            for k, share in chain_weights((rim - y) / max(rim, 1e-6) * len(CHAIN), len(CHAIN)):
                for i, rib in ribs:
                    add("Bell%d" % i if k < 0 else "Tent%d%s" % (i, CHAIN[k]), outer * share * rib)
            for k, share in chain_weights((rim - y) / arm_len * 3, 3):
                add("Body" if k < 0 else "Arm%d" % (k + 1), (1 - outer) * share)
        out.append(w)
    return out


# ---------------------------------------------------------------------------------------------------- the snail

def profile(P, bins=64):
    """The highest point of each slice along the body, tail to head: (slice centres, tops)."""
    z0, z1 = float(P[:, 2].min()), float(P[:, 2].max())
    edges = np.linspace(z0, z1, bins + 1)
    tops = []
    for b in range(bins):
        inside = (P[:, 2] >= edges[b]) & (P[:, 2] <= edges[b + 1])
        tops.append(float(P[inside, 1].max()) if inside.any() else 0.0)
    return (edges[:-1] + edges[1:]) / 2, np.array(tops), edges


def shell_span(P):
    """The shell from the side: the stretch of the body that stands above half the height, about its highest point."""
    centres, tops, edges = profile(P)
    H = float(tops.max())
    width = np.array([np.ptp(P[(P[:, 2] >= edges[b]) & (P[:, 2] <= edges[b + 1]), 0]) if tops[b] > 0 else 0.0 for b in range(len(tops))])
    apex = int(np.argmax(tops * width))                     # tall and wide: the shell, never an eye stalk
    return centres, tops, H, apex


def place_snail(P):
    centres, tops, H, apex = shell_span(P)
    zmin, zmax = float(P[:, 2].min()), float(P[:, 2].max())
    L = zmax - zmin
    step = centres[1] - centres[0]
    foot_top = 0.22 * H
    for _ in range(3):
        half = foot_top + 0.5 * (tops[apex] - foot_top)
        lo = hi = apex
        while lo > 0 and tops[lo - 1] >= half: lo -= 1
        while hi < len(tops) - 1 and tops[hi + 1] >= half: hi += 1
        chord0, chord1 = centres[lo] - step / 2, centres[hi] + step / 2
        zc = (chord0 + chord1) / 2
        a = (chord1 - chord0) / 2 / 0.866                   # an ellipse's chord at half its height is 0.866 of its length
        b = (tops[apex] - foot_top) / 2
        yc = foot_top + b
        # The foot's height: the top of the foot just behind the shell, where nothing lies on it.
        behind = [tops[i] for i in range(len(tops)) if zc - a - 0.12 * L <= centres[i] <= zc - a - 0.01 * L]
        if not behind: break
        foot_top = min(max(float(np.median(behind)), 0.1 * H), 0.35 * H)
    zs0, zs1 = max(zc - a, zmin + 0.02 * L), min(zc + a, zmax - 0.1 * L)
    found = {"kind": "snail", "height": H, "length": L, "foot_top": foot_top, "shell": [zc, yc, a, b], "shell_rear": zs0, "shell_front": zs1}
    # The head: in front of the shell. Its top is where the surface thins to the two stalks.
    front = P[P[:, 2] > zs1 + 0.25 * (zmax - zs1)]
    if len(front) < 20: front = P[P[:, 2] > zmax - 0.2 * L]
    top = float(front[:, 1].max())
    levels = np.linspace(0.0, top, 25)
    counts = np.histogram(front[:, 1], bins=levels)[0].astype(float)
    peak = int(np.argmax(counts))
    head_top = top
    for i in range(peak, len(counts)):
        if counts[i] < 0.3 * counts[peak]: head_top = float(levels[i]); break
    head_top = min(head_top, 0.9 * top)
    found["head_top"] = head_top
    head = front[front[:, 1] <= head_top]
    nose = head[np.argmax(head[:, 2])]
    head_y = float(head[:, 1].mean())
    yf = 0.5 * foot_top
    skull_z = zs1 + 0.55 * (float(nose[2]) - zs1)
    joints = {"root": (0.0, 0.0, 0.0), "root_up": (0.0, 0.5 * yf, 0.0),
              "foot_rear": (0.0, yf, zs0), "foot_front": (0.0, yf, zs1),
              "tail1": (0.0, 0.8 * yf, (zs0 + zmin) / 2), "tail2": (0.0, 0.3 * yf, zmin),
              "skull": (0.0, head_y, skull_z), "nose": (0.0, float(nose[1]), float(nose[2])),
              "shell_base": (0.0, foot_top, zc), "shell_top": (0.0, float(tops[apex]), zc)}
    for side, sign in (("l", 1), ("r", -1)):
        pts = front[(front[:, 0] * sign > 0) & (front[:, 1] > head_top)]
        if len(pts) < 3: pts = front[front[:, 1] > head_top]
        if len(pts) < 3: pts = front
        tip = pts[np.argmax(pts[:, 1])]
        low = pts[pts[:, 1] <= head_top + 0.15 * (tip[1] - head_top)]
        base = low.mean(0) if len(low) else np.array([tip[0] * 0.6, head_top, tip[2] - 0.3 * (tip[1] - head_top)])
        if np.linalg.norm(tip - base) < 0.004: base = np.array([tip[0] * 0.6, head_top - 0.004, tip[2]])
        joints["stalk_%s" % side] = tuple(base); joints["stalk_%s_mid" % side] = tuple((base + tip) / 2); joints["stalk_%s_tip" % side] = tuple(tip)
    return joints, found


def bones_snail():
    out = [("Root", None, "root", "root_up"), ("Body", "Root", "foot_rear", "foot_front"), ("Shell", "Body", "shell_base", "shell_top"),
           ("Neck", "Body", "foot_front", "skull"), ("Head", "Neck", "skull", "nose"),
           ("Tail1", "Body", "foot_rear", "tail1"), ("Tail2", "Tail1", "tail1", "tail2")]
    for side in ("L", "R"):
        s = side.lower()
        out += [("Stalk" + side, "Head", "stalk_" + s, "stalk_%s_mid" % s), ("Stalk%s2" % side, "Stalk" + side, "stalk_%s_mid" % s, "stalk_%s_tip" % s)]
    return out


def in_shell(y, z, found, grow=1.08):
    zc, yc, a, b = found["shell"]
    return ((z - zc) / (a * grow)) ** 2 + ((y - yc) / (b * grow)) ** 2 <= 1.0


def weights_snail(P, joints, found):
    zs0, zs1 = joints["foot_rear"][2], joints["foot_front"][2]
    stops = [("Tail2", None), ("Tail1", joints["tail1"][2]), ("Body", zs0), ("Neck", zs1), ("Head", joints["skull"][2])]
    lengths = [joints["tail1"][2] - joints["tail2"][2], zs0 - joints["tail1"][2], zs1 - zs0, joints["skull"][2] - zs1, joints["nose"][2] - joints["skull"][2]]
    stalks = {}
    for side in ("L", "R"):
        s = side.lower()
        base, tip = np.array(joints["stalk_" + s]), np.array(joints["stalk_%s_tip" % s])
        stalks[side] = (base, tip - base, float(np.dot(tip - base, tip - base)))
    reach = max(math.sqrt(v[2]) for v in stalks.values())
    out = []
    for p in P:
        x, y, z = p
        if in_shell(y, z, found): out.append({"Shell": 1.0}); continue
        w = {}
        # Along the foot: each joint shared half and half, over a third of the shorter bone beside it.
        for i, (name, start) in enumerate(stops):
            share = 1.0
            if start is not None:
                band = max(0.33 * min(abs(lengths[i - 1]), abs(lengths[i])), 1e-5)
                share *= smooth(start - band, start + band, z)
            if i + 1 < len(stops):
                band = max(0.33 * min(abs(lengths[i]), abs(lengths[i + 1])), 1e-5)
                share *= 1 - smooth(stops[i + 1][1] - band, stops[i + 1][1] + band, z)
            if share > 1e-4: w[name] = share
        # The stalks: what stands above the head near a stalk's line goes to it, from its foot to its tip.
        if y > found["head_top"] - 0.1 * reach and z > zs1:
            best = None
            for side, (base, along, length2) in stalks.items():
                t = float(np.dot(p - base, along)) / max(length2, 1e-12)
                d = float(np.linalg.norm(p - (base + along * max(0.0, min(1.0, t)))))
                if t > 0 and d < 0.45 * math.sqrt(length2) and (best is None or d < best[2]): best = (side, t, d)
            if best:
                side, t, _ = best
                on = smooth(0.0, 0.25, t)
                tip = smooth(0.35, 0.65, t)
                w = {k: v * (1 - on) for k, v in w.items()}
                w["Stalk" + side] = on * (1 - tip)
                w["Stalk%s2" % side] = on * tip
        out.append(w)
    return out


# ------------------------------------------------------------------------------------------------- joints, bones

P = points()
kind = kind_of(P)
if mode == "keep":
    kept = json.load(open(joints_path))
    joints, found = kept["joints"], kept["found"]
    kind = found["kind"]
    common.log("joints kept from", joints_path)
else:
    turned = False
    if kind == "snail":
        # The head is the end that reaches further out from under the shell. A snail lying the other way is turned here.
        centres, tops, H, apex = shell_span(surface())
        if centres[apex] - P[:, 2].min() > P[:, 2].max() - centres[apex]:
            mesh.data.transform(mesh.matrix_world.inverted() @ Matrix.Rotation(math.pi, 4, "Z") @ mesh.matrix_world); mesh.data.update()
            P = points(); turned = True
            common.log("the snail lay with its tail forward (the shell sat nearer the front): turned half round")
    joints, found = (place_jelly if kind == "jelly" else place_snail)(surface())
    found["turned"] = turned
    joints = {k: [round(float(c), 5) for c in v] for k, v in joints.items()}
    found = {k: (round(v, 5) if isinstance(v, float) else [round(float(c), 5) for c in v] if isinstance(v, list) else v) for k, v in found.items()}
    with open(joints_path, "w") as f: json.dump({"joints": joints, "found": found, "axes": "glTF metres: x left, y up, z forward"}, f, indent=2)
    if kind == "jelly":
        common.log("jelly: bell from %.3f m (its rim) to %.3f m, %.3f by %.3f m across; joints written to %s"
                   % (found["rim"], found["height"], 2 * found["rx"], 2 * found["rz"], joints_path))
    else:
        common.log("snail: foot %.3f m high, shell %.3f m long about z %.3f, head top %.3f m of %.3f; joints written to %s"
                   % (found["foot_top"], 2 * found["shell"][2], found["shell"][0], found["head_top"], found["height"], joints_path))
BONES = bones_jelly() if kind == "jelly" else bones_snail()

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

# Weights, from where each vertex lies: the four largest, made to add up to one.
weights = weights_jelly(P, found) if kind == "jelly" else weights_snail(P, joints, found)
mesh.vertex_groups.clear()
groups = {name: mesh.vertex_groups.new(name=name) for name, _, _, _ in BONES if name != "Root"}
lonely = most = 0
used = set()
for i, w in enumerate(weights):
    top = sorted(((v, k) for k, v in w.items() if v > 1e-3), reverse=True)[:4]
    if not top:
        # Nothing claimed it (it cannot happen with the rules above; kept as the standard's guard): the nearest bone.
        p = blender(P[i]); lonely += 1
        near = min((b for b in data.bones if b.use_deform), key=lambda b: (b.head_local.lerp(b.tail_local, 0.5) - p).length)
        top = [(1.0, near.name)]
    total = sum(v for v, _ in top)
    for v, k in top: groups[k].add([i], v / total, "REPLACE"); used.add(k)
    most = max(most, len(top))
common.log("weights from the shape (%s): %d vertices, at most %d bones a vertex, %d took the nearest bone's, %d of %d bones hold skin"
           % (kind, len(weights), most, lonely, len(used), len(groups)))
if kind == "snail":
    shell = sum(1 for w in weights if w.get("Shell") == 1.0)
    common.log("shell: %d vertices, each the Shell bone's alone" % shell)
mesh.parent = rig
if not any(m.type == "ARMATURE" for m in mesh.modifiers):
    m = mesh.modifiers.new("Skeleton", "ARMATURE"); m.object = rig
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
for o in bpy.context.scene.objects: o.select_set(o in (mesh, rig))
bpy.ops.export_scene.gltf(filepath=os.path.join(os.path.dirname(out_blend), "rig-%s.glb" % rigger), use_selection=True, export_format="GLB",
                          export_skins=True, export_animations=False, export_def_bones=False, export_image_format="JPEG")
with open(os.path.join(os.path.dirname(out_blend), "rig.json"), "w") as f:
    json.dump({"rigger": rigger, "shape": "soft", "kind": kind, "joints": mode, "unweighted_fixed": lonely, "max_influences": most,
               "bones": [b[0] for b in BONES]}, f, indent=2)
