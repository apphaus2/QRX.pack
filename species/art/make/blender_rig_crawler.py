"""make.py's rig step for the crawler shape, in Blender: beetles and bees (six legs), spiders (eight), the scorpion
(eight legs, two claws, a tail) and crabs (eight legs, two claws, pictured from the front, so they walk sideways).

    blender -b -P blender_rig_crawler.py -- <clean.blend> <rig.blend> <joints.json> <place|keep> <template|unirig> <unirig-skin.npz>

Legs this thin defeat bone heat, so nothing here uses it. The mesh is read as a trunk (where it is thick) and limbs
(where it is thin): every limb is found from its tip, the point farthest from the trunk along the surface, and
followed back to the trunk. A limb's vertices are the ones nearer its tip than any other's along the surface, so two
legs the mesher fused are told apart; the surface is split between them and capped (as blender_rig.py does for paws
that touch). Weights are written from the geometry: along a limb by the distance from its tip, into the trunk's own
bones where the limb joins it, and along the trunk by where a vertex lies (Head, Body, Abdomen).

Bones (Root, Body and Head for every kind; a limb the mesh does not have still gets its bones, with no weight, so
the names are the same for every creature of a kind):
    beetle    Abdomen, Leg1L..Leg3R + Shin1L..Shin3R, AntennaL, AntennaR
    bee       the beetle's, and WingL, WingR
    spider    Abdomen, Leg1L..Leg4R + Shin1L..Shin4R
    scorpion  the spider's, and ClawL, PincerL, ClawR, PincerR, Tail1..Tail4
    crab      Leg1L..Leg4R + Shin1L..Shin4R, ClawL, PincerL, ClawR, PincerR
Legs are numbered from the front; L is the animal's own left. A crab's own front is across the model (it faces
glTF +X or -X and walks along +Z), so its L and R are along z.

place: the joints are found from the mesh and written to joints.json. keep: a kept art/<id>/joints.json is used as
it is (a wrong guess is fixed by hand once); the limbs are then found from its tips. The rigger argument is taken for
make.py's sake: the weights are always the geometric ones.

Joint positions are in glTF metres: x the model's left, y up, z forward (where a walking creature goes)."""
import heapq, itertools, json, math, os, sys
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_common as common      # noqa: E402

clean, out_blend, joints_path, mode, rigger, unirig_npz = common.args()
creature = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(out_blend)))))
bpy.ops.wm.open_mainfile(filepath=clean)
mesh = bpy.data.objects["Mesh"]
for o in list(bpy.context.scene.objects):
    if o is not mesh: bpy.data.objects.remove(o)
bpy.context.view_layer.objects.active = mesh
for o in bpy.context.scene.objects: o.select_set(o is mesh)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# The kinds of crawler. neck and waist: where Head and Abdomen begin, as a share of the trunk's length from its front.
# thin: a vertex is limb where the mesh is thinner than this share of the trunk's thickness.
KINDS = {
    "beetle": dict(legs=3, neck=0.20, waist=0.48, abdomen=True, antennae=True, wings=False, claws=False, tail=0, thin=0.26),
    "bee": dict(legs=3, neck=0.22, waist=0.50, abdomen=True, antennae=True, wings=True, claws=False, tail=0, thin=0.26),
    "spider": dict(legs=4, neck=0.15, waist=0.45, abdomen=True, antennae=False, wings=False, claws=False, tail=0, thin=0.22),
    "scorpion": dict(legs=4, neck=0.18, waist=0.55, abdomen=True, antennae=False, wings=False, claws=True, tail=4, thin=0.45),
    "crab": dict(legs=4, neck=0.15, waist=None, abdomen=False, antennae=False, wings=False, claws=True, tail=0, thin=0.50),
}
KIND_OF = {
    "bottlecap-beetle": "beetle", "darkling-beetle": "beetle", "moss-beetle": "beetle", "mossglow-stag-beetle": "beetle",
    "spotted-garden-beetle": "beetle", "sun-scarab": "beetle", "field-bee": "bee", "honeycrown-bee": "bee",
    "bramble-spider": "spider", "cellar-spider": "spider", "rock-scorpion": "scorpion", "mud-crab": "crab", "one-claw-crab": "crab",
}
# What the placing cannot see for itself, by creature: thin (the share above), facing (a crab's own front: 1 for
# glTF +X, -1 for -X).
TUNE = {
}


def kind_of(name):
    if name in KIND_OF: return KIND_OF[name]
    for word, kind in (("bee", "bee"), ("spider", "spider"), ("scorpion", "scorpion"), ("crab", "crab")):
        if word in name: return kind
    return "beetle"


KIND = kind_of(creature)
K = dict(KINDS[KIND], **TUNE.get(creature, {}))
N = K["legs"]
SIDES = (("L", 1), ("R", -1))
GAP = 0.0008          # metres between the two sides of a split
common.log("crawler: %s is a %s" % (creature, KIND))


def gltf(v): return (v.x, v.z, -v.y)                 # Blender -> glTF
def blender(p): return Vector((p[0], -p[2], p[1]))   # glTF -> Blender


