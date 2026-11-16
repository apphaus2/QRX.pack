#!/usr/bin/env python3
"""A test, not part of the pipeline: built models rewritten with KHR_mesh_quantization, to try on each device
before build.py writes every model that way.

    python3 species/preview/quantize.py [id ...]        default: a few creatures of different kinds

For each id it writes, in species/preview/quantized/:

    <id>.glb             the built model with positions as 16-bit integers and normals as 8-bit ones
    <id>.json            the built creature document, its model pointing at <id>.glb above
    <id>-control.json    the same document pointing at the unchanged models/<id>.glb

Both documents name their model at http://localhost:8778/species/..., so a phone or headset on USB reaches this
Mac after `adb reverse tcp:8778 tcp:8778` (preview/quantized/index.html shows a code for each). If the control
appears and the quantized one does not, the device cannot read KHR_mesh_quantization.

How it packs (KHR_mesh_quantization, https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_mesh_quantization):
each node with a mesh hands the mesh to a new child node, `<name>Q`, whose translation and uniform scale undo the
packing: a position p is stored as round((p - centre) / reach * 32767), so the child places it back at centre +
stored / 32767 * reach. Normals are stored as round(n * 127). Indices and every animation key are copied as they
were; the animated nodes are the same nodes, so every clip still finds its targets.
"""
import copy, gzip, json, math, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPECIES = os.path.dirname(HERE)
sys.path.insert(0, SPECIES)
from lib.gltf import GLB_MAGIC, CHUNK_JSON, CHUNK_BIN, FLOAT, USHORT, WIDTH, read_accessor, read_glb      # noqa: E402

BYTE, SHORT = 5120, 5122
OUT = os.path.join(HERE, "quantized")
DEFAULT = ["street-terrier", "meadow-pony", "northlight-fox", "pond-goldfish", "glacier-owl", "sun-scarab"]


def quantize(data):
    """The .glb `data` rewritten with KHR_mesh_quantization, and the largest distance (model units) any vertex moved."""
    gltf, binary = read_glb(data)
    out = copy.deepcopy(gltf)
    blob, views, accessors = bytearray(), [], []

    def view(raw, target=None, stride=None):
        while len(blob) % 4: blob.append(0)
        entry = {"buffer": 0, "byteOffset": len(blob), "byteLength": len(raw)}
        if stride: entry["byteStride"] = stride
        if target: entry["target"] = target
        views.append(entry)
        blob.extend(raw)
        return len(views) - 1

    def copied(index, target=None):
        """An accessor carried over unchanged (indices, animation times and keys)."""
        old = gltf["accessors"][index]
        size = 4 if old["componentType"] == FLOAT else 2
        start = gltf["bufferViews"][old["bufferView"]].get("byteOffset", 0) + old.get("byteOffset", 0)
        raw = binary[start:start + old["count"] * WIDTH[old["type"]] * size]
        entry = dict(old, bufferView=view(raw, target))
        entry.pop("byteOffset", None)
        accessors.append(entry)
        return len(accessors) - 1

    remap = {}
    def same(index, target=None):
        if index not in remap: remap[index] = copied(index, target)
        return remap[index]

    worst = 0.0
    # Each node with a mesh: the box of all its primitives' positions gives the packing for that mesh.
    for n, node in enumerate(gltf["nodes"]):
        if "mesh" not in node: continue
        mesh = out["meshes"][node["mesh"]]
        everything = [p for prim in gltf["meshes"][node["mesh"]]["primitives"] for p in read_accessor(gltf, binary, prim["attributes"]["POSITION"])]
        lo = [min(p[i] for p in everything) for i in range(3)]
        hi = [max(p[i] for p in everything) for i in range(3)]
        centre = [(lo[i] + hi[i]) / 2 for i in range(3)]
        reach = max(max(hi[i] - lo[i] for i in range(3)) / 2, 1e-9)
        for prim in mesh["primitives"]:
            positions = read_accessor(gltf, binary, prim["attributes"]["POSITION"])
            normals = read_accessor(gltf, binary, prim["attributes"]["NORMAL"])
            packed, raw = [], bytearray()
            for p in positions:
                q = [max(-32767, min(32767, round((p[i] - centre[i]) / reach * 32767))) for i in range(3)]
                back = [centre[i] + q[i] / 32767 * reach for i in range(3)]
                worst = max(worst, math.sqrt(sum((back[i] - p[i]) ** 2 for i in range(3))))
                packed.append(q)
                raw += struct.pack("<3hxx", *q)
            entry = {"bufferView": view(bytes(raw), 34962, 8), "componentType": SHORT, "normalized": True, "count": len(positions), "type": "VEC3",
                     "min": [min(q[i] for q in packed) for i in range(3)], "max": [max(q[i] for q in packed) for i in range(3)]}
            accessors.append(entry)
            prim["attributes"]["POSITION"] = len(accessors) - 1
            raw = bytearray()
            for v in normals:
                raw += struct.pack("<3bx", *[max(-127, min(127, round(c * 127))) for c in v])
            accessors.append({"bufferView": view(bytes(raw), 34962, 4), "componentType": BYTE, "normalized": True, "count": len(normals), "type": "VEC3"})
            prim["attributes"]["NORMAL"] = len(accessors) - 1
            prim["indices"] = same(prim["indices"], 34963)
        # The mesh moves to a child that undoes the packing; the node itself (what clips animate) keeps its place.
        child = {"name": node["name"] + "Q", "translation": [round(c, 7) for c in centre], "scale": [reach] * 3, "mesh": node["mesh"]}
        del out["nodes"][n]["mesh"]
        out["nodes"].append(child)
        out["nodes"][n].setdefault("children", []).append(len(out["nodes"]) - 1)
    for animation in out.get("animations", []):
        for sampler in animation["samplers"]:
            sampler["input"], sampler["output"] = same(sampler["input"]), same(sampler["output"])
    out["accessors"], out["bufferViews"] = accessors, views
    out["extensionsUsed"] = out["extensionsRequired"] = ["KHR_mesh_quantization"]
    blob += b"\0" * (-len(blob) % 4)
    out["buffers"] = [{"byteLength": len(blob)}]
    chunk = json.dumps(out, separators=(",", ":")).encode()
    chunk += b" " * (-len(chunk) % 4)
    glb = (struct.pack("<III", GLB_MAGIC, 2, 12 + 8 + len(chunk) + 8 + len(blob))
           + struct.pack("<II", len(chunk), CHUNK_JSON) + chunk + struct.pack("<II", len(blob), CHUNK_BIN) + bytes(blob))
    return glb, worst


