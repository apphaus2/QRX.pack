#!/usr/bin/env python3
"""Turns the species definitions into creatures: a JsonScene document and a glTF model for each, and the catalog.

    python3 species/build.py                      build everything (creatures/, models/, index.json)
    python3 species/build.py --check              validate the definitions and what is on disk; exit 1 on a fault
    python3 species/build.py --model-base <base>  how the documents name their models: the URL they are served under
                                                  (the default, "https://qrx.apphaus.us/species/models/"), or
                                                  "bundle:" for models shipped inside an app

Standard library only (Python 3.9 or later). README.md describes the layout and how to add to it.
"""
import argparse, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lib import archetypes as archetype_package          # noqa: E402
from lib.behaviour import TEMPERS, logic                  # noqa: E402
from lib.builder import FEATURES, Builder, add_motes      # noqa: E402
from lib.gltf import inspect                              # noqa: E402

GENERATOR = "QRX species/build.py"
DEFAULT_MODEL_BASE = "https://qrx.apphaus.us/species/models/"     # species are pulled by URL, like any glyph a code names; nothing is bundled
MAX_MODEL_BYTES = 80 * 1024        # the pack's creatures are 27 to 75 KB
ID = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
DEFINITION_KEYS = {"id", "name", "species", "description", "biomes", "habitat", "rarity", "archetype", "size", "shape", "colours", "pattern", "movement", "behaviour"}
REQUIRED_KEYS = {"id", "name", "species", "description", "biomes", "habitat", "rarity", "archetype", "size"}


def read_json(*path):
    with open(os.path.join(HERE, *path), encoding="utf-8") as f:
        return json.load(f)