# The animal's own axes (x its left, y up, z its front). A crab's front is across the model: `facing` says which way.
facing = 0


def own(v):
    """Blender point -> the animal's own (left, up, front)."""
    if facing: return (facing * v.y, v.z, facing * v.x)
    return (v.x, v.z, -v.y)


def world(a):
    """The animal's own (left, up, front) -> Blender point."""
    if facing: return Vector((facing * a[2], facing * a[0], a[1]))
    return Vector((a[0], -a[2], a[1]))


def smooth(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)
def mean(points): points = list(points); return tuple(sum(c) / len(points) for c in zip(*points))
def dist(p, q): return math.dist(p, q)


class Surface:
    """The mesh as it is now: its graph, how thick it is at each vertex, the trunk, and each vertex's way to it."""
    def __init__(self):
        me = mesh.data
        self.n = n = len(me.vertices)
        self.co = [v.co.copy() for v in me.vertices]
        self.near = [[] for _ in range(n)]
        for e in me.edges:
            a, b = e.vertices; d = (self.co[a] - self.co[b]).length
            self.near[a].append((b, d)); self.near[b].append((a, d))
        self.area = [0.0] * n
        for p in me.polygons:
            for i in p.vertices: self.area[i] += p.area / len(p.vertices)
        self.bridge()
        lo, hi = common.bounds([mesh])
        self.length = max(hi.x - lo.x, hi.y - lo.y); self.height = hi.z - lo.z
        self.thickness()
        ranked = sorted(range(n), key=lambda i: self.thick[i])
        total, run = sum(self.area), 0.0
        self.body = self.thick[ranked[-1]]
        for i in ranked:
            run += self.area[i]
            if run >= 0.9 * total: self.body = self.thick[i]; break
        self.limit = K["thin"] * self.body
        self.find_trunk()
        self.to_trunk, _, self.pred = self.spread([(i, 0) for i in range(n) if self.trunk[i]])

    def bridge(self):
        """Pieces that hang loose (a leg the mesher left apart) are tied to the main piece at their nearest point."""
        piece, pieces = [-1] * self.n, []
        for s in range(self.n):
            if piece[s] >= 0: continue
            stack, members = [s], []
            piece[s] = len(pieces)
            while stack:
                v = stack.pop(); members.append(v)
                for w, _ in self.near[v]:
                    if piece[w] < 0: piece[w] = len(pieces); stack.append(w)
            pieces.append(members)
        if len(pieces) < 2: return
        main = max(pieces, key=len)
        tree = KDTree(len(main))
        for i in main: tree.insert(self.co[i], i)
        tree.balance()
        for members in pieces:
            if members is main: continue
            d, a, b = min((tree.find(self.co[i])[2], i, tree.find(self.co[i])[1]) for i in members)
            self.near[a].append((b, d)); self.near[b].append((a, d))
        common.log("%d loose pieces tied to the main one" % (len(pieces) - 1))

    def thickness(self):
        """How far it is through the mesh at each vertex: the median of five rays cast inward, then evened out."""
        me = mesh.data
        tree = BVHTree.FromPolygons([tuple(c) for c in self.co], [tuple(p.vertices) for p in me.polygons])
        far = self.length
        thick = []
        for v in me.vertices:
            inward = -v.normal
            side = inward.orthogonal().normalized(); other = inward.cross(side)
            found = []
            for dx, dy in ((0, 0), (0.45, 0), (-0.45, 0), (0, 0.45), (0, -0.45)):
                ray = (inward + side * dx + other * dy).normalized()
                hit = tree.ray_cast(v.co + ray * 1e-5, ray, far)
                found.append(hit[3] if hit[0] is not None else far)
            thick.append(sorted(found)[2])
        for _ in range(2):
            thick = [sorted([thick[i]] + [thick[w] for w, _ in self.near[i]])[(len(self.near[i]) + 1) // 2] for i in range(self.n)]
        self.thick = thick

    def find_trunk(self):
        """The trunk: the largest connected part where the mesh is thick. Specks of thin inside it are the trunk's."""
        fat = [t >= self.limit for t in self.thick]
        best, seen = [], [False] * self.n
        for s in range(self.n):
            if seen[s] or not fat[s]: continue
            stack, members = [s], []
            seen[s] = True
            while stack:
                v = stack.pop(); members.append(v)
                for w, _ in self.near[v]:
                    if fat[w] and not seen[w]: seen[w] = True; stack.append(w)
            if len(members) > len(best): best = members
        self.trunk = [False] * self.n
        for i in best: self.trunk[i] = True
        seen = list(self.trunk)
        for s in range(self.n):
            if seen[s]: continue
            stack, members = [s], []
            seen[s] = True
            while stack:
                v = stack.pop(); members.append(v)
                for w, _ in self.near[v]:
                    if not seen[w]: seen[w] = True; stack.append(w)
            if len(members) < 8:
                for i in members: self.trunk[i] = True

    def spread(self, sources, allowed=None, limit=math.inf):
        """Distances along the surface from the sources [(vertex, label)]: (distance, label, the vertex before)."""
        far = [math.inf] * self.n; label = [-1] * self.n; before = [-1] * self.n
        heap = []
        for v, name in sources: far[v] = 0.0; label[v] = name; heap.append((0.0, v))
        heapq.heapify(heap)
        while heap:
            d, v = heapq.heappop(heap)
            if d > far[v]: continue
            for w, step in self.near[v]:
                if allowed is not None and not allowed[w]: continue
                nd = d + step
                if nd < far[w] and nd <= limit: far[w] = nd; label[w] = label[v]; before[w] = v; heapq.heappush(heap, (nd, w))
        return far, label, before

    def tips(self):
        """The limbs' ends: the farthest point from the trunk, then the farthest not on that limb, and so on."""
        limb = [not t for t in self.trunk]
        least = 0.05 * self.length
        order = sorted((i for i in range(self.n) if limb[i] and self.to_trunk[i] >= least and self.to_trunk[i] < math.inf),
                       key=lambda i: -self.to_trunk[i])
        claimed, tips = [False] * self.n, []
        for t in order:
            if claimed[t]: continue
            reach = self.to_trunk[t]
            slack = 1.7 * self.limit + 0.05 * reach
            far, _, _ = self.spread([(t, 0)], limb, reach + slack)
            for i in range(self.n):
                if far[i] + self.to_trunk[i] <= reach + slack: claimed[i] = True
            tips.append(t)
            if len(tips) >= 40: break
        return tips


def limb_facts(s, tips):
    """Each tip's limb while every tip is its own: where it ends, where it joins the trunk, its length and middle line."""
    limb = [not t for t in s.trunk]
    far, label, _ = s.spread([(t, k) for k, t in enumerate(tips)], limb)
    facts = []
    for k, t in enumerate(tips):
        members = [i for i in range(s.n) if label[i] == k]
        reach = max(far[i] for i in members) or 1e-6
        def centre(lo, hi, members=members, reach=reach):
            pts = [own(s.co[i]) for i in members if lo * reach <= far[i] <= hi * reach]
            return mean(pts) if pts else None
        end = centre(0, 0.08) or own(s.co[t])
        band = 0.2 * reach
        joins = [own(s.co[i]) for i in members if s.to_trunk[i] < band]
        top = mean(joins) if joins else centre(0.85, 1.0) or end
        line = [(u, centre(u - 0.06, u + 0.06)) for u in (0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7)]
        line = [(u, c) for u, c in line if c]
        facts.append(dict(tip=t, end=end, top=top, reach=s.to_trunk[t], line=line, size=len(members),
                          fat=sum(s.thick[i] for i in members) / len(members)))
    return facts


def bend(fact):
    """The knee: the point of the limb's middle line farthest from the straight line between its two ends."""
    a, b = Vector(fact["end"]), Vector(fact["top"])
    chord = b - a
    if chord.length < 1e-6 or not fact["line"]: return tuple((a + b) / 2)
    def off(c):
        p = Vector(c) - a
        return (p - chord * (p.dot(chord) / chord.dot(chord))).length
    u, c = max(fact["line"], key=lambda uc: off(uc[1]))
    if off(c) < 0.08 * chord.length:
        c = min(fact["line"], key=lambda uc: abs(uc[0] - 0.45))[1]
    return c


def torso_facts(s, tail=None):
    """The trunk without the tail, in the animal's own axes: its ends, and the height of its middle along it."""
    pts = [own(s.co[i]) for i in range(s.n) if s.trunk[i] and not (tail and tail[i])]
    z0, z1 = min(p[2] for p in pts), max(p[2] for p in pts)
    span = max(z1 - z0, 1e-6)

    def middle(z):
        near = [p for p in pts if abs(p[2] - z) < 0.07 * span] or pts
        return (min(p[1] for p in near) + max(p[1] for p in near)) / 2

    def girth(z):
        near = [p for p in pts if abs(p[2] - z) < 0.035 * span]
        if not near: return math.inf
        return (max(p[0] for p in near) - min(p[0] for p in near)) * (max(p[1] for p in near) - min(p[1] for p in near))

    def narrowest(share):
        """Near the share given, the place where the trunk is narrowest, when it is clearly narrower there."""
        z = z1 - share * span
        tries = [z + k * 0.02 * span for k in range(-5, 6)]
        best = min(tries, key=girth)
        return best if girth(best) < 0.8 * girth(z) else z
    return dict(z0=z0, z1=z1, span=span, middle=middle, narrowest=narrowest, pts=pts,
                width=max(p[0] for p in pts) - min(p[0] for p in pts), top=max(p[1] for p in pts),
                y=sum(p[1] for p in pts) / len(pts))


def tail_region(s, tip, legs):
    """A scorpion's tail, from its sting: everything nearer the sting along the surface than the hind legs are."""
    far, _, _ = s.spread([(tip, 0)])
    reach = [far[i] for i in legs if far[i] < math.inf]
    length = 0.8 * min(reach) if reach else 0.5 * max(f for f in far if f < math.inf)
    return [f / length if f < length else None for f in far], length


def place(s):
    """The joints, in the animal's own axes, from the limbs' tips."""
    global facing
    if KIND == "crab" and not facing:
        # A crab's claws are held in front of it: its front is the side its two fattest limbs end on.
        facing = int(K.get("facing") or 1)
        if not K.get("facing"):
            fattest = sorted((f for f in limb_facts(s, s.tips()) if f["size"] >= 30), key=lambda f: -f["fat"])[:2]
            middle = sum(own(s.co[i])[2] * s.area[i] for i in range(s.n) if s.trunk[i]) / max(sum(s.area[i] for i in range(s.n) if s.trunk[i]), 1e-9)
            if fattest and sum(f["end"][2] for f in fattest) / len(fattest) < middle: facing = -1
        common.log("the crab faces glTF %sX (where its claws are)" % ("+" if facing > 0 else "-"))
    facts = limb_facts(s, s.tips())
    joints, found = {}, {}
    trunk_pts = [own(s.co[i]) for i in range(s.n) if s.trunk[i]]
    trunk_y = sum(p[1] for p in trunk_pts) / len(trunk_pts)
    free = list(facts)

    def take(chosen):
        for f in chosen:
            if f in free: free.remove(f)

    # Claws: the fattest limb of each side that ends ahead of the middle of the trunk, with any other tip close to
    # its end (the second finger of a pincer).
    if K["claws"]:
        trunk_z = sum(p[2] for p in trunk_pts) / len(trunk_pts)
        for side, sign in SIDES:
            mine = [f for f in free if f["end"][0] * sign > 0]
            if len(mine) < 2: continue
            claw = max([f for f in mine if f["end"][2] > trunk_z] or mine, key=lambda f: f["fat"])
            fingers = [f for f in mine if f is not claw and dist(f["end"], claw["end"]) < 0.5 * claw["reach"] and f["reach"] < 0.6 * claw["reach"]]
            take([claw] + fingers)
            joints["claw_" + side] = claw["top"]; joints["wrist_" + side] = bend(claw); joints["pincer_" + side] = claw["end"]
            for k, f in enumerate(fingers): joints["pincer_%s_%d" % (side, k + 2)] = f["end"]
    # Legs: the limbs that end low (every limb left, for a crab), the longest N a side, numbered from the front by
    # where they join the trunk.
    low = [f for f in free if KIND == "crab" or f["end"][1] < 0.45 * trunk_y]
    sides = {}
    for side, sign in SIDES:
        mine = sorted((f for f in low if f["end"][0] * sign > 0), key=lambda f: -f["reach"])[:N]
        sides[side] = sorted(mine, key=lambda f: -(f["top"][2] + f["end"][2]))
        take(sides[side])
    for side, sign in SIDES:
        mine, others = sides[side], sides["R" if side == "L" else "L"]
        slots = list(range(len(mine)))
        if len(mine) < N and len(others) == N:
            # Fewer than the other side: each takes the number of the other side's leg it stands nearest.
            slots = min(itertools.combinations(range(N), len(mine)),
                        key=lambda c: sum(abs(f["top"][2] - others[k]["top"][2]) + abs(f["end"][2] - others[k]["end"][2]) for f, k in zip(mine, c)))
        for f, k in zip(mine, slots):
            name = "%d%s" % (k + 1, side)
            joints["hip_" + name] = f["top"]; joints["knee_" + name] = bend(f); joints["foot_" + name] = f["end"]
        found["legs_" + side] = len(mine)
    leg_names = [k[5:] for k in joints if k.startswith("foot_")]

    # The tail: the point of the upper mesh farthest along the surface from the nose is the sting.
    tail = None
    if K["tail"]:
        nose = max((i for i in range(s.n) if s.trunk[i]), key=lambda i: own(s.co[i])[2])
        far, _, _ = s.spread([(nose, 0)])
        high = [i for i in range(s.n) if far[i] < math.inf and own(s.co[i])[1] > trunk_y]
        tip = max(high, key=lambda i: far[i])
        limb = [not t for t in s.trunk]
        _, label, _ = s.spread([(s.nearest(world(joints["foot_" + name]), limb), name) for name in leg_names], limb) if leg_names else (None, [-1] * s.n, None)
        along, length = tail_region(s, tip, [i for i in range(s.n) if label[i] != -1])
        tail = [u is not None for u in along]
        for k in range(K["tail"] + 1):
            u = 1 - k / K["tail"]
            ring = [own(s.co[i]) for i in range(s.n) if along[i] is not None and abs(along[i] - u) < 0.07]
            joints["tail%d" % k] = mean(ring) if ring else own(s.co[tip])
        joints["tail%d" % K["tail"]] = own(s.co[tip])
        found["tail"] = round(length, 4)
        take([f for f in free if tail[f["tip"]]])

    t = torso_facts(s, tail)
    neck_z = t["narrowest"](K["neck"])
    # Feelers and wings: of the limbs left, the ones on the head are feelers, the ones above the back are wings.
    if K["antennae"]:
        for side, sign in SIDES:
            mine = [f for f in free if f["end"][0] * sign > 0 and f["top"][2] > neck_z - 0.05 * t["span"] and f["end"][2] > neck_z]
            if not mine: continue
            feeler = max(mine, key=lambda f: f["reach"]); take([feeler])
            joints["antenna_" + side] = feeler["top"]; joints["antenna_%s_tip" % side] = feeler["end"]
    if K["wings"]:
        above = sorted((f for f in free if f["end"][1] > t["y"] and f["end"][2] < neck_z), key=lambda f: -f["size"])[:2]
        above.sort(key=lambda f: -f["end"][0])
        if len(above) == 1 and above[0]["end"][0] < 0: above.insert(0, None)
        for (side, sign), f in zip(SIDES, above):
            if f is None: continue
            take([f])
            joints["wing_" + side] = f["top"]; joints["wing_%s_tip" % side] = f["end"]
    found["other_limbs"] = len(free)

    # The trunk's own joints, on its middle line.
    if KIND == "crab":
        waist_z = t["z0"] + 0.25 * t["span"]
    else:
        waist_z = t["narrowest"](K["waist"])
    mid = (t["z0"] + t["z1"]) / 2
    joints["root"] = (0.0, 0.0, mid); joints["root_up"] = (0.0, 0.25 * t["y"], mid)
    joints["waist"] = (0.0, t["middle"](waist_z), waist_z)
    joints["neck"] = (0.0, t["middle"](neck_z), neck_z)
    joints["nose"] = (0.0, t["middle"](t["z1"] - 0.03 * t["span"]), t["z1"])
    if K["abdomen"]: joints["rear"] = (0.0, t["middle"](t["z0"] + 0.05 * t["span"]), t["z0"])
    found.update(length=round(t["span"], 4), width=round(t["width"], 4), top=round(t["top"], 4), kind=KIND, facing=facing,
                 thickness=round(s.body, 4), thin_below=round(s.limit, 4))
    return joints, found


def nearest(s, point, allowed=None):
    best, at = math.inf, -1
    for i in range(s.n):
        if allowed is not None and not allowed[i]: continue
        d = (s.co[i] - point).length_squared
        if d < best: best, at = d, i
    return at
Surface.nearest = nearest


def bone_list(joints):
    """(name, parent, head joint, tail joint) for this kind: the same names whatever the mesh has."""
    bones = [("Root", None, "root", "root_up"), ("Body", "Root", "waist", "neck"), ("Head", "Body", "neck", "nose")]
    if K["abdomen"]: bones.append(("Abdomen", "Body", "waist", "rear"))
    for k in range(1, N + 1):
        for side, _ in SIDES:
            name = "%d%s" % (k, side)
            bones += [("Leg" + name, "Body", "hip_" + name, "knee_" + name), ("Shin" + name, "Leg" + name, "knee_" + name, "foot_" + name)]
    if K["claws"]:
        for side, _ in SIDES:
            bones += [("Claw" + side, "Body", "claw_" + side, "wrist_" + side), ("Pincer" + side, "Claw" + side, "wrist_" + side, "pincer_" + side)]
    for k in range(K["tail"]):
        bones.append(("Tail%d" % (k + 1), ("Abdomen" if K["abdomen"] else "Body") if k == 0 else "Tail%d" % k, "tail%d" % k, "tail%d" % (k + 1)))
    if K["antennae"]:
        for side, _ in SIDES: bones.append(("Antenna" + side, "Head", "antenna_" + side, "antenna_%s_tip" % side))
    if K["wings"]:
        for side, _ in SIDES: bones.append(("Wing" + side, "Body", "wing_" + side, "wing_%s_tip" % side))
    return bones


def stand_ins(joints):
    """Joints for the limbs the mesh does not have: the other side's, mirrored, or a plain guess from the trunk. Their
    bones carry no weight. Returns the names of the bones that stand in."""
    waist, neck, nose = joints["waist"], joints["neck"], joints["nose"]
    wide = 0.5 * abs(nose[2] - waist[2]) + 0.005
    missing = []

    def fill(keys, side, guess, bones):
        if all(k in joints for k in keys): return
        sign = 1 if side == "L" else -1
        flip = "R" if side == "L" else "L"
        for k, g in zip(keys, guess):
            twin = k[:-1] + flip if k.endswith(side) else k.replace("_%s_" % side, "_%s_" % flip)
            joints[k] = (-joints[twin][0], joints[twin][1], joints[twin][2]) if twin in joints and twin != k else (sign * g[0], g[1], g[2])
        missing.extend(bones)
    for k in range(1, N + 1):
        z = neck[2] + (waist[2] - neck[2]) * (k - 1) / max(N - 1, 1)
        for side, _ in SIDES:
            name = "%d%s" % (k, side)
            fill(["hip_" + name, "knee_" + name, "foot_" + name], side,
                 [(0.4 * wide, waist[1], z), (0.9 * wide, 1.1 * waist[1], z), (1.2 * wide, 0.0, z)], ["Leg" + name, "Shin" + name])
    if K["claws"]:
        for side, _ in SIDES:
            fill(["claw_" + side, "wrist_" + side, "pincer_" + side], side,
                 [(0.4 * wide, neck[1], neck[2]), (0.8 * wide, neck[1], nose[2]), (0.6 * wide, neck[1], nose[2] + 0.5 * wide)], ["Claw" + side, "Pincer" + side])
    if K["antennae"]:
        for side, _ in SIDES:
            fill(["antenna_" + side, "antenna_%s_tip" % side], side, [(0.15 * wide, nose[1], nose[2]), (0.3 * wide, nose[1], nose[2] + 0.4 * wide)], ["Antenna" + side])
    if K["wings"]:
        for side, _ in SIDES:
            fill(["wing_" + side, "wing_%s_tip" % side], side, [(0.2 * wide, 1.6 * waist[1], neck[2]), (0.3 * wide, 1.8 * waist[1], waist[2] - wide)], ["Wing" + side])
    if K["tail"] and "tail0" not in joints:
        rear = joints.get("rear", waist)
        for k in range(K["tail"] + 1): joints["tail%d" % k] = (0.0, rear[1] + 0.2 * wide * k, rear[2] - 0.1 * wide * k)
        missing.extend("Tail%d" % (k + 1) for k in range(K["tail"]))
    return missing


def limbs_of(s, joints, absent):
    """Each vertex's limb, from the joints: (labels, distance from the limb's tip, the tail's share along it).
    A limb is named by its chain of bones; limbs the kind has no bones for are "" and move with the trunk."""
    limb = [not t for t in s.trunk]
    seeds = []          # (joint key of a tip, the limb's name)
    for k in range(1, N + 1):
        for side, _ in SIDES:
            if "Leg%d%s" % (k, side) not in absent: seeds.append(("foot_%d%s" % (k, side), "Leg%d%s" % (k, side)))
    if K["claws"]:
        for side, _ in SIDES:
            if "Claw" + side in absent: continue
            seeds.append(("pincer_" + side, "Claw" + side))
            seeds += [(key, "Claw" + side) for key in joints if key.startswith("pincer_%s_" % side)]
    if K["antennae"]: seeds += [("antenna_%s_tip" % side, "Antenna" + side) for side, _ in SIDES if "Antenna" + side not in absent]
    if K["wings"]: seeds += [("wing_%s_tip" % side, "Wing" + side) for side, _ in SIDES if "Wing" + side not in absent]
    sources = []
    for key, name in seeds:
        v = s.nearest(world(joints[key]), limb)
        if v >= 0: sources.append((v, name))
    # Every other limb end the mesh has (a palp, a spur) is its own, so that it is not taken for a leg's.
    for t in s.tips():
        here = own(s.co[t])
        if all(dist(here, joints[key]) > max(0.2 * s.to_trunk[t], 2 * s.limit) for key, _ in seeds): sources.append((t, ""))
    far, label, _ = s.spread(sources, limb)
    label = [name if name != -1 else "" for name in label]
    along = None
    if K["tail"] and "Tail1" not in absent:
        tip = s.nearest(world(joints["tail%d" % K["tail"]]))
        along, _ = tail_region(s, tip, [i for i in range(s.n) if label[i].startswith("Leg")])
        for i in range(s.n):
            if along[i] is not None and (label[i] == "" or s.trunk[i]): label[i] = "Tail"
            else: along[i] = None
    return label, far, along


def split_limbs(s, label):
    """Where two limbs' faces meet (legs the mesher fused), the surface is split, each side drawn back a little and
    capped, so neither limb drags a web of the other. Returns what it did, or None when nothing touched."""
    me = mesh.data
    names = sorted({name for name in label if name and name != "Tail"})
    number = {name: k + 1 for k, name in enumerate(names)}
    middle = {}
    for name in names: middle[name] = mean(tuple(s.co[i]) for i in range(s.n) if label[i] == name)
    bm = bmesh.new(); bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    side = bm.faces.layers.int.new("limb")
    for f in bm.faces:
        mine = [label[v.index] for v in f.verts]
        if any(name not in number for name in mine): continue
        f[side] = number[max(set(mine), key=mine.count)]
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.link_faces[0][side] and e.link_faces[1][side]
             and e.link_faces[0][side] != e.link_faces[1][side]]
    if not edges: bm.free(); return None
    across = {}
    for e in edges:
        pair = {f[side] for f in e.link_faces}
        for v in e.verts: across.setdefault(tuple(round(c, 7) for c in v.co), set()).update(pair)
    bmesh.ops.split_edges(bm, edges=edges)
    open_edges = [e for e in bm.edges if e.is_boundary and all(f[side] for f in e.link_faces)]
    for v in {v for e in open_edges for v in e.verts}:
        mine = {f[side] for f in v.link_faces}
        if len(mine) != 1: continue                        # where the split ends, the vertex is both limbs'
        me_, = mine
        others = across.get(tuple(round(c, 7) for c in v.co), set()) - mine
        if not others: continue
        away = Vector(middle[names[me_ - 1]]) - Vector(middle[names[min(others) - 1]])
        if away.length > 1e-9: v.co = v.co + away.normalized() * (GAP / 2)
    caps = bmesh.ops.holes_fill(bm, edges=open_edges, sides=0)["faces"]
    caps += close_loops(bm, [e for e in open_edges if e.is_valid and e.is_boundary])
    for f in caps:
        near = [lf[side] for e in f.edges for lf in e.link_faces if lf is not f and lf[side]]
        f[side] = max(set(near), key=near.count) if near else 0
        for loop in f.loops:
            other = next((l for l in loop.vert.link_loops if l.face not in caps), None)
            if other and uv: loop[uv].uv = other[uv].uv
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free(); me.update()
    me.attributes.remove(me.attributes["limb"])
    return "limbs split along %d edges, %d caps" % (len(edges), len(caps))


def close_loops(bm, edges):
    """What holes_fill leaves open (it skips some slits): walk each boundary loop and close it with one face, then
    triangles."""
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


def quarter_turns(s):
    """How many quarter turns about the vertical bring the head to glTF +Z (a crab: its legs' span along z). The clean
    step lays the longest side along z, which for a spider is the span of its legs: the trunk says better. The head
    end is the one the limbs join (legs and feelers grow from the front half of a beetle, a bee, a spider, a scorpion)."""
    if "turn" in K: return int(K["turn"]) % 4
    which = [i for i in range(s.n) if s.trunk[i] != (KIND == "crab")]
    if len(which) < 10: return 0
    w = sum(s.area[i] for i in which) or 1e-9
    cx = sum(s.co[i].x * s.area[i] for i in which) / w; cy = sum(s.co[i].y * s.area[i] for i in which) / w
    xx = sum(s.area[i] * (s.co[i].x - cx) ** 2 for i in which); yy = sum(s.area[i] * (s.co[i].y - cy) ** 2 for i in which)
    xy = sum(s.area[i] * (s.co[i].x - cx) * (s.co[i].y - cy) for i in which)
    phi = 0.5 * math.atan2(2 * xy, xx - yy)
    ax, ay = math.cos(phi), math.sin(phi)
    if KIND == "crab": return 1 if abs(ax) > abs(ay) else 0
    spread = sorted([sum(s.area[i] * ((s.co[i].x - cx) * ax + (s.co[i].y - cy) * ay) ** 2 for i in which),
                     sum(s.area[i] * (-(s.co[i].x - cx) * ay + (s.co[i].y - cy) * ax) ** 2 for i in which)])
    if spread[1] < 1.2 * spread[0]: return 0                 # a round trunk says nothing
    roots = [i for i in range(s.n) if not s.trunk[i] and s.to_trunk[i] < 2 * s.limit]
    lean = sum(s.area[i] * ((s.co[i].x - cx) * ax + (s.co[i].y - cy) * ay) for i in roots)
    if lean < 0: ax, ay = -ax, -ay
    return round((-math.pi / 2 - math.atan2(ay, ax)) / (math.pi / 2)) % 4


def turn_mesh(quarters):
    from mathutils import Matrix
    mesh.data.transform(Matrix.Rotation(quarters * math.pi / 2, 4, "Z")); mesh.data.update()
    lo, hi = common.bounds([mesh])
    mesh.data.transform(Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, 0))); mesh.data.update()


