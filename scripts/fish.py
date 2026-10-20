"""The aquarium's fish: a small reef fish (in two colourings) and a trout as glTF binaries, written by hand
(standard library only).

Each body is a lofted tube, elliptical sections along z from the nose (+z) to the tail, painted by triangle:
the reef fish's white bands with black edges, the trout's olive back, pink flank, cream belly and its spots.
Flat double-sided fins and two black eyes complete it. The caudal fin and the pectoral fins are their own
nodes, so the clips can move them: "swim" sways the body and beats the tail quickly, "idle" sways slowly
with the pectoral fins paddling. Metres, +Y up, the head along +Z (heading 0 faces +Z in JsonScene), the
origin at mid-body, which is what an air actor's position is.

    python3 scripts/fish.py <out>    ->   <out>/models/fish.glb, fish-blue.glb, trout.glb
"""
import json, math, random, struct, sys

out = sys.argv[1]


# ---- vectors --------------------------------------------------------------------------------------------

def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def add(a, b): return tuple(x + y for x, y in zip(a, b))
def mul(a, k): return tuple(x * k for x in a)
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a):
    length = math.sqrt(sum(x * x for x in a)) or 1.0
    return tuple(x / length for x in a)


class Profile:
    """A smooth curve through (t, value) knots, Catmull-Rom between them."""
    def __init__(self, knots):
        self.knots = sorted(knots)

    def __call__(self, t):
        k = self.knots
        t = min(max(t, k[0][0]), k[-1][0])
        i = max(j for j in range(len(k) - 1) if k[j][0] <= t)
        t0, v0 = k[max(i - 1, 0)]; t1, v1 = k[i]; t2, v2 = k[i + 1]; t3, v3 = k[min(i + 2, len(k) - 1)]
        s = (t - t1) / (t2 - t1) if t2 > t1 else 0.0
        return 0.5 * (2 * v1 + (-v0 + v2) * s + (2 * v0 - 5 * v1 + 4 * v2 - v3) * s * s + (-v0 + 3 * v1 - 3 * v2 + v3) * s * s * s)


# ---- geometry -------------------------------------------------------------------------------------------

class Primitive:
    def __init__(self, material):
        self.material, self.positions, self.normals, self.triangles = material, [], [], []

    def add(self, part):
        positions, normals, triangles = part
        base = len(self.positions)
        self.positions += positions
        self.normals += normals
        self.triangles += [(a + base, b + base, c + base) for a, b, c in triangles]


def loft(z0, z1, rx, ry, along, around, paint):
    """Elliptical sections from z0 (t = 0, the nose) to z1 (t = 1, the tail), each triangle painted with the
    material `paint(t, theta)` gives for its middle. Returns one Primitive per material used."""
    def point(t, theta):
        return (rx(t) * math.cos(theta), ry(t) * math.sin(theta), z0 + (z1 - z0) * t)

    positions, normals = [], []
    e = 1e-3
    for i in range(along + 1):
        t = i / along
        for j in range(around + 1):
            theta = 2 * math.pi * j / around
            positions.append(point(t, theta))
            dt = sub(point(min(t + e, 1), theta), point(max(t - e, 0), theta))
            dth = sub(point(t, theta + e), point(t, theta - e))
            normals.append(norm(cross(dt, dth)))
    prims, index = {}, {}

    def vertex(prim, v):
        """The vertex v of the loft in prim, added the first time prim uses it."""
        key = (prim.material, v)
        if key not in index:
            index[key] = len(prim.positions)
            prim.positions.append(positions[v])
            prim.normals.append(normals[v])
        return index[key]

    for i in range(along):
        for j in range(around):
            a = i * (around + 1) + j
            b = a + around + 1
            material = paint((i + 0.5) / along, 2 * math.pi * (j + 0.5) / around)
            prim = prims.setdefault(material, Primitive(material))
            for tri in ((a, b, a + 1), (a + 1, b, b + 1)):
                prim.triangles.append(tuple(vertex(prim, v) for v in tri))
    return list(prims.values())


