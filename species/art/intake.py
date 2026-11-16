#!/usr/bin/env python3
"""Takes what the image agent delivers for one creature, checks it and files it under species/art/<id>/, then
rewrites the table in species/art/README.md.

    python3 species/art/intake.py <id> --full render.jpg --cutout cutout.png --mesh mesh.glb --tool "who made them"
    python3 species/art/intake.py <id> ... --dry-run      check only, file nothing
    python3 species/art/intake.py --table                 rewrite README.md's table from what is filed
    python3 species/art/intake.py <id> --look DIR         the filed cutout on flat gray, written to DIR (never the repo)

Any one of --full, --cutout and --mesh may be given alone (a mesh can arrive after its images). A file already
filed is replaced only with --replace. Faults stop the intake; notes are printed and filed with it.

What is checked (rules from TerraLib's IMAGING.md, sections 3 to 5, and from what the pack's apps can show):
  full     a JPEG, at least FULL_MIN pixels on its long side
  cutout   a PNG with alpha; the subject touches no edge (every pixel within EDGE of the border is transparent);
           one subject (the largest opaque region holds nearly all of the opaque pixels); no gray composite: an
           image with no transparent pixels is refused
  mesh     a binary glTF 2.0 that parses: its buffers, views and accessors in range, indices inside their vertices;
           triangles, vertices, the box it fills, its textures and their sizes, whether it is skinned and its clips;
           extensions it requires that the apps are not known to read are a fault. Size, triangles and texture size
           over the limits below are notes, not faults, until the owner sets them (art/README.md, open questions)
Uses Pillow for the images (the system python3 on this Mac has it).
"""
import argparse, datetime, hashlib, json, os, shutil, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPECIES = os.path.dirname(HERE)
README = os.path.join(HERE, "README.md")
TABLE_START, TABLE_END = "<!-- table: written by intake.py --table -->", "<!-- /table -->"

FULL_MIN = 1024              # px on the long side
EDGE = 2                     # px of clear border the cutout must have on every side
ONE_SUBJECT = 0.97           # share of the opaque pixels the largest region must hold
LIMITS = {"bytes": 1024 * 1024, "triangles": 8000, "texture": 1024}     # SPEC.md section 3 (seven out at once on the Quest); the owner decides
KNOWN_EXTENSIONS = set()     # nothing is required-safe until a device has shown it (KHR_mesh_quantization: preview/quantized/)

GLB_MAGIC, CHUNK_JSON, CHUNK_BIN = 0x46546C67, 0x4E4F534A, 0x004E4942
COMPONENT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}


def pillow():
    try:
        from PIL import Image
        return Image
    except ImportError:
        sys.exit("Pillow is needed for the image checks: run this with the system python3 (/usr/bin/python3), or pip install Pillow")


# ---- the checks -------------------------------------------------------------------------------------------------

def check_full(path):
    Image = pillow()
    faults, facts = [], {}
    with Image.open(path) as im:
        facts.update(format=im.format, width=im.width, height=im.height)
        if im.format != "JPEG": faults.append("the full render is %s, not a JPEG" % im.format)
        if max(im.size) < FULL_MIN: faults.append("the full render is %dx%d, under %d px on its long side" % (im.width, im.height, FULL_MIN))
    return faults, [], facts


