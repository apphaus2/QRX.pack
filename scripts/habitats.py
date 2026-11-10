"""The TV's habitats: the tank, the terrarium and the aviary as glTF binaries, written by hand (standard
library only).

A habitat fills a TV screen: there is no box, no glass and no edge. The camera stands still where the front
glass would be (each scene's `camera` in habitats/*.json) and the floor and the backdrop run past every side of
its view. The backdrop is one quad behind everything with the habitat's gradient as an emissive texture over a
black base colour, so it draws the same under any lighting and the 3D view is opaque without the app's help.
Plants are their own nodes with an "idle" clip that sways them. Metres, +Y up, the camera on +Z looking to -Z.

    python3 scripts/habitats.py <out>    ->   <out>/models/habitat-tank.glb, habitat-terrarium.glb, habitat-aviary.glb

`Model` and the shape helpers are also what scripts/lizard.py builds with.
"""
import json, math, random, struct, sys, zlib


# ---- shapes: each returns (positions, normals, triangles) ------------------------------------------------

def norm(a):
    length = math.sqrt(sum(x * x for x in a)) or 1.0
    return tuple(x / length for x in a)


def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def sub(a, b): return tuple(x - y for x, y in zip(a, b))


class Primitive:
    def __init__(self, material):
        self.material, self.positions, self.normals, self.triangles, self.uvs = material, [], [], [], None

    def add(self, part):
        positions, normals, triangles = part
        base = len(self.positions)
        self.positions += positions
        self.normals += normals
        self.triangles += [(a + base, b + base, c + base) for a, b, c in triangles]
        return self


def ellipsoid(cx, cy, cz, rx, ry, rz, segments=10, rings=6):
    positions, normals, triangles = [], [], []
    for i in range(rings + 1):
        phi = math.pi * i / rings
        for j in range(segments + 1):
            theta = 2 * math.pi * j / segments
            nx, ny, nz = math.sin(phi) * math.cos(theta), math.cos(phi), math.sin(phi) * math.sin(theta)
            positions.append((cx + rx * nx, cy + ry * ny, cz + rz * nz))
            normals.append(norm((nx / rx, ny / ry, nz / rz)))
    for i in range(rings):
        for j in range(segments):
            a = i * (segments + 1) + j
            b = a + segments + 1
            if i > 0: triangles.append((a, b, a + 1))
            if i < rings - 1: triangles.append((a + 1, b, b + 1))
    return positions, normals, triangles


def blade(angle, length, width, lean, segments=4, at=(0.0, 0.0, 0.0), curl=0.0):
    """A tapered flat leaf standing at `at`, turned `angle` degrees about y, bending outwards by `lean` (the tip
    ends lean * length out) and sideways by `curl`. 2 * segments - 1 triangles; draw it double-sided."""
    a = math.radians(angle)
    out_dir, side = (math.sin(a), 0.0, math.cos(a)), (math.cos(a), 0.0, -math.sin(a))
    positions = []
    for i in range(segments + 1):
        h = i / segments
        w = width * (0.45 + 1.6 * h) * (1 - h) ** 0.7 if i < segments else 0.0
        o, c, y = lean * h * h * length, curl * math.sin(h * math.pi) * length, length * (h - 0.25 * lean * h * h)
        centre = (at[0] + out_dir[0] * o + side[0] * c, at[1] + y, at[2] + out_dir[2] * o + side[2] * c)
        if i == segments: positions.append(centre)
        else:
            for s in (-1, 1): positions.append((centre[0] + side[0] * w * s / 2, centre[1], centre[2] + side[2] * w * s / 2))
    normal = norm((-out_dir[0] * 0.5, 0.35, -out_dir[2] * 0.5))
    triangles = []
    for i in range(segments - 1):
        triangles += [(2 * i, 2 * i + 1, 2 * i + 3), (2 * i, 2 * i + 3, 2 * i + 2)]
    triangles.append((2 * segments - 2, 2 * segments - 1, 2 * segments))
    return positions, [normal] * len(positions), triangles


def heightfield(x0, x1, z0, z1, nx, nz, height):
    """A floor from (x0, z0) to (x1, z1), nx by nz cells, y = height(x, z), facing up."""
    positions, normals, triangles = [], [], []
    for j in range(nz + 1):
        for i in range(nx + 1):
            x, z = x0 + (x1 - x0) * i / nx, z0 + (z1 - z0) * j / nz
            positions.append((x, height(x, z), z))
            e = 0.01
            normals.append(norm((height(x - e, z) - height(x + e, z), 2 * e, height(x, z - e) - height(x, z + e))))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            b = a + nx + 1
            triangles += [(a, b, a + 1), (a + 1, b, b + 1)]
    return positions, normals, triangles