def sphere(cx, cy, cz, r, segments=10, rings=6):
    positions, normals, triangles = [], [], []
    for i in range(rings + 1):
        phi = math.pi * i / rings
        for j in range(segments + 1):
            theta = 2 * math.pi * j / segments
            n = (math.sin(phi) * math.cos(theta), math.cos(phi), math.sin(phi) * math.sin(theta))
            positions.append((cx + r * n[0], cy + r * n[1], cz + r * n[2]))
            normals.append(n)
    for i in range(rings):
        for j in range(segments):
            a = i * (segments + 1) + j
            b = a + segments + 1
            if i > 0: triangles.append((a, b, a + 1))
            if i < rings - 1: triangles.append((a + 1, b, b + 1))
    return positions, normals, triangles


def fin(polygon, origin, u, v):
    """A flat polygon with 2D points (a, b) laid in the plane origin + a*u + b*v, fanned from its first point
    (the shapes are star-shaped from it). Double sided; the normal is u x v, the fan wound to match."""
    u, v = norm(u), norm(v)
    n = norm(cross(u, v))
    positions = [add(origin, add(mul(u, a), mul(v, b))) for a, b in polygon]
    area = sum(polygon[i][0] * polygon[i + 1][1] - polygon[i + 1][0] * polygon[i][1] for i in range(len(polygon) - 1))
    triangles = [(0, i, i + 1) if area > 0 else (0, i + 1, i) for i in range(1, len(polygon) - 1)]
    return positions, [n] * len(positions), triangles


# ---- species --------------------------------------------------------------------------------------------

def reef(colours):
    """A small reef fish, 12 cm nose to tail: deep bodied, round fins, three white bands edged in black."""
    body_mat, band_mat, edge_mat, fin_mat = colours
    nose, tail = 0.052, -0.040
    rx = Profile([(0, 0.0025), (0.15, 0.009), (0.4, 0.013), (0.7, 0.010), (1, 0.0045)])
    ry = Profile([(0, 0.004), (0.1, 0.018), (0.3, 0.029), (0.5, 0.030), (0.75, 0.021), (0.9, 0.012), (1, 0.008)])
    bands = [(0.024, 0.034), (-0.010, 0.001), (-0.040, -0.031)]
    edge = 0.0016

    def paint(t, theta):
        z = nose + (tail - nose) * t
        for lo, hi in bands:
            if lo <= z <= hi: return band_mat
            if lo - edge <= z < lo or hi < z <= hi + edge: return edge_mat
        return body_mat

    body = loft(nose, tail, rx, ry, 56, 24, paint)
    eyes = Primitive(EYE)
    for side in (1, -1):
        eyes.add(sphere(side * rx(0.17) * 0.85, ry(0.17) * 0.25, nose + (tail - nose) * 0.17, 0.0032))
    fins = Primitive(fin_mat)
    fins.add(fin([(0.024, 0.018), (0.014, 0.041), (-0.006, 0.044), (-0.030, 0.030), (-0.030, 0.012)], (0, 0, 0), (0, 0, 1), (0, 1, 0)))      # dorsal
    fins.add(fin([(-0.004, -0.018), (-0.012, -0.034), (-0.028, -0.030), (-0.030, -0.010)], (0, 0, 0), (0, 0, 1), (0, 1, 0)))              # anal
    for side in (1, -1):
        fins.add(fin([(0, 0), (0.010, 0.003), (0.014, 0.010), (0.009, 0.015), (0, 0.010)], (side * 0.007, -0.014, 0.012), (side, -0.7, 0), (0, 0, -1)))  # pelvic
    tail_fin = Primitive(fin_mat)
    tail_fin.add(fin([(0, -0.008), (0.012, -0.017), (0.030, -0.023), (0.024, 0), (0.030, 0.023), (0.012, 0.017), (0, 0.008)], (0, 0, 0), (0, 0, -1), (0, 1, 0)))
    pecs = {}
    for name, side in (("PecL", -1), ("PecR", 1)):
        p = Primitive(fin_mat)
        p.add(fin([(0, 0), (0.012, 0.003), (0.018, 0.011), (0.012, 0.017), (0, 0.011)], (0, 0, 0), (side, -0.35, 0), (0, 0, -1)))
        pecs[name] = p
    return {
        "name": "Fish",
        "meshes": {"Body": body + [eyes, fins], "Tail": [tail_fin], "PecL": [pecs["PecL"]], "PecR": [pecs["PecR"]]},
        "positions": {"Body": (0, 0, 0), "Tail": (0, 0, tail), "PecL": (-0.011, -0.004, 0.024), "PecR": (0.011, -0.004, 0.024)},
        "swim": {"period": 0.4, "body": 3, "tail": 25, "pec": 6}, "idle": {"period": 1.6, "body": 1, "tail": 8, "pec": 25},
    }


