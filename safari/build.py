#!/usr/bin/env python3
"""Writes species/safari.json from the safari.json beside each safari creature.

    python3 safari/build.py           write species/safari.json
    python3 safari/build.py --check   validate the definitions and the index; write nothing; exit 1 on a fault

A sighting's land is its own safari.json (name, the card line, class, kind, and a biome weight for each
place it can stand). That file is the definition, the same role as species/definitions/<biome>/<id>.json.
The index is only the build of those files. The folder does not say whether a sighting is fauna or flora,
or roadside or mega: class and kind are in the definition, and the app reads them from the index.

Weights are the species rarity scale (species/rarity.json): 60 common, 25 uncommon, 10 rare, 4 epic, 1 legendary.
Biome ids are the species catalog's (species/biomes.json).

Layout. Every creature is species/safari/<id>/. The model path in the index is species/safari/<id>/mesh.glb.
species/index.json is the wild catalog. This script never reads or writes it.
species/ is not read except for the biome ids and the rarity weights.

Size. The app draws each sighting at the index size, at every distance, with no further scaling.
A definition may give "size": [width, height, length] in metres, y up. That is the drawn size.
When it is absent and a mesh is filed, the size is that mesh's box. Bytes, triangles and clips
still come from made.json. The mesh itself is not rescaled.

Standard library only.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PACK = "https://qrx-pack.apphaus.us/"
INDEX = os.path.join(ROOT, "species", "safari.json")
SIGHTINGS = os.path.join(ROOT, "species", "safari")
# The preview page lives beside the creatures. It is not a sighting.
SKIP = {"preview"}
KEYS = {"id", "name", "description", "biomes", "class", "kind", "size"}
CLASSES = ("roadside", "mega")
KINDS = ("fauna", "flora")
DASH = ("\u2014", "\u2013")
CLIP_ROW = re.compile(r"^\| clips \| (.+) \|$", re.M)
CLIP_NAME = re.compile(r"`([^`]+)`")


def dump(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def biome_ids():
    data = load_json(os.path.join(ROOT, "species", "biomes.json"))
    return [b["id"] for b in data["biomes"]]


def weights():
    data = load_json(os.path.join(ROOT, "species", "rarity.json"))
    return {level["weight"] for level in data["levels"]}


def rel(*parts):
    return "/".join(parts)


def clips_in(prompt_path):
    if not os.path.isfile(prompt_path):
        return None
    text = open(prompt_path, encoding="utf-8").read()
    row = CLIP_ROW.search(text)
    if not row:
        return None
    return CLIP_NAME.findall(row.group(1))


def mesh_facts(folder):
    """Size, bytes, triangles and clips of mesh.glb, from made.json's record of that file."""
    made = os.path.join(folder, "made.json")
    if not os.path.isfile(made):
        return None
    facts = load_json(made).get("files", {}).get("mesh.glb", {}).get("facts", {})
    box = facts.get("box")
    if not (isinstance(box, list) and len(box) == 2 and all(isinstance(c, list) and len(c) == 3 for c in box)):
        return None
    return {
        "size": [round(box[1][i] - box[0][i], 4) for i in range(3)],
        "bytes": facts.get("bytes"),
        "triangles": facts.get("triangles"),
        "clips": facts.get("clips"),
    }


def as_size(value):
    """[width, height, length] in metres, or None when value is not a size."""
    if not (isinstance(value, list) and len(value) == 3):
        return None
    out = []
    for number in value:
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not number > 0:
            return None
        out.append(round(float(number), 4))
    return out