def tube(points, radii, sides=8, squash=1.0, caps=True):
    """A round tube through `points` with a radius at each; `squash` flattens it vertically."""
    positions, normals, triangles = [], [], []
    for k, p in enumerate(points):
        d = norm(sub(points[min(k + 1, len(points) - 1)], points[max(k - 1, 0)]))
        u = norm(cross(d, (0.0, 1.0, 0.0))) if abs(d[1]) < 0.95 else (1.0, 0.0, 0.0)
        v = norm(cross(u, d))
        for s in range(sides + 1):
            t = 2 * math.pi * s / sides
            n = tuple(u[i] * math.cos(t) + v[i] * math.sin(t) * squash for i in range(3))
            positions.append(tuple(p[i] + n[i] * radii[k] for i in range(3)))
            normals.append(norm(tuple(u[i] * math.cos(t) + v[i] * math.sin(t) for i in range(3))))
    for k in range(len(points) - 1):
        for s in range(sides):
            a = k * (sides + 1) + s
            b = a + sides + 1
            triangles += [(a, a + 1, b), (a + 1, b + 1, b)]
    if caps:
        for k, sign in ((0, -1), (len(points) - 1, 1)):
            if radii[k] <= 0: continue
            d = norm(sub(points[min(k + 1, len(points) - 1)], points[max(k - 1, 0)]))
            centre = len(positions)
            positions.append(points[k]); normals.append(tuple(c * sign for c in d))
            ring = k * (sides + 1)
            for s in range(sides):
                triangles.append((centre, ring + s + 1, ring + s) if sign > 0 else (centre, ring + s, ring + s + 1))
    return positions, normals, triangles


def smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def quat(axis, deg):
    h = math.radians(deg) / 2
    s = math.sin(h)
    return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(h))


X, Y, Z = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)


# ---- a PNG, for the backdrop's gradient -------------------------------------------------------------------

def hex_rgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def gradient_png(stops, height=256, width=4):
    """A top-to-bottom gradient through `stops` [(position 0..1, "#rrggbb")] as PNG bytes."""
    rows = []
    for y in range(height):
        t = y / (height - 1)
        i = max(k for k in range(len(stops) - 1) if stops[k][0] <= t)
        (t0, c0), (t1, c1) = (stops[i][0], hex_rgb(stops[i][1])), (stops[i + 1][0], hex_rgb(stops[i + 1][1]))
        s = (t - t0) / (t1 - t0)
        rows.append(b"\x00" + bytes(round(c0[k] + (c1[k] - c0[k]) * s) for k in range(3)) * width)

    def chunk(kind, data): return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))


# ---- glTF -------------------------------------------------------------------------------------------------

