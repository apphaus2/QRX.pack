"""The house pet's bowl and bed as glTF binaries, written by hand (standard library only).

The bowl is a shallow lathed dish, 14 cm across and 4 cm high, in a blue glaze with a tan rim band, with a mound of
kibble inside. The bed is an oval cushion, 50 by 38 cm and 9 cm high: a rolled rim in a warm red around a sunken
quilted centre. Metres, +Y up, the origin on the floor under each; nothing animates. The scene puts them where a pet
eats and sleeps, so the pet (a ground actor) walks up to them and stops short.

    python3 scripts/pet.py <out>    ->   <out>/models/bowl.glb and <out>/models/bed.glb
"""
import json, math, random, struct, sys

out = sys.argv[1]
random.seed(7)


# ---- geometry -------------------------------------------------------------------------------------------

def lathe(profile, segments=28, sx=1.0, sz=1.0):
    """Spins a profile of (radius, height) points around +Y into positions, normals and triangles.

    `sx` and `sz` stretch the result into an oval. Normals come from the profile's slope.
    """
    positions, normals, triangles = [], [], []
    rings = len(profile)
    for i, (r, y) in enumerate(profile):
        # Slope of the profile at this ring, for the normal.
        r0, y0 = profile[max(i - 1, 0)]
        r1, y1 = profile[min(i + 1, rings - 1)]
        dr, dy = r1 - r0, y1 - y0
        length = math.hypot(dr, dy) or 1.0
        nr, ny = dy / length, -dr / length
        for j in range(segments + 1):
            theta = 2 * math.pi * j / segments
            c, s = math.cos(theta), math.sin(theta)
            positions.append((r * c * sx, y, r * s * sz))
            n = (nr * c / sx, ny, nr * s / sz)
            nl = math.sqrt(sum(v * v for v in n)) or 1.0
            normals.append(tuple(v / nl for v in n))
    for i in range(rings - 1):
        for j in range(segments):
            a = i * (segments + 1) + j
            b = a + segments + 1
            triangles.append((a, a + 1, b))
            triangles.append((a + 1, b + 1, b))
    return positions, normals, triangles


def sphere(cx, cy, cz, r, segments=10, rings=6, squash=1.0):
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


class Primitive:
    def __init__(self, material):
        self.material, self.positions, self.normals, self.triangles = material, [], [], []

    def add(self, part):
        positions, normals, triangles = part
        base = len(self.positions)
        self.positions += positions
        self.normals += normals
        self.triangles += [(a + base, b + base, c + base) for a, b, c in triangles]


def material(name, rgb, roughness=0.8):
    return {"name": name, "doubleSided": True, "pbrMetallicRoughness": {"baseColorFactor": [*rgb, 1], "metallicFactor": 0, "roughnessFactor": roughness}}


# ---- glTF -----------------------------------------------------------------------------------------------

class Writer:
    def __init__(self, generator):
        self.generator = generator
        self.blob = bytearray()
        self.buffer_views, self.accessors = [], []

    def view(self, data, target=None):
        while len(self.blob) % 4: self.blob.append(0)
        offset = len(self.blob)
        self.blob.extend(data)
        self.buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data), **({"target": target} if target else {})})
        return len(self.buffer_views) - 1

    def accessor(self, values, kind, component=5126, target=None, bounds=False):
        width = {"SCALAR": 1, "VEC3": 3}[kind]
        fmt = {5126: "f", 5123: "H"}[component]
        flat = [v for value in values for v in (value if width > 1 else (value,))]
        data = struct.pack("<%d%s" % (len(flat), fmt), *flat)
        entry = {"bufferView": self.view(data, target), "componentType": component, "count": len(values), "type": kind}
        if bounds:
            entry["min"] = [min(v[i] for v in values) for i in range(width)]
            entry["max"] = [max(v[i] for v in values) for i in range(width)]
        self.accessors.append(entry)
        return len(self.accessors) - 1

    def primitive(self, prim):
        return {
            "attributes": {"POSITION": self.accessor(prim.positions, "VEC3", target=34962, bounds=True), "NORMAL": self.accessor(prim.normals, "VEC3", target=34962)},
            "indices": self.accessor([i for tri in prim.triangles for i in tri], "SCALAR", 5123, target=34963),
            "material": prim.material,
        }

    def write(self, path, name, primitives, materials):
        gltf = {
            "asset": {"version": "2.0", "generator": self.generator, "copyright": "CC0 1.0, made for QRX"},
            "scene": 0,
            "scenes": [{"name": name, "nodes": [0]}],
            "nodes": [{"name": name.capitalize(), "mesh": 0}],
            "meshes": [{"name": name, "primitives": [self.primitive(p) for p in primitives]}],
            "materials": materials,
            "accessors": self.accessors,
            "bufferViews": self.buffer_views,
            "buffers": [{"byteLength": len(self.blob)}],
        }
        blob = self.blob
        while len(blob) % 4: blob.append(0)
        json_chunk = json.dumps(gltf, separators=(",", ":")).encode()
        while len(json_chunk) % 4: json_chunk += b" "
        glb = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(json_chunk) + 8 + len(blob))
        glb += struct.pack("<II", len(json_chunk), 0x4E4F534A) + json_chunk
        glb += struct.pack("<II", len(blob), 0x004E4942) + bytes(blob)
        open(path, "wb").write(glb)
        print(f"{path.split('/')[-1]}: {len(glb)} bytes, {sum(len(p.positions) for p in primitives)} vertices")