def trout():
    """A brown trout about half a metre long: olive back with dark spots, a few red ones on the pink flank,
    a cream belly, a forked tail and an adipose fin."""
    nose, tail = 0.26, -0.18
    rx = Profile([(0, 0.004), (0.1, 0.02), (0.35, 0.034), (0.6, 0.030), (0.85, 0.016), (1, 0.010)])
    ry = Profile([(0, 0.006), (0.08, 0.030), (0.25, 0.052), (0.45, 0.056), (0.7, 0.042), (0.9, 0.024), (1, 0.017)])
    length = nose - tail
    rng = random.Random(7)
    spots = [(rng.uniform(0.08, 0.95), rng.uniform(-0.3, math.pi + 0.3), rng.uniform(0.0035, 0.0065), SPOT) for _ in range(80)]
    spots += [(rng.uniform(0.2, 0.9), rng.choice([0.0, math.pi]) + rng.uniform(-0.35, 0.35), rng.uniform(0.003, 0.005), RED) for _ in range(16)]

    def paint(t, theta):
        y = math.sin(theta)
        r = (rx(t) + ry(t)) / 2
        for ts, ths, rad, mat in spots:
            d = (theta - ths + math.pi) % (2 * math.pi) - math.pi
            if ((t - ts) * length) ** 2 + (d * r) ** 2 < rad * rad: return mat
        if y > 0.35: return BACK
        if y < -0.5: return BELLY
        return FLANK

    body = loft(nose, tail, rx, ry, 120, 40, paint)
    eyes = Primitive(EYE)
    for side in (1, -1):
        eyes.add(sphere(side * rx(0.12) * 0.85, ry(0.12) * 0.3, nose + (tail - nose) * 0.12, 0.0075))
    fins = Primitive(FIN)
    fins.add(fin([(0.06, 0.035), (0.03, 0.085), (-0.02, 0.09), (-0.06, 0.05), (-0.06, 0.03)], (0, 0, 0), (0, 0, 1), (0, 1, 0)))           # dorsal
    fins.add(fin([(-0.11, 0.025), (-0.12, 0.045), (-0.145, 0.04), (-0.145, 0.02)], (0, 0, 0), (0, 0, 1), (0, 1, 0)))                       # adipose
    fins.add(fin([(-0.08, -0.025), (-0.09, -0.06), (-0.135, -0.055), (-0.145, -0.018)], (0, 0, 0), (0, 0, 1), (0, 1, 0)))                 # anal
    for side in (1, -1):
        fins.add(fin([(0, 0), (0.03, 0.01), (0.04, 0.03), (0.02, 0.042), (0, 0.02)], (side * 0.02, -0.03, 0.0), (side, -0.6, 0), (0, 0, -1)))   # pelvic
    tail_fin = Primitive(FIN)
    tail_fin.add(fin([(0, -0.016), (0.04, -0.05), (0.085, -0.062), (0.068, 0), (0.085, 0.062), (0.04, 0.05), (0, 0.016)], (0, 0, 0), (0, 0, -1), (0, 1, 0)))
    pecs = {}
    for name, side in (("PecL", -1), ("PecR", 1)):
        p = Primitive(FIN)
        p.add(fin([(0, 0), (0.036, 0.012), (0.05, 0.036), (0.026, 0.052), (0, 0.026)], (0, 0, 0), (side, -0.4, 0), (0, 0, -1)))
        pecs[name] = p
    return {
        "name": "Trout",
        "meshes": {"Body": body + [eyes, fins], "Tail": [tail_fin], "PecL": [pecs["PecL"]], "PecR": [pecs["PecR"]]},
        "positions": {"Body": (0, 0, 0), "Tail": (0, 0, tail), "PecL": (-0.03, -0.014, 0.14), "PecR": (0.03, -0.014, 0.14)},
        "swim": {"period": 0.7, "body": 3, "tail": 22, "pec": 5}, "idle": {"period": 2.5, "body": 1, "tail": 7, "pec": 20},
    }


