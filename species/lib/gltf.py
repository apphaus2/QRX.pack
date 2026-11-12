"""A small glTF 2.0 binary writer and reader (standard library only), after `Model` in QRX.pack's
scripts/habitats.py.

The writer makes what JsonScene's loaders take: named nodes of plain coloured primitives (positions, normals,
16-bit indices), and clips of rotation, translation and scale keys with LINEAR interpolation. Everything is
rounded before it is packed, so the same input writes the same bytes on any machine. The reader is the other
half of `--check`: it parses a .glb from disk without trusting the writer and measures what is in it.
"""
import json, math, struct

from .shapes import merge

GLB_MAGIC, CHUNK_JSON, CHUNK_BIN = 0x46546C67, 0x4E4F534A, 0x004E4942
FLOAT, USHORT = 5126, 5123
WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
DIGITS = 6     # decimal places kept for positions, normals and keys


def f32(x):
    """x as the float32 a reader will see."""
    return struct.unpack("<f", struct.pack("<f", x))[0]


class Model:
    """Nodes of coloured primitives and clips, written as one .glb. `scale` multiplies every length."""

    def __init__(self, name, generator, scale=1.0):
        self.name, self.generator, self.scale = name, generator, scale
        self.blob, self.views, self.accessors = bytearray(), [], []
        self.materials, self.material_index = [], {}
        self.meshes, self.nodes, self.roots, self.node_index = [], [], [], {}
        self.clips = {}          # name -> [(node, path, times, values)]
        self.time_accessors = {}
        self.triangles = self.vertices = 0

    # ---- buffers ----

    def view(self, data, target=None):
        while len(self.blob) % 4: self.blob.append(0)
        entry = {"buffer": 0, "byteOffset": len(self.blob), "byteLength": len(data)}
        if target: entry["target"] = target
        self.views.append(entry)
        self.blob.extend(data)
        return len(self.views) - 1

    def accessor(self, values, kind, component=FLOAT, target=None, bounds=False):
        width = WIDTH[kind]
        flat = [v for value in values for v in (value if width > 1 else (value,))]
        if component == FLOAT:
            flat = [round(v, DIGITS) + 0.0 for v in flat]      # + 0.0 turns -0.0 into 0.0
            data = struct.pack("<%df" % len(flat), *flat)
            flat = list(struct.unpack("<%df" % len(flat), data))
        else:
            data = struct.pack("<%dH" % len(flat), *flat)
        entry = {"bufferView": self.view(data, target), "componentType": component, "count": len(values), "type": kind}
        if bounds:
            entry["min"] = [min(flat[i::width]) for i in range(width)]
            entry["max"] = [max(flat[i::width]) for i in range(width)]
        self.accessors.append(entry)
        return len(self.accessors) - 1

    # ---- content ----

    def material(self, name, rgb, double=False, roughness=0.6, metallic=0.0, emissive=None):
        """A plain colour (linear RGB), made once per name."""
        if name in self.material_index: return self.material_index[name]
        entry = {"name": name}
        if double: entry["doubleSided"] = True
        entry["pbrMetallicRoughness"] = {"baseColorFactor": [round(c, 4) for c in rgb] + [1], "metallicFactor": round(metallic, 3), "roughnessFactor": round(roughness, 3)}
        if emissive and any(c > 0 for c in emissive): entry["emissiveFactor"] = [round(min(c, 1.0), 4) for c in emissive]
        self.materials.append(entry)
        self.material_index[name] = len(self.materials) - 1
        return self.material_index[name]

    def node(self, name, prims=(), at=(0.0, 0.0, 0.0), parent=None, turn=None):
        """A node at `at` (in its parent's space) with a mesh of `prims`, a list of (material, part); parts of
        one material become one primitive. `turn` is a rest rotation (a quaternion). Returns the node's index."""
        if name in self.node_index: raise ValueError("node name used twice: %s" % name)
        if "." in name or "/" in name: raise ValueError("node names are animation targets: no '.' or '/' (%s)" % name)
        k = self.scale
        entry = {"name": name, "translation": [round(c * k, DIGITS) + 0.0 for c in at]}
        if turn is not None: entry["rotation"] = [round(c, DIGITS) + 0.0 for c in turn]
        by_material, order = {}, []
        for material, part in prims:
            if not part[2]: continue
            if material not in by_material: order.append(material)
            by_material.setdefault(material, []).append(part)
        primitives = []
        for material in order:
            positions, normals, triangles = merge(*by_material[material])
            if len(positions) > 65535: raise ValueError("%s: more than 65535 vertices in one primitive" % name)
            positions = [(p[0] * k, p[1] * k, p[2] * k) for p in positions]
            primitives.append({
                "attributes": {"POSITION": self.accessor(positions, "VEC3", target=34962, bounds=True), "NORMAL": self.accessor(normals, "VEC3", target=34962)},
                "indices": self.accessor([i for t in triangles for i in t], "SCALAR", USHORT, target=34963),
                "material": material,
            })
            self.triangles += len(triangles)
            self.vertices += len(positions)
        if primitives:
            self.meshes.append({"name": name.lower(), "primitives": primitives})
            entry["mesh"] = len(self.meshes) - 1
        self.nodes.append(entry)
        index = len(self.nodes) - 1
        self.node_index[name] = index
        if parent is None: self.roots.append(index)
        else: self.nodes[parent].setdefault("children", []).append(index)
        return index

    def channel(self, clip, node, path, times, values):
        """Keys for one node in the clip named `clip`: `path` is rotation (quaternions), translation (offsets
        from the node's rest position, in model units) or scale."""
        if path == "translation":
            rest = self.nodes[node]["translation"]
            values = [tuple(rest[i] + v[i] * self.scale for i in range(3)) for v in values]
        elif path == "rotation":
            fixed = []
            for q in values:
                n = math.sqrt(sum(c * c for c in q)) or 1.0
                fixed.append(tuple(c / n for c in q))
            values = fixed
        self.clips.setdefault(clip, []).append((node, path, list(times), list(values)))

    def rename_clip(self, old, new):
        self.clips = {(new if name == old else name): channels for name, channels in self.clips.items()}

    # ---- output ----

    def to_bytes(self):
        animations = []
        for name, channels in self.clips.items():
            samplers, targets = [], []
            for node, path, times, values in channels:
                key = tuple(round(t, DIGITS) for t in times)
                if key not in self.time_accessors: self.time_accessors[key] = self.accessor(list(key), "SCALAR", bounds=True)
                samplers.append({"input": self.time_accessors[key], "output": self.accessor(values, "VEC4" if path == "rotation" else "VEC3"), "interpolation": "LINEAR"})
                targets.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": path}})
            animations.append({"name": name, "samplers": samplers, "channels": targets})
        gltf = {
            "asset": {"version": "2.0", "generator": self.generator, "copyright": "CC0 1.0, made for QRX"},
            "scene": 0, "scenes": [{"name": self.name, "nodes": [len(self.nodes)]}],
            "nodes": self.nodes + [{"name": self.name, "children": self.roots}],
            "meshes": self.meshes, "materials": self.materials,
        }
        if animations: gltf["animations"] = animations
        gltf["accessors"], gltf["bufferViews"] = self.accessors, self.views
        blob = bytes(self.blob) + b"\0" * (-len(self.blob) % 4)
        gltf["buffers"] = [{"byteLength": len(blob)}]
        chunk = json.dumps(gltf, separators=(",", ":")).encode()
        chunk += b" " * (-len(chunk) % 4)
        return (struct.pack("<III", GLB_MAGIC, 2, 12 + 8 + len(chunk) + 8 + len(blob))
                + struct.pack("<II", len(chunk), CHUNK_JSON) + chunk + struct.pack("<II", len(blob), CHUNK_BIN) + blob)