# ---- the joints
s = Surface()
kept = json.load(open(joints_path)) if mode == "keep" else None
turned = int(kept.get("found", {}).get("turned", 0)) if kept else quarter_turns(s)
if turned:
    turn_mesh(turned)
    s = Surface()
    common.log("the mesh was turned %d degrees about the vertical: its head was not along glTF +Z" % (turned * 90))
common.log("trunk %.4f m thick; thinner than %.4f m is limb: %d of %d vertices" % (s.body, s.limit, sum(1 for t in s.trunk if not t), s.n))
if mode == "keep":
    facing = int(kept.get("found", {}).get("facing", 0))
    if KIND == "crab" and not facing: facing = int(K.get("facing") or 1)
    joints = {k: own(blender(v)) for k, v in kept["joints"].items()}
    common.log("joints kept from", joints_path)
else:
    joints, found = place(s)
    found["turned"] = turned
    with open(joints_path, "w") as f:
        json.dump({"joints": {k: [round(c, 5) for c in gltf(world(v))] for k, v in joints.items()}, "found": found,
                   "axes": "glTF metres: x left, y up, z forward"}, f, indent=2)
    common.log("joints placed from the mesh: %d legs on the left, %d on the right, %d limbs of no kind; written to %s"
               % (found["legs_L"], found["legs_R"], found["other_limbs"], joints_path))