class Model:
    """Nodes of primitives, materials by colour, rotation clips, written as one .glb."""

    def __init__(self, name, generator):
        self.name, self.generator = name, generator
        self.blob, self.views, self.accessors = bytearray(), [], []
        self.materials, self.meshes, self.nodes, self.roots = [], [], [], []
        self.images, self.textures, self.animations = [], [], []
        self.triangles = 0

    def view(self, data, target=None):
        while len(self.blob) % 4: self.blob.append(0)
        self.views.append({"buffer": 0, "byteOffset": len(self.blob), "byteLength": len(data), **({"target": target} if target else {})})
        self.blob.extend(data)
        return len(self.views) - 1

    def accessor(self, values, kind, component=5126, target=None, bounds=False):
        width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[kind]
        flat = [v for value in values for v in (value if width > 1 else (value,))]
        data = struct.pack("<%d%s" % (len(flat), {5126: "f", 5123: "H"}[component]), *flat)
        entry = {"bufferView": self.view(data, target), "componentType": component, "count": len(values), "type": kind}
        if bounds:
            entry["min"] = [min(v[i] for v in values) for i in range(width)] if width > 1 else [min(values)]
            entry["max"] = [max(v[i] for v in values) for i in range(width)] if width > 1 else [max(values)]
        self.accessors.append(entry)
        return len(self.accessors) - 1

    def material(self, name, rgb, double=False, roughness=0.9):
        self.materials.append({"name": name, **({"doubleSided": True} if double else {}),
                               "pbrMetallicRoughness": {"baseColorFactor": [*rgb, 1], "metallicFactor": 0, "roughnessFactor": roughness}})
        return len(self.materials) - 1

    def backdrop(self, stops, width, y_top, y_horizon, z, y_bottom=-1.0, y_max=None):
        """The quad behind everything: the gradient runs from `y_top` (the top of the camera's view there) down
        to `y_horizon` and holds its end colours beyond."""
        self.images.append({"bufferView": self.view(gradient_png(stops)), "mimeType": "image/png"})
        self.textures.append({"source": len(self.images) - 1, "sampler": 0})
        self.materials.append({"name": "backdrop", "emissiveFactor": [1, 1, 1], "emissiveTexture": {"index": len(self.textures) - 1},
                               "pbrMetallicRoughness": {"baseColorFactor": [0, 0, 0, 1], "metallicFactor": 0, "roughnessFactor": 1}})
        top = y_max if y_max is not None else y_top + 0.6
        p = Primitive(len(self.materials) - 1)
        p.add(([(-width / 2, y_bottom, z), (width / 2, y_bottom, z), (width / 2, top, z), (-width / 2, top, z)], [Z] * 4, [(0, 1, 2), (0, 2, 3)]))
        v = lambda y: (y_top - y) / (y_top - y_horizon)
        p.uvs = [(0.0, v(y_bottom)), (1.0, v(y_bottom)), (1.0, v(top)), (0.0, v(top))]
        return self.node("Backdrop", [p])

    def node(self, name, primitives, at=(0.0, 0.0, 0.0), parent=None):
        """A node with a mesh of `primitives` (empty ones are dropped; none at all makes a plain joint)."""
        entry = {"name": name, "translation": list(at)}
        prims = []
        for p in primitives:
            if not p.triangles: continue
            attributes = {"POSITION": self.accessor(p.positions, "VEC3", target=34962, bounds=True), "NORMAL": self.accessor(p.normals, "VEC3", target=34962)}
            if p.uvs: attributes["TEXCOORD_0"] = self.accessor(p.uvs, "VEC2", target=34962)
            prims.append({"attributes": attributes, "indices": self.accessor([i for t in p.triangles for i in t], "SCALAR", 5123, target=34963), "material": p.material})
            self.triangles += len(p.triangles)
        if prims:
            self.meshes.append({"name": name.lower(), "primitives": prims})
            entry["mesh"] = len(self.meshes) - 1
        self.nodes.append(entry)
        index = len(self.nodes) - 1
        if parent is None: self.roots.append(index)
        else: self.nodes[parent].setdefault("children", []).append(index)
        return index

    def clip(self, name, times, rotations):
        """A clip of rotation keys by node index."""
        t = self.accessor(times, "SCALAR", bounds=True)
        samplers, channels = [], []
        for node, keys in rotations.items():
            samplers.append({"input": t, "output": self.accessor(keys, "VEC4"), "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": "rotation"}})
        self.animations.append({"name": name, "samplers": samplers, "channels": channels})

    def write(self, path):
        root = {"name": self.name, "children": self.roots}
        gltf = {
            "asset": {"version": "2.0", "generator": self.generator, "copyright": "CC0 1.0, made for QRX"},
            "scene": 0, "scenes": [{"name": self.name, "nodes": [len(self.nodes)]}],
            "nodes": self.nodes + [root], "meshes": self.meshes, "materials": self.materials,
            "accessors": self.accessors, "bufferViews": self.views,
        }
        if self.animations: gltf["animations"] = self.animations
        if self.images:
            gltf.update(images=self.images, textures=self.textures,
                        samplers=[{"magFilter": 9729, "minFilter": 9729, "wrapS": 33071, "wrapT": 33071}])
        while len(self.blob) % 4: self.blob.append(0)
        gltf["buffers"] = [{"byteLength": len(self.blob)}]
        chunk = json.dumps(gltf, separators=(",", ":")).encode()
        while len(chunk) % 4: chunk += b" "
        glb = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(chunk) + 8 + len(self.blob))
        glb += struct.pack("<II", len(chunk), 0x4E4F534A) + chunk + struct.pack("<II", len(self.blob), 0x004E4942) + bytes(self.blob)
        open(path, "wb").write(glb)
        print(f"{path.split('/')[-1]}: {len(glb)} bytes, {self.triangles} triangles")