# ---- the bowl -------------------------------------------------------------------------------------------

GLAZE, RIM, KIBBLE = range(3)
bowl_materials = [
    material("glaze", (0.18, 0.40, 0.62), 0.35),
    material("rim", (0.80, 0.66, 0.46), 0.6),
    material("kibble", (0.52, 0.33, 0.16), 0.9),
]

# Outside up to the lip, a flat rim band, then the inside down to the food line. (radius, height), metres.
outside = [(0.040, 0.000), (0.058, 0.004), (0.066, 0.016), (0.069, 0.028), (0.070, 0.038)]
rim = [(0.070, 0.040), (0.062, 0.040)]
inside = [(0.062, 0.040), (0.060, 0.034), (0.052, 0.022), (0.040, 0.014), (0.020, 0.011), (0.000, 0.010)]
bowl = [Primitive(GLAZE), Primitive(RIM), Primitive(KIBBLE)]
bowl[GLAZE].add(lathe(outside))
bowl[RIM].add(lathe(rim))
bowl[GLAZE].add(lathe(inside))
# A mound of kibble: pebbles over the food line.
for k in range(26):
    a = random.uniform(0, 2 * math.pi)
    d = random.uniform(0, 0.040) ** 0.5 * 0.040 ** 0.5
    bowl[KIBBLE].add(sphere(d * math.cos(a), 0.013 + random.uniform(0, 0.006), d * math.sin(a), random.uniform(0.006, 0.009), squash=0.7))
Writer("QRX.pack scripts/pet.py").write(f"{out}/models/bowl.glb", "bowl", bowl, bowl_materials)


# ---- the bed --------------------------------------------------------------------------------------------

CUSHION, CENTRE, STITCH = range(3)
bed_materials = [
    material("cushion", (0.62, 0.20, 0.17), 0.95),
    material("centre", (0.78, 0.62, 0.48), 1.0),
    material("stitch", (0.45, 0.14, 0.12), 1.0),
]

# The rim is a rolled profile from the floor up and over into the sunken centre; the oval is 50 x 38 cm.
roll = [(0.235, 0.000), (0.248, 0.025), (0.250, 0.055), (0.240, 0.080), (0.218, 0.090), (0.195, 0.082), (0.180, 0.060), (0.175, 0.040)]
centre = [(0.175, 0.040), (0.120, 0.036), (0.060, 0.034), (0.000, 0.033)]
bed = [Primitive(CUSHION), Primitive(CENTRE), Primitive(STITCH)]
bed[CUSHION].add(lathe(roll, segments=40, sx=1.0, sz=0.76))
bed[CENTRE].add(lathe(centre, segments=40, sx=1.0, sz=0.76))
# Quilting: a ring of small tucks in the centre.
for k in range(8):
    a = 2 * math.pi * k / 8
    bed[STITCH].add(sphere(0.10 * math.cos(a), 0.034, 0.076 * math.sin(a), 0.008, squash=0.4))
Writer("QRX.pack scripts/pet.py").write(f"{out}/models/bed.glb", "bed", bed, bed_materials)