absent = stand_ins(joints)
if absent: common.log("not in the mesh, so their bones carry no weight:", ", ".join(absent))
BONES = bone_list(joints)

# ---- limbs that touch are split apart, then the mesh is read again
label, far, along = limbs_of(s, joints, absent)
did = split_limbs(s, label)
if did:
    s = Surface()
    label, far, along = limbs_of(s, joints, absent)
common.log("limbs:", did or "none touch")

# ---- the armature
data = bpy.data.armatures.new("Skeleton")
rig = bpy.data.objects.new("Skeleton", data)
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
for o in bpy.context.scene.objects: o.select_set(o is rig)
bpy.ops.object.mode_set(mode="EDIT")
for name, parent, head, tail in BONES:
    b = data.edit_bones.new(name)
    b.head, b.tail = world(joints[head]), world(joints[tail])
    if (b.tail - b.head).length < 1e-4: b.tail = b.head + Vector((0, 0, 0.003))
    if parent: b.parent = data.edit_bones[parent]; b.use_connect = False
    b.align_roll(Vector((0, -1, 0)) if abs((b.tail - b.head).normalized().y) < 0.9 else Vector((0, 0, 1)))
bpy.ops.object.mode_set(mode="OBJECT")
data.bones["Root"].use_deform = False

# ---- weights, from the geometry
neck, waist = joints["neck"], joints["waist"]
span = abs(joints["nose"][2] - joints.get("rear", waist)[2]) or 1e-6