# Materials, by index into MATERIALS.
EYE, ORANGE, WHITE, BLACK, ORANGE_FIN, BLUE, NAVY, YELLOW_FIN, BACK, FLANK, BELLY, SPOT, RED, FIN = range(14)
MATERIALS = [
    {"name": "eye", "pbrMetallicRoughness": {"baseColorFactor": [0.02, 0.02, 0.02, 1], "metallicFactor": 0, "roughnessFactor": 0.3}},
    {"name": "orange", "pbrMetallicRoughness": {"baseColorFactor": [0.95, 0.42, 0.06, 1], "metallicFactor": 0, "roughnessFactor": 0.6}},
    {"name": "white", "pbrMetallicRoughness": {"baseColorFactor": [0.96, 0.96, 0.92, 1], "metallicFactor": 0, "roughnessFactor": 0.6}},
    {"name": "black", "pbrMetallicRoughness": {"baseColorFactor": [0.05, 0.05, 0.05, 1], "metallicFactor": 0, "roughnessFactor": 0.7}},
    {"name": "orange-fin", "doubleSided": True, "pbrMetallicRoughness": {"baseColorFactor": [0.97, 0.52, 0.12, 1], "metallicFactor": 0, "roughnessFactor": 0.8}},
    {"name": "blue", "pbrMetallicRoughness": {"baseColorFactor": [0.08, 0.32, 0.92, 1], "metallicFactor": 0, "roughnessFactor": 0.55}},
    {"name": "navy", "pbrMetallicRoughness": {"baseColorFactor": [0.03, 0.05, 0.25, 1], "metallicFactor": 0, "roughnessFactor": 0.7}},
    {"name": "yellow-fin", "doubleSided": True, "pbrMetallicRoughness": {"baseColorFactor": [0.98, 0.82, 0.12, 1], "metallicFactor": 0, "roughnessFactor": 0.8}},
    {"name": "back", "pbrMetallicRoughness": {"baseColorFactor": [0.24, 0.32, 0.15, 1], "metallicFactor": 0.1, "roughnessFactor": 0.5}},
    {"name": "flank", "pbrMetallicRoughness": {"baseColorFactor": [0.78, 0.64, 0.58, 1], "metallicFactor": 0.3, "roughnessFactor": 0.4}},
    {"name": "belly", "pbrMetallicRoughness": {"baseColorFactor": [0.92, 0.9, 0.82, 1], "metallicFactor": 0.1, "roughnessFactor": 0.5}},
    {"name": "spot", "pbrMetallicRoughness": {"baseColorFactor": [0.07, 0.06, 0.04, 1], "metallicFactor": 0, "roughnessFactor": 0.6}},
    {"name": "red-spot", "pbrMetallicRoughness": {"baseColorFactor": [0.75, 0.12, 0.08, 1], "metallicFactor": 0, "roughnessFactor": 0.6}},
    {"name": "fin", "doubleSided": True, "pbrMetallicRoughness": {"baseColorFactor": [0.5, 0.42, 0.24, 1], "metallicFactor": 0, "roughnessFactor": 0.8}},
]

NODE_NAMES = ["Body", "Tail", "PecL", "PecR"]


# ---- clips ----------------------------------------------------------------------------------------------

def quat_y(deg):
    h = math.radians(deg) / 2
    return (0.0, math.sin(h), 0.0, math.cos(h))


def quat_z(deg):
    h = math.radians(deg) / 2
    return (0.0, 0.0, math.sin(h), math.cos(h))


def clip_keys(spec):
    """One cycle of a sway: the body yaws a little, the tail a lot and a quarter cycle behind, the pectoral fins
    paddle about the body's axis. 25 keys, the last equal to the first, so the clip loops."""
    period = spec["period"]
    times = [period * i / 24 for i in range(25)]
    rot = {"Body": [], "Tail": [], "PecL": [], "PecR": []}
    for t in times:
        phase = 2 * math.pi * t / period
        rot["Body"].append(quat_y(spec["body"] * math.sin(phase)))
        rot["Tail"].append(quat_y(spec["tail"] * math.sin(phase - 1.3)))
        paddle = spec["pec"] * (0.5 + 0.5 * math.sin(phase))
        rot["PecL"].append(quat_z(-paddle))
        rot["PecR"].append(quat_z(paddle))
    return times, rot


