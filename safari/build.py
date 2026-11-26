#!/usr/bin/env python3
"""Writes safari/index.json from the safari.json beside each roadside and mega creature.

    python3 safari/build.py           write safari/index.json
    python3 safari/build.py --check   validate the definitions and the index; write nothing; exit 1 on a fault

A sighting's land is its own safari.json (name, the card line, and a biome weight for each
place it can stand). That file is the definition, the same role as species/definitions/<biome>/<id>.json.
The index is only the build of those files. Weights are the species rarity scale
(species/rarity.json): 60 common, 25 uncommon, 10 rare, 4 epic, 1 legendary.
Biome ids are the species catalog's (species/biomes.json).

Layout. Roadside fauna live in roadside/fauna/<id>/. Mega fauna live in mega/<id>/, next to the
empty mega/fauna placeholder, because the filed meshes are already there. Mega plants live in
mega/flora/<id>/. Roadside plants would live in roadside/flora/<id>/; that folder is empty.
The index carries the model path, so either layout is enough for the app.

Not sightings: mega/blue-whale-surfacing (a back and a spout) and mega/sauropod-herd (five animals).
They are not one creature. species/ is not read except for the biome ids and the rarity weights.

Standard library only.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PACK = "https://qrx-pack.apphaus.us/"
INDEX = os.path.join(HERE, "index.json")
# A picture that is not one creature, plus the folders that hold other groups.
SKIP_MEGA = {"blue-whale-surfacing", "sauropod-herd", "flora", "fauna", "preview"}
GROUPS = (
    ("roadside", "fauna", ("roadside", "fauna"), False),
    ("roadside", "flora", ("roadside", "flora"), False),
    ("mega", "fauna", ("mega",), True),
    ("mega", "flora", ("mega", "flora"), False),
)
KEYS = {"id", "name", "description", "biomes"}
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
        seen = {}
        for cls, kind, parts, at_mega_root in GROUPS:
            base = os.path.join(ROOT, *parts)
            if not os.path.isdir(base):
                self.fault(rel(*parts), "missing")
                continue
            for name in sorted(os.listdir(base)):
                folder = os.path.join(base, name)
                if not os.path.isdir(folder):
                    continue
                if at_mega_root and name in SKIP_MEGA:
                    continue
                where = rel(*(parts + (name,)))
                if name in seen:
                    self.fault(where, "the id %s is already used by %s" % (name, seen[name]))
                    continue
                seen[name] = where
                self.entries.append(self.read_one(cls, kind, parts, name, folder, where))
        order = {"roadside": 0, "mega": 1, "fauna": 0, "flora": 1}
        self.entries.sort(key=lambda e: (order[e["class"]], order[e["kind"]], e["id"]))

    def read_one(self, cls, kind, parts, name, folder, where):
        definition = os.path.join(folder, "safari.json")
        entry = {
            "id": name, "name": None, "class": cls, "kind": kind, "description": None,
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
        self.lands(where, data.get("biomes"), entry)
        self.model(where, parts, name, folder, kind, entry)
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

    def model(self, where, parts, name, folder, kind, entry):
        mesh = os.path.join(folder, "mesh.glb")
        brief = clips_in(os.path.join(folder, "prompt.md"))
        if not os.path.isfile(mesh):
            entry["model"] = None
            entry["clips"] = brief or []
            if kind == "fauna" and brief is None:
                self.fault(where, "no mesh.glb and no clips row in prompt.md")
            return
        entry["model"] = rel(*(parts + (name, "mesh.glb")))
        if not os.path.isfile(os.path.join(ROOT, *entry["model"].split("/"))):
            self.fault(where, "lists %s but the file is missing" % entry["model"])
        facts = mesh_facts(folder)
        if facts is None:
            self.fault(where, "mesh.glb has no box in made.json")
            return
        for key in ("size", "bytes", "triangles"):
            if not isinstance(facts[key], (int, float) if key != "size" else list):
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
            self.fault("safari/index.json", "missing; run safari/build.py")
            return
        blob = open(INDEX, "rb").read()
        if blob != fresh:
            self.fault("safari/index.json", "stale; run safari/build.py")
        try:
            saved = json.loads(blob.decode("utf-8"))
        except ValueError as error:
            self.fault("safari/index.json", "does not parse: %s" % error)
            return
        rows = saved.get("sightings")
        if not isinstance(rows, list):
            self.fault("safari/index.json", "sightings must be a list")
            return
        for row in rows:
            if not isinstance(row, dict):
                self.fault("safari/index.json", "a sighting is not an object")
                continue
            biomes = row.get("biomes")
            if not isinstance(biomes, dict) or not biomes:
                self.fault("safari/index.json", "%s has no biomes" % row.get("id"))
            elif any(biome not in self.biome_set for biome in biomes):
                bad = [biome for biome in biomes if biome not in self.biome_set]
                self.fault("safari/index.json", "%s has unknown biome %s" % (row.get("id"), ", ".join(bad)))
            model = row.get("model")
            if model is None:
                continue
            if not isinstance(model, str) or not os.path.isfile(os.path.join(ROOT, *model.split("/"))):
                self.fault("safari/index.json", "%s model is missing (%s)" % (row.get("id"), model))


def main():
    parser = argparse.ArgumentParser(description="Build safari/index.json from each creature's safari.json.")
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
        print("wrote safari/index.json (%d sightings)" % len(build.entries))
    build.check_saved(fresh)
    if build.faults:
        for fault in build.faults:
            print(fault, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
