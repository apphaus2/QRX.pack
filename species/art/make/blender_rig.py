"""make.py's rig step, in Blender: the quadruped skeleton of SPEC.md section 3, placed from the mesh (RIGGING.md
step 2), and skin weights, at most four a vertex.

    blender -b -P blender_rig.py -- <clean.blend> <rig.blend> <joints.json> <place|keep> <template|unirig> <unirig-skin.npz>

place: the joints are found from the mesh and written to joints.json (a kept art/<id>/joints.json is never
overwritten: make.py passes "keep" for it, and its joints are used as they are, so a wrong guess is fixed by hand once).
template: Blender's automatic (bone heat) weights. unirig: the weights UniRig predicted for this same skeleton
(rig_unirig.py), read from the .npz.

Joint positions are in glTF metres: x the animal's left, y up, z forward (where the head points)."""
import json, math, os, sys
import bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_common as common      # noqa: E402

clean, out_blend, joints_path, mode, rigger, unirig_npz = common.args()
# The 18 animals made and filed before the stance finder below (2026-11-17) are placed exactly as they were: three of
# them (red-squirrel, ringtail-raccoon, stripe-badger) touch the ground with a tail and would come out differently.
# Take a name out of this list to have that animal placed the new way the next time it is made.
MADE_BEFORE = ("alley-cat", "crag-kid", "dapple-calf", "dapple-fawn", "farmyard-piglet", "frost-wolf-pup", "honeyglow-bear-cub", "marsh-capybara",
               "meadow-cottontail", "meadow-pony", "meadow-sheepdog", "moonlit-cat", "red-squirrel", "ringtail-raccoon", "river-otter", "street-terrier",
               "stripe-badger", "woolly-lamb")
# Frogs sit on their bellies with their back legs folded beside them: no cut below the belly finds those legs, so they
# are placed by a sitting frog's proportions, fitted to this mesh's own length, height and width where each joint is.
SQUAT = ("glowspot-frog", "pond-frog")
creature = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(clean)))))     # art/<id>/work/<variant>/clean.blend
bpy.ops.wm.open_mainfile(filepath=clean)
mesh = bpy.data.objects["Mesh"]
for o in list(bpy.context.scene.objects):
    if o is not mesh: bpy.data.objects.remove(o)

# Bones: name -> (parent, head joint, tail joint). Joints are named points in joints.json.
BONES = [
    ("Root", None, "root", "root_up"),
    ("Body", "Root", "hips", "chest"),
    ("Chest", "Body", "chest", "neck"),
    ("Neck", "Chest", "neck", "skull"),
    ("Head", "Neck", "skull", "nose"),
    ("EarL", "Head", "ear_l", "ear_l_tip"),
    ("EarR", "Head", "ear_r", "ear_r_tip"),
    ("Tail1", "Body", "tail0", "tail1"),
    ("Tail2", "Tail1", "tail1", "tail2"),
    ("Tail3", "Tail2", "tail2", "tail3"),
] + [b for leg, parent in (("FL", "Chest"), ("FR", "Chest"), ("BL", "Body"), ("BR", "Body")) for b in (
    ("Leg" + leg, parent, "top_" + leg, "mid_" + leg),
    ("Shin" + leg, "Leg" + leg, "mid_" + leg, "low_" + leg),
    ("Foot" + leg, "Shin" + leg, "low_" + leg, "toe_" + leg))]


def gltf(v): return (v.x, v.z, -v.y)                 # Blender -> glTF
def blender(p): return Vector((p[0], -p[2], p[1]))   # glTF -> Blender