# ---- glTF -----------------------------------------------------------------------------------------------

def write(species, path):
    blob = bytearray()
    buffer_views, accessors = [], []

    def view(data, target=None):
        while len(blob) % 4: blob.append(0)
        offset = len(blob)
        blob.extend(data)
        buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data), **({"target": target} if target else {})})
        return len(buffer_views) - 1

    def accessor(values, kind, component=5126, target=None, bounds=False):
        width = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}[kind]
        fmt = {5126: "f", 5123: "H"}[component]
        flat_values = [v for value in values for v in (value if width > 1 else (value,))]
        data = struct.pack("<%d%s" % (len(flat_values), fmt), *flat_values)
        entry = {"bufferView": view(data, target), "componentType": component, "count": len(values), "type": kind}
        if bounds:
            entry["min"] = [min(v[i] for v in values) for i in range(width)] if width > 1 else [min(values)]
            entry["max"] = [max(v[i] for v in values) for i in range(width)] if width > 1 else [max(values)]
        accessors.append(entry)
        return len(accessors) - 1

    def mesh_primitive(prim):
        return {
            "attributes": {"POSITION": accessor(prim.positions, "VEC3", target=34962, bounds=True), "NORMAL": accessor(prim.normals, "VEC3", target=34962)},
            "indices": accessor([i for tri in prim.triangles for i in tri], "SCALAR", 5123, target=34963),
            "material": prim.material,
        }

    meshes = [{"name": name.lower(), "primitives": [mesh_primitive(p) for p in species["meshes"][name]]} for name in NODE_NAMES]

    def clip(name, spec):
        times, rotations = clip_keys(spec)
        t = accessor(times, "SCALAR", bounds=True)
        samplers, channels = [], []
        for node, node_name in enumerate(NODE_NAMES):
            samplers.append({"input": t, "output": accessor(rotations[node_name], "VEC4"), "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": "rotation"}})
        return {"name": name, "samplers": samplers, "channels": channels}

    animations = [clip("swim", species["swim"]), clip("idle", species["idle"])]
    gltf = {
        "asset": {"version": "2.0", "generator": "QRX.pack scripts/fish.py", "copyright": "CC0 1.0, made for QRX"},
        "scene": 0,
        "scenes": [{"name": species["name"].lower(), "nodes": [len(NODE_NAMES)]}],
        "nodes": [{"name": name, "mesh": i, "translation": list(species["positions"][name])} for i, name in enumerate(NODE_NAMES)]
                 + [{"name": species["name"], "children": list(range(len(NODE_NAMES)))}],
        "meshes": meshes,
        "materials": MATERIALS,
        "animations": animations,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(blob)}],
    }
    while len(blob) % 4: blob.append(0)
    gltf["buffers"][0]["byteLength"] = len(blob)
    json_chunk = json.dumps(gltf, separators=(",", ":")).encode()
    while len(json_chunk) % 4: json_chunk += b" "
    glb = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(json_chunk) + 8 + len(blob))
    glb += struct.pack("<II", len(json_chunk), 0x4E4F534A) + json_chunk
    glb += struct.pack("<II", len(blob), 0x004E4942) + bytes(blob)
    open(path, "wb").write(glb)
    vertices = sum(len(p.positions) for prims in species["meshes"].values() for p in prims)
    zs = [p[2] + species["positions"][name][2] for name, prims in species["meshes"].items() for prim in prims for p in prim.positions]
    print(f"{path.split('/')[-1]}: {len(glb)} bytes, {vertices} vertices, {max(zs) - min(zs):.3f} m nose to tail")


write(reef((ORANGE, WHITE, BLACK, ORANGE_FIN)), f"{out}/models/fish.glb")
write(reef((BLUE, NAVY, NAVY, YELLOW_FIN)), f"{out}/models/fish-blue.glb")
write(trout(), f"{out}/models/trout.glb")