TIMES = [i / 6 for i in range(37)]   # 6 s, the last key equal to the first


def sway(axis, degrees, phase):
    return [quat(axis, degrees * math.sin(2 * math.pi * t / 6 + phase)) for t in TIMES]


def clump(model, name, material, rng, at, leaves, height, width, lean=(0.15, 0.45), segments=4):
    p = Primitive(material)
    for i in range(leaves):
        p.add(blade(360 * i / leaves + rng.uniform(-20, 20), height * rng.uniform(0.6, 1.0), width, rng.uniform(*lean), segments, curl=rng.uniform(-0.12, 0.12)))
    return model.node(name, [p], at)


def stones(materials, rng, spots, sizes, floor):
    prims = {m: Primitive(m) for m in materials}
    for x, z in spots:
        r = rng.uniform(*sizes)
        prims[rng.choice(materials)].add(ellipsoid(x, floor(x, z), z, r, r * rng.uniform(0.45, 0.7), r * rng.uniform(0.7, 1.2), 8, 5))
    return list(prims.values())


# ---- the tank ---------------------------------------------------------------------------------------------
# Camera (0, 0.48, 1.30) looking level, 40 degrees: at the backdrop (z = -0.7) it sees x +-1.29, y -0.25 to 1.21.

def tank(out):
    m, rng = Model("HabitatTank", "QRX.pack scripts/habitats.py"), random.Random(11)
    floor = lambda x, z: 0.012 * math.sin(3.1 * x + 1.0) * math.cos(4.3 * z) + 0.008 * math.sin(7.0 * x - 2.0 * z)
    haze = lambda x, z: 0.07 + 0.05 * math.sin(1.9 * x + 0.6) + 0.02 * math.sin(5.3 * x)
    sand, far = m.material("sand", (0.74, 0.67, 0.5), roughness=0.95), m.material("far-sand", (0.05, 0.17, 0.24), roughness=1)
    grey, brown = m.material("stone", (0.36, 0.38, 0.38), roughness=0.7), m.material("stone-brown", (0.46, 0.38, 0.3), roughness=0.7)
    weed, kelp = m.material("weed", (0.14, 0.5, 0.33), True, 0.8), m.material("kelp", (0.1, 0.4, 0.36), True, 0.8)
    m.backdrop([(0, "#2AA7BF"), (0.3, "#0E6A8C"), (0.7, "#073553"), (1, "#04121F")], 3.6, 1.21, -0.02, -0.7)
    spots = [(rng.uniform(-1.3, 1.3), rng.uniform(-0.6, 0.0)) for _ in range(11)]
    m.node("Sand", [Primitive(sand).add(heightfield(-2.2, 2.2, -0.7, 1.4, 22, 10, floor)),
                    Primitive(far).add(heightfield(-2.2, 2.2, -0.699, -0.52, 30, 1, lambda x, z: haze(x, z) * smooth((-0.52 - z) / 0.12)))]
           + stones([grey, brown], rng, spots, (0.03, 0.085), floor))
    plants = [("WeedA", weed, (-0.95, -0.30), 9, 0.55, 0.05), ("WeedB", kelp, (0.92, -0.42), 10, 0.72, 0.06), ("WeedC", weed, (0.28, -0.58), 7, 0.24, 0.035),
              ("WeedD", kelp, (-0.42, -0.62), 7, 0.3, 0.04), ("WeedE", weed, (1.3, -0.62), 8, 0.62, 0.055), ("WeedF", kelp, (-1.32, -0.6), 8, 0.5, 0.05),
              ("WeedG", weed, (0.62, -0.2), 6, 0.16, 0.03)]
    rotations = {}
    for i, (name, material, (x, z), leaves, height, width) in enumerate(plants):
        node = clump(m, name, material, rng, (x, floor(x, z), z), leaves, height, width, segments=5)
        rotations[node] = sway(Z if i % 2 == 0 else X, 3.5 if height > 0.4 else 5, i * 1.3)
    m.clip("idle", TIMES, rotations)
    m.write(f"{out}/models/habitat-tank.glb")


# ---- the terrarium ----------------------------------------------------------------------------------------
# Camera (0, 0.42, 1.25) looking at (0, 0.12, -0.30), 40 degrees: the floor fills the lower half of the view and
# the walkers keep to x +-0.75, z -0.80 to 0.10, so the scenery stands around that patch, not on it.