def place():
    """The joints, from the mesh: legs found by cutting below the belly, the spine along the middle, head at the front."""
    points = [gltf(mesh.matrix_world @ v.co) for v in mesh.data.vertices]
    tris = [[points[i] for i in p.vertices] for p in mesh.data.polygons]
    xs, ys, zs = zip(*points)
    H, zmin, zmax = max(ys), min(zs), max(zs)
    L = zmax - zmin

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

    def squat():
        """A sitting frog. Along the body from the rump (0) to the nose (1), up from the ground (0) to the top (1),
        and out from the middle to the mesh's own edge at that place (1): the thigh runs forward from the hip to a
        knee beside the belly, the shin back to the ankle by the rump, the foot forward along the ground; the arm
        goes back and down to the elbow and forward to the hand."""
        def at(u, v, w, sign):
            z, y = zmin + u * L, v * H
            near = [abs(q[0]) for q in points if q[0] * sign > 0 and abs(q[2] - z) < 0.05 * L and abs(q[1] - y) < 0.12 * H]
            return (sign * w * (max(near) if near else max(abs(x) for x in xs)), y, z)
        joints = {}
        for side, sign in (("L", 1), ("R", -1)):
            joints["top_B" + side], joints["mid_B" + side] = at(0.16, 0.32, 0.35, sign), at(0.47, 0.40, 0.80, sign)
            joints["low_B" + side], joints["toe_B" + side] = at(0.10, 0.12, 0.80, sign), at(0.48, 0.0, 0.80, sign)
            joints["top_F" + side], joints["mid_F" + side] = at(0.66, 0.45, 0.50, sign), at(0.58, 0.30, 0.78, sign)
            joints["low_F" + side], joints["toe_F" + side] = at(0.72, 0.08, 0.70, sign), at(0.84, 0.0, 0.70, sign)
        nose = max(points, key=lambda q: q[2])
        mid = lambda u, v: (0.0, v * H, zmin + u * L)
        joints.update(root=mid(0.4, 0.0), root_up=mid(0.4, 0.08), hips=mid(0.2, 0.38), chest=mid(0.6, 0.5), neck=mid(0.72, 0.58), skull=mid(0.8, 0.62),
                      nose=(0.0, nose[1], nose[2]), tail0=mid(0.1, 0.3), tail1=mid(0.06, 0.26), tail2=mid(0.03, 0.22), tail3=mid(0.0, 0.18))
        head_pts = [q for q in points if q[2] > nose[2] - 0.3 * L and q[1] > 0.4 * H]
        for side, sign in (("l", 1), ("r", -1)):                      # the "ears" are the eyes: the highest of the head
            tip = max([q for q in head_pts if q[0] * sign > 0] or head_pts or [nose], key=lambda q: q[1])
            joints["ear_%s_tip" % side] = tip
            joints["ear_%s" % side] = (tip[0] * 0.6, tip[1] - 0.04 * L, tip[2] - 0.01 * L)
        common.log("a sitting frog: placed by its proportions")
        return {k: [round(c, 5) for c in v] for k, v in joints.items()}, {"belly": round(0.1 * H, 4), "height": round(H, 4), "length": round(L, 4), "stance": "squat"}

    def blob(members, ids):
        bx, bz = [q[0] for q in members], [q[1] for q in members]
        return {"pts": members, "ids": ids, "x": sum(bx) / len(bx), "z": sum(bz) / len(bz), "x0": min(bx), "x1": max(bx), "z0": min(bz), "z1": max(bz)}

    def blobs(pts, cell):
        """The slice's (x, z) points joined where they lie within a cell of each other: one blob a foot, or a tail."""
        grid = {}
        for q in pts: grid.setdefault((math.floor(q[0] / cell), math.floor(q[1] / cell)), []).append(q)
        seen, out = set(), []
        for start in grid:
            if start in seen: continue
            seen.add(start); stack, members = [start], []
            while stack:
                c = stack.pop(); members += grid[c]
                for n in ((c[0] + dx, c[1] + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)):
                    if n in grid and n not in seen: seen.add(n); stack.append(n)
            out.append(blob(members, {len(out)}))
        return out

    def stand(low):
        """None (the feet are found as they always were), or the stance: its kind, and for an upright body the
        feet's own points, for a sprawled one the middle of the trunk and a function that places the legs."""
        if creature in MADE_BEFORE: return None
        found = blobs(low, 0.012 * L)
        left, right = [b for b in found if b["x0"] > 0], [b for b in found if b["x1"] < 0]
        near = sorted((abs(l["z"] - r["z"]), i, j) for i, l in enumerate(left) for j, r in enumerate(right) if abs(l["z"] - r["z"]) < 0.15 * L)
        pairs, used = [], (set(), set())
        for _, i, j in near:
            if i in used[0] or j in used[1]: continue
            used[0].add(i); used[1].add(j); pairs.append([left[i], right[j]])
        where = lambda pair: (pair[0]["z"] + pair[1]["z"]) / 2
        pairs.sort(key=where)
        k = 0
        while k < len(pairs) - 1:                           # the toes and the heels of the same two feet are one pair
            if where(pairs[k + 1]) - where(pairs[k]) < 0.12 * L:
                pairs[k] = [blob(a["pts"] + b["pts"], a["ids"] | b["ids"]) for a, b in zip(pairs[k], pairs[k + 1])]; del pairs[k + 1]
            else: k += 1
        if len(pairs) > 2: pairs = sorted(sorted(pairs, key=lambda pair: -len(pair[0]["pts"]) - len(pair[1]["pts"]))[:2], key=where)
        if len(pairs) != 2: return None
        hind, front = pairs
        feet = set().union(*(b["ids"] for b in hind + front))
        z0, z1 = min(b["z0"] for b in hind), max(b["z1"] for b in front)
        others = [b for b in found if not b["ids"] & feet and (b["z0"] > z1 or b["z1"] < z0)]
        mid = (max(b["z1"] for b in hind) + min(b["z0"] for b in front)) / 2
        trunk = max((abs(q[0]) for q in points if abs(q[2] - mid) < 0.03 * L), default=0.05 * L)
        if all(abs(b["x"]) > 0.9 * trunk for b in hind + front):
            common.log("a sprawled body: four feet outside the trunk (%.3f m to each side), %d other contacts with the ground left out" % (trunk, len(others)))
            return {"kind": "sprawled", "gap_mid": mid, "legs": lambda belly: sprawled_legs(hind, front, trunk, belly)}
        if others:
            common.log("two pairs of feet; %d other contacts with the ground (a tail, a chin) left out" % len(others))
            return {"kind": "upright", "points": [q for b in hind + front for q in b["pts"]]}
        return None

    def sprawled_legs(hind, front, trunk, belly):
        """A leg that goes out from the side of the body and down to a foot beside it: the shoulder inside the
        trunk's edge where the limb leaves it, the elbow at the middle of the limb, the ankle over the foot."""
        out = {}
        for end, pair in (("F", front), ("B", hind)):
            tops = []
            for side, sign, foot in (("L", 1, pair[0]), ("R", -1, pair[1])):
                reach = abs(foot["x"])
                limb = [q for q in points if q[0] * sign > trunk and abs(q[2] - foot["z"]) < 0.12 * L]
                inner = [q for q in limb if abs(q[0]) < trunk + 0.35 * (reach - trunk)]
                z_top = sum(q[2] for q in inner) / len(inner) if inner else foot["z"]
                top_here = max((q[1] for q in points if abs(q[2] - z_top) < 0.04 * L), default=H)
                top = (sign * 0.6 * trunk, belly + 0.45 * (top_here - belly), z_top)
                band = [q for q in limb if trunk + 0.35 * (reach - trunk) <= abs(q[0]) <= trunk + 0.75 * (reach - trunk)]
                if band: mid = tuple(sum(c) / len(band) for c in zip(*band))
                else: mid = ((top[0] + foot["x"]) / 2, top[1], (top[2] + foot["z"]) / 2)
                leg = end + side
                out["top_" + leg] = top
                out["mid_" + leg] = mid
                out["low_" + leg] = (foot["x"], min(0.3 * mid[1], 0.02 * L), foot["z"])
                out["toe_" + leg] = (foot["x"], 0.0, foot["z1"])
                tops.append((top_here, z_top))
            out["%s_top" % end] = (0.0, sum(t[0] for t in tops) / 2, sum(t[1] for t in tops) / 2)
        return out

    # The feet: two groups along z near the ground (front and back), the widest gap between them when there are more.
    if creature in SQUAT: return squat()
    low = slice_at(0.04 * H)
    # What stands on the ground, as blobs seen from above. Two left-and-right pairs of feet with other contacts fore
    # or aft (a tail lying on the ground, a chin) are the feet, and the rest is left out; feet that stand outside the
    # trunk are a sprawled body's (a lizard, a newt) and its legs are placed their own way below.
    stance = stand(low)
    if stance and stance["kind"] == "upright": low = stance["points"]
    if stance and stance["kind"] != "upright":
        gap_mid = stance["gap_mid"]
    else:
        g = groups([p[1] for p in low], 0.03 * L)
        if len(g) < 2:
            # Feet close together (a squirrel sitting up, a rabbit crouched): split the one group at its widest gap.
            g = groups([p[1] for p in low], 0.0)
            if len(g) < 2: raise SystemExit("make: found no feet near the ground; place the joints by hand in %s" % joints_path)
            widest = max(range(len(g) - 1), key=lambda i: g[i + 1][0] - g[i][-1])
            g = [[v for grp in g[:widest + 1] for v in grp], [v for grp in g[widest + 1:] for v in grp]]
            common.log("feet close together: front and back split at the widest gap, %.3f m" % (g[1][0] - g[0][-1]))
        gaps = [(g[i + 1][0] - g[i][-1], i) for i in range(len(g) - 1)]
        split = max(gaps)[1]
        back_z = [v for grp in g[:split + 1] for v in grp]; front_z = [v for grp in g[split + 1:] for v in grp]
        gap_mid = (g[split][-1] + g[split + 1][0]) / 2
    # The belly: going up, the first height where the surface crosses the middle of that gap.
    belly = 0.6 * H
    h = 0.04 * H
    while h < 0.8 * H:
        if any(abs(z - gap_mid) < 0.02 * L for _, z in slice_at(h)): belly = h; break
        h += 0.01 * H
    joints = {}
    sides = {"L": 1, "R": -1}
    if stance and stance["kind"] != "upright":
        joints.update(stance["legs"](belly))
    else:
        for end, zs_end in (("F", front_z), ("B", back_z)):
            zc = sum(zs_end) / len(zs_end)
            z_lo, z_hi = min(zs_end) - 0.02 * L, max(zs_end) + 0.02 * L
            top_here = max((p[1] for p in points if abs(p[2] - zc) < 0.04 * L), default=H)
            for side, sign in sides.items():
                def column(h):
                    pts = [p for p in slice_at(h) if z_lo <= p[1] <= z_hi and p[0] * sign > 0]
                    if not pts: pts = [p for p in slice_at(h) if z_lo <= p[1] <= z_hi]
                    if not pts: return (sign * 0.02 * L, zc)
                    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
                leg = end + side
                shoulder = belly + 0.45 * (top_here - belly)
                x0, z0 = column(belly * 0.95)
                elbow, wrist = (0.8, 0.28) if end == "F" else (0.75, 0.33)     # a front elbow sits near the belly, a hock lower
                xm, zm = column(belly * elbow)
                xl, zl = column(belly * wrist)
                feet = [p for p in points if p[1] < 0.05 * H and z_lo <= p[2] <= z_hi and p[0] * sign > 0] or [(xl, 0, zl)]
                toe_z = max(p[2] for p in feet)
                joints["top_" + leg] = (x0 * 0.8, shoulder, z0)
                joints["mid_" + leg] = (xm, belly * elbow, zm)
                joints["low_" + leg] = (xl, belly * wrist, zl)
                joints["toe_" + leg] = (xl, 0.0, toe_z)
            joints["%s_top" % end] = (0.0, top_here, zc)
    f_top, b_top = joints.pop("F_top"), joints.pop("B_top")
    fz = (joints["top_FL"][2] + joints["top_FR"][2]) / 2
    bz = (joints["top_BL"][2] + joints["top_BR"][2]) / 2
    joints["root"] = (0.0, 0.0, (fz + bz) / 2)
    joints["root_up"] = (0.0, 0.25 * belly, (fz + bz) / 2)
    joints["hips"] = (0.0, belly + 0.5 * (b_top[1] - belly), bz)
    joints["chest"] = (0.0, belly + 0.5 * (f_top[1] - belly), fz)
    # The head: the front of the mesh. The nose is the foremost point; the skull a fifth of the length behind it.
    nose = max(points, key=lambda p: p[2])
    head_pts = [p for p in points if p[2] > nose[2] - 0.2 * L and p[1] > belly]
    head_y = sum(p[1] for p in head_pts) / len(head_pts) if head_pts else nose[1]
    joints["nose"] = (0.0, nose[1], nose[2])
    joints["skull"] = (0.0, head_y, nose[2] - 0.17 * L)
    joints["neck"] = (0.0, belly + 0.7 * (f_top[1] - belly), fz + 0.06 * L)
    # The ears: the highest point on each side of the head.
    for side, sign in sides.items():
        pts = [p for p in head_pts if p[0] * sign > 0] or head_pts
        tip = max(pts, key=lambda p: p[1])
        joints["ear_%s_tip" % side.lower()] = tip
        joints["ear_%s" % side.lower()] = (tip[0] * 0.6, tip[1] - 0.04 * L, tip[2] - 0.01 * L)
    # The tail: what lies behind the hips' back end; three joints along it, by distance from its root.
    rear = [p for p in points if p[2] < bz - 0.08 * L]
    hips = joints["hips"]
    if rear:
        def dist(p, q): return math.dist(p, q)
        rump = min(rear, key=lambda p: dist(p, (0.0, hips[1], hips[2] - 0.2 * L)))
        tip = max(rear, key=lambda p: dist(p, hips))
        root = (0.0, rump[1], max(p[2] for p in rear) - 0.0)
        root = (0.0, hips[1] + 0.15 * (b_top[1] - hips[1]), bz - 0.1 * L)
        reach = dist(root, tip)
        line = [p for p in rear if dist(p, root) <= reach]
        def centre(lo, hi):
            pts = [p for p in line if lo <= dist(p, root) < hi] or [tip]
            return tuple(sum(c) / len(pts) for c in zip(*pts))
        joints["tail0"] = root
        joints["tail1"] = centre(0.25 * reach, 0.42 * reach)
        joints["tail2"] = centre(0.58 * reach, 0.75 * reach)
        joints["tail3"] = tip
    else:
        r = (0.0, hips[1], bz - 0.1 * L)
        joints.update(tail0=r, tail1=(0, r[1], r[2] - 0.02), tail2=(0, r[1], r[2] - 0.03), tail3=(0, r[1], r[2] - 0.04))
    found = {"belly": round(belly, 4), "height": round(H, 4), "length": round(L, 4)}
    if stance and stance["kind"] != "upright": found["stance"] = stance["kind"]     # only said when it is not the usual one
    return {k: [round(c, 5) for c in v] for k, v in joints.items()}, found


