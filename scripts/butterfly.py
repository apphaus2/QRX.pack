"""Flit the butterfly's body: a large butterfly as a glTF binary, written by hand (standard library only).

A dark body with a head, eyes and clubbed antennae, and two flat wings hinged at the body, each a
forewing in orange and a hindwing in amber with an eyespot. Two clips turn the wing nodes about the
body's axis: "fly", six fast flaps a second with a little bob, and "idle", a slow pump with the wings
held up, for resting. Metres, +Y up, the head along +Z; the wingspan is about 15 cm.

    python3 scripts/butterfly.py <out>    ->   <out>/models/butterfly.glb
"""
import json, math, struct, sys

out = sys.argv[1]


# ---- geometry -------------------------------------------------------------------------------------------

def ellipsoid(cx, cy, cz, rx, ry, rz, segments=12, rings=8):
    """A UV sphere stretched to three radii: positions, normals and triangles."""
    positions, normals, triangles = [], [], []
    for i in range(rings + 1):
        phi = math.pi * i / rings
        for j in range(segments + 1):
            theta = 2 * math.pi * j / segments
            nx, ny, nz = math.sin(phi) * math.cos(theta), math.cos(phi), math.sin(phi) * math.sin(theta)
            positions.append((cx + rx * nx, cy + ry * ny, cz + rz * nz))
            n = (nx / rx, ny / ry, nz / rz)
            length = math.sqrt(sum(c * c for c in n))
            normals.append(tuple(c / length for c in n))
    for i in range(rings):
        for j in range(segments):
            a = i * (segments + 1) + j
            b = a + segments + 1
            if i > 0: triangles.append((a, b, a + 1))
            if i < rings - 1: triangles.append((a + 1, b, b + 1))
    return positions, normals, triangles


def sphere(cx, cy, cz, r, segments=10, rings=6):
    return ellipsoid(cx, cy, cz, r, r, r, segments, rings)


def tube(p0, p1, r0, r1, segments=6):
    """A tapered tube from p0 (radius r0) to p1 (radius r1), open ended."""
    ax = tuple(b - a for a, b in zip(p0, p1))
    length = math.sqrt(sum(c * c for c in ax))
    ax = tuple(c / length for c in ax)
    helper = (0.0, 1.0, 0.0) if abs(ax[1]) < 0.9 else (1.0, 0.0, 0.0)
    u = (ax[1] * helper[2] - ax[2] * helper[1], ax[2] * helper[0] - ax[0] * helper[2], ax[0] * helper[1] - ax[1] * helper[0])
    ul = math.sqrt(sum(c * c for c in u))
    u = tuple(c / ul for c in u)
    v = (ax[1] * u[2] - ax[2] * u[1], ax[2] * u[0] - ax[0] * u[2], ax[0] * u[1] - ax[1] * u[0])
    positions, normals, triangles = [], [], []
    for (p, r) in ((p0, r0), (p1, r1)):
        for j in range(segments + 1):
            theta = 2 * math.pi * j / segments
            n = tuple(u[k] * math.cos(theta) + v[k] * math.sin(theta) for k in range(3))
            positions.append(tuple(p[k] + r * n[k] for k in range(3)))
            normals.append(n)
    for j in range(segments):
        a, b = j, j + segments + 1
        triangles.append((a, b, a + 1))
        triangles.append((a + 1, b, b + 1))
    return positions, normals, triangles


def flat(polygon, y, up=True):
    """A flat polygon in the XZ plane at height y, fanned from its first point, facing +Y (or -Y)."""
    positions = [(x, y, z) for x, z in polygon]
    normal = (0.0, 1.0 if up else -1.0, 0.0)
    normals = [normal] * len(positions)
    triangles = []
    for i in range(1, len(polygon) - 1):
        a, b, c = positions[0], positions[i], positions[i + 1]
        # Wind so the face normal points the way the vertex normals do.
        cross_y = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
        triangles.append((0, i, i + 1) if (cross_y > 0) == up else (0, i + 1, i))
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


BODY, EYE, FORE, HIND, SPOT = range(5)
MATERIALS = [
    {"name": "body", "pbrMetallicRoughness": {"baseColorFactor": [0.13, 0.09, 0.06, 1], "metallicFactor": 0, "roughnessFactor": 0.9}},
    {"name": "eye", "pbrMetallicRoughness": {"baseColorFactor": [0.02, 0.02, 0.02, 1], "metallicFactor": 0, "roughnessFactor": 0.3}},
    {"name": "wing-fore", "doubleSided": True, "pbrMetallicRoughness": {"baseColorFactor": [0.93, 0.44, 0.08, 1], "metallicFactor": 0, "roughnessFactor": 0.8}},
    {"name": "wing-hind", "doubleSided": True, "pbrMetallicRoughness": {"baseColorFactor": [0.98, 0.70, 0.14, 1], "metallicFactor": 0, "roughnessFactor": 0.8}},
    {"name": "spot", "doubleSided": True, "pbrMetallicRoughness": {"baseColorFactor": [0.16, 0.10, 0.22, 1], "metallicFactor": 0, "roughnessFactor": 0.8}},
]

# The body: an ellipsoid along z, in its own node so the clips can bob it.
body = Primitive(BODY)
body.add(ellipsoid(0, 0, 0, 0.006, 0.006, 0.026))