def terrarium(out):
    m, rng = Model("HabitatTerrarium", "QRX.pack scripts/habitats.py"), random.Random(23)

    def floor(x, z):
        ridge = 0.16 * smooth((-0.9 - z) / 0.3) * (0.65 + 0.35 * math.sin(2.1 * x + 0.5) + 0.12 * math.sin(6.3 * x))
        return 0.012 * math.sin(5.0 * x + 0.4) * math.cos(6.0 * z) + 0.006 * math.sin(11.0 * x - 3.0 * z) + ridge
    soil = m.material("soil", (0.7, 0.49, 0.29), roughness=1)
    rock, rock2 = m.material("rock", (0.45, 0.38, 0.33), roughness=0.8), m.material("rock-pale", (0.6, 0.52, 0.44), roughness=0.8)
    bark, wood = m.material("bark", (0.33, 0.21, 0.13), roughness=0.9), m.material("wood", (0.62, 0.45, 0.28), roughness=0.9)
    succulent, grass = m.material("succulent", (0.36, 0.56, 0.38), True, 0.6), m.material("dry-grass", (0.5, 0.56, 0.27), True, 0.9)
    m.backdrop([(0, "#2B1B14"), (0.45, "#7A4A2A"), (0.72, "#C98A4B"), (1, "#E2B470")], 4.8, 0.85, 0.1, -1.2)
    pebbles = [(rng.uniform(-0.75, 0.75), rng.uniform(0.18, 0.6)) for _ in range(6)] + [(-0.95, -0.05), (0.98, -0.2), (-0.2, -0.95), (1.2, -0.62)]
    big = Primitive(rock).add(ellipsoid(1.12, 0.02, -0.84, 0.3, 0.2, 0.2, 12, 7)).add(ellipsoid(0.82, 0.02, -0.9, 0.15, 0.1, 0.12, 10, 6))
    log = Primitive(bark).add(tube([(-1.3, 0.06, -0.8), (-1.05, 0.065, -0.66), (-0.8, 0.06, -0.5)], [0.06, 0.065, 0.058], 10, caps=False))
    ends = Primitive(wood).add(tube([(-0.8, 0.06, -0.5), (-0.795, 0.06, -0.497)], [0.058, 0.05], 10))
    m.node("Ground", [Primitive(soil).add(heightfield(-2.2, 2.2, -1.2, 1.4, 26, 16, floor)), big, log, ends] + stones([rock, rock2], rng, pebbles, (0.018, 0.04), floor))
    rotations, n = {}, 0
    for name, (x, z), leaves, height, width in (("SucculentA", (-0.45, -0.98), 11, 0.17, 0.07), ("SucculentB", (0.92, -0.42), 12, 0.2, 0.08),
                                                ("SucculentC", (-0.9, -0.33), 10, 0.13, 0.06), ("SucculentD", (0.3, -1.0), 9, 0.12, 0.055),
                                                ("SucculentE", (-0.52, 0.34), 9, 0.07, 0.035), ("SucculentF", (0.6, 0.46), 8, 0.06, 0.03)):
        node = clump(m, name, succulent, rng, (x, floor(x, z), z), leaves, height, width, (0.5, 0.9), 3)
        rotations[node] = sway(Z, 1.5, n); n += 1.1
    for i, (x, z) in enumerate(((-1.15, -0.95), (-0.75, -1.0), (0.05, -0.95), (0.55, -0.9), (1.4, -0.85), (-1.5, -0.6), (1.35, -0.3))):
        node = clump(m, f"Grass{i + 1}", grass, rng, (x, floor(x, z), z), 7, rng.uniform(0.2, 0.34), 0.016, (0.2, 0.6), 3)
        rotations[node] = sway(Z if i % 2 else X, 6, i * 0.9)
    m.clip("idle", TIMES, rotations)
    m.write(f"{out}/models/habitat-terrarium.glb")


# ---- the aviary -------------------------------------------------------------------------------------------
# Camera (0, 0.62, 1.35) looking level, 45 degrees: at the backdrop (z = -1.0) it sees x +-1.73, y -0.35 to 1.59.
# It stands close, because the ones who live here are small.
# The meadow is the bottom of the picture; a branch comes in from the right, its tip near x = 0.46, for someone to perch on.