def trunk_weights(a):
    """Head, Body and Abdomen by where the point lies along the animal."""
    band = 0.05 * span
    head = smooth((a[2] - (neck[2] - band)) / (2 * band))
    rear = 1 - smooth((a[2] - (waist[2] - band)) / (2 * band)) if K["abdomen"] else 0.0
    rear = min(rear, 1 - head)
    w = {"Head": head, "Body": 1 - head - rear}
    if rear > 0: w["Abdomen"] = rear
    return w


def chain_of(name):
    """A limb's bones from its tip inward, and the joints between them."""
    if name.startswith("Leg"): return ["Shin" + name[3:], name], ["knee_" + name[3:]]
    if name.startswith("Claw"): return ["Pincer" + name[4:], name], ["wrist_" + name[4:]]
    return [name], []


reach, turn = {}, {}
for name in sorted({n_ for n_ in label if n_ and n_ != "Tail"}):
    members = [i for i in range(s.n) if label[i] == name]
    reach[name] = max(far[i] for i in members) or 1e-6
    turn[name] = []
    for key in chain_of(name)[1]:
        ring = sorted(members, key=lambda i: (s.co[i] - world(joints[key])).length_squared)[:6]
        turn[name].append(min(0.9, max(0.1, sum(far[i] for i in ring) / len(ring) / reach[name])))