if mode == "keep":
    joints = json.load(open(joints_path))["joints"]
    found = json.load(open(joints_path)).get("found", {})
    common.log("joints kept from", joints_path)
else:
    joints, found = place()
    with open(joints_path, "w") as f: json.dump({"joints": joints, "found": found, "axes": "glTF metres: x left, y up, z forward"}, f, indent=2)
    common.log("joints placed from the mesh: belly %.3f m of %.3f, written to %s" % (found["belly"], found["height"], joints_path))

# Legs that touch (a mesher often fuses two front paws): below the belly, each face goes to the leg whose bones it is
# nearest, the surface is split where the two legs' faces meet, each side is drawn back a little and capped, so
# neither leg drags a web or a flap of the other when they move apart. The caps take the texture around them.
LEG_TOP = 0.7     # of the lowest leg top: the split stays below the chest
GAP = 0.003       # metres between the two sides of a split
LEGS = [(end, side) for end in ("F", "B") for side in ("L", "R")]     # a face's leg_side is 1 + its index here


def seg_dist(p, a, b):
    ab = [b[k] - a[k] for k in range(3)]; ap = [p[k] - a[k] for k in range(3)]
    t = max(0.0, min(1.0, sum(x * y for x, y in zip(ab, ap)) / max(sum(x * x for x in ab), 1e-12)))
    return math.dist(p, [a[k] + t * ab[k] for k in range(3)])