class Build:
    def __init__(self):
        self.faults = []
        self.biomes = biome_ids()
        self.biome_set = set(self.biomes)
        self.weights = weights()
        self.entries = []
        self.read_all()

    def fault(self, where, message):
        self.faults.append("%s: %s" % (where, message))

    def read_all(self):
        if not os.path.isdir(SIGHTINGS):
            self.fault("species/safari", "missing")
            return
        seen = {}
        for name in sorted(os.listdir(SIGHTINGS)):
            folder = os.path.join(SIGHTINGS, name)
            if not os.path.isdir(folder) or name in SKIP:
                continue
            where = rel("species", "safari", name)
            if name in seen:
                self.fault(where, "the id %s is already used by %s" % (name, seen[name]))
                continue
            seen[name] = where
            self.entries.append(self.read_one(name, folder, where))
        order = {"roadside": 0, "mega": 1, "fauna": 0, "flora": 1}
        self.entries.sort(key=lambda e: (order.get(e["class"], 9), order.get(e["kind"], 9), e["id"]))

    def read_one(self, name, folder, where):
        definition = os.path.join(folder, "safari.json")
        entry = {
            "id": name, "name": None, "class": None, "kind": None, "description": None,
            "biomes": {}, "model": None, "size": None, "bytes": None, "triangles": None, "clips": [],
        }
        if not os.path.isfile(definition):
            self.fault(where, "no safari.json")
            return entry
        try:
            data = load_json(definition)
        except ValueError as error:
            self.fault(where + "/safari.json", "does not parse: %s" % error)
            return entry
        if not isinstance(data, dict):
            self.fault(where + "/safari.json", "is not an object")
            return entry
        extra = set(data) - KEYS
        if extra:
            self.fault(where + "/safari.json", "unknown keys %s" % ", ".join(sorted(extra)))
        if data.get("id") != name:
            self.fault(where + "/safari.json", "its id must be the folder name %s" % name)
        self.text(where, "name", data.get("name"), entry)
        self.text(where, "description", data.get("description"), entry)
        self.choice(where, "class", data.get("class"), CLASSES, entry)
        self.choice(where, "kind", data.get("kind"), KINDS, entry)
        self.lands(where, data.get("biomes"), entry)
        authored = data.get("size")
        if "size" in data:
            parsed = as_size(authored)
            if parsed is None:
                self.fault(where + "/safari.json", "size must be [width, height, length] in metres, each greater than 0")
            authored = parsed
        else:
            authored = None
        self.model(where, name, folder, entry.get("kind"), entry, authored)
        return entry

    def text(self, where, key, value, entry):
        if not isinstance(value, str) or not value.strip() or value != value.strip() or "\n" in value:
            self.fault(where + "/safari.json", "%s must be one trimmed line" % key)
            return
        if any(mark in value for mark in DASH):
            self.fault(where + "/safari.json", "%s must not use an em dash or an en dash" % key)
            return
        if len(value) > 160:
            self.fault(where + "/safari.json", "%s is %d characters; a card line is at most 160" % (key, len(value)))
            return
        entry[key] = value

    def choice(self, where, key, value, allowed, entry):
        if value not in allowed:
            self.fault(where + "/safari.json", "%s must be one of %s" % (key, ", ".join(allowed)))
            return
        entry[key] = value

    def lands(self, where, biomes, entry):
        if not isinstance(biomes, dict) or not biomes:
            self.fault(where + "/safari.json", "biomes must list at least one biome")
            return
        ordered = {}
        for biome in self.biomes:
            if biome not in biomes:
                continue
            weight = biomes[biome]
            if weight not in self.weights:
                self.fault(where + "/safari.json", "%s weight %r is not a rarity weight (%s)" % (biome, weight, ", ".join(str(w) for w in sorted(self.weights, reverse=True))))
            else:
                ordered[biome] = weight
        unknown = [biome for biome in biomes if biome not in self.biome_set]
        for biome in unknown:
            self.fault(where + "/safari.json", "unknown biome \"%s\"" % biome)
        if not ordered and not unknown:
            self.fault(where + "/safari.json", "biomes must list at least one biome")
        entry["biomes"] = ordered

    def model(self, where, name, folder, kind, entry, authored):
        mesh = os.path.join(folder, "mesh.glb")
        brief = clips_in(os.path.join(folder, "prompt.md"))
        if not os.path.isfile(mesh):
            entry["model"] = None
            entry["clips"] = brief or []
            entry["size"] = authored
            if kind == "fauna" and brief is None:
                self.fault(where, "no mesh.glb and no clips row in prompt.md")
            if authored is None:
                self.fault(where, "no mesh.glb and no size in safari.json")
            return
        entry["model"] = rel("species", "safari", name, "mesh.glb")
        if not os.path.isfile(os.path.join(ROOT, *entry["model"].split("/"))):
            self.fault(where, "lists %s but the file is missing" % entry["model"])
        facts = mesh_facts(folder)
        if facts is None:
            self.fault(where, "mesh.glb has no box in made.json")
            return
        entry["size"] = authored if authored is not None else facts["size"]
        for key in ("bytes", "triangles"):
            if not isinstance(facts[key], (int, float)) or isinstance(facts[key], bool):
                self.fault(where, "made.json %s is missing" % key)
            else:
                entry[key] = facts[key]
        filed = facts.get("clips")
        if not isinstance(filed, list) or not filed or any(not isinstance(c, str) for c in filed):
            self.fault(where, "made.json clips must be a list of names")
        else:
            entry["clips"] = filed
            if brief is not None and set(brief) != set(filed):
                self.fault(where, "prompt.md clips %s and made.json clips %s differ" % (brief, filed))

    def index(self):
        return {"version": 1, "base": PACK, "sightings": self.entries}

    def check_saved(self, fresh):
        if not os.path.isfile(INDEX):
            self.fault("species/safari.json", "missing; run safari/build.py")
            return
        blob = open(INDEX, "rb").read()
        if blob != fresh:
            self.fault("species/safari.json", "stale; run safari/build.py")
        try:
            saved = json.loads(blob.decode("utf-8"))
        except ValueError as error:
            self.fault("species/safari.json", "does not parse: %s" % error)
            return
        rows = saved.get("sightings")
        if not isinstance(rows, list):
            self.fault("species/safari.json", "sightings must be a list")
            return
        for row in rows:
            if not isinstance(row, dict):
                self.fault("species/safari.json", "a sighting is not an object")
                continue
            biomes = row.get("biomes")
            if not isinstance(biomes, dict) or not biomes:
                self.fault("species/safari.json", "%s has no biomes" % row.get("id"))
            elif any(biome not in self.biome_set for biome in biomes):
                bad = [biome for biome in biomes if biome not in self.biome_set]
                self.fault("species/safari.json", "%s has unknown biome %s" % (row.get("id"), ", ".join(bad)))
            model = row.get("model")
            if model is None:
                continue
            if not isinstance(model, str) or not os.path.isfile(os.path.join(ROOT, *model.split("/"))):
                self.fault("species/safari.json", "%s model is missing (%s)" % (row.get("id"), model))


def main():
    parser = argparse.ArgumentParser(description="Build species/safari.json from each creature's safari.json.")
    parser.add_argument("--check", action="store_true", help="validate and compare; write nothing")
    args = parser.parse_args()
    try:
        build = Build()
    except (OSError, ValueError) as error:
        print("safari/build.py: %s" % error, file=sys.stderr)
        return 1
    fresh = dump(build.index())
    if not args.check and not build.faults:
        with open(INDEX, "wb") as f:
            f.write(fresh)
        print("wrote species/safari.json (%d sightings)" % len(build.entries))
    build.check_saved(fresh)
    if build.faults:
        for fault in build.faults:
            print(fault, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