# The head: a ball with two eyes and two clubbed antennae, a node of its own (the "mouth" socket).
head = [Primitive(BODY), Primitive(EYE)]
head[0].add(sphere(0, 0.001, 0.030, 0.0075))
for side in (-1, 1):
    head[1].add(sphere(side * 0.005, 0.004, 0.034, 0.0025, segments=8, rings=5))
    tip = (side * 0.016, 0.024, 0.052)
    head[0].add(tube((side * 0.003, 0.006, 0.034), tip, 0.0009, 0.0006))
    head[0].add(sphere(*tip, 0.0016, segments=8, rings=5))

# A wing: forewing, hindwing and an eyespot on each face, in the hinge node's space (x outward).
HINGE = 0.004
WING = 0.8
FORE_SHAPE = [(0.0, 0.010), (0.022, 0.030), (0.048, 0.046), (0.072, 0.048), (0.086, 0.036), (0.082, 0.018), (0.066, 0.006), (0.040, 0.001), (0.016, 0.000), (0.0, 0.002)]
HIND_SHAPE = [(0.0, -0.001), (0.018, -0.003), (0.040, -0.006), (0.056, -0.016), (0.062, -0.032), (0.052, -0.050), (0.034, -0.058), (0.016, -0.050), (0.004, -0.030)]
SPOT_AT, SPOT_R = (0.058, 0.027), 0.008


def wing(side):
    """The right wing (side 1, along +x) or the left (side -1)."""
    def shape(points, scale=WING):
        return [(side * x * scale, z * scale) for x, z in points]
    spot = [(SPOT_AT[0] + SPOT_R * math.cos(2 * math.pi * k / 12), SPOT_AT[1] + SPOT_R * math.sin(2 * math.pi * k / 12)) for k in range(12)]
    fore, hind, spots = Primitive(FORE), Primitive(HIND), Primitive(SPOT)
    fore.add(flat(shape(FORE_SHAPE), 0.0))
    hind.add(flat(shape(HIND_SHAPE), 0.0))
    spots.add(flat(shape(spot), 0.0004, up=True))
    spots.add(flat(shape(spot), -0.0004, up=False))
    return [fore, hind, spots]


wings = {"WingR": wing(1), "WingL": wing(-1)}


# ---- animation ------------------------------------------------------------------------------------------

def quat_z(degrees):
    h = math.radians(degrees) / 2
    return (0.0, 0.0, math.sin(h), math.cos(h))


# A wing angle is the right wing's rotation about the body's axis: positive lifts its tip, so the left
# wing takes the opposite sign. 0 is flat out, 80 is nearly closed over the back.
def flap(times, angle, bob=None):
    """Rotation keys for both wings and, with `bob`, a translation for every node, at `times`."""
    rot = {"WingR": [quat_z(angle(t)) for t in times], "WingL": [quat_z(-angle(t)) for t in times]}
    pos = None
    if bob:
        pos = {name: [(x, y + bob(t), z) for t in times] for name, (x, y, z) in NODE_POSITIONS.items()}
    return rot, pos


NODE_POSITIONS = {"Body": (0.0, 0.0, 0.0), "Head": (0.0, 0.0, 0.0), "WingR": (HINGE, 0.004, 0.0), "WingL": (-HINGE, 0.004, 0.0)}

# fly: six flaps in a second, from 15 degrees below flat to 70 above, with a bob at three a second
fly_t = [i / 24 for i in range(25)]
fly_rot, fly_pos = flap(fly_t, lambda t: 27.5 + 42.5 * math.cos(2 * math.pi * 6 * t), lambda t: 0.004 * math.sin(2 * math.pi * 3 * t))

# idle: the wings held up and pumped slowly, over 3 s
idle_t = [i / 8 for i in range(25)]
idle_rot, idle_pos = flap(idle_t, lambda t: 45 + 25 * math.cos(2 * math.pi * t / 3))


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


NODE_NAMES = ["Body", "Head", "WingR", "WingL"]
ROOT = len(NODE_NAMES)
meshes = [
    {"name": "body", "primitives": [mesh_primitive(body)]},
    {"name": "head", "primitives": [mesh_primitive(p) for p in head]},
    {"name": "wing-right", "primitives": [mesh_primitive(p) for p in wings["WingR"]]},
    {"name": "wing-left", "primitives": [mesh_primitive(p) for p in wings["WingL"]]},
]


def clip(name, times, rotations, translations=None):
    samplers, channels = [], []
    t = accessor(times, "SCALAR", bounds=True)
    for node, node_name in enumerate(NODE_NAMES):
        for path, values, kind in (("rotation", rotations.get(node_name) if rotations else None, "VEC4"), ("translation", translations.get(node_name) if translations else None, "VEC3")):
            if values is None: continue
            samplers.append({"input": t, "output": accessor(values, kind), "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": path}})
    return {"name": name, "samplers": samplers, "channels": channels}


animations = [clip("fly", fly_t, fly_rot, fly_pos), clip("idle", idle_t, idle_rot)]

gltf = {
    "asset": {"version": "2.0", "generator": "QRX.pack scripts/butterfly.py", "copyright": "CC0 1.0, made for QRX"},
    "scene": 0,
    "scenes": [{"name": "butterfly", "nodes": [ROOT]}],
    "nodes": [{"name": name, "mesh": i, "translation": list(NODE_POSITIONS[name])} for i, name in enumerate(NODE_NAMES)]
             + [{"name": "Butterfly", "children": list(range(len(NODE_NAMES)))}],
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
open(f"{out}/models/butterfly.glb", "wb").write(glb)
vertices = len(body.positions) + sum(len(p.positions) for p in head) + sum(len(p.positions) for w in wings.values() for p in w)
print(f"butterfly.glb: {len(glb)} bytes, {vertices} vertices")