def leg_zone():
    """Per end (F, B): the z range of its feet and the height the split reaches."""
    zone = {}
    for end in ("F", "B"):
        zs = [joints[k + end + s][2] for k in ("low_", "toe_", "mid_") for s in ("L", "R")]
        reach = max(zs) - min(zs) + 0.03
        top = LEG_TOP * min(joints["mid_%s%s" % (end, s)][1] for s in ("L", "R")) / (0.8 if end == "F" else 0.75)
        zone[end] = (min(zs) - reach / 2, max(zs) + reach / 2, top)
    return zone


def nearest_leg(end, g):
    """1 + the index in LEGS of the leg (of this end) whose shin and foot lie nearest the glTF point g."""
    def d(side):
        k = end + side
        return min(seg_dist(g, joints["mid_" + k], joints["low_" + k]), seg_dist(g, joints["low_" + k], joints["toe_" + k]))
    return 1 + LEGS.index((end, min(("L", "R"), key=d)))


def close_loops(bm, edges):
    """What holes_fill leaves open (it skips some slits): walk each boundary loop and close it with one face, then
    triangles."""
    import bmesh
    nxt = {}
    for e in edges:
        for v in e.verts: nxt.setdefault(v, []).append(e)
    faces, seen = [], set()
    for start in list(nxt):
        if start in seen or len(nxt[start]) != 2: continue
        loop, v, came = [start], start, None
        while True:
            e = next((e for e in nxt[v] if e is not came), None)
            if e is None: loop = None; break
            w = e.other_vert(v)
            if w is start: break
            if w in loop or len(nxt.get(w, [])) != 2: loop = None; break
            loop.append(w); v, came = w, e
        if not loop or len(loop) < 3: continue
        seen.update(loop)
        try: f = bm.faces.new(loop)
        except ValueError: continue
        faces += bmesh.ops.triangulate(bm, faces=[f])["faces"]
    return faces