def along_chain(bones, turns, u, blend=0.07):
    """Weights along a chain of bones (tip first) at the share u of its length from the tip."""
    w = {}
    for k, bone in enumerate(bones):
        lower = smooth((u - (turns[k - 1] - blend)) / (2 * blend)) if k > 0 else 1.0
        upper = 1 - smooth((u - (turns[k] - blend)) / (2 * blend)) if k < len(turns) else 1.0
        if lower * upper > 0: w[bone] = lower * upper
    return w


groups = {name: mesh.vertex_groups.new(name=name) for name, _, _, _ in BONES if name != "Root"}
counts, most = {}, 0
for i in range(s.n):
    a = own(s.co[i])
    name = label[i]
    w = trunk_weights(a)
    if name == "Tail":
        u = along[i]
        tail_bones = ["Tail%d" % k for k in range(K["tail"], 0, -1)]
        limb_w = along_chain(tail_bones, [k / K["tail"] for k in range(1, K["tail"])], u, 0.06)
        join = smooth((u - 0.82) / 0.18)
    elif name:
        bones, _ = chain_of(name)
        limb_w = along_chain(bones, turn[name], far[i] / reach[name])
        join = 1 - smooth(s.to_trunk[i] / (0.2 * reach[name]))
    else:
        limb_w, join = {}, 1.0
    total = sum(limb_w.values()) or 1.0
    w = {k: v * join for k, v in w.items()}
    for k, v in limb_w.items(): w[k] = w.get(k, 0.0) + v / total * (1 - join)
    top = sorted(((v, k) for k, v in w.items() if v > 1e-4), reverse=True)[:4]
    total = sum(v for v, _ in top)
    for v, k in top: groups[k].add([i], v / total, "REPLACE")
    most = max(most, len(top))
    counts[name or "trunk"] = counts.get(name or "trunk", 0) + 1
common.log("weights from the geometry: " + ", ".join("%s %d" % kv for kv in sorted(counts.items())))
common.log("at most %d bones a vertex" % most)

mesh.parent = rig
m = mesh.modifiers.new("Skeleton", "ARMATURE"); m.object = rig
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
for o in bpy.context.scene.objects: o.select_set(o in (mesh, rig))
bpy.ops.export_scene.gltf(filepath=os.path.join(os.path.dirname(out_blend), "rig-%s.glb" % rigger), use_selection=True, export_format="GLB",
                          export_skins=True, export_animations=False, export_def_bones=False, export_image_format="JPEG")
with open(os.path.join(os.path.dirname(out_blend), "rig.json"), "w") as f:
    json.dump({"rigger": "geometry", "kind": KIND, "joints": mode, "facing": facing, "turned": turned, "unweighted_fixed": 0, "max_influences": most,
               "bones": [b[0] for b in BONES], "absent": absent, "limbs": counts}, f, indent=2)
