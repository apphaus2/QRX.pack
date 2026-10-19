"""The singing bush's body: a small round desert shrub as a glTF binary, written by hand (standard library only).

A brown stem and a crown of leafy spheres in three greens, with two animation clips on the crown:
"sway", a slow lean from side to side for idling, and "shake", a fast quiver with a bounce and a
little hop for singing. Metres; the bush is about 0.4 m tall.

    python3 scripts/bush.py <out>    ->   <out>/models/bush.glb
"""
import json, math, random, struct, sys

out = sys.argv[1]
random.seed(3)


# ---- geometry -------------------------------------------------------------------------------------------

def sphere(cx, cy, cz, r, segments=14, rings=9, squash=1.0):
    """A UV sphere's positions, normals and triangles, squashed vertically by `squash`."""
    positions, normals, triangles = [], [], []
    for i in range(rings + 1):
        phi = math.pi * i / rings
        for j in range(segments + 1):
            theta = 2 * math.pi * j / segments
            nx, ny, nz = math.sin(phi) * math.cos(theta), math.cos(phi), math.sin(phi) * math.sin(theta)
            positions.append((cx + r * nx, cy + r * ny * squash, cz + r * nz))
            n = (nx, ny / squash, nz)
            length = math.sqrt(sum(c * c for c in n))
            normals.append(tuple(c / length for c in n))
    for i in range(rings):
        for j in range(segments):
            a = i * (segments + 1) + j
            b = a + segments + 1
            if i > 0: triangles.append((a, b, a + 1))
            if i < rings - 1: triangles.append((a + 1, b, b + 1))
    return positions, normals, triangles


def cylinder(r0, r1, y0, y1, segments=10):
    """A tapered tube from y0 (radius r0) to y1 (radius r1), open ended."""
    positions, normals, triangles = [], [], []
    for (y, r) in ((y0, r0), (y1, r1)):
        for j in range(segments + 1):
            theta = 2 * math.pi * j / segments
            positions.append((r * math.cos(theta), y, r * math.sin(theta)))
            normals.append((math.cos(theta), 0.0, math.sin(theta)))
    for j in range(segments):
        a, b = j, j + segments + 1
        triangles.append((a, b, a + 1))
        triangles.append((a + 1, b, b + 1))
    return positions, normals, triangles


class Primitive:
    def __init__(self, material):
        self.material, self.positions, self.normals, self.triangles = material, [], [], []

    def add(self, part):
        positions, normals, triangles = part
        base = len(self.positions)
        self.positions += positions
        self.normals += normals
        self.triangles += [(a + base, b + base, c + base) for a, b, c in triangles]


DARK, MID, LIGHT, STEM = range(4)
MATERIALS = [
    {"name": "leaf-dark", "pbrMetallicRoughness": {"baseColorFactor": [0.20, 0.42, 0.16, 1], "metallicFactor": 0, "roughnessFactor": 1}},
    {"name": "leaf", "pbrMetallicRoughness": {"baseColorFactor": [0.32, 0.56, 0.21, 1], "metallicFactor": 0, "roughnessFactor": 1}},
    {"name": "leaf-light", "pbrMetallicRoughness": {"baseColorFactor": [0.50, 0.70, 0.27, 1], "metallicFactor": 0, "roughnessFactor": 1}},
    {"name": "stem", "pbrMetallicRoughness": {"baseColorFactor": [0.36, 0.23, 0.11, 1], "metallicFactor": 0, "roughnessFactor": 1}},
]

crown = [Primitive(DARK), Primitive(MID), Primitive(LIGHT)]
# The crown: a big squashed sphere, a ring of leafy lumps around it, a few on top, and small bright tips.
crown[DARK].add(sphere(0, 0.24, 0, 0.17, squash=0.85))
for k in range(8):
    a = 2 * math.pi * k / 8 + random.uniform(-0.2, 0.2)
    d = random.uniform(0.11, 0.15)
    crown[MID if k % 2 else DARK].add(sphere(d * math.cos(a), 0.20 + random.uniform(-0.03, 0.04), d * math.sin(a), random.uniform(0.085, 0.11)))
for k in range(5):
    a = 2 * math.pi * k / 5 + 0.4
    d = random.uniform(0.05, 0.09)
    crown[MID].add(sphere(d * math.cos(a), 0.33 + random.uniform(-0.02, 0.02), d * math.sin(a), random.uniform(0.07, 0.09)))
for k in range(12):
    a = random.uniform(0, 2 * math.pi)
    d = random.uniform(0.08, 0.19)
    y = 0.24 + random.uniform(-0.08, 0.14)
    crown[LIGHT].add(sphere(d * math.cos(a), y, d * math.sin(a), random.uniform(0.03, 0.045)))