# ---- reading ------------------------------------------------------------------------------------------------

class GlbError(Exception):
    pass


def read_glb(data):
    """The JSON and the binary chunk of a .glb, with the container checked."""
    if len(data) < 20: raise GlbError("shorter than a glb header")
    magic, version, total = struct.unpack_from("<III", data, 0)
    if magic != GLB_MAGIC: raise GlbError("not a glb (magic %08x)" % magic)
    if version != 2: raise GlbError("glb version %d, not 2" % version)
    if total != len(data): raise GlbError("header says %d bytes, the file has %d" % (total, len(data)))
    size, kind = struct.unpack_from("<II", data, 12)
    if kind != CHUNK_JSON: raise GlbError("the first chunk is not JSON")
    if size % 4 or 20 + size > len(data): raise GlbError("bad JSON chunk length %d" % size)
    try: gltf = json.loads(data[20:20 + size].decode("utf-8"))
    except ValueError as error: raise GlbError("the JSON chunk does not parse: %s" % error)
    offset = 20 + size
    binary = b""
    if offset < len(data):
        if offset + 8 > len(data): raise GlbError("truncated second chunk")
        size, kind = struct.unpack_from("<II", data, offset)
        if kind != CHUNK_BIN: raise GlbError("the second chunk is not BIN")
        if size % 4 or offset + 8 + size != len(data): raise GlbError("bad BIN chunk length %d" % size)
        binary = data[offset + 8:offset + 8 + size]
    return gltf, binary