def document(source, model_url):
    """The creature document at `source`, its actor's model pointing at `model_url`."""
    with open(source, encoding="utf-8") as f: doc = json.load(f)
    text = json.dumps(doc, ensure_ascii=False)
    old = [a["body"]["model"] for a in doc["actors"] if isinstance(a.get("body"), dict) and "model" in a["body"]]
    if len(old) != 1: raise ValueError("%s: expected one actor with a model, found %d" % (source, len(old)))
    return json.loads(text.replace(json.dumps(old[0]), json.dumps(model_url))), old[0]


def main(ids):
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for creature in ids:
        data = open(os.path.join(SPECIES, "models", creature + ".glb"), "rb").read()
        glb, worst = quantize(data)
        with open(os.path.join(OUT, creature + ".glb"), "wb") as f: f.write(glb)
        source = os.path.join(SPECIES, "creatures", creature + ".json")
        test, was = document(source, BASE + "preview/quantized/%s.glb" % creature)
        control, _ = document(source, BASE + "models/%s.glb" % creature)
        for name, doc in ((creature + ".json", test), (creature + "-control.json", control)):
            with open(os.path.join(OUT, name), "w", encoding="utf-8") as f: json.dump(doc, f, ensure_ascii=False, indent=2); f.write("\n")
        rows.append({"id": creature, "bytes": len(data), "gzip": len(gzip.compress(data, 6, mtime=0)),
                     "quantized": len(glb), "quantizedGzip": len(gzip.compress(glb, 6, mtime=0)), "worstMm": round(worst * 1000, 4), "was": was})
        r = rows[-1]
        print("%-16s %7d -> %7d bytes, gzip %7d -> %7d, worst vertex moved %.3f mm" % (creature, r["bytes"], r["quantized"], r["gzip"], r["quantizedGzip"], r["worstMm"]))
    with open(os.path.join(OUT, "list.json"), "w", encoding="utf-8") as f: json.dump({"base": BASE, "models": rows}, f, indent=2); f.write("\n")


# The preview server (.claude/launch.json, port 8778) serves the pack's species/ folder as its root.
BASE = "http://localhost:8778/"

if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT)