def check_cutout(path):
    Image = pillow()
    faults, notes, facts = [], [], {}
    with Image.open(path) as im:
        facts.update(format=im.format, width=im.width, height=im.height)
        if im.format != "PNG": faults.append("the cutout is %s, not a PNG" % im.format)
        if "A" not in im.getbands(): return faults + ["the cutout has no alpha: it must be the subject alone on a transparent background (a gray composite is never kept)"], notes, facts
        alpha = im.getchannel("A")
    w, h = alpha.size
    data = alpha.tobytes()
    solid = [v > 128 for v in data]
    count = sum(solid)
    if count == 0: return faults + ["the cutout is empty"], notes, facts
    if count == w * h: return faults + ["the cutout has no transparent pixels: it must be the subject alone"], notes, facts
    touching = [side for side, pixels in (
        ("top", data[:EDGE * w]), ("bottom", data[(h - EDGE) * w:]),
        ("left", bytes(data[y * w + x] for y in range(h) for x in range(EDGE))),
        ("right", bytes(data[y * w + x] for y in range(h) for x in range(w - EDGE, w)))) if max(pixels) > 8]
    if touching: faults.append("the subject touches the %s edge: it may be cut off there (TerraLib crops with a margin before cutting out)" % " and ".join(touching))
    xs = [i % w for i, s in enumerate(solid) if s]
    ys = [i // w for i, s in enumerate(solid) if s]
    facts.update(subject=[min(xs), min(ys), max(xs) + 1, max(ys) + 1], opaque=round(count / (w * h), 3))
    biggest = largest_region(solid, w, h)
    facts["oneSubject"] = round(biggest / count, 3)
    if biggest / count < ONE_SUBJECT: faults.append("the cutout holds more than one thing: its largest region is %.0f%% of what is opaque (soil, a shadow or a stray piece?)" % (100 * biggest / count))
    return faults, notes, facts


def largest_region(solid, w, h):
    """The size of the largest 4-connected region of True in a w x h grid (row-major)."""
    seen, best = bytearray(w * h), 0
    for start in range(w * h):
        if not solid[start] or seen[start]: continue
        seen[start], stack, size = 1, [start], 0
        while stack:
            i = stack.pop(); size += 1
            x, y = i % w, i // w
            for j in ((i - 1) if x > 0 else -1, (i + 1) if x < w - 1 else -1, (i - w) if y > 0 else -1, (i + w) if y < h - 1 else -1):
                if j >= 0 and solid[j] and not seen[j]: seen[j] = 1; stack.append(j)
        best = max(best, size)
    return best


def read_glb(data):
    if len(data) < 20: raise ValueError("shorter than a glb header")
    magic, version, total = struct.unpack_from("<III", data, 0)
    if magic != GLB_MAGIC or version != 2: raise ValueError("not a binary glTF 2.0")
    if total != len(data): raise ValueError("the header says %d bytes, the file has %d" % (total, len(data)))
    size, kind = struct.unpack_from("<II", data, 12)
    if kind != CHUNK_JSON: raise ValueError("the first chunk is not JSON")
    gltf = json.loads(data[20:20 + size].decode("utf-8"))
    binary, offset = b"", 20 + size
    if offset < len(data):
        size, kind = struct.unpack_from("<II", data, offset)
        if kind != CHUNK_BIN: raise ValueError("the second chunk is not BIN")
        binary = data[offset + 8:offset + 8 + size]
    return gltf, binary


def accessor_values(gltf, binary, index):
    a = gltf["accessors"][index]
    if "bufferView" not in a: return [0] * a["count"] * WIDTH[a["type"]]          # sparse or all zero: not read here
    view = gltf["bufferViews"][a["bufferView"]]
    if view.get("buffer", 0) != 0: raise ValueError("accessor %d is in an external buffer" % index)
    fmt, size = COMPONENT[a["componentType"]]
    width, count = WIDTH[a["type"]], a["count"]
    stride = view.get("byteStride") or size * width
    start = view.get("byteOffset", 0) + a.get("byteOffset", 0)
    end = start + stride * (count - 1) + size * width if count else start
    if end > view.get("byteOffset", 0) + view["byteLength"] or end > len(binary): raise ValueError("accessor %d runs past its buffer" % index)
    out = []
    for k in range(count): out.extend(struct.unpack_from("<%d%s" % (width, fmt), binary, start + k * stride))
    return out


def check_mesh(path):
    Image = pillow()
    faults, notes, facts = [], [], {}
    data = open(path, "rb").read()
    facts["bytes"] = len(data)
    try: gltf, binary = read_glb(data)
    except (ValueError, UnicodeDecodeError, struct.error) as error: return ["the mesh is not a readable .glb: %s" % error], notes, facts
    try:
        if gltf.get("asset", {}).get("version") != "2.0": faults.append("asset.version is not 2.0")
        required = set(gltf.get("extensionsRequired", []))
        if required - KNOWN_EXTENSIONS: faults.append("it requires %s, which the apps are not known to read" % ", ".join(sorted(required - KNOWN_EXTENSIONS)))
        if gltf.get("extensionsUsed"): facts["extensionsUsed"] = gltf["extensionsUsed"]
        triangles = vertices = 0
        lo, hi, uv, skinned = [float("inf")] * 3, [float("-inf")] * 3, True, False
        for m, mesh in enumerate(gltf.get("meshes", [])):
            for p, prim in enumerate(mesh["primitives"]):
                where = "mesh %d primitive %d" % (m, p)
                if prim.get("mode", 4) != 4: faults.append("%s is not triangles" % where); continue
                attributes = prim["attributes"]
                position = gltf["accessors"][attributes["POSITION"]]
                count = position["count"]
                vertices += count
                for i in range(3):
                    lo[i] = min(lo[i], position["min"][i]); hi[i] = max(hi[i], position["max"][i])
                if "TEXCOORD_0" not in attributes: uv = False
                if "JOINTS_0" in attributes and "WEIGHTS_0" in attributes: skinned = True
                if "indices" in prim:
                    indices = accessor_values(gltf, binary, prim["indices"])
                    if indices and max(indices) >= count: faults.append("%s: an index is past its last vertex" % where)
                    triangles += len(indices) // 3
                else: triangles += count // 3
                accessor_values(gltf, binary, attributes["POSITION"])          # in range, or it raises
        textures = []
        for i, image in enumerate(gltf.get("images", [])):
            if "bufferView" not in image: faults.append("image %d is outside the file (%s): everything must be inside the .glb" % (i, image.get("uri", "?")[:40])); continue
            view = gltf["bufferViews"][image["bufferView"]]
            raw = binary[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]]
            import io
            with Image.open(io.BytesIO(raw)) as im: textures.append({"format": im.format, "size": [im.width, im.height], "bytes": len(raw)})
        facts.update(triangles=triangles, vertices=vertices, box=[[round(c, 4) for c in lo], [round(c, 4) for c in hi]],
                     size=[round(hi[i] - lo[i], 4) for i in range(3)], textures=textures, skinned=skinned,
                     joints=sum(len(s.get("joints", [])) for s in gltf.get("skins", [])), clips=[a.get("name", "") for a in gltf.get("animations", [])])
        if not gltf.get("meshes"): faults.append("the file has no mesh")
        if textures and not uv: faults.append("it has a texture but a primitive has no TEXCOORD_0")
        if not textures: notes.append("no texture: colours come from materials or vertex colours only")
        if len(data) > LIMITS["bytes"]: notes.append("%d KB, over the proposed %d KB" % (len(data) // 1024, LIMITS["bytes"] // 1024))
        if triangles > LIMITS["triangles"]: notes.append("%d triangles, over the proposed %d (a decimation step would bring it down)" % (triangles, LIMITS["triangles"]))
        for t in textures:
            if max(t["size"]) > LIMITS["texture"]: notes.append("a %dx%d texture, over the proposed %d px" % (t["size"][0], t["size"][1], LIMITS["texture"]))
        if not skinned: notes.append("not rigged: it needs a skeleton, weights and clips before it can walk (art/RIGGING.md)")
    except (KeyError, IndexError, TypeError, ValueError, struct.error) as error:
        faults.append("the mesh does not read as glTF: %s %s" % (type(error).__name__, error))
    return faults, notes, facts


CHECKS = {"full": ("full.jpg", check_full), "cutout": ("cutout.png", check_cutout), "mesh": ("mesh.glb", check_mesh)}


# ---- filing and the table ---------------------------------------------------------------------------------------

def sha256(path):
    with open(path, "rb") as f: return hashlib.sha256(f.read()).hexdigest()


def known_ids():
    import glob
    return {os.path.basename(p)[:-5]: p for p in glob.glob(os.path.join(SPECIES, "definitions", "*", "*.json"))}


def intake(args):
    ids = known_ids()
    if args.id not in ids: sys.exit("%s is not a species of the pack" % args.id)
    folder = os.path.join(HERE, args.id)
    if not os.path.exists(os.path.join(folder, "prompt.txt")): sys.exit("%s has no prompt.txt: the prompt an image was made from is kept with it (art/prompts.py)" % args.id)
    given = {kind: getattr(args, kind) for kind in CHECKS if getattr(args, kind)}
    if not given: sys.exit("nothing to take: give --full, --cutout and/or --mesh")
    record_path = os.path.join(folder, "made.json")
    record = json.load(open(record_path, encoding="utf-8")) if os.path.exists(record_path) else {"files": {}}
    stop = False
    for kind, source in given.items():
        name, check = CHECKS[kind]
        faults, notes, facts = check(source)
        print("%s %s: %s" % (args.id, name, "ok" if not faults else "REFUSED"))
        for f in faults: print("  fault: " + f)
        for n in notes: print("  note: " + n)
        print("  " + json.dumps(facts))
        if os.path.exists(os.path.join(folder, name)) and not args.replace: print("  fault: %s is already filed (use --replace)" % name); faults.append("filed")
        if faults: stop = True; continue
        record["files"][name] = {"from": os.path.basename(source), "sha256": sha256(source), "tool": args.tool, "date": args.date, "notes": notes, "facts": facts}
    if stop: sys.exit(1)
    if args.dry_run: print("dry run: nothing filed"); return
    if not args.tool: sys.exit("--tool is needed to file: which agent or program made these")
    for kind, source in given.items(): shutil.copyfile(source, os.path.join(folder, CHECKS[kind][0]))
    with open(record_path, "w", encoding="utf-8") as f: json.dump(record, f, indent=2, ensure_ascii=False); f.write("\n")
    write_table()
    print("filed in species/art/%s/ and README.md's table rewritten" % args.id)


def write_table():
    ids = known_ids()
    rows = ["| creature | prompt | full render | cutout | mesh | made |", "| --- | --- | --- | --- | --- | --- |"]
    for creature in sorted(os.listdir(HERE)):
        folder = os.path.join(HERE, creature)
        if not os.path.isfile(os.path.join(folder, "prompt.txt")): continue
        d = json.load(open(ids[creature], encoding="utf-8")) if creature in ids else {"name": "?", "species": creature}
        prompt = open(os.path.join(folder, "prompt.txt"), encoding="utf-8").read().strip().replace("|", "/")
        record = json.load(open(os.path.join(folder, "made.json"), encoding="utf-8")) if os.path.exists(os.path.join(folder, "made.json")) else {"files": {}}
        files = record["files"]

        def image(name):
            return '<img src="%s/%s" width="160">' % (creature, name) if name in files else "waiting"
        if "mesh.glb" in files:
            m = files["mesh.glb"]["facts"]
            tex = ", ".join("%dx%d" % tuple(t["size"]) for t in m.get("textures", [])) or "none"
            mesh = "[mesh.glb](%s/mesh.glb)<br>%d KB, %d triangles<br>texture %s<br>%s" % (creature, m["bytes"] // 1024, m["triangles"], tex, "rigged" if m.get("skinned") else "not rigged")
        else: mesh = "waiting"
        made = "<br>".join(sorted({"%s, %s" % (f["tool"], f["date"]) for f in files.values()})) or "not yet"
        rows.append("| **%s**<br>%s<br>`%s` | <details><summary>prompt</summary>%s</details> | %s | %s | %s | %s |" % (
            d.get("name", "?"), d.get("species", creature), creature, prompt, image("full.jpg"), image("cutout.png"), mesh, made))
    text = open(README, encoding="utf-8").read()
    if TABLE_START not in text or TABLE_END not in text: sys.exit("README.md has lost its table markers")
    head, rest = text.split(TABLE_START, 1)
    _, tail = rest.split(TABLE_END, 1)
    with open(README, "w", encoding="utf-8") as f: f.write(head + TABLE_START + "\n" + "\n".join(rows) + "\n" + TABLE_END + tail)


def look(args):
    """The filed cutout on flat gray (128, 128, 128), for looking at once; written outside the pack."""
    Image = pillow()
    target = os.path.abspath(args.look)
    if target.startswith(os.path.abspath(os.path.join(SPECIES, ".."))): sys.exit("--look writes outside the repository: no gray composite is kept")
    with Image.open(os.path.join(HERE, args.id, "cutout.png")) as im:
        gray = Image.new("RGBA", im.size, (128, 128, 128, 255))
        gray.alpha_composite(im.convert("RGBA"))
        os.makedirs(target, exist_ok=True)
        out = os.path.join(target, "%s-on-gray.png" % args.id)
        gray.convert("RGB").save(out)
    print(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("id", nargs="?")
    parser.add_argument("--full"); parser.add_argument("--cutout"); parser.add_argument("--mesh")
    parser.add_argument("--tool", help="the agent or program that made the files")
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    parser.add_argument("--replace", action="store_true"); parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--table", action="store_true"); parser.add_argument("--look", metavar="DIR")
    args = parser.parse_args()
    if args.table: write_table(); print("README.md's table rewritten"); return
    if not args.id: parser.error("give a species id, or --table")
    if args.look: look(args); return
    intake(args)


if __name__ == "__main__":
    main()