def dump(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


# ---- the data ------------------------------------------------------------------------------------------------

class Data:
    """rarity.json, habitats.json, biomes.json, reserved.json, the archetypes and every definition, with the faults
    found reading them."""

    def __init__(self):
        self.faults = []
        rarity = read_json("rarity.json")
        self.visitor_share = rarity.get("visitorShare", 1.0)
        self.rarities = {level["id"]: level for level in rarity["levels"]}
        self.habitats = {h["id"]: h for h in read_json("habitats.json")["habitats"]}
        self.biomes = {b["id"]: b for b in read_json("biomes.json")["biomes"]}
        self.reserved = read_json("reserved.json")
        self.archetypes = archetype_package.load()
        self.check_tables(rarity)
        self.definitions = self.read_definitions()

    def fault(self, where, message):
        self.faults.append("%s: %s" % (where, message))

    def check_tables(self, rarity):
        if len(self.rarities) != len(rarity["levels"]): self.fault("rarity.json", "two levels share an id")
        if not 0 < self.visitor_share <= 1: self.fault("rarity.json", "visitorShare must be over 0 and at most 1")
        for level in rarity["levels"]:
            where = "rarity.json %s" % level.get("id")
            if not isinstance(level.get("weight"), (int, float)) or level["weight"] <= 0: self.fault(where, "weight must be a positive number")
            if not HEX.match(str(level.get("colour", ""))): self.fault(where, "colour must be #rrggbb")
            if any(f not in FEATURES for f in level.get("features", [])): self.fault(where, "features may be %s" % ", ".join(FEATURES))
            if not 0 <= level.get("glow", 0) <= 1: self.fault(where, "glow is 0 to 1")
            if not isinstance(level.get("maxBiomes"), int) or level["maxBiomes"] < 1: self.fault(where, "maxBiomes must be 1 or more")
        for h in self.habitats.values():
            where = "habitats.json %s" % h.get("id")
            for key in ("bounds", "wild"):
                box = h.get(key, {})
                if len(box.get("min", [])) != 3 or len(box.get("max", [])) != 3 or any(a >= b for a, b in zip(box["min"], box["max"])): self.fault(where, "%s needs min below max on three axes" % key)
            if h.get("mode") not in ("ground", "air"): self.fault(where, "mode is ground or air (JsonScene's mobility modes)")
            if h.get("origin") not in ("ground", "centre"): self.fault(where, "origin is ground or centre")
            if not h.get("move") or h["move"] == "idle": self.fault(where, "move names the moving clip (swim, walk, fly)")
            if h.get("anchor") not in ("code", "floor", "free"): self.fault(where, "anchor is code, floor or free")
            if len(h.get("size", [])) != 2 or not 0 < h["size"][0] < h["size"][1]: self.fault(where, "size is [smallest, largest] longest side in metres")
        codes = [b.get("code") for b in self.biomes.values()]
        if len(set(codes)) != len(codes): self.fault("biomes.json", "two biomes share a land-cover code")
        for biome in self.biomes.values():
            where = "biomes.json %s" % biome.get("id")
            if not ID.match(str(biome.get("id", ""))): self.fault(where, "id must be lower-case words joined by hyphens")
            if not isinstance(biome.get("code"), int): self.fault(where, "code must be the land-cover class number")
            if not HEX.match(str(biome.get("colour", ""))): self.fault(where, "colour must be #rrggbb")
            if not biome.get("name") or not biome.get("description"): self.fault(where, "needs a name and a description")
            if not isinstance(biome.get("roster"), int) or biome["roster"] < 0: self.fault(where, "roster is the least number of species at home here")
        for name, module in self.archetypes.items():
            missing = [k for k in ("HABITAT", "ORIGIN", "LENGTH", "SHAPE", "COLOURS", "PATTERNS", "build") if not hasattr(module, k)]
            if missing: self.fault("archetype %s" % name, "lacks %s" % ", ".join(missing))

    def read_definitions(self):
        """Every definitions/<biome>/<id>.json, by id, in id order."""
        found, root = {}, os.path.join(HERE, "definitions")
        for folder in sorted(os.listdir(root)):
            if not os.path.isdir(os.path.join(root, folder)): continue
            if folder not in self.biomes: self.fault("definitions/%s" % folder, "is not a biome in biomes.json")
            for name in sorted(os.listdir(os.path.join(root, folder))):
                if not name.endswith(".json"): continue
                where = "definitions/%s/%s" % (folder, name)
                try: definition = read_json("definitions", folder, name)
                except ValueError as error:
                    self.fault(where, "does not parse: %s" % error); continue
                if not isinstance(definition, dict): self.fault(where, "is not an object"); continue
                if definition.get("id") != name[:-5]: self.fault(where, "its id must be the file's name")
                if definition.get("id") in found: self.fault(where, "the id %s is used twice" % definition.get("id")); continue
                if isinstance(definition.get("biomes"), list) and definition["biomes"] and definition["biomes"][0] != folder:
                    self.fault(where, "is filed under %s but its home biome (the first of biomes) is %s" % (folder, definition["biomes"][0]))
                definition["_where"] = where
                found[name[:-5]] = definition
        return dict(sorted(found.items()))

    # ---- one definition ----

    def check_definition(self, d):
        """The faults in one definition; an empty list means it can be built."""
        faults = []
        bad = lambda message: faults.append("%s: %s" % (d["_where"], message))
        for key in sorted(REQUIRED_KEYS - set(d)): bad("needs \"%s\"" % key)
        for key in sorted(set(d) - DEFINITION_KEYS - {"_where"}): bad("unknown key \"%s\"" % key)
        if faults: return faults
        if not ID.match(str(d["id"])): bad("id must be lower-case words joined by hyphens")
        if d["id"] in self.reserved["ids"]: bad("the id %s is one QRX.pack uses" % d["id"])
        for key in ("name", "species", "description"):
            if not isinstance(d[key], str) or not d[key].strip() or "\n" in d[key]: bad("%s must be one line of text" % key)
        if isinstance(d["name"], str) and d["name"] in self.reserved["names"]: bad("the name %s belongs to a QRX.pack creature" % d["name"])
        if isinstance(d["description"], str) and len(d["description"]) > 160: bad("description is over 160 characters")
        rarity, habitat, archetype = self.rarities.get(d["rarity"]), self.habitats.get(d["habitat"]), self.archetypes.get(d["archetype"])
        if rarity is None: bad("unknown rarity \"%s\"" % d["rarity"])
        if habitat is None: bad("unknown habitat \"%s\"" % d["habitat"])
        if archetype is None: bad("unknown archetype \"%s\"" % d["archetype"])
        biomes = d["biomes"]
        if not isinstance(biomes, list) or not biomes or any(not isinstance(x, str) for x in biomes): bad("biomes must be a list of biome ids, home first")
        else:
            for biome in biomes:
                if biome not in self.biomes: bad("unknown biome \"%s\"" % biome)
            if len(set(biomes)) != len(biomes): bad("a biome is listed twice")
            if rarity and len(biomes) > rarity["maxBiomes"]: bad("a %s species may be found in at most %d biome(s), not %d" % (d["rarity"], rarity["maxBiomes"], len(biomes)))
        if not isinstance(d["size"], (int, float)) or isinstance(d["size"], bool) or d["size"] <= 0: bad("size must be a length in metres")
        if habitat and archetype and habitat["origin"] != archetype.ORIGIN:
            bad("a %s keeps its origin at the %s, but the %s habitat needs it at the %s" % (d["archetype"], archetype.ORIGIN, d["habitat"], habitat["origin"]))
        if archetype:
            choices = getattr(archetype, "CHOICES", {})
            for key, value in d.get("shape", {}).items():
                if key not in archetype.SHAPE: bad("the %s archetype has no shape parameter \"%s\" (it has %s)" % (d["archetype"], key, ", ".join(archetype.SHAPE))); continue
                default = archetype.SHAPE[key]
                number = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
                if isinstance(default, bool): ok = isinstance(value, bool)
                elif number(default): ok = number(value)
                elif isinstance(default, list): ok = isinstance(value, list) and len(value) == len(default) and all(number(v) for v in value)
                else: ok = isinstance(value, str)
                if not ok: bad("shape.%s must be like %s" % (key, json.dumps(default)))
                elif key in choices and value not in choices[key]: bad("shape.%s is one of %s" % (key, ", ".join(choices[key])))
            for slot, colour in d.get("colours", {}).items():
                if slot not in archetype.COLOURS: bad("the %s archetype has no colour \"%s\" (it has %s)" % (d["archetype"], slot, ", ".join(archetype.COLOURS)))
                elif not HEX.match(str(colour)): bad("colours.%s must be #rrggbb" % slot)
            pattern = d.get("pattern", {"type": "plain"})
            if not isinstance(pattern, dict) or pattern.get("type") not in archetype.PATTERNS: bad("pattern.type is one of %s" % ", ".join(archetype.PATTERNS))
        movement = d.get("movement", {})
        for key, value in movement.items():
            if key in ("speed", "turnRate"):
                if not isinstance(value, (int, float)) or value <= 0: bad("movement.%s must be a positive number" % key)
            elif key == "pause":
                if not isinstance(value, list) or len(value) != 2 or not 0 <= value[0] <= value[1]: bad("movement.pause is [shortest, longest] seconds")
            else: bad("unknown movement key \"%s\"" % key)
        behaviour = d.get("behaviour", {})
        if behaviour.get("temper", "shy") not in TEMPERS: bad("behaviour.temper is one of %s" % ", ".join(TEMPERS))
        for key in behaviour:
            if key not in ("temper", "distance", "seconds", "watch"): bad("unknown behaviour key \"%s\"" % key)
        return faults


# ---- building --------------------------------------------------------------------------------------------------

def model_reference(base, species_id):
    """How a document names a species' model under `base`."""
    if base.endswith(":") or base.endswith("/") or base == "": return "%s%s.glb" % (base, species_id)
    return "%s/%s.glb" % (base, species_id)


def build_model(data, d):
    """The .glb for one definition, and what the archetype said about it."""
    archetype, rarity, habitat = data.archetypes[d["archetype"]], data.rarities[d["rarity"]], data.habitats[d["habitat"]]
    b = Builder(d, rarity, archetype, GENERATOR)
    made = archetype.build(b) or {}
    if rarity.get("motes") and b.has("motes"): add_motes(b, int(rarity["motes"]))
    if set(b.model.clips) != {"idle", "move"}: raise ValueError("the %s archetype made the clips %s, not idle and move" % (d["archetype"], sorted(b.model.clips)))
    b.model.rename_clip("move", habitat["move"])
    return b.model.to_bytes(), made


def build_document(data, d, made, model_base):
    """The creature's scene, in the shape of QRX.pack's creature-*.json with the body inlined."""
    habitat = data.habitats[d["habitat"]]
    movement, wild = d.get("movement", {}), habitat["wild"]
    state, behaviors, on = logic(d.get("behaviour", {}), movement.get("pause", habitat["pause"]))
    mobility = {"mode": habitat["mode"], "speed": movement.get("speed", habitat["speed"]), "turnRate": movement.get("turnRate", habitat["turnRate"])}
    if habitat["mode"] == "air": mobility["altitude"] = [wild["min"][1], wild["max"][1]]
    mobility.update(idle="idle", move=habitat["move"])
    return {
        "_ui": {"version": 1, "habitat": d["habitat"], "species": d["id"], "rarity": d["rarity"], "biome": d["biomes"][0], "biomes": list(d["biomes"]), "state": state},
        "type": "Scene",
        "anchor": habitat["anchor"],
        "bounds": {"min": list(wild["min"]), "max": list(wild["max"])},
        "actors": [{
            "id": actor_id(d),
            "name": d["name"],
            "transform": {"position": list(habitat["start"]), "rotation": [0, 90, 0]},
            "body": {
                "model": model_reference(model_base, d["id"]),
                "scale": 1,
                "animations": {"idle": {"clip": "idle", "loop": True}, habitat["move"]: {"clip": habitat["move"], "loop": True}},
                "sockets": dict(made.get("sockets", {})),
            },
            "mobility": mobility,
            "behaviors": behaviors,
            "on": on,
        }],
    }


def actor_id(d):
    return re.sub(r"[^a-z0-9]+", "_", d["name"].lower()).strip("_")


def spawn_weight(data, rarity, home):
    """A species' weight in a biome: its rarity's, or `visitorShare` of it away from home."""
    weight = data.rarities[rarity]["weight"] * (1 if home else data.visitor_share)
    return int(weight) if float(weight).is_integer() else round(weight, 4)


def spawn_tables(data, definitions):
    """For each biome, what can spawn there and how likely: the species at home in it at their rarity's weight,
    and the visitors from other biomes at `visitorShare` of theirs."""
    tables = {}
    for biome in data.biomes:
        rows = []
        for d in definitions:
            if biome not in d["biomes"]: continue
            home = d["biomes"][0] == biome
            rows.append({"species": d["id"], "rarity": d["rarity"], "weight": spawn_weight(data, d["rarity"], home), "home": home})
        order = list(data.rarities)
        rows.sort(key=lambda r: (not r["home"], order.index(r["rarity"]), r["species"]))
        tables[biome] = rows
    return tables


def total_weight(rows):
    total = sum(row["weight"] for row in rows)
    return int(total) if float(total).is_integer() else round(total, 4)


def build_all(data, model_base):
    """Every output file as {relative path: bytes}, with the faults met on the way. Definitions with faults are
    left out, so one bad file does not hide the rest."""
    outputs, faults, entries, good = {}, [], [], []
    for d in data.definitions.values():
        found = data.check_definition(d)
        if found: faults += found; continue
        try:
            glb, made = build_model(data, d)
            document = build_document(data, d, made, model_base)
        except Exception as error:      # an archetype's own fault, reported against the definition that met it
            faults.append("%s: could not be built: %s: %s" % (d["_where"], type(error).__name__, error)); continue
        model_faults, facts = inspect(glb)
        if model_faults: faults += ["%s: the model it builds: %s" % (d["_where"], f) for f in model_faults]; continue
        outputs["models/%s.glb" % d["id"]] = glb
        outputs["creatures/%s.json" % d["id"]] = dump(document)
        box = facts["box"]
        good.append(d)
        entries.append({
            "id": d["id"], "name": d["name"], "species": d["species"], "description": d["description"],
            "biome": d["biomes"][0], "biomes": list(d["biomes"]), "habitat": d["habitat"], "rarity": d["rarity"],
            "weight": data.rarities[d["rarity"]]["weight"], "archetype": d["archetype"],
            "document": "creatures/%s.json" % d["id"], "model": "models/%s.glb" % d["id"], "modelRef": model_reference(model_base, d["id"]),
            "size": [round(box[1][i] - box[0][i], 4) for i in range(3)], "bytes": len(glb), "triangles": facts["triangles"],
        })
    tables = spawn_tables(data, good)
    index = {
        "version": 1,
        "modelBase": model_base,
        "visitorShare": data.visitor_share,
        "rarities": [{"id": r["id"], "name": r["name"], "weight": r["weight"], "colour": r["colour"]} for r in data.rarities.values()],
        "habitats": [{"id": h["id"], "name": h["name"]} for h in data.habitats.values()],
        "codes": {str(b["code"]): b["id"] for b in sorted(data.biomes.values(), key=lambda b: b["code"])},
        "biomes": [{"id": b["id"], "code": b["code"], "name": b["name"], "worldcover": b.get("worldcover", b["name"]), "colour": b["colour"], "description": b["description"],
                    "weight": total_weight(tables[b["id"]]), "spawns": tables[b["id"]]}
                   for b in sorted(data.biomes.values(), key=lambda b: b["code"])],
        "species": entries,
    }
    outputs["index.json"] = dump(index)
    outputs["ROSTER.md"] = roster(data, index).encode("utf-8")
    return outputs, faults


def roster(data, index):
    """ROSTER.md: every species by the biome it is at home in, written from the catalog."""
    species = {entry["id"]: entry for entry in index["species"]}
    lines = ["# The roster", "", "Written by `build.py` from the definitions; do not edit. %d species in %d biomes." % (len(species), len(index["biomes"])), ""]
    lines += ["| biome | WorldCover | at home | " + " | ".join(data.rarities) + " | " + " | ".join(data.habitats) + " | visiting |",
              "| --- | --- | --- |" + " --- |" * (len(data.rarities) + len(data.habitats) + 1)]
    for biome in index["biomes"]:
        home = [species[row["species"]] for row in biome["spawns"] if row["home"]]
        lines.append("| %s (`%s`) | %d %s | %d | %s | %s | %d |" % (
            biome["name"], biome["id"], biome["code"], biome["worldcover"], len(home),
            " | ".join(str(sum(1 for e in home if e["rarity"] == r)) for r in data.rarities),
            " | ".join(str(sum(1 for e in home if e["habitat"] == h)) for h in data.habitats), len(biome["spawns"]) - len(home)))
    for biome in index["biomes"]:
        lines += ["", "## %s (`%s`, WorldCover %d: %s)" % (biome["name"], biome["id"], biome["code"], biome["worldcover"]), "", biome["description"], "",
                  "| creature | species | rarity | habitat | archetype | chance here | also found in |", "| --- | --- | --- | --- | --- | --- | --- |"]
        for row in biome["spawns"]:
            entry = species[row["species"]]
            if not row["home"]: continue
            lines.append("| %s | %s (`%s`) | %s | %s | %s | %.2f%% | %s |" % (entry["name"], entry["species"], entry["id"], entry["rarity"], entry["habitat"], entry["archetype"],
                                                                         100.0 * row["weight"] / biome["weight"], ", ".join(entry["biomes"][1:])))
        visitors = ["%s (%s, %.2f%%)" % (species[row["species"]]["name"], species[row["species"]]["biome"], 100.0 * row["weight"] / biome["weight"]) for row in biome["spawns"] if not row["home"]]
        if visitors: lines += ["", "Visiting from other biomes: %s." % ", ".join(visitors)]
    return "\n".join(lines) + "\n"


def write_all(outputs):
    """Writes the outputs and removes creatures and models no definition makes any more."""
    for folder in ("creatures", "models"):
        os.makedirs(os.path.join(HERE, folder), exist_ok=True)
        for name in os.listdir(os.path.join(HERE, folder)):
            if "%s/%s" % (folder, name) not in outputs and name.endswith((".json", ".glb")): os.remove(os.path.join(HERE, folder, name))
    for path, content in outputs.items():
        with open(os.path.join(HERE, path), "wb") as f: f.write(content)


# ---- checking --------------------------------------------------------------------------------------------------

def check_model(data, d, glb, where):
    """(faults, facts) for one species' .glb: it parses, has the clips its habitat plays, fits the habitat and
    stands where its habitat expects. No facts means it could not be read."""
    habitat, faults = data.habitats[d["habitat"]], []
    model_faults, facts = inspect(glb)
    if model_faults: return ["%s: %s" % (where, f) for f in model_faults], {}
    if len(glb) > MAX_MODEL_BYTES: faults.append("%s: %d bytes, over the %d allowed" % (where, len(glb), MAX_MODEL_BYTES))
    for clip in ("idle", habitat["move"]):
        if clip not in facts["clips"]: faults.append("%s: no clip named %s" % (where, clip))
    extra = sorted(set(facts["clips"]) - {"idle", habitat["move"]})
    if extra: faults.append("%s: clips nothing plays: %s" % (where, ", ".join(extra)))
    lo, hi = facts["box"]
    longest = max(hi[i] - lo[i] for i in range(3))
    if not habitat["size"][0] <= longest <= habitat["size"][1]:
        faults.append("%s: its longest side is %.3f m; a %s creature is %.2f to %.2f m" % (where, longest, d["habitat"], habitat["size"][0], habitat["size"][1]))
    swept = facts["swept"]
    for axis, i in (("wide", 0), ("tall", 1), ("long", 2)):
        room = habitat["bounds"]["max"][i] - habitat["bounds"]["min"][i]
        if swept[1][i] - swept[0][i] > room / 2: faults.append("%s: %.3f m %s in motion, over half the %s's %.2f m" % (where, swept[1][i] - swept[0][i], axis, habitat["name"], room))
    if habitat["origin"] == "ground":
        if not -0.004 <= lo[1] <= 0.004: faults.append("%s: stands %.4f m off the ground (its lowest point should be at 0)" % (where, lo[1]))
    elif not all(lo[i] < 0 < hi[i] for i in range(3)): faults.append("%s: the origin is outside the body; a swimmer's or flier's is at mid-body" % where)
    if any(swept[0][i] < lo[i] - 0.5 * longest or swept[1][i] > hi[i] + 0.5 * longest for i in range(3)):
        faults.append("%s: a clip throws part of it more than half its length outside its resting box" % where)
    eyes = facts.get("eyes")
    if eyes is not None and eyes < lo[2] + (hi[2] - lo[2]) / 3: faults.append("%s: its eyes are in the rear third; the head goes along +Z" % where)
    return faults, facts


def check_outputs(data, outputs, model_base):
    """Faults in what is on disk: against what the definitions build now, and each file on its own terms."""
    faults = []
    on_disk = {}
    for path in outputs:
        try:
            with open(os.path.join(HERE, path), "rb") as f: on_disk[path] = f.read()
        except OSError:
            faults.append("%s: missing; run build.py" % path)
    for folder in ("creatures", "models"):
        for name in sorted(os.listdir(os.path.join(HERE, folder))) if os.path.isdir(os.path.join(HERE, folder)) else []:
            if "%s/%s" % (folder, name) not in outputs: faults.append("%s/%s: no definition makes this file" % (folder, name))
    for path, content in on_disk.items():
        if content != outputs[path]: faults.append("%s: differs from what the definitions build now (edited by hand, or stale); run build.py" % path)

    try: index = json.loads(on_disk.get("index.json", b"{}"))
    except ValueError as error: return faults + ["index.json: does not parse: %s" % error]
    listed = {entry.get("id"): entry for entry in index.get("species", [])}
    if len(listed) != len(index.get("species", [])): faults.append("index.json: a species is listed twice")
    names = {}
    for d in data.definitions.values():
        if not isinstance(d.get("name"), str): continue
        if actor_id(d) in names: faults.append("%s: the name %s is also %s's; names are how a player tells creatures apart" % (d["_where"], d["name"], names[actor_id(d)]))
        names[actor_id(d)] = d["id"]

    for d in data.definitions.values():
        if data.check_definition(d): continue
        sid, where = d["id"], "models/%s.glb" % d["id"]
        habitat = data.habitats[d["habitat"]]
        if sid not in listed: faults.append("index.json: %s is not listed" % sid)
        if where not in on_disk or "creatures/%s.json" % sid not in on_disk: continue

        # The model, read back from disk by the reader; and, when the disk is stale, the one the definition builds now.
        glb = on_disk[where]
        model_faults, facts = check_model(data, d, glb, where)
        faults += model_faults
        if glb != outputs[where]: faults += check_model(data, d, outputs[where], "%s: the model it builds now" % d["_where"])[0]
        if not facts: continue

        # The document.
        path = "creatures/%s.json" % sid
        try: doc = json.loads(on_disk[path])
        except ValueError as error:
            faults.append("%s: does not parse: %s" % (path, error)); continue
        bad = lambda message: faults.append("%s: %s" % (path, message))
        header = doc.get("_ui", {})
        if header.get("version") != 1: bad("_ui.version is not 1")
        expected = {"habitat": d["habitat"], "species": sid, "rarity": d["rarity"], "biome": d["biomes"][0], "biomes": d["biomes"]}
        for key, value in expected.items():
            if header.get(key) != value: bad("_ui.%s is %r, not %r" % (key, header.get(key), value))
        if doc.get("type") != "Scene": bad("type is not Scene")
        if doc.get("anchor") != habitat["anchor"]: bad("anchor is not %s" % habitat["anchor"])
        if doc.get("bounds") != {"min": habitat["wild"]["min"], "max": habitat["wild"]["max"]}: bad("bounds are not the %s habitat's" % d["habitat"])
        actors = doc.get("actors", [])
        if len(actors) != 1: bad("has %d actors, not 1" % len(actors)); continue
        actor = actors[0]
        if actor.get("name") != d["name"] or not re.match(r"^[a-z0-9_]+$", str(actor.get("id", ""))): bad("the actor's id or name is wrong")
        body, mobility = actor.get("body", {}), actor.get("mobility")
        if not isinstance(mobility, dict): bad("the actor has no mobility, so it is not a creature"); continue
        if body.get("model") != model_reference(model_base, sid): bad("body.model is %r, not %r" % (body.get("model"), model_reference(model_base, sid)))
        for role in ("idle", "move"):
            name = mobility.get(role)
            clip = body.get("animations", {}).get(name, {}).get("clip")
            if clip is None: bad("mobility.%s names the animation %r, which the body lacks" % (role, name))
            elif clip not in facts["clips"]: bad("the animation %s plays the clip %r, which the model lacks" % (name, clip))
        for socket, node in body.get("sockets", {}).items():
            if node not in facts["nodes"]: bad("the socket %s names the node %r, which the model lacks" % (socket, node))
        if mobility.get("mode") != habitat["mode"]: bad("mobility.mode is not %s" % habitat["mode"])
        if habitat["mode"] == "air":
            low, high = mobility.get("altitude", [None, None])
            if low is None or not doc["bounds"]["min"][1] <= low < high <= doc["bounds"]["max"][1]: bad("mobility.altitude is outside the bounds")
        keys = set(header.get("state", {}))
        used = set(re.findall(r"\"\$([A-Za-z_][A-Za-z0-9_]*)\"", json.dumps(actor)))
        for behaviour in actor.get("behaviors", []):
            if behaviour.get("type") not in ("idle", "wander", "approach", "flee", "follow", "patrol", "lookAt", "perchOn", "flyTo", "goTo"): bad("unknown behavior type %r" % behaviour.get("type"))
        if used - keys: bad("binds state it does not declare: %s" % ", ".join(sorted(used - keys)))

        entry = listed.get(sid, {})
        for key, value in (("biome", d["biomes"][0]), ("biomes", d["biomes"]), ("habitat", d["habitat"]), ("rarity", d["rarity"]), ("weight", data.rarities[d["rarity"]]["weight"]),
                           ("bytes", len(glb)), ("document", path), ("model", where)):
            if sid in listed and entry.get(key) != value: faults.append("index.json: %s.%s is %r, not %r" % (sid, key, entry.get(key), value))

    # The biomes: rosters, rarities, and the spawn tables against the definitions.
    valid = [d for d in data.definitions.values() if not data.check_definition(d)]
    tables = {b.get("id"): b for b in index.get("biomes", [])}
    codes = index.get("codes", {})
    for biome in data.biomes.values():
        bid, home = biome["id"], [d for d in valid if d["biomes"][0] == biome["id"]]
        if len(home) < biome["roster"]: faults.append("biome %s: %d species at home, its roster needs %d" % (bid, len(home), biome["roster"]))
        missing = [r for r in data.rarities if not any(d["rarity"] == r for d in home)]
        if missing: faults.append("biome %s: no %s species at home" % (bid, ", ".join(missing)))
        if codes.get(str(biome["code"])) != bid: faults.append("index.json: codes does not map %d to %s" % (biome["code"], bid))
        table = tables.get(bid)
        if table is None: faults.append("index.json: no table for the biome %s" % bid); continue
        want = {d["id"]: (d["rarity"], d["biomes"][0] == bid) for d in valid if bid in d["biomes"]}
        got = {row.get("species"): row for row in table.get("spawns", [])}
        if set(want) != set(got): faults.append("index.json: the %s table lists %s, the definitions say %s" % (bid, sorted(got), sorted(want)))
        for sid, (rarity, at_home) in want.items():
            row = got.get(sid)
            if row is None: continue
            weight = spawn_weight(data, rarity, at_home)
            if row.get("rarity") != rarity or row.get("home") != at_home or abs(row.get("weight", 0) - weight) > 1e-6:
                faults.append("index.json: the %s table has %s as %r, not a %s %s at weight %g" % (bid, sid, row, rarity, "resident" if at_home else "visitor", weight))
        if abs(table.get("weight", 0) - sum(row.get("weight", 0) for row in table.get("spawns", []))) > 1e-6: faults.append("index.json: the %s table's weight is not the sum of its rows" % bid)
    return faults


def summary(data):
    """The roster as text: by biome, then what the whole set holds."""
    lines = []
    valid = [d for d in data.definitions.values() if not data.check_definition(d)]
    for biome in sorted(data.biomes.values(), key=lambda b: b["code"]):
        home = [d for d in valid if d["biomes"][0] == biome["id"]]
        counts = ", ".join("%d %s" % (sum(1 for d in home if d["rarity"] == r), r) for r in data.rarities)
        habitats = ", ".join("%d %s" % (sum(1 for d in home if d["habitat"] == h), h) for h in data.habitats)
        lines.append("  %3d %-9s %2d at home (%s; %s), %d visiting" % (biome["code"], biome["id"], len(home), counts, habitats, sum(1 for d in valid if biome["id"] in d["biomes"][1:])))
    lines.append("  %d species: %s; %s" % (len(valid), ", ".join("%d %s" % (sum(1 for d in valid if d["habitat"] == h), h) for h in data.habitats),
                                           ", ".join("%d %s" % (sum(1 for d in valid if d["archetype"] == a), a) for a in data.archetypes)))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="validate the definitions and the files on disk, write nothing")
    parser.add_argument("--model-base", help="how documents name their models: a URL prefix (default %s) or bundle:" % DEFAULT_MODEL_BASE)
    args = parser.parse_args()
    data = Data()
    model_base = args.model_base
    if model_base is None:
        try: model_base = read_json("index.json").get("modelBase", DEFAULT_MODEL_BASE) if args.check else DEFAULT_MODEL_BASE
        except (OSError, ValueError): model_base = DEFAULT_MODEL_BASE
    outputs, faults = build_all(data, model_base)
    faults = data.faults + faults
    if not args.check and not faults: write_all(outputs)
    if args.check or not faults: faults += check_outputs(data, outputs, model_base)       # a build checks what it wrote
    print(summary(data))
    digest = hashlib.sha256()
    for path in sorted(outputs): digest.update(path.encode() + b"\0" + outputs[path])
    print("  %d files, %d bytes, model base %s, sha256 %s" % (len(outputs), sum(len(c) for c in outputs.values()), model_base, digest.hexdigest()[:16]))
    if faults:
        print("\n%d fault%s:" % (len(faults), "" if len(faults) == 1 else "s"))
        for fault in faults: print("  " + fault)
        return 1
    print("checked: no faults" if args.check else "built")
    return 0


if __name__ == "__main__":
    sys.exit(main())
