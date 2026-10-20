"""The aquarium's tank: a glass box 1.2 m wide, 0.6 m high and 0.5 m deep with a sand floor, pebbles and two
plants, as a glTF binary written by hand (standard library only).

The tank is a static actor in scene-aquarium.json. Its model box is the tank, so a TV's framing camera (which
frames the actors' boxes) keeps the whole tank in view instead of following the fish. The water is the glass
box tinted and translucent up to the water line, with a clear rim above it. The plants are two nodes with an
"idle" clip that sways them. Metres, +Y up, the origin at the middle of the base: the fish swim in
y 0.08 to 0.52, x +-0.52, z +-0.18 (the scene's bounds).

    python3 scripts/tank.py <out>    ->   <out>/models/tank.glb
"""
import json, math, random, struct, sys

out = sys.argv[1]
W, H, D = 1.2, 0.6, 0.5     # outer size
WATER = 0.56                # the water line
SAND = 0.03                 # sand depth


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


def quad(a, b, c, d, normal):
    """One face a-b-c-d (counter-clockwise seen from the normal's side)."""
    return [a, b, c, d], [normal] * 4, [(0, 1, 2), (0, 2, 3)]


def box(x0, y0, z0, x1, y1, z1, faces="xyz"):
    """A box's outside faces; `faces` names the axes whose faces are made (omit y for an open top and bottom)."""
    parts = []
    if "y" in faces:
        parts.append(quad((x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0), (0, 1, 0)))
        parts.append(quad((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), (0, -1, 0)))
    if "z" in faces:
        parts.append(quad((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (0, 0, 1)))
        parts.append(quad((x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (0, 0, -1)))
    if "x" in faces:
        parts.append(quad((x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (1, 0, 0)))
        parts.append(quad((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0), (-1, 0, 0)))
    return parts


def ellipsoid(cx, cy, cz, rx, ry, rz, segments=10, rings=6):
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


def leaf(angle, length, width, lean):
    """A tapered blade standing at the plant's origin, turned `angle` degrees about y and leaning out by `lean`."""
    a = math.radians(angle)
    out_dir = (math.sin(a), 0.0, math.cos(a))
    side = (math.cos(a), 0.0, -math.sin(a))
    pts = []
    for h, w in ((0, 0.4), (0.3, 1.0), (0.65, 0.8), (1.0, 0.0)):
        y = h * length
        o = lean * h * h * length
        for s in (-1, 1):
            pts.append((out_dir[0] * o + side[0] * w * width * s / 2, y, out_dir[2] * o + side[2] * w * width * s / 2))
    positions = pts[:-1]  # the tip is one point
    normal = (-out_dir[0] * 0.3 + side[0] * 0.0, 0.3, -out_dir[2] * 0.3)
    l = math.sqrt(sum(c * c for c in normal)) or 1
    normal = tuple(c / l for c in normal)
    triangles = [(0, 1, 3), (0, 3, 2), (2, 3, 5), (2, 5, 4), (4, 5, 6)]
    return positions, [normal] * len(positions), triangles


GLASS, WATER_GLASS, SAND_MAT, PEBBLE, PEBBLE2, PLANT = range(6)
MATERIALS = [
    {"name": "glass", "doubleSided": True, "alphaMode": "BLEND", "pbrMetallicRoughness": {"baseColorFactor": [0.85, 0.92, 0.96, 0.12], "metallicFactor": 0, "roughnessFactor": 0.05}},
    {"name": "water", "doubleSided": True, "alphaMode": "BLEND", "pbrMetallicRoughness": {"baseColorFactor": [0.45, 0.72, 0.88, 0.28], "metallicFactor": 0, "roughnessFactor": 0.1}},
    {"name": "sand", "pbrMetallicRoughness": {"baseColorFactor": [0.86, 0.78, 0.6, 1], "metallicFactor": 0, "roughnessFactor": 0.95}},
    {"name": "pebble", "pbrMetallicRoughness": {"baseColorFactor": [0.45, 0.42, 0.4, 1], "metallicFactor": 0, "roughnessFactor": 0.7}},
    {"name": "pebble-brown", "pbrMetallicRoughness": {"baseColorFactor": [0.55, 0.4, 0.3, 1], "metallicFactor": 0, "roughnessFactor": 0.7}},
    {"name": "plant", "doubleSided": True, "pbrMetallicRoughness": {"baseColorFactor": [0.2, 0.55, 0.22, 1], "metallicFactor": 0, "roughnessFactor": 0.8}},
]

hx, hz = W / 2, D / 2
# Water: the sides and the bottom up to the water line, and the surface.
water = Primitive(WATER_GLASS)
for part in box(-hx, 0, -hz, hx, WATER, hz, "xz"): water.add(part)
water.add(quad((-hx, WATER, hz), (hx, WATER, hz), (hx, WATER, -hz), (-hx, WATER, -hz), (0, 1, 0)))
# Glass: the clear rim above the water line.
glass = Primitive(GLASS)
for part in box(-hx, WATER, -hz, hx, H, hz, "xz"): glass.add(part)
# Sand: an opaque slab, a little inside the glass.
sand = Primitive(SAND_MAT)
for part in box(-hx + 0.005, 0, -hz + 0.005, hx - 0.005, SAND, hz - 0.005): sand.add(part)
# Pebbles on the sand.
rng = random.Random(3)
pebbles = {PEBBLE: Primitive(PEBBLE), PEBBLE2: Primitive(PEBBLE2)}
for _ in range(14):
    r = rng.uniform(0.012, 0.03)
    x, z = rng.uniform(-hx + 0.08, hx - 0.08), rng.uniform(-hz + 0.06, hz - 0.06)
    pebbles[rng.choice([PEBBLE, PEBBLE2])].add(ellipsoid(x, SAND, z, r, r * 0.55, r * rng.uniform(0.7, 1.2)))
# Plants: two tufts, each its own node so a clip can sway it.
plants = {}
for name, x, z, leaves, height in (("PlantL", -0.42, -0.1, 7, 0.34), ("PlantR", 0.38, 0.05, 6, 0.26)):
    p = Primitive(PLANT)
    for i in range(leaves):
        p.add(leaf(360 * i / leaves + rng.uniform(-15, 15), height * rng.uniform(0.7, 1.0), 0.035, rng.uniform(0.15, 0.4)))
    plants[name] = (p, (x, SAND, z))


# ---- clip: the plants sway ------------------------------------------------------------------------------

def quat_z(deg):
    h = math.radians(deg) / 2
    return (0.0, 0.0, math.sin(h), math.cos(h))


def quat_x(deg):
    h = math.radians(deg) / 2
    return (math.sin(h), 0.0, 0.0, math.cos(h))


times = [i / 6 for i in range(25)]  # 4 s
sway = {"PlantL": [quat_z(3 * math.sin(2 * math.pi * t / 4)) for t in times],
        "PlantR": [quat_x(2.5 * math.sin(2 * math.pi * t / 4 + 1)) for t in times]}


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


# The opaque parts first, the translucent water and glass last, so a renderer that keeps file order draws them over the rest.
NODE_NAMES = ["Sand", "PlantL", "PlantR", "Water"]
meshes = [
    {"name": "sand", "primitives": [mesh_primitive(sand)] + [mesh_primitive(p) for p in pebbles.values()]},
    {"name": "plant-left", "primitives": [mesh_primitive(plants["PlantL"][0])]},
    {"name": "plant-right", "primitives": [mesh_primitive(plants["PlantR"][0])]},
    {"name": "water", "primitives": [mesh_primitive(water), mesh_primitive(glass)]},
]
positions = {"Sand": (0, 0, 0), "PlantL": plants["PlantL"][1], "PlantR": plants["PlantR"][1], "Water": (0, 0, 0)}
t = accessor(times, "SCALAR", bounds=True)
samplers, channels = [], []
for node, name in enumerate(NODE_NAMES):
    if name not in sway: continue
    samplers.append({"input": t, "output": accessor(sway[name], "VEC4"), "interpolation": "LINEAR"})
    channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": "rotation"}})

gltf = {
    "asset": {"version": "2.0", "generator": "QRX.pack scripts/tank.py", "copyright": "CC0 1.0, made for QRX"},
    "scene": 0,
    "scenes": [{"name": "tank", "nodes": [len(NODE_NAMES)]}],
    "nodes": [{"name": name, "mesh": i, "translation": list(positions[name])} for i, name in enumerate(NODE_NAMES)]
             + [{"name": "Tank", "children": list(range(len(NODE_NAMES)))}],
    "meshes": meshes,
    "materials": MATERIALS,
    "animations": [{"name": "idle", "samplers": samplers, "channels": channels}],
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
open(f"{out}/models/tank.glb", "wb").write(glb)
vertices = len(sand.positions) + len(water.positions) + len(glass.positions) + sum(len(p.positions) for p in pebbles.values()) + sum(len(p.positions) for p, _ in plants.values())
print(f"tank.glb: {len(glb)} bytes, {vertices} vertices, {W} x {H} x {D} m")