def split_legs():
    import bmesh
    zone = leg_zone()
    if found.get("stance") in ("sprawled", "squat"):
        # Legs out to the side never touch each other, and the belly lies as low as they do: nothing to split.
        bm = bmesh.new(); bm.from_mesh(mesh.data); bm.faces.layers.int.new("leg_side"); bm.to_mesh(mesh.data); bm.free()
        common.log("legs: %s, none split" % found["stance"]); return
    me = mesh.data
    mw = mesh.matrix_world; inv = mw.inverted()
    bm = bmesh.new(); bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    side = bm.faces.layers.int.new("leg_side")
    report = []
    for end, (z0, z1, top) in zone.items():
        def inside(f):
            for v in f.verts:
                g = gltf(mw @ v.co)
                if not (g[1] < top and z0 <= g[2] <= z1): return False
            return True
        faces = set(f for f in bm.faces if inside(f))
        for f in faces: f[side] = nearest_leg(end, gltf(mw @ f.calc_center_median()))
        edges = [e for e in {e for f in faces for e in f.edges} if len(e.link_faces) == 2
                 and all(lf in faces for lf in e.link_faces) and e.link_faces[0][side] != e.link_faces[1][side]]
        if not edges: report.append("%s apart" % end); continue
        bmesh.ops.split_edges(bm, edges=edges)
        open_edges = [e for e in bm.edges if e.is_boundary and all(lf in faces for lf in e.link_faces)]
        # Draw each side back from the other leg, so the two caps do not lie on each other (bone heat fails on
        # surfaces that touch) and the paws stand a little apart.
        for v in {v for e in open_edges for v in e.verts}:
            mine = {f[side] for f in v.link_faces}
            if len(mine) != 1: continue                       # where the split ends, the vertex is both legs'
            own = LEGS[mine.pop() - 1][1]; other = "R" if own == "L" else "L"
            away = joints["low_" + end + own][0] - joints["low_" + end + other][0]
            v.co = inv @ (mw @ v.co + Vector((math.copysign(GAP / 2, away), 0, 0)))
        caps = bmesh.ops.holes_fill(bm, edges=open_edges, sides=0)["faces"]
        caps += close_loops(bm, [e for e in open_edges if e.is_valid and e.is_boundary])
        for f in caps:
            near = [lf[side] for e in f.edges for lf in e.link_faces if lf is not f and lf[side]]
            f[side] = max(set(near), key=near.count) if near else 0
            for loop in f.loops:
                other = next((l for l in loop.vert.link_loops if l.face not in caps), None)
                if other and uv: loop[uv].uv = other[uv].uv
        report.append("%s split along %d edges, %d caps" % (end, len(edges), len(caps)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free(); me.update()
    common.log("legs:", "; ".join(report))


split_legs()
# Each vertex's leg (its faces', when they agree), then the attribute goes: it is not to be exported.
_faces = mesh.data.attributes["leg_side"].data
vertex_leg = [set() for _ in mesh.data.vertices]
for f in mesh.data.polygons:
    for i in f.vertices: vertex_leg[i].add(_faces[f.index].value)
vertex_leg = [s.pop() if len(s) == 1 and 0 not in s else 0 for s in vertex_leg]
mesh.data.attributes.remove(mesh.data.attributes["leg_side"])


def own_leg(i):
    """The bones of the one leg vertex i belongs to below the split, else None. Bone heat gives the inside of fused
    paws to the chest or the other paw, which leaves flaps behind when the leg moves."""
    if not vertex_leg[i]: return None
    end, side = LEGS[vertex_leg[i] - 1]
    return [b + end + side for b in ("Leg", "Shin", "Foot")]


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

# Weights.
for o in bpy.context.scene.objects: o.select_set(o in (mesh, rig))
bpy.context.view_layer.objects.active = rig
if rigger == "unirig":
    import numpy as np
    skin = np.load(unirig_npz)
    names, weights, points = [str(n) for n in skin["names"]], skin["weights"], skin["points"]
    # UniRig works in its own normalized space: fit the scale and offset that take its joints onto ours, per axis.
    a, b = skin["joints_unirig"], skin["joints_ours"]
    scale = np.array([np.polyfit(a[:, k], b[:, k], 1) for k in range(3)])
    points = points * scale[:, 0] + scale[:, 1]
    fit = np.abs(a * scale[:, 0] + scale[:, 1] - b).max()
    verts = np.array([tuple(mesh.matrix_world @ v.co) for v in mesh.data.vertices])
    # Each vertex: the inverse-distance mean of its four nearest UniRig points.
    from mathutils.kdtree import KDTree
    tree = KDTree(len(points))
    for i, p in enumerate(points): tree.insert(tuple(p), i)
    tree.balance()
    w = np.zeros((len(verts), weights.shape[1]))
    for i, v in enumerate(verts):
        found = tree.find_n(tuple(v), 4)
        inv = np.array([1 / (dist + 1e-6) for _, _, dist in found])
        w[i] = (weights[[idx for _, idx, _ in found]] * inv[:, None]).sum(0) / inv.sum()
    bpy.ops.object.parent_set(type="ARMATURE_NAME")
    for j, name in enumerate(names):
        if name not in data.bones: continue
        group = mesh.vertex_groups.get(name) or mesh.vertex_groups.new(name=name)
        for i in np.nonzero(w[:, j] > 1e-3)[0]: group.add([int(i)], float(w[i, j]), "REPLACE")
    common.log("UniRig's joints fit ours within %.4f m after scale and offset" % fit)
    common.log("weights from UniRig for", len(names), "bones")
else:
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    common.log("weights from Blender's bone heat")
bpy.context.view_layer.objects.active = mesh
for o in bpy.context.scene.objects: o.select_set(o is mesh)
for g in list(mesh.vertex_groups):
    if g.name == "Root": mesh.vertex_groups.remove(g)
names = {g.index: g.name for g in mesh.vertex_groups}
owned = 0
for v in mesh.data.vertices:
    leg = own_leg(v.index)
    if not leg: continue
    strays = [g for g in v.groups if names[g.group] not in leg and g.weight > 0]
    for g in strays: mesh.vertex_groups[g.group].remove([v.index])
    owned += bool(strays)
    if not any(names[g.group] in leg and g.weight > 1e-4 for g in v.groups):
        p = rig.matrix_world.inverted() @ (mesh.matrix_world @ v.co)
        near = min((b for b in data.bones if b.name in leg), key=lambda b: (b.head_local.lerp(b.tail_local, 0.5) - p).length)
        (mesh.vertex_groups.get(near.name) or mesh.vertex_groups.new(name=near.name)).add([v.index], 1.0, "REPLACE")
common.log("%d low leg vertices had weight from other bones and were kept to their own leg" % owned)
bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
# Any vertex the heat left without a bone takes the nearest bone's.
bones = [(b.name, rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local) for b in data.bones if b.use_deform]
def to_segment(p, a, b):
    ab = b - a; t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-12))); return (a + ab * t - p).length