def aviary(out):
    m, rng = Model("HabitatAviary", "QRX.pack scripts/habitats.py"), random.Random(31)
    floor = lambda x, z: 0.03 * math.sin(1.3 * x + 0.7) + 0.015 * math.sin(3.7 * x - 1.9 * z) + 0.05 * smooth((-0.6 - z) / 0.4)
    turf = m.material("turf", (0.16, 0.36, 0.25), roughness=1)
    grass, grass2 = m.material("grass", (0.2, 0.46, 0.3), True, 0.9), m.material("grass-light", (0.3, 0.55, 0.33), True, 0.9)
    bark, leafy = m.material("bark", (0.24, 0.17, 0.2), roughness=0.9), m.material("leaf", (0.2, 0.44, 0.32), True, 0.8)
    petals = [m.material("petal-pink", (0.96, 0.62, 0.75), roughness=0.7), m.material("petal-gold", (0.98, 0.8, 0.36), roughness=0.7),
              m.material("petal-white", (0.95, 0.93, 0.9), roughness=0.7)]
    m.backdrop([(0, "#141B45"), (0.45, "#4A4A93"), (0.78, "#C97C8A"), (1, "#F4B183")], 4.6, 1.59, 0.06, -1.0)
    m.node("Meadow", [Primitive(turf).add(heightfield(-2.4, 2.4, -1.0, 1.5, 24, 12, floor))])
    rotations = {}
    # The grass in four rows from back to front, each its own node at the row's middle so it can lean a little.
    rows = [(-0.82, 0.14), (-0.52, 0.12), (-0.22, 0.12), (0.1, 0.14)]
    for r, (zc, spread) in enumerate(rows):
        a, b, heads, stems = Primitive(grass), Primitive(grass2), {p: Primitive(p) for p in petals}, Primitive(grass)
        for k in range(18):
            x, z = -1.75 + 3.5 * (k + rng.uniform(0.1, 0.9)) / 18, rng.uniform(-spread, spread)
            y = floor(x, zc + z)
            for _ in range(5):
                (a if rng.random() < 0.6 else b).add(blade(rng.uniform(0, 360), rng.uniform(0.08, 0.2), 0.013, rng.uniform(0.2, 0.7), 3, (x + rng.uniform(-0.05, 0.05), y, z + rng.uniform(-0.03, 0.03))))
        for _ in range(3):
            x, z, h = rng.uniform(-1.5, 1.5), rng.uniform(-spread, spread), rng.uniform(0.14, 0.24)
            y = floor(x, zc + z)
            stems.add(tube([(x, y, z), (x + 0.01, y + h, z)], [0.003, 0.0025], 4, caps=False))
            heads[rng.choice(petals)].add(ellipsoid(x + 0.01, y + h, z, 0.022, 0.013, 0.022, 7, 4))
        node = m.node(f"Grass{r + 1}", [a, b, stems] + list(heads.values()), (0.0, 0.0, zc))
        rotations[node] = sway(X, 2.5, r * 1.4)
    # The branch: from beyond the right edge, with a twig and leaves that stir.
    path = [(2.1, 0.74, -0.32), (1.6, 0.79, -0.3), (1.15, 0.84, -0.26), (0.8, 0.885, -0.22), (0.6, 0.895, -0.2), (0.46, 0.885, -0.2)]
    limb = Primitive(bark).add(tube(path, [0.05, 0.043, 0.034, 0.024, 0.017, 0.01], 8))
    limb.add(tube([(1.15, 0.84, -0.26), (1.06, 0.97, -0.28), (0.93, 1.08, -0.3)], [0.016, 0.011, 0.004], 6))
    m.node("Branch", [limb])
    leaves = Primitive(leafy)
    for x, y, z in ((0.93, 1.08, -0.3), (1.0, 1.03, -0.29), (1.08, 0.95, -0.28), (1.36, 0.82, -0.28), (1.5, 0.8, -0.3), (0.86, 0.89, -0.23), (0.68, 0.9, -0.2), (1.25, 0.84, -0.27)):
        for _ in range(2):
            leaves.add(blade(rng.uniform(0, 360), rng.uniform(0.07, 0.115), 0.05, rng.uniform(0.6, 1.2), 3, (x - 1.15, y - 0.84, z + 0.26)))
    rotations[m.node("Leaves", [leaves], (1.15, 0.84, -0.26))] = sway(Z, 1.6, 0.5)
    m.clip("idle", TIMES, rotations)
    m.write(f"{out}/models/habitat-aviary.glb")


if __name__ == "__main__":
    out = sys.argv[1]
    tank(out); terrarium(out); aviary(out)