def read_accessor(gltf, binary, index):
    """An accessor's values: numbers for SCALAR, tuples otherwise."""
    try:
        accessor = gltf["accessors"][index]
        view = gltf["bufferViews"][accessor["bufferView"]]
        width, count, component = WIDTH[accessor["type"]], accessor["count"], accessor["componentType"]
    except (KeyError, IndexError, TypeError) as error:
        raise GlbError("accessor %s: %r" % (index, error))
    if component not in (FLOAT, USHORT): raise GlbError("accessor %d: component type %s" % (index, component))
    size = 4 if component == FLOAT else 2
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    if view.get("byteStride"): raise GlbError("accessor %d: interleaved views are not written here" % index)
    if count * width * size > view["byteLength"] or start + count * width * size > len(binary):
        raise GlbError("accessor %d runs past its buffer view" % index)
    flat = struct.unpack_from("<%d%s" % (count * width, "f" if component == FLOAT else "H"), binary, start)
    if component == FLOAT and not all(math.isfinite(v) for v in flat): raise GlbError("accessor %d holds a NaN or an infinity" % index)
    return list(flat) if width == 1 else [flat[i:i + width] for i in range(0, len(flat), width)]


# ---- measuring ----------------------------------------------------------------------------------------------

def _matrix(translation, rotation, scale):
    x, y, z, w = rotation
    sx, sy, sz = scale
    return [
        [(1 - 2 * (y * y + z * z)) * sx, (2 * (x * y - z * w)) * sy, (2 * (x * z + y * w)) * sz, translation[0]],
        [(2 * (x * y + z * w)) * sx, (1 - 2 * (x * x + z * z)) * sy, (2 * (y * z - x * w)) * sz, translation[1]],
        [(2 * (x * z - y * w)) * sx, (2 * (y * z + x * w)) * sy, (1 - 2 * (x * x + y * y)) * sz, translation[2]],
    ]


def _compose(a, b):
    """The 3x4 transform b, then a."""
    return [[sum(a[r][k] * b[k][c] for k in range(3)) + (a[r][3] if c == 3 else 0.0) for c in range(4)] for r in range(3)]


def _apply(m, p):
    return tuple(m[r][0] * p[0] + m[r][1] * p[1] + m[r][2] * p[2] + m[r][3] for r in range(3))


def _sample(times, values, t, rotation):
    if t <= times[0]: return values[0]
    if t >= times[-1]: return values[-1]
    i = max(k for k in range(len(times) - 1) if times[k] <= t)
    s = (t - times[i]) / (times[i + 1] - times[i])
    a, b = values[i], values[i + 1]
    if rotation and sum(x * y for x, y in zip(a, b)) < 0: b = tuple(-c for c in b)
    out = tuple(x + (y - x) * s for x, y in zip(a, b))
    if rotation:
        n = math.sqrt(sum(c * c for c in out)) or 1.0
        out = tuple(c / n for c in out)
    return out