lonely = 0
for v in mesh.data.vertices:
    if not any(g.weight > 1e-4 for g in v.groups):
        p = mesh.matrix_world @ v.co
        leg = own_leg(v.index)
        name = min((b for b in bones if not leg or b[0] in leg), key=lambda b: to_segment(p, b[1], b[2]))[0]
        (mesh.vertex_groups.get(name) or mesh.vertex_groups.new(name=name)).add([v.index], 1.0, "REPLACE"); lonely += 1
most = max((sum(1 for g in v.groups if g.weight > 1e-4) for v in mesh.data.vertices), default=0)
common.log("%d vertices had no weight and took the nearest bone's; at most %d bones a vertex" % (lonely, most))
if lonely > 0.02 * len(mesh.data.vertices):
    raise SystemExit("make: bone heat left %d of %d vertices without a bone (it fails on surfaces that touch or holes); "
                     "the rig would move in pieces" % (lonely, len(mesh.data.vertices)))
mesh.parent = rig
if not any(m.type == "ARMATURE" for m in mesh.modifiers):
    m = mesh.modifiers.new("Skeleton", "ARMATURE"); m.object = rig
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
for o in bpy.context.scene.objects: o.select_set(o in (mesh, rig))
bpy.ops.export_scene.gltf(filepath=os.path.join(os.path.dirname(out_blend), "rig-%s.glb" % rigger), use_selection=True, export_format="GLB",
                          export_skins=True, export_animations=False, export_def_bones=False, export_image_format="JPEG")
with open(os.path.join(os.path.dirname(out_blend), "rig.json"), "w") as f:
    json.dump({"rigger": rigger, "joints": mode, "unweighted_fixed": lonely, "max_influences": most, "bones": [b[0] for b in BONES]}, f, indent=2)