stem = Primitive(STEM)
stem.add(cylinder(0.035, 0.022, 0.0, 0.17))
stem.add(sphere(0, 0.0, 0, 0.035, segments=10, rings=5, squash=0.3))   # a flare where it meets the ground


# ---- animation ------------------------------------------------------------------------------------------

def quat_z(degrees):
    h = math.radians(degrees) / 2
    return (0.0, 0.0, math.sin(h), math.cos(h))


def quat_xz(dx, dz):
    """Small lean: x then z, in degrees."""
    hx, hz = math.radians(dx) / 2, math.radians(dz) / 2
    ax, bx = math.cos(hx), math.sin(hx)
    az, bz = math.cos(hz), math.sin(hz)
    # (ax + bx i) * (az + bz k) = ax az + ax bz k + bx az i - bx bz j
    return (bx * az, -bx * bz, ax * bz, ax * az)


# sway: a slow lean side to side, with a breath, over 4 s
sway_t = [0, 1, 2, 3, 4]
sway_rot = [quat_z(0), quat_z(4), quat_z(0), quat_z(-4), quat_z(0)]
sway_scale = [(1, 1, 1), (1.01, 0.99, 1.01), (1, 1, 1), (1.01, 0.99, 1.01), (1, 1, 1)]

# shake: a quiver at 8 Hz with a bounce and a hop, over 1 s
shake_t, shake_rot, shake_scale, shake_pos = [], [], [], []
steps = 16
for i in range(steps + 1):
    t = i / steps
    shake_t.append(t)
    side = 7 if i % 2 else -7
    if i in (0, steps): side = 0
    shake_rot.append(quat_xz(3 * math.sin(2 * math.pi * t * 2), side))
    bounce = 1 + 0.08 * abs(math.sin(math.pi * t * 2))
    shake_scale.append((1 / math.sqrt(bounce), bounce, 1 / math.sqrt(bounce)))
    hop = 0.04 * math.sin(math.pi * t) ** 2 if 0.25 <= t <= 0.75 else 0.0
    shake_pos.append((0.0, hop, 0.0))


# ---- glTF -----------------------------------------------------------------------------------------------

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
    flat = [v for value in values for v in (value if width > 1 else (value,))]
    data = struct.pack("<%d%s" % (len(flat), fmt), *flat)
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


meshes = [
    {"name": "crown", "primitives": [mesh_primitive(p) for p in crown]},
    {"name": "stem", "primitives": [mesh_primitive(stem)]},
]


def clip(name, times, rotations=None, scales=None, translations=None):
    samplers, channels = [], []
    t = accessor(times, "SCALAR", bounds=True)
    for path, values, kind in (("rotation", rotations, "VEC4"), ("scale", scales, "VEC3"), ("translation", translations, "VEC3")):
        if values is None: continue
        samplers.append({"input": t, "output": accessor(values, kind), "interpolation": "LINEAR"})
        channels.append({"sampler": len(samplers) - 1, "target": {"node": CROWN, "path": path}})
    return {"name": name, "samplers": samplers, "channels": channels}


BUSH, CROWN, STEMNODE = 0, 1, 2
animations = [clip("sway", sway_t, sway_rot, sway_scale), clip("shake", shake_t, shake_rot, shake_scale, shake_pos)]

gltf = {
    "asset": {"version": "2.0", "generator": "QRX.pack scripts/bush.py", "copyright": "CC0 1.0, made for QRX"},
    "scene": 0,
    "scenes": [{"name": "bush", "nodes": [BUSH]}],
    "nodes": [
        {"name": "Bush", "children": [CROWN, STEMNODE]},
        {"name": "Crown", "mesh": 0},
        {"name": "Stem", "mesh": 1},
    ],
    "meshes": meshes,
    "materials": MATERIALS,
    "animations": animations,
    "accessors": accessors,
    "bufferViews": buffer_views,
    "buffers": [{"byteLength": len(blob)}],
}

while len(blob) % 4: blob.append(0)
json_chunk = json.dumps(gltf, separators=(",", ":")).encode()
while len(json_chunk) % 4: json_chunk += b" "
glb = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(json_chunk) + 8 + len(blob))
glb += struct.pack("<II", len(json_chunk), 0x4E4F534A) + json_chunk
glb += struct.pack("<II", len(blob), 0x004E4942) + bytes(blob)
open(f"{out}/models/bush.glb", "wb").write(glb)
print(f"bush.glb: {len(glb)} bytes, {sum(len(p.positions) for p in crown) + len(stem.positions)} vertices")