def inspect(data, digits=5):
    """Reads a .glb and returns (faults, facts). The faults are everything wrong with the file as a model the
    apps can show; the facts are what was measured: sizes, clips, the box at rest and the box swept by every clip."""
    faults = []
    try: gltf, binary = read_glb(data)
    except GlbError as error: return [str(error)], {}
    facts = {"bytes": len(data)}
    try:
        if gltf.get("asset", {}).get("version") != "2.0": faults.append("asset.version is not 2.0")
        buffers = gltf.get("buffers", [])
        if len(buffers) != 1 or buffers[0].get("byteLength") != len(binary): faults.append("buffers[0].byteLength is not the BIN chunk's length")
        for i, view in enumerate(gltf.get("bufferViews", [])):
            if view.get("byteOffset", 0) + view["byteLength"] > len(binary): faults.append("bufferView %d runs past the buffer" % i)
        nodes, meshes, materials = gltf.get("nodes", []), gltf.get("meshes", []), gltf.get("materials", [])
        names = [n.get("name") for n in nodes]
        if any(not n for n in names): faults.append("a node has no name")
        if len(set(names)) != len(names): faults.append("node names are not unique: %s" % sorted(n for n in set(names) if names.count(n) > 1))
        if any(n and ("." in n or "/" in n) for n in names): faults.append("a node name has '.' or '/' (clips find nodes by name)")
        for i, material in enumerate(materials):
            pbr = material.get("pbrMetallicRoughness", {})
            colours = list(pbr.get("baseColorFactor", [1, 1, 1, 1])) + list(material.get("emissiveFactor", []))
            if any(not 0 <= c <= 1 for c in colours): faults.append("material %d has a colour outside 0..1" % i)

        # Meshes: every accessor read, bounds, unit normals, indices in range, winding against the normals.
        geometry, triangles, vertices, inside_out, eye_meshes = {}, 0, 0, 0, set()
        for m, mesh in enumerate(meshes):
            parts = []
            for p, primitive in enumerate(mesh.get("primitives", [])):
                where = "mesh %d primitive %d" % (m, p)
                if primitive.get("mode", 4) != 4: faults.append("%s is not triangles" % where)
                material = primitive.get("material")
                if material is None or not 0 <= material < len(materials): faults.append("%s names no material" % where); continue
                positions = read_accessor(gltf, binary, primitive["attributes"]["POSITION"])
                normals = read_accessor(gltf, binary, primitive["attributes"]["NORMAL"])
                indices = read_accessor(gltf, binary, primitive["indices"])
                accessor = gltf["accessors"][primitive["attributes"]["POSITION"]]
                lo = [min(q[i] for q in positions) for i in range(3)]
                hi = [max(q[i] for q in positions) for i in range(3)]
                if "min" not in accessor or "max" not in accessor: faults.append("%s: POSITION has no min/max" % where)
                elif any(abs(a - b) > 1e-6 for a, b in zip(lo + hi, list(accessor["min"]) + list(accessor["max"]))): faults.append("%s: POSITION min/max do not match the data" % where)
                if len(normals) != len(positions): faults.append("%s: %d normals for %d positions" % (where, len(normals), len(positions)))
                if any(abs(math.sqrt(sum(c * c for c in n)) - 1) > 2e-3 for n in normals): faults.append("%s: a normal is not unit length" % where)
                if len(indices) % 3: faults.append("%s: %d indices is not whole triangles" % (where, len(indices)))
                if indices and max(indices) >= len(positions): faults.append("%s: an index is past the last vertex" % where); continue
                if not materials[material].get("doubleSided"):
                    for t in range(0, len(indices) - 2, 3):
                        a, b, c = (positions[indices[t + k]] for k in range(3))
                        e1, e2 = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
                        face = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
                        vertex = [sum(normals[indices[t + k]][i] for k in range(3)) for i in range(3)]
                        if sum(face[i] * vertex[i] for i in range(3)) < 0: inside_out += 1
                parts.append(positions)
                if str(materials[material].get("name", "")).startswith("eye"): eye_meshes.add((m, len(parts) - 1))
                triangles += len(indices) // 3
                vertices += len(positions)
            geometry[m] = parts
        if inside_out: faults.append("%d triangles of single-sided materials face inwards" % inside_out)
        facts.update(triangles=triangles, vertices=vertices, nodes=[n for n in names if n], materials=[m.get("name") for m in materials])

        # The node tree.
        scene = gltf.get("scenes", [{}])[gltf.get("scene", 0)]
        parents = {}
        for i, node in enumerate(nodes):
            for child in node.get("children", []):
                if child in parents or not 0 <= child < len(nodes): faults.append("node %d is a child twice or does not exist" % child)
                parents[child] = i
        roots = scene.get("nodes", [])
        if len(roots) != 1: faults.append("the scene has %d roots, not 1" % len(roots))

        eyes = []      # where the eye-coloured parts are at rest, for "which way does it face"

        def box(pose):
            """The model's box with `pose` {(node, path): value} over the rest transforms."""
            lo, hi = [math.inf] * 3, [-math.inf] * 3

            def walk(index, parent):
                node = nodes[index]
                local = _matrix(pose.get((index, "translation"), node.get("translation", (0, 0, 0))),
                                pose.get((index, "rotation"), node.get("rotation", (0, 0, 0, 1))),
                                pose.get((index, "scale"), node.get("scale", (1, 1, 1))))
                world = _compose(parent, local) if parent else local
                for k, positions in enumerate(geometry.get(node.get("mesh"), [])):
                    if not pose and (node.get("mesh"), k) in eye_meshes: eyes.extend(_apply(world, p)[2] for p in positions)
                    for p in positions:
                        q = _apply(world, p)
                        for i in range(3):
                            if q[i] < lo[i]: lo[i] = q[i]
                            if q[i] > hi[i]: hi[i] = q[i]
                for child in node.get("children", []): walk(child, world)
            for root in roots: walk(root, None)
            return lo, hi

        rest = box({})
        facts["box"] = [[round(c, digits) for c in rest[0]], [round(c, digits) for c in rest[1]]]
        if eyes: facts["eyes"] = round(sum(eyes) / len(eyes), digits)

        # Clips: named, on real nodes, keys in order from 0, unit quaternions, the last key equal to the first.
        clips, swept = {}, [list(rest[0]), list(rest[1])]
        seen = set()
        for a, animation in enumerate(gltf.get("animations", [])):
            name = animation.get("name")
            if not name: faults.append("animation %d has no name" % a); continue
            if name in seen: faults.append("two clips are named %s" % name)
            seen.add(name)
            channels, duration, moved_nodes = [], 0.0, set()
            for channel in animation.get("channels", []):
                target, sampler = channel.get("target", {}), animation["samplers"][channel["sampler"]]
                node, path = target.get("node"), target.get("path")
                where = "clip %s, node %s %s" % (name, names[node] if node is not None and 0 <= node < len(nodes) else node, path)
                if node is None or not 0 <= node < len(nodes): faults.append("%s: no such node" % where); continue
                if path not in ("rotation", "translation", "scale"): faults.append("%s: path not supported" % where); continue
                if (node, path) in moved_nodes: faults.append("%s: two channels" % where)
                moved_nodes.add((node, path))
                if sampler.get("interpolation", "LINEAR") != "LINEAR": faults.append("%s: interpolation is not LINEAR" % where)
                times, values = read_accessor(gltf, binary, sampler["input"]), read_accessor(gltf, binary, sampler["output"])
                if len(times) != len(values) or len(times) < 2: faults.append("%s: %d times for %d keys" % (where, len(times), len(values))); continue
                if times[0] != 0 or any(b <= a for a, b in zip(times, times[1:])): faults.append("%s: key times do not start at 0 and rise" % where)
                if len(values[0]) != (4 if path == "rotation" else 3): faults.append("%s: wrong key width" % where); continue
                if path == "rotation" and any(abs(math.sqrt(sum(c * c for c in q)) - 1) > 2e-3 for q in values): faults.append("%s: a quaternion is not unit length" % where)
                if any(abs(x - y) > 2e-5 for x, y in zip(values[0], values[-1])): faults.append("%s: the last key is not the first, so the loop jumps" % where)
                duration = max(duration, times[-1])
                channels.append((node, path, times, values))
            if not channels: faults.append("clip %s moves nothing" % name); continue
            if any(abs(times[-1] - duration) > 1e-6 for _, _, times, _ in channels): faults.append("clip %s: its channels end at different times" % name)
            clips[name] = {"duration": round(duration, 4), "channels": len(channels)}
            for t in sorted({t for _, _, times, _ in channels for t in times}):
                lo, hi = box({(node, path): _sample(times, values, t, path == "rotation") for node, path, times, values in channels})
                for i in range(3):
                    swept[0][i], swept[1][i] = min(swept[0][i], lo[i]), max(swept[1][i], hi[i])
        facts["clips"] = clips
        facts["swept"] = [[round(c, digits) for c in swept[0]], [round(c, digits) for c in swept[1]]]
    except (GlbError, KeyError, IndexError, TypeError, ValueError) as error:
        faults.append("unreadable: %s %s" % (type(error).__name__, error))
    return faults, facts
